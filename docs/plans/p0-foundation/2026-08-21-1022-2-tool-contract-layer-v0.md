# 2026-08-21-1022-2 工具契约层 v0 · 声明面（契约格式 + 10 个只读工具的声明）

> Plan Status: active
> Mission: p0-foundation
> Work Item: 4. 工具契约层 v0（先包 10 个只读工具）—— **只做声明面（A 半），不解锁 L2（B 半）**
> Last Reviewed: 2026-08-21
> Source: `docs/backlog/p0-foundation-roadmap.md` Work Item Status 第 4 项（`todo`）·判据取自 `docs/masterplan/02-WBS.md` **P0.2** 行
> Related: `2026-08-21-1022-1-zero-dep-boot-compose.md`（同批，先于本 plan；WBS 把 P0.1 列为 P0.2 的前置）·`2026-08-20-2341-3-snapshot-structured-diff.md`（其 §11.5 留下的 `SiteSnapshotSource` 接缝归本工作项的 B 半）
> Audit: required

## Current Baseline

起草时（2026-08-21，HEAD `f47031f`）读活代码 + 实跑 + 独立评审复核得出。**凡是被评审推翻的说法，这里写的是校正后的版本。**

### 判据归属：先把话说准

- roadmap §「工作项 → 门禁测试对照」第 4 行的三列是 `工作项 | 关闭它的门禁测试 | 层`，其**门禁测试列不是空的**，
  写着「提供 `live_site` fixture，解锁 L2 各项」；`—` 在的是**层**列。
  → **工作项 4 是有绑定判据的，那条判据就是「解锁 L2」**，也就是下表的 B 半。
  （对照第 7 行，它的门禁测试列才真的写着「尚无门禁——**开工前先补一条**」。两者不是一回事，别混。）
- 因此本 plan **切出来的 A 半没有绑定的门禁测试**。这不是 roadmap 的设计，是本 plan 自己的切法，责任在本 plan，见 Phase 1 的 `Decision` 与 `## 判据缺口登记`。
- A 半的判据取自 `docs/masterplan/02-WBS.md` **P0.2** 行：验收 = `pytest tests/contracts -q` 退 0，括号里写明「**前置条件/后置断言可独立测试**」。
  这条是**人写在 masterplan 里的**，不是 loop 发明的——但它**不在判定面上**（见下条），这个缺口必须摆出来，不能装作没有。
- **判定面实测**：`missions/p0-foundation.json` 的 `commands.test` = `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`；
  `tools/gates/check_expected_red.py:35` 固定跑 `pytest tests/gates`。
  → **`pytest tests/contracts` 不被 `GATE_VERIFY` 复跑**。本 plan 的验收命令**没有任何外部裁判**，等于 loop 自己给自己判分。
  这正是首轮循环踩过的坑（`STATE.md` 2026-08-21T01:56Z 缺陷 ②：「判定面漏一块，循环就不会自己发现」）。
  `missions/**` 是角色 B 禁区（`01-EXECUTION-MODEL.md` §1 禁止项 ③），loop 无权自己补。
  **这个缺口由本 plan 就地裁定（不占 `STATE.md` §3 的 `[open]` 行），完整论证、备选与翻案条件见 Phase 1 的对应 `Decision`。**
- **WBS P0.2 这一行本身处在一个已登记未决的争议里**，引用它就得说清楚：
  `docs/backlog/needs-human-expected-red-handoff.md` 冲突 4.2 记着「`02-WBS.md` 与 `p0-foundation-roadmap.md` **执行顺序相反** … WBS 那张表的**前置与顺序需要人来对齐**」，状态仍 `open`。
  本 plan 采信它的**验收列**（那是唯一写明 A 半判据的地方），并按 WBS 记下它的**前置列 = P0.1**（即 `…-1-zero-dep-boot-compose.md`）；
  排序仍按 roadmap（引擎 `roadmapPath` 取的是 roadmap），与前批 plan 的做法一致。**本 plan 不替人消解这个争议。**

### 工作项 4 的两半

| 半 | 内容 | 归属 |
|---|---|---|
| A | 契约**声明格式** + 10 个只读工具的**声明** + `tests/contracts/` 独立可测 | **本 plan**（纯 L1，不需要活站点） |
| B | `live_site` fixture 接活站点 + `SiteSnapshotSource.read` 实现，**解锁 L2** | 后继 plan。前置：`…-1` 的可起栈 compose；**且需人改 `tests/gates/conftest.py`** |

**本 plan 关闭 ≠ 工作项 4 关闭。** roadmap 的 `Status values` 表把 `done` 定义为「对应门禁测试已转绿并从名单划掉」，
而工作项 4 绑定的是 B 半——所以本 plan 关闭时 roadmap 工作项 4 置为 **`planned`**（定义：「已有执行 plan 且通过草案评审」），**不是 `done`**，下一轮由 B 半的 plan 接手。

### 代码与文档的现状

- **`tests/contracts/` 目录不存在**（`ls tests` → 只有 `gates`、`unit`）。`agenerp/` 只有 `__init__.py` / `pack.py` / `snapshot.py`。
- 契约结构已有 owner doc 定稿：`docs/architecture/module-boundaries.md` §7.1 给出 YAML 形状
  （`tool` / `target` / `risk` / `requires_permission` / `preconditions` / `postconditions` / `on_violation` / `approval`），
  §7.3.1 明确「只读工具也有契约」并要求 §7.1 的结构**补上 `returns` 段**（裁剪规则、上限条数、必须保留什么）。以上逐条核对过原文。
- §11.5 已留好接缝：`SiteSnapshotSource.read` 抛 `NotImplementedError`，文中逐字写着「**活站点来源属 roadmap 工作项 4（工具契约层 v0）**，此处只留接口」。
- **十个工具的名字全部在 owner doc 里出现过，但「哪十个」是本 plan 的选法，不是 owner doc 的清单**（评审校正）：
  `implementation-roadmap.md:71` 与 WBS P0.2 都只写「10 个只读工具」，**没有列表**。
  `docs/design/agents-and-roles.md` §5.1 列的是**按 Agent 分的工具集**，解释 Agent 七个，另有 `anomaly.scan` / `benchmark.compare` / `dsl.schema` / `field.catalog` / `dsl.validate` / `dsl.preview` 也是只读的。
  → 选法必须写成 `Decision`，把选法、排除项与可逆性写进 owner doc 与 log，见 Phase 2 首项。
- 每个工具的硬约束都有实测出处（照抄清单会漏掉杀伤点，逐条核对过原文）：
  - `permission.scope`（§5.1 引 Spike 01/02）：**必须逐个调 `frappe.has_permission`，不得从 DocPerm/Custom DocPerm 反推**（反推版漏报 `Sales Invoice`，**漏报比噪声危险**）；**必须按 app 过滤掉框架 DocType**（不过滤 83/61 个，过滤后 34/12 个）。
  - `doc.links` 必须返回 `from_is_submittable`（`module-boundaries.md:82`）；下游筛选是「排除已取消」而非「只要已提交」（`docs/analysis/2026-08-19-pre-build-validation.md:143`）。
    ⚠️ **两份文档的字段名对不上**：架构文档写 `from_is_submittable`，分析文档写 `is_submittable`。架构文档是 owner，取 `from_is_submittable`；**这处漂移按计划指南规则 14 不可降级，必须在 Phase 3 登记**。
  - `lineage.trace` 必须同时扫主表级与子表级 Link 并回溯父单据——实测 21 个指向 Sales Order 的 Link 里 **14 个在子表**，只扫主表返回空结果。
  - `doc.get` 不裁剪会把 `_comments` / `_liked_by` 倒给模型（§7.3.1）。
  - 证据充分性门禁 L1/L2（§5.0①）：「问题点名了某张单据 → 接受 answer 前必须调用过 `doc.links`」「`doc.links` 查出的已提交下游单据必须逐张 `doc.get` 后才能作答」。
    §5.0① 明说这是「§7 工具契约的一个特例：只读工具的**前置条件**约束的是**什么时候允许停下来**」。
