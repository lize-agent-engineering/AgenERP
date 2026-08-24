# 2026-08-20-2341-3 状态快照与结构化 diff（L1 部分）

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 2. 状态快照与结构化 diff
> Last Reviewed: 2026-08-21
> Source: `docs/backlog/p0-foundation-roadmap.md` Work Item Status 第 2 项（`todo`）
> Related: `2026-08-20-2341-1-agenerp-package-skeleton.md`（**硬前置**）·`2026-08-20-2341-2-customization-pack-normalizer.md`（同批，先于本 plan）
> Audit: required

## Current Baseline

- roadmap 工作项 2 状态 `todo`，绑定门禁 `tests/gates/test_snapshot_diff_structured.py`：
  - `test_two_snapshots_of_unchanged_site_diff_empty` —— **L1**（roadmap 对照表点名）
  - `test_diff_is_structured_not_text` —— **L1**（同上）
  - `test_field_addition_shows_up_as_structured_change` —— 带 `@pytest.mark.live`，依赖 `live_site` fixture。roadmap 把它划给**工作项 6**（定制包往返验证），**不属本 plan**。
- 三条断言全部 `from agenerp.snapshot import capture, diff`。plan 1 落地后签名已定稿、红因为 `NotImplementedError`。
- `tests/gates/conftest.py` 的 `live_site` fixture 仍抛 `NotImplementedError`（工作项 4 才提供），所以第三条**本 plan 结束后仍会红**，且必须继续留在 `EXPECTED_RED.txt` 里。
- 两条 L1 断言逐条读出的契约（判据原文在门禁文件，此处只写形状）：
  1. `capture(scope="doctypes")` 连调两次，`diff(before, after)` 必须 `.is_empty()` 为真，且 `.summary()` 可调用（断言失败信息里用到）。
  2. `diff(...)` 的返回对象必须有 `added` / `removed` / `changed` 三个属性，且各自是 `list` / `tuple` / `dict` 之一。
- 第三条（live，不在本 plan 范围）额外规定了 `d.added` 的**元素形状**：元素需有 `.doctype` 与 `.fieldname` 属性。本 plan 虽不负责让它变绿，但**必须现在就按这个形状设计**，否则工作项 6 开工时要推翻重来。
- `tests/gates/test_customization_roundtrip_delete.py` 还从 `agenerp.snapshot` import 了 `schema_drift`——属工作项 6，本 plan 不实现，保持 `NotImplementedError`。
- 与 plan 2 相同的结构性事实与后果链：两条 L1 一旦转绿，`python3 tools/gates/check_expected_red.py` 报「名单内的门禁却绿了」并 exit 1 → `GATE_VERIFY` fail → `flows/plan-execution.json` 重试 `EXECUTE` 3 次 → `onMaxRetries.done = "failed"`（子流程终局）→ `flows/mission-driver.json` 的 `EXEC_PLANS` `some_failed`/`all_failed` 一律 `goto DRAFT_PLANS`。**不停机、不落 `.mission-halt.json`、不自动写 STATE**；且 plan 若留在 `active`，`activePlans()` 下轮会再选中它重跑。故本 plan 同样在 Phase 3 末步自置 `Plan Status: deferred`。登记见 `docs/backlog/needs-human-expected-red-handoff.md` 冲突 1/2（plan 1 交付）。
- ⚠️ **本 plan 与 `02-WBS.md` 有两处分歧，按 roadmap 执行、把分歧登记给人**（引擎取的是 `missions/p0-foundation.json` 的 `roadmapPath`，即 roadmap 那份）：
  1. **顺序相反**：WBS 是 P0.3（快照 diff）→ P0.4（规范化器）；roadmap 是 1 规范化器 → 2 快照 diff。
  2. **前置与验收更宽**：`02-WBS.md` 给 P0.3 的前置是 **P0.2（工具契约层 v0）**、验收是**整个门禁文件（3 条）**；roadmap 的对照表只把其中 2 条 L1 划给工作项 2，第 3 条（live）划给工作项 6。本 plan 按 roadmap 的窄口径做，**不碰 P0.2**。
  两处均已写进 plan 1 交付的交接文档冲突 4。

### 起草时识别出的真实设计难点

`capture(scope="doctypes")` 在**没有活站点**的情况下被 L1 调用（门禁文件里这两条没有 `live` 标记、没有 `live_site` 参数）。
实现必须回答：无站点时快照从哪来。不回答就只能写一个「永远返回空」的空壳去骗断言——那样 `diff` 的真实语义一行都没被验证过，
工作项 6 接手时会发现地基是纸糊的。本 plan 的 Phase 1 Decision 专门处理这一点，Phase 2 用 `tests/unit/` 把真实 diff 语义单独钉死。

## Goals

