"""内容源订阅(UP 主)路由:CRUD + 立即同步。

同步 = 枚举 UP 全部视频 → 跟已入库去重 → 新视频自动建 job(进订阅绑定的集合)。
周期自动同步见 api/main.py 的后台任务。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from shared.db import Database
from shared.models import Collection, Subscription, generate_id
from shared.redis_client import RedisClient
from shared.storage import StorageBackend
from api.deps import get_db, get_redis, get_storage, verify_token
from api.routes.jobs import create_job_core

logger = structlog.get_logger(component="subscriptions")
router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"],
                   dependencies=[Depends(verify_token)])


class SubscriptionCreate(BaseModel):
    source_id: str                 # B站 mid
    name: str | None = None
    domain: str = "general"
    source_type: str = "bilibili_up"
    sync_now: bool = True


class SubscriptionUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    enabled: bool | None = None


def _to_dict(s: Subscription) -> dict:
    return {
        "id": s.id, "source_type": s.source_type, "source_id": s.source_id,
        "name": s.name, "domain": s.domain, "collection_id": s.collection_id,
        "enabled": s.enabled,
        "last_synced_at": s.last_synced_at.isoformat() if s.last_synced_at else None,
        "created_at": s.created_at.isoformat(),
    }


async def sync_subscription(
    sub: Subscription, db: Database, redis: RedisClient, storage: StorageBackend,
) -> dict:
    """枚举该订阅的 UP 视频 → 去重 → 新视频建 job。返回 {total, new, skipped}。"""
    if sub.source_type != "bilibili_up":
        raise ValueError(f"unsupported source_type: {sub.source_type}")
    from shared.bili_space import enumerate_up

    cookies = await asyncio.to_thread(db.get_credential, "bili_cookies")
    videos = await enumerate_up(sub.source_id, cookies)
    ingested = await asyncio.to_thread(db.ingested_bvids)
    new = [v for v in videos if v["bvid"] not in ingested]

    for v in new:
        await create_job_core(
            db, redis, storage,
            url=f"https://www.bilibili.com/video/{v['bvid']}",
            content_type="video", domain=sub.domain,
            collection_id=sub.collection_id,
        )
        await asyncio.sleep(0.2)  # 轻微间隔,别瞬时灌爆队列/触发风控

    await asyncio.to_thread(
        db.update_subscription, sub.id, last_synced_at=datetime.now(timezone.utc),
    )
    logger.info("subscription_synced", sub=sub.id, total=len(videos), new=len(new))
    return {"total": len(videos), "new": len(new), "skipped": len(videos) - len(new)}


@router.post("", status_code=201)
async def create_subscription(
    req: SubscriptionCreate,
    db: Database = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    storage: StorageBackend = Depends(get_storage),
):
    if await asyncio.to_thread(db.find_subscription, req.source_type, req.source_id):
        raise HTTPException(400, "该订阅已存在")
    # 自动建一个绑定集合(同名),订阅拉到的视频都归入。
    coll = Collection(id=generate_id("c"), name=req.name or f"UP-{req.source_id}",
                      domain=req.domain, description=f"订阅 {req.source_type}:{req.source_id}")
    await asyncio.to_thread(db.create_collection, coll)
    sub = Subscription(
        id=generate_id("sub"), source_type=req.source_type, source_id=req.source_id,
        name=req.name or f"UP-{req.source_id}", domain=req.domain, collection_id=coll.id,
    )
    await asyncio.to_thread(db.create_subscription, sub)
    result = None
    if req.sync_now:
        try:
            result = await sync_subscription(sub, db, redis, storage)
        except Exception as e:
            logger.warning("initial_sync_failed", sub=sub.id, error=str(e)[:200])
            result = {"error": str(e)[:200]}
    return {"subscription": _to_dict(sub), "sync": result}


@router.get("")
async def list_subscriptions(db: Database = Depends(get_db)):
    return {"subscriptions": [_to_dict(s) for s in await asyncio.to_thread(db.list_subscriptions)]}


@router.post("/{sub_id}/sync")
async def trigger_sync(
    sub_id: str,
    db: Database = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    storage: StorageBackend = Depends(get_storage),
):
    sub = await asyncio.to_thread(db.get_subscription, sub_id)
    if not sub:
        raise HTTPException(404, "subscription not found")
    try:
        return await sync_subscription(sub, db, redis, storage)
    except Exception as e:
        raise HTTPException(502, f"同步失败: {str(e)[:200]}")


@router.patch("/{sub_id}")
async def update_subscription(
    sub_id: str, req: SubscriptionUpdate, db: Database = Depends(get_db),
):
    if not await asyncio.to_thread(db.get_subscription, sub_id):
        raise HTTPException(404, "subscription not found")
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    if fields:
        await asyncio.to_thread(db.update_subscription, sub_id, **fields)
    return _to_dict(await asyncio.to_thread(db.get_subscription, sub_id))


@router.delete("/{sub_id}", status_code=204)
async def delete_subscription(sub_id: str, db: Database = Depends(get_db)):
    await asyncio.to_thread(db.delete_subscription, sub_id)
