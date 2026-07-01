"""Elasticsearch client wrapper for the API."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

from elasticsearch import Elasticsearch

log = logging.getLogger(__name__)

ES_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
INDEX_ALIAS = os.environ.get("ES_INDEX_ALIAS", "metrics-5m")

_client: Elasticsearch | None = None


def _dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def get_client() -> Elasticsearch:
    global _client
    if _client is None:
        _client = Elasticsearch(ES_URL)
    return _client


def check_health() -> bool:
    try:
        info = get_client().cluster.health()
        return info["status"] in ("green", "yellow")
    except Exception:
        return False


def timeseries(
    metric: str,
    start: datetime,
    end: datetime,
    granularity: str = "5m",
    event_type: str | None = None,
    region: str | None = None,
) -> list[dict[str, Any]]:
    es = get_client()

    filters: list[dict] = [
        {"range": {"window_start": {"gte": _dt(start), "lte": _dt(end)}}},
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
    return [
        {"timestamp": b["key_as_string"], "value": b["metric_value"]["value"]}
        for b in resp["aggregations"]["over_time"]["buckets"]
        if b["metric_value"]["value"] is not None
    ]


def top_n(
    metric: str,
    dimension: str,
    limit: int = 10,
    duration_minutes: int = 60,
) -> list[dict[str, Any]]:
    es = get_client()
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=duration_minutes)

    agg_type = "avg" if metric.startswith("avg_") else "sum"

    body: dict[str, Any] = {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    {"range": {"window_start": {"gte": _dt(start), "lte": _dt(now)}}},
                ],
            }
        },
        "aggs": {
            "by_dimension": {
                "terms": {"field": dimension, "size": limit, "order": {"metric_value": "desc"}},
                "aggs": {"metric_value": {agg_type: {"field": metric}}},
            }
        },
    }

    resp = es.search(index=INDEX_ALIAS, body=body)
    return [
        {"key": b["key"], "value": b["metric_value"]["value"]}
        for b in resp["aggregations"]["by_dimension"]["buckets"]
    ]


def current_stats() -> dict[str, Any]:
    es = get_client()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=10)

    body: dict[str, Any] = {
        "size": 0,
        "query": {"bool": {"filter": [{"range": {"window_start": {"gte": _dt(cutoff)}}}]}},
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
        et = bucket["key"]
        result[et] = {
            "total_count": bucket["total_count"]["value"],
            "latest": [h["_source"] for h in bucket["latest_window"]["hits"]["hits"]],
        }
    return result
