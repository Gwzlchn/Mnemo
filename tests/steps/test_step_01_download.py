"""tests for steps/common/step_01_download.py"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from steps.common.step_01_download import DownloadStep
from tests.steps.conftest import make_step_config


class TestDownloadStep:
    def _make(self, job_dir, tmp_path, url="https://example.com/v.mp4", source=None, content_type="video"):
        job_data = {"url": url, "content_type": content_type}
        if source:
            job_data["source"] = source
        (job_dir / "job.json").write_text(json.dumps(job_data))
        config = make_step_config(tmp_path, step_name="01_download", pool="io")
        return DownloadStep("01_download", job_dir, config)

    def test_validate_inputs_missing(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        config = make_step_config(tmp_path, step_name="01_download")
        step = DownloadStep("01_download", job_dir, config)
        assert step.validate_inputs() == ["job.json"]

    def test_validate_inputs_present(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        (job_dir / "job.json").write_text('{"url": "test"}')
        config = make_step_config(tmp_path, step_name="01_download")
        step = DownloadStep("01_download", job_dir, config)
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

    def test_source_detection_pdf(self, tmp_path):
        # 非 arxiv 直链 PDF(OSDI/usenix 等)→ source=pdf,走 _download_pdf(存 source.pdf)。
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        url = "https://www.usenix.org/system/files/osdi23-li-zhuohan.pdf"
        step = self._make(job_dir, tmp_path, url=url, content_type="paper")
        with patch.object(step, "_download_pdf") as mock_dl:
            result = step.execute()
            mock_dl.assert_called_once_with(url)
            assert result["source"] == "pdf"

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

        config = make_step_config(tmp_path, step_name="01_download")
        step = DownloadStep("01_download", job_dir, config)
        # mock 时长提取:去掉对宿主 ffprobe 的隐式依赖(假 mp4 喂 ffprobe 本就读不出时长),
        # 同时把 duration_sec 这条派生字段钉成确定值。
        with patch.object(step, "_get_video_duration", return_value=42.0):
            meta = step._extract_metadata("bilibili", "video")
        assert meta["source"] == "bilibili"
        assert meta["has_subtitle"] is True
        assert meta["file_size_mb"] > 0
        assert meta["duration_sec"] == 42.0

    _ARXIV_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>BERT: Pre-training of Deep
      Bidirectional Transformers</title>
    <summary>We introduce BERT.</summary>
    <published>2018-10-11T17:08:54Z</published>
    <author><name>Jacob Devlin</name></author>
    <author><name>Ming-Wei Chang</name></author>
  </entry>
</feed>"""

    def test_fetch_arxiv_meta_and_merge(self, tmp_path):
        # arxiv API 元数据解析(标题去换行/作者/摘要/发布日)+ 并入 _extract_metadata(权威,优先 PDF)。
        from types import SimpleNamespace
        job_dir = tmp_path / "job"; job_dir.mkdir(); (job_dir / "input").mkdir()
        step = self._make(job_dir, tmp_path, url="https://arxiv.org/abs/1810.04805", content_type="paper")
        with patch.object(step, "run_subprocess", return_value=SimpleNamespace(stdout=self._ARXIV_ATOM)):
            step._fetch_arxiv_meta("1810.04805")
        m = step._arxiv_meta
        assert m["title"] == "BERT: Pre-training of Deep Bidirectional Transformers"
        assert m["authors"] == ["Jacob Devlin", "Ming-Wei Chang"]
        assert m["abstract"] == "We introduce BERT."
        assert m["published_at"] == "2018-10-11"
        (job_dir / "input" / "source.pdf").write_bytes(b"%PDF-1.4")
        meta = step._extract_metadata("arxiv", "paper")
        assert meta["title"].startswith("BERT") and meta["authors"] == ["Jacob Devlin", "Ming-Wei Chang"]

    def test_fetch_arxiv_meta_failure_is_graceful(self, tmp_path):
        # 网络/解析失败 → 不抛、不 stash;_extract_metadata 正常返回(回退 PDF 解析)。
        job_dir = tmp_path / "job"; job_dir.mkdir(); (job_dir / "input").mkdir()
        step = self._make(job_dir, tmp_path, url="https://arxiv.org/abs/1810.04805", content_type="paper")
        with patch.object(step, "run_subprocess", side_effect=Exception("network down")):
            step._fetch_arxiv_meta("1810.04805")
        assert getattr(step, "_arxiv_meta", {}) == {}
        (job_dir / "input" / "source.pdf").write_bytes(b"%PDF-1.4")
        meta = step._extract_metadata("arxiv", "paper")
        assert "title" not in meta

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

        config = make_step_config(tmp_path, step_name="01_download")
        step = DownloadStep("01_download", job_dir, config)
        step._rename_downloaded_video(input_dir)

        assert (input_dir / "source.mp4").exists()
        assert not (job_dir / "带你躺赢带你飞.mp4").exists()

    def test_prune_danmaku_keeps_one(self, tmp_path):
        """多份 .ass(yutto 同时落 danmaku.ass 与 <标题>.ass)只保留一份 danmaku.ass。"""
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        input_dir = job_dir / "input"
        input_dir.mkdir()
        (input_dir / "video_title.ass").write_text("[Script Info]")
        (input_dir / "danmaku.ass").write_text("[Script Info]")

        config = make_step_config(tmp_path, step_name="01_download")
        step = DownloadStep("01_download", job_dir, config)
        step._prune_subtitles_danmaku(input_dir)

        assert (input_dir / "danmaku.ass").exists()
        assert len(list(input_dir.glob("*.ass"))) == 1

    def test_local_file_copies_pdf(self, tmp_path):
        """file:// url(本地目录订阅)→ 复制宿主文件进 input/source.pdf,跳过网络下载。"""
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        src = tmp_path / "inbox" / "paper.pdf"
        src.parent.mkdir()
        src.write_bytes(b"%PDF-1.4 fake pdf content")

        step = self._make(job_dir, tmp_path, url=f"file://{src}", content_type="paper")
        result = step.execute()

        assert result["source"] == "local"
        copied = job_dir / "input" / "source.pdf"
        assert copied.exists()
        assert copied.read_bytes() == b"%PDF-1.4 fake pdf content"
        assert (job_dir / "input" / "metadata.json").exists()

    def test_local_file_video_runs_verify(self, tmp_path):
        """video 类本地文件复制后走 ffprobe 校验:坏文件(无时长)应被挡。"""
        from shared.errors import InputInvalidError

        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        src = tmp_path / "inbox" / "clip.mp4"
        src.parent.mkdir()
        src.write_bytes(b"\x00" * 16)  # 太小且无时长 → _verify_download 抛错

        step = self._make(job_dir, tmp_path, url=f"file://{src}", content_type="video")
        with pytest.raises(InputInvalidError):
            step.execute()

    def test_local_file_missing_raises(self, tmp_path):
        """file:// 指向不存在的本地文件 → InputInvalidError(不静默成功)。"""
        from shared.errors import InputInvalidError

        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        step = self._make(job_dir, tmp_path,
                          url=f"file://{tmp_path / 'inbox' / 'gone.pdf'}",
                          content_type="paper")
        with pytest.raises(InputInvalidError):
            step.execute()

    def test_local_file_no_network_download_called(self, tmp_path):
        """file:// 分支绝不触发 generic/yt-dlp 网络下载。"""
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        src = tmp_path / "inbox" / "note.txt"
        src.parent.mkdir()
        src.write_text("hello article body")

        step = self._make(job_dir, tmp_path, url=f"file://{src}", content_type="article")
        with patch.object(step, "_download_generic") as mock_generic:
            result = step.execute()
            mock_generic.assert_not_called()
        assert result["source"] == "local"
        assert (job_dir / "input" / "source.txt").read_text() == "hello article body"

    def test_prune_subtitle_keeps_chinese_only(self, tmp_path):
        """原生中文视频:只留中文字幕,删 B 站 AI 翻译的其它语种。"""
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        input_dir = job_dir / "input"
        input_dir.mkdir()
        (input_dir / "video.中文.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\n大家好这是中文字幕内容\n")
        (input_dir / "video.English.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nhello english subtitle\n")

        config = make_step_config(tmp_path, step_name="01_download")
        step = DownloadStep("01_download", job_dir, config)
        step._prune_subtitles_danmaku(input_dir)

        srts = list(input_dir.glob("*.srt"))
        assert len(srts) == 1
        assert srts[0].name == "video.中文.srt"
