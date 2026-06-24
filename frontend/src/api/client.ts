import type { TimeseriesPoint, TopNEntry, SnapshotData, HealthStatus, Granularity, Duration, Metric, Dimension } from "../types";
import { mockTimeseries, mockTopN, mockHealth } from "./mock";

const BASE = import.meta.env.VITE_API_BASE_URL || "";
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

async function get<T>(path: string, fallback: T): Promise<T> {
  if (USE_MOCK) return fallback;
  try {
    const res = await fetch(`${BASE}${path}`);
    if (!res.ok) throw new Error(`${res.status}`);
    return await res.json();
  } catch {
    return fallback;
  }
}

export async function fetchHealth(): Promise<HealthStatus> {
  return get("/health", mockHealth);
}

export async function fetchTimeseries(params: {
  metric?: Metric;
  start?: string;
  end?: string;
  granularity?: Granularity;
  event_type?: string;
  region?: string;
}): Promise<TimeseriesPoint[]> {
  const qs = new URLSearchParams();
  if (params.metric) qs.set("metric", params.metric);
  if (params.start) qs.set("start", params.start);
  if (params.end) qs.set("end", params.end);
  if (params.granularity) qs.set("granularity", params.granularity);
  if (params.event_type) qs.set("event_type", params.event_type);
  if (params.region) qs.set("region", params.region);
  return get(`/metrics/timeseries?${qs}`, mockTimeseries);
}

export async function fetchTopN(params: {
  metric?: Metric;
  dimension?: Dimension;
  limit?: number;
  duration?: Duration;
}): Promise<TopNEntry[]> {
  const qs = new URLSearchParams();
  if (params.metric) qs.set("metric", params.metric);
  if (params.dimension) qs.set("dimension", params.dimension);
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.duration) qs.set("duration", params.duration);
  return get(`/metrics/topN?${qs}`, mockTopN);
}

export async function fetchSnapshot(): Promise<SnapshotData> {
  return get("/metrics/snapshot", {});
}
