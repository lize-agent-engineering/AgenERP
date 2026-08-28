"""非门禁测试 · 钉死差集 apply 的**执行**半边（`agenerp.apply.execute_plan` 与作用域收窄）。

**不连真站点**：站点侧收一个假客户端（`execute_plan(..., client=...)`，或对
`apply_pack` 那条委派链 monkeypatch `client_from_env`），所以本文件在 `GATE_VERIFY` 的
默认环境里就能跑，不依赖 docker、不依赖端口。

为什么这些用例必须存在：承重条款
`tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site`
只看「Item 上的探针没了」——**一个把站点定制全删光的实现照样让它绿**。
判据挡不住那个错误，所以收窄自带判据，且**正反两断言写在同一个用例里**：
只写反断言（「Customer 没被删」）的话，一个什么都不删的空实现完美通过。

用例编号与 plan `docs/plans/p0-foundation/2026-08-21-1922-3-execute-plan-site-delete.md`
Phase 2 的 `Proof` 一致（① ~ ⑧ + 一条端到端纯逻辑回归）。
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

from agenerp.apply import (
    PACK_SCOPE,
    ApplyDirectionError,
    ApplyPlan,
    _assert_direction,
    execute_plan,
    narrow_deletes,
    pack_doctypes,
    read_pack,
)
from agenerp.oob import OobError, OobResult
from agenerp.pack import apply_pack, render_doctype_file
from agenerp.site import SiteError
from agenerp.snapshot import ChangedEntry, Snapshot, SnapshotEntry

PROBE = "agenerp_gate_roundtrip"


class FakeSiteClient:
    """记下每一次删除请求。`fail_on` 命中时抛 `SiteError`（站点侧失败的形状）。"""

    def __init__(
        self,
        fail_on: tuple[str, str] | None = None,
        fail_create_on: tuple[str, str] | None = None,
    ) -> None:
        self.deleted: list[tuple[str, str]] = []
        self.created: list[tuple[str, dict]] = []
        # 建与删的**相对顺序**：先建后删这条纪律要判得出来，就得记在同一条时间线上。
        self.order: list[str] = []
        self.listed: list[str] = []
        self._fail_on = fail_on
        self._fail_create_on = fail_create_on
        self._rows: list[dict] = []

    def with_rows(self, rows: list[dict]) -> "FakeSiteClient":
        self._rows = rows
        return self

    def list_resource(self, doctype: str, fields: tuple[str, ...] = ("*",)) -> list[dict]:
        self.listed.append(doctype)
        return list(self._rows)

    def delete_custom_field(self, doctype: str, fieldname: str) -> None:
        if self._fail_on == (doctype, fieldname):
            raise SiteError(f"DELETE Custom Field/{doctype}-{fieldname} → HTTP 417（假件）")
        self.deleted.append((doctype, fieldname))
        self.order.append(f"delete:{doctype}.{fieldname}")

    def create_doc(self, doctype: str, payload: dict) -> dict:
        target = (payload.get("dt"), payload.get("fieldname"))
        if self._fail_create_on == target:
            raise SiteError(f"POST {doctype} {target} → HTTP 417（假件）")
        self.created.append((doctype, dict(payload)))
        self.order.append(f"create:{target[0]}.{target[1]}")
        return {"name": f"{target[0]}-{target[1]}"}


class FakeOobRunner:
    """记下每一次带外命令，按预设答复。**默认答「这个 DocType 上没有孤儿列」**。

    默认取「没有」而不是「凡删过的都算孤儿」：后者会让每个既有用例都顺手发一条 DDL，
    把「清除真的挑过交集」这件事糊掉。要测清除路径的用例**显式**给 `orphans`。
    """

    def __init__(self, orphans: dict[str, list[str]] | None = None, db_name: str = "_testdb"):
        self.orphans = dict(orphans or {})
        self.db_name = db_name
        self.drift_fails = False
        self.commands: list = []

    def __call__(self, command) -> OobResult:
        self.commands.append(command)
        argv = command.argv
        if argv[0] == "cat":
            return OobResult(0, json.dumps({"db_name": self.db_name}), "")
        if argv[0] == "bench":
            if self.drift_fails:
                return OobResult(1, "", "bench: 站点答不上话（假件）")
            kwargs = eval(argv[argv.index("--kwargs") + 1])  # noqa: S307 —— 与 bench 侧同一条口径
            return OobResult(0, json.dumps(self.orphans.get(kwargs["doctype"], [])), "")
        return OobResult(0, "", "")

    @property
    def ddl(self) -> list[str]:
        return [c.argv[-1] for c in self.commands if c.service == "db"]


@pytest.fixture(autouse=True)
def oob(monkeypatch):
    """兜底：任何没被显式注入的带外调用都落到假件上，**本文件永不碰 docker**。

    与文件头「不连真站点」是同一条约束的延伸——清除面接上之后，`execute_plan`
    多了一条打到物理表的路径，不兜住的话既有用例会在 `GATE_VERIFY` 里去 `docker compose exec`。
    """
    runner = FakeOobRunner()
    monkeypatch.setattr("agenerp.oob.ComposeExecRunner", lambda *a, **k: runner)
    return runner


def _entry(doctype: str, fieldname: str, **attributes) -> SnapshotEntry:
    return SnapshotEntry(doctype, fieldname, {"fieldtype": "Data", **attributes})


def _orphan_free(command):
    """带外执行器的假件：答「没有孤儿列」。清除面的判据在本文件 ⑨ 组。"""
    from agenerp.oob import OobResult

    return OobResult(0, "[]", "")


_ORPHAN_FREE = _orphan_free


def _site_row(doctype: str, fieldname: str, **extra) -> dict:
    return {"dt": doctype, "fieldname": fieldname, "fieldtype": "Data", **extra}


def _plan(*deletes: SnapshotEntry, creates=(), updates=()) -> ApplyPlan:
    return ApplyPlan(scope=PACK_SCOPE, creates=tuple(creates), updates=tuple(updates),
                     deletes=tuple(deletes))


def _write_pack(root, doctype: str, rows: list[dict], filename: str | None = None) -> None:
    scope_dir = root / PACK_SCOPE
    scope_dir.mkdir(parents=True, exist_ok=True)
    (scope_dir / f"{filename or doctype}.json").write_text(
        render_doctype_file(doctype, rows), encoding="utf-8"
    )


@pytest.fixture
def wired(monkeypatch):
    """把 `apply_pack` 委派链两端的 `client_from_env` 都换成同一个假客户端。

    两端：`agenerp.snapshot`（`SiteSnapshotSource.read` 读站点现状）与
    `agenerp.apply`（`execute_plan` 发删除请求）。两个模块各自 `from ... import` 进了
    自己的名字空间，只换一处会漏掉另一处。
    """
    client = FakeSiteClient()

    def _factory(site, transport=None):
        return client

    monkeypatch.setattr("agenerp.snapshot.client_from_env", _factory)
    monkeypatch.setattr("agenerp.apply.client_from_env", _factory)
    return client


# --------------------------------------------------------------------------
# ① 只对 deletes 发删除请求，条数与目标逐条相符
# --------------------------------------------------------------------------
def test_execute_plan_deletes_exactly_the_planned_entries():
    client = FakeSiteClient()
    plan = _plan(_entry("Item", "b_field"), _entry("Item", "a_field"), _entry("Customer", "tier"))

    execute_plan(plan, "frontend", client=client)

    assert client.deleted == [("Customer", "tier"), ("Item", "a_field"), ("Item", "b_field")], (
        f"删除的目标或顺序不对：{client.deleted}"
    )


def test_execute_plan_order_is_deterministic():
    """按 `key` 排序 —— 复跑同一个计划的请求序必须一致，否则日志没法比对。"""
    first, second = FakeSiteClient(), FakeSiteClient()
    entries = [_entry("Item", "z"), _entry("Address", "a"), _entry("Item", "a")]

    execute_plan(_plan(*entries), "frontend", client=first)
    execute_plan(_plan(*reversed(entries)), "frontend", client=second)

    assert first.deleted == second.deleted == [("Address", "a"), ("Item", "a"), ("Item", "z")]


# --------------------------------------------------------------------------
# ② 作用域收窄：正反两断言写在同一个用例里
# --------------------------------------------------------------------------
def test_apply_pack_narrows_deletes_to_doctypes_covered_by_the_pack(tmp_path, wired):
    """包只含 `Item.json`，站点上 `Item.probe` 与 `Customer.probe` 都在。

    **正**：恰好发出一条删除请求，目标是 `Item.probe`。
    **反**：对 Customer 零请求。

    只写反断言的话，一个什么都不删的空实现完美通过 —— 那正是最可能发生的失败模式。
    """
    _write_pack(tmp_path, "Item", [])
    wired.with_rows([_site_row("Item", PROBE), _site_row("Customer", PROBE)])

    apply_pack(str(tmp_path), site="frontend")

    assert wired.deleted == [("Item", PROBE)], f"删除的目标不对：{wired.deleted}"
    assert not [d for d in wired.deleted if d[0] == "Customer"], (
        f"包没管辖 Customer，却删了它的定制：{wired.deleted}"
    )


# --------------------------------------------------------------------------
# ③ 「文件在、数组空」回归 —— 门禁里承重条款的真实状态
# --------------------------------------------------------------------------
def test_pack_file_present_with_empty_array_still_deletes(tmp_path, wired):
    """`Item.json` 存在但 `custom_fields` 为空、站点上有 `Item.probe` → 必须删。

    「文件在、数组空」= 「这个 DocType 我管，且它应该没有定制」。
    按**包条目**推管辖面的话 Item 不在集内，门禁会红而单测全绿 —— 所以这条不能省。
    """
    _write_pack(tmp_path, "Item", [])
    wired.with_rows([_site_row("Item", PROBE)])

    assert pack_doctypes(str(tmp_path)) == frozenset({"Item"})
    assert read_pack(str(tmp_path)).entries == (), "夹具没摆成「文件在、数组空」"

    apply_pack(str(tmp_path), site="frontend")

    assert wired.deleted == [("Item", PROBE)]


def test_missing_pack_dir_deletes_nothing(tmp_path, wired):
    """包目录不存在 → 管辖面为空 → 一条都不删（偏保守，错在安全那一侧）。"""
    wired.with_rows([_site_row("Item", PROBE)])

    assert pack_doctypes(str(tmp_path)) == frozenset()
    apply_pack(str(tmp_path), site="frontend")

    assert wired.deleted == []


# --------------------------------------------------------------------------
# ④ 被收窄掉的条目可观测（不许静默丢弃）
# --------------------------------------------------------------------------
def test_narrowed_out_entries_are_logged_not_silently_dropped(caplog):
    plan = _plan(_entry("Item", PROBE), _entry("Customer", "credit_tier"),
                 _entry("Address", "tax_category"))

    with caplog.at_level(logging.WARNING, logger="agenerp.apply"):
        narrowed = narrow_deletes(plan, frozenset({"Item"}))

    assert [e.key for e in narrowed.deletes] == [("Item", PROBE)]
    messages = " ".join(r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING)
    assert messages, "被收窄掉两条却一句 WARNING 都没发 —— 静默丢弃"
    for doctype, fieldname in (("Customer", "credit_tier"), ("Address", "tax_category")):
        assert doctype in messages and fieldname in messages, (
            f"WARNING 没有逐条列出 ({doctype}, {fieldname})：{messages}"
        )


def test_system_generated_fields_are_excluded_and_logged(caplog):
    """应用自带的字段（`is_system_generated`）即便在管辖面内也不删，且不静默。

    实测依据：站点上 10 条 Custom Field 全部 `is_system_generated = 1`，全部由
    ERPNext / CRM 装上；删掉可能直接弄坏应用功能，而按 DocType 收窄挡不住这一类。
    """
    plan = _plan(_entry("Item", PROBE),
                 _entry("Item", "crm_deal", is_system_generated=1))

    with caplog.at_level(logging.WARNING, logger="agenerp.apply"):
        narrowed = narrow_deletes(plan, frozenset({"Item"}))

    assert [e.key for e in narrowed.deletes] == [("Item", PROBE)]
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "crm_deal" in messages and "is_system_generated" in messages, messages


def test_narrowing_keeps_creates_and_updates_untouched():
    """收窄只删减 `deletes`：另外两个序列原样带过，方向不变量的结论不受影响。"""
    creates = (_entry("Customer", "new_field"),)
    updates = (ChangedEntry("Customer", "tier", before={"a": 1}, after={"a": 2}),)
    plan = _plan(_entry("Customer", "gone"), creates=creates, updates=updates)

    narrowed = narrow_deletes(plan, frozenset({"Item"}))

    assert narrowed.creates == creates and narrowed.updates == updates
    assert narrowed.deletes == ()


# --------------------------------------------------------------------------
# ④b covered 口径与 `entries_from_payload` 同源（载荷 doctype 键优先，不按文件名）
# --------------------------------------------------------------------------
def test_covered_set_follows_payload_doctype_not_filename(tmp_path, wired):
    """一份**文件名叫 `Item.json`**、载荷里写 `{"doctype": "Customer"}` 的包。

    条目面按载荷算（`entries_from_payload`），管辖面必须跟着走 —— 否则两者对不上：
    管辖面说管 Item，条目面说这是 Customer 的定制。
    """
    _write_pack(tmp_path, "Customer", [], filename="Item")
    wired.with_rows([_site_row("Item", PROBE), _site_row("Customer", PROBE)])

    assert pack_doctypes(str(tmp_path)) == frozenset({"Customer"})

    apply_pack(str(tmp_path), site="frontend")

    assert wired.deleted == [("Customer", PROBE)], f"管辖面按文件名算错了：{wired.deleted}"


# --------------------------------------------------------------------------
# ⑤ 站点删除失败 → 抛，且不继续删后面的
# --------------------------------------------------------------------------
def test_site_failure_aborts_and_does_not_continue():
    client = FakeSiteClient(fail_on=("Item", "b_field"))
    plan = _plan(_entry("Item", "a_field"), _entry("Item", "b_field"), _entry("Item", "c_field"))

    with pytest.raises(SiteError):
        execute_plan(plan, "frontend", client=client)

    assert client.deleted == [("Item", "a_field")], (
        f"失败之后还在继续删：{client.deleted}（本层不做事务，失败即停）"
    )


# --------------------------------------------------------------------------
# ⑥ 空计划 → 零请求、零副作用
# --------------------------------------------------------------------------
def test_empty_plan_makes_zero_requests():
    client = FakeSiteClient()

    execute_plan(_plan(), "frontend", client=client)

    assert client.deleted == []


def test_empty_plan_does_not_even_need_credentials(monkeypatch):
    """空的删除集连客户端都不构造 —— 否则离线跑一个空计划会红在缺凭据上。"""
    def _explode(site, transport=None):
        raise AssertionError("空计划不该构造站点客户端")

    monkeypatch.setattr("agenerp.apply.client_from_env", _explode)
    execute_plan(_plan(), "frontend")


def test_empty_pack_and_empty_site_makes_zero_requests(tmp_path, wired):
    """包目录为空、站点上也没有定制 → 委派链跑完，零请求。"""
    apply_pack(str(tmp_path), site="frontend")

    assert wired.deleted == []


# --------------------------------------------------------------------------
# ⑦ creates / updates 非空 → 抛且消息指名
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# ⑦ creates —— **2026-08-28 由 P2.4 接上**
#
# P0.5 把它 deferred 时把重开条件写死了：「出现需要用包在站点上**建**字段的调用方时」。
# P2.4 的第四步「迁站点」正是那个调用方 —— 把包 apply 到一个还没有该字段的站点，
# 那个字段就落在 `plan.creates` 里。下面这组是它的判据。
# --------------------------------------------------------------------------
def test_creates_land_as_custom_field_documents():
    client = FakeSiteClient()
    plan = _plan(creates=(_entry("ToDo", "brand_code", fieldtype="Data", label="品牌码"),))

    execute_plan(plan, "gitops.test", client=client)

    assert client.created == [
        ("Custom Field", {"dt": "ToDo", "fieldname": "brand_code",
                          "fieldtype": "Data", "label": "品牌码"})
    ], client.created


def test_creates_order_is_deterministic():
    """与删除路径同口径：按 `key` 排序，复跑同一个计划的请求序一致、日志可比对。"""
    client = FakeSiteClient()
    plan = _plan(creates=(_entry("ToDo", "zulu"), _entry("Note", "alpha"), _entry("ToDo", "alpha")))

    execute_plan(plan, "gitops.test", client=client)

    assert [(d, p["fieldname"]) for d, p in client.created] == [
        ("Custom Field", "alpha"), ("Custom Field", "alpha"), ("Custom Field", "zulu")
    ]
    assert [p["dt"] for _d, p in client.created] == ["Note", "ToDo", "ToDo"]


def test_a_failed_create_aborts_and_does_not_continue():
    """任一条失败即抛且**不继续建后面的** —— 与删除路径同一条纪律。

    ⚠️ 本层**不做事务/回滚**（划给 P3.1）：中途失败会留下部分应用的状态，
    这一点不假装有。判据只保证「不继续」，不保证「已建的会被撤回」。
    """
    client = FakeSiteClient(fail_create_on=("ToDo", "boom"))
    plan = _plan(creates=(_entry("ToDo", "aaa"), _entry("ToDo", "boom"), _entry("ToDo", "zzz")))

    with pytest.raises(SiteError):
        execute_plan(plan, "gitops.test", client=client)

    assert [p["fieldname"] for _d, p in client.created] == ["aaa"], "失败之后还在继续建"


def test_creates_run_before_deletes():
    """🔴 **先建后删。**

    两者都失败得起，但代价不同：建失败时**什么都还没删**，损失最小；
    先删后建时一旦建失败，字段已经没了。破坏性动作放在增量动作之后，
    是本层在「没有事务」这个前提下能做的唯一取舍（事务归 P3.1）。
    """
    client = FakeSiteClient()
    plan = _plan(_entry("ToDo", "old_one"), creates=(_entry("ToDo", "new_one"),))

    execute_plan(plan, "gitops.test", client=client, runner=_ORPHAN_FREE)

    assert client.order == ["create:ToDo.new_one", "delete:ToDo.old_one"], client.order


def test_an_empty_creates_list_makes_zero_requests():
    client = FakeSiteClient()

    execute_plan(_plan(), "gitops.test", client=client)

    assert client.created == [] and client.deleted == []


def test_updates_are_explicitly_rejected_not_silently_skipped():
    client = FakeSiteClient()
    plan = _plan(_entry("Item", PROBE),
                 updates=(ChangedEntry("Item", "tier", before={"a": 1}, after={"a": 2}),))

    with pytest.raises(NotImplementedError):
        execute_plan(plan, "frontend", client=client)

    assert client.deleted == [], "updates 非空时连 deletes 也不该执行 —— 那是部分应用"


# --------------------------------------------------------------------------
# ⑧ 方向传反 → 抛新异常类型（而不是靠裸 assert）
# --------------------------------------------------------------------------
def test_direction_invariant_raises_an_explicit_error_not_a_bare_assert():
    """删除集里出现了「包里仍有」的条目 → 方向传反了 → 必须抛 `ApplyDirectionError`。

    这条自检**走不到 `plan_apply` 的正常路径**（`diff` 自己是自洽的，互换入参只会得到
    镜像但同样自洽的结果）——它挡的是「`diff` 或映射被改坏」那一类，所以直接喂
    `_assert_direction` 一个不自洽的计划。判据是**类型**，不是文字。
    """
    entry = _entry("Item", "brand_code")
    both = Snapshot(scope=PACK_SCOPE, entries=(entry,))

    with pytest.raises(ApplyDirectionError):
        _assert_direction(_plan(entry), desired=both, current=both)


def test_direction_invariant_survives_python_dash_O():
    """**这条才是把裸 `assert` 换掉的理由**：`-O` 下裸 `assert` 整条消失。

    在子进程里带 `-O` 跑一遍同一个不自洽的计划：仍然抛，才算这道闸真的在。
    """
    code = "\n".join((
        "from agenerp.apply import ApplyDirectionError, ApplyPlan, PACK_SCOPE, _assert_direction",
        "from agenerp.snapshot import Snapshot, SnapshotEntry",
        "e = SnapshotEntry('Item', 'brand_code', {})",
        "both = Snapshot(scope=PACK_SCOPE, entries=(e,))",
        "plan = ApplyPlan(scope=PACK_SCOPE, deletes=(e,))",
        "try:",
        "    _assert_direction(plan, desired=both, current=both)",
        "    print('NOT_RAISED')",
        "except ApplyDirectionError:",
        "    print('RAISED')",
    ))
    proc = subprocess.run(
        [sys.executable, "-O", "-c", code],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2],
    )

    assert proc.returncode == 0, proc.stderr
    assert "RAISED" in proc.stdout, (
        f"`python -O` 下方向不变量没有生效（裸 assert 会被整条剥掉）：{proc.stdout!r}"
    )


def test_direction_error_is_not_an_assertion_error():
    """显式类型才可被上层分类处置；`AssertionError` 在 `-O` 下根本不会被抛出来。"""
    assert not issubclass(ApplyDirectionError, AssertionError)
    assert issubclass(ApplyDirectionError, RuntimeError)


# --------------------------------------------------------------------------
# 端到端纯逻辑回归 —— 反 upsert 的完整链路（不连站点）
# --------------------------------------------------------------------------
def test_removing_a_field_from_the_pack_ends_up_as_a_delete_request(tmp_path, wired):
    """包里删掉一个字段 → `plan_apply` 把它算进 `deletes` → 真的发出删除请求。

    这是 Frappe 那条纯 upsert 路径**做不到**的事，也是 `git revert` 撤得回的全部依据。
    """
    _write_pack(tmp_path, "Item", [{"fieldname": "brand_code", "fieldtype": "Data"}])
    wired.with_rows([_site_row("Item", "brand_code"), _site_row("Item", PROBE)])

    desired = read_pack(str(tmp_path))
    assert [e.key for e in desired.entries] == [("Item", "brand_code")]

    apply_pack(str(tmp_path), site="frontend")

    assert wired.deleted == [("Item", PROBE)], (
        f"包里仍有 brand_code、只少了探针，删除请求却是 {wired.deleted}"
    )


# --------------------------------------------------------------------------
# ⑨ 清除面：apply 之后不留**本次造成**的残列（plan `2026-08-21-2220-1` Phase 2）
# --------------------------------------------------------------------------
def test_only_columns_in_the_intersection_are_dropped(oob):
    """**承重条款**：删的列必须同时满足「Frappe 判它是孤儿」与「本次 apply 真删过同名字段」。

    门禁只看探针列没了 —— 一个 `trim_table(dry_run=False)` 的实现照样让它绿，
    却会顺手删掉该 DocType 上**所有**历史孤儿列。判据挡不住，所以收窄自带判据。
    """
    oob.orphans = {"Item": [PROBE, "agenerp_gate_probe", "agenerp_explore_probe"]}
    plan = _plan(_entry("Item", PROBE), _entry("Item", "never_had_a_column"))

    execute_plan(plan, "frontend", client=FakeSiteClient())

    assert len(oob.ddl) == 1, f"该发且只发一条 DDL：{oob.ddl}"
    assert f"DROP COLUMN `{PROBE}`" in oob.ddl[0]
    for untouched in ("agenerp_gate_probe", "agenerp_explore_probe", "never_had_a_column"):
        assert untouched not in oob.ddl[0], f"多删了 {untouched}：{oob.ddl[0]}"


def test_empty_intersection_sends_no_ddl(oob):
    """交集为空时**一条命令都不发**——空 DDL 与「什么都没删」在站点眼里不是一回事。"""
    oob.orphans = {"Item": ["agenerp_gate_probe"]}

    execute_plan(_plan(_entry("Item", PROBE)), "frontend", client=FakeSiteClient())

    assert oob.ddl == [], f"交集为空却发了 DDL：{oob.ddl}"


def test_untouched_orphans_are_logged_not_silently_ignored(oob, caplog):
    """不删的那些也要说出来：否则「站点上还有 5 条历史残列」这件事永远没人知道。"""
    oob.orphans = {"Item": [PROBE, "agenerp_gate_probe"]}

    with caplog.at_level(logging.WARNING, logger="agenerp.apply"):
        execute_plan(_plan(_entry("Item", PROBE)), "frontend", client=FakeSiteClient())

    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "agenerp_gate_probe" in messages and "本次 apply 没有删过同名字段" in messages, messages


def test_fields_frappe_does_not_call_orphaned_are_logged(oob, caplog):
    with caplog.at_level(logging.WARNING, logger="agenerp.apply"):
        execute_plan(_plan(_entry("Item", PROBE)), "frontend", client=FakeSiteClient())

    messages = " ".join(r.getMessage() for r in caplog.records)
    assert PROBE in messages and "不在 schema_drift 的返回集合里" in messages, messages


def test_schema_drift_failure_aborts_instead_of_being_read_as_no_orphans(oob):
    """**不吞掉**：把「巡检没跑起来」当成「没有孤儿列」，残列会静默累积而门禁照样绿。"""
    oob.drift_fails = True

    with pytest.raises(OobError):
        execute_plan(_plan(_entry("Item", PROBE)), "frontend", client=FakeSiteClient())

    assert oob.ddl == [], "巡检都没成功却发了 DDL"


def test_column_outside_the_identifier_allowlist_is_refused(oob):
    """未经验证的标识符不许进 DDL —— 拒掉即抛，不静默放行。"""
    oob.orphans = {"Item": ["bad-col"]}

    with pytest.raises(OobError, match="标识符白名单"):
        execute_plan(_plan(_entry("Item", "bad-col")), "frontend", client=FakeSiteClient())

    assert oob.ddl == []


def test_ddl_single_quotes_the_statement_so_backticks_are_not_command_substituted(oob):
    """2026-08-21 实测红过一次：反引号落在 `sh -c` 的双引号里被当成命令替换（`tabItem: not found`）。"""
    oob.orphans = {"Item": [PROBE]}

    execute_plan(_plan(_entry("Item", PROBE)), "frontend", client=FakeSiteClient())

    payload = oob.ddl[0]
    assert payload.endswith("'"), f"SQL 没有被单引号包住：{payload}"
    assert "-e '" in payload and '-e "' not in payload, payload


def test_db_name_comes_from_site_config_not_from_the_site_name(oob):
    """`db` 服务不设 `MYSQL_DATABASE`，库名（`_5e5899d8398b5f7b` 这种）推不出来，只能读。"""
    oob.orphans = {"Item": [PROBE]}
    oob.db_name = "_5e5899d8398b5f7b"

    execute_plan(_plan(_entry("Item", PROBE)), "frontend", client=FakeSiteClient())

    assert "_5e5899d8398b5f7b" in oob.ddl[0]
    assert any(c.argv[0] == "cat" for c in oob.commands), "库名不是读来的"


def test_columns_are_dropped_only_after_the_custom_fields_are_gone(oob):
    """顺序：先删 Custom Field 再清列。反过来的话 Frappe 会把列当成「字段还在」而不判孤儿。"""
    oob.orphans = {"Item": [PROBE]}
    client = FakeSiteClient()

    execute_plan(_plan(_entry("Item", PROBE)), "frontend", client=client)

    assert client.deleted == [("Item", PROBE)]
    assert oob.ddl, "字段删了却没清列"
