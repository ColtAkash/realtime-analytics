"""PySpark Structured Streaming job: Kafka → aggregate → Cassandra + Elasticsearch."""
import base64
import logging
import os
from urllib.parse import urlparse

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

ASTRA_BUNDLE_B64 = os.environ.get("ASTRA_SECURE_BUNDLE_B64", "")
ASTRA_CLIENT_ID = os.environ.get("ASTRA_CLIENT_ID", "")
ASTRA_CLIENT_SECRET = os.environ.get("ASTRA_CLIENT_SECRET", "")


def _astra_bundle_path() -> str:
    path = "/tmp/astra-secure-connect.zip"
    with open(path, "wb") as f:
        f.write(base64.b64decode(ASTRA_BUNDLE_B64))
    return path


def create_spark_session() -> SparkSession:
    builder = (
        SparkSession.builder
        .appName("realtime-analytics-aggregator")
        .config("spark.sql.streaming.stateStore.stateSchemaCheck", "false")
    )

    if ASTRA_BUNDLE_B64:
        log.info("configuring Spark for Astra DB")
        builder = (
            builder
            .config("spark.cassandra.connection.config.cloud.path", _astra_bundle_path())
            .config("spark.cassandra.auth.username", ASTRA_CLIENT_ID)
            .config("spark.cassandra.auth.password", ASTRA_CLIENT_SECRET)
        )
    else:
        builder = (
            builder
            .config("spark.cassandra.connection.host", CASSANDRA_HOST)
            .config("spark.cassandra.connection.port", CASSANDRA_PORT)
        )

    return builder.getOrCreate()


def _write_cassandra(df: DataFrame, table: str) -> None:
    (
        df.write
        .format("org.apache.spark.sql.cassandra")
        .options(table=table, keyspace=CASSANDRA_KEYSPACE)
        .mode("append")
        .save()
    )


def _write_elasticsearch(df: DataFrame) -> None:
    parsed = urlparse(ELASTICSEARCH_URL)
    # Strip auth from the node address
    host = parsed.hostname or "elasticsearch"
    port = parsed.port or (443 if parsed.scheme == "https" else 9200)
    es_nodes = f"{host}:{port}"

    opts = {
        "es.resource": ES_INDEX_ALIAS,
        "es.nodes": es_nodes,
        "es.nodes.wan.only": "true",
        "es.write.operation": "index",
        "es.mapping.date.rich": "false",
        "es.net.ssl": "true" if parsed.scheme == "https" else "false",
        "es.net.ssl.cert.allow.self.signed": "true",
    }

    if parsed.username:
        opts["es.net.http.auth.user"] = parsed.username
        opts["es.net.http.auth.pass"] = parsed.password or ""

    (
        df.write
        .format("org.elasticsearch.spark.sql")
        .options(**opts)
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
