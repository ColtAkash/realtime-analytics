"""Background task that polls ES every 1s and broadcasts snapshots via WebSocket."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from db import elasticsearch as es_db

log = logging.getLogger(__name__)

BROADCAST_INTERVAL = 1.0


def _build_snapshot() -> dict[str, Any]:
    """Build the compact snapshot payload from ES current_stats."""
    try:
        raw = es_db.current_stats()
    except Exception as e:
        log.warning("es query failed: %s", e)
        return _empty_snapshot()

    event_type_counts: dict[str, float] = {}
    purchase_total = 0.0
    error_count = 0
    total_count = 0

    for event_type, data in raw.items():
        count = data.get("total_count", 0)
        event_type_counts[event_type] = count
        total_count += count

        if event_type == "purchase":
            for entry in data.get("latest", []):
                purchase_total += entry.get("purchase_total_usd", 0) or 0

        if event_type == "system_error":
            error_count += count

    error_rate = (error_count / total_count * 100) if total_count > 0 else 0.0

    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "event_type_counts": event_type_counts,
        "purchase_total_usd": round(purchase_total, 2),
        "error_rate": round(error_rate, 2),
    }


def _empty_snapshot() -> dict[str, Any]:
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "event_type_counts": {},
        "purchase_total_usd": 0.0,
        "error_rate": 0.0,
    }


async def broadcast_loop(manager) -> None:
    """Run in a background task — polls ES and broadcasts to all WS clients."""
    log.info("broadcast loop started")
    while True:
        if manager.count > 0:
            snapshot = await asyncio.get_event_loop().run_in_executor(None, _build_snapshot)
            await manager.broadcast(snapshot)

        await asyncio.sleep(BROADCAST_INTERVAL)


def get_snapshot_sync() -> dict[str, Any]:
    """Synchronous snapshot for initial send on connect."""
    return _build_snapshot()
