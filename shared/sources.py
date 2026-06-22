"""来源统一注册表(唯一事实源)。

把此前散落且互相冲突的来源/ID 逻辑收敛到一处:
- detect_source(url→来源,见 source_detect)
- 内容来源 → Job ID 前缀 + 原生 ID 提取(jobs_{前缀}_{原生id})
- 订阅源类型 → 来源徽标 + Collection ID(col_{标签}_{slug})

不再有 `if BV`/`if bilibili_up` 之类特例分支:B 站/YouTube 只是注册表里的普通条目。
ID 仅作主键/URL slug,去重靠 (source_type, source_id) 列,与 ID 无关。
"""

from __future__ import annotations

import hashlib
import re
import secrets

from .source_detect import detect_source, extract_arxiv_id, extract_bilibili_bvid


def _hash(s: str | None) -> str:
    return hashlib.sha1((s or "").encode()).hexdigest()[:10]


def extract_youtube_id(url: str | None) -> str | None:
    """从 YouTube URL 提取 11 位视频 ID(watch?v= / youtu.be/ / shorts / embed)。"""
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else None


# ── 内容来源(单条内容出处)→ Job ID ──
# 平台来源:(job 前缀, 原生 ID 提取器)。原生 ID 可读(bvid/视频id/arxiv id);取不到回退 url 短哈希。
_PLATFORM: dict[str, tuple[str, "callable | None"]] = {
    "bilibili": ("bili", extract_bilibili_bvid),
    "youtube": ("yt", extract_youtube_id),
    "arxiv": ("arxiv", extract_arxiv_id),
    "podcast": ("audio", None),
    "http_article": ("article", None),
}
# 无平台来源(upload/local/other):前缀按内容类型,原生 ID 用 url 短哈希或随机。
_TYPE_PREFIX = {"video": "video", "article": "article", "paper": "paper", "audio": "audio"}


def content_job_id(url: str | None, content_type: str | None = None, source: str | None = None) -> str:
    """Job ID = jobs_{前缀}_{原生id}。前缀按来源(平台)或内容类型(上传/本地);原生 id 取平台稳定 id,
    取不到/无 url 则短哈希/随机。统一规则,无来源特例。"""
    src = source or (detect_source(url) if url else "upload")
    if src in _PLATFORM:
        prefix, extractor = _PLATFORM[src]
        native = (extractor(url) if (extractor and url) else None) or _hash(url)
    else:
        prefix = _TYPE_PREFIX.get(content_type or "", content_type or "x")
        native = _hash(url) if url else secrets.token_hex(4)
    return f"jobs_{prefix}_{native}"


# ── 订阅源类型(feed 种类)→ 来源徽标 + Collection ID ──
def _yt_slug(sid: str) -> str:
    m = (re.search(r"@([A-Za-z0-9._-]+)", sid)
         or re.search(r"(UC[A-Za-z0-9_-]{20,})", sid)
         or re.search(r"/(?:c|user)/([A-Za-z0-9._-]+)", sid))
    return re.sub(r"[^A-Za-z0-9_-]+", "-", m.group(1)).strip("-") if m else _hash(sid)


def _dir_slug(sid: str) -> str:
    base = sid.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"[^A-Za-z0-9_-]+", "-", base).strip("-") or _hash(sid)


def _plain_slug(sid: str) -> str:
    """短而干净(纯数字/短 id)直接用;长串或含 URL → 短哈希。"""
    clean = re.sub(r"[^A-Za-z0-9_-]+", "-", (sid or "").strip()).strip("-")
    return clean if (clean and len(clean) <= 24 and "://" not in (sid or "")) else _hash(sid)


# source_type → (徽标, collection-id 标签, slug 提取器)
_SUBSCRIPTION: dict[str, tuple[str, str, "callable"]] = {
    "bilibili_up": ("bilibili", "bili_up", _plain_slug),
    "bilibili_fav": ("bilibili", "bili_fav", _plain_slug),
    "bilibili_collection": ("bilibili", "bili_col", _plain_slug),
    "youtube_channel": ("youtube", "yt", _yt_slug),
    "rss": ("rss", "rss", _hash),
    "local_dir": ("local", "local", _dir_slug),
}


def subscription_badge(source_type: str) -> str:
    """订阅源类型 → 来源短标签(前端徽标 + 集合显示)。未登记回退 source_type 本身。"""
    e = _SUBSCRIPTION.get(source_type)
    return e[0] if e else source_type


def subscription_collection_id(source_type: str, source_id: str) -> str:
    """Collection ID = col_{标签}_{slug}。统一规则,无来源特例(B站 UP 自然得 col_bili_up_{mid})。"""
    e = _SUBSCRIPTION.get(source_type)
    if e:
        _, label, slug = e
        return f"col_{label}_{slug(source_id)}"
    label = re.sub(r"[^A-Za-z0-9]+", "_", source_type).strip("_")
    return f"col_{label}_{_plain_slug(source_id)}"