- 实现 `agenerp.snapshot.capture` 与 `agenerp.snapshot.diff`，使 `python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q -m 'not live'` → **exit 0（2 passed）**。
- `diff` 的**真实语义**（增 / 删 / 改三类各自算得对、`is_empty` 与 `summary` 行为正确）由 `tests/unit/` 独立覆盖，**不依赖活站点**，也不依赖门禁那两条弱断言。
- `capture` 的数据来源**可插拔**：无站点时走确定性的离线来源，有站点时走站点来源。工作项 4（工具契约层 v0）接上活站点时，只需提供来源实现，**不改 `capture` / `diff` 的签名与语义**。
- `d.added` 元素形状按 live 断言定稿（含 `.doctype` / `.fieldname`），为工作项 6 留好接缝。

## Non-Goals

- **不让 `test_field_addition_shows_up_as_structured_change` 变绿**——它需要 `live_site`，属工作项 4/6。它必须继续留在 `EXPECTED_RED.txt`。
- 不实现 `schema_drift`、不实现 `agenerp/pack.py` 里任何还抛 `NotImplementedError` 的函数。
- 不接真实 Frappe / ERPNext 站点，不引入任何第三方依赖（CI `gates-l1` 只 `pip install pytest`）。
- 不碰 `tests/gates/**`（含 `EXPECTED_RED.txt`）、`missions/*.json`、`missions/prompts/build-verify.md`、`.github/workflows/**`、`docs/masterplan/**` 已有行（`STATE.md` §3 只追加）。
- 不改 `tools/gates/check_expected_red.py`、不改 `tools/gates/gate-verify.mjs`——改判定器与写保护等同改裁判。
- 不碰 `02-WBS.md` 的 P0.2/P0.3 前置（那两处分歧登记给人，不自行对齐）。
- 不做断言 DSL（WBS P0.3 提到的第三块）——roadmap 工作项 2 的判据只到「结构化 diff」，DSL 无绑定门禁，按 mission 规则「没有判据不开工」留给人定。

## Task Route

- Type: `app-layer design change`（`capture` 的来源抽象是会被工作项 4/6 继承的结构边界，不只是内部实现）
- Owner Docs: `docs/backlog/p0-foundation-roadmap.md`（工作项 2 判据）·`docs/architecture/`（来源抽象的落点，见 Phase 3）·`tests/gates/README.md`（判据出处，只读）
- Skill Selection Basis: 与 plan 2 同理，`docs/skills/` 下无对应方法技能，判据已是可执行断言。各阶段 `Skill: none`。

## 结构边界契约（会被工作项 4/6 继承，故必须写进 plan）

- `capture(scope: str) -> Snapshot`：`Snapshot` 是不可变值对象，只承载「某一时刻某 scope 的结构化状态」，**不持有连接、不做 I/O 缓存**。
- 数据来源经一个显式来源接口取得，接口只需一个方法：给定 scope 返回可比较的结构化数据。本 plan 交付两种实现——**离线来源**（无站点时用，确定性、不猜数据）与来源解析逻辑（有站点配置时选站点来源）。站点来源实现本身属工作项 4。
- `diff(before: Snapshot, after: Snapshot) -> Diff`：纯函数，不碰来源。
- `Diff` 暴露 `added` / `removed` / `changed`（均为序列）、`is_empty()`、`summary()`。三个序列的元素统一为条目对象，至少携带 `doctype` 与 `fieldname` 属性；`changed` 的条目另带变更前后值。
- **两个 scope 不同的 Snapshot 不许被 diff** —— 必须显式报错，不许静默当成「全删全增」。

## Infrastructure And Config Prereqs

- 无新增依赖、无端口、无密钥。仅标准库。
- **硬前置（两条都是硬的）**：① plan 1 已 `completed`（`agenerp/snapshot.py` 签名定稿、`tests/unit/test_contract_surface.py` 存在）；② plan 2 已跑完（`deferred` 或 `completed`，即不在 `ACTIVE_STATUSES`）。②之所以是硬的而非建议：两个 plan 都要改 `test_contract_surface.py` 的同两张清单，并发进入会互相覆盖；顺带也让人能一次性处理两批划名单。前置检查是 Phase 1 的第一项，不通过即停手。
- 回滚策略：改动集中在 `agenerp/snapshot.py` 与 `tests/unit/`，`git revert` 回到「红在 NotImplementedError」，无迁移。

## Execution Plan

### Phase 1 — `capture` 与来源抽象

Status: completed
Targets: `agenerp/snapshot.py`
Skill: `none`

- Item Types: `Proof | Decision | Add`
- Prereqs: plan 1 全部关闭；plan 2 先行（**硬要求**，见下方首项）

- [x] `Proof` **开工前置检查（第一步，不做完不许写代码）**：确认 plan 1 的 `Plan Status` 是 `completed`，且 plan 2 的 `Plan Status` 是 `deferred` 或 `completed`（即 plan 2 已跑完、不在 `ACTIVE_STATUSES` 里）。
      - 任一条不成立：**立即停手**，不实现、不提交代码，向 STATE §3 追加一行说明前置未就绪，并把本 plan 置为 `Plan Status: deferred`（**不要置回 `draft`**——`draft` 会被 `draftPlans()` 重新捡起走 `REVIEW_PLANS` → `EXEC_PLANS`，来回弹；`deferred` 才是停住等人的那个值，与成功路径一致）。
      - 为什么是硬要求而不是建议：`EXEC_PLANS` 的 `forEach: activePlans()` 一次取出全部 active plan 跑子流程，**不检查前一个是否成功**；顺序在本批里只由文件名排序表达。而 plan 2 与本 plan 都要改 `tests/unit/test_contract_surface.py` 的同两张清单，并发进入会互相覆盖。
      - Skill: `none`
