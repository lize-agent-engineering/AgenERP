# 2026-08-21-1922-2 定制包导出（工作项 6 的前半：`export_customizations` 从活站点产出可 diff 的包）

> Plan Status: active
> Mission: p0-foundation
> Work Item: 6. 定制包往返删除验证（活站点端到端）—— **只做「导出」这半：`export_customizations`，不做 apply、不做孤儿列巡检**
> Last Reviewed: 2026-08-21
> Source: `docs/backlog/p0-foundation-roadmap.md` Work Item Status 第 6 项（起草时 `todo`）· 对照表第 6 行的两条断言 · `docs/architecture/module-boundaries.md` §11.1、§11.6
> Related: `2026-08-21-1922-1-site-snapshot-source-live.md`（**前置，必须先关闭**：本 plan 用它的站点客户端与站点投影）· `2026-08-21-1922-3-execute-plan-site-delete.md`（第 3 顺位，用本 plan 产出的包做删除往返）
> Audit: required

## Current Baseline

起草时（2026-08-21，HEAD `a9de1bb`）逐条读活代码与活门禁得出。

### 缺口

- `agenerp/pack.py:64` `export_customizations(doctype, into)` —— 函数体逐字
  `raise NotImplementedError(... 工作项 6 · 定制包往返验证)`。**今天仓里没有任何一行把站点定制写成文件的代码。**
- 读回那一侧**已经有了**：`agenerp/apply.py:60` `read_pack` → `agenerp/snapshot.py:152` `read_scope_dir`
  → `:168` `entries_from_payload`（载荷先过 `normalize`）。本 plan **不得另起第二套解析口径**。

### 门禁逐字要求（判据在这里，不在我的转述里）

两条绑定断言在 `tests/gates/test_customization_roundtrip_delete.py`：

- `test_added_field_exports_into_pack`（`:17`）：加字段 → `export_customizations(doctype="Item", into=pack_repo.path)`
  → `pack_repo.contains_field("Item", PROBE_FIELD)` 为真。
  `PackRepo.contains_field` 读的是 `<root>/doctypes/Item.json` 里 `custom_fields` 数组中
  `fieldname == "agenerp_gate_roundtrip"` 的条目（`tests/gates/conftest.py:241` 起）。
  → **文件路径、键名、身份键三者全被 fixture 钉死**，与 `PACK_SCOPE = "doctypes"`（`agenerp/apply.py:26`）一致。
- `test_export_produces_readable_diff_only`（`:26`）：先导出 → commit → 加字段 → 再导出 →
  `pack_repo.changed_lines()` 必须非空，且**每一行**要么含 `PROBE_FIELD`，要么 `line.strip() in "{}[],"`。

### 第二条断言对**产出格式**的硬约束（起草时逐字读 fixture 推出，不是猜的）

`changed_lines()`（`tests/gates/conftest.py:287` 起）取 `git diff HEAD --unified=0` 的内容行，去掉 diff 头，
`+`/`-` 前缀剥掉后 strip，丢空行。于是：

- `line.strip() in "{}[],"` 是**子串**判定，允许的整行只有 `{`、`}`、`[`、`]`、`,`、`{}`、`}[`、`[]`、`],` 这一类。
  **`},` 不在其中**（`}` 与 `,` 在 `"{}[],"` 里不相邻），`"fieldtype": "Data",` 更不在其中。
- 推论一：**不能用 `json.dumps(..., indent=2)` 那种把每个属性拆成一行的排版**——
  新增一个字段会带出 `"fieldtype": "Data",` 这类不含探针名的行，断言直接失败。
- 推论二：**不能让空数组写成 `"custom_fields": []`**——从空到非空会改到那一行，那行既不含探针名也不是括号行。
- 推论三：一条目一行 + 行尾逗号的排版下，唯一仍会失败的情形是**探针被插到数组末尾**
  （末元素要补逗号 → 那一行变了）。探针名 `agenerp_gate_roundtrip` 以 `agenerp_` 开头，
  按 `fieldname` 排序时几乎必然靠前，但**「几乎必然」不是判据**，所以 Phase 1 有一条 `Explore` 去实测。

**这不是实现细节，是判据对产物形状的约束**，所以写在 plan 里（计划指南规则 6 的例外：结构边界）。

