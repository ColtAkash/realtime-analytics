"""API endpoint tests with mocked DB backends."""
from __future__ import annotations

import sys
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cache
from app import app

client = TestClient(app)

MOCK_TIMESERIES = [
    {"timestamp": "2026-06-24T12:00:00.000Z", "value": 500.0},
    {"timestamp": "2026-06-24T13:00:00.000Z", "value": 600.0},
]

MOCK_TOPN = [
    {"key": "us-east", "value": 1200.0},
    {"key": "eu-west", "value": 800.0},
]

MOCK_STATS = {
    "pageview": {"total_count": 5000, "latest": [{"event_type": "pageview", "event_count": 120}]},
    "purchase": {"total_count": 800, "latest": [{"event_type": "purchase", "event_count": 30}]},
}


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


class TestHealth:
    @patch("db.cassandra.check_health", return_value=True)
    @patch("db.elasticsearch.check_health", return_value=True)
    def test_healthy(self, mock_es, mock_cass):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["cassandra_ok"] is True
        assert data["es_ok"] is True

    @patch("db.cassandra.check_health", return_value=False)
    @patch("db.elasticsearch.check_health", return_value=True)
    def test_degraded(self, mock_es, mock_cass):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["cassandra_ok"] is False


class TestTimeseries:
    @patch("db.elasticsearch.timeseries", return_value=MOCK_TIMESERIES)
    def test_default_params(self, mock_ts):
        resp = client.get("/metrics/timeseries")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["timestamp"] == "2026-06-24T12:00:00.000Z"
        assert data[0]["value"] == 500.0

    @patch("db.elasticsearch.timeseries", return_value=MOCK_TIMESERIES)
    def test_with_filters(self, mock_ts):
        resp = client.get("/metrics/timeseries?metric=avg_duration_ms&granularity=5m&event_type=pageview")
        assert resp.status_code == 200
        mock_ts.assert_called_once()
        call_kwargs = mock_ts.call_args.kwargs
        assert call_kwargs["metric"] == "avg_duration_ms"
        assert call_kwargs["granularity"] == "5m"
        assert call_kwargs["event_type"] == "pageview"

    def test_invalid_metric(self):
        resp = client.get("/metrics/timeseries?metric=bad_metric")
        assert resp.status_code == 400

    def test_invalid_granularity(self):
        resp = client.get("/metrics/timeseries?granularity=2m")
        assert resp.status_code == 400

    @patch("db.elasticsearch.timeseries", return_value=MOCK_TIMESERIES)
    def test_cache_hit(self, mock_ts):
        url = "/metrics/timeseries?start=2026-06-24T00:00:00Z&end=2026-06-24T12:00:00Z"
        resp1 = client.get(url)
        resp2 = client.get(url)
        assert resp1.json() == resp2.json()
        assert mock_ts.call_count == 1


class TestTopN:
    @patch("db.elasticsearch.top_n", return_value=MOCK_TOPN)
    def test_default_params(self, mock_topn):
        resp = client.get("/metrics/topN")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["key"] == "us-east"

    @patch("db.elasticsearch.top_n", return_value=MOCK_TOPN)
    def test_with_params(self, mock_topn):
        resp = client.get("/metrics/topN?metric=purchase_total_usd&dimension=event_type&limit=5&duration=6h")
        assert resp.status_code == 200
        call_kwargs = mock_topn.call_args.kwargs
        assert call_kwargs["metric"] == "purchase_total_usd"
        assert call_kwargs["dimension"] == "event_type"
        assert call_kwargs["limit"] == 5
        assert call_kwargs["duration_minutes"] == 360

    def test_invalid_metric(self):
        resp = client.get("/metrics/topN?metric=invalid")
        assert resp.status_code == 400

    def test_invalid_dimension(self):
        resp = client.get("/metrics/topN?dimension=user_id")
        assert resp.status_code == 400

    def test_invalid_duration(self):
        resp = client.get("/metrics/topN?duration=3h")
        assert resp.status_code == 400

    @patch("db.elasticsearch.top_n", return_value=MOCK_TOPN)
    def test_cache_hit(self, mock_topn):
        client.get("/metrics/topN?duration=24h")
        client.get("/metrics/topN?duration=24h")
        assert mock_topn.call_count == 1


class TestSnapshot:
    @patch("db.elasticsearch.current_stats", return_value=MOCK_STATS)
    def test_returns_stats(self, mock_stats):
        resp = client.get("/metrics/snapshot")
        assert resp.status_code == 200
        data = resp.json()
        assert "pageview" in data
        assert data["pageview"]["total_count"] == 5000

    @patch("db.elasticsearch.current_stats", return_value=MOCK_STATS)
    def test_cache_hit(self, mock_stats):
        client.get("/metrics/snapshot")
        client.get("/metrics/snapshot")
        assert mock_stats.call_count == 1


class TestCORS:
    def test_cors_headers(self):
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in resp.headers


class TestSwagger:
    def test_openapi_json(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "/metrics/timeseries" in data["paths"]
        assert "/metrics/topN" in data["paths"]
        assert "/metrics/snapshot" in data["paths"]
        assert "/health" in data["paths"]
