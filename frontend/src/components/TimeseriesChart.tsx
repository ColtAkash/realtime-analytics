import { memo, useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useMetricsStore } from "../store/metricsSlice";
import { SkeletonChart } from "./Skeleton";

const METRIC_LABELS: Record<string, string> = {
  event_count: "Event Count",
  avg_duration_ms: "Avg Duration (ms)",
  purchase_total_usd: "Purchase Total ($)",
  avg_amount_usd: "Avg Amount ($)",
};

function fmt(ts: string) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function TimeseriesChartInner() {
  const liveHistory = useMetricsStore((s) => s.liveHistory);
  const timeseries = useMetricsStore((s) => s.timeseries);
  const metric = useMetricsStore((s) => s.filters.metric);
  const loading = useMetricsStore((s) => s.loading);
  const [mode, setMode] = useState<"historical" | "live">("historical");

  const showHistorical = mode === "historical" && timeseries.length > 0;

  if (loading && timeseries.length === 0 && liveHistory.length === 0) return <SkeletonChart />;

  const historicalData = timeseries.map((p) => ({
    time: fmt(p.timestamp),
    value: p.value ?? 0,
  }));

  const liveData = liveHistory.map((p) => ({
    time: new Date(p.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    pageview: p.pageview,
    purchase: p.purchase,
    system_error: p.system_error,
  }));

  const isEmpty = showHistorical ? historicalData.length === 0 : liveData.length === 0;

  return (
    <div className="bg-card-light dark:bg-card-dark rounded-xl border border-slate-200 dark:border-slate-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400">
          {showHistorical ? METRIC_LABELS[metric] ?? metric : `Live Events (${liveHistory.length} pts)`}
        </h3>
        <div className="flex rounded-lg overflow-hidden border border-slate-200 dark:border-slate-600 text-xs">
          {(["historical", "live"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1 capitalize transition-colors ${
                mode === m
                  ? "bg-indigo-500 text-white"
                  : "bg-white dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-600"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {isEmpty ? (
        <p className="text-slate-400 text-sm h-52 flex items-center justify-center">
          {mode === "historical" && timeseries.length === 0
            ? "No historical data — data accumulates as Spark writes aggregates"
            : "Waiting for live data..."}
        </p>
      ) : showHistorical ? (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={historicalData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="gradHist" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
            <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#94a3b8" }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} width={55} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", fontSize: 12 }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Area type="monotone" dataKey="value" name={METRIC_LABELS[metric] ?? metric}
              stroke="#6366f1" fill="url(#gradHist)" strokeWidth={2} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={liveData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="gradPageview" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradPurchase" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradError" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
            <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#94a3b8" }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} width={45} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", fontSize: 12 }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Area type="monotone" dataKey="pageview" name="Pageviews" stroke="#6366f1" fill="url(#gradPageview)" strokeWidth={2} isAnimationActive={false} />
            <Area type="monotone" dataKey="purchase" name="Purchases" stroke="#10b981" fill="url(#gradPurchase)" strokeWidth={2} isAnimationActive={false} />
            <Area type="monotone" dataKey="system_error" name="Errors" stroke="#ef4444" fill="url(#gradError)" strokeWidth={2} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default memo(TimeseriesChartInner);