### 与 Frappe 原生导出的关系

`module-boundaries.md` §11.1 末段两条实施约束：Frappe 的 `export_customizations`
**要求 `developer_mode`**（生产站点默认关闭），且**导出目标是 app 目录**而非任意目录。
我们的 `export_customizations(doctype, into)` 签名收的是任意目录，语义也不同。
→ Phase 1 有一条 `Decision` 记这个取舍。

### 判定面能看见什么

`missions/p0-foundation.json` 的 `commands.test` 是
`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`。
→ 本 plan 的行为判据落在 `tests/unit/`（用假站点客户端，不连真站点），`GATE_VERIFY` 复跑得到；
L2 两条门禁的转绿只能在 live 环境实测，**`GATE_VERIFY` 复跑不到**，代偿控制是变异验证 + 独立关闭审计。

### 名单不动的理由

与第 1 顺位同一条：判定器默认环境下 L2 全红（`AGENERP_LIVE` 未设即 `pytest.fail`），
划掉名单会让默认 `GATE_VERIFY` 立刻转红。**本 plan 不划名单**，工作项 6 因此停在 `planned`。
矛盾本身由第 1 顺位的 plan 实测并追加进 STATE §3，本 plan 不重复登记、也不替人选处置项。

## Goals

- 交付 `export_customizations(doctype, into)`：从活站点读该 DocType 的定制，写成**确定性、可 diff** 的包文件。
- 交付**往返一致**：`read_pack(导出目录)` 读回的条目，与 `capture` 从同一站点读到的**同一 DocType 子集逐条相等**。
  （这条是第 3 顺位能算出正确删除集的前提：两侧投影不同源，`plan_apply` 会把每个字段都算成 `changed`。）
- 交付**幂等**：站点没变时重复导出，`git diff` 为空。
- 让 `test_added_field_exports_into_pack` 与 `test_export_produces_readable_diff_only` 在 live 环境实测转绿。

## Non-Goals

- 不实现 `execute_plan`（第 3 顺位）、不实现 `schema_drift`（工作项 6 的第二个 plan）。
- **不导出 Property Setter / Custom DocPerm / Client Script**：`PackRepo` 的载荷形状只认 `custom_fields`
  （`tests/gates/conftest.py:249`），`entries_from_payload` 亦然。扩包体是 P2 的事，本 plan 登记为 deferred。
- 不用 Frappe 的 `export_customizations` / `sync_customizations`（理由见 Phase 1 的 `Decision`）。
- 不改 `tests/gates/**`（红线 1）、不改 `.github/workflows/**`、`missions/**`、`docs/masterplan/DECISIONS.md`；
  `STATE.md` 仅在停手分支追加证据行。
- **不划掉 `tools/gates/expected-red.txt` 任何一行**；**不把工作项 6 置为 `done`**。
- 不改 `normalize` / `diff` / `read_scope_dir` 的既有语义（可以**复用**，不得改口径）。

## Task Route

- Type: `app-layer design change`（定制包是产品的一等产物，P2 的「一句话改首页 → revert 撤得回」直接依赖它的形状）
- Owner Docs: 读 `docs/architecture/module-boundaries.md` §11.1（三个必须自建的部件）、§11.6（包布局裁定与残余风险）·
  待更新：§11.6 的「残余风险」段（`export_customizations` 落地后，布局是否被推翻要给出实测结论）
- Skill Selection Basis: 技能表无对应工作方法技能；产物形状被 fixture 与 `read_scope_dir` 双向钉死，属受限选择。
  各阶段 `Skill: none`；草案评审 `docs/skills/plan-audit-prompt.md`，关闭审计 `docs/skills/closure-audit-prompt.md`。

## Infrastructure And Config Prereqs

- 依赖第 1 顺位交付的站点客户端与环境变量（`AGENERP_SITE` / `AGENERP_SITE_URL` / 凭据）。本 plan **不新增环境变量**。
- 无新增第三方依赖（只用标准库）。
- live 实跑必须带 `AGENERP_HTTP_PORT=18080`（本机 8080 被另一套栈占用，`compose_stack` 有端口预检会直接 fail）。
- 回滚策略：`export_customizations` 一处实现 + 单测 + 文档追加，`git revert` 即回到今天。
  **站点侧无副作用**：导出只读站点、只写本地目录。

## 结构边界（本 plan 定稿的接口契约）

| 落点 | 契约 | 谁实现 |
|---|---|---|
| `agenerp/pack.py` · `export_customizations(doctype, into)` | 签名不变（门禁逐字 `from agenerp.pack import export_customizations`，关键字调用 `doctype=` / `into=`）。行为：从站点读该 DocType 的定制 → 写 `<into>/doctypes/<DocType>.json`。**只重写该 DocType 的文件**，同目录其他文件不动 | 本 plan |
| 序列化器（落点由 Phase 2 定，`pack` 或 `apply` 二选一，不得两处各写一份） | 「条目 → 包文件」的**唯一**写入口径，与 `read_scope_dir` / `entries_from_payload` 的读口径互为逆 | 本 plan |
| **导出的站点读取路径** | **复用 `capture(PACK_SCOPE, SiteSnapshotSource(site))` 再按 DocType 过滤，不新开第二条站点查询**。这样不变量 1 **由构造保证**（同一来源、同一投影、同一 `normalize`），不变量 5（关分页）直接继承第 1 顺位的实现与判据，单测退化成回归性质。自己再发一次 `/api/resource/Custom Field` 查询就会出现第二套口径——那正是 `agenerp/snapshot.py:155` 起的 docstring 反复警告的东西。若 Phase 2 发现非新开不可（例如需要 `capture` 不返回的原始键），**升级为一条 `Decision`** 并说明不变量 1 为何仍成立 | 本 plan |
| 站点行 → `attributes` 的投影 | **沿用第 1 顺位的单一落点**。本 plan 若为可读性收窄它（例如再剥空值），改的必须是那一个落点，且两侧同时生效 | 第 1 顺位交付，本 plan 可收窄 |
| `read_pack` / `read_scope_dir` / `entries_from_payload` | **不改**。往返一致靠导出去贴合读口径，不靠改读口径 | 已在仓里 |

**往返不变量**（Phase 2 的判据，缺一条就不算完成）：

1. **双向相等**：`read_pack(into)` 里属于该 DocType 的条目，与 `capture(scope="doctypes")` 里属于该 DocType 的条目
   **集合相等且属性逐键相等**（不是「⊇」）。少一条 → 第 3 顺位会把它算成 `deletes`（**误删**）；
   属性投影不同源 → 全部算成 `updates`（第 3 顺位显式拒绝 `updates`，**承重条款那条门禁会红在
   `NotImplementedError` 上，与「还没实现」逐字难以区分**）。这条是三个 plan 里最贵的一条不变量。
2. **零定制也必须落盘**：该 DocType 在站点上一条定制都没有时，**照样写出 `{"doctype": …, "custom_fields": []}` 文件**。
   理由是判据层面的硬需求：门禁先 `export` 再 `pack_repo.commit("baseline")`，而
   `changed_lines()` 走的是 `git diff HEAD`（`tests/gates/conftest.py:287` 起）——
   **`git diff` 看不见未跟踪文件**。基线时不落盘，加字段后新文件是 untracked，
   `changed` 为空 → `assert changed, "改了定制却没产生任何 diff"` 直接红。
3. **幂等**：站点未变时重复导出 → 文件逐字节相同（写入前排序、无时间戳、无站点名一类溯源字段）。
4. 导出的文件是**严格 JSON**（`PackRepo._load` 用 `json.loads` 读它，不是宽松解析）。
5. **scope 完整性**：导出写进包的条目，来自站点上该 DocType 的**全部** Custom Field
   （沿用第 1 顺位定的「显式关分页」口径）。分页截断在包里长得跟「站点本来就只有这些」一模一样，
   而它的后果是第 3 顺位误删。

## Execution Plan

### Phase 1 — 实测包的真实形状（`Explore`）与两个 `Decision`

Status: planned
Targets: `docs/backlog/p0-foundation-roadmap.md`、`docs/architecture/module-boundaries.md` §11.6、本 plan（无 `agenerp/` 代码产物）
Skill: `none`
Prereqs: 第 1 顺位 plan 已关闭（站点客户端可用）

- Item Types: `Decision`-heavy（5 项里 4 项为 `Decision`/`Explore`，另 1 项为 `Add`）

- [ ] `Add` **首项先做**：复核 roadmap 工作项 6 已为 `planned`。
      roadmap 的 `Status values` 定义 `planned` = 「已有执行 plan 且**通过草案评审**」——该条件在
      本 plan 第 3 轮评审 `accept` 时即满足，故**起草会话已就地置好**（同一提交里还加了一段说明本批三个 plan 的注记）。
      本项因此是**复核 + 兜底**：若因任何原因被回滚回 `todo`，在这里重置。
      不拖到 Phase 3 的理由：roadmap 写「引擎取第一个 `todo`」，item 6 曾是唯一的 `todo`，
      留着它引擎可能再起一份重复 plan。

- [ ] `Explore` 冷起栈，实测两件事，命令原文与输出一并抄进 plan
      （**必须先于排版 Decision 结束**，指南规则 9）：
      ① 新建站点上 `Item` 到底有几条 Custom Field、fieldname 分别是什么，
      探针 `agenerp_gate_roundtrip` 按 `fieldname` 排序会落在数组的什么位置；
      ② **全站** Custom Field 清点（不只 Item）——这份清单是第 3 顺位判断「作用域收窄有没有生效」的对照基线，
      在这里顺手拿到，比到第 3 顺位再冷起一次栈便宜。
- [ ] `Decision` **包文件排版**。默认取「一条目一行 + 行尾逗号 + 数组括号独占行」。
      备选：① `json.dumps(indent=2)` 全展开——**已被门禁第二条断言排除**（推论一）；
      ② 前导逗号排版——把失败情形从「末尾插入」换成「首位插入」，按 Explore 结果哪个更安全就取哪个；
      ③ 一行装下整个文件——diff 完全不可读，违背 §11.2 的初衷；
      ④ **逗号独占一行**（`{…e1…}` / `,` / `{…e2…}`）——仍是严格 JSON，
      而插入发生在任何位置都只新增「条目行 + 逗号行」两行，且 `,` 本身是断言允许的整行，
      **四种插入位置全过**，一次性消掉推论三那个残余风险。评审建议取它；
      若 Explore 显示排版 ① 的末尾插入风险不存在，也要写明为何仍不取 ④。
      残余风险与 Explore 实测结论一并写进 §11.6。
- [ ] `Decision` **不使用 Frappe 原生 `export_customizations`**。理由（§11.1 末段实测约束）：
      它要求 `developer_mode`、导出目标是 app 目录、且产物形状由 Frappe 定；
      我们要的产物形状已被 fixture 与 `read_scope_dir` 双向钉死。
      备选：走 `bench --site … export-customizations` 再转格式——多一层容器 exec 依赖且形状还得转，未取。
      残余风险：与 Frappe 官方包格式不互通（迁移到别的工具链需转换器），登记为 deferred。
- [ ] `Decision` **属性投影是否收窄**（剥空值让行变短）。判据是往返不变量 1：**收窄必须两侧同源**。
      不收窄的代价是单行很长（可读性差）；收窄的代价是包里看不出「显式设成 0/false」与「缺省」的区别。
      取哪个都要把理由与残余风险写进 §11.6。

Exit Criteria:

- [ ] roadmap 工作项 6 已由 `todo` 置 `planned`
- [ ] Explore 的命令原文、输出、结论落进 plan（含全站 Custom Field 清点）
- [ ] 三条 `Decision` 各有选择、备选与残余风险，且写进 `module-boundaries.md` §11.6
- [ ] **本 plan 引用的每个行号在开工时逐条复核过**（本仓已有行号漂移被修正的先例，`0f7cf14`）；
      引用一律「符号名 + 行号」，符号名对不上就以符号名为准
- [ ] `docs/logs/2026/08-21.md` 追加条目

### Phase 2 — `export_customizations` 落地 + 往返判据

Status: planned
Targets: `agenerp/pack.py`、`tests/unit/test_pack_export.py`（新文件）、`agenerp/snapshot.py`（**仅当 Phase 1 的 `Decision` 4 取「收窄投影」时**——那个落点在 snapshot 里，改它会波及第 1 顺位刚转绿的快照门禁）
Skill: `none`
Prereqs: Phase 1

- Item Types: `Add | Proof`

- [ ] `Add` 实现 `export_customizations`：站点读 → 排序 → 按 Phase 1 定的排版写 `<into>/doctypes/<DocType>.json`；
      目录不存在则创建；**只动该 DocType 的文件**。
- [ ] `Add` 站点不可达 / 认证失败时**抛**（沿用第 1 顺位的 `SiteError`），
      **绝不写出一个空包**——空包会让第 3 顺位的 apply 把**该 DocType 的全部定制**算成待删除
      （第 3 顺位已裁定按「包目录里存在文件的 DocType」收窄，所以炸的是这个 DocType 而不是全站，危险性不减）。
      **与上一条的分界必须写死**：空数组文件**只在站点成功答出「零条目」时**才写；**读取失败必须抛且不留下任何文件**。
      这两条紧挨着，实现时极易合并成一个分支，而合并的后果正是这里说的那个事故。
- [ ] `Add` **零定制也落盘**（往返不变量 2）：该 DocType 没有任何定制时照样写出空数组的文件。
- [ ] `Proof` 单测（假站点客户端，不连真站点）：往返不变量 **1/2/3/4/5 各一条**；
      同目录另一个 DocType 的文件在导出后**逐字节未变**一条；站点抛错时**不产生任何文件**一条。
- [ ] `Proof` **排版回归**：用一条单测直接复刻门禁那条逐行断言的判定
      （对同一份包做「加一个字段再导出」，断言每一行要么含探针名要么是括号行）。
      **不 import `tests/gates/` 的任何东西**（红线 1 + 判据独立性），断言自带。

Exit Criteria:

- [ ] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0，
      且 `tests/unit/test_pack_export.py` 存在、用例数 **≥ 8**（不变量 5 条 + 邻居未变 + 抛错不产文件 + 排版回归），
      记录用例数增量（只写「exit 0」是一条零新增用例也能满足的空断言）
- [ ] `ruff check agenerp tests/unit tests/contracts` → exit 0
- [ ] `agenerp/pack.py` 内不再有 `export_customizations` 的 `NotImplementedError`
- [ ] `docs/logs/2026/08-21.md` 追加条目

### Phase 3 — 活站点实跑两条门禁 + 变异验证 + 文档

Status: planned
Targets: `docs/architecture/module-boundaries.md` §11.6、`docs/backlog/p0-foundation-roadmap.md`、`docs/logs/`
Skill: `none`
Prereqs: Phase 2

- Item Types: `Proof`

- [ ] `Proof` live 实跑，命令原文：
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q`
      → 期望 `test_added_field_exports_into_pack` 与 `test_export_produces_readable_diff_only` **两条绿**，
      另两条（删除、孤儿列）**都仍红在 `execute_plan`**——`test_no_orphan_column_left_behind` 先走
      `apply_pack` → `agenerp/apply.py:105` 就抛了，**本轮根本走不到 `schema_drift`**。**退出码与失败原文照抄**。
- [ ] `Proof` **变异验证 ×2**（都要指名红因，含糊的红不算）：
      ① 在包文件**顶层**加一个独占一行的 `"exported_at": "<ISO 时间戳>"`（**不能塞进探针那一行**，
      否则那行含探针名、断言照样过，变异就空转了）→ `test_export_produces_readable_diff_only` 必须转红；
      ② 导出时故意漏写 `fieldname` 键 → `test_added_field_exports_into_pack` 必须转红
      （这条门禁的牙齿否则一次都没验过）。两次验证后各自还原，并复核工作区相对变异前基线无残留。
- [ ] `Proof` **快照门禁回归**（仅当 Phase 1 的 `Decision` 4 取「收窄投影」时必做；取「不收窄」则写明
      「未动 `agenerp/snapshot.py`，无需回归」并说明）：同一 live 环境复跑
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q`
      → 期望 exit 0，抄退出码。理由：那条门禁的判定面正是这个共享投影，而它刚由第 1 顺位在 live 环境转绿、名单未划——
      **默认环境的判定器恒为 exit 0（该行仍在名单内），这条回归在别处一格都看不见。**
- [ ] `Proof` 收尾复跑默认环境判定器：`python3 tools/gates/check_expected_red.py` → exit 0（名单一行未动）。
- [ ] `Add` §11.6「残余风险」段给出实测结论：包布局是否被 `export_customizations` 推翻（起草时它是 open 的 watch-only residual）。
- [ ] `Add` 在对照表第 6 行更正归属：**两条导出断言**由本 plan 承接；
      `test_no_orphan_column_left_behind` 归工作项 6 的第二个 plan；
      `test_field_addition_shows_up_as_structured_change` 实际由**工作项 4** 的 plan（第 1 顺位）承接——
      对照表现在把它列在第 6 行，这一行的归属要一并更正。
      （工作项 6 的 `todo → planned` 不在这里做，见 Phase 1 首项。）

Exit Criteria:

- [ ] Phase 3 **每一次实跑**的命令原文 + 退出码落进 plan 与日志
- [ ] 两条变异验证都有牙齿且红因指名，还原后工作区**相对变异前基线**无残留
- [ ] 快照门禁回归（或「未收窄投影故无需回归」的说明）已落盘
- [ ] `tools/gates/expected-red.txt` 一行未动；roadmap 第 6 项为 `planned`
- [ ] `module-boundaries.md` §11.6 的残余风险段有实测结论

## Draft Review Record

- 独立草案评审第 1 轮：**needs revision**（独立子代理，全新会话，2026-08-21）。主要发现，逐条已改：
  1. **[阻断]** 往返不变量 1 写成「⊇」太弱——必须是与 `capture` 的**双向集合相等 + 属性逐键相等**，
     否则第 3 顺位会把缺的条目算成 `deletes`（误删）或把全部算成 `updates`（承重条款红在 `NotImplementedError` 上）。
     → 不变量表重写，并增第 5 条 scope 完整性。
  2. **[阻断]** **零定制也必须落盘**：`git diff HEAD` 看不见未跟踪文件，基线导出不写文件的话
     `test_export_produces_readable_diff_only` 的 `assert changed` 直接红。→ 增不变量 2 + Phase 2 一条 `Add` 与判据。
  3. **[重要]** 排版备选漏了「逗号独占一行」——它四种插入位置全过且仍是严格 JSON，一次性消掉「探针排末尾就红」的残余风险。
     → Phase 1 的 `Decision` 增第 ④ 案并注明评审建议取它。
  4. **[次要]** 变异验证可能空转（时间戳若塞进探针那一行，断言照样过）→ 改为顶层独占一行，并补
     `test_added_field_exports_into_pack` 的第二条变异。
  5. **[次要]** `pytest tests/unit -q → exit 0` 是零新增用例也能满足的空断言 → 加用例数下限。
  6. **[次要]** 「另两条仍红在 `execute_plan` / `schema_drift`」说错了——两条都红在 `execute_plan`，本轮走不到 `schema_drift`。→ 更正。
  7. **[次要]** roadmap 对照表第 6 行的归属口径说岔（第 6 行的「其余 3 条」不含删除那条；`test_field_addition_...` 实由工作项 4 承接）→ 更正。
  8. **[次要]** 工作项 6 的 `todo → planned` 放在 Phase 3 太晚（引擎取第一个 `todo`，期间可能重复起 plan）→ 挪到 Phase 1 首项。
  评审独立验算并**确认**了本 plan 对门禁逐行断言的三条推论（`}` 与 `,` 在 `"{}[],"` 里不相邻，故 `},` 不合法等），
  并确认无红线风险、Anti-Slacking 合规、Deferred 三条各有重开事件。
- **第 1 轮有两条我当时未处置，如实补记**（评审记录不该比实际处置乐观）：
  ① **[重要] 共享投影的落点**：Phase 1 的 `Decision` 4 允许收窄「站点行 → attributes」投影，而那个落点在 `agenerp/snapshot.py`，
     动它会波及第 1 顺位刚在 live 转绿的快照门禁，而默认环境的判定器看不见这条回归。
     → 第 2 轮已改：Phase 2 `Targets` 补 `agenerp/snapshot.py`（条件式），Phase 3 增快照门禁回归 `Proof`。
  ② **[次要] 六处行号**：我当时改成「Phase 1 开工复核」，等于把已知事实推后。→ 第 2 轮已当场替换
     （`test_added_field_exports_into_pack:17`、`test_export_produces_readable_diff_only:26`、`conftest.py:287`、
     `conftest.py:249`、`apply.py:26`、`apply.py:60`），Phase 1 那条复核 Exit Criteria 保留作网。
