"""确定性导航策略 + 导航质量的度量骨架。**零模型参与**（D-15：规则能覆盖的流程不 Agent 化）。

owner doc 是 `docs/design/context-and-memory.md` §8.1「结构化导航优先」与
`docs/architecture/module-boundaries.md` §7.4（越权探测的实测形状）。

**「导航好不好用」在本仓的口径**（plan `2026-08-24-1601-2` §5.2 D3）：

- 「少走弯路」= 同一组导航任务下，达到「可以开始作答」或「可以明确拒答」所需的
  `execute()` 调用次数，**含开场注入那一次**；站点请求次数**另计一栏**，不与它混。
- on / off 两组**共用同一个策略对象**，唯一差异是开场包里有没有注入产物。
  两组各写一份策略的话，测到的是两份代码的差异，不是注入的差异 —— 因此
  `run_metric` 把它**实际用过的**策略对象记进返回值，判据断言 `on.strategy is off.strategy`
  （**同一性**，不是相等；两份逐位相同的代码产出的数字也逐位相同，只有 `is` 能打红）。
- **不拿真模型跑几次比次数**：P1.0 实测每格 3 次只够看方向、不够算比率。

策略读的是**开场包里已知的事实**（`OpeningPack.readable`），不是「包是不是空的」——
后者是一条旁路分叉，会让 H4 那条反测测不到该测的东西。

`ScopeFirstStrategy` 建模的是 Spike 01 探针 3 实测出来的形状：不知道可见范围时，
撞了 403 也不会就此收手，而是挨个试**能回答同一个问题的其它路线**（实测 35 次工具调用）。
知道可见范围时，一条都不用试。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from agenerp.orchestration.circuit import result_is_permission_denial
from agenerp.orchestration.opening import OpeningPack
from agenerp.site import SiteClient
from agenerp.tools.runtime import Executor, ToolResult, execute

STEP_EXECUTE = "execute"
STEP_ANSWER = "answer"
STEP_REFUSE = "refuse"

TERMINAL_STEPS = (STEP_ANSWER, STEP_REFUSE)

# 探测一条备选路线时用的占位单号。**只用于「这条路线读不读得到」的判定**，
# 不用于取数：撞得到 403 的是 DocType 这一级，与单号无关。
PROBE_NAME = "<probe>"

# 单题的调用上限。策略是可终止的（每一步要么走掉一个未走的 hop、要么试掉一条未试的路线），
# 这条上限是**防呆**：将来有人改策略改出环，判据红在这里而不是挂死。
MAX_STEPS_PER_TASK = 50


class NavigationLoop(RuntimeError):
    """单题超过 `MAX_STEPS_PER_TASK` —— 策略不再可终止了。"""


@dataclass(frozen=True)
class Hop:
    """导航的一跳：一次具体的工具调用。"""

    tool: str
    params: Mapping[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.tool}({','.join(f'{k}={self.params[k]}' for k in sorted(self.params))})"


@dataclass(frozen=True)
class NavigationTask:
    """一道导航题。**题目与预期路径写死在夹具里，不许执行期改题**（硬约束 ②）。

    `alternates` 是「能回答同一个问题的其它 DocType」—— 不知道可见范围时会被挨个试，
    这正是 §7.4 记的越权探测形状。
    """

    name: str
    target: str
    hops: tuple[Hop, ...] = ()
    alternates: tuple[str, ...] = ()


@dataclass(frozen=True)
class Step:
    """策略给出的下一步。`kind` 为 `answer` / `refuse` 时是终点，两者都算终点。"""

    kind: str
    tool: str = ""
    params: Mapping[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass(frozen=True)
class NavigationState:
    """一题跑到当前为止的已知事实。**不可变**：每一步回一个新状态。"""

    pack: OpeningPack
    learned: Mapping[str, bool] = field(default_factory=dict)
    attempted: tuple[str, ...] = ()
    done: tuple[str, ...] = ()

    def readable(self, doctype: str) -> bool | None:
        """该路线读不读得到。`None` = **还不知道**，与「读不到」分开（§5.0 ①）。

        先看本题内学到的，再看开场包。开场包答不上来时才是真的不知道。
        """
        if doctype in self.learned:
            return self.learned[doctype]
        return self.pack.readable(doctype)

    def after(self, doctype: str, hop_key: str, result: ToolResult) -> NavigationState:
        learned = dict(self.learned)
        if result_is_permission_denial(result):
            learned[doctype] = False
        elif result.ok:
            learned[doctype] = True
        return replace(
            self,
            learned=learned,
            attempted=(*self.attempted, doctype) if doctype not in self.attempted else self.attempted,
            done=(*self.done, hop_key) if hop_key and result.ok else self.done,
        )


class ScopeFirstStrategy:
    """先看可见范围，再决定取什么。**一个可调用对象，on / off 两组共用同一个实例。**

    四条规则，按序：

    1. 目标路线**已知不可读**且所有备选路线也已知不可读 → **明确拒答**（终点）。
    2. 目标路线**已知可读** → 逐个走它的 hop；走完 → **可以开始作答**（终点）。
    3. 还有没试过的路线 → 试下一条。试目标路线就是**直接走它的第一跳**
       （不另发一次探测：撞不撞得到 403 由这一跳自己说话）。
    4. 路线全试完仍无一可读 → 拒答（终点）。
    """

    def __call__(self, task: NavigationTask, state: NavigationState) -> Step:
        routes = (task.target, *task.alternates)

        if state.readable(task.target) is True:
            for hop in task.hops:
                if hop.key not in state.done:
                    return Step(STEP_EXECUTE, hop.tool, hop.params, f"取 {hop.tool}")
            return Step(STEP_ANSWER, reason=f"{task.target} 可读且取数已完成")

        for route in routes:
            if route != task.target and state.readable(route) is True:
                return Step(STEP_ANSWER, reason=f"改走备选路线 {route}")

        for route in routes:
            if state.readable(route) is None and route not in state.attempted:
                if route == task.target and task.hops:
                    hop = task.hops[0]
                    return Step(STEP_EXECUTE, hop.tool, hop.params, f"试目标路线 {route}")
                return Step(
                    STEP_EXECUTE,
                    "doc.get",
                    {"doctype": route, "name": PROBE_NAME},
                    f"试备选路线 {route}",
                )

        return Step(
            STEP_REFUSE,
            reason="你的权限不足以回答这个问题：" + "、".join(routes) + " 均不可读",
        )


@dataclass(frozen=True)
class TaskMetric:
    """一题的度量。两栏分开记（§6 计数口径），不合并成一个数。"""

    task: str
    execute_calls: int
    site_requests: int
    ending: str


@dataclass(frozen=True)
class MetricRun:
    """一组任务在一种开场包下的度量结果。

    `strategy` 是骨架**实际用过的**那个对象 —— 「两组共用策略」因此是结构上可断言的
    （`on.strategy is off.strategy`），不只是一句约定。
    """

    label: str
    strategy: Any
    tasks: tuple[TaskMetric, ...] = ()

    def by_task(self) -> dict[str, TaskMetric]:
        return {metric.task: metric for metric in self.tasks}

    def calls(self, task: str) -> int:
        return self.by_task()[task].execute_calls

    def requests(self, task: str) -> int:
        return self.by_task()[task].site_requests


def run_metric(
    strategy: Any,
    opening_pack: OpeningPack,
    tasks: Sequence[NavigationTask],
    *,
    client: SiteClient,
    label: str = "",
    executors: Mapping[str, Executor] | None = None,
) -> MetricRun:
    """把同一个 `strategy` 在给定开场包下跑一组任务，逐题计数。

    计数口径（§6，跑之前写死的）：`execute_calls` 含开场注入那一次
    （由 `OpeningPack.execute_calls` 带进来）；`site_requests` 是
    `ToolResult.request_count` 之和，**另计一栏**；终点是「可以开始作答」或「可以明确拒答」。
    """
    metrics: list[TaskMetric] = []
    for task in tasks:
        state = NavigationState(pack=opening_pack)
        calls = opening_pack.execute_calls
        requests = opening_pack.cost.request_count
        for _ in range(MAX_STEPS_PER_TASK):
            step = strategy(task, state)
            if step.kind in TERMINAL_STEPS:
                metrics.append(TaskMetric(task.name, calls, requests, step.kind))
                break
            result = execute(
                step.tool, step.params, client=client, context=None, executors=executors
            )
            calls += 1
            requests += result.request_count
            state = state.after(
                str(step.params.get("doctype") or task.target),
                Hop(step.tool, step.params).key,
                result,
            )
        else:
            raise NavigationLoop(f"{task.name} 超过 {MAX_STEPS_PER_TASK} 步仍未到终点")
    return MetricRun(label=label, strategy=strategy, tasks=tuple(metrics))