- **`live_site` 这一半撞红线。校正后的准确说法（原稿说「绕不过去」，评审推翻了）**：
  - `live_site` 定义在 `tests/gates/conftest.py:15`（`:17` 是那句 `raise`），属红线 1。
  - **同名 fixture 覆盖确实不可能**：实测外层 `conftest.py` 定义 `live_site` 返回真对象、内层同名 fixture 抛错 → 运行内层测试得 `NotImplementedError: inner`。**就近者胜。**
  - **但存在一条 hook 级绕道**：根级 `conftest.py` 实现 `pytest_fixture_setup` 并对 `fixturedef.argname == "live_site"` 直接塞 `cached_result`，
    可以在**一个字节都不改 `tests/gates/**`** 的前提下让 fixture 被顶掉（评审实跑得 `1 passed`）。
    ⚠️ **那次实跑是在 scratchpad 里按 `tests/gates/conftest.py` 的形状复刻的最小样例，不是本仓真实的门禁套件**——
    评审期间没有任何一条真门禁被弄绿。写清楚这一点，免得后继读者以为审查时动过裁判。
  - → **本 plan 与其后继一律不得使用这条绕道**：它在字面上不碰红线文件，但实质是从外部改写裁判的行为，与红线 1 的用意直接冲突，
    且会让「门禁绿了」不再等于「实现到位」。它必须作为一个**处置选项交给人明确禁止或授权**，而不是被 loop 悄悄用掉、也不是被谎报为「不存在」。
- 环境事实（本 plan 开工时须**重新实测并记录**，不许沿用这里的数字——`…-1` plan 会改变名单计数）：
  起草时 `python3 tools/gates/check_expected_red.py` → **exit 0**；`python3 -m pytest tests/unit -q` → **exit 0（40 passed）**；`ruff check agenerp tests/unit` → exit 0。
- CI 的 `gates-l1` 只 `pip install pytest`；`agenerp` 必须**零第三方依赖可导入**（`docs/context/project-context.md` 技术基线）。
  本机装有 PyYAML 6.0.3 与 pydantic——**本机装了不等于可以用**。

## Goals

- 交付 `agenerp/contracts.py`：契约的**声明格式**与**校验器**，形状逐条对齐 `module-boundaries.md` §7.1 + §7.3.1 的 `returns` 段，零第三方依赖。
- 交付 10 个只读工具的**契约声明**，且每条实测硬约束都表达在声明里（不是写在注释里）：
  `permission.scope` 的两条、`doc.links` 的 `from_is_submittable`、`lineage.trace` 的子表扫描、`doc.get` 的裁剪、证据门禁 L1/L2、
  以及 §7.5 要求的「本工具是否会返回用户可写自由文本」这一**声明位**。
- 交付 `tests/contracts/`：使 `python3 -m pytest tests/contracts -q` → **exit 0**，其中**前置条件与后置断言各自可独立测试**（WBS P0.2 判据的字面要求），全程不依赖活站点。
- **把三个缺口摆到人看得见的地方**：A 半不在判定面上、十个工具的选法、B 半的红线障碍与那条 hook 绕道。
  其中**只有 B 半那一条进 `STATE.md` §3 的 `[open]`**（真正只有人能做的红线决定）；另两条由本 plan 就地裁定，落在 owner doc / log / `Deferred But Adjudicated`。

## Non-Goals

- **不实现 B 半**：不接活站点、不实现 `SiteSnapshotSource.read`、不实现 `live_site` / `pack_repo` / `compose_stack` 任何一个 fixture。
- **不使用 `pytest_fixture_setup` 一类 hook 从外部改写门禁 fixture 的行为。** 见 Current Baseline 最后一条与 `## 判据缺口登记`。
- **不实现运行时机制，只实现声明面。** 具体地：§7.4 的**权限拒绝熔断**（N=5）与 §7.5 的**数据边界标记包裹函数**不在本 plan 内——
  它们是控制循环的运行时部件，`02-WBS.md` 的 P0 段**没有任何一行**对应它们（最近的落点在 P1/P3.0），且 P0 阶段还没有控制循环去消费它们。
  §7.5 在本 plan 里只保留**声明位**（契约必须声明该工具是否返回用户可写自由文本），包裹动作归后继。处置见 `## Deferred But Adjudicated`。
- 不写 Frappe 运行时代码、不生成运行时 Server Script（红线 7）。
- 不实现写契约（`rollback_and_report` / savepoint 语义属 WBS **P3.1**）。
- **不改 `tools/gates/expected-red.txt`**：本 plan 不让任何门禁转绿，名单一行都不动。
- 不改 `tests/gates/**`、`missions/**`、`.github/workflows/**`、`docs/masterplan/**` 已有行（`STATE.md` §3 只追加）、`tools/gates/check_expected_red.py`、`tools/gates/gate-verify.mjs`。
- 不动 `agenerp/pack.py` 与 `agenerp/snapshot.py` 的既有已实现行为（`normalize` / `capture` / `diff`）。
- **不把 roadmap 工作项 4 置为 `done`**（理由见 Current Baseline「工作项 4 的两半」末段）。本 plan 只把它推进到 `planned`，见 Phase 3。

## Task Route

- Type: `app-layer design change`（新增一个公共契约面 `agenerp.contracts`，后继 P1–P3 都会依赖它的形状）
- Owner Docs: `docs/architecture/module-boundaries.md` §7（契约结构的真相源，只读）·`docs/design/agents-and-roles.md` §5.0/§5.1（工具与实测硬约束，只读）·`docs/masterplan/02-WBS.md` P0.2（判据，只读）·`docs/architecture/module-boundaries.md` 与 `docs/context/project-context.md`（本 plan 要更新的 owner doc）
- Skill Selection Basis: `docs/skills/` 下无「设计声明式契约格式」对应的方法技能；形状由 §7.1 已定稿的结构直接约束，属受限选择。各阶段 `Skill: none`。

## Infrastructure And Config Prereqs

- 无新增依赖、无端口、无环境变量、无外部服务。**`agenerp.contracts` 只用标准库。**
- 契约声明用**纯 Python 数据结构**表达，不引 PyYAML：§7.1 的 YAML 是文档呈现形式，不是运行时格式。
- **软前置**：WBS P0.2 的前置列写着 P0.1，对应 `…-1-zero-dep-boot-compose.md`。本 plan 的 A 半技术上不需要它（全程无活站点），
  但排序按 WBS 与 roadmap 一致地把它放在后面；**若 `…-1` 未完成，本 plan 仍可执行**——这一点必须在 Phase 1 首项显式确认，避免执行会话自行脑补出一个硬前置而空等。
- 回滚策略：全是新增文件 + 若干处文档追加，`git revert` 即回到今天的状态，无迁移、无外部副作用。

## Execution Plan

### Phase 1 — 开工前置、判据缺口登记、契约声明格式

Status: planned
Targets: `agenerp/contracts.py`、`docs/backlog/p0-foundation-roadmap.md`（仅第 5 点的幂等兜底可能写它）、`docs/masterplan/STATE.md`（**仅第 6 点的停手分支会追加 §3**）
Skill: `none`

- Item Types: `Proof | Decision | Add`
- Prereqs: 无硬前置（软前置见 `## Infrastructure And Config Prereqs`）

