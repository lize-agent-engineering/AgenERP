"""`docs/architecture/model-management.md` §12.5 的 `routing-guards` 登记表与仓里真实判据同构。

## 本条只验什么

**本条只验「存在性同构」，不验语义。**
「那条判据到底盖住什么形态」由 `docs/evidence/p1-routing-guard-registration/`
的**变异实测**负责，不由这里负责，也不由表里第 3/4 列那两句散文自证。
这一句是对 `docs/audits/2026-08-26-CP9-P1-retrospective.md` §1.2
（「核了门禁绿不绿，没核绿的门禁在测什么」）的直接对冲：
**本条自己就是一条判据，它有义务先说清楚自己名字之外的边界。**

## 为什么需要它

F8 这条链子上，处置 2026-08-25 就由人 `d18c05c` 做完了，
而 §12.5 的登记文字直到 2026-08-26 还逐字写着「今天没有任何判据拦得住这条路」——
**一句没人知道它有多老的覆盖断言，挂了一年半个月没人发现。**
本条把那张登记表钉在仓里真实存在的判据上：**下一次「判据变了而文档没跟上」当场红。**

## 五条断言，缺一条就有一种漂移能悄悄溜过去

- ① **纳管文件集合写死在 `_REGISTERED_FILES`**，不由表自己导出。
- ② **双向同构**：`A`（表里的 `(文件, 函数名)`）`== B`（`_REGISTERED_FILES` 内全部顶层 `def test_*`）。
- ③ **存活守卫**：`A` 非空。少了它，把表清空会让 `A == B == ∅` 成立而本条**静默绿** ——
  那正是本条要防的第四种形态（判据自身无存活守卫）在本条自己身上的重演。
- ④ **纳管边界**：表里出现未纳管的文件即红。③ 与 ④ 互相咬住 ⇒ `_REGISTERED_FILES` 无法被悄悄放松成空集。
- ⑤ **第 5 列可判定的那一半**：证据路径必须真的存在，日期必须逐字是 `YYYY-MM-DD` 且能被
  `datetime.date.fromisoformat` 解析。⚠️ **钉的是「路径存在 + 日期可解析」，不是「日期是否新鲜」**
  —— 后者钉不住，本条也不声称钉住了。

## 纳管口径与它的代价

口径是**文件级**：一个文件进 `_REGISTERED_FILES`，它里面的**每一个顶层 `def test_*` 都必须各占表里一行**。
代价照实记：它只能纳管「整份都是接缝判据」的文件。把一份十几条的普通测试文件纳进来，
这张表会退化成全量测试清单，而第 3/4 列就没法逐行写实了。
⇒ **本期只纳管一个文件。要纳管第二个，必须先回去重开 plan
`docs/plans/p1-insight/2026-08-26-2101-1-routing-guard-registration-drift.md` Phase 2 里的那条 `Decision`。**
改这行常量就必须重开那条裁定 —— 这是把一条散文裁定变成机器约束的唯一办法。

⚠️ 只读 `tests/gates/**`，一个字节都不写（红线 1）。
"""

from __future__ import annotations

import ast
import re
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
OWNER_DOC = _REPO_ROOT / "docs/architecture/model-management.md"

# 纳管的判据文件集合。改这里 = 重开上面那条 `Decision`。
_REGISTERED_FILES = frozenset({"tests/gates/test_agent_seam_stays_swappable.py"})

_CODE = re.compile(r"`([^`]+)`")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _table_after(marker: str) -> list[list[str]]:
    """读 `<!-- machine-read: <marker> -->` 之后的第一张表，回**数据行**（跳表头与分隔行）。

    口径同 `tests/routing/test_capabilities.py` 的同名函数，**只有一处刻意的差别**：
    那边有一句 `assert len(rows) >= 2`，这边没有。
    留着它，「整表删空」会红在**解析失败**上，而本条要求那一格由 ③ 的存活守卫捕获 ——
    一条变异被别的断言顺带打红，会让守卫看起来有效而其实从未被触发。
    """
    text = OWNER_DOC.read_text(encoding="utf-8")
    anchor = f"<!-- machine-read: {marker} -->"
    assert anchor in text, f"owner doc 里找不到标记 {anchor}"
    lines = text.split(anchor, 1)[1].splitlines()
    rows: list[list[str]] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if started:
                break
            continue
        started = True
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return rows[1:]


