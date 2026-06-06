"""StorageBackend：统一文件访问接口。M1 只实现 LocalStorage。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    async def pull(self, job_id: str, step: str) -> Path: ...
    async def push(self, job_id: str, step: str, work_dir: Path) -> None: ...
    async def cleanup(self, job_id: str, step: str, work_dir: Path) -> None: ...


class LocalStorage:
    """本地部署：数据就在本机，pull/push 都是 no-op。"""

    def __init__(self, jobs_dir: Path):
        self.jobs_dir = jobs_dir

    async def pull(self, job_id: str, step: str) -> Path:
        return self.jobs_dir / job_id

    async def push(self, job_id: str, step: str, work_dir: Path) -> None:
        pass

    async def cleanup(self, job_id: str, step: str, work_dir: Path) -> None:
        pass


def create_storage(jobs_dir: Path) -> StorageBackend:
    """工厂函数。根据环境变量选择 backend。"""
    if os.environ.get("MINIO_URL"):
        raise NotImplementedError("RemoteStorage is M4")
    return LocalStorage(jobs_dir)
