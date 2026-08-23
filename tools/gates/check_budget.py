#!/usr/bin/env python3
"""日预算闸 —— 把「单 mission 累计成本超阈值」从口号变成可判定的退出码。

此前这条停机条件只有 maxTotalSteps 做代理，而实测证明代理不准：
按空转数字估的 120 步，真实工作下是十倍的量。这里直接读本机 transcript 加总。

用法：
  python3 tools/gates/check_budget.py [--budget-tokens N] [--json]

退出码（**一码一义；调用方按它分支，人按 stderr 那句话读**）：
  0  今日用量在预算内
  1  已超预算 —— 停机等人。**只有这一件事退 1。**
  2  24 小时内台账里没有循环趟次记录（全新检出的首趟就是这个）—— 交调用方决定
  3  判定器自身失败：阈值配置读不出 / 环境变量写坏 / 台账读不出 / 任何未预料的异常
     —— **停机等人，不是放行。**

为什么有 3：此前判定器自身崩溃的进程也退 1，而 `tools/loop-supervisor.sh` 闸 2 把 1
逐字翻译成 `halt_with "budget-exceeded" "24 小时内循环用量超出预算，停机等人复核"` ——
**人第二天早上看到的停机记录会说「烧超了」，而真相是闸自己崩了**。3 把「超预算」与
「闸坏了」分成两件事；两件事都往「停」的方向倒，不是拿「不再说谎」换「不再拦」。
取舍与残余风险落纸在 `docs/architecture/system-baseline.md` §14.9。
"""
import argparse
import datetime
import json
import os
import pathlib
import sys
import traceback

# 实测：真实工作约 1,500 万输入 token / 循环（≈$16 当量）。
# 默认 2 亿 ≈ 13 个循环 ≈ $210 当量 —— 「人该回来看一眼」的量级，不是「烧穿了才发现」。
DEFAULT_BUDGET = 200_000_000

EXIT_WITHIN = 0
EXIT_OVER = 1
EXIT_NO_DATA = 2
EXIT_GATE_BROKEN = 3


class GateBroken(RuntimeError):
    """判定器自身失败。与「超预算」严格分开 —— 它走退出码 3，不走 1。"""


def config_path() -> pathlib.Path:
    """阈值配置文件的位置 —— **调用时求值，且相对脚本自己，不相对 cwd**。

    此前是模块级的 `pathlib.Path("tools/gates/budget.json")`：循环在仓根跑读到文件里的
    10 亿，人手工在别的目录下跑读不到它、静默落到内置默认 2 亿 —— **同一个判定器给出
    两个答案**。那次事故记在 `docs/masterplan/STATE.md`，当时只补了「配置文件是唯一
    真相源」这一半，路径解析这一半留到了这里。
    """
    return pathlib.Path(__file__).resolve().parent / "budget.json"


def configured_budget() -> int:
    """阈值的唯一真相源：环境变量 > 配置文件 > 内置默认。

    两处此前的**静默兜底**已改成 `GateBroken`（退 3）：环境变量非空但不是纯数字、
    配置文件在但解析不出。理由同向 —— 两者都是**静默往更松的一侧倒**，而这条闸的
    设计取向是宁可停着等人。**文件不存在**仍用内置默认：那是全新检出的正常状态，不是错误。
    """
    env = os.environ.get("AGENERP_DAILY_TOKEN_BUDGET", "").strip()
    if env:
        if not env.isdigit():
            raise GateBroken(
                f"环境变量 AGENERP_DAILY_TOKEN_BUDGET 不是纯数字：{env!r}"
                "（此前它被静默忽略、落到配置文件的值 —— 比操作者写的意图更松）")
        return int(env)
    path = config_path()
    if not path.exists():
        return DEFAULT_BUDGET
    try:
        return int(json.loads(path.read_text())["daily_token_budget"])
    except Exception as exc:
        raise GateBroken(f"阈值配置 {path} 在，但读不出：{exc!r}") from exc


LEDGER = pathlib.Path("_tmp/loop-usage.jsonl")


def parse_at(raw: str) -> datetime.datetime:
    """台账里的时间戳 → 带时区的 datetime；不带时区的按 UTC 归一，并在 stderr 出声。

    取「归一」不是因为有据 —— `pass_usage.py` 从不产出这种行，它的口径对手写行一个字
    都没说 —— 而是**最小意外，且与仓内唯一写入方的口径一致**；出声是为了让这个假设不静默。
    ⚠️ 残余：负时区手写的本地时间被读成 UTC 会更早，更可能落到 24h 窗口外而被**少算**，
    方向不安全；代偿只有下面这行告警，且它只在有人看日志时起作用。
    """
    t = datetime.datetime.fromisoformat(raw)
    if t.tzinfo is None:
        print(f"[budget] ⚠️ 台账里一行 at 不带时区，按 UTC 归一：{raw}", file=sys.stderr)
        t = t.replace(tzinfo=datetime.UTC)
    return t


def usage_since(start: datetime.datetime) -> dict:
    """只统计台账里的循环趟次。不扫全盘 —— 人的交互会话不该算进循环预算。"""
    tot = {"input": 0, "output": 0, "msgs": 0, "passes": 0, "sessions": 0}
    if not LEDGER.exists():
        return tot
    for line in LEDGER.open(errors="ignore"):
        try:
            r = json.loads(line)
            t = parse_at(r["at"])
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


def _run(a: argparse.Namespace) -> int:
    if a.budget_tokens is None:
        a.budget_tokens = configured_budget()

    now = datetime.datetime.now(datetime.UTC)
    start = now - datetime.timedelta(hours=24)
    tot = usage_since(start)

    if not tot["passes"]:
        # 读不到数据 ≠ 用量为零。不猜，交调用方决定。
        print("[budget] 台账 _tmp/loop-usage.jsonl 里 24 小时内没有循环趟次记录", file=sys.stderr)
        return EXIT_NO_DATA

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
        return EXIT_OVER
    return EXIT_WITHIN


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="check_budget.py",
        description="日预算闸：读台账 _tmp/loop-usage.jsonl，判 24 小时内的循环用量是否超预算。",
        epilog=(
            "退出码（一码一义）：\n"
            "  0  今日用量在预算内\n"
            "  1  已超预算 —— 停机等人。只有这一件事退 1\n"
            "  2  24 小时内台账里没有循环趟次记录（全新检出的首趟就是这个）\n"
            "  3  判定器自身失败（配置读不出 / 环境变量写坏 / 台账读不出 / 未预料的异常）\n"
            "     —— 停机等人，不是放行\n"),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--budget-tokens", type=int,
                    default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        return _run(a)
    except GateBroken as exc:
        print(f"[budget] ❌ 预算闸自身失败 —— 退 3（不是超预算），停机等人：{exc}", file=sys.stderr)
        return EXIT_GATE_BROKEN
    except Exception as exc:
        print(f"[budget] ❌ 预算闸自身失败 —— 退 3（不是超预算），停机等人：{exc!r}", file=sys.stderr)
        traceback.print_exc()
        return EXIT_GATE_BROKEN


if __name__ == "__main__":
    sys.exit(main())
