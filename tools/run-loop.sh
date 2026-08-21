#!/usr/bin/env bash
# 7×24 启动器 —— 让循环脱离启动它的会话独立存活。
#
# 起因（2026-08-21 实测）：把循环挂在交互会话的后台任务里，会话一退子进程就被杀，
# 第二轮正是这样在跑了一小时后被 [killed]。7×24 的第一个前提是「关掉终端它还活着」。
#
# 用法：
#   tools/run-loop.sh start <mission> <todo-id> [额外参数...]
#   tools/run-loop.sh status
#   tools/run-loop.sh stop
#   tools/run-loop.sh log [行数]
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PIDFILE="$ROOT/_tmp/loop.pid"
LOGFILE="$ROOT/_tmp/loop.log"
mkdir -p "$ROOT/_tmp"

alive() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

case "${1:-status}" in
  start)
    shift
    MISSION="${1:?用法: tools/run-loop.sh start <mission> <todo-id> [额外参数...]}"
    TODO="${2:?用法: tools/run-loop.sh start <mission> <todo-id> [额外参数...]}"
    shift 2
    if alive; then echo "已在运行（pid $(cat "$PIDFILE")）。先 stop 或看 status。"; exit 1; fi
    if [ -f "$ROOT/.mission-halt.json" ]; then
      echo "拒绝启动：存在未处置的停机记录"; cat "$ROOT/.mission-halt.json"; exit 2
    fi
    : > "$LOGFILE"
    # macOS 没有 setsid（实测 command not found）。用 Python 的 start_new_session=True
    # 起一个新会话+新进程组的子进程 —— 语义等同 setsid，且本机一定有 python3。
    # 不这么做的话，父会话退出时整组被杀，7×24 第一天就断（第二轮就是这样死的）。
    LOOPX_BIN="${LOOPX_BIN:-$HOME/Library/Python/3.12/bin/loopx}" \
    python3 - "$ROOT" "$LOGFILE" "$MISSION" "$TODO" "$@" > "$PIDFILE" <<'PY'
import os, subprocess, sys
root, logfile, mission, todo, *extra = sys.argv[1:]
log = open(logfile, "ab", buffering=0)
p = subprocess.Popen(
    ["bash", os.path.join(root, "tools/loopx-writeback.sh"), mission, todo, *extra],
    cwd=root, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
    start_new_session=True,   # ← 关键：新会话，父进程死了也不受牵连
)
print(p.pid)
PY
    sleep 1
    echo "已启动（pid $(cat "$PIDFILE")）· 日志 $LOGFILE"
    echo "看进度：tools/run-loop.sh log    停止：tools/run-loop.sh stop"
    ;;
  status)
    if alive; then
      echo "运行中（pid $(cat "$PIDFILE")）"
      tail -3 "$LOGFILE" 2>/dev/null
    else
      echo "未运行"
      [ -f "$LOGFILE" ] && { echo "--- 最后几行 ---"; tail -5 "$LOGFILE"; }
    fi
    if [ -f "$ROOT/.mission-halt.json" ]; then
      echo "--- 停机记录 ---"; cat "$ROOT/.mission-halt.json"
    fi
    # status 是查询，不该因为「没有停机记录」而返回非 0（会被误读成出问题了）
    exit 0
    ;;
  stop)
    if alive; then
      PID=$(cat "$PIDFILE")
      # 杀整个进程组，否则引擎 spawn 的 claude 子进程会变孤儿
      kill -TERM -"$PID" 2>/dev/null || kill -TERM "$PID" 2>/dev/null
      sleep 2
      alive && kill -KILL -"$PID" 2>/dev/null
      echo "已停止（pid $PID）"
    else
      echo "本来就没在跑"
    fi
    rm -f "$PIDFILE"
    ;;
  log) tail -"${2:-40}" "$LOGFILE" 2>/dev/null || echo "还没有日志" ;;
  *) echo "用法: tools/run-loop.sh {start <mission> <todo-id> [参数...]|status|stop|log [行数]}"; exit 1 ;;
esac
