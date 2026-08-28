"""P2.3 判据的夹具：真 schema 快照 + 假站点 + 剧本模型。**零 token、零活栈。**

🔴 **schema 不是我编的。** 用的是 `agenerp/schema/view-schema.json` ——
`agenerp/schema_snapshot.py` 从活站点导出的那一份（8 张表 / 381 字段）。
理由与 `tests/dsl/conftest.py` 逐字同源：**拿一份手写的 schema 去测「字段存在性」，
测的是我编得对不对，不是校验器对不对。**

⚠️ **本层的假 executor 只喂 schema，不代表工具层被测过。**
这些判据验的是**循环**：校验绕不绕得过、错了顶不顶回去、顶不动时交不交。
工具层自己的真实性归 `tests/tools/**` 与 P2.3 Phase 3 的 live 判据。
**这句话写在这里，免得有人以为它守到了。**

⚠️ **不 import `tests/unit/explain_fakes.py`。** 那是 P1.4 的夹具；
两组判据共用一份夹具，改一处就会牵动另一组的红绿。假站点那一份是**唯一**的公共地基
（`tests/tools/conftest.py`），按路径加载。
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from types import ModuleType

from agenerp.dsl.schema import SchemaView
from agenerp.routing import route
from agenerp.routing.capabilities import ModelProfile
from agenerp.routing.config import LlmConfig

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT = REPO_ROOT / "agenerp" / "schema" / "view-schema.json"
TOOLS_CONFTEST = "tests/tools/conftest.py"


def _load(relative_path: str, module_name: str) -> ModuleType:
    """按路径加载仓库里的一个模块。**源文件没了就是红**，不是少跑几条判据。"""
    target = REPO_ROOT / relative_path
    if not target.is_file():
        raise FileNotFoundError(
            f"P2.3 的判据依赖 {relative_path}，但它不存在。"
            "假站点只有一份，源文件没了判据就失去地基。"
        )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_TOOLS = _load(TOOLS_CONFTEST, "_p2_3_tools_conftest")

FakeSite = _TOOLS.FakeSite
client_for = _TOOLS.client_for
doctype = _TOOLS.doctype


# ── 真 schema 快照 ──────────────────────────────────────────────────────────

_RAW = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
SNAPSHOT_FIELDS: list[dict] = _RAW["fields"]
SNAPSHOT_DOCTYPES: tuple[str, ...] = tuple(_RAW["doctypes"])


def schema() -> SchemaView:
    """校验器用的那一份 —— 直接来自活站点导出的快照。"""
    return SchemaView.from_meta_rows(SNAPSHOT_FIELDS)


def site() -> "FakeSite":
    """假站点：DocType 元数据**取自同一份快照**，不另编一套。

    两处口径必须同源 —— 否则模型从工具里看到的字段与校验器认的字段会悄悄错开，
    而那种错开在判据里长得像「模型选错了字段」。
    """
    metas: dict[str, dict] = {}
    for row in SNAPSHOT_FIELDS:
        meta = metas.setdefault(
            row["doctype"], doctype(module="Manufacturing", fields=[])
        )
        meta["fields"].append(
            {
                "fieldname": row["fieldname"],
                "fieldtype": row["fieldtype"],
                "label": row["fieldname"],
                "options": row.get("options") or "",
            }
        )
    return FakeSite(doctypes=metas, rows={name: [] for name in metas})


# ── 剧本模型 ────────────────────────────────────────────────────────────────


class ScriptedModel:
    """按剧本逐条回的假 chat 端点，**收到的载荷逐条留痕**。

    剧本用完之后**重复最后一条**：修复轮那条路径要的就是「模型一再交同一份坏 DSL」，
    而不是「模型忽然沉默」—— 后者会让判据分不清「循环把它顶回去了」与「循环本来就没在跑」。
    """

    def __init__(self, steps: list[dict]) -> None:
        if not steps:
            raise ValueError("剧本不能是空的")
        self.steps = list(steps)
        self.payloads: list[dict] = []

    @property
    def calls(self) -> int:
        return len(self.payloads)

    def tools_offered(self) -> tuple[str, ...]:
        """最后一次调用里，模型可见的工具名。**判「工具面里有没有它」用的就是这个。**"""
        if not self.payloads:
            return ()
        return tuple(
            t["function"]["name"] for t in self.payloads[-1].get("tools", [])
        )

    def __call__(self, payload: dict) -> dict:
        self.payloads.append(payload)
        return self.steps[min(len(self.payloads) - 1, len(self.steps) - 1)]


def usage(prompt: int = 31, completion: int = 17, reasoning: int = 0) -> dict:
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "completion_tokens_details": {"reasoning_tokens": reasoning},
    }


def call(tool: str, call_id: str = "", **params: object) -> dict:
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


def dsl_step(payload: object) -> dict:
    """模型交出 DSL —— 走的是**最终文本**那条路，不是工具调用。

    刻意如此：D2 已裁定校验不进工具面，那么「交视图」这一步也没有理由是工具调用 ——
    多一个工具就多一条「模型不调它就交不出来」的失败形态。
    """
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return {
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": usage(),
    }


def models() -> list[ModelProfile]:
    return [
        ModelProfile(
            name="fake-view-builder",
            capabilities=frozenset({"tool_calling", "long_context", "reasoning", "multi_hop"}),
            is_reasoning_model=False,
        )
    ]


def config() -> LlmConfig:
    """假端点配置。**不读环境变量** —— 判据必须在无凭据的机器上全绿。"""
    return LlmConfig("http://fake-endpoint", "fake-view-builder", "not-a-real-key")


def adapter_for(transport: ScriptedModel):
    """⚠️ 借 `route("explain", …)` 只为**造一个 adapter**。

    视图 Agent 今天**没有自己的任务类目** —— `TASK_CLASSES` 是
    `("permission", "explain", "lineage", "shape")`，加一个要改 owner doc
    `model-management.md` §12.5 那张 machine-read 表（源真相，报人）。
    本层不需要它：`ViewLoop` 的 adapter 是**注入位**，任务类目是产品入口的事。
    这件事记在 plan 的 Phase 3。
    """
    return route("explain", models=models(), config=config(), transport=transport)
