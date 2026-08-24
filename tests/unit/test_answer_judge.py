"""答案判定器 v0 的**离线判据**：全部走假 transport，**零网络、零凭据**。

本文件对应 plan `docs/plans/p1-insight/2026-08-25-0225-1-answer-judge-v0.md` 的 §6 H1 / H1c / H7，
以及 §7 Phase 4 预注册的变异 M1–M10 的靶子。

⚠️ **本文件不判「判定器在 24 条上达没达标」** —— 那是活端点的事（`tools/experiments/p1_answer_judge/`）。
本文件判的是**判定器这个装置的结构性质**：它只吃一段文本、它的标签是模型回包的函数、
它一次调用一条账、它不回写集子。两件事分开，是因为**口径撑不住"它真的在判断"这个结论**
（plan §1.3 三条约束），主证在这里。
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import pathlib
import sys

import pytest

import answer_judge_fixture as fx
from agenerp.explain.ledger import CallLedger
from agenerp.judging import JudgingError, Verdict, judge_one
from agenerp.routing.errors import RoutingError

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JUDGING_PACKAGE = REPO_ROOT / "agenerp/judging"


def _code_without_docstrings(path: pathlib.Path) -> str:
    """把文件里的 docstring 摘掉再看代码 —— 判"实现里有没有这条路"时，
    模块头里对这条路的**说明文字**不该算数。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(
                node.body[0].value, ast.Constant
            ) and isinstance(node.body[0].value.value, str):
                node.body.pop(0)
                if not node.body:
                    node.body.append(ast.Pass())
    return ast.unparse(ast.fix_missing_locations(tree))


# -- H1 · 四种假实现在同一个验收函数下全部为假 -------------------------------


@pytest.mark.parametrize("name", sorted(fx.FAKE_JUDGES))
def test_h1_every_fake_judge_fails_the_acceptance_function(name):
    """**四种假实现全红**：三个常量判定器 + 那个一行关键词匹配器。

    ⚠️ 各自的强度照实说：`always-incomplete` / `always-truncated` 在 19 条正例上 0/19，
    **近乎恒假、几乎没有判别力**；`always-correct` 只压得住"负例召回"这一条；
    `substring-only` 是这四个里唯一有威胁的（旧口径下 23/24）。
    """
    pairs = fx.pairs_from_rule(fx.FAKE_JUDGES[name])
    assert fx.meets_acceptance(pairs) is False, f"{name} 竟然通过了验收口径"


def test_h1_the_four_fakes_are_exactly_the_pre_registered_ones():
    """预注册的那四个，一个不少 —— 少一个，H1 就成了"挑好过的测"。"""
    assert set(fx.FAKE_JUDGES) == {
        "always-correct",
        "always-incomplete",
        "always-truncated",
        "substring-only",
    }


def test_h1_always_correct_would_pass_a_naive_overall_accuracy_bar():
    """**M2 的靶子**：总体准确率 79.2% 看起来很高 —— 所以它不能当口径。"""
    pairs = fx.pairs_from_rule(fx.CONSTANT_JUDGES["always-correct"])
    hit = sum(1 for human, judged in pairs if human == judged)
    assert hit == 19 and len(pairs) == 24
    assert hit / len(pairs) > 0.75
    assert fx.meets_acceptance(pairs) is False


# -- H1c · 两个预注册的对抗基线 x 两个口径，共四格 ---------------------------


@pytest.mark.parametrize("name", sorted(fx.ADVERSARIAL_BASELINES))
@pytest.mark.parametrize("gauge", ["legacy", "current"])
def test_h1c_both_adversarial_baselines_land_where_drafting_predicted(name, gauge):
    """四格逐格断言，**含 (b) 在新口径下通过那一格**。

    断言 (b) 通过，是为了让「**H2 是必要条件，不是充分条件**」这件事**有判据守着**，
    而不是靠人自觉。⚠️ 不许因为 (b) 通过就去再收紧口径 —— plan §1.3 已说明那条路走不通。
    """
    pairs = fx.pairs_from_rule(fx.ADVERSARIAL_BASELINES[name])
    got = fx.meets_legacy_acceptance(pairs) if gauge == "legacy" else fx.meets_acceptance(pairs)
    assert got is fx.EXPECTED_BASELINE_OUTCOMES[name][gauge]


