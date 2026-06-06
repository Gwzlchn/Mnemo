"""平台认证路由：B站扫码 + YouTube cookies。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from api.deps import verify_token

router = APIRouter(prefix="/api/auth", tags=["auth"], dependencies=[Depends(verify_token)])

COOKIES_DIR = Path("/data/cookies")


@router.get("/status")
async def auth_status():
    COOKIES_DIR.mkdir(parents=True, exist_ok=True)
    bilibili = (COOKIES_DIR / "bilibili.txt").exists()
    youtube = (COOKIES_DIR / "youtube.txt").exists()
    return {
        "bilibili": {"has_cookies": bilibili, "status": "ok" if bilibili else "missing"},
        "youtube": {"has_cookies": youtube, "status": "ok" if youtube else "missing"},
    }


@router.post("/bilibili/qrcode")
async def bilibili_qrcode():
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
                timeout=10,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise HTTPException(502, f"bilibili API error: {data}")
            return {
                "qrcode_url": data["data"]["url"],
                "qrcode_key": data["data"]["qrcode_key"],
            }
    except httpx.HTTPError as e:
        raise HTTPException(502, f"bilibili API unreachable: {e}")


@router.get("/bilibili/poll")
async def bilibili_poll(key: str):
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
                params={"qrcode_key": key},
                timeout=10,
            )
            data = resp.json()
            code = data.get("data", {}).get("code", -1)

            status_map = {
                0: ("success", "1080P 已解锁"),
                86038: ("expired", "二维码已过期，请刷新"),
                86090: ("scanned", "已扫码，请在 App 确认"),
                86101: ("waiting", "等待扫码..."),
            }
            status, message = status_map.get(code, ("error", f"未知状态: {code}"))

            if code == 0:
                cookies = resp.cookies
                COOKIES_DIR.mkdir(parents=True, exist_ok=True)
                cookie_lines = [f"{k}\t{v}" for k, v in cookies.items()]
                (COOKIES_DIR / "bilibili.txt").write_text("\n".join(cookie_lines))

            return {"status": status, "message": message}
    except Exception as e:
        raise HTTPException(502, str(e))


@router.post("/youtube/cookies")
async def youtube_cookies(file: UploadFile = File(...)):
    COOKIES_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    (COOKIES_DIR / "youtube.txt").write_bytes(content)
    return {"status": "ok", "message": "YouTube cookies 已保存"}
