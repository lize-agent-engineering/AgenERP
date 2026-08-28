"""P2.3 Phase 4 · 量化评测跑器。**实验设施，不是产品代码。**

    set -a; . ~/.config/agenerp/secrets.env; set +a
    export AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
           AGENERP_ADMIN_PASSWORD=admin
    python3 tools/experiments/p2_view_agent/run_eval.py --out results-sonnet.json

## 双层判分（人 2026-08-28 裁定）

**① 硬判 —— 确定性、零判官 token。** 交出来了 + 两层校验过 + DocType 命中 +
`must_fields` 全在 +（主集）落回 = 0。

**② 判官 —— 只答一个问题：「这个视图切题吗」。**
🔴 **不给判官期望集合。** `docs/logs/2026/08-28-handoff-p2.md` §3④ 记着那个坑：
判官提示词里塞进正解会**引导证人**（「不在集合里」当理由 = 循环论证）。
判官只看到「用户问了什么」和「交出来的视图」。

为什么要第二层：硬判抓不到「结构全对、数出来不是那个数」。真实样本就在本项 ——
`count(naming_series)` 结构全对、字段真实、落回为 0、硬判全绿，**数的却不是笔数**。

## 一道闸都不设

handoff §4 逐字：跑评测**一道闸不要设**，设了闸实测 42% 的题被砍掉、
而那些失败会**伪装成能力不足**。
⚠️ `ViewLoop` 上与「闸」同族的只有三个数，本跑器**一个都不收紧**：
`max_turns`（防跑飞）· `repair_rounds`（本轮要测量的对象，D8）· `tool_turn_nudge`。
三者的实际取值逐条记进结果文件 —— **不记就等于没说自己开了什么闸。**
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from agenerp.dsl.schema import SchemaView  # noqa: E402
from agenerp.routing import route  # noqa: E402
from agenerp.routing.capabilities import ModelProfile  # noqa: E402
from agenerp.routing.config import LlmConfig  # noqa: E402
from agenerp.site import client_from_env  # noqa: E402
from agenerp.views.loop import STOP_PROPOSED, ViewLoop  # noqa: E402
from tools.experiments.p2_view_agent.claude_cli import ClaudeCliTransport  # noqa: E402

DIR = pathlib.Path(__file__).resolve().parent

JUDGE_PROMPT = """
用户对一个 ERP 系统说了这句话：

    {question}

系统据此生成了下面这个视图（DSL）：

{view}

**这个视图回应了用户那句话吗？** 只看切不切题，不要评价字段名好不好听。
判「不切题」的典型：答的是另一张单据 · 用户要一个数却给了一张列表（或反过来）·
计数计在一个大多数行都为空的字段上（那样数出来的不是条数）。

