#!/usr/bin/env bash
# 循环联动冒烟（W0.14）—— 验证「门禁判定 → 循环反应」这条链是真的接上的。
#
# 三个场景，全部用 --dry-run（agent 步被 mock，script 步真跑），不烧 token、不产出业务代码：
#   A. commands.test 通过        → GATE_VERIFY pass → plan 完成
#   B. commands.test 退非 0      → GATE_VERIFY fail → 循环 retry EXECUTE
#   C. 改动 tests/gates/**       → **停机**：引擎退 2 + 落停机记录 + 停机闸拒绝重启
#
# 退出码 0 = 三条链都对。非 0 = 有一条断了，别再往下开 7×24。
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

SMOKE_DIR="$ROOT/_smoke"
MISSION="$ROOT/missions/smoke-gate.json"
VICTIM="tests/gates/test_normalizer_idempotent.py"
fails=0

cleanup() {
  rm -rf "$SMOKE_DIR" "$MISSION" "$ROOT/.mission-halt.json"
  git checkout -- "$VICTIM" 2>/dev/null || true
}
trap cleanup EXIT

setup() {
  mkdir -p "$SMOKE_DIR/plans" "$SMOKE_DIR/audits"
  cat > "$SMOKE_DIR/roadmap.md" <<'EOF'
# Smoke roadmap

## Work Item Status

- 1. 冒烟：验证门禁联动: `planned`
EOF
  cat > "$SMOKE_DIR/plans/2026-01-01-0000-1-smoke.md" <<'EOF'
# 冒烟计划

> Plan Status: active

## Phase 1 — 空转

> Status: in progress

- [ ] 只让流程走到 GATE_VERIFY

### Exit Criteria

- [ ] GATE_VERIFY 给出判定
EOF
  write_mission "true"
}

write_mission() {
  cat > "$MISSION" <<EOF
{
  "name": "smoke-gate",
  "goal": "设施自检：只验证循环与门禁联动，不产出业务代码。",
  "flowName": "mission-driver",
  "driver": "claude",
  "model": "opus",
  "roadmapPath": "_smoke/roadmap.md",
  "plansDir": "_smoke/plans",
  "planGuide": "docs/plans/00-plan-authoring-and-execution-guide.md",
  "auditsDir": "_smoke/audits",
  "contextDir": "docs/context",
  "commands": { "test": "$1" },
  "scripts": { "gate-verify": "tools/gates/gate-verify.mjs" },
  "commitFormat": "<type>(<scope>): <description>"
}
EOF
}

check() { # check <描述> <期望> <实际>
  if [ "$2" = "$3" ]; then echo "  ✓ $1"; else echo "  ✗ $1：期望 [$2] 实际 [$3]"; fails=$((fails+1)); fi
}

run_engine() {
  node tools/mission-driver/src/main.js smoke-gate --dry-run > /tmp/smoke-loop.log 2>&1
  echo $?
}

setup

echo "A · commands.test 通过 → GATE_VERIFY pass"
write_mission "true"
code=$(run_engine)
check "引擎退出码 0" "0" "$code"
check "GATE_VERIFY 判 pass" "yes" "$(grep -qE '\[step [0-9]+\] GATE_VERIFY' /tmp/smoke-loop.log && grep -A1 'GATE_VERIFY (visit #1)' /tmp/smoke-loop.log | grep -q 'marker: pass' && echo yes || echo no)"

echo "B · commands.test 退非 0 → GATE_VERIFY fail → retry EXECUTE"
write_mission "exit 1"
code=$(run_engine)
check "GATE_VERIFY 判 fail" "yes" "$(grep -A1 'GATE_VERIFY (visit #1)' /tmp/smoke-loop.log | grep -q 'marker: fail' && echo yes || echo no)"
check "失败后回到 EXECUTE 重试" "yes" "$(grep -q 'retry GATE_VERIFY→EXECUTE' /tmp/smoke-loop.log && echo yes || echo no)"

echo "C · 改动 tests/gates/** → 停机"
write_mission "true"
echo "# smoke: 模拟 loop 改动门禁" >> "$VICTIM"
code=$(run_engine)
check "引擎退出码 2（停机）" "2" "$code"
check "落下停机记录" "yes" "$([ -f "$ROOT/.mission-halt.json" ] && echo yes || echo no)"
check "记录写明触发条件" "gates-touched" "$(python3 -c "import json;print(json.load(open('$ROOT/.mission-halt.json'))['condition'])" 2>/dev/null)"
./tools/mission-driver.sh smoke-gate --dry-run >/dev/null 2>&1
check "停机记录还在时拒绝启动（退 2）" "2" "$?"
git checkout -- "$VICTIM"; rm -f "$ROOT/.mission-halt.json"
./tools/mission-driver.sh smoke-gate --dry-run >/dev/null 2>&1
check "人处置后可重启（退 0）" "0" "$?"

echo "----"
if [ "$fails" -eq 0 ]; then echo "✅ 循环联动三条链全通"; else echo "❌ $fails 项不符"; fi
exit $([ "$fails" -eq 0 ] && echo 0 || echo 1)
