import { useMetricsStore } from "../store/metricsSlice";
import type { Metric, Granularity, Duration, Dimension } from "../types";

const METRICS: { value: Metric; label: string }[] = [
  { value: "event_count", label: "Event Count" },
  { value: "avg_duration_ms", label: "Avg Duration" },
  { value: "purchase_total_usd", label: "Purchase Total" },
  { value: "avg_amount_usd", label: "Avg Amount" },
];

const GRANULARITIES: Granularity[] = ["5m", "15m", "1h", "1d"];
const DURATIONS: Duration[] = ["1h", "6h", "24h"];
const DIMENSIONS: { value: Dimension; label: string }[] = [
  { value: "region", label: "Region" },
  { value: "event_type", label: "Event Type" },
];

const EVENT_TYPES = ["", "pageview", "purchase", "system_error"];

function Select<T extends string>({
  label, value, options, onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-sm"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

export default function FilterPanel() {
  const { filters, setFilters } = useMetricsStore();

  return (
    <div className="flex flex-wrap gap-3 p-4 bg-card-light dark:bg-card-dark rounded-xl border border-slate-200 dark:border-slate-700">
      <Select
        label="Metric"
        value={filters.metric}
        options={METRICS}
        onChange={(v) => setFilters({ metric: v })}
      />
      <Select
        label="Granularity"
        value={filters.granularity}
        options={GRANULARITIES.map((g) => ({ value: g, label: g }))}
        onChange={(v) => setFilters({ granularity: v })}
      />
      <Select
        label="Duration"
        value={filters.duration}
        options={DURATIONS.map((d) => ({ value: d, label: d }))}
        onChange={(v) => setFilters({ duration: v })}
      />
      <Select
        label="Dimension"
        value={filters.dimension}
        options={DIMENSIONS}
        onChange={(v) => setFilters({ dimension: v })}
      />
      <Select
        label="Event Type"
        value={filters.eventType as string}
        options={EVENT_TYPES.map((t) => ({ value: t, label: t || "All" }))}
        onChange={(v) => setFilters({ eventType: v })}
      />
    </div>
  );
}
