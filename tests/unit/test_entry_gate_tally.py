"""P1.0 逐格计数的判据：**八格可复算 + 四列各自被钉在自己的源上 + 区域外不许再手抄**。

plan `docs/plans/p1-insight/2026-08-25-0850-1-p1-0-cell-tally-single-source.md`。

⚠️ **本文件不裁定四个口径孰为准**（plan D2 / Non-Goal 2）。它判的只有两件事：
① 每一列是不是**忠实转录了它自称的那个源**；② 区域之外还有没有人在手抄。
「哪个对」是人的事 —— 差异逐格量化后登记在 `STATE.md` §3，不在这里选边。
"""

from __future__ import annotations

import hashlib

import pytest

from entry_gate_tally import (
    FIRST_ROUND_CELLS,
    LABELS,
    Cell,
    derive_from_labels,
    derive_from_verdicts,
    doc_table_header,
    doc_totals,
    load_labels,
    load_trace,
    parse_doc_columns,
    parse_state_correction,
    parse_state_first_review,
    parse_verdicts_cells,
    trace_path,
)
from entry_gate_tally import (
    REGION_CLOSE,
    REGION_OPEN,
    REPO_ROOT,
    UNRELATED_LINES,
    anchored_line,
    numbers_in,
    region_lines,
    fractions_in,
    region_prose_lines_with_numbers,
    scan_files,
    scan_handwritten_tallies,
    scan_text,
)

# plan §6 H1 逐字写死的八格。**逐格独立断言，不断言一个聚合数**。
EXPECTED_CELLS = {
    ("qwen-plus", "off"): (0, 3),
    ("qwen-plus", "on"): (2, 3),
    ("qwen3.6-plus", "off"): (3, 3),
    ("qwen3.6-plus", "on"): (3, 3),
    ("qwen3.7-plus-2026-05-26", "off"): (3, 3),
    ("qwen3.7-plus-2026-05-26", "on"): (3, 3),
    ("qwen3.8-max", "off"): (2, 3),
    ("qwen3.8-max", "on"): (3, 3),
}

EXPECTED_LABEL_ROWS = 24

# plan §0.1 执行期实读的标注集指纹。本 plan 一个字节不改它（Non-Goal 1），写死即自证。
LABELS_SHA256 = "243efdf33cc0283fd92bc4995d266994b2d26841164af77132060c86cf195b15"
LABELS_BYTES = 63529


# --------------------------------------------------------------------------- 判据①


@pytest.mark.parametrize(("key", "expected"), sorted(EXPECTED_CELLS.items()))
def test_derived_cell_matches_the_frozen_expectation(key, expected):
    """判据①：八格逐格 == plan §6 H1 写死的值。**一格一条**，不许拿合计蒙混。"""
    derived = derive_from_labels()
    assert key in derived, f"派生结果里没有这一格：{key}"
    assert tuple(derived[key]) == expected, f"{key} 实得 {derived[key]}，期望 {Cell(*expected)}"


def test_derived_tally_covers_exactly_the_eight_cells():
    """判据①的覆盖面：不多不少八格 —— 多出一格说明标注集混进了别的模型。"""
    assert set(derive_from_labels()) == set(EXPECTED_CELLS)


def test_denominator_comes_from_the_group_not_from_a_literal():
    """判据①的形态：分母**由分组实际行数得出**（M4 的对照）。

    删掉某一格的一行，该格分母必须从 3 掉到 2 —— 若分母写死成 3，这条就绿着放过去。
    """
    rows = [r for r in load_labels() if not (r["model"] == "qwen-plus" and r["gate"] == "off")]
    rows.append(dict(load_labels()[1], run_id="synthetic"))  # qwen-plus/off 只留一行
    derived = derive_from_labels(rows)
    assert derived[("qwen-plus", "off")].total == 1


# --------------------------------------------------------------------------- 判据②


