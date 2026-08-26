#!/usr/bin/env python3
"""P2.0R 第二轮 · DocType 消歧：结构化收敛能不能补上那 35 个点。

跑法：
    python3 tools/experiments/p2_schema_retrieval/doctype_disambiguation.py \
        --schema /tmp/schema.json \
        --eval   tools/experiments/p2_schema_retrieval/eval-set.json \
        --out    tools/experiments/p2_schema_retrieval/results-round2.json

五格（预测写在 plan §2，跑之前已提交 `18d6634`）：
    Q1a  字段分数按 DocType 取 max 聚合 → DocType recall@k
    Q1b  DocType 级人话描述单独建向量  → DocType recall@k
    Q2   把子表并进父表（单据族）        → 族 recall@k
    Q3   🔴 两段式：族 Top-3 收敛 → 字段 Top-5
    Q4   上一轮 miss 里「正确族但错表」的真实占比

复用上一轮的 described 字段向量（重算一遍，因为向量没落盘；同一模型同一文本，
数应当与 results.json 完全一致 —— 这本身是一道设施自检）。
"""

import argparse
import json
import math
import statistics
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "qwen3-embedding:0.6b"
BATCH = 64
KS = (1, 3, 5, 10)

KIND = {
    "Currency": "金额", "Float": "数量/数值", "Int": "整数", "Date": "日期",
    "Datetime": "日期时间", "Percent": "百分比", "Check": "是否", "Data": "文本",
    "Small Text": "文本", "Text": "文本", "Text Editor": "富文本",
}


def embed(texts):
    req = urllib.request.Request(
        f"{OLLAMA}/api/embed",
        data=json.dumps({"model": EMBED_MODEL, "input": texts}).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=900).read())["embeddings"]


def norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def embed_all(texts, tag):
    out, t0 = [], time.time()
    for i in range(0, len(texts), BATCH):
        out.extend(norm(v) for v in embed(texts[i : i + BATCH]))
    print(f"  [{tag}] {len(out)} 条，{round(time.time() - t0, 1)}s", flush=True)
    return out


def field_text(f):
    ft, opt = f["fieldtype"], f["options"]
    if ft == "Link":
        kind = "关联到 " + opt
    elif ft == "Select":
        kind = "可选项 " + opt.replace("\n", "/")
    elif ft == "Table":
        kind = "子表 " + opt
    else:
        kind = KIND.get(ft, ft)
    scope = "子表行" if f["istable"] else "单据主表"
    return (
        f"单据 {f['doctype']} 的{scope}字段「{f['label'] or f['fieldname']}」"
        f"（字段名 {f['fieldname']}，类型 {kind}）"
    )


def build_families(fields):
    """单据族 = 一张父 DocType + 它通过 Table 字段挂的全部子表。

    子表可能被多张父表共用（ERPNext 里常见），此时**归给第一个引用它的父表**并记下冲突数
    —— 不静默处理，这个数要报出来。
    """
    child_of, shared = {}, 0
    for f in fields:
        if f["fieldtype"] == "Table" and f["options"]:
            child = f["options"]
            if child in child_of and child_of[child] != f["doctype"]:
                shared += 1
                continue
            child_of[child] = f["doctype"]
    doctypes = sorted({f["doctype"] for f in fields})
    family = {dt: child_of.get(dt, dt) for dt in doctypes}
    return family, shared


