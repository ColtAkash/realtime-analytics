import { memo } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useMetricsStore } from "../store/metricsSlice";
import { SkeletonChart } from "./Skeleton";

function formatTime(ts: string) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function TimeseriesChartInner() {
  const liveHistory = useMetricsStore((s) => s.liveHistory);
  const loading = useMetricsStore((s) => s.loading);

  if (loading && liveHistory.length === 0) return <SkeletonChart />;

  const data = liveHistory.map((p) => ({
    time: formatTime(p.ts),
    pageview: p.pageview,
    purchase: p.purchase,
    system_error: p.system_error,
  }));

  return (
    <div className="bg-card-light dark:bg-card-dark rounded-xl border border-slate-200 dark:border-slate-700 p-6">
      <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-4">
        Live Events ({liveHistory.length} points)
      </h3>
      {data.length === 0 ? (
        <p className="text-slate-400 text-sm h-52 flex items-center justify-center">
          Waiting for live data...
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
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
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              interval="preserveStartEnd"
            />
            <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} width={45} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                fontSize: 12,
              }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Area
              type="monotone" dataKey="pageview" name="Pageviews"
              stroke="#6366f1" fill="url(#gradPageview)"
              strokeWidth={2} isAnimationActive={false}
            />
            <Area
              type="monotone" dataKey="purchase" name="Purchases"
              stroke="#10b981" fill="url(#gradPurchase)"
              strokeWidth={2} isAnimationActive={false}
            />
            <Area
              type="monotone" dataKey="system_error" name="Errors"
              stroke="#ef4444" fill="url(#gradError)"
              strokeWidth={2} isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default memo(TimeseriesChartInner);
