"""Worker 管理路由。"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from shared.db import Database
from api.deps import get_db, verify_token
from api.schemas import WorkerResponse, WorkerUpdateRequest

router = APIRouter(prefix="/api/workers", tags=["workers"], dependencies=[Depends(verify_token)])


@router.get("")
async def list_workers(db: Database = Depends(get_db)):
    workers = await asyncio.to_thread(db.list_workers)
    return [
        WorkerResponse(
            id=w.id, type=w.type, pools=w.pools,
            hostname=w.hostname, status=w.status,
            current_job=w.current_job, current_step=w.current_step,
            tasks_completed=w.tasks_completed, tasks_failed=w.tasks_failed,
            total_duration_sec=w.total_duration_sec,
            first_seen=w.first_seen.isoformat(),
            started_at=w.started_at.isoformat() if w.started_at else None,
            last_heartbeat=w.last_heartbeat.isoformat() if w.last_heartbeat else None,
            admin_note=w.admin_note,
        )
        for w in workers
    ]


@router.get("/{worker_id}")
async def get_worker(worker_id: str, db: Database = Depends(get_db)):
    w = await asyncio.to_thread(db.get_worker, worker_id)
    if not w:
        raise HTTPException(404, "worker not found")
    return WorkerResponse(
        id=w.id, type=w.type, pools=w.pools,
        hostname=w.hostname, status=w.status,
        current_job=w.current_job, current_step=w.current_step,
        tasks_completed=w.tasks_completed, tasks_failed=w.tasks_failed,
        total_duration_sec=w.total_duration_sec,
        first_seen=w.first_seen.isoformat(),
        started_at=w.started_at.isoformat() if w.started_at else None,
        last_heartbeat=w.last_heartbeat.isoformat() if w.last_heartbeat else None,
        admin_note=w.admin_note,
    )


@router.put("/{worker_id}")
async def update_worker(worker_id: str, req: WorkerUpdateRequest, db: Database = Depends(get_db)):
    w = await asyncio.to_thread(db.get_worker, worker_id)
    if not w:
        raise HTTPException(404, "worker not found")
    if req.status is not None:
        w.status = req.status
    if req.admin_note is not None:
        w.admin_note = req.admin_note
    await asyncio.to_thread(db.upsert_worker, w)
    return {"id": worker_id, "status": "updated"}


@router.delete("/{worker_id}", status_code=204)
async def delete_worker(worker_id: str, db: Database = Depends(get_db)):
    w = await asyncio.to_thread(db.get_worker, worker_id)
    if not w:
        raise HTTPException(404, "worker not found")
    await asyncio.to_thread(db.delete_worker, worker_id)
