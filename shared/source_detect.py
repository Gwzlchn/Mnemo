"""URL 来源识别：bilibili / youtube / arxiv / upload / other。

URL 来源识别工具,供 api 与 steps 共用。
"""

from __future__ import annotations

import re


_BILIBILI_PATTERNS = [
    re.compile(r"bilibili\.com"),
    re.compile(r"^BV[a-zA-Z0-9]{10}$"),
    re.compile(r"b23\.tv"),
]

_YOUTUBE_PATTERNS = [
    re.compile(r"youtube\.com"),
    re.compile(r"youtu\.be"),
]

_ARXIV_PATTERNS = [
    re.compile(r"arxiv\.org"),
]

# 音频后缀（含点，小写）单一事实源：URL/enclosure/本地文件以此结尾视作音频。
# rss.py、subscriptions/local_dir.py 均从此导入，避免各写一份导致集合漂移。
AUDIO_SUFFIXES = (".mp3", ".m4a", ".wav", ".aac", ".flac")


def detect_source(url: str) -> str:
    """根据 URL 或标识符判断来源平台。"""
    if not url:
        return "other"

    for pat in _BILIBILI_PATTERNS:
        if pat.search(url):
            return "bilibili"

    for pat in _YOUTUBE_PATTERNS:
        if pat.search(url):
            return "youtube"

    for pat in _ARXIV_PATTERNS:
        if pat.search(url):
            return "arxiv"

    # 音频后缀优先于通用文章:同为 http(s) 链接,音频走播客单集。
    if url.lower().split("?")[0].endswith(AUDIO_SUFFIXES):
        return "podcast"

    # http(s) 且非已知视频/arxiv/音频 → 通用网页文章。
    if re.match(r"https?://", url):
        return "http_article"

    return "other"


def extract_bilibili_bvid(url: str) -> str | None:
    """从 URL 或纯 BV 号提取 BV ID。"""
    m = re.search(r"(BV[a-zA-Z0-9]{10})", url)
    return m.group(1) if m else None


# arXiv ID：新式 2301.00001(可带 vN 版本)或旧式 hep-th/9901001 / math.AG/0601001。
# abs/pdf 路径段可选,裸 ID / 无 abs|pdf 的链接也能提取(保留版本号)。
_ARXIV_ID_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/)?"
    r"(\d+\.\d+(?:v\d+)?|[a-z-]+(?:\.[A-Za-z]{2})?/\d{7}(?:v\d+)?)",
    re.I,
)


def extract_arxiv_id(url: str) -> str | None:
    """从 arXiv URL / 裸 ID 提取论文 ID（新式 2301.00001[vN] 或旧式 hep-th/9901001[vN]）。"""
    m = _ARXIV_ID_RE.search(url or "")
    return m.group(1) if m else None
