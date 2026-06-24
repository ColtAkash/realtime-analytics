"""Test all 3 ES query patterns against live seeded data."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone, timedelta

from elasticsearch import Elasticsearch
from queries import timeseries, top_n, current_stats

ES_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")


def test_timeseries():
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    end = now

    t0 = time.perf_counter()
    results = timeseries(
        metric="event_count",
        start=start,
        end=end,
        granularity="1h",
        event_type="pageview",
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"timeseries(): {len(results)} buckets, {elapsed_ms:.1f}ms")
    assert len(results) > 0, "Expected non-empty timeseries"
    assert elapsed_ms < 100, f"Query too slow: {elapsed_ms:.1f}ms > 100ms"
    for r in results[:3]:
        print(f"  {r['timestamp']}: {r['value']}")
    print(f"  PASS ({elapsed_ms:.1f}ms)")
    print()


def test_top_n():
    t0 = time.perf_counter()
    results = top_n(
        metric="event_count",
        dimension="region",
        limit=5,
        duration_minutes=1440,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"top_n(): {len(results)} entries, {elapsed_ms:.1f}ms")
    assert len(results) > 0, "Expected non-empty top_n"
    assert elapsed_ms < 100, f"Query too slow: {elapsed_ms:.1f}ms > 100ms"
    for r in results:
        print(f"  {r['key']}: {r['value']}")
    print(f"  PASS ({elapsed_ms:.1f}ms)")
    print()


def test_current_stats():
    t0 = time.perf_counter()
    results = current_stats()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"current_stats(): {len(results)} event types, {elapsed_ms:.1f}ms")
    assert len(results) > 0, "Expected non-empty current_stats"
    assert elapsed_ms < 100, f"Query too slow: {elapsed_ms:.1f}ms > 100ms"
    for event_type, data in results.items():
        print(f"  {event_type}: total_count={data['total_count']}, latest_windows={len(data['latest'])}")
    print(f"  PASS ({elapsed_ms:.1f}ms)")
    print()


def warmup():
    """Run a throwaway query to warm ES caches/JIT."""
    from elasticsearch import Elasticsearch
    es = Elasticsearch(ES_URL)
    es.search(index="metrics-5m", body={"size": 0, "query": {"match_all": {}}})


if __name__ == "__main__":
    print("=" * 50)
    print("Elasticsearch Query Tests")
    print("=" * 50)
    print()
    warmup()
    test_timeseries()
    test_top_n()
    test_current_stats()
    print("All tests passed!")
