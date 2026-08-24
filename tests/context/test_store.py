"""存储端口与零依赖内置实现的判据 —— 零网络、零外部依赖。

**round-trip 与确定性是两个性质，必须分开断言**：一个用 `json.dumps` 按插入序写的实现
round-trip 完美、同进程内两次落盘也字节完全相等 —— **只有键序断言能把它打红**。
所以这里有三条分开的判据：

① 落盘 → 读回，**结构保真**；
② 同一会话连续序列化两次，**字节完全相等**；
③ 序列化后每一个对象的**键序恰等于 `sorted(keys)`**。

③ 的承载物必须是**自由键字典**：dataclass 的字段序是固定的，拿它验不出插入序问题。
每轮工具调用的 `params` 是天然载体，因此本文件的样例会话里塞了一个插入序**非字典序**的 `params`。
"""

from __future__ import annotations

import json

import pytest

from agenerp.context.session import Turn, ToolCall, start
from agenerp.context.store import (
    JsonFileSessionStore,
    SessionStore,
    deserialize,
    from_payload,
    serialize,
    to_payload,
)
from agenerp.routing.adapter import Usage
from agenerp.snapshot import Snapshot, SnapshotEntry

BEFORE = Snapshot(scope="doctypes", entries=(SnapshotEntry("Item", "probe", {"a": 1}),))
AFTER = Snapshot(scope="doctypes", entries=(SnapshotEntry("Item", "probe", {"a": 2}),))

# **插入序刻意非字典序**：zeta / mid / alpha。按插入序写盘的实现会原样保留这个次序。
UNSORTED_PARAMS = {"zeta": 1, "mid": "两", "alpha": [3, {"yy": 1, "xx": 2}]}


def _session():
    return (
        start("S-1", user="老板")
        .with_turn(Turn("user", "990 台去哪了", usage=Usage(11, 20, 7)))
        .with_turn(
            Turn(
                "assistant",
                "",
                tool_calls=(ToolCall("doc.get", UNSORTED_PARAMS, ok=True),),
                usage=Usage(100, 200, 150),
            )
        )
        .with_readonly_probe(tool="snapshot.read", params={"scope": "doctypes"},
                             before=BEFORE, after=AFTER, request_count=2)
    )


def _key_orders(text: str) -> list[list[str]]:
    """把每一个 JSON 对象的**实际键序**收集起来 —— `json.loads` 默认会丢掉它。"""
    orders: list[list[str]] = []

    def hook(pairs):
        orders.append([k for k, _ in pairs])
        return dict(pairs)

    json.loads(text, object_pairs_hook=hook)
    return orders


# ── ① 保真 ─────────────────────────────────────────────────────────


def test_save_then_load_is_structurally_faithful(tmp_path):
    store = JsonFileSessionStore(tmp_path)
    session = _session()
    store.save(session)
    assert store.load("S-1") == session


def test_the_free_key_params_survive_the_round_trip_verbatim(tmp_path):
    store = JsonFileSessionStore(tmp_path)
    store.save(_session())
    assert store.load("S-1").turns[1].tool_calls[0].params == UNSORTED_PARAMS


def test_payload_round_trip_without_touching_the_filesystem():
    assert from_payload(to_payload(_session())) == _session()


def test_total_is_not_persisted_as_a_second_source_of_truth():
    """`total` 是 `prompt + completion` 的派生量。落进去就是第二份真相。

    ⚠️ `cached` **不在此列** —— 它不是派生量，是端点自报的 prompt 侧细分，
    不落盘就是静默丢数（下一条判的正是这个）。
    """
    usage_payload = to_payload(_session())["turns"][0]["usage"]
    assert set(usage_payload) == {"prompt", "completion", "reasoning", "cached"}


def test_a_cached_hit_survives_the_round_trip():
    """**上面那条 round-trip 判不到 `cached`** —— `_session()` 的 `cached` 恒为 0，
    一个把 `cached` 落盘时丢掉的实现照样能让它全绿。这一条专喂 `cached > 0`。
    """
    session = start("S-cache").with_turn(
        Turn("assistant", "答案", usage=Usage(prompt=1334, completion=457, reasoning=446, cached=1024))
    )

    assert to_payload(session)["turns"][0]["usage"]["cached"] == 1024
    assert from_payload(to_payload(session)) == session


def test_a_missing_key_raises_instead_of_defaulting():
    payload = to_payload(_session())
    del payload["snapshots"]
    with pytest.raises(KeyError):
        from_payload(payload)


# ── ② 字节确定性 ───────────────────────────────────────────────────


def test_serialising_the_same_session_twice_is_byte_identical():
    assert serialize(_session()) == serialize(_session())


def test_saving_twice_writes_the_same_bytes(tmp_path):
    store = JsonFileSessionStore(tmp_path)
    session = _session()
    store.save(session)
    first = store.path_of("S-1").read_bytes()
    store.save(session)
    assert store.path_of("S-1").read_bytes() == first


# ── ③ 键序 ─────────────────────────────────────────────────────────


def test_every_object_is_written_with_keys_in_sorted_order():
    """**M4 靠这一条打红**（去掉 `sort_keys=True` / 改成按插入序写）。

    这条断言不与 ① / ② 重复：按插入序写的实现在那两条上都是绿的。
    """
    orders = _key_orders(serialize(_session()))
    assert orders, "样例会话里一个 JSON 对象都没有——判据在空转"
    for keys in orders:
        assert keys == sorted(keys), f"键序不是字典序：{keys}"


def test_the_sample_session_really_carries_a_non_lexicographic_free_key_dict():
    """**判据的判据**：样例里必须真有一个插入序非字典序的自由键字典，否则上一条永远绿。"""
    assert list(UNSORTED_PARAMS) != sorted(UNSORTED_PARAMS)
    assert UNSORTED_PARAMS in [call.params for call in _session().turns[1].tool_calls]


# ── 端口本身 ───────────────────────────────────────────────────────


def test_the_builtin_implementation_satisfies_the_port(tmp_path):
    store: SessionStore = JsonFileSessionStore(tmp_path)
    store.save(_session())
    assert store.load("S-1").session_id == "S-1"


def test_the_builtin_implementation_has_zero_external_dependencies():
    """§8.5 逐字「内置实现必须存在且零外部依赖」。判据：只 import 标准库与本仓。"""
    import ast
    from pathlib import Path

    tree = ast.parse(Path("agenerp/context/store.py").read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots <= {"__future__", "json", "collections", "pathlib", "typing", "agenerp"}


def test_deserialize_accepts_what_serialize_produced():
    assert deserialize(serialize(_session())) == _session()
