#!/usr/bin/env python3
"""P2.0R 第六轮 Arm A · 候选清单补一列「某某的子表」。

**与第五轮只差一个变量**：候选行尾多一段 `（<父表> 的子表）`。
第五轮 L2 的 4 条错里 3 条是父/子混淆，而候选清单压根没告诉模型谁是谁的子表 ——
尽管 `SchemaView.child_doctype()` 与活站点导出的父子映射仓里现成就有。

⚠️ 这是**便宜的对照臂**。人提的那件真正的事（给 agent 工具让它自己查）是 Arm B。

跑法：
    python3 tools/experiments/p2_schema_retrieval/round5_llm_doctype.py \
        --schema /tmp/schema.json \
        --eval   tools/experiments/p2_schema_retrieval/eval-set.json \
        --cache  /tmp/p2_vectors_v4.json \
        --out    tools/experiments/p2_schema_retrieval/results-round6a.json

## 这一轮测的是 owner doc 本来就写着的那条主路

`context-and-memory.md` §8.1 修正后的 ② 逐字：「向量检索仅作**兜底召回**……
**检索只负责给候选清单，由模型结合 `meta.fields` 定夺**」。
⚠️ 前四轮量的全是兜底召回那一层，把它当成了主路 —— 本轮补上。

## 天花板已经算过（plan §1.1）

候选清单 N=50 时 DocType `recall@N = 100%` ⇒ **合成上限就是 oracle 的 92.5%**，
只比验收线高 2.5 个点。**本轮不指望达标。**

## D-15 不冲突

「用户说的是哪一张单」**不是规则能覆盖的**（语义判断），交给模型是允许的。
被 D-15 禁止的是把**校验**、**落回判定**那种规则面交出去。
"""

import argparse
import json
import math
import pathlib
import re
import ssl
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from index_and_eval import field_text  # noqa: E402
from score_fusion import KS, recall  # noqa: E402

BASE_DEFAULT = "https://dashscope.aliyuncs.com/compatible-mode/v1"
N_CANDIDATES = 50
USAGE = {"calls": 0, "in": 0, "out": 0, "reasoning": 0, "embed_tokens": 0}

PICK_PROMPT = """用户问了一个 ERP 系统的问题。下面是候选单据（DocType）清单，
每行是 `<序号>. <单据名> | 模块 | 该表有多少行数据`，
子表还会标出它是谁的子表。

⚠️ 用户说「这一行」「某某明细」时，指的通常是**子表**，不是父单据。

请判断用户问的是**哪一张单据**，**只输出那一行的序号**，不要任何其他内容。

用户的问题：{question}

候选：
{candidates}
"""


def _ssl_context():
    """certifi 且**惰性 import** —— 同 `agenerp/routing/adapter.py:103`。"""
    import certifi

    return ssl.create_default_context(cafile=certifi.where())


