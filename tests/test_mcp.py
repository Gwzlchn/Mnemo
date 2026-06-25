"""Flori MCP server 测试:services 读层 + MCP 工具注册/委托。

不 spawn stdio 子进程(进程隔离会脱离内存 fixture DB);MCP 层用 in-process
list_tools/call_tool 验证。trigram 检索需 ≥3 字符,故查询词都取 3+ 字。
"""

from __future__ import annotations

import pytest

from api.mcp_server.server import build_server
from api.services import kb
from shared.models import Collection, Job
from shared.storage import LocalStorage


def _seed(db):
    db.create_collection(
        Collection(id="c1", name="UP", domain="finance",
                   source_type="bilibili_up", source_id="1")
    )
    db.create_job(Job(id="j1", content_type="video", pipeline="video",
                      domain="finance", collection_id="c1", title="庄家坐庄解析"))
    db.create_job(Job(id="j2", content_type="paper", pipeline="paper",
                      domain="deep-learning", title="注意力机制"))
    db.index_job_notes("j1", "smart", "庄家坐庄解析",
                       "讲庄家如何坐庄收割散户的手法", domain="finance", collection_id="c1")
    db.index_job_notes("j2", "smart", "注意力机制",
                       "transformer 注意力机制详解", domain="deep-learning")


class TestKbServices:
    def test_list_knowledge_bases(self, db):
        _seed(db)
        kbs = kb.list_knowledge_bases(db)
        names = {k["domain"] for k in kbs}
        assert {"finance", "deep-learning"} <= names
        fin = next(k for k in kbs if k["domain"] == "finance")
        assert fin["job_count"] == 1 and fin["collection_count"] == 1

    def test_search_hits_and_normalizes(self, db):
        _seed(db)
        res = kb.search(db, "坐庄收割", limit=10)
        assert res and res[0]["job_id"] == "j1"
        assert set(res[0]) == {"title", "snippet", "job_id", "domain", "kind"}
        assert res[0]["domain"] == "finance" and res[0]["kind"] == "smart"

    def test_search_domain_scope(self, db):
        _seed(db)
        assert kb.search(db, "注意力", domain="finance") == []
        assert kb.search(db, "注意力", domain="deep-learning")

    @pytest.mark.asyncio
    async def test_get_note_markdown(self, db, test_config):
        _seed(db)
        storage = LocalStorage(test_config.jobs_dir)
        await storage.write_file(
            "j1", "output/versions/notes_smart_anthropic_opus_20260101-000000.md",
            "# 庄家解析\n正文".encode("utf-8"),
        )
        note = await kb.get_note(db, storage, "j1")
        assert note["job_id"] == "j1" and note["domain"] == "finance"
        assert note["markdown"].startswith("# 庄家解析")
        assert note["note_file"].endswith(".md")

    @pytest.mark.asyncio
    async def test_get_note_missing_md_is_none(self, db, test_config):
        _seed(db)
        storage = LocalStorage(test_config.jobs_dir)
        note = await kb.get_note(db, storage, "j1")
        assert note["markdown"] is None  # 智能笔记未生成

    @pytest.mark.asyncio
    async def test_get_note_unknown_job_raises(self, db, test_config):
        storage = LocalStorage(test_config.jobs_dir)
        with pytest.raises(KeyError):
            await kb.get_note(db, storage, "nope")


class TestMcpServer:
    @pytest.mark.asyncio
    async def test_tools_registered(self, db, test_config):
        mcp = build_server(db, LocalStorage(test_config.jobs_dir))
        names = {t.name for t in await mcp.list_tools()}
        assert names == {"list_knowledge_bases", "search", "get_note"}

    @pytest.mark.asyncio
    async def test_tool_delegates_to_service(self, db, test_config):
        _seed(db)
        mcp = build_server(db, LocalStorage(test_config.jobs_dir))
        result = await mcp.call_tool("search", {"query": "坐庄收割"})
        # FastMCP.call_tool 返回 (content_blocks, structured);命中的 j1 应出现在结果里
        assert result is not None and "j1" in str(result)
