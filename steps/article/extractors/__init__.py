"""文章提取器注册表。

按 matches(url, html) 选站点 extractor,否则 GenericExtractor(trafilatura 通用)兜底。
EXTRACTORS 顺序 = 优先级:具体站点在前,Generic(matches 恒真)在最后兜底。
加新站 = 新建一个 extractor 文件 + 在此 import 并加到 EXTRACTORS 前部,不动通用逻辑。
"""

from __future__ import annotations

from .base import (
    ArticleExtractor,
    GenericExtractor,
    authors_from_jsonld,
    authors_from_page_json,
    generic_content_image_urls,
)
from .substack import SubstackExtractor

EXTRACTORS: list[ArticleExtractor] = [
    SubstackExtractor(),
    GenericExtractor(),   # 兜底,必须最后
]


def pick_extractor(url: str, html: str) -> ArticleExtractor:
    for ex in EXTRACTORS:
        if ex.matches(url or "", html or ""):
            return ex
    return GenericExtractor()


__all__ = [
    "ArticleExtractor",
    "GenericExtractor",
    "SubstackExtractor",
    "EXTRACTORS",
    "pick_extractor",
    "generic_content_image_urls",
    "authors_from_jsonld",
    "authors_from_page_json",
]
