"""Cassandra client wrapper — supports local Cassandra and Astra DB."""
from __future__ import annotations

import base64
import logging
import os
import tempfile
from typing import Any

log = logging.getLogger(__name__)

CASSANDRA_HOST = os.environ.get("CASSANDRA_HOST", "localhost")
CASSANDRA_PORT = int(os.environ.get("CASSANDRA_PORT", "9042"))
CASSANDRA_KEYSPACE = os.environ.get("CASSANDRA_KEYSPACE", "analytics")

ASTRA_BUNDLE_B64 = os.environ.get("ASTRA_SECURE_BUNDLE_B64", "")
ASTRA_CLIENT_ID = os.environ.get("ASTRA_CLIENT_ID", "")
ASTRA_CLIENT_SECRET = os.environ.get("ASTRA_CLIENT_SECRET", "")

_session = None
_bundle_path: str | None = None


def _write_bundle() -> str:
    """Decode the base64 bundle once and return the temp file path."""
    global _bundle_path
    if _bundle_path is None:
        f = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        f.write(base64.b64decode(ASTRA_BUNDLE_B64))
        f.close()
        _bundle_path = f.name
        log.info("astra secure connect bundle written to %s", _bundle_path)
    return _bundle_path


def _get_session():
    global _session
    if _session is None:
        from cassandra.cluster import Cluster
        if ASTRA_BUNDLE_B64:
            from cassandra.auth import PlainTextAuthProvider
            auth = PlainTextAuthProvider(ASTRA_CLIENT_ID, ASTRA_CLIENT_SECRET)
            cluster = Cluster(
                cloud={"secure_connect_bundle": _write_bundle()},
                auth_provider=auth,
            )
            log.info("connecting to Astra DB (keyspace=%s)", CASSANDRA_KEYSPACE)
        else:
            cluster = Cluster([CASSANDRA_HOST], port=CASSANDRA_PORT)
            log.info("connecting to local Cassandra %s:%s", CASSANDRA_HOST, CASSANDRA_PORT)
        _session = cluster.connect(CASSANDRA_KEYSPACE)
    return _session


def check_health() -> bool:
    try:
        session = _get_session()
        session.execute("SELECT now() FROM system.local")
        return True
    except Exception:
        return False