def test_m2b_both_baselines_stay_registered_and_both_gauges_stay_declared():
    """**M2b 的靶子**：把不好看的那个基线悄悄拿掉，这一条当场红。"""
    assert set(fx.ADVERSARIAL_BASELINES) == {"substring-only", "length-plus-substring"}
    assert set(fx.EXPECTED_BASELINE_OUTCOMES) == set(fx.ADVERSARIAL_BASELINES)
    for outcomes in fx.EXPECTED_BASELINE_OUTCOMES.values():
        assert set(outcomes) == {"legacy", "current"}
    assert fx.EXPECTED_BASELINE_OUTCOMES["length-plus-substring"]["current"] is True


# -- 验收函数自身的边界（M1 的靶子） -----------------------------------------


def _pairs(negatives: dict[str, str], positive_hits: int) -> list[tuple[str, str]]:
    """按人标签构造一组 24 对：负例逐条指定判定标签，正例指定命中几条。"""
    out = []
    kept = positive_hits
    for row in fx.rows():
        if row["label"] == "correct":
            out.append(("correct", "correct" if kept > 0 else "incomplete"))
            kept -= 1
        else:
            out.append((row["label"], negatives[row["run_id"]]))
    return out


EXACT_NEGATIVES = {
    "run-02": "incomplete",
    "run-05": "incomplete",
    "run-07": "truncated",
    "run-13": "incomplete",
    "r2-07": "incomplete",
}


def test_acceptance_requires_exact_three_way_labels_on_every_negative():
    """**M1 的靶子**：把 `run-07` 判成 `incomplete`（非 `correct`，但标签错）必须为假。"""
    off_by_one = dict(EXACT_NEGATIVES, **{"run-07": "incomplete"})
    assert fx.meets_acceptance(_pairs(off_by_one, 19)) is False


def test_acceptance_requires_at_least_seventeen_of_nineteen_positives():
    assert fx.meets_acceptance(_pairs(EXACT_NEGATIVES, 16)) is False


def test_acceptance_is_true_at_the_exact_floor():
    assert fx.meets_acceptance(_pairs(EXACT_NEGATIVES, 17)) is True


# -- H7 (1) 签名级 -----------------------------------------------------------

ALLOWED_PARAMS = ("answer", "models", "requested", "config", "transport", "ledger", "index",
                  "max_tokens")
FORBIDDEN_PARAM_SUBSTRINGS = ("label", "reason", "row", "record", "gold", "truth", "expected",
                              "annotation")


def test_h7_1_judge_one_takes_one_piece_of_text_and_nothing_that_can_carry_a_label():
    """**签名级**：行对象整体进不去，`label` / `reason` 没有任何形参可以承载。

    比 AST 扫描强：AST 的作用域是实现者自己选的，签名不是。
    """
    sig = inspect.signature(judge_one)
    names = tuple(sig.parameters)
    assert names == ALLOWED_PARAMS, f"签名变了：{names}"
    first = sig.parameters["answer"]
    assert first.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert first.annotation == "str"  # `from __future__ import annotations` => 注解是字符串
    for name in names[1:]:
        assert sig.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
    for name in names:
        for bad in FORBIDDEN_PARAM_SUBSTRINGS:
            assert bad not in name.lower(), f"形参 {name!r} 能承载被判那一行的 {bad}"


# -- H7 (2) 标签无关级：真行 vs 噪声行 => messages 逐字节相同 -----------------


@pytest.mark.parametrize("run_id", [r["run_id"] for r in fx.rows()])
def test_h7_2_the_row_label_and_reason_never_reach_the_messages(run_id):
    """**每一条**标注各构造两次：真行、把 `label`/`reason` 换成噪声的同一行。

    两次生成的 `messages` **逐字节完全相同** —— 泄漏发生在**入口**，
    所以比较面是送进去的 `messages`，不是出来的 `Verdict`（M10 挡的就是这个放松方向）。
    ⚠️ 与"三个标签词必须出现在题面里"天然共存：题面里的
    `correct`/`incomplete`/`truncated` 是**输出空间的定义**，它不随行变。
    """
    row = fx.row_by_id(run_id)
    real = fx.RecordingTransport()
    noised = fx.RecordingTransport()
    fx.judge_row(row, transport=real)
    fx.judge_row(fx.noise_row(row), transport=noised)
    assert real.payloads[0]["messages"] == noised.payloads[0]["messages"]
    sent = repr(real.payloads[0]["messages"])
    assert row["reason"] not in sent
    assert f'"这条的答案是 {row["label"]}"' not in sent


