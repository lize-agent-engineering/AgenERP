"""P1.6 行业包 v0（离散制造）的判据 —— 判的是「**包在盘上、校验器判得动它**」。

判据全部落在结构化事实上（命中记录、命中数量、退出码、序列化后的声明），
一条都不落在自由文本上（plan §3 Non-Goal 7）。

⚠️ **本文件不判「行业包已接进 `rule.lookup`」** —— 它没接（plan §1.6 / Non-Goal 2）。
`agenerp/tools/queries.py` 的 `rule_lookup` 仍然指名报错，接线由人裁定。
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import inspection_fakes as fakes  # noqa: E402

from agenerp.explain.gate import DOC_NAME  # noqa: E402
from agenerp.inspection import RuleLoadError, load_rules  # noqa: E402
from agenerp.inspection.engine import check_test_cases, inspect_site, without  # noqa: E402
from agenerp.packs import (  # noqa: E402
    DISCRETE,
    PACK_FILE,
    PackLoadError,
    PackNotFound,
    load_pack,
    packs_root,
    validate_pack,
)
from agenerp.packs.__main__ import (  # noqa: E402
    EXIT_OK,
    EXIT_PACK_INVALID,
    EXIT_PACK_NOT_FOUND,
    EXIT_TEST_CASE_FAILED,
    main,
)
from agenerp.seed.checks import EXPECTED_BACKLOG_QTY, EXPECTED_SHORTFALL_QTY  # noqa: E402
from agenerp.seed.model import FINISHED_ITEM, WH_FINISHED  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE_PACKS = pathlib.Path(__file__).resolve().parent / "pack_fixtures"

RULE_BACKLOG = "discrete/finished-goods-backlog"
RULE_SUBCON = "discrete/subcontracting-issued-not-received"
RULE_SHORT_DELIVERED = "discrete/closed-order-short-delivered"

# 第二个数据集的期望积压量。**本文件写死的字面量**，不从构造常量算出来
# （`agenerp/seed/checks.py:18-20` 的同一条纪律）。
VARIANT_INHOUSE = 800
VARIANT_SUBCON = 600
VARIANT_DELIVERY = 500
VARIANT_EXPECTED_BACKLOG_QTY = 900.0


@pytest.fixture
def pack():
    return load_pack(DISCRETE)


def _raw_pack() -> dict:
    return json.loads((packs_root() / DISCRETE / PACK_FILE).read_text(encoding="utf-8"))


def _inspect(pack, site) -> object:
    return inspect_site(pack.rules, fakes.client_for(site), pack.pack_id)


def _quantities(report) -> dict[str, float]:
    return {hit.rule_id: hit.quantity for hit in report.hits}


def healthy_site() -> fakes.FakeSite:
    """**阴性对照**：三条规则各自要找的异常一个都没有的一份合成数据。

    产多少卖多少 · 关闭的订单发齐了 · 外协发出去的收回来了。
    它是 M4（「把某条规则的判据改成永远命中」）的杀手 ——
    消融判据对 M4 是绿的（抽掉规则本来就零命中），这一条不是。
    """
    return fakes.synthetic_site(
        {
            fakes.LEDGER: [
                {"name": "sle-1", "item_code": "cog", "warehouse": "wh-west",
                 "actual_qty": 320, "is_cancelled": 0},
                {"name": "sle-2", "item_code": "cog", "warehouse": "wh-west",
                 "actual_qty": -320, "is_cancelled": 0},
            ],
            fakes.ORDER_ITEM: [
                {"name": "soi-1", "item_code": "cog", "qty": 320,
                 "parent": "so-done", "delivered_qty": 320},
            ],
            "Sales Order": [
                {"name": "so-done", "status": "Closed", "total_qty": 320, "docstatus": 1},
            ],
            "Subcontracting Order": [
                {"name": "sco-done", "docstatus": 1},
            ],
            fakes.SUBCON_ORDER_ITEM: [
                {"name": "scoi-1", "parent": "sco-done", "qty": 180},
            ],
            fakes.SUBCON_RECEIPT_ITEM: [
                {"name": "scri-1", "subcontracting_order": "sco-done", "received_qty": 180},
            ],
        }
    )


# ── H5 不许照答案写规则：源声明与装载后**两侧都判** ──────────────────────────

FORBIDDEN_NUMBERS = ("1010", "2000", "990")


def _without_test_cases(payload: dict) -> str:
    """把 `test_case` 整块摘掉再判。**它是 H5 的显式例外**：合成行里本来就要写具体数据，
    `expect_quantity` 必然是由这些行算出来的数。例外只开给 `test_case`，判据表达一侧不开。"""
    stripped = json.loads(json.dumps(payload))
    for rule in stripped.get("rules", []):
        rule.pop("test_case", None)
    return json.dumps(stripped, ensure_ascii=False)


def _assert_clean(label: str, text: str) -> None:
    assert DOC_NAME.search(text) is None, f"{label} 里出现了单号字面量"
    for number in FORBIDDEN_NUMBERS:
        assert number not in text, f"{label} 里出现了固定测例的答案 {number}"
    assert FINISHED_ITEM not in text, f"{label} 里出现了夹具物料号"
    assert WH_FINISHED not in text, f"{label} 里出现了夹具仓库名"


def test_h5_the_pack_source_carries_no_document_number_and_no_answer(pack):
    """**源声明那一侧。** 只判装载后的形态不够：装载器丢弃未知键会让夹带的答案
    只在源码里可见（P1.5 的 M7 教训）。"""
    _assert_clean("行业包的源声明", _without_test_cases(_raw_pack()))


def test_h5_the_loaded_rules_carry_no_document_number_and_no_answer(pack):
    """**装载后那一侧。** 逐条对 `Rule.serialized()` 断言。"""
    for rule in pack.rules:
        payload = json.loads(rule.serialized())
        payload.pop("test_case", None)
        _assert_clean(f"规则 {rule.rule_id} 装载后的声明", json.dumps(payload, ensure_ascii=False))


def test_h5_the_test_case_rows_do_not_copy_the_fixed_dataset(pack):
    """`test_case` 是 H5 的例外，但**不许照抄固定测例的数** ——
    合成行自成一套，否则测例就变成把答案抄进包里。"""
    for rule in pack.rules:
        rows = json.dumps(rule.test_case.as_dict(), ensure_ascii=False)
        for number in FORBIDDEN_NUMBERS:
            assert number not in rows, f"{rule.rule_id} 的测例照抄了固定测例的 {number}"
        assert FINISHED_ITEM not in rows and WH_FINISHED not in rows


# ── H2 每条规则一对阳性 / 阴性对照 ──────────────────────────────────────────


def test_h2_positive_every_rule_hits_on_its_own_synthetic_rows(pack):
    """**阳性对照（每条都有）**：每条规则自带的 `test_case` 都真跑得过，且都是「期望命中」。

    外协那条在真实数据上**没有**阳性对照（种子的外协链是完整的，
    收发相等是正确行为），它的阳性对照就落在这里。
    """
    assert validate_pack(pack) == ()
    assert {rule.test_case.expect_hit for rule in pack.rules} == {True}
    assert {rule.rule_id for rule in pack.rules} == {
        RULE_BACKLOG,
        RULE_SUBCON,
        RULE_SHORT_DELIVERED,
    }


def test_h2_negative_no_rule_fires_on_healthy_data(pack):
    """**阴性对照（每条都有）**：三种异常一个都没有的数据上，三条规则**全部零命中**。

    这是 M4 的杀手：把任一条规则的判据改成永远命中，这里必红。
    """
    report = _inspect(pack, healthy_site())
    assert report.rule_ids == pack.rule_ids()
    assert report.hits == (), report.as_dict()


def test_h2_positive_the_backlog_rule_hits_the_fixed_dataset(pack):
    """R1 的阳性对照是**由 `agenerp/seed/` 派生的固定测例**，命中量取自期望侧常量。"""
    report = _inspect(pack, fakes.seed_site())
    quantities = _quantities(report)
    assert quantities[RULE_BACKLOG] == EXPECTED_BACKLOG_QTY
    hit = next(h for h in report.hits if h.rule_id == RULE_BACKLOG)
    assert dict(hit.subject) == {"item_code": FINISHED_ITEM, "warehouse": WH_FINISHED}
    assert dict(hit.measures)["received"] - dict(hit.measures)["issued"] == hit.quantity
    assert report.request_count > 0, "巡检必须真查过站点，不是凭空报"


def test_h2_the_backlog_quantity_moves_with_the_dataset(pack):
    """**第二个数据集**（M5 的杀手）：换掉三个构造参数，命中里的数必须跟着变。"""
    site = fakes.seed_site(
        inhouse=VARIANT_INHOUSE, subcon=VARIANT_SUBCON, delivery=VARIANT_DELIVERY
    )
    quantities = _quantities(_inspect(pack, site))
    assert quantities[RULE_BACKLOG] == VARIANT_EXPECTED_BACKLOG_QTY
    assert quantities[RULE_BACKLOG] != EXPECTED_BACKLOG_QTY


def test_h2_positive_the_short_delivered_rule_hits_the_fixed_dataset(pack):
    """R3 在固定测例上**有真实阳性对照**：订单被人工关闭、实发少于订单量，
    缺口取自 `agenerp/seed/checks.py` 的期望侧常量。"""
    quantities = _quantities(_inspect(pack, fakes.seed_site()))
    assert quantities[RULE_SHORT_DELIVERED] == EXPECTED_SHORTFALL_QTY


def test_h2_negative_the_subcontracting_rule_does_not_misfire_on_the_fixed_dataset(pack):
    """⚠️ **外协那条在固定测例上应当零命中，而那个零命中是正确行为**
    （种子的外协链是完整的：发出去多少收回来多少）。

    这里判的是**它不误报**，**不是**「它已在真实数据上验证过命中」——
    真实数据里根本没有那个异常。且零命中必须是**算出来的零**：
    委外量与收货量都得是非零的，否则「没数据」也会静静地绿。
    """
    site = fakes.seed_site()
    report = _inspect(pack, site)
    assert RULE_SUBCON not in _quantities(report)

    rule = next(r for r in pack.rules if r.rule_id == RULE_SUBCON)
    issued = sum(float(row["qty"]) for row in site.rows[fakes.SUBCON_ORDER_ITEM])
    received = sum(float(row["received_qty"]) for row in site.rows[fakes.SUBCON_RECEIPT_ITEM])
    assert issued > 0 and received > 0, "零命中必须是算出来的零，不是没数据"
    assert issued == received
    assert rule.trigger.measure == "outstanding"


def test_h2_ablation_is_kept_but_is_close_to_a_tautology(pack):
    """⚠️ **附带断言，不是发现力的证据。**

    `without()` + `run()` 的实现下这条**接近恒真**：规则没了自然没有它的命中。
    它证明的是「引擎读清单」，不证明「规则有判别力」。判别力由上面的
    阳性 / 阴性对照证明。
    """
    site = fakes.seed_site()
    client = fakes.client_for(site)
    for rule_id in (RULE_BACKLOG, RULE_SHORT_DELIVERED):
        ablated = without(pack.rules, rule_id)
        assert rule_id not in {r.rule_id for r in ablated}
        report = inspect_site(ablated, client, pack.pack_id)
        assert rule_id not in _quantities(report)


# ── H7 出处可回溯：`pack_id` 不是从 `rule_id` 里猜出来的 ─────────────────────


def test_h7_a_hit_names_the_pack_it_came_from(pack):
    report = _inspect(pack, fakes.seed_site())
    assert report.hits
    for hit in report.hits:
        assert hit.pack_id == DISCRETE
        assert hit.as_dict()["pack_id"] == DISCRETE


def test_h7_the_same_rule_under_two_packs_reports_two_different_origins(pack, tmp_path):
    """**同一条 `rule_id` 挂在两个 `pack_id` 下，两次命中的出处必须不同。**

    这是 M7 的杀手，也是否决「把 `pack_id` 编进 `rule_id` 前缀」那条备选的理由：
    出处与身份混成一个字符串时，这条判据根本构造不出来。
    """
    other_id = "other-pack"
    payload = _raw_pack()
    payload["pack_id"] = other_id
    written = tmp_path / other_id
    written.mkdir()
    (written / PACK_FILE).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    other = load_pack(other_id, tmp_path)
    assert other.rule_ids() == pack.rule_ids(), "两个包里是同一批 rule_id —— 判据的前提"

    site = fakes.seed_site()
    mine = _inspect(pack, site)
    theirs = _inspect(other, site)
    assert [h.rule_id for h in mine.hits] == [h.rule_id for h in theirs.hits]
    assert {h.pack_id for h in mine.hits} == {DISCRETE}
    assert {h.pack_id for h in theirs.hits} == {other_id}


def test_h7_the_engines_own_minimal_rules_claim_no_pack(pack):
    """引擎自带的最小规则集**不是行业包制品**，它报出来的命中出处是空的。
    `pack_id` 有默认值这件事不许被读成「随便哪条规则都算 discrete 的」。"""
    from agenerp.inspection import minimal_rules

    report = inspect_site(minimal_rules(), fakes.client_for(fakes.seed_site()))
    assert report.hits
    assert {hit.pack_id for hit in report.hits} == {""}


# ── H6 四种输入四种**可区分**的处置 ─────────────────────────────────────────
#
# 口径取 (i)：**不同退出码**，并且消息各自指名到具体对象。
# ⚠️ 只断言 `!= 0` 是不够的 —— 那样「查无此包」就成了同义反复。


def _cli(*argv: str) -> subprocess.CompletedProcess:
    """**子进程级**判据：跑真实命令行，判真实退出码。

    `gates.yml:559` 附近有一条实测教训 —— 只 import `main()` 的判据永远走不到
    `raise SystemExit(main())` 那两行，那是一条活的假绿路径。函数级判据在下面另写一套。
    """
    return subprocess.run(
        [sys.executable, "-m", "agenerp.packs", *argv],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_h6_the_four_outcomes_have_four_different_exit_codes():
    """四种输入四种退出码，且**互不相等**。"""
    codes = {
        "健康包": EXIT_OK,
        "查无此包": EXIT_PACK_NOT_FOUND,
        "缺 test_case": EXIT_PACK_INVALID,
        "测例跑不过": EXIT_TEST_CASE_FAILED,
    }
    assert len(set(codes.values())) == 4, codes
    assert 2 not in set(codes.values()), "2 留给 argparse 的用法错误，不许复用"


def test_h6_a_healthy_pack_exits_zero_and_names_every_rule():
    done = _cli("validate", "--pack", DISCRETE)
    assert done.returncode == EXIT_OK, done.stderr
    for rule_id in (RULE_BACKLOG, RULE_SUBCON, RULE_SHORT_DELIVERED):
        assert rule_id in done.stdout


def test_h6_a_missing_pack_exits_three_and_names_the_pack_argument():
    """④ `--pack` 拼错 / 包目录不存在。**「查无此包」被读成「校验通过」是最贵的假绿**（M3）。"""
    done = _cli("validate", "--pack", "discreet")
    assert done.returncode == EXIT_PACK_NOT_FOUND, done.stdout
    assert "discreet" in done.stderr
    assert str(packs_root()) in done.stderr
    assert DISCRETE in done.stderr, "消息要告诉人这个目录下现有哪些包"


def test_h6_a_missing_packs_dir_exits_three_too(tmp_path):
    done = _cli("validate", "--pack", DISCRETE, "--packs-dir", str(tmp_path / "nope"))
    assert done.returncode == EXIT_PACK_NOT_FOUND, done.stdout


def test_h6_a_rule_without_a_test_case_exits_four_and_names_the_rule():
    """② 某规则缺 `test_case` → 装载失败，**整份包一起拒载**（M2）。"""
    done = _cli(
        "validate", "--pack", "missing-test-case", "--packs-dir", str(FIXTURE_PACKS)
    )
    assert done.returncode == EXIT_PACK_INVALID, done.stdout
    assert "broken/no-test-case" in done.stderr
    assert "test_case" in done.stderr


def test_h6_a_failing_test_case_exits_five_and_names_expected_and_actual():
    """③ 某规则的 `test_case` 跑不过 → 与 ② 分得开，且消息带期望与实测。"""
    done = _cli(
        "validate", "--pack", "failing-test-case", "--packs-dir", str(FIXTURE_PACKS)
    )
    assert done.returncode == EXIT_TEST_CASE_FAILED, done.stdout
    assert "broken/quantity-does-not-add-up" in done.stderr
    assert "70" in done.stderr and "7.0" in done.stderr


def test_h6_the_function_level_entry_agrees_with_the_subprocess(capsys):
    """**函数级那一套**（快）。两种都写：子进程判得动 M8（退出码恒为 0），
    函数级对 M8 可能是绿的 —— 这正是不能只写一种的理由。"""
    assert main(["validate", "--pack", DISCRETE]) == EXIT_OK
    assert main(["validate", "--pack", "discreet"]) == EXIT_PACK_NOT_FOUND
    assert (
        main(["validate", "--pack", "missing-test-case", "--packs-dir", str(FIXTURE_PACKS)])
        == EXIT_PACK_INVALID
    )
    assert (
        main(["validate", "--pack", "failing-test-case", "--packs-dir", str(FIXTURE_PACKS)])
        == EXIT_TEST_CASE_FAILED
    )
    capsys.readouterr()


def test_the_loader_distinguishes_not_found_from_invalid():
    """装载面上这两件事也是两个异常类型 —— CLI 的两个退出码不是 CLI 自己编的。"""
    with pytest.raises(PackNotFound):
        load_pack("discreet")
    with pytest.raises(PackLoadError):
        load_pack("missing-test-case", FIXTURE_PACKS)
    assert not issubclass(PackNotFound, PackLoadError)


# ── H3 校验器**真的跑了** `test_case`，且**每一条**都跑了 ────────────────────
#
# ⚠️ 变异逐条各施加一次（含最后一条）：只变异第一条时，
# 一个「只校验第一条就返回」的假校验器是**绿**的。


def _derive(tmp_path, name: str, mutate) -> pathlib.Path:
    """从真包派生一个坏包写进 `tmp_path`。**不写进 `industry-packs/`** ——
    产品制品目录里不许躺着故意写坏的包。"""
    payload = _raw_pack()
    payload["pack_id"] = name
    mutate(payload)
    written = tmp_path / name
    written.mkdir()
    (written / PACK_FILE).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _rule_count() -> int:
    return len(_raw_pack()["rules"])


@pytest.mark.parametrize("index", range(3))
def test_h3_flipping_expect_hit_on_any_rule_makes_validate_fail(tmp_path, index):
    """把**第 index 条**规则的 `test_case.expect_hit` 由 `true` 翻成 `false`
    （规则本身一个字不动）→ `validate` 必须非零退出，且指名到那条规则。

    这是 M1 的杀手：只检查 `test_case` 这个键存在的假校验器在这个变异上是绿的。
    """
    assert index < _rule_count()
    rule_id = _raw_pack()["rules"][index]["rule_id"]
    name = f"flipped-{index}"

    def mutate(payload):
        payload["rules"][index]["test_case"]["expect_hit"] = False
        payload["rules"][index]["test_case"].pop("expect_quantity", None)

    root = _derive(tmp_path, name, mutate)
    done = _cli("validate", "--pack", name, "--packs-dir", str(root))
    assert done.returncode == EXIT_TEST_CASE_FAILED, done.stdout
    assert rule_id in done.stderr


@pytest.mark.parametrize("index", range(3))
def test_h3_stripping_the_test_case_from_any_rule_makes_validate_fail(tmp_path, index):
    """同一条纪律适用于 H6 ② 的「缺 `test_case`」变异：**逐条各来一次，含最后一条**。"""
    assert index < _rule_count()
    rule_id = _raw_pack()["rules"][index]["rule_id"]
    name = f"stripped-{index}"

    root = _derive(tmp_path, name, lambda p: p["rules"][index].pop("test_case"))
    done = _cli("validate", "--pack", name, "--packs-dir", str(root))
    assert done.returncode == EXIT_PACK_INVALID, done.stdout
    assert rule_id in done.stderr


def test_h3_the_number_of_rules_is_what_the_per_rule_sweep_assumes():
    """上面两条的 `range(3)` 与包里的规则条数必须对得上 ——
    包里加了第四条规则而扫描没跟着加时，「含最后一条」这句话就悄悄失效了。"""
    assert _rule_count() == 3


def test_the_validator_really_runs_every_test_case_not_just_the_first(pack):
    """装载面上的同一件事：`check_test_cases` 逐条跑，返回的失败清单能指到任意一条。"""
    assert check_test_cases(pack.rules) == ()
    broken = _raw_pack()
    broken["rules"][-1]["test_case"]["expect_quantity"] = 1.0
    failures = check_test_cases(load_rules(broken["rules"]))
    assert len(failures) == 1
    assert failures[0].rule_id == broken["rules"][-1]["rule_id"]


# ── D3 新增算子的**拒载判据**（新增算子必须同时交付求值判据与拒载判据） ──────


def _row_filter_rule(entry: dict) -> list[dict]:
    return [
        {
            "rule_id": "probe/row-filter",
            "statement": "行过滤算子的拒载探针",
            "doctype": "Sales Order",
            "group_by": ["name"],
            "exclude": [entry],
            "measures": [{"name": "ordered", "operator": "sum_positive", "field": "total_qty"}],
            "trigger": {"measure": "ordered", "operator": "greater_than", "value": 0},
            "quantity": "ordered",
            "test_case": {
                "name": "探针",
                "rows": {"Sales Order": [{"name": "so-x", "status": "Closed", "total_qty": 4}]},
                "expect_hit": True,
                "expect_quantity": 4,
            },
        }
    ]


def test_d3_an_unknown_row_filter_operator_is_refused():
    with pytest.raises(RuleLoadError, match="有限算子集"):
        load_rules(_row_filter_rule({"field": "status", "operator": "matches_regex"}))


def test_d3_equals_without_a_literal_is_refused():
    """`equals` / `not_equals` **要**一个字面量。缺了就拒载，不许当成 no-op。"""
    for operator in ("equals", "not_equals"):
        with pytest.raises(RuleLoadError, match="需要一个字面量"):
            load_rules(_row_filter_rule({"field": "status", "operator": operator}))


def test_d3_truthy_with_a_literal_is_refused():
    """反过来：`truthy` / `falsy` **不接受** `value`。

    少了这条，`{"field": "docstatus", "operator": "truthy", "value": 2}` 会被读成
    「排除 docstatus == 2」，而它实际排掉的是所有非零 docstatus —— 静默放宽。
    """
    for operator in ("truthy", "falsy"):
        with pytest.raises(RuleLoadError, match="不接受"):
            load_rules(
                _row_filter_rule({"field": "status", "operator": operator, "value": "Closed"})
            )


def test_d3_a_non_scalar_literal_is_refused():
    for value in ({"a": 1}, ["a"], True):
        with pytest.raises(RuleLoadError, match="必须是字符串或数字"):
            load_rules(
                _row_filter_rule({"field": "status", "operator": "equals", "value": value})
            )


def test_d3_equals_compares_numbers_as_numbers_and_text_as_text(pack):
    """求值判据。站点 REST 面回来的 `docstatus` 可能是 `1` 也可能是 `"1"` ——
    按字符串硬比会让作废单**排不掉**，那正是外协那条会误报的方式。"""
    rule = next(r for r in pack.rules if r.rule_id == RULE_SUBCON)
    site = fakes.synthetic_site(
        {
            "Subcontracting Order": [
                {"name": "sco-void", "docstatus": "2"},
                {"name": "sco-live", "docstatus": "1"},
            ],
            fakes.SUBCON_ORDER_ITEM: [
                {"name": "i-1", "parent": "sco-void", "qty": 900},
                {"name": "i-2", "parent": "sco-live", "qty": 60},
            ],
            fakes.SUBCON_RECEIPT_ITEM: [],
        }
    )
    report = inspect_site([rule], fakes.client_for(site), pack.pack_id)
    assert [dict(hit.subject) for hit in report.hits] == [{"name": "sco-live"}]
    assert report.hits[0].quantity == 60


# ── 包这一层的形状：未知顶层键 / 空 rules / pack_id 与目录名对不上 ──────────


@pytest.mark.parametrize(
    ("label", "mutate", "match"),
    [
        ("未知顶层键", lambda p: p.update({"thresholds": {}}), "不认识的顶层键"),
        ("空 rules", lambda p: p.update({"rules": []}), "`rules` 缺失或为空"),
        ("pack_id 与目录名对不上", lambda p: p.update({"pack_id": "somewhere-else"}), "对不上"),
    ],
)
def test_the_pack_loader_refuses_a_pack_that_is_not_the_declared_shape(
    tmp_path, label, mutate, match
):
    payload = _raw_pack()
    payload["pack_id"] = "probe"
    mutate(payload)
    written = tmp_path / "probe"
    written.mkdir()
    (written / PACK_FILE).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(PackLoadError, match=match):
        load_pack("probe", tmp_path)


def test_the_pack_is_diffable_and_declares_what_it_needs(pack):
    """北极星：包是**可 diff 的产物**。两次装载序列化字节相同，
    且它逐字声明了自己要站点上有哪些 DocType。"""
    first = [rule.serialized() for rule in load_pack(DISCRETE).rules]
    second = [rule.serialized() for rule in load_pack(DISCRETE).rules]
    assert first == second
    for rule in pack.rules:
        assert rule.doctype in pack.requires_doctypes
    assert "Subcontracting Order Item" in pack.requires_doctypes


def test_the_pack_only_reads(pack):
    """②端只读：整份包跑一遍，假站点上一条写请求都没有。"""
    site = fakes.seed_site()
    _inspect(pack, site)
    assert {request.method for request in site.requests} == {"GET"}
