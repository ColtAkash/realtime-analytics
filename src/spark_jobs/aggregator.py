"""PySpark Structured Streaming job: Kafka → aggregate → Cassandra."""
import json
import logging
import os

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

from transforms import (
    EVENT_SCHEMA,
    parse_json,
    split_valid_invalid,
    build_aggregates_5min,
    build_aggregates_15min,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("aggregator")

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "events")
DLQ_TOPIC = os.environ.get("KAFKA_DLQ_TOPIC", "events_dlq")
CASSANDRA_HOST = os.environ.get("CASSANDRA_HOST", "cassandra")
CASSANDRA_PORT = os.environ.get("CASSANDRA_PORT", "9042")
CASSANDRA_KEYSPACE = os.environ.get("CASSANDRA_KEYSPACE", "analytics")
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200")
ES_INDEX_ALIAS = os.environ.get("ES_INDEX_ALIAS", "metrics-5m")
CHECKPOINT_DIR = os.environ.get("CHECKPOINT_DIR", "/tmp/spark-checkpoint")
TRIGGER_INTERVAL = os.environ.get("TRIGGER_INTERVAL", "30 seconds")


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("realtime-analytics-aggregator")
        .config("spark.cassandra.connection.host", CASSANDRA_HOST)
        .config("spark.cassandra.connection.port", CASSANDRA_PORT)
        .config("spark.sql.streaming.stateStore.stateSchemaCheck", "false")
        .getOrCreate()
    )


def _write_cassandra(df: DataFrame, table: str) -> None:
    (
        df.write
        .format("org.apache.spark.sql.cassandra")
        .options(table=table, keyspace=CASSANDRA_KEYSPACE)
        .mode("append")
        .save()
    )


def _write_elasticsearch(df: DataFrame) -> None:
    (
        df.write
        .format("org.elasticsearch.spark.sql")
        .option("es.resource", ES_INDEX_ALIAS)
        .option("es.nodes", ELASTICSEARCH_URL.replace("http://", ""))
        .option("es.nodes.wan.only", "true")
        .option("es.write.operation", "index")
        .option("es.mapping.date.rich", "false")
        .mode("append")
        .save()
    )


def write_5min(batch_df: DataFrame, batch_id: int) -> None:
    if batch_df.isEmpty():
        return
    count = batch_df.count()
    _write_cassandra(batch_df, "metrics_5min")
    try:
        _write_elasticsearch(batch_df)
        log.info("batch %d: wrote %d rows to metrics_5min + elasticsearch", batch_id, count)
    except Exception as e:
        log.warning("batch %d: cassandra OK, elasticsearch failed: %s", batch_id, e)


def write_15min(batch_df: DataFrame, batch_id: int) -> None:
    if batch_df.isEmpty():
        return
    count = batch_df.count()
    _write_cassandra(batch_df, "metrics_15min")
    log.info("batch %d: wrote %d rows to metrics_15min", batch_id, count)


def write_dlq(batch_df: DataFrame, batch_id: int) -> None:
    if batch_df.isEmpty():
        return
    count = batch_df.count()
    (
        batch_df
        .select(
            F.lit(None).cast("string").alias("key"),
            F.to_json(F.struct("*")).alias("value"),
        )
        .write
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("topic", DLQ_TOPIC)
        .save()
    )
    log.info("batch %d: sent %d malformed events to DLQ", batch_id, count)


def main() -> None:
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    log.info("reading from kafka topic=%s at %s", KAFKA_TOPIC, KAFKA_BOOTSTRAP)

    raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    parsed = parse_json(raw)
    valid, invalid = split_valid_invalid(parsed)

    # 5-min aggregation stream → Cassandra
    agg_5min_query = (
        build_aggregates_5min(valid)
        .writeStream
        .outputMode("update")
        .foreachBatch(write_5min)
        .option("checkpointLocation", f"{CHECKPOINT_DIR}/aggregates_5min")
        .trigger(processingTime=TRIGGER_INTERVAL)
        .queryName("aggregates_5min_to_cassandra")
        .start()
    )

    # 15-min aggregation stream → Cassandra
    agg_15min_query = (
        build_aggregates_15min(valid)
        .writeStream
        .outputMode("update")
        .foreachBatch(write_15min)
        .option("checkpointLocation", f"{CHECKPOINT_DIR}/aggregates_15min")
        .trigger(processingTime=TRIGGER_INTERVAL)
        .queryName("aggregates_15min_to_cassandra")
        .start()
    )

    # Dead-letter stream → Kafka DLQ topic
    dlq_query = (
        invalid
        .writeStream
        .outputMode("append")
        .foreachBatch(write_dlq)
        .option("checkpointLocation", f"{CHECKPOINT_DIR}/dlq")
        .trigger(processingTime=TRIGGER_INTERVAL)
        .queryName("dead_letter_queue")
        .start()
    )

    log.info("streaming queries started, awaiting termination")
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
