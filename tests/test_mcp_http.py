"""tests for api/mcp_server/http_app.py —— Bearer token 鉴权中间件(纯 ASGI)。

只验鉴权逻辑(MCP 协议本身见 test_mcp.py):用 dummy 内层 app 包 TokenAuthASGI,
经 httpx ASGITransport 驱动,断 503/401/放行;另验 lifespan 直通 + build_http_app 可构造。
"""

from __future__ import annotations

import httpx
import pytest

from api.mcp_server.http_app import TokenAuthASGI


async def _dummy(scope, receive, send):
    """内层 app:走到这里即鉴权已放行。"""
    assert scope["type"] == "http"
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"text/plain")]})
    await send({"type": "http.response.body", "body": b"ok"})


async def _post(app, headers=None):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        return await c.post("/mcp", headers=headers or {})


@pytest.mark.asyncio
async def test_no_token_no_allow_503(monkeypatch):
    monkeypatch.delenv("FLORI_MCP_TOKEN", raising=False)
    monkeypatch.delenv("FLORI_MCP_ALLOW_NO_AUTH", raising=False)
    r = await _post(TokenAuthASGI(_dummy))
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_token_set_missing_or_wrong_bearer_401(monkeypatch):
    monkeypatch.setenv("FLORI_MCP_TOKEN", "secret123")
    monkeypatch.delenv("FLORI_MCP_ALLOW_NO_AUTH", raising=False)
    assert (await _post(TokenAuthASGI(_dummy))).status_code == 401
    assert (await _post(TokenAuthASGI(_dummy), {"Authorization": "Bearer wrong"})).status_code == 401


@pytest.mark.asyncio
async def test_token_set_correct_bearer_passes(monkeypatch):
    monkeypatch.setenv("FLORI_MCP_TOKEN", "secret123")
    r = await _post(TokenAuthASGI(_dummy), {"Authorization": "Bearer secret123"})
    assert r.status_code == 200
    assert r.text == "ok"


@pytest.mark.asyncio
async def test_allow_no_auth_passes(monkeypatch):
    monkeypatch.delenv("FLORI_MCP_TOKEN", raising=False)
    monkeypatch.setenv("FLORI_MCP_ALLOW_NO_AUTH", "1")
    assert (await _post(TokenAuthASGI(_dummy))).status_code == 200


@pytest.mark.asyncio
async def test_lifespan_passthrough():
    """非 http scope(lifespan)必须直通内层 —— 否则 streamable-http 的 session manager 起不来。"""
    seen = {}

    async def inner(scope, receive, send):
        seen["type"] = scope["type"]

    await TokenAuthASGI(inner)({"type": "lifespan"}, None, None)
    assert seen["type"] == "lifespan"


def test_build_http_app_smoke(monkeypatch, tmp_path):
    """build_http_app 能构造(create_storage 本地后端 + streamable_http_app)。"""
    monkeypatch.setenv("CONFIG_DIR", "/app/configs")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("MINIO_URL", raising=False)
    monkeypatch.setenv("FLORI_MCP_ALLOW_NO_AUTH", "1")
    from api.mcp_server.http_app import build_http_app

    app = build_http_app()
    assert callable(app)
