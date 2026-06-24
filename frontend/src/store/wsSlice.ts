import { create } from "zustand";

type WsStatus = "connecting" | "connected" | "disconnected";

interface WsState {
  status: WsStatus;
  lastMessage: string | null;
  setStatus: (s: WsStatus) => void;
  setLastMessage: (ts: string) => void;
}

export const useWsStore = create<WsState>((set) => ({
  status: "disconnected",
  lastMessage: null,
  setStatus: (status) => set({ status }),
  setLastMessage: (ts) => set({ lastMessage: ts }),
}));
