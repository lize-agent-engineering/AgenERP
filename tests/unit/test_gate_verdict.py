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
import subprocess
import sys
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


# --- 取证面：红因不再随 junit 报告一起被丢掉 ------------------------------------
#
# 判定器以 `-q --tb=no` + `capture_output=True` 起 pytest，红因**只**在 junit 报告里；
# 报告此前解析完就被删，于是门禁红的时候一个字的断言原文都取不到（CI run 32509351108 实测）。
# 下面这些判据全部建在**合成 junit 字符串**上：本机默认判定环境的 7 条预期红是
# `failed on setup with "Failed: compose_stack 需要 AGENERP_LIVE=1` 这类 setup error，
# 里面根本没有断言原文，冒充不了这些判据。

_EXPLAIN = ROOT / "tools/gates/explain_last_gate_failures.py"
_espec = importlib.util.spec_from_file_location("explain_last_gate_failures", _EXPLAIN)
explain = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(explain)


def one_case(inner: str, timestamp: str | None = None) -> str:
    stamp = f" timestamp='{timestamp}'" if timestamp else ""
    return (f"<testsuites><testsuite name='pytest'{stamp}>"
            f"<testcase classname='tests.gates.test_a' name='test_one'>{inner}</testcase>"
            f"</testsuite></testsuites>")


def test_failure_details_keeps_message_and_body_of_a_failure():
    details = gate.failure_details(one_case(
        "<failure message='assert 0 == 1'>E       assert 0 == 1</failure>"))
    assert set(details) == {A}
    assert "assert 0 == 1" in details[A]
    assert "E       assert 0 == 1" in details[A]
    assert "<failure>" in details[A]


def test_failure_details_keeps_message_and_body_of_an_error():
    details = gate.failure_details(one_case(
        "<error message='collection failure'>ImportError: no module named x</error>"))
    assert set(details) == {A}
    assert "collection failure" in details[A]
    assert "ImportError: no module named x" in details[A]
    assert "<error>" in details[A]


def test_failure_details_uses_explicit_placeholders_instead_of_empty_strings():
    """正文/message 缺失时给显式占位：空串会让「这条没留下正文」长得像「取证出口坏了」。"""
    details = gate.failure_details(one_case("<failure/>"))
    assert details[A] == f"<failure> {gate.NO_MESSAGE}\n{gate.NO_BODY}"


def test_failure_details_does_not_count_skipped_as_a_failure():
    assert gate.failure_details(junit(
        ("tests.gates.test_a", "test_one", "skipped"),
        ("tests.gates.test_b", "test_two", "green"),
    )) == {}


def test_failure_details_is_empty_when_everything_is_green():
    assert gate.failure_details(junit(
        ("tests.gates.test_a", "test_one", "green"),
        ("tests.gates.test_b", "test_two", "green"),
    )) == {}


def test_failure_details_and_classify_agree_on_nodeids():
    """取证与判定共用同一套 nodeid 拼法，不许各拼各的——否则红因对不回是哪条门禁。"""
    xml = junit(("tests.gates.test_a", "test_one", "red"))
    reds = {n for n, o in gate.classify(xml).items() if o == "red"}
    assert set(gate.failure_details(xml)) == reds


def test_run_pytest_still_exits_2_when_pytest_writes_no_report(tmp_path, monkeypatch):
    """保命闸：`unlink` 前移之后，「pytest 自己没跑起来」仍然是 FATAL，不得退化成拿旧报告判定。

    真实触发路径是 pytest 收到未知参数（判定器把 sys.argv[1:] 原样转发），它参数解析就失败、
    **不写**报告。这里把那条路径的两个条件直接摆出来：报告路径确定不存在 + 子进程不写文件。
    端到端那一路由 plan 的 Exit Criteria 用 CLI 实跑覆盖，不在 tests/unit 里起真 pytest。
    """
    missing = tmp_path / "never-written.xml"
    monkeypatch.setattr(gate, "JUNIT", missing)
    monkeypatch.setattr(
        gate.subprocess, "run",
        lambda *a, **kw: __import__("types").SimpleNamespace(stdout="boom", stderr="boom"))
    with pytest.raises(SystemExit) as excinfo:
        gate.run_pytest(["--this-arg-does-not-exist"])
    assert excinfo.value.code == 2
    assert not missing.exists()


def test_importing_the_verdict_tool_has_no_side_effects():
    """取证出口要 import 判定器。import 必须不起 pytest、不打印、不碰报告文件。"""
    before = gate.JUNIT.stat().st_mtime if gate.JUNIT.exists() else None
    code = (
        "import importlib.util, subprocess, sys\n"
        "subprocess.run = lambda *a, **k: (_ for _ in ()).throw(AssertionError('起了子进程'))\n"
        f"spec = importlib.util.spec_from_file_location('cer', {str(_TOOL)!r})\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
    assert proc.stderr == ""
    after = gate.JUNIT.stat().st_mtime if gate.JUNIT.exists() else None
    assert before == after


def test_explain_prints_the_report_timestamp_on_the_very_first_line(tmp_path):
    """陈旧可见：报告长期驻盘，「文件在不在」区分不了刚才那轮和三天前那轮。"""
    report = tmp_path / "gates.xml"
    report.write_text(one_case("<failure message='boom'>boom</failure>",
                               timestamp="2026-08-22T02:28:00.123456"))
    first = explain.report_lines(report)[0]
    assert "2026-08-22T02:28:00.123456" in first
    assert str(report) in first


def test_explain_says_so_explicitly_when_the_report_has_no_timestamp(tmp_path):
    report = tmp_path / "gates.xml"
    report.write_text(one_case("<failure message='boom'>boom</failure>"))
    first = explain.report_lines(report)[0]
    assert explain.NO_TIMESTAMP in first
    assert first.strip()


def test_explain_prints_every_red_verbatim_and_never_touches_the_report(tmp_path):
    report = tmp_path / "gates.xml"
    report.write_text(one_case("<failure message='assert 0 == 1'>E       assert 0 == 1</failure>"))
    mtime = report.stat().st_mtime
    body = "\n".join(explain.report_lines(report))
    assert A in body
    assert "E       assert 0 == 1" in body
    assert report.exists()
    assert report.stat().st_mtime == mtime


def test_explain_exits_nonzero_when_the_report_is_missing(tmp_path, capsys):
    """取不到证要明说取不到。打印「没有失败」会让「取不到证」长得像「没红」。"""
    code = explain.main([str(tmp_path / "absent.xml")])
    assert code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "取不到证" in captured.err
