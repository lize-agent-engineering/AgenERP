"""非门禁测试 · 把门禁判定器的两种判定模式钉住。

判定器 `tools/gates/check_expected_red.py` 是本仓唯一的门禁判定器，它产出的退出码就是
`AGENTS.md` 裁判规则 1 里那个「测试过没过」的裁定。**在此文件出现之前，判定逻辑本身零判据覆盖**——
尤其是「出现 skip 即失败」那一条：`pytest` 对全部 skip 的一轮照样退 0，判定器不然，
而没有任何东西在验证判定器真的还在执行这句话。

本文件只喂**手写的 junit XML 片段**给 `classify()` / `verdict()` 两个纯函数，不起 pytest 子进程：
判据要能在毫秒级复跑，且不依赖活站点。两种模式共八态，见下面各条。
判定契约的出处是 `docs/architecture/system-baseline.md` §14.4。
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_TOOL = ROOT / "tools/gates/check_expected_red.py"

# 判定器不是包的一部分（它跑在 `tools/` 下，被 mission 与 CI 用绝对路径调用），
# 所以按文件路径加载，不走 import 系统的包解析。
_spec = importlib.util.spec_from_file_location("check_expected_red", _TOOL)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def junit(*cases: tuple[str, str, str]) -> str:
    """(classname, name, outcome) → 一份最小 junit 报告。outcome ∈ red/green/skipped。"""
    body = []
    for classname, name, outcome in cases:
        inner = {
            "red": "<failure message='boom'>boom</failure>",
            "skipped": "<skipped message='nope'/>",
            "green": "",
        }[outcome]
        body.append(f"<testcase classname='{classname}' name='{name}'>{inner}</testcase>")
    return f"<testsuites><testsuite name='pytest'>{''.join(body)}</testsuite></testsuites>"


A = "tests/gates/test_a.py::test_one"
B = "tests/gates/test_b.py::test_two"


def test_classify_maps_three_outcomes_and_rebuilds_nodeids():
    outcomes = gate.classify(junit(
        ("tests.gates.test_a", "test_one", "red"),
        ("tests.gates.test_b", "test_two", "green"),
        ("tests.gates.test_c", "test_three", "skipped"),
    ))
    assert outcomes == {
        A: "red",
        B: "green",
        "tests/gates/test_c.py::test_three": "skipped",
    }


def test_classify_counts_collection_error_as_red():
    outcomes = gate.classify(
        "<testsuites><testsuite name='pytest'>"
        "<testcase classname='tests.gates.test_a' name='test_one'>"
        "<error message='collection'>boom</error></testcase>"
        "</testsuite></testsuites>"
    )
    assert outcomes == {A: "red"}


# --- default 模式四态 ---------------------------------------------------------

def test_default_expected_red_is_green_verdict():
    code, lines = gate.verdict({A: "red", B: "green"}, {A}, live=False)
    assert code == 0
    assert lines[0] == "门禁 2 项：预期红 1，绿 1，跳过 0"
    assert lines[-1] == "✅ 与预期红名单完全一致"


def test_default_unexpected_red_fails_and_names_it():
    code, lines = gate.verdict({A: "red", B: "red"}, {A}, live=False)
    assert code == 1
    assert "❌ 名单外的门禁红了（真的坏了）：" in lines
    assert f"   {B}" in lines
    assert f"   {A}" not in lines


def test_default_unexpected_green_fails_and_names_it():
    code, lines = gate.verdict({A: "green", B: "green"}, {A}, live=False)
    assert code == 1
    assert any("名单内的门禁却绿了" in line for line in lines)
    assert f"   {A}" in lines


def test_default_skip_fails_even_when_everything_else_matches():
    """`pytest` 对全部 skip 的一轮退 0，判定器不然。这一条就是那个差别。"""
    code, lines = gate.verdict({A: "red", B: "skipped"}, {A}, live=False)
    assert code == 1
    assert "❌ 有测试被跳过 —— 门禁不允许 skip/xfail：" in lines
    assert f"   {B}" in lines


# --- live 模式四态 ------------------------------------------------------------

def test_live_all_green_passes():
    code, lines = gate.verdict({A: "green", B: "green"}, set(), live=True)
    assert code == 0
    assert lines[0] == "门禁 2 项：红 0，绿 2，跳过 0"
    assert lines[-1] == "✅ live 判定：全部门禁绿，零 red、零 skip"


def test_live_any_red_fails_and_names_it():
    code, lines = gate.verdict({A: "red", B: "green"}, set(), live=True)
    assert code == 1
    assert "❌ live 判定契约是全部门禁绿，下列门禁红了：" in lines
    assert f"   {A}" in lines


def test_live_any_skip_fails():
    code, lines = gate.verdict({A: "green", B: "skipped"}, set(), live=True)
    assert code == 1
    assert "❌ 有测试被跳过 —— 门禁不允许 skip/xfail：" in lines
    assert f"   {B}" in lines


def test_live_ignores_the_allowlist_entirely():
    """default 下「名单内那条绿了」是失败；live 下同一份输入必须退 0——名单压根不被读。"""
    outcomes = {A: "green", B: "green"}
    assert gate.verdict(outcomes, {A}, live=False)[0] == 1
    assert gate.verdict(outcomes, {A}, live=True)[0] == 0
    # 连一份根本对不上的名单也不该影响 live 判定。
    assert gate.verdict(outcomes, {"tests/gates/test_nonexistent.py::test_x"}, live=True)[0] == 0


@pytest.mark.parametrize("live", [False, True])
def test_verdict_never_touches_the_process(live):
    """纯函数接缝的意义：不读文件、不起子进程，才能从 tests/unit 直接喂输入。"""
    code, lines = gate.verdict({}, set(), live=live)
    assert code == 0
    assert lines[0].startswith("门禁 0 项：")
