"""非门禁测试 · 钉死孤儿列巡检的**口径**（`agenerp/oob.py` + `agenerp.snapshot.schema_drift`）。

⚠️ **2026-08-28 由 `test_schema_drift.py` 改名为 `test_schema_drift_oob.py`。**
P2.5 的验收路径由 WBS §5 第 105 行**写死**为 `tests/tools/test_schema_drift.py`，
而 `tests/` 下没有 `__init__.py` ⇒ 同名 basename 会让**整轮** pytest
`import file mismatch`（这个坑 `tests/render/test_renderer.py` 模块头逐字记着）。
WBS 那条路径动不了，所以改这一个。**断言一条没动。**

分工：本文件验**口径**（哪些列算孤儿、`dry_run` 钉死、白名单）；
`tests/tools/test_schema_drift.py` 验**工具面**（契约挂上了、两个入口、不进模型工具面）。

**不连真站点、不起容器**：`tests/unit` 必须零依赖可跑（CI 的 `gates-l1` 只 `pip install pytest`）。
带外执行器是注入进来的假件，命令对象本身就是可断言的值——与
`tests/unit/test_site_client.py` 喂假 `Transport` 是同一手法。

live 那一侧的证据在 plan `docs/plans/p0-foundation/2026-08-21-2220-1-schema-drift-orphan-columns.md`
（`information_schema` 交叉验证的写死等式），不在本文件里。
"""

import pytest

from agenerp import oob as oob_mod
from agenerp.contracts import WRITE_VERBS
from agenerp.oob import (
    ALLOWED_CALLS,
    SITE_ENV,
    TRIM_TABLE,
    OobCommand,
    OobError,
    OobResult,
    drop_columns,
    read_site_config,
    run_json,
)
from agenerp.snapshot import schema_drift

# 每加宽一次写面就留一次痕 —— 这个列表是那道痕。**只登记，不取消判据**，
# 与 `tests/unit/test_site_client.py` 的 `WRITE_METHOD_ALLOWLIST` 是同一条纪律
# （`agenerp/site.py` 模块头第 4 条）。
#
# `drop_columns`（2026-08-21，plan `2026-08-21-2220-1` 孤儿列清除面）：
#   Frappe 删 Custom Field **不删物理列**，不清的话反复增删会静默累积孤儿列
#   （判据 `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`）。
#   写面被**刻意限死在 `ALTER TABLE … DROP COLUMN` 一种语句上**：不提供「调用方给整条 SQL」
#   的通用入口，那等于把 `ALLOWED_CALLS` 白名单作废（§11.8）。
OOB_WRITE_METHOD_ALLOWLIST: tuple[str, ...] = ("drop_columns",)


def _public_callables() -> list[str]:
    """`agenerp.oob` 对外暴露的全部公开可调用名（模块级函数 + 公开类的公开方法）。"""
    names: list[str] = []
    for attr in dir(oob_mod):
        if attr.startswith("_"):
            continue
        obj = getattr(oob_mod, attr)
        if callable(obj) and getattr(obj, "__module__", "") == oob_mod.__name__:
            names.append(attr)
            if isinstance(obj, type):
                names.extend(f"{attr}.{m}" for m in dir(obj) if not m.startswith("_"))
    return names


def test_oob_module_exposes_no_unlisted_write_method():
    """写面按**收窄**演进：又多了一个写方法这件事必须付一次 diff 和一次留痕。"""
    offenders = [
        name for name in _public_callables()
        if any(verb in name.split(".")[-1].lower() for verb in WRITE_VERBS)
        and name not in OOB_WRITE_METHOD_ALLOWLIST
    ]

    assert offenders == [], f"未登记的写方法：{offenders}；白名单={OOB_WRITE_METHOD_ALLOWLIST}"


def test_the_oob_allowlist_assertion_actually_has_teeth():
    """白名单断言不能是空转的：给它喂一个写方法名，它必须判成违规。"""
    fabricated = f"{WRITE_VERBS[0]}_everything"

    assert any(v in fabricated.lower() for v in WRITE_VERBS)
    assert fabricated not in OOB_WRITE_METHOD_ALLOWLIST