def test_m10_the_leak_check_compares_the_messages_not_the_verdict():
    """**M10 的靶子**：把 H7 ② 的比较面放宽到 `Verdict`（只看出口不看入口）时，这一条红。"""
    src = inspect.getsource(test_h7_2_the_row_label_and_reason_never_reach_the_messages)
    body = ast.unparse(ast.parse(src).body[0].body[1:])  # 摘掉 docstring，只看真正跑的那几行
    assert "payloads[0]['messages']" in body, "H7 ② 的比较面必须是送进去的 messages"
    assert body.count("payloads[0]['messages']") >= 2
    assert "Verdict" not in body, "H7 ② 一旦改成比较 Verdict，就只看出口不看入口了"


# -- H7 (3) 回包依赖级：三点式，答案取一条含「外协」的 -----------------------


def test_h7_3_the_label_is_a_function_of_the_model_reply():
    """**本 plan 的主证**：同一段答案 + 两份不同的假回包 => 两个不同的标签。

    ⚠️ 答案**钉死取 `run-01`**（含「外协」）—— 否则 M9b 那种
    "命中关键词就直接返回 `correct`、其余才读回包"的混合短路在不含该词的答案上照样过。
    """
    row = fx.row_by_id(fx.KEYWORD_BEARING_RUN_ID)
    assert fx.OVERFIT_KEYWORD in row["answer"]

    first = fx.judge_row(row, transport=fx.RecordingTransport(fx.label_body("correct")))
    second = fx.judge_row(row, transport=fx.RecordingTransport(fx.label_body("incomplete")))
    third = fx.judge_row(row, transport=fx.RecordingTransport(fx.label_body("truncated")))

    assert first.label == "correct"
    assert second.label == "incomplete"
    assert third.label == "truncated"
    assert len({first.label, second.label, third.label}) == 3


def test_h7_3_the_same_answer_can_be_judged_truncated_when_the_reply_says_so():
    """三点式的第三点单列一条：**回包说 `truncated` 就得到 `truncated`**。"""
    row = fx.row_by_id(fx.KEYWORD_BEARING_RUN_ID)
    verdict = fx.judge_row(row, transport=fx.RecordingTransport(fx.label_body("truncated")))
    assert verdict.label == "truncated"


# -- 未知标签指名报错（M5 的靶子） -------------------------------------------


@pytest.mark.parametrize("text", ['{"label": "unjudgeable"}', '{"label": "CORRECT"}'])
def test_an_unknown_label_is_named_and_raised_not_silently_normalised(text):
    row = fx.row_by_id(fx.KEYWORD_BEARING_RUN_ID)
    with pytest.raises(JudgingError) as exc:
        fx.judge_row(row, transport=fx.RecordingTransport(fx.reply_body(text)))
    assert "未知标签" in str(exc.value)


@pytest.mark.parametrize("text", ["我认为这段答案是对的。", "correct 或 incomplete 都说得通"])
def test_a_reply_without_a_parseable_label_object_is_raised_too(text):
    row = fx.row_by_id(fx.KEYWORD_BEARING_RUN_ID)
    with pytest.raises(JudgingError):
        fx.judge_row(row, transport=fx.RecordingTransport(fx.reply_body(text)))


def test_a_reply_wrapped_in_prose_still_parses():
    """推理模型常在 JSON 前写几句 —— 那不是失败，别把它算成解析错误。"""
    row = fx.row_by_id(fx.KEYWORD_BEARING_RUN_ID)
    body = fx.reply_body('三条判据全中。\n\n{"label": "correct"}')
    assert fx.judge_row(row, transport=fx.RecordingTransport(body)).label == "correct"


# -- 判定器不吃 label / reason（结果面） -------------------------------------


