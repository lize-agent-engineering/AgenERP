"""独立评测集的入场核对 —— **零 token**，不调模型。

出题方说主答案与备选字段都对 `/tmp/schema.json` 逐字核对过。那是他们的快照；
本脚本对**活站点**独立再验一遍。理由很实在：`expected` 若指向一个站点上不存在的字段，
验证器第 1 层就会把**任何**回答判错 —— 那是一条注定的假拒，
而且会伪装成「agent 能力不足」。**这种错必须在跑之前拦掉。**
"""

import json
import os
import sys
from collections import Counter

from agenerp.site import SiteClient, SiteError

PATH = "tools/experiments/p2_schema_retrieval/eval-set-independent.jsonl"
items = [json.loads(ln) for ln in open(PATH, encoding="utf-8") if ln.strip()]
print(f"{len(items)} 条\n")

client = SiteClient(os.environ["AGENERP_SITE"],
                    admin_password=os.environ["AGENERP_ADMIN_PASSWORD"])

_cache: dict[str, dict] = {}
_meta_cache: dict[str, dict] = {}


def fields_of(doctype: str) -> dict[str, dict] | None:
    """DocType 的字段表；DocType 本身不存在时回 None（与「字段不存在」区分开）。"""
    if doctype not in _cache:
        try:
            doc = client.get(f"/api/resource/DocType/{doctype}")
            meta = doc.get("data", doc)
        except SiteError:
            _cache[doctype] = {}
            _meta_cache[doctype] = {}
            return None
        _meta_cache[doctype] = meta
        _cache[doctype] = {
            f["fieldname"]: f for f in meta.get("fields", []) if f.get("fieldname")
        }
    return _cache[doctype] or None


def istable(doctype: str) -> bool:
    fields_of(doctype)
    return bool(_meta_cache.get(doctype, {}).get("istable"))


bad_doctype, bad_field, ok = [], [], 0
child_tables = set()

for it in items:
    for ref in [*it["expected"], *it.get("acceptable", [])]:
        dt, _, fn = ref.rpartition(".")
        fields = fields_of(dt)
        if fields is None:
            bad_doctype.append((it["q"][:24], ref))
            continue
        if fn not in fields:
            bad_field.append((it["q"][:24], ref, sorted(fields)[:6]))
            continue
        ok += 1
        if istable(dt):
            child_tables.add(dt)

print(f"✅ 站点上存在：{ok} 个字段引用")
if bad_doctype:
    print(f"\n🔴 DocType 不存在（{len(bad_doctype)}）：")
    for q, ref in bad_doctype:
        print(f"   {ref:<52} ← 「{q}…」")
if bad_field:
    print(f"\n🔴 DocType 在、字段不在（{len(bad_field)}）：")
    for q, ref, sample in bad_field:
        print(f"   {ref:<52} ← 「{q}…」  该表字段样例 {sample}")

print(f"\n涉及的子表 DocType：{len(child_tables)} 个")
print(f"难度：{Counter(i['difficulty'] for i in items)}")
print(f"域　：{Counter(i['domain'] for i in items)}")
n_child = sum(1 for i in items if istable(i['expected'][0].rpartition('.')[0]))
print(f"主答案在子表的题：{n_child}/{len(items)}")

sys.exit(1 if (bad_doctype or bad_field) else 0)
