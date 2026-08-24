"""P1.4 判据的共用假件：**一个假模型端点 + 一个假站点**，零网络、零凭据、零 docker。

**假站点不在这里定义。** 工具执行层那份 `FakeSite` 只有一份，在
`tests/tools/conftest.py`；本模块**按路径把它加载进来**，不复制、不另写。
两份假站点会各自漂移，而它们正是本 plan 全部判据的地基。

为什么是「按路径加载」而不是「搬到 `tests/` 根下再由 conftest 再导出」
（plan `2026-08-24-1755-1` 的 `Decision` D5 给了这两条形状，本模块选后者）：
搬家要动 `tests/tools/conftest.py`，那是 P1.0a / P1.3 已收口判据面的地基（plan §8 风险 ④）；
按路径加载**一个字都不动它**，代价只是本模块多一个加载器。
先例是人做 `3b6d071` 时用的同一招（`tests/gates/test_tool_execution_live.py`
的 `_load_sibling_module`）。

⚠️ **实测补出的一处差别，照实记**：先例那个加载器**没有**把模块塞进 `sys.modules`，
而 `tests/tools/conftest.py` 的模块级 `@dataclass` 在那种加载方式下当场炸
（`dataclasses._is_type` 反查 `sys.modules[cls.__module__]` 拿到 `None`）。
所以下面的 `load_repo_module` **必须**先注册再 `exec_module` —— 这一行不是冗余。

⚠️ `from tests.tools.conftest import FakeSite` 这条路**不成立**（`tests/` 没有
`__init__.py`，不是包）—— 起草期与执行期各实测一次，别再试第三遍。
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from types import ModuleType

from agenerp.routing.capabilities import ModelProfile
from agenerp.routing.config import LlmConfig

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

TOOLS_CONFTEST = "tests/tools/conftest.py"


def load_repo_module(relative_path: str, module_name: str) -> ModuleType:
    """按路径加载仓库里的一个模块。**源文件没了就是红**，不是少跑几条判据。"""
    target = REPO_ROOT / relative_path
    if not target.is_file():
        raise FileNotFoundError(
            f"P1.4 的判据依赖 {relative_path}，但它不存在。"
            "工具执行层的假站点只有一份，源文件没了判据就失去地基。"
        )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    # 先注册再执行：模块级 `@dataclass` 会反查 `sys.modules[cls.__module__]`。
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_TOOLS = load_repo_module(TOOLS_CONFTEST, "_p1_4_tools_conftest")

FakeSite = _TOOLS.FakeSite
client_for = _TOOLS.client_for
doctype = _TOOLS.doctype


# ── 假模型端点 ──────────────────────────────────────────────────────────────


class ScriptedModel:
    """按剧本逐条回的假 chat 端点，**收到的载荷逐条留痕**。

    剧本用完之后**重复最后一条**：强制续跑那条路径要的就是「模型一再给同一个
    取证不足的答案」，而不是「模型忽然沉默」——后者会让判据分不清
    「门禁拦住了」与「循环本来就不作答」。
    """

    def __init__(self, steps: list[dict]) -> None:
        if not steps:
            raise ValueError("剧本不能是空的")
        self.steps = list(steps)
        self.payloads: list[dict] = []

    @property
    def calls(self) -> int:
        return len(self.payloads)

    def __call__(self, payload: dict) -> dict:
        self.payloads.append(payload)
        return self.steps[min(len(self.payloads) - 1, len(self.steps) - 1)]


def usage(prompt: int = 31, completion: int = 17, reasoning: int = 11) -> dict:
    """端点自报的 token 账。`total_tokens = prompt + completion`（D-11 实读的形状）。"""
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "completion_tokens_details": {"reasoning_tokens": reasoning},
    }


def call(tool: str, call_id: str = "", **params: object) -> dict:
    """一次工具调用。工具名按线上形状写下划线版（`doc.get` → `doc_get`）。"""
    return {
        "id": call_id or f"call-{tool}",
        "type": "function",
        "function": {
            "name": tool.replace(".", "_"),
            "arguments": json.dumps(params, ensure_ascii=False),
        },
    }


def tools_step(*calls: dict) -> dict:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": None, "tool_calls": list(calls)},
                "finish_reason": "tool_calls",
            }
        ],
        "usage": usage(),
    }


def answer_step(text: str) -> dict:
    return {
        "choices": [
            {"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
        ],
        "usage": usage(),
    }


def models() -> list[ModelProfile]:
    """一个能力齐全的假档案。**能力校验本身归 `tests/routing`**，本 plan 不重复覆盖。"""
    return [
        ModelProfile(
            name="fake-explainer",
            capabilities=frozenset({"tool_calling", "long_context", "reasoning", "multi_hop"}),
            is_reasoning_model=True,
        )
    ]


def config() -> LlmConfig:
    """假端点配置。**不读环境变量** —— 判据必须在无凭据的机器上全绿。"""
    return LlmConfig("http://fake-endpoint", "fake-explainer", "not-a-real-key")


# ── 假站点的数据 ────────────────────────────────────────────────────────────

ORDER_A = "SAL-ORD-2026-00001"
ORDER_B = "SAL-ORD-2026-00002"
SUBMITTED_DN = "MAT-DN-2026-00001"
CANCELLED_DN = "MAT-DN-2026-00002"
DRAFT_WO_A = "MFG-WO-2026-00001"
DRAFT_WO_B = "MFG-WO-2026-00002"
INBOUND_A = "MAT-STE-2026-00001"
INBOUND_B = "MAT-STE-2026-00002"

ITEM = "HRD-PACK-5K"
WAREHOUSE = "成品仓 - HRD"
BIN_QTY = 1010

SCOPE_CANDIDATES = ("Sales Order", "Delivery Note", "Stock Entry")


def explain_site() -> "FakeSite":
    """两条会让错误实现分叉的轨迹，摆在同一个站点上（D2 的绑定断言要用）：

    - `SAL-ORD-2026-00001` → 下游有一张**已提交**发货单（L2 因此要求逐张 `doc.get`）
    - `SAL-ORD-2026-00002` → 下游只有一张**草稿**工单（L2 因此空过）

    外加一条库存轨迹：`Bin` 上 1,010 台，库存流水里两张使数量增加的凭证
    （另有一张出库、一张已取消，**都不该进 L3 的要求集**）。
    """
    return FakeSite(
        doctypes={
            "Sales Order": doctype(
                is_submittable=1,
                fields=[
                    {"fieldname": "customer", "fieldtype": "Link", "options": "Customer",
                     "label": "客户", "in_list_view": 1},
                    {"fieldname": "items", "fieldtype": "Table",
                     "options": "Sales Order Item", "label": "明细"},
                ],
            ),
            "Sales Order Item": doctype(istable=1, fields=[
                {"fieldname": "item_code", "fieldtype": "Data", "label": "物料"},
            ]),
            "Delivery Note": doctype(is_submittable=1, fields=[
                {"fieldname": "items", "fieldtype": "Table",
                 "options": "Delivery Note Item", "label": "明细"},
            ]),
            "Delivery Note Item": doctype(istable=1, fields=[
                {"fieldname": "against_sales_order", "fieldtype": "Link",
                 "options": "Sales Order", "label": "对应订单"},
            ]),
            "Work Order": doctype(module="Manufacturing", is_submittable=1, fields=[
                {"fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order",
                 "label": "销售订单"},
            ]),
            "Stock Entry": doctype(module="Stock", is_submittable=1, fields=[
                {"fieldname": "items", "fieldtype": "Table",
                 "options": "Stock Entry Detail", "label": "明细"},
            ]),
            "Stock Entry Detail": doctype(istable=1, fields=[
                {"fieldname": "item_code", "fieldtype": "Data", "label": "物料"},
            ]),
            "Bin": doctype(module="Stock", fields=[]),
            "Stock Ledger Entry": doctype(module="Stock", fields=[]),
            "Customer": doctype(fields=[]),
            "Company": doctype(module="Setup", fields=[]),
            "GL Entry": doctype(module="Accounts", fields=[]),
        },
        rows={
            "Module Def": [
                {"name": "Selling", "app_name": "erpnext"},
                {"name": "Manufacturing", "app_name": "erpnext"},
                {"name": "Stock", "app_name": "erpnext"},
                {"name": "Setup", "app_name": "erpnext"},
                {"name": "Accounts", "app_name": "erpnext"},
            ],
            "Company": [{"name": "恒锐动力科技有限公司", "doctype": "Company"}],
            "Sales Order": [
                {
                    "name": ORDER_A, "doctype": "Sales Order", "docstatus": 1,
                    "customer": "北方新能源工程有限公司",
                    "items": [{"name": "soi-1", "item_code": ITEM, "qty": 1000}],
                },
                {
                    "name": ORDER_B, "doctype": "Sales Order", "docstatus": 1,
                    "customer": "南方装备制造有限公司",
                    "items": [{"name": "soi-2", "item_code": ITEM, "qty": 20}],
                },
            ],
            "Delivery Note": [
                {"name": SUBMITTED_DN, "doctype": "Delivery Note", "docstatus": 1, "items": []},
                {"name": CANCELLED_DN, "doctype": "Delivery Note", "docstatus": 2, "items": []},
            ],
            "Delivery Note Item": [
                {"name": "dni-1", "parent": SUBMITTED_DN, "parenttype": "Delivery Note",
                 "against_sales_order": ORDER_A},
                {"name": "dni-2", "parent": CANCELLED_DN, "parenttype": "Delivery Note",
                 "against_sales_order": ORDER_A},
            ],
            "Work Order": [
                {"name": DRAFT_WO_A, "doctype": "Work Order", "docstatus": 0,
                 "sales_order": ORDER_A},
                {"name": DRAFT_WO_B, "doctype": "Work Order", "docstatus": 0,
                 "sales_order": ORDER_B},
            ],
            "Stock Entry": [
                {"name": INBOUND_A, "doctype": "Stock Entry", "docstatus": 1, "items": []},
                {"name": INBOUND_B, "doctype": "Stock Entry", "docstatus": 1, "items": []},
            ],
            "Bin": [
                {"name": "bin-1", "doctype": "Bin", "item_code": ITEM,
                 "warehouse": WAREHOUSE, "actual_qty": BIN_QTY},
            ],
            "Stock Ledger Entry": [
                {"name": "sle-1", "item_code": ITEM, "warehouse": WAREHOUSE,
                 "actual_qty": 1000, "voucher_no": INBOUND_A, "is_cancelled": 0},
                {"name": "sle-2", "item_code": ITEM, "warehouse": WAREHOUSE,
                 "actual_qty": 10, "voucher_no": INBOUND_B, "is_cancelled": 0},
                {"name": "sle-3", "item_code": ITEM, "warehouse": WAREHOUSE,
                 "actual_qty": -5, "voucher_no": SUBMITTED_DN, "is_cancelled": 0},
                {"name": "sle-4", "item_code": ITEM, "warehouse": WAREHOUSE,
                 "actual_qty": 50, "voucher_no": "MAT-STE-2026-00009", "is_cancelled": 1},
            ],
        },
    )
