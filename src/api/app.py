from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from routes.metrics import router as metrics_router
from routes.health import router as health_router
from routes.ws import router as ws_router
from websocket import manager
from broadcaster import broadcast_loop

log_handler = logging.StreamHandler()
log_handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.root.handlers = [log_handler]
logging.root.setLevel(logging.INFO)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    broadcast_task = asyncio.create_task(broadcast_loop(manager))
    heartbeat_task = asyncio.create_task(manager.heartbeat_loop())
    yield
    broadcast_task.cancel()
    heartbeat_task.cancel()


app = FastAPI(
    title="Realtime Analytics API",
    description="REST API for real-time analytics dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
app.include_router(ws_router)
