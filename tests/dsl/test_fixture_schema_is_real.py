"""🔴 P2.1 · 守着「测字段存在性用的那份 schema 本身是真的」。

## 为什么要有这一条

`test_field_refs_must_exist.py` 全部的判别力，都建立在「fixture 里的
`Sales Order.customer` 确实存在、`Sales Order.custmoer` 确实不存在」之上。
**如果那份 fixture 是我手写的，那么这一整个文件测的是我编得对不对。**

这与本仓已经吃过的亏同族：判据绿着，但它验的不是它名字说的那件事
（`docs/audits/2026-08-26-CP9-P1-retrospective.md` §1.2）。

## 这一条能守到什么、守不到什么

**能守**：fixture 有出处、非空、规模合理，且被判据引用的每一个字段名都在里面
（或明确不在，对拒绝用例而言）。
⚠️ **守不到**：站点后来变了而 fixture 没跟着变。那是 P2.5 `schema.drift` 巡检的活，
不是本条的活 —— **这里写清楚，免得有人以为它守到了。**
"""

from __future__ import annotations

import json
import pathlib

# 刻意**直接读文件**，不从 conftest 导入：本条判据要守的就是那份文件本身，
# 经由 conftest 再拿一手，等于让被守的对象自己决定守卫看到什么。
_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "site-schema-subset.json"
_RAW = json.loads(_FIXTURE.read_text(encoding="utf-8"))
SALES_FIELDS: dict[str, dict[str, str]] = _RAW["fields"]
PROVENANCE: dict[str, str] = _RAW["provenance"]


def test_the_fixture_declares_where_it_came_from():
    # 一份没有出处的 schema 和手写的没有区别。
    for key in ("site", "generated_by", "generated_on", "frappe", "erpnext"):
        assert PROVENANCE.get(key), f"fixture 的 provenance 缺 {key}"
    assert "dump_schema.py" in PROVENANCE["generated_by"]


def test_the_fixture_is_a_real_erpnext_doctype_not_a_toy():
    # 真实的 `Sales Order` 有一百多个字段。一份只有五个字段的「schema」
    # 会让「字段不存在」这条判据变得毫无难度 —— 编一个不存在的字段名太容易了。
    assert len(SALES_FIELDS["Sales Order"]) > 50
    assert len(SALES_FIELDS["Sales Order Item"]) > 30


def test_the_fields_the_other_tests_rely_on_are_actually_present():
    # 接受用例用到的字段必须真的在。
    for fieldname in ("customer", "customer_name", "transaction_date",
                      "delivery_date", "grand_total", "status", "terms"):
        assert fieldname in SALES_FIELDS["Sales Order"], fieldname
    for fieldname in ("item_code", "qty", "rate", "delivered_qty"):
        assert fieldname in SALES_FIELDS["Sales Order Item"], fieldname


def test_the_typos_the_other_tests_rely_on_are_actually_absent():
    # 拒绝用例的判别力全在这里：如果 `custmoer` 碰巧真的是个字段，
    # 那条判据就在测一件不存在的事。
    for typo in ("custmoer", "gross_total", "grnd_total", "statuz", "transation_date"):
        assert typo not in SALES_FIELDS["Sales Order"], typo


def test_qty_really_lives_on_the_child_table_and_not_on_the_parent():
    # `test_the_field_check_looks_at_the_blocks_own_doctype_not_any_doctype`
    # 整条判据靠这个事实成立 —— 它必须被单独钉住，不能靠读者相信。
    assert "qty" in SALES_FIELDS["Sales Order Item"]
    assert "qty" not in SALES_FIELDS["Sales Order"]


def test_terms_really_is_a_fieldtype_the_renderer_cannot_draw():
    # 落回判据用 `terms` 当例子，前提是它真的是富文本。
    assert SALES_FIELDS["Sales Order"]["terms"] == "Text Editor"


def test_the_fixture_file_is_valid_json_and_lives_where_conftest_says():
    path = pathlib.Path(__file__).parent / "fixtures" / "site-schema-subset.json"
    assert path.exists()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert set(raw) == {"provenance", "fields"}