只输出一个 JSON 对象，不要解释：{{"on_topic": true 或 false, "why": "一句话"}}
""".strip()


def load_schema() -> SchemaView:
    raw = json.loads((DIR / "eval-schema.json").read_text(encoding="utf-8"))
    return SchemaView.from_meta_rows(raw["fields"])


def load_rows() -> list[dict]:
    text = (DIR / "eval-set.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def adapter_for(transport, model_name: str):
    """借 `route()` 造 adapter —— 走的仍是产品的那一条挑模型路径。"""
    profile = ModelProfile(
        name=model_name,
        capabilities=frozenset({"tool_calling", "long_context", "reasoning", "multi_hop"}),
        is_reasoning_model=False,
    )
    config = LlmConfig("http://claude-cli-not-a-real-endpoint", model_name, "not-a-real-key")
    return route("view", models=[profile], config=config, transport=transport)


def view_as_dict(view) -> dict:
    return {
        "name": view.name,
        "title": view.title,
        "blocks": [
            {"type": b.type, "title": b.title, "doctype": b.doctype, "fields": list(b.fields),
             "filters": [list(f) for f in b.filters], "sort": list(b.sort) if b.sort else None,
             "limit": b.limit, "agg": b.agg, "chart_kind": b.chart_kind, "question": b.question}
            for b in view.blocks
        ],
    }


def hard_score(row: dict, proposal) -> dict:
    """确定性硬判。**每一条不通过都要说出是哪一条不通过**，不给一个光秃秃的 False。"""
    checks: dict[str, bool] = {}
    reasons: list[str] = []

    checks["proposed"] = proposal is not None and proposal.stop_reason == STOP_PROPOSED
    if not checks["proposed"]:
        reasons.append(f"没交出视图（{getattr(proposal, 'stop_reason', 'exception')}）")
        return {"passed": False, "checks": checks, "reasons": reasons}

    checks["validated"] = bool(proposal.validation and proposal.validation.ok)
    refs = proposal.view.field_refs()
    doctypes = {d for d, _ in refs}
    checks["doctype_hit"] = row["expect_doctype"] in doctypes
    if not checks["doctype_hit"]:
        reasons.append(f"DocType 没命中：要 {row['expect_doctype']}，交的是 {sorted(doctypes)}")

    got = {f for d, f in refs if d == row["expect_doctype"]}
    missing = [f for f in row["must_fields"] if f not in got]
    checks["must_fields"] = not missing
    if missing:
        reasons.append(f"必须字段缺：{missing}")

    types = {b.type for b in proposal.view.blocks}
    checks["block_type"] = bool(types & set(row["expect_block_types"]))
    if not checks["block_type"]:
        reasons.append(f"块类型不对：要 {row['expect_block_types']}，交的是 {sorted(types)}")

    if row["domain"] == "in":
        # 「落回 = 0」只在 P2.2 路线 C 的分母（车间工人域）上是判据。
        checks["no_fallback"] = proposal.render_plan.fallbacks == ()
        if not checks["no_fallback"]:
            reasons.append(f"落回了：{[f.reason for f in proposal.render_plan.fallbacks]}")
    else:
        # 域外只要求「每一次落回都有理由」—— 有 reason 就算说清了。
        checks["fallback_explained"] = all(
            f.reason for f in proposal.render_plan.fallbacks
        )

    return {"passed": all(checks.values()), "checks": checks, "reasons": reasons}


def judge(transport, question: str, view: dict) -> dict:
    """判官。**只看题面与产出，看不到期望集合**（§3④：不许引导证人）。"""
    prompt = JUDGE_PROMPT.format(
        question=question, view=json.dumps(view, ensure_ascii=False, indent=1)
    )
    raw = transport._run(prompt)
    text = (raw.get("result") or "").strip()
    try:
        # ⚠️ **不贪婪解析**：只接受整段 JSON。捞出来的「第一个大括号到最后一个」
        # 会把判官的散文当成结论（P2.0R 的判官就崩在这上面）。
        verdict = json.loads(text)
        return {"on_topic": bool(verdict.get("on_topic")), "why": verdict.get("why", "")}
    except ValueError:
        return {"on_topic": None, "why": f"判官没回 JSON：{text[:150]!r}"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results-sonnet.json")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--only", default="", help="只跑某几题，逗号分隔的 id")
    args = parser.parse_args()

    schema = load_schema()
    client = client_from_env("frontend")
    rows = load_rows()
    if args.only:
        wanted = {x.strip() for x in args.only.split(",")}
        rows = [r for r in rows if r["id"] in wanted]

    judge_transport = ClaudeCliTransport(model=args.model)
    results = []
    for index, row in enumerate(rows, 1):
        transport = ClaudeCliTransport(model=args.model)
        loop = ViewLoop(
            adapter=adapter_for(transport, args.model),
            client=client,
            schema=schema,
            doctypes=list(schema.doctypes()),
        )
        record: dict = {"id": row["id"], "q": row["q"], "domain": row["domain"]}
        proposal = None
        try:
            proposal = loop.run(row["q"], session_id=f"eval-{row['id']}")
            record["stop_reason"] = proposal.stop_reason
            record["trajectory_full"] = [
                {"tool": c["tool"], "params": c["params"]}
                for t in proposal.trace.turns if t["kind"] == "tools" for c in t["calls"]
            ]
            record["repairs"] = sum(1 for t in proposal.trace.turns if t["kind"] == "rejected")
            record["rejections"] = [
                t["detail"] for t in proposal.trace.turns if t["kind"] == "rejected"
            ]
            record["view"] = view_as_dict(proposal.view) if proposal.view else None
            record["fallbacks"] = (
                [f.reason for f in proposal.render_plan.fallbacks]
                if proposal.render_plan else None
            )
        except Exception as exc:  # noqa: BLE001 —— 一题炸掉不许拖垮整轮，但要留全栈
            record["stop_reason"] = "exception"
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["traceback"] = traceback.format_exc()[-1500:]

        record["hard"] = hard_score(row, proposal)
        record["judge"] = (
            judge(judge_transport, row["q"], record["view"])
            if record.get("view") else {"on_topic": False, "why": "没有视图可判"}
        )
        record["cost_usd"] = sum(c["cost_usd"] or 0 for c in transport.calls)
        record["calls"] = len(transport.calls)
        results.append(record)
        mark = "✅" if record["hard"]["passed"] else "❌"
        print(f"[{index}/{len(rows)}] {mark} {row['id']} {row['q'][:22]} "
              f"| 判官 {record['judge']['on_topic']} | {record['calls']} 次调用",
              flush=True)

    def rate(domain: str, key) -> str:
        subset = [r for r in results if r["domain"] == domain]
        if not subset:
            return "—"
        hit = sum(1 for r in subset if key(r))
        return f"{hit}/{len(subset)} = {hit / len(subset) * 100:.1f}%"

    summary = {
        "model": args.model,
        "gates": {
            "note": "一道闸都不收紧；与「闸」同族的三个数按实际取值逐条记在这里",
            "values": {
                "max_turns": loop.max_turns,
                "repair_rounds": loop.repair_rounds,
                "tool_turn_nudge": loop.tool_turn_nudge,
            },
        },
        "in_domain_hard": rate("in", lambda r: r["hard"]["passed"]),
        "out_domain_hard": rate("out", lambda r: r["hard"]["passed"]),
        "in_domain_judge": rate("in", lambda r: r["judge"]["on_topic"] is True),
        "out_domain_judge": rate("out", lambda r: r["judge"]["on_topic"] is True),
        "max_repairs_seen": max((r.get("repairs", 0) for r in results), default=0),
        "cost_usd_total": round(
            sum(r.get("cost_usd", 0) for r in results)
            + sum(c["cost_usd"] or 0 for c in judge_transport.calls), 4
        ),
    }
    (DIR / args.out).write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"→ {DIR / args.out}")


if __name__ == "__main__":
    main()
