"""Elasticsearch query patterns for the analytics API."""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any

from elasticsearch import Elasticsearch

ES_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
INDEX_ALIAS = "metrics-5m"


def get_client() -> Elasticsearch:
    return Elasticsearch(ES_URL)


def timeseries(
    metric: str,
    start: datetime,
    end: datetime,
    granularity: str = "5m",
    event_type: str | None = None,
    region: str | None = None,
    client: Elasticsearch | None = None,
) -> list[dict[str, Any]]:
    """Date histogram aggregation over a time range.

    Args:
        metric: Field to aggregate — 'event_count', 'avg_duration_ms',
                'purchase_total_usd', 'avg_amount_usd'.
        start/end: Time range boundaries (UTC).
        granularity: Calendar interval — '5m', '15m', '1h', '1d'.
        event_type: Optional filter.
        region: Optional filter.

    Returns:
        List of {timestamp, value} dicts.
    """
    es = client or get_client()

    filters: list[dict] = [
        {"range": {"window_start": {"gte": start.isoformat(), "lte": end.isoformat()}}},
    ]
    if event_type:
        filters.append({"term": {"event_type": event_type}})
    if region:
        filters.append({"term": {"region": region}})

    agg_type = "avg" if metric.startswith("avg_") else "sum"

    body: dict[str, Any] = {
        "size": 0,
        "query": {"bool": {"filter": filters}},
        "aggs": {
            "over_time": {
                "date_histogram": {
                    "field": "window_start",
                    "fixed_interval": granularity,
                },
                "aggs": {
                    "metric_value": {agg_type: {"field": metric}},
                },
            }
        },
    }

    resp = es.search(index=INDEX_ALIAS, body=body)
    buckets = resp["aggregations"]["over_time"]["buckets"]
    return [
        {
            "timestamp": b["key_as_string"],
            "value": b["metric_value"]["value"],
        }
        for b in buckets
        if b["metric_value"]["value"] is not None
    ]


def top_n(
    metric: str,
    dimension: str,
    limit: int = 10,
    duration_minutes: int = 60,
    client: Elasticsearch | None = None,
) -> list[dict[str, Any]]:
    """Terms aggregation for top-N by a given metric.

    Args:
        metric: Field to aggregate — 'event_count', 'purchase_total_usd', etc.
        dimension: Field to group by — 'event_type', 'region'.
        limit: Number of top entries.
        duration_minutes: Lookback window from now.

    Returns:
        List of {key, value} dicts ordered descending.
    """
    es = client or get_client()
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=duration_minutes)

    agg_type = "avg" if metric.startswith("avg_") else "sum"

    body: dict[str, Any] = {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    {"range": {"window_start": {"gte": start.isoformat(), "lte": now.isoformat()}}},
                ],
            }
        },
        "aggs": {
            "by_dimension": {
                "terms": {
                    "field": dimension,
                    "size": limit,
                    "order": {"metric_value": "desc"},
                },
                "aggs": {
                    "metric_value": {agg_type: {"field": metric}},
                },
            }
        },
    }

    resp = es.search(index=INDEX_ALIAS, body=body)
    buckets = resp["aggregations"]["by_dimension"]["buckets"]
    return [
        {"key": b["key"], "value": b["metric_value"]["value"]}
        for b in buckets
    ]


def current_stats(
    client: Elasticsearch | None = None,
) -> dict[str, Any]:
    """Snapshot of the latest 5-minute window across all event types.

    Returns dict with per-event-type stats from the most recent window.
    """
    es = client or get_client()
    now = datetime.now(timezone.utc)
    five_min_ago = now - timedelta(minutes=10)

    body: dict[str, Any] = {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    {"range": {"window_start": {"gte": five_min_ago.isoformat()}}},
                ],
            }
        },
        "aggs": {
            "by_type": {
                "terms": {"field": "event_type", "size": 10},
                "aggs": {
                    "latest_window": {
                        "top_hits": {
                            "sort": [{"window_start": {"order": "desc"}}],
                            "size": 5,
                            "_source": [
                                "event_type", "region", "window_start",
                                "event_count", "avg_duration_ms",
                                "purchase_total_usd", "avg_amount_usd",
                                "severity_info", "severity_warning",
                                "severity_error", "severity_critical",
                            ],
                        },
                    },
                    "total_count": {"sum": {"field": "event_count"}},
                },
            },
        },
    }

    resp = es.search(index=INDEX_ALIAS, body=body)
    result: dict[str, Any] = {}
    for bucket in resp["aggregations"]["by_type"]["buckets"]:
        event_type = bucket["key"]
        result[event_type] = {
            "total_count": bucket["total_count"]["value"],
            "latest": [
                hit["_source"]
                for hit in bucket["latest_window"]["hits"]["hits"]
            ],
        }
    return result