- 独立草案评审第 3 轮（确认轮）：**accept**（同一独立评审者，逐条复核六项修正与活代码行号，结论：可将 `Plan Status` 由 `draft` 改为 `active`）。
- 独立草案评审第 2 轮：**needs revision → 已改**（同一独立评审者，带上下文复评）。它确认第 1 轮两条阻断与那条重要项
  **实质解决**，并逐字核对了跨 plan 的两处引用（关分页、第 3 顺位拒绝 `updates`）成立、三个 plan 在作用域收窄上已闭环。
  剩余五条，逐条已改：
  1. **[重要]** 结构边界表**没定「导出从哪条路径读站点」**，而不变量 1/5 的成本完全取决于它
     → 增一行落点，写死「复用 `capture` / `SiteSnapshotSource.read`，不新开第二条站点查询」，
     非新开不可时升级为 `Decision`。
  2. **[重要]** 上面那条 ① 的静默丢弃 → 已补记并落三处改动。
  3. **[次要]** 六处行号（其中两条绑定断言的引用互换错位）→ 全部当场替换。
  4. **[次要]** Phase 1 `Targets`/`Item Types` 与新增首项不符 → 更正。
  5. **[次要]** Phase 3 Exit Criteria 说「三条命令」而实际 ≥ 4 次实跑、`git status` 干净不可达 → 改为「每一次实跑」与「相对变异前基线」。
  6. **[次要]** 「空包会让 apply 把站点上**所有定制**算成待删除」与第 3 顺位的收窄裁定不符 → 改为「该 DocType 的全部定制」，
     并在两条相邻 `Add` 之间加了分界句（空数组只在站点答出零条目时写；读取失败必须抛且不留文件）。
  评审的结论原话：改完即可 accept，不需要再论证任何东西。

## Closure Gates

- [ ] in-scope behavior is complete（导出真能产出可 diff 的包，不是只有签名）
- [ ] relevant docs are aligned（§11.6、roadmap 第 6 行、日志）
- [ ] verification has run：`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`
      + `ruff check agenerp tests/unit tests/contracts` + Phase 3 的 live 命令，逐条抄退出码
- [ ] **verification scope limited 明写**：live 实跑只在本机做过，不得报成「CI 上也验证过」
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] **红线自查**：`git diff --name-only` 不含 `tests/gates/`、`.github/workflows/`、`missions/`、
      `docs/masterplan/DECISIONS.md`；`tools/gates/expected-red.txt` 未变

## Deferred But Adjudicated

### 包体只覆盖 Custom Field，不含 Property Setter / DocPerm / Client Script

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: `PackRepo` 与 `entries_from_payload` 两侧的载荷形状都只认 `custom_fields`
  （`tests/gates/conftest.py:249`、`agenerp/snapshot.py:168`），P0 的判据一条都够不着其余种类。
  扩包体要先扩快照条目的身份模型（今天是 `(doctype, fieldname)` 二元组），那是 P2 的事。
- Successor Required: `yes`（P2 定制包 GitOps）
- 重开事件：P2 需要「改首页 → revert 撤得回」覆盖 Property Setter 时。

### 与 Frappe 官方定制包格式不互通

- Classification: `watch-only residual`
- Why Not Blocking Closure: 本项目明确**不用** `sync_customizations`（§11.1 实测：纯 upsert，删不掉），
  互通性因此不是 P0 的判据；真需要时写一个转换器即可，代价局部。
- Successor Required: `no`
- 重开事件：有人要把 AgenERP 的包喂给 Frappe 原生工具链时。

### 孤儿列巡检（`schema_drift`）与 `test_no_orphan_column_left_behind`

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 它查**物理表残留列**，REST 面答不出（`docker-compose.yml` 未对宿主发布 db 端口），
  要么容器 exec、要么另开通道——那是一条独立的传输决策，与「导出」不是同一个结果面。
- Successor Required: `yes` —— 工作项 6 的第二个 plan（roadmap 允许一个工作项 1–2 个 plan）
- 重开事件：第 3 顺位 plan 关闭之后（删除路径先落地，才谈得上删完有没有留下孤儿列）。

## Closure

Status Note: <closure 时填>

Closure Audit Evidence:

- Auditor / Agent: <independent subagent>
- Evidence: <task id / 命令原文 + 退出码 + commit sha>

Follow-up:

- <closure 时填>
