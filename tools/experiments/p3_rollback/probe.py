"""P3.2 回滚前提探测 · **宿主侧编排** —— 实验设施，不进 `agenerp/`。

它只回答一个问题：**`docs/architecture/module-boundaries.md` §7.1 那套 savepoint 回滚语义，
在本仓（frappe 15.118.0 / erpnext 15.119.3）上还成立吗，以及我们的工具层够不够得着它？**

那套语义与它的三个前提全部来自 2026-08-19 的**外部** Spike 05。**D-16：本项目的结论以
本项目实测为准。** 不先探测，P3.1 的回滚语义就是照抄一份没在本仓验过的结论。

## 三层防线（A1）—— 探测要真提交单据，所以先证明「收得干净」

| 层 | 是什么 | 谁做 |
|---|---|---|
| ① 站点备份 | `bench --site <site> backup` | `--backup` 子命令，或人手工 |
| ② 站点指纹 | `python3 -m agenerp.seedsite --verify-site` 跑前跑后逐项相等 | 本脚本每次自动跑两遍 |
| ③ 🔴 **变异先行** | 先手工改一条数据，证明**指纹会报红** | `--mutation-check`，**不见血就非零退出** |

第 ③ 层不是可选项。指纹只有在被证明会咬人之后，它的「全绿」才含信息 ——
否则「我核对过，一切正常」与「我的核对器本身是空的」在退出码上长得一模一样。

## 用法

    python3 tools/experiments/p3_rollback/probe.py --backup
    python3 tools/experiments/p3_rollback/probe.py --mutation-check
    python3 tools/experiments/p3_rollback/probe.py            # 指纹 → 探测 → 指纹

站点凭据从环境变量取（与本仓其余活站点命令同一套）::

    AGENERP_HTTP_PORT=18080 AGENERP_SITE=frontend \\
    AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin \\
    python3 tools/experiments/p3_rollback/probe.py

结果落 `docs/evidence/p3-rollback/`。**预测在跑之前就写死在 `HYPOTHESES.md` 里并单独
commit 过**，两个文件的**首次落库时间**由 `tests/tools/test_rollback_premises_body.py`
比对 —— 「先看结果再写假设」这件事因此是可判的，不靠自觉。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PAYLOAD = Path(__file__).resolve().parent / "payload.py"
EVIDENCE_DIR = REPO_ROOT / "docs" / "evidence" / "p3-rollback"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"

BACKEND_SERVICE = "backend"
JSON_MARKER = "<<<P3JSON>>>"

# A1 变异先行的靶子。它是站点指纹**第 1 项**直接盯着的那个数
# （`✅ Bin(HRD-PACK-5K, 成品仓 - HRD).actual_qty = 1010.00`）。
# 按 (item_code, warehouse) 指名 —— `Bin.name` 是站点生成的 hash，写死它绑死一次装载。
MUTATION_ITEM = "HRD-PACK-5K"
MUTATION_WAREHOUSE = "成品仓 - HRD"
MUTATION_DELTA = 1.0
_BIN_TARGET = {"P3_ITEM": MUTATION_ITEM, "P3_WAREHOUSE": MUTATION_WAREHOUSE}


class ProbeError(RuntimeError):
    """探测本身立不住。**不降级成空结果** —— 空结果会让「没测出问题」与「没测」同形。"""


def _site() -> str:
    site = os.environ.get("AGENERP_SITE", "").strip()
    if not site:
        raise ProbeError("AGENERP_SITE 未设置：探测不猜站点名")
    return site


def _compose(*args: str, stdin: str | None = None, timeout: int = 600) -> subprocess.CompletedProcess:
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), *args]
    return subprocess.run(
        cmd, input=stdin, capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT
    )


def run_payload(mode: str, site: str, extra_env: dict[str, str] | None = None) -> dict:
    """把 `payload.py` 从 stdin 喂进容器里的 bench venv python，取回它打的那行 JSON。

    ⚠️ **不走 `agenerp/oob.py`**：那条通道的 `ALLOWED_CALLS` 把可执行函数连 kwargs 一起钉死
    （模块头约束 2），加一条进去要付一次产品代码的 diff 和一次留痕 —— 而这是探测设施，
    不是产品能力。两者的界线就在这里，不该为了跑一次实验把产品的白名单撑开。
    """
    env_args: list[str] = []
    for key, value in {"P3_SITE": site, "P3_MODE": mode, **(extra_env or {})}.items():
        env_args += ["-e", f"{key}={value}"]
    proc = _compose(
        "exec", "-T", *env_args, BACKEND_SERVICE,
        "bash", "-lc", "cd /home/frappe/frappe-bench/sites && ../env/bin/python -",
        stdin=PAYLOAD.read_text(encoding="utf-8"),
    )
    marker_line = next(
        (line for line in proc.stdout.splitlines() if line.startswith(JSON_MARKER)), None
    )
    if marker_line is None:
        raise ProbeError(
            f"容器内载荷没有打出 {JSON_MARKER} 那一行（exit={proc.returncode}）。\n"
            f"--- stdout ---\n{proc.stdout[-3000:]}\n--- stderr ---\n{proc.stderr[-3000:]}"
        )
    payload = json.loads(marker_line[len(JSON_MARKER):])
    payload["_exit_code"] = proc.returncode
    payload["_stderr_tail"] = proc.stderr[-2000:]
    return payload


def fingerprint(site: str) -> dict:
    """站点指纹 = `python3 -m agenerp.seedsite --verify-site` 的**逐行原文 + 退出码**。

    只留退出码是不够的：判据要能说出「哪一项变了」，而那句话只在行文本里。
    """
    proc = subprocess.run(
        [sys.executable, "-m", "agenerp.seedsite", "--verify-site", "--site", site],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=300,
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return {
        "exit_code": proc.returncode,
        "all_green": proc.returncode == 0,
        "lines": lines,
        "failed_lines": [line for line in lines if line.startswith("❌")],
        "stderr_tail": proc.stderr[-2000:],
    }


def backup(site: str) -> dict:
    """防线①。**跑前必须有一份可还原的备份** —— 探测的坏消息分支之一是「污染了站点」，
    那一支的处置逐字是「结论作废、冷起重来」，而冷起要有东西可还原。"""
    proc = _compose("exec", "-T", BACKEND_SERVICE, "bench", "--site", site, "backup", timeout=900)
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def mutation_check(site: str) -> dict:
    """🔴 防线③ · 变异先行：证明指纹**会**报红。

    步骤是固定的六步，**每一步的实得值都进 JSON**：
    绿 → 读原值 → 改 → **必须红** → 还原 → **必须重新绿**。

    第 4 步不红即整条探测作废：一个不会报红的指纹，跑前跑后「逐项相等」不含任何信息。
    """
    out: dict = {"target_bin": f"Bin({MUTATION_ITEM}, {MUTATION_WAREHOUSE})",
                 "delta": MUTATION_DELTA}

    out["step_1_fingerprint_before"] = fingerprint(site)
    if not out["step_1_fingerprint_before"]["all_green"]:
        out["verdict"] = "基线就不绿，变异验证无从做起"
        out["ok"] = False
        return out

    read = run_payload("bin_read", site, _BIN_TARGET)
    if not read.get("ok"):
        out["verdict"] = f"读不到靶子 Bin：{read.get('error')}"
        out["ok"] = False
        return out
    original = float(read["bin"]["actual_qty"])
    out["step_2_original_actual_qty"] = original

    mutated = original + MUTATION_DELTA
    out["step_3_mutate"] = run_payload(
        "bin_set", site, {**_BIN_TARGET, "P3_VALUE": repr(mutated)}
    )
    try:
        out["step_4_fingerprint_after_mutation"] = fingerprint(site)
    finally:
        # 还原**永远要跑**，哪怕第 4 步炸了。站点比结论重要。
        out["step_5_restore"] = run_payload(
            "bin_set", site, {**_BIN_TARGET, "P3_VALUE": repr(original)}
        )
    out["step_6_fingerprint_after_restore"] = fingerprint(site)

    bit = not out["step_4_fingerprint_after_mutation"]["all_green"]
    restored = out["step_6_fingerprint_after_restore"]["all_green"]
    out["fingerprint_bites"] = bit
    out["site_restored"] = restored
    out["ok"] = bool(bit and restored)
    out["verdict"] = (
        "指纹有牙齿，且站点已还原" if out["ok"]
        else ("指纹没牙 —— 变异之后它照样全绿，整条探测作废" if not bit
              else "🔴 站点未还原，需要人介入（见 step_5_restore）")
    )
    return out


def premises(site: str) -> dict:
    """A2 + A3。跑前跑后各取一次指纹，中间那一次是容器内的四个前提测量。"""
    out: dict = {}
    out["fingerprint_before"] = fingerprint(site)
    if not out["fingerprint_before"]["all_green"]:
        out["ok"] = False
        out["verdict"] = "跑前指纹不绿，不在脏站点上测前提"
        return out
    out["measurement"] = run_payload("premises", site)
    out["fingerprint_after"] = fingerprint(site)
    before = out["fingerprint_before"]["lines"]
    after = out["fingerprint_after"]["lines"]
    out["fingerprint_identical"] = before == after
    out["fingerprint_diff"] = [
        [a, b] for a, b in zip(before, after, strict=False) if a != b
    ]
    out["ok"] = bool(out["measurement"].get("ok") and out["fingerprint_identical"])
    out["verdict"] = (
        "四个前提各有实测值，站点指纹跑前跑后逐项相等" if out["ok"]
        else "见 measurement.error / fingerprint_diff"
    )
    return out


def _write(name: str, payload: dict) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    target = EVIDENCE_DIR / name
    payload = {
        "captured_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT
        ).stdout.strip(),
        **payload,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 tools/experiments/p3_rollback/probe.py",
        description="P3.2 回滚前提探测（实验设施）",
    )
    parser.add_argument("--backup", action="store_true", help="防线①：站点备份")
    parser.add_argument("--mutation-check", action="store_true",
                        help="🔴 防线③：证明站点指纹会报红（不见血即非零退出）")
    parser.add_argument("--fingerprint", action="store_true", help="只取一次站点指纹")
    args = parser.parse_args(argv)

    try:
        site = _site()
        if args.backup:
            result = backup(site)
            print(result["stdout"])
            return result["exit_code"]
        if args.fingerprint:
            result = fingerprint(site)
            print("\n".join(result["lines"]))
            return result["exit_code"]
        if args.mutation_check:
            result = mutation_check(site)
            target = _write("mutation-check.json", result)
        else:
            result = premises(site)
            target = _write("premises.json", result)
    except ProbeError as exc:
        print(f"探测立不住，已停在出错那一步：{exc}", file=sys.stderr)
        return 2

    print(f"{'✅' if result.get('ok') else '❌'} {result.get('verdict', '')}")
    print(f"结果已落 {target.relative_to(REPO_ROOT)}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
