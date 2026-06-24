"""Pure transformation functions for the streaming aggregator.

All functions take and return DataFrames — no I/O, no side effects.
"""
from pyspark.sql import DataFrame
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

WINDOW_5MIN = "5 minutes"
WINDOW_15MIN = "15 minutes"

EVENT_SCHEMA = StructType([
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
])

VALID_EVENT_TYPES = {"pageview", "purchase", "system_error"}


def parse_json(df: DataFrame) -> DataFrame:
    """Parse Kafka value bytes into typed columns."""
    return (
        df
        .selectExpr("CAST(value AS STRING) AS json_str", "timestamp AS kafka_ts")
        .select(
            F.from_json(F.col("json_str"), EVENT_SCHEMA).alias("data"),
            F.col("kafka_ts"),
        )
        .select("data.*", "kafka_ts")
        .withColumn("event_ts", F.to_timestamp("timestamp"))
    )


def split_valid_invalid(df: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Split into valid events and dead-letter rows."""
    valid_condition = (
        F.col("event_type").isin(list(VALID_EVENT_TYPES))
        & F.col("event_ts").isNotNull()
    )
    valid = df.filter(valid_condition)
    invalid = df.filter(~valid_condition)
    return valid, invalid


def normalize_region(df: DataFrame) -> DataFrame:
    """Normalize region column: use service name for system_error, coalesce to 'unknown'."""
    return df.withColumn(
        "region",
        F.when(F.col("event_type") == "system_error", F.col("service"))
        .when(F.col("region").isNotNull(), F.col("region"))
        .otherwise(F.lit("unknown")),
    )


def _aggregate_pageviews(df: DataFrame, window: str) -> DataFrame:
    return (
        df
        .filter(F.col("event_type") == "pageview")
        .groupBy(
            F.window(F.col("event_ts"), window),
            F.col("event_type"),
            F.col("region"),
        )
        .agg(
            F.count("*").alias("event_count"),
            F.avg("duration_ms").alias("avg_duration_ms"),
        )
        .select(
            F.col("event_type"),
            F.col("region"),
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.col("event_count"),
            F.col("avg_duration_ms"),
            F.lit(None).cast(DoubleType()).alias("purchase_total_usd"),
            F.lit(None).cast(DoubleType()).alias("avg_amount_usd"),
            F.lit(0).cast(LongType()).alias("severity_info"),
            F.lit(0).cast(LongType()).alias("severity_warning"),
            F.lit(0).cast(LongType()).alias("severity_error"),
            F.lit(0).cast(LongType()).alias("severity_critical"),
        )
    )


def _aggregate_purchases(df: DataFrame, window: str) -> DataFrame:
    return (
        df
        .filter(F.col("event_type") == "purchase")
        .groupBy(
            F.window(F.col("event_ts"), window),
            F.col("event_type"),
            F.col("region"),
        )
        .agg(
            F.count("*").alias("event_count"),
            F.sum("amount_usd").alias("purchase_total_usd"),
            F.avg("amount_usd").alias("avg_amount_usd"),
        )
        .select(
            F.col("event_type"),
            F.col("region"),
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.col("event_count"),
            F.lit(None).cast(DoubleType()).alias("avg_duration_ms"),
            F.col("purchase_total_usd"),
            F.col("avg_amount_usd"),
            F.lit(0).cast(LongType()).alias("severity_info"),
            F.lit(0).cast(LongType()).alias("severity_warning"),
            F.lit(0).cast(LongType()).alias("severity_error"),
            F.lit(0).cast(LongType()).alias("severity_critical"),
        )
    )


def _aggregate_errors(df: DataFrame, window: str) -> DataFrame:
    return (
        df
        .filter(F.col("event_type") == "system_error")
        .groupBy(
            F.window(F.col("event_ts"), window),
            F.col("event_type"),
            F.col("region"),
        )
        .agg(
            F.count("*").alias("event_count"),
            F.sum(F.when(F.col("severity") == "info", 1).otherwise(0)).alias("severity_info"),
            F.sum(F.when(F.col("severity") == "warning", 1).otherwise(0)).alias("severity_warning"),
            F.sum(F.when(F.col("severity") == "error", 1).otherwise(0)).alias("severity_error"),
            F.sum(F.when(F.col("severity") == "critical", 1).otherwise(0)).alias("severity_critical"),
        )
        .select(
            F.col("event_type"),
            F.col("region"),
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.col("event_count"),
            F.lit(None).cast(DoubleType()).alias("avg_duration_ms"),
            F.lit(None).cast(DoubleType()).alias("purchase_total_usd"),
            F.lit(None).cast(DoubleType()).alias("avg_amount_usd"),
            F.col("severity_info"),
            F.col("severity_warning"),
            F.col("severity_error"),
            F.col("severity_critical"),
        )
    )


def _build_for_window(df: DataFrame, window: str) -> DataFrame:
    return (
        _aggregate_pageviews(df, window)
        .unionByName(_aggregate_purchases(df, window))
        .unionByName(_aggregate_errors(df, window))
        .withColumn("updated_at", F.current_timestamp())
    )


def build_aggregates_5min(df: DataFrame) -> DataFrame:
    enriched = normalize_region(df)
    return _build_for_window(enriched, WINDOW_5MIN)


def build_aggregates_15min(df: DataFrame) -> DataFrame:
    enriched = normalize_region(df)
    return _build_for_window(enriched, WINDOW_15MIN)