def test_labels_are_pinned_to_the_very_runs_they_claim_to_label():
    """判据②：24 行的 `(model, gate)` 与轨迹同名键逐条相等，`answer` 与 `final_answer` 逐字节相等。

    **标注集的格归属不是自报的** —— 若它标的是另一批文本，这条当场红。
    """
    rows = load_labels()
    key_comparisons = 0
    answer_comparisons = 0
    for row in rows:
        trace = load_trace(row["run_id"])
        assert trace["run_id"] == row["run_id"], row["run_id"]
        assert trace["model"] == row["model"], row["run_id"]
        assert trace["gate"] == row["gate"], row["run_id"]
        key_comparisons += 1
        assert trace["final_answer"] == row["answer"], row["run_id"]
        answer_comparisons += 1
    # 计数断言：挡住「循环体一行没跑」的空实现（plan Phase 1 判据② 逐字要求）。
    assert key_comparisons == EXPECTED_LABEL_ROWS
    assert answer_comparisons == EXPECTED_LABEL_ROWS


def test_every_label_row_resolves_to_an_existing_trace_file():
    """判据②的输入面：`run_id` → 轨迹路径的解析对两轮各自的目录都成立。"""
    resolved = 0
    for row in load_labels():
        path = trace_path(row["run_id"])
        assert path.is_file(), f"{row['run_id']} 解析到的轨迹不存在：{path}"
        resolved += 1
    assert resolved == EXPECTED_LABEL_ROWS


def test_unknown_run_id_prefix_fails_loudly():
    """认不出轮次前缀时**当场失败**，不静默回一个不存在的路径。"""
    with pytest.raises(AssertionError, match="认不出"):
        trace_path("round3-01")


# --------------------------------------------------------------------------- 判据③


def test_label_set_shape():
    """判据③：行数 == 24 且 `run_id` 互不重复。"""
    rows = load_labels()
    assert len(rows) == EXPECTED_LABEL_ROWS
    run_ids = [r["run_id"] for r in rows]
    assert len(set(run_ids)) == EXPECTED_LABEL_ROWS, "有重复的 run_id"


def test_denominators_sum_to_the_whole_label_set():
    """判据③：八格分母之和 == 24 —— 挡住「某一格被静默漏掉」。"""
    assert sum(cell.total for cell in derive_from_labels().values()) == EXPECTED_LABEL_ROWS


def test_label_vocabulary_is_closed():
    """`label` 取值只有那三种；冒出第四种说明标注集被改过，派生口径要重看。"""
    assert {r["label"] for r in load_labels()} == {"correct", "incomplete", "truncated"}


def test_labels_fixture_is_untouched_by_this_plan():
    """plan Non-Goal 1 的自证：标注集的字节数与 sha256 与 §0.1 实读逐字相同。

    本 plan **只读它、只数它**。这一条一旦红，说明有人在「数一数」的过程里改了被数的东西。
    """
    raw = LABELS.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == LABELS_SHA256
    assert len(raw) == LABELS_BYTES
    assert raw.count(b"\n") == EXPECTED_LABEL_ROWS


# --------------------------------------------------------------------------- 判据④⑤⑥：四列

# 四列的取值并集（⑨b 用它兜底）。**这不是「正确值」** —— 四列并置，本仓不裁定孰为准。
COLUMN_VALUE_UNION = frozenset({"0/3", "1/3", "2/3", "3/3", "2/12", "5/12", "8/12"})


def _doc_column(name: str) -> dict[tuple[str, str], Cell]:
    return parse_doc_columns()[name]


def test_doc_table_has_exactly_the_four_columns_and_no_verdict_column():
    """D2 的落地形态：四列**并置**，且表里**没有**「正确值」/「以哪个为准」这类列。"""
    assert tuple(parse_doc_columns()) == ("甲", "乙", "丙", "丁")
    header = doc_table_header()
    for banned in ("正确值", "为准", "采信", "结论值"):
        assert banned not in "".join(header), f"四列表里冒出了裁定列：{header}"


def test_criterion_4_column_ding_equals_the_deriver():
    """判据④：丁列与 Phase 1 的派生器**逐格相等**（M1 打这一条）。"""
    derived = derive_from_labels()
    doc = _doc_column("丁")
    assert set(doc) == set(FIRST_ROUND_CELLS)
    for key in FIRST_ROUND_CELLS:
        assert doc[key] == derived[key], f"丁列 {key} 与派生器不符：{doc[key]} vs {derived[key]}"


