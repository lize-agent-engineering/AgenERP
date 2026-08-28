"""🔴 P2.3 Phase 4 · 守着「评测集的期望字段本身是真的」。

## 为什么要有这一条

量化评测全部的判别力，都建立在「`Work Order.qty` 确实存在、
`Stock Entry.name` 确实存在」之上。**如果那些期望字段是我编的，
那么整个评测测的是我编得对不对，不是视图 Agent 对不对。**

纪律与 `tests/dsl/test_fixture_schema_is_real.py` 逐条同源，
那里守的是校验器用的 schema，这里守的是评分用的期望集合。

## 能守到什么、守不到什么

**能守**：schema 有出处 · 每个 `must_fields` 在实读 schema 里真实存在 ·
主集只用车间工人那几张表 · 域外确实在域外 · 每条题的形状齐全。

⚠️ **守不到**：题目问得对不对（「工单一共多少张」该不该用 `name` 计数，
是**我的判断**）。那一层由判官在评测里回答「切题吗」——
`docs/logs/2026/08-28-handoff-p2.md` §3④ 记着一个真实样本：
`count(naming_series)` 结构全对、硬判全绿，数出来却不是笔数。
"""

from __future__ import annotations

import json
import pathlib

import pytest

_DIR = pathlib.Path(__file__).resolve().parents[2] / "tools" / "experiments" / "p2_view_agent"
_SET = _DIR / "eval-set.jsonl"
_SCHEMA = _DIR / "eval-schema.json"

_ROWS = [json.loads(line) for line in _SET.read_text(encoding="utf-8").splitlines() if line.strip()]
_RAW = json.loads(_SCHEMA.read_text(encoding="utf-8"))

_BY_DOCTYPE: dict[str, set[str]] = {}
for _row in _RAW["fields"]:
    _BY_DOCTYPE.setdefault(_row["doctype"], set()).add(_row["fieldname"])

# 车间工人真实可读的三张表（`agenerp/seedusers.py` 建的受限身份）。
_WORKER_DOCTYPES = {"Work Order", "Stock Entry", "Item"}
_BLOCK_TYPES = {"list", "detail", "metric", "chart", "explain"}


def test_the_schema_declares_where_it_came_from():
    """一份没有出处的 schema 和手写的没有区别。"""
    provenance = _RAW["provenance"]
    for key in ("site", "generated_by", "generated_on"):
        assert provenance.get(key), f"缺 provenance.{key}"
    assert "dump_eval_schema.py" in provenance["generated_by"]


def test_the_eval_set_is_not_empty_and_has_both_halves():
    assert _ROWS, "评测集是空的"
    assert sum(1 for r in _ROWS if r["domain"] == "in") >= 10
    assert sum(1 for r in _ROWS if r["domain"] == "out") >= 5


def test_every_id_is_unique():
    ids = [r["id"] for r in _ROWS]
    assert len(ids) == len(set(ids)), "题号重复 —— 结果会互相覆盖"


@pytest.mark.parametrize("row", _ROWS, ids=[r["id"] for r in _ROWS])
def test_every_expected_field_really_exists(row):
    """🔴 本文件的主条：**期望集合逐个指回实读 schema。**"""
    doctype = row["expect_doctype"]
    assert doctype in _BY_DOCTYPE, f"{row['id']}：DocType {doctype!r} 不在实读 schema 里"
    assert row["must_fields"], f"{row['id']}：一个期望字段都没有的题，判不出对错"
    for fieldname in row["must_fields"]:
        assert fieldname in _BY_DOCTYPE[doctype], f"{row['id']}：{doctype}.{fieldname} 不存在"


@pytest.mark.parametrize("row", _ROWS, ids=[r["id"] for r in _ROWS])
def test_every_row_has_the_shape_the_scorer_needs(row):
    for key in ("id", "q", "expect_doctype", "must_fields", "expect_block_types", "domain"):
        assert key in row, f"{row.get('id')}：缺 {key}"
    assert row["q"].strip(), f"{row['id']}：题面是空的"
    assert row["domain"] in ("in", "out")
    unknown = set(row["expect_block_types"]) - _BLOCK_TYPES
    assert not unknown, f"{row['id']}：块类型不在封闭表里 {unknown}"


def test_the_in_domain_half_stays_inside_the_worker_doctypes():
    """主集的「落回 = 0」只在 P2.2 路线 C 的分母上成立 —— 分母不许被悄悄扩大。"""
    for row in _ROWS:
        if row["domain"] == "in":
            assert row["expect_doctype"] in _WORKER_DOCTYPES, (
                f"{row['id']} 的 {row['expect_doctype']} 不在车间工人的三张表里"
            )


def test_the_out_of_domain_half_is_really_out_of_domain():
    """域外子集要真的在域外，否则「两个数分开报」报的是同一件事。"""
    for row in _ROWS:
        if row["domain"] == "out":
            assert row["expect_doctype"] not in _WORKER_DOCTYPES, (
                f"{row['id']} 的 {row['expect_doctype']} 其实在主集域里"
            )
