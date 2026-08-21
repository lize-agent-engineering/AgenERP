"""非门禁测试 · 钉死 `diff` 的真实语义。

门禁 `test_diff_is_structured_not_text` 只检查三个属性存在且是序列——
一个恒返回三个空列表的假实现也能过。真正的判据在这里：增 / 删 / 改三类各自算得对、
互不串味，`is_empty()` 与 `summary()` 行为正确，跨 scope 显式报错。

条目形状（`.doctype` / `.fieldname`）按 `test_snapshot_diff_structured.py` 的 live 断言定稿，
工作项 6 接手时不该需要改这里。
"""

import pytest

from agenerp.snapshot import Snapshot, SnapshotEntry, SnapshotScopeMismatch, diff


def _snapshot(*entries, scope="doctypes"):
    return Snapshot(scope=scope, entries=tuple(entries))


def _field(doctype, fieldname, **attributes):
    return SnapshotEntry(doctype=doctype, fieldname=fieldname, attributes=attributes)


BRAND = _field("Item", "brand_code", fieldtype="Data")
SHELF = _field("Item", "shelf_life_days", fieldtype="Int")
TIER = _field("Customer", "credit_tier", fieldtype="Select")


def test_same_snapshot_diffs_empty():
    """自比必须为空。这条不成立，后面所有 state-diff 判定都是噪声。"""
    snap = _snapshot(BRAND, TIER)

    d = diff(snap, snap)

    assert d.is_empty()
    assert (d.added, d.removed, d.changed) == ((), (), ())


def test_added_field_lands_only_in_added():
    """新增字段只进 `added`，且能精确指出是哪个 DocType 的哪个字段（预演 live 断言的形状）。"""
    d = diff(_snapshot(BRAND), _snapshot(BRAND, SHELF))

    assert not d.is_empty()
    assert [(e.doctype, e.fieldname) for e in d.added] == [("Item", "shelf_life_days")]
    assert d.removed == () and d.changed == ()
    assert d.added[0].attributes == {"fieldtype": "Int"}


def test_removed_field_lands_only_in_removed():
    """删除字段只进 `removed`。跑到 `changed` 里就意味着调用方会漏掉一次删除。"""
    d = diff(_snapshot(BRAND, SHELF), _snapshot(BRAND))

    assert [(e.doctype, e.fieldname) for e in d.removed] == [("Item", "shelf_life_days")]
    assert d.added == () and d.changed == ()


def test_changed_attribute_lands_only_in_changed_with_both_values():
    """改属性只进 `changed`，且前后值都带得出来——否则调用方得回头再查两份快照。"""
    before = _snapshot(_field("Item", "brand_code", fieldtype="Data"))
    after = _snapshot(_field("Item", "brand_code", fieldtype="Select"))

    d = diff(before, after)

    assert d.added == () and d.removed == ()
    assert len(d.changed) == 1
    entry = d.changed[0]
    assert (entry.doctype, entry.fieldname) == ("Item", "brand_code")
    assert entry.before == {"fieldtype": "Data"}
    assert entry.after == {"fieldtype": "Select"}


def test_three_kinds_at_once_do_not_bleed_into_each_other():
    """增删改同时发生时三个序列必须各归各位，不串味。"""
    before = _snapshot(BRAND, SHELF, TIER)
    after = _snapshot(
        _field("Item", "brand_code", fieldtype="Select"),
        TIER,
        _field("Customer", "region", fieldtype="Link"),
    )

    d = diff(before, after)

    assert [(e.doctype, e.fieldname) for e in d.added] == [("Customer", "region")]
    assert [(e.doctype, e.fieldname) for e in d.removed] == [("Item", "shelf_life_days")]
    assert [(e.doctype, e.fieldname) for e in d.changed] == [("Item", "brand_code")]


def test_same_fieldname_on_different_doctypes_is_not_the_same_entry():
    """身份是 (doctype, fieldname) 而非 fieldname。只按字段名去重会把两个 DocType 混成一个。"""
    before = _snapshot(_field("Item", "code", fieldtype="Data"))
    after = _snapshot(_field("Customer", "code", fieldtype="Data"))

    d = diff(before, after)

    assert [(e.doctype, e.fieldname) for e in d.added] == [("Customer", "code")]
    assert [(e.doctype, e.fieldname) for e in d.removed] == [("Item", "code")]
    assert d.changed == ()


def test_summary_is_callable_on_empty_and_non_empty_diffs():
    """`summary()` 只出现在断言失败信息里；它自己抛异常会把真实失败原因盖掉。"""
    empty = diff(_snapshot(BRAND), _snapshot(BRAND))
    assert isinstance(empty.summary(), str) and empty.summary()

    non_empty = diff(_snapshot(BRAND), _snapshot(BRAND, SHELF))
    text = non_empty.summary()
    assert isinstance(text, str)
    assert "shelf_life_days" in text, "人读摘要里看不到出问题的字段，等于没写"


def test_machine_verdict_does_not_depend_on_summary_text():
    """「结构化而非文本」的含义：判定走三个序列，`summary()` 变了也不影响结论。"""
    d = diff(_snapshot(BRAND), _snapshot(BRAND, SHELF))

    assert len(d.added) == 1
    assert not d.is_empty()


def test_scope_mismatch_raises_instead_of_silently_diffing():
    """跨 scope 比较必须报错。静默降级会产出一份「全删全增」的假 diff。"""
    before = _snapshot(BRAND, scope="doctypes")
    after = _snapshot(TIER, scope="permissions")

    with pytest.raises(SnapshotScopeMismatch):
        diff(before, after)


def test_diff_does_not_mutate_its_inputs():
    """纯函数：diff 之后两份快照必须原样可用，否则连做两次比较会得出不同结论。"""
    before = _snapshot(BRAND, SHELF)
    after = _snapshot(BRAND, TIER)

    first = diff(before, after)
    second = diff(before, after)

    assert before == _snapshot(BRAND, SHELF)
    assert after == _snapshot(BRAND, TIER)
    assert (first.added, first.removed, first.changed) == (
        second.added,
        second.removed,
        second.changed,
    )


def test_diff_carries_the_shared_scope():
    """diff 结果得说清自己是哪个 scope 的，否则多 scope 汇总时无从归位。"""
    d = diff(_snapshot(BRAND, scope="permissions"), _snapshot(BRAND, scope="permissions"))

    assert d.scope == "permissions"
