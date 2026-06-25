"""stdio 入口:`python -m api.mcp_server`。

agent 端(如 Claude Code)以 stdio 启动本进程作为 MCP server:
  claude mcp add flori -- <docker 包装,跑本模块>
v2 再加 streamable-HTTP(挂 API + 经 Caddy + token 认证)。
"""

from __future__ import annotations

from api.mcp_server.server import build_default_server


def main() -> None:
    build_default_server().run()  # 默认 stdio 传输


if __name__ == "__main__":
    main()
