"""P0 门禁 · 定制包规范化器的幂等性。

判据来源：Spike 06 实测打脸点——**什么都不改重新导出，Frappe 也会产生 diff**
（`modified` / `creation` / `owner` / `_comments` 等易变字段 + 顺序不稳定）。
不解决这个，git 历史就没有意义：每次导出都是噪声，看不出到底改了什么。
"""


def _raw_export_fixture():
    """两次「什么都没改」的导出，除易变字段外内容相同、顺序不同。"""
    a = {
        "custom_fields": [
            {"fieldname": "b_field", "label": "B", "modified": "2026-08-20 10:00:00",
             "creation": "2026-08-01 09:00:00", "owner": "alice@example.invalid", "_comments": "[]"},
            {"fieldname": "a_field", "label": "A", "modified": "2026-08-20 10:00:01",
             "creation": "2026-08-01 09:00:01", "owner": "alice@example.invalid", "_comments": "[]"},
        ]
    }
    b = {
        "custom_fields": [
            {"fieldname": "a_field", "label": "A", "modified": "2026-08-21 11:30:00",
             "creation": "2026-08-01 09:00:01", "owner": "bob@example.invalid", "_comments": "[]"},
            {"fieldname": "b_field", "label": "B", "modified": "2026-08-21 11:30:02",
             "creation": "2026-08-01 09:00:00", "owner": "bob@example.invalid", "_comments": "[]"},
        ]
    }
    return a, b


def test_normalize_is_stable_across_reexport():
    """同样的定制，两次导出规范化后必须逐字节相等。"""
    from agenerp.pack import normalize

    a, b = _raw_export_fixture()
    assert normalize(a) == normalize(b), "什么都没改，规范化后仍不相等 —— git 历史将全是噪声"


def test_normalize_strips_volatile_fields():
    """易变字段必须被剥离，不能留在包里。"""
    from agenerp.pack import normalize

    a, _ = _raw_export_fixture()
    text = repr(normalize(a))
    for volatile in ("modified", "creation", "owner", "_comments"):
        assert volatile not in text, f"规范化后仍残留易变字段 {volatile}"


def test_normalize_orders_deterministically():
    """顺序必须稳定，不能靠导出顺序碰运气。"""
    from agenerp.pack import normalize

    a, b = _raw_export_fixture()
    names = [f["fieldname"] for f in normalize(a)["custom_fields"]]
    assert names == sorted(names), f"规范化后顺序不是确定的：{names}"
    assert names == [f["fieldname"] for f in normalize(b)["custom_fields"]]
