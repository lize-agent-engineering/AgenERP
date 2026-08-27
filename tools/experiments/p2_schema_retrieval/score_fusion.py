#!/usr/bin/env python3
"""P2.0R 第三轮 · 分数融合：不硬切，改加权重排。

跑法：
    python3 tools/experiments/p2_schema_retrieval/score_fusion.py \
        --schema /tmp/schema.json \
        --eval   tools/experiments/p2_schema_retrieval/eval-set.json \
        --out    tools/experiments/p2_schema_retrieval/results-round3.json \
        --cache  /tmp/p2_vectors.json

机制（写死在 plan §1.1，跑之前已提交 `9ff97bf`）：

    fused(f) = α · sim(q, f) + (1 − α) · famscore(family(f))
    famscore(F) = max over f' in F of sim(q, f')

`α = 1.0` 退化成基线（纯字段分，**必须恰好等于 65.0%**，这是设施自检 F1）。
`α = 0.0` 是「软两段式」：族排在前，但一个候选都不丢。

⚠️ **本脚本报全部 α 的曲线，不只报最优值**（plan §2.1 第 1 条）：
只报最优值 = 把一次网格搜索包装成一个发现。

向量落盘缓存到 `--cache`，后续轮次不必每次重算 145 秒。
"""

import argparse
import json
import math
import pathlib
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "qwen3-embedding:0.6b"
BATCH = 64
KS = (1, 3, 5, 10)
ALPHAS = [round(i / 10, 1) for i in range(11)]

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


def embed_all(texts, tag):
    out, t0 = [], time.time()
    for i in range(0, len(texts), BATCH):
        out.extend(norm(v) for v in embed(texts[i : i + BATCH]))
    print(f"  [{tag}] {len(out)} 条，{round(time.time() - t0, 1)}s", flush=True)
    return out


def build_families(fields):
    """单据族 —— 口径与第二轮**逐字相同**，否则三轮不可比。"""
    child_of = {}
    for f in fields:
        if f["fieldtype"] == "Table" and f["options"]:
            child_of.setdefault(f["options"], f["doctype"])
    return {dt: child_of.get(dt, dt) for dt in {f["doctype"] for f in fields}}


def recall(ranked, wants):
    return {
        f"top{k}": round(sum(1 for r, w in zip(ranked, wants) if w & set(r[:k])) * 100 / len(wants), 1)
        for k in KS
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default="/tmp/p2_vectors.json")
    args = ap.parse_args()

    fields = json.load(open(args.schema))["fields"]
    items = json.load(open(args.eval))["items"]
    texts = [field_text(f) for f in fields]

    cache = pathlib.Path(args.cache)
    if cache.exists():
        blob = json.load(open(cache))
        if blob.get("model") == EMBED_MODEL and blob.get("texts_sha") == _sha(texts):
            print(f"命中向量缓存 {cache}")
            fv = blob["field_vectors"]
        else:
            print("缓存与当前 schema/模型不匹配，重算")
            fv = None
    else:
        fv = None
    if fv is None:
        fv = embed_all(texts, "fields/described")
        json.dump({"model": EMBED_MODEL, "texts_sha": _sha(texts), "field_vectors": fv},
                  open(cache, "w"))
        print(f"向量已缓存到 {cache}")

    qv = embed_all([it["q"] for it in items], "queries")

    family = build_families(fields)
    fam_of = [family[f["doctype"]] for f in fields]
    labels = [f"{f['doctype']}.{f['fieldname']}" for f in fields]
    want = [set(it["expected"]) for it in items]
    want_dt = [{e.rsplit(".", 1)[0] for e in it["expected"]} for it in items]

    sims = [[sum(a * b for a, b in zip(q, v)) for v in fv] for q in qv]

    # 每条问句的族聚合分（max），口径同第二轮
    famscores = []
    for s in sims:
        best = {}
        for i, fam in enumerate(fam_of):
            if s[i] > best.get(fam, -2.0):
                best[fam] = s[i]
        famscores.append(best)

    curve, detail_by_alpha = {}, {}
    for alpha in ALPHAS:
        ranked = []
        for s, fam in zip(sims, famscores):
            # α=0 时族内全部同分 —— 用 sim 破平，这就是「软两段式」
            order = sorted(
                range(len(fields)),
                key=lambda i: (-(alpha * s[i] + (1 - alpha) * fam[fam_of[i]]), -s[i]),
            )[:10]
            ranked.append([labels[i] for i in order])
        curve[str(alpha)] = recall(ranked, want)
        detail_by_alpha[str(alpha)] = ranked
        print(f"  α={alpha:>3}  {curve[str(alpha)]}", flush=True)

    best_alpha = max(ALPHAS, key=lambda a: curve[str(a)]["top5"])
    top5s = [curve[str(a)]["top5"] for a in ALPHAS]
    spread = max(top5s) - min(top5s)

    # F4：最好一档的 miss 里「正确 DocType 连出现在 Top-5 都没有」的条数
    def missing_doctype_count(ranked):
        n = 0
        for r, w, wdt in zip(ranked, want, want_dt):
            if w & set(r[:5]):
                continue
            if not (wdt & {g.rsplit(".", 1)[0] for g in r[:5]}):
                n += 1
        return n

    res = {
        "embed_model": EMBED_MODEL,
        "n_items": len(items),
        "alpha_curve": curve,
        "best_alpha": best_alpha,
        "best_top5": curve[str(best_alpha)]["top5"],
        "baseline_alpha_1_top5": curve["1.0"]["top5"],
        "curve_spread_top5": round(spread, 1),
        "F4_missing_doctype_in_top5": {
            "baseline_alpha_1.0": missing_doctype_count(detail_by_alpha["1.0"]),
            f"best_alpha_{best_alpha}": missing_doctype_count(detail_by_alpha[str(best_alpha)]),
        },
        "best_detail_top5": [
            {"q": it["q"], "expected": it["expected"], "top5": r[:5]}
            for it, r in zip(items, detail_by_alpha[str(best_alpha)])
        ],
    }
    print(f"\n最优 α = {best_alpha} · Top-5 = {res['best_top5']}"
          f" · 基线(α=1.0) = {res['baseline_alpha_1_top5']}"
          f" · 曲线跨度 = {spread} 个点")
    print("F4 「正确 DocType 连出现都没出现」的 miss 条数：", res["F4_missing_doctype_in_top5"])

    json.dump(res, open(args.out, "w"), ensure_ascii=False, indent=2)
    print(f"\n→ {args.out}")


def _sha(texts):
    import hashlib

    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode())
        h.update(b"\0")
    return h.hexdigest()


if __name__ == "__main__":
    main()