def test_criterion_5_column_yi_equals_the_state_first_review():
    """判据⑤（乙）：与 `STATE.md` `2026-08-24T07:31Z` 那张表**机械解析后逐格相等**。"""
    state = parse_state_first_review()
    doc = _doc_column("乙")
    for key in FIRST_ROUND_CELLS:
        assert doc[key] == state[key], f"乙列 {key} 与 STATE 07:31Z 表不符"


def test_criterion_5_column_bing_equals_the_state_correction():
    """判据⑤（丙）：与 `2026-08-24T09:01Z` 更正表的 `正确值` 列逐格相等，合计也相等。"""
    state, total = parse_state_correction()
    doc = _doc_column("丙")
    for key in FIRST_ROUND_CELLS:
        assert doc[key] == state[key], f"丙列 {key} 与 STATE 09:01Z 更正表不符"
    assert doc_totals()["丙"] == total


def test_criterion_6_column_jia_equals_the_loop_verdicts():
    """判据⑥：甲列 == `verdicts.md` 逐条打勾行**数出来**的结果。"""
    verdicts = derive_from_verdicts()
    doc = _doc_column("甲")
    for key in FIRST_ROUND_CELLS:
        assert doc[key] == verdicts[key], f"甲列 {key} 与 verdicts.md 逐条打勾不符"


def test_verdicts_self_reported_rate_agrees_with_counting_its_own_rows():
    """交叉核对：`verdicts.md` 揭配置表自报的正确率 == 数它自己那些打勾行的结果。

    两处不一致就说明解析口径错了 —— 本判据不许拿自报数当结果（判据⑥ 逐字要求）。
    """
    counted = derive_from_verdicts()
    for key, (_, self_reported) in parse_verdicts_cells().items():
        assert counted[key] == self_reported, f"{key} 数出来 {counted[key]}，该表自报 {self_reported}"


def test_column_totals_are_the_sum_of_their_own_four_cells():
    """合计行**不是手抄**：每列的合计 == 该列四格相加（分子分母都加）。"""
    totals = doc_totals()
    columns = parse_doc_columns()
    for name, total in totals.items():
        cells = [columns[name][key] for key in FIRST_ROUND_CELLS]
        assert total == Cell(sum(c.hits for c in cells), sum(c.total for c in cells)), name


def test_the_four_columns_really_do_disagree():
    """本 plan 的前提自证：四列**确实不是同一组数** —— 若哪天它们全等了，
    「并置而不裁定」这个形态就该重看，而不是继续摆着。"""
    totals = doc_totals()
    assert len({str(t) for t in totals.values()}) > 1, f"四列合计已全等：{totals}"


# --------------------------------------------------------------------------- 判据⑨：区域内

# ⑨a 的绑定表：**逐字锚点 → 该行有序数元组该等于哪几个列-格**。
# 取数跨度是**锚点所在的那一整行**，一行绑定一次（plan Phase 2 逐字写死）。
# ⚠️ 它判的是「这句话是否仍然忠实转述它自称的出处」，**不是「这个数对不对」** ——
# 结论句被钉到乙列，是因为本节 `2026-08-24T07:31Z` 那个出处自述取的就是乙列。
ANCHOR_BINDINGS = (
    ("门禁把 0/3 提到 1/3", (("乙", ("qwen-plus", "off")), ("乙", ("qwen-plus", "on")))),
    (
        "加门禁反而 1/3 → 0/3",
        (
            ("乙", ("qwen3.6-plus", "off")),
            ("乙", ("qwen3.6-plus", "on")),
            ("乙", "合计"),
        ),
    ),
    ("「0/3 vs 1/3」不得当作量化结论", (("乙", ("qwen-plus", "off")), ("乙", ("qwen-plus", "on")))),
    (
        "该文件记弱模型门禁 on 为 2/3、强模型两格均为 3/3",
        (("甲", ("qwen-plus", "on")), ("甲", ("qwen3.6-plus", "off"))),
    ),
)


def _expected_value(column: str, ref) -> str:
    if ref == "合计":
        return str(doc_totals()[column])
    return str(parse_doc_columns()[column][ref])


