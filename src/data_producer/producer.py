from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from threading import Event

from confluent_kafka import KafkaError, Producer

from schemas import generate_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("producer")

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.environ.get("KAFKA_TOPIC", "events")
RATE = int(os.environ.get("EVENT_RATE_PER_SEC", "100"))
LOG_INTERVAL = 10

shutdown = Event()


def on_delivery(err, msg):
    if err is not None:
        log.error("delivery failed: %s", err)


def wait_for_kafka(producer: Producer, timeout: int = 120) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = max(0, deadline - time.monotonic())
        try:
            meta = producer.list_topics(timeout=min(5, remaining))
            if meta.topics:
                log.info("connected to kafka (%d topics)", len(meta.topics))
                return
        except Exception:
            pass
        time.sleep(2)
    log.error("could not connect to kafka within %ds", timeout)
    sys.exit(1)


def run() -> None:
    producer = Producer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "linger.ms": 50,
        "batch.num.messages": 1000,
        "queue.buffering.max.messages": 100_000,
    })

    wait_for_kafka(producer)
    log.info("publishing to topic=%s at %d events/sec", TOPIC, RATE)

    interval = 1.0 / RATE
    sent_count = 0
    sent_bytes = 0
    window_start = time.monotonic()

    while not shutdown.is_set():
        loop_start = time.monotonic()

        event, key = generate_event()
        payload = json.dumps(event).encode()
        producer.produce(
            TOPIC,
            value=payload,
            key=key.encode(),
            callback=on_delivery,
        )
        sent_count += 1
        sent_bytes += len(payload)
        producer.poll(0)

        elapsed_since_window = time.monotonic() - window_start
        if elapsed_since_window >= LOG_INTERVAL:
            eps = sent_count / elapsed_since_window
            bps = sent_bytes / elapsed_since_window
            log.info(
                "throughput: %.1f events/sec, %.1f KB/sec (total: %d events)",
                eps, bps / 1024, sent_count,
            )
            sent_count = 0
            sent_bytes = 0
            window_start = time.monotonic()

        sleep_time = interval - (time.monotonic() - loop_start)
        if sleep_time > 0:
            shutdown.wait(sleep_time)

    remaining = producer.flush(timeout=10)
    if remaining > 0:
        log.warning("%d messages still in queue at shutdown", remaining)
    log.info("producer shut down")


def main() -> None:
    signal.signal(signal.SIGTERM, lambda *_: shutdown.set())
    signal.signal(signal.SIGINT, lambda *_: shutdown.set())
    run()


if __name__ == "__main__":
    main()
