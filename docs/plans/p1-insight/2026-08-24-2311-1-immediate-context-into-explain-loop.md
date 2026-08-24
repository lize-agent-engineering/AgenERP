# P1.8 前置 · ① 即时上下文（当前单据）接进解释循环

> Plan Status: completed
> Mission: p1-insight
> Work Item: 10. Agent 侧边栏嵌 Desk（P1.8）—— 本 plan 是它**后端侧的硬前置**；同时结清工作项 4（P1.2）Non-Goals 3 留下的接线缺口
> Execution Order: 1 / 2（本批第一个。同批第二个是 `2026-08-24-2311-2-desk-embed-carrier-decision.md`。**必须串行**：两者都要往 `docs/architecture/module-boundaries.md` 新增落点节、都要往 `docs/masterplan/STATE.md` 追加、都要写 `docs/logs/2026/08-24.md`；且第二个 plan 的「一次带当前单据的解释请求」在语义上依赖本 plan 的接线。开写前重读当时的最大节号再顺延，避免撞号）
> Last Reviewed: 2026-08-24（起草基线 sha `e3de756`，`git status --porcelain` 除本批两个未跟踪的 plan 文件外无输出）
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 10（P1.8「保留当前单据上下文」逐字）· `docs/masterplan/02-WBS.md` §4 **P1.8 行** · `docs/design/context-and-memory.md` §8.2 ① 行与「上下文窗口工程」规则 1/2 · 工作项 4 的 plan `2026-08-24-1457-2-context-layer-v0.md` §3 Non-Goals 3
> Related: 前置 P1.2（已 `completed`，交付 `agenerp/context/`）· 前置 P1.4（已 `completed`，交付 `agenerp/explain/`）· 后继 P1.8 承载面 plan（本批第二个）
> Audit: required

## 0. 执行前必做：重取基线

本节的数字与行号是**起草当时**（sha `e3de756`）读出来的。执行者**开工第一件事**是原样重读下面
七处，把实读结果写进 §0.1；**与本节不一致时以实读为准**，并在 §0.1 逐条记差异 —— 不许默默按本节写。

```bash
git -C . log -1 --format=%H && git status --porcelain
sed -n '285,320p'  agenerp/explain/loop.py          # _open / _opening_message / run() 的消息装配
sed -n '587,605p'  agenerp/explain/loop.py          # explain() 签名
sed -n '119,168p'  agenerp/orchestration/opening.py # open_session(immediate=...) 的去向
sed -n '86,132p'   agenerp/context/immediate.py     # ImmediateContext.blocks() / assemble()
grep -rn "assemble(" agenerp tests | grep -v "context/immediate.py"   # ① 装配面今天的调用方（H1）
grep -rn "^### 7\." docs/architecture/module-boundaries.md | tail -3   # 落点节最大号
```

### 0.1 执行期重取基线的**实读结果**

> 执行者填。格式：每条一行「读了什么 → 实读结果 → 与 §1 一致 / 不一致（差在哪）」。
> **本节为空即视为未重取基线**，收口审计据此判不通过。
> 落点节号在本节**落定**（`§7.x` 的 `x`），后文一律引本节，不在别处再写死一次。

执行期实读（2026-08-25，开工第一件事，七处逐条原样复跑）：

1. `git log -1 --format=%H && git status --porcelain` → sha `e3de756537db7ed124fcb09561a228a37a128745`，
   `git status --porcelain` 只有本批两个未跟踪的 plan 文件（`?? docs/plans/p1-insight/2026-08-24-2311-1-…`、
   `?? …-2311-2-…`）→ **与 §1 一致**（起草基线 sha 逐字相同，工作树干净）。
2. `sed -n '285,320p' agenerp/explain/loop.py` → `_open()` 在 `:285`，调 `open_session()` 只传
   `client` / `doctypes` / `session` / `executors`，**没有 `immediate`**；`_opening_message()` 在 `:298`，
   只渲染 `pack.scope`；`run()` 在 `:307`，`messages` 三条初值在 `:317-321`，第二条 `system` 在 `:319`，
   `{"role": "user", ...}` 在 `:320` → **与 §1.2 一致**。
3. `sed -n '587,605p' agenerp/explain/loop.py` → `explain()` 在 `:587`，签名十二个参数逐字为
   `question` / `task_class` / `client` / `models` / `requested` / `config` / `transport` / `doctypes` /
   `session_id` / `user` / `max_turns` / `executors`，**没有任何表示「当前单据」的参数** → **与 §1.2 一致**。
4. `sed -n '119,168p' agenerp/orchestration/opening.py` → `open_session(immediate=...)` 在 `:124`，
   `OpeningPack(... immediate=immediate ...)` 在 `:162`；`cost=InjectionCost(result.request_count, candidate_count)`
   在 `:160` → **与 §1.2 / J6 一致**（J6 的 `:160` 行号复现）。
5. `sed -n '86,132p' agenerp/context/immediate.py` → `ImmediateContext` 在 `:86`，`blocks()` 在 `:95`，
   返回两块：`ContextBlock(TIER_DOCUMENT, "document", {...doctype/name/role/view/fields})` 与
   `ContextBlock(TIER_ACTIONS, "actions", list(self.actions))`；`assemble()` 在 `:113`，
   `wrap_free_text(dict(fields), BOUNDARY_KEEP)` 在 `:123` → **与 §1.1 / §1.4 一致**。
6. `grep -rn "assemble(" agenerp tests | grep -v "context/immediate.py"` → 四行命中，逐行归类：
   `agenerp/context/session.py:156`（docstring 提及，**不是调用**）·
   `tests/tools/test_navigation.py:319`（判据调用）· `tests/context/test_immediate.py:56` 与 `:172`（判据调用）。
   **`agenerp/` 下零调用点** → **与 §1.1 / H1 的预测逐字一致**（H1 吻合，见 §6 实际列）。
7. `grep -rn "^### 7\." docs/architecture/module-boundaries.md | tail -3` → 最大为
   `docs/architecture/module-boundaries.md:868:### 7.11 单次解释成本账本与失控闸在本仓的落点（P1.7 · 2026-08-24）`
   → **与 §7 Phase 3 起草期记的「最大为 §7.11，`module-boundaries.md:868`」一致**。

**落点节号落定：`§7.12`**（顺延 §7.11）。后文一律引本条，不在别处再写死一次。

另附执行期实读的五条基线数（§1.6 逐条复跑）：`tests/unit` **503 passed** ·
`tests/context` **53 passed** · `tests/tools` **81 passed, 12 skipped** ·
`tests/routing` **164 passed, 1 skipped** · `tests/contracts` **151 passed**，
`python3 tools/gates/check_expected_red.py` 退 0（门禁 11 项：预期红 0，绿 11）→ **五条与 §1.6 逐字一致**。

## 1. Current Baseline

### 1.1 ① 即时上下文装配面已经存在，而且**产品路径上一个调用方都没有**

- `agenerp/context/immediate.py` 交付了 `CurrentDocument` / `ContextBlock` / `ImmediateContext` /
  `assemble()`（`:113`）/ `trim()`（`:132`），判据 `tests/context/test_immediate.py`，随 P1.2 收口（53 passed）。
- `ImmediateContext.blocks()`（`:95`）把 ① 档摊成一块 `payload`：
  `{"doctype", "name", "role", "view", "fields"}`；② 档摊成 `list[str]`。
- **调用方清点（起草期实读，不是推断）**：`agenerp/` 下对 `assemble(` 的命中只有
  `agenerp/context/session.py:156` 的**一句 docstring 提及**，没有任何调用点。
  `tests/` 下有两处真调用：`tests/context/**` 与 **`tests/tools/test_navigation.py:319`**。
- → **产品路径上零调用方**；装配面今天只被判据用着。

### 1.2 循环侧留了位置，但那个位置在产品路径上是**死端**

- `agenerp/orchestration/opening.py`：`open_session(immediate=...)`（`:124`）把参数原样塞进
  `OpeningPack.immediate`（`:162`）。
- **`OpeningPack.immediate` 今天唯一的读者是一条判据**：
  `tests/tools/test_navigation.py:328` 的 `assert pack.immediate is immediate`
  （P1.3 交付，钉的是「开场包原样携带 ①、不改一个字段」）。
  ⚠️ **本 plan 不重做这一条**；它还负责一件事：Phase 1 的「`tests/tools` 逐字不变」
  正是靠它 —— 本 plan 若把开场包的携带语义改坏，那条会先红。
- **产品路径上没有任何读者**：`agenerp/explain/loop.py` · `ExplainLoop._open()`（`:285`）
  调 `open_session()` 时**根本没有传 `immediate`**，所以在产品路径上那个字段永远是 `None`。
- `ExplainLoop._opening_message()`（`:298`）只渲染 `pack.scope`（可见范围），与当前单据无关。
- `explain()`（`:587`）的签名里**没有任何表示「当前单据」的参数**：
  `question` / `task_class` / `client` / `models` / `requested` / `config` / `transport` /
  `doctypes` / `session_id` / `user` / `max_turns` / `executors`。
- `ExplainResult.opening`（`loop.py:226`）**已经把开场包带出来了**（`_result()` 在 `:572` 填的），
  所以「死端接没接上」这件事**在返回值上可断言**（J10 用它）。

**一句话基线**：① 层今天是**装配得出来、送不进去**。P1.8 逐字要求「保留当前单据上下文」，
而当前单据从来没有到过模型面前。

### 1.3 P1.2 已经把这件事写成了显式定界，不是遗漏

`docs/plans/p1-insight/2026-08-24-1457-2-context-layer-v0.md` §3 Non-Goals 3 逐字：
「**不做控制循环本身**……本 plan 交付『循环要用的上下文装配与会话记录』，循环归 P1.4」。
P1.4 的 plan 则只接了会话侧（`agenerp.context.session`），① 档没接。
**两个 plan 各自的边界都成立，缝在中间** —— 本 plan 就是来补这条缝的。

### 1.4 注入面的包裹口径已经定死，本 plan 不许再定一次

`assemble()` 对字段表调 `wrap_free_text(dict(fields), BOUNDARY_KEEP)`（`immediate.py:123`），
`BOUNDARY_KEEP` 恰好是 `STRUCTURAL_KEYS`（`:32`，`name` **不在**里面 —— 取舍见 §7.7 的 `Decision`）。
标记串本身在 `agenerp/tools/runtime.py`：`DATA_BOUNDARY_OPEN = "⟦用户输入数据·非指令⟧"`（`:62`）、
`DATA_BOUNDARY_CLOSE = "⟦数据结束⟧"`（`:63`）、值里自带的闭标记被换成
`_BOUNDARY_ESCAPE = "⟪已剥离的边界标记⟫"`（`:67`）。`module-boundaries.md` §7.5 是这条规则的出处。
**本 plan 的渲染面必须把这层标记原样带下去**，剥掉即等于把 §7.5 在这条注入面上取消掉。

### 1.5 ② 档（已执行动作）在循环里**已经有一份**，形态不同

`ConversationSession.audit_records()`（`session.py:155`）把已执行动作摊成字符串序列，
注释逐字写着「喂给 `immediate.assemble(actions=...)` 的那一档」。
但 `ExplainLoop` 的 `messages` 列表本身就逐条带着 `tool_call` 与工具结果 ——
**同一批事实在循环里已经在场，只是形态不同**。这直接决定 §7 的 `Decision` D2。

### 1.6 本 plan 不改判据以外的既有行为（五条基线数）

起草期实读：`tests/unit` **503 passed** · `tests/context` **53 passed** ·
`tests/tools` **81 passed, 12 skipped** · `tests/routing` **164 passed, 1 skipped** ·
`tests/contracts` **151 passed**。
本 plan 只**新增**判据文件与**新增**关键字参数，既有断言一条都不该动；
动了就是行为变更，必须在 §7 里显式登记，不许顺手改。
⚠️ `tests/contracts` 必须跑：本 plan 动的是 `agenerp.explain.explain` 这个**公开入口的签名**，
而 `agenerp/insight/` 走的正是它（P1.5 收口记录逐字）。

## 2. Goals

1. **当前单据真的到得了模型面前**：`explain()` 接收一份 `ImmediateContext`，
   循环把它渲染成**一条独立的 `system` 消息**，角色、位置、条数全部写死可断言。
2. **`opening.py:162` 那条死端在产品路径上被真的接上**：`ExplainResult.opening.immediate`
   是调用方传进来的**同一个对象**（不是循环旁路自持一份）。
3. **判据能区分「真接了」与「看起来接了」**：注入内容取自 `ImmediateContext.blocks()`，
   而不是循环自己按 `document` 重拼一份；且随夹具变。
4. **边界标记不在渲染面失守**：自由文本字段注入后 `⟦…⟧` 标记原样在。
5. **不截断**：渲染面**没有任何截断分支**，超长字段原样出现在消息里。
6. **注入不偷偷打站点**：带 / 不带两种配置下 `FakeSite.requests` **逐字相等**。
7. **注入只发生一次**：整跑中 ① 消息不随轮数重发。
8. 落点写进 `docs/architecture/module-boundaries.md` 新增节（节号见 §0.1），
   `docs/design/context-and-memory.md` §8.2 ① 行补落点指针（**只补指针，不改语义**）。

## 3. Non-Goals

1. **不做 ③ 记忆层 / ④ 检索层**（P1.2 已裁定，重开事件未触发）。
2. **不把 ② 档再注入一次**（理由见 §1.5，裁定见 §7 D2）。
3. **不引入上下文预算参数、不调 `trim()`**（裁定见 §7 D3；Deferred 见 §11）。
4. **不写 Desk / 前端的任何一行**，不建任何 HTTP 服务面 —— 那是本批第二个 plan 与 P1.8 本体。
5. **不做权限校验**：① 层「不打站点、不查权限」是 `immediate.py` 模块头写死的三条规矩之一。
   调用方塞进来的字段表是否是当前登录用户有权看的，**本层不判、也判不了**（§8 R1）。
6. **不改 `agenerp/context/immediate.py` 的装配语义**（`assemble` / `trim` / `blocks` 的行为），
   **不改 `agenerp/orchestration/opening.py`**（它已经把 `immediate` 摆对了）。
   只做调用方。若判据打红逼出必须改，按 §7 的登记规则显式记，不许顺手改。
7. **不改 `tests/tools/test_navigation.py:315-328`**（那是 P1.3 已收口的判据，也是本 plan 的护栏）。
8. **不动 `docs/backlog/p1-insight-roadmap.md` 的 Work Item Status 块**：
   工作项 10 保持 `todo`（本 plan 只是它的前置，不结清它）。裁定见 Phase 3。
9. **不碰 `tests/gates/**`、`.github/workflows/**`、`missions/*.json`、`docs/masterplan/**`**（红线 1/2/3/5）。
   `STATE.md` 只追加。

## 4. Task Route

- Type: `implementation-only change`（接线 + 判据；无数据模型形状变更、无活站点写、无公开契约新增）
- Owner Docs:
  - `docs/design/context-and-memory.md` **§8.2**（① 行与「上下文窗口工程」规则 1/2 —— 本 plan 只在 ① 行补落点指针）
  - `docs/architecture/module-boundaries.md` **§7.5**（边界标记，**只读**，包裹口径的出处）
  - `docs/architecture/module-boundaries.md` **§7.7**（上下文层落点，**只读**，`BOUNDARY_KEEP` 取舍的出处）
  - `docs/architecture/module-boundaries.md` **§7.6a**（编排层落点，**只读**，开场包携带 ① 的出处）
  - `docs/architecture/module-boundaries.md` **§7.8**（解释循环落点，本 plan 在其后新增一节）
- Skill Selection Basis:
  Registry（`docs/skills/README.md`）无实现类 skill 匹配「把已有装配面接进已有循环」→ 实现记 `Skill: none`；
  Phase 3 收尾用 `development-wisdom-gate-prompt.md` 自查；
  草案评审 `plan-audit-prompt.md`，关闭审计 `closure-audit-prompt.md`。

## 5. Infrastructure And Config Prereqs

- Phase 1 / Phase 2 **零外部依赖**：纯离线，不需要站点、不需要 LLM、不需要 docker。
  假件复用 `tests/unit/explain_fakes.py`（它按路径加载 `tests/tools/conftest.py` 的
  `FakeSite` / `client_for`，**不另写一份**）。
- Phase 3 的活端点两跑需要：`.env` 的 `DASHSCOPE_API_KEY`（**绝不进 git、不打印**）+
  本机活栈（`docker compose up -d`，站点 `frontend`，`127.0.0.1:18080`）+ 种子数据已装载。
  **拿不到其中任何一项时**：Phase 3 的活跑项记 `blocked` 并写进 `STATE.md` §3，
  Phase 1 / Phase 2 照常收口 —— 不许拿离线夹具冒充活跑证据。
- 无数据迁移，无回滚脚本需求：本 plan **不写活站点**（`git revert` 即完整回滚）。

## 6. 开工前写死的假设（硬约束②：预测在前、结果在后、逐条吻合）

> 下面五条**在写任何一行实现之前**逐字定稿。事后**只允许在「实际」列追加**，
> 不许改写「预测」列。不吻合的照实记，并写清前提哪里错了。

| # | 假设（预测） | 怎么判（命令 / 断言） | 实际 |
|---|---|---|---|
| **H1** | `grep -rn "assemble(" agenerp tests \| grep -v "context/immediate.py"` 的命中**恰好是三类**：① `agenerp/context/session.py:156` 的 docstring 提及（**不是调用**）② `tests/context/**` 的判据调用 ③ `tests/tools/test_navigation.py:319` 的判据调用。**`agenerp/` 下零调用点** | 上面那条 grep 的输出逐行归类 | **吻合**。实跑回四行，逐行归类：`agenerp/context/session.py:156`（docstring 提及）· `tests/tools/test_navigation.py:319`（判据调用）· `tests/context/test_immediate.py:56` 与 `:172`（判据调用）。**`agenerp/` 下零调用点**。见 §0.1 第 6 条 |
| **H2** | 注入**不产生任何额外站点请求**：带 / 不带 `immediate` 两种配置下 `FakeSite.requests` **逐字相等** | Phase 2 的 J6，同一夹具跑两次 | **吻合**。`test_j6_injection_costs_zero_extra_site_requests` 绿：`site_with.requests == site_without.requests`（`SiteRequest` 是 frozen 值对象，逐字比）。M7（渲染面加一次 `client` 请求）在这一条上红，`opening_request_count` 对 M7 确实一点不变 —— J6 的警告实测成立。活端点侧同向：两跑 `opening_request_count` 都是 **10** |
| **H3** | 带 `immediate` 时 `messages` 恰好**多一条**（不多不少），该条 `role == "system"`，位置在开场可见范围之后、`user` 提问之前 | Phase 2 的 J1 + J3 | **吻合**。J1 三例：省略参数 3 条、显式 `None` 3 条、给值（走 `explain()`）**4 条**；J3：注入那条 `role == "system"`、下标 == 开场那条 + 1、且 < `user` 那条的下标。M11（改成 `user`）与 M2（挪到提问之后）各红一条 |
| **H4** | 活端点一跑：把那张销售订单的字段表作为 ① 档送进去之后，模型在整跑中对**同一个 `name`** 的 `doc.get` 次数为 **0**（字段已在上下文里，不必再取一次）。数法：遍历 `ExplainTrace.tool_calls` 的 `tool` + `params` | Phase 3 从 `ExplainResult.trace` 数 | **吻合**（起草期写着「很可能不吻合」，实测吻合）。带 ① 那跑对 `SAL-ORD-2026-00001` 的 `doc.get` 次数 = **0**（第一个动作直接是 `doc.links`）；不带那跑 = **1**（是它的第一个动作）。⚠️ **这只是一跑**，不能读成「注入总能省掉那次取数」。证据 `docs/evidence/p1-immediate/summary.json` |
| **H5** | 带 `immediate` 的 prompt token **高于**同题不带的一跑（方向性预测，**不作优劣比较**，D-16） | Phase 3 两跑的 `cost_ledger` 汇总 | **部分吻合，前提有错**。**第 1 次模型调用**：3,775 vs 1,066（**高于**，+2,709，① 档 5,478 字符）—— 这一层方向吻合。**整跑合计**：75,159 vs 101,282（**低于**）—— 这一层不吻合。**前提错在**：H5 隐含「两跑除注入那段外一样」，实测轮数不同（带 ① **9** 次调用 `answered`；不带 **12** 次且撞 `max-turns` 未作答），整跑合计主要反映轮数差而非注入量。⚠️ **不据此作任何优劣比较**（D-16）。全文 `docs/evidence/p1-immediate/README.md` |

⚠️ **H4 很可能不吻合** —— 模型完全可能出于「核对」再取一次。不吻合不是失败，
是把「注入是否真的省了一次取数」这件事**测出来**；照实记，不改预测。

## 7. Execution Plan

### 本 plan 的三个 `Decision`（起草期已定稿，执行期只允许在实测反证下改，改了要写清）

**D1 · 渲染成一条独立的 `system` 消息，插在开场可见范围之后、`user` 提问之前**

| 候选 | 说明 | 结论 |
|---|---|---|
| (a) 拼进 `SYSTEM_PROMPT` | 它是模块级常量、判据直接引它；把每次请求都变的内容拼进常量，等于让常量不再是常量 | 否决 |
| (b) 拼进 `user` 提问那条消息 | 用户原话与注入内容混在一条里，事后无从分辨模型看的是哪一半；也让「注入了没有」不可断言 | 否决 |
| **(c) 独立的第三条 `system` 消息** | 与既有 `_opening_message()` **同形态**（`loop.py:319` 已经是第二条 `system`，P1.4 已在活端点上实测跑通） | **取此** |

残余风险：部分 OpenAI 兼容端点对多条 `system` 消息的处理口径不同。
**本仓已有先例且已实测**，所以这是既有形态的第三条，不是新形态；仍在 §8 R3 登记，Phase 3 的活跑会再撞一次。
⚠️ `role == "system"` 是本裁定的**承重部分**，必须有判据钉住（J3），否则实现改成 `user`
也能全绿，而 (b) 的否决理由当场作废。

**D2 · 只接 ① 档，② 档不重复注入**

理由见 §1.5：② 档的同一批事实在 `messages` 里已经逐条在场（`tool_call` + 工具结果）。
再注入一份会造成**双写**，且两份可能不一致（`audit_records()` 是摘要行，`messages` 是原始结果），
而「不一致时以哪份为准」没有任何判据说得清。
备选是「注入 ② 档、同时把 `messages` 里的工具结果压缩掉」—— 那是控制循环的记忆策略改造，
**远超本 plan 的一条接线**，否决。
残余风险：`blocks()` 会返回 ② 档那一块，渲染面**只取 ① 档那一块**，
因此必须**按 `key == "document"` 取**，不能按下标取 —— 下标取会在 `blocks()` 改序时静默串档（J7 钉住）。

**D3 · 不引入预算参数，循环根本不裁**

D-16 要求任何数字有本项目实测出处，而「① 档该占多少字符」本项目**没有测过**。
起草期评审另外指出：`trim()` 在本期的调用形态下只有两种结果 ——
**未超预算时返回的块序列与不裁恒等**；**超预算时抛而不裁**（`immediate.py:147-153`，
① / ② 都在 `UNTRIMMABLE_TIERS`，且本期没有 ③ / ④，可裁集合为空）。
因此一个 `immediate_budget` 参数在本 plan 里**没有真实调用方**，
而「装配得出来、送不进去」正是 §1.1 批评的那种形态 —— 本 plan 不许自己再造一个。

- 裁定：**不加参数、不调 `trim()`**。「① 不可裁」这条规则在循环侧的兑现方式改成
  **渲染面没有任何截断分支**，判据是「超长字段值原样完整出现在消息里」（J5）。
- 被否决的备选：(a) 拍一个默认字符数 —— 数字没出处，一旦写进代码会被后来者当实测结论引用；
  (b) 加参数但默认 `None` —— 零调用方的开关，同上。
- 残余风险：一张超大单据能把上下文撑爆，**失败形态在端点侧而不是本仓侧**（§8 R2）。
  重开事件写在 §11。

### Phase 1 — 把 ① 档接进循环

Status: completed
Targets: `agenerp/explain/loop.py`
Skill: `none`

- Item Types: `Add`（5 项中 4 项为 `Add`，末项为 `Proof`；三条 `Decision` 已在上面定稿）
- Prereqs: §0.1 已填

- [x] `Add` `ExplainLoop.__init__` 增加 `immediate: ImmediateContext | None = None`
      **一个**关键字参数；`_open()` 把它透传给 `open_session(immediate=...)`
      （把 `opening.py:162` 那条死端在产品路径上接上）
- [x] `Add` 新增 `_immediate_message(pack) -> str | None`：
      `pack.immediate is None` → 返回 `None`（**不注入任何消息**）；
      否则从 **`pack.immediate.blocks()`** 里**按 `key == "document"` 取块**，
      把该块的 `payload` 以 `json.dumps(..., ensure_ascii=False, sort_keys=True)` 原样序列化进消息体。
      ⚠️ **不得对 `payload` 做任何再加工**：不截断、不省略、不 unwrap 边界标记、
      不从 `pack.immediate.document` 另行重拼
- [x] `Add` `run()` 在 `_opening_message` 那条（`loop.py:319`）之后、`{"role": "user", ...}` 之前
      插入 `{"role": "system", "content": <该串>}`；**只在装配 `messages` 时插一次**，
      主循环里不再 append（J9 钉住）
- [x] `Add` `explain()` 增加同名关键字参数并原样透传给 `ExplainLoop`；docstring 写清
      「① 层不查权限，字段表由调用方负责」这条边界
- [x] `Proof` `tests/unit/test_explain_immediate_context.py` 新建，覆盖 Phase 2 的 J1–J11。
      命令：`python3 -m pytest tests/unit/test_explain_immediate_context.py -q` 退 0

Exit Criteria:

- [x] 带 `immediate` 时消息多一条、不带时一条不多（消融两侧各有断言）
- [x] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` 退 0，
      且 passed 数**只增不减**（503 → 更大）
- [x] `python3 -m pytest tests/context -q`（53）· `tests/tools -q`（81 + 12 skipped）·
      `tests/routing -q`（164 + 1 skipped）· `tests/contracts -q`（151）四条退 0 且**数字逐字不变**
- [x] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` 退 0
- [x] 落点节留到 Phase 3 一次写完（本 phase 不写文档）

### Phase 2 — 判据：把「真接了」与「看起来接了」分开

Status: completed
Targets: `tests/unit/test_explain_immediate_context.py`
Skill: `none`
Prereqs: Phase 1

- Item Types: `Proof`（本 phase 全部为 `Proof`）

判据清单（每条都要说明**它挡住的是哪种假实现**）：

- [x] **J1 消融 · 三例 · 至少一例走产品入口**：同一夹具、同一道题跑三次 ——
      ① **完全不给这个关键字参数**（走默认值）② 显式 `immediate=None`
      ③ `immediate=<装配产物>`。③ 的 `messages` 恰好多一条；**① 与 ② 一条都不多**。
      ⚠️ ① 与 ② **必须分开写**：M8 变的是**默认值**，若消融只写显式 `None`，
      默认值那条路径从未被跑到，M8 会绿而什么也没证明。
      ⚠️ **产品入口那一例取 ③（给值）**：必须经 `explain()` 跑，不许只在自建的 `ExplainLoop` 上成立
      —— 先例逐字：`tests/unit/test_explain_cost_ledger.py:586`。
      （M5「收了参数但不透传」由这一例打红；J5 的 `explain()` 那例是它的第二道保险。）
      ⚠️ **观测面写死**：`messages` 是 `ExplainLoop.run()` 的局部变量（`loop.py:317`），
      **`ExplainResult` 上没有它**。J1 / J3 / J5 / J9 / J11 对 `messages` 的一切断言
      一律读 `ScriptedModel.payloads[*]["messages"]`（`explain_fakes.py:83`），
      **不要去找返回值上的钩子** —— 那个钩子不存在。
      挡：「无论给不给都注入一条空壳」、「`explain()` 收了参数但不透传」。
- [x] **J2 内容取自 `blocks()`，且随夹具变**：
      (a) **参数化两个实质不同的夹具**（`doctype` / `name` / `fields` 三项都不同，
      其中那个**小夹具至少带 2 个字段** —— 只带 1 个的话 M14 的「只取前 N 个键」在 N=1 时恒等，
      变异会以错误的理由变绿），
      断言注入内容随夹具变 —— 挡「把某一个夹具的 payload 写死在渲染面上」；
      **并且**：对其中那个**小夹具**，把消息体从 `messages` 里解析回来，
      与一份**手写的期望字典逐字相等**（顶层键 `doctype` / `name` / `role` / `view` / `fields`，
      且 `fields` 的键集合完整）。
      ⚠️ **期望字典必须手写**，不许写成「再调一次 `blocks()` 拿来比」—— 那是 §8 R4 禁止的自证形态。
      挡：**payload 保真度缺口** —— 只判「随夹具变」与「标记键在」的话，
      渲染面把 `fields` 截成前 N 个键、或把 `role` / `view` 丢掉，J1–J10 全绿而 Goal 5 落空；
      (b) 另加一个 `ImmediateContext` **替身**，其 `blocks()` 返回**可与任何朴素重拼区分**的
      payload（例如多一个只有 `blocks()` 才会产出的标记键），断言注入内容来自 `blocks()` ——
      ⚠️ **替身必须继承 `ImmediateContext` 并且只覆盖 `blocks()`**，
      让 `.document` / `.role` / `.view` 原样可用。写成只有 `blocks()` 的鸭子类型桩，
      会让 M3 以 `AttributeError` 翻红 —— **红得不是地方，等于没测**（§8 R5 同一条理由）；
      挡「不调 `blocks()`，改从 `pack.immediate.document` 忠实重拼」（那种写法在朴素夹具上
      与 `blocks()` 逐字节相同，**单靠相等断言杀不掉**）。
- [x] **J3 角色与位置**：注入那条 `role == "system"`；其下标 == `_opening_message` 那条的下标 + 1；
      `user` 提问在它之后。断言写在**角色 + 下标关系**上，不写在「消息里有没有某个字符串」上。
      挡：「注入了但角色是 `user`」（D1 的 (b) 否决理由当场作废）、「注入了但塞在提问之后」。
- [x] **J4 边界标记不失守**：夹具里放一个含闭标记的自由文本字段（形状沿用
      `tests/context/test_immediate.py:114`，不新编一种），断言序列化后的消息体里
      `DATA_BOUNDARY_OPEN`（`⟦用户输入数据·非指令⟧`）与 `DATA_BOUNDARY_CLOSE`（`⟦数据结束⟧`）
      **原样包住该字段值**，且夹具里自带的闭标记已被换成 `⟪已剥离的边界标记⟫`
      （三个常量从 `agenerp.tools.runtime` import，**不在判据里抄字面**）。
      挡：「渲染时顺手 unwrap 一下更好看」。
- [x] **J5 不截断**：给一个远超常规长度的字段值（例如 100 KB），断言它在消息体里
      **原样完整出现**（首尾各取一段比对，不出现省略号 / 截断标记），且消息长度 ≥ 该值长度。
      至少一例经 `explain()`。
      挡：静默截断 —— 截断之后「模型没看见那个字段」与「上下文里没有那个字段」无从分辨。
- [x] **J6 零额外站点请求**：带 / 不带两侧的 **`FakeSite.requests` 逐字相等**
      （先例逐字：roadmap 工作项 5「判据落在 `FakeSite.requests` 上、不落在标志位上」）。
      ⚠️ **不能只判 `trace.opening_request_count`** —— 它取自 `pack.cost.request_count`
      （`opening.py:160` 的 `cost=InjectionCost(result.request_count, …)`，只数 `permission.scope` 那一次 `execute`），
      渲染面直接 `self.client.get(...)` 打一次站点它一点不变。
      `opening_request_count` 只作辅助断言。
      挡：「注入面顺手自己去 `doc.get` 补几个字段」—— ① 层不打站点是 `immediate.py` 写死的规矩。
- [x] **J7 按 key 取块**：构造一个 `blocks()` 顺序被换过的替身（**同样继承
      `ImmediateContext`、只覆盖 `blocks()`**，理由同 J2(b)），断言取到的仍是 ① 档。
      挡：按下标取块（D2 残余风险）。
      ⚠️ **断言形态必须是全量的**：先 `parsed = json.loads(...)`，
      再断言 `isinstance(parsed, dict)` **然后**才取键。M9 之下块 payload 会变成 `list`，
      裸写 `json.loads(...)["doctype"]` 会以 `TypeError` 翻红 —— 又是「红得不是地方」（§8 R5）。
- [x] **J8 调用次数不变**：带 / 不带两侧的 `CallLedger` 条数相等。
      挡：注入被误接成「多起一次模型调用」。
      ⚠️ **它挡不住「每轮重发同一条消息」** —— 重发不改变 `adapter.chat` 次数。那件事由 J9 挡。
- [x] **J9 只注入一次**：多轮剧本（模型先调工具再作答）下，遍历 `ScriptedModel` 收到的
      **每一条**请求载荷，断言含 ① payload 的消息数**恒为 1**。
      挡：「每轮 append 一次」—— 那会让注入把 prompt 成本随轮数放大，而 J1/J8 全绿。
- [x] **J10 死端真的接上了**：`result.opening.immediate` **is** 调用方传进去的那个对象
      （同一性，不是相等）。
      挡：「不传给 `open_session()`，改用 `self.immediate` 直接渲染」—— 那样 J1–J9 全绿，
      而 `opening.py:162` 仍是死端，Goal 2 未兑现。

- [x] **J11 ② 档没有被一起注进去**：夹具的 `actions` **非空**
      （例如 `actions=("permission.scope → 可读 3",)`），断言那些字符串
      **不出现**在注入的消息体里。
      挡：**渲染面把 `blocks()` 的所有块一起序列化** —— 那正是 D2 花一整段否决的「双写」，
      而 J1–J10 对它全部无感（① 确实在里面，条数也没变）。
      ⚠️ 这是与「D1 承重的 `role` 必须有判据」对称的一条：**承重的 `Decision` 必须有判据钉住**。
      ⚠️ 断言形态同 J7：先判类型再取键，别让变异以 `TypeError` 翻红。
变异自查（**每条改坏一处，跑 `tests/unit`，必须由本 plan 新增的判据打红**；
绿的那条说明判据有缺口，**就地补断言并登记为 M13、M14…**，不许放过）：

- [x] **M1** 删掉 `run()` 里插入该条消息的那一行 → 应红（J1/J3）
- [x] **M2** 把插入位置挪到 `user` 提问之后 → 应红（J3）
- [x] **M3** 渲染时不调 `blocks()`，改从 `pack.immediate.document` 忠实重拼同结构 payload
      → 应红（**J2(b)**；⚠️ 只有 J2(b) 的替身杀得掉它，J2(a) 与相等断言都杀不掉）
- [x] **M4** 渲染前对 `fields` 做一次 unwrap → 应红（J4）
- [x] **M5** `explain()` 收了参数但不透传给 `ExplainLoop` → 应红（J1 的产品入口那一例）
- [x] **M6** 渲染时对超长值截断到 **N = 1** 个字符 → 应红（J5）。⚠️ **N 必须写死成 1**：N 若大于 J5 夹具那个 100 KB 值的长度，截断等于没发生，变异会以错误的理由变绿
- [x] **M7** 渲染面里加一次 `client` 请求 → 应红（J6 的 `FakeSite.requests` 比对）
- [x] **M8** 把默认值从 `None` 改成一个空壳
      `assemble(doctype="", name="", fields={}, role="", view="")` → 应红（J1 不带的一侧）
      ⚠️ **不许写成 `ImmediateContext()`** —— 它的 `document` / `role` / `view` 无默认值，
      直接 `TypeError`，会以错误的理由「红」，什么也没证明
- [x] **M9** 按下标取块而不是按 `key` → 应红（J7）
- [x] **M10** 主循环里每轮再 append 一次 ① 消息 → 应红（J9）
- [x] **M11** 把注入那条的 `role` 改成 `"user"` → 应红（J3）
- [x] **M12** `_open()` 不传 `immediate`、改用 `self.immediate` 渲染 → 应红（J10）
- [x] **M13** 渲染面把 `blocks()` **全部块**都序列化进去（① + ②）→ 应红（J11）
- [x] **M14** 渲染前把 `payload["fields"]` **只取前 1 个键**（或丢掉 `role` / `view`）→ 应红（J2(a) 的手写期望字典）。⚠️ 同 M6：取前 N 个键的 N 必须小于小夹具的字段数，否则恒等

#### 变异自查的**实测记录**（2026-08-25，逐条各施加一次，每次跑 `pytest tests/unit -q --tb=line -rf`）

施加方式：对 `agenerp/explain/loop.py` 做一处替换 → 跑 `tests/unit` → **还原**。
基线是 **520 passed**（本 plan 前 503 + 新增 17）。**十四条全红，无一条需要补断言**，因此没有 M15。
「红在哪条断言」逐条指名（行号是 `tests/unit/test_explain_immediate_context.py` 的行）：

| # | 结果 | `pytest` 汇总 | **红的是哪一条断言**（指名） |
|---|---|---|---|
| M1 | **红** | 12 failed, 508 passed | `test_j1_the_product_entry…:252` `assert 3 == 4`（`len(messages)`）；另 11 条经 `sole_injected():174` 报「实得 0 条」 |
| M2 | **红** | 1 failed, 519 passed | `test_j3…:319` `assert 3 == (1 + 1)` —— **下标关系**那一条（`injected_index == opening_index + 1`） |
| M3 | **红** | 1 failed, 519 passed | **只有** `test_j2b…:297` `assert None is True`（`parsed.get(MARK)`）。J2(a) 的相等断言对它全绿 —— 与 plan 的预测逐字吻合 |
| M4 | **红** | 5 failed, 515 passed | `test_j4…:341` `assert False`（`value.startswith(DATA_BOUNDARY_OPEN)`）；连带 J2(a):285 / J5:370 / J7:407 |
| M5 | **红** | 3 failed, 517 passed | `test_j1_the_product_entry…:252` `assert 3 == 4` —— **产品入口那一例**；连带 J5[run_entry]:174 与 J10 的同一性断言 |
| M6 | **红** | 2 failed, 518 passed | `test_j5…:370` `assert '' == '甲甲甲…'` 两个参数化各一次（`inner == HUGE_VALUE`） |
| M7 | **红** | 1 failed, 519 passed | `test_j6…:390` `assert [SiteRequest(…)] == [SiteRequest(…)]` —— **`FakeSite.requests` 那一条**，不是 `opening_request_count`（后者在本变异下确实一点不变，与 J6 的警告吻合） |
| M8 | **红** | 1 failed, 519 passed | `test_j1_no_keyword_at_all…:230` `assert [2] == []` —— **默认值**那条路径（显式 `None` 那例全绿），三例消融的必要性当场兑现 |
| M9 | **红** | 1 failed, 519 passed | `test_j7…:406` `assert False`（`isinstance(parsed, dict)`）。**是断言红，不是 `TypeError`** —— §8 R5 要的形态成立 |
| M10 | **红** | 12 failed, 508 passed | `test_j9…` 经 `sole_injected():174` 报「实得 2 条」；J1 产品入口:252 `assert 5 == 4` |
| M11 | **红** | 1 failed, 519 passed | `test_j3…:318` `assert 'user' == 'system'` —— D1 承重的 `role` 那一条 |
| M12 | **红** | 1 failed, 519 passed | **只有** `test_j10…` 的 `result.opening.immediate is immediate` 同一性断言。J1–J9 对它全绿 —— 与 plan 的预测逐字吻合 |
| M13 | **红** | 3 failed, 517 passed | `test_j11…:480` `assert {'actions', …} == {'doctype', …}`（`set(parsed)`）；连带 J2(a):285 / J7:407。**是断言红，不是 `TypeError`** |
| M14 | **红** | 3 failed, 517 passed | `test_j2a_the_small_fixture_body_equals_a_handwritten_expectation:285` 的**手写期望字典**相等断言；连带 J4:340 `KeyError: 'resolution'` 与 J7:407 |

结论：**M1–M14 全红，且每一条都红在 plan 指定的那条判据上**。
两条「只有一条判据杀得掉」的预测（M3 → 只有 J2(b)；M12 → 只有 J10）实测成立，
说明 J2(b) 的替身与 J10 的同一性断言**都不是冗余**。变异脚本不进仓（一次性自查设施）。

Exit Criteria:

- [x] J1–J11 全部落地且退 0
- [x] M1–M14 逐条**各施加一次**、逐条记录「红 / 绿」；绿的已补断言并登记（M15…）
- [x] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` 退 0
- [x] No owner-doc update required（本 phase 只加判据）

### Phase 3 — 活端点两跑 · owner doc 落点 · 日志

Status: completed
Targets: `docs/architecture/module-boundaries.md`（新增节，节号见 §0.1）· `docs/design/context-and-memory.md` §8.2 ① 行 · `docs/masterplan/STATE.md`（**只追加**）· `docs/logs/2026/08-24.md` · `docs/evidence/p1-immediate/`
Skill: `development-wisdom-gate-prompt.md`（收尾自查）
Prereqs: Phase 2

- Item Types: `Proof | Add | Decision`

- [x] `Proof` **活端点两跑（同一道题，唯一变量是带不带 ①）**：题目取固定测例（成品仓积压
      1,010 台），① 档取活站点上那张销售订单的真实字段表（经 `SiteClient` 只读取回，
      **不手写**）。两跑的 `trace` 与 `cost_ledger` 落 `docs/evidence/p1-immediate/`。
      ⚠️ **一跑不是分布**：结论只覆盖这一道题、这一次；不与 P1.4 的 45,195、
      不与 P1.7 的 58,579 作优劣比较（D-16）
- [x] `Proof` 回填 §6 的 H1–H5「实际」列，**逐条**写吻合 / 不吻合；不吻合的写清前提哪里错了
- [x] `Decision` **roadmap 状态块的处置（起草期已定死，执行期照做）**：
      工作项 10（P1.8）**保持 `todo`**，本 plan 不动
      `docs/backlog/p1-insight-roadmap.md` 的 Work Item Status 块一个字。
      理由：本 plan 是 P1.8 的**前置**而不是它本身，`tests/ui/test_sidebar.py` 未创建、
      也未声称满足（`02-WBS.md:87`）。本 plan 的收口证据只落 `STATE.md` §2 + `docs/logs/`
- [x] `Add` `docs/architecture/module-boundaries.md` **新增一节**（节号见 §0.1；
      起草时最大为 §7.11，`module-boundaries.md:868`）：写 D1/D2/D3 三条裁定与被否决的备选、
      J1–J11 的判据落点、以及「① 层不查权限」这条边界的转述与它的 successor
- [x] `Add` `docs/design/context-and-memory.md` **§8.2 ① 行只补落点指针**
      （「前端注入」那格后面补上「循环侧接入点 `agenerp/explain/loop.py`，见 §7.x」）。
      ⚠️ **规则 1「① 不可裁剪」那段一个字不改**
- [x] `Add` `docs/masterplan/STATE.md` §2 追加证据行（时间 · WBS 行 ID · 命令→退出码 · sha · 下一项）；
      §3 追加 needs-human：若本 plan 期间发现任何越权边界（例如活跑要求写站点），逐条记
- [x] `Add` `docs/logs/2026/08-24.md` 追加一条

Exit Criteria:

- [x] 六条验证命令原文 + 退出码写进 `## Closure`（`check_expected_red && pytest tests/unit` ·
      `pytest tests/context` · `pytest tests/tools` · `pytest tests/routing` ·
      `pytest tests/contracts` · `ruff check ...`）
- [x] H1–H5 逐条有「实际」（§5 的 blocked 路径下，H4 / H5 写 `blocked（原因）` + 一条 needs-human，视为满足）
- [x] 落点节存在；§8.2 ① 行只多了指针（`git diff` 可证只增不改）
- [x] `docs/backlog/p1-insight-roadmap.md` 的 Work Item Status 块 `git diff` **无输出**
- [x] `docs/logs/` 已更新

## 8. 风险

**R1 · ① 层不查权限，而 P1.8 的调用方是浏览器里的登录用户（已确认的结构性风险，不是猜测）**

`immediate.py` 模块头规矩 1 逐字：「当前单据、角色、视图全由调用方给。这一层不打站点、
不查权限」。本 plan 把这条口径原样带进循环：**谁调 `explain()`，谁就能把任意字段表送进模型**。
今天唯一的调用方是本仓自己的判据与脚本，风险为零；
**P1.8 一旦让浏览器发起解释，调用方就变成了外部输入** —— 那时「这些字段是不是这个用户有权看的」
必须有人回答。
- 本 plan 的处置：**不在这里补权限校验**（补在 ① 层等于推翻 P1.2 的分层裁定），
  而是把这条写进落点节，并作为本批第二个 plan（承载面）的**输入约束**逐字交接。
- 非阻塞理由：本 plan 不新增任何外部调用面。

**R2 · 不裁 → 超大单据的失败形态在端点侧而不是本仓侧**

D3 已裁定。残余风险照实登记：一张超大单据会让端点报错（形态未测），
而不是本仓抛一个说得清的异常。重开事件写在 §11。

**R3 · 三条 `system` 消息的端点行为**

D1 已说明；Phase 3 的活跑会再撞一次，结果照实记（吻合与否都记）。

**R4 · 判据可能"自证"**

J2 若写成「两边都调 `blocks()` 再比」，等于让判据给自己判卷。
正确写法：**从 `messages` 里把注入那条解析回来**，与**独立构造**的期望值比；
且 J2(b) 的替身必须产出「朴素重拼产不出来」的东西，否则 M3 会绿。
这条写进判据文件的模块头，收口审计逐字核。

**R5 · 变异自查可能"看起来红"而实际是别的原因红**

M8 已因此改过一次写法（`ImmediateContext()` 会 `TypeError`）。
执行期施加每条变异后，**必须核对红的是哪一条断言**，不是「跑出来非 0 就算数」。

