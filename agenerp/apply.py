"""差集 apply 引擎：读包 → 与站点现状求差 → **对差集在活站点上执行删除**。

为什么整条要自建（`docs/architecture/module-boundaries.md` §11.1 的实测结论）：
Frappe 的 `sync_customizations_for_doctype` 是**纯 upsert，没有任何删除分支**——
从定制包 JSON 里删掉一个字段再 sync，站点上的字段纹丝不动，`git revert` 撤不掉定制。
「删除集」这个概念在那条路径上根本不存在，它正是本项目必须自己长出来的东西。

职责切分（两半都在本模块，但接触外部世界的只有第二半）：

- **算出删除集是纯逻辑** —— `read_pack` / `plan_apply` / `pack_doctypes` / `narrow_deletes`，
  无 I/O 副作用、不接站点，判据在 `tests/unit/`。
- **执行删除才需要活站点** —— `execute_plan`，I/O 全部委给 `agenerp.site`（§11.7）。

**执行前必须先收窄**（这是本模块唯一一条「不这么做就会静默毁坏站点」的约束，所以写在最前面）：
`apply_pack` 里的 `current` 是**整个 scope 的站点现状**，而一个定制包通常只管几个 DocType。
直接执行 `plan.deletes` 会把包没覆盖到的 DocType 上的定制一并删光——2026-08-21 活站点实测：
只含 `Item.json` 的包算出 11 条 `deletes`，其中 10 条是别的 DocType 上应用自带的字段。
门禁那条断言照样会绿（它只看 Item 上的探针没了），**判据挡不住这个错误**，所以收窄自带判据
（`tests/unit/test_apply_execute.py`）。裁定与备选见 §11.6。

**本模块不做建（`creates`）与改（`updates`）**：两者非空时 `execute_plan` 显式抛，
不静默跳过——假装成功比没实现更坏。successor 见 plan `2026-08-21-1922-3` 的 Deferred 第一条。

三个序列（`creates` / `updates` / `deletes`）是判定面；`summary()` 只供人读（断言失败信息、日志），
**不是判定面**——与 `agenerp.snapshot.Diff` 是同一条约定，不开第二口径。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path

from agenerp.oob import Runner, drop_columns
from agenerp.site import SiteClient, client_from_env
from agenerp.snapshot import (
    ChangedEntry,
    Snapshot,
    SnapshotEntry,
    diff,
    doctype_from_payload,
    read_scope_dir,
    schema_drift,
)

# 被收窄 / 被排除的删除条目走这里发 WARNING。**「不许静默丢弃」这条安全承诺的唯一判据面**，
# 也是 `agenerp/` 全树的第一处 logging（plan `2026-08-21-1922-3` 的结构边界表）。
LOGGER = logging.getLogger("agenerp.apply")

# 应用自带的 Custom Field 的标记列。ERPNext / CRM 会往 DocType 上装这类字段，
# 删掉可能直接弄坏应用功能，而按 DocType 收窄挡不住它们（§11.6 裁定 2）。
# `normalize` 不剥这个键（不含 modified / creation / owner / `_comments`），故快照条目里读得到。
SYSTEM_GENERATED_KEY = "is_system_generated"


class ApplyDirectionError(RuntimeError):
    """`desired` / `current` 传反了。

    A 半时这只是纯逻辑自检，用裸 `assert` 就够；B 半接上真删除之后，它是**唯一**挡住
    「把整站定制算成待删」的运行时闸门，而 `python -O` / `PYTHONOPTIMIZE=1` 会把裸 `assert`
    整条剥掉 —— 那正是灾难性误删最可能发生的方式。所以换成显式 `raise`（加严，不是改判定）。
    """


# 定制包的目录布局：`<root>/<scope>/<DocType>.json`，与仓内 `OfflineSnapshotSource` 同一套
# （裁定与备选见 `docs/architecture/module-boundaries.md` §11.6）。
PACK_SCOPE = "doctypes"


@dataclass(frozen=True)
class ApplyPlan:
    """一次 apply 的完整意图：建什么、改什么、**删什么**。

    不可变值对象，不持站点连接、不做 I/O。`deletes` 与另外两个序列同为一等公民——
    Frappe 缺的恰恰是它，把它降级成「可选清理」等于把 revert 能力丢回去。
    """

    scope: str
    creates: tuple[SnapshotEntry, ...] = ()
    updates: tuple[ChangedEntry, ...] = ()
    deletes: tuple[SnapshotEntry, ...] = ()

    def is_empty(self) -> bool:
        return not (self.creates or self.updates or self.deletes)

    def summary(self) -> str:
        if self.is_empty():
            return f"scope={self.scope}：无需 apply"
        parts = [
            f"{label} {len(items)}：{', '.join(f'{e.doctype}.{e.fieldname}' for e in items)}"
            for label, items in (
                ("新建", self.creates),
                ("更新", self.updates),
                ("删除", self.deletes),
            )
            if items
        ]
        return f"scope={self.scope} · " + " · ".join(parts)


def read_pack(path: str | Path, scope: str = PACK_SCOPE) -> Snapshot:
    """把定制包目录读成快照。

    解析口径与 `OfflineSnapshotSource` **同源**（都走 `snapshot.read_scope_dir`）：
    易变字段在那里就被 `normalize` 剥掉了，包与站点现状因此可比。
    目录不存在返回零条目快照而**不抛**——「还没有这个 scope 的定制」是合法状态，
    抛异常会让调用方红在环境而不是红在实现上。
    载荷不是 JSON 对象、或条目缺 `fieldname` 时显式报错，不静默跳过。
    """
    root = Path(path)
    return Snapshot(scope=scope, entries=read_scope_dir(root, scope), source=f"pack:{root}")


def plan_apply(desired: Snapshot, current: Snapshot) -> ApplyPlan:
    """求差：`desired`（定制包）相对 `current`（站点现状）该做哪些动作。

    纯函数：不读来源、不改入参。scope 不同时沿用 `SnapshotScopeMismatch` 拒绝。

    ⚠️ 参数序：`snapshot.diff` 的 `added` = 只在 `after`、`removed` = 只在 `before`，
    因此正确调用是 `diff(before=current, after=desired)`——**与本函数的形参顺序相反**。
    写反了不会报错，只会把「删」算成「建」，所以下面有不变量把守，`tests/unit` 另有互换用例。
    """
    d = diff(before=current, after=desired)
    plan = ApplyPlan(scope=d.scope, creates=d.added, updates=d.changed, deletes=d.removed)
    _assert_direction(plan, desired, current)
    return plan


def _assert_direction(plan: ApplyPlan, desired: Snapshot, current: Snapshot) -> None:
    """方向不变量：建 = 只在包里，删 = 只在站点上，改 = 两边都有。

    **不用裸 `assert`**：见 `ApplyDirectionError` 的 docstring —— `python -O` 下裸 `assert`
    整条消失，而这里是接上真删除之后挡住灾难性误删的最后一道闸。
    """
    in_desired, in_current = desired.by_key(), current.by_key()
    for entry in plan.creates:
        if entry.key not in in_desired or entry.key in in_current:
            raise ApplyDirectionError(
                f"creates 里出现了站点上已有的 {entry.key}——desired / current 传反了"
            )
    for entry in plan.deletes:
        if entry.key not in in_current or entry.key in in_desired:
            raise ApplyDirectionError(
                f"deletes 里出现了定制包里仍有的 {entry.key}——desired / current 传反了"
            )
    for entry in plan.updates:
        if entry.key not in in_desired or entry.key not in in_current:
            raise ApplyDirectionError(
                f"updates 里出现了只存在于一侧的 {entry.key}"
            )


def pack_doctypes(path: str | Path, scope: str = PACK_SCOPE) -> frozenset[str]:
    """这个定制包**管辖**哪些 DocType = `<root>/<scope>/` 里存在文件的那些。

    口径与 `entries_from_payload` **同源**（都走 `snapshot.doctype_from_payload`）：
    载荷 `doctype` 键优先、文件名 stem 兜底。只按文件名算的话，一份 `Item.json` 内写
    `{"doctype": "Customer"}` 会让管辖面与条目面对不上。

    **管辖面不能从 `ApplyPlan` 的条目里推**（§11.6 裁定 1，实测排除的备选 ②）：
    从包里删掉某 DocType 的最后一个字段后，该 DocType 的文件是「**文件在、数组空**」——
    包里一个该 DocType 的条目都没有，按条目推它就不在管辖面内，那条字段永远删不掉。
    「文件在、数组空」= 「这个 DocType 我管，且它应该没有定制」；
    「文件不在」= 「这个 DocType 不归这个包管」。

    目录不存在返回空集合而**不抛**——与 `read_pack` 同一条约定（「还没有这个 scope 的定制」
    是合法状态）。空集合意味着**一条都不删**，方向偏保守，错在安全那一侧。
    """
    scope_dir = Path(path) / scope
    if not scope_dir.is_dir():
        return frozenset()
    return frozenset(
        doctype_from_payload(json.loads(f.read_text(encoding="utf-8")), f.stem)
        for f in sorted(scope_dir.glob("*.json"))
    )


def _describe(entries: tuple[SnapshotEntry, ...]) -> str:
    return ", ".join(f"({e.doctype!r}, {e.fieldname!r})" for e in entries)


def narrow_deletes(plan: ApplyPlan, covered: frozenset[str]) -> ApplyPlan:
    """把 `plan.deletes` 收窄到**包管辖的 DocType**，并排除应用自带的字段。

    纯函数：返回新的 `ApplyPlan`，不改入参，不做 I/O。`creates` / `updates` 原样带过——
    收窄只做删减，不改变方向不变量已经对全集得出的结论。

    **被丢掉的条目一条都不静默**：逐类发一条 WARNING 并列出 `(doctype, fieldname)`。
    静默丢弃与「什么都没删」在调用方眼里一模一样，那正是本仓反复挡的那种事。
    """
    kept: list[SnapshotEntry] = []
    out_of_scope: list[SnapshotEntry] = []
    system_generated: list[SnapshotEntry] = []
    for entry in plan.deletes:
        if entry.doctype not in covered:
            out_of_scope.append(entry)
        elif entry.attributes.get(SYSTEM_GENERATED_KEY):
            system_generated.append(entry)
        else:
            kept.append(entry)

    if out_of_scope:
        LOGGER.warning(
            "apply 跳过 %d 条**不在定制包管辖范围内**的删除（包覆盖的 DocType：%s）：%s",
            len(out_of_scope), sorted(covered) or "（空）", _describe(tuple(out_of_scope)),
        )
    if system_generated:
        LOGGER.warning(
            "apply 跳过 %d 条**应用自带**（%s）的删除：%s",
            len(system_generated), SYSTEM_GENERATED_KEY, _describe(tuple(system_generated)),
        )
    return replace(plan, deletes=tuple(kept))


def execute_plan(
    plan: ApplyPlan,
    site: str,
    client: SiteClient | None = None,
    runner: Runner | None = None,
) -> None:
    """对活站点执行 `plan` 的**删除**部分。差集 apply 的 B 半，唯一落点。

    只做删除（§11.6 裁定 3）：`creates` / `updates` 非空时**显式抛**，不静默跳过。

    删除**顺序确定**（按 `key` 排序）：调用方复跑同一个计划时请求序一致，日志可比对。
    任一条失败即抛（`agenerp.site.SiteError`）且**不继续删后面的**——中途失败会留下
    **部分应用**的状态，本层不做事务/回滚（`02-WBS.md` 把写契约划给 P3.1），这一点不假装。

    空的删除集**零副作用**：连客户端都不构造，所以离线跑一个空计划不会红在缺凭据上。

    `client` 是可选注入（默认 `None` → `client_from_env(site)`），与 `SiteSnapshotSource.client`
    同一个目的：让单测喂假客户端，不是给产品代码多一条配置路径。
    """
    if plan.creates or plan.updates:
        raise NotImplementedError(
            "execute_plan 只实现了删除路径：本次计划里 "
            f"creates {len(plan.creates)} 条、updates {len(plan.updates)} 条，拒绝执行。"
            "建/改的执行是显式 deferred（不是遗漏，也不静默跳过）——"
            "裁定见 docs/architecture/module-boundaries.md §11.6 裁定 3，"
            "successor 见 docs/plans/p0-foundation/2026-08-21-1922-3-execute-plan-site-delete.md "
            "的 ## Deferred But Adjudicated 第一条（重开事件：出现需要用包在站点上建字段的调用方）。"
            f"（本次计划：{plan.summary()}，目标站点 {site!r}）"
        )
    if not plan.deletes:
        return
    resolved = client if client is not None else client_from_env(site)
    deleted = tuple(sorted(plan.deletes, key=lambda e: e.key))
    for entry in deleted:
        resolved.delete_custom_field(entry.doctype, entry.fieldname)
    drop_orphan_columns(deleted, site, runner=runner)


def drop_orphan_columns(
    deleted: tuple[SnapshotEntry, ...], site: str, runner: Runner | None = None
) -> None:
    """删完 Custom Field 之后清掉**本次 apply 自己造成**的残留物理列。

    Frappe 删 Custom Field **不删物理列**（Spike 06 的结论在 v15.119.3 上仍成立，2026-08-21
    活站点复验）。不清的话反复增删会静默累积孤儿列，判据是
    `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`。

    **作用域收窄到交集**（§11.6，与 `narrow_deletes` 是同一条原则）：一列要被删，必须同时
    ① 在 `schema_drift(doctype)` 的返回集合里（**Frappe 自己**判它是孤儿），
    ② 在本次 apply 真删掉的 fieldname 集合里。
    直接调 `trim_table(dry_run=False)` 更省代码，但那会把该 DocType 上**所有**孤儿列一次删光——
    2026-08-21 活站点实测 `Item` 上有 6 条孤儿列、其中 5 条不是本次 apply 造成的（历轮残留）。
    那等于让一次 apply 顺手删掉五列历史数据，违反「apply 只做包表达过的意图」。
    **门禁挡不住这个错误**（它只看探针列没了，多删的另外 5 列一个字都不会说），
    所以收窄自带判据（`tests/unit/test_apply_execute.py`）。

    **`schema_drift` 抛错时本函数也抛，不吞**：把「巡检没跑起来」当成「没有孤儿列」，
    会让残列在站点上静默累积，而门禁照样绿——与 §11.7 第 1 条是同一条约定。

    被跳过的列一条都不静默：沿用本模块的 `LOGGER.warning` 纪律，逐条列出
    `(doctype, column, 跳过原因)`。
    """
    wanted: dict[str, set[str]] = {}
    for entry in deleted:
        wanted.setdefault(entry.doctype, set()).add(entry.fieldname)

    for doctype in sorted(wanted):
        orphans = set(schema_drift(doctype, site=site, runner=runner))
        fieldnames = wanted[doctype]
        removable = sorted(fieldnames & orphans)

        not_orphaned = sorted(fieldnames - orphans)
        if not_orphaned:
            LOGGER.warning(
                "apply 跳过 %d 条**Frappe 不认为是孤儿列**的清除（%s）：%s",
                len(not_orphaned), doctype,
                ", ".join(f"({doctype!r}, {c!r}, '不在 schema_drift 的返回集合里')"
                          for c in not_orphaned),
            )
        untouched = sorted(orphans - fieldnames)
        if untouched:
            LOGGER.warning(
                "apply **不碰** %d 条不是本次 apply 造成的孤儿列（%s）：%s",
                len(untouched), doctype,
                ", ".join(f"({doctype!r}, {c!r}, '本次 apply 没有删过同名字段')"
                          for c in untouched),
            )

        drop_columns(doctype, tuple(removable), site=site, runner=runner)
