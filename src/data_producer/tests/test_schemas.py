import re
from datetime import datetime, timezone

import pytest

from schemas import (
    PAGES,
    REGIONS,
    SERVICES,
    SEVERITIES,
    generate_event,
    generate_pageview,
    generate_purchase,
    generate_system_error,
)

ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$")


class TestPageView:
    def test_has_required_fields(self):
        event = generate_pageview()
        assert set(event.keys()) == {
            "event_type", "timestamp", "user_id", "session_id", "page", "duration_ms",
        }

    def test_event_type(self):
        assert generate_pageview()["event_type"] == "pageview"

    def test_timestamp_is_iso(self):
        assert ISO_PATTERN.match(generate_pageview()["timestamp"])

    def test_user_id_format(self):
        uid = generate_pageview()["user_id"]
        assert uid.startswith("u-")
        assert len(uid) == 14

    def test_session_id_format(self):
        sid = generate_pageview()["session_id"]
        assert sid.startswith("s-")
        assert len(sid) == 14

    def test_page_is_valid(self):
        assert generate_pageview()["page"] in PAGES

    def test_duration_range(self):
        for _ in range(100):
            d = generate_pageview()["duration_ms"]
            assert 200 <= d <= 120_000

    def test_custom_user_id(self):
        event = generate_pageview(user_id="u-custom12345")
        assert event["user_id"] == "u-custom12345"


class TestPurchase:
    def test_has_required_fields(self):
        event = generate_purchase()
        assert set(event.keys()) == {
            "event_type", "timestamp", "user_id", "session_id",
            "item_id", "amount_usd", "region",
        }

    def test_event_type(self):
        assert generate_purchase()["event_type"] == "purchase"

    def test_item_id_format(self):
        iid = generate_purchase()["item_id"]
        assert iid.startswith("item-")

    def test_amount_range(self):
        for _ in range(100):
            amt = generate_purchase()["amount_usd"]
            assert 0.99 <= amt <= 499.99

    def test_region_is_valid(self):
        assert generate_purchase()["region"] in REGIONS


class TestSystemError:
    def test_has_required_fields(self):
        event = generate_system_error()
        assert set(event.keys()) == {
            "event_type", "timestamp", "service", "error_code", "message", "severity",
        }

    def test_event_type(self):
        assert generate_system_error()["event_type"] == "system_error"

    def test_service_is_valid(self):
        assert generate_system_error()["service"] in SERVICES

    def test_error_code_range(self):
        for _ in range(100):
            code = generate_system_error()["error_code"]
            assert 400 <= code <= 599

    def test_severity_is_valid(self):
        assert generate_system_error()["severity"] in SEVERITIES


class TestGenerateEvent:
    def test_returns_event_and_key(self):
        event, key = generate_event()
        assert isinstance(event, dict)
        assert isinstance(key, str)

    def test_key_matches_event_type(self):
        for _ in range(200):
            event, key = generate_event()
            if event["event_type"] in ("pageview", "purchase"):
                assert key == event["user_id"]
            else:
                assert key == event["service"]

    def test_distribution(self):
        counts = {"pageview": 0, "purchase": 0, "system_error": 0}
        n = 10_000
        for _ in range(n):
            event, _ = generate_event()
            counts[event["event_type"]] += 1
        assert counts["pageview"] / n > 0.60
        assert counts["purchase"] / n > 0.12
        assert counts["system_error"] / n > 0.04

    def test_all_types_appear(self):
        types = set()
        for _ in range(200):
            event, _ = generate_event()
            types.add(event["event_type"])
        assert types == {"pageview", "purchase", "system_error"}
