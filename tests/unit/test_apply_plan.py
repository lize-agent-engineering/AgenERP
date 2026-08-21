"""非门禁测试 · 钉死差集 apply 引擎 A 半（`agenerp.apply`）的真实行为。

工作项 5 绑定的门禁 `test_removing_from_pack_actually_deletes_on_site` 要活站点，
被 `AGENTS.md` 红线 1 挡在 `tests/gates/conftest.py` 里，loop 无权让它转绿。
**所以 A 半的判据只能落在这里**，而这里正是 `missions/p0-foundation.json` 的
`commands.test` 复跑得到的地方（`python3 -m pytest tests/unit -q`）。

本文件只用标准库：判定面一旦依赖第三方包，换台机器就会红在环境而不是红在实现上。
"""

import copy
import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from agenerp.apply import PACK_SCOPE, ApplyPlan, execute_plan, plan_apply, read_pack
from agenerp.snapshot import Snapshot, SnapshotEntry, SnapshotScopeMismatch

# §11.1 的实测结论，反 upsert 那条断言失败时逐字打给人看。
_UPSERT_LESSON = (
    "Spike 06 实测（docs/architecture/module-boundaries.md §11.1）："
    "Frappe 的 sync_customizations_for_doctype 是纯 upsert、没有任何删除分支，"
    "从定制包里删掉字段再 sync，站点上的字段纹丝不动 —— git revert 撤不掉定制。"
    "「删除集」是本项目必须自建的东西；这条断言就是它还在不在的裁判。"
)


def _snapshot(*entries, scope=PACK_SCOPE):
    return Snapshot(scope=scope, entries=tuple(entries))


def _field(doctype, fieldname, **attributes):
    return SnapshotEntry(doctype=doctype, fieldname=fieldname, attributes=attributes)


BRAND = _field("Item", "brand_code", fieldtype="Data")
SHELF = _field("Item", "shelf_life_days", fieldtype="Int")
TIER = _field("Customer", "credit_tier", fieldtype="Select")


def _write_pack_doctype(root: Path, doctype: str, fields, scope: str = PACK_SCOPE):
    scope_dir = root / scope
    scope_dir.mkdir(parents=True, exist_ok=True)
    payload = {"doctype": doctype, "custom_fields": list(fields)}
    (scope_dir / f"{doctype}.json").write_text(json.dumps(payload), encoding="utf-8")


# --- 承重条款：删除集必须存在 -------------------------------------------------------


def test_field_removed_from_pack_lands_in_deletes():
    """**反 upsert 回归**：站点上有、包里没有的字段，必须出现在 `plan.deletes` 里。

    这条红了意味着删除集又没了，`git revert` 撤不掉定制这个坑原样复现。
    """
    desired = _snapshot(BRAND)
    current = _snapshot(BRAND, SHELF)

    plan = plan_apply(desired=desired, current=current)

    assert [e.key for e in plan.deletes] == [SHELF.key], (
        f"从定制包里删掉 {SHELF.doctype}.{SHELF.fieldname} 之后，它没有进 deletes："
        f"{plan.summary()}。{_UPSERT_LESSON}"
    )
    assert plan.creates == (), f"不该有新建：{plan.summary()}"
    assert plan.updates == (), f"不该有更新：{plan.summary()}"
    assert not plan.is_empty(), f"有字段待删，计划却自称为空：{_UPSERT_LESSON}"


def test_delete_survives_alongside_creates_and_updates():
    """三类动作同时存在时互不串味 —— 删除不许被「反正也要 upsert」吞掉。"""
    desired = _snapshot(_field("Item", "brand_code", fieldtype="Link"), TIER)
    current = _snapshot(BRAND, SHELF)

    plan = plan_apply(desired=desired, current=current)

    assert [e.key for e in plan.creates] == [TIER.key]
    assert [e.key for e in plan.updates] == [BRAND.key]
    assert [e.key for e in plan.deletes] == [SHELF.key], _UPSERT_LESSON
    changed = plan.updates[0]
    assert changed.before == {"fieldtype": "Data"}
    assert changed.after == {"fieldtype": "Link"}


