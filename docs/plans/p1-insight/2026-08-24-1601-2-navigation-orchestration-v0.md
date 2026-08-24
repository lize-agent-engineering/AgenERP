# P1.3 导航的编排行为：`permission.scope` 开场自动注入 + 导航质量判据

> Plan Status: active
> Mission: p1-insight
> Work Item: 5. 导航的编排行为：permission.scope 开场自动注入（P1.3）
> Execution Order: 2 / 2（本批第二个；前置是同批第一个 `docs/plans/p1-insight/2026-08-24-1457-2-context-layer-v0.md`）
> Last Reviewed: 2026-08-24（基线 sha `b3b2f1f`；**独立草案评审三轮至共识**，见 §11）
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 5 · `docs/masterplan/02-WBS.md` §4 **第 82 行**（P1.3）
> Related: 前置 P1.2（同批第一个）· 继承 P1.0a 的执行入口 `agenerp/tools/runtime.py:316`
> Audit: required

## 1. Current Baseline

**开工基线 sha `b3b2f1f`**（`git log -1`；其上一条是 `432efd6`）。
`b3b2f1f` 是**人**裁定「`qwen3.6-plus` 在本项目两跳题上是 1/6 不是 2/6」的那次改文档，
**与本 plan 无交集**——本 plan 不引用任何模型正确率数字。

工作树非 clean，且**正在被别人改动**：`docs/evidence/p1-entry-gate-round2/` 下不断增加
`r2-*.json`（P1.0 第二轮重测**正在进行中**），`docs/masterplan/DECISIONS.md` 与
`docs/backlog/p1-insight-roadmap.md` 也有未提交改动（**人**的动作）。
**这些本 plan 一个字不动**（红线 3/5）。开工时工作树的具体内容会与此处不同，
**以 `git status` 实测为准**；关键是 HEAD 仍为 `b3b2f1f`。

以下每条都是本轮实读，不是回忆。

### 1.1 「开场自动注入」这件事，今天在本仓**只有声明，没有执行者**

- 契约声明位在 `agenerp/tools_readonly.py:296`：`PERMISSION_SCOPE` 的第二条后置断言
  `fact="injected_at_session_start"`，**没有写 `operator`**，因此按 `agenerp/contracts.py:95`
  的默认取 `is_true` —— 它求的是**调用方交进来的那个布尔值的真假**。
- `agenerp/tools/runtime.py:316` 的 `execute(...)` docstring 逐字：
  「`context` 是**调用方**（控制循环）持有的事实：……`permission.scope` 的开场注入标记……
  工具自己推不出这些——它们是编排面的事实，**让工具自报等于让被考的人填成绩单**」。
- `grep -rn injected_at_session_start . --exclude-dir=.git`（不计本 plan 自身）共 **10 处**，
  逐类点清：**产品侧 1**（上面那条声明）· **测试夹具里写死的字面量 `True` 3**
  （`tests/contracts/test_postconditions.py:31` · `tests/tools/test_executors.py:27` ·
  `tests/tools/test_live_conformance.py:64`）· **契约清单断言 2**
  （`tests/contracts/test_readonly_registry.py:117` 与 `:120`）· **实验设施注释 1**
  （`loop.py:17`）· **文档 3**（`module-boundaries.md:165` ·
  `docs/logs/2026/08-24.md:230` · `docs/plans/p1-insight/2026-08-24-P1.0-entry-gate-experiment.md:323`）。
- `tools/experiments/p1_entry_gate/loop.py:17` 的模块头逐字写着它**故意不提供** `permission.scope`：
  「它的后置断言 `injected_at_session_start` 断的是**编排面**的事实（开场自动注入，属 P1.3），
  本设施没有实现那件事。把它当 `True` 递进去就是**断言一件不成立的事**」。

→ **今天全仓没有任何一行代码真的做过这件事。** 本 plan 的第一个交付面就是把这个事实变成真的，
且**让它不能靠写死 `True` 蒙混**。

### 1.1a **契约在机制上强制这条事实由调用方交进来** —— 起草期实读发现，决定 Phase 1 的形状

把 §1.1 的三条摆在一起看，会得到一个首稿没写、但决定成败的结论：

- `permission_scope` 执行体推出的事实**只有** `permission_probe_method`（`site_scope.py:162-168`）；
- `execute` 的事实合并是 `facts = {**caller_facts, **dict(outcome.facts)}`（`runtime.py:359`）；
- `Condition.evaluate` 在事实缺席时直接判否：`contracts.py:102-103` 逐字
  `f"上下文缺少事实 {self.fact!r}"`，随后 `execute` 在 `STAGE_POSTCONDITIONS` `_abort`。

→ **因此 `execute("permission.scope", ...)` 只要调用方没把 `injected_at_session_start` 交进来，
就必然 `ok=False`。** 这不是缺陷，是这条事实的本性：**工具推不出编排面的事，只有编排面知道。**

**这条限制会打死一个天真的写法**：「装配器不传这条事实，只从返回的 `ToolResult` 推」——
那样 `ToolResult.ok` 永远是 `False`，推导判据里的 `ok is True` 永远不成立，
整个 Phase 1 会红在自己的设计上。**先写清楚，比执行时撞上再改设计好。**

**因此 Phase 1 的机制被拆成两段，二者语义不同、不许混为一谈**：

| | 事实的含义 | 谁给 | 可验性 |
|---|---|---|---|
| **契约面**（`tools_readonly.py:296` 那条后置断言） | 「**本次调用是编排面在会话开场发起的**」 | 调用方自证（本性如此，工具推不出） | 弱：调用方说了算 |
| **开场包面**（本 plan 的交付） | 「**注入这件事真的发生过**」 | 从注入记录**推导** | 强：可从 `FakeSite.requests` 核出，且写死标志会被反测打红 |

**D4 · 要不要顺手改强契约面那条后置断言？** **裁定：不改。** 备选与否决理由：
(A) 把 `injected_at_session_start` 改成由执行体推 —— **否决**：执行体没有「会话」这个概念，
让它推等于让它猜，且要改 P1.0a 已收口的执行体（§3 Non-Goals 3）；
(B) 给契约加一条 `operator` 更强的断言 —— **否决**：契约层的求值面只看事实字典，
再强的算子也还是求调用方交进来的那个值，**强不了**，只会制造「已加固」的错觉；
(C) **不改，把强度放在编排面**（选定）：契约面维持调用方自证，
强判据由本 plan 的开场包面与反测承担。
**残余风险**：`tools_readonly.py:296` 那条后置断言**在本 plan 之后仍然是一个调用方自证的软断言**，
任何绕过 `agenerp/orchestration/` 直接调 `execute` 的人都能把它填成 `True`。
**收口时逐字写明这一点，不得说成「注入已被契约保证」。**

