"""Step 05: 概念提取 + 一句话摘要(article v2,★必跑)。

有智能笔记则从笔记抽,否则从原文/章节抽;产出 output/concepts.json
({summary, key_terms:[{term,definition}]})供 scheduler._collect_glossary 采集进图谱。
即便关闭智能笔记/评审,本步仍跑 → 概念始终进图谱。"""

from __future__ import annotations

from shared.step_base import StepBase, file_hash


class ArticleConceptsStep(StepBase):
    def validate_inputs(self) -> list[str]:
        if not (self.job_dir / "intermediate" / "sections.json").exists():
            return ["intermediate/sections.json"]
        return []

    def input_hashes(self) -> dict[str, str]:
        hashes: dict[str, str] = {
            "sections": file_hash(self.job_dir / "intermediate" / "sections.json"),
        }
        note = self.latest_smart_note()
        if note:
            hashes["smart"] = file_hash(note)   # 有笔记则随笔记变化重跑
        hashes.update(self.prompt_profile_style_hashes())
        return hashes

    def execute(self) -> dict | None:
        source_text, source = self._source_text()
        prompt = self._build_prompt(source_text)
        result, parse_failed = self.call_ai_json(
            prompt, fallback={"summary": "", "key_terms": []},
        )
        key_terms = result.get("key_terms") or []
        out = {
            "summary": (result.get("summary") or "").strip(),
            "key_terms": key_terms,
            "source": source,            # 'smart_note' | 'original'(概念抽自哪)
            "parse_failed": parse_failed,
        }
        self.write_output("output/concepts.json", out)
        return {"concepts": len(key_terms), "source": source,
                "summary_len": len(out["summary"]), "parse_failed": parse_failed,
                "provider": self.last_ai_provider, "model": self.last_ai_model}

    def _source_text(self) -> tuple[str, str]:
        """决策C:有智能笔记读笔记,否则拼原文章节文本。"""
        note = self.latest_smart_note()
        if note:
            return note.read_text(encoding="utf-8"), "smart_note"
        sections = self.load_json("intermediate/sections.json")
        parts: list[str] = []
        if sections.get("title"):
            parts.append(f"# {sections['title']}\n")
        if sections.get("abstract"):
            parts.append(sections["abstract"] + "\n")
        from steps.utils.sections import render_section_tree
        for sec in sections.get("sections", []):
            render_section_tree(sec, parts, level=2)
        return "".join(parts), "original"

    def _build_prompt(self, text: str) -> str:
        profile = self.load_domain_prompt_profile()
        clip = text[:12000]   # 概念抽取不需全文逐字,限长防超
        parts = [
            "请从以下内容提取【核心概念】并写一句话摘要,严格输出 JSON。\n",
            "要求:\n",
            "- key_terms:文中讲清楚的关键概念(术语),每个给一句简洁中文定义;",
            "英文专有名词原样保留、不翻译。\n",
            "- summary:用一句话(≤60 字)概括全文要点。\n",
            '- 输出格式:{"summary": "...", "key_terms": [{"term": "...", "definition": "..."}]}\n',
            "- 只输出 JSON,不要额外解释或代码块标记。\n",
        ]
        parts.append(self.terminology_block(profile))   # 已沉淀标准概念注入(共用)
        parts.append("\n--- 内容 ---\n")
        parts.append(clip)
        return "".join(parts)


if __name__ == "__main__":
    ArticleConceptsStep.cli_main("05_concepts")
