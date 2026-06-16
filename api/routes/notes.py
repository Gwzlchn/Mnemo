"""笔记/截图/视频文件服务。经 StorageBackend 读，兼容本地盘与 MinIO。"""

from __future__ import annotations

import fnmatch
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse

from shared.config import AppConfig
from shared.storage import StorageBackend
from api.deps import get_config, get_storage, verify_token

router = APIRouter(prefix="/api/jobs", tags=["notes"], dependencies=[Depends(verify_token)])

# 产物 → 步骤分组(按出现顺序归第一个命中的步;未命中归「其他」)。
_STEP_GROUPS = [
    ("00_download", "下载 / 原始", ["input/metadata.json", "input/article_meta.json",
                                    "input/*.srt", "input/*.ass", "input/source.html", "input/source.pdf"]),
    ("01_scene", "场景检测", ["intermediate/scenes.json"]),
    ("02_frames", "代表帧", ["intermediate/frames.json", "assets/*"]),
    ("03_dedup", "去重", ["intermediate/dedup.json"]),
    ("04_ocr", "OCR", ["intermediate/ocr.json"]),
    ("05_danmaku", "弹幕", ["intermediate/danmaku.json"]),
    ("06_punctuate", "口播标点", ["output/transcript.md"]),
    ("07_mechanical", "机械版笔记", ["output/notes_mechanical.md"]),
    ("08_smart", "智能版笔记", ["output/notes_smart.md", "output/versions/smart__*"]),
    ("09_review", "评审", ["output/review.json", "output/versions/review__*"]),
    ("logs", "日志", ["logs/*"]),
]
# 不列出:大源文件 / yutto 中间件 / 内部点文件 / job.json(含 SESSDATA,绝不暴露)。
_ARTIFACT_HIDE = ["input/source.mp4", "input/source.mp3", "input/*.m4s", "input/*_cover.*"]


