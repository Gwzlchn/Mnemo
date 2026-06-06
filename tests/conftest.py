"""公用 test fixtures。"""

from pathlib import Path

import pytest


@pytest.fixture
def configs_dir():
    """项目根目录的 configs/ 示例配置。"""
    return Path(__file__).parent.parent / "configs"


@pytest.fixture
def tmp_data_dir(tmp_path):
    """临时 data 目录，模拟 /data/。"""
    (tmp_path / "db").mkdir()
    (tmp_path / "jobs").mkdir()
    (tmp_path / "prompts").mkdir()
    return tmp_path
