import type { TimeseriesPoint, TopNEntry, WsMessage, HealthStatus } from "../types";

function hoursAgo(h: number): string {
  return new Date(Date.now() - h * 3600_000).toISOString();
}

export const mockTimeseries: TimeseriesPoint[] = Array.from({ length: 24 }, (_, i) => ({
  timestamp: hoursAgo(24 - i),
  value: Math.round(800 + Math.random() * 400),
}));

export const mockTopN: TopNEntry[] = [
  { key: "us-east", value: 12400 },
  { key: "eu-west", value: 9800 },
  { key: "ap-south", value: 7200 },
  { key: "us-west", value: 6500 },
];

export const mockWsMessage: WsMessage = {
  ts: new Date().toISOString(),
  event_type_counts: { pageview: 6200, purchase: 1400, system_error: 350 },
  purchase_total_usd: 48250.0,
  error_rate: 4.4,
};

export const mockHealth: HealthStatus = {
  status: "ok",
  cassandra_ok: true,
  es_ok: true,
};
