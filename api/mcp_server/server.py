"""Flori MCP server(v1)。

借鉴 Notion:单 server 管整库 + 工具少而精(search/fetch 式)+ Markdown 输出省 token。
3 个只读工具薄包 api.services.kb(单一来源);domain 作为作用域参数(非一库一 server)。
检索后端可插拔(默认 FtsSearch;未来换 sqlite-vec 语义,工具签名不变)。
"""

from __future__ import annotations

import os

import structlog
from mcp.server.fastmcp import FastMCP

from api.services import kb
from shared.db import Database
from shared.storage import LocalStorage, StorageBackend

log = structlog.get_logger()


def build_server(
    db: Database,
    storage: StorageBackend,
    search_backend: kb.SearchBackend | None = None,
) -> FastMCP:
    """构造 FastMCP server(可注入 db/storage/检索后端,便于测试与未来替换)。"""
    mcp = FastMCP("flori")
    backend: kb.SearchBackend = search_backend or kb.FtsSearch(db)

    @mcp.tool()
    def list_knowledge_bases() -> list[dict]:
        """列出所有知识库(domain)及其 集合/内容/概念/订阅 计数。

        agent 探索的起点:先用它知道有哪些知识库,再用 search 在某个库里检索。
        """
        res = kb.list_knowledge_bases(db)
        log.info("mcp.list_knowledge_bases", n=len(res))
        return res

    @mcp.tool()
    def search(query: str, domain: str | None = None, limit: int = 10) -> list[dict]:
        """在知识库里全文检索内容/笔记,返回候选列表。

        - domain 可选:限定某个知识库(来自 list_knowledge_bases)。
        - 返回 [{title, snippet, job_id, domain, kind}];snippet 内 <mark> 包裹命中片段。
        - 典型用法:先用本工具按关键词找到候选,再用 get_note(job_id) 取整篇 Markdown。
        - 注意:中文 trigram 检索,查询词至少 3 个字符才会命中。
        """
        try:
            res = backend.search(query, domain, limit)
        except Exception as e:  # noqa: BLE001 — 工具边界,记录后回抛给 client
            log.warning("mcp.search.error", query=query, domain=domain, err=str(e))
            raise
        log.info("mcp.search", query=query, domain=domain, n=len(res))
        return res

    @mcp.tool()
    async def get_note(job_id: str) -> dict:
        """按 job_id 取一篇笔记的完整智能笔记 Markdown + 元信息。

        - job_id 来自 search 的结果。
        - 返回 {job_id, title, domain, collection_id, content_type, status, note_file, markdown}。
        - markdown 为 null 表示该内容的智能笔记尚未生成(如 job 未完成)。
        """
        try:
            res = await kb.get_note(db, storage, job_id)
        except KeyError:
            log.warning("mcp.get_note.not_found", job_id=job_id)
            raise
        log.info("mcp.get_note", job_id=job_id, has_md=bool(res.get("markdown")))
        return res

    return mcp


def build_default_server() -> FastMCP:
    """从环境(CONFIG_DIR/DATA_DIR,默认与容器一致)构造生产用 server(只读)。"""
    from shared.config import load_config

    cfg = load_config(
        config_dir=os.environ.get("CONFIG_DIR", "/data/configs"),
        data_dir=os.environ.get("DATA_DIR", "/data"),
    )
    db = Database(cfg.db_path)
    db.init_schema()  # 幂等:表已存在则 no-op
    storage = LocalStorage(cfg.jobs_dir)
    return build_server(db, storage)
