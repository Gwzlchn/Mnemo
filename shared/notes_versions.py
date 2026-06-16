"""智能笔记版本文件名解析。命名:output/versions/notes_smart_{provider}_{model}_{YYYYMMDD-HHMMSS}.md
(provider/model 内不含 '_',故按 '_' 切分无歧义;version 取生成时间,可排序,最大者为最新)。"""

from __future__ import annotations

import re

# provider/model 段不含下划线(写入时已归一),version 为 YYYYMMDD-HHMMSS。
_SMART_RE = re.compile(r"notes_smart_([^_/]+)_([^_/]+)_(\d{8}-\d{6})\.md$")


def parse_smart_version(rel: str) -> dict | None:
    m = _SMART_RE.search(rel)
    if not m:
        return None
    return {"provider": m.group(1), "model": m.group(2), "version": m.group(3), "file": rel}


def latest_smart(files: list[str]) -> str | None:
    """从文件相对路径列表里挑最新的智能笔记版本(按 version 时间戳)。"""
    cands = [f for f in files if _SMART_RE.search(f)]
    if not cands:
        return None
    return max(cands, key=lambda f: _SMART_RE.search(f).group(3))


def review_path_for_note(note_rel: str) -> str | None:
    """与某版智能笔记 1:1 配对的评审文件路径:notes_smart_X.md → versions/review_X.json。"""
    m = _SMART_RE.search(note_rel)
    if not m:
        return None
    return f"output/versions/review_{m.group(1)}_{m.group(2)}_{m.group(3)}.json"
