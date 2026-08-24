# 工具契约层 · 定制包与 GitOps

> 模块之间靠什么说话：工具契约层的形状，以及定制包如何用 GitOps 管住「系统形态」这件事。§11.2 是防死亡螺旋的承重段。

| | |
|---|---|
| 来源 | 由 `ARCHITECTURE.md`（草案 v0.6，69KB/1159 行）于 2026-08-20 按语义拆分而来 · 证据仓 `1c622c8` |
| 原文 | `${XM}/docs/next/ARCHITECTURE.md`（**冻结，不再更新**；本文件是唯一在演进的版本） |
| 索引 | [docs/architecture/README.md](../architecture/README.md) |

> **章节编号保持原样**（§1、§7、§11.2 …），因为主计划的 `REF:` 表按标题原文定位。**改标题等于断链**，要改先改 [REF 表](../masterplan/README.md)。

---

## 7. 工具契约层

### 7.1 契约结构

```yaml
tool: doc.submit
target: Delivery Note
risk: L2
requires_permission: [Delivery Note.submit]
preconditions:
  - 存在关联的 Loss Review 且 status == Approved   # 来自行业包规则
  - 所有明细行 warehouse 非空
postconditions:                                    # 后置断言，执行后必须成立
  - docstatus == 1
  - 对应 Stock Ledger Entry 数量 == 明细合计
  - GL 借贷相等
on_violation: rollback_and_report
approval: required_if(金额 > 阈值)
```

**`rollback_and_report` 的确切语义（Spike 05 实测确定）**：

> **rollback = 在工具执行入口开数据库 savepoint，后置断言不成立时 `frappe.db.rollback(save_point=...)`。**
> 实测：单据、Stock Ledger Entry、GL Entry、**naming series 计数器**全部回退，
> **不产生作废单、不产生反向分录、不产生单号空洞**。
> **绝不是 cancel / amend** —— cancel 是用户的业务动作，不是契约的补偿机制。

它成立依赖三个**ERPNext 的实现细节，不是承诺**，必须纳入 CI 回归：

| # | 前提 | 实测值 | 失效后果 |
|---|---|---|---|
| 1 | 提交路径不自行 `db.commit()` | **0 次**（普通与倒填日期提交均为 0） | 回滚够不着 |
| 2 | 提交路径不 `enqueue` 后台任务 | **0 次** | 任务对着已回滚的数据跑 |
| 3 | 无事务外副作用（邮件、文件、webhook） | 需按契约逐个声明 | 回滚不掉外部动作 |

→ 因此**写契约必须声明它是否产生事务外副作用**；产生的，`on_violation` 只能是
`abort_before_side_effect`，不能是 `rollback_and_report`。

### 7.2 为什么必须是契约而不是裸工具

现有所有 ERPNext MCP 桥都是把 DocType CRUD 直接暴露成工具，靠模型自己规划。问题：

- Agent 能做什么由 prompt 决定 → prompt 可被注入、可被绕过
- 失败后无补偿语义
- 无法客观判定「做对了没有」

**契约把这三件事外置成可检视的声明**，与 prompt 无关。即使模型被诱导，前置条件不满足就执行不了，后置断言不成立就回滚。

### 7.3 与 Frappe 既有门禁的关系

契约的前置条件**不替代** `hooks.doc_events`，而是**镜像并前移**它：

- `before_submit` 是最后防线，**永远保留，永远生效**
- 契约前置条件让 Agent 在调用前就知道会失败，从而能解释、能补救，而不是撞墙后重试

### 7.3.1 只读工具也有契约（Spike 02 产出）

契约不只约束写操作。只读工具的契约约束两件事：

1. **什么时候允许停下来** —— 证据充分性门禁，见 §5.0 ①
2. **返回什么** —— `returns` 裁剪规则

第 2 条是实测踩出来的：`permission.scope` 的第一版把后端能查到的权限原样返回，
老板 83 个 DocType、工人 61 个，**其中约九成是 Frappe 框架管道**，纯 token 噪声。
`doc.get` 若不裁剪同样会把 `_comments` / `_liked_by` 之类倒给模型。

→ §7.1 的契约结构应补上 `returns` 段：声明裁剪规则、上限条数、以及**必须保留什么**
（如 `doc.links` 必须返回 `from_is_submittable`，否则下游筛选会整类丢掉不可提交的
业务单据——见 §5.0 ①）。

### 7.4 权限拒绝熔断（实测产出的硬规则）

Spike 01 探针 3 实测：以车间工人身份（仅可读 3 个 DocType）询问毛利，模型工具调用量从约 7 次放大到 **35 次**——它在挨个尝试 GL Entry、Payment Entry、Journal Entry、Landed Cost Voucher、Cost Center、Serial and Batch Bundle…… 系统性寻找绕过路径。

模型的最终回答是正确的（明确拒绝作答、未编造数字），**但过程本身有两个问题**：

1. **成本**：一个越权问题烧掉约 5 倍 token。中小企业负担不起。
2. **治理**：连续大量权限拒绝，在审计视角下就是**越权探测特征**——无论 Agent 是否有意。

因此契约层必须设置熔断，且**不能依赖模型自觉**：

| 规则 | 行为 |
|---|---|
| 单次会话内连续 N 次权限拒绝（建议 N=5） | 立即终止工具调用循环 |
| 终止后 | 向用户明确返回「你的权限不足以回答这个问题」，并给出所需权限清单 |
| 同时 | 写入审计，标记为权限探测事件 |

配合 `permission.scope`，理想路径是 Agent 在**第一次查询之前**就判定「此问题超出我的可见范围」，而不是撞 35 次墙。

**落点（2026-08-24，P1.3）**：`agenerp/orchestration/circuit.py` 的 `DenialBreaker`。
plan [`2026-08-24-1601-2`](../plans/p1-insight/2026-08-24-1601-2-navigation-orchestration-v0.md)。

| 项 | 落地形态 |
|---|---|
| N | 默认 **5**（`DENIAL_THRESHOLD`，本节建议值） |
| 「连续」语义 | **连续，不是累计**：中间成功一次即清零。累计版会把一个跑了两小时、零星撞过 5 次权限边界的正常会话误刹，判据 `test_a_success_in_the_middle_clears_the_streak` 钉住它 |
| 拒绝的识别口径 | **只有 HTTP 403** 算权限拒绝，沿用 `agenerp/tools/site_scope.py` 的 `doctypes_with_data` 那条实测口径。站点宕机 / 超时 / 5xx **不计进熔断计数** —— 那会把「站点坏了」读成「你没权限」 |
| 非 403 失败的处理 | **既不计数、也不清零**。当成清零处理就给「每两次 403 之间制造一次超时」留了一条绕过路径；当成计数就把一次站点故障读成一次越权探测 |
| 终止时给出什么 | 固定文案「你的权限不足以回答这个问题」+ **所需权限清单**（形如 `read:GL Entry`，**指名 DocType**） |
| 两处 403 口径的一致性 | 靠一条**行为级**断言绑定：拿 `FakeSite` 驱动 `doctypes_with_data` 两次（403 那次进 `unreadable`、非 403 那次原样抛出），断言编排层对同样两种输入给出相同分类。**不比源码文本** |

~~⚠️ **接到真实控制循环上是 P1.4 的动作，本期没做。**~~
✅ **已接线（2026-08-24，P1.4）**：`agenerp/explain/loop.py` 的 `ExplainLoop._execute_one()`
在**每一次** `execute` 之后喂 `DenialBreaker.record(result, doctype=...)`，`tripped` 为真即
**停止再发工具调用**（同一批里剩下的调用也不发）并返回 `report()`。
「真实会话里它一定被调用到」由 `tests/unit/test_explain_loop.py::test_breaker_stops_the_loop_after_five_consecutive_denials`
判定：判据数的是**循环发起的 `execute` 次数**（不是站点收到的 HTTP 请求数），
剧本一批给 6 个调用、实测只发出 5 个。落点节见 §7.8。

~~⚠️ **本节的「写入审计，标记为权限探测事件」那一行本期未落地**~~
✅ **已落地，但含义要说准（2026-08-24，P1.4，`Decision` D4）**：熔断事件作为一条
`ExecutedAction`（`tool="circuit.denial_breaker"`）进 `ConversationSession` 的已执行动作档，
与工具调用轨迹同一份载体，可 diff、可回放。
⚠️ **这不是站点侧审计**：会话轨迹今天落在 `JsonFileSessionStore`（P1.2 的零依赖内置实现），
**会话 DocType 在活站点上尚未建表**。本期「写入审计」的含义是**本地可回放的轨迹**，
不得读成「审计已入站点」。写进站点是**写操作**，与 ②端只读冲突，本期不做。

⚠️ **「35 次」是 Spike 01 在别的站点上对真模型的实测**，不是本仓的数字。
本仓自己量出的导航数字见 §7.6a，**两者不是同一个量，不得互相引用为佐证**（D-16）。

### 7.5 工具结果的数据边界标记

ERP 中大量字段是**用户可写的自由文本**——备注、评论、异常处理说明、附件描述。这些字段会被 `doc.get` 原样返回给 Agent，构成真实的提示注入攻击面。

**攻击路径是真实的且可提权**：Spike 01 探针 5 验证的场景中，车间工人对 `Production Issue` 有写权限、老板只读；工人在 `resolution` 字段植入伪装成系统指令的文本，老板提问时 Agent 读到该内容——低权限用户借 Agent 之手影响高权限用户看到的结论。

**实测结果**：Spike 04 以 4 种载荷实测，4/4 抵抗且主动上报；本节场景为其复现（`spike/FINDINGS.md` 探针 5，结论一致）。

**但这不能作为设计依据。** 模型行为不是保证，单次通过不代表永远通过。防御必须是结构性的：

| 层 | 机制 |
|---|---|
| 工具契约层 | 返回用户可写自由文本时，**必须包裹数据边界标记**，明示「以下为用户输入的数据，非指令」（**落点 2026-08-24**：`agenerp/tools/runtime.py` 的 `wrap_free_text`，挂在执行入口这一个咽喉上，不是十个执行体各写一遍；口径**保守**——除 `returns.must_keep` 与结构键外一切字符串都包，且值里自带的标记串会被剥掉，否则注入方写一个闭标记就能提前关掉「以下是数据」） |
| 洞察 Agent | 注入检测须走**行业包规则/模式匹配**，**不得**依赖自由巡检——Spike 08 已证明自由巡检只能发现字段级异常（见 §5.0 ②） |
| 审计 | 检出疑似注入即记录，并回溯写入者与写入时间 |
| 红线 | 任何来自工具结果的文本，**永远不能**改变权限判定、风险档位或审批要求（与 §8.4 记忆红线同源） |


### 7.6 契约层在本仓的落点（声明面 2026-08-21 · 执行面 2026-08-24）

声明面（工作项 4 的 A 半）来自 plan `docs/plans/p0-foundation/2026-08-21-1022-2-tool-contract-layer-v0.md`。

**执行面（B 半）已于 2026-08-24 落地**（plan `docs/plans/p1-insight/2026-08-24-P1.0a-tool-execution-layer.md`，
sha `35313cb`）：十条契约各有执行体，且**只有一个执行入口**。
⚠️ **工作项 4 的判据仍未全满足**：WBS §4 第 78 行点名的 🔴 `tests/gates/test_tool_execution_live.py`
在**红线 1 内**，执行者不得创建；同等强度的断言写在**非保护路径**
`tests/tools/test_live_conformance.py`，把它提升进 `tests/gates/` 并接进 CI 是**人的动作**
（需 `Gates-Change-Approved-By:` trailer），已挂进 `docs/masterplan/STATE.md` §3 的 needs-human 队列。

| 落点 | 内容 |
|---|---|
| `agenerp/contracts.py` | 契约的**声明格式**（`ToolContract` / `Returns` / `Condition`）与**校验器**（`validate` / `check` / `validate_registry`），外加前置条件与后置断言的**求值面**（`Condition.evaluate` 对注入进来的 `ReadOnlyContext` 求值，**不连任何站点**） |
| `agenerp/tools_readonly.py` | 十个只读工具的契约声明（`READONLY_CONTRACTS`） |
| `tests/contracts/` | 判据文件：格式组 / 前置条件组 / 后置断言组 / 十工具清单与实测硬约束回归 |
| `agenerp/tools/runtime.py` | **执行入口**（B 半）：四步序 `check_preconditions` → 打站点 → 按 `returns` 裁剪（剥框架管道字段 / `max_rows` 截断 / `must_keep` 核对 / §7.5 数据边界标记）→ `check_postconditions`。**③ 与 ④ 不可颠倒**：后置断言判的是**给出去的东西**。外加 `Session`——执行体与站点之间的唯一通道，逐条记调用留痕 |
| `agenerp/tools/{site_scope,documents,queries}.py` | 十个执行体，逐条照契约原文实现，各自只负责「打站点、拼返回值」 |
| `agenerp/tools/registry.py` | 契约 ↔ 执行体的注册表；双向判据在 `tests/tools/test_registry_pairing.py` |
| `agenerp/seedusers.py` | 受限身份「车间工人」的**幂等**装载步骤（只读 3 个 DocType）。`permission.scope` 的判别力此前在只有 Administrator 的站点上验不出来 |
| `tests/tools/` | 判据文件：执行入口组 / 十执行体组（假站点）/ 双向注册组 / **活站点合规组**（无凭据时 skip 并打印理由） |

**运行时表达形式是纯 Python 而不是 YAML。** §7.1 的 YAML 是文档呈现形式：CI 的 `gates-l1` 只 `pip install pytest`，
`import yaml` 会红在缺依赖上。校验器接受的是**已解析的数据结构**，将来外挂一个 YAML → dict 加载器不改变本层任何签名。

**十个工具的清单与选法**（owner doc 只写「10 个只读工具」，没给过清单；这是 plan 的 `Decision`，写在这里供人复核）：

| 来源 | 工具 |
|---|---|
| `docs/design/agents-and-roles.md` §5.1 解释 Agent | `query.read`、`schema.search`、`snapshot.read`、`lineage.trace`、`rule.lookup`、`system.overview`、`permission.scope` |
| §5.0 ① 证据充分性门禁与 `docs/design/context-and-memory.md` §8.1 结构化导航 | `doc.get`、`doc.links`、`meta.fields` |

排除项与理由：`anomaly.scan` / `benchmark.compare` 属洞察 Agent，依赖行业包规则（P1 才有）；
`dsl.schema` / `field.catalog` / `dsl.validate` / `dsl.preview` 属视图 Agent，依赖视图 DSL（P2 才有）。
选法是「P0 阶段就有真实约束可写的只读工具」，不是随手凑十个。
**换清单的代价很低**：改 `agenerp/tools_readonly.py` 的声明与 `tests/contracts/` 的清单断言，契约格式本身不受影响。

**哪些实测硬约束被表达成了可断言的东西**（写在声明里而不是注释里——注释不可测）：

| 约束 | 出处 | 表达为 |
|---|---|---|
| `permission.scope` 必须逐个调 `frappe.has_permission`，禁止从 DocPerm 反推 | §5.1 实现约束 1 | 后置断言 `permission_probe_method == "has_permission"` |
| `permission.scope` 必须按 app 过滤框架 DocType（83/61 → 34/12） | §5.1 实现约束 2、§7.3.1 | `returns.trim_rules` |
| `permission.scope` 由控制循环开场自动注入 | §5.1 Spike 02 复测 | 后置断言 `injected_at_session_start` |
| `doc.links` 必须保留 `from_is_submittable` | §7.3.1 | `returns.must_keep` + 后置断言 |
| `lineage.trace` 必须同时扫主表级与子表级 Link 并回溯父单据 | §5.1「硬约束」 | 三条后置断言 |
| `doc.get` 裁掉 `_comments` / `_liked_by` 一类框架字段 | §7.3.1 | `returns.trim_rules` |
| `doc.get` 会返回用户可写自由文本 | §7.5 | `returns.user_writable_free_text = True`（**声明位**） |
| 证据充分性门禁 L1/L2 | §5.0 ① | 作答类工具（`query.read` / `snapshot.read`）的 `preconditions` |

门禁挂在作答类工具而不是 `doc.get` / `doc.links` 上，是因为后两者本身就是 L1/L2 要求的**取证步骤**——
拿门禁去卡取证步骤是循环依赖（L1 卡住第一次 `doc.links` 就再也调不出 `doc.links`）。

**哪些没有被表达**（v0 只有声明面，运行时部件不在内）：

- §7.4 的**权限拒绝熔断**（N=5）与 §7.5 的**数据边界标记包裹动作**——二者是控制循环的运行时部件，
  `docs/masterplan/02-WBS.md` 的 P0 段没有任何一行对应它们，且 P0 还没有控制循环去消费它们。
  §7.5 在 v0 里只留**声明位**，包裹动作归 P1。处置见 plan 的 `## Deferred But Adjudicated`。
- ~~**工具的运行时执行器**：十条契约今天只有声明，没有一条被真正调用过（属 P1 控制循环）。~~
  **2026-08-24 已不成立**：执行器已落地（见上表），十个工具在活站点上各跑过一次并守约
  （`tests/tools/test_live_conformance.py`，带凭据实跑 exit 0）。
  ~~§7.4 的**权限拒绝熔断**（N=5）仍未做——它是**控制循环**的行为，不是工具的，归 P1.0 的控制循环。~~
  **2026-08-24 两处均已改准**：① P1.0 交付的是**实验设施**（`tools/experiments/`，模块头逐字「不进 `agenerp/`」）且已 `done`，熔断从来没有在它名下被做过——那是一条**责任人空缺的悬空条目**，不是别人的欠账；② 熔断已由 **P1.3** 落地在 `agenerp/orchestration/circuit.py`，落点见 §7.4 末尾与 §7.6a。~~**但它尚未接到任何真实控制循环上**，接线归 P1.4。~~ **2026-08-24 已接线（P1.4）**：`agenerp/explain/loop.py` 的 `ExplainLoop`，落点节见 §7.8。

**执行面落地时实测出来的三条限制，照实记在这里**（2026-08-24，活站点 `frontend`）：

1. **受限身份枚举不出 DocType 清单。** stock Frappe 只把 `DocType` 的读权限给
   System Manager / Administrator（实读该 DocType 的 `DocPerm` 只有这两条），
   且对它建 `Custom DocPerm` **不生效**（授了 read 之后 `has_permission("DocType")` 仍为 `False`）。
   → `permission.scope` 的候选集因此**可以由调用方给**（`doctypes` 参数），
   发现式默认路径只对有元数据读权限的身份成立。**不靠给工人发 System Manager 绕过去**——
   那等于把「受限」这件事取消掉，判别力也就没了。
2. **REST 面上没有批量计数端点。** 「只回有数据的 DocType」这条裁剪规则要对每个候选调一次
   `frappe.client.get_count`：本站点 239 次、约 2 秒。虚拟 DocType 必须排掉——它们没有物理表，
   计数回 `{}`（无 `message`）而不是 0（实测 `Bulk Transaction Log`，`is_virtual = 1`）。
3. **「过程约束」类后置断言只能从调用留痕上推。** `permission.scope` 的「必须逐个调
   `has_permission`」、`query.read` 的「不得跨表拼装」在返回值上看不出来，
   `Session` 的调用记录是它们唯一的可验形态。**残余弱点**：它验得了「调没调」，
   验不了「每次调用的参数语义都对」。

**一处 owner-doc 字段名漂移，就地裁定**：本文件 §7.3.1 写 `from_is_submittable`，
`docs/analysis/2026-08-19-pre-build-validation.md 的「五、未排除的残余风险」节` 写 `is_submittable`。
**架构文档是 owner，实现取 `from_is_submittable`**；`docs/analysis/` 那份是历史分析记录，**不改它**（改它等于销毁证据）。
接活站点实现 `doc.links` 时以 Frappe 的真实返回字段名为准复核；若两者都不对，回来改本文件——那是人的动作。

**判据缺口，如实记在这里**：`python3 -m pytest tests/contracts -q` **不在** `missions/p0-foundation.json` 的 `commands.test` 里
（那条是 `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`），因此 `GATE_VERIFY` 复跑不到它。
`missions/**` 是角色 B 禁区，loop 无权自己补。代偿控制是独立关闭审计。人要补上，把该命令加进 `commands.test` 即可。

### 7.6a 编排层在本仓的落点（P1.3 · 2026-08-24）

plan [`2026-08-24-1601-2`](../plans/p1-insight/2026-08-24-1601-2-navigation-orchestration-v0.md)。
owner doc 是 `docs/design/agents-and-roles.md` §5.1（`permission.scope`「由控制循环在会话开场
自动注入」）、`docs/design/context-and-memory.md` §8.1（结构化导航优先）与本文件 §7.4（熔断）。

**不是控制循环本体**（模型选工具 → 回注 → 作答 → 门禁 → 强制续跑）：那归 P1.4。
本层交付「循环开场要做的事」与「循环出事时要刹的车」，三个对象各自可独立构造。

| 落点 | 内容 |
|---|---|
| `agenerp/orchestration/opening.py` | 会话开场装配器 `open_session(...)`：在任何模型消息之前执行一次 `permission.scope`，产物 + 注入代价 + **由记录推导的**事实进 `OpeningPack` |
| `agenerp/orchestration/navigation.py` | 确定性导航策略 `ScopeFirstStrategy` 与度量骨架 `run_metric(strategy, opening_pack, tasks, ...)`。**零模型参与**（D-15） |
| `agenerp/orchestration/circuit.py` | §7.4 的 `DenialBreaker` + 403 识别口径（`is_permission_denial` / `result_is_permission_denial`） |
| `tests/tools/test_navigation.py` | 本层全部判据（32 条，假站点，零网络零凭据零 docker）。文件名由 `docs/masterplan/02-WBS.md` §4 第 82 行的验收原文点名 |

#### 「开场自动注入」的两段机制，**分名分述，不许混为一谈**

| | 事实的含义 | 谁给 | 可验性 |
|---|---|---|---|
| **契约面** `injected_at_session_start`（`agenerp/tools_readonly.py` 的 `PERMISSION_SCOPE` 第二条后置断言） | 「本次调用是编排面在会话开场发起的」 | **调用方自证**（本性如此：工具没有「会话」这个概念，推不出编排面的事） | **弱**：调用方说了算 |
| **开场包面** `opening_injection_verified`（`OpeningPack.facts`） | 「注入这件事**真的发生过**」 | 从 `ToolResult` **推导** | **强**：可从站点留痕核出，写死标志会被反测打红 |

`agenerp/tools/runtime.py` 的事实合并是 `{**caller_facts, **outcome.facts}`，
`agenerp/contracts.py` 的 `Condition.evaluate` 在事实缺席时直接判否 —— 因此装配器**必须**
把契约面那条交进 `ReadOnlyContext`，否则 `execute("permission.scope", ...)` 必然在
`postconditions` 上 abort。

⚠️ **`tools_readonly.py` 那条后置断言在 P1.3 之后仍然是一个调用方自证的软断言。**
任何绕过 `agenerp/orchestration/` 直接调 `execute` 的人都能把它填成 `True`。
**不得**把它说成「注入已被契约保证」——P1.3 加强的是**编排面**，不是契约面。

#### 三个 `Decision`（供人复核）

- **D1 编排面落哪个包** —— 选定新包 `agenerp/orchestration/`，判据落既有的 `tests/tools/`。
  否决 (A) 并进 `agenerp/context/`（P1.2 的 Non-Goals 3 把控制循环排除在上下文层之外，
  塞进去等于让 P1.2 收口后的结果面被悄悄扩写）；否决 (C) 塞进 `agenerp/tools/runtime.py`
  （那是**工具执行入口**这一个咽喉，让工具层知道循环的事方向反了）。
  ~~**残余风险**：本层与 P1.4 循环本体的接缝**只有单侧**（本层提供，P1.4 消费），
  未被任何真实循环验证过。~~
  **2026-08-24 已改准（P1.4）**：接缝**两侧都在**了 —— `agenerp/explain/loop.py` 是消费侧，
  开场注入与熔断在循环里各有一个真实调用点，判据见 §7.8。