@pytest.mark.parametrize(("anchor", "refs"), ANCHOR_BINDINGS)
def test_criterion_9a_prose_number_matches_the_column_it_cites(anchor, refs):
    """判据⑨a：被绑定的每一行散文，其内嵌的数**按出现顺序**等于它自称的那几个列-格。

    **锚点缺失即红** —— `anchored_line()` 找不到唯一一行就当场失败（M9 打这一条）。
    """
    actual = numbers_in(anchored_line(anchor))
    expected = tuple(_expected_value(column, ref) for column, ref in refs)
    assert actual == expected, f"锚点 {anchor!r} 的数 {actual}，按它自称的列该是 {expected}"


def test_criterion_9a_side_assertion_two_cells_are_equal():
    """⑨a-4 那句「强模型**两格均为**」四个字的含义：甲列强模型两格必须真的相等。"""
    jia = parse_doc_columns()["甲"]
    assert jia[("qwen3.6-plus", "off")] == jia[("qwen3.6-plus", "on")]


def test_criterion_9a_coverage_is_constructed_not_counted():
    """⑨a 的覆盖完整性：区域内**含数字的散文行**条数 == 被绑定的锚点条数。

    多一行没被绑定就红 —— 覆盖是构造出来的，不是靠今天数出来的那几行。
    表格行由 判据④⑤⑥ 按列钉住，**刻意排除在本计数之外，是分工不是漏掉**。
    """
    assert len(region_prose_lines_with_numbers()) == len(ANCHOR_BINDINGS)


def test_criterion_9b_every_number_in_the_region_is_a_declared_column_value():
    """判据⑨b（兜底）：区域内**每一处**数字出现都必须落在四列取值的并集里。

    ⚠️ **⑨b 单独是不够的** —— 把某一格改成另一个同样在并集里的值，它是绿的。
    承重的是 ⑨a 与 判据④⑤⑥；⑨b 只兜「冒出一个谁都没声明过的新数」（M9b 打这一条）。
    """
    declared = {str(cell) for column in parse_doc_columns().values() for cell in column.values()}
    declared |= {str(total) for total in doc_totals().values()}
    assert declared == set(COLUMN_VALUE_UNION), f"四列取值并集变了：{sorted(declared)}"
    for line in region_lines():
        for number in fractions_in(line):
            assert number in declared, f"区域内冒出一个四列都没声明过的数 {number}：{line.strip()!r}"


def test_criterion_9b_reaches_wider_than_the_guard_number_face():
    """⑨b 的取数口径必须**比守卫的数字面宽**（M9b 逼出来的那一条）。

    `4/9` 这种四列都没声明过的数**不匹配守卫的数字面** —— 若 ⑨b 复用那个面，
    M9b 就会跑绿、兜底那半在区域里根本没在兜。
    """
    assert numbers_in("顺手记一笔 4/9。") == ()
    assert fractions_in("顺手记一笔 4/9。") == ("4/9",)


# --------------------------------------------------------------------------- 判据⑦：守卫

# M7 / M7b 的注入文本，**plan §8 Phase 4 跑之前逐字写死**，执行期一个字未改。
M7_INJECTION = "⚠️ qwen3.6-plus 在两跳题上是 1/6。"
M7B_INJECTION = "是 1/6。"


def test_criterion_7_positive_control_the_wide_net_really_does_misfire():
    """判据⑦ 的**阳性对照**：只留数字面、去掉语境面与区域面，那 6 行无关文本**全部误报**。

    没有这一条，「收窄之后 0 误报」就分不清是「收窄有效」还是「守卫根本没在扫」。
    """
    wide = scan_handwritten_tallies(require_context=False, honour_region=False)
    indexed = {(path, line) for path, _, line in wide}
    for path, fragment in UNRELATED_LINES:
        assert any(p == path and fragment in line for p, line in indexed), (
            f"宽网没有命中这一行无关文本，阳性对照不成立：{path} :: {fragment}"
        )
    assert len(wide) > len(UNRELATED_LINES), "宽网只命中无关面，说明区域内的表根本没被扫到"


def test_criterion_7_narrowed_guard_has_zero_false_positives_and_zero_misses():
    """判据⑦：三条谓词合取之后，`agenerp/**` 与 `docs/architecture/**` 上**一处命中都没有**。

    命中不为空 = 区域外还有人在手抄 P1.0 的逐格数（§6 **H4** 判这一条）。
    """
    hits = scan_handwritten_tallies()
    assert hits == [], "区域外仍有手抄的 P1.0 逐格数：\n" + "\n".join(
        f"  {path}:{number}: {line.strip()}" for path, number, line in hits
    )


