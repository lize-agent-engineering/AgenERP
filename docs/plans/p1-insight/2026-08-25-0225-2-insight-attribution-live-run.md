# 洞察 Agent 归因的**首次活端点实跑** —— 判结构化事实，不判文本质量

> Plan Status: completed
> Mission: p1-insight
> Work Item: 7. 巡检器（纯规则引擎）+ 洞察 Agent（归因）（P1.5，见 D-15）—— **本 plan 是它的第 2 个 plan**，
> 结清那一行 ⚠️ 里逐字写着的「**归因那一半也没有在活端点上跑过 —— 不得读成「洞察 Agent 已验证」**」
> Last Reviewed: 2026-08-25
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 7 收口记录的两条 ⚠️ ·
> `docs/architecture/module-boundaries.md` §7.9 · `agenerp/insight/__init__.py` 模块头
> Related: [`2026-08-24-1755-2-inspector-and-insight-agent.md`](./2026-08-24-1755-2-inspector-and-insight-agent.md)（P1.5 本体，`completed`）·
> [`2026-08-25-0225-1-answer-judge-v0.md`](./2026-08-25-0225-1-answer-judge-v0.md)（**本批第 1 个 plan，硬前置**）·
> [`2026-08-24-2109-1-industry-pack-v0-discrete.md`](./2026-08-24-2109-1-industry-pack-v0-discrete.md)（行业包，本 plan 的规则来源）
> Audit: required
> Execution Order: **2 / 2**（**必须在 `…-0225-1` 之后**，Prereq 见 §7 Phase 1）

## 0. 执行前必做：重取基线

1. `git log -1 --format=%H` / `git status --porcelain`（起草期 `f8b2d15015e80dda3112123315ef02d28bee564f`；
   ⚠️ `git status --porcelain` **不是无输出** —— 有本批两个 plan 文件未入仓。
   **判据收窄成：除本批两个 plan 文件外无输出**，与本批第 1 个 plan §0.1 第 1 条同口径）
2. **本批第 1 个 plan `…-0225-1` 的 `Plan Status` 与它 §6 H2 的实际列** —— 见 §7 Phase 1 的**前置闸**
3. `docs/architecture/module-boundaries.md` `7.x` 族最大节号（起草期 **§7.14**；`…-0225-1` 预定占 **§7.15**，
   本 plan 预定落 **§7.16**；**以开工时实读为准**，被占用就顺延）
4. 活栈状态：`AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml ps`
   —— 六个服务 healthy，`agenerp-frontend-1` 映射 `127.0.0.1:18080->8080/tcp`
5. `~/.config/agenerp/secrets.env` 存在且 `0600`，含 `DASHSCOPE_API_KEY`
6. 八条基线命令的开工数字（起草期见 §1.1）

### 0.1 执行期重取基线的**实读结果**

1. `git log -1 --format=%H` → **`36112c2905063b69ff5820971dd3bac863ae3cdb`**（起草期是 `f8b2d15`；
   其后本批第 1 个 plan `…-0225-1` 已落地并回填了收口 sha，故基线前移，照实记）。
   `git status --porcelain` → **无输出**（**比起草期判据更严**：起草期把判据收窄成
   「除本批两个 plan 文件外无输出」，执行期两个 plan 文件都已入仓，所以是真正的空输出）。
2. **前置闸两条合取，逐条实读，均满足**：
   - **(a)** `grep -n "^> Plan Status" docs/plans/p1-insight/2026-08-25-0225-1-answer-judge-v0.md`
     → `3:> Plan Status: completed`，**逐字 `completed`**。
   - **(b)** 按**内容**认那一格（承载「① 5 条负例逐条三分类精确匹配 且 ② 正例 ≥ 17/19」的，
     实为该 plan §6 的 **H2** 那一行，`…-0225-1.md:325`）：「实际」列**逐字以「吻合」开头**
     ——「**吻合，且是在第 1 轮**（修订次数 **0**，全量轮数 **1**）……① 5 条负例逐条三分类精确 **5/5**；
     ② 19 条正例保住 **19/19**……`meets_acceptance = true`」。⇒ **(b) 满足**，
     且**不属于**起草期预留的那种「第 2 轮才达标 ⇒ 该格记不吻合但口径其实达成」的情形
     —— 它第 1 轮就达标，那一格本身就是「吻合」。
   ⇒ 两条合取成立，**本 plan 开工**。
3. `docs/architecture/module-boundaries.md` 的 `7.x` 族最大节号实读为 **§7.15**
   （`…-0225-1` 已占用，与起草期预测一致）⇒ 本 plan 落 **§7.16**，无需顺延。
4. `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml ps` →
   九个容器全部 `Up 19 hours`，其中**六个 healthy**（`backend` / `db` / `frontend` /
   `redis-cache` / `redis-queue` / `websocket`），另三个（`queue-long` / `queue-short` /
   `scheduler`）无 healthcheck 只报 `Up`；`agenerp-frontend-1` 映射
   **`127.0.0.1:18080->8080/tcp`**。⇒ 与起草期逐字一致，**不需要 `up -d --wait`**（栈已在跑）。
5. `ls -l ~/.config/agenerp/secrets.env` → `-rw-------@ 1 lize staff 305 Aug 24 18:21`（**0600**），
   `grep -c DASHSCOPE_API_KEY` → **1**。
6. **八条基线命令的开工数字**（`36112c2`，工作区干净）：
   `check_expected_red.py` **exit 0**（`门禁 11 项：预期红 0，绿 11，跳过 0`）·
   `tests/unit` **599 passed** · `tests/contracts` **151 passed** · `tests/tools` **81 passed, 12 skipped** ·
   `tests/routing` **167 passed, 1 skipped** · `tests/context` **53 passed** · `tests/experiments` **10 passed** ·
   `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
   **exit 0**。
   ⚠️ **与 §1.1 起草期数字的差，全部来自 `…-0225-1` 的落地，不是本 plan 的**：
   `tests/unit` **540 → 599**（+59，`test_answer_judge.py`）· `tests/routing` **164 → 167**
   （+3，`agenerp/judging/` 三个产品模块）。**四个不变面（contracts / tools / context / experiments）
   逐字未变** ⇒ H6 的对照基线照旧，H7 的对照基线按本条的 **167**（起草期已写死「按开工基线对照，不按 164」）。

## 1. Current Baseline

### 1.1 起草期实读的八条命令（`f8b2d15`，工作区干净）

`check_expected_red.py` **exit 0**（`门禁 11 项：预期红 0，绿 11，跳过 0`）·
`tests/unit` **540 passed** · `tests/contracts` **151 passed** · `tests/tools` **81 passed, 12 skipped** ·
`tests/routing` **164 passed, 1 skipped** · `tests/context` **53 passed** · `tests/experiments` **10 passed** ·
`ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` **exit 0**。

### 1.2 归因这一半**从未在活端点上跑过**

P1.5 落账逐字（roadmap 工作项 7）：「**活站点巡检一次 → exit 0**」——
那是**巡检器**（`agenerp/inspection/`，**零 LLM**）在活站点上跑过一次。
同一行另一句逐字：「**归因那一半也没有在活端点上跑过** —— 不得读成「洞察 Agent 已验证」」。

⇒ `agenerp/insight/attribution.py` 的 `attribute()` / `attribute_all()` 今天的全部证据
都来自 `tests/unit/test_insight_attribution.py`（9 条，走假件）。
**真模型 + 真站点这条组合，本仓一次都没跑过。**

### 1.3 归因链上的既有接缝（本 plan 不新建，只调用）

- `agenerp.inspection.inspect_site(rules, client) -> InspectionReport`（只读 REST，零 LLM）
- `agenerp.packs.load_pack("discrete") -> Pack`（三条规则，每条带 `test_case`）
- `agenerp.insight.attribute_all(report, **kwargs) -> tuple[Attribution, ...]`，
  内部逐条走 `attribute(hit, ...)` → **`agenerp.explain.explain(question, task_class="…")`**，
  **不另起循环**（D-15 / §7.9）
- `Attribution` 带 `hit` / `question` / `answer` / `accepted` / `result`；
  `result.cost_ledger` 是 P1.7 的账本；`hits_unchanged(report, attributions)` 断言命中未被改写
- `ensure_unchanged()` 在每次 `attribute()` 收尾时校验 `hit` 逐字未变（`InsightBoundaryError`）
- `agenerp/insight/attribution.py:41` 的 `TASK_CLASS = "explain"` ⇒ 归因走的是 **`explain` 档**，
  `STATE.md` §3 里那条关于 `lineage` 档的残余风险**对本 plan 不适用**（收口审计不必重推）

### 1.3b 「只读」在本仓**不等于「只发 GET」**（起草期实读，决定了本 plan 的判据形状）

`explain()` 开场**无条件**注入 `permission.scope`（`agenerp/orchestration/opening.py:143`），
它经 `agenerp/tools/site_scope.py:150-153` **逐个 DocType** 调
`session.call_method("frappe.client.has_permission", …)`，
而 `agenerp/site.py:311-334` 的 `call_method` 实现是 **`POST /api/method/<dotted.path>`**。
`agenerp/insight/attribution.py` 默认 `doctypes=None` ⇒ 走发现路径，
`site_scope.py` 自己的注释逐字写着本站点业务 DocType **239 个**。
`system.overview`（`site_scope.py:79`）同理 POST `frappe.client.get_count`。

⇒ **「全程零 `POST`」这句话是错的**，一个完全只读的会话也会发出大量 `POST`。
本 plan 的只读判据因此**按端点语义定义，不按 HTTP 动词定义**，白名单写死在 §6 H8 与 §7 Phase 1。
⚠️ **这是起草期实读改准的一处** —— 上一版把"零 `POST`"写进了 Non-Goals、见即停、H8、判据与变异
五个地方，照那个跑会在第二个请求上误停机。

### 1.4 起草期已知的**两条会在活跑里现形**的事（不是新发现，是预登记）

- **(a) `HRD-PACK-5K` 会被 L1 门禁当成"问题点名的单据"**。P1.5 落账逐字：
  「D3 的残余风险实测确认：命中 `subject` 里的物料号 `HRD-PACK-5K` 是三段全大写数字，
  落进 `gate.py` 的 `DOC_NAME`」。**误报方向是更严**，本 plan **不擅自绕开**（§3 Non-Goals 4）。
- **(b) 活站点上 `discrete` 包只命中一条**。P1.6 落账 H4 实测：
  `finished-goods-backlog` 命中 `1010.0`（与离线逐字一致）· `subcontracting-issued-not-received` **零命中** ·
  `closed-order-short-delivered` **离线命中 10、站点零命中**（`Sales Order.status` 是
  `To Deliver and Bill` 而不是 `Closed`，已记 `docs/bugs/02-…`，归属**种子装载面**，
  `STATE.md` §3 `[open] 2026-08-24T21:40Z`）。
  ⇒ **本 plan 预期只有 1 条命中可归因**，这不是缺陷，是已登记的站点现状。
  **本 plan 不修它、不代人处置、不改规则去凑命中**（那是照答案写规则）。

### 1.5 判定器的适用边界（**本 plan 最重要的一条自我限制**）

本批第 1 个 plan 交付的判定器，其**已验证适用范围只有 P1.0 那一道题**（`…-0225-1` §1.4）。
**归因文本是另一个题族**（问的是"这条命中要不要紧、为什么"，不是"成品仓怎么回事"）。
⇒ 把判定器用在归因文本上**属外推**，按 **D-16** 只能写成
「**据判定器，判为 X，待复验**」，**不能**写成「归因质量已验证」。
本 plan 的**判据一条都不落在判定器的标签取值上**（§2 目标 3 / §6.1 O1）。

## 2. Goals

1. **洞察 Agent 的归因第一次在真模型 + 真站点上跑通**，一次实跑的完整轨迹落
   `docs/evidence/p1-insight-live/`（含命中、题面、答案全文、门禁判定、逐次账本、端点原始 usage）。
2. 这一跑被**结构化事实**判住（不是"跑通就算"）：命中逐字未被改写 · 门禁判定有出处 ·
   账本条数 == `chat()` 被调次数 · usage 三项 > 0 · 取证轨迹非空且工具调用可枚举。
3. **判定器的标签取值**不构成任何通过 / 失败条件（§1.5）。
   ⚠️ **精确措辞，不是上一版那句"不进任何 Exit Criteria"**：本 plan 确实要求
   「**判定记录存在且可复现**」（那是**证据卫生**：一份自由文本证据不附判定记录，
   正是 roadmap 那一节要挡的东西），但**记录里那个标签是 `correct` 还是 `incomplete`，
   不改变本 plan 的任何通过与否**。
4. §1.4 的两件已知事（L1 误判物料号 · 站点只命中一条）**在活跑里被逐条确认或证伪**，
   结果照实记 —— 证伪了就说明起草期的登记有误，同样照实记。

## 3. Non-Goals

1. **不判归因文本的质量。** §1.5 已说清；判定器输出只是观测。
2. **不改 `agenerp/insight/**` 与 `agenerp/inspection/**` 的任何行为**（本 plan 是一次**验证**，
   不是一次改造）。发现缺陷 → 按 `Fix` 处置或登记，**但改行为要另起 plan**，见 §7 Phase 3 的分流规则。
3. **不修 `docs/bugs/02-…`（站点 `Sales Order.status`）**，它归种子装载面且已在 needs-human 队列。
4. **不绕开 L1 把 `HRD-PACK-5K` 从 `DOC_NAME` 里摘出去**（§1.4a：误报方向更严）。
5. **不对活站点做任何写**——「写」按**端点语义**定义，不按 HTTP 动词（§1.3b）。
   白名单（**起草期写死**）：任意 `GET` · `POST /api/method/login` ·
   `POST /api/method/frappe.client.has_permission` · `POST /api/method/frappe.client.get_count`。
   白名单之外的 `POST` / `PUT` / `DELETE`（尤其任何 `/api/resource/**` 的写）**一律停机**。
6. **不创建 / 不修改 `tests/gates/**`**（红线 1），不声称满足任何 WBS 🔴 验收件。
7. **不新增 `tests/` 顶层目录**（CI ⑦ 会红，改它属红线 2）。
8. **不设成本阈值、不加拦截分支**（D-18）。
9. **不改 roadmap 工作项 7 的状态行**（它已 `done`；本 plan 结清的是那一行 ⚠️ 点名的缺口）。

## 4. Task Route

- Type: `verification or audit work`（一次实测），含少量 `Add`（实验脚本 + 离线判据）
- Owner Docs: `docs/architecture/module-boundaries.md`（落点节 **§7.16**，新增；
  并**改准** §7.9 里"归因未在活端点跑过"那一句的失效归属）·
  `docs/design/agents-and-roles.md` §5.1（**只补落点指针**，不改结论）
- Skill Selection Basis: 主体是"跑一次并把它判住"，注册表里没有对口的实现类技能；
  评审用 `plan-audit-prompt.md`、收口用 `closure-audit-prompt.md`（均独立子代理）。各 Phase 记 `Skill: none`。
- Protected Areas 复核：本 plan 触及「`docs/masterplan/` 其余文件」一行，且**只以该行明文许可的
  追加方式**（`STATE.md` 追加证据行，numstat 删除列为 0）。站点写面：**本 plan 不调
  `create_doc` / `ensure_doc` / `submit_doc` / `delete_custom_field` / `drop_columns` 中的任何一个**，
  `call_method` 只经 §3 Non-Goals 5 的只读方法白名单。
  ⚠️ **照实说清**：Protected Areas 的两条站点写行**没有**枚举 `call_method`（POST）与
  `submit_doc`（PUT），所以"表里没有这一行"不等于"没有写面"——
  本 plan 的结论建立在**白名单 + 请求记录器**上，不建立在那张表的完备性上；
  不动 `tests/gates/**` / `.github/workflows/**` / `missions/*.json` / `DECISIONS.md` / 证据仓。

## 5. Infrastructure And Config Prereqs

- **活栈必须先起**：`AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`
  （**端口 18080**：8080 被本机另一套常驻 ERPNext 栈占着）
- 站点侧 env 三个必须由命令给：`AGENERP_SITE=frontend` · `AGENERP_SITE_URL=http://127.0.0.1:18080` ·
  `AGENERP_ADMIN_PASSWORD=admin`（产品代码不内置口令默认值）
- 模型侧：`~/.config/agenerp/secrets.env` 的 `DASHSCOPE_API_KEY` + `AGENERP_LLM_*`
- **不需要**重跑种子装载链（站点已装载；`down -v` 会丢整站数据，**见即停**）

### 5.1 见即停清单（起草期写死）

1. 任何**白名单外**的站点请求（§3 Non-Goals 5 那份白名单）——
   **停**。特别地：任何 `POST|PUT|DELETE /api/resource/**`、
   任何白名单外方法名的 `POST /api/method/*`、任何 `create_doc` / `ensure_doc` /
   `submit_doc` / `delete_custom_field` / `drop_columns` 调用
2. `docker compose … down -v` / `bench restore` / 任何重装种子的动作 —— **停**
3. 任何要改 `tests/gates/**` / `.github/workflows/**` / `missions/*.json` / `docs/masterplan/` 已有行的动作 —— **停**
4. 任何要改 `agenerp/insight/**` 或 `agenerp/inspection/**` **行为**的动作 —— **停**，按 §7 Phase 3 分流
5. 任何"改规则让它多命中一条"的念头 —— **停**（照答案写规则，§1.4b）
6. 用 `git checkout -- <file>` 还原变异 —— **停**，改用文件级备份
7. 单次实跑的模型调用超过 **12** 次 —— **停**并照实记（§6 H4；
   **不是 40** —— `loop.py:61` `MAX_TURNS = 25` 每轮一次 `chat()`，40 按构造不可达，
   写 40 等于给了一条永不触发的假闸）

## 6. 开工前写死的假设（硬约束②）

**预测列一个字不改；不吻合的照实记并说清前提哪里错了。**

| # | 假设（预测，逐字） | 怎么测 | 实际 |
|---|---|---|---|
| **H1** | 活站点上 `discrete` 包**恰好命中 1 条**：`discrete/finished-goods-backlog`，量 **1010.0**，`HRD-PACK-5K` / `成品仓 - HRD`；另两条零命中（§1.4b） | `inspect_site(load_pack("discrete").rules, client_from_env("frontend"))` | **吻合，逐格命中预测。** 命令：`python3 -m tools.experiments.p1_insight_live.run --inspect-only`（exit **0**，2026-08-25，零 LLM、零 token）。活站点上 `discrete` 包**恰好命中 1 条**：`discrete/finished-goods-backlog`，`quantity_name = on_hand`、**`quantity = 1010.0`**，`subject` 逐字 `{item_code: HRD-PACK-5K, warehouse: 成品仓 - HRD}`，`measures` 为 `{received: 2000.0, issued: 990.0, on_hand: 1010.0, ordered: 1000.0}`；另两条（`subcontracting-issued-not-received` / `closed-order-short-delivered`）**零命中**，与 §1.4b 预登记逐字一致。巡检侧 `request_count = 9`。⚠️ **「这 9 条全是 `GET`」是自记事实，没有独立留痕**：`--inspect-only` 不落证据文件，独立关闭审计被本 plan 明文禁止重跑活站点，因此只有本文这一处记载（命中本身另有两份完整实跑 JSON 佐证）。⇒ **§1.4b 的两条预登记之一（站点只命中一条）在活跑里被确认，不是证伪**（§2 Goal 4）。 |
| **H2** | 归因跑完 `hits_unchanged(report, attributions)` 为 **True**，且每条 `Attribution.hit` 与巡检报告里那条**逐字相等**（`ensure_unchanged` 不抛） | 实跑 + 断言 | **吻合，两跑各一次。** `hits_unchanged(report, attributions)` 两跑均为 **True**（证据 `checks.hits_unchanged` 与 `inspection.hits_unchanged` 两处各记一遍），`ensure_unchanged()` 未抛 `InsightBoundaryError`；`attributions[0].hit` 与 `inspection.hits[0]` **逐字相等**（`pack_id` / `rule_id` / `statement` / `subject` / `quantity_name` / `quantity` / `measures` 七项）。⚠️ 照实说清：本次归因 **`accepted = False`**（见 H4 与 §12），而 `hit` 逐字不变这件事**不因归因未被接受而失效** —— `Attribution.hit` 与 `answer` 本来就不混（`attribution.py` 类 docstring 逐字：`accepted` 为假时 `answer` 是空的，而 `hit` 照样在）。 |
| **H3** | **L1 门禁把 `HRD-PACK-5K` 当成"问题点名的单据"**（§1.4a）。**判在门禁自己的记录上，不判在工具调用上**：`agenerp/explain/gate.py:85` 的 `documents_named_in(question)`（正则 `:47` `DOC_NAME`）对本次题面**返回的集合含 `HRD-PACK-5K`**，且 L1 因此对答案要求 `doc.links` 级取证。⚠️ 上一版写的"循环至少对该物料号发起一次取证类工具调用"**不具判别力**（循环无论如何都会调工具），已在起草期改准 | 直接调 `documents_named_in(question)` + 读 `EvidenceSurface` 的 L1 判定记录 | **吻合，且判在比预测更强的一处记录上。** ① `documents_named_in(question)` 对本次题面返回 **`["HRD-PACK-5K"]`**（两跑一致，落在证据 `attributions[0].gate_l1.documents_named_in_question`）—— 物料号被当成「问题点名的单据」，§1.4a 预登记**被确认**。② L1 因此要求 `doc.links` 级取证这一半，**记录不在 ② 作答前那次求值上**：本次模型自始至终没有交出答案，`trace.gate_checks` 长度为 **0**（run-01）。但它落在 **① 工具前置那一次求值**的逐条记录上，拒绝理由逐字：「前置未满足：问题点名了某张单据 → 接受 answer 之前，必须已对它调用过 doc.links —— **未覆盖 ['HRD-PACK-5K']**」，run-01 出现 **14 次**（13 次 `query.read` + 1 次 `snapshot.read`）、run-02 **17 次**（全部 `query.read`）（`attributions[0].tool_calls[].reasons`，被拦的是 `query.read` / `snapshot.read`）。⚠️ **起草期的措辞在此处需要照实修正**：H3 写的是「读 `EvidenceSurface` 的 **L1 判定记录**」，两处求值取自**同一个** `EvidenceSurface`（D2），所以①的记录同样是 L1 的判定记录、并且**指名了那个物料号**；但**②那一次求值本跑一次都没发生过**，这一点必须与「H3 吻合」写在同一格里，不得读成「L1 在作答关口拦过它」。 |
| **H4** | 一次归因的模型调用 **≤ 12 次**。**出处逐字，且两个量分开说**：`docs/evidence/p1-explain/live-run-01.json` 的 `per_call_ledger` 长度 = **7**（模型调用），`trace.execute_calls` = **8**（**工具执行，不是同一个量**）；`docs/evidence/p1-cost/live-run-01.json` = **8** 次模型调用 / 9 次工具调用。⇒ 本项目仅有的两个观测是 **7** 与 **8**，12 是给它们留的余量。⚠️ **不是阈值、不拦截**（D-18），超了只停机记账。另判：账本条数 **== `chat()` 被调次数**；usage 三项**全部 > 0**；`total_matches_endpoint` **逐次为真** | 计数探针 + 账本落证据 | **不吻合（≤ 12 未达成），其余三项全部吻合。按起草期写死的处置：复跑一次 → 两次都超 → 记不吻合、照实落账、照常收口（D-18 记账不拦截），并往 `STATE.md` §3 追加一条 needs-human。**<br>**① ≤ 12 —— 不吻合。** run-01 **25** 次（`stopped = max-turns`）、**原样复跑** run-02 **22** 次（`stopped = tool-call-runaway`），两次都超，且**可复现**。口径逐字按 Exit Criteria：本次归因的 `cost_ledger` 条数，§6.1 O1 那次判定调用不计入（O1 两跑都因空答案抛 `JudgingError`，账本条数 0）。**12 这个数一个字不改。**<br>**② 账本条数 == `chat()` 被调次数 —— 吻合。** run-01 **25 == 25**、run-02 **22 == 22**；两个数来自**不同采集面**（账本在循环里记，计数探针包在 transport 上数）。<br>**③ usage 三项全部 > 0 —— 吻合。** run-01 累计 `prompt 123,177` / `completion 11,980` / `reasoning 10,032`；run-02 `116,699` / `6,023` / `3,580`；**逐条记录**的三项也都 > 0（两跑合计 **47** 条记录，最小 `reasoning` = **36**；43 只是 run-01 的最小值 —— **这处数字是独立关闭审计逐条复算后改准的**）。<br>**④ `total_matches_endpoint` 逐次为真 —— 吻合。** 两跑全部记录 `total_matches_endpoint` 与 `reasoning_matches_endpoint` 均为 `true`。<br>**为什么超**：根因**已实测定位，不是猜的** —— `doc.links` 对 `Item/HRD-PACK-5K` 必然 HTTP 500（站点上 `Quick Stock Balance` 是 **Single DocType**，`issingle = 1`，没有实体表），于是 L1 要的那一条证据**在本站点上取不到**，循环只能一直取证到轮数/工具调用上限。该缺陷按 §7 Phase 3 的 D1 分流登记为 `docs/bugs/03-…`，**本 plan 不改它**。 |
| **H6** | **四个面逐字不变**：`tests/contracts` 151 · `tests/tools` 81 passed, 12 skipped · `tests/context` 53 · `tests/experiments` 10；`tests/unit` **只增不减** | 五条命令 | **五条全部吻合，四个不变面逐字不变**：`tests/contracts` **151 passed** · `tests/tools` **81 passed, 12 skipped** · `tests/context` **53 passed** · `tests/experiments` **10 passed**（四条与 §0.1 第 6 条的开工基线逐字相同，各 exit 0）；`tests/unit` **599 → 614 passed**（**只增不减**，N = **15**，全部来自新增的 `tests/unit/test_insight_live_harness.py`）。⚠️ 那 15 条里有 **1 条是变异自查当场补出来的 M7** —— 原来的 14 条对「把 `evidence_trace_enumerable` 改成恒真」**全绿**，见 §12。 |
| **H7** | **`tests/routing` 的条数按新增 `agenerp/**/*.py` 文件数增长**。本 plan **预计新增 0 个产品模块**（实验脚本落 `tools/experiments/`，不在 `agenerp/` 下）⇒ 预测 `tests/routing` **逐字不变**（`…-0225-1` 落地后的值，起草期无法预知，收口时按**开工基线**对照，不按 164） | `python3 -m pytest tests/routing -q` | **吻合，逐字不变。** `167 passed, 1 skipped`（exit 0），与 §0.1 第 6 条的**开工基线逐字相同**（不是与起草期那个 164 对照 —— 起草期已写死按开工基线）。本 plan 新增 **0** 个 `agenerp/**/*.py`：实验脚本落 `tools/experiments/p1_insight_live/`、离线判据落 `tests/unit/`，两者都不在 `agenerp/` 下，`find agenerp -name '*.py' | wc -l` 前后同为 **56**。 |
| **H8** | **全程零白名单外请求**，且 **`POST` 的条数可预测**：`≈ 1 次 login + N 次 `frappe.client.has_permission``（N = `permission.scope` 实际枚举的 DocType 数，**预测 N > 0 且 ≤ 239**，`site_scope.py` 注释逐字 239 个业务 DocType），**`frappe.client.get_count` 的次数 = 239 × (`system.overview` + `schema.search` 被调次数)** ——
`doctypes_with_data` 每次都**逐个业务 DocType** POST 一次，而 `Session` **不是缓存**
（`agenerp/tools/runtime.py` 模块头逐字），⇒ 模型每调一次这两个工具就再来 239 个 POST，
`MAX_TOOL_CALLS = 32` 之下**总量可达数千**。⚠️ **这既是请求量预测，也是一条墙钟时间预警**，
起草期写死免得执行期被"跑了十分钟还没完"打个措手不及；**白名单外的写请求 0 次**；跑前跑后 `docker compose exec -T backend bench --site frontend list-apps` 逐字一致（**本仓的命令形态经容器，不是宿主命令**） | 请求记录器（method + path 逐条）+ 前后对照 | **吻合，含那条算式在内逐项对上；一处数字照实修正。**<br>**① 零白名单外请求。** 两跑 `requests.denied` 均为 **空**，`requests.other_verbs` 均为 **空**（一次 `PUT` / `DELETE` 都没有），全部请求要么是 `GET`、要么落在三条白名单方法路径上。白名单外的**写**请求 **0** 次。<br>**② `POST` 条数可预测。** run-01 `POST` **477** = `1 login` + **238** `has_permission` + **238** `get_count`；run-02 `POST` **715** = `1` + **238** + **476**。⚠️ **N = 238，不是 239** —— `site_scope.py` 注释里那个「239 个业务 DocType」是 2026-08-24 的实读，今天实读为 **238**，落在起草期写死的「N > 0 且 ≤ 239」之内。**改的是本格的实际列，不改注释、不改起草期预测。**<br>**③ `get_count` 的算式。** `238 × (system.overview + schema.search 被调次数)`：run-01 这两个工具共被调 **1** 次 → `238 × 1 = 238` ✅；run-02 共被调 **2** 次（各 1）→ `238 × 2 = 476` ✅。**逐字对上。**<br>**④ 墙钟时间预警成立。** run-01 **241.5 s**、run-02 **131.2 s**（总请求 1,419 / 1,195 条）。<br>**⑤ `list-apps` 前后一致。** `docker compose exec -T backend bench --site frontend list-apps` → exit **0**，`frappe 15.118.0 UNVERSIONED` / `erpnext 15.119.3 UNVERSIONED`，与 `docs/analysis/2026-08-25-0119-desk-sid-identity-probe.md` 记的那次读回**逐字相同**。⚠️ **照实说清一处执行期的口径退让**：本 plan **没有**在 run-01 之前当场取一次「跑前」读数，用的是仓里已有的那份记录当「前」值。⇒「前后一致」这句话在本 plan 里的强度低于原计划；站点零写这个结论的**主要承重面是请求记录器**（逐条 method + path，白名单外的写 0 次），`list-apps` 只是旁证。 |

⚠️ **编号有意跳过 `H5`**：上一版的 H5（判定器给不给得出标签）已整体降进 §6.1 的 `O1`，
**编号不重排**（重排会让"预测列一个字不改"这条自食其言）。收口审计不必去找一个不存在的 H5。

### 6.1 观测格（**不参与吻合计数，不构成任何通过条件**）

| # | 观测项 | 怎么看 | 实际 |
|---|---|---|---|
| **O1** | 把归因答案喂 `…-0225-1` 的判定器一次，看它给出三个标签里的哪一个、会不会报错 | `judge_one(attribution.answer)` | **跑了，且判定器没崩 —— 但它没能给出标签，原因不在判定器。** 两跑的归因 `answer` 都是**空文本**（`accepted = False`，模型自始至终没作答），`judge_one("")` 按 `agenerp/judging/` 自己的口径**指名抛** `JudgingError: 待判的答案是空文本 —— 空答案不是一次判定的合法输入`，脚本原样记进证据（`attributions[0].judge`：`ok=false` / `label=""` / `error` 全文 / `ledger.calls = 0`）。⇒ **O1 测的那件事（判定器在跨题族输入上不崩）得到的是一个「拒绝而非崩溃」的结果**：它没有回一个假标签，也没有把空串判成 `correct`。⚠️ **本格的标签取值是空的，而本 plan 的通过与否一个字都不依赖它**（§2 Goal 3 / §1.5 / M6）。⚠️ **没有跨题族的标签可看** —— 「判定器在归因文本上给什么标签」这件事，本 plan **没有观测到**，不得由任何下游读成已观测。 |

⚠️ **O1 测的是「判定器在跨题族输入上不崩」，不是「归因质量合格」**（§1.5）。
**它的标签取值不构成任何通过条件**；证据文件里必须逐字标注
「**据判定器，判为 X，待复验；本 plan 不据此对归因质量下任何结论**」（D-16）。

**⚠️ H1 是承重格**：若活跑命中数与预测不符（例如变成 0 条或 2 条），
**先原样复跑那条命令**（`AGENTS.md` 裁判规则 3）；复跑不出来就记「**不可复现**」，
**不许猜根因**；可复现则按 §7 Phase 3 的分流规则处置，**不许改规则去凑**。

## 7. Execution Plan

**执行顺序即下列顺序，不许并行、不许跳。**

### Phase 1 — 前置闸 + 实跑脚手架（**不打站点、不烧 token**）

Status: completed
Targets: `tools/experiments/p1_insight_live/run.py` · `tests/unit/test_insight_live_harness.py`
Skill: `none`

- Item Types: `Add | Proof`
- **Prereqs（前置闸，起草期写死，执行期不许绕）**：见本 phase 第一个 `[ ] Proof` 项，
  它是**可勾选、可审计**的一条，不是散在 `Prereqs:` 里的一句话。

- [x] `Proof` **前置闸（本 plan 的第一件事，不满足就到此为止）**。两条**合取**，逐条实读并记进 §0.1：
      - **(a)** `grep -n "^> Plan Status" docs/plans/p1-insight/2026-08-25-0225-1-answer-judge-v0.md`
        → 逐字 `completed`。
      - **(b)** `…-0225-1` §6 中**承载「① 5 条负例逐条三分类精确匹配 且 ② 正例 ≥ 17/19」那一格**
        （**按内容认，不按编号认** —— 那个 plan 仍在 `draft`，编号可能变）的「实际」列
        **逐字记为「吻合」**。
        ⚠️ **只有逐字「吻合」算满足**：`部分吻合` / 空白 / `不适用` / `不吻合` **一律算不满足**
        （本仓有 `部分吻合` / `部分一致` / `五格里四格吻合` 的先例，不写死会被读松）。
        ⚠️ **判的是口径达成，不是那格的"预测 vs 实际"是否相符** —— 那格同时写着
        「预测：第 1 轮就达到」，若判定器**第 2 轮**才达标，该格会诚实地记为不吻合，
        **而口径其实达成了**。这种情况下 **(b) 视为满足**，并在 §0.1 逐字说明。
      - 任一不满足 ⇒ **本 plan 整体不开工**：置 `Plan Status: deferred`，往 `STATE.md` §3 **追加**
        一条 needs-human，重开事件逐字「**`…-0225-1` 的验收口径达成，或人另行裁定归因如何被判**」。
      - ⚠️ **不许**降级成「先跑一跑归因、判定记录以后再补」—— 那会产出一份没有判定手段的
        自由文本证据，正是 roadmap 那一节要挡的东西。
- [x] `Add` 实验脚本 `tools/experiments/p1_insight_live/run.py`：
      装 `discrete` 包 → `inspect_site` → `attribute_all` → 落证据。
      **只读**：不调任何写方法（`create_doc` / `ensure_doc` / `submit_doc` /
      `delete_custom_field` / `drop_columns` 一个不碰）。
      **判定结果由外部注入（可替身），且退出码路径不读 `verdict.label`** ——
      这是 M6 与 Phase 1 判据 ⑤ 的接缝，必须在本项里做出来
- [x] `Add` **请求记录器**（H8）：把 `SiteClient` 的传输层包一层，逐条记 method + path，
      **按 §3 Non-Goals 5 的白名单判**（不是按动词判，§1.3b）。
      白名单外的请求 → **指名报错并非零退出**
- [x] `Add` `chat()` 计数探针（H4，先例 `tests/unit/test_explain_cost_ledger.py` 的构造面替身）
- [x] `Proof` 离线判据 `tests/unit/test_insight_live_harness.py`（**全部走假件，零网络零站点**）：
      ① 脚本的证据落盘形状（键集合固定、含逐次账本、**取证轨迹的 `tool_calls` 非空且可枚举**
      —— 这是 §2 目标 2 第五条事实的判据落点 —— **不含任何凭据字面量**）·
      ② `hits_unchanged` 为假时脚本**非零退出**（不许把它记成一次成功实跑）·
      ③ 请求记录器：白名单内的 `POST /api/method/frappe.client.has_permission` **放行**、
      白名单外的 `POST /api/resource/Item` **指名报错并非零退出**（两条都要有，只测一半会把
      §1.3b 那次改准又丢掉）· ④ 账本条数 != `chat()` 计数时**非零退出** ·
      ⑤ **退出码在三个判定标签下逐一不变**（喂 `correct` / `incomplete` / `truncated` 三种
      判定结果各跑一次，退出码逐字相同）—— 这是 §2 Goal 3 的可判形式，M6 的靶子

Exit Criteria:

- [x] 前置闸已逐条实读并记进 §0.1（不满足则按上面的停机分支执行，**本 plan 到此为止**）
- [x] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**，`tests/unit` 只增不减
- [x] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → **exit 0**
- [x] `git diff --stat -- tests/gates/ .github/workflows/ missions/ docs/masterplan/DECISIONS.md agenerp/insight/ agenerp/inspection/` → **无输出**
- [x] `No owner-doc update required`（落点节在 Phase 4 一次性写）

### Phase 2 — 活跑一次（真站点 + 真端点）

Status: completed
Targets: `docs/evidence/p1-insight-live/`
Skill: `none`

- Item Types: `Proof`
- Prereqs: Phase 1 全部 Exit Criteria 已勾；活栈已 `up -d --wait` 且六个 healthy

- [x] `Proof` 起栈并实读 `docker compose ps`，逐字记进 §0.1
- [x] `Proof` 跑巡检，**先把 H1 填了再往下走**（命中数与预测不符 → 先原样复跑，再按 §6 承重格口径处置）
- [x] `Proof` 跑归因**一次**，落 `docs/evidence/p1-insight-live/live-run-01.json`：
      命中 / 题面 / 答案全文 / `accepted` / 工具调用序列 / 逐次账本 / 端点原始 usage / 耗时。
      **凭据一个字节不进证据文件**
- [x] `Proof` 逐格填 §6 的 **H2 / H3 / H4 / H8**
- [~] `Proof` 把归因答案喂一次判定器，填 **§6.1 O1**，并在证据文件里**逐字标注**
      「**据判定器，判为 X，待复验；本 plan 不据此对归因质量下任何结论**」（§1.5 / D-16）
      —— **前半做到、后半做不到，照实记 `[~]`**：判定器被喂了一次（两跑各一次），
      但两跑的 `answer` 都是**空文本**，`judge_one("")` 指名抛 `JudgingError`，
      **没有 X 可填进那句话**。证据里落的是同一位置的诚实版本
      （`attributions[0].judge`：`ok=false` / `label=""` / `error` 全文 /
      `note` = 「判定器这次没给出标签 —— 照实记；本 plan 的通过与否不依赖它（§2 Goal 3）」），
      另在 `docs/evidence/p1-insight-live/README.md` 逐字写死「**没有观测到任何跨题族标签**」。
      ⚠️ **不许**为了凑出那句标注去喂别的文本 —— 那就不是这一跑的归因答案了。

Exit Criteria:

- [x] 证据文件齐全且可复核；**H1 / H2 / H3 / H4 / H8 五格**「实际」列已填
      （**§6.1 O1 单独记，不计入本条**）
- [x] **判定记录存在且可复现**（O1 跑过、结果与输入全文在证据文件里）——
      ⚠️ 本条判的是**记录的存在与可复现**，**不判那个标签是什么**（§2 Goal 3）
- [x] 站点侧**零白名单外请求**已由请求记录器逐条证明，跑前跑后
      `docker compose exec -T backend bench --site frontend list-apps` 逐字一致
- [~] 调用次数 ≤ 12（**口径：本次归因的 `cost_ledger` 条数；§6.1 O1 那次判定调用不计入**）。
      **超了怎么办，起草期写死**：先**原样复跑一次**（裁判规则 3）；两次都超 ⇒
      H4 该格记 **不吻合**、证据与次数照实落账、**本 plan 照常收口**
      （D-18：这是记账不是闸，超了不改变 plan 状态），并往 `STATE.md` §3 **追加**一条
      needs-human 说明「本项目的归因调用量高于仅有的两个观测（7 / 8）」。**不许**回头去改 12 这个数
- [x] `docs/logs/2026/<MM-DD>.md` 更新

### Phase 3 — 分流：活跑抓到的问题**归谁**

Status: completed
Targets: `docs/bugs/`（**D1 (ii) 命中时**）· `docs/masterplan/STATE.md`（**只追加**）
Skill: `bug-diagnosis-prompt.md`（**仅当**抓到一个可复现且根因未证的缺陷时启用；否则 `none`）

- Item Types: `Fix | Decision`（**`Follow-up` 不在本 phase 的允许类型里** ——
  D1 对确认的活缺陷禁止用它，把它列在页面上只会招手）
- Prereqs: Phase 2 完成

- [x] `Decision D1` **分流规则（起草期写死，执行期只套用，不现编）**：
      - **(i) 落在本 plan 交付面内**（实验脚本 / 离线判据 / 证据形状）→ 本 plan **就地 `Fix`**
      - **(ii) 落在 `agenerp/insight/**` 或 `agenerp/inspection/**` 的行为上** →
        **不在本 plan 改**（§3 Non-Goals 2 / 见即停第 4 条）。先**原样复跑**确认可复现，
        可复现则登记 `docs/bugs/` + `STATE.md` §3 needs-human，**不可复现就记「不可复现」，不猜根因**
      - **(iii) 落在已登记的既有 open 上**（如 `docs/bugs/02-…` 的站点 `Sales Order.status`）→
        **只引用、不重复登记、不代人处置**
      - ⚠️ **确认的活缺陷一律 `Fix` 或登记，不许写成 `Follow-up`**（Minimum Rule 7 / 14）
      **备选与残余风险（Minimum Rule 9）**：备选是「(ii) 类就地在本 plan 改 `agenerp/insight/**`」，
      **被 §3 Non-Goals 2 否决** —— 本 plan 是一次**验证**，在同一个 plan 里既当运动员又当裁判，
      会让"活跑抓到的问题"变成"顺手改到跑绿为止"。**残余风险照实登记：(ii) 类缺陷的修复被推迟到
      一个尚不存在的后继 plan**，在那之前它只是 `docs/bugs/` 里的一行。
- [x] `Proof` 逐条套用 D1，把每一个发现写成一行：现象 → 复跑结果 → 分流档 → 落点

      **本次活跑的全部发现（4 条，没有悬空项）**：

      | # | 现象 | 复跑结果 | 分流档 | 落点 |
      |---|---|---|---|---|
      | **F1** | `doc.links` 对 `Item/HRD-PACK-5K` **必然 HTTP 500** —— `scan_links` 遍历 Link 宿主时撞上 `Quick Stock Balance`（本站点 `issingle = 1`，无实体表），一次 500 让整次 `doc.links` 作废。⇒ L1 要的证据取不到 ⇒ 归因**永远到不了 `accepted`**（两跑 `answer` 皆空） | **可复现**：原样复跑 run-02 同一形态（`doc.links` 500 出现 5 次、L1 未覆盖 `['HRD-PACK-5K']` 出现 17 次）。根因**实测定位**（直接读 DocType 元数据 `issingle=1`），**不是猜的** | **(ii) 类推**——⚠️ **照实说清**：D1 的 (ii) 逐字写的是「落在 `agenerp/insight/**` 或 `agenerp/inspection/**` 的行为上」，而本条落在 **`agenerp/tools/documents.py`**，**D1 起草期的三档没有逐字盖住它**。按 (ii) 的**理由**（「在同一个 plan 里既当运动员又当裁判，会让活跑抓到的问题变成顺手改到跑绿为止」）处置：**登记不修**。这是执行期的一次归档判断，写在这里而不是悄悄套进某一档 | `docs/bugs/03-doc-links-dies-on-single-doctypes.md` + `STATE.md` §3 needs-human（带触发条件） |
      | **F2** | 一次归因烧掉 **25 / 22** 次模型调用，超过 H4 写死的 ≤ 12 | **可复现**（两跑都超）。起草期已写死处置：记不吻合、照实落账、**照常收口**（D-18 记账不拦截） | **(ii) 类推 · 与 F1 同因** —— 它是 F1 的**后果**不是独立缺陷：L1 满足不了 ⇒ 循环取证到上限。**不单开 bug**，随 F1 一起交人 | §6 H4 该格记「不吻合」+ `STATE.md` §3 与 F1 同一条 needs-human |
      | **F3** | 活站点上 `discrete` 包只命中 1 条（`closed-order-short-delivered` 零命中，因 `Sales Order.status` 是 `To Deliver and Bill`） | 与 §1.4b 预登记**逐字一致**，`--inspect-only` 一次读出 | **(iii)** 已登记的既有 open | **只引用、不重复登记、不代人处置**：`docs/bugs/02-…` + `STATE.md` §3 `[open] 2026-08-24T21:40Z` |
      | **F4** | `permission.scope` 实际枚举到的业务 DocType 是 **238** 个，而 `agenerp/tools/site_scope.py` 的注释逐字写着 **239** | 两跑都是 238（`has_permission` POST 条数），且 `get_count` 恰为 `238 × 工具调用次数` | **(i) 之外、也不是缺陷** —— 那句注释记的是 **2026-08-24 的实读**，不是一条被判据钉住的常量；本 plan 的预测写的是「N > 0 且 ≤ 239」，238 落在其中 | **不改注释、不改预测**，只在 §6 H8 的「实际」列照实记下这个差 |

      ⚠️ **零个 (i) 类** —— 本 plan 交付面（实验脚本 / 离线判据 / 证据形状）在两次活跑里**没有暴露缺陷**：
      六项 `checks` 两跑全绿、证据键集合两跑一致、请求记录器一次白名单外请求都没放过。
      **这不是「没找」**：F1 正是被这套脚手架的逐条轨迹逼出来的。
- [x] `Fix` (i) 类问题就地修完并复跑 —— **(i) 类为零，本项无事可修**。
      ⚠️ **不许**因此把 F1 / F2 降级成「本 plan 顺手修一下」（§3 Non-Goal 2 / 见即停 4 的理由同款），
      也**不许**写成 `Follow-up`（D1 逐字禁止）—— 它们是**已登记的活缺陷**，落点在上表最后一列。

Exit Criteria:

- [x] 每个发现都落进 (i)/(ii)/(iii) 之一，**没有悬空项**
- [x] (ii) 类已登记且带触发条件；(iii) 类只引用未改写
- [x] `docs/logs/` 更新

### Phase 4 — 变异自查 + 落点节 §7.16 + 收口

Status: completed
Targets: `docs/architecture/module-boundaries.md`（**§7.16 新增** + **§7.9 失效归属改准**）·
`docs/design/agents-and-roles.md` §5.1（**只补落点指针**）· `docs/masterplan/STATE.md`（**只追加**）·
`docs/logs/2026/<MM-DD>.md` · `docs/backlog/p1-insight-roadmap.md`（**执行期追加的 target**：
工作项 7 那一行的**行内追加**结清记录，**`done` 状态行不改**，Non-Goal 9 守住；
起草期漏列，独立关闭审计要求补上，照实记）
Skill: `closure-audit-prompt.md`（**独立子代理**）

- Item Types: `Proof | Add`
- Prereqs: Phase 3 完成

- [x] `Proof` **变异自查 M1–M6**（施加 → 复跑 → 记打红它的判据 → **文件级备份还原**，禁 `git checkout`）：
      - **M1** 脚本把 `hits_unchanged` 的假值吞掉后退 0 → 必须打红
      - **M2** 账本条数与 `chat()` 计数不等时脚本仍退 0 → 必须打红
      - **M3** 请求记录器放过一次**白名单外的写**（例如 `POST /api/resource/Item`）→ 必须打红。
        ⚠️ **不是"放过一次 `POST`"** —— 白名单内的 `POST` 本来就该放行（§1.3b）
      - **M4** 证据文件里混进凭据字面量 → 必须打红
      - **M5** 命中为空时脚本把它当成"跑通了"退 0 → 必须打红（**空集不是成功**）
      - **M6** **判定器的标签取值被用作通过 / 失败条件** —— 具体靶子：在
        `tools/experiments/p1_insight_live/run.py` 的退出码路径上加一条
        `if verdict.label != "correct": raise SystemExit(1)` →
        `tests/unit/test_insight_live_harness.py` 的判据 ⑤（**退出码在三个标签下逐一不变**）
        **必须打红**。⚠️ 上一版把 M6 写成"变异一段散文"，那种变异**没有靶子也没有判据能打红它**，
        只会被自证；已在起草期改准
      **有绿的就地补断言并登记为 M7、M8…**，复跑确认被打红
- [x] `Add` `module-boundaries.md` **§7.16**（纯新增：本次活跑的口径、
      **H1–H4 / H6–H8 + O1 的对照（`H5` 有意留空，见 §6 的编号说明）**、D1 分流规则、
      **§1.5 的判定器边界逐字**、残余风险）
- [x] `Fix` **§7.9 的失效归属处置，默认用「追加」而不是「改写」**：那句话
      （「归因那一半没有在活端点上跑过」）活在一段标题为**活站点验证范围**的段落里 ——
      它记的是**那个 plan 那一跑的范围**，不是一处漂移。⇒ 默认动作是在该句后**追加**
      「（**已由 plan `…-0225-2` 结清，口径见 §7.16**）」，**原句一个字不改**
      （本仓收口记录一贯的追加式账本形态）。**只有**实跑结果与原句正面冲突时才改写，
      改写要在 §12 逐字说明冲突在哪
- [x] `Add` `agents-and-roles.md` §5.1 **只补落点指针**（删除列必须为 0）
- [x] `Proof` 红线自证：`git status --porcelain -- tests/gates/ .github/workflows/ missions/ docs/masterplan/DECISIONS.md` → **无输出**；
      `STATE.md` numstat **删除列为 0**
- [x] `Proof` 八条基线命令全跑一遍，与 §1.1 / §6 H6 / H7 逐格对照
- [x] `Proof` 往 `STATE.md` §2 **追加**证据行（命令原文 + 退出码 + 落地 sha）；有 needs-human 则 §3 **追加**
- [x] `Proof` **独立关闭审计**（独立子代理，fresh session），结论记进 `## Closure` —— 结论 **`needs revision`**，五条 blocking + 三条非阻塞**逐条处置后收口**，见 `## Closure`

Exit Criteria:

- [x] M1–M6（含新增的 M7+）逐条被打红 —— **M1–M6 逐条 exit 1，另新增 M7（变异自查当场发现的缺口，就地补断言后 exit 1）**，逐条见 §12.1
- [x] §7.16 已落地；§7.9 的改准**只动归属那一句**（或逐字未改并说明）；§5.1 删除列为 0
- [x] 八条命令全部 exit 0，H6 / H7 已填
- [x] `STATE.md` 只追加；`docs/logs/` 更新
- [x] 独立关闭审计完成并记录（`## Closure`：结论、它自己重跑了什么、五条 blocking 的逐条处置、六条残余风险）

## 8. 风险

① **一跑不是分布。** 一次活跑证明的是"这条链在真环境里走得通"，**不是**"归因稳定/正确"。
   控制：Goals 2 只判结构化事实；§1.5 + §6.1 O1 的逐字标注 + §7.16 三处重复"不下质量结论"。

② **判定器被越界使用。** 跨题族外推是本 plan 最容易犯的错。
   控制：M6 变异（**标签取值进退出码即红**，靶子与判据都已具名）+ Non-Goals 1 +
   Exit Criteria 里**没有一条**引用判定器的**标签取值**（引用的只有"判定记录存在且可复现"）。

③ **活跑会改站点状态吗？** 归因走 P1.4 的循环，十个契约**全部只读** ——
   但**只读不等于只发 `GET`**（§1.3b：`permission.scope` 会 POST `frappe.client.has_permission`）。
   控制：H8 的**白名单**请求记录器（白名单外的写指名报错并非零退出）+
   跑前跑后 `list-apps` 对照 + 见即停第 1 条。
   ⚠️ **白名单是起草期按实读列的，不是穷举证明** —— 若活跑抓到一个既非写、又不在白名单里的
   方法名，按见即停第 1 条**停机并照实记**，**不许执行期往白名单里加**（那等于让被测者改考题）。
   ⚠️ **残余风险照实登记**：本仓**没有站点级 teardown**，万一真发生了写，
   复位只能 `down -v` 冷起并重跑整条种子装载链（`docs/architecture/module-boundaries.md` §12.9），
   **本 plan 不交付任何代码级回滚**。

④ **命中只有 1 条 ⇒ 样本量 1。** §1.4b 已预登记。控制：照实记，
   **不许**为了多一条命中去改规则或改站点数据（见即停第 5 条）。

⑤ **本 plan 依赖另一个尚未执行的 plan。** 若 `…-0225-1` 的 H2 不吻合，本 plan 整体不开工。
   控制：Phase 1 的前置闸是**起草期写死的合取条件**，且**禁止降级执行**。

## 9. Draft Review Record

- **独立草案评审 第 1 轮：`needs revision`**（独立子代理，fresh session，2026-08-25）。5 条 blocking：
  **① 「全程零 `POST`」是错的** —— `explain()` 开场无条件注入 `permission.scope`
  （`opening.py:143`）→ `site_scope.py:150-153` 逐 DocType 调 `frappe.client.has_permission`
  → `site.py:311-334` 是 `POST /api/method/…`，而本站点业务 DocType **239 个**。
  当时的 plan 把"零 `POST`"写进了 Non-Goals / 见即停 / H8 / 判据 / 变异**五处**，
  照它跑会在**第二个请求上误停机**。
  ② 前置闸措辞太松（没定义什么叫"吻合"、按编号而非内容锚定、不是可勾选项）·
  ③ Goal 3「判定器输出不进任何 Exit Criteria」被 Phase 2 自己的 Exit Criteria 推翻（H5 就是判定器那格）·
  ④ M6 变异的靶子是一段散文，**没有任何判据能打红它** ·
  ⑤ H4 误把 P1.4 的 `execute_calls`（8）当成模型调用数（实为 **7**），且「≤ 40」在
  `MAX_TURNS = 25` 之下**结构上不可达**，等于一条永不触发的假闸。
- **本轮改了什么**：新增 **§1.3b** 记下"只读 ≠ 只发 GET"的实读，并把只读判据整体改成
  **端点语义白名单**（Non-Goals 5 / 见即停 1 / H8 / Phase 1 记录器 / M3 五处同步）·
  前置闸升为 Phase 1 **第一个 `[ ]` Proof 项**，按**内容**锚定、要求**逐字「吻合」**、
  并写死"第 2 轮才达标"那种情形怎么算 · H5 整体降进 **§6.1 O1** 观测格，
  Goal 3 改成「**标签取值**不构成通过条件」，Exit Criteria 改为 H1/H2/H3/H4/H8 五格 +
  一条只判"判定记录存在且可复现"的门 · M6 改成**有靶子有判据**（`run.py` 退出码路径 +
  Phase 1 判据 ⑤「退出码在三个标签下逐一不变」）· H4 逐字区分 7 与 8 两个量，上限改 **12**。
- **独立草案评审 第 2 轮：`acceptable as-is`**（独立子代理，fresh session，2026-08-25）。
  五条逐条判 `RESOLVED`；评审**独立枚举了 `explain()` / `attribute()` 可达的全部站点端点**，
  确认白名单完备（只读跑法不会误触）；另确认 `≤ 12` 可证伪且不平凡、H8 两半均可证伪、
  无悬挂引用、Anti-Slacking 与 Minimum Rules 无违反。**0 条 blocking**，5 条非阻塞注记。
- **本轮按非阻塞注记改了什么**（全部采纳）：H8 把 `get_count` 的量**算出来**
  （239 × 两个工具的调用次数，`MAX_TOOL_CALLS = 32` 之下可达数千，兼作墙钟时间预警）·
  §6 写明**有意跳过 `H5`** 编号、Phase 4 对照表相应改成 `H1–H4 / H6–H8 + O1` ·
  Phase 1 的 `run.py` 交付项补上 **M6/判据⑤ 所依赖的判定注入接缝** ·
  「≤ 12」补上**口径**（本次归因的 `cost_ledger` 条数，O1 那次不计入）与**超了怎么办**
  （复跑一次 → 记不吻合 → 照常收口，D-18 记账不拦截）· `list-apps` 改成本仓的
  `docker compose exec -T backend …` 形态 · §0 第 1 条把"工作区干净"收窄成
  "除本批两个 plan 文件外无输出" · Goal 2 第五条事实（取证轨迹非空）补上判据落点。

## 10. Closure Gates

- [x] in-scope behavior is complete —— 交付面是**实验设施 + 离线判据 + 证据**，三样齐全；
      `agenerp/insight/**` / `agenerp/inspection/**` **一行未改**（本 plan 是验证，不是改造）
- [x] relevant docs are aligned（§7.16 新增 · §7.9 归属**追加式**结清、**原句一个字节未改** ·
      §5.1 只补指针 **4 增 0 删** · roadmap 工作项 7 的 **`done` 状态行与既有文字照实保留**，
      只在同一个括号内追加结清记录，Non-Goal 9 守住。⚠️ **独立关闭审计逐字符比对后改准**：唯一的字符级改动是**行尾那个 `）` 被右移**到追加段之后，
      「一个字未改写」这句措辞已在 roadmap 与本节两处同步改准）
- [x] verification has run：八条基线命令 + **两次**活跑（第 2 次是原样复跑），
      命令原文与退出码逐条记在 §0.1 / §6 / §12 / `STATE.md` / `docs/logs/`
- [x] scoped verification is not conflated with full verification ——
      **verification scope limited** 逐字写在四处：本节、§7.16 末节、
      `docs/evidence/p1-insight-live/README.md`、`STATE.md` 那条证据行。
      逐字口径：**两次活跑只在本机、只跑了两次、CI 完全没有覆盖**（活栈 + 真 key 都不在 runner 上）；
      CI 复跑得到的只有 `tests/unit/test_insight_live_harness.py` 那 **15** 条离线判据
- [x] no in-scope item downgraded to deferred/follow-up ——
      本轮抓到的 4 条发现**逐条落进 D1 的 (i)/(ii)/(iii)**（见 Phase 3 那张表），
      **没有一条写成 `Follow-up`**。⚠️ 照实说清两处**记 `[~]` 而不是勾干净**的项：
      Phase 2 的 O1 标注项（没有 X 可填）与 Phase 2 Exit Criteria 的「≤ 12」——
      **两者都不是 in-scope 项被降级**，前者是"要标注的那个值不存在"，
      后者是**起草期就写死了「超了照常收口」**的记账项（D-18）
- [x] independent draft review completed and recorded（§9：两轮，第 2 轮 `acceptable as-is`）
- [x] text consistency verified：顶部 `Plan Status` · 四个 phase 的 `Status` · 各 Exit Criteria ·
      本节 · `docs/logs/2026/08-25.md` · `STATE.md` 六处口径一致
      （尤其「**这一跑没有产出任何归因文本**」这句在 plan / §7.16 / 证据 README / STATE / 日志 / roadmap **六处都在**）
- [x] closure audit was independent（`Reviewer availability = subagent`；结论见 `## Closure`）
- [x] closure evidence exists in files（`docs/evidence/p1-insight-live/`：README + 两份 JSON；
      `STATE.md` 证据行 + needs-human 各一条；`docs/bugs/03-…`）
- [x] 站点侧**零白名单外请求**已证（按端点语义，不按 HTTP 动词：两跑 `denied` 空、
      `other_verbs` 空、写请求 0 次）；红线自证四个 pathspec 无输出；
      `STATE.md` numstat **`19  0`**（删除列为 0）

## 11. Deferred But Adjudicated

### 归因文本的**质量结论**

- Classification: `out-of-scope improvement`（**显式定界，不是遗漏**）
- Why Not Blocking Closure: 判自由文本要先有**该题族**的人工标注集
  （roadmap 逐字「标签只能由人读原文定」），本仓今天只有 P1.0 那一题族的 24 条。
- Successor Required: `yes`。重开事件：**人为归因题族标注出一份集子**（≥ 4 条负例，
  理由同 roadmap「反例比正例值钱」）。

### 多次活跑与分布

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 一跑是验证链路可走，不是测分布（D-16）。
- Successor Required: `no`。重开事件：**要用归因的实测数字去定任何阈值或做任何比较时**
  （届时须先有采样计划与写死的假设，属另一个 plan）。

### 站点上 `closed-order-short-delivered` 零命中

- Classification: `out-of-scope improvement`（**既有 open，只引用不重复登记**）
- Why Not Blocking Closure: 归属是**种子装载面**，已记 `docs/bugs/02-…` 与
  `STATE.md` §3 `[open] 2026-08-24T21:40Z`，**需人裁定两件事**。
- Successor Required: `yes` —— 由**人**。重开事件：**人处置那条 `[open]` 时**。
  ⚠️ 本 plan **不代人处置、不改规则去凑命中**。

### L1 门禁把物料号当单据号（§1.4a）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 误报方向是**更严**（P1.5 落账逐字），
  在②端只读阶段"更严"不产生用户可见损害。
- Successor Required: `no`。重开事件：**出现一条因该误报而被错误拒绝的真实归因**
  （届时要连同 `gate.py` 的 `DOC_NAME` 口径一起重定）。

## 12. 执行记录

### 12.1 变异自查 M1–M7（施加 → 复跑 → 记打红它的判据 → **文件级 `cp` 备份还原**）

**全程未用 `git checkout`**（见即停第 6 条），未触碰任何红线路径。
被测对象是 `tools/experiments/p1_insight_live/run.py`，判据是
`tests/unit/test_insight_live_harness.py`。还原后复跑 **15 passed（exit 0）**。

| # | 变异（靶子逐字） | 退出码 | 被哪条判据打红 |
|---|---|---|---|
| **M1** | `decide()` 的 `"hits_unchanged"` 改成恒 `True`（把假值吞掉） | **1** | `test_it_exits_non_zero_when_the_hits_were_rewritten` |
| **M2** | `"ledger_matches_chat_calls"` 改成恒 `True` | **1** | `test_it_exits_non_zero_when_the_ledger_does_not_match_the_chat_count` |
| **M3** | `RecordingTransport` 放过 `POST`/`PUT`/`DELETE` 到 `/api/resource/**` | **1** | `test_the_recorder_names_and_refuses_a_write_to_api_resource` + `test_a_denied_request_makes_the_whole_run_fail`（**2 条**）。⚠️ **同一次变异下 `test_the_recorder_lets_a_whitelisted_post_through` 仍然通过** —— 这正是 §1.3b 那次改准要的形状：M3 打的是「放过白名单外的**写**」，不是「放过一次 `POST`」 |
| **M4** | `credential_hits()` 的 `"found"` 改成恒 `[]`（凭据扫描被吞掉） | **1** | `test_m4_a_credential_literal_in_the_evidence_fails_the_run` |
| **M5** | `"hits_not_empty"` 改成恒 `True`（空集当成跑通了） | **1** | `test_it_exits_non_zero_when_the_inspection_found_nothing` |
| **M6** | 在 `main()` 的退出码路径上加 `if …judge["label"] != "correct": raise SystemExit(1)` | **1** | `test_the_exit_code_is_identical_under_every_verdict_label` + `test_the_verdict_note_is_recorded_verbatim_as_pending_review` + `test_the_decision_path_never_reads_the_verdict_label`（**3 条**） |
| **M7** | `"evidence_trace_enumerable"` 改成恒 `True` | **1**（补判据**之后**） | `test_m7_an_empty_evidence_trace_fails_the_run` |

⚠️ **M7 是变异自查当场发现的缺口，不是起草期就有的**，照实记全过程：
起草期的 Phase 1 判据 ① 里只有「取证轨迹非空且可枚举」的**快乐路径断言**
（`checks["evidence_trace_enumerable"] is True`），把 `decide()` 里那一项**改成恒真**之后，
**原有 14 条判据全绿** —— 一条恒真的判据等于没判。
就地补 `test_m7_an_empty_evidence_trace_fails_the_run`（剧本第一步就直接作答、一次工具都不调
⇒ ② 门禁拦下、循环耗尽轮数、`tool_calls` 为空），复跑确认该变异 **exit 1**、还原后 **exit 0**。
plan §7 Phase 4 逐字写着「**有绿的就地补断言并登记为 M7、M8…**」，本条就是它。

### 12.2 起草期预测与实际不吻合的地方，逐条

1. **H4 的「≤ 12」不吻合**（两跑 **25 / 22**）。处置**完全按起草期写死的走**：
   先原样复跑一次 → 两次都超 → 记不吻合、证据与次数照实落账 → **照常收口**（D-18）→
   `STATE.md` §3 追加 needs-human。**12 这个数一个字没改。**
2. **H8 的 N 是 238，不是 `site_scope.py` 注释里的 239。** 那句注释记的是 2026-08-24 的实读，
   不是被判据钉住的常量；起草期的预测写的是「N > 0 且 **≤ 239**」，238 落在其中 ⇒
   **预测本身吻合**，只是那个参考数字过期了。**注释不改、预测不改**，只在 H8 实际列记下这个差。
3. **H3 的第二半判在了另一处记录上。** 起草期说「读 `EvidenceSurface` 的 L1 判定记录」，
   实际 **② 作答前那次求值一次都没发生**（模型没作答，`gate_checks` 长度 0）；
   打在 **① 工具前置**那次求值的逐条拒绝理由上，而它**指名了 `HRD-PACK-5K`**，
   两处求值取自同一个 `EvidenceSurface`（D2）⇒ 判据强度不降，但**措辞必须改准**，已写进该格。
4. **O1 的「据判定器，判为 X，待复验」写不出来。** `answer` 为空 ⇒ `judge_one("")` 抛
   `JudgingError` ⇒ **没有 X**。Phase 2 该项记 `[~]`，证据里落诚实版本，README 逐字写死
   「**没有观测到任何跨题族标签**」。**不许**为了凑出那句话去喂别的文本。
5. **Goal 1「归因第一次在真模型 + 真站点上跑通」按字面只做到一半，照实裁定。**
   ✅ 已做到：一次实跑的**完整轨迹**落了 `docs/evidence/p1-insight-live/`（命中、题面、门禁判定、逐次账本、端点原始 usage、工具调用序列、耗时全在）。
   ❌ 没做到：那份轨迹里**「答案全文」是空的** —— Goal 1 的括号里逐字列着「答案全文」，而两跑 `accepted = false`。⇒ **「跑通」这个词按最强读法（模型给出了一段归因）不成立**，按弱读法（这条链在真环境里从头走到尾没有跑飞、没有越权、没有写）成立。
   **本 plan 采用弱读法收口**，理由是 Goal 2 的五条结构化事实**全部达成**、Goal 4 的两件预登记**逐条被确认**，而阻断强读法的是一个**已定位、已登记、明文不在本 plan 交付面内**的活缺陷（`docs/bugs/03-…`）。这一裁定在 §7.16 / 证据 README / roadmap / STATE / 日志**五处同口径**，**不得被引用成「归因已验证」**。
6. **两份证据 JSON 的 `run` 字段都是 `p1-insight-live-01`。** 这是 `run.py` 里的**常量**，而第 2 跑按裁判规则 3 是**原样复跑**（同一条命令）—— 同一条命令给出同一个标识符是它该有的行为，不是漏改。两份文件靠**文件名**与 `at` 时间戳区分（`21:17:50Z` / `21:20:39Z`）。独立关闭审计建议把它改成从 `--out` 推导，**本轮不改代码**：改了也无法回填进已生成的这两份证据，反而会让「同一条命令、两个标识符」多出一层不一致。照实记在这里。
7. **`list-apps` 的「跑前」读数没有当场取。** 用的是仓里已有的那份记录
   （`docs/analysis/2026-08-25-0119-desk-sid-identity-probe.md`）。⇒「前后一致」这句话在本 plan 里
   **强度低于原计划**；站点零写的承重面是**请求记录器**（逐条 method + path），`list-apps` 只是旁证。

### 12.3 §7.9 的处置：**用了「追加」，没有改写**

那句话（「归因那一半没有在活端点上跑过」）活在一段标题为**活站点验证范围**的段落里，
记的是**那个 plan 那一跑的范围**，不是一处漂移 ⇒ 按起草期写死的默认动作，
在该句后**追加**结清指针，**原句一个字节未改**（`git diff` 上那一行的 `-`/`+` 共享同一前缀）。
**实跑结果与原句没有正面冲突**（原句说的是"没跑过"，本轮把它跑了），
所以**不触发**「只有正面冲突才改写」那条分支。

### 12.4 红线自证

- `git status --porcelain -- tests/gates/ .github/workflows/ missions/ docs/masterplan/DECISIONS.md` → **无输出**
- `git diff --stat -- agenerp/insight/ agenerp/inspection/` → **无输出**（本 plan 是验证，不是改造）
- `git diff --numstat -- docs/masterplan/STATE.md` → **`19  0`**（**删除列为 0**，只追加）
- `git diff --numstat -- docs/design/agents-and-roles.md` → **`4  0`**（只补指针，删除列为 0）
- 证据仓（`XM_PATH`）**未写入**；未生成任何运行时 Server Script；未改项目名 / 包名 / 命名空间

## Closure

**独立关闭审计：`needs revision` → 五条 blocking + 三条非阻塞逐条处置后收口。**
`Reviewer availability = subagent`（`docs/context/ai-autonomy-policy.md:29`）。
执行者：**独立子代理，fresh session，不带实现上下文**。

**它不是冷复跑。** 审计自己重跑了八条基线命令、**自己重施了 M1–M7 七条变异**
（文件级 `cp` 备份还原，**全程未用 `git checkout` / `restore` / `stash`**，
还原后 `diff` 为空、md5 前后相同、备份已删），逐条确认**被点名的那条判据**就是发红的那条；
并**独立复算**了两份证据 JSON 的全部数字（`chat_calls` / 账本条数 / `POST` 拆解 /
`238 × (system.overview + schema.search)` 那条算式 / usage 三项 / `total_matches_endpoint` /
`denied` / 凭据扫描）；四条红线自证也由它自己重跑。**它没有联系活站点或模型端点**。

审计确认成立的（摘要，非本文自评）：M3 的那条微妙副命题（**同一次变异下
`test_the_recorder_lets_a_whitelisted_post_through` 仍然通过**）逐字成立 ·
判定器的标签**可证地不在任何退出码路径上** · §7.9 **逐字节只追加** ·
两份证据里**没有凭据字面量** · 最容易被埋掉的两件事（**没有产出归因文本**、
**H4 的 ≤ 12 未达成**）在六份制品里**都写在明处、没有一处被开脱** ·
**没有任何 in-scope 项被降级** · `verification scope limited` 在要求的每一处都在。

### 五条 blocking 的处置（逐条，一条不挑着记）

- **F-1 收口自证顺序错了** —— §10「closure audit was independent」在审计**还没回来**时就被勾上，
  且 `## Closure` 是空的。**已改**：本节先写实，`## Closure` 落地之后才勾那三处，
  `text consistency verified` 重新自查一遍。
- **F-2 数字错了：L1 拒绝条数 run-01 不是 10 是 14。** **已改**（plan §6 H3 / `module-boundaries.md`
  §7.16 / `docs/bugs/03-…` **三处同步**）。**本文自查确认**：run-01 **14** 条
  （13 × `query.read` + 1 × `snapshot.read`），run-02 **17** 条（全部 `query.read`）。
  ⚠️ **成因照实记**：起草侧那个 10 是执行期**肉眼数控制台输出**得来的，没有用程序数一遍 ——
  同一类错误的防法是「凡是要写进文档的计数一律程序算」。
- **F-3 `最小 reasoning = 43` 的作用域写宽了。** 43 是 **run-01** 的最小值，
  两跑合计 47 条记录的最小值是 **36**（run-02 第 14 / 20 条）。**已改**。
  载重命题（**三项逐条 > 0**）经审计逐条复算**在全部 47 条上成立**。
- **F-4 roadmap 那句「一个字未改写」不精确。** 行尾那个 `）` 被右移到追加段之后
  （字符级唯一改动）。**已改**：roadmap 与 plan §10 **两处措辞同步改准**；
  并把 `docs/backlog/p1-insight-roadmap.md` 补进 Phase 4 的 `Targets`
  （**起草期漏列，执行期确实改了它**）。
- **F-5 `STATE.md` 的落地 sha 还是占位。** **已处置**：收口提交之后**追加一条回填行**
  （仓内先例 `36112c2`），`STATE.md` 仍然**只追加、不改写已有行**（红线 5）。
  ⚠️ 裁判规则 2 要求「命令原文 + 退出码 + commit sha」三者齐全 ——
  **在那条回填行落地之前，本 plan 的状态是「我认为完成，待验证」**。

### 三条非阻塞的处置

- **F-6（建议改 `run.py` 让 `run` 字段从 `--out` 推导）—— 不改代码，照实记进 §12.2 第 6 条。**
  两份 JSON 都自称 `p1-insight-live-01` 是因为它是常量，而第 2 跑按裁判规则 3 是**原样复跑**
  （同一条命令）⇒ 同一个标识符是**它该有的行为**。改了也回填不进已生成的证据。
- **F-7（H1 的「9 条全是 GET」没有独立留痕）—— 已在 §6 H1 那格标成自记事实。**
- **F-8（Goal 1 按字面只做到一半）—— 已在 §12.2 新增第 5 条逐条裁定**：
  弱读法成立、强读法不成立，本 plan **采用弱读法收口**并说清理由，
  五处制品同口径，**不得被引用成「归因已验证」**。

### 审计点名的残余风险（原样转录，不软化）

1. 样本量 **2**、单机、**CI 不可见**；CI 会重跑的只有那 **15** 条离线判据。
2. **「归因能给出一段答案」这件事，本仓证据为零**，卡在 `docs/bugs/03-…` 上；
   六处重复的那句「没有产出任何归因文本」**是唯一一道防线**，
   防的是将来有人引 §7.16 说「归因已验证」。
3. `docs/bugs/03-…` **按设计没有后继 plan**；在人裁定之前，`doc.links` 对
   **任何点名了 `Item` 的问题**都是坏的，不只洞察。
4. **D1 的三档没盖住 F1**（它落在 `agenerp/tools/documents.py`）——
   已在三处照实标注，但**下一个复用 D1 的 plan 需要先把这一档补上**。
5. 端点白名单是**起草期的枚举，不是完备性证明** —— 缓解在于记录器是**fail-closed** 的
   （白名单外当场抛 + `no_denied_requests` 判据），M3 证明了它有牙。
6. 站点零写**完全押在请求记录器上**；`list-apps` 的「跑前」值取自仓内既有记录，
   **不是 run-01 之前当场取的**，已在四处披露。
