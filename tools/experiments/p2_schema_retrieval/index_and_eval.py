#!/usr/bin/env python3
"""P2.0R · 复现 Spike 07 并把「选单据」与「选字段」切开单独量。

跑法（本机，Ollama 需在 127.0.0.1:11434 上）：
    python3 tools/experiments/p2_schema_retrieval/index_and_eval.py \
        --schema /tmp/schema.json \
        --eval   tools/experiments/p2_schema_retrieval/eval-set.json \
        --out    tools/experiments/p2_schema_retrieval/results.json

嵌入模型刻意与 Spike 07 相同（`qwen3-embedding:0.6b`）—— 换模型这一轮不测，
理由与重开条件写在 plan §11。纯标准库，无 numpy / faiss。

五格（预测写在 plan §2，跑之前已提交）：
    P0  现役 schema_search（DocType 名 + 模块名子串匹配）的字段级命中
    P1  business × described
    P2  live × described
    P3  失败方式分类：miss 里「字段名对、DocType 错」占多少
    P4  oracle 消融：给定 ground-truth DocType，只在其字段内检索
"""

import argparse
import json
import math
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "qwen3-embedding:0.6b"
BATCH = 64
KS = (1, 3, 5, 10)

LAYOUT_KIND = {
    "Currency": "金额",
    "Float": "数量/数值",
    "Int": "整数",
    "Date": "日期",
    "Datetime": "日期时间",
    "Percent": "百分比",
    "Check": "是否",
    "Data": "文本",
    "Small Text": "文本",
    "Text": "文本",
    "Text Editor": "富文本",
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


def field_text(f, style):
    """索引文本 —— 检索质量的主要变量，因此做 A/B。两种写法逐字沿用 Spike 07。"""
    if style == "raw":
        return f"{f['doctype']}.{f['fieldname']} {f['label']} {f['fieldtype']} {f['options']}".strip()
    ft, opt = f["fieldtype"], f["options"]
    if ft == "Link":
        kind = "关联到 " + opt
    elif ft == "Select":
        kind = "可选项 " + opt.replace("\n", "/")
    elif ft == "Table":
        kind = "子表 " + opt
    else:
        kind = LAYOUT_KIND.get(ft, ft)
    scope = "子表行" if f["istable"] else "单据主表"
    return (
        f"单据 {f['doctype']} 的{scope}字段「{f['label'] or f['fieldname']}」"
        f"（字段名 {f['fieldname']}，类型 {kind}）"
    )


def build(fields, style):
    texts = [field_text(f, style) for f in fields]
    vecs, t0 = [], time.time()
    for i in range(0, len(texts), BATCH):
        vecs.extend(norm(v) for v in embed(texts[i : i + BATCH]))
        if (i // BATCH) % 20 == 0:
            print(f"  [{style}] {min(i + BATCH, len(texts))}/{len(texts)}  {round(time.time() - t0)}s", flush=True)
    print(f"  [{style}] 建索引完成 {len(vecs)} 条，{round(time.time() - t0, 1)}s", flush=True)
    return vecs


def rank(qvec, fields, vecs, keep=None):
    """余弦相似度排序。keep 非 None 时只在该下标集合内排（oracle 消融用）。"""
    idx = range(len(fields)) if keep is None else keep
    scored = [(sum(a * b for a, b in zip(qvec, vecs[i])), i) for i in idx]
    scored.sort(reverse=True)
    return [fields[i] for _, i in scored[:10]]


def score(detail):
    total = len(detail)
    return {
        f"top{k}": round(sum(1 for d in detail if d["rank"] and d["rank"] <= k) * 100 / total, 1)
        for k in KS
    }


def evaluate(items, qvecs, fields, vecs, keep_fn=None):
    detail = []
    for item, qv in zip(items, qvecs):
        keep = keep_fn(item) if keep_fn else None
        if keep is not None and not keep:
            # oracle 里目标 DocType 一个字段都没入索引 —— 记为不可能命中，不静默跳过
            detail.append({"q": item["q"], "rank": None, "expected": item["expected"], "top5": [], "note": "候选集为空"})
            continue
        top = rank(qv, fields, vecs, keep)
        want = set(item["expected"])
        got = [f"{f['doctype']}.{f['fieldname']}" for f in top]
        hit = next((i + 1 for i, g in enumerate(got) if g in want), None)
        detail.append({"q": item["q"], "rank": hit, "expected": item["expected"], "top5": got[:5]})
    return {"recall": score(detail), "detail": detail}


def classify_misses(result):
    """P3 的判法**事先写死在 plan §2**：一条 miss 的 Top-5 里若存在某项，其 fieldname
    与某个 expected 的 fieldname 相同而 DocType 不同 → 计「单据错」。"""
    misses = [d for d in result["detail"] if not d["rank"] or d["rank"] > 5]
    wrong_doc = []
    for d in misses:
        want = {(e.rsplit(".", 1)[0], e.rsplit(".", 1)[1]) for e in d["expected"]}
        want_fn = {fn for _, fn in want}
        for g in d["top5"]:
            gdt, gfn = g.rsplit(".", 1)
            if gfn in want_fn and gdt not in {dt for dt, _ in want}:
                wrong_doc.append({"q": d["q"], "expected": d["expected"], "got": g})
                break
    return {
        "n_miss": len(misses),
        "n_wrong_doctype_right_fieldname": len(wrong_doc),
        "share": round(len(wrong_doc) * 100 / len(misses), 1) if misses else None,
        "examples": wrong_doc[:8],
        "all_misses": [{"q": d["q"], "expected": d["expected"], "top5": d["top5"]} for d in misses],
    }


def schema_search_baseline(items, fields):
    """P0 · 现役 `agenerp/tools/site_scope.py::schema_search` 的口径复刻。

    命中口径：关键词对 `"{doctype} {module}".lower()` 的子串匹配。
    问句原样按空白切词（该函数的 `_keywords` 就是这么做的）。
    ⚠️ 这是**地板自检**，不是对 schema_search 设计的评判 —— 它本来就是
    DocType 召回器，从不返回字段（见 plan §1.2）。
    """
    entries = sorted({(f["doctype"], f["module"]) for f in fields})
    by_dt = {}
    for f in fields:
        by_dt.setdefault(f["doctype"], []).append(f)
    detail = []
    for item in items:
        words = [w for w in item["q"].replace("，", " ").replace("？", " ").split() if w]
        words = [w.lower() for w in words]
        matched = [
            dt for dt, mod in entries if any(w in f"{dt} {mod}".lower() for w in words)
        ]
        got = [f"{f['doctype']}.{f['fieldname']}" for dt in matched for f in by_dt[dt]][:10]
        want = set(item["expected"])
        hit = next((i + 1 for i, g in enumerate(got) if g in want), None)
        detail.append({"q": item["q"], "rank": hit, "expected": item["expected"], "top5": got[:5],
                       "n_doctypes_matched": len(matched)})
    return {"recall": score(detail), "detail": detail}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    all_fields = json.load(open(args.schema))["fields"]
    items = json.load(open(args.eval))["items"]
    print(f"字段 {len(all_fields)}，问句 {len(items)}")

    live_idx = {i for i, f in enumerate(all_fields) if f["rowcount"] > 0}
    print(f"business DocType {len({f['doctype'] for f in all_fields})} / 字段 {len(all_fields)}")
    print(f"live     DocType {len({all_fields[i]['doctype'] for i in live_idx})} / 字段 {len(live_idx)}")

    print("嵌入问句 …", flush=True)
    qvecs = [norm(v) for v in embed([it["q"] for it in items])]

    results = {
        "embed_model": EMBED_MODEL,
        "n_items": len(items),
        "scale": {
            "business_doctypes": len({f["doctype"] for f in all_fields}),
            "business_fields": len(all_fields),
            "live_doctypes": len({all_fields[i]["doctype"] for i in live_idx}),
            "live_fields": len(live_idx),
        },
    }

    print("\n=== P0 · 现役 schema_search 地板自检 ===", flush=True)
    p0 = schema_search_baseline(items, all_fields)
    print("  ", p0["recall"])
    results["P0_schema_search"] = p0

    for style in ("raw", "described"):
        print(f"\n=== 建索引 style={style}（business 全量，live 复用同一批向量）===", flush=True)
        vecs = build(all_fields, style)

        biz = evaluate(items, qvecs, all_fields, vecs)
        print(f"  business × {style}: {biz['recall']}", flush=True)
        results[f"business_{style}"] = biz

        live = evaluate(items, qvecs, all_fields, vecs, keep_fn=lambda _it: live_idx)
        print(f"  live     × {style}: {live['recall']}", flush=True)
        results[f"live_{style}"] = live

        if style == "described":
            results["P3_failure_modes"] = {
                "business": classify_misses(biz),
                "live": classify_misses(live),
            }
            print("\n=== P4 · oracle 消融（给定 ground-truth DocType）===", flush=True)

            def oracle_keep(it):
                want_dt = {e.rsplit(".", 1)[0] for e in it["expected"]}
                return {i for i, f in enumerate(all_fields) if f["doctype"] in want_dt}

            orc = evaluate(items, qvecs, all_fields, vecs, keep_fn=oracle_keep)
            print("  oracle × described:", orc["recall"], flush=True)
            results["P4_oracle_described"] = orc

    json.dump(results, open(args.out, "w"), ensure_ascii=False, indent=2)
    print(f"\n→ {args.out}")


if __name__ == "__main__":
    main()
