"""入口关口实验设施的判据（假模型 + 假站点，不打网络、不连站点）。

四条断言各自对着一种**会让实验失去意义**的失败模式：

- 门禁开时违规**必**回注 → 不回注的话「有门禁」那两格其实没有门禁；
- 门禁关时不回注但**照样记录** → 不记的话，无门禁那两格只剩一句「答错了」，
  没法回答「它到底漏了什么」；
- token 超限**即中止并记无效** → 不中止的话一次跑飞会吃掉整个实验的预算；
- 四格提示词**字节级相同** → 不同的话测到的是提示词差异，不是门禁差异。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agenerp.site import SiteClient, SiteResponse
from tools.experiments.p1_entry_gate import gate as gate_rules
from tools.experiments.p1_entry_gate.loop import (
    EXCLUDED_TOOLS,
    read_prompt,
    run,
    tool_schemas,
    write_trace,
)
from tools.experiments.p1_entry_gate.llm import DashScopeClient, Usage

QUESTION = "销售订单 SAL-ORD-2026-00001 显示已完成，但成品仓还压着货，这是怎么回事？"

# 假站点：一张 Bin（成品仓 1010）+ 两张使数量增加的凭证 + 一张出库凭证。
# **形状与活站点实读一致**（2026-08-24：入库 = 自制 1000 + 外协收货 1000，出库 = 发货 990）。
SITE_ROWS = {
    "Bin": [
        {"item_code": "HRD-PACK-5K", "warehouse": "成品仓 - HRD", "actual_qty": 1010.0},
    ],
    "Stock Ledger Entry": [
        {"item_code": "HRD-PACK-5K", "warehouse": "成品仓 - HRD", "actual_qty": 1000.0,
         "voucher_no": "MAT-STE-2026-00003", "is_cancelled": 0},
        {"item_code": "HRD-PACK-5K", "warehouse": "成品仓 - HRD", "actual_qty": 1000.0,
         "voucher_no": "MAT-SCR-2026-00001", "is_cancelled": 0},
        {"item_code": "HRD-PACK-5K", "warehouse": "成品仓 - HRD", "actual_qty": -990.0,
         "voucher_no": "MAT-DN-2026-00001", "is_cancelled": 0},
    ],
}


def _site_transport(request):
    import urllib.parse

    path = urllib.parse.unquote(urllib.parse.urlparse(request.url).path)
    doctype = path[len("/api/resource/") :]
    return SiteResponse(200, json.dumps({"data": SITE_ROWS.get(doctype, [])}, ensure_ascii=False))


@pytest.fixture
def site() -> SiteClient:
    return SiteClient("fake", base_url="http://fake", api_key="k", api_secret="s",
                      transport=_site_transport)


class FakeModel:
    """按脚本逐条回话的假模型。**它不判断任何东西**——判断是循环的事。"""

    def __init__(self, script: list[dict], usage: Usage | None = None) -> None:
        self.script = list(script)
        self.calls: list[list[dict]] = []
        self._usage = usage or Usage(prompt=10, completion=5, reasoning=3)

    def __call__(self, payload: dict) -> dict:
        self.calls.append(list(payload["messages"]))
        message = self.script.pop(0) if self.script else {"content": "没有更多脚本了"}
        return {
            "choices": [{"message": message}],
            "usage": {
                "prompt_tokens": self._usage.prompt,
                "completion_tokens": self._usage.completion,
                "completion_tokens_details": {"reasoning_tokens": self._usage.reasoning},
            },
        }


def _llm(script, usage=None) -> DashScopeClient:
    return DashScopeClient("fake-model", api_key="", base_url="", transport=FakeModel(script, usage))


def _run(site, script, *, gate_on: bool, max_tokens: int = 10_000, usage=None):
    llm = _llm(script, usage)
    trace = run(
        question=QUESTION, llm=llm, client=site, gate_on=gate_on,
        max_tokens=max_tokens, run_id="run-test",
    )
    return trace, llm._transport  # noqa: SLF001 —— 判据要看假模型收到了什么


ANSWER_WITHOUT_EVIDENCE = {"content": "成品仓现在有 1010 台，订单已完成。"}
ANSWER_AGAIN = {"content": "成品仓 1010 台 = 入库 2000 − 发货 990，多做了一批。"}


def test_gate_on_forces_a_continuation_when_evidence_is_missing(site):
    """门禁开 + 证据不足 → **必须**回注强制续跑消息，而不是把答案收下。"""
    trace, transport = _run(site, [ANSWER_WITHOUT_EVIDENCE, ANSWER_AGAIN], gate_on=True)

    assert len(trace.gate_checks) >= 1
    assert trace.gate_checks[0]["enforced"] is True
    assert trace.gate_checks[0]["failed"], "证据一件都没取，门禁必须发红"
    injected = [m for m in transport.calls[-1] if m["role"] == "user"]
    assert any("证据不足，还不能作答" in m["content"] for m in injected)


def test_gate_off_records_the_same_red_but_never_injects(site):
    """门禁关 → 判定照做、记录照记，**但不回注**。少了记录就没法比对「它漏了什么」。"""
    trace, transport = _run(site, [ANSWER_WITHOUT_EVIDENCE], gate_on=False)

    assert trace.final_answer == ANSWER_WITHOUT_EVIDENCE["content"]
    assert trace.gate_checks[0]["enforced"] is False
    assert trace.gate_checks[0]["failed"], "门禁关不等于不判定"
    assert not any(
        "证据不足" in (m.get("content") or "")
        for turn in transport.calls
        for m in turn
        if m["role"] == "user"
    )


def test_forced_continuation_never_names_the_missing_documents(site):
    """强制续跑消息**只说缺几件，不说缺哪几件**——说出单号等于把答案递过去。"""
    trace, transport = _run(site, [ANSWER_WITHOUT_EVIDENCE, ANSWER_AGAIN], gate_on=True)

    injected = "\n".join(
        m["content"] for m in transport.calls[-1] if m["role"] == "user" and m["content"]
    )
    assert "还有" in injected and "项证据没有取到" in injected
    for name in ("MAT-SCR-2026-00001", "MAT-STE-2026-00003", "MAT-DN-2026-00001"):
        assert name not in injected, f"门禁把 {name} 递给了模型"


def test_token_ceiling_stops_the_run_and_records_it_invalid(site):
    """token 超限 → 中止并记 `无效`。**无效运行照实记录，不静默丢弃。**"""
    heavy = Usage(prompt=400, completion=400, reasoning=200)
    trace, _ = _run(site, [ANSWER_WITHOUT_EVIDENCE] * 10, gate_on=True,
                    max_tokens=1000, usage=heavy)

    assert trace.invalid is not None
    assert "token 超限" in trace.invalid["reason"]
    assert trace.final_answer == ""
    assert trace.usage["reasoning"] > 0


def test_usage_counts_reasoning_separately(site):
    """三项分开记：`qwen3.6-plus` 按 reasoning token 计费，混进 completion 就算不出成本。"""
    trace, _ = _run(site, [ANSWER_WITHOUT_EVIDENCE], gate_on=False,
                    usage=Usage(prompt=7, completion=11, reasoning=195))

    assert trace.usage == {"prompt": 7, "completion": 11, "reasoning": 195, "total": 18}


def test_the_prompt_is_one_file_and_the_loop_does_not_touch_it(site):
    """四格提示词字节级相同：由**同一个文件**保证，且循环把它原样放进 system 消息。"""
    prompt, digest, size = read_prompt()

    traces = [
        _run(site, [ANSWER_WITHOUT_EVIDENCE], gate_on=on)[0] for on in (True, False)
    ]
    assert {t.prompt_sha256 for t in traces} == {digest}
    assert {t.prompt_bytes for t in traces} == {size}
    for _, transport in [_run(site, [ANSWER_WITHOUT_EVIDENCE], gate_on=on) for on in (True, False)]:
        system = [m for m in transport.calls[0] if m["role"] == "system"]
        assert [m["content"] for m in system] == [prompt]


def test_the_loop_holds_no_second_copy_of_the_prompt():
    """提示词只有一份来源。循环源码里出现第二份副本，四格就可能悄悄分叉。"""
    prompt, _, _ = read_prompt()
    source = Path("tools/experiments/p1_entry_gate/loop.py").read_text(encoding="utf-8")

    for line in [ln.strip() for ln in prompt.splitlines() if len(ln.strip()) > 12]:
        assert line not in source, f"循环里出现了提示词的副本：{line[:30]}"


def test_permission_scope_is_not_offered_to_the_model():
    """`permission.scope` 不在工具面里：它的后置断言断的是编排面的事实（P1.3），
    本设施没实现那件事，递一个 `True` 进去就是断言一件不成立的事。"""
    names = {schema["function"]["name"] for schema in tool_schemas()}

    assert "permission_scope" not in names
    assert EXCLUDED_TOOLS == ("permission.scope",)
    assert len(names) == 9


def test_trace_is_written_with_every_section(site, tmp_path):
    """轨迹结构完整：工具调用序列 / 最终答案 / 门禁判定 / token 三项 / 无效原因。"""
    trace, _ = _run(site, [ANSWER_WITHOUT_EVIDENCE], gate_on=False)

    path = write_trace(trace, tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert set(payload) >= {
        "run_id", "model", "gate", "question", "max_tokens", "prompt_sha256",
        "turns", "gate_checks", "final_answer", "usage", "tool_calls_total", "invalid",
    }
    assert set(payload["usage"]) == {"prompt", "completion", "reasoning", "total"}
    assert payload["gate_checks"][0]["facts"]["documents_named_in_question"] == [
        "SAL-ORD-2026-00001"
    ]


def test_l3_required_vouchers_come_from_the_site_not_from_the_model(site):
    """L3 的触发口径是**答案里的数字**，不是「模型查过 Bin」——
    一个从不查 Bin、却照样报出 1010 的回答，同样要取全入库来源的证。"""
    required = gate_rules.inbound_vouchers_for_answer(site, "成品仓有 1,010 台")

    assert required == ["MAT-SCR-2026-00001", "MAT-STE-2026-00003"]
    assert gate_rules.inbound_vouchers_for_answer(site, "少发了 10 台") == []
