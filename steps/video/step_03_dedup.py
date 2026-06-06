"""Step 03: 截图去重。pHash 快速筛 → SSIM 精确确认。"""

from __future__ import annotations

import json
from pathlib import Path

from shared.step_base import StepBase, file_hash


class DedupStep(StepBase):
    def validate_inputs(self) -> list[str]:
        missing = []
        if not (self.job_dir / "intermediate" / "candidates.json").exists():
            missing.append("intermediate/candidates.json")
        return missing

    def input_hashes(self) -> dict[str, str]:
        return {
            "candidates": file_hash(self.job_dir / "intermediate" / "candidates.json"),
            "config": json.dumps(self.config.get("domain", {}).get("dedup", {}), sort_keys=True),
        }

    def execute(self) -> dict | None:
        import imagehash
        from PIL import Image

        candidates = self.load_json("intermediate/candidates.json")
        assets_dir = self.job_dir / "assets"

        dedup_cfg = self.config.get("domain", {}).get("dedup", {})
        hash_size = dedup_cfg.get("phash_hash_size", 8)
        phash_threshold = dedup_cfg.get("phash_threshold", 6)
        ssim_threshold = dedup_cfg.get("ssim_threshold", 0.92)
        ssim_resize = tuple(dedup_cfg.get("ssim_resize", [320, 180]))

        results = []
        seen_hashes: list[tuple[imagehash.ImageHash, int]] = []

        for i, cand in enumerate(candidates):
            self.report_progress(i, len(candidates), "deduplicating")
            img_path = assets_dir / cand["filename"]

            if not img_path.exists():
                results.append({**cand, "keep": False, "phash": "", "reason": "missing"})
                continue

            try:
                with Image.open(img_path) as img:
                    ph = imagehash.phash(img, hash_size=hash_size)
            except Exception as e:
                self.log.warning("phash_error", path=str(img_path), error=str(e))
                results.append({**cand, "keep": False, "phash": "", "reason": "error"})
                continue

            duplicate = False
            for prev_hash, prev_idx in seen_hashes:
                if ph - prev_hash <= phash_threshold:
                    if self._ssim_check(img_path, assets_dir / candidates[prev_idx]["filename"],
                                        ssim_threshold, ssim_resize):
                        duplicate = True
                        break

            results.append({**cand, "keep": not duplicate, "phash": str(ph)})
            if not duplicate:
                seen_hashes.append((ph, i))

        self.report_progress(len(candidates), len(candidates), "done")
        self.write_output("intermediate/dedup.json", results)
        kept = sum(1 for r in results if r["keep"])
        return {"total": len(results), "kept": kept, "removed": len(results) - kept}

    def _ssim_check(self, path_a: Path, path_b: Path, threshold: float, resize: tuple) -> bool:
        try:
            import numpy as np
            from PIL import Image
            from skimage.metrics import structural_similarity as ssim

            with Image.open(path_a) as ia, Image.open(path_b) as ib:
                img_a = np.array(ia.convert("L").resize(resize))
                img_b = np.array(ib.convert("L").resize(resize))
            score = ssim(img_a, img_b)
            return score >= threshold
        except Exception as e:
            self.log.warning("ssim_error", path_a=str(path_a), path_b=str(path_b), error=str(e))
            return False


if __name__ == "__main__":
    DedupStep.cli_main("03_dedup")
