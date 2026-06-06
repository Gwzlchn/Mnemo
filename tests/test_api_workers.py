"""tests for api/routes/workers.py"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from shared.config import load_config
from shared.db import Database
from shared.models import Worker
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


def _make_worker(db):
    w = Worker(
        id="cpu-test001",
        type="cpu",
        pools=["cpu", "io"],
        hostname="test-host",
        status="idle",
        first_seen=datetime.now(),
    )
    db.upsert_worker(w)
    return w


class TestWorkers:
    @pytest.mark.asyncio
    async def test_list_empty(self, client):
        resp = await client.get("/api/workers")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_with_worker(self, client, db):
        _make_worker(db)
        resp = await client.get("/api/workers")
        assert len(resp.json()) == 1
        assert resp.json()[0]["id"] == "cpu-test001"

    @pytest.mark.asyncio
    async def test_get_worker(self, client, db):
        _make_worker(db)
        resp = await client.get("/api/workers/cpu-test001")
        assert resp.status_code == 200
        assert resp.json()["hostname"] == "test-host"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, client):
        resp = await client.get("/api/workers/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_worker(self, client, db):
        _make_worker(db)
        resp = await client.put("/api/workers/cpu-test001", json={"status": "draining"})
        assert resp.status_code == 200
        w = db.get_worker("cpu-test001")
        assert w.status == "draining"

    @pytest.mark.asyncio
    async def test_delete_worker(self, client, db):
        _make_worker(db)
        resp = await client.delete("/api/workers/cpu-test001")
        assert resp.status_code == 204
        assert db.get_worker("cpu-test001") is None