### 1.2 `permission.scope` 执行体已经就绪，且它的三条实测限制会直接决定编排面的形状

实读 `agenerp/tools/site_scope.py:121-160`：

| 事实 | 出处（实读） | 对编排面的约束 |
|---|---|---|
| 候选集**可以由调用方给**（`params["doctypes"]`），不给才走发现式默认路径 | `site_scope.py:129`（docstring）+ `:144`（代码 `given = params.get("doctypes")`）+ `module-boundaries.md` §7.6 限制 1 | **受限身份枚举不出 DocType 清单**（stock Frappe 只把 `DocType` 读权限给 System Manager / Administrator，且建 `Custom DocPerm` 不生效）→ 编排面**必须能带着候选集去注入**，不能只会走发现式 |
| `can_read = False` 的行**照样返回** | `site_scope.py:138`（docstring）+ `:156`（代码 `rows.append`） | 注入产物里**必然含 `can_read: False` 的行**，「全是 True」是假实现的形状 |
| `permission_probe_method` 由**本次实际调过的方法名**推出来 | `site_scope.py:141`（docstring）+ `:162`（代码 `probed = sorted(...session.methods())`） | 注入产物携带的事实是**执行体推的**，编排面不得覆盖它（`runtime.py:359` 的合并方向 `{**caller_facts, **outcome.facts}`：执行体的事实覆盖调用方的，方向不可反） |
| 发现式路径的**候选规模**是全部业务 DocType（本站点 239 个），逐个调一次 `has_permission` | `site_scope.py:151-156` 的循环（**结构事实**）。⚠️ **239 这个数**出自 `module-boundaries.md` §7.6 限制 2，而那条量的是 **`frappe.client.get_count`** 的次数，**不是 `has_permission` 的次数**——本仓从未量过后者 | 开场注入的**代价必须被记下来并可断言**，否则「开场自动注入」会变成一个每次会话烧几百次请求的隐性成本。⚠️ 收口时**不得**把 239 写成「注入的实测代价」（硬约束 ④） |

### 1.3 `tests/tools/test_navigation.py` **不存在**

`ls tests/tools` → `conftest.py` · `test_executors.py` · `test_live_conformance.py` ·
`test_registry_pairing.py` · `test_runtime.py`。WBS §4 第 82 行的验收原文点名的就是
`pytest tests/tools/test_navigation.py -q`，**该文件是本 plan 的交付物之一**。
它**不在** `tests/gates/**`（红线 1）里，本 plan 可以创建。

`tests/tools/conftest.py` 已有一个**行为与 Frappe REST 面同形的假站点** `FakeSite`
（支持 `has_permission` / `get_count` / 资源列表 / 单文档 / 建档，逐条留痕 `requests`），
**权限答案由夹具直接给定**。本 plan 的全部判据在它上面跑，零网络、零凭据、零 docker。

### 1.4 §7.4 权限拒绝熔断：一条**悬空**的 owner-doc 条目，本 plan 就地裁定

`docs/architecture/module-boundaries.md` §7.4 逐字要求：单次会话内连续 N 次权限拒绝
（建议 N=5）→ 立即终止工具调用循环 → 明确返回「你的权限不足以回答这个问题」+ 所需权限清单 → 写审计。
同文件 §7.6 末尾逐字写着它「**仍未做**——它是**控制循环**的行为，不是工具的，**归 P1.0 的控制循环**」。

**但 P1.0 已经 `done`，且它交付的是实验设施**（`tools/experiments/`，模块头逐字「不进 `agenerp/`」），
**熔断没有被做，责任人那一栏因此是空的**。这是一条悬空条目，不是别人的欠账。
处置见 §5.2 的 `Decision` D2。

### 1.5 已经就绪、本 plan 直接消费的东西

| 可用 | 出处（实读） |
|---|---|
| 十个只读工具的**唯一执行入口** `execute(tool, params, *, client, context, executors)` | `agenerp/tools/runtime.py:316` |
| 调用方事实的载体 `ReadOnlyContext` | `agenerp/contracts.py`（`execute` 用它求前置/后置） |
| `ToolResult`（含 `ok` / `facts` / `stage` / `reasons` / `request_count`） | `agenerp/tools/runtime.py` |
| 假站点 `FakeSite` | `tests/tools/conftest.py` |
| 受限身份「车间工人」（只读 `Work Order` / `Stock Entry` / `Item` 三个） | `agenerp/seedusers.py:39` `READABLE_DOCTYPES` |
| ① 即时上下文装配面 + ② 对话会话记录 | `agenerp/context/`（**P1.2 交付，尚不存在**，见 §5.1 Prereqs） |

### 1.6 判定面缺口（与 `tests/routing` / `tests/tools` 同形态，照实说）

`tests/tools` **不在** `missions/p1-insight.json` 的 `commands.test`
（实读：`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`），
也**不在** CI 的 `unit-and-contracts` / `lint` 任何一个 job 的作用域里
（实读 `.github/workflows/gates.yml`：两个 job 的作用域逐字是 `tests/unit` `tests/contracts`，
`lint` 那行是 `ruff check agenerp tests/unit tests/contracts`）。
`.github/workflows/**` 在红线 2 内。`missions/**` **不在 AGENTS.md 红线表 1–7 里**
（照实说，不夸大）——它是 `docs/context/ai-autonomy-policy.md` Protected Areas 里标 `blocked` 的项，
本 plan 按同样保守的方式处理：**不动它**。两者都不由 loop 自己补。
STATE §3 已有一条 `[open]`（2026-08-24T07:50Z）记着这件事。
处置：三条代偿控制（§5.3）+ 收口时**在 STATE §3 追加**，**不得声称 CI 已覆盖**。

### 1.7 还缺什么

缺**编排面本身**：一个「会话开场把什么摆到模型面前」的确定性装配器，
以及「导航好不好用」的**可断言口径**。今天前者不存在，后者在本仓从未被量过——
owner doc 里那句「工具调用从 35 次降到 1 次」是 **Spike 02 在别的站点上的实测**，
按硬约束 ④ 它只能当**假设的来源**，不能当本 plan 的结论或目标值（§6 Phase 2 逐字处理）。

## 2. Goals

1. `agenerp/orchestration/` 落地**会话开场装配器**：在模型看到第一条消息之前，
   自动执行 `permission.scope` 并把结果摆进开场包，**不依赖模型想起来调用**。