- [x] `Decision` 定下「无活站点时 `capture` 从哪取数」：**离线来源从一个确定性的本地位置读**（仓内约定路径，不存在即视为「零条目」），而不是「硬编码返回空」。
      - **这两者不是一回事，必须分清**：硬编码返回空是个只为让断言过关的空壳，`capture` 本身一行逻辑都没被验证；「从确定位置读、读不到就是零条目」则是一条真实的、可被非空夹具驱动的读取路径——今天它恰好读到零条目，是因为仓里还没有数据，不是因为函数被写死。Phase 2 用非空夹具目录直接测它。
      - 理由：门禁两条 L1 问的是「同一来源两次快照是否相等」与「diff 是否结构化」，零条目对这两个命题是**诚实的最小真值**；伪造样本数据则会让「未改动站点 diff 为空」变成自证的假货。
      - 备选 1：无站点直接抛异常 —— 否决，会让两条 L1 门禁永远红在环境而非实现，重蹈 W0.6「红得不对」。
      - 备选 2：内置一份固定样本 DocType 表 —— 否决，等于把测试夹具伪装成产品行为，工作项 4 接站点时会与真实数据打架。
      - 残余风险：零条目下那两条门禁断言的信息量仍然低。缓解：Phase 2 对 `capture`（非空夹具）与 `diff`（增删改三类）各自做不依赖站点的真实覆盖，把语义强度补回来。
      - 翻案条件：工作项 4 提供 `live_site` 后，若发现离线快照与站点快照的类型不一致，回来修来源接口。
      - Skill: `none`
- [x] `Add` 定义 `Snapshot` 值对象：携带 scope、来源身份、结构化条目集合；相等性只看内容不看采集时间（否则「两次快照相等」永远不成立——这正是 Spike 06 在定制包上踩过的同一个坑）。
      - Skill: `none`
- [x] `Add` 定义来源接口与离线来源实现，以及 `capture` 里的来源解析（无站点配置 → 离线来源；来源位置可由参数或环境变量指向，测试据此喂夹具目录）。站点来源留 `NotImplementedError` 并指向 roadmap 工作项 4。
      - Skill: `none`

Exit Criteria:

- [x] `python3 -c "from agenerp.snapshot import capture; a=capture(scope='doctypes'); b=capture(scope='doctypes'); print(a==b)"` → 打印 `True`，exit 0
- [x] ⚠️ 上一条**本身是空洞的**（两个零条目快照当然相等），它只证明不抛异常。`capture` 的真实判据在 Phase 2 的 `tests/unit/test_snapshot_capture.py`，不在这里。
- [x] `ruff check agenerp tests/unit` → exit 0
- [x] 无 owner-doc 更新（归 Phase 3）

### Phase 2 — `diff` 与真实语义覆盖

Status: completed
Targets: `agenerp/snapshot.py`、`tests/unit/test_snapshot_diff.py`、`tests/unit/test_snapshot_capture.py`、`tests/unit/test_contract_surface.py`
Skill: `none`

- Item Types: `Add | Proof`
- Prereqs: Phase 1

- [x] `Add` 实现 `Diff` 与 `diff()`：按上文结构边界契约产出 `added` / `removed` / `changed`；`is_empty()` 当且仅当三者皆空；`summary()` 返回**人读的**摘要（它只出现在断言失败信息里，不是机器判定面——机器判定走三个序列，这正是「结构化而非文本」的含义）。
      - Skill: `none`
- [x] `Add` scope 不匹配时显式报错，不静默降级。
      - Skill: `none`
- [x] `Proof` `tests/unit/test_snapshot_capture.py` 覆盖 `capture` 本身（**用非空夹具目录，这是 H 类空洞判据的解药**）：
      - 指向一个含多个 DocType/字段的夹具 → 快照条目数与内容正确，不是零
      - 同一夹具连读两次 → 两个 Snapshot 相等（相等性只看内容，不看采集时刻）
      - 夹具改一个字段后重读 → 快照不再相等（证明它真的在读，而不是返回常量）
      - 指向不存在的位置 → 零条目快照，不抛异常
      - 不同 scope → 快照携带的 scope 不同
      - Skill: `none`
- [x] `Proof` `tests/unit/test_snapshot_diff.py` 覆盖（每条注明失败意味着什么）：
      - 同一快照自比 → `is_empty()` 为真
      - 加一个字段 → 只进 `added`，条目的 `.doctype` / `.fieldname` 取值正确（**预演 live 断言的形状**）
      - 删一个字段 → 只进 `removed`
      - 改一个字段属性 → 只进 `changed`，且带得出前后值
      - 三类同时发生 → 三个序列各自不串味
      - `summary()` 在空 diff 与非空 diff 上都可调用且不抛
      - scope 不匹配 → 抛错而非返回「全删全增」
      - Skill: `none`
