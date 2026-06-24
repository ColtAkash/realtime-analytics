"""WebSocket endpoint tests."""
from __future__ import annotations

import asyncio
import sys
import os
import time
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MOCK_SNAPSHOT = {
    "ts": "2026-06-24T12:00:00.000Z",
    "event_type_counts": {"pageview": 500, "purchase": 80, "system_error": 20},
    "purchase_total_usd": 12345.67,
    "error_rate": 3.33,
}


@pytest.fixture
def mock_es():
    with patch("broadcaster.es_db") as mock:
        mock.current_stats.return_value = {
            "pageview": {"total_count": 500, "latest": []},
            "purchase": {"total_count": 80, "latest": [{"purchase_total_usd": 12345.67}]},
            "system_error": {"total_count": 20, "latest": []},
        }
        yield mock


@pytest.fixture
def test_client(mock_es):
    from app import app
    return TestClient(app)


class TestWebSocketConnection:
    def test_connect_receives_snapshot(self, test_client, mock_es):
        with test_client.websocket_connect("/ws/metrics") as ws:
            data = ws.receive_json()
            assert "ts" in data
            assert "event_type_counts" in data
            assert "purchase_total_usd" in data
            assert "error_rate" in data

    def test_snapshot_format(self, test_client, mock_es):
        with test_client.websocket_connect("/ws/metrics") as ws:
            data = ws.receive_json()
            counts = data["event_type_counts"]
            assert counts["pageview"] == 500
            assert counts["purchase"] == 80
            assert counts["system_error"] == 20
            assert data["purchase_total_usd"] == 12345.67
            assert isinstance(data["error_rate"], float)

    def test_pong_accepted(self, test_client, mock_es):
        with test_client.websocket_connect("/ws/metrics") as ws:
            ws.receive_json()
            ws.send_json({"type": "pong"})

    def test_disconnect_cleanup(self, test_client, mock_es):
        from websocket import manager
        initial = manager.count
        with test_client.websocket_connect("/ws/metrics") as ws:
            ws.receive_json()
            assert manager.count == initial + 1
        assert manager.count == initial


class TestConnectionManager:
    def test_multiple_connections(self, test_client, mock_es):
        from websocket import manager
        initial = manager.count
        with test_client.websocket_connect("/ws/metrics") as ws1:
            ws1.receive_json()
            with test_client.websocket_connect("/ws/metrics") as ws2:
                ws2.receive_json()
                assert manager.count == initial + 2
            assert manager.count == initial + 1
        assert manager.count == initial

    def test_connect_disconnect_cycles(self, test_client, mock_es):
        from websocket import manager
        for i in range(20):
            with test_client.websocket_connect("/ws/metrics") as ws:
                ws.receive_json()
        assert manager.count == 0


class TestBroadcasterSnapshot:
    def test_build_snapshot_returns_correct_format(self, mock_es):
        from broadcaster import _build_snapshot
        snap = _build_snapshot()
        assert "ts" in snap
        assert "event_type_counts" in snap
        assert "purchase_total_usd" in snap
        assert "error_rate" in snap

    def test_error_rate_calculation(self, mock_es):
        from broadcaster import _build_snapshot
        snap = _build_snapshot()
        total = 500 + 80 + 20
        expected_rate = round(20 / total * 100, 2)
        assert snap["error_rate"] == expected_rate

    def test_empty_es_returns_empty_snapshot(self):
        with patch("broadcaster.es_db") as mock:
            mock.current_stats.return_value = {}
            from broadcaster import _build_snapshot
            snap = _build_snapshot()
            assert snap["event_type_counts"] == {}
            assert snap["purchase_total_usd"] == 0.0
            assert snap["error_rate"] == 0.0

    def test_es_failure_returns_empty_snapshot(self):
        with patch("broadcaster.es_db") as mock:
            mock.current_stats.side_effect = Exception("connection refused")
            from broadcaster import _build_snapshot
            snap = _build_snapshot()
            assert snap["event_type_counts"] == {}
