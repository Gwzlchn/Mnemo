"""Worker 入口。"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys

import structlog

from shared.config import load_config
from shared.db import Database
from shared.redis_client import RedisClient
from shared.storage import create_storage

from .transport import create_transport
from .worker import WORKER_POOLS, Worker, auto_discover_tags

logger = structlog.get_logger(component="worker")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Worker process")
    parser.add_argument(
        "--type", required=True,
        choices=["download", "cpu", "ai", "gpu"],
        help="Worker type (determines default pools)",
    )
    parser.add_argument("--tags", nargs="*", default=None, help="Capability tags")
    parser.add_argument("--reject-tags", nargs="*", default=None, help="Reject tags")
    parser.add_argument("--pools", nargs="*", default=None, help="Override default pools")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    data_dir = os.environ.get("DATA_DIR", "/data")
    config_dir = os.environ.get("CONFIG_DIR", "/data/configs")

    config = load_config(config_dir=config_dir, data_dir=data_dir)

    redis = RedisClient(redis_url)
    await redis.connect()
    await redis.ping()
    logger.info("redis_connected", url=redis_url)

    db = Database(config.db_path)
    db.init_schema()

    storage = create_storage(config.jobs_dir)
    transport = create_transport(redis, db)

    pools = args.pools or WORKER_POOLS[args.type]
    tags = set(args.tags) if args.tags else auto_discover_tags()
    reject_tags = set(args.reject_tags) if args.reject_tags else set()

    worker = Worker(
        transport=transport, config=config, storage=storage,
        worker_type=args.type, pools=pools,
        tags=tags, reject_tags=reject_tags,
    )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, worker.shutdown)

    try:
        await worker.run()
    finally:
        db.close()
        await redis.close()


if __name__ == "__main__":
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )
    asyncio.run(main())