# --- 方向：写反了必须被抓出来 -------------------------------------------------------


def test_direction_is_not_symmetric():
    """互换 `desired` / `current`，`creates` 与 `deletes` 必须互换。

    恒返回空计划、或把删算成建的实现都过不了这一条 —— 两次调用的结果必须不同。
    """
    a = _snapshot(BRAND)
    b = _snapshot(BRAND, SHELF)

    forward = plan_apply(desired=a, current=b)
    backward = plan_apply(desired=b, current=a)

    assert [e.key for e in forward.deletes] == [SHELF.key]
    assert forward.creates == ()
    assert [e.key for e in backward.creates] == [SHELF.key]
    assert backward.deletes == ()
    assert not forward.is_empty() and not backward.is_empty(), (
        "互换方向后两边都空 —— 说明求差根本没在算，是个恒空的假实现"
    )


def test_positional_call_keeps_pack_first():
    """位置参数调用的语义与关键字调用一致：第一个参数是**包**，第二个是站点现状。

    `plan_apply` 内部要把参数序反过来喂给 `snapshot.diff`（`diff(before=current, after=desired)`），
    这条守的就是那次反转没有漏做。
    """
    assert plan_apply(_snapshot(BRAND), _snapshot(BRAND, SHELF)).deletes == (SHELF,)


# --- 幂等、空计划、拒绝、不改入参 ---------------------------------------------------


def test_same_snapshot_yields_empty_plan():
    snap = _snapshot(BRAND, TIER)

    plan = plan_apply(desired=snap, current=snap)

    assert plan.is_empty()
    assert (plan.creates, plan.updates, plan.deletes) == ((), (), ())
    assert plan.scope == PACK_SCOPE
    assert "无需 apply" in plan.summary()


def test_scope_mismatch_is_refused():
    """跨 scope 求差必须显式拒绝，不许静默当成「全删全增」。"""
    with pytest.raises(SnapshotScopeMismatch):
        plan_apply(desired=_snapshot(BRAND, scope="doctypes"), current=_snapshot(BRAND, scope="permissions"))


def test_plan_apply_does_not_mutate_its_inputs():
    desired = _snapshot(BRAND, TIER)
    current = _snapshot(BRAND, SHELF)
    desired_before = copy.deepcopy(desired)
    current_before = copy.deepcopy(current)

    plan_apply(desired=desired, current=current)

    assert desired == desired_before
    assert current == current_before
    assert [e.attributes for e in desired.entries] == [e.attributes for e in desired_before.entries]
    assert [e.attributes for e in current.entries] == [e.attributes for e in current_before.entries]


def test_plan_is_immutable():
    plan = plan_apply(desired=_snapshot(BRAND), current=_snapshot(BRAND, SHELF))

    with pytest.raises(FrozenInstanceError):
        plan.deletes = ()


def test_summary_is_not_the_decision_surface():
    """`summary()` 只给人读，三个序列才是判定面 —— 但它得把删除真的写出来。"""
    plan = plan_apply(desired=_snapshot(BRAND), current=_snapshot(BRAND, SHELF))

    text = plan.summary()

    assert "删除" in text and "Item.shelf_life_days" in text


# --- read_pack 的三条边界 -----------------------------------------------------------


def test_read_pack_missing_directory_is_zero_entries(tmp_path):
    """包里还没有这个 scope 是**合法状态**，不是错误。

    抛异常会让调用方红在环境上而不是红在实现上（W0.6「红得不对」的同一个坑）。
    """
    snap = read_pack(tmp_path / "not-created-yet")

    assert len(snap) == 0
    assert snap.entries == ()
    assert snap.scope == PACK_SCOPE


def test_read_pack_reads_fields_from_pack_directory(tmp_path):
    _write_pack_doctype(tmp_path, "Item", [{"fieldname": "brand_code", "fieldtype": "Data"}])

    snap = read_pack(tmp_path)

    assert [e.key for e in snap.entries] == [("Item", "brand_code")]
    assert snap.entries[0].attributes == {"fieldtype": "Data"}
    assert snap.source.startswith("pack:")


