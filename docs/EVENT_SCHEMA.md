# Event Schema

All events are JSON-serialized and published to the Kafka topic `events`.

## Common Fields

Every event includes:

| Field        | Type   | Description                        |
|--------------|--------|------------------------------------|
| `event_type` | string | One of: `pageview`, `purchase`, `system_error` |
| `timestamp`  | string | ISO 8601 UTC (e.g. `2026-06-24T12:00:00Z`)    |

## Event Types

### PageView

User browsing activity. Partition key: `user_id`.

```json
{
  "event_type": "pageview",
  "timestamp": "2026-06-24T12:00:00.000Z",
  "user_id": "u-abc123",
  "session_id": "s-def456",
  "page": "/products/widget",
  "duration_ms": 4200
}
```

| Field         | Type   | Constraints          |
|---------------|--------|----------------------|
| `user_id`     | string | `u-` prefix + UUID   |
| `session_id`  | string | `s-` prefix + UUID   |
| `page`        | string | URL path             |
| `duration_ms` | int    | 0–300000 (0–5 min)   |

### Purchase

E-commerce transaction. Partition key: `user_id`.

```json
{
  "event_type": "purchase",
  "timestamp": "2026-06-24T12:01:00.000Z",
  "user_id": "u-abc123",
  "session_id": "s-def456",
  "item_id": "item-789",
  "amount_usd": 29.99,
  "region": "us-east"
}
```

| Field        | Type   | Constraints                                         |
|--------------|--------|-----------------------------------------------------|
| `user_id`    | string | `u-` prefix + UUID                                  |
| `session_id` | string | `s-` prefix + UUID                                  |
| `item_id`    | string | `item-` prefix + numeric ID                         |
| `amount_usd` | float  | 0.01–9999.99                                        |
| `region`     | string | One of: `us-east`, `us-west`, `eu-west`, `ap-south` |

### SystemError

Infrastructure/service error. Partition key: `service`.

```json
{
  "event_type": "system_error",
  "timestamp": "2026-06-24T12:02:00.000Z",
  "service": "api-gateway",
  "error_code": 503,
  "message": "upstream timeout after 30s",
  "severity": "warning"
}
```

| Field        | Type   | Constraints                                                     |
|--------------|--------|-----------------------------------------------------------------|
| `service`    | string | One of: `api-gateway`, `payment-svc`, `auth-svc`, `search-svc` |
| `error_code` | int    | HTTP status code (400–599)                                      |
| `message`    | string | Free-text error description                                     |
| `severity`   | string | One of: `info`, `warning`, `error`, `critical`                  |

## Partition Key Rationale

- **PageView / Purchase** use `user_id` so all events for a given user land on the
  same partition, preserving per-user ordering for session reconstruction and
  funnel analysis downstream.
- **SystemError** uses `service` so errors from the same service are co-located,
  enabling per-service aggregation in the Spark streaming job without cross-partition
  shuffles.

## Distribution

The producer generates events with the following default distribution:
- 70% PageView
- 20% Purchase
- 10% SystemError

This mirrors a realistic analytics workload where browsing far exceeds purchasing,
and system errors are relatively rare.