- [ ] `Proof` **开工前置检查（第一步，不做完不许写代码）**：
      1. 重新实测并记录三条基线的**今日**退出码：`python3 tools/gates/check_expected_red.py`、`python3 -m pytest tests/unit -q`、`ruff check agenerp tests/unit`。
         **记退出码与输出原文，不许照抄 Current Baseline 里的计数**——`…-1` plan 一旦落地，名单计数就变了。
      2. **记下本 plan 的开工 sha**（`git rev-parse HEAD`）并写进 `docs/logs/`——Phase 3 的三条区间 diff 判据全靠它，不记就没法复核。
      3. 确认 `tests/contracts/` 仍不存在、`agenerp/contracts.py` 仍不存在（若已存在 → 说明有别的会话在做同一件事，**停手**并按下面第 6 点处置）。
      4. 确认 `…-1-zero-dep-boot-compose.md` 的状态。**它未完成不构成阻塞**（A 半不需要活站点），照常继续；
         这一条存在的意义是：不让执行会话把 WBS 的「前置 P0.1」误读成硬前置而空等一轮。
      5. **确认 roadmap 工作项 4 已是 `planned`；若仍是 `todo`，就地改成 `planned`。**
         起草步转 `active` 时已写过一次，这里是幂等复核——没有任何引擎产物负责写它，不复核就可能一直留在 `todo`，
         而「引擎取第一个 `todo`」会让下一轮把 A 半再起草一遍。取值依据见 Phase 3 的归属说明。
      6. 任一「停手」条件成立时：不实现、不提交代码，向 `docs/masterplan/STATE.md` §3 **追加一行**说明，
         并把本 plan 置为 `Plan Status: deferred`（**不要置 `draft`**——`draftPlans()` 会把 `draft` 重新捡起走 `REVIEW_PLANS` → `EXEC_PLANS`，来回弹；`deferred` 才是停住等人的值）。
      - Skill: `none`
- [ ] `Decision` **就地裁定判据缺口 #1，不把它写成 `STATE.md` §3 的 `[open]` 行**（独立评审 NEW-5 逼出来的选择，理由必须写进 plan）：
      - 缺口是真的：`pytest tests/contracts -q` 不在 `commands.test` 里，`GATE_VERIFY` 复跑不到它，本 plan 的主判据没有外部裁判。
      - **但它不该占一行 `[open]`**——理由是**议程不该被淹没**，不是「会停机」（独立评审 NEW-6 校正了这一点，原稿把后果说重了）：
        实测 `tools/mission-driver/` 下没有任何 flow / script / 表达式读 `STATE.md`（唯一命中是人格文本 `agents/build.claude.md:16`）；
        真正的停机开关是 `tools/gates/gate-verify.mjs:71` 落的 `.mission-halt.json`。
        `README.md:38` 是**角色 A RESUME 清单**的一行、`04-RUNBOOK.md:76` 是监控面板的异常信号行——**它们设定的是人下次开工的议程，不是循环的闸**。
        所以代价不是「停掉 7×24」，而是：把三件低代价可逆的事都塞进 §3，会淹没真正需要人裁的那一件（B 半的红线决定），让下一次 RESUME 失焦。
      - **也不能自称有判据。** 裁定如下，三条一起才成立：
        (1) 判据本身**是人写的**——`02-WBS.md` P0.2 的验收列，不是 loop 发明的；
        (2) 本 plan **不关闭工作项 4**（工作项 4 绑定的是 B 半），不存在「拿自判的判据去关闭一个有绑定门禁的工作项」；
        (3) 代偿控制是**独立关闭审计**（`Audit: required`），本仓的关闭审计不采信 plan 内既有 `[x]`、逐条复跑——前两个 plan 的 `## Closure` 记录可查。
      - 备选与否决：(a) 停工等人补一条红门禁——mission 规则「没有就先补一条红的（补测试要人批）」针对的是**工作项**，
        而工作项 4 **有**绑定门禁（B 半）；A 半是本 plan 自己切的一片，够不上那条规则的触发条件。且停工换不来判据，只是把同一个问题推到下一轮再问一次。
        (b) 干脆不做 A 半——那等于工作项 4 永远动不了，因为 B 半被红线卡着。
      - 残余风险：人若认为 A 半也必须有红门禁，本 plan 的交付要补一条门禁再走一次关闭。
        **登记方式是「写到人看得见的地方」而不是「拦住人」**：`docs/context/project-context.md` 的命令表注明它不在 `commands.test` 内，
        `docs/logs/` 与 `module-boundaries.md` 的追加小节各记一次，`## Deferred But Adjudicated` 带重开事件。
      - 翻案条件：人把 `python3 -m pytest tests/contracts -q` 接进 `commands.test`（一行的事，`missions/**` 是角色 B 禁区，loop 无权动），或批准补一条红门禁。
      - Skill: `none`
- [ ] `Decision` 定下契约的**运行时表达形式**：纯 Python 声明式对象（`dataclass`，frozen），**不引 PyYAML**。
      - 备选：(a) YAML 文件 + 解析器；(b) 纯 Python 声明。
      - 否决 (a) 的理由是实测约束不是口味：CI 的 `gates-l1` 只 `pip install pytest`，`import yaml` 会红在缺依赖；
        `docs/context/project-context.md` 的技术基线已把「零第三方依赖可导入」写死。§7.1 的 YAML 是**文档呈现**，不是运行时格式。
      - 残余风险：将来行业包若要让非开发者写契约，可能需要 YAML 入口。缓解——校验器接受的是**已解析的数据结构**，外挂一个 YAML → dict 加载器不改变本层任何签名。
      - 翻案条件：行业包需要外部可编辑契约文件时。
      - Skill: `none`
- [ ] `Add` 实现契约结构，字段逐条对齐 §7.1 + §7.3.1，**一个都不许省**：
      `tool` / `target` / `risk` / `requires_permission` / `preconditions` / `postconditions` / `returns` / `on_violation` / `approval`。
      - `returns` 段按 §7.3.1 的三项要求成形：**裁剪规则**、**上限条数**、**必须保留什么**；另加 §7.5 的**声明位**：本工具是否会返回用户可写自由文本。
      - Skill: `none`
- [ ] `Add` 实现校验器：拒绝结构不合法的契约，**每种拒绝都有独立可测的失败模式**（缺必填段、`risk` 取值非法、`returns` 缺「必须保留什么」、只读工具声明了写副作用等）。
      - **失败要报得准**：错误消息必须指出是哪个工具的哪一段不合法，否则 10 个契约里错一个要人肉找。
      - Skill: `none`
- [ ] `Add` 实现**前置条件与后置断言的求值面**，使二者可脱离活站点被独立测试（WBS P0.2 判据的字面要求）：
      条件对一个**注入进来的只读上下文**求值，返回「满足 / 不满足 + 原因」，**不自己去连任何站点**。
      - 这正是「独立可测」的机制：测试构造上下文即可，不需要 ERPNext。
      - Skill: `none`

Exit Criteria:

- [ ] `python3 -c "import agenerp.contracts"` → exit 0
- [ ] 零第三方依赖判据 —— **写成「导入前后的增量」，不是「导入后的全集」**（独立评审实测：全集写法在本机必红，
      `sys.modules` 里本来就有 `__main__`、`_distutils_hack` 与 site-packages `.pth` 注入的 `__editable___*_finder`，
      且它们在 CI 与本机不一样。**一条在合规模块上也会红的判据是假判据**）：
      取 `import agenerp.contracts` **前后**的顶层模块集合求差，差集中不属于 `sys.stdlib_module_names` 且不是 `agenerp` 的应为空 → exit 0
      （评审已用现有 stdlib-only 模块验证该写法退 0）