def test_drop_columns_with_no_columns_sends_nothing():
    """空集合**直接返回不发命令**——空 DDL 不是「什么都不删」的正确表达。"""
    runner = FakeRunner()

    drop_columns("Item", (), site="frontend", runner=runner)

    assert runner.commands == []


def test_drop_columns_does_not_share_the_bench_allowlist():
    """`ALLOWED_CALLS` 管的是 Python 函数调用，管不到 DDL —— 两者是两个 exec 目标。"""
    runner = FakeRunner([_ok('{"db_name": "_testdb"}'), _ok("")])

    drop_columns("Item", ("a_col",), site="frontend", runner=runner)

    assert [c.service for c in runner.commands] == ["backend", "db"]
    assert "ALTER TABLE `tabItem` DROP COLUMN `a_col`;" in runner.commands[-1].argv[-1]


class FakeRunner:
    """记下每一次命令，按预设答复。默认答一个空的 JSON 数组。"""

    def __init__(self, results=None):
        self.commands: list[OobCommand] = []
        self._results = list(results or [])

    def __call__(self, command: OobCommand) -> OobResult:
        self.commands.append(command)
        if self._results:
            return self._results.pop(0)
        return OobResult(0, "[]\n", "")


def _ok(stdout: str) -> OobResult:
    return OobResult(0, stdout, "")


@pytest.fixture(autouse=True)
def _no_ambient_site(monkeypatch):
    """本机的 `AGENERP_SITE` 不得渗进单测——否则「忘了传 site」这条会在开发机上假绿。"""
    monkeypatch.delenv(SITE_ENV, raising=False)


def test_schema_drift_sorts_and_deduplicates():
    """返回值是**排序去重后的元组**。不定型（原签名 `Any`）时调用方只能靠猜。"""
    runner = FakeRunner([_ok('["b_col", "a_col", "b_col"]')])

    assert schema_drift("Item", site="frontend", runner=runner) == ("a_col", "b_col")


def test_schema_drift_asks_frappe_with_dry_run_pinned_true():
    """巡检必须是**只读**的：`dry_run` 恒为 `True`，且口径复用 Frappe 自己的 `trim_table`。"""
    runner = FakeRunner()

    schema_drift("Item", site="frontend", runner=runner)

    argv = runner.commands[0].argv
    assert argv[:5] == ("bench", "--site", "frontend", "execute", TRIM_TABLE)
    kwargs = eval(argv[argv.index("--kwargs") + 1])  # noqa: S307 —— 与 bench 侧同一条 eval 口径
    assert kwargs == {"doctype": "Item", "dry_run": True}


def test_bench_kwargs_are_a_python_literal_not_json():
    """实测红过一次：`bench execute --kwargs` 走 `eval`，JSON 的 `true` 会红在 `NameError`。"""
    runner = FakeRunner()

    schema_drift("Item", site="frontend", runner=runner)

    payload = runner.commands[0].argv[-1]
    assert "True" in payload and "true" not in payload


def test_caller_cannot_smuggle_dry_run_false():
    """钉死的 kwargs 只钉名字挡不住任何东西——`dry_run=False` 会把该 DocType 的孤儿列一次删光。"""
    with pytest.raises(TypeError):
        run_json(TRIM_TABLE, doctype="Item", site="frontend",
                 runner=FakeRunner(), dry_run=False)  # type: ignore[call-arg]

    assert ALLOWED_CALLS[TRIM_TABLE] == {"dry_run": True}


def test_function_outside_the_allowlist_is_refused():
    """白名单外的函数名一律拒——白名单退化成「能传任意函数」就等于把它作废。"""
    runner = FakeRunner()

    with pytest.raises(OobError, match="不在带外调用白名单内"):
        run_json("frappe.db.sql_ddl", doctype="Item", site="frontend", runner=runner)

    assert runner.commands == [], "被拒的调用不该发出任何命令"


def test_doctype_outside_the_identifier_allowlist_is_refused():
    runner = FakeRunner()

    with pytest.raises(OobError, match="标识符白名单"):
        schema_drift("Item; DROP TABLE tabItem", site="frontend", runner=runner)

    assert runner.commands == []


