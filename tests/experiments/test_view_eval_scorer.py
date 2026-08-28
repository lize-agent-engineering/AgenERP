"""🔴 P2.3 Phase 4 · 守着那个**给出主集 10/12、域外 6/6 的打分函数**。

## 为什么补这一条（独立收口审计 2026-08-28 抓的）

原来 `run_eval.py` 的 `hard_score()` **一条判据都没有**，而 roadmap、log、plan
三处引用的数字全部由它算出。同一次审计在里面找到**两个恒真的 check**
（`validated` 与 `fallback_explained`）—— 有这么一条哪怕最简单的判据，当场就会被抓到。

⚠️ **恒真的 check 不是「多一层保险」，是「看起来严了但什么都没验」** ——
这与本仓最忌讳的那种失败形态同族：绿着，但验的不是它名字说的那件事。
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from dataclasses import dataclass

_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from agenerp.dsl.blocks import Block, View  # noqa: E402
from agenerp.dsl.fallback import Fallback, RenderPlan  # noqa: E402
from agenerp.dsl.validate import ValidationResult  # noqa: E402


def _scorer():
    """按路径加载跑器。**它不在 `agenerp` 包里** —— 实验设施不进产品包。"""
    path = _ROOT / "tools" / "experiments" / "p2_view_agent" / "run_eval.py"
    assert path.is_file(), "评测跑器不见了，本判据失去被守对象"
    spec = importlib.util.spec_from_file_location("_p2_3_run_eval", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_p2_3_run_eval"] = module
    spec.loader.exec_module(module)
    return module.hard_score


@dataclass
class FakeProposal:
    view: View | None
    validation: ValidationResult | None
    render_plan: RenderPlan | None
    stop_reason: str


def proposal_for(doctype: str, fields: tuple[str, ...], *, block_type: str = "list",
                 fallbacks: tuple[Fallback, ...] = ()) -> FakeProposal:
    view = View(name="v", title="v",
                blocks=(Block(type=block_type, doctype=doctype, fields=fields),))
    return FakeProposal(
        view=view,
        validation=ValidationResult(ok=True, errors=()),
        render_plan=RenderPlan(rendered=view.blocks, fallbacks=fallbacks),
        stop_reason="proposed",
    )


ROW_IN = {"id": "t", "expect_doctype": "Work Order", "must_fields": ["qty"],
          "expect_block_types": ["list"], "domain": "in"}
ROW_OUT = {**ROW_IN, "domain": "out"}


def test_a_correct_answer_passes():
    assert _scorer()(ROW_IN, proposal_for("Work Order", ("qty",)))["passed"]


def test_no_proposal_fails_and_says_so():
    result = _scorer()(ROW_IN, None)
    assert not result["passed"]
    assert result["reasons"], "不通过却说不出为什么，等于没判"


def test_the_wrong_doctype_fails():
    result = _scorer()(ROW_IN, proposal_for("Stock Entry", ("qty",)))
    assert not result["passed"]
    assert any("DocType" in r for r in result["reasons"])


def test_a_missing_must_field_fails():
    result = _scorer()(ROW_IN, proposal_for("Work Order", ("status",)))
    assert not result["passed"]
    assert any("qty" in r for r in result["reasons"])


def test_the_wrong_block_type_fails():
    result = _scorer()(ROW_IN, proposal_for("Work Order", ("qty",), block_type="metric"))
    assert not result["passed"]


def test_a_fallback_fails_the_in_domain_half():
    """🔴 主集的「落回 = 0」是**判据**，不是描述 —— 它必须真的能判失败。"""
    fell = (Fallback(index=0, block_type="list", reason="字段类型画不了"),)
    result = _scorer()(ROW_IN, proposal_for("Work Order", ("qty",), fallbacks=fell))
    assert not result["passed"]
    assert any("落回" in r for r in result["reasons"])


def test_a_fallback_does_not_fail_the_out_of_domain_half():
    """域外**不判落回** —— 那是 P2.2 分母之外，没有「应该画得出来」这个期望。

    ⚠️ 这一条与上一条成对：分开写，才能看出「落回 = 0」到底作用在哪一半上。
    """
    fell = (Fallback(index=0, block_type="list", reason="字段类型画不了"),)
    assert _scorer()(ROW_OUT, proposal_for("Work Order", ("qty",), fallbacks=fell))["passed"]


def test_no_check_is_constantly_true():
    """🔴 恒真的 check 看起来是「多一层保险」，实际什么都没验。

    这一条把两侧各跑一遍、把每个 check 的取值集合并起来 ——
    **任何一个只见过 `True` 的 check 都会被点名。**
    """
    scorer = _scorer()
    seen: dict[str, set[bool]] = {}
    cases = [
        (ROW_IN, proposal_for("Work Order", ("qty",))),
        (ROW_IN, proposal_for("Stock Entry", ("qty",))),
        (ROW_IN, proposal_for("Work Order", ("status",))),
        (ROW_IN, proposal_for("Work Order", ("qty",), block_type="metric")),
        (ROW_IN, proposal_for("Work Order", ("qty",),
                              fallbacks=(Fallback(index=0, block_type="list", reason="x"),))),
        (ROW_OUT, proposal_for("Work Order", ("qty",))),
        (ROW_IN, None),
    ]
    for row, proposal in cases:
        for name, value in scorer(row, proposal)["checks"].items():
            seen.setdefault(name, set()).add(bool(value))

    constant = sorted(name for name, values in seen.items() if values == {True})
    assert not constant, f"这些 check 从来没失败过，等于没在判：{constant}"
