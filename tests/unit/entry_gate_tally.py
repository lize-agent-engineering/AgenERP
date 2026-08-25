"""P1.0 逐格计数的**单一真相源**：四个口径各自从自己的源机械派生，本模块一个数都不手抄。

## 为什么它在 `tests/unit/` 而不在 `agenerp/`（plan `2026-08-25-0850-1` D1）

- 这是**一次历史实验的记账**，不是产品行为。放进产品包会让「本仓实测过的数字」
  变成运行时可 import 的东西，与 §12.5「配置种子不是厂商绑定」的分层相冲。
- 备选「落 `tools/experiments/p1_entry_gate/`」也被否决：实验设施已冻结，
  且 `tools/**` 不在 `commands.test` 与 CI 的 pytest 作用域里 —— 判据会复跑不到。
- 代价照实记：`tests/unit/` 里一个非 `test_` 前缀的模块**不会被 pytest 自动收集**，
  只有被 `test_entry_gate_tally.py` import 才跑得到。

## 四个口径，四个源，**本模块不裁定哪个为准**

| 列 | 源 | 本模块怎么取 |
|---|---|---|
| 甲 | `docs/evidence/p1-entry-gate/verdicts.md` | 逐条打勾行的「结论」列 + 揭配置表的 run 分组，**数出来**，不读该表自报的正确率 |
| 乙 | `docs/masterplan/STATE.md` `2026-08-24T07:31Z` 行的表 | 解析该行之后第一张 md 表 |
| 丙 | `docs/masterplan/STATE.md` `2026-08-24T09:01Z` 行的表 | 解析该行之后第一张 md 表的 `正确值` 列 |
| 丁 | `tests/fixtures/p1_entry_gate_labels.jsonl` | 按 `(model, gate)` 分组数 `label == "correct"` |

⚠️ **`STATE.md` 与 `verdicts.md` 都是只读**（红线 5 / plan Non-Goal 4-5）：本模块只 `read_text()`。
⚠️ **标注集一个字节不改**（plan Non-Goal 1）：只 `read` 与 `count`，不回写判定结果。
"""

from __future__ import annotations

import json
import pathlib
import re
from collections import Counter

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

LABELS = REPO_ROOT / "tests/fixtures/p1_entry_gate_labels.jsonl"
STATE = REPO_ROOT / "docs/masterplan/STATE.md"
VERDICTS = REPO_ROOT / "docs/evidence/p1-entry-gate/verdicts.md"
MODEL_MANAGEMENT = REPO_ROOT / "docs/architecture/model-management.md"

# run_id 前缀 → 轨迹目录。第一轮 `run-NN`、第二轮 `r2-NN`，两轮各一个目录。
TRACE_DIRS = {
    "run-": REPO_ROOT / "docs/evidence/p1-entry-gate",
    "r2-": REPO_ROOT / "docs/evidence/p1-entry-gate-round2",
}

# 第一轮的四格，**顺序即四列表的行序**（甲乙丙丁四列共用它）。
FIRST_ROUND_CELLS = (
    ("qwen-plus", "off"),
    ("qwen-plus", "on"),
    ("qwen3.6-plus", "off"),
    ("qwen3.6-plus", "on"),
)

# 单一真相源区域的一对起止标记（plan §6.1 第 3 条谓词的区域面）。
REGION_OPEN = "<!-- machine-read: p1-0-cell-tally -->"
REGION_CLOSE = "<!-- /machine-read: p1-0-cell-tally -->"


class Cell(tuple):
    """一格计数 `(命中, 总数)`，`str()` 出来就是 `2/3` 这个写法。"""

    __slots__ = ()

    def __new__(cls, hits: int, total: int) -> Cell:
        return super().__new__(cls, (hits, total))

    @property
    def hits(self) -> int:
        return self[0]

    @property
    def total(self) -> int:
        return self[1]

    def __str__(self) -> str:
        return f"{self[0]}/{self[1]}"


