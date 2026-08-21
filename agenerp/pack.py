"""定制包（customization pack）的导出、规范化与 apply。

`normalize`（工作项 1）、`export_customizations`（工作项 6 的前半）与 `apply_pack`
（工作项 5，委派链的入口，含对差集执行删除）均已实现。签名逐字对齐 tests/gates/ 里的调用处。

本模块是「条目 → 包文件」的**唯一写入口径**；读回那一侧在 `agenerp.snapshot`
（`read_scope_dir` / `entries_from_payload`），两者互为逆。结构边界与排版裁定见
`docs/architecture/module-boundaries.md` §11.6。

⚠️ **不得在模块顶层 import `agenerp.snapshot` 或 `agenerp.apply`**：`snapshot` 顶层导入
本模块的 `normalize`，提到顶层就是循环导入。需要它们的函数在**函数体内**导入，
判据在 `tests/unit/test_apply_plan.py::test_import_order_does_not_deadlock`。
"""

import json
import os
from pathlib import Path
from typing import Any

_TODO = "尚未实现 —— 见 docs/backlog/p0-foundation-roadmap.md 的工作项对照表"

# 易变字段的判定口径：按**键名子串**黑名单剥离，不按值猜。
# 新增易变键时改这里——这是唯一落点，行为覆盖在 tests/unit/test_pack_normalize.py。
VOLATILE_KEY_SUBSTRINGS: tuple[str, ...] = ("modified", "creation", "owner", "_comments")

# 列表条目的稳定身份键（Frappe 定制导出里 custom_fields / property_setters 都用它）。
_IDENTITY_KEY = "fieldname"


def normalize(export: dict[str, Any]) -> dict[str, Any]:
    """把一次原始定制导出规范化成可 diff 的确定性结构。

    剥掉 modified / creation / owner / _comments 等易变字段，并稳定排序。

    纯函数：返回全新对象，绝不就地修改入参（调用方的两次快照必须互不污染）。
    幂等：``normalize(normalize(x)) == normalize(x)``。
    """
    return _normalize_value(export)


def _is_volatile_key(key: Any) -> bool:
    """键名**含**任一易变词即算易变（`modified_by` / `owner_id` 一并剥掉）。

    门禁断言对 `repr(normalize(...))` 做子串检查，精确键名匹配挡不住派生键。
    """
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(word in lowered for word in VOLATILE_KEY_SUBSTRINGS)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if not _is_volatile_key(key)
        }
    if isinstance(value, (list, tuple)):
        items = [_normalize_value(item) for item in value]
        if items and all(isinstance(item, dict) for item in items):
            items.sort(key=_entry_sort_key)
        return items
    return value


def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, str]:
    """条目的稳定身份：优先 `fieldname`，缺失时退化为规范化后的表示。"""
    identity = entry.get(_IDENTITY_KEY)
    return ("" if identity is None else str(identity), repr(entry))


# 包文件那侧的两个键。读回那侧的对应物是 `agenerp.snapshot` 的 `_DOCTYPE_KEY` / `_ENTRIES_KEY`，
# 两处必须一致——`tests/unit/test_pack_export.py` 有一条测试直接把它们钉在一起。
PACK_DOCTYPE_KEY = "doctype"
PACK_ENTRIES_KEY = "custom_fields"

_INDENT = "  "


