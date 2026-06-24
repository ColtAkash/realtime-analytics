import { useMetrics } from "../hooks/useMetrics";
import { useWebSocket } from "../hooks/useWebSocket";
import { useMetricsStore } from "../store/metricsSlice";
import FilterPanel from "./FilterPanel";
import LiveCounter from "./LiveCounter";
import TimeseriesChart from "./TimeseriesChart";
import TopNChart from "./TopNChart";
import GaugeChart from "./GaugeChart";
import { SkeletonCard, SkeletonChart } from "./Skeleton";

export default function Dashboard() {
  useMetrics();
  useWebSocket();

  const live = useMetricsStore((s) => s.live);
  const loading = useMetricsStore((s) => s.loading);

  const counts = live?.event_type_counts ?? {};
  const totalEvents = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      <FilterPanel />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {loading && !live ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <LiveCounter
              label="Total Events"
              value={totalEvents}
              color="text-blue-500"
            />
            <LiveCounter
              label="Pageviews"
              value={counts.pageview ?? 0}
              color="text-indigo-500"
            />
            <LiveCounter
              label="Revenue"
              value={live?.purchase_total_usd ?? 0}
              prefix="$"
              color="text-emerald-500"
            />
            <LiveCounter
              label="Purchases"
              value={counts.purchase ?? 0}
              color="text-amber-500"
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TimeseriesChart />
        </div>
        <GaugeChart />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-1 gap-6">
        <TopNChart />
      </div>
    </div>
  );
}