- **D2 §7.4 熔断进不进本期** —— 选定「进」。它是**责任人空缺的悬空条目**（见 §7.6 那条已改准的归属）、
  是**确定性规则**（D-15）、且与开场注入同源（注入是主路径，熔断是兜底，
  分在两个 plan 里会让「主路径失效时会怎样」没有归属）。**残余风险**见 §7.4 末尾的 ⚠️。
- **D3 「导航质量」用什么口径量** —— 选定「**确定性导航策略在假站点上的 `execute()` 调用次数**，
  on / off 两组对照，两组**共用同一个策略对象**」。否决 (A) 拿真模型跑几次比次数
  （P1.0 实测每格 3 次只够看方向不够算比率，且每跑一次烧一次 token、结论还不稳）；
  否决 (B) 直接把「35 → 1」写成断言目标值（D-16：那是别的站点上的数字）。

#### 导航质量：**本仓夹具实测，非站点实测**

计数口径先定死再跑（否则 H1/H3 的真假可以事后选）：「调用次数」= 一次会话内 `execute()`
被调用的总次数，**含开场注入那一次**；「站点请求次数」= `ToolResult.request_count` 之和，
**另计一栏**；终点是「可以开始作答」**或**「可以明确拒答」，两者都算终点。
候选集 10 个 DocType，注入代价 `request_count = 10`（逐个 `has_permission`）。

| 导航题 | on `execute()` | off `execute()` | on 站点请求 | off 站点请求 | 终点 |
|---|---|---|---|---|---|
| ① 受限身份问不可见 DocType | **1** | **5** | 10 | 5 | 两组都拒答 |
| ② 可见范围内的单跳取数 | 2 | 1 | 12 | 2 | 两组都作答 |
| ③ 多跳结构化导航（`meta.fields` / `doc.links`） | 4 | 3 | 16 | 6 | 两组都作答 |

**这几个数是本仓夹具（`tests/tools/conftest.py` 的 `FakeSite`）上的实测，不是站点实测。**
§7.4 记的「35 次」是 Spike 01 在**别的站点**上对真模型的实测，
**两者不是同一个量、不是同一道题，不得互相引用为佐证**（D-16）。

**两件不好看的事照实记**：

1. **注入在站点请求这一栏上是净亏的，连它赢的那道题也是**（① 题 10 对 5）。
   「调用次数少」与「站点请求少」是两件事，口径分两栏正是为了让这一点藏不住。
   **「开场自动注入更省」这句话只在 `execute()` 次数这一栏成立。**
2. **off 组那 5 次由题面决定**（① 题写死了 4 条备选路线）。题目与备选路线逐条写死在
   `tests/tools/test_navigation.py` 的 `TASKS` 里，人复核时能看见选了什么、没选什么。
   **选题偏向这条残余风险不消除。**

判据形状是**方向 + 上界**，不钉具体次数：次数会随夹具演进漂移，钉死它会让判据红在夹具
而不是红在实现。**残余风险**：方向性断言比数值断言弱，一个「只慢一点点」的退化不会被打红；
缓解是把上表的数字写在这里，人复核时能看见趋势。**残余风险不消除。**

#### 判据缺口与验证范围，照实记

`tests/tools`（含本期新增的 `test_navigation.py`）**已在 CI 的 `unit-and-contracts` job 里**
（2026-08-24 由人接进 `.github/workflows/gates.yml` 的第 ③ 步，并加了一条「没有测试目录被漏在
CI 之外」的元判据），`lint` job 的 ruff 作用域也已含它。
**但它仍不在 `missions/p1-insight.json` 的 `commands.test` 里**
（那条是 `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`），
因此 `GATE_VERIFY` 子进程**复跑不到本层的判据**。`missions/**` 与 `.github/workflows/**`
loop 都无权自己动，已挂进 `docs/masterplan/STATE.md` §3 的 needs-human 队列。
代偿控制：M1–M8 变异自查 + 独立关闭审计 + 那条队列行。

### 7.7 上下文层在本仓的落点（P1.2 · 2026-08-24）

plan [`2026-08-24-1457-2`](../plans/p1-insight/2026-08-24-1457-2-context-layer-v0.md)。
owner doc 是 `docs/design/context-and-memory.md` §8.2（上下文四层）与 §8.5（内置实现零依赖）。
**只做 ① 即时与 ② 会话两层**；③ 记忆与 ④ 检索不在内（该 plan Non-Goals 1/2，重开事件写在它的 §9）。

| 落点 | 内容 |
|---|---|
| `agenerp/context/immediate.py` | **① 即时层**的确定性装配：`assemble()` 收当前单据（`doctype` / `name` / 完整字段表）、角色、视图，产出 `ImmediateContext`；`trim()` 按 §8.2 的四条优先级规则裁到预算内 |
| `tests/context/test_immediate.py` | ① 层判据：字段→值映射恒等、边界标记三条正向断言、裁剪次序与「裁不下就抛」 |
| `agenerp/context/session.py` | **② 会话层**：`ConversationSession`（轮次 / 已执行动作 / 前后快照引用）、会话级用量聚合 `usage_total`、审计记录摊平 `audit_records()`。**不可变**，每个 `with_*` 回新会话 |
| `agenerp/context/store.py` | 会话的**存储端口** `SessionStore`（协议）+ **零依赖内置实现** `JsonFileSessionStore`（落盘 JSON，`sort_keys=True`）。§8.5 逐字要求「内置实现必须存在且零外部依赖」 |
| `agenerp/context/doctype/agent_conversation_session.json` | 会话 DocType 的**声明**（落 git、可 diff、可 review）。**不含任何 apply 逻辑** —— 活站点上的建表是人的动作，见下面的可逆性声明 |
| `tests/context/_scan.py` | 两条红线**共用**的源码/AST 扫描器（权限求值面 · 站点写入面） |
| `tests/context/test_session.py` · `test_store.py` | ② 层判据：轮次 / 动作 / 快照引用、token 三项口径、`Usage.plus` 计数、保真 / 字节相等 / 键序三条分开的落盘断言、权限红线扫描 |
| `tests/context/test_doctype_declaration.py` | 声明 ↔ `ConversationSession` 逐字段同构 · **零站点写**扫描 |

**装配面不自己去猜。** 当前单据、角色、视图**全部由调用方给**：这一层不打站点、不查权限、不问模型。
全是确定性规则，零模型参与（D-15）。

**产物是结构，不是拼好的字符串。** §8.2 的「① 当前单据的完整字段永远优先，① 不可裁剪」
要能被机械判定，而字符串上断言不出「哪个字段被裁掉了」。

**四条优先级规则表达成四个档位，本层只实现其中两条**：

| 档 | 规则出处（§8.2） | 本层 |
|---|---|---|
| `TIER_DOCUMENT` (0) | ① 当前单据的完整字段永远优先，不可裁剪 | **实现**，在 `UNTRIMMABLE_TIERS` 里 |
| `TIER_ACTIONS` (1) | ② 已执行动作的审计记录不可压缩 | **实现**，在 `UNTRIMMABLE_TIERS` 里 |
| `TIER_MEMORY` (2) | ③ 记忆按「是否已验证」排序，未验证的先裁 | **只留档位**：`trim()` 会先裁它，但**档内排序不实现**（属 ③ 记忆层） |
| `TIER_SCHEMA` (3) | ④ schema 按检索相关度裁 | **只留档位**：`trim()` 最先裁它，**相关度排序不实现**（属 ④ 检索层） |

留位方式是：`trim()` 认这两个档位、按 `④ → ③` 的次序先裁它们，**档内保持调用方给的次序、从尾部丢**。
③ / ④ 的档内排序由将来那两层各自决定后把块排好再传进来，本层不替它们排。

**裁不下就抛，不静默截断**（`ContextBudgetExceeded`）。静默截断之后，
「上下文里没有那个字段」与「模型没看见那个字段」在事后无从分辨。

#### `Decision`：前端注入的单据字段要不要再包一次数据边界标记 —— **要包**

§7.5 的包裹动作今天挂在 `agenerp/tools/runtime.py` 的**工具执行入口**这一个咽喉上。
而 ① 层的「当前单据完整字段」是**前端注入**的，**不经过那个入口** —— 这是 §7.5 今天没有覆盖到的第二条入口。

- **裁定**：包。§7.5 红线逐字是「任何来自工具结果的文本」，而前端注入的单据字段
  同样是用户可写自由文本，攻击面同源（Spike 01 探针 5：车间工人写 `resolution`、老板提问时读到）。
- **备选（否决）**：不包，靠前端保证。否决理由——前端不在本仓，靠不住的东西不能当结构性防御。
- **包法**：**复用** `agenerp.tools.runtime.wrap_free_text`，不抄一份 —— 抄一份就会漂移。
  语义逐字沿用它的现行口径：**先把值里自带的标记串转义，然后无条件包**。
  「已包过就不再包」是**错的**：那等于给攻击者一条「自己写一对标记 → 装配面认为已包过 →
  载荷落在数据边界之外」的路。判据 `test_a_field_carrying_its_own_boundary_marker_is_escaped_and_still_wrapped`。
- **残余风险，不宣称消除**：转义口径认的是标记串**字面**，注入方若写出与标记串等价的变体仍可能钻过去。
  这是 P1.0a `wrap_free_text` 的**既有**残余，本层复用它，不修它、也不假装它不在。

#### `Decision`：本层的 `keep` 集合取 `STRUCTURAL_KEYS`，**`name` 不加进去**

工具层的 `keep` 是 `returns.must_keep | STRUCTURAL_KEYS`（`runtime.py:298`），
而 `STRUCTURAL_KEYS` 实读是 `("doctype", "parenttype", "parentfield")` —— **`name` 不在里面**。
本层没有 `returns`，因此 `BOUNDARY_KEEP` 恰好取 `STRUCTURAL_KEYS`。

`name` **不加**的理由：`must_keep` 之所以免包，是因为它是**下游据以判定的结构标识**
（`runtime.py:68` 逐字「证据门禁按单号比对已调过哪些 `doc.get`」），包进标记判定面就失效。
而本层把单据身份摆在 `CurrentDocument.doctype` / `.name` 两个**专用字段**上，
下游读身份读的是它们，不是字段表里的那一份 —— 于是「不包就会失效的判定面」在本层不存在。
另一侧，prompt 命名的 DocType 上 `name` 是**人写的自由文本**。
两相权衡取 `runtime.py:220` 的保守口径：**漏套比噪声危险**，所以字段表里的 `name` 被包。
判据 `test_structural_keys_are_not_wrapped` 与 `test_identity_is_carried_outside_the_wrapped_field_map`
把这个选择两侧都钉住了。

#### 一处私有名依赖，照实记

`tests/context/test_immediate.py` 显式 `from agenerp.tools.runtime import _BOUNDARY_ESCAPE`
——**私有名**。这样写是有意的：转义串一旦改名，该判据会当场 `ImportError`，
而不是悄悄退化成「什么都没验」。代价是本判据与 `runtime.py` 的内部名绑死了，改名要同改两处。

#### 命名消歧：`ConversationSession` 不是 `tools.runtime.Session`

| | `agenerp.context.session.ConversationSession` | `agenerp.tools.runtime.Session` |
|---|---|---|
| 是什么 | **对话会话** | **工具会话** —— 执行体与站点之间的唯一通道 |
| 记什么 | 轮次 / 已执行动作 / 前后快照引用 / 每轮 token 账 | `request_count` / `resource_doctypes` / `row_sources` / `methods` 四类站点请求留痕 |
| 谁消费 | 控制循环（P1.4）与审计 | 契约的后置断言（推「过程约束」类事实） |
| 生命周期 | 一次对话 | 一次 `execute()` |

**同名不同义，没有继承、没有组合、不可互换。** 产品类名带 `Conversation` 前缀就是为了这个。
**残余**：将来若有人再引入第三个 `Session`，这张表拦不住，只能靠 review。

#### ② 会话的用量聚合：`Usage.plus()`，不许自己写加法

逐项语义**沿用 P1.1，不另立一套**（`agenerp/routing/adapter.py` 的 `Usage`）：
`reasoning` 是 `completion` 的**一个细分**，不是第四个桶；`total = prompt + completion`，
**reasoning 不参与求和**。分工是：`Usage` 是**一次调用**的账，「一个会话累计烧了多少」是会话的属性，
P1.1 里没有这个概念，也不该有 —— 所以聚合归本层。

**折叠形态定死**：从空 `Usage()` 起逐轮折，N 轮 → **恰好 N 次 `plus()`**。
判据 monkeypatch `Usage.plus` 数次数，次数写死成 `== 3`，**不写「至少一次」**。
没有这一条，「必须调 `plus()`」只是一句注释 —— 一份手写但算得对的三项加法能满足全部算术断言。

#### ② 的「前后快照」记的是取证快照，**不是写操作的回滚点**

`ConversationSession.with_readonly_probe()` 收调用方给的两张 `Snapshot`，
用 `agenerp.snapshot.diff` 算差异摘要，只存 `SnapshotRef`（`label` / `scope` / `entry_count`），
**不复制快照内容** —— 复制会让会话记录随站点规模膨胀，而 ② 层要落进一条 DocType 记录里。

本模块**不调 `capture`**：那是 I/O，归调用方。复用的是 `Snapshot` 的形状与 `diff` 的口径，
**不另写第二套比对** —— 第二套会在 scope 不同、属性变更这类边角上与它错开。

⚠️ v0 的 ② 端**只有只读工具，没有写动作**，所以这里记的是**取证前后的只读快照**。
不要读成「已经在记写操作的回滚点了」。

#### `Decision`：「会话落 DocType」在 v0 落成什么 —— **端口 + 零依赖内置实现 + 声明落 git**

| 方案 | 否决 / 选定 |
|---|---|
| (A) 直接在活站点建 DocType 并写记录 | **否决**。`agents-and-roles.md` §9 的风险档 **L3**（新建 DocType / DDL）**强制人批**，loop 自行执行等于绕过人批；且 `SiteClient` 侧无 teardown，回滚只能手工 |
| **(B) 存储端口 + 零依赖内置实现 + DocType 声明落 git，建表交人** | **选定**。WBS §4 P1.2 的验收原文是 `pytest tests/context -q` 退 0，(B) 完整满足；§8.5 逐字要求「内置实现必须存在且零外部依赖」，(B) 正是它；声明落 git 满足 L3 的「落 git + 可回滚」里 loop 能做的那部分 |
| (C) 只做内存实现，不出声明 | **否决**。那样「落 DocType」四个字一点没兑现，收口时只能靠措辞含糊过关 |

**不扩展 `agenerp/pack.py`**：定制包格式只装 Custom Field（`PACK_ENTRIES_KEY = "custom_fields"`），
装不下一个新 DocType；扩展它会把改动挂进 `apply_pack → execute_plan → drop_orphan_columns → oob.drop_columns`
这条**不可逆 DDL 调用链**，而那条链已被 `docs/backlog/irreversible-ddl-has-no-code-level-precondition.md`
登记为 `deferred`、处置者是人。本仓因此**不长第二条 DDL 路径**。

#### 可逆性声明（`ai-autonomy-policy.md` Protected Areas 末行的 Required Evidence，逐字回答）

**本层不新增任何对活站点的写调用。** `agenerp/context/**` 不引用
`SiteClient.create_doc` / `ensure_doc` / `delete_custom_field`，
判据是 `tests/context/test_doctype_declaration.py::test_the_context_layer_never_writes_to_a_live_site`
（源码/AST 扫描，不是 code review）。
**因此站点侧回滚问题在本层的交付面上不产生。**

⚠️ **残余，照实记，不得说成「已证明不可能写站点」**：AST 扫描挡得住直写，
挡不住 `getattr(client, "create_" + "doc")` 这类拼名调用。v0 接受这条残余。

⚠️ **会话记录在活站点上还没有落处。** 将来人手工建表之后要回滚，手工命令原文是
`docker compose exec -T backend bench --site frontend backup`（先备份）+ 在 Desk 里删除该 DocType。
**这是「回滚仍然只能手工做」，不是「已提供回滚」。** 已挂进 `docs/masterplan/STATE.md` §3 的 needs-human 队列。

#### 权限 / 风险红线的机械判据

`context-and-memory.md` §8.4 的硬红线（代码级、不可配置）与本文件 §7.5 红线行同源：
**本层的任何字段都不得参与权限判定或风险档计算。** v0 表达成三条可扫描的禁令 ——
本包不 import `agenerp.contracts`、不碰它的求值面（`ReadOnlyContext` / `Condition` /
`check_preconditions` / `check_postconditions` / …）、不构造 `facts` 字典交给 `execute`。

⚠️ **黑名单刻意是这三样具体的东西，不是「禁止 import `agenerp.tools.runtime`」**：
① 层正要 import 那个模块的 `wrap_free_text`，一条过宽的模块级禁令会把 ① 层当场打红，
而那与权限判定毫无关系。

#### 判据缺口，如实记在这里

`tests/context` **不在** `missions/p1-insight.json` 的 `commands.test` 里，
也不在 `.github/workflows/gates.yml` 的 `unit-and-contracts` / `lint` 任何一个 job 的作用域里
（那两个 job 的作用域是 `tests/unit` `tests/contracts`）。因此 **`GATE_VERIFY` 与 CI 都复跑不到本层的主判据**。
`missions/**` 与 `.github/workflows/**` 都在红线内，loop 无权自己补。
代偿控制：变异自查（plan Phase 3 的 M1–M8）+ 独立关闭审计 + STATE §3 的 needs-human 行。
**不得因为本层测试自己是绿的就说「已被门禁覆盖」。**

### 7.8 解释 Agent 控制循环在本仓的落点（P1.4 · 2026-08-24）

plan [`2026-08-24-1755-1`](../plans/p1-insight/2026-08-24-1755-1-explain-agent-and-evidence-gate.md)。
owner doc 是 `docs/design/agents-and-roles.md` §5.0 ①（三条证据规则）与 §5.1（开场注入）。

**本节结清了两笔挂在别处的欠账**：§7.4 末尾那两条 ⚠️（熔断接线、审计写入）与
§7.6 那句「尚未接到任何真实控制循环上」。五处失效归属已就地改准，不另起新行。

#### 各文件职责

| 文件 | 职责 | 不做什么 |
|---|---|---|
| `agenerp/explain/__init__.py` | 导出面：**只有** `explain` 与 `ExplainResult` | 不导出循环类、事实采集面、工具 schema —— 导出面一旦泄开就收不回来 |
| `agenerp/explain/gate.py` | 证据充分性门禁的**事实采集面**：把五条事实凑齐交给 `EVIDENCE_GATE` 求值 | **一个字都不复述规则**（复述之后判的就成了这份复述）；不判「答得对不对」 |
| `agenerp/explain/loop.py` | 控制循环本体：开场 → 模型 → `execute` → 回注 → 作答 → 门禁 → 强制续跑 | 不自己发 HTTP、不自己挑模型、不自己写 `Usage` 加法 |

四个零件是**换掉的**，不是新写的 —— 循环形状继承 `tools/experiments/p1_entry_gate/loop.py`
（P1.0 的实验设施，**一行没动、一个文件没复制**）：模型侧换成 `agenerp.routing.route()`、
开场侧换成 `agenerp.orchestration.open_session()`、会话侧换成 `agenerp.context.session`、
熔断侧接上 `agenerp.orchestration.DenialBreaker`。

#### 两处门禁求值的分工（`Decision` D2）

**两处不是重复，各卡各的：**

| | 卡什么 | 在哪 | 谁做的 |
|---|---|---|---|
| ① 工具前置 | 「作答类工具能不能**被调用**」 | `QUERY_READ` / `SNAPSHOT_READ` 的 `preconditions` | P1.0a，本 plan 一个字不改 |
| ② 作答前 | 「这个 answer 能不能**被接受**」 | `ExplainLoop._judge()` | 本 plan 新增 |

只有 ② 拦得住「模型不调作答类工具、直接凭 `doc.get` 的返回值报数字」——
那正是 Spike 02 实测到的失败形态（§5.0 ①：只调一次 `doc.get` 就下结论）。
**两处求的是同一个事实字典**：同一个 `EvidenceSurface` 实例，`surface_id` + `uses` 留痕
让「同源」可被断言而不是靠人复核。

#### 七个 `Decision`

| # | 选定 | 主要否决项 |
|---|---|---|
| D1 | 模型侧走 `agenerp.routing.route()` 取 `ChatAdapter` | 否决复用实验设施的 `llm.py`（它自己的模块头写着「不是产品代码」，且绕过 P1.1 的能力分档校验） |
| D2 | 两处求值并存，**事实采集面只有一份** | 否决「只保留 ①」（拦不住 Spike 02 那条路）；否决「只保留 ②」（要改 P1.0a 已收口的契约） |
| D3 | `permission.scope` **不进模型可见的工具面** | 开场注入已由 P1.3 确定性化，再让模型自己调一次等于把它交回给模型（D-15） |
| D4 | 熔断事件落进**会话轨迹** | 否决写进站点审计表（那是**写操作**，与 ②端只读冲突）；否决继续留白（owner doc 已归本 plan） |
| D5 | 判据落 `tests/unit/`，假站点**按路径加载** `tests/tools/conftest.py` | 否决新建 `tests/<目录>`（CI 步骤 ⑦ 必红，改 workflow 是红线）；否决在 `tests/unit` 另写一份假站点（两份会各自漂移） |
| D6 | 熔断 `doctype` 取 `params["doctype"]`，**没有该参数的按工具名兜底** | 否决让 `execute` 回填（要改 P1.0a 已收口的执行面） |
| D7 | ② 门禁的消融**只在判据侧构造**（直接 new `ExplainLoop`） | 否决在产品入口加 `gate=on/off` 开关（在一道安全闸上给产品面开关，调用方一行就能关掉） |

#### 判据缺口与验证范围，照实记

**判据落点**：`tests/unit/test_evidence_gate_single_hop_body.py`（H1 三条 + H2 两条）与
`tests/unit/test_explain_loop.py`（11 条）。`tests/unit` 是今天**唯一**同时进
`missions/p1-insight.json` 的 `commands.test`（`GATE_VERIFY` 复跑得到）与 CI 的目录 ——
**这是本层相对 §7.6a / §7.7 那两条「复跑不到」缺口的加严项**，不是又一条缺口。

**四条残余风险，逐条立着**：

1. **D6 的兜底口径只满足一半「指名 DocType」**。没有 `doctype` 参数的工具
   （`system.overview` / `schema.search` 一类）按**工具名**记，清单里给出的是
   `read:system.overview` 而不是 `read:<DocType>` 形状。§7.4 表第二行的「指名 DocType」
   对这一类**只成立一半**。兜底存在的理由是让清单**不为空**，不是假装它总是 DocType。
2. **D7 的消融开关只在判据侧**，因此 H1 的「门禁关」那一侧测的是**判据侧构造出来的对象**，
   不是产品默认路径。缓解是 H1 多一条断言（产品默认路径下 ② 门禁确实是开的，
   且 `explain()` 签名里根本没有这个参数）；**风险不消除**。
3. **L3 有一个已知逃逸口**：只描述「积压」而**不报数字**的回答 escape 得掉 L3
   （规则原文要的是「作答涉及某个仓库的库存**数量**」）。本层**不擅自扩大 L3 的口径**——
   改规则措辞属 owner doc 与人的裁定面。这条原样带自 `tools/experiments/p1_entry_gate/gate.py`。
4. **`lineage` 档今天会放行 `qwen3.6-plus`**，而它在本项目两跳题上是 1/6
   （`docs/masterplan/STATE.md` §3 `[open] 2026-08-24T07:50Z`）。那条 `[open]`
   **不因本层落地而消失**，本层也不代人处置它。

**活端点验证范围（H4）**：2026-08-24 跑过**一次**，轨迹在
[`docs/evidence/p1-explain/`](../evidence/p1-explain/README.md)。它证明的是「循环在活站点 +
活端点上跑得通、token 账目对得上端点自报的数、L3 在真实数据上抓到了那张外协入库单」。
它**没有**证明「门禁拦得住单跳」（那一跑模型第一次作答就已取证充分，`forced_continues` 为空），
也**没有**证明熔断被触发（Administrator 身份不撞 403）。那两件由上面的 `tests/unit` 判据证明。
**单次实跑不做多次采样**（成本量级见 plan §8 风险 ⑤），正确率归 P1.0，本层不产出正确率数字。

**WBS §4 P1.4 的 🔴 验收本层交付不了**：`tests/gates/test_evidence_gate_blocks_single_hop.py`
在红线 1 内，loop 不得创建。本层交付它的**断言体**
`tests/unit/test_evidence_gate_single_hop_body.py` 与交接说明（写在该文件的模块头），
按 P1.0a 的先例（`tests/gates/test_tool_execution_live.py`，`Gates-Change-Approved-By: lize`）
由**人**按路径加载。⚠️ **收口时不得声称该验收已满足。**
⚠️ 该门禁是**纯路径加载、无 live 语义**的（断言体是假 transport + 假站点，全程不依赖活站点，
**没有 skip 可以收严**，P1.0a 那次的「skip → fail」在这里不适用）——
**这一句要人复核**，loop 不替人拍板它算不算满足那个 🔴。

### 7.9 巡检器与洞察 Agent 在本仓的落点（P1.5 · 2026-08-24）

plan [`2026-08-24-1755-2`](../plans/p1-insight/2026-08-24-1755-2-inspector-and-insight-agent.md)。
owner doc 是 `docs/design/agents-and-roles.md` §5.0 ②（巡检器存在的实测理由）与 §5.1。
决策依据是 `docs/masterplan/DECISIONS.md` **D-15**（只读，本节不改它一个字）。

⚠️ **先把最容易读错的一件事写在最前面：巡检规则 ≠ 行业包制品。**
`agenerp/inspection/minimal.py` 里那**一条**规则是**引擎自带的判据夹具**，用来证明
「发现力来自规则清单」这件事本身；**行业包 v0（`pack_id` + `rule_id` 的来源、每条带
`test_case` 的完整清单）由 P1.6 交付**，落点见 **§7.10**（制品在 `industry-packs/discrete/`，
装载面与校验器在 `agenerp/packs/`）。因此 `agenerp/tools/queries.py` 的
`rule.lookup` **仍然指名报错**，那不是过期漂移，是两件事：一件是引擎，一件是内容 ——
⚠️ **P1.6 之后理由又变了一次**：不是「没有包」，是「**包在盘上、未接进工具面**」（§7.10）。
另外，`agenerp/pack.py` 的「包」是**定制包**（Custom Field / Property Setter 的导出与 apply，
见 §11），与行业规则包毫无关系 —— 命名消歧见下面的 `Decision` D2。

#### 为什么是两个模块而不是一个「洞察 Agent」

D-15 逐字：「按清单逐条查、命中即报**是代码，不是 Agent**」，模型真正不可替代的位置
在**命中之后**。判据是「路径能否预先枚举」：巡检枚举得完 → 必须是代码；
归因叙述的组织枚举不完 → 仍归模型。混在一个「Agent」里会让规则的确定性
被模型的随机性污染，且成本白花。

| 包 | 职责 | 不做什么 |
|---|---|---|
| `agenerp/inspection/` | 巡检器：声明式规则清单 → 逐条查 → 命中即报，**零 LLM** | **没有任何模型接缝**；不写任何业务数据；不判「要不要紧」 |
| `agenerp/insight/` | 洞察 Agent：命中**之后**的归因（为什么会这样 / 要不要紧） | 不发现任何东西；不另起控制循环；**不改写命中记录** |

| 文件 | 职责 |
|---|---|
| `agenerp/inspection/rules.py` | 规则的声明形状 v0 + 装载器（有限算子集；**未知键与缺 `test_case` 一律拒载**） |
| `agenerp/inspection/engine.py` | 巡检执行体 + 命中记录 `Hit` / 报告 `InspectionReport`；行源可换（站点 / 内存） |
| `agenerp/inspection/minimal.py` | 最小规则集 v0（一条，口径「产出 vs 销出」） |
| `agenerp/insight/attribution.py` | 命中 → 归因的接线；边界执行 `ensure_unchanged` |

#### 四个 `Decision`

- **D1 · 规则的声明形状 v0 = 声明式数据 + 有限算子。**
  否决 (A) 自由 Python 谓词 —— 不可 diff、不可迁移，与北极星里「可 diff、可回滚、可迁移的产物」
  直接冲突；否决 (C) 照搬 `agenerp/contracts.py` 的 `Condition` —— 那套算子的语义是
  「什么时候允许停下来」，与「业务数据是否荒谬」不是一回事，硬套会让两处语义互相污染。
  形状至少含 `rule_id` / 人话陈述 / 确定性判据表达 / **`test_case`**（P1.6 的验收原文
  「无 `test_case` 的规则即失败」，位现在就留出来了，且引擎会**真跑**它）。
  **算子集刻意小**：行过滤 `truthy` / `falsy`；度量 `sum_positive` / `sum_negative_abs` /
  `difference` / `related_sum`；触发 `greater_than` / `at_least_fraction_of`。
- **D2 · 目录命名消歧**（`constrained choice`：备选被既有命名与标准库挤掉）。
  `agenerp/pack.py` 已占用「包」，`inspect` 是标准库名 → `agenerp/inspection/` 与
  `agenerp/insight/`，**两者分开**是 D-15 的直接后果，不许合并；本层不复用 `pack.py` 的任何结构。
- **D3 · 归因走 P1.4 的解释循环，不另起一条。** 消费的符号是 **`agenerp.explain.explain`**
  （§7.8 的导出面两项之一），命中记录作为问题的一部分进循环，取证与证据充分性门禁全部沿用。
  否决 (A) 洞察侧自开一条不带门禁的轻循环 —— 那正是 §5.0 ① 要修的「停在第一层证据上」。
- **D4 · 判据夹具由 `agenerp/seed/` 派生，不许手写数据行。** 手写夹具可以被调到
  「怎么写规则都命中」，消融判据就测不出发现力。**两侧取数方向不许合并**：
  夹具（数据）取**构造侧**（`agenerp/seed/model.py` / `dataset.py`），
  期望值取 `agenerp/seed/checks.py` 或由判据自己写死字面量 —— 从同一侧取会让断言变成
  同义反复（`checks.py:18-20` 的原话）。
  **耦合照实登记**：夹具与种子数据集是耦合的，种子改了夹具会跟着变。这是想要的耦合
  （改了就该红），**不是「夹具独立」**。

#### 「零 LLM」判在哪个可观测量上

不判源码文本（那种检查改个字符串就骗过去了），判两个可观测量：

1. **进程级探针**：把 `ChatAdapter` 的 `__init__` / `chat` / `_send` / `_post`、`_ssl_context`、
   `urllib.request.urlopen` 整体换成一被碰就抛的替身，整条巡检路径跑完仍绿。
   **配阳性对照**：同一模块里 `route("explain", …)` 在同一探针下必须被打红 ——
   没有阳性对照的「零调用」什么都没测（替身没装上、装错位置，两种情况都会静静地绿）。
2. **导入图**：全新解释器里 `import agenerp.inspection` 之后，`agenerp.routing`
   **不在 `sys.modules`** 里。巡检器**根本没有模型接缝** —— 留一个「可注入模型」的口子
   再往里塞替身，等于先假设接缝存在再证明它没被用过。

#### 判据缺口与验证范围（不粉饰）

- **两条 🔴 门禁文件本层交付不了**：`tests/gates/test_insight_rule_ablation.py` 与
  「巡检器在零 LLM 调用下跑通固定测例」那一条都在红线 1 内，loop 不得创建。
  本层交付**断言体** `tests/unit/test_inspection_rules.py` 与 `tests/unit/test_insight_attribution.py`，
  按 P1.0a 先例（断言体不重写，按路径加载开发期那份）由**人**创建门禁文件。
  ⚠️ **收口时不得声称 WBS §4 P1.5 的 🔴 验收已满足。**
- **最小规则集只有一条，阈值是取舍不是实测**：`at_least_fraction_of` 的 `0.5`
  是 v0 的保守口径，没有跑过多站点校准。误报/漏报率本层不产出数字。
- **有限算子集在 P1.6 可能不够用**：v0 的判据是「够跑固定测例 + 形状可扩」，
  不是「覆盖离散制造全部规则」。重开事件是 P1.6 起草时发现某条规则表达不出来。
- **`related_sum` 不看单据状态**：订单量按 `Sales Order Item` 全量求和，不筛 `docstatus`。
  固定测例上只有一张已提交订单，所以这一条今天不影响结论；多站点上它会。
- **归因文本的质量本层没有任何判据**：判自由文本要先跑通
  `tests/unit/test_answer_judging_fixture.py` 的 24 条人工标注，属另一个交付面。
  本层的判据只落在结构化事实上：命中记录、命中数量、调用次数、取证轨迹、门禁判定。
- **D3 的两条残余风险**（都是选项 B 的代价，实测确认）：
  ① 命中记录里的数字会进答案文本 → 触发 L3 的取证要求（**这是想要的行为**，但抬高单次成本）；
  ② 命中的 `subject` 里可能有**长得像单号**的取值（`HRD-PACK-5K` 是三段全大写数字，
  正好落进 `agenerp/explain/gate.py` 的 `DOC_NAME`），于是 **L1 把物料号当成
  「问题点名的单据」**并要求 `doc.links`。**不擅自绕开**：门禁措辞归 owner doc 与人的裁定面，
  且它误报的方向是**更严**（保守侧），不是更松。

**活站点验证范围**：2026-08-24 在本地活站点（`frontend@http://127.0.0.1:18080`）
跑过**一次**巡检，退出码 0，命中与离线夹具**逐字一致**
（`on_hand = 1010.0`、`received = 2000.0`、`issued = 990.0`、`ordered = 1000.0`，
`request_count = 5`）。它证明的是「规则表达在真站点的 REST 面上跑得通、
子表按 `parent` 取得到、命中与离线一致」。**归因那一半没有在活端点上跑过**
（本层不需要，也不声称跑过）。

### 7.10 行业包 v0（离散制造）在本仓的落点（P1.6 · 2026-08-24）

plan [`2026-08-24-2109-1`](../plans/p1-insight/2026-08-24-2109-1-industry-pack-v0-discrete.md)。
owner doc 是 `docs/design/agents-and-roles.md` §5.1；决策依据是
`docs/masterplan/DECISIONS.md` **D-15 / D-12**（只读，本节不改它们一个字）。

⚠️ **消歧一：本节的 `Decision` D1–D5 与 §7.9 的 D1–D4 不同源、不同编号空间**，
两处不许互相引用编号。§7.9 定的是「引擎怎么做」，本节定的是「内容长什么样、谁来判它」。

⚠️ **消歧二：仓里有三个「包」，本节只管第三个。**
`agenerp/pack.py` = **定制包**（Custom Field / Property Setter 的导出与 apply，见 §11）·
`agenerp/inspection/minimal.py` = **引擎自带的判据夹具**（一条规则，不是制品）·
`industry-packs/` + `agenerp/packs/` = **行业包制品与它的校验器**（本节）。

⚠️ **消歧三（本节最容易被读错的一句）：包在盘上 ≠ 包已接进 `rule.lookup`。**
本期交付的是「制品在盘上、校验器判得动它」，**不是**「行业包已装载进工具面」。
`agenerp/tools/queries.py` 的 `rule_lookup` **仍然指名报错**，理由从「没有包」
变成「包在盘上、未接线，接线待人裁定」——`tests/gates/test_tool_execution_live.py`
钉着它的现行行为，翻转会让一条 L2 门禁由绿转红（详见下面「未接线」一段）。

#### 制品与代码的落点

| 东西 | 位置 |
|---|---|
| 行业包制品 | `industry-packs/discrete/pack.json`（`pack_id` / `version` / `requires_doctypes` / `rules[]`） |
| 装载面 + 校验器 | `agenerp/packs/loader.py`（`load_pack` / `validate_pack` / `Pack`） |
| CLI | `agenerp/packs/__main__.py` —— `python3 -m agenerp.packs validate --pack discrete` |
| 判据 | `tests/unit/test_industry_pack.py`（39 条）· 坏包夹具 `tests/unit/pack_fixtures/` |

包 v0 收三条规则，**每条都带 `test_case`，且每条都有阳性 / 阴性两侧对照**：

| rule_id | 它找的异常 | 固定测例上 |
|---|---|---|
| `discrete/finished-goods-backlog` | 产出远大于销出（成品积压） | **命中 1,010**（= `agenerp/seed/checks.py` 的 `EXPECTED_BACKLOG_QTY`） |
| `discrete/subcontracting-issued-not-received` | 外协发出去的活收不回来（D-12 点名的一类） | **零命中，且那个零命中是正确行为**（见下） |
| `discrete/closed-order-short-delivered` | 订单被人工关闭却实发少于订单量（账面全绿陷阱） | **命中 10**（= `EXPECTED_SHORTFALL_QTY`） |

#### 五条 `Decision`

- **D1 · 判据表达取 §7.9 的 `Rule` 形状，不取 D01 建议的 `query` + `assert`。**
  被否决的是证据仓 `spike/D01-decisions/FINDINGS.md` §D-3 建议的「裸 SQL 查询 + 自然语言断言」：
  本仓取数走站点 REST 只读端点（`agenerp/inspection/engine.py` 的 `SiteRows`），**根本没有 SQL 面**；
  自然语言 `assert` 不可执行，落地必然退回「让模型理解规则」，与 D01 自己的第 2 条原则
  （「判据必须可独立执行、可断言，不依赖 LLM 判断」）和 §7.9 的选择同时冲突。
  **残余风险**：本仓格式与 D01 建议格式不一致，将来要吃外部按 D01 写的包需要一个转换层 ——
  本期没有输入，登记为 deferred。
- **D2 · 包文件用 JSON，不用 YAML**（`constrained choice`）。
  理由是实读出来的硬约束：`.github/workflows/gates.yml` **五处** `pip install pytest certifi`
  （`:104` / `:176` / `:241` / `:451` / `:505`）**没有 PyYAML**，而 `.github/workflows/**` 在红线内，
  本期无权加装依赖；`agenerp/contracts.py:9-11` 已有同一条先例。
  **代价照实记**：JSON 写不了注释，规则的「为什么」只能进 `statement` 字段；
  D01 建议的 YAML 形态因此**未采纳**。
- **D3 · 扩两个行过滤算子（`equals` / `not_equals`），其余缺口收内容。**
  由 Explore E1 的实测驱动（结论见下面「E1」一段）。判定口径：**只有语义能有限枚举、
  且写得出自己的拒载判据的算子才许新增**；任何要「传一段表达式 / 谓词 / SQL 进来」的方案一律否决。
  两个新算子各带一个字面量（`ROW_FILTER_KEYS` 加一位 `value`），
  并同时交付三样：有限键集里的登记 · 求值判据 · **拒载判据**（未知算子名、缺字面量、
  `truthy`/`falsy` 夹带 `value`、非标量字面量，四种都拒载）。
  ⚠️ **日期算术（「逾期 N 天」）明确不在本期**：它要引入时间基准与时区口径，属另一个交付面。
  外协那条 v0 因此按「**已发料 − 已收货 > 0**」这种**不含时间**的形态表达。
  **本期表达不了的规则类别（D3 的产物，照实列）**：
  ① 需要**触发侧合取**的（如「入库为零**且**出库大于零」）—— 现有 `trigger` 只有一条，没有 `and`；
  ② 需要**按组计数**的（如「同一物料在多个仓库重复堆积」）—— 度量算子里没有 `count`；
  ③ 需要**日期算术**的（如「逾期 N 天未收」）。三类都**没有**先写进包里、判据以后补。
- **D4 · 包落在仓库根 `industry-packs/<pack_id>/pack.json`**，不是 `agenerp/packs/data/`。
  ⚠️ **权衡只用本仓今天可判的口径写**：仓里**没有 `MANIFEST.in`**、`pyproject.toml` **没有
  `[tool.setuptools.package-data]`**、CI 与 `tools/` 里**没有任何 wheel 构建步骤** ——
  所以「随 wheel 打包」与「wheel 装不到」**两条今天都不可验证，不许拿来当理由**。
  可判的两条是：① **路径解析方式** —— `agenerp/packs/loader.py` 的 `packs_root()`
  由本文件位置上溯两级到仓库根，`--packs-dir` 是显式覆盖口；
  ② **它自己的判据** —— 解析不到时抛 `PackNotFound`，CLI 退 `3`（不是「校验通过」）。
  选它的理由：包是**制品**不是代码，与「生态伙伴独立提供行业包」同一个方向，
  且和 `agenerp/pack.py`（定制包）在目录上就分得开。
  被否决的 (B) `agenerp/packs/data/` 的代价：包躺在 Python 包目录里，
  「制品」与「代码」在路径上读不出区别。
  **残余风险（写成假设，不写成事实）**：*假如*将来做 wheel 分发，仓库根的
  `industry-packs/` 大概率不在 wheel 里 —— 这**今天不可验证**，`--packs-dir` 是它的逃生口。
- **D5 · 出处（`pack_id`）落在 `Hit` 上，来源那一层是包。**
  §7.9 交付的 `Hit` **没有** `pack_id`，而 `rule.lookup` 契约的 `must_keep` 含它
  （`agenerp/tools_readonly.py:238`，后置断言叫 `rules_carry_provenance`）。
  选定 (A)：给 `Hit` **加**一个带默认值的 `pack_id` 字段，
  **来源那一层点名**是 `Pack.pack_id` → `engine.run()` / `inspect_site()` 的 `pack_id` 形参。
  它**不进 `Rule` / `RULE_KEYS`**：规则声明不该知道自己在哪个包里。
  被否决 (B)「在包这一层包一层 `rule_id → pack_id` 映射」：命中记录本身仍答不出出处，
  出了引擎就丢。被否决 (C)「把 `pack_id` 编进 `rule_id` 前缀」：出处与身份混成一个字符串，
  `rule_id` 一改出处就变，且「同一 `rule_id` 挂两个包」这条判据在它上面**根本构造不出来**。
  **残余风险**：`pack_id` 默认空串 —— 引擎自带的最小规则集报出来的出处是空的。
  这是想要的（它不是行业包制品），并由 `test_h7_the_engines_own_minimal_rules_claim_no_pack` 钉住。

#### Explore E1：算子缺口的实测结论（与开工前写死的预测逐格对照）

| # | 候选规则 | 预测 | 实测 | 对照 |
|---|---|---|---|---|
| R1 | 产出远大于销出 | 够 | 够，原样表达 | **吻合** |
| R2 | 外协已发料、迟迟未收 | 不够 · 缺按字段值相等筛行（判「逾期」还缺日期算术） | 确实缺：`docstatus == 2` 的作废单排不掉（`truthy` 会把 `docstatus == 1` 一起排掉）→ 新增 `equals`。日期那一维本期不做 | **吻合** |
| R3 | 订单已关闭但实发少于订单量 | 不够 · 同上（按 `status` 相等筛行）；方向不缺 | 缺的是**反向**那一个：`exclude` 的语义是「命中即排除」，「只看 `status == "Closed"`」要写成「排除 `status != "Closed"`」→ 新增 `not_equals`。方向确实不缺（`difference` + `greater_than` 反写即可） | **部分吻合（预测缺 `equals`，实际缺的是同一族的 `not_equals`）** |
| R4 | 某物料入库为零却有出库 | 不够 · 缺触发侧的合取 | 确实缺：`trigger` 只有一条，`{"and": …}` 被未知键拒载 | **吻合** |
| R5 | 同一物料在多个仓库重复堆积 | 不够 · 缺按组计数 | 确实缺：`count` 不在 `MEASURE_OPERATORS` 里，被有限算子集拒载 | **吻合** |

⚠️ 上表是**开工前写死、事后逐格对照**的产物，预测错了照实记，**不回头改预测**。
R4 / R5 按 D3 的「收内容」出路处理：v0 不收，类别写在 D3 里。

#### 校验器的四种处置（互相分得开）

`python3 -m agenerp.packs validate --pack <id>` 的退出码口径 **(i)**：不同退出码，
**并且**消息指名到具体对象。

| 输入 | 退出码 | 消息指名到 |
|---|---|---|
| 健康包 | `0` | 包 id、版本、路径、逐条 `rule_id` 与测例名 |
| `--pack` 拼错 / 包目录不存在 | `3` | 那个 `--pack` 取值、查过的目录、该目录下现有的包 |
| 某规则缺 `test_case`（或形状不合） | `4` | 那条 `rule_id` |
| 某规则的 `test_case` 跑不过 | `5` | 那条 `rule_id`、测例名、期望与实测 |

`2` 留给 argparse 的用法错误，不复用。
⚠️ **三个非零码分开不是洁癖**：合成同一个「非零」时，「查无此包」会被读成「这个包有问题」,
而 `--pack` 打错一个字母的人拿不到任何线索 —— 那是最贵的一种假绿。

**校验器真的跑测例，不是只检查那个键存在**：`validate_pack` 走
`agenerp.inspection.engine.check_test_cases`，逐条在内存行集上真跑。
判据把「翻转 `expect_hit`」与「摘掉 `test_case`」两种变异**逐条各施加一次（含最后一条）**——
只变异第一条时，一个「只校验第一条就返回」的假校验器是绿的。
坏包夹具放 `tests/unit/pack_fixtures/`（静态两份）与 `tmp_path`（逐条派生），
**不放进 `industry-packs/`**：产品制品目录里不许躺着故意写坏的包。

#### 判别力是怎么证明的（以及消融判据为什么不算数）

⚠️ **消融判据（抽掉规则 → 它那条异常查不出来）在 `without()` + `run()` 的实现下接近恒真**：
规则没了自然没有它的命中。它证明的是「引擎读清单」，**不证明「规则有判别力」**。
本节保留它，但**降级为附带断言**。

主判据是**每条规则一对阳性 / 阴性对照**：
阳性 = 含该异常的数据上必须命中，且命中里的**数是算出来的**；
阴性 = 三种异常一个都没有的健康数据上**必须零命中**。
另加**第二个数据集**（换掉 `INHOUSE_QTY` / `SUBCON_QTY` / `DELIVERY_QTY` 三个构造参数、
期望值在判据里写死一个 `!= 1010` 的字面量），证明那个数**随数据集变**。

**不许照答案写规则**：包的序列化形态里不出现单号字面量、不出现 `1010` / `2000` / `990`、
不出现夹具的物料号与仓库名，**源声明与装载后两侧都判**（只判装载后那一侧时，
一条把答案写在装载器不认识的键里的声明会被丢弃、序列化里看不见，可它明晃晃写在源码里）。
`test_case` 整块是这条判据的**显式例外**（合成行本来就要写具体数据），
但测例的取值**不许照抄固定测例的数**，这一条也有自己的断言。

#### 外协那条规则：验的是「它不误报」，不是「它已在真实数据上验证过命中」

⚠️ **逐字声明：外协那条规则未在真实数据上验证过命中。**
种子数据集的外协链是**完整的**（`agenerp/seed/documents.py:147-236`：
`Subcontracting Order.status = "Completed"`，收货 `qty` / `received_qty` 都等于订单量），
即发出去多少收回来多少 —— 所以它在固定测例与活站点上**都零命中，而那个零命中是正确行为**。
种子被 `tests/gates/test_seed_dataset_absurdity.py`（裁判）钉着，**不许为了给它造阳性对照
往种子里加一个新异常**。
它的**阳性对照落在自己的 `test_case`**（合成行，这正是 `test_case` 存在的理由），
固定测例上判的是**它不误报**，且那个零命中必须是**算出来的零**
（委外量与收货量都得非零，否则「没数据」也会静静地绿）。

#### 活站点验证范围（H4 · 2026-08-24）

在本地活站点（`frontend@http://127.0.0.1:18080`）用 `industry-packs/discrete/` 跑过**一次**
整份包（9 次只读请求），与离线固定测例逐字比对，**结论是「部分一致」，照实记**：

- `discrete/finished-goods-backlog`：**两侧逐字一致**（`item_code=HRD-PACK-5K` /
  `warehouse=成品仓 - HRD` / `quantity=1010.0`）。命中集合非空且含它 —— H4 的防伪前提成立
  （否则「两个空集相等」也叫「逐字一致」）。
- `discrete/subcontracting-issued-not-received`：两侧**都零命中**，与上一段一致，是正确行为。
- `discrete/closed-order-short-delivered`：**离线命中 10，站点零命中** ——
  ⚠️ **这正是 D-12 预言的失败形态被抓到了，不是本包的缺陷。**
  可复现的观测（复跑一次结果相同）：站点上 `Sales Order.status` 是 `"To Deliver and Bill"`，
  而 `agenerp/seed/model.py:57` 的 `SALES_ORDER_STATUS` 是 `"Closed"`；
  `agenerp/seedsite.py` 全文没有写这个 `status` 的地方。
  **规则一个字没改去迁就站点**（那是照答案写规则）。归属不在本节的交付面 ——
  已记 `docs/bugs/02-…`，并在 `docs/masterplan/STATE.md` §3 追加了 needs-human。

#### 未接线：`rule.lookup` 为什么还在报错

三处判据钉着 `rule_lookup` 的**现行报错行为**：
`tests/gates/test_tool_execution_live.py:119`（**裁判**，红线内一个字不许动）·
它委派进去的 `tests/tools/test_live_conformance.py:157`（裁判的实际断言面）·
`tests/tools/test_executors.py:290`（离线同形态）。
把行业包接进 `rule.lookup` 会让那条 L2 门禁**由绿转红**，而让它复绿只有两条路 ——
改裁判，或改它委派的断言体（等价于间接改裁判）。**两条都在红线内，loop 不许走。**
→ 接线**交给人裁定**，两条出路与各自代价见 `docs/masterplan/STATE.md` §3 的 needs-human。

#### 本期显式不做的（定界，不是遗漏）

- **不做 `thresholds` / `terminology` 两个顶层块**（D01 建议格式里的另外两块）：
  它们服务的是呈现与检索（P2 的术语层），本期没有消费者 ——
  **没有消费者的声明块就是没有守卫的字符串**。
- **不做行业包的分发/插件化机制**（D01 与 `open-questions.md` #5 都放 P5：
  「只有一个行业包时，插件化机制是纯粹的复杂度」）。
- **不实现 `anomaly.scan` / `benchmark.compare`**：它们不在十个只读契约里，新增契约是另一个交付面。

### 7.11 单次解释成本账本与失控闸在本仓的落点（P1.7 · 2026-08-24）

对应 plan `docs/plans/p1-insight/2026-08-24-2109-2-explain-cost-accounting.md`，
上位裁定是 `docs/masterplan/DECISIONS.md` **D-18**（P1.7 由「成本上限」改为「成本记账」）
与 **D-11**（推理模型回两个字也烧约 195 reasoning token）。

**一条 WBS 行上有两个交付面**：**账本**（成本可观测）与**失控闸**（工具调用总数上限）。
D-18 逐字要求「**两者的判据分开写，不许合并**」—— 判据因此落在**两个文件**里，
但**实现落在同一个模块**，因为「失控闸停机时账仍完整」这条行为契约把两者耦合在一起。

#### 三句边界（先写清楚这个模块**不是**什么）

1. **记账 ≠ 拦截。** 账本里**没有阈值，也没有任何「超了就……」的分支**。
   D-18 取消的正是阈值：没有本项目的成本分布就定阈值，定出来的是外部经验。
   **先有数据，再谈阈值。** 判据 `test_the_ledger_never_blocks_anything` 钉住这一条。
2. **失控闸 ≠ 成本闸。** 它管的是「**坏**」（Agent 陷入循环、无限调工具），不是「贵」。
   它不拦成本、不改模型、不降级，只做「停下来」这一件事。
3. **本账本 ≠ `tools/gates/check_budget.py` 那个循环日预算停机闸。**
   后者是 7×24 循环自己的成本闸（**会真停机**），本账本是产品运行期的记账面。
   **两者不互读、不互写。** 把它们接起来会同时造出 D-18 禁止的拦截路径、并触及
   `tools/gates/`（红线 1）。

#### 账本：采集面只有一处

| 面 | 落点 |
|---|---|
| 账本本体 | `agenerp/explain/ledger.py` —— `CallEntry` / `CallLedger` / `CALL_TOOLS` / `CALL_ANSWER` / `CALL_ERROR` |
| **采集面（唯一）** | `agenerp/explain/loop.py` 的 `ExplainLoop.run()` 里 `self.adapter.chat(...)` **那一个调用点的两条出口**：`except RoutingError` 分支 `record_error(...)`、正常返回后紧跟 `record_reply(...)` |
| 导出面 | `ExplainResult.cost_ledger`（`@property`）· `ExplainTrace.cost_ledger` 字段 · `ExplainTrace.as_dict()` 的 `"cost_ledger"` 键 |
| 判据 | `tests/unit/test_explain_cost_ledger.py`（成本组）· `tests/unit/test_explain_cost_accounting_body.py` §A（🔴 断言体） |
| 活端点证据 | `docs/evidence/p1-cost/`（一跑，8 次调用 8/8 对上端点自报的数） |

**为什么只有一份事实面**：`adapter.chat(...)` 在 `run()` 里是**唯一**调用点，
记账写在它的紧后面（在分支判断**之前**），四条循环出口没有一条能绕过去 ——
而不是靠「每条出口都记得写一遍」。两份账必然漂移。

**为什么不挂在 `ChatAdapter` 上**：那是 P1.1 的导出面，改它会同时动 `tests/routing`
的既有判据，且「**一次解释**」这个聚合概念根本不在那一层。
**为什么不从 `ConversationSession` 反推**：session 只记「成为了一轮对话」的调用，
模型抛错那一次**根本没有 turn**，反推必然漏 —— 实测该路径上 session 的 usage 记录数为 **0**。

**三项 token 的口径归 P1.1，本模块一个字不重定**：`reasoning` 是 `completion` 的细分、
不是第四个桶，`total = prompt + completion`。汇总走 `Usage.plus()`，**不自己写三项加法**。

**每条记录留两组数，刻意不合并**：解析后的 `usage`（由 `usage_of()` 产出，本模块不另写解析）
+ **端点自报的原始数字** `endpoint_total` / `endpoint_reasoning`。
理由是判据强度：`prompt + completion == total` 是恒真式，判它等于没判；
只有拿解析后的数去对**端点自己报的那个数**，「只记 completion 不记 reasoning」与
「把 reasoning 再加一遍」这两类假实现才打得红。

#### 异常出口的记账口径（含「空回答」那条）

模型调用抛错时**照样记一条**（`outcome = model-error`），分两种：

- **端点确实回了包**（「空回答」「回包里没有 choices」「choices[0] 没有成形的 message」
  三条路径）→ 记**真数**。为此给 `agenerp/routing/errors.py` 的 `RoutingError`
  加了一个可选属性 `usage: dict | None`，由 `agenerp/routing/adapter.py` 的三处抛出点注入
  **端点自报的原始 usage 字典**。
  ⚠️ **只挂 `dict`，不挂 `Usage`**：`Usage` 定义在 `adapter.py`，而 `adapter.py` 自己
  `import` `errors` —— 在 `errors.py` 里 import `Usage` 即成 adapter ↔ errors 循环，
  `routing/__init__.py` 会当场 `ImportError`。**`errors.py` 不 import 本包任何模块**是硬约束。
  ⚠️ 挂的是**原始 dict** 而不是 `Usage.as_dict()`：后者里的 `total` 是那个恒真式，
  注入它会让异常路径上的「对得上端点」判了等于没判。
  ⚠️ 该改动**动到 P1.1 的导出面**，因此 `pytest tests/routing -q` 进入本模块的验证命令清单。
- **端点根本没回包**（连不上、配置不全）→ 三项记 0，`endpoint_*` 记 `None`
  —— **「不知道」不写成「对得上」**，`total_matches_endpoint` 因此为 `False`。

**不许悄悄不记**：不记就等于把一次真实花掉的 token 从账上抹掉，
而 D-11 点名的推理模型正走这条路径。

#### 两个数、一个权威（P1.7 的 `Decision` D2）

`ExplainResult.usage`（读 `ConversationSession.usage_total`，P1.4 的既有导出面）
**保留不动**。两者口径不同，分工写死：

| | 答的是什么 | 口径 |
|---|---|---|
| `ExplainResult.usage` | 这次**会话**累计了多少 | 成为了一轮对话的那些调用 |
| `ExplainResult.cost_ledger` | 这次**解释**调了几次模型、各花多少 | `adapter.chat` 发生过几次 |

**要算钱就读账本。** 正常路径上两者逐项相等，异常路径上**账本 ≥ session**
（抛错那次没有 turn）。两条关系各有判据钉死，防的是「两处各算各的」。

#### 失控闸：计量对象与默认值

| 项 | 取值 | 依据 |
|---|---|---|
| 常量 | `MAX_TOOL_CALLS = 32`（`agenerp/explain/loop.py`） | 见下两段算术 |
| 停止原因 | `STOP_RUNAWAY = "tool-call-runaway"` —— **专属**，不复用 `max-turns` / `permission-breaker` | D-18「判据分开写，不许合并」 |
| 计量对象 | **(B1) 模型发起的工具调用数**（`trace.model_tool_calls`） | 见下 |
| 留痕 | `trace.runaway_events[] = {"turn", "tool_calls", "limit"}` + `trace.model_tool_calls`，均进 `as_dict()` | 停机不留痕就没法事后判它该不该停 |
| 产品面开关 | **没有**。`explain()` 的签名里根本没有这个参数 | 照抄 P1.4 的 D7：安全闸不给产品面开关 |
| 判据 | `tests/unit/test_explain_runaway_guard.py`（失控闸组）· `tests/unit/test_explain_cost_accounting_body.py` §B（🔴 断言体） | |

**为什么是 (B1) 而不是 (B2)「实际进入 `execute()` 的次数」**：未知工具 / 被排除工具在
`_execute_one()` 里 `trace.execute_calls += 1` **之前**就早返回 ——
选 (B2) 的话，一个**不断编造工具名**的跑飞模型会让计数**恒为 0**、闸门**永不触发**。
**(B1) 的代价照实记**：它把「没打到站点的调用」也算进来，闸门比「实际干了多少活」略严。
**这是刻意的** —— 它管的是「停下来」，不是「花了多少」。

**默认值 32 的两段算术**（依据只能是本项目实测，外部经验值一律不引，D-16）：

1. **对实测留余量**：P1.4 那一次活端点解释实测 `execute_calls == 8`
   （`docs/evidence/p1-explain/live-run-01.json`）—— 这是**唯一**可引用的本项目数字。
   `32 = 8 × 4`，四倍余量。P1.7 这一跑实测 **9 次**，同样远在闸下（`docs/evidence/p1-cost/`）。
2. **对 `MAX_TURNS` 严格大于**：`MAX_TURNS = 25`，主循环是 `range(1, max_turns + 1)`，
   「每轮发一次工具调用」的正常形态下第 25 轮恰好是第 25 次调用。
   **默认值取 25 时失控闸会赶在 `STOP_MAX_TURNS` 之前触发**，产品默认路径上 `max-turns`
   永不可达，失控闸就地退化成一个更严的 `max_turns` —— **那正是 D-18 禁止的合并**。
   下界因此是 `MAX_TURNS + 1 = 26`（**等号处不算数**），`32 > 26`，余量 6。

#### 对上位文件措辞的重读（留痕，不改上位文件）

D-18 与 `docs/masterplan/02-WBS.md` §4 P1.7 行都写「工具调用**轮数**上限」，
而本期按实读把它落成「**工具调用**那一维」—— 轮数已由 `max_turns` 占用，
且一次回复可携带 K 个 `tool_call`，轮数根本不设限于此（D-18 要挡的「调得通但陷入循环」
正是后者）。`DECISIONS.md` 是 blocked 面，**本期一个字未改**。
⚠️ **本期不声称满足了 WBS 的字面措辞** —— 人若按字面读作「轮数」，须回到轮数口径重做。

#### 判据缺口（照实登记，不粉饰）

- **WBS §4 P1.7 的两条 🔴 门禁文件未创建**（红线 1 禁止 loop 创建 `tests/gates/**`）：
  一条**有名**（`tests/gates/test_explain_cost_accounting.py`）、一条**未命名**
  （`02-WBS.md` 第二个 🔴 没有给文件路径）。
  **两条的断言体都已交付**，在 `tests/unit/test_explain_cost_accounting_body.py`
  的 §A / §B **两节**（不合并），带加载片段与交接说明。由**人**创建门禁文件、
  按路径加载。「纯路径加载、无 live 语义是否仍满足那两个 🔴」**由人裁定**。
- **活端点只跑了一次**：一跑证明账本可用，**不是成本分布**。多次采样属另一个 plan（D-16）。
- **异常出口与失控闸在活端点上都没有被走到**：那两件由单测证明，不由那一跑证明
  （`docs/evidence/p1-cost/README.md` 的「没证明什么」一节逐条列了）。

---

### 7.12 ① 即时上下文（当前单据）在解释循环里的落点（P1.8 前置 · 2026-08-25）

对应 plan `docs/plans/p1-insight/2026-08-24-2311-1-immediate-context-into-explain-loop.md`。
本节补的是 **§7.7（上下文层）与 §7.8（解释循环）之间的那条缝**：
① 层的装配面 P1.2 就交付了，循环 P1.4 也交付了，但**产品路径上从来没有人把前者送进后者** ——
`ImmediateContext` 装配得出来、送不进去，而 `open_session(immediate=...)` 摆好的位置
（`agenerp/orchestration/opening.py:162`）在产品路径上是**死端**。本节就是把这条线接上。

#### 落点

| 面 | 落点 |
|---|---|
| 入口参数 | `agenerp/explain/loop.py` · `ExplainLoop.__init__(immediate=...)` 与 `explain(immediate=...)`（**一个**关键字参数，默认 `None`） |
| 死端接上 | `ExplainLoop._open()` 把 `self.immediate` 透传给 `open_session(immediate=...)`；渲染面读的是 **`pack.immediate`**，不是 `self.immediate`（否则 `opening.py:162` 仍是死端） |
| 渲染面 | `ExplainLoop._immediate_message(pack) -> str \| None` —— 抬头常量 `IMMEDIATE_PREFIX` + 换行 + `json.dumps(payload, ensure_ascii=False, sort_keys=True)` |
| 取块口径 | 按 **`block.key == IMMEDIATE_BLOCK_KEY`**（`"document"`）取，**不按下标** |
| 插入点 | `run()` 装配 `messages` 时插一次：第二条 `system`（开场可见范围）**之后**、`user` 提问**之前**。主循环里**不再 append** |
| 判据 | `tests/unit/test_explain_immediate_context.py`（J1–J11，17 条） |
| 活端点证据 | `docs/evidence/p1-immediate/`（同题两跑，唯一变量是带不带 ①） |

#### 三条 `Decision`（含被否决的备选）

**D1 · 渲染成一条独立的 `system` 消息，插在开场可见范围之后、`user` 提问之前**

| 候选 | 结论 | 理由 |
|---|---|---|
| (a) 拼进 `SYSTEM_PROMPT` | 否决 | 它是模块级常量、判据直接引它；把每次请求都变的内容拼进常量，等于让常量不再是常量 |
| (b) 拼进 `user` 提问那条消息 | 否决 | 用户原话与注入内容混在一条里，事后无从分辨模型看的是哪一半；也让「注入了没有」不可断言 |
| **(c) 独立的第三条 `system` 消息** | **取此** | 与既有 `_opening_message()` **同形态**（P1.4 已在活端点上实测跑通），是既有形态的第三条，不是新形态 |

`role == "system"` 是本裁定的**承重部分**，由 J3 单独钉住 —— 没有它，实现改成 `user`
也能全绿，而 (b) 的否决理由当场作废。
残余风险：部分 OpenAI 兼容端点对多条 `system` 消息的口径不同。
2026-08-25 的活端点两跑（`qwen3.6-plus`）上**没有撞到**，一跑不是分布。

**D2 · 只接 ① 档，② 档（已执行动作）不重复注入**

② 档的同一批事实在 `messages` 里已经逐条在场（`tool_call` + 工具结果）。再注一份是**双写**，
且两份可能不一致（`audit_records()` 是摘要行，`messages` 是原始结果），
而「不一致时以哪份为准」没有任何判据说得清。
被否决的备选：「注入 ② 档、同时把 `messages` 里的工具结果压缩掉」——
那是控制循环的记忆策略改造，远超一条接线。
本裁定由 **J11** 钉住（夹具 `actions` 非空，断言那些字符串不出现在注入的消息体里）：
**承重的 `Decision` 必须有判据钉住**，与 D1 的 `role` 是对称的一条。
重开事件：**当循环开始压缩 / 摘要 `messages` 里的工具结果时**（那时 ② 档就不再「已在场」了）。

**D3 · 不引入上下文预算参数，循环根本不裁**

D-16 要求任何数字有本项目实测出处，而「① 档该占多少字符」本项目没有测过。
且 `trim()` 在本期的调用形态下只有两种结果：未超预算时与不裁恒等；超预算时**抛而不裁**
（① / ② 都在 `UNTRIMMABLE_TIERS`，本期没有 ③ / ④，可裁集合为空）。
因此一个 `immediate_budget` 参数在本期**没有真实调用方** —— 那正是本节开头批评的
「装配得出来、送不进去」，不许再造一个。
被否决的备选：(a) 拍一个默认字符数（数字没出处，会被后来者当实测结论引用）；
(b) 加参数但默认 `None`（零调用方的开关）。

- 兑现方式改成：**渲染面没有任何截断分支**，判据是 J5「超长字段值原样完整出现在消息里」。
- 残余风险照实登记：一张超大单据能把上下文撑爆，**失败形态在端点侧而不是本仓侧**。
  重开事件（两个都要满足）：① 承载面出现真实调用方（浏览器传来的单据可能任意大）；
  ② 成本的多次采样产出过一次实测分布。

#### 判据落点（J1–J11 各挡住哪种假实现）

| 判据 | 挡住的假实现 |
|---|---|
| J1 消融三例（省略参数 / 显式 `None` / 给值且走 `explain()`） | 「无论给不给都注入一条空壳」「`explain()` 收了参数但不透传」。三例分开写是必须的：省略参数那例判的是**默认值**，只写显式 `None` 的话默认值那条路径从未被跑到 |
| J2(a) 随夹具变 + **手写**期望字典 | 「把某个夹具的 payload 写死在渲染面」「`fields` 截成前 N 个键 / 丢掉 `role` 或 `view`」 |
| J2(b) `blocks()` 替身产出标记键 | 「不调 `blocks()`，改从 `pack.immediate.document` 忠实重拼」—— 那种写法在朴素夹具上与 `blocks()` 逐字节相同，**相等断言杀不掉** |
| J3 角色 + 下标关系 | 「注入了但角色是 `user`」「注入了但塞在提问之后」 |
| J4 边界标记原样在 | 「渲染时顺手 unwrap 一下更好看」 |
| J5 不截断（一例经 `explain()`） | 静默截断 —— 截断之后「模型没看见那个字段」与「上下文里没有那个字段」无从分辨 |
| J6 **`FakeSite.requests` 逐字相等** | 「注入面顺手自己去 `doc.get` 补几个字段」。⚠️ 判在 `opening_request_count` 上**挡不住**它（那个数只数 `permission.scope` 那一次 `execute`，渲染面直接打站点它一点不变） |
| J7 按 `key` 取块（块序被换过的替身） | 按下标取块 —— `blocks()` 改序时会**静默串档** |
| J8 `CallLedger` 条数相等 | 注入被误接成「多起一次模型调用」。⚠️ 它**挡不住**每轮重发（重发不改 `adapter.chat` 次数） |
| J9 每条请求载荷上恒为 1 条 | 「主循环里每轮再 append 一次」—— 那会让注入的 prompt 成本随轮数放大，而 J1 / J8 全绿 |
| J10 `result.opening.immediate` **is** 传进去的对象 | 「不传给 `open_session()`，改用 `self.immediate` 直接渲染」—— 那样 J1–J9 全绿而死端仍在 |
| J11 ② 档字符串不出现在消息体里 | 「渲染面把 `blocks()` 的所有块一起序列化」（D2 否决的双写），而 J1–J10 对它全部无感 |

判据的**自证防线**（写在判据文件模块头）：J2 的期望值**手写**，
不是「再调一次 `blocks()` 拿来比」—— 后者等于让被测实现给自己判卷。
`messages` 是 `run()` 的局部变量，`ExplainResult` 上**没有**它；
一切对 `messages` 的断言一律读 `ScriptedModel.payloads[*]["messages"]`。

十四条变异（M1–M14）逐条各施加一次，**全部由本组判据打红**，其中
M3 **只有** J2(b) 杀得掉、M12 **只有** J10 杀得掉 —— 两条替身式判据都不是冗余。
逐条记录在 plan 的 Phase 2。

#### 边界：**① 层不查权限**，而 P1.8 的调用方会是浏览器里的登录用户

`agenerp/context/immediate.py` 模块头规矩 1 逐字：「当前单据、角色、视图全由调用方给。
这一层不打站点、不查权限」。本节把这条口径**原样带进了循环**：
**谁调 `explain(immediate=...)`，谁就能把任意字段表送进模型。**

今天唯一的调用方是本仓自己的判据与脚本，风险为零。
**P1.8 一旦让浏览器发起解释，调用方就变成了外部输入** —— 那时
「这些字段是不是这个用户有权看的」必须有人回答。

- **不在 ① 层补权限校验**（补在那里等于推翻 P1.2 的分层裁定，也推翻 §7.7）。
- **successor**：这条约束逐字交接给承载面 plan
  `docs/plans/p1-insight/2026-08-24-2311-2-desk-embed-carrier-decision.md`，
  作为它的**输入约束**。重开事件：**P1.8 让浏览器发起解释的那一刻**。

#### 活端点两跑证明了什么、没证明什么

**证明了**：导出面 `explain(immediate=...)` 在活站点 + 活端点上跑得通；
`result.opening.immediate` 在活端点上确实是调用方传进去的**那个对象**（死端真的接上了）；
① 档取自活站点的 70 个字段、序列化 5,478 字符，注入后第 1 次模型调用的 prompt
比同题不带的一跑**多 2,709 token**。

**没证明**（照实写）：**这是每侧各一跑，不是分布**。
两跑的轮数不同（带 ① 9 次调用 `answered`；不带 12 次撞 `max-turns` 未作答），
所以**整跑 prompt 合计不可直接归因于注入**。
「注入让解释更容易成功 / 更便宜」**没有被证明，也没有被主张**（D-16）。
逐条见 `docs/evidence/p1-immediate/README.md`。

---


---

## 11. 定制包与 GitOps

### 11.1 核心流程

```
自然语言
    ↓ 视图/形态 Agent
定制包（规范化 JSON/YAML，可 review 的 diff）
    ↓ 风险评估 → 人批准
    ↓ AgenERP 自建 apply 引擎（差集计算：增 / 改 / 删）   ← 不是 bench migrate
应用到站点
    ↓
落成 git 中可版本化的产物
    ↓
可 diff / 可 revert / 可迁移到另一站点
```

**Spike 06 实测：这条链上「可 revert」这一环，用 Frappe 原生机制做不到。**

用架构文档自己的例子（给外协收货加水洗牢度字段）跑完六步：

| 步骤 | 结果 |
|---|---|
| 建 Custom Field | Custom Field ✅、数据库列 ✅ |
| `export_customizations` 导出 | 产出 JSON ✅ |
| 删除 Custom Field | 记录删了，**数据库列仍在、数据仍在** |
| 从定制包 sync 回来 | 字段回来 ✅、**数据完好** ✅ |
| **从 JSON 里删掉字段再 sync（即 `git revert`）** | **字段纹丝不动。revert 无效。** |

原因在 Frappe 的 `sync_customizations_for_doctype`：它是**纯 upsert，没有任何删除分支**。

**本仓的实测反证（2026-08-21）：现在撤得回了。** 上表最后一行说的是**走 Frappe 那条路径**时的结果；
换成本项目自建的差集 apply 引擎（§11.6，`read_pack` → `plan_apply` → `narrow_deletes` → `execute_plan`）后，
同一个动作在活站点上实测**字段真的消失**：门禁 `test_removing_from_pack_actually_deletes_on_site` **PASSED**，
且变异验证（把删除改成 no-op）让它逐字转红「字段仍在站点上」。
**仍未撤回的是物理列**——「删 Custom Field 不删列、数据仍在」那一行**没有被推翻**，
它归第三个部件 `schema_drift`（`test_no_orphan_column_left_behind` 仍红，红因已挪到那里）。

→ 三个必须自建的部件（建议随 P0 的契约层与快照一起做，它们是同一批地基）：

| 部件 | 解决什么 |
|---|---|
| **规范化器** | 导出物含 `modified` / `creation` / `owner` / `_comments` 等易变字段，**什么都不改重新导出也会产生 diff**，git 历史失去意义。必须剥离并稳定排序 |
| **差集 apply 引擎** | 读包 → 与站点现状求差 → **对差集执行删除**。这是 revert 的唯一实现路径 |
| **`schema.drift` 巡检** | 删字段留下孤儿数据库列。LLM 让定制成本趋近于零之后，孤儿列会迅速累积——正是 §1.4.4 说的那种加速 |

另两条实施约束：`export_customizations` **要求 `developer_mode`**（生产站点默认关闭），
且导出目标是 **app 目录**而非站点目录——意味着每个租户的定制需要一个归属 app。

### 11.2 为什么这是防死亡螺旋的关键

ERP 定制的经典死法：定制散落在数据库里，没有版本、没有 diff、没法迁移；三年后没人记得为什么加了这个字段；升级即爆炸。

**LLM 让生成定制的成本趋近于零 —— 这会把死亡螺旋加速一百倍**，除非生成的同时就是可治理的产物。

这也是与低代码平台的根本分歧所在，见 §1.4.4。

### 11.3 实测教训：定制该不该做的判断

实测发现 Job Card 上同时存在：
- `quality_inspection`（ERPNext 原生）
- `xm_process_quality_inspection`（自定义）

**两个字段装着完全相同的值。** 这是「定制失控」的典型起手式——不知道原生已有，于是又加一个。

对比外协收货单上的「定型温度 / 缩率 / 速度」——ERPNext 原生不可能有，是真正的行业知识。

→ **形态 Agent 的核心能力不是「生成字段」，是「判断该不该生成」**：原生是否已有？谁在用？删掉会怎样？`meta.custom_field` 契约的前置条件必须包含原生字段冲突检查。

---

### 11.4 反向风险：改标准 Workspace 会被升级静默覆盖

Spike 06 证明 Custom Field **撤不回来**。Workspace 的问题方向相反：**留不住**。

ERPNext 把标准工作台以 JSON fixture 装在 app 目录里（`erpnext/selling/workspace/selling/selling.json` 等）。`frappe/modules/import_file.py` 按文件 md5 决定是否导入：

- 日常 `bench migrate`：hash 未变 → 跳过（:137）→ 用户改动存活
- 升级 ERPNext 且官方改过该 JSON：hash 变化 → `import_doc` 走 `delete_doc` + 重新插入（:273）→ **用户改动无声消失**

且 Workspace **没有 Custom Field / Property Setter 那样的定制隔离层**——它是整条记录被覆盖，不是字段级合并。

| | Custom Field | Workspace |
|---|---|---|
| 缺陷 | 撤不回来 | 留不住 |
| 后果 | 定制只增不减 | 定制寿命 = 一次升级 |

**证据强度**：代码路径已确认，**端到端未实测**——待 Spike 11 证实或证伪，不得据此下终局结论。

→ 若成立，这是视图 DSL 的又一条独立论据：**DSL 存在 AgenERP 自己的表里，不参与 Frappe 的 fixture 覆盖循环。** 反之，视图 Agent 若直接改标准 Workspace，产物只有一次升级的寿命。

---

### 11.5 状态快照与结构化 diff 的结构边界

「可 diff、可回滚、可迁移」要求先有**可比较的状态**。`agenerp/snapshot.py` 交付这一层，
三个部件的职责必须互不重叠——重叠一次，diff 就会开始骗人。

| 部件 | 职责 | 不变量 |
|---|---|---|
| `Snapshot` | 承载「某一时刻某 scope 的结构化状态」 | 不可变值对象；**不持连接、不做 I/O 缓存**；相等性只看 `scope` + 条目内容 |
| `SnapshotSource` | **唯一做 I/O 的接缝**：给定 scope 返回条目 | **离线来源**：位置不存在 → 空元组，不抛异常（「还没有定制」是合法状态）；**站点来源**：站点答不上话不是合法状态 → 抛 `SiteError`，见 §11.7；`identity` 只是溯源串，不参与相等性 |
| `diff` | 比较两份快照 | 纯函数：不读来源、不改入参；同样两份快照比两次结论必须相同 |

#### 为什么相等性里不能有采集时刻

带上采集时刻，「同一站点两次快照相等」就永远不成立，「未改动 → diff 为空」这条判据随之失效。
这与 §11.3 的教训同源：**易变字段污染 diff**。所以离线来源读到的载荷先过 `agenerp.pack.normalize`
（剥 modified / creation / owner / `_comments`、稳定排序）——快照的确定性与定制包用同一套口径，不该有第二份。

#### 「结构化」的判定含义

`Diff` 暴露 `added` / `removed` / `changed` 三个序列，元素统一携带 `.doctype` / `.fieldname`，
`changed` 另带 `before` / `after`。**判定面是这三个序列**；`summary()` 只供人读（断言失败信息、日志），
调用方不必解析任何文本就能回答「什么被加了 / 删了 / 改了」。条目身份是 `(doctype, fieldname)` 二元组，
不是裸字段名——只按字段名去重会把两个 DocType 上的同名字段混成一个。

#### 两条显式拒绝

- **scope 不同的两份快照不许被 diff**：抛 `SnapshotScopeMismatch`，不静默降级成「全删全增」。
  静默降级会让调用方以为站点被清空又重建。
- **无活站点不等于错误**：无站点配置时走离线来源（仓内约定路径 `<root>/<scope>/*.json`，
  位置不存在即零条目），而不是抛异常。让它抛异常，门禁就会永远红在环境而不是红在实现上。

#### 留给工具契约层的接缝

来源解析次序是 **显式来源 > 站点配置（`AGENERP_SITE`）> 离线来源（`AGENERP_SNAPSHOT_DIR`）**，**这一条没变**。
`SiteSnapshotSource.read` 已于 2026-08-21 接上（工作项 4 的 B 半），落点与凭据口径见 §11.7；
如当初所料，`capture` / `diff` 的签名与语义一个字没动，`SiteSnapshotSource(site)` 的既有构造式也没动
（新增的 `client` 是可选注入，默认 `None` → 走 `client_from_env`）。

**站点来源与离线来源的一处必要分歧**（不是口径分裂，是两种失败语义不同）：离线来源「位置不存在」
返回空元组，站点来源「站点答不上话」抛 `SiteError`。降级成空快照会让「未改动 → diff 为空」在站点宕机时
照样绿，还会让 `plan_apply` 把站点上每个字段都算成「要删」。剥易变字段的口径两边**仍然同源**
（同一个 `agenerp.pack.normalize`）。站点行的身份列是 `dt` 而不是 `doctype` —— 那是包文件那侧的键，两边不能互抄。

判据出处：`tests/gates/test_snapshot_diff_structured.py`（L1 两条 + live 一条）；真实语义覆盖在
`tests/unit/test_snapshot_capture.py` 与 `tests/unit/test_snapshot_diff.py`，不依赖活站点
（站点来源那组喂**假客户端**：`dt → doctype` 投影、两次读相同、易变列被剥、同名字段不混、
25 条不截断、未知 scope 抛、`capture` 不吞 `SiteError`）。
### 11.6 差集 apply 引擎在本仓的落点（2026-08-21，A 半 + B 半均已落地）

§11.1「三个必须自建的部件」第二行**整条**已落地：读包 → 与站点现状求差 → **收窄** → 对差集在活站点上执行删除。
切分依据只有一条：**算出删除集是纯逻辑，执行删除才需要活站点。**
B 半（`execute_plan` 的删除路径、作用域收窄、建/改显式拒绝）见本节末的三条裁定。

| 落点 | 职责 | 状态 |
|---|---|---|
| `agenerp/apply.py` · `read_pack(path, scope=PACK_SCOPE)` | 定制包目录 → `Snapshot` | 已实现 |
| `agenerp/apply.py` · `ApplyPlan` | 不可变值对象：`creates` / `updates` / `deletes` | 已实现 |
| `agenerp/apply.py` · `plan_apply(desired, current)` | 纯函数求差 | 已实现 |
| `agenerp/apply.py` · `pack_doctypes(path, scope)` | 包**管辖**哪些 DocType = 目录里存在文件的那些（收窄集） | 已实现（B 半） |
| `agenerp/apply.py` · `narrow_deletes(plan, covered)` | 纯函数收窄 `deletes`，被丢弃的条目发 WARNING | 已实现（B 半） |
| `agenerp/apply.py` · `execute_plan(plan, site, client=None)` | **对站点执行**：删除已实现；`creates` / `updates` **显式拒绝** | 已实现（B 半） |
| `agenerp/apply.py` · `ApplyDirectionError` | 方向不变量的失败机制：裸 `assert` 换成显式 `raise`（`-O` 下不消失） | 已实现（B 半） |
| `agenerp/site.py` · `SiteClient.delete_custom_field` | 站点侧**字段**删除的唯一出口，只删 Custom Field | 已实现（B 半） |
| `agenerp/oob.py` · `drop_columns(doctype, columns)` | 站点侧**物理列**删除的唯一出口（§11.8）。删字段不删列，两个出口管两件事 | 已实现（清除面） |
| `agenerp/apply.py` · `drop_orphan_columns(deleted, site)` | 清除面的作用域收窄：只删 `本次删掉的 fieldname ∩ schema_drift(doctype)` | 已实现（清除面） |
| `agenerp/pack.py` · `apply_pack(path, site)` | 委派链的入口，签名不变；委派链**四步**（读包 → 求差 → 收窄 → 执行） | 已委派 |
| `agenerp/snapshot.py` · `schema_drift(doctype)` | 物理表孤儿列巡检（§11.1 第三个部件），返回 `tuple[str, ...]` | 已实现（§11.8） |

**方向约定**（写反了不报错、只会把「删」算成「建」，所以写在这里）：`plan_apply(desired, current)` 的
`desired` = 定制包、`current` = 站点现状；而 `snapshot.diff(before, after)` 的 `added` = 只在 `after`、
`removed` = 只在 `before`。因此内部正确调用是 `diff(before=current, after=desired)`——**与 `plan_apply`
自己的形参顺序相反**。映射 `added→creates` / `removed→deletes` / `changed→updates`，
函数内另有方向不变量把守，`tests/unit/test_apply_plan.py` 有互换用例。

**定制包目录布局：取 `<root>/<scope>/<DocType>.json`。** 三个候选与取舍：

| 候选 | 说明 | 结论 |
|---|---|---|
| (a) `<root>/custom/<DocType>.json` | 贴 Frappe `export_customizations` 的 `<app>/<module>/custom/` 惯例 | 未取：`custom` 是写死的单层，装不下「快照 scope」这个维度 |
| (b) `<root>/<scope>/<DocType>.json` | 贴仓内既有 `OfflineSnapshotSource` 的布局 | **取此** |
| (c) 单文件 `<root>/pack.json` | 最省事 | 未取：一个 DocType 一个文件才有可读的 git diff，这正是 §11.2 要的东西 |

取 (b) 的理由是**口径同源**：`read_pack` 与 `OfflineSnapshotSource.read` 走同一个
`snapshot.read_scope_dir`（其中的载荷解析是同一个 `entries_from_payload`）。两套口径会让
「包里读到的」与「站点快照读到的」在同一份 JSON 上得出不同条目，求差结果随之失真。

**残余风险（2026-08-21 实测结论，原为 watch-only residual，现已关闭）**：
`export_customizations` 已落地（见本节末「定制包写入口径」），**布局 (b) 未被推翻**——
导出直接写 `<into>/doctypes/<DocType>.json`，与 `read_pack` / `OfflineSnapshotSource` 同一份
`read_scope_dir` 互为逆，`read_pack` 一行未改、`plan_apply` 形状未动。判据：
`tests/unit/test_pack_export.py` 的往返用例（导出 → `read_pack` → 与 `capture` 逐条相等）。

**承重条款已在 live 环境实测转绿（2026-08-21，B 半落地后）。** 工作项 5 绑定的
`tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site`
在 fixture 自己拉起的一次性栈上实跑 **PASSED**（该文件 `1 failed, 3 passed`）。
当时仍红的 `::test_no_orphan_column_left_behind` 红因**已从 `execute_plan` 挪到 `schema_drift`**——
它第一次走得到那一步。**该条其后也在 live 环境转绿**（2026-08-21，清除面落地，见上一小节）：
该文件四条在 live 下 `4 passed`，本节此前那句「唯一仍红」已不再成立。
`tools/gates/expected-red.txt` **一行未动**（默认判定环境下 L2 恒红，
`AGENERP_LIVE` 未设即 `pytest.fail`；划掉会让默认 `GATE_VERIFY` 立刻转红），
roadmap 工作项 5 / 6 均停在 `planned`。该矛盾此前登记在 `docs/masterplan/STATE.md` §3，
人已于 2026-08-21T14:21Z（`873c97f`）把 §3 的 `[open]` 全部关闭；口径以 §2
（2026-08-21T11:20Z「名单必须反映判定器实际看到的」）为准。
**live 环境下判定器退 1 是预期**（名单内的条目在 live 下变绿），不得被读成回归。
A 半的判据落在 `tests/unit/test_apply_plan.py`、B 半与清除面的落在
`tests/unit/test_apply_execute.py`（28 条，喂假客户端 + 假带外执行器，
`missions/p0-foundation.json` 的 `commands.test` 复跑得到）。

**`apply_pack` 现在红在哪**（2026-08-21 更新：两个站点侧落点都已接上）：离线跑仍红在
`SiteSnapshotSource.read`——没有活站点、没有凭据时它抛 `SiteError` 而**不伪装成功**，
判据是 `tests/unit/test_apply_plan.py::test_apply_pack_reds_on_the_site_half_not_on_diffing`。
**有活站点时整条链路跑通**（读包 → 求差 → 收窄 → 删除），不再红在 `execute_plan`。

`agenerp.apply` 在 `apply_pack` 的**函数体内**导入：`apply` 顶层导入 `snapshot`，`snapshot` 顶层
导入 `pack.normalize`，提到顶层就是 `pack` ↔ `apply` 循环导入。两种导入次序各有一个子进程判据。

**定制包写入口径（`export_customizations`，工作项 6 的前半，2026-08-21）**

「条目 → 包文件」只有一个写入口径，落在 `agenerp/pack.py`（读口径在 `agenerp/snapshot.py` ·
`read_scope_dir` / `entries_from_payload`，两者互为逆）：

| 落点 | 职责 | 状态 |
|---|---|---|
| `agenerp/pack.py` · `render_doctype_file(doctype, rows)` | 纯函数：条目 → 包文件文本。**唯一**排版落点 | 已实现 |
| `agenerp/pack.py` · `export_customizations(doctype, into, source=None)` | 站点读（复用 `capture` + `SiteSnapshotSource`）→ 过滤该 DocType → 写 `<into>/doctypes/<DocType>.json` | 已实现 |

**站点读取路径不新开第二条查询**：`export_customizations` 走
`capture(PACK_SCOPE, source=SiteSnapshotSource(site))` 再按 `entry.doctype` 过滤。
往返一致因此**由构造保证**（同一来源、同一投影、同一 `normalize`），关分页的完整性直接继承 §11.7。
`source` 是可选注入（默认 `None` → 按 `AGENERP_SITE` 构造站点来源），目的与
`SiteSnapshotSource.client` 一样：让单测喂假客户端，不是给产品代码多一条配置路径。
**站点名未配置、站点答不上话、认证失败一律抛 `SiteError` 且不落任何文件**——
`resolve_source` 的「无站点配置就退回离线来源」在这里是**危险的**：它会把一个空包写进磁盘，
而空包在第 3 顺位读起来跟「该 DocType 的定制全被删了」一模一样。

**包文件排版取「逗号独占一行」。** 三个候选与取舍：

| 候选 | 说明 | 结论 |
|---|---|---|
| (a) `json.dumps(indent=2)` 全展开 | 最常见 | 未取：新增一个字段会带出 `"fieldtype": "Data",` 这类行，`test_export_produces_readable_diff_only` 的逐行断言直接红 |
| (b) 一条目一行 + **行尾逗号** | 最像手写 JSON | 未取：探针插到数组**末尾**时要给前一个条目补逗号，那一行随之改动而它不含探针名 → 红。今天 `Item` 上恰好 0 条定制使该情形不可达，但那是**站点数据的偶然**，不是产物形状的性质 |
| (c) **一条目一行 + `,` 独占一行**，`[` / `]` 各自独占一行 | 仍是严格 JSON | **取此**：任意位置插入只新增「条目行 + 逗号行」两行，而 `,` 自身满足门禁那条 `line.strip() in "{}[],"` → 四种插入位置全过 |

`[` 与 `]` 必须各自独占一行（不写 `"custom_fields": []`）：否则数组从空变非空会改到那一行，
而那一行既不含探针名也不是括号行。**零定制也必须落盘**——门禁 baseline 走 `git diff HEAD`，
它看不见未跟踪文件，基线不落盘的话 `assert changed` 恒红。

**属性投影不收窄（2026-08-21 裁定）**：沿用 §11.7 的 `entries_from_site_rows` 口径（剥易变键后全留）。
理由是往返不变量要求收窄**两侧同源**，而那个唯一落点同时喂着 `test_snapshot_diff_structured.py`
在 live 环境刚转绿的那条断言——**默认判定环境下它恒红（在预期红名单内），这条回归在 `GATE_VERIFY` 里看不见**。
用「让包文件行短一点」换一条只有 live 才看得见的回归风险不划算。
**残余风险**：条目行长在 1KB 量级（活站点实测 Custom Field 行 58 键，剥易变键并去掉 `dt` / `fieldname`
后每条 52 个属性），人读 `git diff` 要横向滚动；缓解是「一条字段一行」这个粒度本身——
加/删/改哪个字段仍一眼可见。将来若收窄，落点仍是 `entries_from_site_rows` 一处，且必须同 phase 复跑 live 快照门禁。

**残余风险（`Decision` 2）**：本项目**不用** Frappe 原生 `export_customizations`
（它要 `developer_mode`、导出目标是 app 目录、产物形状由 Frappe 定），代价是与官方定制包格式**不互通**；
真要互通时写一个转换器即可，代价局部。

**活站点实测（2026-08-21，栈端口 18080）**：
`AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q`
→ **exit 1**，`2 failed, 2 passed`：`test_added_field_exports_into_pack` 与
`test_export_produces_readable_diff_only` **两条 PASSED**；另两条 FAILED，逐字红在
`agenerp/apply.py:107` 的 `execute_plan` `NotImplementedError`（**不是红在导出上**）。
**验证范围**：只在本机 live 环境做过；`missions/p0-foundation.json` 的 `commands.test` 跑不到这两条，
CI 亦未验证——代偿控制是下面两条变异 + 独立关闭审计。

**两条变异验证（都指名红因）**，以及它们顺带暴露的**门禁牙齿边界**：

| 变异 | 结果 |
|---|---|
| 包文件顶层加一个 `"exported_at"` **常量**行 | `test_export_produces_readable_diff_only` **仍绿**（`3 failed → 不含它`）。原因：常量行两次导出逐字相同，`git diff` 里根本不出现。**这条门禁判的是「变动行」，不是「有没有多余的键」** |
| 同一位置改成 `datetime.now().isoformat()`（真时间戳） | **转红**，逐字：`AssertionError: diff 里夹带了与本次改动无关的内容：['"exported_at": "…21:37:50.039229",', '"exported_at": "…21:37:50.523794",']` |
| 渲染时丢掉条目的 `fieldname` 键 | `test_added_field_exports_into_pack` **转红**，逐字：`AssertionError: 新增的字段没有进定制包`（这条门禁的牙齿此前一次都没验过） |

第一格是**新事实，照实记**：`test_export_produces_readable_diff_only` 挡的是**易变**噪声，
挡不住恒定的多余键——真要挡后者得靠往返不变量（`tests/unit/test_pack_export.py`），不是靠它。
第三格还顺带说明：丢掉 `fieldname` 后 `test_export_produces_readable_diff_only` **仍绿**，
因为条目行里的 `"name": "Item-agenerp_gate_roundtrip"` 仍含探针名——**两条门禁各挡各的，谁都不是另一条的替身**。

两次变异后均已还原：`shasum -a 256 agenerp/pack.py` 变异前与还原后同为
`fa5f2747…1a6889ad`，`git status --porcelain` 相对变异前基线无残留。

**未收窄投影，故 `agenerp/snapshot.py` 一个字未动**（`Decision` 3），按 plan 这一格无需回归；
仍在同一 live 环境顺手复跑了一次作为加固：
`… python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q` → **exit 0**，`3 passed`。

#### apply 对活站点执行删除的三条裁定（B 半，2026-08-21）

plan `docs/plans/p0-foundation/2026-08-21-1922-3-execute-plan-site-delete.md` 的 Phase 1，
全部依活站点实测得出（栈端口 18080），不是推断。

**裁定 1 · 作用域收窄口径 = 包目录里「存在文件」的 DocType 集合。**
落点是 `agenerp/apply.py` 新增的 `pack_doctypes(path, scope)`，在 `agenerp/pack.py` · `apply_pack`
的委派链里过滤 `plan.deletes`（`read_pack` 的签名与返回类型不动、`plan_apply` 的求差逻辑不动）。

必要性是实测出来的：`apply_pack` 的 `current` 是**整个 scope 的站点现状**，而门禁给的包只有 `Item.json`。
实测那一次 `plan.deletes` 有 **11 条，其中 10 条是别的 DocType 上应用自带的字段**
（`Address.tax_category`、`Customer.crm_deal` …）。不收窄就会把它们全删光，而门禁那条断言
（只看 Item 上探针没了）**照样绿**——判据挡不住这个错误，所以收窄自带判据
（`tests/unit/test_apply_execute.py` 的正反两断言写在同一个用例里）。

| 候选 | 说明 | 结论 |
|---|---|---|
| (a) 不收窄 | 直接执行 `plan.deletes` | 未取：实测会删掉 10 条应用自带字段 |
| (b) 按**包条目**里出现过的 DocType | 从 `ApplyPlan` 的条目里推 | 未取：`remove_field` 之后 `Item.json` 是**「文件在、数组空」**，`Item` 不在集内 → 探针不会被删，承重条款照样红（实测坐实） |
| (c) **按包目录里存在文件的 DocType** | 「文件在、数组空」= 「我管这个 DocType，且它应该没有定制」 | **取此** |
| (d) `apply_pack(..., doctypes=)` 显式参数 | 更精确 | 未取：门禁调用式是 `apply_pack(pack_repo.path, site=...)`，必填参数改不了调用方，可选参数则默认路径仍不安全 |
| (e) 让 `capture` 只读包里的 DocType | 把安全约束塞进快照层 | 未取：`capture` 是共享件，污染职责边界 |

covered 的判定口径与 `entries_from_payload` **同源**：载荷里的 `doctype` 键优先、文件名 stem 兜底。
只按文件名算的话，一份 `Item.json` 内写 `{"doctype": "Customer"}` 会让管辖面与条目面对不上。
**残余风险**：靠**删除包文件**表达「清空该 DocType 的全部定制」这一意图表达不出来（删文件 = 「不管它」）；
「文件在、数组空」这条路是通的，且默认口径偏保守（少删），错的方向在安全那一侧。

**裁定 2 · `is_system_generated` 的 Custom Field 排除在删除集外。**
实测分布：站点上 10 条 Custom Field **全部** `is_system_generated = 1`，散在 7 个 DocType 上，
全部由 ERPNext / CRM 应用装上；REST 建出来的探针是 `0`。**按 DocType 收窄挡不住这一类**——
包里一旦出现 `Customer.json`，`Customer.crm_deal` 就落进删除集，删掉可能直接弄坏应用功能。
`normalize` 不剥这个键（不含 modified / creation / owner / `_comments`），所以它在快照条目的
`attributes` 里读得到，判据面是存在的。
**残余风险**：包因此**不是**该 DocType 的完整真相源——从包里删掉一条 `is_system_generated` 的字段，
apply 不会照做，`git revert` 撤不掉这一类定制。代价被限定在「应用自己装的字段」上，那一类本就不该由定制包管辖。

**裁定 3 · 建（`creates`）/ 改（`updates`）一律显式拒绝。**
`execute_plan` 在两者任一非空时抛 `NotImplementedError` 并指名 successor。
备选「一并实现」未取（P0 无判据覆盖，等于交付没人验的破坏性代码）；
备选「静默跳过」**明令禁止**（假装成功正是本仓反复挡的那种事）。
**残余风险**：站点侧的回滚只能手工重建（`POST /api/resource/Custom Field` 或 Desk），
「用包把删掉的字段建回来」这条能力要等 `creates` 落地。

**被收窄 / 被排除的条目一律不静默**：`logging.getLogger("agenerp.apply")` 发 WARNING 并逐条列出
`(doctype, fieldname)`。这是「不许静默丢弃」这个安全承诺的唯一判据面，也是 `agenerp/` 全树的第一处 logging。

**删除的传输语义（活站点实测）**：`DELETE /api/resource/Custom Field/<dt>-<fieldname>` 成功返回
**HTTP 202** `{"data":"ok"}`（不是 200/204），随后 `GET` 同一路径返回 404；删一个不存在的 name 返回
**404** `DoesNotExistError`。因此成败判据沿用 `SiteClient._request` 的 `200 <= status < 300`，
不为删除另开分支；**「要删的东西不在」被判为失败并抛 `SiteError`，不静默吞掉**。


#### apply 之后不留残列：清除面与它的作用域裁定（2026-08-21）

**为什么 apply 必须多做这一步**：Frappe 删 Custom Field **不删物理列**（Spike 06 的结论在
v15.119.3 上复验仍成立）。不清的话反复增删会静默累积孤儿列——2026-08-21 活站点实测，
`tabItem` 上已积了 6 条。判据是
`tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`。
**只做巡检转不了绿**：`schema_drift` 诚实实现之后，探针列会被如实报成孤儿列，
门禁照旧红——巡检与清除必须同时做。

**Decision：清除的作用域收窄到「交集」，不是「该 DocType 上的全部孤儿列」。**

| 候选 | 说明 | 结论 |
|---|---|---|
| (a) `trim_table(doctype, dry_run=False)` | Frappe 自己的语义，一次把该 DocType 上**所有**孤儿列删光；最省代码、完全复用框架 | 未取：实测 `Item` 上 6 条孤儿列里**有 5 条不是本次 apply 造成的**（历轮门禁探针 + 人工探查）。选它等于让一次 apply 顺手删掉五列历史数据，把「清理」和「apply」混成一件事，违反「apply 只做包表达过的意图」 |
| (b) 只删「本次 apply 真删掉了 Custom Field」的那些列 | 取 `execute_plan` 收窄后的 `deletes` 与 `schema_drift` 的**交集**，逐列 `DROP COLUMN` | **取此**：与本节上面的「作用域收窄」是同一条原则 |

**门禁挡不住选 (a) 的错误**——它只看探针列没了，多删的另外 5 列一个字都不会说。
这与 `narrow_deletes` 那次是同一个陷阱换了一层（那次不收窄会连删 11 条而门禁照样绿），
所以收窄自带判据（`tests/unit/test_apply_execute.py` 的 ⑨ 组）。

**残余风险与它的两道闸**：(b) 要自己拼一条 DDL。因此一列要进 DDL 必须**同时**满足
① 在 `schema_drift(doctype)` 的返回集合里（**Frappe 自己**判它是孤儿）、
② 在本次 apply 真删掉的 fieldname 集合里；再加 §11.8 的标识符白名单
（`^[A-Za-z0-9_ ]+$`，v0 的刻意收窄）。任一条件不成立就**跳过并 WARNING**，
标识符不合法则直接抛 `OobError`——两者不是一回事，不许混。

**Decision：DDL 走 `db` 容器直发，不加进 `ALLOWED_CALLS`。**

| 候选 | 说明 | 结论 |
|---|---|---|
| (i) `bench execute frappe.db.sql_ddl --kwargs "{'query': …}"` | 调用方给整条 SQL | 未取：这正是 §11.8 拒绝过的通用 RCE 接口，把它加进白名单等于把白名单作废 |
| (ii) `docker compose exec -T db mariadb -e "ALTER TABLE …"` | DDL 走 db 容器，不经任何 Python 执行面 | **取此**。它**不与 §11.8 的巡检选型冲突**：那里拒绝候选 (b) 的理由是「不要第二套**字段口径**」，而这里不做任何字段判断——判断已由 `schema_drift` 做完，db 侧只执行一条列名已被验证过的 DDL |
| (iii) 扩白名单到 `trim_table(dry_run=False)` | —— | 未取：与上面的作用域裁定 (b) 直接冲突 |

**顺序是先删字段、再清列**，不能反：反过来 Frappe 会把该列当成「字段还在」而不判它是孤儿
（判据 `test_columns_are_dropped_only_after_the_custom_fields_are_gone`）。

**`schema_drift` 抛错时 `execute_plan` 也抛，不吞**：把「巡检没跑起来」读成「没有孤儿列」，
残列会静默累积而门禁照样绿。

**作用域的活站点实测（2026-08-21，方向是「减少」不是「新增」）**：门禁跑前
`schema_drift("Item")` 回 6 条，跑后回 5 条——**消失的恰好只有 `agenerp_gate_roundtrip`**
（本门禁的探针，也就是本次 apply 自己造成的那一列）；
`agenerp_gate_probe` / `agenerp_explore_probe` / `agenerp_explore_probe2` /
`agenerp_scope_probe_item` / `agenerp_probe_orphan` **一条不少地还在**。
这是「没有顺手多删」的正向证据。原文在 plan
`docs/plans/p0-foundation/2026-08-21-2220-1-schema-drift-orphan-columns.md` Phase 2。

**门禁自己在污染站点（已登记，本 plan 不处置）**：`tests/gates/conftest.py` 的 teardown 只删
Custom Field 不删列，所以此前每跑一轮就留一条孤儿列——清除面接上之后这条止血了，
但 teardown 本身在红线 1 内，loop 不得改。触发条件与 successor 见
`docs/backlog/gate-fixtures-pollute-the-live-site.md`。

### 11.7 站点只读传输在本仓的落点（工作项 4 的 B 半，2026-08-21）

§11.5 末节留下的接缝接上了：`agenerp/site.py` 是 `agenerp` 里**唯一经 HTTP/REST** 打到真站点的模块，
`agenerp/oob.py`（§11.8，2026-08-21）是第二条打到站点的传输，走的是带外容器命令、够得到物理表；
`SiteSnapshotSource.read` 经它回答「站点现状是什么」。plan `docs/plans/p0-foundation/2026-08-21-1922-1-site-snapshot-source-live.md`。

| 落点 | 职责 | 状态 |
|---|---|---|
| `agenerp/site.py` · `SiteClient` | 连活站点的**唯一 HTTP** 传输落点（物理层那条在 §11.8）。`get(path, params)` 返回已解析载荷；`list_resource(doctype)` 列出全部行；`find_one(doctype, filters)` 按 filters 找至多一份（**只把「查得到、但零行」判成不存在**） | 已实现（读方法 + **三条**写方法：`delete_custom_field` · `create_doc` · `ensure_doc`，见本节末尾的 2026-08-22 改准段与 §12.9；白名单口径见 `agenerp/site.py` 模块头第 4 条） |
| `agenerp/site.py` · `SiteError` | 站点侧一切失败的统一异常：连不上 / 认证失败 / 非 2xx / 载荷不是 JSON | 已实现 |
| `agenerp/site.py` · `client_from_env(site)` | 环境 → 客户端的组装点，缺凭据时抛并指名变量 | 已实现 |
| `agenerp/site.py` · `Transport` / `UrllibTransport` | 可注入的传输接缝：单测喂假件，产品走标准库 | 已实现 |
| `agenerp/site.py` · 写 / 删方法 | 归工作项 5 的删除段（plan [`2026-08-21-1922-3`](../plans/p0-foundation/2026-08-21-1922-3-execute-plan-site-delete.md)）。**白名单有且只有一条** `SiteClient.delete_custom_field`（模块头第 4 条，`agenerp/site.py:16-17`）；不提供「删任意 DocType 文档」的通用方法 | 已实现（判据 `tests/unit/test_site_client.py` 的 `WRITE_METHOD_ALLOWLIST`）。**⚠️ 2026-08-22 就地改准（确认的 owner-doc 漂移，Minimum Rule 14 不降级）**：本格此前是一句**否定态的状态词**（原文逐字取法：`git show 57702c5:docs/architecture/module-boundaries.md | sed -n '581p'`；此处不复述那个词，因为本 plan 的机判判据要求本表行范围内不再出现它）。**那句话从 2026-08-21 起就是假的**——`1922-3` 已于 **2026-08-21 关闭**，方法已落地并在活站点上实测删过字段，本次是**改准一句假陈述，不是「新增一项」**，它整整假了一天。同一份文档的 §11.6 落点表（`:338` 一带）当时就写着「已实现（B 半）」，两张表在同一个文件里互相矛盾了同样长的时间。改准由 plan [`2026-08-22-1041-1`](../plans/p0-foundation/2026-08-22-1041-1-destructive-write-owner-doc-alignment.md) 做 |

**配置口径（环境变量，产品代码不内置口令默认值）**：

| 变量 | 含义 | 默认 |
|---|---|---|
| `AGENERP_SITE` | 站点名，同时用作 HTTP `Host` 头 | 无（未设即走离线来源，§11.5 的次序不变） |
| `AGENERP_SITE_URL` | 站点基址 | `http://127.0.0.1:${AGENERP_HTTP_PORT:-8080}`，与 `docker-compose.yml` 的端口映射同源 |
| `AGENERP_API_KEY` / `AGENERP_API_SECRET` | Frappe token 认证，**必须成对** | 无 |
| `AGENERP_ADMIN_USER` / `AGENERP_ADMIN_PASSWORD` | 会话登录（token 未配时的回退） | 用户名 `Administrator`；**口令无默认值** |

`tests/gates/conftest.py` 给 fixture 留了 `admin` 这个口令默认值，那是**测试脚手架**。
产品代码内置口令等于把「本地默认口令」变成一条对外暴露时会咬人的隐性配置，所以缺凭据时
显式抛 `SiteError` 并指名缺哪个变量。半套 token（只给 key 或只给 secret）判为配错而不是
静默回退——静默回退会让「token 没生效」在日志里完全看不见。

**Decision：认证取「token 优先、会话登录回退」。** 备选与否决理由：

| 候选 | 说明 | 结论 |
|---|---|---|
| (a) 只做会话登录 | 最省事 | 未取：把口令带进每次运行，且 Frappe 的登录端点有速率限制 |
| (b) 只做 token | 更贴生产 | 未取：零依赖 compose 栈上没有现成 key，L2 门禁跑不起来 |
| (c) token 优先、会话登录回退 | 两者兼容 | **取此** |

**残余风险（如实记）**：回退路径把口令读进进程内存并随登录请求发出。缓解只有一条——
配了 token 就完全不走登录往返（判据 `tests/unit/test_site_client.py::test_token_credentials_skip_the_login_roundtrip`）。
生产站点应当配 token；`AGENERP_ADMIN_PASSWORD` 是本地零依赖栈的通道。

**三条实测硬约束，全部表达成了断言**（不是注释）：

| 约束 | 出处 | 判据 |
|---|---|---|
| `Host` 头必须等于站点名 | `docker-compose.yml` 的 backend 探针注释：gunicorn 按 Host 解析站点，打 `127.0.0.1` 会被当成一个叫 `127.0.0.1` 的站点而 404 | `test_host_header_is_the_site_name` |
| 路径必须 URL 编码（保留 `/`） | DocType 名带空格（`Custom Field`），不编码时 `http.client` 以 `URL can't contain control characters` 拒掉 | `test_path_is_url_encoded_keeping_slashes` |
| 必须显式关分页 | Frappe `/api/resource` 默认只回 20 条；静默截断会让「未改动 → diff 为空」在缺条目时照样绿 | `test_list_resource_explicitly_disables_paging` + `test_list_resource_returns_every_row_the_site_gave`，外加 live 层实测条目数（§11.5 的完整性不变量） |

**只读不变量的判据形式是「显式白名单」而不是「一个写动词都不许出现」**：
`tests/unit/test_site_client.py::test_site_module_exposes_no_unlisted_write_method` 断言
「公开方法名里出现 `agenerp/contracts.py` 的 `WRITE_VERBS` 的，必须在一个可见的字面量白名单内」，
**本 plan 内白名单为空**。写成绝对禁令的话，工作项 5 的删除段在同一模块上加 `delete_custom_field`
会被一条已关闭 plan 的判据当场打红，届时只剩「动别人的判据」和「卡住」两条路。
白名单让它按**收窄**演进：每加一个写方法都要付一次 diff 和一次留痕。

**⚠️ 2026-08-22 就地改准（plan `2026-08-22-2107-1`）：本节标题里的「只读」与
`agenerp/site.py` 原 docstring 里的「本模块的写面只该覆盖『结构定制』」，两句都已不再成立。**
改准前本节通篇按「站点**只读**传输 + 一条例外」的口径写；2026-08-22 起 `SiteClient` 是一个
**通用写客户端**：`create_doc(doctype, payload)` 能建**任意 DocType** 的文档，
`ensure_doc(doctype, key, payload)` 在它上面做「先查后建、**只建不改**」的幂等。
写面覆盖的已经是**业务主数据**（公司 / 科目 / 仓库 / 物料 / BOM…），不是结构定制。
**这是扩张，就写成扩张，不写成「一直如此」。** 本节标题保留「只读传输」是因为它记的是
工作项 4 那一次交付的历史落点；**当前形态以本段为准。**

**扩张的代偿有三条，且都可判**（不是靠自觉）：

1. `docs/context/ai-autonomy-policy.md` Protected Areas 新增「对活站点的**非破坏性写**（建 / 改）」行，
   定级 `plan-first`，Required Evidence 含**一条对可逆性说话的**。此前该区域默认 `implement`。
2. 上面那道白名单守卫**已登记** `SiteClient.create_doc` 与 `SiteClient.ensure_doc`。
   ⚠️ `ensure_doc` 的名字里**一个 `WRITE_VERB` 都没有**，守卫**扫不到它**——它是**主动登记**的。
   只登记守卫扫得到的，等于让守卫替人决定该留什么痕。守卫的牙齿由变异验证实证
   （删掉 `create_doc` 那条 → `tests/unit` 必红并逐字点名该方法）。
3. `agenerp/seedsite.py` 是这两个方法**目前唯一的调用方**（§12.9）。
   **残余风险照实记**：这三条都不阻止将来出现第二个调用方，也不约束「写的是什么」。
   出现第二个调用方时应评估是否要把写面收进一个更窄的门面。

**`find_one` 为什么不走「GET 单文档、404 判不存在」**：2026-08-22 实测，站点对
`Warehouse` / `Account` / `Item` / `BOM` **不采纳显式 `name`**（分别按
`warehouse_name`/`account_name` + 公司缩写、`item_code`、命名序列 `BOM-{item}-{###}` 派生），
按 name 取单文档对半数 DocType 无从下手。列表端点 + `filters` 的「零行」是 **HTTP 200**，
与「站点答不上话」在状态码上天然分开 —— 这正是本模块第 1 条约束（不伪装成功）要的形状。
**只把「查得到、但零行」判成不存在**；把非 2xx 判成「不存在」会让 `ensure_doc` 在站点宕机时
一路重复建，这条有专门的参数化单测（401 / 403 / 500 / 502）。

**不起本地 `http.server` 做单测**：本机 8080 已被另一套常驻栈占用是实测事实，
在 `GATE_VERIFY` 与 CI 的 `gates-l1` 里再绑一个端口是自找的不稳定源。单测喂注入式假传输；
唯一例外是「连不上 → `SiteError`」那条，它必须走真 `UrllibTransport`（假件证明不了
`URLError` 被翻译过），用一个刚释放的端口构造 connection refused，不留监听。


### 11.8 带外容器命令传输在本仓的落点（工作项 6 的第二个 plan，2026-08-21）

**为什么需要第二条传输，而不是把 §11.7 扩一扩**：`schema_drift` 要回答的是
「物理表上还剩哪些列」。Frappe **没有任何白名单方法**回物理列，且 `docker-compose.yml`
不对宿主发布 db 端口——REST 那条路不是取舍问题，是**够不到**。所以另起一条，
不是给 §11.7 加功能。

模块：`agenerp/oob.py`（out-of-band）。零第三方依赖，只用 `subprocess` + `json`，
与 `agenerp/site.py` 同一条约束。

**三个 exec 目标**（模块不叫 `bench.py` 就是因为它不只跑 bench）：

| 目标 | 命令 | 方向 | 落点 |
|---|---|---|---|
| `backend` | `bench --site <site> execute <白名单函数> --kwargs …` | 读 | `run_json` |
| `backend` | `cat sites/<site>/site_config.json` | 读 | `read_site_config` |
| `db` | `mariadb … -e "ALTER TABLE … DROP COLUMN …"` | **写** | `drop_columns`（§11.6 的清除面） |

| 落点 | 职责 | 状态 |
|---|---|---|
| `agenerp/oob.py` · `OobError` | 带外命令一切失败的统一异常，与 `SiteError` 平级 | 已实现 |
| `agenerp/oob.py` · `ALLOWED_CALLS` | **「函数名 → 钉死的 kwargs」映射**，v0 只有 `frappe.model.meta.trim_table → {"dry_run": True}` | 已实现 |
| `agenerp/oob.py` · `run_json(function, doctype, …)` | 白名单内的 `bench execute`，返回已解析 JSON | 已实现 |
| `agenerp/oob.py` · `read_site_config(site, …)` | 读站点 `site_config.json`，**DDL 拿库名的唯一来源** | 已实现 |
| `agenerp/oob.py` · `Runner` / `ComposeExecRunner` | 可注入的执行接缝：单测喂假件，产品走 `docker compose exec -T` | 已实现 |
| `agenerp/oob.py` · `drop_columns(doctype, columns, …)` | 本模块**唯一的写动作**，见 §11.6 的清除面 | 已实现 |
| `agenerp/snapshot.py` · `schema_drift(doctype)` | 孤儿列巡检，返回 `tuple[str, ...]`（排序去重） | 已实现 |

**Decision：巡检口径复用 Frappe 自己的 `trim_table`，不自建第二套。**

| 候选 | 说明 | 结论 |
|---|---|---|
| (a) `bench execute frappe.model.meta.trim_table` | 复用 Frappe 的孤儿列定义，`dry_run` 同时给出巡检与清除两个模式 | **取此** |
| (b) `docker compose exec db mariadb` 直查 `information_schema` | 只读 SQL、不执行任何代码 | 未取：要把 `default_fields + optional_fields + child_table_fields` 与 `_` 前缀规则**抄一遍**，产生第二套字段口径（§11.5 的「不该有第二份」）。Frappe 一次升级就能让两边错开，而错开的表现是**孤儿列漏报**——最难发现的那种假绿 |
| (c) 经 REST | —— | 未取：够不到（见本节开头） |

一次性交叉验证（**不留成常驻的第二套口径**）：2026-08-21 在活站点上把
`set(schema_drift("Item"))` 与 `information_schema.COLUMNS` 减去 `tabDocField` / `tabCustom Field`
的结果对账，两侧相等（17 行 = 11 个基础列 + 6 条孤儿列）。原文在 plan
`docs/plans/p0-foundation/2026-08-21-2220-1-schema-drift-orphan-columns.md`。
**不拿 `trim_table(dry_run=True)` 做交叉验证**——那是拿函数和它自己的后端对账，什么也证明不了。

**与红线 7（不得让 Agent 生成运行时 Server Script）的界线，必须写清楚不许含糊过去**：
红线 7 禁的是把可执行脚本**装进站点**、由站点在处理请求时自己执行——那是**持久化**的 RCE 面。
`agenerp/oob.py` 是运维侧的**一次性带外调用**：不留任何站点态，进程退出即结束。
这条界线不是靠「意图」立住的，靠的是下面两条机制：

1. **`ALLOWED_CALLS` 钉到参数一级。** 它是「函数名 → kwargs」映射，不是名字集合。
   调用方只能给 `doctype`；`dry_run` 恒为 `True`，**传不进 `False`**。只钉名字挡不住
   `trim_table(dry_run=False)`——那会把该 DocType 的孤儿列一次删光，正是 §11.6 清除面
   明文排除的作用域。
2. **不提供通用 SQL / 通用函数入口。** `frappe.db.sql_ddl(query=…)` 这类「调用方给整条 SQL」的
   接口被显式排除：把它加进白名单等于把白名单作废。DDL 因此走 `db` 容器的
   `drop_columns`，列名先经两道验证（§11.6），**不与 `ALLOWED_CALLS` 共用**——
   那张表管的是 Python 函数调用，管不到 DDL。

**两条实测硬约束（不是猜的）**：

| 约束 | 出处 | 判据 |
|---|---|---|
| `bench execute --kwargs` 的载荷是 **Python 字面量，不是 JSON** | `frappe/commands/utils.py:258` 对它做 `eval(kwargs)`；喂 `json.dumps` 的结果红在 `NameError: name 'true' is not defined`（2026-08-21 实测红过一次） | `test_bench_kwargs_are_a_python_literal_not_json` |
| 库名只能读、**推不出来** | `docker-compose.yml` 的 `db` 服务只设 `MYSQL_ROOT_PASSWORD`、不设 `MYSQL_DATABASE`，`mariadb` 没有默认库；库名形如 `_5e5899d8398b5f7b`，从 `AGENERP_SITE=frontend` 推不出来 | `test_read_site_config_returns_the_db_name` |

**缓存的连带事实（第三轮独立评审在活栈上带回，记此备查）**：Frappe 把列清单缓存在 Redis 的
`table_columns` 里，带外 `ALTER TABLE` 本会让它变陈旧、从而让门禁继续红；但 `trim_table` 的
**第一行**就是 `frappe.cache.hdel("table_columns", …)`，所以每次 `schema_drift` 调用都会先把
缓存打掉。上面的 Decision (a) 与 §11.6 的 DDL 走 db 容器因此能安全组合。

**不伪装成功**：命令起不来 / 非零退出 / 载荷不是 JSON —— 一律抛 `OobError`，
**绝不降级成空列表**。空列表是「没有孤儿列」这个合法结论的表示，用它兼表「命令没跑起来」
会让门禁在栈坏掉时照样绿——与 §11.7 第 1 条是同一条约定。

**「不伪装成功」的唯一例外，2026-08-22 实测追加（plan `2026-08-22-0228-2`）**：
上面那条「载荷不是 JSON 一律抛」在**全新站点**上会把一个**合法结论**判成故障，
表现是 `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`
**清干净了反而红**——CI runner 2 跑红 2 次（run `32509351108`），本机 `down -v` 冷起后 3 跑红 3 次，
红因原文 `agenerp.oob.OobError: frappe.model.meta.trim_table 的输出不是 JSON：''`。

机制逐字（v15.119.3 容器内实读 `apps/frappe/frappe/commands/utils.py:285`）：`bench execute`
末尾是 `if ret:` 才 `print(json.dumps(ret))`——**假值返回一个字都不打印**。所以
「该 DocType 上一条孤儿列都没有」（`trim_table` 回 `[]`）在这条通道上就是**零字节 stdout**。
本机常驻站点长期躺着别的门禁留下的历史孤儿列（冷起前实测 `["agenerp_gate_probe"]`），
清完自己的探针列后集合仍非空 → 打印 JSON → 绿；**全新站点没有任何残留 → 清完必然归零 → 必然红**。
这逐字解释了此前记录的「本机 6 跑红 1 次、runner 2 跑红 2 次」差异，起草时「runner 方向更有利」
的推理由此被证伪。

处置：`run_json` 对**退出码 0 且 stdout 全空**返回哨兵 `FALSY_RESULT`，由调用方按自己的
返回类型翻译（`schema_drift` → `()`）。**刻意不返回 `None` 也不直接返回 `[]`**：
`json.loads("null")` 就是 `None`，用它兼表两件事会重新制造本节要挡的歧义；直接给 `[]`
等于替调用方猜「这个函数返回列表」，白名单以后多一条返回 dict 的函数那个猜就会静默错掉。

**这不是放宽，三种真故障够不到该分支**（2026-08-22 冷起站点逐条实跑，全部非零退出，
先被 `_run` 拦掉）：函数不存在 → exit 1 `AttributeError`；函数内部抛错 → exit 1
`pymysql.err.ProgrammingError`；站点不存在 → exit 1。判据
`tests/unit/test_schema_drift.py::test_blank_stdout_is_not_confused_with_a_broken_command`
等 4 条。**清除面本身从未坏过**：同一轮实跑前后全量 `capture` 对照为
`entries added/removed: []`、`columns added/removed: []`，`information_schema` 独立确认
探针列不在 `tabItem` 上——红在**巡检的表达能力**，不在清除。

**配置口径（环境变量，全部带默认值）**：

| 变量 | 含义 | 默认 |
|---|---|---|
| `AGENERP_SITE` | 站点名 | 无（**不猜**：缺了就抛 `OobError`，猜一个站点名去跑 DDL 是本模块最不该有的行为） |
| `AGENERP_OOB_BACKEND_SERVICE` | 跑 bench / cat 的 compose 服务名 | `backend` |
| `AGENERP_OOB_DB_SERVICE` | 跑 DDL 的 compose 服务名 | `db` |
| `AGENERP_OOB_COMPOSE_FILE` | compose 文件路径 | 仓库根的 `docker-compose.yml` |

---

## 12. 种子数据集在本仓的落点

**这不是定制包。** §11 讲的是「把站点的结构定制变成可 diff 的产物」；本节讲的是
「把一份**业务数据**用程序确定性地长出来」。两者只共用一件东西：判定「两次是否一样」的那个 `diff`。
把它塞进 §11.x 会让「定制包」这个词同时指结构与数据，是错位，所以另起一级。

模块：`agenerp.seed`（包，非单文件）。零第三方依赖，纯标准库，不读时钟、不读环境、不联网。

### 12.1 单价对账：¥6,450 与 1,010 米对得上，机制不是移动加权均价

本仓此前的文档只记了结果（成品仓结余 1,010 米、价值 ¥6,450），没记它是怎么来的，
`6450 / 1010 = 6.3861…` 这个非整洁单价因此长期被当作「移动加权均价滚出来的实测值」。
**该猜测是错的，本次在冻结的证据仓里查到了更早的、含单价的原始记录并完成对账。**

原始记录：证据仓 `xm_pattern_demo/demo/business_flow.py` 的 `DEMO` 常量表
（`raw_rate` / `raw_qty` / `subcontract_cost` / `sales_rate` / `order_qty` / `delivery_qty` /
`approved_loss_qty`）与 `xm_pattern_demo/demo/bootstrap.py` 里三台工位的
`workstation_costs.operating_cost`。二者都在 `evidence-repo.env` 指定的 `XM_SHA` 上（只读，红线 6，本次未写入）。

对账（每一步都可复算）：

| 批次 | 构成 | 金额 | 单价 |
|---|---|---|---|
| 自制入库 1,000 米 | 原料 120 Kg × ¥35 = ¥4,200 + 工序 (300+180+120) 分钟 ÷ 60 × ¥80/小时 = ¥800 | ¥5,000 | **¥5.00/米** |
| 外协收货 1,000 米 | 投入原料 120 Kg × ¥35 = ¥4,200 + 外协服务费 ¥2,200 | ¥6,400 | **¥6.40/米** |

发货 990 米按 **FIFO** 全部出自自制批 → COGS = 990 × 5.00 = ¥4,950；
结余 = 自制批余 10 米 × 5.00 + 外协批 1,000 米 × 6.40 = ¥50 + ¥6,400 = **¥6,450**，数量 **1,010 米**。

**两个数同时对上，且是两个单价不同的批次按 FIFO 分层的结果，不是一个均价。**
对照组：若按移动加权均价，结余应为 (5,000 + 6,400) ÷ 2,000 × 1,010 = **¥5,757**，与实测的 ¥6,450 不符。
这条对照是本节最有用的部分——它把「站点用的是 FIFO」从推测变成了可证伪的结论。

顺带对上的还有两笔逾期：应收 990 × ¥18.8 = **¥18,612**、应付外协服务费 **¥2,200**，
均与 Spike 08 的实测数字逐分相等，**无需硬写合计数**。

**结论：本仓此前登记的「¥6,450 与 1,010 米单价对不上」这处数值漂移不存在，已对账关闭。**
后继文档若再引用这两个数，应连同上表的成本构成一起引，不要只引结果。

### 12.2 哪些数是硬断言，哪些是派生量

- **硬断言（生成器直接构造的常量）**：入库合计 2,000 米（1,000 自制 + 1,000 外协）、发货 990 米、
  已审批合理损耗 10 米、销售单量 1,000 米，以及两档批次单价 ¥5.00 / ¥6.40 的成本构成
  （原料单价 ¥35/Kg、BOM 用量 120 Kg/1,000 米、工时 600 分钟、工位费率 ¥80/小时、外协服务费 ¥2,200、售价 ¥18.8/米）。
- **派生量（由上面那些算出来，不许硬写）**：成品仓结余 1,010 米、结余价值 ¥6,450、COGS ¥4,950、
  应收逾期 ¥18,612、应付逾期 ¥2,200、毛利 ¥13,662、全部 GL 分录金额。
- 起草期的倾向是「数量硬断言、金额只如实记录不断言」，理由是金额被当成二手数字。
  §12.1 的对账推翻了这个前提：金额现在是**可从原始单价推出来的**，因此 `verify()` 把 ¥6,450 也列为断言项——
  它断的不是「抄来的数对不对」，而是「这份数据集的成本结构算出来还是不是那个数」。
- **备选与残余风险**：备选是 (b) 反推一个整洁单价去凑 ¥6,450、(c) 只断言数量。
  (b) 已被 §12.1 排除（真单价查到了，不需要反推）；(c) 会漏掉「FIFO 分层」这个关键机制，
  一旦有人把生成器改成移动加权均价，只断数量的判据不会发红。**残余风险**：若日后核实站点其实不是 FIFO，
  §12.1 的对账链会断，届时应改的是本节而不是把断言放松。

### 12.3 落盘形状

`<out>/<scope>/<DocType>.json`，一个 scope 一个目录、一个 DocType 一个文件，
**目录布局与 `agenerp.snapshot` 的离线来源一致**；scope 固定为 `seed`。
文件内容用业务自己的键：`{"doctype": ..., "records": [{"name": ..., ...}]}`。

- 采纳的是「目录形状对齐 + 判定器复用」，**不是**「解析口径复用」。
  `snapshot.read_scope_dir` 读的是定制包，条目身份键是 `fieldname`、载荷键是 `custom_fields`；
  业务单据的身份是单据号 `name`。把销售订单塞进 `custom_fields` 只是为了复用而说假话，
  会让「定制包」与「业务数据」在同一个解析口径下混淆。
- 复用的是**判定面**：`agenerp.seed` 把数据集转成 `snapshot.Snapshot`
  （每条记录一个 `SnapshotEntry`，`doctype` 取 DocType、`fieldname` 取单据号、`attributes` 取其余字段），
  再交给已通过门禁的 `snapshot.diff` 判「两次生成是否一样」。
  **本仓不为此写第二个比较器**——这正是「别写第二个判定器」那条既有教训的落点。
- **备选与残余风险**：备选是 (b) 单个大 JSON、(c) 一 DocType 一 JSONL。
  两者都要另写一套比较逻辑才能回答「两次一不一样」。**残余风险**：
  `SnapshotEntry.fieldname` 这个字段名在业务数据上语义偏窄（装的是单据号），
  阅读 `Snapshot` 时容易误读；缓解是本节这段文字，代价可接受，不值得为它改动已冻结的快照契约。

### 12.4 确定性从哪来

- 结构与全部参与断言的数量、单价、日期一律**构造式写死或由构造式算出**，不经 RNG。
- `random.Random(seed)` 只驱动**不参与任何断言的装饰性字段**（两张入库单的批号后缀）。
  只用 `randrange`，不用 `shuffle` / `sample`——后两者的实现细节在 CPython 历史上变过，
  把判据押在它们上面等于把确定性押在实现细节上。
- 生成路径上**禁止** `datetime.now()` / `time.time()` / `os.environ`。
  单据日期由固定基准日加固定偏移推出；「逾期 3 天」也是数据（数据集自带一个 `as_of` 日期），不是跑出来的。
  这条不是口头承诺：单测扫生成器的全部源码文件，出现上述任一符号即红。
- 因为保留了受控 RNG，`--seed` 是**真参数**：`generate(42)` 与 `generate(43)` 的批号不同，
  两者的全部断言项则完全一致。

### 12.5 两笔逾期的构造方式

由单据自然加总，**不硬写合计数**：应收来自那张 990 米的销售发票（990 × ¥18.8 = ¥18,612），
应付来自那张外协服务费采购发票（¥2,200）。硬写一个没有单据支撑的余额，本身就是一个新的业务荒谬，
会污染这个测例——而这个测例的全部意义正是「逾期落在字段上、积压不落在任何字段上」的对照。
两笔的实际加总与 Spike 08 的实测值**零差异**，没有舍入分歧要记。

### 12.6 生成物不进仓库

生成物只写 `--out` 指定的目录；不给 `--out` 时写进临时目录并把路径打到 stdout。**仓库里不落任何生成物。**

- 备选是「提交一份基准产物进仓、`--verify` 与它比对」。不取，理由有二：
  可推导的东西冻进 git 之后每次改生成器都要走一次「更新基准」的仪式；
  且验收原文要的是「同种子**两次生成** diff 为空」，比的是两次当场生成，本就不需要仓内基准。
- **残余风险**：没有仓内基准，**跨版本 / 跨机器**的确定性回归不会被 CI 自动发现——
  被比过的只有同一次运行内的两次生成。要补这一层需引入仓内基准，由后继 plan 决定，不在本次范围内。

### 12.7 判据归属（如实记录，不粉饰）

本项的验收命令是 `python3 -m agenerp.seed --seed 42 --verify`（主计划 WBS 原文写的是 `python`，
本机没有 `python` 这个可执行名，实际形态是 `python3`）。

