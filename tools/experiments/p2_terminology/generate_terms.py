#!/usr/bin/env python3
"""P2.7 · 术语层生成器：给字段起中文名。

跑法：
    python3 tools/experiments/p2_terminology/generate_terms.py \
        --schema /tmp/schema.json \
        --out    agenerp/i18n/terms.zh.json \
        --labels tests/i18n/fixtures/english-labels.json \
        --model  qwen3.5:0.8b            # 本地 Ollama，API 成本 0

`--probe N` 只跑前 N 个字段，用来**先看质量再决定要不要花钱**（plan §2.1）。

## 三条设计约束

1. **范围跟着路线 C 走**：只做车间工人可读的三张表 + 它们挂的子表（317 个字段）。
   整站 6,350 个是 20 倍量，而本仓有过一次单问答烧 13.6 万 token 的实测。
2. **首选本地模型，API 成本 0**（D-17）。本地不过 T3 那一关才升级。
3. **模型只负责起名字，其余全是规则**（硬约束 ③）：
   哪些字段要起名、起完之后合不合格、指不指得回真实字段 —— 都由代码判，不问模型。
"""

import argparse
import json
import re
import sys
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
BATCH = 20
CJK = re.compile(r"[一-鿿]")

WORKER_DOCTYPES = ("Work Order", "Stock Entry", "Item")

PROMPT = """你是 ERP 系统的中文术语专家。下面每一行是一个 ERPNext 字段，格式是：
<序号>. <单据名>.<字段名> | 英文标签 | 类型 | 关联

请给每个字段起一个**简短的中文列名**，用于表格表头。要求：

- 只输出中文，2 到 8 个字，不要标点、不要英文、不要解释
- 是**列名**不是句子（例如「过账日期」而不是「这张单据的过账日期」）
- 忠实于字段的实际含义；英文标签与字段名不一致时**以字段名为准**
- 严格按 `<序号>. <中文名>` 逐行输出，不要多写任何一行

两条领域事实，照它来：

1. **类型是 Check 的字段是勾选框，值只有是/否。**
   它的列名**必须**以「是否」「允许」「启用」「已」「需」「可」之一开头，
   **不许起成名词，也不许起成动作短语**。
   - `has_batch_no` → **「是否批次管理」**；起成「批次号」或「有批次号」都是错的
   - `use_multi_level_bom` → **「是否使用多级BOM」**；起成「使用多级BOM」是错的
   - `skip_transfer` → **「是否跳过调拨」**；起成「跳过调拨至在制仓」是错的
   - `set_basic_rate_manually` → **「是否手动设定基本价」**
2. 这是**制造业** ERP。`Item` 指的是**物料**，不是「项目」；
   `Project` 才是项目。`Stock Entry` 是库存调拨单。

字段：
{rows}
"""


# 真实用量的累计器。**不自报，按 API 回的数记。**
USAGE = {"calls": 0, "in": 0, "out": 0, "reasoning": 0}


def ollama_chat(model: str, prompt: str) -> str:
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "think": False,
                "options": {"temperature": 0.1},
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as res:
        body = json.loads(res.read())
    USAGE["calls"] += 1
    USAGE["in"] += body.get("prompt_eval_count") or 0
    USAGE["out"] += body.get("eval_count") or 0
    return body["message"]["content"]


def _ssl_context():
    """macOS 上 Python 的 `ssl` 不走系统钥匙串，直连百炼会
    `CERTIFICATE_VERIFY_FAILED`（`curl` 却是通的，所以很容易误判成「网络问题」）。

    ⚠️ **`import certifi` 刻意写在函数体内**，与 `agenerp/routing/adapter.py:103` 同一条纪律：
    CI 的 `unit-and-contracts` job 只 `pip install pytest`，模块级 import 会让它当场 ImportError。
    """
    import ssl

    import certifi

    return ssl.create_default_context(cafile=certifi.where())


