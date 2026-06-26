"""入口:`python -m api.mcp_server` —— streamable-http MCP server(唯一传输)。

streamable-http + Bearer token,uvicorn 监听 MCP_PORT(默认 8090),经 Caddy 暴露 /mcp。
按库作用域:用路径 /mcp/{domain}(由 DomainScopeASGI 中间件处理),无需每库起进程;
或 env FLORI_MCP_DEFAULT_DOMAIN=<domain> 设全局默认库(见 server.scope_domain)。
"""

from __future__ import annotations

import os

import uvicorn

from api.mcp_server.http_app import build_http_app


def main() -> None:
    uvicorn.run(
        build_http_app(),
        host="0.0.0.0",  # noqa: S104 — 容器内监听,经端口绑定/反代收口
        port=int(os.environ.get("MCP_PORT", "8090")),
    )


if __name__ == "__main__":
    main()