- [x] `Fix` 更新 `tests/unit/test_contract_surface.py`：把 `capture` 与 `diff` 从 `NOT_YET_IMPLEMENTED` 清单**移到** `IMPLEMENTED` 清单。
      - 不做这一步，`python3 -m pytest tests/unit -q` 必红——plan 1 那条测试断言 `NOT_YET_IMPLEMENTED` 里的每个名字调用后抛 `NotImplementedError`。这是本 plan 造成的连带影响，必须由本 plan 修，故记 `Fix`。
      - Skill: `none`
- [x] `Proof` 复跑该文件，确认 `schema_drift` 与 `agenerp/pack.py` 中未实现的函数**仍在 `NOT_YET_IMPLEMENTED` 里且仍抛 `NotImplementedError`**（没有顺手做掉别的工作项）。
      - Skill: `none`

Exit Criteria:

- [x] `python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q -m 'not live'` → **exit 0，2 passed**
- [x] `python3 -m pytest tests/unit -q` → exit 0
- [x] `python3 -m pytest tests/gates -q --tb=line` → `test_field_addition_shows_up_as_structured_change` **仍红**，且红因是 `live_site` 的 `NotImplementedError`（不是被本 plan 弄成别的错）
- [x] `ruff check agenerp tests/unit` → exit 0
- [x] 无 owner-doc 更新（归 Phase 3）

### Phase 3 — 落结构边界文档、留证据、交接

Status: completed
Targets: `docs/architecture/module-boundaries.md`、`docs/logs/2026/08-20.md`、`docs/masterplan/STATE.md`（**只追加**）、本 plan 文件自身（末步改 `Plan Status`）
落点已定死，不留给执行会话选：`docs/architecture/README.md` 把 `module-boundaries.md` 登记为「§7 工具契约层、§11 定制包与 GitOps」的归属，快照/来源接口/Diff 的结构边界正属这一类；`model-management.md` 归属的是「§12 模型管理」（LLM 模型），不是这里。
Skill: `none`

- Item Types: `Add | Proof`
- Prereqs: Phase 1, Phase 2

- [x] `Add` 把「结构边界契约」一节的内容写进 `docs/architecture/`：`Snapshot` / 来源接口 / `Diff` 的职责与不变量，并写明**站点来源属工作项 4，此处留接缝**。这是 Task Route 判定为 `app-layer design change` 所要求的 owner-doc 更新。
      - Skill: `none`
- [x] `Add` 写 `docs/logs/2026/08-20.md` 条目：交付内容 + 命令原文 + 退出码 + commit sha。
      - **执行记录（2026-08-21）**：起草日是 08-20，实际执行日是 08-21。按 `AGENTS.md` 操作规则 7「一天一文件」，
        条目写入 `docs/logs/2026/08-21.md`（本轮已有两条 08-21 条目，新条目按写作指南置于文件顶部）。
        起草时写死 08-20 属跨日执行的必然偏差，不改 08-20 的历史文件。
      - Skill: `none`
- [x] `Proof` 复跑 `python3 tools/gates/check_expected_red.py` 并如实记录退出码。
      - 预期 **exit 1**，「名单内的门禁却绿了」列出本工作项两条 L1（若 plan 2 的三行尚未被人划掉，则一并列出，共五条）。
      - 同 plan 2 的禁止清单：不改 `EXPECTED_RED.txt`、不改判定器、不加 skip/xfail、不把实现改回不可用。
      - **执行记录（2026-08-21）· 实测 exit 0，与起草时的预期不同，前提已被人变更**：
        人在 `4bbe3f5`（提交信息带 `Gates-Change-Approved-By: lize`）裁定「测试代码是裁判、预期红名单只是账本」，
        把名单由 `tests/gates/EXPECTED_RED.txt` 迁至**红线外**的 `tools/gates/expected-red.txt`，
        并一次划掉 5 行（规范化器 3 + 快照 diff 2，含本工作项两条 L1）。`AGENTS.md` 红线 1 已同步补上该边界。
        故本轮实测 `python3 tools/gates/check_expected_red.py` → **exit 0**（门禁 13 项：预期红 8，绿 5，跳过 0）。
        禁止清单本轮**一件都没触发**：名单未改（改动由人在开工前完成）、判定器未改、无 skip/xfail、实现未回退。
      - Skill: `none`