2. `injected_at_session_start` 这条事实**由真实发生过的注入事件推出来**，
   不是调用方写死的 `True` —— 并有反测保证「只写标志不真注入」必然红。
3. 给导航工具补**质量判据**：在假站点上以**确定性导航策略**（零模型）量出
   「开场注入 on / off 两种配置下，同一组导航任务各需多少次工具调用」，
   数字**在本仓自己的夹具上跑出来**并落进 owner doc（硬约束 ④）。
4. §7.4 的**权限拒绝熔断**（连续 N 次权限拒绝即终止）落地为编排面的确定性规则（见 §5.2 D2）。
5. `python3 -m pytest tests/tools/test_navigation.py -q` 退 0，**且其中有一条断言开场注入真的发生**
   （WBS §4 第 82 行的验收原文）。

**一个结果面**（指南第 4 条）：上面五条不是五个关闭判据，而是**同一个结果面**
——「`agenerp/orchestration/` 这一层编排行为」——的五个侧面，
全部收敛在 WBS 点名的那一条命令 `pytest tests/tools/test_navigation.py -q` 上。
开场注入、导航质量、熔断三者共用同一个模块树、同一份判据文件、同一条验收命令；
拆成三个 plan 会让「注入失效时兜底在哪」没有归属（§5.2 D2 的理由）。

## 3. Non-Goals

1. **不做控制循环本身**（模型选工具 → 回注 → 作答 → 门禁 → 强制续跑）。本 plan 交付
   「循环开场要做的事」与「循环出事时要刹的车」，**循环本体归 P1.4**。
   熔断在本 plan 里是一个**被调用方驱动的计数器 + 策略对象**，
   把它接到真实循环上是 P1.4 的接线动作，本 plan 不代做、不代称已做。
2. **不做证据充分性门禁 L1/L2/L3 的运行时**（P1.4，WBS §4 第 83 行）。
3. **不改 `permission.scope` 执行体的任何行为**。它已由 P1.0a 收口并在活站点跑过；
   本 plan 只**调用**它。若发现它的缺陷，登记进 STATE §3，不就地改。
4. **不引入任何 LLM 调用**。本 plan 全部判据零网络、零凭据、零 docker。
   质量判据用**确定性导航策略**度量，不是拿模型跑几次看结果（硬约束 ③ + P1.0 的教训：
   每格 3 次只够看方向，不够算比率）。
5. **不改 `tools/experiments/**`**（P1.0 已收口，轨迹是判定证据）。
6. **不碰 `tests/gates/**`、`.github/workflows/**`、`missions/*.json`、`docs/masterplan/` 除
   `STATE.md` 追加以外的任何文件**（红线 1/2/3/5）。
7. **不在活站点上跑任何东西作为关闭证据**。活站点冒烟若做，只作补充事实，
   `tests/tools/test_live_conformance.py` 的既有形态（无凭据时 skip 并打印理由）不被本 plan 改变。

## 4. Task Route

- Type: `app-layer design change`（新增一层编排能力；不改契约声明、不改执行体、不碰站点写面）
- Owner Docs:
  - `docs/architecture/module-boundaries.md` §7.4（**本 plan 的 owner**，熔断）与 §7.6（落点表，本 plan 追加一节）
  - `docs/design/agents-and-roles.md` §5.1（**只读**，「由控制循环在会话开场自动注入」的出处）
  - `docs/design/context-and-memory.md` §8.1（**只读**，「结构化导航优先」的出处）
- Skill Selection Basis:
  Registry 无实现类 skill 匹配「新增一层编排能力」→ 实现记 `Skill: none`；
  Phase 3 涉及 owner doc 与红线，收尾用 `development-wisdom-gate-prompt.md` 自查；
  草案评审 `plan-audit-prompt.md`，关闭审计 `closure-audit-prompt.md`。

## 5. Infrastructure And Config Prereqs

### 5.1 前置

- **同批第一个 plan（P1.2 上下文层 v0）必须先 `completed`。** 理由：开场包 = ① 即时上下文
  ＋ 注入产物，前者的结构由 P1.2 的 `agenerp/context/immediate.py` 定义；
  且注入产物要记进 ② 对话会话（P1.2 的 `ConversationSession`）。先写编排再改结构等于返工。
  ⚠️ **若本 plan 被先派发**（STATE §3 2026-08-24T04:10Z 那条 `[open]` 记着 driver 的派发顺序
  与 roadmap 相反）：**执行者停在这里，往 STATE §3 追加一行**，不要把 P1.2 的上下文层顺手写进来。
- 不需要活站点、不需要 docker、不需要 LLM 凭据。**本 plan 全部判据零网络。**

### 5.2 三个 `Decision` 前置

**D1 — 编排面落在哪个包，判据文件放哪。**

| 方案 | 否决/选定理由 |
|---|---|
| (A) 并进 `agenerp/context/` | **否决**。P1.2 的 Non-Goals 3 逐字把「控制循环」排除在上下文层之外；把循环开场行为塞进上下文层会让 P1.2 的结果面在收口后被悄悄扩写 |
| **(B) 新包 `agenerp/orchestration/`；判据全部落在既有的 `tests/tools/`** | **选定**。编排是独立一层（`agents-and-roles.md` §5.1 的「编排 Agent」已有这个名字）；判据落 `tests/tools/` 有两个硬理由：① WBS 的验收原文点名 `tests/tools/test_navigation.py`；② 不新增第三个「不在任何判定面上」的测试目录（§1.6），残余风险集中在一处更便于人一次性接进 CI |
| (C) 塞进 `agenerp/tools/runtime.py` | **否决**。`runtime.py` 是**工具执行入口**这一个咽喉，把「会话开场做什么」塞进去等于让工具层知道循环的事，方向反了 |

**残余风险**：`agenerp/orchestration/` 与 P1.4 的循环本体之间的接缝在本 plan 里只有单侧
（本 plan 提供，P1.4 消费）。**本 plan 不宣称这个接缝已被真实循环验证过**，收口时逐字写明。

**D2 — §7.4 权限拒绝熔断进不进本 plan。**

**选定：进。** 三条理由：
① §1.4 已查明它是**悬空条目**——owner doc 把它记在「P1.0 的控制循环」名下，而 P1.0 交付的是
实验设施且已 `done`，**没有人在做它**；
② 它是**确定性规则**（连续计数 + 阈值 + 固定文案），D-15 逐字「规则能覆盖的流程不 Agent 化」，
放进模型侧就是错的；
③ 它与本 plan 的第一个交付面**同源**：§7.4 结尾逐字「配合 `permission.scope`，理想路径是 Agent 在
**第一次查询之前**就判定『此问题超出我的可见范围』，而不是撞 35 次墙」——注入是主路径，熔断是兜底，
分在两个 plan 里会让「主路径失效时会怎样」没有归属。

