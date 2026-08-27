"""🔴 P2.2 · 路线 C 的主判据：**车间工人的日常视图，落回 Desk 的次数 = 0**。

## 这条判据代表什么

人 2026-08-27 选定路线 C：不重写 Desk（`system-baseline.md` §3.2 已判那条走不通 ——
Desk 覆盖 ~30 种 fieldtype，重写必须 100% 完备，Frappe 核心开发者自己的尝试
2022 年就停了），而是把「100% 完备」的**分母**从「全部 1000+ DocType」换成
「**这个角色每天碰的那几个**」。

⇒ **「落回 = 0」就是「统一在一个前端」这句话的可执行形式。**

## 防作弊：视图定义先于实现提交

`agenerp/dsl/roles.py` 落在 `957ac06`，**早于渲染器实现**。当时实测落回 = **3**
（R1，plan §2.1）。若允许事后调视图定义，这条判据就退化成
「我挑了一组不会落回的字段」。**git 的先后是这条判据的一部分。**

## ⚠️ 它守不到什么（写清楚，免得有人以为守到了）

- **只对车间工人成立。** 别的角色可读的 DocType 不同，缺的 fieldtype 也不同。
- **不验真的画对了。** 那是 `tests/render/` 的活体判据（真浏览器）。
  本文件验的是**判定**：这一版渲染器**声称**画得了这些块。
"""

from __future__ import annotations

import pytest

from agenerp.dsl.fallback import plan_render
from agenerp.dsl.roles import WORKER_DAILY_VIEWS, WORKER_DOCTYPES
from agenerp.dsl.validate import validate


@pytest.mark.parametrize("view", WORKER_DAILY_VIEWS, ids=[v.name for v in WORKER_DAILY_VIEWS])
def test_every_worker_view_validates(view, schema):
    # 硬约束 ④：每一处字段引用都要指回真实存在的字段。
    result = validate(view, schema)
    assert result.ok, f"{view.name} 校验不过：{result.errors}"


@pytest.mark.parametrize("view", WORKER_DAILY_VIEWS, ids=[v.name for v in WORKER_DAILY_VIEWS])
def test_no_worker_view_falls_back_to_desk(view, schema):
    """🔴 R2 · 路线 C 的主判据。"""
    plan = plan_render(view, schema)
    assert plan.fallbacks == (), (
        f"{view.name} 还有 {len(plan.fallbacks)} 块落回 Desk：\n"
        + "\n".join(f"  · blocks[{f.index}]（{f.block_type}）{f.reason}" for f in plan.fallbacks)
    )


def test_the_worker_views_actually_exercise_the_four_missing_fieldtypes(schema):
    """防作弊：这三个视图**必须**碰到那 4 种当初缺的类型。

    否则「落回 = 0」可能只是因为我挑了一组本来就画得了的字段 ——
    那样这条判据在「补齐了没有」这一维上是空的（P1 复盘 §1.2 同形）。
    """
    used = set()
    for view in WORKER_DAILY_VIEWS:
        for doctype, fieldname in view.field_refs():
            kind = schema.fieldtype(doctype, fieldname)
            if kind:
                used.add(kind)
    for kind in ("Table", "Text Editor", "Attach Image", "Attach"):
        assert kind in used, f"没有任何一个工人视图碰到 {kind}，这条判据因此是空的"


def test_the_worker_views_only_touch_doctypes_the_role_can_actually_read(schema):
    """权限是真的：车间工人只可读三张表（`agenerp/seedusers.py:39`）。

    视图若引用了角色读不到的 DocType，用户看到的就是一片「无权限」——
    那不叫「统一在一个前端」。

    ⚠️ 子表随其父表的权限走，所以把三张表的 `Table` 字段指向的子表一并算进来 ——
    **子表映射来自活站点导出（`child-tables.json`），不手写。**
    """
    allowed = set(WORKER_DOCTYPES)
    for parent in WORKER_DOCTYPES:
        for fieldname, fieldtype in schema.fields_of(parent):
            if fieldtype != "Table":
                continue
            child = schema.child_doctype(parent, fieldname)
            if child:
                allowed.add(child)

    for view in WORKER_DAILY_VIEWS:
        for block in view.blocks:
            if block.doctype:
                assert block.doctype in allowed, (
                    f"{view.name} 的 blocks 引用了角色读不到的 {block.doctype}"
                )
            for _table_field, child_doctype, _names in block.child_fields:
                assert child_doctype in allowed, (
                    f"{view.name} 展开了角色读不到的子表 {child_doctype}"
                )

