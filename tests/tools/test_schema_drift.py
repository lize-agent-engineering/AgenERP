"""🔴 P2.5 · 孤儿列巡检的工具面判据。`02-WBS.md` §5 第 105 行那条验收命令打的就是本文件。

    python3 -m pytest tests/tools/test_schema_drift.py -q

**离线**：带外执行器喂假件，不连站点、不打网络。

## 本文件验什么、不验什么

**验**：工具面 —— 契约挂上了 · 两个入口的取舍 · 返回形状 · **不进模型工具面**。

⚠️ **不验**口径本身（「哪些列算孤儿」）。那是 `agenerp/snapshot.py:schema_drift()` 的活，
判据在 `tests/unit/test_schema_drift.py`（`dry_run` 钉死 True · 调用方塞不进 `False` ·
白名单外一律拒）。本文件**不重验一遍** —— 两处验同一件事就会有两套口径。
"""

from __future__ import annotations

from agenerp.contracts import ReadOnlyContext
from agenerp.oob import OobResult
from agenerp.tools.registry import EXECUTORS
from agenerp.tools_readonly import ALL_CONTRACTS, INSPECTION_CONTRACTS, READONLY_CONTRACTS
from agenerp.tools_readonly import get as contract_of

TOOL = "schema.drift"
EMPTY = ReadOnlyContext({})


def runner_for(mapping: dict[str, list[str]]):
    """假的带外执行器：按命令文本里出现的 DocType 名回该表的孤儿列。"""

    def _run(command) -> OobResult:
        # `OobCommand` 是**可检视的值对象**（`service` + `argv`）——
        # 假件按 argv 里出现的 DocType 名回该表的孤儿列。
        text = " ".join(command.argv)
        for doctype, columns in mapping.items():
            if doctype in text:
                import json

                return OobResult(0, json.dumps(columns), "")
        # 退出码 0 且 stdout 全空 = 「没有孤儿列」这个**合法结论**在这条通道上的形状
        # （`agenerp/oob.py` 模块头第 1 条）。这里回 `[]` 走同一条路。
        return OobResult(0, "[]", "")

    return _run


class FakeClient:
    """只需要一个站点名 —— 巡检走带外通道，不打 REST 面。"""

    site = "gitops.test"


def run(params: dict, mapping: dict[str, list[str]] | None = None, client=None):
    from agenerp.tools.runtime import execute

    return execute(
        TOOL, params,
        client=FakeClient() if client is None else client,
        context=EMPTY,
        runner=runner_for(mapping or {}),
    )


# ── 契约挂上了 ──────────────────────────────────────────────────────────────


def test_the_tool_has_a_contract_and_an_executor():
    """少一边就是一个静默缺口 —— 与 `test_registry_pairing.py` 同一条理由。"""
    assert contract_of(TOOL).tool == TOOL
    assert TOOL in EXECUTORS


def test_the_contract_is_not_one_of_the_ten_read_only_tools():
    """🔴 **它在自己的契约族里，不在那十个模型面工具里。**

    `tests/tools/test_live_conformance.py` 是**门禁断言体**（红线①内），
    它逐条验的正是那十个；`tests/contracts/test_readonly_registry.py` 也写死 `== 10`。
    塞进去要动红线，而且在设计上也不对 —— 见下一条。
    """
    assert len(READONLY_CONTRACTS) == 10
    assert TOOL not in {c.tool for c in READONLY_CONTRACTS}
    assert TOOL in {c.tool for c in INSPECTION_CONTRACTS}
    assert contract_of(TOOL) in ALL_CONTRACTS