def render_doctype_file(doctype: str, rows: list[dict[str, Any]]) -> str:
    """条目 → 包文件文本。**「怎么排版」的唯一落点**，纯函数、不碰磁盘。

    排版取「一条目一行 + `,` 独占一行」，`[` 与 `]` 各自独占一行（裁定与备选见 §11.6）：
    判据是 `test_export_produces_readable_diff_only` 的逐行断言——变动行要么含新字段名，
    要么 `line.strip() in "{}[],"`。本排版下**任意位置**插入一个条目都只新增
    「条目行 + 逗号行」两行，而 `,` 自身满足那条断言。

    行尾逗号排版（`{…},`）看着更常见，但探针插到数组末尾时要给前一个条目补逗号，
    那一行随之变动而它不含新字段名 → 红。空数组同理不能写成 `"custom_fields": []`：
    从空变非空会改到那一行。
    """
    lines = [
        "{",
        f"{_INDENT}{json.dumps(PACK_DOCTYPE_KEY)}: {json.dumps(doctype, ensure_ascii=False)},",
        f"{_INDENT}{json.dumps(PACK_ENTRIES_KEY)}: [",
    ]
    for index, row in enumerate(rows):
        if index:
            lines.append(f"{_INDENT * 2},")
        lines.append(_INDENT * 2 + json.dumps(row, ensure_ascii=False, sort_keys=True))
    lines.append(f"{_INDENT}]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def export_customizations(doctype: str, into: str, source: Any = None) -> None:
    """把某个 DocType 的定制从活站点导出到定制包工作副本 `into`。

    写 `<into>/doctypes/<DocType>.json`，**只动这一个文件**，同目录其他 DocType 不受影响。

    站点读取**复用 `capture` + `SiteSnapshotSource`，不新开第二条站点查询**：往返一致
    因此由构造保证（同一来源、同一投影、同一 `normalize`），关分页的完整性直接继承
    `agenerp.site.SiteClient.list_resource`。自己再发一次查询就会出现第二套口径。

    `source` 是可选注入（默认 `None` → 按 `AGENERP_SITE` 构造站点来源），目的与
    `SiteSnapshotSource.client` 一样：让单测喂假件，不是给产品代码多一条配置路径。
    这里**刻意不走 `snapshot.resolve_source`**——它「无站点配置就退回离线来源」，
    在导出这条路径上会把一个空包写进磁盘，而空包读起来跟「这个 DocType 的定制全被删了」
    一模一样，apply 会照着它去删。

    分界写死：**空数组文件只在站点成功答出「零条目」时才写**；站点名未配置 / 答不上话 /
    认证失败一律抛 `SiteError` 且**不留下任何文件**。零条目也必须落盘——门禁的 baseline
    走 `git diff HEAD`，它看不见未跟踪文件，基线不落盘的话「加了字段却没有 diff」恒红。
    """
    from agenerp.apply import PACK_SCOPE
    from agenerp.site import SiteError
    from agenerp.snapshot import SITE_ENV, SiteSnapshotSource, capture

    resolved = source
    if resolved is None:
        site = os.environ.get(SITE_ENV, "").strip()
        if not site:
            raise SiteError(
                f"导出定制包需要活站点：设置 {SITE_ENV}（导出不退回离线来源——"
                "退回会写出一个空包，而空包与「定制全被删了」在 apply 眼里一模一样）"
            )
        resolved = SiteSnapshotSource(site)

    snapshot = capture(PACK_SCOPE, source=resolved)
    rows = [
        {_IDENTITY_KEY: entry.fieldname, **entry.attributes}
        for entry in snapshot.entries
        if entry.doctype == doctype
    ]
    rows.sort(key=lambda row: str(row[_IDENTITY_KEY]))

    target = Path(into) / PACK_SCOPE / f"{doctype}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_doctype_file(doctype, rows), encoding="utf-8")


def apply_pack(path: str, site: str) -> None:
    """把定制包 `path` 应用到站点 `site`，**含对差集执行删除**。

    委派给 `agenerp.apply`，四步：读包 → 求差 → **收窄** → 执行。签名不变（门禁逐字调用
    `apply_pack(pack_repo.path, site=live_site.name)`），`site` 是**站点名**不是 URL——
    地址与凭据仍由 `agenerp.site` 从环境解析。

    **收窄那一步不能省，也只能落在这里**：`current` 是**整个 scope 的站点现状**，
    而包通常只管几个 DocType；不收窄就会把包没覆盖到的 DocType 上的定制一并删光
    （2026-08-21 活站点实测：只含 `Item.json` 的包算出 11 条 `deletes`，10 条是别的 DocType 上
    应用自带的字段）。管辖面要读包**目录**才算得出来，而 `execute_plan` 只拿得到条目——
    所以落点在委派链里，不在 `execute_plan` 内。裁定与备选见
    `docs/architecture/module-boundaries.md` §11.6。

    收窄在求差**之后**：方向不变量已先对全集通过，过滤只做删减，不影响它的结论。

    `agenerp.apply` 在**函数体内**导入：`apply` 顶层已经导入 `snapshot`，而 `snapshot` 顶层
    导入本模块的 `normalize`；把它提到顶层就是 `pack` ↔ `apply` 循环导入。
    判据在 `tests/unit/test_apply_plan.py::test_import_order_does_not_deadlock`。
    """
    from agenerp.apply import (
        PACK_SCOPE,
        execute_plan,
        narrow_deletes,
        pack_doctypes,
        plan_apply,
        read_pack,
    )
    from agenerp.snapshot import SiteSnapshotSource, capture

    desired = read_pack(path)
    current = capture(PACK_SCOPE, source=SiteSnapshotSource(site))
    plan = plan_apply(desired=desired, current=current)
    execute_plan(narrow_deletes(plan, pack_doctypes(path)), site)
