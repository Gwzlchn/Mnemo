"""平台认证路由：YouTube cookies + 平台 cookie 状态（B站扫码登录见 api/routes/bili.py）。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File

from api.deps import verify_token

router = APIRouter(prefix="/api/auth", tags=["auth"], dependencies=[Depends(verify_token)])

COOKIES_DIR = Path("/data/cookies")


@router.get("/status")
async def auth_status():
    """平台 cookie 文件状态。B站登录态以 /api/bili/status(DB)为准,此处仅反映
    下载步的本地文件回退 bilibili.txt 是否存在 + YouTube cookies 是否已配置。"""
    COOKIES_DIR.mkdir(parents=True, exist_ok=True)
    bilibili = (COOKIES_DIR / "bilibili.txt").exists()
    youtube = (COOKIES_DIR / "youtube.txt").exists()
    return {
        "bilibili": {"has_cookies": bilibili, "status": "ok" if bilibili else "missing"},
        "youtube": {"has_cookies": youtube, "status": "ok" if youtube else "missing"},
    }


@router.post("/youtube/cookies")
async def youtube_cookies(file: UploadFile = File(...)):
    COOKIES_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    (COOKIES_DIR / "youtube.txt").write_bytes(content)
    return {"status": "ok", "message": "YouTube cookies 已保存"}
