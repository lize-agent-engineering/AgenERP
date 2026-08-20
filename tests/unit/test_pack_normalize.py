"""非门禁测试 · `agenerp.pack.normalize` 的回归覆盖。

门禁（`tests/gates/test_normalizer_idempotent.py`，红线内只读）只用一层扁平样本
锁住三条判据。真实 Frappe 导出比那复杂：嵌套结构、列表套列表、派生的易变键名、
没有 `fieldname` 的条目。这里覆盖门禁**没覆盖但真实导出会撞上**的形状。

每条测试的 docstring 写明「红了意味着什么」，方便冷读时判断是判据变了还是实现坏了。
"""

import copy

from agenerp.pack import normalize


def _nested_export() -> dict:
    return {
        "custom_fields": [
            {
                "fieldname": "b_field",
                "modified": "2026-08-20 10:00:00",
                "options": [
                    {"fieldname": "z_opt", "owner": "alice@example.invalid"},
                    {"fieldname": "a_opt", "creation": "2026-08-01 09:00:00"},
                ],
            },
            {
                "fieldname": "a_field",
                "meta": {"depth": {"modified_by": "bob@example.invalid", "keep": 1}},
            },
        ],
        "property_setters": [],
        "doctype": "Item",
    }


def test_volatile_keys_are_stripped_at_every_depth():
    """红 = 递归剥离漏了某一层，真实导出一进 git 就是噪声 diff。"""
    text = repr(normalize(_nested_export()))
    for volatile in ("modified", "creation", "owner", "_comments"):
        assert volatile not in text, f"深层仍残留易变字段 {volatile}"


def test_substring_matched_keys_are_stripped():
    """红 = 只剥了精确键名。门禁断言 2 做的是 `repr` 子串检查，派生键一样会让它红。"""
    export = {
        "custom_fields": [
            {
                "fieldname": "a_field",
                "modified_by": "alice@example.invalid",
                "creation_date": "2026-08-01",
                "owner_id": 7,
                "label": "A",
            }
        ]
    }
    entry = normalize(export)["custom_fields"][0]
    assert entry == {"fieldname": "a_field", "label": "A"}


def test_non_volatile_keys_survive():
    """红 = 黑名单误伤业务字段，规范化把真实定制吃掉了。"""
    export = {"custom_fields": [{"fieldname": "a", "label": "A", "reqd": 1, "options": ""}]}
    assert normalize(export)["custom_fields"][0] == {
        "fieldname": "a",
        "label": "A",
        "options": "",
        "reqd": 1,
    }


def test_entries_without_fieldname_are_ordered_stably():
    """红 = 无身份键的条目会因导出顺序抖动，或直接抛 KeyError。"""
    a = {"rows": [{"b": 2}, {"a": 1}]}
    b = {"rows": [{"a": 1}, {"b": 2}]}
    assert normalize(a) == normalize(b)
    assert normalize(a)["rows"] == normalize(normalize(a))["rows"]


def test_mixed_entries_with_and_without_fieldname_do_not_raise():
    """红 = 混合条目走排序时类型不可比，规范化在真实导出上直接崩。"""
    export = {"rows": [{"fieldname": "z"}, {"no_identity": 1}, {"fieldname": "a"}]}
    rows = normalize(export)["rows"]
    assert len(rows) == 3
    assert [r["fieldname"] for r in rows if "fieldname" in r] == ["a", "z"]


def test_dict_keys_are_sorted():
    """红 = 键序随导出顺序走，`repr` 与 git diff 都会抖。"""
    export = {"z_top": 1, "a_top": 2, "custom_fields": [{"fieldname": "f", "z": 1, "a": 2}]}
    assert list(normalize(export)) == ["a_top", "custom_fields", "z_top"]
    assert list(normalize(export)["custom_fields"][0]) == ["a", "fieldname", "z"]


def test_empty_and_non_custom_fields_shapes_survive():
    """红 = 空容器或非 `custom_fields` 顶层键被吞掉，包的形状对不上原导出。"""
    export = {"custom_fields": [], "property_setters": {}, "doctype": "Item", "version": 3}
    assert normalize(export) == {
        "custom_fields": [],
        "doctype": "Item",
        "property_setters": {},
        "version": 3,
    }
    assert normalize({}) == {}


def test_lists_of_scalars_keep_their_order():
    """红 = 标量列表被重排。Select 选项之类的顺序是业务语义，不是噪声。"""
    export = {"custom_fields": [{"fieldname": "f", "options": ["b", "a", "c"]}]}
    assert normalize(export)["custom_fields"][0]["options"] == ["b", "a", "c"]


def test_tuples_normalize_to_lists():
    """红 = 序列类型没被统一，同样内容的两份导出会 diff 出差异。"""
    assert normalize({"rows": ({"fieldname": "b"}, {"fieldname": "a"})}) == normalize(
        {"rows": [{"fieldname": "a"}, {"fieldname": "b"}]}
    )


def test_input_is_not_mutated():
    """红 = 就地改了入参，调用方的两次快照互相污染，plan 3 的 diff 语义直接毁掉。"""
    export = _nested_export()
    before = copy.deepcopy(export)
    normalize(export)
    assert export == before


def test_normalize_is_idempotent():
    """红 = 反复导出仍产生噪声，GitOps 的「可 diff」不成立。"""
    export = _nested_export()
    once = normalize(export)
    assert normalize(once) == once
    assert repr(normalize(once)) == repr(once)
