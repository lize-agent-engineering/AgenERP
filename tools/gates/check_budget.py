#!/usr/bin/env python3
"""日预算闸 —— 把「单 mission 累计成本超阈值」从口号变成可判定的退出码。

此前这条停机条件只有 maxTotalSteps 做代理，而实测证明代理不准：
按空转数字估的 120 步，真实工作下是十倍的量。这里直接读本机 transcript 加总。

用法：
  python3 tools/gates/check_budget.py [--budget-tokens N] [--exclude-session ID] [--json]

退出码：
  0  今日用量在预算内
  1  已超预算 —— 调用方应停机等人
  2  读不到用量数据（不猜，按「未知」处理，交调用方决定）
"""
import argparse
import datetime
import json
import os
import pathlib
import sys

# 实测：真实工作约 1,500 万输入 token / 循环（≈$16 当量）。
# 默认 2 亿 ≈ 13 个循环 ≈ $210 当量 —— 「人该回来看一眼」的量级，不是「烧穿了才发现」。
DEFAULT_BUDGET = 200_000_000


LEDGER = pathlib.Path("_tmp/loop-usage.jsonl")


def usage_since(start: datetime.datetime) -> dict:
    """只统计台账里的循环趟次。不扫全盘 —— 人的交互会话不该算进循环预算。"""
    tot = {"input": 0, "output": 0, "msgs": 0, "passes": 0, "sessions": 0}
    if not LEDGER.exists():
        return tot
    for line in LEDGER.open(errors="ignore"):
        try:
            r = json.loads(line)
            t = datetime.datetime.fromisoformat(r["at"])
        except (ValueError, KeyError):
            continue
        if t < start:
            continue
        tot["passes"] += 1
        tot["sessions"] += r.get("sessions", 0)
        tot["input"] += r.get("input", 0)
        tot["output"] += r.get("output", 0)
        tot["msgs"] += r.get("msgs", 0)
    return tot


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-tokens", type=int,
                    default=int(os.environ.get("AGENERP_DAILY_TOKEN_BUDGET", DEFAULT_BUDGET)))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    now = datetime.datetime.now(datetime.UTC)
    start = now - datetime.timedelta(hours=24)
    tot = usage_since(start)

    if not tot["passes"]:
        # 读不到数据 ≠ 用量为零。不猜，交调用方决定。
        print("[budget] 台账 _tmp/loop-usage.jsonl 里 24 小时内没有循环趟次记录", file=sys.stderr)
        return 2

    over = tot["input"] > a.budget_tokens
    pct = tot["input"] / a.budget_tokens * 100
    if a.json:
        print(json.dumps({"input_tokens": tot["input"], "output_tokens": tot["output"],
                          "messages": tot["msgs"], "passes": tot["passes"], "sessions": tot["sessions"],
                          "budget": a.budget_tokens, "used_pct": round(pct, 1), "over": over},
                         ensure_ascii=False))
    else:
        print(f"[budget] 24h 内输入 {tot['input']:,} / 预算 {a.budget_tokens:,}（{pct:.1f}%）"
              f" · {tot['passes']} 趟 / {tot['sessions']} 个会话 · 输出 {tot['output']:,}")
    if over:
        print(f"[budget] ❌ 超预算 —— 停机等人。要放宽改 AGENERP_DAILY_TOKEN_BUDGET，"
              f"改之前先想清楚为什么这一天要烧这么多。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
