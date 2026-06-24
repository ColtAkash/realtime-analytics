import { useEffect } from "react";
import { useMetricsStore } from "../store/metricsSlice";
import { fetchTimeseries, fetchTopN } from "../api/client";

export function useMetrics() {
  const { filters, setTimeseries, setTopN, setLoading, setError } = useMetricsStore();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const end = new Date().toISOString();
    const durationMs: Record<string, number> = {
      "5m": 5 * 60_000, "15m": 15 * 60_000, "1h": 3600_000,
      "6h": 6 * 3600_000, "24h": 24 * 3600_000,
    };
    const start = new Date(Date.now() - (durationMs[filters.duration] || 24 * 3600_000)).toISOString();

    Promise.all([
      fetchTimeseries({
        metric: filters.metric,
        start,
        end,
        granularity: filters.granularity,
        event_type: filters.eventType || undefined,
      }),
      fetchTopN({
        metric: filters.metric,
        dimension: filters.dimension,
        limit: 10,
        duration: filters.duration,
      }),
    ])
      .then(([ts, top]) => {
        if (cancelled) return;
        setTimeseries(ts);
        setTopN(top);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [filters.metric, filters.granularity, filters.duration, filters.dimension, filters.eventType]);
}