def recall(ranked_lists, wants):
    out = {}
    for k in KS:
        hit = sum(1 for r, w in zip(ranked_lists, wants) if w & set(r[:k]))
        out[f"top{k}"] = round(hit * 100 / len(wants), 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prev", default="tools/experiments/p2_schema_retrieval/results.json")
    args = ap.parse_args()

    fields = json.load(open(args.schema))["fields"]
    items = json.load(open(args.eval))["items"]
    doctypes = sorted({f["doctype"] for f in fields})
    print(f"字段 {len(fields)} · DocType {len(doctypes)} · 问句 {len(items)}")

    family, shared = build_families(fields)
    fam_members = {}
    for dt, fam in family.items():
        fam_members.setdefault(fam, []).append(dt)
    sizes = sorted((len(v) for v in fam_members.values()), reverse=True)
    print(f"单据族 {len(fam_members)} 个 · 最大族 {sizes[0]} 张表 · 中位 {statistics.median(sizes)}"
          f" · 被多父共用而未并入的子表 {shared} 处")

    print("嵌入 …", flush=True)
    qv = embed_all([it["q"] for it in items], "queries")
    fv = embed_all([field_text(f) for f in fields], "fields/described")

    # ---- 每条问句对每个字段的相似度（一次算完，后面全是聚合）----
    sims = [[sum(a * b for a, b in zip(q, v)) for v in fv] for q in qv]

    want_dt = [{e.rsplit(".", 1)[0] for e in it["expected"]} for it in items]
    want_fam = [{family[d] for d in w} for w in want_dt]
    want_field = [set(it["expected"]) for it in items]

    res = {"n_items": len(items), "embed_model": EMBED_MODEL,
           "families": len(fam_members), "largest_family": sizes[0], "shared_children": shared}

    # ---- 设施自检：字段级 business × described 应与上一轮完全一致 ----
    base_ranked = []
    for s in sims:
        order = sorted(range(len(fields)), key=lambda i: -s[i])[:10]
        base_ranked.append([f"{fields[i]['doctype']}.{fields[i]['fieldname']}" for i in order])
    res["selfcheck_field_business_described"] = recall(base_ranked, want_field)
    print("设施自检（应等于上一轮 business×described）:", res["selfcheck_field_business_described"])
    try:
        prev = json.load(open(args.prev))["business_described"]["recall"]
        res["selfcheck_matches_previous"] = res["selfcheck_field_business_described"] == prev
        print("  与上一轮逐格相等：", res["selfcheck_matches_previous"], "| 上一轮:", prev)
    except Exception as exc:  # noqa: BLE001
        res["selfcheck_matches_previous"] = f"未能读取上一轮结果: {exc}"

    # ---- Q1a · 字段分数 max 聚合到 DocType ----
    def agg_rank(keyfn):
        out = []
        for s in sims:
            best = {}
            for i, f in enumerate(fields):
                k = keyfn(f)
                if s[i] > best.get(k, -2):
                    best[k] = s[i]
            out.append([k for k, _ in sorted(best.items(), key=lambda kv: -kv[1])[:10]])
        return out

    q1a = agg_rank(lambda f: f["doctype"])
    res["Q1a_doctype_max_agg"] = recall(q1a, want_dt)
    print("Q1a DocType(max 聚合):", res["Q1a_doctype_max_agg"])

    # ---- Q1b · DocType 级人话描述向量 ----
    by_dt = {}
    for f in fields:
        by_dt.setdefault(f["doctype"], []).append(f)

    def dt_text(dt):
        fs = by_dt[dt]
        labels = [x["label"] or x["fieldname"] for x in fs if x["label"]][:12]
        kind = "子表" if fs[0]["istable"] else "单据"
        return (f"{kind} {dt}（模块 {fs[0]['module']}，共 {len(fs)} 个字段）"
                f"，主要字段：{'、'.join(labels)}")

    dv = embed_all([dt_text(d) for d in doctypes], "doctypes/described")
    q1b = []
    for q in qv:
        sc = [(sum(a * b for a, b in zip(q, v)), d) for v, d in zip(dv, doctypes)]
        sc.sort(reverse=True)
        q1b.append([d for _, d in sc[:10]])
    res["Q1b_doctype_level_embedding"] = recall(q1b, want_dt)
    print("Q1b DocType(独立描述向量):", res["Q1b_doctype_level_embedding"])

    # ---- Q2 · 族聚合 ----
    q2 = agg_rank(lambda f: family[f["doctype"]])
    res["Q2_family_max_agg"] = recall(q2, want_fam)
    print("Q2 单据族(max 聚合):", res["Q2_family_max_agg"])

    # ---- Q3 · 两段式：族 Top-3 收敛 → 字段 Top-5 ----
    idx_by_fam = {}
    for i, f in enumerate(fields):
        idx_by_fam.setdefault(family[f["doctype"]], []).append(i)

    q3_ranked, cand_sizes, q3_detail = [], [], []
    for n, (s, fams) in enumerate(zip(sims, q2)):
        keep = [i for fam in fams[:3] for i in idx_by_fam[fam]]
        cand_sizes.append(len(keep))
        order = sorted(keep, key=lambda i: -s[i])[:10]
        got = [f"{fields[i]['doctype']}.{fields[i]['fieldname']}" for i in order]
        q3_ranked.append(got)
        hit = next((j + 1 for j, g in enumerate(got) if g in want_field[n]), None)
        q3_detail.append({"q": items[n]["q"], "rank": hit, "expected": items[n]["expected"],
                          "families_top3": fams[:3], "n_candidates": len(keep), "top5": got[:5]})
    res["Q3_two_stage_family_top3"] = recall(q3_ranked, want_field)
    res["Q3_candidate_field_count"] = {
        "median": statistics.median(cand_sizes),
        "min": min(cand_sizes), "max": max(cand_sizes),
    }
    res["Q3_detail"] = q3_detail
    print("Q3 两段式(族 Top-3 → 字段):", res["Q3_two_stage_family_top3"])
    print("   候选字段数 中位", res["Q3_candidate_field_count"]["median"],
          "| 范围", res["Q3_candidate_field_count"]["min"], "-", res["Q3_candidate_field_count"]["max"])

    # ---- Q4 · 上一轮 miss 里「正确族但错表」占多少 ----
    q4 = {"n_miss": 0, "right_family_wrong_table": 0, "examples": []}
    for n, (r, w, wf) in enumerate(zip(base_ranked, want_field, want_fam)):
        if w & set(r[:5]):
            continue
        q4["n_miss"] += 1
        got_fams = {family[g.rsplit(".", 1)[0]] for g in r[:5]}
        if wf & got_fams:
            q4["right_family_wrong_table"] += 1
            q4["examples"].append({"q": items[n]["q"], "expected": items[n]["expected"], "top5": r[:5]})
    res["Q4_right_family_wrong_table"] = q4
    print(f"Q4 上一轮 miss {q4['n_miss']} 条，其中「正确族但错表」{q4['right_family_wrong_table']} 条")

    json.dump(res, open(args.out, "w"), ensure_ascii=False, indent=2)
    print(f"\n→ {args.out}")


if __name__ == "__main__":
    main()