def test_command_failure_raises_instead_of_returning_empty():
    """**承重条款**：空元组是「没有孤儿列」这个合法结论；用它兼表「命令没跑起来」会让门禁假绿。"""
    runner = FakeRunner([OobResult(1, "", "bench: 站点不存在")])

    with pytest.raises(OobError, match="带外命令失败"):
        schema_drift("Item", site="frontend", runner=runner)


def test_non_list_payload_raises():
    runner = FakeRunner([_ok('{"columns": []}')])

    with pytest.raises(OobError, match="回的不是列表"):
        schema_drift("Item", site="frontend", runner=runner)


def test_non_string_column_raises():
    runner = FakeRunner([_ok("[1, 2]")])

    with pytest.raises(OobError, match="回的列名不是字符串"):
        schema_drift("Item", site="frontend", runner=runner)


def test_unparsable_payload_raises():
    runner = FakeRunner([_ok("Traceback (most recent call last):\n")])

    with pytest.raises(OobError, match="不是 JSON"):
        schema_drift("Item", site="frontend", runner=runner)


def test_missing_site_raises_instead_of_guessing():
    with pytest.raises(OobError, match=SITE_ENV):
        schema_drift("Item", runner=FakeRunner())


def test_read_site_config_returns_the_db_name():
    """DDL 的库名只能读、推不出来：`db` 服务不设 `MYSQL_DATABASE`。"""
    runner = FakeRunner([_ok('{"db_name": "_5e5899d8398b5f7b", "db_type": "mariadb"}')])

    assert read_site_config("frontend", runner=runner)["db_name"] == "_5e5899d8398b5f7b"
    assert runner.commands[0].argv == ("cat", "sites/frontend/site_config.json")


def test_read_site_config_refuses_a_path_traversing_site_name():
    runner = FakeRunner()

    with pytest.raises(OobError, match="拒绝拼进容器内路径"):
        read_site_config("../../etc", runner=runner)

    assert runner.commands == []


# --- 「零孤儿列」必须表达得出来（plan 2026-08-22-0228-2，红因分流 (b) 档） -------------
#
# 红因逐字：全新站点上 apply 把探针列清干净之后，`trim_table` 返回 `[]`，
# 而 `bench execute` 只在返回值为真时才打印（`frappe/commands/utils.py:285` 的 `if ret:`），
# 于是 stdout 是零字节 → 旧代码判成「载荷不是 JSON」→ `OobError` → 门禁红。
# **清干净了反而红**。下面四条钉的是这条通道，不是钉门禁。


def test_empty_stdout_means_the_callee_returned_a_falsy_value():
    """`bench execute` 对假值返回一个字都不打印 —— 这不是故障，是协议。"""
    from agenerp.oob import FALSY_RESULT

    runner = FakeRunner([_ok("")])

    assert run_json(TRIM_TABLE, doctype="Item", site="frontend", runner=runner) is FALSY_RESULT


def test_a_site_with_zero_orphan_columns_is_expressible():
    """**承重条款**：站点上一条孤儿列都没有时，巡检必须回空元组，而不是抛。"""
    runner = FakeRunner([_ok("")])

    assert schema_drift("Item", site="frontend", runner=runner) == ()


def test_blank_stdout_is_not_confused_with_a_broken_command():
    """例外只覆盖**退出码 0**：非零退出仍旧抛，空 stdout 不给它开后门。"""
    runner = FakeRunner([OobResult(1, "", "")])

    with pytest.raises(OobError, match="带外命令失败"):
        schema_drift("Item", site="frontend", runner=runner)


def test_the_falsy_sentinel_is_not_a_result_any_caller_can_use_by_accident():
    """哨兵不是 `None` 也不是 `[]`：这两个都会重新制造本模块要挡的那种歧义。"""
    from agenerp.oob import FALSY_RESULT

    assert FALSY_RESULT is not None
    assert FALSY_RESULT != []
    assert not isinstance(FALSY_RESULT, list)
    # `json.loads("null")` 就是 None —— 站点真回了 `null` 与「什么都没打印」必须分得开。
    assert run_json(TRIM_TABLE, doctype="Item", site="frontend",
                    runner=FakeRunner([_ok("null")])) is None
