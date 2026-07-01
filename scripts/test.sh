#!/usr/bin/env bash
# Flori 测试【唯一入口】—— 所有 agent / 会话统一走此脚本,别再各写 `docker compose run …`。
# 权威规约见 CLAUDE.md §测试规约。全容器内跑(宿主不装依赖)。
#
# 用【常驻热测试容器】flori-test-warm(docker-compose.test.yml 已挂源码 → 改代码即时生效),
# 消除每次 `run --rm` 的容器启停税。首次自动建镜像 + 起热容器。
#
# 用法:
#   scripts/test.sh -m <module> [-m <module2> …]   # 只跑相关模块(默认本地快测):tests/test_<module>*.py
#   scripts/test.sh --changed [-m <module>]        # 只跑受本次改动影响的用例(pytest-testmon,迭代秒级)
#   scripts/test.sh --all                          # 全量 + 覆盖率门 75%(对齐 CI)
#   scripts/test.sh --fe [vitest 参数…]            # 前端 vitest
#   scripts/test.sh -- <裸 pytest 参数…>           # 透传任意 pytest 参数(高级)
#   scripts/test.sh --rebuild                      # 改了 pyproject [test] 依赖后重建测试镜像
#   scripts/test.sh --down                         # 停/删热容器
#   scripts/test.sh                                # 打本帮助
#
# 标准 flags(烤死,勿在调用处另写):-p no:cacheprovider  -m 'not fuzz'  -n auto。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"                       # 让 tests/test_*.py glob 相对 worktree 展开(与容器内 /app/tests 同路径)
COMPOSE="$REPO/docker-compose.test.yml"
FE_COMPOSE="$REPO/docker-compose.fe-test.yml"
WARM="flori-test-warm"
IMAGE="flori-test:latest"

usage() { sed -n '2,20p' "$0" | sed 's/^#\{1,\} \{0,1\}//; s/^#$//'; exit "${1:-0}"; }

ensure_warm() {
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo ">> 建测试镜像(首次)…" >&2
    docker compose -f "$COMPOSE" build test
  fi
  if [ -z "$(docker ps -q -f "name=^${WARM}$" 2>/dev/null)" ]; then
    docker rm -f "$WARM" >/dev/null 2>&1 || true          # 清已停的同名残留
    echo ">> 起热测试容器 $WARM(源码挂载,常驻;下次复用)…" >&2
    docker compose -f "$COMPOSE" run -d --name "$WARM" --entrypoint sh test -c 'sleep infinity' >/dev/null
  fi
}

# ── 参数解析 ──
[ $# -eq 0 ] && usage 0
MODE="fast"; CHANGED=0; MODULES=(); RAW=()
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage 0 ;;
    --down) docker rm -f "$WARM" >/dev/null 2>&1 && echo ">> 已删热容器 $WARM" || echo ">> 无热容器"; exit 0 ;;
    --rebuild) docker rm -f "$WARM" >/dev/null 2>&1 || true; docker compose -f "$COMPOSE" build test; echo ">> 已重建测试镜像(改了 [test] 依赖后用)"; shift ;;
    --fe)   shift; exec docker compose -f "$FE_COMPOSE" run --rm fe-test "$@" ;;
    --all)  MODE="all"; shift ;;
    --changed) CHANGED=1; shift ;;
    -m)     shift; [ $# -gt 0 ] || usage 1; MODULES+=("$1"); shift ;;
    --)     shift; RAW=("$@"); break ;;
    *)      echo "未知参数: $1" >&2; usage 1 ;;
  esac
done

# ── 组装 pytest 参数 ──
ARGS=(pytest -p no:cacheprovider -m 'not fuzz')
if [ "$CHANGED" -eq 1 ]; then
  ARGS+=(--testmon)                    # 只跑受改动影响用例;与 xdist 同用易冲突 → 走单进程(子集小,够快)
else
  ARGS+=(-n auto)                      # 多进程并行
fi
if [ "$MODE" = "all" ]; then
  ARGS+=(--cov=shared --cov=api --cov=scheduler --cov=worker --cov=steps
         --cov-branch --cov-report=term-missing --cov-fail-under=75)
fi
for mod in "${MODULES[@]}"; do
  ARGS+=(tests/test_"${mod}"*.py)      # host glob(cd $REPO)→ 展开成实文件,与容器 /app/tests 对齐
done
[ ${#RAW[@]} -gt 0 ] && ARGS+=("${RAW[@]}")

ensure_warm
echo ">> docker exec $WARM ${ARGS[*]}" >&2
exec docker exec "$WARM" "${ARGS[@]}"
