#!/usr/bin/env python3
"""P2.0R 第六轮 Arm B · 给 agent 工具，让它自己去查。

跑法（先探针，再全量 —— 闸口写死在 plan §2.0）：
    python3 tools/experiments/p2_schema_retrieval/round6b_agent_navigates.py \
        --eval tools/experiments/p2_schema_retrieval/eval-set.json \
        --out  tools/experiments/p2_schema_retrieval/results-round6b.json \
        --probe 3 --max-turns 8

## 这一轮测的是 owner doc 说的主路

`context-and-memory.md` §8.1 修正后的 ②：**优先结构化导航**
（`system.overview` / `meta.fields` / `doc.links`），向量检索仅作兜底召回。
Spike 02 的受约束 Agent 四道探针全过、**全程零向量检索**。

⚠️ **本轮刻意不新写工具** —— `agenerp/tools/registry.py` 现成的十个执行体
已覆盖 §8.1 点名的那三个。人提的「添加数据库查询工具」记在 plan §11，
重开条件是「agent 卡在某个现有工具答不了的问题上，且缺口能被具体指出来」。

## 🔴 成本

`loop.py` 写着 D-26 定的 **20 万 token/次**上限 ⇒ 40 条的最坏情况是 **800 万**。
所以本脚本**默认只跑探针**，`--probe` 不给才跑全量，且 `--max-turns` 默认收紧到 8
（产品默认是 40 —— 找一个字段不该要 40 轮）。
**单价按 API 回的数算**，写进结果文件。
"""

import argparse
import json
import os
import re
import sys
import time


def build_deps():
    """造出 `explain()` 要的三样：站点客户端 · 模型档案 · 路由配置。

    **全部走产品路径上的那几个工厂**，不自己拼 —— 自己拼就等于测了一条产品不走的路。
    """
    from agenerp.routing.capabilities import KNOWN_MODEL_PROFILES
    from agenerp.routing.config import from_env as config_from_env
    from agenerp.site import client_from_env

    site = os.environ.get("AGENERP_SITE") or "frontend"
    return client_from_env(site), tuple(KNOWN_MODEL_PROFILES.values()), config_from_env()


QUESTION = """请找出回答下面这个问题需要用到的 ERPNext 字段。

问题：{q}

**只回答字段本身**，格式严格为 `DocType.fieldname`（例如 `Sales Order.customer`）。
可以给最多 5 个候选，每行一个，按可能性从高到低排。
不要解释、不要别的内容。"""

FIELD_RE = re.compile(r"([A-Z][A-Za-z ]+?)\.([a-z_][a-z0-9_]*)")


