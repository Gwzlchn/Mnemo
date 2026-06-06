"""tests for steps/common/step_00_download.py"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from steps.common.step_00_download import DownloadStep
from tests.steps.conftest import make_step_config


class TestDownloadStep:
    def _make(self, job_dir, tmp_path, url="https://example.com/v.mp4", source=None, content_type="video"):
        job_data = {"url": url, "content_type": content_type}
        if source:
            job_data["source"] = source
        (job_dir / "job.json").write_text(json.dumps(job_data))
        config = make_step_config(tmp_path, step_name="00_download", pool="io")
        return DownloadStep("00_download", job_dir, config)

    def test_validate_inputs_missing(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        config = make_step_config(tmp_path, step_name="00_download")
        step = DownloadStep("00_download", job_dir, config)
        assert step.validate_inputs() == ["job.json"]

    def test_validate_inputs_present(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        (job_dir / "job.json").write_text('{"url": "test"}')
        config = make_step_config(tmp_path, step_name="00_download")
        step = DownloadStep("00_download", job_dir, config)
        assert step.validate_inputs() == []

    def test_source_detection_bilibili(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        step = self._make(job_dir, tmp_path, url="https://www.bilibili.com/video/BV1xx411c7mD")
        with patch.object(step, "_download_bilibili") as mock_dl:
            result = step.execute()
            mock_dl.assert_called_once_with("https://www.bilibili.com/video/BV1xx411c7mD")
            assert result["source"] == "bilibili"

    def test_source_detection_youtube(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        step = self._make(job_dir, tmp_path, url="https://www.youtube.com/watch?v=abc")
        with patch.object(step, "_download_youtube") as mock_dl:
            result = step.execute()
            mock_dl.assert_called_once_with("https://www.youtube.com/watch?v=abc")
            assert result["source"] == "youtube"

    def test_source_detection_arxiv(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        step = self._make(job_dir, tmp_path, url="https://arxiv.org/abs/2301.00001", content_type="paper")
        with patch.object(step, "_download_arxiv") as mock_dl:
            result = step.execute()
            mock_dl.assert_called_once_with("https://arxiv.org/abs/2301.00001")
            assert result["source"] == "arxiv"

    def test_upload_mode_skips_download(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        (job_dir / "input" / "source.mp4").write_bytes(b"\x00" * 1024)
        step = self._make(job_dir, tmp_path, source="upload")
        result = step.execute()
        assert result["source"] == "upload"
        assert (job_dir / "input" / "metadata.json").exists()

    def test_metadata_extraction(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        input_dir = job_dir / "input"
        input_dir.mkdir()
        (input_dir / "source.mp4").write_bytes(b"\x00" * 1048576 * 2)
        (input_dir / "subtitle.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nhi\n")

        config = make_step_config(tmp_path, step_name="00_download")
        step = DownloadStep("00_download", job_dir, config)
        meta = step._extract_metadata("bilibili", "video")
        assert meta["source"] == "bilibili"
        assert meta["has_subtitle"] is True
        assert meta["file_size_mb"] > 0

    def test_idempotent(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        step = self._make(job_dir, tmp_path, source="upload")
        step.execute()
        step.mark_done()
        step2 = self._make(job_dir, tmp_path, source="upload")
        assert step2.should_run() is False

    def test_rename_video_from_job_root(self, tmp_path):
        """yutto may download to job root instead of input/ — rename should find it."""
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        input_dir = job_dir / "input"
        input_dir.mkdir()
        # yutto puts file in job root with video title as name
        (job_dir / "带你躺赢带你飞.mp4").write_bytes(b"\x00" * 2048)

        config = make_step_config(tmp_path, step_name="00_download")
        step = DownloadStep("00_download", job_dir, config)
        step._rename_downloaded_video(input_dir)

        assert (input_dir / "source.mp4").exists()
        assert not (job_dir / "带你躺赢带你飞.mp4").exists()

    def test_rename_danmaku_from_job_root(self, tmp_path):
        """yutto may put .ass in job root — rename should find it."""
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        input_dir = job_dir / "input"
        input_dir.mkdir()
        (job_dir / "video_title.ass").write_text("[Script Info]")

        config = make_step_config(tmp_path, step_name="00_download")
        step = DownloadStep("00_download", job_dir, config)
        step._rename_downloaded_danmaku(input_dir)

        assert (input_dir / "danmaku.ass").exists()
        assert not (job_dir / "video_title.ass").exists()

    def test_rename_subtitle_from_job_root(self, tmp_path):
        """yutto may put .srt in job root — rename should find it."""
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        input_dir = job_dir / "input"
        input_dir.mkdir()
        (job_dir / "video_title.srt").write_text("1\n00:00:01 --> 00:00:02\nhi\n")

        config = make_step_config(tmp_path, step_name="00_download")
        step = DownloadStep("00_download", job_dir, config)
        step._rename_downloaded_subtitle(input_dir)

        assert (input_dir / "subtitle.srt").exists()
        assert not (job_dir / "video_title.srt").exists()
