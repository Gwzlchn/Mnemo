"""Step 05: 文章笔记质量评审。AI 按维度评分 + 改进建议。"""

from __future__ import annotations

import json

from shared.step_base import StepBase, file_hash


class ArticleReviewStep(StepBase):
    def validate_inputs(self) -> list[str]:
        missing = []
        if self.latest_smart_note() is None:
            missing.append("output/versions/notes_smart_*.md")
        if not (self.job_dir / "intermediate" / "sections.json").exists():
            missing.append("intermediate/sections.json")
        return missing

    def input_hashes(self) -> dict[str, str]:
        return {
            "smart": file_hash(self.latest_smart_note()) if self.latest_smart_note() else "",
            "sections": file_hash(self.job_dir / "intermediate" / "sections.json"),
        }

    def execute(self) -> dict | None:
        smart_clip, coverage, note_file = self.prepare_smart_for_review()
        sections = self.load_json("intermediate/sections.json")

        original_titles = [s["title"] for s in sections.get("sections", [])]

        prompt = (
            "请对以下文章笔记进行质量评审。\n\n"
            "评分维度（每项 1-5 分）：\n"
            "1. completeness: 信息完整性\n"
            "2. accuracy: 准确性\n"
            "3. structure: 结构清晰度\n"
            "4. readability: 可读性\n"
            "5. insight: 观点提炼深度\n\n"
            + self._REVIEW_OUTPUT_EXTRAS +
            "只输出如下扁平 JSON：五个维度为顶层整数键，不要嵌套进 scores 子对象、"
            "不要加 rationale 字段、不要代码围栏、不要任何额外说明文字。\n"
            "{\n"
            '  "completeness": 4, "accuracy": 4, "structure": 4,\n'
            '  "readability": 4, "insight": 4,\n'
            '  "key_terms": [{"term": "概念名", "definition": "一句话候选定义"}],\n'
            '  "missing_concepts": ["遗漏的重要概念"],\n'
            '  "top3_improvements": ["改进建议1", "改进建议2", "改进建议3"]\n'
            "}\n\n"
            f"原文章节：{json.dumps(original_titles, ensure_ascii=False)}\n\n"
            f"--- 笔记 ---\n{smart_clip}"
        )

        review, parse_failed = self.run_dimension_review(
            prompt,
            fallback={
                "completeness": 3, "accuracy": 3, "structure": 3,
                "readability": 3, "insight": 3,
                "overall": 3.0,
                "key_terms": [],
                "missing_concepts": [],
                "top3_improvements": ["AI 返回的不是有效 JSON"],
            },
            score_keys=[
                "completeness", "accuracy", "structure",
                "readability", "insight",
            ],
            note_file=note_file, coverage=coverage,
        )
        return {"overall": review.get("overall", 0), "parse_failed": parse_failed,
                "note_file": note_file, "coverage_truncated": coverage["truncated"]}


if __name__ == "__main__":
    ArticleReviewStep.cli_main("05_review")
