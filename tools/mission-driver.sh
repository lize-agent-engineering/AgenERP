#!/bin/bash

# --- AgenERP 停机闸（W0.14）-------------------------------------------------
# 7×24 靠的是反复重启这个脚本。停机记录还在，就一次都不许再启动 ——
# 否则「停机」只是停了一轮，下一轮照常带病狂奔。清除由人做，不是由 loop 做。
HALT_FILE="$(cd "$(dirname "$0")/.." && pwd)/.mission-halt.json"
if [ -f "$HALT_FILE" ]; then
  echo "════════════════════════════════════════════════════════" >&2
  echo "  拒绝启动：存在未处置的停机记录" >&2
  echo "════════════════════════════════════════════════════════" >&2
  cat "$HALT_FILE" >&2
  echo "" >&2
  echo "按 docs/masterplan/01-EXECUTION-MODEL.md §2 的五步处置，" >&2
  echo "处置完删除 $HALT_FILE 再启动。" >&2
  exit 2
fi
# --- 停机闸结束 -------------------------------------------------------------

# tools/mission-driver.sh — Mission driver launcher (thin shim).
#
# The mission-driver ENGINE is NOT copied into this repo. It lives in the shared
# attractor-guided-engineering-template and is located via MISSION_DRIVER_HOME,
# read from (in priority order):
#   1. the process environment (export MISSION_DRIVER_HOME=...)
#   2. the repo-root .env file (copy .env.example to .env and edit)
#
# MISSION_DRIVER_HOME may be RELATIVE (resolved from this repo's root) or absolute.

DIR="$(cd "$(dirname "$0")" && pwd | tr -d '\r')"
PROJECT_ROOT="$(cd "$DIR/.." && pwd | tr -d '\r')"

# Environment wins over .env: capture any pre-set value, load .env, then restore.
_ENV_MDH="$MISSION_DRIVER_HOME"
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$PROJECT_ROOT/.env"
  set +a
fi
[ -n "$_ENV_MDH" ] && MISSION_DRIVER_HOME="$_ENV_MDH"

if [ -z "$MISSION_DRIVER_HOME" ]; then
  echo "ERROR: MISSION_DRIVER_HOME is not set." >&2
  echo "  cp .env.example .env  then set MISSION_DRIVER_HOME in .env" >&2
  exit 1
fi

case "$MISSION_DRIVER_HOME" in
  /*|[A-Za-z]:[/\\]*) ABS_HOME="$MISSION_DRIVER_HOME" ;;
  *) ABS_HOME="$(cd "$PROJECT_ROOT/$MISSION_DRIVER_HOME" 2>/dev/null && pwd | tr -d '\r')" ;;
esac

if [ -z "$ABS_HOME" ] || [ ! -f "$ABS_HOME/src/main.js" ]; then
  echo "ERROR: MISSION_DRIVER_HOME does not point to a valid mission-driver install." >&2
  echo "  resolved to = ${ABS_HOME:-<unresolved>}" >&2
  exit 1
fi

exec node "$ABS_HOME/src/main.js" \
  --dir "$PROJECT_ROOT" \
  --missions-dir "missions" \
  "$@"