- [ ] `ruff check agenerp tests/unit` → exit 0
- [ ] `python3 tools/gates/check_expected_red.py` → **exit 0**，且门禁计数**与本 plan 开工时实测的那组数字一致**（本 plan 不让任何门禁转绿也不弄红；**不写死数字**，因为 `…-1` 会改变它）
- [ ] `docs/masterplan/STATE.md` **本阶段不被改动**（缺口 #1 就地裁定，不占 `[open]` 行；只有 Phase 1 首项的「停手」分支才会追加）
- [ ] 其余 owner-doc 更新归 Phase 3

### Phase 2 — 10 个只读工具的声明 + `tests/contracts/`

Status: planned
Targets: `agenerp/tools_readonly.py`、`tests/contracts/`（新目录）
Skill: `none`

- Item Types: `Decision | Add | Proof`
- Prereqs: Phase 1

- [ ] `Decision` 定下**哪十个**，并写明选法——这是本 plan 自己的选择，owner doc 没给过清单（评审校正）。
      - 选法（写进 plan 与文档，供人复核）：取 `agents-and-roles.md` §5.1 **解释 Agent** 的七个
        （`query.read`、`schema.search`、`snapshot.read`、`lineage.trace`、`rule.lookup`、`system.overview`、`permission.scope`），
        加上 §5.0① 与 `docs/design/context-and-memory.md:59` 在**证据充分性门禁**里点名的三个（`doc.get`、`doc.links`、`meta.fields`）。
      - 排除项与理由（必须写出来，不能只列入选的）：`anomaly.scan` / `benchmark.compare` 属**洞察** Agent，依赖行业包规则（P1 才有）；
        `dsl.schema` / `field.catalog` / `dsl.validate` / `dsl.preview` 属**视图** Agent，依赖视图 DSL（P2 才有）。
        → 选法是「P0 阶段就有真实约束可写的只读工具」，不是「随手凑十个」。
      - 残余风险：人可能本来想的是另一组十个。**缓解不是占一行 `[open]`**（同 Phase 1 缺口 #1 的裁定，理由见那里：§3 是给人的议程队列，把低代价可逆的事塞进去会淹没真正需要人裁的那一件）——
        选法、排除项与理由写进 Phase 3 追加的 `module-boundaries.md` 小节与 `docs/logs/`，并在 `## Deferred But Adjudicated` 记一条 `watch-only residual`。
        **可逆性由本 plan 自己写明**：人若换清单，改的是 `agenerp/tools_readonly.py` 的声明与 `tests/contracts/` 的清单断言，**契约格式本身不受影响**。
      - 若实现中发现某个名字在 owner doc 里指的其实是别的东西 → **停手**，追加登记，**不自行改名**。
      - Skill: `none`
- [ ] `Add` 声明这十个工具的契约，名字逐字取自 owner doc。
      - Skill: `none`
- [ ] `Add` 把每条实测硬约束**写进契约声明本身**（写在注释里不算数，注释不可测）：
      - `permission.scope`：`returns` 声明「按 app 过滤框架 DocType」的裁剪规则；契约里显式记下「**逐个 `has_permission`，禁止从 DocPerm 反推**」这条来源约束，并使其可被断言。
      - `doc.links`：`returns` 的「必须保留」含 **`from_is_submittable`**（架构文档是 owner；与分析文档 `is_submittable` 的差异按 Phase 3 登记）；下游筛选规则表达为「排除已取消」而非「只要已提交」。
      - `lineage.trace`：表达「必须同时扫主表级与子表级 Link 并回溯父单据」。
      - `doc.get`：`returns` 裁剪规则剔除 `_comments` / `_liked_by` 一类框架字段；§7.5 声明位置 `true`（它会返回用户可写自由文本）。
      - 证据充分性门禁 L1/L2 表达为作答类工具的 `preconditions`（§5.0① 明确它属于「什么时候允许停下来」）。
      - Skill: `none`
- [ ] `Proof` 建 `tests/contracts/`，使 `python3 -m pytest tests/contracts -q` → exit 0，**结构上分三组**，每组写明失败意味着什么：
      1. **格式组**：校验器对每种非法结构各红一次。失败 = 校验器放行了不合法契约。
      2. **前置条件组**：对构造出来的只读上下文求值，满足与不满足**各至少一例**。失败 = 前置条件不可独立测试，WBS P0.2 判据不成立。
      3. **后置断言组**：同上，构造「成立」与「不成立」两种结果。失败 = 后置断言不可独立测试。
      - Skill: `none`
- [ ] `Proof` 为每条实测硬约束各写一条回归断言（这些是本项目付过学费的点，不能只靠 review 记住）：
      十个工具清单完整且名字逐字相符、`doc.links` 的「必须保留」含 `from_is_submittable`、`permission.scope` 的裁剪规则存在、
      `lineage.trace` 声明扫子表、`doc.get` 的 §7.5 声明位为 `true`。
      - Skill: `none`
- [ ] `Proof` 确认 `tests/contracts/` **不污染既有判定面**：
      `check_expected_red.py` 内部固定跑 `pytest tests/gates`，新目录不在其范围；
      `pyproject.toml` 的 `testpaths=["tests"]` 会让裸 `pytest` 把三个目录一起收——**必须避免与 `tests/unit` 出现同名文件**
      （评审实测：跨目录同 basename 会产生 `import file mismatch` 并 `Interrupted: 1 error during collection`）。
      - 判法要写准：`pytest tests -q` **本来就退非 0**（还有 8 条预期红门禁），所以判据是**grep 输出里没有 `import file mismatch`**，不是「退出码为 0」。
      - Skill: `none`
- [ ] `Proof` **预先裁定**：本 plan **不需要**改 `tests/unit/test_contract_surface.py`。
      - 依据（评审实测，不是猜）：该文件是两张**显式清单 + 参数化**（`tests/unit/test_contract_surface.py:22-33`），**没有穷尽性断言**，
        且两张清单只管 `agenerp.pack` / `agenerp.snapshot` 的六个名字。新增 `agenerp/contracts.py` 不会让它变红（本机实测仍 40 passed）。
      - 执行时**复跑一次确认**；若确实变红，那说明该文件在本 plan 之前已被别人改过——按 Phase 1 第 6 点停手处置，不要顺手改它。
      - Skill: `none`

Exit Criteria:

- [ ] `python3 -m pytest tests/contracts -q` → **exit 0**（WBS P0.2 的验收命令原文）
- [ ] `python3 -m pytest tests/unit -q` → exit 0（且**未修改** `tests/unit/test_contract_surface.py`）
- [ ] `! python3 -m pytest tests -q --tb=no 2>&1 | grep -q 'import file mismatch'` → **exit 0**
      - **不写成 `| grep -c … → 0`**：`grep -c` 无命中时自身退 1，成功态是 exit 1，属本仓已抓过两次的判据反转。
      - 判的是这个 grep，**不是 pytest 的退出码**——`pytest tests` 本来就退非 0（还有预期红门禁在）。
- [ ] `ruff check agenerp tests/unit tests/contracts` → exit 0（**`tests/contracts/` 必须已存在**，ruff 对不存在的路径直接报错）
- [ ] `python3 tools/gates/check_expected_red.py` → exit 0，计数与开工时实测一致
- [ ] `docs/masterplan/STATE.md` **本阶段不被改动**（十工具选法就地裁定，见 Phase 2 首项）
- [ ] 其余 owner-doc 更新归 Phase 3

### Phase 3 — 文档、B 半交接、收尾

Status: planned
Targets: `docs/architecture/module-boundaries.md`（**只追加**）、`docs/context/project-context.md`、`docs/masterplan/STATE.md`（**只追加 §3**）、`docs/logs/2026/08-21.md`、本 plan 文件自身（末步）
Skill: `none`

