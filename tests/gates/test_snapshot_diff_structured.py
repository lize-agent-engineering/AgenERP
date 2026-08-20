"""P0 门禁 · 状态快照与结构化 diff。

判据（roadmap P0 验收）：能对同一站点打两次快照，并输出**结构化** diff。
结构化 = 机器可判定：调用方不必解析人类可读文本就能回答「什么被加了/删了/改了」。
"""
import pytest


def test_two_snapshots_of_unchanged_site_diff_empty():
    """什么都没动 → diff 必须为空。这条不成立的话，后面所有 state-diff 判定都是噪声。"""
    from agenerp.snapshot import capture, diff

    before = capture(scope="doctypes")
    after = capture(scope="doctypes")

    d = diff(before, after)
    assert d.is_empty(), f"未改动站点却产生了 diff：{d.summary()}"


def test_diff_is_structured_not_text():
    """diff 必须以结构化形式给出增/删/改三类，而不是一段自然语言。"""
    from agenerp.snapshot import capture, diff

    before = capture(scope="doctypes")
    after = capture(scope="doctypes")
    d = diff(before, after)

    for field in ("added", "removed", "changed"):
        assert hasattr(d, field), f"diff 缺少结构化字段 {field}"
        assert isinstance(getattr(d, field), (list, tuple, dict))


@pytest.mark.live
def test_field_addition_shows_up_as_structured_change(live_site):
    """真加一个字段 → diff 必须精确指出是哪个 DocType 的哪个字段被加了。"""
    from agenerp.snapshot import capture, diff

    before = capture(scope="doctypes")
    live_site.add_custom_field(doctype="Item", fieldname="agenerp_gate_probe", fieldtype="Data")
    after = capture(scope="doctypes")

    d = diff(before, after)
    assert not d.is_empty()
    assert any(
        c.doctype == "Item" and c.fieldname == "agenerp_gate_probe" for c in d.added
    ), f"加了字段但 diff 没指出来：{d.summary()}"
