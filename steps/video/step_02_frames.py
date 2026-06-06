"""Step 02: 关键帧提取。每场景取代表帧 + 超长场景保底采样。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from shared.step_base import StepBase, file_hash


class FramesStep(StepBase):
    def validate_inputs(self) -> list[str]:
        missing = []
        if not (self.job_dir / "intermediate" / "scenes.json").exists():
            missing.append("intermediate/scenes.json")
        if not (self.job_dir / "input" / "source.mp4").exists():
            missing.append("input/source.mp4")
        return missing

    def input_hashes(self) -> dict[str, str]:
        return {
            "scenes": file_hash(self.job_dir / "intermediate" / "scenes.json"),
        }

    def execute(self) -> dict | None:
        scenes = self.load_json("intermediate/scenes.json")
        video_path = self.job_dir / "input" / "source.mp4"
        assets_dir = self.job_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        candidates = []
        frame_index = 0

        for i, scene in enumerate(scenes):
            self.report_progress(i, len(scenes), "extracting frames")
            start = scene["start_sec"]
            end = scene["end_sec"]
            duration = end - start

            timestamps = self._pick_timestamps(start, end, duration)
            for ts in timestamps:
                filename = f"scene_{frame_index:04d}_{ts:.1f}s.jpg"
                out_path = assets_dir / filename

                self._extract_frame(video_path, ts, out_path)

                if out_path.exists() and out_path.stat().st_size > 1024:
                    candidates.append({
                        "index": frame_index,
                        "scene_index": i,
                        "timestamp_sec": round(ts, 2),
                        "filename": filename,
                    })
                    frame_index += 1

        self.report_progress(len(scenes), len(scenes), "done")
        self.write_output("intermediate/candidates.json", candidates)
        return {
            "total": len(candidates),
            "scenes": len(scenes),
            "sampled": len(candidates) - len(scenes),
        }

    def _pick_timestamps(self, start: float, end: float, duration: float) -> list[float]:
        if duration <= 0.1:
            return [start]

        if duration <= 30:
            return [start + duration * 0.5]

        ts = [start + duration * 0.7]
        sample_interval = 15.0
        t = start + sample_interval
        while t < end - 1:
            ts.append(t)
            t += sample_interval
        return sorted(set(ts))

    def _extract_frame(self, video_path: Path, timestamp: float, output: Path) -> None:
        try:
            subprocess.run(
                [
                    "ffmpeg", "-ss", str(timestamp),
                    "-i", str(video_path),
                    "-frames:v", "1",
                    "-q:v", "2",
                    "-y", str(output),
                ],
                capture_output=True, timeout=30,
            )
        except subprocess.TimeoutExpired:
            self.log.warn("frame_extract_timeout", timestamp=timestamp)


if __name__ == "__main__":
    FramesStep.cli_main("02_frames")
