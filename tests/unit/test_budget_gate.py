"""非门禁测试 · 把日预算停机闸 `tools/gates/check_budget.py` 的判定钉住。

这条闸是 7×24 循环唯一的成本停机入口：`tools/loop-supervisor.sh` 闸 2 逐字按它的退出码
决定「落停机记录」还是「放行」。在此文件出现之前，它与写台账的 `pass_usage.py` 一样是
**零判据覆盖**——本仓仅有的两个 0%。

判据口径见 `docs/architecture/system-baseline.md` §14.9。

⚠️ 隔离是硬约束：任何一条断言都不得读真实的 `tools/gates/budget.json`、
不得写真实的 `_tmp/loop-usage.jsonl`。下面的 autouse fixture 负责这件事。
"""

import datetime
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_TOOL = ROOT / "tools/gates/check_budget.py"

# 判定器不是包的一部分（跑在 `tools/` 下，被监督器用相对路径调用），
# 所以按文件路径加载，不走 import 系统的包解析。与 test_gate_verdict.py 同法。
_spec = importlib.util.spec_from_file_location("check_budget", _TOOL)
budget = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(budget)


def point_config_at(monkeypatch, path: Path) -> None:
    """把「阈值配置文件」这个真相源指到 path。

    单点改写：本仓此刻是 cwd 相对的模块常量 `CONFIG`。各条断言正文只经过这个助手，
    所以真相源的解析方式换了，跟着改的只有这一处。
    """
    monkeypatch.setattr(budget, "CONFIG", path)


def point_ledger_at(monkeypatch, path: Path) -> None:
    monkeypatch.setattr(budget, "LEDGER", path)


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.delenv("AGENERP_DAILY_TOKEN_BUDGET", raising=False)
    point_config_at(monkeypatch, tmp_path / "no-such-budget.json")
    point_ledger_at(monkeypatch, tmp_path / "no-such-ledger.jsonl")


def rec(at: str, **kw) -> str:
    r = {"at": at, "label": "x", "sessions": 1, "input": 0, "output": 0, "msgs": 1}
    r.update(kw)
    return json.dumps(r, ensure_ascii=False)


def write_ledger(monkeypatch, tmp_path, *lines: str) -> Path:
    p = tmp_path / "loop-usage.jsonl"
    p.write_text("".join(line + "\n" for line in lines))
    point_ledger_at(monkeypatch, p)
    return p


def hours_ago(n: float) -> str:
    return (datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=n)).isoformat()


def run_main(monkeypatch, capsys, *argv: str):
    """跑 main() 并返回 (退出码, stdout, stderr)。退出码才是监督器看的那个东西。"""
    monkeypatch.setattr(sys, "argv", ["check_budget.py", *argv])
    code = budget.main()
    cap = capsys.readouterr()
    return code, cap.out, cap.err


# ---- configured_budget()：阈值的三档优先级 ----------------------------------

def test_env_var_wins_over_config_file(monkeypatch, tmp_path):
    cfg = tmp_path / "budget.json"
    cfg.write_text(json.dumps({"daily_token_budget": 999}))
    point_config_at(monkeypatch, cfg)
    monkeypatch.setenv("AGENERP_DAILY_TOKEN_BUDGET", "12345")
    assert budget.configured_budget() == 12345


def test_config_file_wins_over_builtin_default(monkeypatch, tmp_path):
    cfg = tmp_path / "budget.json"
    cfg.write_text(json.dumps({"daily_token_budget": 777_000}))
    point_config_at(monkeypatch, cfg)
    assert budget.configured_budget() == 777_000


def test_builtin_default_when_config_file_absent(monkeypatch, tmp_path):
    point_config_at(monkeypatch, tmp_path / "definitely-not-here.json")
    assert budget.configured_budget() == budget.DEFAULT_BUDGET


def test_unreadable_config_falls_back_to_builtin_default(monkeypatch, tmp_path):
    """现状：配置文件在、但解析不出 → 静默落到内置默认，没有任何提示。"""
    cfg = tmp_path / "budget.json"
    cfg.write_text("{ 这不是 json")
    point_config_at(monkeypatch, cfg)
    assert budget.configured_budget() == budget.DEFAULT_BUDGET


def test_non_numeric_env_var_silently_falls_through(monkeypatch, tmp_path):
    """现状：`isdigit()` 为假的环境变量被静默忽略，落到文件的值——比操作者意图更松。"""
    cfg = tmp_path / "budget.json"
    cfg.write_text(json.dumps({"daily_token_budget": 654_321}))
    point_config_at(monkeypatch, cfg)
    monkeypatch.setenv("AGENERP_DAILY_TOKEN_BUDGET", "200,000,000")
    assert budget.configured_budget() == 654_321


# ---- usage_since()：窗口、畸形行、五个累加口径 ------------------------------

