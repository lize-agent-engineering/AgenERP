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
# 两个 pidfile 必须分开：监督器会检查 loop.pid 判断「有没有单趟在跑」，
# 若把监督器自己的 pid 也写进 loop.pid，它开机就会看见自己、等自己结束 —— 自引用死锁（实测踩过）。
PIDFILE="$ROOT/_tmp/loop.pid"
SUPFILE="$ROOT/_tmp/supervisor.pid"
LOGFILE="$ROOT/_tmp/loop.log"
mkdir -p "$ROOT/_tmp"

alive_f() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }
alive()   { alive_f "$PIDFILE"; }
alive_sup(){ alive_f "$SUPFILE"; }

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
  supervise)
    # 连续模式：起监督器（配额自动续跑 + 日预算闸），而不是单趟。
    # launchd 那条路被 macOS TCC 挡着（仓库在 ~/Documents 下），在那之前用这个。
    shift
    MISSION="${1:?用法: tools/run-loop.sh supervise <mission> <todo-id>}"
    TODO="${2:?用法: tools/run-loop.sh supervise <mission> <todo-id>}"
    if alive_sup; then echo "监督器已在运行（pid $(cat "$SUPFILE")）"; exit 1; fi
    if alive; then echo "有单趟在跑（pid $(cat "$PIDFILE")），等它结束或先 stop"; exit 1; fi
    if [ -f "$ROOT/.mission-halt.json" ]; then
      echo "拒绝启动：存在未处置的停机记录"; cat "$ROOT/.mission-halt.json"; exit 2
    fi
    : > "$LOGFILE"
    AGENERP_MISSION="$MISSION" AGENERP_TODO="$TODO" \
    LOOPX_BIN="${LOOPX_BIN:-$HOME/Library/Python/3.12/bin/loopx}" \
    python3 - "$ROOT" "$LOGFILE" > "$SUPFILE" <<'PY'
import os, subprocess, sys
root, logfile = sys.argv[1:3]
log = open(logfile, "ab", buffering=0)
p = subprocess.Popen(["bash", os.path.join(root, "tools/loop-supervisor.sh")],
                     cwd=root, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                     start_new_session=True)
print(p.pid)
PY
    sleep 2
    echo "监督器已启动（pid $(cat "$SUPFILE")）· 日志 $LOGFILE"
    ;;
  status)
    if alive_sup; then echo "监督器运行中（pid $(cat "$SUPFILE")）"; fi
    if alive; then
      echo "单趟运行中（pid $(cat "$PIDFILE")）"
      tail -3 "$LOGFILE" 2>/dev/null
    elif ! alive_sup; then
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
    if alive_sup; then
      SPID=$(cat "$SUPFILE")
      kill -TERM -"$SPID" 2>/dev/null || kill -TERM "$SPID" 2>/dev/null
      sleep 2; alive_sup && kill -KILL -"$SPID" 2>/dev/null
      echo "监督器已停止（pid $SPID）"; rm -f "$SUPFILE"
    fi
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
  *) echo "用法: tools/run-loop.sh {start <mission> <todo-id> [参数...]|supervise <mission> <todo-id>|status|stop|log [行数]}"; exit 1 ;;
esac
