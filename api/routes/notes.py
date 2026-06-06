"""笔记/截图/视频文件服务。"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse

from shared.config import AppConfig
from api.deps import get_config, verify_token

router = APIRouter(prefix="/api/jobs", tags=["notes"], dependencies=[Depends(verify_token)])


def _validate_job_id(job_id: str) -> None:
    if ".." in job_id or "/" in job_id or "\x00" in job_id:
        raise HTTPException(400, "invalid job_id")


def _job_dir(config: AppConfig, job_id: str) -> Path:
    _validate_job_id(job_id)
    d = config.jobs_dir / job_id
    if not d.exists():
        raise HTTPException(404, "job not found")
    return d


@router.get("/{job_id}/notes/smart")
async def get_smart_notes(job_id: str, config: AppConfig = Depends(get_config)):
    path = _job_dir(config, job_id) / "output" / "notes_smart.md"
    if not path.exists():
        raise HTTPException(404, "smart notes not ready")
    return Response(content=path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


@router.get("/{job_id}/notes/mechanical")
async def get_mechanical_notes(job_id: str, config: AppConfig = Depends(get_config)):
    path = _job_dir(config, job_id) / "output" / "notes_mechanical.md"
    if not path.exists():
        raise HTTPException(404, "mechanical notes not ready")
    return Response(content=path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


@router.get("/{job_id}/notes/transcript")
async def get_transcript(job_id: str, config: AppConfig = Depends(get_config)):
    path = _job_dir(config, job_id) / "output" / "transcript.md"
    if not path.exists():
        raise HTTPException(404, "transcript not ready")
    return Response(content=path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


@router.get("/{job_id}/review")
async def get_review(job_id: str, config: AppConfig = Depends(get_config)):
    path = _job_dir(config, job_id) / "output" / "review.json"
    if not path.exists():
        raise HTTPException(404, "review not ready")
    return Response(content=path.read_bytes(), media_type="application/json")


@router.get("/{job_id}/assets/{filename}")
async def get_asset(job_id: str, filename: str, config: AppConfig = Depends(get_config)):
    if ".." in filename or "/" in filename:
        raise HTTPException(400, "invalid filename")
    path = _job_dir(config, job_id) / "assets" / filename
    if not path.exists():
        raise HTTPException(404, "asset not found")
    return FileResponse(path)


@router.get("/{job_id}/source")
async def get_source(job_id: str, request: Request, config: AppConfig = Depends(get_config)):
    job_dir = _job_dir(config, job_id)
    video_path = job_dir / "input" / "source.mp4"
    if not video_path.exists():
        raise HTTPException(404, "source not found")

    file_size = video_path.stat().st_size
    range_header = request.headers.get("range")

    if not range_header:
        return FileResponse(video_path, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})

    try:
        range_str = range_header.replace("bytes=", "")
        parts = range_str.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        end = min(end, file_size - 1)
        if start < 0 or start > end or start >= file_size:
            raise ValueError("invalid range")
        length = end - start + 1
    except (ValueError, IndexError):
        raise HTTPException(416, "invalid Range header")

    def _stream():
        with open(video_path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(8192, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        _stream(),
        status_code=206,
        media_type="video/mp4",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
        },
    )
