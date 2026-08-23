"""非门禁测试 · 把「按趟计量」的写入端 `tools/gates/pass_usage.py` 钉住。

它与 `tools/gates/check_budget.py` 是一条链：`measure` 写台账 `_tmp/loop-usage.jsonl`，
停机闸读同一份台账。写错了，闸就判错了——而在此文件出现之前这条链两端都是 0% 覆盖。

判据口径见 `docs/architecture/system-baseline.md` §14.9。

⚠️ 隔离是硬约束：不得读真实的 `~/.claude/projects/**`，不得写真实的台账。
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_TOOL = ROOT / "tools/gates/pass_usage.py"

_spec = importlib.util.spec_from_file_location("pass_usage", _TOOL)
pu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pu)

# 下面的 autouse fixture 会把 sessions_dir 指到 tmp_path；
# 「拼法本身」那条断言要测的是真函数，所以在这里先留一份原件。
_REAL_SESSIONS_DIR = pu.sessions_dir


@pytest.fixture
def sessions(tmp_path, monkeypatch):
    d = tmp_path / "sessions"
    d.mkdir()
    monkeypatch.setattr(pu, "sessions_dir", lambda: d)
    return d


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(pu, "sessions_dir", lambda: tmp_path / "no-such-sessions")
    monkeypatch.setattr(pu, "LEDGER", tmp_path / "ledger" / "loop-usage.jsonl")


def assistant(**usage) -> str:
    return json.dumps({"type": "assistant", "message": {"usage": usage}})


def run_main(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["pass_usage.py", *argv])
    return pu.main()


def ledger_rows() -> list[dict]:
    return [json.loads(line) for line in pu.LEDGER.read_text().splitlines() if line]


def test_sessions_dir_is_derived_from_cwd(tmp_path, monkeypatch):
    home = tmp_path / "home"
    work = tmp_path / "work"
    home.mkdir()
    work.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(work)
    slug = str(work.resolve()).replace("/", "-")
    assert _REAL_SESSIONS_DIR() == home / ".claude/projects" / slug


def test_current_files_is_empty_when_sessions_dir_absent():
    assert pu.current_files() == set()


def test_current_files_lists_only_jsonl(sessions):
    (sessions / "a.jsonl").write_text("")
    (sessions / "b.jsonl").write_text("")
    (sessions / "notes.txt").write_text("")
    assert pu.current_files() == {"a.jsonl", "b.jsonl"}


# ---- sum_usage()：台账里那两个数字的算法 ------------------------------------

def test_sum_usage_input_is_the_three_token_fields_summed(sessions):
    """三个字段取**三个互不相同的非零值**——取 0 或取相等值会让「删掉一项」算出同一个和。"""
    (sessions / "s.jsonl").write_text(assistant(
        input_tokens=101, cache_creation_input_tokens=2003,
        cache_read_input_tokens=30007, output_tokens=41) + "\n")
    assert pu.sum_usage({"s.jsonl"}) == {"input": 32111, "output": 41, "msgs": 1}


def test_sum_usage_counts_only_assistant_messages(sessions):
    (sessions / "s.jsonl").write_text(
        json.dumps({"type": "user", "message": {"usage": {"input_tokens": 500}}}) + "\n"
        + assistant(input_tokens=7, output_tokens=3) + "\n")
    assert pu.sum_usage({"s.jsonl"}) == {"input": 7, "output": 3, "msgs": 1}


def test_sum_usage_skips_messages_without_usage(sessions):
    (sessions / "s.jsonl").write_text(
        json.dumps({"type": "assistant", "message": {}}) + "\n"
        + assistant(input_tokens=7, output_tokens=3) + "\n")
    assert pu.sum_usage({"s.jsonl"})["msgs"] == 1


def test_sum_usage_skips_malformed_lines(sessions):
    (sessions / "s.jsonl").write_text(
        "{ 半行坏数据\n" + assistant(input_tokens=7, output_tokens=3) + "\n")
    assert pu.sum_usage({"s.jsonl"}) == {"input": 7, "output": 3, "msgs": 1}


def test_sum_usage_ignores_names_that_are_not_files(sessions):
    assert pu.sum_usage({"gone.jsonl"}) == {"input": 0, "output": 0, "msgs": 0}


# ---- snapshot → measure：差分语义与台账是追加 -------------------------------

def test_measure_records_only_sessions_that_appeared_after_snapshot(
        tmp_path, monkeypatch, sessions, capsys):
    (sessions / "old.jsonl").write_text(assistant(input_tokens=900, output_tokens=9) + "\n")
    snap = tmp_path / "snap.txt"
    assert run_main(monkeypatch, "snapshot", str(snap)) == 0

    (sessions / "new.jsonl").write_text(assistant(input_tokens=11, output_tokens=2) + "\n")
    assert run_main(monkeypatch, "measure", str(snap), "--label", "p0") == 0
    capsys.readouterr()

    rows = ledger_rows()
    assert len(rows) == 1
    assert rows[0]["sessions"] == 1
    assert rows[0]["input"] == 11
    assert rows[0]["label"] == "p0"


def test_measure_appends_and_does_not_overwrite(tmp_path, monkeypatch, sessions, capsys):
    snap = tmp_path / "snap.txt"
    run_main(monkeypatch, "snapshot", str(snap))
    (sessions / "a.jsonl").write_text(assistant(input_tokens=11, output_tokens=1) + "\n")
    run_main(monkeypatch, "measure", str(snap), "--label", "one")

    run_main(monkeypatch, "snapshot", str(snap))
    (sessions / "b.jsonl").write_text(assistant(input_tokens=22, output_tokens=2) + "\n")
    run_main(monkeypatch, "measure", str(snap), "--label", "two")
    capsys.readouterr()

    rows = ledger_rows()
    assert [r["label"] for r in rows] == ["one", "two"]
    assert [r["input"] for r in rows] == [11, 22]


def test_measure_without_snapshot_counts_every_session_as_this_pass(
        tmp_path, monkeypatch, sessions, capsys):
    """Baseline 8 的现状：快照缺失 → `before` 空 → 全部历史会话被记成「本趟」。

    本文件**只钉现状、不改行为**；裁定见 plan 的 `## Deferred But Adjudicated` 同名条目
    （产品路径上 snapshot 恒先于 measure，且真撞上时方向是「停」不是「放行」）。
    """
    (sessions / "old1.jsonl").write_text(assistant(input_tokens=100, output_tokens=1) + "\n")
    (sessions / "old2.jsonl").write_text(assistant(input_tokens=200, output_tokens=2) + "\n")
    assert run_main(monkeypatch, "measure", str(tmp_path / "never-taken.txt")) == 0
    capsys.readouterr()

    rows = ledger_rows()
    assert rows[0]["sessions"] == 2
    assert rows[0]["input"] == 300
