"""差集 apply 引擎的 **A 半**：读包 → 与站点现状求差 → 产出含**删除计划**的 `ApplyPlan`。

为什么这半边要自建（`docs/architecture/module-boundaries.md` §11.1 的实测结论）：
Frappe 的 `sync_customizations_for_doctype` 是**纯 upsert，没有任何删除分支**——
从定制包 JSON 里删掉一个字段再 sync，站点上的字段纹丝不动，`git revert` 撤不掉定制。
「删除集」这个概念在那条路径上根本不存在，它正是本项目必须自己长出来的东西。

职责切分（本模块只做前者）：

- **算出删除集是纯逻辑** —— `read_pack` / `plan_apply`，无 I/O 副作用、不接站点，判据在 `tests/unit/`。
- **执行删除才需要活站点** —— `execute_plan` 在此只留接缝并 `raise`，归工作项 6 与同一个 successor。

三个序列（`creates` / `updates` / `deletes`）是判定面；`summary()` 只供人读（断言失败信息、日志），
**不是判定面**——与 `agenerp.snapshot.Diff` 是同一条约定，不开第二口径。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agenerp.snapshot import ChangedEntry, Snapshot, SnapshotEntry, diff, read_scope_dir

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
    """方向不变量：建 = 只在包里，删 = 只在站点上，改 = 两边都有。"""
    in_desired, in_current = desired.by_key(), current.by_key()
    for entry in plan.creates:
        assert entry.key in in_desired and entry.key not in in_current, (
            f"creates 里出现了站点上已有的 {entry.key}——desired / current 传反了"
        )
    for entry in plan.deletes:
        assert entry.key in in_current and entry.key not in in_desired, (
            f"deletes 里出现了定制包里仍有的 {entry.key}——desired / current 传反了"
        )
    for entry in plan.updates:
        assert entry.key in in_desired and entry.key in in_current, (
            f"updates 里出现了只存在于一侧的 {entry.key}"
        )


def execute_plan(plan: ApplyPlan, site: str) -> None:
    """对活站点执行 `plan`，**含真正的删除**。B 半的唯一落点。"""
    raise NotImplementedError(
        "execute_plan 尚未实现 —— 差集 apply 引擎的 B 半（对站点执行）。"
        "它要的 live_site / pack_repo 两个 fixture 全在 tests/gates/conftest.py（AGENTS.md 红线 1），"
        "loop 无权实现；归 docs/backlog/p0-foundation-roadmap.md 工作项 6，"
        "重开条件见 docs/masterplan/STATE.md §3 的 [open] 行（处置项 a/b/c/d 只有人能选）。"
        f"（本次计划：{plan.summary()}，目标站点 {site!r}）"
    )
