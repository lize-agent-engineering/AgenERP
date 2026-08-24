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
sha `5a712a7`）：十条契约各有执行体，且**只有一个执行入口**。
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
  §7.4 的**权限拒绝熔断**（N=5）仍未做——它是**控制循环**的行为，不是工具的，归 P1.0 的控制循环。

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
人已于 2026-08-21T14:21Z（`3fed439`）把 §3 的 `[open]` 全部关闭；口径以 §2
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
| `agenerp/site.py` · 写 / 删方法 | 归工作项 5 的删除段（plan [`2026-08-21-1922-3`](../plans/p0-foundation/2026-08-21-1922-3-execute-plan-site-delete.md)）。**白名单有且只有一条** `SiteClient.delete_custom_field`（模块头第 4 条，`agenerp/site.py:16-17`）；不提供「删任意 DocType 文档」的通用方法 | 已实现（判据 `tests/unit/test_site_client.py` 的 `WRITE_METHOD_ALLOWLIST`）。**⚠️ 2026-08-22 就地改准（确认的 owner-doc 漂移，Minimum Rule 14 不降级）**：本格此前是一句**否定态的状态词**（原文逐字取法：`git show 4ac3517:docs/architecture/module-boundaries.md | sed -n '581p'`；此处不复述那个词，因为本 plan 的机判判据要求本表行范围内不再出现它）。**那句话从 2026-08-21 起就是假的**——`1922-3` 已于 **2026-08-21 关闭**，方法已落地并在活站点上实测删过字段，本次是**改准一句假陈述，不是「新增一项」**，它整整假了一天。同一份文档的 §11.6 落点表（`:338` 一带）当时就写着「已实现（B 半）」，两张表在同一个文件里互相矛盾了同样长的时间。改准由 plan [`2026-08-22-1041-1`](../plans/p0-foundation/2026-08-22-1041-1-destructive-write-owner-doc-alignment.md) 做 |

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