def _artifact_kind(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if ext in ("jpg", "jpeg", "png", "gif", "webp"):
        return "image"
    if ext == "json":
        return "json"
    if ext in ("md", "srt", "txt", "html", "ass", "log"):
        return "text"
    return "other"


def _artifact_hidden(f: str) -> bool:
    base = f.rsplit("/", 1)[-1]
    if base.startswith("."):  # .done / .{step}.config.json / .progress / .error.json
        return True
    if f == "job.json":  # 含 SESSDATA
        return True
    return any(fnmatch.fnmatch(f, p) for p in _ARTIFACT_HIDE)


def _validate_job_id(job_id: str) -> None:
    if ".." in job_id or "/" in job_id or "\x00" in job_id:
        raise HTTPException(400, "invalid job_id")


async def _serve(
    storage: StorageBackend, job_id: str, rel_path: str, media_type: str, missing: str,
    cache: bool = False,
) -> Response:
    _validate_job_id(job_id)
    data = await storage.read_file(job_id, rel_path)
    if data is None:
        raise HTTPException(404, missing)
    headers = {}
    if cache:
        # 帧图等产物不可变(文件名含时间戳),长缓存让翻页/重访秒开,省 1Mbps 公网带宽。
        headers["Cache-Control"] = "public, max-age=604800, immutable"
    return Response(content=data, media_type=media_type, headers=headers)


def _safe_provider(p: str) -> str:
    # provider 仅用于拼版本文件名,限字母数字与 -_,挡路径穿越。
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", p or ""):
        raise HTTPException(400, "invalid provider")
    return p


@router.get("/{job_id}/notes/smart")
async def get_smart_notes(job_id: str, provider: str | None = None,
                          storage: StorageBackend = Depends(get_storage)):
    # provider 指定时取该版本,否则取默认(最近一次)。
    rel = f"output/versions/smart__{_safe_provider(provider)}.md" if provider else "output/notes_smart.md"
    return await _serve(storage, job_id, rel,
                        "text/markdown; charset=utf-8", "smart notes not ready")


@router.get("/{job_id}/note-versions")
async def list_note_versions(job_id: str, storage: StorageBackend = Depends(get_storage)):
    """列出该 job 的智能笔记各 provider 版本 + 各自评分,供前端版本切换。"""
    _validate_job_id(job_id)
    import json as _json
    files = await storage.list_files(job_id)
    versions = []
    for f in files:
        if f.startswith("output/versions/smart__") and f.endswith(".md"):
            prov = f[len("output/versions/smart__"):-len(".md")]
            score = None
            rdata = await storage.read_file(job_id, f"output/versions/review__{prov}.json")
            if rdata:
                try:
                    score = _json.loads(rdata).get("overall")
                except (ValueError, _json.JSONDecodeError):
                    pass
            versions.append({"provider": prov, "overall": score})
    versions.sort(key=lambda v: v["provider"])
    return {"versions": versions}


@router.get("/{job_id}/notes/mechanical")
async def get_mechanical_notes(job_id: str, storage: StorageBackend = Depends(get_storage)):
    return await _serve(storage, job_id, "output/notes_mechanical.md",
                        "text/markdown; charset=utf-8", "mechanical notes not ready")


@router.get("/{job_id}/notes/transcript")
async def get_transcript(job_id: str, storage: StorageBackend = Depends(get_storage)):
    return await _serve(storage, job_id, "output/transcript.md",
                        "text/markdown; charset=utf-8", "transcript not ready")


@router.get("/{job_id}/review")
async def get_review(job_id: str, provider: str | None = None,
                     storage: StorageBackend = Depends(get_storage)):
    rel = f"output/versions/review__{_safe_provider(provider)}.json" if provider else "output/review.json"
    return await _serve(storage, job_id, rel, "application/json", "review not ready")


@router.get("/{job_id}/assets/{filename}")
async def get_asset(job_id: str, filename: str, storage: StorageBackend = Depends(get_storage)):
    if ".." in filename or "/" in filename:
        raise HTTPException(400, "invalid filename")
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return await _serve(storage, job_id, f"assets/{filename}", media_type, "asset not found",
                        cache=True)


@router.get("/{job_id}/artifacts")
async def list_artifacts(job_id: str, storage: StorageBackend = Depends(get_storage)):
    """列某 job 全部产物,按步骤分组(供前端分步查看)。隐藏大源文件/内部文件/job.json。"""
    _validate_job_id(job_id)
    files = [f for f in await storage.list_files(job_id) if not _artifact_hidden(f)]
    assigned: set[str] = set()
    groups = []
    for step, label, pats in _STEP_GROUPS:
        matched = sorted(
            f for f in files
            if f not in assigned and any(fnmatch.fnmatch(f, p) for p in pats)
        )
        assigned.update(matched)
        if matched:
            groups.append({"step": step, "label": label,
                           "files": [{"path": f, "kind": _artifact_kind(f)} for f in matched]})
    other = sorted(f for f in files if f not in assigned)
    if other:
        groups.append({"step": "其他", "label": "其他",
                       "files": [{"path": f, "kind": _artifact_kind(f)} for f in other]})
    return {"groups": groups}


@router.get("/{job_id}/artifact")
async def get_artifact(job_id: str, path: str, storage: StorageBackend = Depends(get_storage)):
    """取任意产物(仅放行真实存在且未隐藏的;按扩展名定 content-type;图片长缓存)。"""
    _validate_job_id(job_id)
    if ".." in path or path.startswith("/") or "\x00" in path:
        raise HTTPException(400, "invalid path")
    files = await storage.list_files(job_id)
    if path not in files or _artifact_hidden(path):
        raise HTTPException(404, "artifact not found")
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    ct = {
        "md": "text/markdown; charset=utf-8",
        "json": "application/json; charset=utf-8",
        "txt": "text/plain; charset=utf-8",
        "srt": "text/plain; charset=utf-8",
        "html": "text/plain; charset=utf-8",  # 不渲染原始 HTML
        "ass": "text/plain; charset=utf-8",
        "log": "text/plain; charset=utf-8",
    }.get(ext) or (mimetypes.guess_type(path)[0] or "application/octet-stream")
    return await _serve(storage, job_id, path, ct, "artifact not found",
                        cache=_artifact_kind(path) == "image")


@router.get("/{job_id}/source")
async def get_source(job_id: str, request: Request, config: AppConfig = Depends(get_config)):
    # 视频回放仍走本地盘的 range 流式;分布式(MinIO)模式下的对象存储 range 流式为后续。
    _validate_job_id(job_id)
    video_path = config.jobs_dir / job_id / "input" / "source.mp4"
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
