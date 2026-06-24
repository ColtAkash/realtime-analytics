from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Annotated, Any

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

import cache
from db import elasticsearch as es_db

log = logging.getLogger(__name__)

router = APIRouter()

VALID_METRICS = {"event_count", "avg_duration_ms", "purchase_total_usd", "avg_amount_usd"}
VALID_DIMENSIONS = {"event_type", "region"}
VALID_GRANULARITIES = {"5m", "15m", "1h", "1d"}


class TimeseriesPoint(BaseModel):
    timestamp: str
    value: float | None


class TopNEntry(BaseModel):
    key: str
    value: float | None


def _cache_key(prefix: str, **kwargs) -> str:
    raw = json.dumps(kwargs, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"


@router.get("/timeseries", response_model=list[TimeseriesPoint])
def get_timeseries(
    metric: Annotated[str, Query(description="Metric field to aggregate")] = "event_count",
    start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
    granularity: Annotated[str, Query(description="Interval: 5m, 15m, 1h, 1d")] = "1h",
    event_type: Annotated[str | None, Query(description="Filter by event type")] = None,
    region: Annotated[str | None, Query(description="Filter by region")] = None,
):
    if metric not in VALID_METRICS:
        raise HTTPException(400, f"Invalid metric. Choose from: {VALID_METRICS}")
    if granularity not in VALID_GRANULARITIES:
        raise HTTPException(400, f"Invalid granularity. Choose from: {VALID_GRANULARITIES}")

    now = datetime.now(timezone.utc)
    start = start or (now - timedelta(hours=24))
    end = end or now

    key = _cache_key("ts", metric=metric, start=start, end=end,
                     granularity=granularity, event_type=event_type, region=region)
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = es_db.timeseries(
        metric=metric, start=start, end=end,
        granularity=granularity, event_type=event_type, region=region,
    )
    cache.put(key, result)
    return result


@router.get("/topN", response_model=list[TopNEntry])
def get_top_n(
    metric: Annotated[str, Query(description="Metric field to aggregate")] = "event_count",
    dimension: Annotated[str, Query(description="Dimension to group by")] = "region",
    limit: Annotated[int, Query(ge=1, le=100, description="Number of results")] = 10,
    duration: Annotated[str, Query(description="Lookback: 1h, 6h, 24h")] = "1h",
):
    if metric not in VALID_METRICS:
        raise HTTPException(400, f"Invalid metric. Choose from: {VALID_METRICS}")
    if dimension not in VALID_DIMENSIONS:
        raise HTTPException(400, f"Invalid dimension. Choose from: {VALID_DIMENSIONS}")

    duration_map = {"5m": 5, "15m": 15, "1h": 60, "6h": 360, "24h": 1440}
    duration_minutes = duration_map.get(duration)
    if duration_minutes is None:
        raise HTTPException(400, f"Invalid duration. Choose from: {list(duration_map.keys())}")

    key = _cache_key("topn", metric=metric, dimension=dimension,
                     limit=limit, duration=duration)
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = es_db.top_n(
        metric=metric, dimension=dimension,
        limit=limit, duration_minutes=duration_minutes,
    )
    cache.put(key, result)
    return result


@router.get("/snapshot")
def get_snapshot():
    key = "snapshot:current"
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = es_db.current_stats()
    cache.put(key, result)
    return result
