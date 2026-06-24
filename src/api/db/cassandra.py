"""Cassandra client wrapper for the API."""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

CASSANDRA_HOST = os.environ.get("CASSANDRA_HOST", "localhost")
CASSANDRA_PORT = int(os.environ.get("CASSANDRA_PORT", "9042"))
CASSANDRA_KEYSPACE = os.environ.get("CASSANDRA_KEYSPACE", "analytics")

_session = None


def _get_session():
    global _session
    if _session is None:
        from cassandra.cluster import Cluster
        cluster = Cluster([CASSANDRA_HOST], port=CASSANDRA_PORT)
        _session = cluster.connect(CASSANDRA_KEYSPACE)
    return _session


def check_health() -> bool:
    try:
        session = _get_session()
        session.execute("SELECT now() FROM system.local")
        return True
    except Exception:
        return False
