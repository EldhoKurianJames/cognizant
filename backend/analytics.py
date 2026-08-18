"""Cache analytics endpoints: hit rate, cost saved, top cached queries, invalidations."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db_session
from db_models import CacheAuditLog, QueryCache
from models import (
    CacheAnalyticsResponse,
    CacheInvalidationEvent,
    CacheInvalidationsResponse,
    TopCachedQuery,
)

router = APIRouter(prefix="/analytics", tags=["cache-analytics"])


@router.get("/cache", response_model=CacheAnalyticsResponse)
def cache_analytics(db: Session = Depends(get_db_session)):
    total_hits = db.query(CacheAuditLog).filter(CacheAuditLog.cache_status == "hit").count()
    total_misses = db.query(CacheAuditLog).filter(CacheAuditLog.cache_status == "miss").count()
    total_invalidations = (
        db.query(CacheAuditLog)
        .filter(CacheAuditLog.cache_status == "regenerated_schema_changed")
        .count()
    )
    total_queries_cached = db.query(QueryCache).count()

    denominator = total_hits + total_misses + total_invalidations
    hit_rate = round(total_hits / denominator, 4) if denominator else 0.0

    total_cost_saved = (
        db.query(func.coalesce(func.sum(CacheAuditLog.api_cost_saved), 0.0))
        .filter(CacheAuditLog.cache_status == "hit")
        .scalar()
        or 0.0
    )

    top_entries = (
        db.query(QueryCache)
        .order_by(QueryCache.hit_count.desc())
        .limit(10)
        .all()
    )
    top_cached_queries = [
        TopCachedQuery(
            question=entry.question,
            hit_count=entry.hit_count,
            cost_saved=round(entry.hit_count * entry.api_cost, 6),
            last_used_at=entry.last_used_at,
        )
        for entry in top_entries
    ]

    return CacheAnalyticsResponse(
        total_queries_cached=total_queries_cached,
        total_cache_hits=total_hits,
        total_cache_misses=total_misses,
        total_invalidations=total_invalidations,
        hit_rate=hit_rate,
        total_cost_saved=round(total_cost_saved, 6),
        top_cached_queries=top_cached_queries,
    )


@router.get("/cache-invalidations", response_model=CacheInvalidationsResponse)
def cache_invalidations(db: Session = Depends(get_db_session)):
    events = (
        db.query(CacheAuditLog)
        .filter(CacheAuditLog.cache_status == "invalidated")
        .order_by(CacheAuditLog.created_at.desc())
        .limit(50)
        .all()
    )
    return CacheInvalidationsResponse(
        invalidations=[
            CacheInvalidationEvent(
                question=event.question,
                reason=event.reason,
                old_schema_hash=event.old_schema_hash,
                new_schema_hash=event.new_schema_hash,
                created_at=event.created_at,
            )
            for event in events
        ]
    )