def test_it_is_not_on_the_model_facing_tool_surface():
    """🔴 D-15：巡检是**规则面**，不 Agent 化（P1.5 的巡检器就是零 LLM 调用的纯规则引擎）。

    ⚠️ 这一条**由构造保证**，不靠排除表：`tool_schemas()` 按 `READONLY_CONTRACTS` 生成，
    而本工具不在那里面。靠 `EXCLUDED_TOOLS` 排除是让机制和意图打架 —— 排除表漏一行就漏出去了。
    """
    from agenerp.explain.loop import tool_schemas

    offered = {schema["function"]["name"] for schema in tool_schemas()}
    assert "schema_drift" not in offered


# ── 两个入口，二选一 ────────────────────────────────────────────────────────


def test_a_single_doctype_reports_its_orphan_columns():
    result = run({"doctype": "ToDo"}, {"ToDo": ["stale_col", "another"]})

    assert result.ok, result.reasons
    assert result.data["rows"] == [
        {"doctype": "ToDo", "column": "another"},
        {"doctype": "ToDo", "column": "stale_col"},
    ], result.data


def test_rows_carry_the_doctype_not_just_the_column_name():
    """裸列名在批量模式下说不清是哪张表的 —— `must_keep` 因此含 `doctype`。"""
    assert set(contract_of(TOOL).returns.must_keep) == {"doctype", "column"}


def test_a_clean_doctype_reports_zero_rows_and_that_is_a_conclusion():
    """🔴 「没有孤儿列」是**合法结论**，不是「查不动」。

    两者长得一样的话，带外调用坏掉会被读成「干净」—— 那正是最难发现的假绿。
    查不动由 `OobError` 表达（口径判据在 `tests/unit/test_schema_drift.py`）。
    """
    result = run({"doctype": "ToDo"}, {})

    assert result.ok
    assert result.data["rows"] == []
    assert result.data["scanned"] == ["ToDo"], "扫了哪些表要说出来，否则「零行」没有分母"


def test_neither_entry_given_is_refused():
    """**都不给一律拒**，不许悄悄退化成「扫全站」——那是既慢又没人负责的口径。"""
    result = run({})

    assert not result.ok
    assert any("doctype" in reason and "pack" in reason for reason in result.reasons), result.reasons


def test_both_entries_given_is_refused():
    """都给也拒：两个范围哪个说了算，调用方自己都没想清楚。"""
    result = run({"doctype": "ToDo", "pack": "/tmp/whatever"})

    assert not result.ok


def test_a_pack_scans_exactly_the_doctypes_the_pack_governs(tmp_path):
    """批量的范围由**包**定 —— 与 P2.4「包是唯一真相源」同一条线。"""
    from agenerp.apply import PACK_SCOPE
    from agenerp.pack import render_doctype_file

    scope = tmp_path / PACK_SCOPE
    scope.mkdir(parents=True)
    (scope / "ToDo.json").write_text(
        render_doctype_file("ToDo", [{"fieldname": "x", "fieldtype": "Data"}]), encoding="utf-8"
    )
    (scope / "Note.json").write_text(
        render_doctype_file("Note", [{"fieldname": "y", "fieldtype": "Data"}]), encoding="utf-8"
    )

    result = run({"pack": str(tmp_path)}, {"Note": ["orphan_note_col"]})

    assert result.ok, result.reasons
    assert result.data["scanned"] == ["Note", "ToDo"], result.data
    assert result.data["rows"] == [{"doctype": "Note", "column": "orphan_note_col"}]


def test_a_pack_that_governs_nothing_is_refused_not_reported_as_clean(tmp_path):
    """🔴 空包扫出零行，与「这个包一张表都不管」**不是一回事**。

    后者是调用方给错了路径。合并成「干净」会让一个打错的路径看起来像体检通过。
    """
    result = run({"pack": str(tmp_path)})

    assert not result.ok
    assert any("一张表都不管" in reason or "管辖" in reason for reason in result.reasons)


