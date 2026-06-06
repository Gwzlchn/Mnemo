"""步骤测试公用 fixture。"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def job_dir(tmp_path):
    """创建标准 job 目录结构。"""
    for d in ["input", "intermediate", "output", "assets", "logs"]:
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def step_config(tmp_path):
    """构建最小 step config dict。"""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    return {
        "step": {"name": "test", "pool": "cpu", "timeout_sec": 60, "retries": 0},
        "ai": {},
        "domain": {"name": "general"},
        "style_tags": [],
        "paths": {
            "data_dir": str(tmp_path),
            "prompts_dir": str(prompts_dir),
            "config_dir": str(tmp_path),
        },
        "providers": {},
    }


def make_step_config(tmp_path, step_name="test", pool="cpu", **overrides):
    """构建指定步骤名的 config。"""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    cfg = {
        "step": {"name": step_name, "pool": pool, "timeout_sec": 60, "retries": 0},
        "ai": {},
        "domain": {"name": "general"},
        "style_tags": [],
        "paths": {
            "data_dir": str(tmp_path),
            "prompts_dir": str(prompts_dir),
            "config_dir": str(tmp_path),
        },
        "providers": {},
    }
    cfg.update(overrides)
    return cfg