def _parse_cell(text: str) -> Cell:
    """把 `**0 / 3**` 这类写法解析成 `Cell(0, 3)`。分母**从文本里读**，不写死。"""
    match = re.search(r"(\d+)\s*/\s*(\d+)", text)
    assert match, f"解析不出计数：{text!r}"
    return Cell(int(match.group(1)), int(match.group(2)))


def _md_table_after(text: str, anchor: str) -> list[list[str]]:
    """取 `anchor` 之后的第一张 markdown 表，回**数据行**（跳表头与分隔行）。

    与 `tests/routing/test_capabilities.py::_table_after` 同形，但这里的表**缩进两格**
    （`STATE.md` §2 的表在 bullet 之下），因此先 `strip()` 再判 `|` 开头。
    """
    assert anchor in text, f"找不到锚点：{anchor!r}"
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
    assert len(rows) >= 2, f"锚点 {anchor!r} 之后没有找到成形的表"
    return rows[1:]


def _bare(text: str) -> str:
    """剥掉 markdown 的强调与反引号，回裸文本。"""
    return text.replace("**", "").replace("`", "").strip()


# --------------------------------------------------------------------------- 丁：标注集派生


def load_labels() -> list[dict]:
    """读那 24 行人工标注。**只读**，本模块不写它一个字节。"""
    with LABELS.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def derive_from_labels(rows: list[dict] | None = None) -> dict[tuple[str, str], Cell]:
    """丁列：按 `(model, gate)` 分组数 `label == "correct"`。

    **分母由分组实际行数得出**，不写死 `3` —— 标注集少一行就该在分母上看得见。
    """
    rows = load_labels() if rows is None else rows
    hits: Counter[tuple[str, str]] = Counter()
    totals: Counter[tuple[str, str]] = Counter()
    for row in rows:
        key = (row["model"], row["gate"])
        totals[key] += 1
        if row["label"] == "correct":
            hits[key] += 1
    return {key: Cell(hits[key], totals[key]) for key in sorted(totals)}


def trace_path(run_id: str) -> pathlib.Path:
    """`run_id` → 轨迹文件路径。前缀认不出就当场失败，不静默回一个不存在的路径。"""
    for prefix, directory in TRACE_DIRS.items():
        if run_id.startswith(prefix):
            return directory / f"{run_id}.json"
    raise AssertionError(f"认不出 run_id 的轮次前缀：{run_id!r}")