def dashscope_chat(model: str, prompt: str) -> str:
    """百炼（OpenAI 兼容口）。

    🔴 **`enable_thinking: false` 不是可选项，是预算的前提。**
    2026-08-27 实测同一个问句：
        开思考 → `completion_tokens` **1808**，其中 `reasoning_tokens` **1800**
        关思考 → `completion_tokens` **4**
    **差 450 倍，而关掉之后答案反而更准**（`是否启用批次管理` vs `批次管理`）。
    默认开着思考时，整站 6,350 个字段的账会从 273k 变成 1–2M ——
    那是 P1 那次 runaway（13.6 万）的十倍量级。
    """
    import os

    key = os.environ.get("AGENERP_LLM_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("没有 AGENERP_LLM_API_KEY / DASHSCOPE_API_KEY —— 不猜凭据")
    base = os.environ.get(
        "AGENERP_LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(
            {
                "model": model,
                "enable_thinking": False,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=600, context=_ssl_context()) as res:
        body = json.loads(res.read())
    if body.get("error"):
        raise RuntimeError(f"百炼回错：{body['error']}")
    usage = body.get("usage") or {}
    USAGE["calls"] += 1
    USAGE["in"] += usage.get("prompt_tokens") or 0
    USAGE["out"] += usage.get("completion_tokens") or 0
    USAGE["reasoning"] += (usage.get("completion_tokens_details") or {}).get(
        "reasoning_tokens"
    ) or 0
    return body["choices"][0]["message"]["content"]


def chat(model: str, prompt: str) -> str:
    """按模型名分流。`dashscope:` 前缀走百炼，其余走本地 Ollama。"""
    if model.startswith("dashscope:"):
        return dashscope_chat(model.split(":", 1)[1], prompt)
    return ollama_chat(model, prompt)


def in_scope(schema_rows):
    children = {
        f["options"]
        for f in schema_rows
        if f["doctype"] in WORKER_DOCTYPES and f["fieldtype"] == "Table" and f["options"]
    }
    scope = set(WORKER_DOCTYPES) | children
    return [f for f in schema_rows if f["doctype"] in scope]


def describe(index: int, field: dict) -> str:
    return (
        f"{index}. {field['doctype']}.{field['fieldname']}"
        f" | {field['label'] or '(无)'} | {field['fieldtype']}"
        f" | {field['options'] or '(无)'}"
    )


def clean(name: str) -> str:
    """把模型回显的输入格式剥掉，只留中文列名。

    ⚠️ **这是实测出来的**：小模型会把提示里的分隔符一起抄回来，
    例如 `是否成品 | Is Finished Item`。第一版没剥，这类被「过长」规则丢掉，
    覆盖率停在 **218/317 = 68.8%** —— 而**中文答案本身是对的**。
    ⇒ 那是**解析问题不是质量问题**，修在生成器这一侧（**判据一个字没动**）。
    """
    for sep in ("|", "｜", "(", "（", " - ", "—", "//"):
        if sep in name:
            name = name.split(sep, 1)[0]
    # ⚠️ **实测**：模型会把单据名当前缀写进来（`工单工序.工作站`），20/317 条如此。
    # 中文列名里本来就不该有点号 ⇒ 只留最后一段。
    if "." in name:
        name = name.rsplit(".", 1)[-1]
    return name.strip().strip("。.，,：:；;「」『』\"'`* ")


def parse(reply: str, batch: list[dict]) -> dict[str, str]:
    """按序号回填。**认不出的就不要**，不猜、不顺延 —— 顺延会让整批错位。"""
    out: dict[str, str] = {}
    for line in reply.splitlines():
        m = re.match(r"\s*(\d+)\s*[.、)]\s*(.+?)\s*$", line)
        if not m:
            continue
        idx = int(m.group(1)) - 1
        name = clean(m.group(2))
        if 0 <= idx < len(batch) and name:
            field = batch[idx]
            out[f"{field['doctype']}.{field['fieldname']}"] = name
    return out


RETRY_PROMPT = """给下面这个 ERPNext 字段起一个简短的中文列名。

单据：{doctype}
字段名：{fieldname}
英文标签：{label}
类型：{fieldtype}
关联：{options}

要求：**只输出中文列名本身**，2 到 8 个字。
不要英文、不要标点、不要序号、不要解释、不要换行。
英文标签与字段名不一致时以字段名为准。
类型是 Check 时读成是非说法（「是否…」「允许…」），不要起成名词。
这是制造业 ERP：Item 指物料不是项目。"""


def why_rejected(key: str, value: str, english: dict, fieldname: dict) -> str:
    """规则面的合格判定。**只有这一处**，批量与重试共用，不写第二份。"""
    v = (value or "").strip()
    if not v or len(v) > 20:
        return f"空或过长：{v!r}"
    if not CJK.search(v):
        return f"不含中文：{v!r}"
    if v == english.get(key) or v == fieldname.get(key):
        return f"抄了英文/fieldname：{v!r}"
    return ""


def retry_one(model: str, field: dict) -> str:
    reply = chat(
        model,
        RETRY_PROMPT.format(
            doctype=field["doctype"],
            fieldname=field["fieldname"],
            label=field["label"] or "(无)",
            fieldtype=field["fieldtype"],
            options=field["options"] or "(无)",
        ),
    )
    return clean(reply.strip().splitlines()[0] if reply.strip() else "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--model", default="qwen3.5:0.8b")
    ap.add_argument("--probe", type=int, default=0)
    args = ap.parse_args()

    site = json.load(open(args.schema))
    fields = in_scope(site["fields"])
    if args.probe:
        fields = fields[: args.probe]
    print(f"范围：{len({f['doctype'] for f in fields})} 张表 / {len(fields)} 个字段 · 模型 {args.model}")

    terms: dict[str, str] = {}
    t0 = time.time()
    for start in range(0, len(fields), BATCH):
        batch = fields[start : start + BATCH]
        rows = "\n".join(describe(i + 1, f) for i, f in enumerate(batch))
        reply = chat(args.model, PROMPT.format(rows=rows))
        got = parse(reply, batch)
        terms.update(got)
        print(f"  {start + len(batch)}/{len(fields)}  本批回填 {len(got)}/{len(batch)}"
              f"  {round(time.time() - t0)}s", flush=True)

    # ---- 规则面的过滤：不合格的**不入库**（硬约束 ④：宁缺毋滥）----
    english = {f"{f['doctype']}.{f['fieldname']}": (f["label"] or "") for f in fields}
    fieldname = {f"{f['doctype']}.{f['fieldname']}": f["fieldname"] for f in fields}
    by_key = {f"{f['doctype']}.{f['fieldname']}": f for f in fields}

    kept, dropped = {}, {}
    for key, value in terms.items():
        why = why_rejected(key, value, english, fieldname)
        (dropped if why else kept).__setitem__(key, why or value.strip())
    print(f"\n批量之后：合格 {len(kept)} / 范围 {len(fields)}"
          f"  —— 不合格 {len(dropped)}，没回填 {len(fields) - len(terms)}")

    # ---- 逐条重试：批量里被规则挡下的与压根没回填的，单独再问 ----
    # ⚠️ **为什么是重试而不是继续加剥离规则**：实测剩下的失败形态是
    # 「中文 English」用**空格**分隔。按 ASCII 切会误伤「BOM 编号」这类合法答案。
    # 重试成本≈0（本地模型），而误伤是不可见的 —— 宁可多问几次。
    todo = sorted(set(by_key) - set(kept))
    for attempt in (1, 2):
        if not todo:
            break
        print(f"  重试第 {attempt} 轮：{len(todo)} 条", flush=True)
        still = []
        for key in todo:
            value = retry_one(args.model, by_key[key])
            if why_rejected(key, value, english, fieldname):
                still.append(key)
            else:
                kept[key] = value
        todo = still

    print(f"\n合格 {len(kept)} / 范围 {len(fields)} = {len(kept) * 100 / len(fields):.1f}%")
    if todo:
        print(f"  两轮重试后仍不合格 {len(todo)} 条 —— **不入库**：")
        for key in todo[:10]:
            print(f"    {key}  英文「{english.get(key)}」")

    if args.probe:
        print("\n（探针模式，不落盘）抽样：")
        for key, value in list(kept.items())[:20]:
            print(f"    {key:<44} 「{value}」   英文「{english.get(key)}」")
        return

    json.dump(
        {
            "provenance": {
                "site": site.get("site", "frontend"),
                "generated_by": "tools/experiments/p2_terminology/generate_terms.py",
                "generated_on": "2026-08-27",
                "model": args.model if ":" in args.model else f"ollama:{args.model}",
                "scope": "车间工人可读的三张表及其子表（路线 C）",
                "note": "不合格的一律不入库，不是先留着再说。",
                # 🔴 **用量按 API 回的数记，不是我算的**。自报的账不是账。
                "usage": dict(USAGE),
            },
            "terms": dict(sorted(kept.items())),
        },
        open(args.out, "w"),
        ensure_ascii=False,
        indent=2,
    )
    json.dump(dict(sorted(english.items())), open(args.labels, "w"), ensure_ascii=False, indent=2)
    print(f"\n→ {args.out}\n→ {args.labels}")


if __name__ == "__main__":
    sys.exit(main())
