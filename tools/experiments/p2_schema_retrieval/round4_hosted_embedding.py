#!/usr/bin/env python3
"""P2.0R 第四轮 · 换托管 embedding 重量基线。

跑法：
    python3 tools/experiments/p2_schema_retrieval/round4_hosted_embedding.py \
        --schema /tmp/schema.json \
        --eval   tools/experiments/p2_schema_retrieval/eval-set.json \
        --out    tools/experiments/p2_schema_retrieval/results-round4.json \
        --cache  /tmp/p2_vectors_v4.json \
        --embed-model text-embedding-v4

## 为什么这一轮能开（plan §0）

前三轮全部用本地 `qwen3-embedding:0.6b` 量的，而**本地模型已被禁用**（人 2026-08-27）。
⇒ 不是「换个模型看能不能更好」，是**基线是用一把不再允许使用的尺子量的**。

## 除嵌入模型外，一个变量都不动

同一份 40 条评测集 · 同一段 `described` 索引文本 · 同一个 `business` 范围 · 同一套 Top-k 口径。
索引文本与评分函数**直接从 `index_and_eval.py` import**，不复制第二份 ——
复制一份就有了「两边悄悄错开」的可能，而错开的表现是一个看着能比、其实不能比的数。

## 预算

整站 6,350 条约 **176k embedding token**（探针实测每条约 28）。
**向量必须落盘缓存**，否则每次复跑都是又一个 176k。用量按 API 回的数记，**不自报**。
"""

import argparse
import json
import math
import pathlib
import ssl
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
# 索引文本取第一轮那份（`described`），召回口径取第三轮那份 ——
# **两者都是 import 进来的，不复制第二份**。复制一份就有了「两边悄悄错开」的可能，
# 而错开的表现是一个看着能比、其实不能比的数。
from index_and_eval import field_text  # noqa: E402
from score_fusion import KS, recall  # noqa: E402

BASE_DEFAULT = "https://dashscope.aliyuncs.com/compatible-mode/v1"
EMBED_BATCH = 10  # 兼容口对 embeddings 的单次条数限制偏小，取 10 稳妥
USAGE = {"calls": 0, "tokens": 0}


def _ssl_context():
    """certifi 且**惰性 import** —— 同 `agenerp/routing/adapter.py:103`。

    CI 的 `unit-and-contracts` job 只 `pip install pytest`，模块级 import 会当场 ImportError。
    """
    import certifi

    return ssl.create_default_context(cafile=certifi.where())