def test_read_pack_strips_volatile_fields(tmp_path):
    """易变字段不进条目 —— 与 `agenerp.pack.normalize` 同口径，不开第二套。

    留着它们，「什么都没改重新导出」也会算出一堆 updates，删除集淹没在噪声里。
    """
    _write_pack_doctype(
        tmp_path,
        "Item",
        [
            {
                "fieldname": "brand_code",
                "fieldtype": "Data",
                "modified": "2026-08-21 10:00:00",
                "creation": "2026-08-01 09:00:00",
                "owner": "Administrator",
                "modified_by": "Administrator",
                "_comments": "[]",
            }
        ],
    )

    snap = read_pack(tmp_path)

    assert snap.entries[0].attributes == {"fieldtype": "Data"}


def test_read_pack_ignoring_volatile_fields_keeps_plan_empty(tmp_path):
    """只有易变字段变了 → 计划必须为空。这是「可 diff 的产物」这条要求的落地判据。"""
    _write_pack_doctype(tmp_path, "Item", [{"fieldname": "brand_code", "fieldtype": "Data"}])
    before = read_pack(tmp_path)
    _write_pack_doctype(
        tmp_path,
        "Item",
        [{"fieldname": "brand_code", "fieldtype": "Data", "modified": "2026-08-21 23:59:59"}],
    )
    after = read_pack(tmp_path)

    assert plan_apply(desired=after, current=before).is_empty()


def test_read_pack_rejects_entry_without_fieldname(tmp_path):
    """条目缺 `fieldname` → 显式报错，不静默跳过。

    静默跳过的后果最恶劣：那个字段既不在 desired 里也不会被算成 delete，
    它会永远留在站点上，而计划看起来干干净净。
    """
    _write_pack_doctype(tmp_path, "Item", [{"fieldtype": "Data"}])

    with pytest.raises(ValueError, match="fieldname"):
        read_pack(tmp_path)


def test_read_pack_rejects_non_object_payload(tmp_path):
    scope_dir = tmp_path / PACK_SCOPE
    scope_dir.mkdir(parents=True)
    (scope_dir / "Item.json").write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    with pytest.raises(ValueError):
        read_pack(tmp_path)


def test_read_pack_and_plan_apply_compose_into_a_delete(tmp_path):
    """端到端（无站点）：包里删掉一个字段 → 它必须出现在删除集里。

    这是 A 半能给出的、离门禁 `test_removing_from_pack_actually_deletes_on_site`
    最近的一条判据 —— 差的只剩「对站点执行」那一步。
    """
    _write_pack_doctype(
        tmp_path,
        "Item",
        [
            {"fieldname": "brand_code", "fieldtype": "Data"},
            {"fieldname": "agenerp_gate_roundtrip", "fieldtype": "Data"},
        ],
    )
    current = read_pack(tmp_path)
    _write_pack_doctype(tmp_path, "Item", [{"fieldname": "brand_code", "fieldtype": "Data"}])
    desired = read_pack(tmp_path)

    plan = plan_apply(desired=desired, current=current)

    assert [e.fieldname for e in plan.deletes] == ["agenerp_gate_roundtrip"], _UPSERT_LESSON


# --- B 半的接缝：必须红在「执行未实现」 ---------------------------------------------


def test_execute_plan_is_the_single_landing_spot_for_the_site_half():
    plan = plan_apply(desired=_snapshot(BRAND), current=_snapshot(BRAND, SHELF))

    with pytest.raises(NotImplementedError) as excinfo:
        execute_plan(plan, site="dev.localhost")

    message = str(excinfo.value)
    assert "工作项 6" in message, f"红因没有指名后继：{message}"
    assert "STATE.md" in message, f"红因没有指向等人的那行 [open]：{message}"


