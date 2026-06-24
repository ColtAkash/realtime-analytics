"""Cassandra write load test.

Writes 10k rows/sec for 30 seconds across all three tables,
reports p50/p95/p99 write latency.
"""
from __future__ import annotations

import os
import random
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

from cassandra.cluster import Cluster
from cassandra.query import BatchStatement, SimpleStatement

CASSANDRA_HOST = os.environ.get("CASSANDRA_HOST", "localhost")
CASSANDRA_PORT = int(os.environ.get("CASSANDRA_PORT", "9042"))
CASSANDRA_KEYSPACE = os.environ.get("CASSANDRA_KEYSPACE", "analytics")

TARGET_RATE = 10_000
DURATION_SEC = 30
BATCH_SIZE = 50
CONCURRENCY = 16

EVENT_TYPES = ["pageview", "purchase", "system_error"]
REGIONS = ["us-east", "us-west", "eu-west", "ap-south"]


def connect():
    cluster = Cluster([CASSANDRA_HOST], port=CASSANDRA_PORT)
    session = cluster.connect(CASSANDRA_KEYSPACE)
    return cluster, session


def prepare_statements(session):
    metrics_5min = session.prepare(
        "INSERT INTO metrics_5min "
        "(event_type, region, window_start, window_end, event_count, "
        "avg_duration_ms, purchase_total_usd, avg_amount_usd, "
        "severity_info, severity_warning, severity_error, severity_critical, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    metrics_15min = session.prepare(
        "INSERT INTO metrics_15min "
        "(event_type, region, window_start, window_end, event_count, "
        "avg_duration_ms, purchase_total_usd, avg_amount_usd, "
        "severity_info, severity_warning, severity_error, severity_critical, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    user_sessions = session.prepare(
        "INSERT INTO user_sessions "
        "(user_id, session_id, started_at, ended_at, page_count, "
        "purchase_count, total_duration_ms, total_spent_usd, last_page) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    return metrics_5min, metrics_15min, user_sessions


def gen_metrics_row(base_time: datetime):
    event_type = random.choice(EVENT_TYPES)
    region = random.choice(REGIONS)
    offset = random.randint(0, 1000) * 5
    window_start = base_time + timedelta(minutes=offset)
    window_end = window_start + timedelta(minutes=5)
    now = datetime.now(timezone.utc)
    return (
        event_type, region, window_start, window_end,
        random.randint(1, 10000),
        random.uniform(100, 120000) if event_type == "pageview" else None,
        random.uniform(10, 50000) if event_type == "purchase" else None,
        random.uniform(1, 500) if event_type == "purchase" else None,
        random.randint(0, 100) if event_type == "system_error" else 0,
        random.randint(0, 50) if event_type == "system_error" else 0,
        random.randint(0, 30) if event_type == "system_error" else 0,
        random.randint(0, 10) if event_type == "system_error" else 0,
        now,
    )


def gen_session_row():
    now = datetime.now(timezone.utc)
    started = now - timedelta(minutes=random.randint(1, 60))
    return (
        f"u-{uuid.uuid4().hex[:12]}",
        f"s-{uuid.uuid4().hex[:12]}",
        started,
        now,
        random.randint(1, 50),
        random.randint(0, 5),
        random.randint(1000, 300000),
        round(random.uniform(0, 500), 2),
        random.choice(["/", "/products", "/cart", "/checkout", "/account"]),
    )


def write_batch(session, stmts, base_time):
    """Write one batch of BATCH_SIZE rows, return latency in ms."""
    metrics_5min, metrics_15min, user_sessions = stmts

    start = time.perf_counter()
    for _ in range(BATCH_SIZE):
        table_choice = random.random()
        if table_choice < 0.4:
            row = gen_metrics_row(base_time)
            session.execute(metrics_5min.bind(row))
        elif table_choice < 0.8:
            row = gen_metrics_row(base_time)
            session.execute(metrics_15min.bind(row))
        else:
            row = gen_session_row()
            session.execute(user_sessions.bind(row))

    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms


def percentile(data: list[float], pct: float) -> float:
    idx = int(len(data) * pct / 100)
    return sorted(data)[min(idx, len(data) - 1)]


def main():
    cluster, session = connect()
    stmts = prepare_statements(session)

    batches_per_sec = TARGET_RATE // BATCH_SIZE
    total_batches = batches_per_sec * DURATION_SEC
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    print(f"Load test: {TARGET_RATE} rows/sec × {DURATION_SEC}s = {TARGET_RATE * DURATION_SEC:,} total rows")
    print(f"Batch size: {BATCH_SIZE}, batches/sec: {batches_per_sec}, concurrency: {CONCURRENCY}")
    print()

    latencies: list[float] = []
    total_rows = 0
    test_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        for sec in range(DURATION_SEC):
            sec_start = time.perf_counter()
            futures = []
            for _ in range(batches_per_sec):
                futures.append(pool.submit(write_batch, session, stmts, base_time))

            for f in as_completed(futures):
                batch_latency = f.result()
                per_row = batch_latency / BATCH_SIZE
                latencies.append(per_row)
                total_rows += BATCH_SIZE

            elapsed = time.perf_counter() - sec_start
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

            if (sec + 1) % 10 == 0:
                rate = total_rows / (time.perf_counter() - test_start)
                print(f"  [{sec+1:2d}s] {total_rows:>8,} rows written, {rate:,.0f} rows/sec")

    total_elapsed = time.perf_counter() - test_start

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)

    print()
    print("=" * 50)
    print(f"Total rows:   {total_rows:,}")
    print(f"Duration:     {total_elapsed:.1f}s")
    print(f"Throughput:   {total_rows / total_elapsed:,.0f} rows/sec")
    print()
    print(f"Write latency (per row):")
    print(f"  p50:  {p50:.2f} ms")
    print(f"  p95:  {p95:.2f} ms")
    print(f"  p99:  {p99:.2f} ms")
    print("=" * 50)

    cluster.shutdown()

    if p99 > 50:
        print(f"\nFAIL: p99 ({p99:.2f}ms) exceeds 50ms threshold")
        exit(1)
    else:
        print(f"\nPASS: p99 ({p99:.2f}ms) is within 50ms threshold")


if __name__ == "__main__":
    main()