def chat(prompt: str, *, model: str, base_url: str, api_key: str) -> str:
    """OpenAI 兼容口。**`enable_thinking: false` 是预算的前提**（450 倍那条）。"""
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(
            {
                "model": model,
                "enable_thinking": False,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=300, context=_ssl_context()) as res:
        body = json.loads(res.read())
    if body.get("error"):
        raise RuntimeError(f"端点回错：{body['error']}")
    u = body.get("usage") or {}
    USAGE["calls"] += 1
    USAGE["in"] += u.get("prompt_tokens") or 0
    USAGE["out"] += u.get("completion_tokens") or 0
    USAGE["reasoning"] += (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
    return body["choices"][0]["message"]["content"]


def embed(texts, model, key, base):
    req = urllib.request.Request(
        f"{base}/embeddings",
        data=json.dumps({"model": model, "input": texts}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=300, context=_ssl_context()) as res:
        body = json.loads(res.read())
    USAGE["embed_tokens"] += (body.get("usage") or {}).get("total_tokens") or 0
    return [r["embedding"] for r in sorted(body["data"], key=lambda d: d["index"])]


def norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="qwen3.6-plus")
    ap.add_argument("--embed-model", default="text-embedding-v4")
    args = ap.parse_args()

    import os

    key = os.environ.get("AGENERP_LLM_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise SystemExit("没有 API key —— 不猜凭据")
    base = os.environ.get("AGENERP_LLM_BASE_URL", BASE_DEFAULT)

    fields = json.load(open(args.schema))["fields"]
    items = json.load(open(args.eval))["items"]
    texts = [field_text(f, "described") for f in fields]

    cache = pathlib.Path(args.cache)
    if not cache.exists():
        raise SystemExit(
            f"向量缓存 {cache} 不在了 —— 重建要 178k token。**先确认这一点再跑**（plan §6）。"
        )
    blob = json.load(open(cache))
    if blob.get("model") != args.embed_model:
        raise SystemExit(f"缓存是 {blob.get('model')} 的，与 --embed-model 不符，不将就")
    # 🔴 **缓存必须对得上当前 schema。** 第一版漏了这一步（ruff 报 `texts` 未使用才暴露出来）——
    # schema 一变，就会**静默地**拿旧向量去算，而失败形态是「数看着正常但没意义」。
    # 这类静默失效正是本仓最贵的那种。
    import hashlib

    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode())
        h.update(b"\0")
    if blob.get("texts_sha") != h.hexdigest():
        raise SystemExit(
            "向量缓存与当前 schema 对不上（texts_sha 不同）—— **不将就**。"
            "要么用对得上的 schema，要么重建缓存（那是 178k）。"
        )
    fv = blob["field_vectors"]
    print(f"命中向量缓存：{blob['model']} · {len(fv)} 条（本次 embed 只花问句那 40 条）")

    qv = []
    for i in range(0, len(items), 10):
        qv.extend(norm(v) for v in embed([it["q"] for it in items[i : i + 10]],
                                         args.embed_model, key, base))

    labels = [f"{f['doctype']}.{f['fieldname']}" for f in fields]
    want = [set(it["expected"]) for it in items]
    want_dt = [{e.rsplit(".", 1)[0] for e in it["expected"]} for it in items]
    meta = {f["doctype"]: f for f in fields}
    # 父子映射**从活站点导出的 schema 里算**，不手写。
    # 一张子表被多个父表挂时归第一个 —— 与 tests/dsl/fixtures/child-tables.json 同源口径。
    parent_of: dict[str, str] = {}
    for f in fields:
        if f["fieldtype"] == "Table" and f["options"]:
            parent_of.setdefault(f["options"], f["doctype"])

    sims = [[sum(a * b for a, b in zip(q, v)) for v in fv] for q in qv]

    # ---- 候选清单：字段分数 max 聚合到 DocType，取 Top-N ----
    cand_lists = []
    for s in sims:
        best = {}
        for i, f in enumerate(fields):
            if s[i] > best.get(f["doctype"], -2):
                best[f["doctype"]] = s[i]
        cand_lists.append([dt for dt, _ in sorted(best.items(), key=lambda kv: -kv[1])[:N_CANDIDATES]])

    # ---- L1 · 设施自检 ----
    contains = sum(1 for c, w in zip(cand_lists, want_dt) if w & set(c))
    print(f"\nL1 设施自检：候选清单（N={N_CANDIDATES}）含正确单据 **{contains}/{len(items)}**"
          f"  ⇒ {'✅' if contains == len(items) else '❌ 后面的数不看'}")
    if contains != len(items):
        raise SystemExit(1)

    # ---- L2 · 模型选单据 ----
    picked, detail = [], []
    for n, (item, cands) in enumerate(zip(items, cand_lists)):
        listing = "\n".join(
            f"{i + 1}. {dt} | {meta[dt]['module']} | {meta[dt]['rowcount']} 行"
            + (f" | 是「{parent_of[dt]}」的子表" if dt in parent_of else "")
            for i, dt in enumerate(cands)
        )
        reply = chat(PICK_PROMPT.format(question=item["q"], candidates=listing),
                     model=args.model, base_url=base, api_key=key)
        m = re.search(r"\d+", reply or "")
        idx = int(m.group()) - 1 if m else -1
        chosen = cands[idx] if 0 <= idx < len(cands) else None
        picked.append(chosen)
        ok = chosen in want_dt[n]
        detail.append({"q": item["q"], "expected_doctypes": sorted(want_dt[n]),
                       "picked": chosen, "correct": ok, "raw": (reply or "").strip()[:40]})
        print(f"  {n + 1:>2}/{len(items)}  {'✅' if ok else '❌'} 选了 {chosen}"
              f"  （期望 {sorted(want_dt[n])}）", flush=True)

    l2 = sum(1 for d in detail if d["correct"]) * 100 / len(items)
    print(f"\nL2 模型选单据准确率：**{l2:.1f}%**")

    # ---- L3 · 合成 ----
    ranked = []
    for n, chosen in enumerate(picked):
        keep = [i for i, f in enumerate(fields) if f["doctype"] == chosen] if chosen else []
        order = sorted(keep, key=lambda i: -sims[n][i])[:10]
        ranked.append([labels[i] for i in order])
    l3 = recall(ranked, want)
    print(f"L3 合成字段召回：{l3}   （四轮最好 Top-5 = 70.0，上限 92.5）")

    # ---- L4 · 分解模型自检 ----
    predicted = l2 * 0.925
    gap = abs(l3["top5"] - predicted)
    print(f"L4 分解模型自检：L2 × 92.5% = {predicted:.1f}%，实测合成 Top-5 = {l3['top5']:.1f}%"
          f"，偏差 **{gap:.1f}** 个点  ⇒ {'✅ ≤5' if gap <= 5 else '❌ >5，分解模型不成立'}")

    res = {"model": args.model, "embed_model": args.embed_model, "n_candidates": N_CANDIDATES,
           "usage": dict(USAGE), "L1_candidate_contains_truth": f"{contains}/{len(items)}",
           "L2_doctype_pick_accuracy": round(l2, 1), "L3_composite_field_recall": l3,
           "L4_predicted_from_decomposition": round(predicted, 1), "L4_gap": round(gap, 1),
           "ks": list(KS), "detail": detail}
    json.dump(res, open(args.out, "w"), ensure_ascii=False, indent=2)
    print(f"\n实际用量（按 API 回的数）：{USAGE['calls']} 次 chat · "
          f"{USAGE['in']} in / {USAGE['out']} out / reasoning {USAGE['reasoning']} · "
          f"embed {USAGE['embed_tokens']}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
