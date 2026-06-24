"""Unit tests for transforms.py using static DataFrames (no Kafka needed)."""
import pytest
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from transforms import (
    split_valid_invalid,
    normalize_region,
    _aggregate_pageviews,
    _aggregate_purchases,
    _aggregate_errors,
    build_aggregates_5min,
    build_aggregates_15min,
    VALID_EVENT_TYPES,
    WINDOW_5MIN,
)


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder
        .master("local[1]")
        .appName("test-transforms")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "localhost")
        .getOrCreate()
    )
    yield session
    session.stop()


def _make_event_df(spark, events):
    schema = StructType([
        StructField("event_type", StringType()),
        StructField("timestamp", StringType()),
        StructField("user_id", StringType()),
        StructField("session_id", StringType()),
        StructField("page", StringType()),
        StructField("duration_ms", IntegerType()),
        StructField("item_id", StringType()),
        StructField("amount_usd", DoubleType()),
        StructField("region", StringType()),
        StructField("service", StringType()),
        StructField("error_code", IntegerType()),
        StructField("message", StringType()),
        StructField("severity", StringType()),
        StructField("kafka_ts", TimestampType()),
        StructField("event_ts", TimestampType()),
    ])
    return spark.createDataFrame(events, schema)


WINDOW_BASE = datetime(2026, 6, 24, 12, 0, 0)
WINDOW_MID = datetime(2026, 6, 24, 12, 2, 0)
WINDOW_LATE = datetime(2026, 6, 24, 12, 4, 0)


def _pageview(ts=WINDOW_BASE, duration_ms=1000, region=None):
    return (
        "pageview", ts.isoformat(), "u-1", "s-1", "/home", duration_ms,
        None, None, region, None, None, None, None, ts, ts,
    )


def _purchase(ts=WINDOW_BASE, amount=100.0, region="us-east"):
    return (
        "purchase", ts.isoformat(), "u-2", "s-2", None, None,
        "item-1", float(amount), region, None, None, None, None, ts, ts,
    )


def _error(ts=WINDOW_BASE, severity="error", service="api-gateway"):
    return (
        "system_error", ts.isoformat(), None, None, None, None,
        None, None, None, service, 500, "fail", severity, ts, ts,
    )


class TestSplitValidInvalid:
    def test_valid_events_pass_through(self, spark):
        df = _make_event_df(spark, [_pageview(), _purchase(), _error()])
        valid, invalid = split_valid_invalid(df)
        assert valid.count() == 3
        assert invalid.count() == 0

    def test_unknown_event_type_goes_to_invalid(self, spark):
        bad = (
            "unknown_type", WINDOW_BASE.isoformat(), "u-1", "s-1", None, None,
            None, None, None, None, None, None, None, WINDOW_BASE, WINDOW_BASE,
        )
        df = _make_event_df(spark, [_pageview(), bad])
        valid, invalid = split_valid_invalid(df)
        assert valid.count() == 1
        assert invalid.count() == 1

    def test_null_timestamp_goes_to_invalid(self, spark):
        bad = (
            "pageview", None, "u-1", "s-1", "/home", 1000,
            None, None, None, None, None, None, None, None, None,
        )
        df = _make_event_df(spark, [bad])
        valid, invalid = split_valid_invalid(df)
        assert valid.count() == 0
        assert invalid.count() == 1


class TestNormalizeRegion:
    def test_pageview_uses_region_or_unknown(self, spark):
        df = _make_event_df(spark, [
            _pageview(region="us-east"),
            _pageview(region=None),
        ])
        result = normalize_region(df).select("region").collect()
        keys = [r.region for r in result]
        assert keys == ["us-east", "unknown"]

    def test_purchase_uses_region(self, spark):
        df = _make_event_df(spark, [_purchase(region="eu-west")])
        result = normalize_region(df).select("region").collect()
        assert result[0].region == "eu-west"

    def test_system_error_uses_service(self, spark):
        df = _make_event_df(spark, [_error(service="auth-svc")])
        result = normalize_region(df).select("region").collect()
        assert result[0].region == "auth-svc"


