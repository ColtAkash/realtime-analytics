import { create } from "zustand";
import type { TimeseriesPoint, TopNEntry, WsMessage, LivePoint, Metric, Granularity, Duration, Dimension } from "../types";

const MAX_LIVE_POINTS = 60;

interface Filters {
  metric: Metric;
  granularity: Granularity;
  duration: Duration;
  dimension: Dimension;
  eventType: string;
}

interface MetricsState {
  filters: Filters;
  timeseries: TimeseriesPoint[];
  topN: TopNEntry[];
  live: WsMessage | null;
  liveHistory: LivePoint[];
  loading: boolean;
  error: string | null;

  setFilters: (partial: Partial<Filters>) => void;
  setTimeseries: (data: TimeseriesPoint[]) => void;
  setTopN: (data: TopNEntry[]) => void;
  pushLive: (msg: WsMessage) => void;
  setLoading: (v: boolean) => void;
  setError: (e: string | null) => void;
}

function wsToLivePoint(msg: WsMessage): LivePoint {
  const counts = msg.event_type_counts;
  return {
    ts: msg.ts,
    pageview: counts.pageview ?? 0,
    purchase: counts.purchase ?? 0,
    system_error: counts.system_error ?? 0,
    total: Object.values(counts).reduce((a, b) => a + b, 0),
    error_rate: msg.error_rate,
    purchase_usd: msg.purchase_total_usd,
  };
}

export const useMetricsStore = create<MetricsState>((set) => ({
  filters: {
    metric: "event_count",
    granularity: "1h",
    duration: "24h",
    dimension: "region",
    eventType: "",
  },
  timeseries: [],
  topN: [],
  live: null,
  liveHistory: [],
  loading: false,
  error: null,

  setFilters: (partial) =>
    set((s) => ({ filters: { ...s.filters, ...partial } })),
  setTimeseries: (data) => set({ timeseries: data }),
  setTopN: (data) => set({ topN: data }),
  pushLive: (msg) =>
    set((s) => {
      const point = wsToLivePoint(msg);
      const history = [...s.liveHistory, point];
      if (history.length > MAX_LIVE_POINTS) history.shift();
      return { live: msg, liveHistory: history };
    }),
  setLoading: (v) => set({ loading: v }),
  setError: (e) => set({ error: e }),
}));