- Item Types: `Add | Fix | Proof`
- Prereqs: Phase 1, Phase 2

- [ ] `Add` 在 `docs/architecture/module-boundaries.md` §7 之后**追加**一小节（不改写 §7 已有任何一行），记录契约层 v0 声明面在本仓的落点：
      模块路径、十个工具的清单**与选法**、判据文件、哪些实测硬约束被表达成了可断言的东西，以及**哪些没有**（熔断、数据边界包裹动作 → 指向 `## Deferred But Adjudicated`）。
      - Skill: `none`
- [ ] `Fix` 登记 `doc.links` 字段名的 owner-doc 漂移：`module-boundaries.md:82` 写 `from_is_submittable`，
      `docs/analysis/2026-08-19-pre-build-validation.md:143` 写 `is_submittable`。
      - 处置：**架构文档是 owner，实现取 `from_is_submittable`**；在上一条追加的小节里写明这处差异、取舍理由与出处行号。
        **不占 `[open]` 行**（同 Phase 1 缺口 #1 的裁定，理由见那里；且这是一处已有明确 owner 可裁的命名差异）；`## Deferred But Adjudicated` 记 `watch-only residual` 并带重开事件。
      - **不改 `docs/analysis/` 那份**——它是历史分析记录，改它等于销毁证据。确认存在的 owner-doc 漂移按计划指南规则 14 不可降级，故记 `Fix`。
      - Skill: `none`
- [ ] `Fix` 更新 `docs/context/project-context.md` 的 Verification Commands 表：新增一行 `python3 -m pytest tests/contracts -q`。
      - 该文件自己的规矩：**只准写本机实测跑得出退出码的真命令**，不许留占位符。
      - 同时注明它**不在 `commands.test` 里**（`GATE_VERIFY` 复跑不到），并指向 Phase 1 那条就地裁定（缺口 #1）——否则读者会以为它已被判定面覆盖。
      - Skill: `none`
- [ ] `Add` 向 `docs/masterplan/STATE.md` §3 **追加一行**，登记 **B 半的红线障碍**。
      **这是本 plan 唯一的一行 `[open]`**（缺口 #1、十工具选法、字段名漂移都已就地裁定，理由各自写在对应项里）。为什么这一条必须占一行：
      它要的是一个**红线决定**——`tests/gates/**` 改不改、hook 级绕道禁不禁——按红线 1 只有人能做。
      §3 是给人的议程队列（引擎不读它），这一条正是该上议程的那种事；另外三件低代价可逆的已就地裁定，不占位、不淹没它。
      **同时写明：本行不阻塞本 plan 关闭。** 它挡的是 B 半与工作项 5/6/8，不是 A 半的交付
      （对照 plan `…-2341-2` 的那一行：那条挡的是它**自己**的关闭，所以它必须停在 `deferred`；本 plan 不是那个情形）。
      **授权链**（往 `STATE.md` 写这件事本身有争议，必须引出来）：`AGENTS.md` 红线 5 明文「`STATE.md` 只允许**追加**证据行」，
      执行器人格 `tools/mission-driver/agents/build.claude.md:16` 逐字指示「拿不准就停下来写进 `STATE.md` 的 needs-human 队列，等人」；
      二者按 `AGENTS.md` 开头声明的次序高于 `01-EXECUTION-MODEL.md` §1 表里「角色 B 不得手写 STATE」。
      ⚠️ **这处矛盾尚未被任何交接文档登记**（`needs-human-expected-red-handoff.md` 的四组冲突都不是它）——本 plan 按更高优先级那条执行，把矛盾原文写进 plan 与 log，**不擅自消解，也不为它另开一行**。
      内容必须准确到可供人做红线决定，**不许写成「绕不过去」**：
      - 事实：`live_site` 定义在 `tests/gates/conftest.py:15`（`:17` 是 `raise`），属红线 1；同文件 `:5` 写着「实现到位时把 raise 换成真东西即可」，
        而 `:7` 紧接着写「⚠️ 本文件同样在 `tests/gates/**` 红线内：loop 不得修改」——**那句话是写给人的，不是给 loop 的指令，两句并不冲突**
        （`tests/gates/README.md` 也明写「这个目录里的文件，loop 一律不得修改」）。**不要把它写成第二个「冲突 1」**：冲突 1 已由人在 `920ce0e` 裁定关闭，`tests/gates/EXPECTED_RED.txt` 已不存在。
      - 实测：同名 fixture 覆盖**不可能**（就近者胜，`NotImplementedError: inner`）；但 `pytest_fixture_setup` hook 级绕道**可行**（根级 conftest 即可让门禁 `1 passed`，不碰 `tests/gates/**` 一个字节）。
      - 处置项（**本 plan 不替人选**）：
        (a) 人带 `Gates-Change-Approved-By:` trailer 把三个 fixture 的 `raise` 换成真实现；
        (b) 比照 `expected-red.txt` 的先例，把 harness 接缝也迁出 `tests/gates/`（「测试代码是裁判，harness 是接线」）；
        (c) 维持现状——**代价要写明**：工作项 5/6/8 的判据将永远不可达；
        (d) **明确禁止（或授权）hook 级绕道**。本 plan 的建议是**明确禁止并写进红线说明**，因为它能让门禁绿而实现不到位——但**这是人的决定，不是本 plan 的**。
      - Skill: `none`
- [ ] `Add` 按 `docs/logs/00-log-writing-guide.md` 写 `docs/logs/2026/08-21.md` 条目：交付内容 + 每条验证命令原文 + 退出码 + commit sha，
      并**点明本 plan 只交付工作项 4 的 A 半、工作项 4 停在 `planned`（不是 `done`）**，B 半的前置与障碍指向上一条登记。
      - **同时把与 `tools/mission-driver/prompts/execute.md` 的两处冲突逐字记下**（本仓的惯例是把偏差与授权链写进 plan，见 `STATE.md` 2026-08-21T10:20Z 那条）：
        `:10` 「a. Update the plan's `Plan Status` to `completed`」——要执行会话在关闭审计**之前**就自称完成，与 `AGENTS.md` 裁判规则 1/2（「无权自报通过」）冲突，**裁判规则胜出**；
        `:11` 「b. … change the work item from ❌ to ✅」——要把工作项置 done，而 roadmap `:9` 说该文件「由引擎在 **closure 审计通过后**回写」、`:35` 把 `done` 定义为「通过 closure 审计」，
        且工作项 4 绑定的是 B 半（本 plan 没做）。按次序（红线 > masterplan 执行协议 > AGENTS.md 其余 > **上游模板默认**），`execute.md` 是上游模板默认，**roadmap 与裁判规则胜出**。
      - **工作项 4 的状态：`planned`，且本阶段不写它**（评审 NEW-10：不能一边用 roadmap 的严格读法否掉 `execute.md:11`，一边自己在 `EXECUTE` 里写 roadmap）。归属如下：
        · `todo → planned` **应由把 plan 转 `active` 的那一步写**——`planned` 的定义是「已有执行 plan 且通过草案评审」（roadmap `:34`），
          那正是 `draft → active` 那一刻成立的事实，与「closure 审计通过后回写」说的不是同一件事（那句管的是 `done`）。
          ⚠️ **但没有任何引擎产物被指示去写它**——`plan-review.md:22` 只说改 plan 自己的 `Plan Status`，`closure-audit.md` 里 `roadmap` 出现 0 次。
          所以 Phase 1 第 5 点的幂等兜底不是走过场，它是这条状态转换唯一有保证的落点。
        · `planned → done` 归 `CLOSURE_AUDIT`——但**本 plan 不会走到那一步**：工作项 4 绑定的是 B 半，A 半交付完它仍是 `planned`。
        · **Phase 3 一行 roadmap 都不改**；`EXECUTE` 步内唯一可能的 roadmap 写入是 Phase 1 第 5 点那个幂等兜底
          （起草步已写过时它什么也不做；只有当那次写入没落地时它才补一次）。
        留 `planned` 而不是 `todo` 的理由：留 `todo` 会让下一轮 `DRAFT_PLANS` 把 A 半再起草一遍，白烧一个循环；
        B 半的接续由 `## Deferred But Adjudicated` 的 successor 条目承担（`draft-from-roadmap` 明写会考虑前序 plan 的 deferred 项），**不靠 `todo` 这个信号，也不靠那行 `[open]`**。
      - Skill: `none`
