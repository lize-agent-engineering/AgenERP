"""`docs/architecture/module-boundaries.md` §7.26 的 `ci-coverage` 登记表与三张真实判定面同构。

## 本条只验什么

**本条只验「存在性同构」，不验语义。**（措辞沿用先例 `tests/routing/test_routing_guard_registration.py`。）
它只回答「**哪个测试目录被谁复跑得到**」这一件事：`unit-and-contracts` 里跑不跑、
`lint` 的 ruff 扫不扫、`missions/p1-insight.json` 的 `commands.test` 里有没有。
**不管** live 面那三个 job（`gates-l2` / `gates-l2-live` / `gates-l2-seed`）在测什么、
**不管** `tools/gates/check_expected_red.py` 的判定域、**不管条数**、**不管断言质量** ——
「跑得到」不等于「测得住」。边界逐字写在 §7.26.1 里。
这一句是对 `docs/audits/2026-08-26-CP9-P1-retrospective.md:95`
（「核了门禁绿不绿，没核绿的门禁在测什么」）的直接对冲：
**本条自己就是一条判据，它有义务先说清楚自己名字之外的边界。**

## 为什么本条**不需要**先例那样的 `_REGISTERED_FILES` 纳管常量

先例踩过一个坑并逐字记着：`A == B` 而 `B` 由表自己导出 ⇒ 整表删空则 `A == B == ∅`，**判据静默绿**；
它靠一个写死的纳管常量 + 纳管边界断言堵住。**本条的 `B` 三路都不由表导出**——
目录集合来自**文件系统实扫**（`ls -d tests/*/`）、步骤来自 `.github/workflows/gates.yml` **实读**、
`commands.test` 来自 `missions/p1-insight.json` **实读**
⇒ `A == B == ∅` 那个陷阱在本条上**按构造不成立**，纳管常量省得掉。
**省掉一个先例有过的守卫，必须说明为什么省得掉，而不是默默不写。**
（存活守卫本身**没有**省：见断言 ⑤。）

## 七条断言，每条各对应一种漂移

- ① **目录集合三向同构**：表的目录列 == `ls -d tests/*/` 实扫 == `gates.yml` 第 ⑦ 步的 `COVERED`。
  `COVERED` 是这件事的**第二份机器可读副本**（在红线 2 内、loop 只读），一并咬住。
- ② **`unit-and-contracts` 步骤列双向**，两个方向分开写死：
  **②a（表 → CI）** 表说「第 N 步」的目录必须真有那一步且序号一致；表说「本 job 里不跑」的必须真的没有。
  **②b（CI → 表）** 该 job 里每一条**裸目录** `pytest tests/<dir>` 步骤都必须在表里有对应行且序号一致。
- ③ **`lint` 列双向**：只与 `lint` job 里那条 **`run:`** 行的 `ruff check` 参数对齐。
  ⚠️ **不许匹配 `name:` 行** —— 那一行逐字是 `ruff check（agenerp + tests/ 全部非门禁目录）`，
  首匹配解析器会从它里面读出 `tests/`。
- ④ **`commands.test` 列双向**：与 `commands.test` 里**全部** `tests/<dir>` 参数对齐。
  ⚠️ **不许只读第一个** —— `pytest tests/unit tests/context -q` 这种写法会让首 token 解析器漏掉后一个。
- ⑤ **存活守卫**：表的数据行非空，**且其余六条各自在「表为空」时立即短路返回**，
  使「整表删空」这一种变异**只红在本条上**。⚠️ 这与先例那条「一条测试内部的顺序」**形态不同**，
  不许写成「口径同先例」。
- ⑥ **第 6 列可判定的那一半**：日期逐字 `YYYY-MM-DD` 且能被 `date.fromisoformat` 解析、证据路径存在。
  ⚠️ **钉不住「日期是否新鲜」** —— 后者钉不住，本条也不声称钉住了（plan 的 `D3`）。
- ⑦ **步骤没被悄悄关掉**：第 2 列点名的每一步不得带 `if:` 或 `continue-on-error:`，
  `unit-and-contracts` job 本身也不得带 `if:`；表的第 3 列必须逐字反映实际。
  ⚠️ 只有前六条时，给第 ⑤ 步加 `if: false` 或 `continue-on-error: true`，本条**仍会 exit 0**，
  而表和 §7.7 仍宣称「CI 复跑得到」。两种写法在 `gates.yml` 里**都已实际存在**（`:211` · `:367-368`）。
  ⚠️ 本条**跳过**「表里点了名、但步骤表里根本查不到」的目录 —— 那种情形归 ②a 报。

## 残余风险，照实记（plan 的 `D2`）

本条落在 `tests/unit/`，而 `tests/unit` 是今天**唯一**同时进 `commands.test` 与 CI 的目录
⇒ **人正当地改了 CI 之后，本条会红在 `GATE_VERIFY` 上**。这是选它做落点的**已知代价**，不是遗漏。
缓解只有一条：**任何一条断言失败都逐字打印「表说什么 · 仓里实际是什么 · 该改哪个文件的哪一列」**。
**不接受「把本条挪出 `commands.test` 以免拖红」这种缓解** —— 那是用降低判别力换绿。

⚠️ 只读 `.github/workflows/**` 与 `missions/**`，一个字节都不写（红线 2 / Protected Areas）。
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
OWNER_DOC = _REPO_ROOT / "docs/architecture/module-boundaries.md"
WORKFLOW = _REPO_ROOT / ".github/workflows/gates.yml"
MISSION = _REPO_ROOT / "missions/p1-insight.json"

_MARKER = "ci-coverage"
_CODE = re.compile(r"`([^`]+)`")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 「裸目录」：`tests/<dir>` 后面紧跟空白或行尾。不认文件路径 ——
# 否则 `pytest tests/gates/test_zero_dep_boot.py` 会把 `gates` 算成一步。
_BARE_DIR = re.compile(r"\btests/([A-Za-z0-9_]+)(?=\s|$)")
_STEP_NO = re.compile(r"[①②③④⑤⑥⑦⑧⑨]")
_FIX_HINT = (
    f"该改的是 {OWNER_DOC.relative_to(_REPO_ROOT)} §7.26 的 "
    f"<!-- machine-read: {_MARKER} --> 那张表"
)


def _table_rows() -> list[list[str]]:
    """读 `<!-- machine-read: ci-coverage -->` 之后的第一张表，回**数据行**（跳表头与分隔行）。

    ⚠️ **刻意不写 `assert len(rows) >= 2`**（口径同先例）：留着它，「整表删空」会红在解析上，
    而那一格必须由断言 ⑤ 的存活守卫捕获 —— 一条变异被别的断言顺带打红，
    会让守卫看起来有效而其实从未被触发。
    """
    text = OWNER_DOC.read_text(encoding="utf-8")
    anchor = f"<!-- machine-read: {_MARKER} -->"
    assert anchor in text, f"owner doc 里找不到标记 {anchor} —— §7.26 的登记表被删了或改名了"
    rows: list[list[str]] = []
    started = False
    for line in text.split(anchor, 1)[1].splitlines():
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


def _cell_code(cell: str) -> str | None:
    m = _CODE.search(cell)
    return m.group(1) if m else None


def _declared() -> dict[str, list[str]]:
    """表的目录 → 该行六列（原样）。第 1 列必须是反引号包住的 `tests/<dir>`。"""
    out: dict[str, list[str]] = {}
    for row in _table_rows():
        assert len(row) == 6, f"`{_MARKER}` 表的行必须是六列，实读 {len(row)} 列：{row}"
        raw = _cell_code(row[0])
        assert raw and raw.startswith("tests/"), (
            f"第 1 列必须是反引号包住的 `tests/<目录>`，实读：{row[0]!r}\n{_FIX_HINT}"
        )
        name = raw[len("tests/") :]
        assert name not in out, f"`{_MARKER}` 表里 `tests/{name}` 出现了两行\n{_FIX_HINT}"
        out[name] = row
    return out


def _actual_dirs() -> set[str]:
    return {p.name for p in (_REPO_ROOT / "tests").iterdir() if p.is_dir()}


def _workflow_lines() -> list[str]:
    return WORKFLOW.read_text(encoding="utf-8").splitlines()


def _job_span(job: str) -> tuple[int, int]:
    """`jobs:` 下某个 job 的行区间（0-based，右开）。**这是「认出 job 边界」那条形状约束。**"""
    lines = _workflow_lines()
    head = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
    start = None
    for i, line in enumerate(lines):
        m = head.match(line)
        if not m:
            continue
        if m.group(1) == job:
            start = i
        elif start is not None:
            return start, i
    assert start is not None, f"{WORKFLOW.name} 里找不到 job `{job}:` —— 它被改名或删掉了"
    return start, len(lines)


def _job_has_if(job: str) -> str | None:
    """job 级 `if:`（`steps:` 之前、缩进 4 的那一层）。"""
    lines = _workflow_lines()
    start, end = _job_span(job)
    for line in lines[start:end]:
        if re.match(r"^    steps:\s*$", line):
            break
        if re.match(r"^    if:", line):
            return line.strip()
    return None


def _steps(job: str) -> list[dict[str, object]]:
    """把一个 job 的 `steps:` 切成块，每块回 `name` / `weakened` / `dirs`。

    ⚠️ **两条形状约束缺一不可**（它们在今天的基线上互为「另一条的替身」，
    活性各由一对变异证明：边界由 N7/N8，裸目录由 N10）：
    ① 只在本 job 的行区间里找（`_job_span`）；② 目录参数必须是**裸目录**（`_BARE_DIR`）。
    """
    lines = _workflow_lines()
    start, end = _job_span(job)
    blocks: list[list[str]] = []
    for line in lines[start:end]:
        if re.match(r"^      - ", line):
            blocks.append([line])
        elif blocks:
            blocks[-1].append(line)
    out: list[dict[str, object]] = []
    for block in blocks:
        body = "\n".join(block)
        name = ""
        m = re.search(r"^\s*-?\s*name:\s*(.+?)\s*$", body, re.MULTILINE)
        if m:
            name = m.group(1)
        weakened = [
            ln.strip()
            for ln in block
            if re.match(r"^\s*(if|continue-on-error):", ln)
        ]
        dirs: list[str] = []
        for ln in block:
            if "pytest" not in ln:
                continue
            dirs += _BARE_DIR.findall(ln)
        if dirs:
            out.append({"name": name, "weakened": weakened, "dirs": sorted(set(dirs))})
    return out


def _ci_steps_by_dir() -> dict[str, dict[str, object]]:
    """`unit-and-contracts` 里每个**裸目录** pytest 步骤：目录 → {序号, 名字, 削弱项}。"""
    out: dict[str, dict[str, object]] = {}
    for step in _steps("unit-and-contracts"):
        no = _STEP_NO.search(str(step["name"]))
        for d in step["dirs"]:  # type: ignore[union-attr]
            out[d] = {
                "no": no.group(0) if no else "",
                "name": step["name"],
                "weakened": step["weakened"],
            }
    return out


def _covered_literal() -> set[str]:
    """第 ⑦ 步的 `COVERED="…"` 字面值 —— 这件事的第二份机器可读副本。"""
    start, end = _job_span("unit-and-contracts")
    for line in _workflow_lines()[start:end]:
        m = re.search(r'COVERED="([^"]*)"', line)
        if m:
            return set(m.group(1).split())
    raise AssertionError(
        "`unit-and-contracts` 里找不到 `COVERED=\"…\"` —— 第 ⑦ 步（防漏接的元判据）被改掉或删掉了。\n"
        "它在红线 2 内，loop 只读；若确是人正当改的，改 §7.26 的表跟上，不是改本条。"
    )


def _ruff_dirs() -> set[str]:
    """`lint` job 里那条 **`run:`** 行的 ruff 参数。⚠️ 不许匹配 `name:` 行。"""
    start, end = _job_span("lint")
    for line in _workflow_lines()[start:end]:
        m = re.match(r"^\s*run:\s*(.*ruff check .*)$", line)
        if m:
            return set(_BARE_DIR.findall(m.group(1)))
    raise AssertionError(
        "`lint` job 里找不到 `run: … ruff check …` 那一行 —— 静态检查的判定面被改掉了。\n"
        "⚠️ 本条刻意不读 `name:` 行（它逐字是 `ruff check（agenerp + tests/ 全部非门禁目录）`）。"
    )


def _mission_test_dirs() -> set[str]:
    """`commands.test` 里**全部** `tests/<dir>` 参数（不是只读第一个）。"""
    command = json.loads(MISSION.read_text(encoding="utf-8"))["commands"]["test"]
    return set(_BARE_DIR.findall(command))


_NOT_RUN = "本 job 里不跑"
_IN, _NOT_IN, _NO_WEAKEN = "在", "不在", "否"


def _step_no(row: list[str]) -> str | None:
    """第 2 列：回步骤序号；`本 job 里不跑` 回 `None`。"""
    cell = row[1]
    if cell == _NOT_RUN:
        return None
    no = _cell_code(cell) or cell
    assert _STEP_NO.fullmatch(no), (
        f"第 2 列只能是 `①`–`⑨` 或逐字 `{_NOT_RUN}`，实读：{cell!r}\n{_FIX_HINT}"
    )
    return no


def _column(row: list[str], idx: int, label: str) -> bool:
    cell = row[idx]
    assert cell in (_IN, _NOT_IN), (
        f"第 {idx + 1} 列（{label}）只能逐字是 `{_IN}` 或 `{_NOT_IN}`，实读：{cell!r}\n{_FIX_HINT}"
    )
    return cell == _IN


def test_01_directory_sets_are_three_way_isomorphic() -> None:
    """① 表的目录列 == `ls -d tests/*/` 实扫 == `gates.yml` 第 ⑦ 步的 `COVERED`，三者两两相等。"""
    declared = _declared()
    if not declared:
        return  # 表为空归断言 ⑤ 报（见 test_05）
    table, actual, covered = set(declared), _actual_dirs(), _covered_literal()
    assert table == actual, (
        "§7.26 的登记表与 `tests/` 下真实的目录集合对不上了。\n"
        f"表里有、仓里没有：{sorted(table - actual)}\n"
        f"仓里有、表里没有：{sorted(actual - table)}\n"
        f"{_FIX_HINT} —— 每个 `tests/` 下的目录各占一行（纳管口径是**目录**，不是文件）。"
    )
    assert table == covered, (
        "§7.26 的登记表与 `gates.yml` 第 ⑦ 步的 `COVERED` 字面值对不上了"
        "（同一事实的第二份机器可读副本）。\n"
        f"表里有、`COVERED` 里没有：{sorted(table - covered)}\n"
        f"`COVERED` 里有、表里没有：{sorted(covered - table)}\n"
        f"`COVERED` 在 .github/workflows/gates.yml 的 `unit-and-contracts` 里，**红线 2，loop 只读**；\n"
        f"能改的只有一边：{_FIX_HINT} 的第 1 列。"
    )


def test_02a_every_declared_step_exists_in_ci() -> None:
    """②a 表 → CI：表说「第 N 步」的必须真有那一步且序号一致；说「本 job 里不跑」的必须真的没有。"""
    declared = _declared()
    if not declared:
        return
    ci = _ci_steps_by_dir()
    for name, row in sorted(declared.items()):
        want = _step_no(row)
        got = ci.get(name)
        if want is None:
            assert got is None, (
                f"`tests/{name}`：表说「{_NOT_RUN}」，而 `unit-and-contracts` 里**确实有**一步跑它 ——\n"
                f"  仓里实际：{got['name']!r}\n"  # type: ignore[index]
                f"{_FIX_HINT} 的第 2 列（改成那一步的序号）。"
            )
            continue
        assert got is not None, (
            f"`tests/{name}`：表说它在 `unit-and-contracts` 的第 {want} 步，"
            f"而该 job 里**没有任何一条**裸目录 `pytest tests/{name}` 步骤。\n"
            f"  仓里实际跑到的目录：{sorted(ci)}\n"
            f"{_FIX_HINT} 的第 2 列（改成 `{_NOT_RUN}`），"
            f"或确认 .github/workflows/gates.yml 是不是被人正当改过（那属红线 2，只能改表跟上）。"
        )
        assert got["no"] == want, (
            f"`tests/{name}`：表说第 {want} 步，仓里实际是 {got['no'] or '（无序号）'} 步"
            f"（步骤名逐字 {got['name']!r}）。\n{_FIX_HINT} 的第 2 列。"
        )


def test_02b_every_ci_step_has_a_table_row() -> None:
    """②b CI → 表：`unit-and-contracts` 里每条裸目录 pytest 步骤都必须在表里有行且序号一致。"""
    declared = _declared()
    if not declared:
        return
    for name, step in sorted(_ci_steps_by_dir().items()):
        row = declared.get(name)
        assert row is not None, (
            f"`unit-and-contracts` 里有一步跑 `tests/{name}`（步骤名逐字 {step['name']!r}），"
            f"而 §7.26 的表里**没有它的行**。\n"
            f"{_FIX_HINT} —— 加一行，第 2 列填 {step['no'] or '该步序号'}。"
        )
        want = _step_no(row)
        assert want == step["no"], (
            f"`tests/{name}`：仓里实际是第 {step['no'] or '（无序号）'} 步"
            f"（步骤名逐字 {step['name']!r}），表说 {want or _NOT_RUN}。\n{_FIX_HINT} 的第 2 列。"
        )


def test_03_lint_column_matches_the_ruff_run_line() -> None:
    """③ 第 4 列双向：只与 `lint` job 里那条 **`run:`** 行的 ruff 参数对齐。"""
    declared = _declared()
    if not declared:
        return
    table = {n for n, row in declared.items() if _column(row, 3, "lint（ruff）作用域")}
    real = _ruff_dirs()
    assert table == real, (
        "§7.26 第 4 列（`lint`（ruff）作用域）与 `lint` job 那条 `run:` 行对不上了。\n"
        f"表说在、ruff 参数里没有：{sorted(table - real)}\n"
        f"ruff 参数里有、表说不在：{sorted(real - table)}\n"
        f"仓里实际的 ruff 参数（`tests/` 部分）：{sorted(real)}\n"
        f"{_FIX_HINT} 的第 4 列 —— .github/workflows/gates.yml 属红线 2，loop 只读。"
    )


def test_04_commands_test_column_matches_the_mission() -> None:
    """④ 第 5 列双向：与 `commands.test` 里**全部** `tests/<dir>` 参数对齐（不是只读第一个）。"""
    declared = _declared()
    if not declared:
        return
    table = {n for n, row in declared.items() if _column(row, 4, "commands.test")}
    real = _mission_test_dirs()
    assert table == real, (
        "§7.26 第 5 列（`missions/p1-insight.json` 的 `commands.test`）与该文件对不上了。\n"
        f"表说在、`commands.test` 里没有：{sorted(table - real)}\n"
        f"`commands.test` 里有、表说不在：{sorted(real - table)}\n"
        f"仓里实际的 `commands.test` 目录参数：{sorted(real)}\n"
        f"{_FIX_HINT} 的第 5 列 —— `missions/**` 在 "
        "`docs/context/ai-autonomy-policy.md` 的 Protected Areas 里标 `blocked`，loop 只读。"
    )


def test_05_table_is_not_empty() -> None:
    """⑤ 存活守卫：整表删空必须**只红在本条上**。

    其余六条各自对空表短路返回 —— 一条变异被别的断言顺带打红，
    会让守卫看起来有效而其实从未被触发。
    """
    assert _declared(), (
        f"§7.26 的 `{_MARKER}` 表为空 —— 判据静默失效。\n"
        "这条断言存在的唯一理由：没有它，把表删空会让其余六条各自无事可做而全部转绿，"
        "而「登记表被清空」正是本条要防的形态之一。\n"
        f"表的位置：{OWNER_DOC.relative_to(_REPO_ROOT)} §7.26 的 <!-- machine-read: {_MARKER} -->"
    )


def test_06_every_row_points_at_evidence_that_exists() -> None:
    """⑥ 第 6 列可判定的那一半：日期逐字 `YYYY-MM-DD` 且可解析、证据路径存在。

    ⚠️ 钉的是「日期可解析 + 路径存在」，**不是「日期是否新鲜」** —— 后者钉不住，本条不声称钉住了。
    """
    declared = _declared()
    if not declared:
        return
    for name, row in sorted(declared.items()):
        cell = row[5]
        parts = [p.strip() for p in cell.split("·")]
        assert len(parts) == 2, (
            f"`tests/{name}`：第 6 列必须是「日期 · 证据路径」两段，实读：{cell!r}\n{_FIX_HINT}"
        )
        stamp, rel = parts[0].strip("` "), parts[1].strip("` ")
        assert _ISO_DATE.match(stamp), (
            f"`tests/{name}`：第 6 列的日期必须逐字是 YYYY-MM-DD，实读：{stamp!r}\n{_FIX_HINT}"
        )
        date.fromisoformat(stamp)
        assert (_REPO_ROOT / rel).exists(), (
            f"`tests/{name}`：第 6 列指向的证据路径不存在：{rel}\n"
            "一条指向虚空的证据路径，比没有证据路径更糟 —— 它是一次可信度背书。\n"
            f"{_FIX_HINT} 的第 6 列。"
        )


def test_07_named_steps_are_not_silently_disabled() -> None:
    """⑦ 第 2 列点名的每一步不得带 `if:` / `continue-on-error:`，job 本身也不得带 `if:`。

    ⚠️ 本条**跳过**「表里点了名、但步骤表里查不到」的目录 —— 那种情形归 ②a 报，
    不跳则同一条变异会被两条断言重复打红。
    """
    declared = _declared()
    if not declared:
        return
    job_if = _job_has_if("unit-and-contracts")
    assert job_if is None, (
        "`unit-and-contracts` job 本身带上了条件 —— 整个 job 可以被静默跳过，"
        "而 §7.26 的表仍宣称这些目录「CI 复跑得到」。\n"
        f"  仓里实际：{job_if!r}\n"
        "这属红线 2（loop 只读）；若确是人正当改的，§7.26 的表必须跟上说实话。"
    )
    ci = _ci_steps_by_dir()
    for name, row in sorted(declared.items()):
        if _step_no(row) is None:
            continue
        step = ci.get(name)
        if step is None:
            continue  # 归 ②a 报
        weakened = step["weakened"]
        assert not weakened, (
            f"`tests/{name}`：第 {step['no']} 步被条件或软失败削弱了 ——「跑了」不等于「拦得住」。\n"
            f"  仓里实际：{weakened}（步骤名逐字 {step['name']!r}）\n"
            f"  表的第 3 列说：{row[2]!r}\n"
            f"{_FIX_HINT} 的第 3 列 —— 若确是人正当改的，第 3 列必须逐字写出那个条件。"
        )
        assert row[2] == _NO_WEAKEN, (
            f"`tests/{name}`：表的第 3 列写着 {row[2]!r}，而第 {step['no']} 步"
            f"实际**没有**任何 `if:` / `continue-on-error:`。\n{_FIX_HINT} 的第 3 列（应为 `{_NO_WEAKEN}`）。"
        )
