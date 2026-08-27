"""🔴 P2.7 · 术语层：给字段一个中文名字，且能证明它没乱起。

WBS §5 第 107 行那条验收命令打的就是本目录：`pytest tests/i18n -q` 退 0。

## 基线是「零」，不是「少」

活站点导出实读（2026-08-27）：**业务 app 全量 6,350 个字段，label 含中文的 = 0**。
`Item Reorder.warehouse` 的 label 逐字是「**Request for**」——
字段名说的是仓库，标签说的是「请求给」。

## ⚠️ 这套判据的上限，写在最前面

**它验的是「有没有离谱地错」，不是「翻译得好不好」。**

后者没有规则面的判法。而本仓硬约束 ③（D-15）不许把规则能覆盖的事交给模型，
**反过来也成立：不许让模型判自己的产物**。
⇒ 术语层的质量上限由 `test_the_fifteen_terms_that_must_not_be_wrong` 那 15 条决定，
**这个上限是低的，不掩饰。**

能守住的是这几条（全是规则面）：
覆盖率 · **逐条指回真实存在的字段**（硬约束 ④）· 含中文 · 不等于英文原文 · 不等于 fieldname。
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from agenerp.i18n import TERMS_PATH, load_terms
from agenerp.dsl.roles import WORKER_DOCTYPES

CJK = re.compile(r"[一-鿿]")

_SCHEMA_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "dsl/fixtures/site-schema-subset.json"
)
_CHILD_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "dsl/fixtures/child-tables.json"
)

# 🔴 §2.4 的清单。**在生成之前写死并提交**（`a080f15`），事后不许调。
# 可接受关键词只列**客观词**（数量 / 仓库 / 日期这一类），不含风格判断 ——
# 否则这条判据会变成「我喜不喜欢这个译法」。
MUST_NOT_BE_WRONG = {
    "Item.item_code": ("编码", "编号", "代码", "料号"),
    "Item.item_name": ("名称",),
    "Item.stock_uom": ("单位",),
    "Item.description": ("描述", "说明"),
    "Item.brand": ("品牌",),
    "Work Order.qty": ("数量",),
    "Work Order.produced_qty": ("数量", "产量"),
    "Work Order.status": ("状态",),
    "Work Order.company": ("公司",),
    "Work Order.source_warehouse": ("仓库",),
    "Stock Entry.posting_date": ("日期",),
    "Stock Entry.from_warehouse": ("仓库",),
    "Stock Entry.to_warehouse": ("仓库",),
    "Stock Entry Detail.qty": ("数量",),
    "Stock Entry Detail.uom": ("单位",),
}
MUST_NOT_BE_WRONG_THRESHOLD = 13


@pytest.fixture(scope="module")
def terms() -> dict:
    return load_terms()


@pytest.fixture(scope="module")
def scope_fields() -> dict[str, str]:
    """车间工人覆盖面上的 `(DocType.fieldname) → 英文 label`。

    ⚠️ 来自**活站点导出**（`dump_schema.py` 的产物子集），不是手写的 ——
    与 `tests/dsl/` 那一层同源。
    """
    fields = json.loads(_SCHEMA_FIXTURE.read_text(encoding="utf-8"))["fields"]
    children_raw = json.loads(_CHILD_FIXTURE.read_text(encoding="utf-8"))
    scope = set(WORKER_DOCTYPES)
    for key, child in children_raw.items():
        if key.split(".", 1)[0] in WORKER_DOCTYPES:
            scope.add(child)
    return {
        f"{doctype}.{fieldname}": fieldname
        for doctype, table in fields.items()
        if doctype in scope
        for fieldname in table
    }


# ── T1 · 覆盖率与「指回真实字段」 ────────────────────────────────────────────


def test_the_terms_file_exists_and_declares_where_it_came_from(terms):
    """一份没有出处的术语层与手写的没有区别。"""
    for key in ("generated_by", "generated_on", "model", "scope", "site"):
        assert terms["provenance"].get(key), f"术语层的 provenance 缺 {key}"


def test_every_term_points_at_a_field_that_actually_exists(terms, scope_fields):
    """🔴 硬约束 ④ 用在术语层自己身上。

    一条指不回真实字段的术语是纯粹的噪音：它永远不会被用到，
    却会让「覆盖率」这个数变得好看。**指不回的一律不入库，不是「先留着再说」。**
    """
    strays = [key for key in terms["terms"] if key not in scope_fields]
    assert not strays, f"术语层里有 {len(strays)} 条指不回本轮范围内的真实字段：{strays[:8]}"


def test_the_terms_cover_every_field_in_the_worker_scope(terms, scope_fields):
    """T1 · 覆盖率 = 100%。漏掉的字段在界面上仍然是英文。"""
    missing = sorted(set(scope_fields) - set(terms["terms"]))
    assert not missing, (
        f"车间工人覆盖面 {len(scope_fields)} 个字段里，还有 {len(missing)} 个没有中文名："
        f"{missing[:10]}"
    )


# ── T2 · 规则面的质量下限 ────────────────────────────────────────────────────


def test_almost_every_term_actually_contains_chinese(terms):
    """T2 · ≥ 95% 含中文。

    一条不含中文的「中文名」是这一层完全失效的形态，而它在覆盖率上仍然算数。
    """
    total = len(terms["terms"])
    with_cjk = [k for k, v in terms["terms"].items() if CJK.search(v or "")]
    ratio = len(with_cjk) * 100 / total
    assert ratio >= 95.0, (
        f"只有 {ratio:.1f}% 的术语含中文（{len(with_cjk)}/{total}）；"
        f"不含中文的例子：{sorted(set(terms['terms']) - set(with_cjk))[:8]}"
    )


def test_no_term_is_just_the_english_label_copied_over(terms, scope_fields):
    """抄一遍英文 label 也能拿满覆盖率 —— 那是这一层最省事的假装方式。"""
    english = _english_labels()
    copied = [k for k, v in terms["terms"].items() if english.get(k) and v.strip() == english[k]]
    assert not copied, f"这些术语只是把英文 label 抄了一遍：{copied[:8]}"


def test_no_term_is_just_the_fieldname(terms, scope_fields):
    """抄 fieldname 同理。"""
    copied = [
        key for key, value in terms["terms"].items()
        if scope_fields.get(key) and value.strip() == scope_fields[key]
    ]
    assert not copied, f"这些术语只是把 fieldname 抄了一遍：{copied[:8]}"


def test_no_term_is_empty_or_absurdly_long(terms):
    """空的与长篇大论都不是「标签」。列宽有限，一个 40 字的表头等于没有表头。"""
    bad = {k: v for k, v in terms["terms"].items() if not v.strip() or len(v.strip()) > 20}
    assert not bad, f"这些术语为空或过长：{list(bad.items())[:6]}"


# ── T3 · 🔴 那 15 条不该错的 ─────────────────────────────────────────────────


def test_the_fifteen_terms_that_must_not_be_wrong(terms):
    """🔴 T3 · 决定性的一格。清单与关键词在**生成之前**写死（`a080f15`）。

    ⚠️ **它验的是「有没有离谱地错」，不是「翻译得好不好」** —— 见本模块 docstring。
    这条判据是术语层质量的**上限**，而这个上限低。不掩饰。
    """
    hits, misses = [], []
    for key, acceptable in MUST_NOT_BE_WRONG.items():
        value = (terms["terms"].get(key) or "").strip()
        if any(word in value for word in acceptable):
            hits.append(key)
        else:
            misses.append((key, value, acceptable))
    assert len(hits) >= MUST_NOT_BE_WRONG_THRESHOLD, (
        f"15 条「不该错」的只中了 {len(hits)} 条（要求 ≥ {MUST_NOT_BE_WRONG_THRESHOLD}）。\n"
        + "\n".join(f"  · {k} → 「{v}」，期望含以下任一 {list(a)}" for k, v, a in misses)
    )


def test_the_must_not_be_wrong_list_is_not_quietly_shrinkable(terms, scope_fields):
    """清单本身也要守：条目数与阈值都写死，且每一条都必须指向真实字段。

    没有这一条，「把清单删到只剩 13 条」是让 T3 变绿的最省事办法。
    """
    assert len(MUST_NOT_BE_WRONG) == 15
    assert MUST_NOT_BE_WRONG_THRESHOLD == 13
    for key in MUST_NOT_BE_WRONG:
        assert key in scope_fields, f"清单里的 {key} 不是本轮范围内的真实字段"


# ── 术语层不许悄悄改变「哪些字段被用到」 ─────────────────────────────────────


def test_the_terms_file_is_valid_json_and_lives_where_the_loader_says():
    assert TERMS_PATH.exists(), f"术语层产物不在 {TERMS_PATH}"
    raw = json.loads(TERMS_PATH.read_text(encoding="utf-8"))
    assert set(raw) == {"provenance", "terms"}


def _english_labels() -> dict[str, str]:
    """字段的英文 label —— 从活站点导出的 fixture 里拿，不手写。"""
    path = pathlib.Path(__file__).resolve().parents[1] / "i18n" / "fixtures" / "english-labels.json"
    if not path.exists():
        pytest.fail(
            f"缺 {path} —— 英文 label 必须来自活站点导出，不许手写。"
            "生成方式见 tools/experiments/p2_terminology/"
        )
    return json.loads(path.read_text(encoding="utf-8"))
