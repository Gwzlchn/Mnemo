"""统一日志配置:全栈(API / 调度器 / Worker / 步骤子进程)输出带 ISO 时间戳的
结构化 JSON,便于 Dozzle 等统一采集,避免各服务渲染格式不一致。"""

from __future__ import annotations

import structlog


def setup_logging() -> None:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )
