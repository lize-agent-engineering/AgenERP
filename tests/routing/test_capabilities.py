"""能力声明的判据。

三组判据，一组比一组难糊弄：

1. **同构** —— `agenerp/routing/capabilities.py` 的三份声明与
   `docs/architecture/model-management.md` §12.5 的三张 `machine-read` 表逐行相等。
   文档改了代码没改（或反过来）就红。这是"声明退化成一张没人校验的表"的唯一机械控制。
   ⚠️ 它管不了"两边一起写错"，这条残余风险照实登记在 owner doc §12.5 里。
2. **校验器** —— 四类畸形声明各打红一次。
3. **反测** —— 把 `lineage` 的最低能力换成空集必须红；`lineage` 必须严格严于 `explain`。
   没有这一组，"分档"这件事就没有判据：一张所有类目都要求空集的表同样能让上面两组全绿。

解析文档的代码**写在测试这边**，产品包不依赖 markdown ——
反过来会让文档格式变成运行时依赖。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from agenerp.routing.capabilities import (
    CAPABILITIES,
    KNOWN_MODEL_PROFILES,
    TASK_CLASSES,
    TASK_MINIMUM_CAPABILITIES,
    ModelProfile,
    minimum_capabilities,
    validate_declarations,
    validate_model_profile,
    validate_task_requirements,
)
from agenerp.routing.errors import DeclarationError

OWNER_DOC = Path(__file__).resolve().parents[2] / "docs/architecture/model-management.md"

_CODE = re.compile(r"`([^`]+)`")


def _table_after(marker: str) -> list[list[str]]:
    """读 `<!-- machine-read: <marker> -->` 之后的第一张表，回**数据行**（跳表头与分隔行）。"""
    text = OWNER_DOC.read_text(encoding="utf-8")
    anchor = f"<!-- machine-read: {marker} -->"
    assert anchor in text, f"owner doc 里找不到标记 {anchor}"
    lines = text.split(anchor, 1)[1].splitlines()
    rows: list[list[str]] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if started:
                break
            continue
        started = True
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    assert len(rows) >= 2, f"标记 {marker} 之后没有找到成形的表"
    return rows[1:]


def test_capability_enum_is_isomorphic_to_the_owner_doc():
    documented = tuple(_CODE.search(row[0]).group(1) for row in _table_after("capability-enum"))
    assert documented == CAPABILITIES


def test_task_matrix_is_isomorphic_to_the_owner_doc():
    documented = {}
    for row in _table_after("task-capability-matrix"):
        task = _CODE.search(row[0]).group(1)
        documented[task] = frozenset(_CODE.findall(row[1]))
    assert tuple(documented) == TASK_CLASSES
    assert documented == dict(TASK_MINIMUM_CAPABILITIES)


def test_model_profiles_are_isomorphic_to_the_owner_doc():
    documented = {}
    for row in _table_after("model-profiles"):
        name = _CODE.search(row[0]).group(1)
        documented[name] = ModelProfile(
            name=name,
            capabilities=frozenset(_CODE.findall(row[1])),
            is_reasoning_model=row[2] == "是",
        )
    assert documented == dict(KNOWN_MODEL_PROFILES)


def test_shipped_declarations_validate():
    validate_declarations()


def test_missing_task_entry_is_rejected():
    table = {t: TASK_MINIMUM_CAPABILITIES[t] for t in TASK_CLASSES if t != "lineage"}
    with pytest.raises(DeclarationError, match="缺条目"):
        validate_task_requirements(table)


def test_unknown_task_class_is_rejected():
    table = dict(TASK_MINIMUM_CAPABILITIES) | {"vibes": frozenset({"tool_calling"})}
    with pytest.raises(DeclarationError, match="枚举外的任务类目"):
        validate_task_requirements(table)


def test_capability_outside_the_enum_is_rejected_in_a_task_requirement():
    table = dict(TASK_MINIMUM_CAPABILITIES) | {"explain": frozenset({"cheap"})}
    with pytest.raises(DeclarationError, match="枚举外的能力"):
        validate_task_requirements(table)


def test_capability_outside_the_enum_is_rejected_in_a_model_profile():
    with pytest.raises(DeclarationError, match="枚举外的能力"):
        validate_model_profile(ModelProfile(name="m", capabilities=frozenset({"fast"})))


def test_unknown_task_class_does_not_silently_become_an_empty_requirement():
    """未知类目回空集 = 谁都能接。那是本模块存在理由的反面，必须报错。"""
    with pytest.raises(DeclarationError, match="未知任务类目"):
        minimum_capabilities("no-such-task")


def test_empty_minimum_capability_set_is_rejected():
    """**反测**：把 `lineage` 的最低能力换成空集必须红 —— 否则"分档"没有判据。"""
    table = dict(TASK_MINIMUM_CAPABILITIES) | {"lineage": frozenset()}
    with pytest.raises(DeclarationError, match="空集"):
        validate_task_requirements(table)


def test_lineage_is_strictly_stricter_than_explain():
    """§12.3 结论 3：多跳推理是能力分水岭。分水岭两侧的要求不许相等。"""
    assert minimum_capabilities("lineage") > minimum_capabilities("explain")
    assert "multi_hop" in minimum_capabilities("lineage")
    assert "multi_hop" not in minimum_capabilities("explain")


@pytest.mark.parametrize(
    ("model", "task", "expected"),
    [
        ("qwen3.6-plus", "lineage", True),
        ("qwen3.6-plus", "shape", True),
        ("qwen-plus", "explain", True),
        ("qwen-plus", "lineage", False),
        ("qwen3:14b", "permission", True),
        ("qwen3:14b", "lineage", False),
    ],
)
def test_shipped_profiles_satisfy_exactly_the_tasks_the_owner_doc_says(model, task, expected):
    assert KNOWN_MODEL_PROFILES[model].satisfies(task) is expected


def test_missing_for_names_every_gap_sorted():
    weak = KNOWN_MODEL_PROFILES["qwen3:14b"]
    assert weak.missing_for("shape") == ("long_context", "multi_hop", "reasoning")