- [ ] `Proof` 红线自查，用**区间 diff**（裸 `git diff` 只看未提交改动，改动一提交就静音）：
      `git diff --name-only <本 plan 开工时的 sha>..HEAD -- tests/gates/ .github/workflows/ missions/ tools/gates/` → **输出必须为空**；
      `git diff <本 plan 开工时的 sha>..HEAD -- docs/masterplan/STATE.md` → **只有新增行**，且 `docs/masterplan/` 下无其他文件被改。
      - `tools/gates/` 整目录都查：本 plan 连 `expected-red.txt` 都不该动。
      - Skill: `none`
- [ ] `Proof` **末步：本阶段不改 `Plan Status`，把它留给 `CLOSURE_AUDIT` 步**——并把「谁写、写什么」说死，否则会烧循环。
      - 事实（评审复核 `flows/plan-execution.json` 的步序）：`EXECUTE → CLOSURE_SCRIPT_CHECK →（fail）CLOSURE_AUDIT → BUILD_VERIFY → GATE_VERIFY`。
        独立关闭审计是**同一子流程里更靠后的一步**，所以在 `EXECUTE` 内部「审计已通过」**永远为假**——把状态切换写在 Phase 3 里，等于写了一条永远走不到的分支。
      - 因此归属如下：
        · `EXECUTE`（本阶段）：把 Phase 1–3 的执行项与 Exit Criteria 打勾，`Plan Status` **保持 `active`**，`## Closure Gates` 九框**保持未勾**。
        · `CLOSURE_AUDIT`（独立审计会话）：审计**通过** → 勾九框 + 置 `Plan Status: completed` + 补 `## Closure` 证据（plan `…-2341-3` 正是这么关的）；
          审计**不通过且需要改代码** → 保持 `active` 让子流程回 `EXECUTE`；
          审计**不通过且阻塞于人** → 置 `Plan Status: deferred` 并写明重开条件（plan `…-2341-2` 正是这么停的）。
          **`deferred` 是「停住等人」的那个值**（不在 `ACTIVE_STATUSES` 也不在 `DRAFT_STATUSES`）；留在 `active` 会被 `activePlans()` 每轮重新选中、把已完成的活重跑一遍。
      - ⚠️ **不要为了让 `CLOSURE_SCRIPT_CHECK` 变绿而去勾 `## Closure Gates`。** 那九个框里包含「closure audit was independent」「closure evidence exists in files」——
        `EXECUTE` 走到这里时它们是**假的**。勾上就是自证关闭，违反 `AGENTS.md` 裁判规则 1/2 与计划指南规则 13。
        `closureScriptCheck` 因未勾的框判 fail 是**预期**（`flow-loader.js` 对 `totalUnchecked > 0` 一律判 fail），且它正是把流程送进 `CLOSURE_AUDIT` 的那一步。
      - Skill: `none`

Exit Criteria:

- [ ] `module-boundaries.md` 的区间 diff 显示**只有新增行**
- [ ] `docs/context/project-context.md` 含 `pytest tests/contracts` 且未新增 `<fill real command>` 占位符
- [ ] `docs/masterplan/STATE.md` §3 共多出**一行** `[open]`（仅 B 半红线障碍），区间 diff 只有新增行
- [ ] `docs/logs/2026/08-21.md` 已更新，含命令原文 + 退出码 + sha，且写明「只交付 A 半、工作项 4 停在 `planned`（不是 `done`）」
- [ ] 区间红线自查两条输出均符合要求
- [ ] owner doc 已更新：`docs/architecture/module-boundaries.md`、`docs/context/project-context.md`
- [ ] 收尾复跑：`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**；`python3 -m pytest tests/contracts -q` → **exit 0**
- [ ] Phase 1–3 的执行项与 Exit Criteria 全部 `[x]`；`## Closure Gates` 九框**保持未勾**，等独立关闭审计
      （**这一条最后勾**——它是对其余各条的汇总自检，先勾就是空话）

## 判据缺口登记

写在这里而不是塞进 `## Deferred But Adjudicated`：那一节的契约是「**不阻塞关闭**」，而下面第 1 条**影响关闭的可信度**，
虽然经裁定不阻塞，也该单独摆出来让审计员一眼看到。把两类东西混在一节里会毁掉那一节的契约（前批 plan 已踩过这个点）。

1. **A 半不在判定面上（已就地裁定，不占 `[open]`）。** `pytest tests/contracts -q` 不被 `GATE_VERIFY` 复跑（`missions/**` 是角色 B 禁区，loop 无权加）。
   裁定依据三条：判据是人写的（WBS P0.2 验收列）· 本 plan 不关闭工作项 4 · 代偿控制是独立关闭审计。完整论证与备选见 Phase 1 的对应 `Decision`。
   **为什么不占 `[open]`**：§3 是**给人的议程队列**，引擎不读它（实测：`tools/mission-driver/` 下无任何产物读 `STATE.md`；停机开关是 `.mission-halt.json`）。
   把三件低代价可逆的事都写进去，会淹没真正需要人裁的那一件。人要翻案，把那条命令加进 `commands.test` 即可。
2. **十个工具的选法是 loop 的选择**（owner doc 没给过清单），**同样就地裁定**：选法、排除项、可逆性写进 `module-boundaries.md` 追加小节与 log，
   `## Deferred But Adjudicated` 记 `watch-only residual`。
3. **B 半的红线障碍与那条 hook 级绕道 —— 这一条占 `STATE.md` §3 的一行 `[open]`。**
   它要的是红线决定（`tests/gates/**` 改不改、hook 绕道禁不禁），按红线 1 只有人能做，正是 §3 该拦的事。
   **本行不阻塞本 plan 关闭**：它挡的是 B 半与工作项 5/6/8，不是 A 半的交付。

**本节不用 `[ ]` 复选框**：`flow-loader.js` 的 `closureScriptCheck` 对 `totalUnchecked > 0` 一律判 fail，
一个只有人能勾的框会让子流程每轮都红、并被 `activePlans()` 反复重选，把预算烧光。诚实地记为文字，而不是记成一个永远勾不上的框。

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，agent `a91304a379609c5a3`）—— 10 条 blocking。
  要害四条：① roadmap 第 4 行的**门禁测试列不是空的**（`—` 在的是「层」列），原稿据此推出的「本工作项没有绑定判据」不成立；
  ② 判据先行：A 半确实没有绑定门禁，且 `pytest tests/contracts` **不在 `commands.test` 里**，等于 loop 自判；
  ③ 「`live_site` 实测无法绕过」**被实跑推翻**——`pytest_fixture_setup` hook 可在不碰 `tests/gates/**` 的前提下让门禁 `1 passed`；
  ④ 原稿引 `tests/gates/README.md` 那句「把 raise 换成真东西即可」是**伪造引文**（该句只在 `conftest.py:5`，README 写的是相反的话），且冲突 1 早已由 `920ce0e` 关闭。
  另有：写死门禁计数（`…-1` 会改变它）、缺开工前置检查与末步 `Plan Status`、熔断/数据边界包裹在 P0 无验收、十工具清单是 loop 自选却被冻进 owner doc、WBS P0.2 被择优引用（前置 P0.1 与冲突 4.2 未提）。nit 若干。
