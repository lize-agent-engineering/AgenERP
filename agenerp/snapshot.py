"""站点状态快照与结构化 diff。

三个部件，职责互不重叠（结构边界见 `docs/architecture/module-boundaries.md` §11.5）：

- `Snapshot`：不可变值对象，只承载「某一时刻某 scope 的结构化状态」。不持连接、不做 I/O 缓存。
- 来源（`SnapshotSource`）：唯一做 I/O 的地方。本模块交付**离线来源**与**站点来源**；
  站点侧的 HTTP 传输在 `agenerp.site`（§11.7），本模块不自己开第二个连接落点。
- `diff`：纯函数，不碰来源，产出机器可判定的 added / removed / changed。

「结构化」的含义：调用方靠三个序列回答「什么被加/删/改了」，不必解析 `summary()` 的文本。
`summary()` 只供人读（断言失败信息、日志），**不是判定面**。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from agenerp.oob import TRIM_TABLE, OobError, Runner, run_json
from agenerp.pack import normalize
from agenerp.site import SiteClient, client_from_env

# 离线来源的约定根目录：仓内 `.agenerp/snapshots/<scope>/*.json`。
# 目录不存在 = 零条目快照，**不是错误**——今天仓里还没有快照数据，这条读取路径本身是真的。
OFFLINE_ROOT_ENV = "AGENERP_SNAPSHOT_DIR"
_DEFAULT_OFFLINE_ROOT = Path(__file__).resolve().parents[1] / ".agenerp" / "snapshots"

# 有站点配置时走站点来源。次序是**显式来源 > 站点配置 > 离线来源**，见 `resolve_source`。
SITE_ENV = "AGENERP_SITE"

# 离线快照文件里承载字段清单的键，与 `agenerp.pack` 的定制导出同名。
_ENTRIES_KEY = "custom_fields"
_IDENTITY_KEY = "fieldname"
_DOCTYPE_KEY = "doctype"

# 站点行里承载「这个字段挂在哪个 DocType 上」的列名是 `dt`，**不叫 `doctype`**
# （`_DOCTYPE_KEY` 是**包文件**那侧的键，两边不能互抄）。身份是 `(doctype, fieldname)`
# 二元组：只按字段名去重会把两个 DocType 上的同名字段混成一条。
_SITE_DOCTYPE_KEY = "dt"

# 站点来源认识的 scope → 承载它的 DocType。**未知 scope 显式抛，不返回空元组**：
# 返回空会让「这个 scope 拼错了」和「这个 scope 下没有定制」长得一模一样。
SITE_SCOPE_DOCTYPES: dict[str, str] = {"doctypes": "Custom Field"}


class SnapshotScopeMismatch(ValueError):
    """两个 scope 不同的快照被 diff。

    静默地当成「全删全增」会让调用方以为站点被清空又重建，
    所以这里必须显式报错而不是降级。
    """


@dataclass(frozen=True)
class SnapshotEntry:
    """快照里的一个条目：某个 DocType 上的某个字段。

    形状由 `tests/gates/test_snapshot_diff_structured.py` 的 live 断言定稿
    （`c.doctype == "Item" and c.fieldname == "agenerp_gate_probe"`），
    工作项 6 接手时不需要改这里。
    """

    doctype: str
    fieldname: str
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str]:
        return (self.doctype, self.fieldname)


@dataclass(frozen=True)
class ChangedEntry:
    """一个既没被加也没被删、但属性变了的条目。前后值都带出来，调用方不必回头再查快照。"""

    doctype: str
    fieldname: str
    before: dict[str, Any] = field(default_factory=dict)
    after: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str]:
        return (self.doctype, self.fieldname)


@dataclass(frozen=True)
class Snapshot:
    """某一时刻、某 scope 下的结构化状态。

    **相等性只看 scope 与条目内容**：`source` 只是溯源信息（`compare=False`），
    且这里根本不携带采集时刻——带了它，「同一站点两次快照相等」永远不成立，
    这正是 Spike 06 在定制包上踩过的坑（易变字段污染 diff）。
    """

    scope: str
    entries: tuple[SnapshotEntry, ...] = ()
    source: str = field(default="", compare=False)

    def __len__(self) -> int:
        return len(self.entries)

    def by_key(self) -> dict[tuple[str, str], SnapshotEntry]:
        return {entry.key: entry for entry in self.entries}


class SnapshotSource(Protocol):
    """快照的数据来源。**唯一做 I/O 的接缝**——`capture` 与 `diff` 都不碰外部世界。

    `identity` 是人读的溯源串（路径 / 站点名），只进 `Snapshot.source`，不参与相等性。
    """

    identity: str

    def read(self, scope: str) -> tuple[SnapshotEntry, ...]:
        """返回该 scope 下的全部条目。

        **离线来源**：位置不存在时返回空元组，不抛异常（「还没有定制」是合法状态）。
        **站点来源**：站点答不上话不是合法状态，抛 `agenerp.site.SiteError`——
        降级成空会让「未改动 → diff 为空」在站点宕机时照样绿。见 §11.5 与 §11.7。
        """
        ...


@dataclass(frozen=True)
class OfflineSnapshotSource:
    """从仓内约定位置读快照：`<root>/<scope>/*.json`，一个 DocType 一个文件。

    文件形状（`doctype` 缺省时取文件名）::

        {"doctype": "Item", "custom_fields": [{"fieldname": "brand_code", "fieldtype": "Data"}]}

    读到的载荷先过 `agenerp.pack.normalize`：剥掉 modified / creation / owner 等易变字段，
    否则「什么都没改重新导出」也会 diff 出差异——快照的确定性与定制包是同一条要求，
    不该有第二套口径。
    """

    root: Path

    @property
    def identity(self) -> str:
        return f"offline:{self.root}"

    def read(self, scope: str) -> tuple[SnapshotEntry, ...]:
        return read_scope_dir(self.root, scope)


@dataclass(frozen=True)
class SiteSnapshotSource:
    """活站点来源：站点现状 → 条目。I/O 全部委给 `agenerp.site`（§11.7）。

    `client` 是**可选注入**（默认 `None` → 走 `client_from_env`），既有构造式
    `SiteSnapshotSource(site)` 的调用点一个字不用改。注入的目的是让单测能喂假客户端，
    而不是让产品代码多一条配置路径。

    **口径与离线来源同源**：载荷同样先过 `agenerp.pack.normalize` 剥易变字段
    （modified / creation / owner / `_comments`），否则同一站点两次快照必然 diff 出差异。
    不开第二套口径——§11.5 的「不该有第二份」。
    """

    site: str
    client: SiteClient | None = None

    @property
    def identity(self) -> str:
        return f"site:{self.site}"

    def read(self, scope: str) -> tuple[SnapshotEntry, ...]:
        doctype = SITE_SCOPE_DOCTYPES.get(scope)
        if doctype is None:
            raise ValueError(
                f"站点来源不认识 scope {scope!r}；已知：{sorted(SITE_SCOPE_DOCTYPES)}"
            )
        client = self.client if self.client is not None else client_from_env(self.site)
        entries = entries_from_site_rows(client.list_resource(doctype))
        return tuple(sorted(entries, key=lambda entry: entry.key))


def read_scope_dir(root: Path, scope: str) -> tuple[SnapshotEntry, ...]:
    """按 `<root>/<scope>/*.json` 读出该 scope 的全部条目，一个 DocType 一个文件。

    **目录布局与解析口径的唯一落点**：离线来源与 `agenerp.apply.read_pack` 都走这里，
    不许各自再写一遍——两套口径会让「包里读到的」和「站点快照读到的」在同一份 JSON 上
    得出不同条目，求差结果随之失真。位置不存在返回空元组，不抛。
    """
    scope_dir = root / scope
    if not scope_dir.is_dir():
        return ()
    entries: list[SnapshotEntry] = []
    for path in sorted(scope_dir.glob("*.json")):
        entries.extend(entries_from_payload(json.loads(path.read_text()), path.stem))
    return tuple(sorted(entries, key=lambda entry: entry.key))


def _normalized_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"快照文件必须是 JSON 对象，读到 {type(payload).__name__}")
    return normalize(payload)


def doctype_from_payload(payload: Any, default_doctype: str) -> str:
    """一份快照/定制包载荷讲的是**哪个 DocType**：载荷 `doctype` 键优先、文件名兜底。

    与 `entries_from_payload` 走同一条判定（两者都经 `_normalized_payload`）。
    差集 apply 的作用域收窄靠它算「这个包管辖哪些 DocType」，两套口径会让管辖面与条目面对不上：
    一份 `Item.json` 内写 `{"doctype": "Customer"}` 时，条目算 Customer 而管辖面算 Item。
    """
    return str(_normalized_payload(payload).get(_DOCTYPE_KEY, default_doctype))


def entries_from_payload(payload: Any, default_doctype: str) -> list[SnapshotEntry]:
    normalized = _normalized_payload(payload)
    doctype = str(normalized.get(_DOCTYPE_KEY, default_doctype))
    rows = normalized.get(_ENTRIES_KEY, [])
    if not isinstance(rows, list):
        raise ValueError(f"{doctype} 的 {_ENTRIES_KEY} 必须是列表，读到 {type(rows).__name__}")
    entries = []
    for row in rows:
        if not isinstance(row, dict) or _IDENTITY_KEY not in row:
            raise ValueError(f"{doctype} 的条目缺少 {_IDENTITY_KEY}：{row!r}")
        attributes = {k: v for k, v in row.items() if k != _IDENTITY_KEY}
        entries.append(SnapshotEntry(doctype, str(row[_IDENTITY_KEY]), attributes))
    return entries


def entries_from_site_rows(rows: Any) -> list[SnapshotEntry]:
    """站点上的 Custom Field 行 → 快照条目。**「一行变成哪些属性」的唯一落点。**

    投影口径是「剥掉易变键之后全留」。将来若为 diff 可读性收窄它（例如再剥空值），
    只能改这一个地方：导出与站点读取用不同投影，会让 `plan_apply` 把每个字段都算成 `changed`。
    """
    if not isinstance(rows, list):
        raise ValueError(f"站点返回的行集合必须是列表，读到 {type(rows).__name__}")
    entries: list[SnapshotEntry] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"站点行必须是对象，读到 {type(row).__name__}：{row!r}")
        doctype = row.get(_SITE_DOCTYPE_KEY)
        fieldname = row.get(_IDENTITY_KEY)
        if not doctype or not fieldname:
            raise ValueError(
                f"站点行缺少 {_SITE_DOCTYPE_KEY} / {_IDENTITY_KEY}，无法定身份：{row!r}"
            )
        normalized = normalize(row)
        attributes = {
            key: value
            for key, value in normalized.items()
            if key not in (_SITE_DOCTYPE_KEY, _IDENTITY_KEY)
        }
        entries.append(SnapshotEntry(str(doctype), str(fieldname), attributes))
    return entries


def resolve_source(source: SnapshotSource | None = None) -> SnapshotSource:
    """定下这次快照从哪读：显式来源 > 站点配置 > 离线来源。

    没有站点配置时走离线来源，而**不是**抛异常——否则两条 L1 门禁会永远红在环境上，
    而不是红在实现上（W0.6「红得不对」的同一个坑）。
    """
    if source is not None:
        return source
    site = os.environ.get(SITE_ENV, "").strip()
    if site:
        return SiteSnapshotSource(site)
    root = os.environ.get(OFFLINE_ROOT_ENV, "").strip()
    return OfflineSnapshotSource(Path(root) if root else _DEFAULT_OFFLINE_ROOT)


def capture(scope: str, source: SnapshotSource | None = None) -> Snapshot:
    """对当前站点在 `scope` 范围内打一次状态快照。"""
    resolved = resolve_source(source)
    return Snapshot(scope=scope, entries=tuple(resolved.read(scope)), source=resolved.identity)


@dataclass(frozen=True)
class Diff:
    """两次快照之间的结构化差异。三个序列是判定面，`summary()` 只给人看。"""

    scope: str
    added: tuple[SnapshotEntry, ...] = ()
    removed: tuple[SnapshotEntry, ...] = ()
    changed: tuple[ChangedEntry, ...] = ()

    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)

    def summary(self) -> str:
        if self.is_empty():
            return f"scope={self.scope}：无差异"
        parts = [
            f"{label} {len(items)}：{', '.join(f'{e.doctype}.{e.fieldname}' for e in items)}"
            for label, items in (
                ("新增", self.added),
                ("删除", self.removed),
                ("变更", self.changed),
            )
            if items
        ]
        return f"scope={self.scope} · " + " · ".join(parts)


def diff(before: Snapshot, after: Snapshot) -> Diff:
    """比较两次快照，给出结构化的 added / removed / changed。

    纯函数：不读来源、不改入参。scope 不同的两个快照**不许**被比较。
    """
    if before.scope != after.scope:
        raise SnapshotScopeMismatch(
            f"两个快照的 scope 不同（{before.scope!r} vs {after.scope!r}），"
            "拒绝把它当成「全删全增」"
        )
    old, new = before.by_key(), after.by_key()
    added = tuple(new[key] for key in sorted(new.keys() - old.keys()))
    removed = tuple(old[key] for key in sorted(old.keys() - new.keys()))
    changed = tuple(
        ChangedEntry(*key, before=old[key].attributes, after=new[key].attributes)
        for key in sorted(old.keys() & new.keys())
        if old[key].attributes != new[key].attributes
    )
    return Diff(scope=before.scope, added=added, removed=removed, changed=changed)


def schema_drift(
    doctype: str, site: str | None = None, runner: Runner | None = None
) -> tuple[str, ...]:
    """`doctype` 的物理表上**存在、但按 Frappe 自己的口径不属于任何字段**的列，排序去重。

    这是「孤儿列巡检」的唯一落点。口径**直接复用 Frappe 的 `frappe.model.meta.trim_table`**
    （`dry_run=True`，经 `agenerp.oob` 的白名单带外调用，§11.8）：它算的是
    `set(表上的列) - set(有值字段)`，再剥掉 `default_fields + optional_fields +
    child_table_fields` 与 `_` 前缀的框架列。自己用 `information_schema` 减一遍
    `tabDocField` / `tabCustom Field` 也能算出同一集合，但那会产生**第二套字段口径**——
    Frappe 一次升级就能让两边错开，而错开的表现是「孤儿列漏报」，最难发现的那种假绿（§11.5）。

    返回 `tuple[str, ...]`（不是 `Any`）：调用方靠它做 `in` 与集合运算，不定型只能靠猜。

    **站点答不上话时抛 `agenerp.oob.OobError`，不返回空元组**——空元组是「没有孤儿列」这个
    合法结论的表示，用它兼表「命令没跑起来」会让门禁在栈坏掉时照样绿（与 §11.7 同一条约定）。

    `site` / `runner` 是可选注入（默认按 `AGENERP_SITE` 与 `docker compose exec` 解析），
    目的与 `SiteSnapshotSource.client` 一样：让单测喂假件，不是给产品代码多一条配置路径。
    """
    columns = run_json(TRIM_TABLE, doctype=doctype, site=site, runner=runner)
    if not isinstance(columns, list):
        raise OobError(
            f"{TRIM_TABLE} 对 {doctype} 回的不是列表，读到 {type(columns).__name__}：{columns!r:.200}"
        )
    for column in columns:
        if not isinstance(column, str):
            raise OobError(f"{TRIM_TABLE} 对 {doctype} 回的列名不是字符串：{column!r}")
    return tuple(sorted(set(columns)))