def test_the_verdict_is_byte_identical_for_a_row_whose_label_and_reason_are_noise():
    row = fx.row_by_id(fx.KEYWORD_BEARING_RUN_ID)
    real = fx.judge_row(row, transport=fx.RecordingTransport(fx.label_body("correct")))
    noised = fx.judge_row(fx.noise_row(row), transport=fx.RecordingTransport(fx.label_body("correct")))
    assert isinstance(real, Verdict)
    assert real.as_dict() == noised.as_dict()


# -- M6 · 本包一律走 route()，不直接构造 ChatAdapter -------------------------


def test_m6_the_judging_package_never_constructs_a_chat_adapter_itself():
    """F8（`ChatAdapter` 可被直接构造绕过能力校验）那条路**不在本包重现**。"""
    for path in sorted(JUDGING_PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "ChatAdapter", f"{path.name} 直接构造了 ChatAdapter"
            if isinstance(node, ast.ImportFrom):
                imported = [a.name for a in node.names]
                assert "ChatAdapter" not in imported, f"{path.name} import 了 ChatAdapter"
    judge_src = (JUDGING_PACKAGE / "judge.py").read_text(encoding="utf-8")
    assert "route(" in judge_src


def test_no_product_module_in_the_judging_package_reads_the_annotation_set():
    """产品包**不许**依赖 `tests/fixtures/**`（D7b：边界倒置）。"""
    for path in sorted(JUDGING_PACKAGE.glob("*.py")):
        code = _code_without_docstrings(path)
        assert "p1_entry_gate_labels" not in code
        assert "tests/fixtures" not in code


# -- M7 · 判定结果不回写标注集 -----------------------------------------------


def test_m7_running_the_whole_fixture_offline_leaves_the_annotation_set_byte_identical():
    """**集子不可写**要有判据守着，不能只靠人自觉（plan Goal 5）。"""
    transport = fx.RecordingTransport(fx.label_body("correct"))
    verdicts = [fx.judge_row(row, transport=transport) for row in fx.rows()]
    assert len(verdicts) == 24
    assert transport.calls == 24
    # 参照是**模块导入那一刻**的指纹，不是"本条判据跑之前"的指纹 —— 见 `PRISTINE_SHA256` 的注释。
    assert fx.fixture_sha256() == fx.PRISTINE_SHA256


def test_m7_neither_the_judging_package_nor_the_helper_has_a_write_path():
    for path in [*sorted(JUDGING_PACKAGE.glob("*.py")), REPO_ROOT / "tests/unit/answer_judge_fixture.py"]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr not in {"write_text", "write_bytes"}, f"{path.name} 有写文件的路径"


# -- M8 · 一次 chat() 一条账 -------------------------------------------------


def test_m8_the_ledger_has_exactly_one_entry_per_chat_call():
    ledger = CallLedger()
    transport = fx.RecordingTransport(fx.label_body("correct"))
    for index, row in enumerate(fx.rows()):
        fx.judge_row(row, transport=transport, ledger=ledger, index=index)
    assert transport.calls == 24
    assert len(ledger) == transport.calls
    assert all(entry.total_matches_endpoint for entry in ledger.entries)
    assert ledger.total.reasoning == 29 * 24


def test_m8_a_failed_call_is_still_on_the_ledger_and_still_raised():
    """端点回过包 = token 已经真的花掉。**不许悄悄不记**（P1.7 / D-18）。"""
    ledger = CallLedger()
    broken = fx.RecordingTransport({"usage": fx.usage_body(), "choices": []})
    row = fx.row_by_id(fx.KEYWORD_BEARING_RUN_ID)
    with pytest.raises(RoutingError):
        fx.judge_row(row, transport=broken, ledger=ledger, index=0)
    assert broken.calls == 1
    assert len(ledger) == 1
    assert ledger.entries[0].outcome == "model-error"
    assert ledger.entries[0].usage.total == fx.usage_body()["total_tokens"]


def test_the_reasoning_model_usage_lands_on_the_verdict():
    row = fx.row_by_id(fx.KEYWORD_BEARING_RUN_ID)
    verdict = fx.judge_row(row, transport=fx.RecordingTransport(fx.label_body("correct")))
    assert verdict.usage.prompt > 0 and verdict.usage.completion > 0 and verdict.usage.reasoning > 0
    assert verdict.endpoint_usage["total_tokens"] == verdict.usage.total
    assert verdict.model == "fake-judge"


# -- 题面自身的性质 ----------------------------------------------------------


def test_the_rubric_declares_exactly_three_labels_and_no_fourth_class():
    from agenerp.judging import rubric

    assert rubric.LABELS == ("correct", "incomplete", "truncated")
    prompt = rubric.system_prompt()
    for label in rubric.LABELS:
        assert label in prompt
    assert "unjudgeable" not in prompt
    assert "无法判定" in prompt


def test_the_rubric_criteria_are_the_frozen_p10_ones():
    """三条判据逐字取自 `docs/evidence/p1-entry-gate/verdicts.md`，**本 plan 不新增判准**。"""
    from agenerp.judging import rubric

    verdicts = (REPO_ROOT / "docs/evidence/p1-entry-gate/verdicts.md").read_text(encoding="utf-8")
    for criterion in rubric.CRITERIA:
        head = criterion.split("（")[0].strip().lstrip("①②③").strip()
        assert head in verdicts, f"判据 {head!r} 不在 P1.0 冻结的那张表里"


def test_an_empty_answer_is_not_a_legal_input():
    with pytest.raises(JudgingError):
        judge_one("   ", models=fx.models(), config=fx.config(), transport=fx.RecordingTransport())


# -- M12 · 泄漏判据也要盖住**产出证据的那条路** ------------------------------
#
# 独立关闭审计（2026-08-25）指出的一处缺口：H7 ② 只跑过
# `answer_judge_fixture.judge_row`，而 `docs/evidence/p1-answer-judge/` 里那三份
# 被采信的证据是 `tools/experiments/p1_answer_judge/run.py` 跑出来的 —— **另一条调用点**，
# 且 `tools/` 既无判据覆盖也不在 ruff 作用域内。审计实读确认当时**没有发生泄漏**，
# 但没有任何东西挡住后来的人把 `row["label"]` 拼进活跑的题面。
# 本条把 H7 ② 那条谓词**原样抬到实验设施上**：真行 vs 噪声行，`messages` 逐字节相同。


def _load_experiment_harness():
    """按路径加载实验脚本。**它不在 `tests/` 里，也不是产品包** —— 按路径加载，不改 `sys.path`。"""
    target = REPO_ROOT / "tools/experiments/p1_answer_judge/run.py"
    assert target.is_file(), f"实验设施不在了：{target}"
    spec = importlib.util.spec_from_file_location("_p1_answer_judge_run", target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _HarnessFixture:
    """喂给 `run_all` 的最小夹具面：只换 `rows()`，别的照旧。

    `meets_acceptance` 在这里恒为假 —— **本判据不判口径**，只判「送进去的东西有没有泄漏」。
    """

    def __init__(self, rows: list[dict]) -> None:
        self._rows = [dict(r) for r in rows]

    def rows(self) -> list[dict]:
        return [dict(r) for r in self._rows]

    def row_by_id(self, run_id: str) -> dict:
        return next(r for r in self.rows() if r["run_id"] == run_id)

    def fixture_sha256(self) -> str:
        return fx.fixture_sha256()

    def meets_acceptance(self, pairs) -> bool:
        return False


def _harness_messages(monkeypatch, rows: list[dict]) -> list:
    """离线跑一趟 `run_all`，把它**实际送出去的** `messages` 逐条收下来。"""
    harness = _load_experiment_harness()
    monkeypatch.setattr("agenerp.routing.router.config_from_env", fx.config)
    transport = fx.RecordingTransport()
    harness.run_all(_HarnessFixture(rows), transport=transport)
    return [p["messages"] for p in transport.payloads]


def test_m12_the_experiment_harness_never_leaks_the_label_or_reason_either(monkeypatch):
    """**M12 的靶子**：实验设施把该行的 `label` / `reason` 拼进活跑题面时，这一条红。"""
    real_rows = fx.rows()
    real = _harness_messages(monkeypatch, real_rows)
    noised = _harness_messages(monkeypatch, [fx.noise_row(r) for r in real_rows])

    assert len(real) == len(real_rows), "24 行要真的各送出去一次，否则这条判据是空的"
    assert real == noised, "实验设施送出去的 messages 随行的 label/reason 变了 —— 泄漏在入口"

    sent = repr(real)
    for row in real_rows:
        assert row["reason"] not in sent
        assert f'"这条的答案是 {row["label"]}"' not in sent
