# P1 · 解释与洞察（②端只读） — mission roadmap

> Last updated: 2026-08-24
> Sources: [`docs/masterplan/02-WBS.md`](../masterplan/02-WBS.md) §4（判据的真相源）·
> [`tests/gates/`](../../tests/gates/README.md)（判据的可执行形式）

## Purpose

这是 **`p1-insight` mission 自己的 roadmap**，由引擎在 closure 审计通过后回写。
全局阶段索引在 [`implementation-roadmap.md`](./implementation-roadmap.md)，由人维护。

P1 的目标一句话：**让 Agent 能看懂这套 ERP，并且能证明它真的看懂了。**
**②端只读**——本阶段 Agent 不写任何业务数据。

## 本阶段的三条硬约束（违反即停机，不是风格建议）

**① 判据不许只验「调得通」。**（CP9 继承项①）
退出码 0 与「跑了且过」不是一回事。P1 尤其危险：**「Agent 答对了」与
「Agent 蒙对了」在结果层面长得一模一样**。每条判据都要能区分这两者。

**② 预测在前、结果在后、逐条吻合。**（CP9 继承项②）
凡实验性质的工作项，假设**在跑之前逐字写死**，事后逐条对照，不许事后改写。

**③ 规则能覆盖的流程不 Agent 化。**（D-15）
面对任一环节先问：**「这一步的判断能不能写成确定性规则？」** 能写就写成规则。
只有输入模糊、路径不可预先枚举、或需按中间结果动态改变后续动作时，才交给模型。
**反向边界**：自然语言理解、多跳路径选择、归因叙述的组织**枚举不完**，
强行规则化会退化成脆弱的关键词匹配。判据是「路径能否预先枚举」，不是「看起来复不复杂」。

**④ 以本项目的实测为准。**（D-16）
外部基准、他人评测、厂商声明，只能作**假设的来源**，不能作**结论的依据**。
引用任何数字前先问：**「这个数字是在本项目、本数据集、本任务上跑出来的吗？」**
不是，就写成「据某处，推测……，待复验」，不写成结论。
**已发生的实例**：外部基准把 `qwen3.6-plus` 排在靠前一档，**本项目任务上 **4/6**（`门禁off 3/3` + `门禁on 1/3`）⚠️ 此数经两次更正：先记 2/6、后记 1/6，均因判定正则漏掉一种拆法，见 STATE §2 同日更正行**。

## Work Item Status

> **这是唯一的动态状态块。** 状态只在这里改。
> 顺序即执行顺序，引擎取第一个 `todo`。

- 1. 工具执行层：10 个只读契约的执行体（P1.0a）: `done`（2026-08-24，sha `35313cb`；独立收口审计 2026-08-24 通过，见 plan `## Closure`。WBS §4 第 78 行的 🔴 门禁那一半**已由人补齐**——`tests/gates/test_tool_execution_live.py`，commit `3b6d071`，`Gates-Change-Approved-By: lize`，STATE §3 `[resolved] 2026-08-24T05:49Z`。⚠️ 仍待人做：`tests/tools` 本身未进 `gates.yml` 的 `unit-and-contracts` / `lint` 两个 job。**◆ 2026-08-26 第 2 个 plan 记录（本行原有文字照实保留，⚠️ 唯一的字符级改动是行尾那个 `）` 被右移到本段之后）**：plan `docs/plans/p1-insight/2026-08-26-1618-1-doc-links-child-host-guard.md` → `completed`（三个 Phase 全 `completed`，执行项 + `Exit Criteria` + `Closure Gates` 零 `[ ]` 残留）。**表规 3 的 1–2 个 plan 预算就此用满（2/2）。** 落地内容：`doc.links` / `lineage.trace` 共用的 `scan_links()` **子表支两处站点调用各自补守卫** —— `5396e68` 把人对 C1 的裁定第 ② 条（逐字「单个宿主查失败**不整次作废**」）**只落在了主表支**，而本文件「已知的坑」逐字写着「21 个指向 `Sales Order` 的 Link 里 **14 个在子表**」⇒ **没守卫的那支是多数路径**；活站点上 `doc.links{Item, HRD-PACK-5K}` 的 14 行里 **8 行**来自子表宿主。落点节 `module-boundaries.md` **§7.24**（新增），证据 `docs/evidence/p1-insight-doclinks-guard/`。**判据先红后绿**：两条失败点判据修改前各自红在**构造的异常逐字穿透到测试外层**上（栈顶分别是 `documents.py:129` / `:139`，**不是断言不相等**）；第三条反「绿着坏掉」判据按构造修改前即绿。**变异自查 M1–M6 全部打红**（M6 是自加的额外确认，**不是补漏** —— M1–M5 五条全打红），逐条复原后 `sha256` 六次同值。**三条裁定各有选定/被否/残余风险**：① 回溯父单据失败 ⇒ **丢掉那一行**（否掉「以 `docstatus=None` 记入」—— 下游筛选逐字 `docstatus != CANCELLED` 而 `None != 2` 为真 ⇒ **已取消单据会漏出去**）· ② `scanned_link_levels` 的过度声称**改掉**（记级挪到站点调用成功之后；零命中仍记、宿主全崩不记），「既有判据不由绿转红」是**实证**的 · ③ 失败**留痕**，但**只加在 `scan_links()` 的返回上**，`doc_links()` / `lineage_trace()` 的 `Outcome.facts` 一个键不加 ⇒ 契约后置条件与活体门禁形状不变（红线 1）。verification：`check_expected_red.py` → **exit 0**（`门禁 28 项：预期红 0，绿 28，跳过 0`）· `pytest tests/unit tests/tools -q` → **exit 0**（`908 passed, 29 skipped`，基线 `903` **只增不减**）· `pytest tests/contracts tests/routing tests/context -q` → **exit 0**（`375 passed, 1 skipped`）· `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → **exit 0**（顺带清掉随 `5396e68` 进仓的 `F401 import pytest`，它本会让下一次推送的 `gates.yml` `lint` job 变红）。活站点 `doc.links` **改动前后各一跑**，两跑 `ok= True rows= 14` 且 `sha256` 逐字节相同 ⇒ 正常路径一个字未变。⚠️ **活体门禁 `tests/gates/test_tool_execution_live.py` 改动前后都是 exit 1**（H8 未命中，照实记）—— **唯一的红逐字是同一条** `test_permission_scope_produces_at_least_one_real_negative`，红因是**环境缺受限身份口令**（`AGENERP_WORKER_PASSWORD` 未设），**与 `doc.links` 无关、改动之前就红**；`[doc.links]` / `[lineage.trace]` 两个参数化 id **两跑逐字都是 PASSED** ⇒ 裁判未回归。**未为让它转绿动 `tests/gates/**` 一个字节**（红线 1），装载受限身份已登记交人。⚠️ **一个判据错觉本轮实测坐实**：`check_expected_red.py` 全绿**读不出**「活体门禁没回归」—— 该文件是 `pytestmark = pytest.mark.live` 而判定器默认注入 `-m "not live"` ⇒ 那条参数化断言一条都不会跑。⚠️ **verification scope limited**：未跑整仓 `pytest tests -q -m "not live"`（已知基线即红），未经 CI 服务端复跑。⚠️ **独立收口审计由收口审计步执行，本轮执行者不代跑、不代批、不预填结论。**⚠️ 本行的 `done` 状态与前面所有文字**一个字未改**）
- 2. 入口关口实验：门禁能否补偿模型能力（P1.0 🚪）: `done`（2026-08-24；结论 **`被削弱`** —— 弱模型 `qwen-plus` 门禁 off 0/3 → on 2/3，但强模型 `qwen3.6-plus` **无门禁** 3/3，门禁没让弱模型追上强模型。判定见 `docs/audits/p1-insight/2026-08-24-P1.0-entry-gate.md`，14 份轨迹与判定表见 `docs/evidence/p1-entry-gate/`。⚠️ 结论只覆盖这一道题、两个模型、每格 3 次有效运行，不得外推）
- 3. 模型路由 v0：OpenAI 兼容 adapter + 能力声明按任务分档（P1.1）: `done`（2026-08-24，sha `5a0f87a`；plan `docs/plans/p1-insight/2026-08-24-1457-1-model-routing-v0.md`，独立收口审计见其 `## Closure`。`agenerp/routing/` 五个模块 + `tests/routing` **132 passed, 1 skipped**；分档表落 `docs/architecture/model-management.md` **§12.5**（新增落点节），§12.3 那处「或由更强的循环门禁补偿」按 P1.0 **人侧独立复核**的判定改准。活端点冒烟跑过一次：`usage={'prompt':15,'completion':194,'reasoning':188}`，与开工前写死的预期 `reasoning > 0`（D-11）吻合。⚠️ **verification scope limited**：`tests/routing` 既不在 `commands.test` 也不在任何 CI job 里，与 `tests/tools` 同形态，**不得读成 CI 已覆盖**；已随收口在 STATE §3 追加 needs-human。⚠️ 另有两条 needs-human：`qwen3.6-plus` 的 `multi_hop` 声明建立在本项目 2/6 的实测上；本文件工作项 2 的逐格计数与下方 P1.7 警示表不一致，loop 未代改）
- 3b. **`route()` 静默换模型 —— 配置的 `AGENERP_LLM_MODEL` 被忽略**（从工作项 3 拆出，人 2026-08-26）: `done` —— 验收：`tests/unit/test_configured_model_is_the_one_used.py` **补一条不传 `requested` 的用例并绿**。详见 `02-WBS.md` 的 `P1.1-fix` 行与 STATE §3 同日条目。**plan 预算独立计**，不占工作项 3 的额度。已有草稿 `docs/plans/p1-insight/2026-08-26-1728-1-routing-honors-configured-model.md`。

  **◆ 2026-08-26 第 1 个 plan 收口记录（本行原有文字照实保留，一个字未改写）**：plan `docs/plans/p1-insight/2026-08-26-1728-1-routing-honors-configured-model.md` → `completed`（三个 Phase 全 `completed`，执行项 + `Exit Criteria` + `红线自证清单` 零 `[ ]` 残留；`Closure Gates` **只余 `closure audit was independent` 一条留 `[ ]`**，见下方 ⚠️）。**plan 预算独立计，未占工作项 3 的额度**（本行逐字如此）。
  落地内容：**`route()` 体内把 `config` 解析上提到挑档案之前**，`requested is None` 时用 `(resolved_config.model or "").strip() or None` 顶上 ⇒ **`AGENERP_LLM_MODEL` 从此就是被点名的那个模型，点不动就明确失败，绝不换一个跑**。`D-1` 选 (A)，(B)/(C)/(D) 三条备选各有逐字否决理由。落点节 `module-boundaries.md` **§7.25**（新增，七小节），`model-management.md` §12.5 两处限定，证据 `docs/evidence/p1-routing-configured-model/`。
  **B1 复现前后两输出**：改动前 `config.model = qwen3:14b | adapter.model = qwen3.8-max`（**配了 A 调了 B，无声**）→ 改动后 **两边相等**。
  **改动代价与 plan B5 的预测逐字吻合**：只改 `route()` ⇒ 六目录 `15 failed, 1284 passed`，**15 条全部在 `tests/routing/test_router.py`**，唯一成因是该文件夹具的 `model="unused"` 字面量（**它编码的正是本缺陷**）；改成 `model=""` 后 `tests/routing` 回到 `170 passed`，`git diff … | grep -c '^-[^-]'` → **1**（既有断言一条未改、未删、未放松）。
  **WBS `P1.1-fix` 验收逐字成立**：`tests/unit/test_configured_model_is_the_one_used.py` **纯新增**两条**不传 `requested`** 的用例（参数化成功面 5 条 + 未知模型失败面 1 条），`6 passed` → **`12 passed`**，`grep -c '^-[^-]'` → **0**（既有 6 条一字未改）；**两条在改动前都是红的**（`4 failed, 1 passed` / `DID NOT RAISE`）⇒ 它们确实钉在缺口上，**不是「让现有用例继续绿」**。
  verification：`check_expected_red.py` → **exit 0**（`门禁 29 项：预期红 0，绿 29，跳过 0`）· `pytest tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments -q -m "not live"` → **exit 0**（`1314 passed, 23 skipped, 7 deselected`，基线 `1299` **只增不减**）· `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → **exit 0** · `pytest tests/routing -q` → **exit 0**（`179 passed, 1 skipped`）。
  ⚠️ **五条判据在改动前就是绿的，照实说**：P5（`requested` 压过 `config.model`）/ P6 / P6b / P6 后半 / P7 —— 旧实现**从不读 `config.model`** ⇒ 这些语义在它那里**真空成立**。**没有为凑「先红后绿」去改它们**；它们的有效性由变异 **M2 / M3 / M6b** 坐实。plan 写死「必须打红」的只有 **P8 / P9**，那两条都红。
  ⚠️ **变异表 11 格里 2 格没按预期形态打红，原样留在 §7.25.7 未修饰**：**M6**（`model=profile.name` → `model=None`）对 P4 **exit 0**（点名分支下两值恰好相同），补的 **M6b** 改判 P6 → **exit 1**（整个 `tests/routing` `32 failed, 147 passed`）；**M8**（表里删掉 `qwen3:14b`）红在**收集期**而非目标断言，且**对 WBS 验收文件 exit 0（`10 passed`）** —— 它按表参数化，表缩小时用例数从 12 掉到 10 而全绿 ⇒ **「遍历一张表」的参数化判据对「表本身变短」是盲的**。这是普遍形态、非本 plan 局部问题，**交人**（重开事件写在 §7.25.7）。
  ⚠️ **D1（`AGENERP_LLM_MODEL` 配错名字回 502 而非 503）交人** —— 本轮**亲自实测**（未采信 plan 起草期的数）：`STATUS = 502`、文本逐字 `点名的模型 'typo-model' 不在候选档案里；候选是 ['fake-explainer']`。修法面在 `agenerp/serve/**` = 工作项 10（`P1.8a`，plan 预算 `2/2` 已满）⇒ 本 plan 不动，已追加进 `STATE.md` §3。**本次改动把它的暴露面放大了**：改之前配错名字根本不触发这条路（静默换模型），现在它是点名分支的正常失败态 —— **后者远好于前者，但状态码仍是错的。**
  ⚠️ **执行期 HEAD 移动了**：起跑基线 `433d2ca`，执行中人侧落了 `42fa183` / `9be3007`，HEAD 变成 `9be3007`。**本 loop 追加进 `STATE.md` §3 的那条 needs-human，在人侧提交时正在 working tree 里，被一并带进了 `9be3007`** ⇒ 那 8 行**署在人的 commit 名下，内容是 loop 写的**。仍满足红线 5（`git show 9be3007 -- docs/masterplan/STATE.md | grep -c '^-[^-]'` → **0**），**但署名不准这件事不掩盖**。`missions/p2-views.json` 是人侧 `9be3007` 的产物，本 loop 未写、未提交。
  ⚠️ **独立收口审计未做** —— 本轮执行环境不具备独立子代理、人未在场，执行者做的是**单人冷复跑**；`closure audit was independent` 这条 gate **留 `[ ]`**，详见 plan `## Closure`。
  ⚠️ **verification scope limited**：未跑整仓 `pytest tests -q -m "not live"`（**已知基线即红**，`gates`×`tools` 环境泄漏已单列立案）；未跑 `-m live`（plan 的 Prereqs 逐字不要求）；未经 CI 服务端复跑。
  ⚠️ 本行的原有文字与前面所有内容**一个字未改**，仅把状态 `todo` 改成 `done` 并在末尾追加本段。
- 4. 上下文层 v0：即时上下文注入 + 会话落 DocType（P1.2）: `done`（2026-08-24；plan `docs/plans/p1-insight/2026-08-24-1457-2-context-layer-v0.md`。`agenerp/context/` 三个模块 + 会话 DocType **声明** + `tests/context` **53 passed**（WBS §4 P1.2 的验收原文 `pytest tests/context -q` 退 0；首次收口时 51 条，补 M9 判据后 53 条）。落点节 `module-boundaries.md` **§7.7**（新增），`context-and-memory.md` §8.2 的 ① / ② 两行补上落点指针（③ / ④ 一个字未动）。变异自查 **M1–M8 八个全部被打红**，无一需要就地补断言；**独立关闭审计**（sha `3337d69`）另出 A1–A5 五个变异，A5 打出一处判据缺口（② 档只有常量声明断言、没有行为断言），已回 EXECUTE 补上正向 + 反测两条并登记为 **M9**，复跑确认 M9 被打红，判据 **51 → 53 passed**。⚠️ **只做 ① 即时与 ② 会话两层**，③ 记忆 / ④ 检索是起草期显式定界的 Non-Goals，重开事件见 plan §9。⚠️ **会话在活站点上尚未建表** —— 那是风险档 L3 强制人批的动作，本 plan 未发出任何 DDL；已随收口在 STATE §3 追加 needs-human（含手工回滚命令原文）。**`closure audit was independent` 已勾** —— 独立关闭审计已于 sha `3337d69` 补做，结论 `issues`（见 plan §12.8）；⚠️ 但 **A5 的补齐（M9 两条断言）做在那轮审计之后、只经执行者自查**，不得读作「补齐也被独立复核过」。⚠️ **verification scope limited**：`tests/context` 在**首次**收口那一刻既不在 `commands.test` 也不在任何 CI job 里；此后由另一条工作线的 `b0ad632` 接进 CI 的 `unit-and-contracts`，本轮的 53 条会被 CI 复跑，**但那笔改动不属本 plan**）
- 5. 导航的编排行为：permission.scope 开场自动注入（P1.3）: `done`（2026-08-24，权威 sha `e3764fc`；⚠️ **代码产物的首次进仓 commit 是人的 CI 提交 `659b41f` / `1c61089`**——同一工作树上被 `git add` 扫进去的，归属照实记在 plan `## Closure` 的表里；plan `docs/plans/p1-insight/2026-08-24-1601-2-navigation-orchestration-v0.md`。`agenerp/orchestration/` 三个模块（`opening.py` / `navigation.py` / `circuit.py`）+ `tests/tools/test_navigation.py` **32 passed**（WBS §4 第 82 行的验收原文 `pytest tests/tools/test_navigation.py -q` 退 0，其中 `test_opening_injection_really_happens_on_the_site` 就是「有一条断言开场注入真的发生」那一条，判据落在 `FakeSite.requests` 上、不落在标志位上）。落点节 `module-boundaries.md` **§7.6a**（新增）+ §7.4 末尾追加熔断落点，且 §7.6 那句「熔断仍未做…归 P1.0 的控制循环」的**失效归属已改准**。变异自查 **M1–M8 八个全部被打红**；⚠️ **M6 第一轮是绿的**（相等断言挡不住「装配路径上写死成正确值」），已就地补同一性断言与「不许凭空补一个」两条，M6a/M6b 复跑均 exit 1。§6 的 **H1–H4 四条全部吻合**，假设一个字未改、题一道未换。⚠️ **导航数字是本仓夹具实测，非站点实测**（① 题 on 1 次 / off 5 次 `execute()`），与 owner doc 里 Spike 01/02 的「35 次」「35 → 1」**不是同一个量，不得互相引用为佐证**；且**站点请求那一栏 on 组净亏**（10 对 5），「更省」只在 `execute()` 次数这一栏成立。⚠️ **熔断尚未接到任何真实控制循环上**（接线归 P1.4），§7.4 的「写入审计」那一行同样未落地。⚠️ `tools_readonly.py` 的 `injected_at_session_start` **仍是调用方自证的软断言**，本期加强的是编排面不是契约面。⚠️ **独立关闭审计未做** —— 本轮执行环境不具备独立子代理，`closure audit was independent` 这条 gate **留白**，详见 plan `## Closure`。⚠️ **verification scope limited**：`tests/tools` 已在 CI 的 `unit-and-contracts` / `lint` 里（`b0ad632`，不属本 plan），但仍不在 `missions/p1-insight.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到；已随收口在 STATE §3 追加 needs-human）
- 6. 解释 Agent + 证据充分性门禁（P1.4）: `done`（2026-08-24，基线 sha `6b07889`；plan `docs/plans/p1-insight/2026-08-24-1755-1-explain-agent-and-evidence-gate.md`。`agenerp/explain/` 三个模块（`gate.py` / `loop.py` / `__init__.py`）+ `tests/unit/test_explain_loop.py`（11 条）+ `tests/unit/test_evidence_gate_single_hop_body.py`（5 条）+ `tests/unit/explain_fakes.py`。`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**（`预期红 0，绿 11` · `389 passed`，基线 373 → +16）；`python3 -m pytest tests/tools -q` → **exit 0**（`81 passed, 12 skipped`，与基线逐字相同，`tests/tools/**` 一个字未改）；`ruff check ...` → **exit 0**。**循环形状继承 `tools/experiments/p1_entry_gate/loop.py`，换掉四个零件**（模型侧 `routing.route()` / 开场侧 `orchestration.open_session()` / 会话侧 `context.session` / 熔断侧 `DenialBreaker`），实验设施一行未动。**门禁在两处求值、事实采集面只有一份**（D2），同源性由 `EvidenceSurface` 的 `surface_id` + `uses` 留痕可断言。落点节 `module-boundaries.md` **§7.8**（新增），**五处失效归属一并改准** —— 其中包括工作项 5 那条「⚠️ 熔断尚未接到任何真实控制循环上 / 写入审计那一行未落地」：**两条均已由本工作项结清**（上一行工作项 5 的收口记录按追加式账本保留原文，不改写）。变异自查 **M1–M8 八个全部被打红，无一需要补断言，因此没有 M9**。§6 的 **H1–H4 全部吻合**，假设一个字未改。H4 活端点跑**一次**（`docs/evidence/p1-explain/`）：`usage` 三项均 > 0，七次调用账目**逐次**对得上端点自报的 `raw["usage"]`；**L3 在真实数据上抓到了那张外协入库单** `MAT-SCR-2026-00001`。⚠️ **那一跑没走到 ② 门禁的拒绝路径、也没触发熔断**（模型第一次作答就已取证充分；Administrator 不撞 403）——那两件由 `tests/unit` 判据证明，不由那一跑证明。⚠️ 单跑 **45,195 token**，**低于** 本文件 P1.7 节记的 9.7 万–12.8 万；**不修饰成「优化了」**，本 plan 没做成本工作，成因未测量。⚠️ **WBS §4 P1.4 的 🔴 `tests/gates/test_evidence_gate_blocks_single_hop.py` 本工作项未创建、也未声称已满足**（红线 1）——交付的是它的**断言体**与交接说明，由**人**按 P1.0a 先例按路径加载；已在 STATE §3 追加 needs-human。⚠️ **独立关闭审计未做** —— 本轮执行环境不具备独立子代理，`closure audit was independent` 这条 gate **留白**，详见 plan `## Closure`。**补记（2026-08-24）：该审计已由独立会话补做，结论接受收口** —— 前一句「未做」是执行当轮的原状，照实保留、不改写；补做侧复跑 `check_expected_red.py`（`预期红 0，绿 11`）/ `pytest tests/unit -q`（`389 passed`）/ `pytest tests/tools -q`（`81 passed, 12 skipped`）/ `ruff check ...` / `pytest tests -q -m "not live"`（`849 passed, 12 skipped, 21 deselected`）**五条均 exit 0**，与本行数字逐字吻合；红线四个 pathspec 无输出、`STATE.md` 只追加。记录见 plan `## Closure` 末尾的「独立关闭审计补做记录」一节。⚠️ `lineage` 档放行 `qwen3.6-plus` 那条 `[open]` **不因本工作项落地而消失**，本工作项不代人处置）
- 7. 巡检器（纯规则引擎）+ 洞察 Agent（归因）（P1.5，见 D-15）: `done`（2026-08-24，基线 sha `04aa9ea`；plan `docs/plans/p1-insight/2026-08-24-1755-2-inspector-and-insight-agent.md`。**D-15 落成代码**：巡检是代码（`agenerp/inspection/`，四个模块，**零 LLM**），归因才是模型（`agenerp/insight/`，两个模块，走 P1.4 的 `agenerp.explain.explain`，**不另起循环**），两者分开不合并。判据 `tests/unit/test_inspection_rules.py`（16 条）+ `tests/unit/test_insight_attribution.py`（9 条）+ `tests/unit/inspection_fakes.py`。`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**（`预期红 0，绿 11` · `414 passed`，基线 389 → +25）；`python3 -m pytest tests/contracts -q` → **exit 0**（`151 passed`）；`python3 -m pytest tests/tools -q` → **exit 0**（`81 passed, 12 skipped`，与基线逐字相同）；`ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → **exit 0**。**规则是数据不是代码**（D1：声明式数据 + 有限算子），装载器**未知键与缺 `test_case` 一律拒载**且 `test_case` 会被引擎真跑。**消融跑两个数据集**：固定测例（由 `agenerp/seed/` 派生，一行数据未手写）命中 `on_hand = 1010.0`（`== EXPECTED_BACKLOG_QTY`）；换过 `INHOUSE_QTY`/`SUBCON_QTY`/`DELIVERY_QTY` 三个参数的第二个数据集命中 **900.0** —— 数随数据集变；抽掉该规则 → 零命中，把 `trigger.value` 由 `0.5` 改到 `10.0` → 也零命中。**「零 LLM」判在两个可观测量上**：进程级探针（`ChatAdapter` 构造面整体替身）+ **阳性对照**，以及全新解释器里 `import agenerp.inspection` 之后 `agenerp.routing` **不在 `sys.modules`** —— 巡检器**根本没有模型接缝**。落点节 `module-boundaries.md` **§7.9**（新增，含 D1–D4 与「**巡检规则 ≠ 行业包制品**」一句），`agents-and-roles.md` §5.1 **只补落点指针**（10 行纯新增，§5.0 ② 结论一个字未动）。**活站点巡检一次 → exit 0**，命中与离线夹具逐字一致（`received 2000` / `issued 990` / `ordered 1000` / `on_hand 1010`）。变异自查 **M1–M8 + M9–M11 + M12 全部被打红**；⚠️ **M7 第一轮是绿的**（装载器静默丢弃未知键 → 夹带的单号躲过只判序列化形态的结构判据），已就地补两条断言（结构判据**源声明与装载后两侧都判** + **未知键拒载**）并登记为 **M12**（M9–M11 已被 Phase 2 占用）。⚠️ **未交付行业包 v0**：最小规则集只有**一条**，是**引擎自带的判据夹具**，**不是行业包制品**；`rule.lookup` 的报错行为**未翻转**（重开事件仍是 P1.6）；`anomaly.scan` / `benchmark.compare` **仍未实现**（不在十个只读契约里）。⚠️ **WBS §4 P1.5 的两条 🔴 门禁 `tests/gates/test_insight_rule_ablation.py` 与「巡检器零 LLM」本工作项未创建、也未声称已满足**（红线 1）—— 交付的是它们的**断言体**与交接说明，由**人**按 P1.0a 先例按路径加载；已在 STATE §3 追加 needs-human。⚠️ **归因文本的质量本工作项没有任何判据**（判自由文本要先跑通 24 条人工标注），**归因那一半也没有在活端点上跑过** —— 不得读成「洞察 Agent 已验证」。⚠️ **D3 的残余风险实测确认**：命中 `subject` 里的物料号 `HRD-PACK-5K` 是三段全大写数字，落进 `gate.py` 的 `DOC_NAME`，于是 L1 把它当成「问题点名的单据」；误报方向是**更严**，本工作项不擅自绕开。⚠️ **独立关闭审计未做** —— 本轮执行环境不具备独立子代理，`closure audit was independent` 这条 gate **留白**，详见 plan `## Closure`。**◆ 2026-08-25 结清记录（本行原有文字照实保留；⚠️ **唯一的字符级改动是行尾那个 `）` 被右移到本段之后**—— 追加写在同一个括号内，独立关闭审计逐字符比对后要求把「一个字未改写」这句措辞改准，已改）**：上面那句 ⚠️「**归因那一半也没有在活端点上跑过**」**已由第 2 个 plan** `docs/plans/p1-insight/2026-08-25-0225-2-insight-attribution-live-run.md` **结清**，落点节 `module-boundaries.md` **§7.16**，证据 `docs/evidence/p1-insight-live/`。**跑了两次**（第 2 次是原样复跑），脚本两跑均 exit 0，六项结构化判据两跑全绿：命中非空 · 命中逐字未改写 · 账本条数 == `chat()` 被调次数（**两数来自不同采集面**）· 取证轨迹非空可枚举 · **零白名单外站点请求** · 证据无凭据字面量。八条基线命令全部 exit 0（`tests/unit` **599 → 614**，`tests/routing` **逐字不变**，本轮新增 **0** 个 `agenerp/**/*.py`）。变异自查 **M1–M6 逐条被打红**；⚠️ **M7 是变异自查当场发现的缺口并就地补的**（`evidence_trace_enumerable` 改成恒真 → 原 14 条判据全绿）。⚠️⚠️ **最重要的一句，不得被读松**：**这一跑没有产出任何归因文本** —— 两跑 `accepted = false`、`answer` 为空，`docs/evidence/p1-insight-live/` 里一段归因文本都没有。已证的只有「巡检 → 题面 → 取证 → 门禁这条链在真环境里走得通、零越权零写、账目对得上」；**「归因能给出答案」这半仍未证**，成因是一个已登记的活缺陷 —— `doc.links` 撞上 Single DocType（`Quick Stock Balance`，`issingle = 1`）直接 HTTP 500，L1 要的证据在本站点上取不到（`docs/bugs/03-…` + `STATE.md` §3 needs-human，**本 plan 不改它**）。⚠️ **判定器在归因题族上一个标签都没观测到**（`answer` 为空，`judge_one("")` 指名抛 `JudgingError`）⇒「判定器能判归因」这句话**本仓仍无任何实证**。⚠️ **H4 的「单次归因 ≤ 12 次模型调用」不吻合**：两跑 **25 / 22** 次，两次都超，按起草期写死的处置记不吻合、照实落账、照常收口（D-18 记账不拦截），**12 这个数一个字没改**。⚠️ **verification scope limited**：两次活跑只在本机、CI 完全没有覆盖；CI 复跑得到的只有那 15 条离线判据。⚠️ 本行的 `done` 状态与前面所有文字**一个字未改**（该 plan §3 Non-Goal 9 明文禁止））
- 8. 行业包 v0（离散制造），每条规则带 test_case（P1.6）: `done`（2026-08-24，基线 sha `928a888`，实现 sha `6682b68`；plan `docs/plans/p1-insight/2026-08-24-2109-1-industry-pack-v0-discrete.md`。**交付的是「包在盘上、校验器判得动它」，不是「行业包已装载进工具面」**：制品 `industry-packs/discrete/pack.json`（**三条**规则，每条带 `test_case`：成品积压 / 外协发出未收 / 订单已关闭却少发），装载面 + 校验器 `agenerp/packs/`，CLI `python3 -m agenerp.packs validate --pack discrete`，判据 `tests/unit/test_industry_pack.py`（**39 条**）+ 坏包夹具 `tests/unit/pack_fixtures/`。`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**（`预期红 0，绿 11` · 414 → **453 passed**）；`python3 -m pytest tests/contracts -q` → **exit 0**（`151 passed`）；`python3 -m pytest tests/tools -q` → **exit 0**（`81 passed, 12 skipped`）；`ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → **exit 0**；`python3 -m agenerp.packs validate --pack discrete` → **exit 0**。**四种输入四种可区分的退出码**（`0` 健康 / `3` 查无此包 / `4` 缺 `test_case` / `5` 测例跑不过，`2` 留给 argparse），且消息各自指名到具体对象。**校验器逐条真跑 `test_case`**，「翻转 `expect_hit`」与「摘掉 `test_case`」两种变异**逐条各施加一次含最后一条**。落点节 `module-boundaries.md` **§7.10**（新增，含 D1–D5 与被否决的备选、E1 的算子缺口对照表、本期表达不了的三类规则）；**三处失效归属改准**（`agents-and-roles.md` §5.1 / `module-boundaries.md` §7.9 / `open-questions.md` #5 的「格式」那一半），`context-and-memory.md` §8.6 **只补落点指针**。变异自查 **M1–M8 八个全部被打红，无一需要补断言，因此没有 M9**；其中 M4 由**阴性对照**打红（消融对它是绿的）、M5 由**第二个数据集**打红、M8 **只被子进程判据打红**（函数级对它是绿的）。§6 的 **H1 五格里四格吻合、R3 一格部分吻合**（预测缺 `equals`，实际缺的是同族的 `not_equals`），预测表原文保留未改。⚠️ **`rule.lookup` 未接线**：它仍然指名报错，理由从「没有包」变成「包在盘上、未接线」；翻转会让 `tests/gates/test_tool_execution_live.py` 的一条由绿转红（那是裁判，红线 1），**接线由人裁定**，已在 STATE §3 追加 needs-human。⚠️ **外协那条规则未在真实数据上验证过命中** —— 种子外协链完整（发多少收多少），两侧零命中是正确行为，验的只是「它不误报」。⚠️ **消融判据是恒真的那一侧**，发现力由每条规则的阳性/阴性对照证明。⚠️ **活站点核对（H4）实测「部分一致」**：`finished-goods-backlog` 两侧逐字一致（1010.0）、外协两侧零命中，但 `closed-order-short-delivered` **离线命中 10、站点零命中** —— **D-12 预言的失败形态被抓到**（站点上 `Sales Order.status` 是 `To Deliver and Bill`，离线写的是 `Closed`）。**规则一个字没改去迁就站点**；已记 `docs/bugs/02-…`，归属（种子装载面）交人，见 STATE §3。⚠️ **不做的三件事是显式定界不是遗漏**：`thresholds` / `terminology` 两个顶层块 · 行业包分发机制（P5）· `anomaly.scan` / `benchmark.compare`（不在十个只读契约里）。⚠️ **WBS §4 P1.6 行的验收命令字符串**（`python` → `python3`）定稿证据行已落 STATE §2，但 `docs/masterplan/` 已有行只有人能改（红线 5），**loop 未代改**。⚠️ **独立关闭审计未做** —— 本轮执行环境不具备独立子代理，`closure audit was independent` 这条 gate **留白**，详见 plan `## Closure`）
- 9. **单次解释成本记账**（记账但不拦截，D-18）（P1.7）: `done`（2026-08-24，基线 sha `f24e351`；plan `docs/plans/p1-insight/2026-08-24-2109-2-explain-cost-accounting.md`。**一条 WBS 行上两个交付面，判据分两个文件**（D-18 逐字「两者的判据分开写，不许合并」）：**账本** `agenerp/explain/ledger.py`（`CallEntry` / `CallLedger`）—— 一次模型调用一条记录，三项 token 分开记 + **端点自报的原始数字另留一组**，一次解释一份汇总（`Usage.plus()` 折叠，不自己写加法）；**失控闸** `agenerp/explain/loop.py` 的 `MAX_TOOL_CALLS = 32` + 专属停止原因 `STOP_RUNAWAY = "tool-call-runaway"`。判据 `tests/unit/test_explain_cost_ledger.py`（27 条）+ `tests/unit/test_explain_runaway_guard.py`（11 条）+ `tests/unit/test_explain_cost_accounting_body.py`（12 条，🔴 断言体，§A / §B 两节）。`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**（`预期红 0，绿 11` · 453 → **503 passed**）；`python3 -m pytest tests/contracts -q` → **exit 0**（`151 passed`）；`python3 -m pytest tests/tools -q` → **exit 0**（`81 passed, 12 skipped`）；`ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → **exit 0**；`python3 -m pytest tests/routing -q` → **exit 0**（163 → **164 passed, 1 skipped**）。**账本的采集面只有一处**：`ExplainLoop.run()` 里那**唯一一个** `adapter.chat(...)` 调用点的**两条出口**，写在分支判断之前 —— 四条循环出口没有一条绕得过去（计数探针：`chat()` 被调次数 == 账本条数，五个出口各一例，含经由 `agenerp.insight` 进来的那条）。**异常出口照样记账**：给 `RoutingError` 加了一个**不带类型依赖的可选 `usage: dict`**（`errors.py` 不 import 本包任何模块是硬约束，挂 `Usage` 会造成 adapter ↔ errors 循环 import），由 `adapter.py` 三处抛出点注入端点原始 usage；端点没回包时三项记 0 且 `endpoint_*` 记 `None`（**「不知道」不写成「对得上」**）。**失控闸的计量对象是「模型发起的工具调用数」而不是 `execute_calls`**（后者在未知工具上早返回，编造工具名的跑飞模型会让它恒为 0 —— 已有判据实测该形态下 `execute_calls == 0` 而闸门照样截住）；默认值 32 的**两段算术**：`8 × 4`（P1.4 实测 `execute_calls == 8`，本项目唯一可引用的数字）且**严格大于** `MAX_TURNS = 25`（下界 26，取等号会让 `max-turns` 在产品默认路径上永不可达，那正是 D-18 禁止的合并）。落点节 `module-boundaries.md` **§7.11**（新增），**五处「成本上限」drift 改准**（`model-management.md:55` / `:213` + **三处代码孪生句**：`capabilities.py` / `adapter.py` / `loop.py` 模块头，均**仅注释**）。变异自查 **M1–M8 八个全部被打红，无一需要补断言，因此没有 M9**。§6 的 **H2 / H3 / H4 / H5 全部吻合**；**H1 ①b 不吻合**（预测「空回答路径账本系统性偏低」，实测**不偏低** —— 本 plan 把前提改掉了），预测原文保留未改，该条转为守护性回归。**活端点跑一次**（`docs/evidence/p1-cost/`）：8 次调用，`total_matches_endpoint` **8/8**、`reasoning_matches_endpoint` **8/8**、三项均 > 0，实测 **53,041 / 5,538 / 3,098 / 58,579**。⚠️ **不与 P1.4 的 45,195、不与本文件下方记的 9.7 万–12.8 万作优劣比较** —— 三次不同的解释，本 plan 没做任何成本工作（D-16）。⚠️ **那一跑没走到异常出口、没触发失控闸**（`stopped == "answered"`、`model_tool_calls == 9`）—— 那两件由 `tests/unit` 判据证明，不由那一跑证明；**一跑不是成本分布**，定阈值仍需采样计划。⚠️ **没有设任何成本阈值、没有任何拦截分支**（D-18）。⚠️ **WBS §4 P1.7 的两条 🔴 门禁本工作项未创建、也未声称已满足**（红线 1）—— **一条有名**（`tests/gates/test_explain_cost_accounting.py`）、**一条未命名**（`02-WBS.md` 第二个 🔴 没有给文件路径），**两条的断言体都已交付**并分成 §A / §B 两节，由**人**按 P1.0a 先例按路径加载；已在 STATE §3 追加 needs-human。⚠️ **未声称满足 WBS「工具调用轮数上限」的字面措辞** —— 本期按「工具调用」那一维实现，`DECISIONS.md` 一个字未改，重读留痕在 §7.11。⚠️ **本文件上方「成本上限须按 reasoning token 计」那一句与本条并存、会误导**，loop 未代改（该段是 mission roadmap 的静态说明），已在 STATE §3 点名。⚠️ **独立关闭审计未做** —— 本轮执行环境不具备独立子代理，`closure audit was independent` 这条 gate **留白**，详见 plan `## Closure`）
- 10. **解释服务的 HTTP 面**（P1.8a，见 D-19）: `done` —— ⚠️ **人侧实测把 `done` 改回 `todo`（2026-08-25）**：验收两条**都不成立**：① `pytest -m live tests/gates/test_explain_service_live.py` **跑不了**（栈起不来）② **零依赖启动门禁不绿** —— `docker compose down -v` 后干净重建，`frontend` 无限 `Restarting`，报 `host not found in upstream "backend:8000"`。详见 STATE §3 同日条目 · **⚠️ 上面那句「验收两条都不成立」是 2026-08-26 之前的事实，现已作废（人 2026-08-26T04:20Z 复核）**：① `AGENERP_LIVE=1 … pytest -m live tests/gates/test_explain_service_live.py` 对活站点直跑 ⇒ **`6 passed in 4.10s`** ② 零依赖启动门禁 CI 最近一次 **`L2 慢门禁（零依赖启动）: success`**；本机判定器 **28 项全绿零跳过**。③ 当初回退的直接起因（`frontend` 起不来 / 间歇不可达）已由 **工作项 10b** 修复并验证 —— 三次连绿 `182ef2a`/`cb3ad79`/`aae1843`（run `32924757237`/`32924918686`/`32925450458`，人逐个 `gh api` 核过：全 success 且全在修复 commit 之后）；`frontend` 现 **Up 19 小时 healthy**。**是人把它改回 `todo` 的，现在由人改回 `done`，与 loop 的状态源权限无关。**

  **◆ 2026-08-25 第 2 个 plan 结清记录**（plan `docs/plans/p1-insight/2026-08-25-1423-1-explain-service-compose-and-same-origin.md`，落点节 `module-boundaries.md` **§7.21** + `system-baseline.md` **§14.11**；上面那段第 1 个 plan 的收口文字**一字未改**）：

  - **WBS §4 P1.8a 的验收原文是两条**：`pytest -m live tests/gates/test_explain_service_live.py` 退 0 · **零依赖启动门禁须仍绿**。**逐条说清楚交没交付**：
    - ✅ **第二条完整交付**：`down -v` → `docker compose up -d --wait --wait-timeout 900` → **exit 0**，墙钟 **100 秒**，十个长期运行服务全 `running`、七个有探针的全 `healthy`（含新增的 `agenerp-serve`）。`env -i … docker compose config -q` → exit 0。`tests/unit/test_compose_zero_dep.py` **14 条全绿，一条未改松**。D-19 那句「新服务必须也能在『一个 AI 变量都不配』时起得来」**在一次真正的冷起上成立**。
    - ⚠️ **第一条只交付了它的前提，没交付它「退 0」**。交付的是**加载所需的活栈与同源那一跳**：`agenerp-serve` 进了 compose、nginx 有了 `location /agenerp/`（经 `frontend` 对外口实测 `GET /agenerp/health` → **200**，`/api/method/ping` 仍 **200**），断言体默认基址已与 `default_base_url()` 同源。**断言体实测 `5 passed, 1 skipped`，exit 0。**
    - ⚠️⚠️ **那份门禁在本 plan 之后仍然是红的，红因收窄但没消失**：第 4 条（`test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to`）在 **503 分支**上**自带** `pytest.skip`（`tests/unit/test_explain_service_body.py:223`），而 `gates-l2-live` 起栈时一个 AI 变量都不配、契约又逐字是「全部绿、零 red、零 skip」⇒ **必然红在那一条 skip 上**。**六条里五条转绿，第 4 条 skip。**
  - **状态为什么定成 `done` 而不是继续 `todo`** —— 三条一起成立才定的：① **表规 3 的预算 2/2 已满**（拆行 commit `ec74161`「docs(wbs): P1.8 拆成 a/b 两行」是**人**做的，author `lize`）⇒ 留 `todo` 会让引擎去起第 3 个 plan，而**此后的后继只能由人在 `02-WBS.md` 拆行 / 加行**（红线 5，loop 无权）；② **本工作项 in-scope 的活全部做完**，没有一项被降级成 deferred；③ **剩下的两件事都在红线内、都归人**——`tests/gates/**` 本体（红线 1，⚠️ **人已于 `f09b8f0` 自行提交了它**，本 plan 一个字未碰）与那条 skip 的两条出路（① 改 `.github/workflows/**` = 红线 2；② 改 503 分支的判定口径）。⇒ 定 `done` 记的是「**loop 这一侧做完了**」，**不是**「WBS 那条验收命令已经退 0」。**后者尚未成立，本行不假装它成立。**
  - **交付物**：`docker-compose.yml` 增 `agenerp-serve`（复用 `x-erpnext-image` + `x-ai-env`，**不复用 `x-backend-defaults`、不挂 `sites`/`logs` 卷**、**无 `ports:` 块**、探针打 `/agenerp/health`、`depends_on` 只有 `create-site`）+ `frontend` 增两条（nginx 模板 `:ro` 挂载、`depends_on: agenerp-serve`，**服务名 / `ports:` 那一行 / `FRAPPE_SITE_NAME_HEADER` / 三条既有 `depends_on` 一个字未动**）· `tools/nginx/frappe.conf.template`（上游模板副本 + 两段哨兵包围的本仓内容）· `agenerp/serve/__main__.py` 增 `HOST_ENV` + `resolve_host()`（**默认仍是回环**，`app.py` **一行未改**）· `tests/unit/test_explain_same_origin.py`（**21 条 / 九族判据**）· `tests/unit/test_explain_service_body.py` 的一处 `Fix`（默认基址）。
  - **七条裁定**（§7.21 `D-b-1`…`D-b-7`）：同源那一跳选 **(A) 在本仓维护一份上游 nginx 模板副本**——(B)/(D) 的否决**用执行期自己的探针实测**（(D) `nginx -t` 退 **1**；(B) `nginx -t` 退 **0** 但第二个 server 块被**静默丢弃**，即「配置测试全绿、反代根本不存在」）；(A) 胜过 (E) wrapper 的决定性理由**不是维护代价而是可判定性**（(E) 落盘的是一段会去改别的文件的 shell，判据⑧ 离线无从判起）。包送达选 **bind mount + `PYTHONPATH`**；回程地址 **`http://frontend:8080` 字面写死**（写成 `${AGENERP_SITE_URL:-…}` 会在 `gates-l2-seed` 的 job 级 `env:` 下让容器**打自己**，而 `/agenerp/health` 恒 200 ⇒ **绿着坏掉**）；**正式重开 §7.20 `D-a-1`** 的监听地址一格（新变量 `AGENERP_SERVE_HOST`，**默认仍是回环**，只收 IP 字面量、非法值当场失败不静默回退）。
  - **验证（全绿）**：`python3 tools/gates/check_expected_red.py` → exit 0（`门禁 26 项：预期红 0，绿 26，跳过 0`）· `python3 -m pytest tests/unit -q` → **`777 passed, 6 skipped`**（基线 756，**只增不减**）· `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` → `456 passed, 13 skipped`（**与基线逐字相同**）· `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → `All checks passed!` · `git diff -- pyproject.toml` → **0 行**（零新增依赖）· `git ls-files --others --exclude-standard -- 'agenerp/**/*.py'` → **0 行**（零新增模块）。**§6 的 H1–H11 十一格全部吻合**，预测原文一个字未改。
  - **变异自查 M1–M10 逐条被打红**，一条未跳过、一条不需现补断言，复原后 `sha256` 逐字节 `RESTORED OK`。⚠️ **M7 只打红五个参数化里的四个**——没被打红的那个恰好是 `AGENERP_HTTP_PORT=18080`，它**等于**被改回去的那个写死值；同一处漂移在恰好匹配的环境里就是看不见的，**照实记，不修饰成「全打红」**。
  - ⚠️ **M8 之后出现一次未能复现的故障**：`frontend` 重启循环、日志逐字 `[emerg] host not found in upstream "backend:8000"`。按裁判规则 3 **原样复跑** `up -d --wait --wait-timeout 900` → **exit 0** 全部恢复 ⇒ 记为「**不可复现**」，**不猜根因**。报错指名的是**上游模板自己那一行**，不是本仓加的那个上游。
  - ⚠️ **`client_from_sid()` 的活体那一半只证到一半**：真 `sid` → **503**、伪造 `sid` → **401**，两者之差证明服务确实拿调用者的 `sid` 去站点认了人；但**「服务解析出的是谁」本轮没有直接观测到**（那个用户名只在 200 分支的 `payload["user"]` 里）。「认的就是发请求那个人」目前是**推断**，**不是实测**，已在 STATE §3 追加 needs-human。
  - ⚠️ **verification scope limited**：未跑整仓 `pytest tests -q -m "not live"`；**未经 CI 服务端复跑**（三个 L2 job 在 runner 上的行为本轮零数据）；**未做任何浏览器侧验证**（`sid` 的 `HttpOnly` + 同源发送全程用 `curl` / `http.client` 手工带 Cookie 头模拟，**真浏览器会不会把 `sid` 带到 `/agenerp/*` 上，本仓仍无实证** —— 那是工作项 11 的面）；nginx 那条 `proxy_read_timeout 300` **没有在一次真实的长解释上验证过**（本轮所有 `/explain` 都在 503 分支上 0.02 秒返回）。
  - **◆ 收口后补测（同日）：人那份门禁真跑了一次 —— `1 failed, 5 passed`。** `AGENERP_LIVE=1 … python3 -m pytest -m live tests/gates/test_explain_service_live.py -q -rs` → exit **1**。**那 1 条红的是且只是** `Failed: 活栈上一个 AI 变量都没配 —— 503 已判…`，即门禁自己那段 `skip → fail` 收严把断言体 `:223` 那条 `pytest.skip` 翻译成了红。⇒ **红因从「六条全红（连不上 / 反代不存在）」收窄成「五条转绿、第 4 条红在那条 skip 上」，但 job 仍然是红的。****对照**：栈没起来时同一条命令是 `6 failed`。⇒ 上面那句「第一条只交付了它的前提，没交付它退 0」**有了直接实证**，不再只是推演。
  - ⚠️ **一处更正**：收尾提交里记为「不可复现」的 `frontend` 重启循环（`[emerg] host not found in upstream "backend:8000"`）**补测期间又出现一次**，共两次，**两次都在原样复跑 `up -d --wait` 后 exit 0 完全恢复**。已排除两项：**本仓那份 nginx 模板**（一次性容器里 `nginx -t` **exit 0**，`backend` 与 `agenerp-serve` 两个名字都解析得出）与 **`tests/gates/conftest.py`**（无 import 期 compose 调用、`compose_stack` 非 autouse 且那份门禁不请求它）。第二次发生时 `backend` / `agenerp-serve` 的 `RestartCount=0` 而 `StartedAt` 同一秒 ⇒ 有**本 plan 之外的某个动作**跑过一次 `docker compose up`。**根因仍未确定，仍然不猜**；⚠️ **也不写成「与本 plan 无关」** —— 本 plan 确实给 `frontend` 加了一条 `depends_on` 与一处挂载，没有证据表明相关，也没做过能排除它们的实验。
  - **◆ 2026-08-25 人报的缺陷已复现、已定位、已修、已实测（`4e9e74d` 的处置回执）—— ⚠️ 本行状态词仍是人改回去的 `todo`，loop 不擅自再翻。** 落点节 `module-boundaries.md` **§7.21 `D-b-8`**。**决定性实验**（30 秒，不靠冷起栈的随机性）：`docker compose stop agenerp-serve && docker compose up -d --force-recreate --no-deps frontend` → 修前逐字 `[emerg] host not found in upstream "agenerp-serve:8330"`、frontend `restarting` ⇒ **缺陷坐实，且报的正是本仓加的那个上游**。**成因**：nginx 在**加载配置那一刻**解析 `upstream` 里的主机名，解析不出来就 `[emerg]` 退出且不重试，而 frontend 是 `restart: on-failure` ⇒ **整个前端陷入重启循环**。⇒ **`D-b-1` 选 (A) 是对的，落地形态错了** —— 本仓加的那一跳把 frontend 的可用性绑在了一个它不需要的服务上。**修法两处**：① nginx 侧删 `upstream` 块，改 `resolver` + 变量形式的 `proxy_pass`（**每次请求时**解析）；② compose 侧**删掉** `frontend.depends_on.agenerp-serve`（⚠️ 它**挡不住**这个失败形态——`depends_on` 只管 `up` 的次序，管不到 `restart: on-failure` 的重启——**代价真、收益假**）。**修后实测**：同一条实验下 frontend `running`/`healthy`、`RestartCount=0`、`/api/method/ping` **200**、`/agenerp/health` **502**（降级是局部的、可观测的）；恢复服务后 `/agenerp/health` **200**、断言体 `5 passed, 1 skipped`、人那份门禁 `1 failed, 5 passed`；**冷起栈** `down -v` → `up -d --wait --wait-timeout 900` → **exit 0**、全部 healthy、`RestartCount=0`、两个端点都 200。**新增判据⑩ / ⑩b**（21 → **23 条**，`tests/unit` 777 → **779**），**变异扩到 M11**（M1–M11 共 **12 次**施加，逐条打红、逐条 `RESTORED OK`）；判据⑩b 专门挡「**用一条 `depends_on` 当修法**」。
  - ⚠️ **人报的那个 `backend:8000` 变体没有被直接修掉**：那是**上游模板自己那一行**，同一条 nginx 性质，改它等于改上游文件内容、把副本与上游的差集撑大（K3）。**本次只保证「本仓加的那一跳不再有能力拖垮 frontend」，不保证「frontend 再也不会因为上游解析失败而重启循环」。**
  - ⚠️ **本机 Docker 另有两处不稳定，与本仓无关但影响取证**：① **另一个 compose 项目**（项目名 `docker`）的 `frontend-1` 占着宿主 `0.0.0.0:8080` ⇒ 不带 `AGENERP_HTTP_PORT` 的 `up` 会死在 `Bind for 0.0.0.0:8080 failed: port is already allocated` —— **这正是人那条复现命令在本机的另一种死法**；② 冷起栈两次中途报 `Error response from daemon: No such container: <id>`。**两处都不猜根因**，只说明本轮冷起栈取证是在一台不稳定的机器上做的。
  - ⚠️ **独立收口审计未做** —— 本轮执行环境不具备独立子代理，`closure audit was independent` 这条 gate **留白**（执行者自己复跑不算独立审计），详见 plan `## Closure`。
- 10b. **`frontend` 间歇不可达 —— 起栈时序缺陷**（从工作项 10 拆出，人 2026-08-25）: `done` —— 验收：**`gates-l2-live` 连续 3 次 run 全绿零跳过，且 3 次都在「落地修复的那个 commit」及其之后**（间歇缺陷，一次绿不算；**修复之前的绿更不算** —— `7af5493` 就全绿过，那时一行修复都没写）。收口时必须点名 sha 与 3 个 run id。详见 `02-WBS.md` 的 `P1.8a-fix` 行与 STATE §3 同日条目。**plan 预算独立计**，不占工作项 10 的额度。
  - **◆ 已交付并收口（2026-08-26）：`2026-08-25-1118-1-gates-l2-live-intermittent-red.md` → `completed`（表规 3 的预算此后 1/2）。**
    **修复 commit `182ef2a`**（人落，`D-26`「把 `TIMEOUT` 拆成 `CHEAP_TIMEOUT = 30` / `EXPLAIN_TIMEOUT = 180` 两个预算」，带 `Gates-Change-Approved-By: lize`；它落在 `tests/gates/**` 红线内的判据正文 `tests/unit/test_explain_service_body.py`，**loop 无权写**）。
    **三次 `push` run 全绿零跳过**：`32924757237`（`182ef2a`，修复提交本身）· `32924918686`（`cb3ad79`）· `32925450458`（`aae1843`），三次判定步原文均为 `门禁 54 项：红 0，绿 54，跳过 0`；`git merge-base --is-ancestor 182ef2a <sha>` 三个全退 0。
    **守卫**：`tests/unit/test_explain_service_timeout_budgets.py`（6 条，含 3 条行为判据），**7 个变异 7/7 打红**（M5「长预算只从 30 挪到 31」尤其关键 —— 它让「改了数字但没真改」过不去）。
    ⚠️ **`02-WBS.md:88`（`P1.8a-fix` 行）的状态词至今没写** —— `docs/masterplan/` 在红线 5 内（loop 只读），且 P1 那张表实读**没有「状态」列**（表头 5 列）⇒ 本行就是 `10b` 的状态词落点。**那一格已交人**，见 `STATE.md` §3 `[open] 2026-08-26T03:39Z`。
    ⚠️ **verification scope limited** —— 验收面是 `P3-4` 的五条命令 + 三次 run；整仓 `pytest tests -q -m "not live"` 有 12 个 error（`tests/gates`×`tests/tools` 环境泄漏，已单列 `gates-and-tools-leak-env-across-directories.md`，与本缺陷无关）。
- 11. **Desk 侧边栏**（⌘K，调 P1.8a 的面）（P1.8b）: `done`
  - **◆ 第 2 个 plan 已交付并收口（2026-08-26）：`2026-08-25-1743-1-desk-sidebar-cmdk-and-live-ui-gate.md` → `completed`（表规 3 的预算此后 `2/2` 满）。**
    **验收命令原文与退出码**：`AGENERP_LIVE=1 AGENERP_HTTP_PORT=18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs` → **exit 0 · `11 passed` · 零 skip**，连跑三次全绿（`41.54s` / `51.31s` / `40.25s`，三次都在 `down -v` 冷起之后）。
    **收集条数 11 == 断言体里 `test_` 函数条数 11** —— 「零 skip」这句话在一条都没跑时也成立，由条数把它钉住（`no tests collected` 退 5）。
    **交付**：`agenerp/serve/assets/desk.js`（⌘K 唤起 / `Esc` / toggle / 焦点归还 + 九个已枚举码 + `200` + 兜底态）· `tests/ui/test_sidebar.py`（薄加载器，零 skip 严格模式）· `tests/unit/test_desk_sidebar_body.py`（断言体，**受 `pytest tests/unit -q` 那一轮保护**）· `tests/unit/test_desk_sidebar_static.py`（离线判据 + **五条**源码级守卫）· 落点节 `module-boundaries.md` **§7.23**。
    **变异自查 `M1`–`M16` 十六条 / 18 次施加，18/18 `RESTORED OK`**，其中 **`M7` 第一次施加时一格都没打红**（门禁退化成 `exit 0 · 11 skipped`，一条绿着的、不存在的门禁）⇒ 当场补第五条守卫后打红，经过已逐字记在证据文件。
    **本仓第一次真浏览器侧实证**：浏览器把 `HttpOnly` 的 `sid` 带到了 `/agenerp/explain`（直接读那次请求的 `Cookie` 头，morsel 名 `['full_name','sid','system_user','user_id','user_image']`，值长 56 字符），而同页 `document.cookie` 里**没有** `sid`。
    ⚠️ **`H7` 预测不吻合，照实记**：预测 `503`，实际 **`401`** —— 原因是下面那条 CSRF 发现；判据**不钉死任何一个码**（先观测实际码，再断言面板渲染的是该码那一态）。
    ⚠️ **本轮真实 token 成本 = 0** —— 容器里 `AGENERP_LLM_API_KEY` / `BASE_URL` **实测为空**，且那次真请求在 `config_factory` 之前就被 401 挡下 ⇒ 一次模型调用都没发生。**这不是「本 plan 零成本」的普遍形式**，配上密钥后那一次真请求会真调模型（中位约 11 万 token）。
    🔴 **两条实测撞出来、落在红线内的缺陷，已交人**（`STATE.md` §3 `[needs-human] 2026-08-26T05:30Z`）：**①** 浏览器网页会话的 `sid` 在 `/agenerp/explain` 上被 **CSRF** 挡下（既有活体门禁用的 `POST /api/method/login` 会话不受影响 ⇒ **那份门禁绿在一种真人永远不会有的会话上**），修法在 `agenerp/serve/**` = P1.8a 的请求契约面，本 plan Non-Goals 1 禁止碰；**②** 先例 `tests/gates/test_explain_service_live.py:80` 的全局 `pytest.skip` 重绑是**进程级污染**，同轮跑到它之后本 plan 断言体的 skip 全变 error（单跑绿、同轮红，已实测三条），修法在 `tests/gates/**` = 红线 1。
    ⚠️ **`tests/ui/` 在 CI 上今天零覆盖，六件交接全部落在 `.github/workflows/**`（红线 2）** —— `COVERED` 少一个 `ui`（下次推送时 `unit-and-contracts` 第 ⑦ 步必红，**那正是那条守卫被写出来的目的**）· `gates-l2-live` 没有跑它的 step（**光加 `COVERED` 不会让它跑起来一次**）· `lint` job 的 ruff 参数不含 `tests/ui`。**装 chromium 的三个方案 + 实测墙钟/体积已一并交回，选哪个归人。**
    ⚠️ **verification scope limited**：整仓 `pytest tests -q -m "not live"` **已跑但未绿**（**基线即红** —— 对照实跑把本 plan 新增的两份挪开，同一条命令 `5 failed, 1308 passed, 12 errors`）· **未经 CI 服务端复跑**（`tests/ui/` 不在任何 job 作用域里，**本门禁在 CI 上的行为零数据**）· **独立收口审计由执行者自己复跑，该 gate 留白**。
    **全部命令原文、退出码、观测值见 `docs/evidence/p1-desk-sidebar/README.md`。**
    ⚠️ **`02-WBS.md:89`（P1.8b 行）的状态词没写** —— `docs/masterplan/` 在红线 5 内（loop 只读），且 P1 那张表实读**没有「状态」列**（表头 5 列）⇒ **本行就是工作项 11 的状态词落点**，与 `10b` 同一处置。
  - **◆ 第 1 个 plan 已交付（表规 3 的预算此后 1/2）：`2026-08-25-1615-1-desk-injection-seam-and-asset-route.md` → `completed`。**
    ⚠️ **本行状态词仍是 `todo`，不是遗漏** —— 那个 plan **从不声称满足** WBS §4 第 88 行的验收命令
    （`pytest -m live tests/ui/test_sidebar.py`），它**不做 ⌘K、不做侧边栏 UI、不建 `tests/ui/`**（其 Non-Goals 1/2）。
    它交付的是那条命令成立所必需、而此前**完全不存在**的一格：**Desk 页面上如何才能加载到本仓的一段 JS。**
    本行要转 `done`，等的是**第 2 个 plan**（表规 3 的最后一格预算）。
  - **补的是一格空着的裁定**：`DECISIONS.md` **D-19** 把承载形态定为「独立进程 + nginx 同源反代，不是 Frappe custom app」，
    于是 §7.13 `D1` 选中的「自建 Frappe app」被逐字否掉，**但 D-19 没有给出替代的注入口** ——
    而 `www/app.py:47` 实读证明 Desk 全局 JS 只有 `hooks["app_include_js"]` 与 `frappe.conf["app_include_js"]`
    两个来源，**两个都要进 Frappe 侧**。落点节 `module-boundaries.md` **§7.22**（新增，`§7.13/§7.20/§7.21` 一个字未改）。
  - **裁定四条**：`D-c-1` 选 **(I)**（哨兵段内另起 `location ^~ /app`，**只在该块内** `sub_filter`）·
    `D-c-2` 选 **(a)**（`agenerp/serve/assets/desk.js` + 服务的一条**不认人**只读 GET 路由，零新增挂载 / 零新增 location）·
    `D-c-3` 风险档自评 **L1**（与 §7.21 `D-b-7` 同档；`D1` 当年判 L3 的理由随 D-19 否掉那条路而消失——**是被评的对象换了**）·
    `D-c-4` 裁定 §7.20 `D-a-2`「不加第三条」**不适用**于一条不认人、不碰站点、不碰 LLM 的静态资产路由，**`D-a-2` 一个字未改**。
  - ⚠️ **(H) 的否决是实测出来的，不是论证出来的**：一次可复原的临时施加下，server 级 `sub_filter` 实测
    **误伤门户页 `/login`（1 次）与走 `location ~ ^/files/…` 那条路的 HTML（1 次）** —— 后者等于把注入串写进用户下载的 HTML。
    选 (I) 之后同样两条请求实测**各 0 次**（体分别 347,156 / 330,562 字节，**有体可数，不是空响应**）。
  - **活栈八条探针 `H5`–`H11` 全部吻合开跑前写死的预测**：`nginx -t` exit 0 · 资产 URL 200 / `text/javascript; charset=utf-8` / 与仓里那份逐字节相同 ·
    `/app` 注入标记**恰好 1 次**且在 `</body>` **之前** · 停掉 `agenerp-serve` 后 frontend `healthy`、`RestartCount=0`、`/app` 仍 200 且标记仍在、资产回 **502**（§7.21 `D-b-8` 不回归）。
    **冷起** `down -v` → `up -d --wait --wait-timeout 900` → **exit 0，墙钟 68 秒**，十个长期服务全 `running`；冷起后重新登录复跑，这一跳仍成立。
  - **上游差集复核**：`<` 行 **0** 条（上游一行未删未改）、`>` 行 **100** 条落在**恰好两个 hunk** ⇒ **K3 成立，段数仍是两段**。
  - ⚠️ **变异自查抓到一个真窟窿，照实记**：**M5**（`Content-Type` 改成 `application/json`）第一轮**没打红** ——
    那条判据当时写的是「服务发出的 == `ASSET_CONTENT_TYPE`」，**两边是同一个常量的两次读取**，
    守不住「常量本身被改成浏览器不会执行的类型」，而那正是最难发现的失败形态（标签在、`curl` 200、`nginx -t` 绿，只有浏览器不执行）。
    **当场补断言**（media type 必须落在 JavaScript MIME 集合里）后复跑 → 打红。
    **M6**（改资产一个字节）**按构造打不红**（「逐字节相同」比的是两个源），照实保留在表里，
    并补了 M6b/M6c 两条覆盖它真正守的失败形态。共 **14 次施加、13 次打红、全部 `RESTORED OK`**。
  - ⚠️ **verification scope limited**：未跑整仓 `pytest tests -q -m "not live"`（跑的是 `tests/unit` **801 passed, 6 skipped**，开工基线 `779 passed, 6 skipped`
    + `contracts/tools/routing/context` **456 passed, 13 skipped**）· **未经 CI 服务端复跑** ·
    **未做任何浏览器验证** —— 本轮证到「HTML 里确实有那个 `<script src>`、且那个 URL 真回 200 JS」，
    ⚠️ **「HTML 里有 `<script>` 标签」≠「浏览器执行了它」**，那是第 2 个 plan 的面 ·
    「真实静态 HTML 附件会不会被损坏」本栈 `files/` 为空且 Non-Goals 3 禁止上传取证 ⇒ `not observed on this stack`。
  - **◆ 独立收口审计已补做（`closure audit was independent` 由留白转满足）** —— 由 mission-driver 任务 `2026-08-25-135246-mission-driver` 派发的**独立收口审计步骤**执行，审计者**不是该 plan 的执行者**，逐条对活仓复跑取证：`check_expected_red.py` → exit **0**（`门禁 26 项：预期红 0，绿 26，跳过 0`）· `pytest tests/unit -q` → exit **0**（`801 passed, 6 skipped`）· `pytest tests/unit/test_desk_asset_route.py tests/unit/test_desk_injection_static.py -q` → exit **0**（`22 passed`，新增判据**确实在跑**）· `ruff check …` → exit **0**。**反空壳实读**：`agenerp/serve/app.py:301-303` ⇒ `_respond_asset()`（`:341-360`）真读文件真写 `wfile`，非空壳。逐条结论见 plan `## Closure`。
    ⚠️ **边界照实记**：审计轮复跑的是**离线那一半**；**活栈那一半（`H5`–`H11`、冷起、变异表 `M1`–`M12`）审计轮未二次复跑**，采信执行期落盘的 `docs/evidence/p1-desk-seam/README.md` ⇒ 这一段仍是 `verification scope limited`，**不谎称全绿复跑**。

## 已经就绪的前置（不要重做）

- **样板公司**：恒锐动力科技有限公司（HRD）· 户用储能电池包。数据集 15 个
  DocType **全部为原生 ERPNext**，无自建表（D-9）
- **固定测例**：成品仓积压 **1,010 台 / ¥3,110,200**。账面全绿——订单被人工
  置为 `Closed`，系统按完成计，达成率 100% 而实发 990 台
- **外协四步链**：采购订单(外协) → 外协订单 → 发料 → 外协收货，全部由服务端
  工厂方法派生（D-12）
- **证据充分性门禁**：L1/L2（Spike 02 产出）+ **L3**（入库来源的覆盖，P1.0 T1 已定义，
  含过拟合反测）
- **站点侧对账 30 项**：财务/库存 9 + 文档图条数 9 + 跨单据 Link 字段 12
- **LLM**：DashScope（`qwen3.6-plus` 默认，D-11）。⚠️ 它是推理模型，
  回两个字也烧约 195 reasoning token，成本上限须按 reasoning token 计

## P1.7 已按 D-18 改为「记账但不拦截」（动手前必读）

原设计是「单次解释成本**上限**」，前提是「便宜模型 + 强门禁」可用。
P1.0 两轮实测都不支持这个前提（第一轮 5/12、第二轮 11/12，**可用的是更强的
模型，不是门禁补偿**）。实测单次解释 **9.7 万–12.8 万 token**。

用户 2026-08-24 裁定：**记账但不拦截**。

- 判据从「成本 ≤ X」变成「**成本可观测**」：prompt / completion / **reasoning**
  三项分开记，可按一次解释汇总
- ⚠️ **不许退化成「跑通就算」**：要能挡住「只记 completion 不记 reasoning」的
  假实现（D-11：回两个字也烧约 195 reasoning token）
- ⚠️ **不拦成本 ≠ 不拦失控**：工具调用轮数上限仍要有。一个陷入循环的 Agent
  会无限调工具 —— 那不是「贵」，是**坏**。两者判据**分开写，不许合并**

### 第 2 个 plan 已落地：prompt 侧细分 `cached` 也进了账（2026-08-25）

plan `docs/plans/p1-insight/2026-08-25-0554-1-prompt-cache-accounting.md`（`completed`）。
⚠️ **上面那条「三项分开记」的字面验收由第 1 个 plan（`2026-08-24-2109-2`）已完整满足**，
本条**不声称它没做完**。本 plan 的授权来自 **P1.1 `2026-08-24-1457-1` §9 第三条 Deferred
自己写死的 successor 指派**（重开事件「P1.4 解释 Agent 落地」已触发）。

- `Usage` 现在是**四项**：`prompt` / `completion` / `reasoning` / **`cached`**。
  `cached` 是 **`prompt` 的细分**，与 `reasoning` 是 `completion` 的细分**形状完全对称**；
  **`cached` 不进 `total`**（它是 `prompt` 的子集，加进去当场与端点自报的 `total_tokens` 对不上）。
- 账本加 `endpoint_cached` + `cached_matches_endpoint`（端点没报 ⇒ `False`）；
  会话落盘 `store.py` 落/读**四键**（否则 `cached > 0` 的会话 round-trip 不相等 —— 静默丢数）。
- 判据 `tests/unit/test_prompt_cache_accounting.py`（**12 条**）+ `tests/context/test_store.py`（+1）。
  `check_expected_red.py && pytest tests/unit -q` → **exit 0**（614 → **626 passed**）；
  `pytest tests/context -q` → **exit 0**（53 → **54**）；`pytest tests/routing -q` → **exit 0**（`167 passed, 1 skipped`）。
  **变异自查 M1–M10 十个全部被打红，无一需要补断言，因此没有 M11。**
- **首次在本项目自己的端点上实测前缀缓存**（`docs/evidence/p1-cache/`，`qwen3.6-plus`，一次 10 轮解释）：
  **逐次 `cached_tokens` 全为 `0`**，且端点在 `prompt_tokens_details` 里
  **根本没有报 `cached_tokens` 这个键**（键集逐次恒为 `{"text_tokens"}`）。
  ⚠️ **这是负结果，负结果同样有价值** —— 它是本仓关于这个问题的**第一个观测样本**（此前 0 个）。
- ⚠️ **举证责任的边界（跑之前写死的）**：**活端点证据在这一支上不承担「记全了」的举证责任**
  —— 逐次全为 0 时 `cached_matches_endpoint` 恒为 `0 == 0 → True`，
  **一个把 `cached` 恒写 0 的假实现产出的证据文件与真实现逐字节相同**。
  「记全了」由 `tests/unit` 的判据 ① 与 ⑧ **单独承担**。
- ⚠️ **`model-management.md` §12.2 的 Spike 02 成本表与「没有前缀缓存，解释 Agent 在经济上不成立」
  那句结论一个字未动**，只加了一行指针（两个数**不得互相佐证**，D-16）。
  **一次实测不足以推翻一句上位结论**；改写与否**由人裁定**。
- ⚠️ **没有设任何阈值、没有加任何拦截分支**（D-18）；**没有做前缀重排 / 提示词改造**（Non-Goals 2）；
  **没有做多次采样与分布**（一次实测不是分布）。
- ⚠️ **工作项 9 的 plan 预算（表规 3 的 1–2 个）到此用尽** —— plan §11 的**五条** Deferred
  若将来重开，须由**人**在 `02-WBS.md` 拆行 / 加行（红线 5，loop 无权）。
- ⚠️ **独立关闭审计未做** —— 本轮执行环境不具备独立子代理，详见 plan `## Closure`。

## ⚠️ 判自由文本答案之前，先跑通标注集（P1.4 / P1.5 动手前必读）

**`tests/fixtures/p1_entry_gate_labels.jsonl`**（24 条，人工标注，每条带 `reason`）
**`tests/unit/test_answer_judging_fixture.py`**（判据的判据）

### 为什么它存在

人侧判 P1.0 那道题的答案时，用关键词正则判了**四次，四次都判错**：

| 第几次 | 漏掉的 |
|---|---|
| 1 | 要求字面 `2000`，认不出 `1000 + 1000 - 990` |
| 2 | 根因词列了「重复生产」，漏了「重复记录」 |
| 3 | 认不出 `10 台尾数 + 1000 台外协` 这第三种拆法 —— 第一轮整体从 5/12 误判成 2/12 |
| 4 | 「没有任何销售订单来消化」「无单可发」「额外的外协收货」都不在词表里 |

**每次都是读原文才发现，而每次修完都以为修干净了。**
→ 结论不是「再补一版词表」，是**正则判自由文本这条路走不通**。

### 对 P1.4 / P1.5 的要求

P1.4 判「解释 Agent 答得对不对」、P1.5 判「洞察 Agent 找没找到」，
**比 P1.0 那道题更难判**。三条：

1. **动手写判定器之前，先让它跑通那 24 条标注。** 跑不通就别往下写 ——
   那说明判定方法有问题，不是答案有问题
2. **标签只能由人读原文定**，不能由任何判定器产生 —— 否则是让判据给自己判卷
3. **反例比正例值钱**：集子里 4 条「不完全」+ 1 条「截断」是刻意留的，
   只有正例的集子挡不住「一律判正确」的假实现

⚠️ 若判的是**结构化事实**（例如「给定事实集，三条门禁规则怎么判」），
本节不适用 —— 那是可枚举的，正则/条件求值没问题。
**本节针对的是判自由文本。** 两者别混。

#### ✅ 第 1 条已结清（2026-08-25，P1.4 侧）

**「动手写判定器之前，先让它跑通那 24 条标注」这一条已经做到了。**
判定器在 `agenerp/judging/`，**第 1 轮全量 24 条逐条一致 24/24**
（负例三分类精确 5/5、正例 19/19，0 次修订），落地 sha `45bb8c3`。
plan `docs/plans/p1-insight/2026-08-25-0225-1-answer-judge-v0.md`，
落点节 `docs/architecture/module-boundaries.md` **§7.15**，证据 `docs/evidence/p1-answer-judge/`。

⚠️ **第 2 条与第 3 条一个字没变，仍然完全有效**：

- **第 2 条**（标签只能由人读原文定）：那 24 条**一个字节未改**，判定结果**没有回写集子**
  （有判据守着）。构造对照里"剥离"那一半的预期标签**是判定器产生的**，
  已被独立评审裁定**不可作证据**、降为观测。
- **第 3 条**（反例比正例值钱）：这一轮再次证明它 —— **总体准确率不能当口径**，
  `always-correct` 在这份集子上是 19/24 = **79.2%**。

⚠️ **本节对 P1.5（归因文本）的要求并未因此结清**：判定器**已验证的适用范围只有 P1.0 那一道题**，
判归因属**跨题族外推**，按 D-16 只能写「待复验」。

⚠️ **两条 loop 无权做、只能由人做的事，仍然敞着**：

1. **扩充集子**（更多负例 / 第二个题族的人工标注）。今天只有 **5 条负例**，
   因此**没有做留出集**（分不动），⇒ **对"集子之外的判别力"没有实证支撑，不得读成"泛化已验证"**。
2. **读两段构造文本再写标签**（`run-01` 截到 179 字符的那段、剥离后剩 13 行的那段）。
   独立评审的原话：读一遍只要两分钟，读完两条**都**能变成人工标注、**都**可采 ——
   而 loop 选择了论证而不是去读，这正是本节记的那个教训。

## 已知的坑（照抄，不要重新发现）

- ~~**`permission.scope` 的判别力在当前站点上验不出来**~~ —— **2026-08-24 已解决**：
  `agenerp/seedusers.py` 幂等建出受限身份「车间工人」（只读 3 个 DocType），
  以它实跑得到**可读 3、不可读 3**。⚠️ **新坑照实记**：stock Frappe 只把 `DocType`
  的读权限给 System Manager / Administrator，且对它建 `Custom DocPerm` **不生效**，
  因此**受限身份枚举不出 DocType 清单**——`permission.scope` 的候选集必须由调用方给，
  **不要靠给工人发 System Manager 绕过去**（那等于把「受限」取消掉）
- **`lineage.trace` 必须扫子表**：21 个指向 `Sales Order` 的 Link 里 14 个在子表
- **`doc.links` 的下游筛选是「排除已取消」**，不是「只要已提交」——
  滤掉草稿会把 L2 门禁架空
- **外协订单在 ERPNext v15 结构上挂不回销售订单**（没有 `sales_order` 字段），
  这是 P1.0 实验陷阱的来源，**不是缺陷，不要去"修"它**
- **Python 直连 HTTPS 需显式 certifi**：本机 python.org 版未装 CA 根证书
