#!/usr/bin/env bash
# 7×24 监督器 —— 无人值守时唯一还醒着的东西。
#
# 它不做判断，只做调度。每一趟按固定次序过五道闸，任一道说停就停：
#   1. 停机记录在 → 停，且不再重启（清除由人做）
#   2. 日预算超了 → 落停机记录，停
#   3. LoopX 配额说别跑 → 睡一段再问，不硬冲（撞限流窗口是常态不是故障）
#   4. 跑一趟 mission，用量记进台账
#   5. 认证失败 / 红线违规（退 2）→ 停，等人
#
# 设计取向：**宁可停着等人，不可带病连轴转。** 无人值守时没人能纠正它，
# 所以每一道闸都往"停"的方向倒。
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MISSION="${AGENERP_MISSION:-p0-foundation}"
TODO="${AGENERP_TODO:?需要 AGENERP_TODO（LoopX todo id）}"
LOOPX="${LOOPX_BIN:-$HOME/Library/Python/3.12/bin/loopx}"
GOAL_ID="${LOOPX_GOAL_ID:-agenerp-goal}"
AGENT_ID="${LOOPX_AGENT_ID:-supervisor-a}"
QUOTA_WAIT="${AGENERP_QUOTA_WAIT:-1800}"     # 配额不放行时睡多久再问（默认 30 分钟）
PASS_PAUSE="${AGENERP_PASS_PAUSE:-60}"       # 两趟之间的喘息
SNAP="$ROOT/_tmp/session-snapshot.txt"
HALT="$ROOT/.mission-halt.json"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

halt_with() {  # halt_with <condition> <reason>
  python3 - "$HALT" "$1" "$2" "$MISSION" <<'PY'
import json, sys, datetime, pathlib
path, cond, reason, mission = sys.argv[1:5]
pathlib.Path(path).write_text(json.dumps({
    "haltedAt": datetime.datetime.now(datetime.UTC).isoformat(),
    "condition": cond, "reason": reason, "mission": mission,
    "remedy": "处置后删除本文件；监督器会在下次启动时重新放行",
}, ensure_ascii=False, indent=2) + "\n")
PY
  log "停机（$1）：$2"
}

# 自己认领 pidfile —— 两个入口（launchd 与 tools/run-loop.sh supervise）必须共用同一份真相，
# 否则 launchd 起的这个不写 pid，run-loop 就会再起第二个，两个监督器并发跑同一个 mission。
SUPFILE="$ROOT/_tmp/supervisor.pid"
if [ -f "$SUPFILE" ] && kill -0 "$(cat "$SUPFILE")" 2>/dev/null && [ "$(cat "$SUPFILE")" != "$$" ]; then
  log "已有监督器在跑（pid $(cat "$SUPFILE")），本进程退出"
  exit 0
fi
mkdir -p "$ROOT/_tmp"; echo $$ > "$SUPFILE"
trap 'rm -f "$SUPFILE"' EXIT

log "监督器启动 · mission=$MISSION todo=$TODO（pid $$）"

# 若已有一趟在跑（tools/run-loop.sh 起的），等它跑完再接管，别并发
if [ -f "$ROOT/_tmp/loop.pid" ] && kill -0 "$(cat "$ROOT/_tmp/loop.pid")" 2>/dev/null; then
  log "已有一趟在跑（pid $(cat "$ROOT/_tmp/loop.pid")），等它结束"
  while kill -0 "$(cat "$ROOT/_tmp/loop.pid" 2>/dev/null)" 2>/dev/null; do sleep 30; done
  log "上一趟已结束，接管"
fi

while true; do
  # ---- 闸 1：停机记录 ----
  if [ -f "$HALT" ]; then
    log "存在未处置的停机记录，监督器退出（不自动重启，等人）"
    cat "$HALT"
    exit 0
  fi

  # ---- 闸 2：日预算 ----
  python3 tools/gates/check_budget.py
  case $? in
    1) halt_with "budget-exceeded" "24 小时内循环用量超出预算，停机等人复核"; exit 0 ;;
    2) log "预算：台账暂无记录（首趟），放行" ;;
  esac

  # ---- 闸 3：LoopX 配额 ----
  DEC=$("$LOOPX" --format json quota should-run --goal-id "$GOAL_ID" --agent-id "$AGENT_ID" 2>/dev/null \
        | python3 -c 'import json,sys;print(json.load(sys.stdin).get("decision","unknown"))' 2>/dev/null || echo unknown)
  if [ "$DEC" != "run" ]; then
    log "配额未放行（decision=$DEC），睡 ${QUOTA_WAIT}s 再问 —— 撞窗口是常态不是故障"
    sleep "$QUOTA_WAIT"
    continue
  fi

  # ---- 闸 4：跑一趟，并把用量记进台账 ----
  python3 tools/gates/pass_usage.py snapshot "$SNAP"
  log "开跑一趟"
  bash tools/loopx-writeback.sh "$MISSION" "$TODO"
  CODE=$?
  python3 tools/gates/pass_usage.py measure "$SNAP" --label "$MISSION"
  log "本趟退出码 = $CODE"

  # ---- 闸 5：退 2 一律停（红线违规 / 认证过期 / 引擎超限但带停机记录）----
  if [ "$CODE" -eq 2 ]; then
    if [ -f "$HALT" ]; then
      log "撞停机条件，监督器退出等人"
      cat "$HALT"
      exit 0
    fi
    log "退出码 2 但无停机记录（引擎超限终止），继续下一趟"
  fi

  sleep "$PASS_PAUSE"
done
