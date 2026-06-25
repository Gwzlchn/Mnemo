"""入口:`python -m api.mcp_server`。

MCP_TRANSPORT(默认 stdio):
- stdio:agent 端(如 Claude Code)以 stdio 启动本进程作为 MCP server
    claude mcp add flori -- <docker 包装,跑本模块>
- http:streamable-http + Bearer token,uvicorn 监听 MCP_PORT(默认 8090),经 Caddy 暴露 /mcp。
"""

from __future__ import annotations

import os

from api.mcp_server.server import build_default_server


def _configure_stdio_logging() -> None:
    """MCP stdio:stdout 必须是纯 JSON-RPC 协议流。structlog 默认 PrintLogger 写 stdout
    会污染协议(tool 调用时的 log 行混进响应)→ 重定向到 stderr。"""
    import sys

    import structlog

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        import uvicorn

        from api.mcp_server.http_app import build_http_app

        uvicorn.run(
            build_http_app(),
            host="0.0.0.0",  # noqa: S104 — 容器内监听,经端口绑定/反代收口
            port=int(os.environ.get("MCP_PORT", "8090")),
        )
    else:
        _configure_stdio_logging()  # 先把日志引到 stderr,再开 stdio(保 stdout 纯净)
        build_default_server().run()  # 默认 stdio 传输


if __name__ == "__main__":
    main()
