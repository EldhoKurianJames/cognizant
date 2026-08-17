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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import get_engine
from models import ExecuteSQLRequest, QueryRequest, QueryResponse
from schema_introspection import format_schema_for_context, get_database_schema
from sql_generator import generate_sql_from_question
from sql_templates import try_template_match
from sql_validator import validate_sql

app = FastAPI(title="Text-to-SQL Analytics API")

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
def query(request: QueryRequest):
    engine = get_engine()

    try:
        tables = get_database_schema(engine)
        schema_context = format_schema_for_context(tables)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read schema: {e}")

    # Fast path: try a deterministic rule-based match before calling the LLM.
    sql = try_template_match(request.question, tables)
    source = "template"

    if sql is None:
        try:
            sql = generate_sql_from_question(request.question, schema_context)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"SQL generation failed: {e}")
        source = "llm"

    try:
        validate_sql(sql)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Generated SQL rejected: {e} | SQL: {sql}")

    try:
        columns, rows = _run_select(sql)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {e} | SQL: {sql}")

    return QueryResponse(
        question=request.question,
        sql=sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        source=source,
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