**备选与否决理由**：留给 P1.4 —— 否决，因为 P1.4 的结果面是「解释 Agent + 证据充分性门禁」，
再挂一个来源不同的红线规则会让那个 plan 的关闭判据说不清。

**残余风险**：本 plan 交付计数器与策略，**接到真实循环上是 P1.4 的动作**。
因此本 plan 能证明的是「给它喂 N 次权限拒绝，它会刹车、会给出所需权限清单」，
**不能**证明「真实会话里它一定被调用到」。这条逐字写进 §8 与收口叙述。

**D3 — 「导航质量」在本仓用什么口径量。**

**选定：确定性导航策略在假站点上的工具调用次数，on / off 两组对照。**

- 「少走弯路」= **同一组导航任务下，达到「可以开始作答 / 可以明确拒答」所需的 `execute()` 调用次数**。
- 两组**共用同一份导航策略代码**，唯一差异是开场包里有没有注入产物。
  这是本口径能立住的关键：两组若各写一份策略，测到的是两份代码的差异，不是注入的差异
  （**这条与 P1.0 实验的「提示词单一来源」同形**，`loop.py` 模块头设计约束 1）。
- **零模型参与**：策略是「按开场包里已知的事实决定下一步取什么」，路径可预先枚举 → D-15 归规则。
- **否决 (A) 拿真模型跑几次比次数**：P1.0 已实测每格 3 次只够看方向不够算比率，
  且会把「质量判据」变成一个每次跑都要烧 token、结论还不稳的东西。
- **否决 (B) 直接把 owner doc 的「35 → 1」写成断言目标值**：硬约束 ④——那是 Spike 02 在**别的
  站点**上的数字，不是本项目本夹具上的实测。它只能作**假设的来源**。

### 5.3 判定面缺口（同 §1.6）的三条代偿控制

① Phase 3 的假实现变异自查；② 独立关闭审计；
③ 收口时**在 STATE §3 追加**一条 needs-human（把 `tests/tools` / `tests/routing` / `tests/context`
一并接进 `unit-and-contracts` / `lint`，并点名新文件 `tests/tools/test_navigation.py`）。
**收口时不得声称 CI 已覆盖 `tests/tools`。**

## 6. 开工前写死的假设（硬约束 ②，跑之前逐字写死）

Phase 2 的质量度量会产出本仓此前没有过的数字。**以下的计数口径与四条假设在跑之前写死，
事后逐条对照，不许改写。**

**计数口径（先定死，否则 H1/H3 的真假可以由执行者事后选）**：

- 「调用次数」= **一次会话内 `execute()` 被调用的总次数，含开场注入那一次**。
- 「站点请求次数」= `ToolResult.request_count` 之和，**另计一栏**，不与上一项混。
- 计数的终点是「策略判定**可以开始作答** 或 **可以明确拒答**」的那一刻，两者都算终点。

- **H1**：受限身份（只读 3 个 DocType）问一个需要读**不可见 DocType** 的问题时，
  **注入 on 组的 `execute()` 调用次数 严格小于 off 组**。
- **H2**：注入 on 组在该题上的调用次数 **≤ 2**（1 次注入 + 至多 1 次确认）。
- **H3**（**成本记账，不是判别性假设**——按上面的计数口径它接近恒真，保留它是为了
  让「注入不是免费的」这件事有一个被写下来的位置）：对一个**完全在可见范围内**的导航任务，
  on 组的调用次数 **不小于** off 组。**本 plan 不假装注入没有代价。**
- **H4**：把 on 组的开场包换成**空包**，但**人工把 `opening_injection_verified` 置真**
  （不经装配器推导），**H1 不再成立**——这是「口径本身有没有牙齿」的反测。
  ⚠️ 判据取「on 组**不小于** off 组」，**不取「两者相等」**：空包变体里注入那一次调用
  算不算、怎么算，会让计数差 1，钉死等号是给自己挖坑。
  ⚠️ **置真的是开场包面那条 `opening_injection_verified`，不是契约面那条
  `injected_at_session_start`**（§1.1a 的两段机制不许混）：后者从不进开场包，
  策略读不到它，拿它做 H4 等于什么都没换。
  空包变体**仍带这条为真的标志**，以确保策略不是靠「包是不是空的」这个旁路分叉——
  若策略实际上在读包的空满而不是读事实，H4 就测不到该测的东西。

事后对照表落在 Phase 2 的执行记录里，**四条逐条写「吻合 / 不吻合」，不吻合的照实写，不改假设**。

## 7. Execution Plan

### Phase 1 — 会话开场装配器：真的注入，且骗不过去

Status: completed
Targets: `agenerp/orchestration/__init__.py` · `agenerp/orchestration/opening.py` · `tests/tools/test_navigation.py`
Skill: `none`

- Item Types: `Add | Proof`
- Prereqs: §5.1（P1.2 完成）

- [x] `Add` — `open_session(...)`：在**任何模型消息之前**调用一次
      `execute("permission.scope", ..., client=..., context=...)`，把 `ToolResult` 收进开场包。
      **候选集允许由调用方给**（§1.2 限制 1）：受限身份枚举不出 DocType 清单，
      装配器必须支持带候选集注入，**不得**为了走发现式路径而给身份提权。
      - Skill: `none`
- [x] `Add` — **两段机制照 §1.1a 落地，不混为一谈**：
      ① **契约面**——装配器调 `execute` 时**必须**把 `injected_at_session_start=True` 交进
      `ReadOnlyContext`，否则契约必然在 `STAGE_POSTCONDITIONS` 上 `_abort`（`runtime.py:359`
      + `contracts.py:102`）。这一段是**调用方自证**，本 plan 不宣称它被加强。
      ② **开场包面**——装配器**在拿到 `ToolResult` 之后重新推导**一条**独立命名**的事实
      （`opening_injection_verified`，与契约那条**不同名**，防止两者被读成同一件事），
      推导判据写死在代码里：注入产物存在 · `tool == "permission.scope"` · `ok is True` ·
      `request_count > 0` · 产物里含 `can_read` 行。
      **开场包里对外暴露的是 ② 那条**；调用方传进来的任何同名值一律不进开场包。
      - Skill: `none`