def _registered_rows() -> list[list[str]]:
    return _table_after("routing-guards")


def _declared_pairs() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in _registered_rows():
        assert len(row) == 5, f"`routing-guards` 表的行必须是五列，实读 {len(row)} 列：{row}"
        path = _CODE.search(row[0])
        func = _CODE.search(row[1])
        assert path and func, f"第 1/2 列必须各有一个反引号包住的值：{row}"
        pairs.add((path.group(1), func.group(1)))
    return pairs


def _toplevel_tests(rel: str) -> set[tuple[str, str]]:
    path = _REPO_ROOT / rel
    assert path.is_file(), f"`_REGISTERED_FILES` 里的 {rel} 不存在 —— 纳管的判据文件被删了或改名了"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        (rel, node.name)
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test")
    }


def test_registration_table_is_isomorphic_to_the_real_guards() -> None:
    """① 纳管集合写死 · ② 双向同构 · ③ 存活守卫 · ④ 纳管边界。"""
    declared = _declared_pairs()

    # ③ 存活守卫：先于 `A == B`，否则清空表会让两边同为空集而静默绿。
    assert declared, (
        "`routing-guards` 表为空 —— 判据静默失效。\n"
        "这条断言存在的唯一理由：没有它，把表删空会让 A == B == ∅ 成立而本条转绿，"
        "而那正是本条登记的第四种不覆盖形态（判据自身无存活守卫）。\n"
        f"表的位置：{OWNER_DOC.relative_to(_REPO_ROOT)} §12.5 的 <!-- machine-read: routing-guards -->"
    )

    # ④ 纳管边界：表里不许出现未纳管的文件。
    declared_files = {f for f, _ in declared}
    assert declared_files <= set(_REGISTERED_FILES), (
        f"`routing-guards` 表里出现了未纳管的判据文件：{sorted(declared_files - set(_REGISTERED_FILES))}\n"
        "要纳管新文件，先改本模块的 `_REGISTERED_FILES`，"
        "而改它就必须回去重开 plan 2026-08-26-2101-1 Phase 2 的那条 `Decision`（文件级口径的代价写在那里）。"
    )

    # ② 双向同构。
    real = set().union(*(_toplevel_tests(rel) for rel in sorted(_REGISTERED_FILES)))
    assert declared == real, (
        "`routing-guards` 表与仓里真实的判据对不上了。\n"
        f"表里有、仓里没有：{sorted(declared - real)}\n"
        f"仓里有、表里没有：{sorted(real - declared)}\n"
        "纳管口径是**文件级**：一个文件进表，它里面每一个顶层 `def test_*` 都要各占一行。"
    )


def test_every_row_points_at_evidence_that_exists() -> None:
    """⑤ 第 5 列可判定的那一半：证据路径存在 + 日期逐字 `YYYY-MM-DD` 且可解析。

    ⚠️ 钉的是「路径存在 + 日期可解析」，**不是「日期是否新鲜」** —— 后者钉不住，本条不声称钉住了。
    它要挡的失败形态是「今天写下、将来目录被删或改名而本条全绿」那种指向虚空的可信度背书 ——
    与本节要修的那条漂移同形。
    """
    rows = _registered_rows()
    assert rows, "`routing-guards` 表为空 —— 判据静默失效（同 ③）"
    for row in rows:
        cell = row[4]
        parts = [p.strip() for p in cell.split("·")]
        assert len(parts) == 2, f"第 5 列必须是「日期 · 证据路径」两段，实读：{cell}"
        stamp = parts[0].strip("` ")
        rel = parts[1].strip("` ")
        assert _ISO_DATE.match(stamp), f"第 5 列的日期必须逐字是 YYYY-MM-DD，实读：{stamp!r}"
        date.fromisoformat(stamp)
        assert (_REPO_ROOT / rel).exists(), (
            f"第 5 列指向的证据路径不存在：{rel}\n"
            "一条指向虚空的证据路径，比没有证据路径更糟 —— 它是一次可信度背书。"
        )
