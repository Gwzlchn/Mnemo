"""tests for steps/video/step_05_danmaku.py"""

import json

import pytest

from steps.video.step_05_danmaku import DanmakuStep
from tests.steps.conftest import make_step_config

ASS_CONTENT = """\
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:05.00,0:00:07.00,Default,,0,0,0,,Hello
Dialogue: 0,0:00:02.00,0:00:04.00,Default,,0,0,0,,World
Dialogue: 0,0:00:10.00,0:00:12.00,Default,,0,0,0,,{\\move(1,2,3,4)}filtered
"""


class TestDanmakuStep:
    def _make(self, job_dir, tmp_path):
        config = make_step_config(tmp_path, step_name="05_danmaku", pool="io")
        return DanmakuStep("05_danmaku", job_dir, config)

    def test_validate_missing(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        (job_dir / "input").mkdir()
        step = self._make(job_dir, tmp_path)
        assert step.validate_inputs() == ["input/*.ass"]

    def test_execute(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate"]:
            (job_dir / d).mkdir()
        (job_dir / "input" / "danmaku.ass").write_text(ASS_CONTENT)

        step = self._make(job_dir, tmp_path)
        result = step.execute()
        assert result["comments"] == 2

        danmaku = json.loads((job_dir / "intermediate" / "danmaku.json").read_text())
        assert len(danmaku) == 2
        assert danmaku[0]["time_sec"] == 2.0
        assert danmaku[0]["text"] == "World"

    def test_idempotent(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate"]:
            (job_dir / d).mkdir()
        (job_dir / "input" / "danmaku.ass").write_text(ASS_CONTENT)

        step = self._make(job_dir, tmp_path)
        step.execute()
        step.mark_done()
        step2 = self._make(job_dir, tmp_path)
        assert step2.should_run() is False