- [x] `Add` 向 `docs/masterplan/STATE.md` §3 **追加**一行 needs-human（只追加，不改写、不删除已有行）。
      - **执行记录（2026-08-21）· 落点改为 §2 会话日志，§3 不新增 `open` 行**：本项的前提是上一项会退 1、
        因而存在「等人划名单」这件待办。该前提已随 `4bbe3f5` 消失——本 plan `## Human Handoff` 的验收条件
        （`check_expected_red.py` → exit 0）在开工前就已满足。此时往 §3 塞一条 `[open]` 等于凭空造一个人的待办，
        违反裁判规则 2 的诚实要求。故改为向 **§2 会话日志**（同样是追加式证据段）追加 4 行：
        执行结果与四条命令退出码 + sha `6b52f3b`、`9292b5b` 遗留契约测试已清、§3 不新增 open 行的理由、红线区间自查。
        `git diff --stat docs/masterplan/STATE.md` → `5 insertions(+)`、删除行数 0，只追加不改写（红线 5 满足）。
      - 授权链与 plan 2 相同：`AGENTS.md` 红线 5「`STATE.md` 只允许追加证据行」+ 执行器人格 `tools/mission-driver/agents/build.claude.md` 的直接指示，二者按 `AGENTS.md` 开头的次序高于 `01-EXECUTION-MODEL.md` §1「角色 B 不得手写 STATE」与 `gate-verify.mjs` 注释的反向说法；该矛盾已登记，**不由本 plan 消解**。
      - 行格式照 §3 表头，四个字段齐全，WBS 行 ID 用 **P0.3**（`02-WBS.md` 里快照 diff 是 P0.3；roadmap 的「工作项 2」是 mission 内编号，别混用）。处置栏留 `open`。
      - Skill: `none`
- [x] `Add` **末步**：把本 plan 文件头的 `> Plan Status:` 由 `active` 改为 `deferred`，并在 `## Human Handoff` 写明重开条件。
      - **执行记录（2026-08-21）· 保持 `active`，不置 `deferred`**：`deferred` 的唯一理由是「等人划名单」，
        而人已在开工前用 `4bbe3f5` 做完（见上两项）。本 plan `## Human Handoff` 自己写的重开条件就是
        「上述提交落地后把本 plan 由 `deferred` 改回 `active` 走关闭审计」——先置 `deferred` 再立刻改回 `active`
        没有任何信息量，且会让引擎误以为此处仍卡着人。故直接停在 `active`，交独立 `CLOSURE_AUDIT` 关闭。
      - **`CLOSURE_SCRIPT_CHECK` 判 fail 不再是死路**：`tools/mission-driver/flows/plan-execution.json` 的
        `CLOSURE_SCRIPT_CHECK.transitions.fail` 是 `goto CLOSURE_AUDIT`（不是 retry EXECUTE）。
        起草时担心的「反复重选烧预算」在这条路径上不成立：9 个未勾的 Closure Gates 恰好把流程送进独立关闭审计，
        这正是它们该走的地方。
      - 这一步**必须在所有执行项与 Exit Criteria 打勾之后**做。
      - ⚠️ **不要为了让 `CLOSURE_SCRIPT_CHECK` 变绿而去勾 `## Closure Gates`。** 那 9 个框里包含「closure audit was independent」「closure evidence exists in files」——本 plan 走到这里时它们是**假的**（`## Closure` 还是 `<未关闭>`）。勾上就是自证关闭，违反 `AGENTS.md` 裁判规则 1/2 与计划指南规则 13。`closureScriptCheck` 确实会因这些未勾的框判 fail，**这是预期**：子流程本来就会因 `GATE_VERIFY` 终局为 `failed`，追一个绿的 script check 什么也换不来；真正止住反复重选、保住预算的是自置 `deferred`，不是绿的 script check。
      - Skill: `none`

Exit Criteria:

- [x] `docs/architecture/` 下已记录 Snapshot / 来源接口 / Diff 的结构边界与不变量 —— `docs/architecture/module-boundaries.md` **§11.5 状态快照与结构化 diff 的结构边界**
- [x] `docs/logs/2026/08-20.md` 已更新，含命令原文 + 退出码 + sha —— 实际落在 `docs/logs/2026/08-21.md`（执行日；理由见上方执行记录）
- [x] ~~`STATE.md` §3 多出一行 `[open]`~~ —— 前提消失，改为 §2 追加 4 行证据；`git diff --stat docs/masterplan/STATE.md` → `5 insertions(+)`，删除 0，**只有新增行**
- [x] 红线 1 自查用**区间** diff：`git diff --name-only 8d73ee5..HEAD -- tests/gates/ .github/workflows/ docs/masterplan/DECISIONS.md` → **输出为空**（`8d73ee5` 是本轮开工时的 HEAD；`git diff --name-only HEAD` 只看未提交改动，与 `gate-verify.mjs` 的写保护共享同一盲区，自查不能沿用它）
- [x] Phase 1–3 的**执行项与 Exit Criteria** 全部 `[x]`；`## Closure Gates` 的 9 个框**保持未勾**，等独立关闭审计
- [x] ~~本 plan 文件头为 `> Plan Status: deferred`~~ —— 执行步收尾时改为 **`active`**：deferral 的唯一理由（等人划名单）已由人在开工前的 `4bbe3f5` 消解，理由见上方执行记录。**2026-08-21 独立关闭审计通过后由审计步改为 `completed`**（见 `## Closure`）

## 收尾协议（给执行本 plan 的会话）

> **执行记录（2026-08-21）**：下面三条的共同前提——「名单在红线内、只能等人划」——已由 `4bbe3f5` 消解
> （名单迁至红线外的 `tools/gates/expected-red.txt`，`AGENTS.md` 红线 1 同步补了边界；人已划掉含本工作项
> 两条 L1 在内的 5 行）。故第 1 条描述的矛盾本轮**没有发生**（`build-verify` 若再要求划名单，划的是账本不是裁判，
> 不触红线）；第 2 条的「`GATE_VERIFY` 判 fail 是预期终局」**不再成立**——`check_expected_red.py` 实测 exit 0；
> 第 3 条的解除条件（人的划名单提交落地 + 判定器退 0）已满足，故本轮可以直陈实测退出码，
> 但**关闭**仍未完成（`## Closure` 是 `<未关闭>`、9 个 Closure Gates 未勾），完成宣称仍限于「执行完毕」这一层。

与 plan 2 的 `## 收尾协议` 逐条适用，此处不重复推导，只点名三件最容易走错的：

1. **`missions/prompts/build-verify.md` 步骤 c 会明确要求你把转绿的测试从 `tests/gates/EXPECTED_RED.txt` 删掉并入代码提交**；`check_expected_red.py` 的输出与 `gate-verify.mjs` 的回灌会把同一句话再送你两遍。按 `AGENTS.md` 开头的优先级次序（红线 > masterplan 执行协议 > AGENTS 其余 > 上游模板默认），**红线 1 胜出，不执行**。同一份 `build-verify.md` 第 3 条自己就写着「`tests/gates/**` 一个字都不许改」，它内部矛盾——矛盾由人消解，登记在 `docs/backlog/needs-human-expected-red-handoff.md` 冲突 1。
2. `GATE_VERIFY` 判 fail 是**预期终局**，不停机、不写 STATE、不重试到天亮；plan 留在 `active` 会被 `activePlans()` 反复重选并重跑已完成的活，所以末步必须自置 `deferred`。
3. 完成宣称写成「**我认为完成，待验证**」，直到人的划名单提交落地、`check_expected_red.py` 退 0。

## Human Handoff（阻塞关闭，不阻塞执行）

- ✅ **已满足（2026-08-21，人在本 plan 开工前完成）**。下面三行是原文，保留以便对照。
- 待办：人提交一次带 `Gates-Change-Approved-By: <姓名>` trailer 的提交，把 `tests/gates/EXPECTED_RED.txt` 里 `test_snapshot_diff_structured.py` 的**两条 L1**（`test_two_snapshots_of_unchanged_site_diff_empty`、`test_diff_is_structured_not_text`）划掉。**第三条 `test_field_addition_shows_up_as_structured_change` 必须留在名单里**——它属工作项 6，本 plan 结束后它仍然红。
- 验收：`python3 tools/gates/check_expected_red.py` → exit 0。
- **实际落地**：`4bbe3f5`（`Gates-Change-Approved-By: lize`）不止划名单，还把名单整体迁出红线 1
  （`tests/gates/EXPECTED_RED.txt` → `tools/gates/expected-red.txt`），并同步改了 `AGENTS.md` 红线 1 的边界说明。
  一次划掉 5 行（规范化器 3 + 快照 diff 2）；第三条 live 断言仍留在名单里，符合本节要求。
  验收实测：`python3 tools/gates/check_expected_red.py` → **exit 0**（门禁 13 项：预期红 8，绿 5，跳过 0）。
  故本 plan **不进入 `deferred`**，按下条重开条件直接停在 `active` 等独立关闭审计。
- 重开条件：上述提交落地后把本 plan 由 `deferred` 改回 `active` 走关闭审计；或人按交接文档冲突 3 选了选项 (d)（关闭与划名单解耦），则直接走关闭审计。
- 本节故意不用 `[ ]`：只有人能勾的框会让 `closureScriptCheck` 每轮判 fail 并被反复重选，把预算烧光。

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，agent `a39d683b1f978d6d3`）—— 命中本 plan 的：A、B、C、D、F、G（与 plan 2 同源，处置相同）、H（`capture` 全无非空洞覆盖：Phase 2 每一条都在测 `diff`，而 Phase 1 的 `a == b` 判据在两个零条目快照上恒真；且「返回空快照」与「来源可插拔」自相矛盾）、I（与 `02-WBS.md` 的顺序/前置/验收口径分歧未登记；前置只是散文）。另收下 nit 9（架构文档落点不该留给执行会话选）。
  - 评审同时确认了本 plan 的两处关键复述属实：`test_snapshot_diff_structured.py` **没有**模块级 `live` 标记，`-m 'not live'` 确实只选中那两条 L1；第三条 live 断言确实要求 diff 条目带 `.doctype` / `.fieldname`。
- Revision after iteration 1: Decision 改写为「离线来源从确定位置读、读不到即零条目」并说明它与「硬编码返回空」的区别；Phase 2 新增 `tests/unit/test_snapshot_capture.py` 五条非空夹具覆盖，并给 Phase 1 那条空洞判据加了显式免责；删掉不可勾的 Closure Gate，改为 `## Human Handoff` + 末步自置 `deferred`；后果链按引擎实测重写；登记与 `02-WBS.md` 的两处分歧；Phase 1 首项改为「plan 1 未 completed 或 plan 2 未跑完即停手」（并说明两者会争抢同一份清单文件）；架构落点定死为 `docs/architecture/module-boundaries.md`；STATE §3 补授权链与 WBS 行 ID **P0.3**。
- Independent draft review iteration 2: **needs revision** —— A/B/C/D/F/G/H/I 逐条确认已解决（H 被评为本批最强的一处修订），但**新发现 M**（与 plan 2 同源）：「全文无剩余 `[ ]`」判据会逼执行器自证关闭。另 3 条 nit。
- Revision after iteration 2: 同 plan 2 的处置。
- Independent draft review iteration 3: **needs revision** —— Exit Criteria 已改对，但 `deferred` 那一步的理由**漏改**，仍写着「必须在所有其他项打勾之后做——`closureScriptCheck` 对 `totalUnchecked > 0` 判 fail」，与四行之下的判据自相矛盾（指南规则 11）。
- Revision after iteration 3: 把 plan 2 的 ⚠️ 段原样补到该项上，「所有其他项」收窄为「执行项与 Exit Criteria」。
- Independent draft review iteration 4: **accept**（agent `a39d683b1f978d6d3`，复核 L173-175 那一处修订：与四行之下的 Exit Criterion 已一致，9 个 Closure Gates 确认未勾）。**共识达成，转 `active`。**

## Closure Gates

> 九框由**独立关闭审计**（`CLOSURE_AUDIT`，fresh session，不带实现上下文）在 2026-08-21 逐条复核后勾选。
> 执行步按 Phase 3 的 ⚠️ 段保持全部未勾，未自证关闭——该约束已被遵守，见 `## Closure` 的审计记录。

- [x] in-scope behavior is complete —— `agenerp/snapshot.py` 全部落地并被 unit + 门禁真实调用；`SiteSnapshotSource.read` / `schema_drift` 按 Non-Goals 保留 `NotImplementedError` 且仍被 `test_contract_surface.py` 断言红着
- [x] relevant docs are aligned —— `docs/architecture/module-boundaries.md` §11.5（L209-247）已记录 `Snapshot` / `SnapshotSource` / `diff` 的职责与不变量、来源解析次序、两条显式拒绝、工作项 4 接缝
- [x] verification has run（审计原样复跑，退出码单独取 `$?`）：`python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q -m 'not live'` → exit 0（2 passed, 1 deselected）/ `python3 -m pytest tests/unit -q` → exit 0（40 passed）/ `ruff check agenerp tests/unit` → exit 0 / `python3 tools/gates/check_expected_red.py` → exit 0（门禁 13 项：预期红 8，绿 5，跳过 0）
- [x] scoped verification is not conflated with full verification —— **verification scope limited**：本 plan 刻意只跑 L1 子集（`-m 'not live'`），live 那条不在范围内；全量 `python3 -m pytest tests/gates -q --tb=line` 实测 1 failed / 5 passed / 7 errors，**未报全绿**，残余红项均属工作项 3/4/5/6
- [x] no in-scope item downgraded to deferred/follow-up —— `## Deferred But Adjudicated` 三项（live 断言 / 断言 DSL / 站点来源）逐条对照 roadmap 对照表与 Non-Goals，均是本 plan 起草即声明的范围外项，无在范围内的活被降级
- [x] independent draft review completed and recorded —— `## Draft Review Record` 四轮迭代（iteration 4 `accept`，agent `a39d683b1f978d6d3`）
- [x] text consistency verified: status, phases, gates, and log all agree —— Plan Status `completed` / Phase 1–3 `Status: completed` 且执行项与 Exit Criteria 全 `[x]` / 本节九框全 `[x]` / `docs/logs/2026/08-21.md` 与 `docs/masterplan/STATE.md` §2 四行证据一致
- [x] closure audit was independent —— 由独立 `CLOSURE_AUDIT` 代理完成，不采信 plan 内既有 `[x]`，逐条读活代码 + 原样复跑
- [x] closure evidence exists in files —— `docs/architecture/module-boundaries.md` §11.5、`docs/logs/2026/08-21.md`、`docs/masterplan/STATE.md` §2（2026-08-21T10:20Z 四行）、commit `9292b5b` / `6b52f3b` / `084c17e`

## Deferred But Adjudicated

### `test_field_addition_shows_up_as_structured_change`（live）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: roadmap §工作项 → 门禁测试对照 明确把它划给**工作项 6**，其前置是工作项 4 提供 `live_site` fixture。本 plan 已按它的断言形状定稿 `Diff` 条目（含 `.doctype` / `.fieldname`），接缝留好。
- Successor Required: `yes` —— 工作项 6 的 plan
- 重开事件：工作项 4 交付 `live_site` fixture 后立即可做。

### 断言 DSL（WBS P0.3 的第三块）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: roadmap 工作项 2 的绑定门禁只覆盖「快照 + 结构化 diff」，DSL **没有任何判据**。按 mission 规则「判据先行，没有就先补一条红的（补测试要人批）」，无判据不开工。
- Successor Required: `no`
- 重开事件：人补出绑定门禁测试并批准后。

### 站点来源实现（`capture` 接活站点）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 属 roadmap 工作项 4（工具契约层 v0）。本 plan 只留接口与 `NotImplementedError`，不猜实现。
- Successor Required: `yes` —— 工作项 4 的 plan
- 重开事件：工作项 4 开工时。

## Closure

Status Note: 三个 Phase 的执行项与 Exit Criteria 全部落地并经独立审计复核；四条验证命令原样复跑全部退 0；
`## Human Handoff` 的验收条件（`check_expected_red.py` → exit 0）已由人的 `4bbe3f5` 满足，deferral 理由不复存在。
红线自查用区间 diff 通过（`tests/gates/` / `.github/workflows/` / `DECISIONS.md` 本轮零改动），
`STATE.md` 只追加不改写（`5 insertions(+)`，删除 0）。故本 plan 可关闭为 `completed`。

Closure Audit Evidence:

- Auditor / Agent: 独立关闭审计代理（`CLOSURE_AUDIT`，fresh session，不带实现上下文，未参与本 plan 任何实现）
- 审计日期 / 基线: 2026-08-21 · HEAD `084c17e` · 工作区 `git status --porcelain` 输出为空
- 审计方法: **不采信 plan 内既有 `[x]`**——逐条读活代码与活文档，原样复跑全部验证命令，退出码单独取 `$?`

| 复核项 | 方法 | 实测 |
|---|---|---|
| L1 门禁 | `python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q -m 'not live'` | **exit 0** · 2 passed, 1 deselected |
| unit 全量 | `python3 -m pytest tests/unit -q` | **exit 0** · 40 passed |
| lint | `ruff check agenerp tests/unit` | **exit 0** · All checks passed! |
| 预期红名单 | `python3 tools/gates/check_expected_red.py` | **exit 0** · 门禁 13 项：预期红 8，绿 5，跳过 0 |
| 全量门禁（scope 限制的对照） | `python3 -m pytest tests/gates -q --tb=line` | 1 failed / 5 passed / 7 errors —— 未报全绿 |
| live 断言红因 | `python3 -m pytest tests/gates/...::test_field_addition_shows_up_as_structured_change -q --tb=line` | 仍红，红因为 `live_site` 的 `NotImplementedError`（属工作项 4/6，未被本 plan 弄成别的错） |
| 红线 1/2/3 | `git diff --name-only 8d73ee5..HEAD -- tests/gates/ .github/workflows/ docs/masterplan/DECISIONS.md` | **输出为空** |
| 红线 5（STATE 只追加） | `git diff --stat 6b52f3b..084c17e -- docs/masterplan/STATE.md` | `5 insertions(+)`，删除 0 |

- 反空壳复核（逐个读代码，非签名比对）: `capture` 经 `resolve_source` 真实走 `OfflineSnapshotSource.read` 的
  `glob("*.json")` → `json.loads` → `normalize` → `SnapshotEntry` 路径；`diff` 用 `by_key()` 集合运算算出三类，
  `changed` 带 `before` / `after`；`SnapshotScopeMismatch` 是显式 `raise` 而非静默降级。**无空函数体、无 `return None` 占位、无吞异常**。
  `tests/unit/test_snapshot_capture.py` 9 条全部用 `tmp_path` **非空夹具**驱动（3 条目断言 / 改夹具后不再相等 /
  易变字段被剥掉 / 显式来源优先），起草评审点名的 H 类「零条目空洞判据」确认已被压住。
  `tests/unit/test_snapshot_diff.py` 11 条覆盖增删改不串味、`(doctype, fieldname)` 二元身份、跨 scope 抛错、纯函数不改入参。
- 未被顺手做掉的邻项复核: `tests/unit/test_contract_surface.py` 的 `NOT_YET_IMPLEMENTED` 仍含
  `agenerp.pack:export_customizations` / `agenerp.pack:apply_pack` / `agenerp.snapshot:schema_drift`，且测试仍断言其抛 `NotImplementedError`。
- 五点一致性: Plan Status `completed` / Phase 1–3 `Status: completed` 且全 `[x]` / Closure Gates 九框全 `[x]` /
  `docs/logs/2026/08-21.md` 顶部条目 / `docs/masterplan/STATE.md` §2 四行 —— 逐条比对，一致。
- Deferred 诚实性: 三项均为起草即声明的范围外项，与 roadmap 对照表（工作项 4/6）及 Non-Goals 对齐，
  无在范围内的实缺或契约漂移被藏进 Deferred / Follow-up。
- 落地: 本次审计把 `Plan Status` 由 `active` 改为 `completed`、`Last Reviewed` 改为 2026-08-21、
  勾选九个 Closure Gates、写入本节证据，并把 `docs/backlog/p0-foundation-roadmap.md` 工作项 2 由
  `planned` 改为 **`done`**（该表定义 `done` = 完成且通过 closure 审计 + 门禁转绿并从预期红名单划掉，两条现均为真）。
- 结论: **approved**

Follow-up:

- 工作项 4（工具契约层 v0）落地 `live_site` fixture 后，接上 `SiteSnapshotSource.read`；届时复核离线快照与站点快照的条目类型是否一致（Phase 1 Decision 的翻案条件）。
- roadmap 工作项 1（定制包规范化器）仍为 `todo`，属 plan 2 的遗留，不在本 plan 范围内，交后续轮次处理。
