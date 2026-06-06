"""tests for steps/video/step_07_mechanical.py"""

import json

import pytest

from steps.video.step_07_mechanical import MechanicalStep
from tests.steps.conftest import make_step_config


class TestMechanicalStep:
    def _setup_job(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets"]:
            (job_dir / d).mkdir()

        dedup = [
            {"index": 0, "scene_index": 0, "timestamp_sec": 5.0, "filename": "scene_0000_5.0s.jpg", "keep": True, "phash": "abc"},
            {"index": 1, "scene_index": 1, "timestamp_sec": 65.0, "filename": "scene_0001_65.0s.jpg", "keep": True, "phash": "def"},
            {"index": 2, "scene_index": 2, "timestamp_sec": 200.0, "filename": "scene_0002_200.0s.jpg", "keep": True, "phash": "ghi"},
        ]
        (job_dir / "intermediate" / "dedup.json").write_text(json.dumps(dedup))

        ocr = [
            {"index": 0, "filename": "scene_0000_5.0s.jpg", "timestamp_sec": 5.0, "text": "Hello", "boxes": []},
            {"index": 1, "filename": "scene_0001_65.0s.jpg", "timestamp_sec": 65.0, "text": "", "boxes": []},
            {"index": 2, "filename": "scene_0002_200.0s.jpg", "timestamp_sec": 200.0, "text": "World", "boxes": []},
        ]
        (job_dir / "intermediate" / "ocr.json").write_text(json.dumps(ocr))

        return job_dir

    def test_execute_minimal(self, tmp_path):
        job_dir = self._setup_job(tmp_path)
        config = make_step_config(tmp_path, step_name="07_mechanical", pool="io")
        step = MechanicalStep("07_mechanical", job_dir, config)
        result = step.execute()

        assert result["frames"] == 3
        md = (job_dir / "output" / "notes_mechanical.md").read_text()
        assert "## 第 1 章" in md
        assert "scene_0000_5.0s.jpg" in md

    def test_with_optional_inputs(self, tmp_path):
        job_dir = self._setup_job(tmp_path)

        danmaku = [{"time_sec": 10.0, "text": "这个推导讲得真清楚"}]
        (job_dir / "intermediate" / "danmaku.json").write_text(json.dumps(danmaku))

        (job_dir / "output" / "transcript.md").write_text("[00:05] 你好\n[01:05] 世界\n")

        config = make_step_config(tmp_path, step_name="07_mechanical", pool="io")
        step = MechanicalStep("07_mechanical", job_dir, config)
        result = step.execute()

        md = (job_dir / "output" / "notes_mechanical.md").read_text()
        assert "这个推导讲得真清楚" in md
        assert "[00:05]" in md

    def test_without_optional_inputs(self, tmp_path):
        job_dir = self._setup_job(tmp_path)
        config = make_step_config(tmp_path, step_name="07_mechanical", pool="io")
        step = MechanicalStep("07_mechanical", job_dir, config)
        result = step.execute()
        assert result["frames"] == 3

    def test_chapter_splitting(self, tmp_path):
        job_dir = self._setup_job(tmp_path)
        config = make_step_config(tmp_path, step_name="07_mechanical", pool="io")
        step = MechanicalStep("07_mechanical", job_dir, config)
        step.execute()

        md = (job_dir / "output" / "notes_mechanical.md").read_text()
        assert "## 第 2 章" in md

    def test_validate_inputs(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        (job_dir / "intermediate").mkdir()
        config = make_step_config(tmp_path, step_name="07_mechanical")
        step = MechanicalStep("07_mechanical", job_dir, config)
        assert "intermediate/dedup.json" in step.validate_inputs()

    def test_idempotent(self, tmp_path):
        job_dir = self._setup_job(tmp_path)
        config = make_step_config(tmp_path, step_name="07_mechanical", pool="io")
        step = MechanicalStep("07_mechanical", job_dir, config)
        step.execute()
        step.mark_done()
        step2 = MechanicalStep("07_mechanical", job_dir, config)
        assert step2.should_run() is False
