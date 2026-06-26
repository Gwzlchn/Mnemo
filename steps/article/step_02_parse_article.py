"""Step 02: 文章解析。trafilatura 抽正文 + 元数据;v2 补全元信息(abstract/image/tags/author)
+ 产出可读原文 Markdown(output/original.md,正文图片下载到 assets/ 本地引用)。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from shared.step_base import StepBase, file_hash


class ParseArticleStep(StepBase):
    def validate_inputs(self) -> list[str]:
        if not (self.job_dir / "input" / "source.html").exists():
            return ["input/source.html"]
        return []

    def input_hashes(self) -> dict[str, str]:
        return {"html": file_hash(self.job_dir / "input" / "source.html")}

    def execute(self) -> dict | None:
        import trafilatura

        html = (self.job_dir / "input" / "source.html").read_text(encoding="utf-8")

        extracted = trafilatura.extract(
            html, output_format="json", with_metadata=True,
            include_comments=False, include_tables=True,
        )

        title = authors_src = date = text = ""
        abstract = image = ""
        tags: list[str] = []
        authors: list[str] = []
        if extracted:
            data = json.loads(extracted)
            title = (data.get("title") or "").strip()
            text = (data.get("text") or "").strip()
            date = (data.get("date") or "").strip()
            abstract = (data.get("description") or data.get("excerpt") or "").strip()  # v2
            image = (data.get("image") or "").strip()                                  # v2
            # 站点通用占位图(如 wscn 的 _static/share.png、logo、default)不是文章实际配图,丢弃。
            if image and re.search(r'(share|/_static/|/static/|logo|default|placeholder)', image.lower()):
                image = ""
            tags = self._split_tags(data.get("tags") or data.get("categories"))        # v2
            authors_src = data.get("author") or ""
            if authors_src:
                authors = [a.strip() for a in str(authors_src).split(";") if a.strip()]

        if not text:
            text = (trafilatura.extract(html, include_comments=False) or "").strip()

        meta = self._load_meta()
        title = title or (meta.get("title") or "").strip()
        date = date or (meta.get("date") or "").strip()
        if not authors and meta.get("author"):
            authors = [a.strip() for a in str(meta["author"]).split(";") if a.strip()]
        # v2:author 仍空 → ① ld+json 兜底 ② 页面内嵌 JSON 的 author 对象兜底
        # (华尔街见闻等 SPA:"author":{...,"display_name":"李丹",...})。
        if not authors:
            authors = self._authors_from_jsonld(html)
        if not authors:
            authors = self._authors_from_page_json(html)

        sections = []
        if text:
            sections.append({"level": 1, "title": title or "正文", "page": 1, "text": text})

        parsed = {
            "title": title,
            "authors": authors,
            "abstract": abstract,                      # v2:补全
            "image": image,                            # v2:封面/配图
            "tags": tags,                              # v2:标签/分类
            "url": meta.get("url", ""),
            "sitename": meta.get("sitename", ""),
            "date": date,
            "word_count": len(text),
            "sections": sections,
            "text": text,
        }
        self.write_output("intermediate/parsed.json", parsed)

        # v2:可读原文 Markdown(图片下载到 assets/ 改本地引用),供前端「原文」tab。
        md, img_count = self._original_markdown(html, parsed)
        self.write_output("output/original.md", md)

        return {"chars": len(text), "title": title, "images": img_count,
                "abstract": bool(abstract), "tags": len(tags)}

    # ── helpers ──

    @staticmethod
    def _split_tags(raw) -> list[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(t).strip() for t in raw if str(t).strip()]
        return [t.strip() for t in re.split(r"[;,，、]", str(raw)) if t.strip()]

    def _authors_from_jsonld(self, html: str) -> list[str]:
        """从 <script type="application/ld+json"> 兜底抽 author.name(best-effort)。"""
        out: list[str] = []
        for m in re.finditer(
            r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I
        ):
            try:
                obj = json.loads(m.group(1).strip())
            except (json.JSONDecodeError, ValueError):
                continue
            for node in (obj if isinstance(obj, list) else [obj]):
                a = node.get("author") if isinstance(node, dict) else None
                for one in (a if isinstance(a, list) else [a]):
                    if isinstance(one, dict) and one.get("name"):
                        out.append(str(one["name"]).strip())
                    elif isinstance(one, str) and one.strip():
                        out.append(one.strip())
            if out:
                break
        # 去重保序
        seen, dedup = set(), []
        for a in out:
            if a not in seen:
                seen.add(a); dedup.append(a)
        return dedup

    def _authors_from_page_json(self, html: str) -> list[str]:
        """SPA 页面内嵌 JSON 的 author 兜底:"author":{...,"display_name":"..."} 或 "name":"..."。
        取首个非空、排除站点/编辑占位。best-effort。"""
        for m in re.finditer(r'"author"\s*:\s*\{(.*?)\}', html, re.S):
            blob = m.group(1)
            nm = re.search(r'"(?:display_name|name)"\s*:\s*"([^"]+)"', blob)
            if nm and nm.group(1).strip():
                return [nm.group(1).strip()]
        return []

    # ── 原文 Markdown + 正文图片(trafilatura 会丢图,故图片从原始 HTML 抽)──

    def _original_markdown(self, html: str, parsed: dict) -> tuple[str, int]:
        """trafilatura 出正文 markdown(纯文本,它会丢图);正文图改从原始 HTML 抽(按尺寸滤),
        下载到 assets/ 后作为「导语图」插在标题后(trafilatura 无图位,无法精确内联)。"""
        import trafilatura
        md = ""
        try:
            md = trafilatura.extract(
                html, output_format="markdown", include_comments=False, include_tables=True,
            ) or ""
        except Exception:
            md = ""
        if not md:
            md = parsed.get("text", "")
        title = parsed.get("title", "")
        # 标题:trafilatura md 常不带 H1,补上
        if title and not md.lstrip().startswith("# "):
            md = f"# {title}\n\n{md}"

        img_md, n = self._download_content_images(html)
        if img_md:
            # 插在第一行标题之后(导语图);无标题则置顶
            lines = md.split("\n", 1)
            if lines and lines[0].startswith("# "):
                md = lines[0] + "\n\n" + img_md + ("\n" + lines[1] if len(lines) > 1 else "")
            else:
                md = img_md + "\n\n" + md
        return md, n

    @staticmethod
    def _content_image_urls(html: str) -> list[str]:
        """从原始 HTML 抽【正文级】图片 URL:滤掉头像/图标/logo/svg、小图(缩略图/相关文章)、
        以及【<a> 链接包裹的图】(促销/广告 banner 几乎都是可点链接,正文图表通常不带链)。
        小图判定:URL 的 w/{N} 或 width={N},或 <img width="{N}">,N<400 视为非正文。"""
        # 链接包裹的 <img>(<a ...><img src=...>)→ 视为广告/促销,排除。
        linked = set(re.findall(
            r'<a\b[^>]*>\s*(?:<[^/a][^>]*>\s*)*<img\b[^>]*\bsrc=["\']([^"\']+)', html, re.I))
        urls: list[str] = []
        seen: set[str] = set()
        for tag in re.findall(r'<img\b[^>]*>', html, re.I):
            src_m = re.search(r'\bsrc=["\']([^"\']+)["\']', tag, re.I)
            if not src_m:
                continue
            src = src_m.group(1).strip()
            if src in linked:
                continue   # <a> 包裹 → 广告/促销 banner
            low = src.lower()
            if src.startswith("data:") or any(
                k in low for k in ("avatar", "/logo", "icon", "sprite", "emoji", ".svg")
            ):
                continue
            w = None
            wm = re.search(r'[/_-]w[/=](\d+)', low) or re.search(r'[?&]width=(\d+)', low)
            if wm:
                w = int(wm.group(1))
            else:
                wa = re.search(r'\bwidth=["\']?(\d+)', tag, re.I)
                if wa:
                    w = int(wa.group(1))
            if w is not None and w < 400:
                continue   # 缩略图/头像/相关文章
            key = src.split("?")[0]   # 同图不同尺寸参数去重
            if key not in seen:
                seen.add(key)
                urls.append(src)
        return urls

    def _download_content_images(self, html: str) -> tuple[str, int]:
        """下载正文图到 assets/img_N.ext,返回 markdown 图片段 + 张数(失败的图跳过)。"""
        import urllib.request
        assets = self.job_dir / "assets"
        refs: list[str] = []
        for i, url in enumerate(self._content_image_urls(html)):
            ext = (re.search(r'\.(png|jpe?g|gif|webp)', url.lower()) or [None, "jpg"])[1]
            ext = "jpg" if ext == "jpeg" else ext
            fname = f"img_{i:02d}.{ext}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=20).read()
                if not data:
                    continue
                assets.mkdir(parents=True, exist_ok=True)
                (assets / fname).write_bytes(data)
                refs.append(f"![](assets/{fname})")
            except Exception:
                continue
        return "\n\n".join(refs), len(refs)

    def _load_meta(self) -> dict:
        path = self.job_dir / "input" / "article_meta.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}


if __name__ == "__main__":
    ParseArticleStep.cli_main("02_parse_article")