- [x] `Add` — 开场包记**注入代价**：`request_count` 与候选集大小随产物一并落进开场包，
      使「开场注入烧了多少次站点请求」可被断言（§1.2 限制 4）。
      - Skill: `none`
- [x] `Proof` — `tests/tools/test_navigation.py`（unit，`FakeSite`，零网络）：
      ① **WBS 验收原文那一条**：断言开场注入**真的发生**——从 `FakeSite.requests` 里
      核出那次 `POST /api/method/frappe.client.has_permission`，而不是只看标志位；
      ② 注入产物里**含 `can_read: False` 的行**（全是 `True` 是假实现的形状，§1.2）。
      ⚠️ 用**现成的** `fake_site` 夹具做不到这一条：它的 `permissions` / `forbidden` 都是空的，
      `has_permission` 对一切回 `True`。测试**必须自己把 `permissions` 里某几个置 `False`**；
      ③ `permission_probe_method` 来自执行体、未被装配器覆盖；
      ④ **反测 A**：装配器跳过 `execute`、直接把 `opening_injection_verified` 写成 `True`
      → 必须红（判据落在 `FakeSite.requests` 上，不落在标志位上）；
      ⑤ **反测 B（改写版）**：**带候选集注入时，装配器不得走发现式发现路径**——
      断言 `FakeSite.requests` 里**不出现任何** `GET /api/resource/DocType`
      的元数据枚举请求，且 `has_permission` 的调用次数**恰等于**候选集大小。
      ⚠️ 首稿那条「装配器给身份提权 → 必须红」**已删除**：`FakeSite` 根本没有身份概念
      （`conftest.py` 的 `client_for` 把 `api_key` 写死成 `"k"`，权限答案是夹具给的 dict），
      提权面在 `agenerp/seedusers.py` 这条写路径上，而本阶段②端只读根本不碰它——
      **那条反测对任何实现都恒绿，是一句听着安全的空话**，留着比删掉更危险；
      ⑥ **注入代价的断言**（M7 的靶子）：开场包里记的 `request_count` 与候选集大小，
      必须**与实际发生的请求对得上**——断言它等于 `len(FakeSite.requests)` 中
      `has_permission` 那部分的条数、且等于候选集大小。
      ⚠️ 只断言 `request_count > 0` **不够**：一个把代价写成常量的实现照样绿。
      - Skill: `none`

Exit Criteria:

- [x] 开场注入真实发生；**开场包暴露的 `opening_injection_verified` 由记录推导**，
      与契约面那条调用方自证的 `injected_at_session_start` **分名分述**；反测 A / B 各有一条红
- [x] 注入代价（`request_count` + 候选集大小）可断言
- [x] owner doc：**本 Phase 无 owner-doc 更新**（落点节集中在 Phase 3 一次写完，不分两次改同一节）
- [x] `python3 -m pytest tests/tools/test_navigation.py -q` 退 0（命令原文 + 退出码 + sha 同条写出）
- [x] `docs/logs/2026/08-24.md` 更新

### Phase 2 — 导航质量判据：在本仓自己的夹具上量，不搬外部数字

Status: planned
Targets: `agenerp/orchestration/navigation.py` · `tests/tools/test_navigation.py`
Skill: `none`

- Item Types: `Add | Proof | Decision`
- Prereqs: Phase 1

- [ ] `Add` — 确定性导航策略 `plan_next_step(...)`（零模型，路径可预先枚举 → D-15 归规则）：
      按开场包里**已知的事实**决定下一步取什么；已知「目标 DocType 不可读」时**立即停止并拒答**。
      - Skill: `none`
- [ ] `Add` — 度量骨架：**策略以单个可调用对象的形式注入骨架**（`run_metric(strategy, opening_pack, tasks)`），
      同一个 `strategy` 对象在 on / off 两种开场包下跑同一组导航任务，
      统计每题的 `execute()` 次数与站点请求次数（口径见 §6）。
      **「两组共用策略」必须是结构上可断言的，不能只是约定**：骨架把它实际用过的
      策略对象记进返回值，测试断言 `on_run.strategy is off_run.strategy`（**同一性，不是相等**）。
      没有这条，M3 那种「两组各抄一份」的变异会**恒绿**——两份相同的代码产出相同的次数。
      - Skill: `none`
- [ ] `Add` — 任务集（**固定、写死在夹具里**，来源于本仓已有的实测面）：
      至少三题 —— ① 受限身份问不可见 DocType（对应 §7.4 的越权探测场景）；
      ② 可见范围内的单跳取数；③ 需要 `meta.fields` / `doc.links` 的多跳导航。
      **题目与预期路径逐字写进夹具**，不许执行期改题。
      - Skill: `none`
- [ ] `Proof` — 跑度量，把 on / off 两组数字**填进 §6 的对照表**，逐条判 H1–H4 吻合与否。
      **不吻合就照实写并停下来问人，不改假设、不换题**（硬约束 ②）。
      - Skill: `none`
- [ ] `Decision` — 质量判据在测试里断言成什么形状：**断言 H1/H2/H4 的方向与上界**，
      **不断言具体次数等于某个数**（次数会随夹具演进漂移，钉死它会让判据变成脆的）。
      具体数字**记进 owner doc 的落点节**并标注「本仓夹具实测，非站点实测」。
      备选「把次数钉死成常量」——否决理由：夹具一改就红，红在夹具而不是红在实现。
      **残余风险**：方向性断言比数值断言弱，一个「只慢一点点」的退化不会被打红；
      缓解是把数字写进落点节，人复核时能看见趋势。**残余风险不消除。**
      - Skill: `none`

Exit Criteria:

- [ ] H1–H4 四条逐条有「吻合 / 不吻合」判定，写在 plan 里
- [ ] 质量判据以方向 + 上界形式落进 `tests/tools/test_navigation.py`，且 H4 反测为红
- [ ] 两组数字落进 owner doc 落点节，逐字标注「本仓夹具实测，非站点实测」（硬约束 ④）
- [ ] `docs/logs/2026/08-24.md` 更新

### Phase 3 — 权限拒绝熔断 + 落点节 + 收口

Status: planned
Targets: `agenerp/orchestration/circuit.py` · `tests/tools/test_navigation.py` · `docs/architecture/module-boundaries.md` · `docs/masterplan/STATE.md`（**仅追加**）
Skill: `development-wisdom-gate-prompt.md`（收尾自查）

- Item Types: `Add | Proof | Fix | Decision`
- Prereqs: Phase 1、Phase 2

