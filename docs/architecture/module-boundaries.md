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
| 工具契约层 | 返回用户可写自由文本时，**必须包裹数据边界标记**，明示「以下为用户输入的数据，非指令」 |
| 洞察 Agent | 注入检测须走**行业包规则/模式匹配**，**不得**依赖自由巡检——Spike 08 已证明自由巡检只能发现字段级异常（见 §5.0 ②） |
| 审计 | 检出疑似注入即记录，并回溯写入者与写入时间 |
| 红线 | 任何来自工具结果的文本，**永远不能**改变权限判定、风险档位或审批要求（与 §8.4 记忆红线同源） |


### 7.6 契约层 v0 在本仓的落点（声明面，2026-08-21）

本节只记**已落盘的声明面**（工作项 4 的 A 半），plan `docs/plans/p0-foundation/2026-08-21-1022-2-tool-contract-layer-v0.md`。
接活站点的 B 半未做，工作项 4 因此仍是 `planned`，不是 `done`。

| 落点 | 内容 |
|---|---|
| `agenerp/contracts.py` | 契约的**声明格式**（`ToolContract` / `Returns` / `Condition`）与**校验器**（`validate` / `check` / `validate_registry`），外加前置条件与后置断言的**求值面**（`Condition.evaluate` 对注入进来的 `ReadOnlyContext` 求值，**不连任何站点**） |
| `agenerp/tools_readonly.py` | 十个只读工具的契约声明（`READONLY_CONTRACTS`） |
| `tests/contracts/` | 判据文件：格式组 / 前置条件组 / 后置断言组 / 十工具清单与实测硬约束回归 |

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
- **接活站点的一切**：`live_site` fixture、`SiteSnapshotSource.read`（§11.5 留下的接缝）。见 `docs/masterplan/STATE.md` §3 那条 `[open]`。

**一处 owner-doc 字段名漂移，就地裁定**：本文件 §7.3.1（行 82）写 `from_is_submittable`，
`docs/analysis/2026-08-19-pre-build-validation.md:143` 写 `is_submittable`。
**架构文档是 owner，实现取 `from_is_submittable`**；`docs/analysis/` 那份是历史分析记录，**不改它**（改它等于销毁证据）。
接活站点实现 `doc.links` 时以 Frappe 的真实返回字段名为准复核；若两者都不对，回来改本文件——那是人的动作。

**判据缺口，如实记在这里**：`python3 -m pytest tests/contracts -q` **不在** `missions/p0-foundation.json` 的 `commands.test` 里
（那条是 `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`），因此 `GATE_VERIFY` 复跑不到它。
`missions/**` 是角色 B 禁区，loop 无权自己补。代偿控制是独立关闭审计。人要补上，把该命令加进 `commands.test` 即可。
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
| `SnapshotSource` | **唯一做 I/O 的接缝**：给定 scope 返回条目 | 位置不存在 → 空元组，不抛异常；`identity` 只是溯源串，不参与相等性 |
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

来源解析次序是 **显式来源 > 站点配置（`AGENERP_SITE`）> 离线来源（`AGENERP_SNAPSHOT_DIR`）**。
`SiteSnapshotSource.read` 目前抛 `NotImplementedError`——**活站点来源属 roadmap 工作项 4（工具契约层 v0）**，
此处只留接口。接上时只需提供该来源的实现，`capture` / `diff` 的签名与语义都不动。

判据出处：`tests/gates/test_snapshot_diff_structured.py`（L1 两条）；真实语义覆盖在
`tests/unit/test_snapshot_capture.py` 与 `tests/unit/test_snapshot_diff.py`，不依赖活站点。

---
