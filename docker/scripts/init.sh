#!/usr/bin/env bash
set -euo pipefail

KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-kafka:29092}"
CASSANDRA_HOST="${CASSANDRA_HOST:-cassandra}"
CASSANDRA_PORT="${CASSANDRA_PORT:-9042}"
ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://elasticsearch:9200}"
KAFKA_TOPIC="${KAFKA_TOPIC:-analytics.events}"
CASSANDRA_KEYSPACE="${CASSANDRA_KEYSPACE:-analytics}"
ELASTICSEARCH_INDEX="${ELASTICSEARCH_INDEX:-events}"

echo "=== Creating Kafka topic: ${KAFKA_TOPIC} ==="

python3 - <<PYEOF
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import sys, time

for attempt in range(30):
    try:
        admin = KafkaAdminClient(bootstrap_servers="${KAFKA_BOOTSTRAP_SERVERS}")
        break
    except Exception as e:
        print(f"Kafka not ready (attempt {attempt+1}/30): {e}")
        time.sleep(2)
else:
    print("ERROR: Could not connect to Kafka")
    sys.exit(1)

try:
    admin.create_topics([
        NewTopic(name="${KAFKA_TOPIC}", num_partitions=3, replication_factor=1)
    ])
    print(f"Created topic: ${KAFKA_TOPIC}")
except TopicAlreadyExistsError:
    print(f"Topic already exists: ${KAFKA_TOPIC}")

admin.close()
PYEOF

echo "=== Creating Cassandra keyspace + tables ==="

python3 - <<PYEOF
from cassandra.cluster import Cluster
import sys, time

for attempt in range(30):
    try:
        cluster = Cluster(["${CASSANDRA_HOST}"], port=${CASSANDRA_PORT})
        session = cluster.connect()
        break
    except Exception as e:
        print(f"Cassandra not ready (attempt {attempt+1}/30): {e}")
        time.sleep(2)
else:
    print("ERROR: Could not connect to Cassandra")
    sys.exit(1)

session.execute("""
    CREATE KEYSPACE IF NOT EXISTS ${CASSANDRA_KEYSPACE}
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
""")
print(f"Keyspace ready: ${CASSANDRA_KEYSPACE}")

session.set_keyspace("${CASSANDRA_KEYSPACE}")

METRICS_DDL = """
CREATE TABLE IF NOT EXISTS {table} (
    event_type text, region text, window_start timestamp, window_end timestamp,
    event_count bigint, avg_duration_ms double, purchase_total_usd double,
    avg_amount_usd double, severity_info bigint, severity_warning bigint,
    severity_error bigint, severity_critical bigint, updated_at timestamp,
    PRIMARY KEY ((event_type, region, window_start))
) WITH default_time_to_live = 7776000
"""

for table in ("metrics_5min", "metrics_15min"):
    session.execute(METRICS_DDL.format(table=table))
    print(f"Table ready: {table}")

session.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        user_id text, session_id text, started_at timestamp, ended_at timestamp,
        page_count int, purchase_count int, total_duration_ms bigint,
        total_spent_usd double, last_page text,
        PRIMARY KEY ((user_id), session_id)
    ) WITH CLUSTERING ORDER BY (session_id ASC)
       AND default_time_to_live = 7776000
""")
print("Table ready: user_sessions")

cluster.shutdown()
PYEOF

echo "=== Setting up Elasticsearch ILM + index template ==="

# ILM policy: rollover at 1GB or 1 day, delete after 90 days
curl -sf -X PUT "${ELASTICSEARCH_URL}/_ilm/policy/metrics-ilm" \
    -H 'Content-Type: application/json' \
    -d '{"policy":{"phases":{"hot":{"min_age":"0ms","actions":{"rollover":{"max_primary_shard_size":"1gb","max_age":"1d"}}},"delete":{"min_age":"90d","actions":{"delete":{}}}}}}'
echo ""

# Delete conflicting built-in metrics template if present
curl -sf -X DELETE "${ELASTICSEARCH_URL}/_index_template/metrics" || true

# Index template with priority > built-in (100)
curl -sf -X PUT "${ELASTICSEARCH_URL}/_index_template/metrics-5m-template" \
    -H 'Content-Type: application/json' \
    -d '{
        "index_patterns": ["metrics-5m-*"],
        "priority": 200,
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index.lifecycle.name": "metrics-ilm",
                "index.lifecycle.rollover_alias": "metrics-5m"
            },
            "mappings": {
                "properties": {
                    "event_type":         {"type": "keyword"},
                    "region":             {"type": "keyword"},
                    "window_start":       {"type": "date"},
                    "window_end":         {"type": "date"},
                    "event_count":        {"type": "integer"},
                    "avg_duration_ms":    {"type": "float"},
                    "purchase_total_usd": {"type": "float"},
                    "avg_amount_usd":     {"type": "float"},
                    "severity_info":      {"type": "integer"},
                    "severity_warning":   {"type": "integer"},
                    "severity_error":     {"type": "integer"},
                    "severity_critical":  {"type": "integer"},
                    "updated_at":         {"type": "date"}
                }
            }
        }
    }'
echo ""

# Bootstrap first rollover index with write alias
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${ELASTICSEARCH_URL}/metrics-5m-000001")
if [ "$STATUS" = "200" ]; then
    echo "Index metrics-5m-000001 already exists"
else
    curl -sf -X PUT "${ELASTICSEARCH_URL}/metrics-5m-000001" \
        -H 'Content-Type: application/json' \
        -d '{"aliases":{"metrics-5m":{"is_write_index":true}}}'
    echo ""
    echo "Created bootstrap index: metrics-5m-000001"
fi

echo "=== Init complete ==="
