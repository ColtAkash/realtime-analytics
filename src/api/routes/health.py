from __future__ import annotations

from fastapi import APIRouter

from db import cassandra as cass_db
from db import elasticsearch as es_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    cassandra_ok = cass_db.check_health()
    es_ok = es_db.check_health()
    all_ok = cassandra_ok and es_ok
    return {
        "status": "ok" if all_ok else "degraded",
        "cassandra_ok": cassandra_ok,
        "es_ok": es_ok,
    }