def parse_fields(answer: str) -> list[str]:
    """从答案里抠出 `DocType.fieldname`。**认不出的就不算**，不猜。"""
    out, seen = [], set()
    for m in FIELD_RE.finditer(answer or ""):
        key = f"{m.group(1).strip()}.{m.group(2)}"
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out[:5]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--probe", type=int, default=0, help="只跑前 N 条（预算探针用）")
    ap.add_argument("--sample", type=int, default=0,
                    help="**等距**抽 N 条。⚠️ 与 --probe 不同：--probe 取前 N 条，"
                         "而评测集按域排序，前 N 条只覆盖前几个域（有偏）。"
                         "预算闸口判为「只跑一半」时用这个，别用 --probe。")
    ap.add_argument("--max-turns", type=int, default=8)
    ap.add_argument("--schema", default="/tmp/schema.json")
    args = ap.parse_args()

    from agenerp.explain.loop import explain

    items = json.load(open(args.eval))["items"]
    if args.probe:
        items = items[: args.probe]
    elif args.sample:
        # 等距抽样：评测集按 selling / buying / stock / manufacturing / accounts /
        # quality / subcontracting 排序，取前 N 条会漏掉后面几个域。
        step = len(items) / args.sample
        items = [items[int(i * step)] for i in range(args.sample)]

    # 硬约束 ④ 的执行体：答案必须指回真实存在的字段。
    real = {
        f"{f['doctype']}.{f['fieldname']}"
        for f in json.load(open(args.schema))["fields"]
    }

    client, models, config = build_deps()
    print(f"问句 {len(items)} 条 · max_turns={args.max_turns} · "
          f"{'探针模式' if args.probe else '全量'}")

    detail, total_in, total_out, tool_calls_total = [], 0, 0, 0
    t0 = time.time()
    for n, item in enumerate(items, 1):
        try:
            result = explain(
                QUESTION.format(q=item["q"]),
                task_class="explain",
                client=client,
                models=models,
                config=config,
                max_turns=args.max_turns,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  {n}/{len(items)}  ❌ 炸了：{type(exc).__name__}: {exc}", flush=True)
            detail.append({"q": item["q"], "error": f"{type(exc).__name__}: {exc}"})
            continue

        answer = getattr(result, "answer", "") or ""
        # 🔴 **要算钱就读账本**（`loop.py:263` 的 `cost_ledger` docstring 逐字）：
        # `usage` 答的是「这次会话累计了多少」（只记成为了一轮对话的那些调用），
        # 而 `cost_ledger` 答的是「一共调了几次模型、各花了多少」——
        # 模型抛错那一次没有 turn，异常路径上账本 ≥ usage。
        # ⚠️ 第一版我把 `result.usage`（一个 **property**）当对象取 `prompt_tokens`，
        # 拿到 0 —— 而**预算闸口正是靠这个数放行的**。表坏了闸门就形同虚设，
        # 这类「读数为 0 却一路绿灯」正是本仓最贵的失败形态。
        ledger = result.cost_ledger
        u_in = sum(e.usage.prompt for e in ledger.entries)
        u_out = sum(e.usage.completion for e in ledger.entries)
        u_reasoning = sum(e.usage.reasoning for e in ledger.entries)
        total_in += u_in
        total_out += u_out

        trace = getattr(result, "trace", None)
        calls = list(getattr(trace, "tool_calls", None) or [])
        tools_used = sorted({(c.get("tool") if isinstance(c, dict) else getattr(c, "tool", ""))
                             or "" for c in calls} - {""})
        tool_calls_total += len(calls)

        got = parse_fields(answer)
        # 🔴 硬约束 ④：指不回真实字段的一律不算命中，**不给「它意思对了」这种分**。
        grounded = [g for g in got if g in real]
        want = set(item["expected"])
        rank = next((i + 1 for i, g in enumerate(grounded) if g in want), None)

        detail.append({
            "q": item["q"], "expected": item["expected"], "answer_fields": got,
            "grounded_fields": grounded, "rank": rank,
            "tools_used": tools_used, "n_tool_calls": len(getattr(trace, "tool_calls", None) or []),
            "tokens": {"in": u_in, "out": u_out, "reasoning": u_reasoning,
                       "model_calls": len(ledger.entries)},
            "stop_reason": getattr(result, "stop_reason", None),
        })
        print(f"  {n}/{len(items)}  {'✅' if rank and rank <= 5 else '❌'} "
              f"{u_in + u_out:>6} token · {len(tools_used)} 种工具 {tools_used} · "
              f"答 {grounded[:2]}", flush=True)

    ok = [d for d in detail if d.get("rank") and d["rank"] <= 5]
    n = len(detail)
    per = (total_in + total_out) / n if n else 0
    print(f"\nB1 设施自检：调过工具的问句 "
          f"{sum(1 for d in detail if d.get('n_tool_calls'))}/{n}")
    print(f"B2 字段 Top-5：**{len(ok) * 100 / n:.1f}%**（{len(ok)}/{n}）  "
          f"（第五轮 82.5% · Arm A 85.0% · 上限 92.5%）")
    print(f"\n🔴 单价：**{per:,.0f} token/条**  "
          f"（闸口：≤8k 跑全量 · 8–20k 只跑 20 条 · >20k 不跑）")
    print(f"合计 {total_in:,} in / {total_out:,} out · 工具调用 {tool_calls_total} 次 · "
          f"{round(time.time() - t0)}s")

    json.dump({"probe": args.probe, "max_turns": args.max_turns, "n": n,
               "B2_top5_pct": round(len(ok) * 100 / n, 1) if n else None,
               "tokens": {"in": total_in, "out": total_out, "per_question": round(per)},
               "tool_calls_total": tool_calls_total, "detail": detail},
              open(args.out, "w"), ensure_ascii=False, indent=2)
    print(f"→ {args.out}")


if __name__ == "__main__":
    sys.exit(main())
