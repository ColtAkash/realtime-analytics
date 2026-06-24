from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from websocket import manager
from broadcaster import get_snapshot_sync

log = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/metrics")
async def ws_metrics(ws: WebSocket):
    await manager.connect(ws)
    try:
        snapshot = await asyncio.get_event_loop().run_in_executor(None, get_snapshot_sync)
        await ws.send_json(snapshot)

        while True:
            data = await ws.receive_json()
            if data.get("type") == "pong":
                await manager.record_pong(ws)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await manager.disconnect(ws)
