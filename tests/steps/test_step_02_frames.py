"""tests for steps/video/step_02_frames.py (mock ffmpeg)"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from steps.video.step_02_frames import FramesStep
from tests.steps.conftest import make_step_config


class TestFramesStep:
    def _setup(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "assets"]:
            (job_dir / d).mkdir()
        (job_dir / "input" / "source.mp4").write_bytes(b"\x00" * 2048)
        scenes = [
            {"index": 0, "start_sec": 0.0, "end_sec": 10.0, "duration_sec": 10.0},
            {"index": 1, "start_sec": 10.0, "end_sec": 25.0, "duration_sec": 15.0},
        ]
        (job_dir / "intermediate" / "scenes.json").write_text(json.dumps(scenes))
        return job_dir

    def test_validate_missing(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate"]:
            (job_dir / d).mkdir()
        config = make_step_config(tmp_path, step_name="02_frames")
        step = FramesStep("02_frames", job_dir, config)
        assert len(step.validate_inputs()) == 2

    def test_pick_timestamps_short(self, tmp_path):
        job_dir = self._setup(tmp_path)
        config = make_step_config(tmp_path, step_name="02_frames")
        step = FramesStep("02_frames", job_dir, config)
        ts = step._pick_timestamps(0.0, 10.0, 10.0)
        assert len(ts) == 1
        assert ts[0] == 5.0

    def test_pick_timestamps_long(self, tmp_path):
        job_dir = self._setup(tmp_path)
        config = make_step_config(tmp_path, step_name="02_frames")
        step = FramesStep("02_frames", job_dir, config)
        ts = step._pick_timestamps(0.0, 60.0, 60.0)
        assert len(ts) > 1

    @patch("subprocess.run")
    def test_execute_mock(self, mock_run, tmp_path):
        job_dir = self._setup(tmp_path)
        config = make_step_config(tmp_path, step_name="02_frames", pool="cpu")

        def fake_ffmpeg(*args, **kwargs):
            cmd = args[0]
            output = cmd[-1]
            Path(output).write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 2000)
            return MagicMock(returncode=0)

        from unittest.mock import MagicMock
        mock_run.side_effect = fake_ffmpeg

        step = FramesStep("02_frames", job_dir, config)
        result = step.execute()

        assert result["total"] >= 2
        candidates = json.loads((job_dir / "intermediate" / "candidates.json").read_text())
        assert len(candidates) >= 2
