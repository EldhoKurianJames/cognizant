"""SQLAlchemy ORM models backing the schema-aware query cache."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class QueryCache(Base):
    """Caches a generated SQL query alongside the schema fingerprint used to produce it."""

    __tablename__ = "query_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    generated_sql: Mapped[str] = mapped_column(Text, nullable=False)
    schema_hash_at_cache_time: Mapped[str] = mapped_column(String(64), nullable=False)
    api_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    api_cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    # Values: 'hit', 'miss', 'invalidated_schema_changed'
    cache_status: Mapped[str] = mapped_column(String(32), default="miss")
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class CacheAuditLog(Base):
    """Append-only log of every cache lookup, used for analytics and debugging."""

    __tablename__ = "cache_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    # Values: 'hit', 'miss', 'regenerated_schema_changed'
    cache_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    old_schema_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_schema_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    query_execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    api_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    api_cost_saved: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    user_id: Mapped[str] = mapped_column(String(64), default="demo_user")
