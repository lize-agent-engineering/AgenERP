"""种子数据集的判据第二只脚：确定性、种子敏感性、场景断言、负例、纯净性。

WBS 的验收命令 `python3 -m agenerp.seed --seed 42 --verify` 不在
`missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到它；
**本文件是复跑得到的那一半**（`python3 -m pytest tests/unit -q` 在 `commands.test` 里）。
"""

from __future__ import annotations

import uuid  # MUTATION-A: 故意的 F401，实验后必须 revert

import copy
import json
import re
from pathlib import Path

import pytest

from agenerp.seed import SCOPE, generate, read, to_snapshot, verify, write
from agenerp.seed.__main__ import main
from agenerp.snapshot import diff

REPO_ROOT = Path(__file__).resolve().parents[2]

# 生成器的源码文件：`seed*.py` 与 `seed/*.py` 的**并集**。
# 写死 `agenerp/seed.py` 会在拆包后静默扫了个空，「无违规」就成了空真。
GENERATOR_SOURCES = sorted(
    set((REPO_ROOT / "agenerp").glob("seed*.py")) | set((REPO_ROOT / "agenerp" / "seed").glob("*.py"))
)

# 确定性的头号杀手。出现在生成路径上即红。
FORBIDDEN_SYMBOLS = ("datetime.now", "time.time", "os.environ", "random.random(")


# ── 确定性 ───────────────────────────────────────────────────────────
def test_same_seed_generates_equal_datasets():
    assert generate(42) == generate(42)


def test_same_seed_diffs_empty_through_the_shared_differ():
    """判「两次一不一样」用的是已通过门禁的 `snapshot.diff`，本仓不写第二个比较器。"""
    delta = diff(to_snapshot(generate(42)), to_snapshot(generate(42)))
    assert delta.is_empty(), delta.summary()


def test_two_writes_are_byte_identical(tmp_path):
    """对象相等还不够——序列化层也可能引入不确定性，这里比的是**字节**。"""
    first, second = tmp_path / "a", tmp_path / "b"
    write(generate(42), first)
    write(generate(42), second)
    names = sorted(p.name for p in (first / SCOPE).iterdir())
    assert names == sorted(p.name for p in (second / SCOPE).iterdir())
    for name in names:
        assert (first / SCOPE / name).read_bytes() == (second / SCOPE / name).read_bytes(), name


