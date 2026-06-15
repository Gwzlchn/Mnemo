"""tests for api/routes/subscriptions.py — 订阅 CRUD + 同步(枚举 mock)。"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from shared.config import load_config
from shared.db import Database
from shared.models import Job, Subscription, generate_id
from api.main import create_app


@pytest.fixture
def test_config(tmp_path, configs_dir):
    cfg = load_config(config_dir=configs_dir, data_dir=tmp_path)
    cfg.jobs_dir = tmp_path / "jobs"; cfg.jobs_dir.mkdir()
    cfg.prompts_dir = tmp_path / "prompts"; cfg.prompts_dir.mkdir()
    return cfg


@pytest.fixture
def db(test_config):
    d = Database(test_config.db_path); d.init_schema()
    yield d; d.close()


@pytest.fixture
def app(db, test_config):
    return create_app(db=db, redis=AsyncMock(), config=test_config)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestSubscriptionDB:
    def test_crud(self, db):
        sub = Subscription(id="sub_1", source_type="bilibili_up", source_id="123", name="UP")
        db.create_subscription(sub)
        assert db.get_subscription("sub_1").source_id == "123"
        assert db.find_subscription("bilibili_up", "123").id == "sub_1"
        db.update_subscription("sub_1", enabled=False)
        assert db.get_subscription("sub_1").enabled is False
        assert len(db.list_subscriptions()) == 1
        assert len(db.list_subscriptions(enabled_only=True)) == 0
        db.delete_subscription("sub_1")
        assert db.get_subscription("sub_1") is None

    def test_ingested_bvids(self, db):
        db.create_job(Job(id="j1", content_type="video", pipeline="video",
                          url="https://www.bilibili.com/video/BV1hT7k6JEq7"))
        db.create_job(Job(id="j2", content_type="article", pipeline="article",
                          url="https://example.com/x"))
        assert db.ingested_bvids() == {"BV1hT7k6JEq7"}


class TestSubscriptionAPI:
    @pytest.mark.asyncio
    async def test_create_syncs_and_dedups(self, client, app, monkeypatch):
        # 已入库一个 BV → 同步时应跳过
        app.state.db.create_job(Job(id="j0", content_type="video", pipeline="video",
                                    url="https://www.bilibili.com/video/BV1old000000"))

        async def fake_enum(mid, cookies=None):
            return [
                {"bvid": "BV1old000000", "title": "已入库", "duration": "1:00"},
                {"bvid": "BV1new111111", "title": "新1", "duration": "2:00"},
                {"bvid": "BV1new222222", "title": "新2", "duration": "3:00"},
            ]
        monkeypatch.setattr("shared.bili_space.enumerate_up", fake_enum)

        resp = await client.post("/api/subscriptions", json={"source_id": "247209804", "sync_now": True})
        assert resp.status_code == 201
        data = resp.json()
        assert data["sync"]["total"] == 3
        assert data["sync"]["new"] == 2     # 跳过已入库的 1 个
        assert data["sync"]["skipped"] == 1
        # 订阅 + 自动建的集合
        sub = data["subscription"]
        assert sub["source_id"] == "247209804" and sub["collection_id"]
        # 新视频已建 job 且绑定集合
        jobs = (await client.get(f"/api/jobs?collection_id={sub['collection_id']}")).json()
        assert jobs["total"] == 2

    @pytest.mark.asyncio
    async def test_duplicate_subscription_rejected(self, client, monkeypatch):
        async def fake_enum(mid, cookies=None):
            return []
        monkeypatch.setattr("shared.bili_space.enumerate_up", fake_enum)
        await client.post("/api/subscriptions", json={"source_id": "999", "sync_now": False})
        resp = await client.post("/api/subscriptions", json={"source_id": "999", "sync_now": False})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_now_endpoint(self, client, app, monkeypatch):
        calls = {"n": 0}
        async def fake_enum(mid, cookies=None):
            calls["n"] += 1
            return [{"bvid": "BV1aaaaaaaaa", "title": "x", "duration": "1:00"}]
        monkeypatch.setattr("shared.bili_space.enumerate_up", fake_enum)
        sub_id = (await client.post("/api/subscriptions", json={"source_id": "555", "sync_now": False})).json()["subscription"]["id"]
        resp = await client.post(f"/api/subscriptions/{sub_id}/sync")
        assert resp.status_code == 200 and resp.json()["new"] == 1
