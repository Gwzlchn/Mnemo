"""tests for api/routes/profiles.py"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from shared.config import load_config
from shared.db import Database
from api.main import create_app


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
def app(db, test_config):
    return create_app(db=db, redis=AsyncMock(), config=test_config)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _create_profile(prompts_dir, domain, **kwargs):
    profiles_dir = prompts_dir / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    data = {"domain": domain, "role": "test role", "terminology": [], **kwargs}
    (profiles_dir / f"{domain}.yaml").write_text(
        yaml.dump(data, allow_unicode=True), encoding="utf-8"
    )


class TestProfiles:
    @pytest.mark.asyncio
    async def test_list_empty(self, client):
        resp = await client.get("/api/profiles")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_with_profile(self, client, test_config):
        _create_profile(test_config.prompts_dir, "deep-learning", role="分析师")
        resp = await client.get("/api/profiles")
        assert len(resp.json()) == 1
        assert resp.json()[0]["domain"] == "deep-learning"

    @pytest.mark.asyncio
    async def test_get_profile(self, client, test_config):
        _create_profile(test_config.prompts_dir, "ml", role="AI 编辑")
        resp = await client.get("/api/profiles/ml")
        assert resp.status_code == 200
        assert resp.json()["role"] == "AI 编辑"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, client):
        resp = await client.get("/api/profiles/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_profile(self, client, test_config):
        _create_profile(test_config.prompts_dir, "deep-learning")
        resp = await client.put("/api/profiles/deep-learning", json={"role": "新角色"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "新角色"

    @pytest.mark.asyncio
    async def test_create_new_profile(self, client, test_config):
        (test_config.prompts_dir / "profiles").mkdir(exist_ok=True)
        resp = await client.put("/api/profiles/math", json={
            "role": "数学编辑",
            "terminology": ["微积分: calculus"],
        })
        assert resp.status_code == 200
        assert resp.json()["domain"] == "math"

    @pytest.mark.asyncio
    async def test_add_term(self, client, test_config):
        _create_profile(test_config.prompts_dir, "deep-learning", terminology=["注意力: 加权聚合"])
        resp = await client.post("/api/profiles/deep-learning/terms", json={"term": "微调: 下游适配"})
        assert resp.status_code == 200
        assert len(resp.json()["terminology"]) == 2

    @pytest.mark.asyncio
    async def test_add_duplicate_term(self, client, test_config):
        _create_profile(test_config.prompts_dir, "deep-learning", terminology=["注意力: 加权聚合"])
        resp = await client.post("/api/profiles/deep-learning/terms", json={"term": "注意力: 加权聚合"})
        assert len(resp.json()["terminology"]) == 1

    @pytest.mark.asyncio
    async def test_delete_term(self, client, test_config):
        _create_profile(test_config.prompts_dir, "deep-learning", terminology=["注意力: 加权聚合", "微调: 下游适配"])
        resp = await client.delete("/api/profiles/deep-learning/terms/注意力: 加权聚合")
        assert resp.status_code == 200
        assert len(resp.json()["terminology"]) == 1


class TestDomainValidation:
    @pytest.mark.asyncio
    async def test_domain_path_traversal_rejected(self, client):
        resp = await client.get("/api/profiles/..%2F..%2Fetc%2Fpasswd")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.asyncio
    async def test_domain_with_slash_rejected(self, client):
        resp = await client.get("/api/profiles/test/../secrets")
        assert resp.status_code in (400, 404, 422)
