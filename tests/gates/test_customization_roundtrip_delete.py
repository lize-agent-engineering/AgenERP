"""P0 门禁 · 定制包往返，重点是**删得掉**。

判据（roadmap P0 验收）：新增字段 → 导出 → `git diff` 干净可读 → 从包中删除 → apply → **字段真的消失**。

为什么单独立一条：Spike 06 实测 Frappe 的 `sync_customizations` 是**纯 upsert**，
从包里删掉一个字段再 apply，站点上的字段**不会消失**——也就是 `git revert` 撤不掉定制。
这是 P2「一句话改首页 → revert 撤得回」能否成立的前提。因此本项目**不使用** `sync_customizations`，
改用自建差集 apply 引擎；本测试就是这条选择的裁判。
"""
import pytest

pytestmark = pytest.mark.live

PROBE_FIELD = "agenerp_gate_roundtrip"


def test_added_field_exports_into_pack(live_site, pack_repo):
    from agenerp.pack import export_customizations

    live_site.add_custom_field(doctype="Item", fieldname=PROBE_FIELD, fieldtype="Data")
    export_customizations(doctype="Item", into=pack_repo.path)

    assert pack_repo.contains_field("Item", PROBE_FIELD), "新增的字段没有进定制包"


def test_export_produces_readable_diff_only(live_site, pack_repo):
    """导出必须只产生与这次改动相关的 diff——不能夹带一堆时间戳噪声。"""
    from agenerp.pack import export_customizations

    export_customizations(doctype="Item", into=pack_repo.path)
    pack_repo.commit("baseline")

    live_site.add_custom_field(doctype="Item", fieldname=PROBE_FIELD, fieldtype="Data")
    export_customizations(doctype="Item", into=pack_repo.path)

    changed = pack_repo.changed_lines()
    assert changed, "改了定制却没产生任何 diff"
    assert all(PROBE_FIELD in line or line.strip() in "{}[]," for line in changed), (
        f"diff 里夹带了与本次改动无关的内容：{[l for l in changed if PROBE_FIELD not in l][:5]}"
    )


def test_removing_from_pack_actually_deletes_on_site(live_site, pack_repo):
    """**承重条款**：从包里删掉字段 → apply → 站点上必须真的没有这个字段。"""
    from agenerp.pack import apply_pack, export_customizations

    live_site.add_custom_field(doctype="Item", fieldname=PROBE_FIELD, fieldtype="Data")
    export_customizations(doctype="Item", into=pack_repo.path)

    pack_repo.remove_field("Item", PROBE_FIELD)
    apply_pack(pack_repo.path, site=live_site.name)

    assert not live_site.has_custom_field("Item", PROBE_FIELD), (
        "从定制包删除并 apply 之后，字段仍在站点上 —— 说明 apply 是纯 upsert，revert 撤不掉定制"
    )


def test_no_orphan_column_left_behind(live_site, pack_repo):
    """删掉 Custom Field 不删列，反复增删会静默累积孤儿列（Spike 06）。"""
    from agenerp.pack import apply_pack, export_customizations
    from agenerp.snapshot import schema_drift

    live_site.add_custom_field(doctype="Item", fieldname=PROBE_FIELD, fieldtype="Data")
    export_customizations(doctype="Item", into=pack_repo.path)
    pack_repo.remove_field("Item", PROBE_FIELD)
    apply_pack(pack_repo.path, site=live_site.name)

    orphans = schema_drift(doctype="Item")
    assert PROBE_FIELD not in orphans, f"留下了孤儿列：{orphans}"