- Revision after iteration 1: 全文重写。判据归属改写为「工作项 4 的绑定判据是 B 半，A 半是本 plan 自己的切法」并承担责任；
  新增 `## 判据缺口登记` 三条与三行 `STATE.md` §3 登记（判据缺口 / 十工具选法 / B 半障碍含 hook 绕道处置项 (d)）；
  hook 绕道改为**如实写出并列为需人明确禁止/授权的选项**，同时写进 Non-Goals 禁止本 plan 使用；删掉伪造引文，改为核对过的 `conftest.py:5`/`:7` 与 README 原文，并注明冲突 1 已关闭；
  门禁计数一律改为「与开工时实测一致」；补开工前置检查（含「`…-1` 未完成不构成阻塞」）与末步 `Plan Status` + 「不要为绿 script check 去勾九框」；
  §7.4 熔断与 §7.5 包裹动作移出范围（只留 §7.5 声明位），带重开事件；十工具改为 `Decision` + 选法 + 排除项 + 登记给人；
  补 WBS P0.2 的前置列与冲突 4.2 的未决状态；零依赖判据改为 `sys.stdlib_module_names` 全量比对；
  `test_contract_surface.py` 由 `Fix` 改为**预先裁定「无需改动」**（实测该文件无穷尽性断言）；`pytest tests` 判据改为 grep `import file mismatch`；
  `from_is_submittable` 漂移登记为 `Fix`；所有 `git diff` 改区间形式。
- Independent draft review iteration 2: **needs revision**（同一独立子代理，重读磁盘版本并实跑）—— 原 10 条中 8 条 RESOLVED，2 条 PARTIALLY；新增 5 条 blocking。
  要害：**NEW-5** —— 把缺口 #1 记成 `STATE.md` §3 的 `[open]` 行、同一轮又要关闭，二者不能并存：
  `README.md:38` / `04-RUNBOOK.md:76` / `00-GOALS.md:63` 都规定 §3 有 `open` 行就**先处理它、立即停手**，
  而 plan 引作追加授权的那句人格指令原文结尾正是「**等人**」——引了前半句却做了相反的事。
  **NEW-1**：`sys.stdlib_module_names` 全集写法在合规模块上也退 1（`__main__` / `_distutils_hack` / `.pth` 注入的 `__editable___*_finder`），是假判据。
  **NEW-2**：末步「审计通过则置 `completed`」由 `EXECUTE` 执行时永远为假（`CLOSURE_AUDIT` 是同子流程更靠后的一步），且回退分支写成 `active` 会被 `activePlans()` 反复重选。
  **NEW-3**：`execute.md:10`/`:11` 两处直接指示与本 plan 相反的动作，plan 未逐字引用、未给优先级裁定。
  **NEW-4**：「这处矛盾已登记在前批 plan 的交接文档」是假的——交接文档四组冲突没有一条是它。
  另有 nit：`grep -c … → 0` 又一次退出码反转、无人记开工 sha、自指的汇总判据、hook 复现需注明是 scratchpad 复刻而非真门禁。
- Revision after iteration 2: 采纳 NEW-5 的选项 (i)——**`[open]` 由三行减到一行**，只保留「B 半红线障碍 + hook 绕道」（那是真正只有人能做的红线决定），
  并写明该行**不阻塞本 plan 关闭**（对照 `…-2341-2` 那行挡的是它自己的关闭）；缺口 #1、十工具选法、字段名漂移三件改为**就地裁定**，
  各自写出备选、否决理由、残余风险与翻案条件，并落到 owner doc / log / `Deferred But Adjudicated`。
  零依赖判据改为**导入前后求差**；末步改为「本阶段不改 `Plan Status`」并把三种归属（通过→`completed` / 需改代码→`active` / 阻塞于人→`deferred`）写给 `CLOSURE_AUDIT`；
  逐字引 `execute.md:10`/`:11` 并给出优先级裁定，工作项 4 改为置 `planned`（留 `todo` 会让下一轮重复起草 A 半）；
  删掉不实的「已登记」并改写为「尚未被登记，本 plan 不为它另开一行」；`grep -c` 改 `! grep -q`；补「记下开工 sha」；汇总判据注明最后勾；hook 复现注明是 scratchpad 复刻。
- Independent draft review iteration 3: **needs revision**（同一独立子代理，重读磁盘版本并实跑）—— NEW-1..NEW-5 全部 RESOLVED，
  且评审明确裁定两件关键事：**(a) 缺口 #1 的就地裁定「是 adjudication，不是 self-authorisation」**——mission 规则的主语是**工作项**，
  工作项 4 有绑定门禁（B 半），本 plan 不关闭任何工作项、判据是人写的、代偿控制真实存在；
  **(b) `planned` 合法且不会让引擎跳到工作项 5**——`draft-from-roadmap` 只在 `todo` 项为空时才返回 `nothing`，而工作项 1/3 排在 5 前面。
  新增 5 条 blocking：**NEW-6** 我给的「一行 `[open]` 会停掉整个 mission」是**假的**——实测 `tools/mission-driver/` 下无任何 flow/script 读 `STATE.md`，
  停机开关是 `gate-verify.mjs:71` 落的 `.mission-halt.json`；`README.md:38` 是角色 A 的 RESUME 清单、`04-RUNBOOK.md:76` 是监控面板信号，**都不是循环的闸**。
  结论（一行 `[open]`）对，理由错，必须换成「不淹没人的议程」。
  **NEW-7** `todo`/`planned` 在三处自相矛盾；**NEW-8** 末步块被重写残留成两份，第二份还带着已作废的句子；
  **NEW-9** 三处指向已删除的 `[open]` 行；**NEW-10** 一边用 roadmap 的严格读法否掉 `execute.md:11`、一边自己在 `EXECUTE` 内写 roadmap。nit：Phase 2 的 Targets 与其 Exit Criteria 打架、`1b.` 编号。
- Revision after iteration 3: NEW-6 的理由整段换成「§3 是给人的议程队列，引擎不读它；三件低代价可逆的事塞进去会淹没真正需要人裁的那一件」，
  三处引用同步改写并写明真正的停机开关是 `.mission-halt.json`；`todo`/`planned` 三处统一为 `planned`；删掉重复的末步块；
  三处失效引用改指就地裁定；roadmap 写入归属拆清——`todo → planned` 归**起草/评审步**（`planned` 的定义就是 `draft → active` 那一刻的事实，
  与「closure 审计通过后回写」管的 `done` 不是同一件事）、Phase 1 首项加一条幂等复核、`EXECUTE` 阶段一行 roadmap 都不改；
  Phase 2 的 Targets 去掉 `STATE.md`；前置检查改为 1–6 连续编号。
- Independent draft review iteration 4: **needs revision**（同一独立子代理）—— NEW-8/9/10 已解决，NEW-6/7 各剩残留，且**结构、范围与论证已被判定为 sound**：
  NEW-6 已被推翻的「`[open]` 会停掉整个 mission」在另外两处仍以「同上」的形式活着（行 207、269）；
  NEW-7 的 `todo` 在 Phase 3 的 Exit Criteria（行 338）残留——而那一条恰恰规定执行会话往 `docs/logs/` 里写什么，等于要求写下一句与全文矛盾的话；
  前置检查重编号后行 131 的「按下面第 4 点处置」成了悬空编号（停手处置现在是第 6 点）；
  行 309「本阶段（`EXECUTE`）一行 roadmap 都不改」被 Phase 1 第 5 点的兜底证伪，且 Phase 1 的 `Targets` 没列 roadmap 文件。
  评审同时确认：单行 `[open]` 与 Phase 3 实际动作**吻合**；工作项 4 在 Goals/Non-Goals/Phase/Deferred 各处除行 338 外**一致**；
  `plan-check.mjs` 解析无结构错误；`plan-review.md:22` / `closure-audit.md`（`roadmap` 出现 0 次）/ roadmap `:9`/`:34`/`:35` 引文逐条属实。