- [ ] `Add` — `DenialBreaker`：单次会话内**连续** N 次权限拒绝即终止（N 默认 5，§7.4 建议值），
      终止时产出**所需权限清单**与固定文案。**「连续」不是「累计」**——中间成功一次即清零，
      这一点必须有独立断言（累计版会把正常会话误刹）。
      - Skill: `none`
- [ ] `Decision | Add` — 拒绝的识别口径**沿用已实测的那一条**：`agenerp/tools/site_scope.py:70`
      逐字「**只有 HTTP 403 被判成『这个身份读不到』**」，其余任何失败照旧抛出去（判定代码在 `:79-84`）。
      **不得**把站点宕机、超时、5xx 计进熔断计数——那会把「站点坏了」读成「你没权限」。
      ⚠️ **它今天不是一个可复用件**：那段判定内联在 `doctypes_with_data` 里，
      而 `permission_scope` 自己**根本不分类 403**。因此「沿用」必须二选一，本 plan 就地裁定：
      **选定「在 `agenerp/orchestration/` 里独立实现一次，并加一条断言锁死两处口径一致」**。
      **断言的机制写死，免得执行者去比源码文本**：拿 `FakeSite` 驱动 `doctypes_with_data`
      两次——一次让目标 DocType 落在 `forbidden`（403），一次让站点抛非 403 的失败——
      取它的**行为**（前者进 `unreadable`、后者原样抛出）作为基准，
      断言 `agenerp/orchestration/` 那份对同样两种输入给出**相同的分类**。
      ⚠️ **现成的 `FakeSite` 造不出「非 403 失败」**：它对 `get_count` 只回 200 或 403。
      测试要**包一层 transport**（几行）让它抛一个非 403 的 `SiteError`——
      这一步先写在这里，免得执行者卡在「夹具做不到」上。
      备选「把 `site_scope.py` 里那段抽成公共函数」——**否决**：那要改 P1.0a 已收口的执行体，
      撞 §3 Non-Goals 3。**残余风险**：两处口径靠一条断言绑定，
      有人只改一处且顺手改断言就会漂移——这条写进落点节，靠人复核兜。
      - Skill: `none`
- [ ] `Proof` — `tests/tools/test_navigation.py` 追加：
      ① 连续 5 次 403 → 刹车，且返回值含所需权限清单；
      ② 4 次 403 + 1 次成功 + 4 次 403 → **不刹车**（连续 vs 累计的反测）；
      ③ 5 次**非 403 失败** → **不刹车**（站点宕机不算权限拒绝）；
      ④ 刹车文案与所需权限清单**非空且指名 DocType**。
      - Skill: `none`
- [ ] `Proof` — **假实现变异自查**（逐个植入 → 跑 `python3 -m pytest tests/tools -q` → 原样还原，
      结果表进 plan）。**八个，一个不少**：
      M1 装配器不注入、只写标志 `True`；
      M2 注入产物只保留 `can_read: True` 的行；
      M3 **保持 `run_metric` 签名不变**，在骨架内部**按开场包分叉**：
         包里没有注入产物（即 off 那一路）时改用另造的实例
         （`copy.deepcopy(strategy)` 或 `type(strategy)()`）——
         两组数字**逐位相同**，只有 `on_run.strategy is off_run.strategy` 这条**同一性**断言能打红。
         ⚠️ **不要**把变异写成「改签名收两个策略参数」：那会让既有调用点 `TypeError`，
         红在**元数**上而不是红在同一性上，等于没测到该测的东西
         （且改测试调用点违反本节「只改实现、不动测试」的变异协议）；
      M4 熔断改成累计计数；
      M5 熔断把非 403 失败也计进去；
      M6 **在 `ToolResult` 之后的开场包装配路径上**覆盖 `permission_probe_method`
         （⚠️ 变异位必须在装配路径，不能在传给 `execute` 的 `context` 里——
         `runtime.py:359` 已让执行体的事实覆盖调用方的，那个位置的变异会被机制自动吃掉、恒绿）；
      M7 装配器把「注入代价」（`request_count` 与候选集大小）从开场包里去掉或写成常量
         （对应「注入代价可断言」那条 Exit Criteria——没有它，那条判据没有反测）；
      M8 装配器**忽略调用方给的候选集**、一律走发现式路径
         （对应反测 B：`FakeSite.requests` 里会冒出 `GET /api/resource/DocType`，必须红）。
      **八个一个不少；任何一个没被打红，就地补断言，并把「补了什么」写进 plan。**
      - Skill: `none`
- [ ] `Fix` — `docs/architecture/module-boundaries.md`：
      (a) **§7.4 末尾追加落点**（熔断从「仍未做」改为已落地，含 N 值、连续语义、403-only 口径、
      以及「**接到真实循环上是 P1.4 的动作**」这句限定）；
      (b) **§7.6 追加一节「编排层在本仓的落点」**（各文件职责、D1/D2/D3 三个 `Decision`、
      §6 的 H1–H4 对照结果、Phase 2 的两组数字并标注「本仓夹具实测」、§1.6 判定面缺口照实记）。
      ⚠️ §7.6 里那句「§7.4 的权限拒绝熔断（N=5）仍未做……归 P1.0 的控制循环」**必须一并改准**
      ——它现在是**确认的 owner-doc 漂移**（P1.0 已 `done` 且未做它），按指南第 14 条不可降级为 follow-up。
      - Skill: `none`
- [ ] `Add | Proof` — 收口时**在 STATE §3 追加**一条 needs-human，内容三项
      （**不是 `Decision`**：三项内容都由已有事实直接推出，没有待选方案，因而没有备选与残余风险可写）：
      (a) `tests/tools`（含新文件 `test_navigation.py`）/ `tests/routing` / `tests/context`
      接进 CI 的 `unit-and-contracts` / `lint` 与 `commands.test`；
      (b) 逐字写明**熔断尚未接到任何真实循环上**（§5.2 D2 残余风险）；
      (c) 逐字写明本 plan 的质量数字是**本仓夹具实测**，与 owner doc 里 Spike 02 的「35 → 1」
      **不是同一个站点、不是同一道题**，不得互相引用为佐证。
      **只追加，不改写任何已有行**（红线 5）。
      - Skill: `none`

Exit Criteria:

- [ ] 熔断四条断言全绿，含「连续 vs 累计」与「403-only」两条反测
- [ ] 变异自查 **M1–M8 八项**结果表进 plan，含「由此当场加强过的地方」
- [ ] `module-boundaries.md` §7.4 与 §7.6 两处更新，且 §7.6 那句已失效的归属被改准
- [ ] STATE §3 追加一条 needs-human，且 `git diff --numstat` 对该文件的**删除列为 0**
- [ ] `docs/logs/2026/08-24.md` 更新

