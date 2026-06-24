export function SkeletonCard() {
  return (
    <div className="animate-pulse bg-card-light dark:bg-card-dark rounded-xl border border-slate-200 dark:border-slate-700 p-6">
      <div className="h-4 w-24 bg-slate-200 dark:bg-slate-600 rounded mb-4" />
      <div className="h-8 w-32 bg-slate-200 dark:bg-slate-600 rounded mb-2" />
      <div className="h-3 w-20 bg-slate-100 dark:bg-slate-700 rounded" />
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="animate-pulse bg-card-light dark:bg-card-dark rounded-xl border border-slate-200 dark:border-slate-700 p-6 h-64">
      <div className="h-4 w-32 bg-slate-200 dark:bg-slate-600 rounded mb-6" />
      <div className="flex items-end gap-1 h-40">
        {Array.from({ length: 12 }, (_, i) => (
          <div
            key={i}
            className="flex-1 bg-slate-200 dark:bg-slate-600 rounded-t"
            style={{ height: `${30 + Math.random() * 70}%` }}
          />
        ))}
      </div>
    </div>
  );
}