def test_written_json_is_utf8_without_bom_and_sorted(tmp_path):
    write(generate(42), tmp_path)
    payload = (tmp_path / SCOPE / "Bin.json").read_bytes()
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert payload.endswith(b"\n")
    text = payload.decode("utf-8")
    parsed = json.loads(text)
    assert text == json.dumps(parsed, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def test_roundtrip_through_disk_preserves_the_dataset(tmp_path):
    original = generate(42)
    write(original, tmp_path)
    assert diff(to_snapshot(original), to_snapshot(read(tmp_path))).is_empty()


# ── 种子敏感性 ────────────────────────────────────────────────────────
def test_different_seeds_differ_only_in_decorative_fields():
    """定稿保留了受控 RNG，所以 `--seed` 是真参数：产物不同，但断言项完全一致。"""
    assert generate(42) != generate(43)
    delta = diff(to_snapshot(generate(42)), to_snapshot(generate(43)))
    assert not delta.is_empty()
    assert not delta.added and not delta.removed, "不同 seed 不该增删单据，只该改装饰性字段"
    assert {entry.doctype for entry in delta.changed} == {"Stock Entry"}
    assert verify(generate(43)) == []


def test_help_text_describes_seed_as_a_real_parameter(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    text = capsys.readouterr().out
    assert "装饰性字段" in text
    assert "全部断言项完全一致" in text


# ── 场景断言：逐条覆盖 verify() 的每一项 ──────────────────────────────
def test_verify_passes_on_the_generated_dataset():
    assert verify(generate(42)) == []


def test_receipts_total_two_thousand_metres():
    dataset = generate(42)
    received = sum(
        float(row["actual_qty"])
        for row in dataset.of("Stock Ledger Entry")
        if row["item_code"] == "XM-LACE-1000" and row["actual_qty"] > 0
    )
    assert received == 2000.0


def test_delivery_is_nine_hundred_ninety_metres():
    dataset = generate(42)
    note = dataset.of("Delivery Note")[0]
    assert note["items"][0]["qty"] == 990


def test_finished_bin_holds_the_backlog():
    """1,010 米 / ¥6,450 —— 这个数据集存在的理由。"""
    dataset = generate(42)
    bin_row = next(
        row
        for row in dataset.of("Bin")
        if row["item_code"] == "XM-LACE-1000" and row["warehouse"] == "XM 成品仓 - XM"
    )
    assert bin_row["actual_qty"] == 1010.0
    assert bin_row["stock_value"] == 6450.0


def test_backlog_value_is_fifo_layered_not_moving_average():
    """FIFO 分层：10 × ¥5.00 + 1,000 × ¥6.40。移动加权均价口径应得 ¥5,757，不是 ¥6,450。"""
    assert 10 * 5.00 + 1000 * 6.40 == 6450.0
    assert (5000.0 + 6400.0) / 2000 * 1010 == pytest.approx(5757.0)


def test_approved_loss_review_exists_and_is_approved():
    review = generate(42).of("Loss Review")[0]
    assert review["name"] == "LOSS-00003"
    assert review["approved_loss_quantity"] == 10
    assert review["status"] == "Approved"


def test_overdue_pair_matches_spike_08():
    dataset = generate(42)
    assert dataset.of("Sales Invoice")[0]["outstanding_amount"] == pytest.approx(18612.0)
    assert dataset.of("Purchase Invoice")[0]["outstanding_amount"] == pytest.approx(2200.0)
    for row in dataset.of("Sales Invoice") + dataset.of("Purchase Invoice"):
        assert row["status"] == "Overdue"
        assert row["due_date"] < dataset.as_of, "逾期必须由 as_of 与 due_date 判出，不是硬贴一个状态"


def test_books_are_all_green():
    """账面四项**必须全绿**——荒谬藏在没有任何字段发红的地方。"""
    dataset = generate(42)
    debit = sum(float(row["debit"]) for row in dataset.of("GL Entry"))
    credit = sum(float(row["credit"]) for row in dataset.of("GL Entry"))
    assert debit == pytest.approx(credit), "GL 借贷必须平"
    assert all(float(row["actual_qty"]) >= 0 for row in dataset.of("Bin")), "负库存必须为 0"
    assert all(
        float(row["qty_after_transaction"]) >= 0 for row in dataset.of("Stock Ledger Entry")
    )
    revenue = sum(
        float(r["credit"]) for r in dataset.of("GL Entry") if "主营业务收入" in r["account"]
    )
    cogs = sum(float(r["debit"]) for r in dataset.of("GL Entry") if "主营业务成本" in r["account"])
    assert revenue - cogs == pytest.approx(13662.0, abs=0.01)
    order_item = dataset.of("Sales Order")[0]["items"][0]
    review = dataset.of("Loss Review")[0]
    settled = order_item["delivered_qty"] + review["approved_loss_quantity"]
    assert settled / order_item["qty"] * 100 == pytest.approx(100.0), "达成率必须是 100%"


# ── 负例：篡改后 verify() 必须报出、且能定位 ─────────────────────────
def _tampered(doctype: str, mutate) -> object:
    dataset = generate(42)
    rows = [copy.deepcopy(dict(row)) for row in dataset.of(doctype)]
    mutate(rows)
    records = dict(dataset.records)
    records[doctype] = tuple(rows)
    return type(dataset)(seed=dataset.seed, as_of=dataset.as_of, records=records)


@pytest.mark.parametrize(
    ("doctype", "mutate", "marker"),
    [
        ("Bin", lambda rows: rows.__setitem__(
            next(i for i, r in enumerate(rows) if r["warehouse"] == "XM 成品仓 - XM"),
            {**next(r for r in rows if r["warehouse"] == "XM 成品仓 - XM"), "actual_qty": 900.0},
        ), "成品仓结余"),
        ("Loss Review", lambda rows: rows[0].__setitem__("status", "Draft"), "LOSS-00003 的状态"),
        ("Loss Review", lambda rows: rows[0].__setitem__("approved_loss_quantity", 0),
         "已审批损耗"),
        ("Sales Invoice", lambda rows: rows[0].__setitem__("outstanding_amount", 1.0),
         "应收逾期合计"),
        ("Purchase Invoice", lambda rows: rows[0].__setitem__("outstanding_amount", 9.0),
         "应付逾期合计"),
        ("GL Entry", lambda rows: rows[0].__setitem__("debit", rows[0]["debit"] + 1),
         "GL 借贷不平"),
    ],
)
def test_verify_reports_a_locatable_reason_when_tampered(doctype, mutate, marker):
    failures = verify(_tampered(doctype, mutate))
    assert failures, f"篡改 {doctype} 后 verify() 仍返回空——判据没有牙齿"
    assert any(marker in reason for reason in failures), failures


def test_negative_stock_is_reported():
    tampered = _tampered("Bin", lambda rows: rows[0].__setitem__("actual_qty", -1.0))
    assert any("负库存" in reason for reason in verify(tampered))


def test_cli_returns_one_and_names_the_failure(capsys, monkeypatch):
    monkeypatch.setattr("agenerp.seed.__main__.verify", lambda dataset: ["伪造的失败原因"])
    assert main(["--seed", "42", "--verify"]) == 1
    assert "伪造的失败原因" in capsys.readouterr().err


def test_cli_returns_zero_on_the_real_dataset(capsys):
    assert main(["--seed", "42", "--verify"]) == 0
    assert "两次生成 diff 为空" in capsys.readouterr().out


def test_cli_without_verify_writes_and_returns_zero(tmp_path, capsys):
    assert main(["--seed", "42", "--out", str(tmp_path)]) == 0
    capsys.readouterr()
    assert (tmp_path / SCOPE / "Bin.json").is_file()


# ── 纯净性：把「确定性」从口头承诺变成可执行断言 ──────────────────────
def test_generator_sources_were_actually_found():
    """否则「扫描无违规」是空真——拆包后写死路径会静默扫了个空。"""
    assert len(GENERATOR_SOURCES) >= 1
    assert any(path.name == "dataset.py" for path in GENERATOR_SOURCES)


@pytest.mark.parametrize("symbol", FORBIDDEN_SYMBOLS)
def test_generator_sources_are_free_of_nondeterminism(symbol):
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in GENERATOR_SOURCES
        if symbol in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"{symbol} 出现在生成路径上：{offenders}"


def test_generator_sources_do_not_use_unstable_random_helpers():
    """`shuffle` / `sample` 的实现细节在 CPython 历史上变过，不许出现在生成路径上。"""
    pattern = re.compile(r"\.(shuffle|sample)\s*\(")
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in GENERATOR_SOURCES
        if pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders
