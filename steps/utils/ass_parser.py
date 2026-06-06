"""ASS/SSA 弹幕解析。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DanmakuEntry:
    time_sec: float
    text: str


_DIALOGUE_RE = re.compile(
    r"^Dialogue:\s*\d+,"           # layer
    r"(\d+):(\d{2}):(\d{2})\.(\d{2}),"  # start
    r"(\d+):(\d{2}):(\d{2})\.(\d{2}),"  # end
    r"[^,]*,"                      # style
    r"[^,]*,"                      # name
    r"[^,]*,"                      # marginL
    r"[^,]*,"                      # marginR
    r"[^,]*,"                      # marginV
    r"[^,]*,"                      # effect
    r"(.*)",                       # text
    re.IGNORECASE,
)

_EFFECT_TAGS = re.compile(r"\\(?:move|pos|fad|org|clip|an\d)\b")
_ASS_TAGS = re.compile(r"\{[^}]*\}")


def _ts_to_sec(h: str, m: str, s: str, cs: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100


def parse_ass(text: str) -> list[DanmakuEntry]:
    """解析 ASS 弹幕，过滤特效标签，按时间排序。"""
    entries: list[DanmakuEntry] = []

    for line in text.splitlines():
        m = _DIALOGUE_RE.match(line)
        if not m:
            continue

        raw_text = m.group(9)

        if _EFFECT_TAGS.search(raw_text):
            continue

        clean = _ASS_TAGS.sub("", raw_text).replace("\\N", " ").strip()
        if not clean:
            continue

        start = _ts_to_sec(m.group(1), m.group(2), m.group(3), m.group(4))
        entries.append(DanmakuEntry(time_sec=start, text=clean))

    entries.sort(key=lambda e: e.time_sec)
    return entries


def load_ass(path: Path) -> list[DanmakuEntry]:
    """从文件加载 ASS 弹幕。"""
    return parse_ass(path.read_text(encoding="utf-8"))
