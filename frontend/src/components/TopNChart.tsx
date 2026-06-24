import { memo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { useMetricsStore } from "../store/metricsSlice";
import { SkeletonChart } from "./Skeleton";

const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

function TopNChartInner() {
  const topN = useMetricsStore((s) => s.topN);
  const loading = useMetricsStore((s) => s.loading);
  const dimension = useMetricsStore((s) => s.filters.dimension);

  if (loading && topN.length === 0) return <SkeletonChart />;

  const data = topN.map((e) => ({
    name: e.key,
    value: e.value ?? 0,
  }));

  return (
    <div className="bg-card-light dark:bg-card-dark rounded-xl border border-slate-200 dark:border-slate-700 p-6">
      <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-4">
        Top by {dimension}
      </h3>
      {data.length === 0 ? (
        <p className="text-slate-400 text-sm h-52 flex items-center justify-center">No data available</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
            <XAxis type="number" tick={{ fontSize: 10, fill: "#94a3b8" }} />
            <YAxis
              type="category" dataKey="name"
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              width={80}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                fontSize: 12,
              }}
              formatter={(v: number) => v.toLocaleString()}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive={false}>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default memo(TopNChartInner);
