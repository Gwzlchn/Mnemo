"""WebSocket 进度推送。"""

from __future__ import annotations

import asyncio
import json

import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from shared.redis_client import RedisClient
from api.deps import get_redis

logger = structlog.get_logger(component="ws")

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws/jobs/{job_id}")
async def ws_job(websocket: WebSocket, job_id: str):
    await websocket.accept()
    redis: RedisClient = websocket.app.state.redis

    pubsub = redis.r.pubsub()
    await pubsub.subscribe(f"events:{job_id}")
    try:
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                await websocket.send_text(msg["data"])
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws_job_error", job_id=job_id)
    finally:
        await pubsub.unsubscribe(f"events:{job_id}")
        await pubsub.aclose()


@router.websocket("/api/ws/global")
async def ws_global(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            status = await _build_global_status(websocket.app)
            await websocket.send_text(json.dumps(status, ensure_ascii=False))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws_global_error")


async def _build_global_status(app) -> dict:
    db = app.state.db

    total, _ = await asyncio.to_thread(db.list_jobs, limit=0)
    done_total, _ = await asyncio.to_thread(db.list_jobs, status="done", limit=0)
    failed_total, _ = await asyncio.to_thread(db.list_jobs, status="failed", limit=0)
    processing_total, _ = await asyncio.to_thread(db.list_jobs, status="processing", limit=0)

    return {
        "jobs": {
            "total": total,
            "done": done_total,
            "processing": processing_total,
            "failed": failed_total,
        },
    }
