-- =============================================================================
-- Cassandra Schema — realtime-analytics
-- =============================================================================
--
-- PARTITION KEY RATIONALE
--
-- metrics_5min / metrics_15min:
--   PK: (event_type, region, window_start)
--   - event_type (3 values) × region (4–5 values) × window_start (one per
--     5/15-min window) yields high cardinality, distributing data evenly
--     across nodes and avoiding hot partitions.
--   - Dashboard queries always filter by event_type + region + time range,
--     so each query hits exactly one partition — no scatter-gather.
--   - Hot-partition risk: a single (event_type, region) pair produces one
--     partition per window. At 100 events/sec this is ~30k events per 5-min
--     window, well under the ~100k cell per-partition guideline.
--   - Mitigation if traffic scales 10x: add a bucketing column
--     (e.g., bucket = hash(user_id) % 4) to split partitions further.
--
-- user_sessions:
--   PK: (user_id), clustering: session_id
--   - One partition per user, rows ordered by session.
--   - Dashboard "user drill-down" queries fetch all sessions for a user
--     in a single read.
--   - Hot-partition risk: power users with thousands of sessions. Mitigated
--     by 90-day TTL which caps partition size.
--
-- TTL: 90 days (7,776,000 seconds) on all tables. Old data is automatically
-- tombstoned and compacted away without manual cleanup.
--
-- No secondary indexes — all queries are by partition key only.
-- =============================================================================

CREATE KEYSPACE IF NOT EXISTS analytics
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE analytics;

-- 5-minute tumbling window aggregates
CREATE TABLE IF NOT EXISTS metrics_5min (
    event_type         text,
    region             text,
    window_start       timestamp,
    window_end         timestamp,
    event_count        bigint,
    avg_duration_ms    double,
    purchase_total_usd double,
    avg_amount_usd     double,
    severity_info      bigint,
    severity_warning   bigint,
    severity_error     bigint,
    severity_critical  bigint,
    updated_at         timestamp,
    PRIMARY KEY ((event_type, region, window_start))
) WITH default_time_to_live = 7776000;

-- 15-minute tumbling window aggregates
CREATE TABLE IF NOT EXISTS metrics_15min (
    event_type         text,
    region             text,
    window_start       timestamp,
    window_end         timestamp,
    event_count        bigint,
    avg_duration_ms    double,
    purchase_total_usd double,
    avg_amount_usd     double,
    severity_info      bigint,
    severity_warning   bigint,
    severity_error     bigint,
    severity_critical  bigint,
    updated_at         timestamp,
    PRIMARY KEY ((event_type, region, window_start))
) WITH default_time_to_live = 7776000;

-- Per-user session log for drill-down queries
CREATE TABLE IF NOT EXISTS user_sessions (
    user_id       text,
    session_id    text,
    started_at    timestamp,
    ended_at      timestamp,
    page_count    int,
    purchase_count int,
    total_duration_ms bigint,
    total_spent_usd double,
    last_page     text,
    PRIMARY KEY ((user_id), session_id)
) WITH CLUSTERING ORDER BY (session_id ASC)
   AND default_time_to_live = 7776000;
