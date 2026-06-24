import { memo, useEffect, useRef, useState } from "react";

interface Props {
  value: number;
  prefix?: string;
  suffix?: string;
  label: string;
  color?: string;
  decimals?: number;
}

function LiveCounterInner({ value, prefix = "", suffix = "", label, color = "text-blue-500", decimals = 0 }: Props) {
  const [display, setDisplay] = useState(value);
  const rafRef = useRef<number>();
  const startRef = useRef(display);
  const startTime = useRef(0);

  useEffect(() => {
    startRef.current = display;
    startTime.current = performance.now();

    function animate(now: number) {
      const elapsed = now - startTime.current;
      const duration = 500;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = startRef.current + (value - startRef.current) * eased;
      setDisplay(current);
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    }

    rafRef.current = requestAnimationFrame(animate);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [value]);

  const formatted = decimals > 0
    ? display.toFixed(decimals)
    : Math.round(display).toLocaleString();

  return (
    <div className="bg-card-light dark:bg-card-dark rounded-xl border border-slate-200 dark:border-slate-700 p-6">
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
      <p className={`text-2xl font-bold mt-1 tabular-nums ${color}`}>
        {prefix}{formatted}{suffix}
      </p>
    </div>
  );
}

export default memo(LiveCounterInner);
