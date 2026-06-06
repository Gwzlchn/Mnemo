#!/usr/bin/env bash
# 将原型目录产物注入到新系统的 job 目录结构中
# 用法: ./inject_prototype.sh <原型目录> <job_dir>
set -euo pipefail

SRC=${1:?用法: $0 <原型目录> <job_dir>}
DST=${2:?用法: $0 <原型目录> <job_dir>}

mkdir -p "$DST"/{input,intermediate,assets,output}

# 中间产物 → intermediate/
for f in scenes.json candidates.json dedup.json ocr.json danmaku.json; do
  [ -f "$SRC/$f" ] && cp "$SRC/$f" "$DST/intermediate/"
done

# 截图 → assets/
if [ -d "$SRC/frames" ]; then
  cp "$SRC/frames/"*.jpg "$DST/assets/" 2>/dev/null || true
fi

# 最终产物 → output/
[ -f "$SRC/transcript.md" ] && cp "$SRC/transcript.md" "$DST/output/"
[ -f "$SRC/notes_mechanical.md" ] && cp "$SRC/notes_mechanical.md" "$DST/output/"
[ -f "$SRC/notes_smart.md" ] && cp "$SRC/notes_smart.md" "$DST/output/"
[ -f "$SRC/review.json" ] && cp "$SRC/review.json" "$DST/output/"

echo "注入完成:"
echo "  中间文件: $(ls -1 "$DST/intermediate/" 2>/dev/null | wc -l)"
echo "  截图: $(ls -1 "$DST/assets/" 2>/dev/null | wc -l)"
echo "  产出: $(ls -1 "$DST/output/" 2>/dev/null | wc -l)"
