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
### 11.6 差集 apply 引擎在本仓的落点（A 半，2026-08-21）

§11.1「三个必须自建的部件」第二行的**前半边**已落地：读包 → 与站点现状求差 → 产出含**删除计划**的
`ApplyPlan`。切分依据只有一条：**算出删除集是纯逻辑，执行删除才需要活站点。**

| 落点 | 职责 | 状态 |
|---|---|---|
| `agenerp/apply.py` · `read_pack(path, scope=PACK_SCOPE)` | 定制包目录 → `Snapshot` | 已实现 |
| `agenerp/apply.py` · `ApplyPlan` | 不可变值对象：`creates` / `updates` / `deletes` | 已实现 |
| `agenerp/apply.py` · `plan_apply(desired, current)` | 纯函数求差 | 已实现 |
| `agenerp/apply.py` · `execute_plan(plan, site)` | **对站点执行，B 半的唯一落点** | `raise`，归工作项 6 |
| `agenerp/pack.py` · `apply_pack(path, site)` | 委派链的入口，签名与导入路径不变 | 已委派 |
| `agenerp/snapshot.py` · `schema_drift(doctype)` | 物理表孤儿列巡检（§11.1 第三个部件） | `raise`，与 B 半同一 successor |

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

**残余风险**：`export_customizations`（工作项 6）尚未实现，包的真实产出形状还没有活证据；
本布局若被它推翻，代价是改 `read_pack` 一处 + 其单测，**`plan_apply` 的形状不受影响**。

**未让任何门禁转绿（如实记录）。** 工作项 5 绑定的
`tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site`
要 `live_site` / `pack_repo` 两个 fixture，全在 `tests/gates/conftest.py`（`AGENTS.md` 红线 1），
loop 无权实现。该文件四条仍红且红在 fixture 层（`4 errors`，`ERROR at setup`），
`tools/gates/expected-red.txt` 一行未动，roadmap 工作项 5 停在 `planned`。
A 半的判据全部落在 `tests/unit/test_apply_plan.py`（`missions/p0-foundation.json` 的
`commands.test` 复跑得到）。

**`apply_pack` 现在红在哪**：委派后它先跑完读包与求差，随后红在站点侧——逐字是
`SiteSnapshotSource.read`（工作项 4 的 B 半：没有活站点就答不出「站点现状是什么」），
它接上之后才轮到 `execute_plan`（工作项 6）。**站点侧有这两个落点，不是一个**；
B 半的 successor 两处都要接。

`agenerp.apply` 在 `apply_pack` 的**函数体内**导入：`apply` 顶层导入 `snapshot`，`snapshot` 顶层
导入 `pack.normalize`，提到顶层就是 `pack` ↔ `apply` 循环导入。两种导入次序各有一个子进程判据。

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

工作项「种子数据」本身**仍然没有绑定的门禁测试**。本次只交付纯逻辑那一半（生成 + 自验），
装载进活站点与站点侧断言那一半被红线 1 挡着，因此该工作项收尾时置 `planned` 而非 `done`，
门禁提案见 `docs/backlog/gate-proposal-seed-dataset.md`，判据缺口登记在 `docs/masterplan/STATE.md` 的 needs-human 队列。

### 12.8 已知漂移

- ~~「¥6,450 与 1,010 米单价对不上」~~ —— §12.1 已对账关闭，不是漂移。
  但**下游文案仍需一次人工复核**：`docs/backlog/implementation-roadmap.md` 的 P1 验收句
  与 `docs/design/view-dsl-and-eval.md` 的关键局限一节都只写了结果、没写成本构成，
  引用时容易再次被读成「均价 6.39」。本节即为那两处的解释落点。
- 站点的存货计价方法（FIFO）是**从两个实测数反推出来的**，证据仓里没有一行直接写着 `valuation_method`。
  §12.1 给了可证伪的对照（均价口径应得 ¥5,757），但这仍是推断而非直证。