def test_usage_since_returns_zeros_when_ledger_absent(monkeypatch, tmp_path):
    point_ledger_at(monkeypatch, tmp_path / "nope.jsonl")
    start = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=24)
    assert budget.usage_since(start) == {
        "input": 0, "output": 0, "msgs": 0, "passes": 0, "sessions": 0}


def test_usage_since_excludes_records_outside_the_window(monkeypatch, tmp_path):
    write_ledger(monkeypatch, tmp_path,
                 rec(hours_ago(25), input=1_000),
                 rec(hours_ago(1), input=7))
    start = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=24)
    tot = budget.usage_since(start)
    assert tot["passes"] == 1
    assert tot["input"] == 7


def test_usage_since_skips_malformed_json_line(monkeypatch, tmp_path):
    write_ledger(monkeypatch, tmp_path, "{ 半行坏数据", rec(hours_ago(1), input=5))
    start = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=24)
    assert budget.usage_since(start)["passes"] == 1


def test_usage_since_skips_record_without_at_key(monkeypatch, tmp_path):
    write_ledger(monkeypatch, tmp_path,
                 json.dumps({"label": "无 at 键", "input": 99}),
                 rec(hours_ago(1), input=5))
    start = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=24)
    tot = budget.usage_since(start)
    assert tot["passes"] == 1
    assert tot["input"] == 5


def test_usage_since_sums_five_counters(monkeypatch, tmp_path):
    write_ledger(monkeypatch, tmp_path,
                 rec(hours_ago(3), sessions=2, input=11, output=101, msgs=1001),
                 rec(hours_ago(2), sessions=3, input=22, output=202, msgs=2002))
    start = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=24)
    assert budget.usage_since(start) == {
        "passes": 2, "sessions": 5, "input": 33, "output": 303, "msgs": 3003}


# ---- main()：三个退出码就是监督器闸 2 的输入 --------------------------------

def test_main_returns_2_when_window_has_no_pass(monkeypatch, capsys, tmp_path):
    write_ledger(monkeypatch, tmp_path, rec(hours_ago(30), input=10))
    code, _, err = run_main(monkeypatch, capsys)
    assert code == 2
    assert "没有循环趟次记录" in err


def test_main_returns_0_when_within_budget(monkeypatch, capsys, tmp_path):
    write_ledger(monkeypatch, tmp_path, rec(hours_ago(1), input=100))
    code, out, _ = run_main(monkeypatch, capsys, "--budget-tokens", "1000")
    assert code == 0
    assert "预算" in out


def test_main_returns_1_and_says_over_budget(monkeypatch, capsys, tmp_path):
    """退出码给监督器看，这句话给人看。两者都得钉。"""
    write_ledger(monkeypatch, tmp_path, rec(hours_ago(1), input=1_000))
    code, _, err = run_main(monkeypatch, capsys, "--budget-tokens", "10")
    assert code == 1
    assert "超预算" in err
    assert "停机等人" in err


# ---- 两条现在就红的判据（Phase 2 修；D0 取 xfail(strict=True)）--------------

@pytest.mark.xfail(strict=True, reason="Baseline 3 确认的活缺陷：不带时区的 at 让闸崩成 exit 1，Phase 2 修")
def test_naive_timestamp_must_not_be_reported_as_over_budget(monkeypatch, capsys, tmp_path):
    """台账里一行 `at` 不带时区时，闸崩在 `usage_since` 的 `t < start`，未捕获，进程 exit 1。

    而 exit 1 在 `tools/loop-supervisor.sh` 里逐字是
    `halt_with "budget-exceeded" "24 小时内循环用量超出预算，停机等人复核"`——
    **停机记录会说「烧超了」，真相是判定器自己崩了**。退出码必须唯一对应一件事。
    """
    naive = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)) \
        .replace(tzinfo=None).isoformat()
    write_ledger(monkeypatch, tmp_path, rec(naive, input=100))
    code, _, _ = run_main(monkeypatch, capsys, "--budget-tokens", "1000")
    assert code == 0


@pytest.mark.xfail(strict=True, reason="判定器自身失败仍会冒充「超预算」，Phase 2 加顶层兜底")
def test_gate_internal_failure_must_not_be_reported_as_over_budget(monkeypatch, capsys, tmp_path):
    """通用契约，不依赖上一条那个具体输入：注入一个「归一时间戳」覆盖不到的异常。

    台账路径指向一个**目录** → `LEDGER.open()` 抛 `IsADirectoryError`。
    要求两件事：① 退出码不是 1（不冒充超预算）；② 异常原文出现在 stderr 上（不吞掉）。
    """
    d = tmp_path / "ledger-is-a-dir"
    d.mkdir()
    point_ledger_at(monkeypatch, d)
    code, _, err = run_main(monkeypatch, capsys)
    assert code != 1
    assert "IsADirectoryError" in err
