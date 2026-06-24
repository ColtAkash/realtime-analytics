import { useWsStore } from "../store/wsSlice";

const STATUS_CONFIG = {
  connected: { color: "bg-green-500", label: "Live" },
  connecting: { color: "bg-yellow-500 animate-pulse", label: "Connecting" },
  disconnected: { color: "bg-red-500", label: "Disconnected" },
} as const;

export default function ConnectionStatus() {
  const status = useWsStore((s) => s.status);
  const cfg = STATUS_CONFIG[status];

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className={`w-2.5 h-2.5 rounded-full ${cfg.color}`} />
      <span className="text-slate-600 dark:text-slate-400">{cfg.label}</span>
    </div>
  );
}
