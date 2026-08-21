"""格式组 —— 校验器对每种非法结构各红一次。

**失败意味着什么**：校验器放行了不合法的契约。那等于契约层没有校验器——
十条契约里错一个，要靠人肉在 review 里看出来，而 review 正是本项目反复证明会漏的那一环。

判据出处：`docs/masterplan/02-WBS.md` P0.2（`pytest tests/contracts -q` 退 0）。
"""

import pytest

from agenerp.contracts import (
    APPROVAL_NOT_REQUIRED,
    Condition,
    ContractError,
    Returns,
    ToolContract,
    check,
    check_registry,
    validate,
    validate_registry,
)

GOOD_RETURNS = Returns(
    trim_rules=("只回点名的字段",),
    max_rows=10,
    must_keep=("name",),
)


def make(**overrides) -> ToolContract:
    base = dict(
        tool="query.read",
        target="Sales Order",
        risk="L0",
        requires_permission=("Sales Order.read",),
        returns=GOOD_RETURNS,
        on_violation="abort_and_report",
        approval=APPROVAL_NOT_REQUIRED,
    )
    base.update(overrides)
    return ToolContract(**base)


def test_a_wellformed_contract_has_no_problems():
    assert validate(make()) == ()
    check(make())


@pytest.mark.parametrize(
    "overrides,segment",
    [
        ({"tool": "  "}, "tool"),
        ({"target": ""}, "target"),
        ({"risk": "L9"}, "risk"),
        ({"risk": ""}, "risk"),
        ({"on_violation": ""}, "on_violation"),
        ({"on_violation": "shrug"}, "on_violation"),
        ({"approval": ""}, "approval"),
        ({"returns": None}, "returns"),
        ({"returns": Returns(trim_rules=(), max_rows=10, must_keep=("name",))}, "returns"),
        ({"returns": Returns(trim_rules=("x",), max_rows=None, must_keep=("name",))}, "returns"),
        ({"returns": Returns(trim_rules=("x",), max_rows=0, must_keep=("name",))}, "returns"),
        ({"returns": Returns(trim_rules=("x",), max_rows=True, must_keep=("name",))}, "returns"),
        ({"returns": Returns(trim_rules=("x",), max_rows=10, must_keep=())}, "returns"),
        ({"side_effects": ("发邮件",)}, "side_effects"),
        ({"requires_permission": ("Sales Order.submit",)}, "requires_permission"),
        ({"requires_permission": ("Sales Order.delete",)}, "requires_permission"),
        ({"on_violation": "rollback_and_report"}, "on_violation"),
        ({"approval": "required_if(金额 > 阈值)"}, "approval"),
        ({"preconditions": (Condition(text="", fact="f"),)}, "preconditions[0]"),
        ({"preconditions": (Condition(text="t", fact="  "),)}, "preconditions[0]"),
        ({"preconditions": (Condition(text="t", fact="f", operator="wat"),)}, "preconditions[0]"),
        ({"postconditions": (Condition(text="t", fact=""),)}, "postconditions[0]"),
        ({"postconditions": ("不是 Condition",)}, "postconditions[0]"),
    ],
)
def test_each_malformed_shape_is_rejected(overrides, segment):
    problems = validate(make(**overrides))
    assert problems, f"校验器放行了不合法契约：{overrides}"
    assert any(segment in p for p in problems), f"错误消息没指名到 {segment}：{problems}"


def test_error_message_names_the_tool_not_just_the_segment():
    """十条契约里错一个，消息里必须能看出是哪一个工具——否则要人肉找。"""
    problems = validate(make(tool="doc.links", risk="L9"))
    assert all(p.startswith("doc.links · ") for p in problems), problems


def test_unnamed_tool_still_gets_a_readable_label():
    problems = validate(make(tool=""))
    assert all(p.startswith("<未命名工具> · ") for p in problems), problems


def test_check_raises_and_carries_every_problem():
    with pytest.raises(ContractError) as excinfo:
        check(make(risk="L9", on_violation="", approval=""))
    message = str(excinfo.value)
    for segment in ("risk", "on_violation", "approval"):
        assert segment in message, message


def test_validate_does_not_short_circuit():
    """一次看全所有问题——逐条修再逐条跑会把循环烧光。"""
    problems = validate(make(tool="", target="", risk="L9", on_violation="", approval=""))
    assert len(problems) >= 5, problems


def test_registry_rejects_duplicate_tool_names():
    """重名会让「按名取契约」静默取错一条。"""
    problems = validate_registry([make(), make()])
    assert any("工具名重复" in p for p in problems), problems
    with pytest.raises(ContractError):
        check_registry([make(), make()])


def test_registry_accepts_distinct_wellformed_contracts():
    assert validate_registry([make(), make(tool="doc.get")]) == ()


def test_write_only_rules_do_not_fire_when_read_only_is_false():
    """收紧规则只对 read_only 生效——写契约（P3.1）来的时候不该被 v0 的规则挡住。"""
    problems = validate(
        make(
            read_only=False,
            side_effects=("发邮件",),
            requires_permission=("Delivery Note.submit",),
            on_violation="abort_before_side_effect",
            approval="required_if(金额 > 阈值)",
        )
    )
    assert problems == ()
