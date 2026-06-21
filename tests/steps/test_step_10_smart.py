"""tests for steps/video/step_10_smart.py"""

import json
import os

import pytest

from steps.video.step_10_smart import SmartStep
from tests.steps.conftest import make_step_config


class TestSmartStep:
    def _setup_job(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        for d in ["input", "intermediate", "output", "assets", "logs"]:
            (job_dir / d).mkdir()
        (job_dir / "output" / "notes_mechanical.md").write_text("## 第 1 章\n\n内容\n")
        return job_dir

    def test_validate_inputs(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        (job_dir / "output").mkdir()
        config = make_step_config(tmp_path, step_name="10_smart")
        step = SmartStep("10_smart", job_dir, config)
        assert step.validate_inputs() == ["output/notes_mechanical.md"]

    def test_execute_dry_run(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DRY_RUN", "1")
        job_dir = self._setup_job(tmp_path)
        config = make_step_config(tmp_path, step_name="10_smart", pool="ai")
        step = SmartStep("10_smart", job_dir, config)
        result = step.execute()
        assert result["chars"] > 0
        assert list((job_dir / "output" / "versions").glob("notes_smart_*.md"))

    def test_execute_two_pass_with_images(self, tmp_path):
        # 有截图时走两段:① 带图的视觉 pass(按序号 N 出描述) ② 不带图的纯文本 pass(成稿);
        # 帧从 dedup 清单(非 glob)按 index 选取,图片用 ![](img:N) 占位符,落盘回填成 assets/frame-NNNN.jpg。
        job_dir = self._setup_job(tmp_path)
        (job_dir / "assets" / "frame-0000.jpg").write_bytes(b"\xff\xd8\xff\xe0fakejpg")
        (job_dir / "intermediate" / "dedup.json").write_text(json.dumps(
            [{"index": 0, "filename": "frame-0000.jpg", "timestamp_sec": 1.7,
              "source": "scene", "keep": True}]))
        (job_dir / "intermediate" / "ocr.json").write_text(json.dumps(
            [{"index": 0, "filename": "frame-0000.jpg", "timestamp_sec": 1.7, "text": "分时跳水"}]))
        config = make_step_config(tmp_path, step_name="10_smart", pool="ai")
        step = SmartStep("10_smart", job_dir, config)
        calls = []
        note = ("# 力盛赛车案复盘\n\n![分时跳水图](img:0)\n\n"
                + "## 章节\n这是足够长的正文内容用于通过净化长度判废。\n" * 30)

        def fake_call_ai(prompt, images=None, **kw):
            calls.append({"has_images": bool(images), "prompt": prompt})
            return "0 | 红框圈住分时跳水" if images else note
        step.call_ai = fake_call_ai

        result = step.execute()
        assert len(calls) == 2
        assert calls[0]["has_images"] is True                  # ① 视觉 pass 带图
        assert "不要写任何笔记正文" in calls[0]["prompt"]        # 视觉 pass 只要描述
        assert "[0]" in calls[0]["prompt"]                     # 帧按序号 N 标注
        assert calls[1]["has_images"] is False                 # ② 文本 pass 不带图
        assert "红框圈住分时跳水" in calls[1]["prompt"]          # 视觉描述喂进文本 pass
        assert result["images_sent"] == 1
        # 落盘:占位符 img:0 已回填成真实 assets/ 路径,无裸占位符残留
        written = next((job_dir / "output" / "versions").glob("notes_smart_*.md")).read_text(encoding="utf-8")
        assert "](assets/frame-0000.jpg)" in written
        assert "img:0" not in written

    def test_backfill_image_refs(self):
        # ![](img:N) 占位符:命中 N 回填成 assets/<filename>;未命中(AI 编的/越界)整条删掉。
        out = SmartStep._backfill_image_refs(
            "![甲](img:0) 文字 ![乙](img:9) 尾 ![丙](img:1)",
            {0: "frame-0000.jpg", 1: "frame-0001.jpg"},
        )
        assert "![甲](assets/frame-0000.jpg)" in out
        assert "![丙](assets/frame-0001.jpg)" in out
        assert "img:" not in out          # 占位符全部消解
        assert "![乙]" not in out          # 未命中的 N 整条图片删除

    def test_execute_no_images_single_pass(self, tmp_path):
        # 无截图时只一段纯文本调用。
        job_dir = self._setup_job(tmp_path)
        config = make_step_config(tmp_path, step_name="10_smart", pool="ai")
        step = SmartStep("10_smart", job_dir, config)
        calls = []
        note = "# 标题\n\n" + "## 章节\n足够长的正文内容用于通过净化判废。\n" * 30

        def fake_call_ai(prompt, images=None, **kw):
            calls.append(bool(images)); return note
        step.call_ai = fake_call_ai
        result = step.execute()
        assert calls == [False]                                # 仅一次、不带图
        assert result["images_sent"] == 0

    def test_input_hashes_includes_styles(self, tmp_path):
        job_dir = self._setup_job(tmp_path)
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        (prompts_dir / "10_smart.md").write_text("system prompt")
        profiles_dir = prompts_dir / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "deep-learning.yaml").write_text("role: test\n")
        styles_dir = prompts_dir / "styles"
        styles_dir.mkdir()
        (styles_dir / "lecture.yaml").write_text("tag: lecture\nhints: ['test']\n")

        config = make_step_config(tmp_path, step_name="10_smart", pool="ai")
        config["domain"] = {"name": "deep-learning"}
        config["style_tags"] = ["lecture"]
        config["paths"]["prompts_dir"] = str(prompts_dir)

        step = SmartStep("10_smart", job_dir, config)
        hashes = step.input_hashes()
        assert "prompt" in hashes
        assert "profile" in hashes
        assert "styles" in hashes
        assert "lecture" in hashes["styles"]

    def test_build_prompt_with_profile(self, tmp_path):
        job_dir = self._setup_job(tmp_path)
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        profiles_dir = prompts_dir / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "deep-learning.yaml").write_text(
            "role: 深度学习领域编辑\n"
            "domain_context: 模型架构\n"
            "terminology:\n  - '注意力: 加权聚合'\n"
            "do_not:\n  - '不要编造实验数据'\n"
        )

        config = make_step_config(tmp_path, step_name="10_smart")
        config["domain"] = {"name": "deep-learning"}
        config["paths"]["prompts_dir"] = str(prompts_dir)

        step = SmartStep("10_smart", job_dir, config)
        prompt = step._build_user_prompt("test content")
        assert "模型架构" in prompt
        assert "注意力" in prompt
        assert "不要编造实验数据" in prompt
