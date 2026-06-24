from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Any

PAGES = [
    "/", "/products", "/products/widget", "/products/gadget",
    "/cart", "/checkout", "/account", "/search", "/about",
]

REGIONS = ["us-east", "us-west", "eu-west", "ap-south"]

ITEMS = [f"item-{i}" for i in range(1, 51)]

SERVICES = ["api-gateway", "payment-svc", "auth-svc", "search-svc"]

SEVERITIES = ["info", "warning", "error", "critical"]

ERROR_MESSAGES = [
    "upstream timeout after 30s",
    "connection refused",
    "rate limit exceeded",
    "invalid token",
    "database connection pool exhausted",
    "disk space low",
    "memory threshold exceeded",
    "certificate expired",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _user_id() -> str:
    return f"u-{uuid.uuid4().hex[:12]}"


def _session_id() -> str:
    return f"s-{uuid.uuid4().hex[:12]}"


def generate_pageview(user_id: str | None = None) -> dict[str, Any]:
    return {
        "event_type": "pageview",
        "timestamp": _now_iso(),
        "user_id": user_id or _user_id(),
        "session_id": _session_id(),
        "page": random.choice(PAGES),
        "duration_ms": random.randint(200, 120_000),
    }


def generate_purchase(user_id: str | None = None) -> dict[str, Any]:
    return {
        "event_type": "purchase",
        "timestamp": _now_iso(),
        "user_id": user_id or _user_id(),
        "session_id": _session_id(),
        "item_id": random.choice(ITEMS),
        "amount_usd": round(random.uniform(0.99, 499.99), 2),
        "region": random.choice(REGIONS),
    }


def generate_system_error() -> dict[str, Any]:
    return {
        "event_type": "system_error",
        "timestamp": _now_iso(),
        "service": random.choice(SERVICES),
        "error_code": random.choice([400, 401, 403, 404, 500, 502, 503, 504]),
        "message": random.choice(ERROR_MESSAGES),
        "severity": random.choice(SEVERITIES),
    }


def generate_event() -> tuple[dict[str, Any], str]:
    """Generate a random event and its partition key."""
    roll = random.random()
    if roll < 0.70:
        event = generate_pageview()
        key = event["user_id"]
    elif roll < 0.90:
        event = generate_purchase()
        key = event["user_id"]
    else:
        event = generate_system_error()
        key = event["service"]
    return event, key
