"""公用 test fixtures。"""

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from shared.config import load_config
from shared.db import Database

# 测试环境视为可信本地:默认放行无 token 鉴权(verify_token fail-closed 的逃生口),
# 否则所有命中受保护端点、未设 API_TOKEN 的用例都会 503。需测 fail-closed 的用例自行清此项。
os.environ.setdefault("API_ALLOW_NO_AUTH", "1")


# ── API 测试共用 fixture(此前 13 个 test_api_*.py 各复制一份;G1 上移)──
# 注:app 与 redis mock 仍各文件自定义(redis mock 体随路由而异,G7),conftest 的 client 依赖各文件 app;
# db 被各非 api 测试以本地同名 fixture 覆盖(就近优先),互不影响;test_api_search 自带带 seed 的 db 覆盖。
@pytest.fixture
def test_config(tmp_path, configs_dir):
    cfg = load_config(config_dir=configs_dir, data_dir=tmp_path)
    cfg.jobs_dir = tmp_path / "jobs"
    cfg.jobs_dir.mkdir()
    cfg.prompts_dir = tmp_path / "prompts"
    cfg.prompts_dir.mkdir()
    return cfg


@pytest.fixture
def db(test_config):
    d = Database(test_config.db_path)
    d.init_schema()
    yield d
    d.close()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


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
