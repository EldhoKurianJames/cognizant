"""Validates, invalidates, and updates cached SQL queries for default and dynamic databases."""

import hashlib
from datetime import datetime, timezone

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import schema_hasher
from db_models import CacheAuditLog, DynamicQueryCache, QueryCache


def compute_question_hash(question: str, connection_id: str | None = None) -> str:
    """Normalize and hash a question, scoped to a specific database connection.

    `connection_id` distinguishes the default configured database (None /
    "default") from any ad-hoc uploaded database (see db_connections.py), so
    the same question text asked against two different databases never
    collides on the same cache entry.
    """
    normalized = " ".join(question.strip().lower().split())
    scope = connection_id or "default"
    return hashlib.sha256(f"{scope}::{normalized}".encode("utf-8")).hexdigest()


def find_cache_entry(
    question_hash: str,
    connection_id: str | None,
    db_session: Session,
) -> QueryCache | DynamicQueryCache | None:
    """Look up a cached query in dynamic_query_cache (if connection_id) or query_cache (default DB)."""
    if connection_id:
        return (
            db_session.query(DynamicQueryCache)
            .filter_by(question_hash=question_hash)
            .first()
        )
    return db_session.query(QueryCache).filter_by(question_hash=question_hash).first()


def is_cache_valid(
    cached_query_entry: QueryCache | DynamicQueryCache,
    current_engine: Engine,
) -> tuple[bool, str | None]:
    """Return (is_valid, current_schema_hash).

    `current_schema_hash` is None if it could not be computed (e.g. the SQL
    references a table that no longer parses), in which case the cache is
    always treated as invalid to be safe.
    """
    try:
        current_hash = schema_hasher.get_schema_hash_for_query(
            cached_query_entry.generated_sql, current_engine
        )
    except Exception:
        return False, None

    return cached_query_entry.schema_hash_at_cache_time == current_hash, current_hash


def invalidate_cache_entry(
    question_hash: str,
    db_session: Session,
    connection_id: str | None = None,
    reason: str = "schema_changed",
    new_schema_hash: str | None = None,
) -> None:
    """Delete a stale cache entry and record the invalidation in the audit log."""
    if connection_id:
        entry = (
            db_session.query(DynamicQueryCache)
            .filter_by(question_hash=question_hash)
            .first()
        )
    else:
        entry = db_session.query(QueryCache).filter_by(question_hash=question_hash).first()

    if entry is None:
        return

    db_session.add(
        CacheAuditLog(
            question=entry.question,
            connection_id=connection_id,
            cache_status="invalidated",
            reason=reason,
            old_schema_hash=entry.schema_hash_at_cache_time,
            new_schema_hash=new_schema_hash,
            query_execution_time_ms=0,
            api_tokens_used=0,
            api_cost_saved=0.0,
            user_id="demo_user",
        )
    )
    db_session.delete(entry)
    db_session.commit()


def update_cache_entry(
    question: str,
    question_hash: str,
    new_sql: str,
    new_hash: str,
    tokens_used: int,
    api_cost: float,
    db_session: Session,
    cache_status: str = "miss",
    connection_id: str | None = None,
) -> QueryCache | DynamicQueryCache:
    """Insert or update the cache entry with a freshly generated query in dynamic_query_cache or query_cache."""
    now = datetime.now(timezone.utc)

    if connection_id:
        entry = (
            db_session.query(DynamicQueryCache)
            .filter_by(question_hash=question_hash)
            .first()
        )
        if entry is None:
            entry = DynamicQueryCache(
                connection_id=connection_id,
                question=question,
                question_hash=question_hash,
                generated_sql=new_sql,
                schema_hash_at_cache_time=new_hash,
                api_tokens_used=tokens_used,
                api_cost=api_cost,
                hit_count=0,
                cache_status=cache_status,
                last_used_at=now,
            )
            db_session.add(entry)
        else:
            entry.generated_sql = new_sql
            entry.schema_hash_at_cache_time = new_hash
            entry.api_tokens_used = tokens_used
            entry.api_cost = api_cost
            entry.cache_status = cache_status
            entry.last_used_at = now
    else:
        entry = db_session.query(QueryCache).filter_by(question_hash=question_hash).first()
        if entry is None:
            entry = QueryCache(
                question=question,
                question_hash=question_hash,
                generated_sql=new_sql,
                schema_hash_at_cache_time=new_hash,
                api_tokens_used=tokens_used,
                api_cost=api_cost,
                hit_count=0,
                cache_status=cache_status,
                last_used_at=now,
            )
            db_session.add(entry)
        else:
            entry.generated_sql = new_sql
            entry.schema_hash_at_cache_time = new_hash
            entry.api_tokens_used = tokens_used
            entry.api_cost = api_cost
            entry.cache_status = cache_status
            entry.last_used_at = now

    db_session.commit()
    db_session.refresh(entry)
    return entry


def record_cache_hit(
    entry: QueryCache | DynamicQueryCache,
    db_session: Session,
    execution_time_ms: int,
    connection_id: str | None = None,
) -> None:
    """Bump hit_count/last_used_at on a cache hit and log it in CacheAuditLog for analytics."""
    entry.hit_count += 1
    entry.cache_status = "hit"
    entry.last_used_at = datetime.now(timezone.utc)

    db_session.add(
        CacheAuditLog(
            question=entry.question,
            connection_id=connection_id,
            cache_status="hit",
            reason=None,
            old_schema_hash=None,
            new_schema_hash=entry.schema_hash_at_cache_time,
            query_execution_time_ms=execution_time_ms,
            api_tokens_used=0,
            api_cost_saved=entry.api_cost,
            user_id="demo_user",
        )
    )
    db_session.commit()


def record_cache_miss(
    question: str,
    db_session: Session,
    execution_time_ms: int,
    tokens_used: int,
    schema_hash: str | None,
    cache_status: str = "miss",
    connection_id: str | None = None,
) -> None:
    """Log a cache miss or regenerated event in CacheAuditLog for analytics."""
    db_session.add(
        CacheAuditLog(
            question=question,
            connection_id=connection_id,
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
    db_session.commit()
