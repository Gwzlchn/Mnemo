"""RSS/Atom feed 抓取 + 解析的薄封装(隔离 feedparser 依赖)。

单独成模块的两个原因:
  1. feedparser 是惰性 import —— shared/subscriptions/rss.py 经
     `from shared import rss_fetch` + `rss_fetch.parse_feed(...)`(模块属性调用)使用,
     适配器模块本身能在没装 feedparser 的环境被 import(注册副作用仍生效);只有真正
     同步 RSS 时才会触发 feedparser import。
  2. 可 mock —— 测试用 `monkeypatch.setattr("shared.rss_fetch.parse_feed", ...)`
     即可替换网络/解析,不联网。与 bili_space.enumerate_up 的模块属性调用约定一致。
"""

from __future__ import annotations


def parse_feed(url: str):
    """抓取并解析一个 RSS/Atom feed,返回 feedparser 的解析结果对象。

    feedparser.parse 既能吃 URL(自己抓取),也能吃 XML 字符串/字节(测试直接喂)。
    本函数透传给它;网络/容错由 feedparser 处理(它不抛异常,失败时 entries 为空、
    bozo 置位)。feedparser 仅在此处 import,缺失时报错信息明确指向 [api] 依赖组。"""
    try:
        import feedparser
    except ImportError as e:  # pragma: no cover - 环境缺依赖时的明确报错
        raise RuntimeError(
            "RSS source-adapter 需要 feedparser:pip install '.[api]'"
        ) from e
    return feedparser.parse(url)