class TestAggregatePageviews:
    def test_count_and_avg_duration(self, spark):
        events = [
            _pageview(ts=WINDOW_BASE, duration_ms=1000),
            _pageview(ts=WINDOW_MID, duration_ms=3000),
            _pageview(ts=WINDOW_LATE, duration_ms=5000),
        ]
        df = normalize_region(_make_event_df(spark, events))
        result = _aggregate_pageviews(df, WINDOW_5MIN).collect()
        assert len(result) == 1
        row = result[0]
        assert row.event_count == 3
        assert abs(row.avg_duration_ms - 3000.0) < 0.01

    def test_ignores_non_pageview(self, spark):
        df = normalize_region(_make_event_df(spark, [_purchase(), _error()]))
        result = _aggregate_pageviews(df, WINDOW_5MIN).collect()
        assert len(result) == 0

    def test_null_monetary_fields(self, spark):
        df = normalize_region(_make_event_df(spark, [_pageview()]))
        row = _aggregate_pageviews(df, WINDOW_5MIN).collect()[0]
        assert row.purchase_total_usd is None
        assert row.avg_amount_usd is None


class TestAggregatePurchases:
    def test_count_sum_avg(self, spark):
        events = [
            _purchase(ts=WINDOW_BASE, amount=100.0),
            _purchase(ts=WINDOW_MID, amount=200.0),
        ]
        df = normalize_region(_make_event_df(spark, events))
        result = _aggregate_purchases(df, WINDOW_5MIN).collect()
        assert len(result) == 1
        row = result[0]
        assert row.event_count == 2
        assert abs(row.purchase_total_usd - 300.0) < 0.01
        assert abs(row.avg_amount_usd - 150.0) < 0.01

    def test_groups_by_region(self, spark):
        events = [
            _purchase(ts=WINDOW_BASE, amount=50.0, region="us-east"),
            _purchase(ts=WINDOW_MID, amount=80.0, region="eu-west"),
        ]
        df = normalize_region(_make_event_df(spark, events))
        result = _aggregate_purchases(df, WINDOW_5MIN).collect()
        assert len(result) == 2
        regions = {r.region for r in result}
        assert regions == {"us-east", "eu-west"}

    def test_ignores_non_purchase(self, spark):
        df = normalize_region(_make_event_df(spark, [_pageview(), _error()]))
        result = _aggregate_purchases(df, WINDOW_5MIN).collect()
        assert len(result) == 0


class TestAggregateErrors:
    def test_severity_breakdown(self, spark):
        events = [
            _error(ts=WINDOW_BASE, severity="info"),
            _error(ts=WINDOW_MID, severity="error"),
            _error(ts=WINDOW_MID, severity="error"),
            _error(ts=WINDOW_LATE, severity="critical"),
        ]
        df = normalize_region(_make_event_df(spark, events))
        result = _aggregate_errors(df, WINDOW_5MIN).collect()
        assert len(result) == 1
        row = result[0]
        assert row.event_count == 4
        assert row.severity_info == 1
        assert row.severity_warning == 0
        assert row.severity_error == 2
        assert row.severity_critical == 1

    def test_groups_by_service(self, spark):
        events = [
            _error(ts=WINDOW_BASE, service="api-gateway"),
            _error(ts=WINDOW_MID, service="auth-svc"),
        ]
        df = normalize_region(_make_event_df(spark, events))
        result = _aggregate_errors(df, WINDOW_5MIN).collect()
        assert len(result) == 2


class TestBuildAggregates:
    def test_unions_all_types(self, spark):
        events = [_pageview(), _purchase(), _error()]
        df = _make_event_df(spark, events)
        result = build_aggregates_5min(df)
        types = {r.event_type for r in result.collect()}
        assert types == {"pageview", "purchase", "system_error"}

    def test_has_updated_at(self, spark):
        df = _make_event_df(spark, [_pageview()])
        result = build_aggregates_5min(df).collect()
        assert result[0].updated_at is not None

    def test_output_columns_match_cassandra(self, spark):
        expected_cols = {
            "event_type", "window_start", "window_end", "region",
            "event_count", "avg_duration_ms", "purchase_total_usd",
            "avg_amount_usd", "severity_info", "severity_warning",
            "severity_error", "severity_critical", "updated_at",
        }
        df = _make_event_df(spark, [_pageview()])
        result = build_aggregates_5min(df)
        assert set(result.columns) == expected_cols

    def test_15min_produces_output(self, spark):
        events = [_pageview(), _purchase(), _error()]
        df = _make_event_df(spark, events)
        result = build_aggregates_15min(df)
        assert result.count() == 3

    def test_empty_input_produces_empty_output(self, spark):
        df = _make_event_df(spark, [])
        result = build_aggregates_5min(df)
        assert result.count() == 0