- Revision after iteration 4: 行 207、269 改为「同 Phase 1 缺口 #1 的裁定，理由见那里」，使那条理由**全文只有一处表述**；
  行 338 改为「工作项 4 停在 `planned`（不是 `done`）」；行 131 的编号改为第 6 点；
  行 309 收窄为「Phase 3 一行 roadmap 都不改；`EXECUTE` 内唯一可能的写入是 Phase 1 第 5 点的幂等兜底」，
  并把「本 plan 转 `active` 时已写」改为「**应由**转 `active` 的那一步写；没有任何引擎产物被指示去写它，所以 Phase 1 第 5 点是这条状态转换唯一有保证的落点」；
  Phase 1 `Targets` 补上 roadmap 文件与「仅停手分支会写 STATE」。
- Independent draft review iteration 5: **accept**（同一独立子代理，agent `a91304a379609c5a3`）—— 六处修复逐条 RESOLVED；
  `plan-check.mjs` 解析无结构错误；`工作项 4` 在每一处活文本里都是 `planned`（`grep` 确认全文再无「保持 `todo`」）；
  1–6 编号的所有交叉引用逐一对得上；单行 `[open]` 与 Phase 3 实际动作吻合。
  评审结论原文：「每一条判据都可达且非显然的那几条我自己跑过；每一处引文都与出处相符；唯一自判的那条判据在四个地方被披露且有真实的代偿控制。」
  另给一条**非阻塞建议**：把 `planned → done` 的写入落点这条已查实约束写给 B 半的 successor（`closure-audit.md` 里 `roadmap` 出现 0 次），
  否则它会重蹈同一个洞——工作项 1 此刻就卡在 `todo` 是活证据。
- Revision after iteration 5: 采纳该建议，写进 `### 工作项 4 的 B 半` 的 Deferred 条目；顺手清掉一处多余空行。
- **共识达成，转 `active`。**

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned
- [ ] verification has run：`python3 -m pytest tests/contracts -q`（exit 0）/ `python3 -m pytest tests/unit -q`（exit 0）/ `python3 tools/gates/check_expected_red.py`（exit 0）/ `ruff check agenerp tests/unit tests/contracts`（exit 0）
- [ ] scoped verification is not conflated with full verification —— 本仓无全量套件（无 build、无 typecheck），**L2 门禁仍全红**，且本 plan 的主判据 `pytest tests/contracts` **不在 `GATE_VERIFY` 的复跑范围内**（见 `## 判据缺口登记` 第 1 条）；上列即当前可跑的全部
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files

## Deferred But Adjudicated

### 工作项 4 的 B 半（`live_site` 接活站点 + `SiteSnapshotSource.read`）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: B 半有两个本 plan 无权跨越的前置：可起栈的 compose（`…-1` plan）、以及**只有人能做的** `tests/gates/conftest.py` 改动。
  本 plan 关闭时 roadmap 工作项 4 置 **`planned`**（不是 `done`），因此不存在「把没做完的活报成 done」的情形。
  **B 半的接续靠的是本条 successor 条目**（`draft-from-roadmap` 明写会「considering deferred items recorded in previous plans」），
  **不是**靠 STATE §3 那一行 `[open]`，也不是靠把工作项留在 `todo`。
- Successor Required: `yes` —— 工作项 4 的第二个 plan（roadmap 规则允许一个工作项 1–2 个 plan）
- **交给 successor 的一条已查实约束**：它要自带 `planned → done` 的写入落点。
  `closure-audit.md` 里 `roadmap` 出现 **0** 次、`plan-review.md:22` 只改 plan 自己的 `Plan Status`、`execute.md:11` 已被本 plan 按优先级次序否掉——
  **没有任何引擎产物被指示写这一步**。照本 plan Phase 1 第 5 点的办法自带一条幂等兜底即可。
  不这么做的后果此刻就在仓里看得见：roadmap 工作项 1 至今仍是 `todo`，而规范化器早已实现、转绿并在 `920ce0e` 划出名单。
- 重开事件：`…-1-zero-dep-boot-compose.md` 关闭**且**人对 Phase 3 登记的 (a)/(b)/(c)/(d) 作出选择之后。

### §7.4 权限拒绝熔断（N=5）与 §7.5 数据边界标记的**包裹动作**

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 二者是**控制循环的运行时部件**，`02-WBS.md` 的 P0 段没有任何一行对应它们（最近落点在 P1/P3.0），
  且 P0 阶段还没有控制循环去消费它们——现在实现只能得到「结构存在」的空断言，那正是本仓反复禁止的假判据。
  §7.5 的**声明位**（工具是否返回用户可写自由文本）已在本 plan 内，接缝留好。
- Successor Required: `yes` —— P1 建控制循环时
- 重开事件：P1 的解释 Agent 控制循环开工时；届时熔断计数器与包裹函数各自应有自己的判据。

### 十个只读工具的选法由 loop 拍板

- Classification: `watch-only residual`
- Why Not Blocking Closure: owner doc 只写「10 个只读工具」没给清单；本 plan 的选法、排除项与理由已写进 Phase 2 的 `Decision`、
  `module-boundaries.md` 的追加小节与 `docs/logs/`。**可逆成本低**：换清单只改 `agenerp/tools_readonly.py` 的声明与 `tests/contracts/` 的清单断言，契约格式不受影响。
- Successor Required: `no`
- 重开事件：人复核清单并提出不同的十个时；或 P1 建控制循环发现某个工具其实该换。

### `doc.links` 字段名的 owner-doc 漂移（`from_is_submittable` vs `is_submittable`）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 有明确 owner——`module-boundaries.md:82`（架构文档）写 `from_is_submittable`，实现照它取；
  `docs/analysis/2026-08-19-pre-build-validation.md:143` 是历史分析记录，**不改它**（改它等于销毁证据）。差异、取舍与两处行号已写进 Phase 3 追加的小节。
- Successor Required: `no`
- 重开事件：接活站点实现 `doc.links` 时，以 Frappe 的真实返回字段名为准复核；若两者都不对，回来改架构文档（那是人的动作）。

### 写契约（`rollback_and_report` / savepoint 回滚语义）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: `02-WBS.md` 把它划给 **P3.1**（工具契约层 v1），判据是 `tests/contracts/test_write_contract.py`。
  P0 的 v0 只包只读工具，roadmap 工作项 4 的标题就写着「先包 10 个只读工具」。
- Successor Required: `no`（属 P3 mission）
- 重开事件：P3 开工时。

### `02-WBS.md` 与 roadmap 的顺序/前置冲突（冲突 4.2）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 已由 `docs/backlog/needs-human-expected-red-handoff.md` 冲突 4.2 登记为 `open`，明写「需要人来对齐」。
  本 plan 只采信 P0.2 的**验收列**并如实记下其**前置列**，不替人消解。
- Successor Required: `no`（人动作）
- 重开事件：人对齐 WBS 与 roadmap 的顺序时。

## Closure

Status Note: <未关闭>

Closure Audit Evidence:

- Auditor / Agent: <独立关闭审计子代理，待填>
- Evidence: <待填：命令原文 + 退出码 + commit sha>

Follow-up:

- <待填；确认缺陷不得记在这里>