def test_criterion_7_guard_is_not_vacuous_m7():
    """守卫**非空转**（M7 的可复跑形态）：新写一处**带语境**的手抄，当场打红。"""
    injected = ["## 某节", "", M7_INJECTION, ""]
    assert scan_text(injected) == [(3, M7_INJECTION)]


def test_criterion_7_context_marker_may_sit_on_a_preceding_line():
    """语境面的窗口是「本行 + 前 4 行」：标识在上一行、数字在下一行**照样打红**。

    这正是 §6.1.1 否决「只看本行」的那个失败形态（该口径漏报 4 行）。
    """
    injected = ["`qwen3.6-plus` 的多跳表现：", "", "", "", "无门禁 1/3。"]
    assert scan_text(injected) == [(5, "无门禁 1/3。")]
    assert scan_text(injected, require_context=False)[0][0] == 5


def test_criterion_7_bare_tally_without_context_is_a_known_blind_spot_m7b():
    """**M7b：这一条的期望就是「守卫看不见」** —— 不是通过，是把边界实测出来。

    一处前 4 行内不含任何标识的裸计数，对**任何**基于语境的守卫都不可见
    （plan §6.2 第 7 条、§11 具名残余风险）。⚠️ **它若打红了反而要回头查** ——
    那说明窗口比 §6.1.1 标定的更宽。**不假装守得住。**
    """
    injected = ["## 无关小节", "", "", "", "", M7B_INJECTION]
    assert scan_text(injected) == [], "M7b 打红了：窗口比 §6.1.1 标定的更宽，回头查"
    # 同一行文本一旦有语境就该被抓到 —— 证明漏的是语境不是数字面。
    assert scan_text(["门禁", M7B_INJECTION]) == [(2, M7B_INJECTION)]


def test_criterion_7_region_is_not_a_filename_whitelist():
    """区域面排除的是**由标记界定的一段**，不是一份文件白名单。

    同一个文件里、区域之外新写一处手抄，**照样红**。
    """
    injected = [
        REGION_OPEN,
        "门禁 off **0/3**",
        REGION_CLOSE,
        "",
        "⚠️ 门禁把它提到 2/3。",
    ]
    assert scan_text(injected) == [(5, "⚠️ 门禁把它提到 2/3。")]


def test_criterion_7_guard_scope_covers_both_trees():
    """守卫扫的是两棵树的**全部**文件，不是几个写死的文件名。"""
    scanned = {str(path.relative_to(REPO_ROOT)) for path in scan_files()}
    assert "agenerp/explain/loop.py" in scanned
    assert "docs/architecture/model-management.md" in scanned
    assert "docs/architecture/module-boundaries.md" in scanned
    assert len(scanned) > 10, f"扫描面只有 {len(scanned)} 个文件，疑似退化成白名单"


# --------------------------------------------------------------------------- 判据⑧：历史叙述

HISTORY_FILE = REPO_ROOT / "tests/unit/test_answer_judging_fixture.py"


def test_criterion_8_the_historical_narrative_keeps_its_own_numbers():
    """判据⑧：四次判错那张历史叙述表的**数字一个字不改**。

    它记的是「我当时判成了什么」，不是「哪个数才对」——
    按今天的口径去改它，等于把历史抹平（挡住「顺手把历史改成新口径」）。
    """
    text = HISTORY_FILE.read_text(encoding="utf-8")
    assert "第一轮整体从 5/12 误判成 2/12" in text
    assert "三份正确答案判成「不完全」" in text
    assert "要求字面 `2000`，认不出 `1000 + 1000 - 990`" in text


def test_criterion_8_the_historical_narrative_points_at_the_single_source():
    """判据⑧的另一半：那张表旁边必须有一条指向 §12.3 单一真相源的指针。"""
    text = HISTORY_FILE.read_text(encoding="utf-8")
    assert "model-management.md` §12.3" in text
    assert "tests/unit/entry_gate_tally.py" in text
