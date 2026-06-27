"""externalize-prompt:模板文件与代码内 _DEFAULT 常量一致(防漂移)+ _load_prompt_template/template_hash 行为。"""
from __future__ import annotations
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO / "configs" / "prompts" / "templates"


def test_templates_match_constants():
    """每个 templates/*.md 与生成它的代码常量逐字一致 —— 改代码常量必须同步重生成模板,反之亦然。
    跑:python scripts/gen_prompt_templates.py 重生成。"""
    from scripts.gen_prompt_templates import TEMPLATES
    for name, content in TEMPLATES.items():
        f = TEMPLATES_DIR / name
        assert f.exists(), f"模板缺失:{name}(跑 scripts/gen_prompt_templates.py 生成)"
        assert f.read_text(encoding="utf-8") == content, f"模板与常量漂移:{name}"


def test_all_eleven_templates_present():
    from scripts.gen_prompt_templates import TEMPLATES
    assert len(TEMPLATES) == 11
    assert {f.name for f in TEMPLATES_DIR.glob("*.md")} >= set(TEMPLATES)


def _mk_step(tmp_path: Path):
    """构造一个最小 StepBase 实例(只为测 _load_prompt_template/template_hash)。"""
    from shared.step_base import StepBase
    s = StepBase.__new__(StepBase)
    s.config = {"paths": {"prompts_dir": str(tmp_path)}}
    s.step_name = "x"
    return s


def test_load_prompt_template_fallback_to_default(tmp_path):
    s = _mk_step(tmp_path)
    # 模板不存在 → 回退 default(空卷/旧部署兜底)
    assert s._load_prompt_template("nope", "DEFAULT-TEXT") == "DEFAULT-TEXT"


def test_load_prompt_template_reads_file(tmp_path):
    s = _mk_step(tmp_path)
    td = tmp_path / "templates"
    td.mkdir()
    (td / "foo.md").write_text("FROM-FILE <<BODY>>", encoding="utf-8")
    assert s._load_prompt_template("foo", "DEFAULT") == "FROM-FILE <<BODY>>"
    # 占位用 replace 注入(prompt 含字面 {},不可 format)
    assert s._load_prompt_template("foo", "D").replace("<<BODY>>", "X{a}") == "FROM-FILE X{a}"


def test_template_hash_changes_on_edit(tmp_path):
    s = _mk_step(tmp_path)
    td = tmp_path / "templates"
    td.mkdir()
    f = td / "foo.md"
    f.write_text("v1", encoding="utf-8")
    h1 = s.template_hash("foo")
    assert h1  # 非空
    f.write_text("v2", encoding="utf-8")
    assert s.template_hash("foo") != h1  # 改模板 → 指纹变 → should_run 重跑
    assert s.template_hash("absent") == ""  # 全缺 → 空串(不影响指纹)
