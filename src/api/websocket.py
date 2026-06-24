"""WebSocket connection manager with heartbeat and auto-cleanup."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

log = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30
MISSED_PONG_LIMIT = 3


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, float] = {}
        self._lock = asyncio.Lock()

    @property
    def count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections[ws] = time.monotonic()
        log.info("ws connected, total=%d", self.count)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(ws, None)
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.close()
        except Exception:
            pass
        log.info("ws disconnected, total=%d", self.count)

    async def broadcast(self, data: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._connections.keys())

        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

    async def _ping_one(self, ws: WebSocket) -> bool:
        try:
            await ws.send_json({"type": "ping"})
            return True
        except Exception:
            return False

    async def heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            async with self._lock:
                targets = list(self._connections.items())

            dead: list[WebSocket] = []
            for ws, last_pong in targets:
                if time.monotonic() - last_pong > HEARTBEAT_INTERVAL * MISSED_PONG_LIMIT:
                    dead.append(ws)
                    continue
                if not await self._ping_one(ws):
                    dead.append(ws)

            for ws in dead:
                log.info("ws heartbeat timeout, closing")
                await self.disconnect(ws)

    async def record_pong(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._connections:
                self._connections[ws] = time.monotonic()


manager = ConnectionManager()