## 8. 本 mission 四条硬约束的逐条对照

| 约束 | 本 plan 怎么满足 |
|---|---|
| ① 判据不许只验「调得通」 | 「注入调得通」不是判据，「**注入真的发生过**（从 `FakeSite.requests` 核出）且写死标志会红」才是。变异自查 **M1–M8** 是「假实现照样绿吗」的直接回答 |
| ② 预测在前、结果在后 | Phase 2 的质量度量是本仓没有过的数字 → §6 的 H1–H4 在跑之前逐字写死，事后逐条对照，不吻合照实写 |
| ③ 规则能覆盖的流程不 Agent 化（D-15） | 开场装配、导航策略、熔断计数**全是确定性规则**，零模型参与。质量判据刻意不用真模型度量（§5.2 D3 的否决 A） |
| ④ 以本项目的实测为准（D-16） | owner doc 的「35 → 1」只作**假设的来源**（§1.7），不作目标值也不作断言常量；本 plan 自己量出的数字标注「本仓夹具实测，非站点实测」 |

## 9. 风险

1. **「注入发生了」被写成一个骗得过去的标志。** 这是本 plan 最核心的失败模式，
   也是它存在的理由。缓解：事实由记录推导 + 反测 A + 变异 M1。**残余**：推导判据本身若被改松
   （例如只看 `ok is True` 不看 `request_count`），反测仍会绿——靠独立关闭审计兜。
2. **质量口径被设计成必然赢。** 缓解：H4 反测（换空包则差异必须消失）+ 变异 M3（两组各用一份策略必须红）。
   **残余**：任务集是本 plan 自己选的，选题偏向仍可能存在；缓解是题目写死在夹具里、
   来源逐条注明，人复核时能看见选了什么、没选什么。**残余风险不消除。**
3. **熔断没有接到任何真实循环上**（§5.2 D2）。缓解：STATE §3 (b) 项逐字声明。
   **残余不消除**：本 plan 能证明的是策略对象的行为，不是「真实会话里它一定被调用到」。
4. **`tests/tools` 不在任何判定面上**（§1.6）。缓解：§5.3 三条。**残余风险不消除。**
5. **P1.2 未完成时被先派发**（§5.1）。缓解：写死为 Prereqs，并规定执行者停下来往 STATE §3 追加一行。
6. **契约面那条后置断言仍然软**（§1.1a D4 残余）：绕过 `agenerp/orchestration/` 直接调 `execute` 的人
   照样能把 `injected_at_session_start` 填成 `True`。缓解：开场包面另立一条推导事实 + 反测 A。
   **残余不消除**——本 plan 加强的是编排面，不是契约面。
7. **两处 403 口径靠一条断言绑定**（Phase 3 的 `Decision` 残余）。**残余不消除。**
8. **`agenerp/orchestration/` 与 P1.4 循环本体的接缝只有单侧验证**（§5.2 D1 残余）。
   缓解：接口面刻意做小（开场包、导航策略、熔断三个对象，各自可独立构造）。
   **残余**：P1.4 接线时可能发现接口不合用——那时改接口是 P1.4 的动作，不是本 plan 的缺陷。

## 10. Deferred But Adjudicated

### 证据充分性门禁的运行时（L1/L2/L3）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: WBS §4 **第 83 行**把它归 P1.4，且它有自己的 🔴 门禁
  `tests/gates/test_evidence_gate_blocks_single_hop.py`（红线 1 内，人才能建）。
- Successor Required: `yes`（P1.4）
- 重开事件：**P1.4 开工**。

### 熔断接进真实控制循环

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 真实循环本体属 P1.4（§3 Non-Goals 1）；本 plan 交付被调用方驱动的策略对象。
- Successor Required: `yes`（P1.4）
- 重开事件：**P1.4 的控制循环落地**，或人明确要求先接到实验设施上。

### 「35 → 1」在本项目站点上的复验

- Classification: `watch-only residual`
- Why Not Blocking Closure: 那是 Spike 02 在别的站点上的数字（硬约束 ④）；
  本 plan 用本仓夹具量出自己的数字，**不以复验外部数字为关闭条件**。
- Successor Required: `no`
- 重开事件：**有人要把「35 → 1」当作本项目的结论引用**——那时必须先在本项目站点上复验。

### 向量兜底召回

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: `context-and-memory.md` §8.1 的现行结论是「结构化导航优先，
  向量仅作兜底」；P1.0a 与 P1.2 均已裁为 out-of-scope，重开事件未触发。
- Successor Required: `no`
- 重开事件：**结构化导航在真实问句上出现可复现的召回失败**（有轨迹为证）。

## 11. Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，全新会话，2026-08-24）——
  开出 5 条 Blocker：① Phase 1 的核心交付**机制上不可能**——`runtime.py:359` 的事实合并加上
  `contracts.py:102` 的缺席即判否，使 `execute("permission.scope")` 在调用方不交这条事实时
  必然 `ok=False`，而首稿写的是「不接受外部传入」；② 反测 B（装配器给身份提权）
  **不可机械检测**，`FakeSite` 根本没有身份概念，对任何实现恒绿；
  ③ M3（两组各用一份策略代码）没有任何断言能打红——两份相同代码产出相同次数；
  ④ §6 的 H1–H4 **没有定义计数口径**，开场注入那次算不算进去会翻转 H1/H3 的真假，
  执行者可以看完数字再选；⑤ 基线 sha 与工作树描述都写错（HEAD 是 `b3b2f1f`，
  evidence 那几个文件是已跟踪被修改而非未跟踪）。另有 8 条 non-blocking + 7 条 fact-check。
  **逐条处置**：①→新增 **§1.1a**，把契约面（调用方自证，不加强）与开场包面
  （从记录推导、另立名 `opening_injection_verified`）拆成两段，并补 `Decision` D4
  裁定「不改契约、把强度放在编排面」，残余风险逐字写明；
  ②→反测 B 改写为可机械检测的形态（带候选集注入时 `FakeSite.requests` 里
  不得出现 `GET /api/resource/DocType`，且 `has_permission` 次数恰等于候选集大小），
  并逐字说明首稿那条为何被删；③→度量骨架改为**策略以单个可调用对象注入**，
  断言 `on_run.strategy is off_run.strategy`（同一性），M3 相应改为「骨架接受两个策略参数」；
  ④→§6 新增**计数口径**三行（含开场注入那一次；站点请求另计；终点含「明确拒答」），
  并把 H3 标注为「成本记账，不是判别性假设」；⑤→基线改 `b3b2f1f`、工作树照实。
  另处置：§1.1 的census 由「9 处」改为逐类点清的 10 处、§1.2 表的四处行号改准、
  239 那个数的**归属**改准（它量的是 `get_count` 不是 `has_permission`，本仓从未量过后者）、
  403 口径补一条 `Decision`（它今天不是可复用件）、M6 变异位改到装配路径、
  STATE 追加项由 `Decision` 改为 `Add | Proof`、§2 补一句「一个结果面」的说明。