def test_apply_pack_really_runs_the_pure_half():
    """`apply_pack` 必须真的走进 `read_pack` —— 一个原地 `raise` 的假委派过不了这条。

    包里放一个缺 `fieldname` 的条目：报错必须来自读包这一步（`ValueError`），
    而不是站点侧的 `NotImplementedError`。
    """
    import tempfile

    from agenerp.pack import apply_pack

    with tempfile.TemporaryDirectory() as tmp:
        _write_pack_doctype(Path(tmp), "Item", [{"fieldtype": "Data"}])

        with pytest.raises(ValueError, match="fieldname"):
            apply_pack(tmp, site="dev.localhost")


def test_apply_pack_reds_on_the_site_half_not_on_diffing(tmp_path):
    """门禁逐字 `from agenerp.pack import apply_pack`：导入路径与签名一字不改。

    红因已经从「求差不存在」挪到站点侧。**当前逐字是 `SiteSnapshotSource.read`**
    （工作项 4 的 B 半：没有活站点就答不出「站点现状是什么」），它接上之后才轮到
    `execute_plan`（工作项 6）。两处都在站点侧，A 半在它们之前已经跑完。
    """
    from agenerp.pack import apply_pack

    with pytest.raises(NotImplementedError) as excinfo:
        apply_pack(str(tmp_path), site="dev.localhost")

    message = str(excinfo.value)
    assert "apply_pack" not in message, (
        f"红因还停在 apply_pack 自己身上，说明委派没接上：{message}"
    )
    assert "SiteSnapshotSource.read" in message or "execute_plan" in message, (
        f"红因不在站点侧的两个落点上：{message}"
    )


# --- 零依赖与导入方向（**必须在全新子进程里测**） -----------------------------------
# 不许在当前 pytest 进程里对 `sys.modules` 前后求差：`agenerp.apply` 可能已被本文件
# 或别的测试模块导入，差集恒为空，断言就成了永远绿的假判据。

_DUMP_TOP_LEVEL = "import sys; print(' '.join(sorted({m.split('.')[0] for m in sys.modules})))"


def _top_level_modules(setup: str) -> tuple[set[str], subprocess.CompletedProcess]:
    proc = subprocess.run(
        [sys.executable, "-c", f"{setup}\n{_DUMP_TOP_LEVEL}"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    return set(proc.stdout.split()), proc


def test_importing_apply_pulls_in_no_third_party_module():
    """`agenerp.apply` 只用标准库 + 仓内模块。

    CI 的 `gates-l1` 只 `pip install pytest`；这里多进来一个第三方包，
    别人 clone 之后就会红在环境上。基线子进程用来扣掉解释器自带的启动模块。
    """
    baseline, baseline_proc = _top_level_modules("pass")
    loaded, target_proc = _top_level_modules("import agenerp.apply")

    assert baseline_proc.returncode == 0, baseline_proc.stderr
    assert target_proc.returncode == 0, target_proc.stderr
    residue = {
        name
        for name in loaded - baseline
        if name != "agenerp" and name not in sys.stdlib_module_names
    }
    assert not residue, f"agenerp.apply 拉进了第三方模块：{sorted(residue)}"
    assert "agenerp" in loaded, "子进程根本没导入 agenerp —— 这条判据是假的"


@pytest.mark.parametrize(
    "order",
    [
        "import agenerp.pack; import agenerp.apply",
        "import agenerp.apply; import agenerp.pack",
    ],
)
def test_import_order_does_not_deadlock(order: str):
    """`pack` ↔ `apply` 不许有顶层循环导入。

    `apply_pack` 用到 `agenerp.apply` 时在**函数体内**导入；有人把它提到模块顶层，
    两个导入次序里就会有一个炸 `ImportError`（partially initialized module）。
    """
    _, proc = _top_level_modules(order)

    assert proc.returncode == 0, f"导入次序 {order!r} 失败：{proc.stderr}"


def test_apply_plan_can_be_constructed_empty():
    """`ApplyPlan` 的默认值是三个空序列 —— 调用方不必给全参数。"""
    assert ApplyPlan(scope=PACK_SCOPE).is_empty()
