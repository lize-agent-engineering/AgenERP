"""🔴 快照必须包含 Frappe 的**标准字段** —— 活体实测抓出来的缺口。

## 怎么抓到的（2026-08-28，P2.3 Phase 3）

问「库存转移一共有多少笔」，模型交的是 `metric` / `agg=count` /
`fields=["name"]` —— **那是正解**：`name` 是每张单据的主键，计它的行数就是笔数。

校验器回的是：

    字段不存在：Stock Entry.name

因为快照只收 `DocType.fields`（即 DocField），而 `name` / `creation` / `modified` /
`owner` / `modified_by` / `docstatus` / `idx` 这些**每张表上都真实存在**的标准字段
一个都不在里面。模型于是退到 `naming_series` —— 一个语义更差的字段。

**模型答对了，我们的 schema 说它不存在。** 这与 P2.0R 那一串同族
（`docs/logs/2026/08-28-handoff-p2.md` §3④）：**每一次「能力失败」往下查都是 harness。**

## 边界

这里只管「快照如实包含它们」。它们**确实在**每张 Frappe 表上 ——
不是我们造出来的字段，`frappe.model.default_fields` 就是这一组。
"""

from __future__ import annotations

import json
import pathlib

from agenerp import schema_snapshot

# ⚠️ 用绝对路径，不用相对路径：相对路径把判据绑死在 cwd 上，换个目录跑就 FileNotFoundError。
_SNAPSHOT = pathlib.Path(__file__).resolve().parents[2] / "agenerp" / "schema" / "view-schema.json"


def test_the_standard_field_set_is_declared():
    """这一组是 Frappe 的 `default_fields`，不是我们编的。"""
    assert "name" in schema_snapshot.STANDARD_FIELDS
    assert "creation" in schema_snapshot.STANDARD_FIELDS
    assert "docstatus" in schema_snapshot.STANDARD_FIELDS
    # 每一条都要带类型 —— 渲染器按类型判画得了画不了，没类型等于画不了。
    for fieldname, fieldtype in schema_snapshot.STANDARD_FIELDS.items():
        assert fieldtype, f"{fieldname} 没有 fieldtype"


def test_every_doctype_in_the_committed_snapshot_has_them():
    payload = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    by_doctype: dict[str, set[str]] = {}
    for row in payload["fields"]:
        by_doctype.setdefault(row["doctype"], set()).add(row["fieldname"])

    assert by_doctype, "快照是空的"
    for doctype, fields in by_doctype.items():
        missing = set(schema_snapshot.STANDARD_FIELDS) - fields
        assert not missing, f"{doctype} 少了标准字段：{sorted(missing)}"


def test_the_loaded_schema_view_accepts_a_count_on_name():
    """🔴 端到端那一条：**`count(name)` 必须验得过。**

    这就是被拒掉的那个正解。少了这一条，快照回退时没人发现。
    """
    schema = schema_snapshot.load()
    assert schema is not None
    for doctype in schema.doctypes():
        assert schema.has_field(doctype, "name"), f"{doctype}.name 验不过"


def test_the_standard_fields_are_drawable():
    """加进来的字段类型必须是这一版渲染器画得了的 —— 否则等于给视图埋落回。"""
    from agenerp.dsl.fallback import RENDERABLE_FIELDTYPES

    for fieldname, fieldtype in schema_snapshot.STANDARD_FIELDS.items():
        assert fieldtype in RENDERABLE_FIELDTYPES, f"{fieldname} 是 {fieldtype}，画不了"