def load_trace(run_id: str) -> dict:
    return json.loads(trace_path(run_id).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- 乙 / 丙：STATE.md

STATE_ANCHOR_B = "- 2026-08-24T07:31Z ·"
STATE_ANCHOR_C = "- 2026-08-24T09:01Z ·"


def parse_state_first_review() -> dict[tuple[str, str], Cell]:
    """乙列：`STATE.md` `2026-08-24T07:31Z` 行之后那张表的「正确」列。"""
    rows = _md_table_after(STATE.read_text(encoding="utf-8"), STATE_ANCHOR_B)
    parsed = {(_bare(r[0]), _bare(r[1])): _parse_cell(r[2]) for r in rows}
    assert tuple(parsed) == FIRST_ROUND_CELLS, f"乙列的格位与四格表不符：{tuple(parsed)}"
    return parsed


def parse_state_correction() -> tuple[dict[tuple[str, str], Cell], Cell]:
    """丙列：`2026-08-24T09:01Z` 更正表的 `正确值` 列（末列），外带它自己写的合计。

    该表最后一行是 `| 合计 | | **2/12** | **5/12** |`，格位列不是模型名 —— 单独取出来回。
    """
    rows = _md_table_after(STATE.read_text(encoding="utf-8"), STATE_ANCHOR_C)
    parsed: dict[tuple[str, str], Cell] = {}
    total: Cell | None = None
    for row in rows:
        if _bare(row[0]) == "合计":
            total = _parse_cell(row[3])
            continue
        parsed[(_bare(row[0]), _bare(row[1]))] = _parse_cell(row[3])
    assert tuple(parsed) == FIRST_ROUND_CELLS, f"丙列的格位与四格表不符：{tuple(parsed)}"
    assert total is not None, "丙列的表里找不到「合计」行"
    return parsed, total


# --------------------------------------------------------------------------- 甲：verdicts.md

_VERDICT_ANCHOR_ROWS = "## 逐条打勾（14 次运行，其中 2 次无效）"
_VERDICT_ANCHOR_CELLS = "## 揭配置（打勾之后才对应）"


def parse_verdicts_per_run() -> dict[str, str]:
    """逐条打勾行：`run_id` → 结论（`正确` / `不完全` / `错误` / `无效`）。"""
    rows = _md_table_after(VERDICTS.read_text(encoding="utf-8"), _VERDICT_ANCHOR_ROWS)
    return {_bare(row[0]): _bare(row[4]) for row in rows}


def parse_verdicts_cells() -> dict[tuple[str, str], tuple[tuple[str, ...], Cell]]:
    """揭配置表：格位 → (该格的 run 列表, 该表自报的正确率)。

    格位从 `` `qwen-plus` `` 这个反引号里取模型名、从 `**off**` / `**on**` 取门禁 ——
    **不按行序猜**，行序换了照样对。
    """
    rows = _md_table_after(VERDICTS.read_text(encoding="utf-8"), _VERDICT_ANCHOR_CELLS)
    parsed: dict[tuple[str, str], tuple[tuple[str, ...], Cell]] = {}
    for row in rows:
        model = re.search(r"`([^`]+)`", row[0])
        gate = re.search(r"门禁 \*\*(on|off)\*\*", row[0])
        assert model and gate, f"揭配置表的格位解析不出来：{row[0]!r}"
        runs = tuple(part.strip() for part in _bare(row[1]).split("/"))
        parsed[(model.group(1), gate.group(1))] = (runs, _parse_cell(row[3]))
    assert tuple(parsed) == FIRST_ROUND_CELLS, f"甲列的格位与四格表不符：{tuple(parsed)}"
    return parsed


def derive_from_verdicts() -> dict[tuple[str, str], Cell]:
    """甲列：**数**逐条打勾行里判 `正确` 的条数，不读揭配置表自报的正确率。

    自报的那一列另由 `test_entry_gate_tally.py` 拿来交叉核对 —— 两处一致才算解析对了。
    """
    per_run = parse_verdicts_per_run()
    cells = parse_verdicts_cells()
    derived: dict[tuple[str, str], Cell] = {}
    for key, (runs, _) in cells.items():
        verdicts = [per_run[run] for run in runs]
        derived[key] = Cell(sum(1 for v in verdicts if v == "正确"), len(verdicts))
    return derived


# --------------------------------------------------------------------------- 守卫（plan §6.1）

# 数字面：§1.6 两条 grep 的并集，**逐字**。
GUARD_NUMBER = re.compile(r"[0-3]/3|[0-9]+/(?:6|12)")

# 语境面：本行或其**前 4 行**内出现的标识之一。窗口大小的标定见 plan §6.1.1
# （本行 0/4 · 整段 2/1 · 前 2 行 0/1 · **前 4 行 0/0**；前 5/6/8 同样 0/0 ⇒ 取下端）。
GUARD_MARKERS = (
    "P1.0",
    "入口关口",
    "两跳题",
    "门禁",
    "qwen-plus",
    "qwen3.6-plus",
    "qwen3.7-plus",
    "qwen3.8-max",
)
GUARD_WINDOW = 4

# 守卫的扫描面：本 plan 有权改的两个目录。`docs/masterplan/**`（红线 5）·
# `docs/audits/**` · `docs/evidence/**` · `docs/backlog/**` · `docs/plans/**`
# **刻意在作用域外，是定界不是漏扫**（plan §1.6 末条 / Non-Goals）。
GUARD_SCOPE = ("agenerp", "docs/architecture")

# plan §1.6 写死的**无关面**：守卫必须对这 6 行保持沉默，一行不多一行不少。
UNRELATED_LINES = (
    ("agenerp/oob.py", "2026-08-22 冷起实测 3/3、CI runner 2/2"),
    ("docs/architecture/module-boundaries.md", "83/61 → 34/12"),
    ("docs/architecture/module-boundaries.md", "P1.6 的 `0/3/4/5` 四种可区分退出码"),
    ("docs/architecture/module-boundaries.md", "第 2/3 条仍完全有效"),
    ("docs/architecture/module-boundaries.md", "(a) 2/3 留出（否决，如上）"),
    ("docs/architecture/module-boundaries.md", "6 条 × 3 次，**6/6 一致**"),
)


def scan_files() -> list[pathlib.Path]:
    """守卫扫的全部文件：`agenerp/**/*.py` + `docs/architecture/**/*.md`。"""
    found: list[pathlib.Path] = []
    for root in GUARD_SCOPE:
        base = REPO_ROOT / root
        pattern = "*.py" if root == "agenerp" else "*.md"
        found.extend(
            path
            for path in sorted(base.rglob(pattern))
            if "__pycache__" not in path.parts
        )
    assert found, "守卫的扫描面是空的 —— 目录名写错了"
    return found


def _region_mask(lines: list[str]) -> list[bool]:
    """逐行标记「是否落在单一真相源区域内」。起止标记本身算区域内。"""
    inside = False
    mask: list[bool] = []
    for line in lines:
        if REGION_OPEN in line:
            inside = True
        mask.append(inside)
        if REGION_CLOSE in line:
            inside = False
    return mask


def scan_handwritten_tallies(
    *,
    require_context: bool = True,
    honour_region: bool = True,
) -> list[tuple[str, int, str]]:
    """守卫本体：回全部命中 `(仓内相对路径, 行号, 原文)`。

    三条谓词的合取（plan §6.1）：**数字面 ∧ 语境面 ∧ 区域面**。
    两个旋钮只为**阳性对照**而存在 —— 关掉语境面与区域面就是「宽网」，
    判据⑦ 用它证明那 6 行无关面**真的会被误报**，从而证明收窄不是空转。
    """
    hits: list[tuple[str, int, str]] = []
    for path in scan_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in scan_text(
            lines, require_context=require_context, honour_region=honour_region
        ):
            hits.append((str(path.relative_to(REPO_ROOT)), number, line))
    return hits


def scan_text(
    lines: list[str],
    *,
    require_context: bool = True,
    honour_region: bool = True,
) -> list[tuple[int, str]]:
    """三条谓词施加在**一段文本**上，回 `(行号, 原文)`。

    与文件系统解耦，因此变异（M7 / M7b）可以在**合成文本**上施加并复跑，
    不必真去改一份 owner doc 再改回来。
    """
    mask = _region_mask(lines) if honour_region else [False] * len(lines)
    found: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if not GUARD_NUMBER.search(line):
            continue
        if honour_region and mask[index]:
            continue
        if require_context:
            window = lines[max(0, index - GUARD_WINDOW) : index + 1]
            if not any(m in w for w in window for m in GUARD_MARKERS):
                continue
        found.append((index + 1, line))
    return found


# --------------------------------------------------------------------------- 判据⑨：区域内

# ⑨a 的四条逐字锚点。**Phase 2 逐字保留了这四行，连换行位置都没动** ——
# 取数跨度是「锚点所在的那一整行」，重新折行会把元组劈开、当场打红（plan Phase 2 写死）。
REGION_ANCHORS = (
    "门禁把 0/3 提到 1/3",
    "加门禁反而 1/3 → 0/3",
    "「0/3 vs 1/3」不得当作量化结论",
    "该文件记弱模型门禁 on 为 2/3、强模型两格均为 3/3",
)


def region_lines() -> list[str]:
    """§12.3 单一真相源区域**内**的全部行（不含那对起止标记本身）。"""
    text = MODEL_MANAGEMENT.read_text(encoding="utf-8")
    assert REGION_OPEN in text, f"owner doc 里找不到 {REGION_OPEN}"
    assert REGION_CLOSE in text, f"owner doc 里找不到 {REGION_CLOSE}"
    return text.split(REGION_OPEN, 1)[1].split(REGION_CLOSE, 1)[0].splitlines()


def region_prose_lines_with_numbers() -> list[str]:
    """区域内**含数字的散文行**：不以 `|` 开头（即不属于任何 md 表格）且命中数字面。

    表格行由 判据④⑤⑥ 按列钉住，**刻意排除在本计数之外，是分工不是漏掉**。
    """
    return [
        line
        for line in region_lines()
        if not line.strip().startswith("|") and GUARD_NUMBER.search(line)
    ]


def anchored_line(anchor: str) -> str:
    """按逐字锚点子串在区域内定位到**唯一一行**。锚点缺失即失败（⑨a 的锚点缺失即红）。"""
    found = [line for line in region_lines() if anchor in line]
    assert len(found) == 1, f"锚点 {anchor!r} 在区域内命中 {len(found)} 行，期望恰好 1 行"
    return found[0]


def numbers_in(line: str) -> tuple[str, ...]:
    """按出现顺序取出一行里全部匹配**守卫数字面**的数（⑨a 的取数口径）。"""
    return tuple(match.group(0) for match in GUARD_NUMBER.finditer(line))


# ⑨b 的取数口径**刻意比守卫的数字面宽**：任何 `n/m` 形状都算一处「数字出现」。
# ⚠️ **这一条是被 M9b 逼出来的，照实记**：第一版 ⑨b 复用了 `GUARD_NUMBER`，
# 而 M9b 的注入文本 `4/9` **不匹配那个面**（它只认 `[0-3]/3` 与 `x/6` `x/12`），
# 于是 M9b 当场跑绿 —— **兜底那半在区域里根本没在兜**。守卫的数字面是给「找手抄」用的，
# ⑨b 要的是「区域里有没有冒出一个谁都没声明过的数」，两者本来就不该是同一个面。
REGION_FRACTION = re.compile(r"\d+/\d+")


def fractions_in(line: str) -> tuple[str, ...]:
    """按出现顺序取出一行里全部 `n/m` 形状的数（⑨b 的取数口径）。"""
    return tuple(match.group(0) for match in REGION_FRACTION.finditer(line))


# --------------------------------------------------------------------------- §12.3 四列并置表

_TOTAL_ROW_LABEL = "第一轮合计"


def _doc_table_rows() -> list[list[str]]:
    """区域内那张四列并置表的**全部行**（含表头，跳分隔行）。"""
    rows: list[list[str]] = []
    started = False
    for line in region_lines():
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
    assert len(rows) >= 2, "区域内找不到成形的四列并置表"
    return rows


def doc_table_header() -> list[str]:
    return _doc_table_rows()[0]


def _column_names() -> list[str]:
    """表头形如 `甲 · 循环自判`，列名取 `·` 之前那一段。"""
    return [cell.split("·")[0].strip() for cell in doc_table_header()[1:]]


def parse_doc_columns() -> dict[str, dict[tuple[str, str], Cell]]:
    """§12.3 四列并置表 → `{列名: {格位: Cell}}`。合计行不进这里。"""
    names = _column_names()
    parsed: dict[str, dict[tuple[str, str], Cell]] = {name: {} for name in names}
    for row in _doc_table_rows()[1:]:
        if _bare(row[0]) == _TOTAL_ROW_LABEL:
            continue
        model = re.search(r"`([^`]+)`", row[0])
        gate = re.search(r"门禁 \*\*(on|off)\*\*", row[0])
        assert model and gate, f"四列表的格位解析不出来：{row[0]!r}"
        key = (model.group(1), gate.group(1))
        for name, cell in zip(names, row[1:], strict=True):
            parsed[name][key] = _parse_cell(cell)
    for name, cells in parsed.items():
        assert tuple(cells) == FIRST_ROUND_CELLS, f"{name} 列的格位与四格表不符：{tuple(cells)}"
    return parsed


def doc_totals() -> dict[str, Cell]:
    """§12.3 四列并置表的合计行 → `{列名: Cell}`。"""
    names = _column_names()
    for row in _doc_table_rows()[1:]:
        if _bare(row[0]) == _TOTAL_ROW_LABEL:
            return {n: _parse_cell(c) for n, c in zip(names, row[1:], strict=True)}
    raise AssertionError(f"四列表里找不到「{_TOTAL_ROW_LABEL}」行")
