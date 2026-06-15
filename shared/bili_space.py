"""B站 UP 主空间视频枚举。用 bilibili-api(内置 wbi 签名/buvid/ticket,解 -352 风控)。

凭证取自 DB app_credentials.bili_cookies(扫码登录入库的 SESSDATA/bili_jct/buvid3);
未登录也可枚举公开投稿,但带登录态更稳、清晰度更高。
"""

from __future__ import annotations

import json


def _credential(bili_cookies_raw: str | None):
    from bilibili_api import Credential
    if not bili_cookies_raw:
        return None
    try:
        d = json.loads(bili_cookies_raw)
    except (ValueError, TypeError):
        return None
    return Credential(
        sessdata=d.get("SESSDATA"),
        bili_jct=d.get("bili_jct"),
        dedeuserid=str(d.get("DedeUserID", "")) or None,
        buvid3=d.get("buvid3"),
    )


async def enumerate_up(mid: str, bili_cookies_raw: str | None = None) -> list[dict]:
    """列出某 UP 全部投稿(按发布时间倒序)。返回 [{bvid,title,duration,pic,created}]。"""
    import asyncio
    from bilibili_api import user

    cred = _credential(bili_cookies_raw)
    u = user.User(int(mid), credential=cred)
    out: list[dict] = []
    pn = 1
    while True:
        res = await u.get_videos(pn=pn, ps=50, order=user.VideoOrder.PUBDATE)
        vlist = res.get("list", {}).get("vlist", [])
        for v in vlist:
            out.append({
                "bvid": v["bvid"],
                "title": v.get("title", ""),
                "duration": v.get("length", ""),
                "pic": v.get("pic", ""),
                "created": v.get("created"),
            })
        total = res.get("page", {}).get("count", 0)
        if len(out) >= total or not vlist:
            break
        pn += 1
        await asyncio.sleep(1)  # 翻页间隔,降风控触发
    return out