def test_without_a_site_it_refuses_instead_of_guessing_from_the_environment():
    """🔴 站点名**不许靠环境变量猜**。

    巡检报的是**哪个站点**的孤儿列；回落到 `AGENERP_SITE` 会让「调用方指的站点」
    与「环境里配的站点」在不一致时静默按后者跑 —— 那种错在结果上看不出来。
    """
    class _NoSite:
        site = ""

    result = run({"doctype": "ToDo"}, {}, client=_NoSite())

    assert not result.ok
    assert any("站点" in reason for reason in result.reasons), result.reasons


def test_it_sends_no_rest_request_at_all():
    """🔴 「只报不删」在**传输面**的可观测形态：一个 REST 请求都没发。

    ⚠️ 这一条比后置事实硬：后置是执行体自己报的（虽然从行为推出来），
    而这一条数的是 `session.request_count` —— **被测代码改不动的那个计数**。
    删 Custom Field 走 REST，会在这里留下痕迹。
    """
    result = run({"doctype": "ToDo"}, {"ToDo": ["stale_col"]})

    assert result.ok
    assert result.request_count == 0, "巡检发了 REST 请求 —— 它只该走带外只读通道"


def test_the_postconditions_can_be_false():
    """🔴 **「能为假」才证明它在算。**

    2026-08-28 独立收口审计抓到的：原来这条判据只断言两条事实**等于 True** ——
    而把实现改成写死的 `True`，**13 条判据一条都不红**。
    一条名叫「不是自报的」、实际分辨不出自报的判据，正是本仓最忌讳的那种绿。

    修法是把推导抽成纯函数，然后喂**该为假**的输入。
    下面每一格都是「实现写死 True 就会红」的那种断言。
    """
    from agenerp.oob import TRIM_TABLE, OobCommand
    from agenerp.tools.drift import derive_facts

    def cmd(*argv: str) -> OobCommand:
        return OobCommand(service="backend", argv=argv)

    good = cmd("bench", "execute", TRIM_TABLE, "--kwargs", "{'dry_run': True}")

    # ① 正常一轮：两条都真
    facts = derive_facts([good], 0)
    assert facts["uses_frappe_trim_table_dry_run"] is True
    assert facts["reports_without_dropping"] is True

    # ② 一条命令都没发过 ⇒ 说不出「口径来自 Frappe」
    assert derive_facts([], 0)["uses_frappe_trim_table_dry_run"] is False

    # ③ 调的不是 trim_table ⇒ 假
    other = cmd("bench", "execute", "frappe.db.sql", "--kwargs", "{'dry_run': True}")
    assert derive_facts([other], 0)["uses_frappe_trim_table_dry_run"] is False

    # ④ 🔴 是 trim_table 但**没带 dry_run** ⇒ 假。
    #    事实名承诺了 `dry_run`，只查函数名就是承诺了没验的那一半（审计的 C4）。
    no_dry = cmd("bench", "execute", TRIM_TABLE, "--kwargs", "{}")
    assert derive_facts([no_dry], 0)["uses_frappe_trim_table_dry_run"] is False

    # ⑤ 发过 REST 请求 ⇒ 「只报不删」立不住
    assert derive_facts([good], 1)["reports_without_dropping"] is False

    # ⑥ 命令里出现 drop ⇒ 同上
    dropping = cmd("bench", "execute", TRIM_TABLE, "--kwargs", "{'dry_run': True}", "drop")
    assert derive_facts([dropping], 0)["reports_without_dropping"] is False


def test_the_facts_the_executor_emits_come_from_that_same_function():
    """纯函数判得再好，执行体不用它也白搭 —— 这一条把两端接上。"""
    from agenerp.tools.drift import schema_drift_scan
    from agenerp.tools.runtime import Session

    class _Client:
        site = "gitops.test"

    outcome = schema_drift_scan(
        Session(_Client(), runner=runner_for({"ToDo": ["c"]})), {"doctype": "ToDo"}
    )

    assert outcome.facts["uses_frappe_trim_table_dry_run"] is True
    assert outcome.facts["reports_without_dropping"] is True
