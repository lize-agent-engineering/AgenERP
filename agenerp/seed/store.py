"""落盘、读回，以及交给 `agenerp.snapshot.diff` 判定的那座桥。

落盘形状 `<out>/<scope>/<DocType>.json`，目录布局与 `agenerp.snapshot` 的离线来源一致，
**但不复用它的定制包解析口径**：业务单据的身份是单据号 `name`，不是 `fieldname`
（理由见 `docs/architecture/module-boundaries.md` §12.3）。

复用的是**判定面**——把数据集转成 `Snapshot` 后交给已通过门禁的 `diff`，
本仓不为「两次生成是否一样」写第二个比较器。

字节级确定：`sort_keys=True`、固定 `indent`、`ensure_ascii=False`、UTF-8 无 BOM、结尾一个换行。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agenerp.seed.model import SCOPE, Dataset
from agenerp.snapshot import Snapshot, SnapshotEntry

_META_FILE = "_meta"
_RECORDS_KEY = "records"
_IDENTITY_KEY = "name"


def _dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def write(dataset: Dataset, out: Path) -> Path:
    """把数据集写进 `<out>/<scope>/`，返回该 scope 目录。字节级确定。"""
    scope_dir = out / SCOPE
    scope_dir.mkdir(parents=True, exist_ok=True)
    for doctype in dataset.doctypes():
        payload = {"doctype": doctype, _RECORDS_KEY: list(dataset.of(doctype))}
        (scope_dir / f"{doctype}.json").write_text(_dumps(payload), encoding="utf-8")
    meta = {"seed": dataset.seed, "as_of": dataset.as_of, "doctypes": list(dataset.doctypes())}
    (scope_dir / f"{_META_FILE}.json").write_text(_dumps(meta), encoding="utf-8")
    return scope_dir


def read(out: Path) -> Dataset:
    """从 `<out>/<scope>/` 读回数据集。`write` 的逆，用于跨进程/跨机器比对。"""
    scope_dir = out / SCOPE
    meta = json.loads((scope_dir / f"{_META_FILE}.json").read_text(encoding="utf-8"))
    records: dict[str, tuple[dict[str, Any], ...]] = {}
    for doctype in meta["doctypes"]:
        payload = json.loads((scope_dir / f"{doctype}.json").read_text(encoding="utf-8"))
        records[doctype] = tuple(payload[_RECORDS_KEY])
    return Dataset(seed=meta["seed"], as_of=meta["as_of"], records=records)


def to_snapshot(dataset: Dataset) -> Snapshot:
    """把数据集转成 `Snapshot`，好让 `agenerp.snapshot.diff` 来判「两次一不一样」。

    `SnapshotEntry.fieldname` 在这里装的是**单据号**——字段名对业务数据偏窄，
    但形状是通用的 (doctype, 身份, 属性)，为它另造一个快照契约不划算（§12.3）。
    """
    entries = [
        SnapshotEntry(
            doctype=doctype,
            fieldname=str(row[_IDENTITY_KEY]),
            attributes={key: value for key, value in row.items() if key != _IDENTITY_KEY},
        )
        for doctype in dataset.doctypes()
        for row in dataset.of(doctype)
    ]
    entries.sort(key=lambda entry: entry.key)
    return Snapshot(scope=SCOPE, entries=tuple(entries), source=f"seed:{dataset.seed}")
