"""Seed Elasticsearch with aggregate data from Cassandra for testing."""
from __future__ import annotations

import os
import random
from datetime import datetime, timezone, timedelta

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

ES_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
INDEX_ALIAS = "metrics-5m"

EVENT_TYPES = ["pageview", "purchase", "system_error"]
REGIONS = ["us-east", "us-west", "eu-west", "ap-south"]
SERVICES = ["api-gateway", "payment-svc", "auth-svc", "search-svc"]


def generate_docs(hours: int = 24) -> list[dict]:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    base = now - timedelta(hours=hours)
    docs = []

    windows = int(hours * 60 / 5)
    for i in range(windows):
        window_start = base + timedelta(minutes=i * 5)
        window_end = window_start + timedelta(minutes=5)

        for region in REGIONS:
            docs.append({
                "_index": INDEX_ALIAS,
                "event_type": "pageview",
                "region": region,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
                "event_count": random.randint(50, 200),
                "avg_duration_ms": round(random.uniform(5000, 60000), 1),
                "purchase_total_usd": None,
                "avg_amount_usd": None,
                "severity_info": 0,
                "severity_warning": 0,
                "severity_error": 0,
                "severity_critical": 0,
                "updated_at": window_end.isoformat(),
            })

            docs.append({
                "_index": INDEX_ALIAS,
                "event_type": "purchase",
                "region": region,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
                "event_count": random.randint(5, 50),
                "avg_duration_ms": None,
                "purchase_total_usd": round(random.uniform(500, 5000), 2),
                "avg_amount_usd": round(random.uniform(20, 200), 2),
                "severity_info": 0,
                "severity_warning": 0,
                "severity_error": 0,
                "severity_critical": 0,
                "updated_at": window_end.isoformat(),
            })

        for svc in SERVICES:
            docs.append({
                "_index": INDEX_ALIAS,
                "event_type": "system_error",
                "region": svc,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
                "event_count": random.randint(0, 15),
                "avg_duration_ms": None,
                "purchase_total_usd": None,
                "avg_amount_usd": None,
                "severity_info": random.randint(0, 5),
                "severity_warning": random.randint(0, 3),
                "severity_error": random.randint(0, 3),
                "severity_critical": random.randint(0, 1),
                "updated_at": window_end.isoformat(),
            })

    return docs


def main():
    es = Elasticsearch(ES_URL)
    docs = generate_docs(hours=24)
    print(f"Seeding {len(docs)} documents into {INDEX_ALIAS}...")
    success, errors = bulk(es, docs, raise_on_error=False)
    print(f"Indexed: {success}, errors: {len(errors) if isinstance(errors, list) else errors}")
    es.indices.refresh(index=INDEX_ALIAS)
    count = es.count(index=INDEX_ALIAS)["count"]
    print(f"Total docs in index: {count}")


if __name__ == "__main__":
    main()
