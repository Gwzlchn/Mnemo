"""Step 07: 机械版笔记。按时间线拼接截图+OCR+弹幕+逐字稿。"""

from __future__ import annotations

import json
from pathlib import Path

from shared.step_base import StepBase, file_hash


CHAPTER_INTERVAL_SEC = 180


class MechanicalStep(StepBase):
    def validate_inputs(self) -> list[str]:
        missing = []
        if not (self.job_dir / "intermediate" / "dedup.json").exists():
            missing.append("intermediate/dedup.json")
        if not (self.job_dir / "intermediate" / "ocr.json").exists():
            missing.append("intermediate/ocr.json")
        return missing

    def input_hashes(self) -> dict[str, str]:
        hashes = {
            "dedup": file_hash(self.job_dir / "intermediate" / "dedup.json"),
            "ocr": file_hash(self.job_dir / "intermediate" / "ocr.json"),
        }
        danmaku_path = self.job_dir / "intermediate" / "danmaku.json"
        if danmaku_path.exists():
            hashes["danmaku"] = file_hash(danmaku_path)
        transcript_path = self.job_dir / "output" / "transcript.md"
        if transcript_path.exists():
            hashes["transcript"] = file_hash(transcript_path)
        return hashes

    def execute(self) -> dict | None:
        dedup = self.load_json("intermediate/dedup.json")
        ocr = self.load_json("intermediate/ocr.json")

        danmaku_path = self.job_dir / "intermediate" / "danmaku.json"
        danmaku = json.loads(danmaku_path.read_text()) if danmaku_path.exists() else []

        transcript_path = self.job_dir / "output" / "transcript.md"
        transcript_lines = self._parse_transcript(transcript_path) if transcript_path.exists() else []

        kept_frames = [d for d in dedup if d.get("keep", False)]
        ocr_map = {o["index"]: o for o in ocr}

        events = self._build_timeline(kept_frames, ocr_map, danmaku, transcript_lines)
        md = self._render_markdown(events)

        self.write_output("output/notes_mechanical.md", md)
        return {"frames": len(kept_frames), "events": len(events)}

    def _build_timeline(self, frames, ocr_map, danmaku, transcript_lines):
        events = []

        for frame in frames:
            ts = frame["timestamp_sec"]
            ocr_entry = ocr_map.get(frame["index"], {})
            events.append({
                "time": ts,
                "type": "frame",
                "filename": frame["filename"],
                "ocr_text": ocr_entry.get("text", ""),
            })

        for d in danmaku:
            events.append({
                "time": d["time_sec"],
                "type": "danmaku",
                "text": d["text"],
            })

        for tl in transcript_lines:
            events.append({
                "time": tl["time_sec"],
                "type": "transcript",
                "text": tl["text"],
            })

        events.sort(key=lambda e: e["time"])
        return events

    def _render_markdown(self, events) -> str:
        if not events:
            return "# 机械版笔记\n\n（无内容）\n"

        parts = []
        chapter_idx = 1
        last_chapter_time = -CHAPTER_INTERVAL_SEC

        for event in events:
            ts = event["time"]
            if ts - last_chapter_time >= CHAPTER_INTERVAL_SEC:
                m = int(ts) // 60
                s = int(ts) % 60
                parts.append(f"\n## 第 {chapter_idx} 章 [{m:02d}:{s:02d}]\n")
                chapter_idx += 1
                last_chapter_time = ts

            if event["type"] == "frame":
                parts.append(f"\n![{event['filename']}](assets/{event['filename']})\n")
                ocr_text = event.get("ocr_text", "").strip()
                if ocr_text:
                    parts.append(f"\n> OCR: {ocr_text}\n")

            elif event["type"] == "danmaku":
                parts.append(f"- 💬 {event['text']}\n")

            elif event["type"] == "transcript":
                m = int(ts) // 60
                s = int(ts) % 60
                parts.append(f"[{m:02d}:{s:02d}] {event['text']}\n")

        return "".join(parts)

    def _parse_transcript(self, path: Path) -> list[dict]:
        import re
        lines = []
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"\[(\d{2}):(\d{2})\]\s*(.*)", line)
            if m:
                ts = int(m.group(1)) * 60 + int(m.group(2))
                lines.append({"time_sec": ts, "text": m.group(3)})
        return lines


if __name__ == "__main__":
    MechanicalStep.cli_main("07_mechanical")
