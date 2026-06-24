import { useEffect, useRef } from "react";
import { useWsStore } from "../store/wsSlice";
import { useMetricsStore } from "../store/metricsSlice";
import type { WsMessage } from "../types";
import { mockWsMessage } from "../api/mock";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/metrics";
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";
const RECONNECT_DELAY = 3000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const { setStatus, setLastMessage } = useWsStore();
  const pushLive = useMetricsStore((s) => s.pushLive);

  useEffect(() => {
    if (USE_MOCK) {
      setStatus("connected");
      pushLive(mockWsMessage);
      const interval = setInterval(() => {
        pushLive({
          ...mockWsMessage,
          ts: new Date().toISOString(),
          event_type_counts: {
            pageview: 5000 + Math.round(Math.random() * 2000),
            purchase: 1000 + Math.round(Math.random() * 800),
            system_error: 200 + Math.round(Math.random() * 300),
          },
          purchase_total_usd: 30000 + Math.round(Math.random() * 20000),
          error_rate: Math.round(Math.random() * 80) / 10,
        });
      }, 1000);
      return () => clearInterval(interval);
    }

    function connect() {
      setStatus("connecting");
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setStatus("connected");

      ws.onmessage = (evt) => {
        try {
          const data: WsMessage = JSON.parse(evt.data);
          if ((data as any).type === "ping") {
            ws.send(JSON.stringify({ type: "pong" }));
            return;
          }
          pushLive(data);
          setLastMessage(data.ts);
        } catch {}
      };

      ws.onclose = () => {
        setStatus("disconnected");
        wsRef.current = null;
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
      };

      ws.onerror = () => ws.close();
    }

    connect();

    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);
}
