"""tests for api/routes/admin.py"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.main import create_app


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.ping = AsyncMock(return_value=True)
    r.get_pool_count = AsyncMock(return_value=0)
    r.get_queue_info = AsyncMock(return_value={"length": 0})
    r.get_all_pool_limit_overrides = AsyncMock(return_value={})
    r.publish = AsyncMock()
    return r


@pytest.fixture
def app(db, mock_redis, test_config):
    return create_app(db=db, redis=mock_redis, config=test_config)


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_ok(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["checks"]["redis"] == "ok"
        assert data["checks"]["db"] == "ok"

    @pytest.mark.asyncio
    async def test_health_redis_down(self, client, mock_redis):
        mock_redis.ping = AsyncMock(side_effect=Exception("down"))
        resp = await client.get("/api/health")
        data = resp.json()
        assert data["checks"]["redis"] == "error"
        assert data["status"] == "unhealthy"


class TestMetrics:
    @pytest.mark.asyncio
    async def test_metrics_prometheus_text(self, client):
        resp = await client.get("/api/metrics")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")
        body = resp.text
        assert "flori_up 1" in body
        assert "flori_redis_up 1" in body
        assert "flori_db_up 1" in body
        assert "flori_workers_online" in body
        assert "flori_disk_free_gb" in body

    @pytest.mark.asyncio
    async def test_metrics_redis_down_reflected(self, client, mock_redis):
        mock_redis.ping = AsyncMock(side_effect=Exception("down"))
        body = (await client.get("/api/metrics")).text
        assert "flori_redis_up 0" in body


class TestStatus:
    @pytest.mark.asyncio
    async def test_status(self, client):
        resp = await client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        # 空 db + mock redis(pool/queue=0):断具体值,而非只断 key 存在(后者源码返错结构也假绿)。
        assert data["workers"] == {}                       # 无 worker
        assert data["jobs"]["total"] == 0 and data["jobs"]["pending"] == 0
        assert data["pools"] and all(                      # 每个池 used/queue 归零
            p["used"] == 0 and p["queue"] == 0 for p in data["pools"].values())
        assert "available_gb" in data["disk"]


class TestPoolsConfig:
    @pytest.mark.asyncio
    async def test_get_pools(self, client):
        resp = await client.get("/api/config/pools")
        assert resp.status_code == 200
        assert "pools" in resp.json()

    @pytest.mark.asyncio
    async def test_get_pool_limits(self, client):
        resp = await client.get("/api/config/pool-limits")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    @pytest.mark.asyncio
    async def test_put_pool_limit_unknown_400(self, client):
        resp = await client.put("/api/config/pool-limits", json={"no_such_pool": 1})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_put_pool_limit_valid(self, client, mock_redis):
        pools = (await client.get("/api/config/pool-limits")).json()
        pool = next(iter(pools), None)
        if pool:
            resp = await client.put("/api/config/pool-limits", json={pool: 256})
            assert resp.status_code == 200
            mock_redis.set_pool_limit_override.assert_awaited_with(pool, 256)


class TestStylesConfig:
    @pytest.mark.asyncio
    async def test_get_styles_empty_when_no_dir(self, client):
        resp = await client.get("/api/config/styles")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_styles_reads_yaml(self, client, test_config):
        styles_dir = test_config.prompts_dir / "styles"
        styles_dir.mkdir(parents=True, exist_ok=True)
        (styles_dir / "lecture.yaml").write_text("tag: lecture\nname: 课堂\n")
        (styles_dir / "talk.yaml").write_text("name: 演讲\n")  # no tag -> falls back to stem
        resp = await client.get("/api/config/styles")
        assert resp.status_code == 200
        body = resp.json()
        assert "lecture" in body
        assert "talk" in body
