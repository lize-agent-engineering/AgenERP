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

# PATH 自愈：已装载的 launchd plist 改不了（改了要 unload/load，等于半路杀掉正在跑的循环），
# 所以每趟开跑前在这里补齐系统标准路径。漏 /usr/local/bin 的代价是实打实的：
# Docker Desktop 的 CLI 软链在那儿，缺了它零依赖启动门禁会以
# `FileNotFoundError: 'docker'` 假红——判据没问题、实现没问题，是环境少了一段 PATH。
# （2026-08-21 迁 launchd 后实测；见 tools/install-loop-agent.sh 的 plist 模板。）
for d in /usr/local/bin /usr/local/sbin; do
  case ":$PATH:" in *":$d:"*) ;; *) PATH="$PATH:$d" ;; esac
done
export PATH

MISSION="${1:?用法: tools/loopx-writeback.sh <mission> <todo-id> [传给引擎的额外参数...]}"
TODO_ID="${2:?用法: tools/loopx-writeback.sh <mission> <todo-id> [传给引擎的额外参数...]}"
shift 2
GOAL_ID="${LOOPX_GOAL_ID:-agenerp-goal}"

# loopx 未必在 PATH 上（pip --user 装的 console script）
LOOPX="${LOOPX_BIN:-$(command -v loopx || echo "$HOME/Library/Python/3.12/bin/loopx")}"
[ -x "$LOOPX" ] || { echo "找不到 loopx（设 LOOPX_BIN 指定）：$LOOPX" >&2; exit 3; }

# 0. 配额闸：撞限流窗口是常态不是故障，该等就等，别硬冲
DECISION=$("$LOOPX" --format json quota should-run --goal-id "$GOAL_ID" --agent-id "${LOOPX_AGENT_ID:-supervisor-a}" 2>/dev/null \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("decision","unknown") if d.get("ok") else "loopx-unavailable")' 2>/dev/null || echo unknown)
# ⚠️ 与 loop-supervisor.sh 同族：`|| echo unknown` 在管道已输出后再追加一行，
#    DECISION 变成 "loopx-unavailable\nunknown"，任何 = 比较都不成立。只取第一行。
DECISION=$(printf '%s' "$DECISION" | head -1 | tr -d "[:space:]")
echo "[writeback] quota decision = $DECISION"
# ⚠️ **CP9 已判 LoopX「停用」**。此时 quota should-run 回 ok:false，decision 取不到，
# 本闸会走进下面那个 `exit 0` —— **看起来成功、实际一趟都没跑**。
# 与 loop-supervisor.sh 闸 3 同一处置：不可用时判为 run 并明写，不是「总是放行」。
if [ "$DECISION" = "loopx-unavailable" ]; then
  echo "[writeback] LoopX 不可用（CP9 已判停用），跳过配额闸 —— 监督器的日预算闸仍在管"
  DECISION=run
fi
if [ "$DECISION" != "run" ]; then
  echo "[writeback] 配额未放行，本轮不启动（这不是故障）"
  exit 0
fi

# 1. 跑 mission（停机闸在 shim 里，撞了会直接退 2）
RUN_LOG="$(mktemp -t agenerp-run)"
./tools/mission-driver.sh "$MISSION" "$@" 2>&1 | tee "$RUN_LOG"
CODE=${PIPESTATUS[0]}
echo "[writeback] mission '$MISSION' 退出码 = $CODE"

# 1b. 认证类失败 → 停机，不是普通失败。
#     实测教训（2026-08-21）：订阅 OAuth 过期时循环 13 秒死在 step 1，
#     而写回闸把它当普通失败保持 open —— 下一轮继续撞，撞到人回来为止。
#     刷新 token 只能由人做，所以这类失败必须停机，不能留给下一轮。
if [ "$CODE" -ne 0 ] && grep -qiE "OAuth session expired|Failed to authenticate|invalid api key|401 unauthorized|authentication_error" "$RUN_LOG"; then
  SIG=$(grep -ioE "OAuth session expired[^\"]*|Failed to authenticate[^\"]*|invalid api key|401 unauthorized|authentication_error" "$RUN_LOG" | head -1)
  python3 - "$ROOT" "$MISSION" "$SIG" <<'PY'
import json, sys, datetime, pathlib
root, mission, sig = sys.argv[1], sys.argv[2], sys.argv[3]
pathlib.Path(root, ".mission-halt.json").write_text(json.dumps({
    "haltedAt": datetime.datetime.now(datetime.UTC).isoformat(),
    "condition": "auth-expired",
    "reason": "执行器认证失败，刷新只能由人完成",
    "signature": sig.strip()[:200],
    "mission": mission,
    "remedy": "在交互式终端执行 claude login，然后删除本文件重启循环",
}, ensure_ascii=False, indent=2) + "\n")
PY
  "$LOOPX" todo update --goal-id "$GOAL_ID" --todo-id "$TODO_ID" --status blocked \
    --reason "执行器认证过期（auth-expired）：需人重新登录，循环已停机" >/dev/null 2>&1
  rm -f "$RUN_LOG"
  echo "[writeback] 认证失败 → 已停机并落 .mission-halt.json（下次启动会被拒绝，直到人处置）"
  exit 2
fi
rm -f "$RUN_LOG"

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
    # 退出码 2 有两种来源，别混：
    #   · 红线停机 → 有 .mission-halt.json，必须人处置
    #   · 引擎的超限终止（maxCycles / maxTotalSteps / pingPong）→ 没有该文件，是正常的边界到顶
    # 首轮实测就踩了这个坑：--max-cycles 2 到顶被当成停机，todo 被误标 blocked。
    if [ -f "$ROOT/.mission-halt.json" ]; then
      "$LOOPX" todo update --goal-id "$GOAL_ID" --todo-id "$TODO_ID" --status blocked \
        --reason "mission 退出码 2：撞红线停机（见 .mission-halt.json / STATE §3）" >/dev/null
      echo "[writeback] 已标 blocked —— 红线停机需人处置，循环不会自行重启"
    else
      "$LOOPX" todo update --goal-id "$GOAL_ID" --todo-id "$TODO_ID" --status open \
        --note "mission 退出码 2：引擎超限终止（cycles/steps 到顶），非红线停机；保持 open 待下轮" >/dev/null
      echo "[writeback] 引擎超限终止（非停机），保持 open"
    fi
    ;;
  *)
    "$LOOPX" todo update --goal-id "$GOAL_ID" --todo-id "$TODO_ID" --status open \
      --note "mission 退出码 $CODE：未完成，保持 open 待下轮" >/dev/null
    echo "[writeback] 保持 open"
    ;;
esac
exit "$CODE"
