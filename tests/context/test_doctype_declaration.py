"""会话 DocType **声明**的判据 —— 零网络、零站点。

两件事，都写死成机械判据：

① 声明与 `ConversationSession` **逐字段同构**：改了一边不改另一边就红（M5 靠这一条打红）。
② `agenerp/context/**` **一处也不写活站点**（M8 靠这一条打红）。这条直接兑现 plan §5.2
   的可逆性声明：本层不新增任何对活站点的写调用，因此**站点侧回滚问题在本 plan 的交付面上不产生**。

⚠️ **残余，照实记，不许说成「已证明不可能写站点」**：源码/AST 扫描挡得住直写，
挡不住 `getattr(client, "create_" + "doc")` 这类拼名调用。v0 接受这条残余。

⚠️ **这里没有任何 apply 逻辑，本仓也不该长出第二条 DDL 路径。**
在活站点上建这张表是风险档 L3、**强制人批**的动作，已挂进 `STATE.md` §3 的 needs-human 队列。
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from _scan import SITE_WRITE_NAMES, site_write_hits, source_files

from agenerp.context.session import ConversationSession
from agenerp.context.store import to_payload

DECLARATION_DIR = Path("agenerp/context/doctype")
DECLARATION = DECLARATION_DIR / "agent_conversation_session.json"


def _declaration() -> dict:
    return json.loads(DECLARATION.read_text(encoding="utf-8"))


def _declared_fieldnames() -> list[str]:
    return [field["fieldname"] for field in _declaration()["fields"]]


def _dataclass_fieldnames() -> list[str]:
    return [f.name for f in dataclasses.fields(ConversationSession)]


# ── ① 声明 ↔ ConversationSession 同构 ──────────────────────────────


def test_the_declaration_is_committed_to_git_and_parses():
    assert DECLARATION.exists()
    assert _declaration()["name"] == "Agent Conversation Session"


def test_declared_fields_match_the_dataclass_field_for_field():
    """**M5 靠这一条打红**：声明多一个字段而 `ConversationSession` 没有，立刻红。"""
    assert sorted(_declared_fieldnames()) == sorted(_dataclass_fieldnames())


def test_field_order_lists_exactly_the_declared_fields():
    assert _declaration()["field_order"] == _declared_fieldnames()


def test_the_persisted_payload_uses_the_same_keys_as_the_declaration():
    """第三条边：落盘 payload 的键 = 声明的字段 = dataclass 的字段。三者围成一圈。"""
    payload_keys = sorted(to_payload(ConversationSession(session_id="S-1")))
    assert payload_keys == sorted(_declared_fieldnames())


def test_session_id_is_the_naming_field_and_unique():
    """会话 id 是身份。不 unique 的话，两次落盘会变成两条记录而不是一次更新。"""
    declaration = _declaration()
    assert declaration["autoname"] == "field:session_id"
    session_id = next(f for f in declaration["fields"] if f["fieldname"] == "session_id")
    assert session_id["reqd"] == 1 and session_id["unique"] == 1


def test_the_declaration_carries_no_apply_logic_of_its_own():
    """声明目录里**只有 JSON**：本仓不长第二条 DDL 路径（plan §1.4 / §5.2）。"""
    assert sorted(p.name for p in DECLARATION_DIR.iterdir()) == [DECLARATION.name]


# ── ② 零站点写 ─────────────────────────────────────────────────────


def test_the_context_layer_never_writes_to_a_live_site():
    """**M8 靠这一条打红**：任一模块里加一行 `client.create_doc(...)` 立刻红。"""
    assert site_write_hits() == []


def test_the_write_blacklist_is_the_three_names_the_policy_points_at():
    """黑名单出处是 `ai-autonomy-policy.md` Protected Areas 末行点名的那几个写入面。"""
    assert SITE_WRITE_NAMES == frozenset({"create_doc", "ensure_doc", "delete_custom_field"})


def test_the_write_scan_actually_reads_every_module():
    """扫描器不许空转：`agenerp/context/**` 下每个 `.py` 都要被读到。"""
    scanned = {p.name for p in source_files()}
    on_disk = {p.name for p in Path("agenerp/context").rglob("*.py")}
    assert scanned == on_disk
    assert {"immediate.py", "session.py", "store.py"} <= scanned
