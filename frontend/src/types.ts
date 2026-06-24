export interface TimeseriesPoint {
  timestamp: string;
  value: number | null;
}

export interface TopNEntry {
  key: string;
  value: number | null;
}

export interface SnapshotData {
  [eventType: string]: {
    total_count: number;
    latest: Record<string, unknown>[];
  };
}

export interface WsMessage {
  ts: string;
  event_type_counts: Record<string, number>;
  purchase_total_usd: number;
  error_rate: number;
}

export interface LivePoint {
  ts: string;
  pageview: number;
  purchase: number;
  system_error: number;
  total: number;
  error_rate: number;
  purchase_usd: number;
}

export interface HealthStatus {
  status: string;
  cassandra_ok: boolean;
  es_ok: boolean;
}

export type Granularity = "5m" | "15m" | "1h" | "1d";
export type Duration = "5m" | "15m" | "1h" | "6h" | "24h";
export type Metric = "event_count" | "avg_duration_ms" | "purchase_total_usd" | "avg_amount_usd";
export type Dimension = "event_type" | "region";