## 9. Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，2026-08-24）
  because 八条 BLOCKING：① §1.1/§1.2 关于「零调用方 / 零读者」的基线错了
  （`tests/tools/test_navigation.py:319` 有调用、`:328` 有读者）；② H1 的预测被它自己的命令当场证伪；
  ③ J6 判在 `opening_request_count` 上挡不住 M7（渲染面直接打站点它不变）；
  ④ J2 的「逐字相等」杀不掉 M3（朴素重拼产出字节相同的 JSON）；
  ⑤ 存在一种全绿的假实现（每轮重发 ① 消息），J8 对它是假保护；
  ⑥ D1 承重的 `role == "system"` 没有任何判据钉住；
  ⑦ 没有判据证明 `opening.py:162` 那条死端真的被接上；
  ⑧ M5 的红绿取决于 J1 走哪个入口而 plan 没写，M8 那条变异根本不可执行。
  另有九条 NON-BLOCKING（D3 自相矛盾、`immediate_budget` 近乎空转、`trim` 不是方法、
  J4 后半句不可断言、两处行号偏了、roadmap 状态块处置未写、缺 routing 基线数、
  缺 `tests/contracts`、§10 把节号写死）。
- 处置（iteration 1 → 本稿）：**十七条全部就地改**，无一降级为 follow-up。
  其中三条改动改变了 plan 的形状，逐条记：
  (a) **删掉 `immediate_budget` 参数**（NON-BLOCKING 第 10 条）—— 它在本期没有真实调用方，
  正是 §1.1 批评的「装配得出来、送不进去」；「① 不可裁」改由 J5「不截断」兑现，D3 重写；
  (b) **J 清单由 8 条增到 10 条**（新增 J9 只注入一次、J10 死端接上），
  变异由 9 条增到 12 条；
  (c) **§1.1 / §1.2 的措辞从「零调用方 / 零读者」收窄为「产品路径上零调用方 / 零读者」**，
  并把那两条已有判据点名写进基线与 Non-Goals 7（它们是本 plan 的护栏）。
- Independent draft review iteration 2: **needs revision**（独立子代理，fresh session，2026-08-24）
  because 两条 BLOCKING —— 两种能通过 J1–J10 全绿的假实现：
  ① **① + ② 两块一起序列化**（D2 花一整段否决的「双写」没有任何判据钉住 ——
  与 iteration 1 的第 ⑥ 条「D1 承重的 `role` 没判据」是**对称的同一种缺陷**）；
  ② **截的是字段集合而不是字段值**（J5 只钉一个超长 value，J2 只钉「随夹具变」与「标记键在」，
  于是 `fields` 被截成前 N 个键、或 `role` / `view` 被丢掉，全绿而 Goal 5 落空）。
  另有四条 NON-BLOCKING：J6 的行号偏一行（`opening.py:161` → `:160`）·
  J2(b)/J7 的替身若写成鸭子类型桩会让 M3/M9 以 `AttributeError` 翻红（红得不是地方）·
  J1 没写消融的「不带」那侧是省略参数还是显式 `None`（M8 变的是**默认值**，写错就恒绿）·
  J1/J3/J5 没写 `messages` 的观测面（它是 `run()` 的局部变量，`ExplainResult` 上没有）·
  §10 的「H1–H5 逐条有实际」与 §5 允许的 blocked 路径互斥 · Phase 1 的 uniform item type 与末项标签不符。
  ⚠️ 评审同时**逐条复核并确认**：iteration 1 的 17 条修复**全部真的落进正文**（不是只写在 §9）；
  D3 删掉 `immediate_budget` 是**正当替换**（那个参数在本期没有可达语义）；
  M1/M2/M4/M6/M7/M10/M11/M12 八条**因正确的理由**被判据打红。
- 处置（iteration 2 → 本稿）：**八条全部就地改**，无一降级为 follow-up。
  形状改动两处：**新增 J11**（② 档没被一起注进去，钉住 D2）与
  **J2(a) 增加一份手写期望字典**（钉住 payload 保真度，且按 §8 R4 手写、不许回调 `blocks()` 自证）；
  变异随之由 12 条增到 **14 条**（M13 全块序列化 / M14 截字段集合）。
  另把 J1 的消融由两例改成**三例**（省略参数 / 显式 `None` / 给值），使 M8 真的测得到默认值。
- Independent draft review iteration 3: **acceptable as-is**（独立子代理，fresh session，2026-08-24）
  after 新增 J11 与 J2(a) 的手写期望字典、变异增至 M14、J1 消融改为三例。
  评审侧**逐条复核并确认**：iteration 2 的八条修复全部落进正文（不是只写在 §9）；
  §1 / §7 的全部 file:line 与 §1.6 的五条基线数在 sha `e3de756` 上复现；
  H1 的 grep 实跑回的正是预测的三类，**不再自我证伪**；
  且**构造不出第三种能通过 J1–J11 的假实现**。无红线违规、无 Anti-Slacking 违规。
  另出六条 NON-BLOCKING（M6 / M14 的截断长度 N 未写死会让变异以错误理由变绿 ·
  J1 未指明三例中哪一例走产品入口 · J7 / J11 的断言形态若裸取键会以 `TypeError` 翻红 ·
  「四条基线数」实为五条、§0「六处」实为七处 · J11 位置 · §9 与 status 待回填），
  **六条已在本稿全部就地改**（N 写死为 1、小夹具至少 2 个字段、产品入口取 ③、
  断言先判类型再取键、计数改准、J11 移到 J10 之后）。
- **共识达成**：iteration 3 判 `acceptable as-is`，`Plan Status` 由 `draft` 改为 `active`。

## 10. Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（§7.x 落点节 + §8.2 ① 行指针）
- [x] verification has run：六条命令原文与退出码写进 `## Closure`
- [x] scoped verification is not conflated with full verification —— 若未跑 `pytest tests -q -m "not live"`
      或未过 CI，逐字写「verification scope limited」并说明残余风险
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（§9）
- [x] text consistency verified：顶部 status、各 phase status、exit criteria、gates、日志一致
- [ ] closure audit was independent —— **未满足，照实留白**：本轮无独立子代理可用（执行者不自证）。先例 P1.7 同形态：收口当轮留白，由 mission-driver 另派 fresh session 的独立审计器补做。**在补做之前，本 plan 的收口结论只到「执行者自验全绿」为止。**
- [x] closure evidence exists in files
- [x] **红线自证**：`git diff --stat` 对 `tests/gates/` `.github/workflows/` `missions/`
      `docs/masterplan/DECISIONS.md` 四个 pathspec **无输出**；
      `docs/masterplan/STATE.md` 只增不改（`git diff -- docs/masterplan/STATE.md | grep '^-'` 无输出）
- [x] **§6 的 H1–H5 逐条有「实际」**，且预测列一个字未改。
      ⚠️ **§5 允许的 blocked 路径下**（拿不到 `DASHSCOPE_API_KEY` / 活栈 / 种子数据之一）：
      H4 / H5 的「实际」列写 `blocked（原因）`，并在 `STATE.md` §3 有对应的 needs-human 行 ——
      **这算满足本条门禁**。不许为了填满表格写一个没跑出来的数
- [x] **M1–M14 逐条有红 / 绿记录**，且红的那条**指名是哪一条断言红的**
- [x] **`docs/backlog/p1-insight-roadmap.md` 的 Work Item Status 块未被改动**

## 11. Deferred But Adjudicated

### ② 档（已执行动作）的显式注入

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: D2 已裁定 —— 同一批事实在 `messages` 里已在场，重复注入会双写。
- Successor Required: `no`。重开事件：**当循环开始压缩 / 摘要 `messages` 里的工具结果时**
  （那时 ② 档就不再"已在场"了）。

### ① 档的上下文预算与裁剪接入点

- Classification: `optimization candidate`
- Why Not Blocking Closure: D3 已裁定不发明数字（D-16），也不加零调用方的开关。
  `trim()` 与 `ContextBudgetExceeded` 的行为已由 `tests/context/test_immediate.py`（53 passed）覆盖，
  缺的只是循环侧的接入点与一个有出处的数字。
- Successor Required: `yes`。重开事件（**两个都要满足**）：
  ① 承载面 plan 出现真实调用方（浏览器传来的单据可能任意大）；
  ② P1.7 Deferred「成本的多次采样与分布」产出过一次实测分布。

### ① 档的权限校验

- Classification: `watch-only residual`
- Why Not Blocking Closure: 今天没有外部调用面（§8 R1）。
- Successor Required: `yes`。重开事件：**P1.8 让浏览器发起解释的那一刻**。
  交接对象：本批第二个 plan `2026-08-24-2311-2-desk-embed-carrier-decision.md`。

## Closure

Status Note: **三个 Phase 全部执行完毕，`Plan Status: completed`。收口结论到「执行者自验全绿」为止 ——
`closure audit was independent` **未满足，照实留白**（见下）。**

**实现与判据的提交 sha：`b112d08`**（基线 sha `e3de756`）。
本节的 sha 由**紧随其后的一个纯文档提交**回填（sha 不可能写进它自己命名的那个提交里；
回填提交的 sha 见 `git log`，它只改本 plan / `docs/logs/2026/08-25.md` / `docs/masterplan/STATE.md` 三个文件）。
`b112d08` 改动 12 个文件：
`agenerp/explain/loop.py`（唯一改动的产品文件）· `tests/unit/test_explain_immediate_context.py`（新建）·
`docs/architecture/module-boundaries.md`（新增 §7.12）· `docs/design/context-and-memory.md`（§8.2 ① 行加指针）·
`docs/evidence/p1-immediate/`（5 个文件，新建）· `docs/logs/2026/08-25.md`（新建）·
`docs/masterplan/STATE.md`（只追加）· 本 plan 文件。

### 六条验证命令的原文与退出码（同一轮，2026-08-25）

| # | 命令原文 | 退出码 | 输出 |
|---|---|---|---|
| 1 | `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | **0** | `门禁 11 项：预期红 0，绿 11，跳过 0` · `✅ 与预期红名单完全一致` · **`520 passed`**（基线 503，**只增不减**，+17） |
| 2 | `python3 -m pytest tests/context -q` | **0** | `53 passed` —— **逐字不变** |
| 3 | `python3 -m pytest tests/tools -q` | **0** | `81 passed, 12 skipped` —— **逐字不变** |
| 4 | `python3 -m pytest tests/routing -q` | **0** | `164 passed, 1 skipped` —— **逐字不变** |
| 5 | `python3 -m pytest tests/contracts -q` | **0** | `151 passed` —— **逐字不变** |
| 6 | `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | **0** | `All checks passed!` |

`tools/gates/expected-red.txt` **本轮无需划减** —— 名单里预期红为 0 条，无「名单内转绿」可划。

**verification scope limited**（逐字，按 Closure Gate 第 4 条要求）：
上面六条**全部在本机跑**。**未跑** `pytest tests -q -m "not live"`，**未过 CI 服务端复跑**。
残余风险：`tests/gates/` 的 live 语义（带凭据的活站点门禁）与 CI 上的复跑本轮**没有验证过**；
本 plan 只新增了 `tests/unit` 下的判据与 `agenerp/explain/loop.py` 的一个可选关键字参数
（默认 `None`，不给就与本 plan 之前逐字同行为），因此**预期**不影响那两层 —— 但**预期不是证据**。

### 红线自证

- `git status --porcelain -- tests/gates/ .github/workflows/ missions/ docs/masterplan/DECISIONS.md`
  → **无输出**（红线 1 / 2 / 3）。
- `docs/masterplan/STATE.md` **只增不改**（红线 5）—— 判据换成了**逐行子序列检查**，
  不是 `grep '^-[^-]'`：⚠️ **那条 grep 有盲区**，markdown 项目符号行本身以 `-` 开头，
  在 diff 里显示成 `--`，会被 `[^-]` 排除掉，于是「删掉一整条 bullet」它看不见。
  实际判据：把 `git show e3de756:docs/masterplan/STATE.md` 的 **465 行**逐行拿去在当前文件里
  按顺序匹配 —— **未在场的条数 = 0**，即基线每一行都原样、按原顺序仍在，当前 **479 行**，
  净增 14 行全是本 plan 追加的。**这条盲区值得记住**：以后判「只增不改」不许再用那条 grep。
- `git status --porcelain -- docs/backlog/p1-insight-roadmap.md` → **无输出**（Work Item Status 块未被改动）。
- 未写入证据仓 `${XM_PATH}`（红线 6）；未生成任何运行时 Server Script（红线 7）；未改项目名 / 包名（红线 4）。

### `## 0.1` / `§6` / 变异记录的落点

- §0.1：七处基线**逐条实读**已填，落点节号**落定为 §7.12**。七处**全部与起草期一致**，无差异可记。
- §6：H1–H5 的「实际」列**逐条已填**，**预测列一个字未改**。H1/H2/H3/H4 **吻合**，
  H5 **部分吻合且写清了前提哪里错了**（不是 blocked 路径 —— 活跑真跑出来了）。
- Phase 2 的 `#### 变异自查的实测记录`：M1–M14 **逐条有红 / 绿**，且逐条**指名是哪一条断言红的**。
  十四条**全红**，无一条需要补断言，因此**没有 M15**。

### 两处与 plan 字面不一致、按实读执行的地方（照实记，不改预测）

1. **`DASHSCOPE_API_KEY` 的位置**：§5 写在 `.env`，实读已迁到 `~/.config/agenerp/secrets.env`
   （0600，仓库目录之外；用户 2026-08-24 明示 `.env` 不放敏感信息）。
   **因此 Phase 3 的活跑没有走 §5 的 blocked 路径**，H4 / H5 都跑出了真数。
2. **日志文件名**：Phase 3 写 `docs/logs/2026/08-24.md`，实际执行日是 **2026-08-25**，
   按 `docs/logs/00-log-writing-guide.md` 的「一天一个文件」落进 `docs/logs/2026/08-25.md`。

两条都已同步登记进 `docs/masterplan/STATE.md` §3 的 `[open] 2026-08-25T00:35Z` 第 ③ 项。

Closure Audit Evidence:

- Auditor / Agent: **无 —— 本轮未做独立关闭审计。** 本轮环境不具备独立子代理（执行者不自证），
  照实留白，不降级成「执行者自审即通过」。先例同形态：P1.7 收口当轮留白，
  由 mission-driver 另派 fresh session 的独立审计器补做（见 `docs/logs/2026/08-24.md`）。
  **在补做之前，本 plan 的收口结论只到「执行者自验全绿」为止。**
- Evidence: 六条命令的退出码与输出（上表）· `docs/evidence/p1-immediate/`（活端点两跑 + README 的
  「证明了什么 / 没证明什么」）· Phase 2 的 M1–M14 逐条红/绿记录 ·
  `docs/architecture/module-boundaries.md` §7.12 · `docs/logs/2026/08-25.md` ·
  `docs/masterplan/STATE.md` §2 的 `2026-08-25T00:35Z` 行与 §3 的 `[open] 2026-08-25T00:35Z` 行 ·
  实现提交 `b112d08`（+ 一个纯文档回填提交）。

Follow-up:

- **（必做）独立关闭审计补做** —— 唯一未勾的 Closure Gate。由 fresh session、不带实现上下文、
  非本 plan 执行者的审计器做，重点核三件事：① §8 R4 的自证防线（J2 的期望值是否真的手写、
  没有回调 `blocks()`）；② M1–M14 的「红在哪条断言」是否与记录一致（可原样复跑）；
  ③ §7.12 里对活端点两跑的「没证明什么」是否有一处越界成了优劣比较。
- **（下一项）本批第二个 plan** `docs/plans/p1-insight/2026-08-24-2311-2-desk-embed-carrier-decision.md`
  （P1.8 承载面）。**必须串行**：它也要往 `module-boundaries.md` 新增落点节（**最大号现为 §7.12，顺延取 §7.13**）、
  也要往 `STATE.md` 追加、也要写当日日志。它的**输入约束**已由 §7.12 逐字交接：**① 层不查权限**。
- **（不做）工作项 10 的状态位** —— 保持 `todo`，本 plan 是它的前置而不是它本身。裁定见 Phase 3。
