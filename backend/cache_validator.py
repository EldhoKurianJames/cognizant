"""Validates, invalidates, and updates cached SQL queries.

A cached query is considered valid only if the schema hash of the tables it
references is unchanged since it was cached. Pure data changes never
invalidate the cache; only structural schema changes do.
"""

import hashlib
from datetime import datetime, timezone

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import schema_hasher
from db_models import CacheAuditLog, QueryCache


def compute_question_hash(question: str) -> str:
    """Normalize and hash a question so semantically identical questions collide."""
    normalized = " ".join(question.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def is_cache_valid(cached_query_entry: QueryCache, current_engine: Engine) -> tuple[bool, str | None]:
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
    reason: str = "schema_changed",
    new_schema_hash: str | None = None,
) -> None:
    """Delete a stale cache entry and record the invalidation in the audit log."""
    entry = db_session.query(QueryCache).filter_by(question_hash=question_hash).first()
    if entry is None:
        return

    db_session.add(
        CacheAuditLog(
            question=entry.question,
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
) -> QueryCache:
    """Insert or update the cache entry for `question_hash` with a freshly generated query."""
    entry = db_session.query(QueryCache).filter_by(question_hash=question_hash).first()
    now = datetime.now(timezone.utc)

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


def record_cache_hit(entry: QueryCache, db_session: Session, execution_time_ms: int) -> None:
    """Bump hit_count/last_used_at on a cache hit and log it for analytics."""
    entry.hit_count += 1
    entry.cache_status = "hit"
    entry.last_used_at = datetime.now(timezone.utc)

    db_session.add(
        CacheAuditLog(
            question=entry.question,
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
