#!/usr/bin/env bash
# 跨模型对照的一条臂 —— 在隔离 worktree 里用指定 driver 跑同一个工作项。
#
# 为什么值得做：这个项目手里有件稀罕东西 —— **一套确定性的裁判**（13 条门禁 +
# 预期红名单棘轮 + GATE_VERIFY 复跑退出码）。判定不依赖谁评价谁，所以
# 「同一起点、同一工作项、同一批门禁，只换模型」这个实验是干净的。
#
# 用法：tools/ab-run.sh <臂名> <driver> <model> <基线 ref> [额外参数...]
#   例：tools/ab-run.sh codex-sol codex gpt-5.6-sol dc653ec
#       tools/ab-run.sh claude-opus claude opus dc653ec
#
# 产出：_tmp/ab/<臂名>/{worktree, run.log, metrics.json}
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARM="${1:?用法: tools/ab-run.sh <臂名> <driver> <model> <基线 ref> [额外参数...]}"
DRIVER="${2:?同上}"; MODEL="${3:?同上}"; BASE="${4:?同上}"; shift 4

OUT="$ROOT/_tmp/ab/$ARM"; WT="$OUT/worktree"
rm -rf "$OUT"; mkdir -p "$OUT"
git worktree remove --force "$WT" 2>/dev/null
git branch -D "ab/$ARM" 2>/dev/null

echo "[ab:$ARM] 从 $BASE 开 worktree"
git worktree add -b "ab/$ARM" "$WT" "$BASE" >/dev/null 2>&1 || { echo "worktree 创建失败"; exit 1; }

# 每条臂用自己的 mission 副本，只改 driver / model 两个字段 —— 其余一字不动
python3 - "$WT" "$ARM" "$DRIVER" "$MODEL" <<'PY'
import json, sys, pathlib
wt, arm, driver, model = sys.argv[1:5]
p = pathlib.Path(wt, "missions/p0-foundation.json")
d = json.loads(p.read_text())
d["name"] = f"ab-{arm}"
d["driver"] = driver
d["model"] = model
d.setdefault("_notes", {})["ab"] = f"对照实验臂 {arm}：只改 driver/model，其余与 p0-foundation 完全一致"
pathlib.Path(wt, f"missions/ab-{arm}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
PY

cd "$WT"
python3 "$ROOT/tools/gates/pass_usage.py" snapshot "$OUT/snap.txt" 2>/dev/null

START=$(date +%s)
node tools/mission-driver/src/main.js "ab-$ARM" "$@" > "$OUT/run.log" 2>&1
CODE=$?
END=$(date +%s)

cd "$ROOT"
python3 tools/gates/pass_usage.py measure "$OUT/snap.txt" --label "ab-$ARM" 2>/dev/null | tail -1

# 判定用的是**门禁**，不是观感
cd "$WT"
bash -c 'python3 tools/gates/check_expected_red.py >/dev/null 2>&1 && python3 -m pytest tests/unit -q >/dev/null 2>&1'
GATE=$?
COMMITS=$(git rev-list --count "$BASE"..HEAD 2>/dev/null || echo 0)
DIRTY=$(git status --short | wc -l | tr -d ' ')
RETRIES=$(grep -c "retry .*→" "$OUT/run.log" 2>/dev/null || echo 0)
TOUCHED_GATES=$(git diff --name-only "$BASE"..HEAD -- 'tests/gates/**' | wc -l | tr -d ' ')
cd "$ROOT"

python3 - "$OUT/metrics.json" "$ARM" "$DRIVER" "$MODEL" "$BASE" "$CODE" "$GATE" "$COMMITS" "$DIRTY" "$RETRIES" "$TOUCHED_GATES" "$((END-START))" <<'PY'
import json, sys
keys = ["arm","driver","model","base","exit_code","gate_exit","commits","dirty_files","retries","gate_files_touched","wall_seconds"]
vals = sys.argv[2:]
d = dict(zip(keys, vals))
for k in ("exit_code","gate_exit","commits","dirty_files","retries","gate_files_touched","wall_seconds"):
    d[k] = int(d[k])
d["gate_green"] = d["gate_exit"] == 0
d["red_line_violated"] = d["gate_files_touched"] > 0
open(sys.argv[1], "w").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(d, ensure_ascii=False, indent=2))
PY
