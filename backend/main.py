import os
import socket

# Monkeypatch socket.getaddrinfo to bypass local DNS resolution timeouts if requested
if os.getenv("BYPASS_DNS_TIMEOUTS", "false").lower() == "true":
    _orig_getaddrinfo = socket.getaddrinfo

    def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host == "generativelanguage.googleapis.com":
            return _orig_getaddrinfo("172.217.117.4", port, family, type, proto, flags)
        elif host == "ep-wispy-sun-axuj92z8-pooler.c-4.us-east-2.aws.neon.tech":
            return _orig_getaddrinfo("18.226.241.3", port, family, type, proto, flags)
        return _orig_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = custom_getaddrinfo

import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

import cache_validator
import schema_hasher
from analytics import router as analytics_router
from database import get_db_session, get_engine
from db_models import Base, CacheAuditLog, QueryCache
from models import ExecuteSQLRequest, QueryRequest, QueryResponse
from schema_introspection import format_schema_for_context, get_database_schema
from sql_generator import generate_sql_from_question
from sql_templates import try_template_match
from sql_validator import validate_sql

app = FastAPI(title="Text-to-SQL Analytics API")
app.include_router(analytics_router)

# Create the query cache tables on startup if they don't already exist.
Base.metadata.create_all(bind=get_engine())

ENABLE_QUERY_CACHE = os.getenv("ENABLE_QUERY_CACHE", "true").lower() == "true"
CACHE_INVALIDATION_ON_SCHEMA_CHANGE = (
    os.getenv("CACHE_INVALIDATION_ON_SCHEMA_CHANGE", "true").lower() == "true"
)
HAIKU_PRICE_PER_TOKEN = float(os.getenv("HAIKU_PRICE_PER_TOKEN", "0.0000015"))

allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,https://main.d3dz7qujv68w6q.amplifyapp.com")
allowed_origins = [origin.strip().rstrip("/") for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_select(sql: str) -> tuple[list[str], list[dict]]:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return columns, rows


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schema")
def schema():
    try:
        engine = get_engine()
        tables = get_database_schema(engine)
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, db: Session = Depends(get_db_session)):
    engine = get_engine()
    start_time = time.perf_counter()

    from_cache = False
    cache_status = "n/a"
    schema_hash = None
    tokens_used = 0
    api_cost = 0.0
    api_cost_saved = 0.0
    source = "template"
    sql = None
    cached_entry = None
    schema_changed_invalidation = False
    question_hash = cache_validator.compute_question_hash(request.question)

    # 1. Try the cache first (only ever populated by LLM-generated queries).
    if ENABLE_QUERY_CACHE:
        existing_entry = db.query(QueryCache).filter_by(question_hash=question_hash).first()
        if existing_entry is not None:
            valid, current_hash = cache_validator.is_cache_valid(existing_entry, engine)
            if valid:
                cached_entry = existing_entry
                sql = existing_entry.generated_sql
                source = "llm"
                from_cache = True
                cache_status = "hit"
                schema_hash = current_hash
                api_cost_saved = existing_entry.api_cost
                # execution time is recorded below, once the query actually runs.
            elif CACHE_INVALIDATION_ON_SCHEMA_CHANGE:
                cache_validator.invalidate_cache_entry(
                    question_hash, db, reason="schema_changed", new_schema_hash=current_hash
                )
                schema_changed_invalidation = True

    # 2. No valid cache entry: try the deterministic template match, then the LLM.
    if sql is None:
        try:
            tables = get_database_schema(engine)
            schema_context = format_schema_for_context(tables)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read schema: {e}")

        sql = try_template_match(request.question, tables)
        source = "template"

        if sql is None:
            try:
                sql, tokens_used = generate_sql_from_question(request.question, schema_context)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"SQL generation failed: {e}")
            source = "llm"

            try:
                schema_hash = schema_hasher.get_schema_hash_for_query(sql, engine)
            except Exception:
                schema_hash = None

            api_cost = round(tokens_used * HAIKU_PRICE_PER_TOKEN, 6)
            cache_status = "regenerated_schema_changed" if schema_changed_invalidation else "miss"

            if ENABLE_QUERY_CACHE and schema_hash is not None:
                cache_validator.update_cache_entry(
                    question=request.question,
                    question_hash=question_hash,
                    new_sql=sql,
                    new_hash=schema_hash,
                    tokens_used=tokens_used,
                    api_cost=api_cost,
                    db_session=db,
                    cache_status=cache_status,
                )

    try:
        validate_sql(sql)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Generated SQL rejected: {e} | SQL: {sql}")

    try:
        columns, rows = _run_select(sql)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {e} | SQL: {sql}")

    execution_time_ms = int((time.perf_counter() - start_time) * 1000)

    if from_cache:
        cache_validator.record_cache_hit(cached_entry, db, execution_time_ms)
    elif source == "llm":
        db.add(
            CacheAuditLog(
                question=request.question,
                cache_status=cache_status,
                reason="schema_changed" if cache_status == "regenerated_schema_changed" else None,
                old_schema_hash=None,
                new_schema_hash=schema_hash,
                query_execution_time_ms=execution_time_ms,
                api_tokens_used=tokens_used,
                api_cost_saved=0.0,
                user_id="demo_user",
            )
        )
        db.commit()

    return QueryResponse(
        question=request.question,
        sql=sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        source=source,
        from_cache=from_cache,
        cache_status=cache_status,
        schema_hash=schema_hash,
        execution_time_ms=execution_time_ms,
        api_tokens_used=tokens_used,
        api_cost=api_cost,
        api_cost_saved=api_cost_saved,
    )


@app.post("/execute-sql")
def execute_sql(request: ExecuteSQLRequest):
    try:
        validate_sql(request.sql)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        columns, rows = _run_select(request.sql)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {e}")

    return {"sql": request.sql, "columns": columns, "rows": rows, "row_count": len(rows)}
