"""来源统一注册表(detection 在 source_detect;id 生成在 shared.ids)。

历史上 id 生成与来源注册表都在本文件;现 id 生成(job/collection/worker/lineage)已收敛到
shared.ids(唯一事实源)。本模块保留为兼容再导出层 + detect_source 入口,既有
`from shared.sources import content_job_id / subscription_collection_id / ...` 调用点不破。
"""

from __future__ import annotations

from .source_detect import detect_source, extract_arxiv_id, extract_bilibili_bvid
from .ids import (  # noqa: F401  (兼容再导出:id 生成单一来源在 shared.ids)
    _hash,
    extract_youtube_id,
    lineage_key,
    lineage_key_of,
    content_job_id,
    generate_worker_id,
    generate_collection_id,
    subscription_badge,
    subscription_collection_id,
)

__all__ = [
    "detect_source", "extract_arxiv_id", "extract_bilibili_bvid", "extract_youtube_id",
    "lineage_key", "lineage_key_of", "content_job_id",
    "generate_worker_id", "generate_collection_id",
    "subscription_badge", "subscription_collection_id",
]