**它不在 `missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 子进程复跑不到它**；
`missions/**` 是角色 B 禁区，要接进去只有人能做。代偿控制两条：
① 变异验证（故意破坏一条断言 → 该命令必须转红且指名道姓），证明判据有牙齿；
② 独立关闭审计复跑该命令。这与工具契约层 v0 的 `tests/contracts` 用的是同一套代偿。

**⚠️ 以下两句 2026-08-22 就地改准（plan `2026-08-22-2107-1`）。改准前逐字是**
「工作项『种子数据』本身**仍然没有绑定的门禁测试**」与「装载进活站点与站点侧断言那一半**被红线 1 挡着**」，
**两句在 2026-08-22 都已不成立**，属确认的 owner-doc 漂移（Minimum Rule 14 不降级）。

**改准一 · 工作项 7 有一条绑定门禁。** `tests/gates/test_seed_dataset_absurdity.py` **存在**，
**6 条**（确定性 ×2 / 1,010 米 · ¥6,450 精确值 / 积压对规则可见 / 不含图片 / 无第三方权利），
**2026-08-21 由人补齐**，实跑全绿，且**从未进过** `tools/gates/expected-red.txt`。
它是 **L1**，断的是**生成器**（`:23-24` 自带 `1010.0` / `6450.0` 两个常量副本，
刻意不从 `agenerp.seed.model` 取数）。因此 mission 规则「判据先行」对工作项 7 **是满足的**。
**但站点侧那一半仍然没有门禁**：`docs/backlog/gate-proposal-seed-dataset.md` 拟的三条 **L2** 断言
至今是提案文本，`Status: proposed`，采纳者是人（`Gates-Change-Approved-By:`）。
**不得把本段读成「工作项 7 站点侧已有门禁」——那是假的。**

**⚠️ 改准二（2026-08-22，plan `2026-08-22-2107-2`）· 站点侧那三条断言现在有了「可执行形式」，
但它仍然不是门禁。** 上一段那句「站点侧那一半仍然没有门禁」**依然成立，不得删**；
本段只补一件事：`python3 -m agenerp.seedsite --verify-site --site <site>` 已落地，
它读回站点自己算出的数、跟 `agenerp/seed/checks.py` 的 `EXPECTED_*` 比，
**不通过就退 1**（三条变异实测：见 §12.10）。
**它是一条 CLI 退出码，不是 `tests/gates/**` 下的测例**，`GATE_VERIFY` 复跑不到它，
CI 不跑它，任何人都可以不跑它。**因此「工作项 7 已有站点侧门禁」这句话仍然是假的。**
把提案变成门禁只差人的一次带 `Gates-Change-Approved-By:` trailer 的提交。

**改准二 · 红线 1 挡的是「站点侧断言**作为一条门禁**」，不是装载器。**
装载器落在 `agenerp/seedsite.py`（见 §12.9），**红线 1 不挡它**——2026-08-22 它已经落地并在活站点上跑通。
被挡着的只有「把站点侧断言写成 `tests/gates/**` 下的一条测试」这一件事，**那一半仍需人批，这一半没有变**。

工作项 7 收尾时仍置 `planned` 而非 `done`，**但理由不是「没有门禁」**：`done` 的定义要求
「对应门禁测试已转绿**并从预期红名单划掉**」，而那条 L1 门禁**从未进过名单**，
「划掉」这个动作没有对象，定义在字面上不可满足 —— 与工作项 4 / 9 同一情形。
该缺口登记在 `docs/backlog/needs-human-expected-red-handoff.md` 与
`docs/masterplan/STATE.md` 的 needs-human 队列，**由人裁定**。
### 12.8 已知漂移

- ~~「¥6,450 与 1,010 米单价对不上」~~ —— §12.1 已对账关闭，不是漂移。
  但**下游文案仍需一次人工复核**：`docs/backlog/implementation-roadmap.md` 的 P1 验收句
  与 `docs/design/view-dsl-and-eval.md` 的关键局限一节都只写了结果、没写成本构成，
  引用时容易再次被读成「均价 6.39」。本节即为那两处的解释落点。
- 站点的存货计价方法（FIFO）是**从两个实测数反推出来的**，证据仓里没有一行直接写着 `valuation_method`。
  §12.1 给了可证伪的对照（均价口径应得 ¥5,757），但这仍是推断而非直证。
  **⚠️ 这一条 2026-08-22 起仍然开着，不得写成已闭合。** 它说的是**冻结证据仓**那个站点
  （`docs/masterplan/evidence-repo.env` 的 `XM_PATH`，红线 6，只读），本仓无法对它取新证。
- **（2026-08-22 新增，plan `2026-08-22-2107-2`）本仓 `frontend` 站点的计价方法是实读的，不是推断的。**
  `GET /api/resource/Stock Settings/Stock Settings` → `valuation_method = "FIFO"`、
  `allow_negative_stock = 0`；`Item[XM-LACE-1000].valuation_method = ""`（空 → 回落到全局 FIFO）。
  同一站点上由**站点自己**算出 `Bin(XM-LACE-1000, XM 成品仓 - XM) = 1010.0 米 / ¥6,450.00`
  （`valuation_rate 6.386138614`）。**即 ¥6,450 在本仓是「在这个 `valuation_method` 下由站点实算成立」的**，
  不再只是算术对账。**这条实读事实只覆盖本仓站点，不覆盖上一条**——两者是两个站点，不要合并读。

### 12.9 主数据装载在本仓的落点（工作项 7 的 B 半第一段，2026-08-22）

plan `docs/plans/p0-foundation/2026-08-22-2107-1-seed-site-write-surface-and-masters.md`。
§12.1–§12.7 讲的是**纯内存/落盘的数据集**（A 半）；本节讲的是**把它装进活站点**的那一段。

**模块归属：装载器在 `agenerp/seedsite.py`，不在 `agenerp/seed/` 内。**
理由不是风格：§12 逐字规定 `agenerp.seed`「零第三方依赖，纯标准库，**不读时钟、不读环境、不联网**」，
而装载器必然读环境（站点凭据）并联网。把它放进那个包等于把一条**好的、且被 31 条单测依赖的**
不变量改松。取舍是「多一个同级单文件模块」（先例：`agenerp/oob.py`）换「生成路径保持纯净」。
**`agenerp/seed/**` 在这一段落地时一个字节未改**，只被只读引用。

**依赖顺序（写死在 `plan_steps()` 里，纯函数，可被单测直接判）**，共 40 步：

`Warehouse Type` → `Company` → `Account`(11) → `Warehouse`(4) → `Item Group`(4) → `UOM`(3) →
**`Workstation`(1) → `Operation`(3)** → `Item`(3) → 客商分组(6) → `Customer`/`Supplier` → `BOM`。

- **`Workstation` / `Operation` 不可省、不可后置**：`masters.bom()` 的 `operations` 三行的
  `operation` 是 Link 到 `Operation` DocType，缺它 `POST /api/resource/BOM` 回
  `417 LinkValidationError`，CLI 会按「失败即停」退非 0。
- **`Warehouse Type: Transit` 必须在 `Company` 之前**：2026-08-22 实测，缺它建公司直接
  `417 LinkValidationError: Could not find Warehouse Type: Transit`。
- **⚠️ 本仓的站点没跑过 setup wizard**（建站命令只有 `bench new-site --install-app erpnext`）。
  实测冷起后 `UOM` / `Item Group` / `Customer Group` / `Territory` / `Supplier Group` / `Fiscal Year`
  **全部 0 行**，只有 `Currency`(149) / `Country`(250) / `Domain`(2) 有行。
  上面那些 fixture 因此**由装载器自己补**，名字**照抄 ERPNext 的标准 fixture 名**，不自造。
- **建 `Company` 会让站点自己生成 82 条英文科目 + 5 个仓库 + 2 个成本中心**，
  与 `model.py` 的 11 个中文科目**零重合** —— 那 11 条必须补建，挂在站点生成的组节点下。

**幂等口径：`SiteClient.ensure_doc` 先查后建、只建不改。**
判据是**第二跑「新建 0」**，不是「没报错」（实测：第一跑 `新建 40 / 已存在 0`，
原样第二跑 `新建 0 / 已存在 40`，两次退出码均 0）。
**代价照实说**：站点上已存在但字段不对的对象**不会被纠正，也不会报错**。
取这一侧的理由是「少写」比「悄悄改写站点」安全；漏网的字段错误会由第二个 plan 的站点侧对账
表现成「站点自己算出的数对不上」，不会静默通过。**重开事件**：第二个 plan 的对账因主数据字段不符而红时，
应补一条显式的「已存在但不符即报错」，而不是悄悄改写站点。

**装载器自有的纯结构字段清单（不参与任何断言）**：

| 类别 | 值 |
|---|---|
| 公司结构 | `ABBR = "XM"` · `default_currency = "CNY"` · `country = "China"` · `create_chart_of_accounts_based_on = "Standard Template"` · `chart_of_accounts = "Standard"` |
| 科目结构 | `ACCOUNT_SHAPE`：11 组 `(root_type, account_type, parent_account)`，父节点全部是站点自己生成的组节点（`Stock Assets - XM` 等） |
| 站点生成的树根 | `All Warehouses - XM` · `Stock Assets/Expenses/Liabilities - XM` · `Accounts Payable/Receivable - XM` · `Direct Income - XM` |
| setup wizard 前置 fixture | `Warehouse Type: Transit` · `Item Group: All Item Groups` · `Customer Group: All Customer Groups` / `Commercial` · `Territory: All Territories` / `Rest Of The World` · `Supplier Group: All Supplier Groups` / `Local` |
| 工位 | `Workstation: XM 织造机台`（`hour_rate_labour` 取 `model.WORKSTATION_HOUR_RATE`；⚠️ **直接给 `hour_rate` 会被站点算掉回 0.0**，它是几个分项之和的派生量） |

**参与断言的数值一律从 `agenerp.seed` 取，装载器里不得出现第二份**：
`M.COMPANY` / `M.CUSTOMER` / `M.SUPPLIER` / `M.WH_*` / `M.ACC_*` / `M.WAREHOUSE_ACCOUNT` /
`M.WORKSTATION_HOUR_RATE` / `masters.items()` / `masters.bom()` / `names.BOM`。
**这条边界靠人读，没有机械判据**；缓解是第二个 plan 的对账会把「结构字段填错」表现成数对不上。

**命名隔离**：装载器写进站点的对象名沿用 `model.py` 已有的 `XM` 前缀常量，**不新造命名规则**。
隔离是否成立**由「装载前后各跑一次整目录 live 判定」判出来**，不靠声明：
两次均 exit 0 且逐字 `门禁 19 项：红 0，绿 19，跳过 0`。

**⚠️ 装了就留在站点上：没有代码级 teardown。**
装载器**只建不删**，`agenerp/site.py` 也**不提供**「删任意 DocType 文档」的通用方法
（那等于把业务数据交出去）。复位手段只有两条，都是**手工**的：
① `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down -v` 冷起（丢整站数据，实测 59.6 秒）；
② 事前 `docker compose exec -T backend bench --site frontend backup`，事后由**人**手工
`bench --site frontend restore <path>`（`restore` **不在** `agenerp/oob.py` 的 `ALLOWED_CALLS` 内，
放宽带外执行面是另一条已登记的人裁定题）。
**这是本节的一条真代价，不粉饰**：门禁一旦开始依赖「站点上没有种子数据」这个前提，
或人要求把种子站点做成可反复重置的 fixture，就得回来补 teardown。

**两处不粉饰的实测结果**：

- **BOM 的 `raw_material_cost = 0.0`**：BOM 默认 `rm_cost_as_per = "Valuation Rate"`，
  装完主数据时站点尚无库存故为 0。`model.INHOUSE_VALUE = 5000.0` 里
  `120 × 35 = 4200` 那一半**要等第二个 plan 装完期初库存后由站点自己算出来**。
  ⚠️ 试过 `rm_cost_as_per: "Manual"` —— ERPNext **v15.119.3 直接 500**
  （`UnboundLocalError: cannot access local variable 'rate'`，`_exc_source: erpnext`）。
  **上游缺陷，不绕它。** 工序成本那一半是对的：`400 + 240 + 160 = 800.0`，
  与 `model.OPERATION_MINUTES / 60 * WORKSTATION_HOUR_RATE` 逐字相等。
- **`model.ACC_OPERATING` 在活站点上永远命不中**：它逐字是 `生产费用（计入估值）- XM`，
  **`- XM` 前少一个空格**，而 ERPNext 的 `Account.autoname` 走 `" - ".join(...)`，
  只可能产出 `生产费用（计入估值） - XM`。装载器**报告不静默**（打印告警行并指向 bug note），
  但**不因此退非 0**（科目建成功了，这不是装载失败）。缺陷登记在
  `docs/bugs/01-acc-operating-constant-can-never-match-a-live-account-name.md`；
  **本次不修**，因为落点在 `agenerp/seed/**`，被该 plan 的 Closure Gate 挡住。

  **⚠️ 2026-08-22 就地改准（plan `2026-08-22-2325-1`）—— 上面这一条的三句话真假不同，分开读，原文一句不删：**

  1. **「`model.ACC_OPERATING` 在活站点上永远命不中」→ 现已为假。**
     该常量已改成 `生产费用（计入估值） - XM`（补上那个空格），
     站点的 `autoname` 现在派生得出它。上面那段描述的是 `2107-1` 落地时的真实状态，
     作为当时的证据保留。
  2. **「装载器报告不静默……但不因此退非 0」→ 仍然为真，不是假。**
     `LoadReport.mismatches` 及其告警行 `2026-08-22-2325-1` **一行未动**：
     名字不符照样报告、照样不退非 0。准确的说法是**机制保留，但自该 plan 起没有已知的活触发点**
     （15 个带后缀常量全部规整，由 `tests/unit/test_seed_model_constants.py` 的机械判据钉住）。
     保留理由见 §12.11。
  3. **「本次不修」→ 作为历史陈述为真，不加改准。**
     「本次」指 §12.9 自己那个 plan（`2026-08-22-2107-1`），它确实没修，理由也确实是 Closure Gate。
     **前向指引**：修它的是后继 plan `2026-08-22-2325-1`，
     同时把 `strip_abbr` 从「容忍」改成「失败即停」并补上机械判据，见 §12.11。

**本段交付的行为没有属于自己的门禁。** 站点侧那三条 **L2** 断言仍是提案文本
（`docs/backlog/gate-proposal-seed-dataset.md`，`Status: proposed`，采纳者是人）。
代偿控制沿用 §12.7 已写死的那一套：CLI 退出码 + `tests/unit` 单测 + 变异验证 + 独立关闭审计。
**验证范围 scoped**：`python3 -m agenerp.seedsite --load-masters --site frontend` **不在**
`missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到它。

### 12.10 单据装载与站点侧对账在本仓的落点（工作项 7 的 B 半第二段，2026-08-22）

plan `docs/plans/p0-foundation/2026-08-22-2107-2-seed-documents-site-computed-backlog.md`。
§12.9 把**主数据**装进了活站点；本节讲**业务单据**那一段，以及它证明了什么、没证明什么。

**它存在的理由，一句话**：在本节之前，`agenerp/seed/ledger.py` **自己构造** `Bin` /
`Stock Ledger Entry` / `GL Entry` 三类行，`checks.py` 再拿这些构造出来的行去断言 ——
**那是生成器自己跟自己对账**。本节之后，这三类行全部由**站点自己**产生。

#### 选定的单据链，以及被否掉的两条

装载顺序（依赖顺序写死在 `agenerp/seedsite.py:document_steps()`，纯函数，可被单测直接判）：

`Fiscal Year` → `Stock Entry Type` ×3 → `Price List` ×2（三个结构前置）→
`Stock Entry(Material Receipt)` 期初原料 300 Kg → `Sales Order` 1,000 米 →
`Work Order`#1（在制仓）→ `Stock Entry(Material Transfer for Manufacture)` 120 Kg →
`Stock Entry(Manufacture)` + 工序附加成本 → `Work Order`#2（外协仓）→
`Stock Entry(MTfM)` 120 Kg → `Stock Entry(Manufacture)` + 外协服务费附加成本 →
`Delivery Note` 990 米 → `Sales Invoice` → `Purchase Invoice`。

**被否掉的备选，记名不省略**：

- **收窄链**（`Stock Entry` 直接按批次价 ¥5.00 / ¥6.40 入库）—— 否决。那把 §12.1 里*产生*
  这两个费率的成本汇总整段喂给站点，站点只剩最后一次 FIFO 减法。
- **ERPNext v15 原生外协链**（`Purchase Order(is_subcontracted)` → `Subcontracting Order` →
  `Subcontracting Receipt`）—— **实测撞死，不是嫌麻烦**：建 PO 回 417
  `ValidationError: Row #1: Finished Good Item ... must be a sub-contracted item`，
  即成品 `Item` 必须带 `is_sub_contracted_item = 1`（且 `Subcontracting Order.purchase_order` 必填）。
  加这个字段要改 `--load-masters` 的载荷，而那是前一个 plan 已关闭的交付面。

#### 站点算了 §12.1 的哪几段、哪几段是喂进去的（逐字列举，不含糊）

**站点算的**（本仓载荷里一个都没送）：

1. `BOM.operating_cost = ¥800`（站点按三条工序 400 / 240 / 160 汇总 = `600 分钟 ÷ 60 × ¥80/小时`）；
2. `Manufacture` 分录里原料的实际估值 `120 Kg × 原料仓 FIFO 估值 ¥35 = ¥4,200`；
3. 自制批单位成本 `(4,200 + 800) ÷ 1,000 = ¥5.00/米`；
4. 外协批单位成本 `(4,200 + 2,200) ÷ 1,000 = ¥6.40/米`；
5. FIFO 分层与发货成本（`Delivery Note` 行回 `incoming_rate` 取**最早那一层**）；
6. `Bin` / `Stock Ledger Entry` / `GL Entry` 三类行，以及 `Work Order.required_items`。

**喂进去的**（都是 §12.1 的**输入**，不是它的结论）：`RAW_RATE` ¥35/Kg · `OPENING_RAW_QTY` 300 Kg ·
`BOM_RAW_QTY` 120 Kg · 三条工序的分钟数与 `WORKSTATION_HOUR_RATE` ¥80/小时（前一段装的主数据）·
`SUBCONTRACT_FEE` ¥2,200 · `SALES_RATE` ¥18.8/米 · 各单据的数量与日期 ·
以及**从站点读回来再送回去**的 `BOM.operating_cost`（换算方式照抄 ERPNext 自己那一行，
`bom.py:add_operations_cost` → `operating_cost_per_unit × fg_completed_qty`）。

**`INHOUSE_RATE` / `SUBCON_RATE` / `INHOUSE_VALUE` / `SUBCON_VALUE` 与
`BACKLOG_QTY` / `BACKLOG_VALUE` / `COGS_VALUE` / `GROSS_PROFIT` 八个派生量，
在 `agenerp/seedsite.py` 里零命中**（两条单测 + 关闭时的 `grep` 双判）。

**⚠️ 结论强度的两条限定，写在这里免得被引用得比实际强**：

- **外协批走的 DocType 不是 `Subcontracting Receipt`**，是 `Stock Entry(Manufacture)` +
  服务费附加成本。它复现的是 ERPNext 给外协收货算成本的**同一道公式**
  （`rm_cost_per_qty + service_cost_per_qty`），**但走的单据不同**。
  **不得据此宣称「站点验证了 ERPNext 的外协单据链」。**
- 自制批的工序成本 ¥800 是站点算的，但**它由装载器搬运了一次**（读 `BOM.operating_cost` 再送回
  `additional_costs`）。原因是 ERPNext 的 `add_operations_cost()` 只在服务端 `make_stock_entry`
  路径上跑，走 `/api/resource` 建档时不跑（实测：不送 `additional_costs` 时成品行回 `valuation_rate 4.2`，
  工序成本整段丢掉）。**搬运不等于重算**，但也不等于「站点端到端自动完成」。

#### 幂等口径

**站点不采纳显式 `name`**（实测：送 `name: "MAT-STE-9999-88888"` 建 `Stock Entry`，
站点回 `MAT-STE-2026-00009`，命名序列胜出）。冷起空站点上序列号恰好等于 `agenerp/seed/names.py`
那几个字面量，**但那是「按顺序建」的巧合，不是站点承诺**。幂等键因此用业务字段过滤：

| DocType | 幂等键 |
|---|---|
| `Fiscal Year` / `Stock Entry Type` / `Price List` | `name`（这三类站点采纳显式 `name`） |
| `Stock Entry` | `(company, purpose, posting_date)` —— 五张分录两两不同 |
| `Work Order` | `(company, production_item, wip_warehouse)` —— **两张工单只有在制仓不同** |
| `Sales Order` | `(company, customer, transaction_date)` |
| `Delivery Note` / `Sales Invoice` | `(company, customer, posting_date)` |
| `Purchase Invoice` | `(company, supplier, posting_date)` |

`find_one` **不分 `docstatus`**，因此命中一份 `docstatus 0` 的草稿时装载器**补提交**，
计入 `submitted` 而不计入 `created`。没有这一格，一次中途失败留下的草稿会让第二跑「新建 0」照样绿。

#### 干净站点循环为什么是强制前置

**站点没有单据级撤销手段**，本模块也不提供（`SiteClient` 没有 cancel/amend）。
在已装载的站点上再跑一次业务链会让 `Bin.actual_qty` 变成 2020 而不是 1010 ——
**承重判据按构造不可达**，变异验证同理不可执行。因此每一次测量与每一次变异实验都从
`docker compose down -v` 冷起开始（`down -v` → `up -d --wait --wait-timeout 300` →
`--load-masters` → `--load-documents`，实测单轮约 60 秒起栈 + 装载）。

**代价照实说**：`down -v` 丢掉整站数据。首次冷起前必须先 `bench backup`
（本次实测：`database.sql.gz` 832,967 B / `site_config_backup.json` 94 B）。
`restore` **不在** `agenerp/oob.py` 的 `ALLOWED_CALLS` 内，恢复只能由人手工做。

#### 达成率那一项：站点上算不出来

拟断言 ② 的四项里，「销售订单达成率 100%」**在当前口径下站点算不出来**。
它依赖 `Loss Review`（本仓虚构 DocType）与 `Delivery Note.xm_loss_review`（本仓虚构自定义字段），
**ERPNext v15 里两者都不存在**；站点实测算出 `Sales Order.per_delivered = 99.0`。
给站点建它们要发 DDL（造物理表），本 plan 逐字禁止，且会改变 `schema_drift` 的观测面。
处置**不是静默丢弃**：该项已移出 `--verify-site` 的结果面，并写进
`docs/backlog/gate-proposal-seed-dataset.md`，免得人采纳提案时拿到一条注定红的门禁。

#### 判据归属与验证范围

`--verify-site` 覆盖 **9 项**：结存数量 / 结存金额 / GL 借贷差额 / 负库存条目数 /
GL 收入贷方 / GL 成本借方 / 毛利 / 应收逾期 / 应付逾期。期望值**一律**从
`agenerp/seed/checks.py` 的 `EXPECTED_*` 取（`checks.py` 自述「刻意不从 `agenerp.seed.model` 取数」，
它才是判官侧那份副本），本模块里没有第二份；一条 AST 结构单测把这件事钉死。
输出**成功与失败都**打带出处的实得值与期望值 —— 只打「通过」用 `grep` 就能伪造。

**本段交付的行为没有属于自己的门禁**，与 §12.9 同一处境。代偿控制：CLI 退出码 +
`tests/unit`（**293 条** —— 2026-08-23 二次就地改准，此前写的 288 已被 plan `2026-08-23-0120-2`
新增的 5 条 overdue 诊断判据推翻；口径同样是 `python3 -m pytest tests/unit -q` 的实测通过数。
再上一次由 283 改成 288 的记述保留在下一行：此前写的 283 已被 plan `2026-08-22-2325-1`
新增的 5 条判据推翻；口径是 `python3 -m pytest tests/unit -q` 的实测通过数）+ 三条变异验证 +
`--load-documents` 幂等第二跑的新建计数 +
装载前后两次 live 整目录判定 + 独立关闭审计。
**验证范围 scoped**：`--load-documents` / `--verify-site` 都**不在**
`missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到它们。

⚠️ **一条不粉饰的时间依赖**：两张发票的 `status == "Overdue"` 是站点拿**真实时钟**跟 `due_date`
比出来的，不是拿数据集的 `as_of` 比的。种子日期固定在 2026-02/03，故恒成立 ——
但这条断言的成立条件是「今天 > `due_date`」，不是结构性成立。
**⚠️ 2026-08-23 补取证出处（句子本体未改，因为实测证实了它）**，plan `2026-08-23-0120-2` Proof A/B/C 分流 (i)：
写 `status` 的是**提交时的同步调用链**，容器内 ERPNext v15.119.3 实读 ——
`erpnext/accounts/doctype/sales_invoice/sales_invoice.py:274 validate()` → `:350 self.set_status()`
→ `:2037-2038 elif is_overdue(self, total): self.status = "Overdue"` → `:2077-2100 is_overdue()`
里逐字 `today = getdate()`（`purchase_invoice.py:258` / `:292` / `:2012-2013` 同构，`:22` 直接 import 同一个函数）。
`scheduler` 的日任务 `erpnext.controllers.accounts_controller.update_invoice_status`
（`erpnext/hooks.py:447` → `accounts_controller.py:3530-3583`）**不参与**：它的 `conditions` 逐字只更新
`status LIKE "Unpaid%" / "Partly Paid%"` 的行，且本仓站点侧 scheduler 实测为 disabled、
`tabScheduled Job Log` 0 行。⚠️ **一处比上面这句更细的实读**：两张发票都有 `payment_schedule`，
`is_overdue` 走子表分支，比的是 `payment_schedule.due_date`（实测与发票头 `due_date` 同值，结论不变）。

**⚠️ 2026-08-23 新增：诊断与承重断言的分工（plan `2026-08-23-0120-2`，D1 (d)）。**
`_overdue_checks` 那两条 `CheckResult` 的 `label` 里现在折进了一段**诊断**：按**装载器自己的幂等键**
（`{company, customer|supplier, posting_date}`，直接取 `document_steps()` 里那两步的 `key`，不复制第二份字面量）
把本仓预期的那两张发票在站点上认出来，逐条打出 `status` / `due_date` / `docstatus` / `outstanding_amount`。
**三条边界必须一起读，否则会被读成「判据加严了」**：
① **它不参与 `ok` 的计算** —— `ok` 仍只由 `_numeric_check` → `_close(total, expected)` 决定，
筛选条件逐字仍是 `status == "Overdue" and int(docstatus) == 1`，`EXPECTED_*` 一分未改；
② **它不新增结果行** —— 对账仍是 **9 项**，上面 `--verify-site` 覆盖 9 项那句与「独立约束是 8 条」那条**仍然为真**；
③ **它加严的是可诊断性，不是判据** —— 既不新增红的入口，也不新增绿的入口，只改变红的时候读得到什么。
**候选集刻意不取自站点的 `status == "Overdue"` 过滤结果**：那样站点回零张 `Overdue` 时候选集为空，
诊断会在它唯一存在理由的那个场景下空转；**也不取自 `agenerp/seed/names.py` 的单据号字面量**，
理由是 `seedsite.py` 的 `DocStep` docstring 已经写明那几个号「是『按顺序建』的巧合，不是站点承诺」。
⚠️ **诊断里那个「今天」是宿主时钟，不是站点时钟**，消息里逐字标注 `（宿主侧）`：
2026-08-23 实测 `/api/method/frappe.utils.nowdate` **HTTP 403（没 whitelist）**，
`SiteClient` 的只读面读不到站点侧的「今天」（读得到的只有 `frappe.client.get_time_zone`）。
两者若有差，表现是**诊断文字略有偏差，不是判定结果错**。

**⚠️ 三条由 2026-08-22 独立关闭审计当场指出、就地记准的限定**（不改代码，改说法）：

1. **「9 项」是打印出来的行数，不是 9 条互相独立的约束 —— 独立约束是 8 条。**
   `verify_site()` 的第 5 / 6 / 7 项分别钉 `revenue == EXPECTED_RECEIVABLE_OVERDUE`、
   `cogs == EXPECTED_COGS`、`revenue − cogs == EXPECTED_GROSS_PROFIT`，
   而 `checks.py` 里 `EXPECTED_GROSS_PROFIT = 18612 − 4950`。
   **第 7 项因此不可能在第 5、6 项都绿时单独发红。** 引用「9 项全过」时不得读成 9 条独立判据。
2. **`EXPECTED_RECEIVABLE_OVERDUE` 被复用在了它声明含义之外的一处。**
   `checks.py` 对它的声明是「应收**逾期**合计 = 990 × ¥18.8」，而 `verify_site()` 的第 5 项
   拿它当「GL 收入贷方合计」的期望值。两者此刻相等**只因为那张发票 100% 未收款**；
   一旦种子里出现部分收款，这一项会因为一个与它名字无关的原因发红。
   **它没有违反本 plan 的要求**（要求是「不得引入新的期望值字面量」，此处确实没有），
   但打给操作者的 `出处` 标注**比实际含义窄**。修法归后续 plan，此处只登记。
3. **派生量零命中的可判形式是 `M.<NAME>` / `model.<NAME>`，不是裸名。**
   裸名 `grep` 在 `agenerp/seedsite.py` 里**有命中**（`CH.EXPECTED_BACKLOG_QTY` /
   `CH.EXPECTED_BACKLOG_VALUE` / `CH.EXPECTED_GROSS_PROFIT`，全部在**对账侧**，
   那正是本模块被要求去做的事）。**装载输入侧的 `M.<NAME>` 命中数为 0**，
   由 `tests/unit/test_seedsite_documents.py::test_no_derived_quantity_is_ever_fed_to_the_site` 判。

### 12.11 带缩写后缀的常量为什么必须失败即停（2026-08-22）

plan [`2026-08-22-2325-1`](../plans/p0-foundation/2026-08-22-2325-1-acc-operating-constant-fix.md)。
§12.9 记的是「容忍 + 报告」这个代偿；本节记的是**撤掉代偿之后的口径**，以及为什么这样选。

**不变量**：`agenerp/seed/model.py` 里全部带公司缩写后缀的常量（11 个 `ACC_*` + 4 个 `WH_*`）
必须逐字满足 `constant == " - ".join([<x>_name, ABBR])`。
理由是 ERPNext v15 的 `Account.autoname` / `Warehouse.autoname` 只可能产出这个形状
（2026-08-22 用真载荷在活站点上实测），不满足的常量在站点上**永远命不中**，幂等键每次落空。
钉住它的是 `tests/unit/test_seed_model_constants.py`：**遍历模块属性**取清单（不手抄，
第 16 个常量加进来时判据自己长），**不经由 `strip_abbr` / `site_name_of` 求值**
（拿容忍它的那段代码给它开证明，判据会空转），失败信息指名常量与实际值。

**`Decision`：`strip_abbr` 收到派生不出来的串时抛异常。** 三个候选与代价：

| 候选 | 行为 | 代价 |
|---|---|---|
| (a) 维持现状 | ` - XM` 与 `- XM` 两种后缀都剥 | 下一个拼错的常量继续被**静默纠正**，缺陷不可见——而本 plan 存在的理由正是这种静默 |
| (b) 严格 `removesuffix`，不匹配原样返回 | 返回整串 | **比不修更坏**：`site_name_of` 会再拼一次后缀，在站点上**真建出** `X - XM - XM` 这种对象 |
| **(c) 不匹配即抛（选它）** | `ValueError`，站点上一个对象都不建 | 无后缀的调用方会撞上它 |

**(c) 的可行性不是印象，是枚举**：`grep -rn "strip_abbr\|site_name_of" --include='*.py'` 全仓
26 处（直接 3 + 经 `site_name_of` 间接 23），喂进去的**全部**是 `ACC_*` 或 `WH_*`
（含 `masters.warehouses()` 那一路，其 `name` 取自 `WH_*`）；
`M.COMPANY` / `TRANSIT_WAREHOUSE_TYPE` / `ROOT_WAREHOUSE` / `PARENT_*` **一条都不经过它**。

**残余风险，不粉饰**：将来若有人要拿无后缀的常量走这条路，会撞上这个异常。
**那正是希望发生的事** —— 异常信息里写清了所要求的形状 `<name> - {ABBR}` 与机械判据的位置。
爆炸半径也照实记：常量一旦拼错，`plan_steps()` 在调用点直接抛，
`test_seedsite_loader.py` 与 `test_seedsite_documents.py` 会**成片报错**，而不是只红机械判据一条。

**`LoadReport.mismatches` 保留，但此刻没有已知的活触发点。**
它是「站点回名 vs 本仓预期」的**通用**对账，不是为 `ACC_OPERATING` 一个常量造的：
站点的 `autoname` 口径若变（ERPNext 升级、公司缩写改动、DocType 换命名规则），
它是唯一会当场说话的东西，而 `strip_abbr` 的失败即停只覆盖「本仓自己拼错」这一半。
删掉它等于修好一个缺陷、丢掉一层保护。覆盖没有因此空转：
`tests/unit/test_seedsite_loader.py` 用**测试内构造的畸形 `Step`** 保住「报告」与「不空转」两半，
另有一条 `test_the_real_master_data_plan_reports_no_mismatch_at_all` 钉住「产品数据此刻确实干净」。

**本段交付的行为没有属于自己的门禁**，与 §12.9 / §12.10 同一处境。
代偿控制：`tests/unit`（**293 条**，2026-08-23 就地改准，此前写的 288 已被 plan `2026-08-23-0120-2`
新增的 5 条判据推翻）+ 一次变异验证（把 `M.WH_RAW` 改成缺空格 → 必须红且逐字点名 `WH_RAW`）
+ 冷起站点上的 `--load-masters` / `--load-documents` / `--verify-site` 实跑 + 独立关闭审计。
**验证范围限于本机，不含 CI**。