- Independent draft review iteration 2: **needs revision**（独立子代理，全新会话，2026-08-24；
  该评审**实跑了** `execute("permission.scope", ...)` 打 `FakeSite`，逐条核对而非纸面读）——
  确认 §1.1a 的机制描述**正确**（带 `injected_at_session_start=True` 与候选集时
  `ok=True`、`request_count=3`、只发三次 `has_permission`；不带则 abort 在 `postconditions`
  且理由是「上下文缺少事实」），确认反测 B **可机械检测**，确认 §6 计数口径无歧义、
  H2 与之自洽，确认 M1/M2/M4/M5/M6 各有能打红的断言，红线与 Anti-Slacking 干净，
  并确认把 §7.4 熔断折进本 plan **在指南第 4 条下站得住**。
  余下 2 条 Blocker：① **H4 引用了一个按 §1.1a 永不进开场包的名字**
  （`injected_at_session_start`），H4 因此不可实现——这是本轮改动引入的回归；
  ② M3 写成「改签名收两个策略参数」会让既有调用点 `TypeError`，**红在元数不是红在同一性**，
  同一性断言仍然没有反测，且改测试调用点违反变异协议本身。
  **逐条处置**：①→H4 改为「人工置真 `opening_injection_verified`」，并写明空包变体仍带该标志
  以防策略靠「包空不空」旁路分叉；②→M3 改为**保签名的内部替身**
  （`copy.deepcopy(strategy)` / `type(strategy)()`），两组数字逐位相同、只有 `is` 能打红。
  另处置 non-blocking：`runtime.py:357`→**`:359`**（五处）、`site_scope.py` 循环行号改准、
  §8 标题「三条」→「四条」、`missions/**` 由「红线内」改为照实说（它在 Protected Areas 标 `blocked`，
  不在 AGENTS.md 红线表 1–7 里）、Phase 1 `Proof` ② 补上「现成 `fake_site` 夹具全回 `True`，
  测试必须自己置 `False`」、Phase 3 的 403 一致性断言补上**机制**（拿 `FakeSite` 驱动
  `doctypes_with_data` 取行为作基准，不比源码文本）、新增 **M7 / M8** 覆盖
  「注入代价可断言」与反测 B 两条此前没有反测的判据。
- Independent draft review iteration 3: **acceptable as-is**（独立子代理，全新会话，2026-08-24）——
  **无 Blocker**。确认 iteration 2 的两条 Blocker 均已解决：H4 现在点名
  `opening_injection_verified`（Phase 1 真正推导并放进开场包的那条），H1–H4 与 §1.1a 的
  两段机制、与计数口径三处自洽（H2 的 ≤2 = 1 次注入 + 1 次确认，与「含开场注入那一次」吻合）；
  M3 改成保签名的内部替身后 `copy.deepcopy` 产出逐位相同的数字，**只有 `is` 断言能打红**，
  元数报错那条失败模式已消失。并确认 **M8 真能打红**（忽略候选集会走进 `business_doctypes`，
  发出 `GET /api/resource/DocType`，正是反测 B 禁止的），`fake_site` 夹具全回 `True` 的说明属实，
  以及全部行号、引文、CI/missions 作用域、WBS 82/83、STATE §3 两条时间戳逐条核准；
  `module-boundaries.md:183` 那句「熔断仍未做…归 P1.0」确为 owner-doc 漂移，按指南第 14 条记 `Fix` 正确。
  8 条 non-blocking 中**会绊住执行者的 6 条已就地处置**：
  Phase 1 新增 `Proof` ⑥（注入代价必须与实际请求条数对得上——M7 此前没有靶子，
  且只断 `request_count > 0` 挡不住「写成常量」）；§8 表格「M1–M6」改「M1–M8」；
  Phase 3 的 403 一致性断言补上「现成 `FakeSite` 造不出非 403 失败，要包一层 transport」；
  M3 的措辞改为「按开场包分叉」以贴合 `run_metric` 的单参数签名；
  H4 的判据由「差异消失」改为「**H1 不再成立**（on 不小于 off），不取等号」；
  Phase 1 Exit Criteria 补 `No owner-doc update required` 的等价说明。
  余 2 条为提示项：§1 的工作树快照必然随时间漂移（已改为「以 `git status` 实测为准」），
  以及 P1.2 前置在起草时尚未完成——§5.1 的「停下来往 STATE §3 追加一行」规则**开工第一天就是活的**。

## 12. Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned（`module-boundaries.md` §7.4 落点 + §7.6 新节，且 §7.6 那句已失效的熔断归属被改准）
- [ ] verification has run：`python3 -m pytest tests/tools/test_navigation.py -q` ·
      `python3 -m pytest tests/tools -q` ·
      `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` ·
      `python3 -m pytest tests/contracts -q` ·
      `python3 -m pytest tests/context -q`（**该目录由前置 P1.2 交付**，本 plan 开工时它必然已存在；
      跑它是为了证明本 plan 没有把上下文层碰坏）·
      `ruff check agenerp tests/unit tests/contracts`
      —— 命令原文 + 退出码 + commit sha 同条写出
- [ ] scoped verification is not conflated with full verification —— `tests/tools` 不在 CI 与
      `commands.test` 上，收口时必须逐字写「verification scope limited」并说明残余风险
- [ ] §6 的 H1–H4 四条逐条判定已写入，不吻合的照实写且未改假设
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified（`grep -B5 "\- \[ \]" <plan> | grep "Status: completed"` 为空）
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] STATE §3 已**追加** needs-human（含 (a)(b)(c) 三项），且该文件删除列为 0
- [ ] 收口叙述里**没有**任何「熔断已在真实循环上生效」或「本仓复现了 35 → 1」的说法
- [ ] 收口叙述逐字写明：`tools_readonly.py:296` 那条后置断言**仍是调用方自证的软断言**
      （§1.1a D4 的残余风险），**不得**说成「注入已被契约保证」
- [ ] 收口叙述**不得**把 239 写成「开场注入的实测代价」（§1.2 表末的 ⚠️）

## 13. Closure

<待收口时填写。代填即伪造关闭证据。>