def embed(texts: list[str], model: str, key: str, base: str) -> list[list[float]]:
    req = urllib.request.Request(
        f"{base}/embeddings",
        data=json.dumps({"model": model, "input": texts}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=300, context=_ssl_context()) as res:
        body = json.loads(res.read())
    if body.get("error"):
        raise RuntimeError(f"百炼回错：{body['error']}")
    USAGE["calls"] += 1
    USAGE["tokens"] += (body.get("usage") or {}).get("total_tokens") or 0
    # **按 index 排回原序** —— 兼容口不保证返回顺序，错序会让整轮的数变成噪音。
    rows = sorted(body["data"], key=lambda d: d["index"])
    return [r["embedding"] for r in rows]


def norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def embed_all(texts, model, key, base, tag):
    out, t0 = [], time.time()
    for i in range(0, len(texts), EMBED_BATCH):
        out.extend(norm(v) for v in embed(texts[i : i + EMBED_BATCH], model, key, base))
        if (i // EMBED_BATCH) % 40 == 0:
            print(f"  [{tag}] {min(i + EMBED_BATCH, len(texts))}/{len(texts)}"
                  f"  {round(time.time() - t0)}s  累计 {USAGE['tokens']} token", flush=True)
    print(f"  [{tag}] 完成 {len(out)} 条，{round(time.time() - t0, 1)}s，"
          f"{USAGE['tokens']} token", flush=True)
    return out


def texts_sha(texts):
    import hashlib

    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode())
        h.update(b"\0")
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--embed-model", default="text-embedding-v4")
    args = ap.parse_args()

    import os

    key = os.environ.get("AGENERP_LLM_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise SystemExit("没有 AGENERP_LLM_API_KEY / DASHSCOPE_API_KEY —— 不猜凭据")
    base = os.environ.get("AGENERP_LLM_BASE_URL", BASE_DEFAULT)

    fields = json.load(open(args.schema))["fields"]
    items = json.load(open(args.eval))["items"]
    texts = [field_text(f, "described") for f in fields]
    print(f"字段 {len(fields)} · 问句 {len(items)} · 嵌入模型 {args.embed_model}")

    cache = pathlib.Path(args.cache)
    sha = texts_sha(texts)
    fv = None
    if cache.exists():
        blob = json.load(open(cache))
        if blob.get("model") == args.embed_model and blob.get("texts_sha") == sha:
            print(f"命中向量缓存 {cache} —— 本次不重花那 176k")
            USAGE.update(blob.get("usage") or {})
            fv = blob["field_vectors"]
    if fv is None:
        fv = embed_all(texts, args.embed_model, key, base, "fields")
        json.dump({"model": args.embed_model, "texts_sha": sha,
                   "usage": dict(USAGE), "field_vectors": fv}, open(cache, "w"))
        print(f"向量已缓存到 {cache}")

    qv = embed_all([it["q"] for it in items], args.embed_model, key, base, "queries")

    # ---- E1 · 设施自检 ----
    dims = {len(fv[0]), len(qv[0])}
    print(f"\nE1 设施自检：字段向量维度 {len(fv[0])} · 问句向量维度 {len(qv[0])}"
          f"  ⇒ {'✅ 同维' if len(dims) == 1 else '❌ 不同维，后面的数一概不看'}")
    if len(dims) != 1:
        raise SystemExit(1)

    labels = [f"{f['doctype']}.{f['fieldname']}" for f in fields]
    want = [set(it["expected"]) for it in items]
    want_dt = [{e.rsplit(".", 1)[0] for e in it["expected"]} for it in items]

    sims = [[sum(a * b for a, b in zip(q, v)) for v in fv] for q in qv]

    def rank(keep_fn=None):
        out = []
        for n, s in enumerate(sims):
            idx = range(len(fields)) if keep_fn is None else keep_fn(n)
            order = sorted(idx, key=lambda i: -s[i])[:10]
            out.append([labels[i] for i in order])
        return out

    # ---- E2 · business × described ----
    base_ranked = rank()
    e2 = recall(base_ranked, want)
    print(f"\nE2 business × described：{e2}   （前三轮基线 Top-5 = 65.0）")

    # ---- E3 · oracle ----
    def oracle_keep(n):
        return [i for i, f in enumerate(fields) if f["doctype"] in want_dt[n]]

    e3 = recall(rank(oracle_keep), want)
    print(f"E3 oracle（给定 ground-truth DocType）：{e3}   （第一轮 Top-5 = 97.5）")

    # ---- E4 · miss 的形态 ----
    miss = [n for n, r in enumerate(base_ranked) if not (want[n] & set(r[:5]))]
    no_dt = [n for n in miss
             if not (want_dt[n] & {g.rsplit(".", 1)[0] for g in base_ranked[n][:5]})]
    share = round(len(no_dt) * 100 / len(miss), 1) if miss else None
    print(f"E4 miss {len(miss)}/40，其中「正确 DocType 连出现都没出现」{len(no_dt)}"
          f"（{share}%）  （第一轮 78%）")

    res = {
        "embed_model": args.embed_model,
        "n_items": len(items),
        "n_fields": len(fields),
        "dim": len(fv[0]),
        "usage": dict(USAGE),
        "E2_business_described": e2,
        "E3_oracle_described": e3,
        "E4_missing_doctype_in_top5": {"n_miss": len(miss), "n_no_doctype": len(no_dt),
                                       "share": share},
        "ks": list(KS),
        "detail": [
            {"q": items[n]["q"], "expected": items[n]["expected"], "top5": base_ranked[n][:5],
             "rank": next((j + 1 for j, g in enumerate(base_ranked[n]) if g in want[n]), None)}
            for n in range(len(items))
        ],
    }
    json.dump(res, open(args.out, "w"), ensure_ascii=False, indent=2)
    print(f"\n实际用量（按 API 回的数）：{USAGE['calls']} 次调用 · {USAGE['tokens']} token")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
