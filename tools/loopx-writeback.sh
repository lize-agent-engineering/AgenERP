#!/usr/bin/env bash
# LoopX 写回闸（D-6 分层契约的执行面）
#
# 用法：tools/loopx-writeback.sh <mission> <todo-id>
#
# 分层（写死，别越界）：
#   · LoopX        拥有 **WBS 项级 / 跨会话** 状态：一个 todo = 一个 mission run 或一个人工项
#   · mission-driver 拥有 **mission 内** 执行状态：plan 步骤、门禁、重试
#   · 写回**单向**：mission 的退出码由本脚本写回 LoopX，**不经 AI 转述**
#
# 为什么要这个脚本而不是让 AI 自己调 loopx：
#   AI 调 loopx 就等于让被考核者填成绩单。本脚本只搬运退出码，不解释、不加工。
#   LoopX 那侧还会自己复跑 todo 的 --validation-command —— 两道都不信自报。
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MISSION="${1:?用法: tools/loopx-writeback.sh <mission> <todo-id> [传给引擎的额外参数...]}"
TODO_ID="${2:?用法: tools/loopx-writeback.sh <mission> <todo-id> [传给引擎的额外参数...]}"
shift 2
GOAL_ID="${LOOPX_GOAL_ID:-agenerp-goal}"

# loopx 未必在 PATH 上（pip --user 装的 console script）
LOOPX="${LOOPX_BIN:-$(command -v loopx || echo "$HOME/Library/Python/3.12/bin/loopx")}"
[ -x "$LOOPX" ] || { echo "找不到 loopx（设 LOOPX_BIN 指定）：$LOOPX" >&2; exit 3; }

# 0. 配额闸：撞限流窗口是常态不是故障，该等就等，别硬冲
DECISION=$("$LOOPX" --format json quota should-run --goal-id "$GOAL_ID" --agent-id "${LOOPX_AGENT_ID:-supervisor-a}" 2>/dev/null \
  | python3 -c 'import json,sys;print(json.load(sys.stdin).get("decision","unknown"))' 2>/dev/null || echo unknown)
echo "[writeback] quota decision = $DECISION"
if [ "$DECISION" != "run" ]; then
  echo "[writeback] 配额未放行，本轮不启动（这不是故障）"
  exit 0
fi

# 1. 跑 mission（停机闸在 shim 里，撞了会直接退 2）
./tools/mission-driver.sh "$MISSION" "$@"
CODE=$?
echo "[writeback] mission '$MISSION' 退出码 = $CODE"

# 2. 按退出码写回，措辞只描述事实
case "$CODE" in
  0)
    # 完成请求交给 LoopX —— 它会自己复跑该 todo 的 validation-command，
    # 校验不过就会拒收，这里不做任何"应该能过"的辩解。
    "$LOOPX" --format json todo complete --goal-id "$GOAL_ID" --todo-id "$TODO_ID" \
      --evidence "mission $MISSION 退出码 0（由 tools/loopx-writeback.sh 直接搬运，未经 AI 转述）" \
      > /tmp/loopx-writeback.json 2>&1
    python3 - <<'PY'
import json
try:
    d = json.load(open("/tmp/loopx-writeback.json"))
except Exception:
    print("[writeback] LoopX 响应无法解析，视为未接受"); raise SystemExit(0)
v = d.get("validation") or {}
print(f"[writeback] LoopX 接受 = {d.get('ok')}  校验退出码 = {v.get('exit_code')}  passed = {v.get('passed')}")
if d.get("ok") is not True:
    print("[writeback] 未被接受：该工作项自己的校验命令没过 —— mission 退 0 不等于工作项完成")
PY
    ;;
  2)
    "$LOOPX" todo update --goal-id "$GOAL_ID" --todo-id "$TODO_ID" --status blocked \
      --reason "mission 退出码 2：撞停机条件（见 .mission-halt.json / STATE §3）" >/dev/null
    echo "[writeback] 已标 blocked —— 停机需人处置，循环不会自行重启"
    ;;
  *)
    "$LOOPX" todo update --goal-id "$GOAL_ID" --todo-id "$TODO_ID" --status open \
      --note "mission 退出码 $CODE：未完成，保持 open 待下轮" >/dev/null
    echo "[writeback] 保持 open"
    ;;
esac
exit "$CODE"
