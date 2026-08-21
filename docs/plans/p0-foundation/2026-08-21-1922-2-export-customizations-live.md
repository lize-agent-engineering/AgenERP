# 2026-08-21-1922-2 定制包导出（工作项 6 的前半：`export_customizations` 从活站点产出可 diff 的包）

> Plan Status: completed
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

Status: completed
Targets: `docs/backlog/p0-foundation-roadmap.md`、`docs/architecture/module-boundaries.md` §11.6、本 plan（无 `agenerp/` 代码产物）
Skill: `none`
Prereqs: 第 1 顺位 plan 已关闭（站点客户端可用）

- Item Types: `Decision`-heavy（5 项里 4 项为 `Decision`/`Explore`，另 1 项为 `Add`）

- [x] `Add` **首项先做**：复核 roadmap 工作项 6 已为 `planned`。
      roadmap 的 `Status values` 定义 `planned` = 「已有执行 plan 且**通过草案评审**」——该条件在
      本 plan 第 3 轮评审 `accept` 时即满足，故**起草会话已就地置好**（同一提交里还加了一段说明本批三个 plan 的注记）。
      本项因此是**复核 + 兜底**：若因任何原因被回滚回 `todo`，在这里重置。
      不拖到 Phase 3 的理由：roadmap 写「引擎取第一个 `todo`」，item 6 曾是唯一的 `todo`，
      留着它引擎可能再起一份重复 plan。

- [x] `Explore` 冷起栈，实测两件事，命令原文与输出一并抄进 plan
      （**必须先于排版 Decision 结束**，指南规则 9）：
      ① 新建站点上 `Item` 到底有几条 Custom Field、fieldname 分别是什么，
      探针 `agenerp_gate_roundtrip` 按 `fieldname` 排序会落在数组的什么位置；
      ② **全站** Custom Field 清点（不只 Item）——这份清单是第 3 顺位判断「作用域收窄有没有生效」的对照基线，
      在这里顺手拿到，比到第 3 顺位再冷起一次栈便宜。
- [x] `Decision` **包文件排版**。默认取「一条目一行 + 行尾逗号 + 数组括号独占行」。
      备选：① `json.dumps(indent=2)` 全展开——**已被门禁第二条断言排除**（推论一）；
      ② 前导逗号排版——把失败情形从「末尾插入」换成「首位插入」，按 Explore 结果哪个更安全就取哪个；
      ③ 一行装下整个文件——diff 完全不可读，违背 §11.2 的初衷；
      ④ **逗号独占一行**（`{…e1…}` / `,` / `{…e2…}`）——仍是严格 JSON，
      而插入发生在任何位置都只新增「条目行 + 逗号行」两行，且 `,` 本身是断言允许的整行，
      **四种插入位置全过**，一次性消掉推论三那个残余风险。评审建议取它；
      若 Explore 显示排版 ① 的末尾插入风险不存在，也要写明为何仍不取 ④。
      残余风险与 Explore 实测结论一并写进 §11.6。
- [x] `Decision` **不使用 Frappe 原生 `export_customizations`**。理由（§11.1 末段实测约束）：
      它要求 `developer_mode`、导出目标是 app 目录、且产物形状由 Frappe 定；
      我们要的产物形状已被 fixture 与 `read_scope_dir` 双向钉死。
      备选：走 `bench --site … export-customizations` 再转格式——多一层容器 exec 依赖且形状还得转，未取。
      残余风险：与 Frappe 官方包格式不互通（迁移到别的工具链需转换器），登记为 deferred。
- [x] `Decision` **属性投影是否收窄**（剥空值让行变短）。判据是往返不变量 1：**收窄必须两侧同源**。
      不收窄的代价是单行很长（可读性差）；收窄的代价是包里看不出「显式设成 0/false」与「缺省」的区别。
      取哪个都要把理由与残余风险写进 §11.6。

Exit Criteria:

- [x] roadmap 工作项 6 已由 `todo` 置 `planned`
- [x] Explore 的命令原文、输出、结论落进 plan（含全站 Custom Field 清点）
- [x] 三条 `Decision` 各有选择、备选与残余风险，且写进 `module-boundaries.md` §11.6
- [x] **本 plan 引用的每个行号在开工时逐条复核过**（本仓已有行号漂移被修正的先例，`0f7cf14`）；
      引用一律「符号名 + 行号」，符号名对不上就以符号名为准
- [x] `docs/logs/2026/08-21.md` 追加条目

### Phase 2 — `export_customizations` 落地 + 往返判据

Status: completed
Targets: `agenerp/pack.py`、`tests/unit/test_pack_export.py`（新文件）、`agenerp/snapshot.py`（**仅当 Phase 1 的 `Decision` 4 取「收窄投影」时**——那个落点在 snapshot 里，改它会波及第 1 顺位刚转绿的快照门禁）
Skill: `none`
Prereqs: Phase 1

- Item Types: `Add | Proof`

- [x] `Add` 实现 `export_customizations`：站点读 → 排序 → 按 Phase 1 定的排版写 `<into>/doctypes/<DocType>.json`；
      目录不存在则创建；**只动该 DocType 的文件**。
- [x] `Add` 站点不可达 / 认证失败时**抛**（沿用第 1 顺位的 `SiteError`），
      **绝不写出一个空包**——空包会让第 3 顺位的 apply 把**该 DocType 的全部定制**算成待删除
      （第 3 顺位已裁定按「包目录里存在文件的 DocType」收窄，所以炸的是这个 DocType 而不是全站，危险性不减）。
      **与上一条的分界必须写死**：空数组文件**只在站点成功答出「零条目」时**才写；**读取失败必须抛且不留下任何文件**。
      这两条紧挨着，实现时极易合并成一个分支，而合并的后果正是这里说的那个事故。
- [x] `Add` **零定制也落盘**（往返不变量 2）：该 DocType 没有任何定制时照样写出空数组的文件。
- [x] `Proof` 单测（假站点客户端，不连真站点）：往返不变量 **1/2/3/4/5 各一条**；
      同目录另一个 DocType 的文件在导出后**逐字节未变**一条；站点抛错时**不产生任何文件**一条。
- [x] `Proof` **排版回归**：用一条单测直接复刻门禁那条逐行断言的判定
      （对同一份包做「加一个字段再导出」，断言每一行要么含探针名要么是括号行）。
      **不 import `tests/gates/` 的任何东西**（红线 1 + 判据独立性），断言自带。

Exit Criteria:

- [x] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0，
      且 `tests/unit/test_pack_export.py` 存在、用例数 **≥ 8**（不变量 5 条 + 邻居未变 + 抛错不产文件 + 排版回归），
      记录用例数增量（只写「exit 0」是一条零新增用例也能满足的空断言）
- [x] `ruff check agenerp tests/unit tests/contracts` → exit 0
- [x] `agenerp/pack.py` 内不再有 `export_customizations` 的 `NotImplementedError`
- [x] `docs/logs/2026/08-21.md` 追加条目

### Phase 3 — 活站点实跑两条门禁 + 变异验证 + 文档

Status: completed
Targets: `docs/architecture/module-boundaries.md` §11.6、`docs/backlog/p0-foundation-roadmap.md`、`docs/logs/`
Skill: `none`
Prereqs: Phase 2

- Item Types: `Proof`

- [x] `Proof` live 实跑，命令原文：
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q`
      → 期望 `test_added_field_exports_into_pack` 与 `test_export_produces_readable_diff_only` **两条绿**，
      另两条（删除、孤儿列）**都仍红在 `execute_plan`**——`test_no_orphan_column_left_behind` 先走
      `apply_pack` → `agenerp/apply.py:105` 就抛了，**本轮根本走不到 `schema_drift`**。**退出码与失败原文照抄**。
- [x] `Proof` **变异验证 ×2**（都要指名红因，含糊的红不算）：
      ① 在包文件**顶层**加一个独占一行的 `"exported_at": "<ISO 时间戳>"`（**不能塞进探针那一行**，
      否则那行含探针名、断言照样过，变异就空转了）→ `test_export_produces_readable_diff_only` 必须转红；
      ② 导出时故意漏写 `fieldname` 键 → `test_added_field_exports_into_pack` 必须转红
      （这条门禁的牙齿否则一次都没验过）。两次验证后各自还原，并复核工作区相对变异前基线无残留。
- [x] `Proof` **快照门禁回归**（仅当 Phase 1 的 `Decision` 4 取「收窄投影」时必做；取「不收窄」则写明
      「未动 `agenerp/snapshot.py`，无需回归」并说明）：同一 live 环境复跑
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q`
      → 期望 exit 0，抄退出码。理由：那条门禁的判定面正是这个共享投影，而它刚由第 1 顺位在 live 环境转绿、名单未划——
      **默认环境的判定器恒为 exit 0（该行仍在名单内），这条回归在别处一格都看不见。**
- [x] `Proof` 收尾复跑默认环境判定器：`python3 tools/gates/check_expected_red.py` → exit 0（名单一行未动）。
- [x] `Add` §11.6「残余风险」段给出实测结论：包布局是否被 `export_customizations` 推翻（起草时它是 open 的 watch-only residual）。
- [x] `Add` 在对照表第 6 行更正归属：**两条导出断言**由本 plan 承接；
      `test_no_orphan_column_left_behind` 归工作项 6 的第二个 plan；
      `test_field_addition_shows_up_as_structured_change` 实际由**工作项 4** 的 plan（第 1 顺位）承接——
      对照表现在把它列在第 6 行，这一行的归属要一并更正。
      （工作项 6 的 `todo → planned` 不在这里做，见 Phase 1 首项。）

Exit Criteria:

- [x] Phase 3 **每一次实跑**的命令原文 + 退出码落进 plan 与日志
- [x] 两条变异验证都有牙齿且红因指名，还原后工作区**相对变异前基线**无残留
- [x] 快照门禁回归（或「未收窄投影故无需回归」的说明）已落盘
- [x] `tools/gates/expected-red.txt` 一行未动；roadmap 第 6 项为 `planned`
- [x] `module-boundaries.md` §11.6 的残余风险段有实测结论

## 实测回填

### Phase 1 · `Explore` —— 活站点上的定制现状（2026-08-21，栈端口 18080）

**起栈命令原文与退出码**：

    AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait
    → exit 0（六个 healthy 服务 + 两个一次性容器 Exited 0）

**清点命令原文**（只读，不建任何探针字段；走的就是本 plan 要复用的那条代码路径 `agenerp.site.SiteClient.list_resource`）：

    AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 - <<'EOF'
    from agenerp.site import client_from_env
    c = client_from_env("frontend")
    rows = c.list_resource("Custom Field")
    print(len(rows), c.get("/api/method/frappe.client.get_count", {"doctype": "Custom Field"}))
    ...
    EOF

**输出原文（全站 Custom Field 清点 —— 第 3 顺位「作用域收窄有没有生效」的对照基线）**：

    TOTAL Custom Field rows: 10
    count endpoint: {'message': 10}
      'Address'                    'is_your_company_address'
      'Address'                    'tax_category'
      'Communication'              'company'
      'Contact'                    'is_billing_contact'
      'Customer'                   'crm_deal'
      'Email Account'              'company'
      'Print Settings'             'compact_item_print'
      'Print Settings'             'print_taxes_with_zero_amount'
      'Print Settings'             'print_uom_after_quantity'
      'Quotation'                  'crm_deal'
    Item custom fields sorted: []
    probe index if added: 0 of 1
    merged: ['agenerp_gate_roundtrip']
    RAW ROW KEYS (n=58): ['allow_in_quick_entry', 'allow_on_submit', 'bold', 'collapsible',
      'collapsible_depends_on', 'columns', 'creation', 'default', 'depends_on', 'description',
      'docstatus', 'dt', 'fetch_from', 'fetch_if_empty', 'fieldname', 'fieldtype', 'hidden',
      'hide_border', 'hide_days', 'hide_seconds', 'idx', 'ignore_user_permissions',
      'ignore_xss_filter', 'in_global_search', 'in_list_view', 'in_preview', 'in_standard_filter',
      'insert_after', 'is_system_generated', 'is_virtual', 'label', 'length', 'link_filters',
      'mandatory_depends_on', 'modified', 'modified_by', 'module', 'name', 'no_copy',
      'non_negative', 'options', 'owner', 'permlevel', 'placeholder', 'precision', 'print_hide',
      'print_hide_if_no_value', 'print_width', 'read_only', 'read_only_depends_on', 'report_hide',
      'reqd', 'search_index', 'show_dashboard', 'sort_options', 'translatable', 'unique', 'width']

**三条结论（都改写了 plan 起草时的假定，照实记）**：

1. **`Item` 上今天一条 Custom Field 都没有（0 条）。** 于是往返不变量 2（零定制也必须落盘）
   **不是理论边界，而是 `test_export_produces_readable_diff_only` 走的正路**：那条门禁的 baseline 导出
   就是一个空数组文件，不落盘的话加字段后新文件是 untracked、`git diff HEAD` 看不见、`assert changed` 直接红。
   起草时把它当成「兜底情形」，实测证明它是主路径。
2. **探针排序位置：index 0 of 1。** 数组从**空**变成**一条**，plan 推论三说的「插到数组末尾要给前一个元素补逗号」
   那个残余风险在本站点上**根本没有机会发生**（没有前一个元素）。但这是**当前站点数据的偶然**，
   不是判据保证——Item 上以后但凡有第二个定制字段，风险就回来了。因此排版仍取 ④（见下面的 `Decision`）。
3. **站点行 58 个键，其中没有 `doctype` 键**（承载归属的是 `dt`）。剥掉 `normalize` 的四类易变键
   （`creation` / `modified` / `modified_by` / `owner`）后 54 个，再去掉 `dt` / `fieldname` 后
   **每个条目 52 个属性**。这直接决定了「一条目一行」的行长在 1KB 量级——是下面 `Decision`（属性投影是否收窄）的输入。

### Phase 1 · `Decision` 1 —— 包文件排版取「逗号独占一行」（备选 ④）

**取**：`{` / `"doctype": …,` / `"custom_fields": [` / 条目行 / `,` 行 / 条目行 / `]` / `}`，两空格缩进，末尾换行。

**备选与结论**：

| 候选 | 结论 |
|---|---|
| ① `json.dumps(indent=2)` 全展开 | **未取**，门禁第二条断言直接排除：新增字段会带出 `"fieldtype": "Data",` 这类既不含探针名、`strip()` 又不在 `"{}[],"` 里的行 |
| ② 一条目一行 + **行尾逗号** | 未取。四种插入位置里「插到数组末尾」会改到前一个条目行（补逗号），那一行不含探针名 → 红。本站点 Item 恰好 0 条定制使该情形今天不可达，但那是数据的偶然不是判据 |
| ③ 一行装下整个文件 | 未取，diff 完全不可读，违背 §11.2 |
| ④ **逗号独占一行** | **取此**。仍是严格 JSON；任意位置插入只新增「条目行 + 逗号行」两行，`,` 本身 `strip()` 后是 `"{}[],"` 的子串 → **四种插入位置全过** |

**为什么实测显示 ② 今天也安全却仍不取 ②**（plan 明确要求回答这一问）：② 的安全性取决于
「Item 上没有排在探针之后的定制字段」这条**站点数据事实**，而不是产物形状的性质。第 3 顺位要在同一份包上做
删除往返，P2 还要在真实租户站点上跑——那些站点的 Item 一定有别的定制字段。判据不该依赖数据的偶然。

**空数组也必须让 `[` 独占一行**（推论二）：写成 `"custom_fields": []` 时，从空到非空会改到那一行，
那行既不含探针名也不是括号行 → 红。本排版下 `[` 与 `]` 各自独占一行，从空到一条只新增一行条目行。

**残余风险**：`,` 独占一行不是常见 JSON 排版习惯，人读 review 时会略感陌生；代价仅止于观感，
且换来「插入位置无关」的判据稳定性。已写进 `module-boundaries.md` §11.6。

### Phase 1 · `Decision` 2 —— 不使用 Frappe 原生 `export_customizations`

**取**：自建导出（站点 REST 只读 → 本地包文件）。

**理由**（§11.1 末段的两条实施约束 + 本仓判据）：Frappe 的 `export_customizations` 要求
`developer_mode`（生产站点默认关闭），且导出目标是 **app 目录**而非任意目录，而我们的签名
`export_customizations(doctype, into)` 收的是任意目录；更要紧的是**产物形状已被
`tests/gates/conftest.py` 的 `PackRepo` 与 `agenerp/snapshot.py` 的 `read_scope_dir` 双向钉死**，
Frappe 的产物形状由 Frappe 定，拿来还得转。

**备选**：走 `bench --site … export-customizations` 再转格式——多一层容器 exec 依赖（本仓的站点面是 REST，
见 §11.7）且形状仍需转换，未取。

**残余风险**：与 Frappe 官方定制包格式不互通，迁移到别的工具链需要一个转换器。
已在 `## Deferred But Adjudicated` 登记为 `watch-only residual`，重开事件写在那里。

### Phase 1 · `Decision` 3 —— 属性投影**不收窄**

**取**：沿用第 1 顺位定的投影口径（`agenerp/snapshot.py` · `entries_from_site_rows`：剥易变键之后全留，
再去掉 `dt` / `fieldname`），本 plan **一个字都不改**。

**理由**：往返不变量 1 要求收窄必须**两侧同源**，而那个唯一落点在 `entries_from_site_rows`——
它同时喂着第 1 顺位刚在 live 转绿的 `test_snapshot_diff_structured.py::test_field_addition_shows_up_as_structured_change`，
而**默认判定环境下那条门禁恒红（在名单内），这条回归在 `GATE_VERIFY` 里一格都看不见**。
用「让包文件行短一点」这个纯可读性收益，去换一条只有 live 才看得见的回归风险，不划算。

**备选**：剥掉 null / 0 / 空串属性，行长从 ~1KB 降到 ~100B。未取，理由同上；且它有语义代价——
包里从此看不出「显式设成 0/false」与「Frappe 缺省」的区别，而 apply 侧要写回站点时这个区别是有意义的。

**残余风险**：条目行长在 1KB 量级（52 个属性），人读 `git diff` 时要横向滚动。
缓解是「一条字段一行」这个粒度本身——加/删/改哪个字段仍然一眼可见，只是属性级差异要靠工具看。
将来若收窄，落点仍是 `entries_from_site_rows` 一处，且必须在同一 phase 里复跑 live 快照门禁。
已写进 `module-boundaries.md` §11.6。

### Phase 2 · 落地与往返判据（2026-08-21）

**产物**（三处，无第四处）：

- `agenerp/pack.py` · `render_doctype_file(doctype, rows)` —— 纯函数，「怎么排版」的**唯一**落点。
- `agenerp/pack.py` · `export_customizations(doctype, into, source=None)` —— 站点读 → 过滤该 DocType →
  排序 → 写 `<into>/doctypes/<DocType>.json`。站点读**复用 `capture(PACK_SCOPE, source=SiteSnapshotSource(site))`**，
  一条新查询都没开（结构边界表那一行照办），因此不变量 1 由构造保证、不变量 5 直接继承 §11.7。
  `agenerp.snapshot` / `agenerp.apply` 在**函数体内**导入（顶层导入即 `pack` ↔ `snapshot` 循环）。
- `tests/unit/test_pack_export.py` —— 新文件，**15 条**用例。

**`Decision` 4（属性投影）落地为「不收窄」**，故 `agenerp/snapshot.py` **一个字节未改**
（`git status --porcelain` 里没有它）。

**为什么导出不走 `snapshot.resolve_source`**：它「无站点配置就退回离线来源」，而离线来源在空目录上
返回零条目且不抛——那正好会写出一个空包，而空包在第 3 顺位读起来跟「该 DocType 的定制全被删了」
一模一样。导出这条路径上，站点名未配置 / 站点答不上话 / 认证失败**一律抛 `SiteError` 且不留任何文件**；
**空数组文件只在站点成功答出「零条目」时才写**。两条分界各有一条单测把守。

**用例数增量（不写空断言的「exit 0」）**：`tests/unit` 由 **130 → 144**（+14）。
拆开是 `test_pack_export.py` **新增 15 条**，`test_contract_surface.py` **减 1 条**——
`agenerp.pack:export_customizations` 从 `NOT_YET_IMPLEMENTED` 搬进 `IMPLEMENTED`，
那条参数化的「调用即 `NotImplementedError`」用例随之消失（该文件的既定维护方式：只搬名字，不改结构）。

**15 条的分布**：往返不变量 1（双向相等 + 易变键不进包，2 条）· 2（零定制落盘 + 空数组不塌成一行，2 条）·
3（重复导出逐字节相同，1 条）· 4（严格 JSON + 条目按 `fieldname` 排序，1 条）·
5（全部行进包 + 请求里 `limit_page_length=0` 仍在，1 条，用真 `SiteClient` + 假传输）·
邻居 DocType 文件逐字节未变（1 条）· 站点抛错不产文件（1 条）· 无 `AGENERP_SITE` 抛而不退回离线（1 条）·
**排版回归 4 条**（`empty-array` / `insert-at-front` / `insert-at-end` / `insert-in-middle` 四种插入位置各一格）·
写读两侧键名一致（1 条）。

排版回归**不 import `tests/gates/` 的任何东西**（红线 1 + 判据独立性），断言在本文件里自带；
差分用 `difflib`（`n=0`）而不是起 git——判的是「插入一个条目会改动哪些行」，
两者对纯插入给出同一组新增行，而 difflib 不需要在 tmp 目录里配 git 身份。
`insert-at-end` 那一格正是把 `Decision` 1 里「行尾逗号排版会红」钉死的地方——
它不依赖任何站点数据，所以 `Explore` 实测的「Item 今天恰好 0 条定制」不再是判据的支点。

**Phase 2 验证（命令原文 + 退出码）**：

| 命令 | 退出码 |
|---|---|
| `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | **0**（判定器：门禁 19 项，预期红 7、绿 12、跳过 0，与名单完全一致；单测 144 passed） |
| `python3 -m pytest tests/unit/test_pack_export.py -q` | **0**（15 passed） |
| `ruff check agenerp tests/unit tests/contracts` | **0**（All checks passed） |

`agenerp/pack.py` 内已无 `export_customizations` 的 `NotImplementedError`（该函数体全部为实现代码）。

### Phase 3 · 活站点实跑、变异验证与文档（2026-08-21，栈端口 18080）

**栈状态**：`docker compose ps` → 六个 healthy + 三个 running（queue-long / queue-short / scheduler 无 healthcheck），
`curl -H 'Host: frontend' http://127.0.0.1:18080/api/method/ping` → **HTTP 200**。栈是既有运行实例，本轮未冷起。

**① 两条导出门禁实跑**（plan 原文那条命令，一字未改）：

    AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q
    → exit 1 · `2 failed, 2 passed in 4.94s`

逐条（同一条命令加 `-v` 复跑，exit 同为 1）：

| 门禁 | 结果 |
|---|---|
| `test_added_field_exports_into_pack` | **PASSED** |
| `test_export_produces_readable_diff_only` | **PASSED** |
| `test_removing_from_pack_actually_deletes_on_site` | FAILED —— `agenerp/apply.py:107: NotImplementedError`（`execute_plan`） |
| `test_no_orphan_column_left_behind` | FAILED —— **同样** `agenerp/apply.py:107: NotImplementedError`（`execute_plan`），本轮走不到 `schema_drift` |

后两条的红因与 plan 起草时的预判**逐字相符**：都在 `apply_pack` → `execute_plan` 处停下，不是红在导出上。
失败原文里 `execute_plan` 打出的计划是 `删除 11`（跨 11 个 DocType）——**那是第 3 顺位「作用域收窄」的输入，不是本 plan 的缺陷**：
`read_pack` 只看到 `Item.json`，而 `capture` 读的是全站，两者相减自然把别的 DocType 算成删除。
第 3 顺位已裁定按「包目录里存在文件的 DocType」收窄，此处照实记录，不在本 plan 处置。

**② 变异验证 ×2 —— 都指名红因，并顺带暴露了门禁的牙齿边界（新事实，照实记）**：

| 变异 | 结果 |
|---|---|
| 包文件顶层加 `"exported_at"` **常量**行（`"2026-08-21T19:22:00Z"`） | `test_export_produces_readable_diff_only` **仍绿**（`2 failed, 2 passed`，与未变异时一模一样）。**变异空转** —— 常量行两次导出逐字相同，`git diff` 里根本不出现 |
| 同一位置改成 `datetime.now().isoformat()`（真时间戳） | **转红**：`3 failed, 1 passed`，逐字 `AssertionError: diff 里夹带了与本次改动无关的内容：['"exported_at": "2026-08-21T21:37:50.039229",', '"exported_at": "2026-08-21T21:37:50.523794",']` |
| 排序阶段丢 `fieldname`（第一次尝试） | 转红但**红得不对**：`KeyError: 'fieldname'` 在 `agenerp/pack.py:146` 的排序键上——那是实现自己崩了，**证明不了门禁的断言有牙齿**。作废重做 |
| 渲染阶段丢 `fieldname`（重做） | `test_added_field_exports_into_pack` **转红**，逐字 `AssertionError: 新增的字段没有进定制包`（`tests/gates/test_customization_roundtrip_delete.py:23`）。**这条门禁的牙齿此前一次都没验过，现在验过了** |

两条**必须记进 §11.6 的新事实**：

1. `test_export_produces_readable_diff_only` 挡的是**易变**噪声，**挡不住恒定的多余键**。
   plan 起草时写的变异 ①「加一个独占一行的 `exported_at`」隐含假定它是时间戳；写成常量就空转。
   真要挡「包里多了不该有的键」，靠的是往返不变量（`tests/unit/test_pack_export.py`），不是这条门禁。
2. 渲染阶段丢 `fieldname` 时 `test_export_produces_readable_diff_only` **仍绿**——
   条目行里的 `"name": "Item-agenerp_gate_roundtrip"` 仍含探针名。**两条门禁各挡各的，谁都不是另一条的替身。**

**还原核对**：两次变异后均已还原。`shasum -a 256 agenerp/pack.py` 变异前与还原后**同为**
`fa5f27476c554d180bd00729fa22d4a39ddcf7ad195ab65d623f976a1a6889ad`；
`git status --porcelain` 相对变异前基线**逐行相同**（`M agenerp/pack.py` / `M docs/architecture/module-boundaries.md` /
`M docs/plans/.../1922-2...md` / `M tests/unit/test_contract_surface.py` / `?? tests/unit/test_pack_export.py`）。
还原后复跑同一条 live 命令 → **exit 1 · `2 failed, 2 passed`**，与变异前一致。

**③ 快照门禁回归**：`Decision` 3 取「不收窄投影」，`agenerp/snapshot.py` 一个字节未动，按 plan 这一格**无需回归**。
仍在同一 live 环境顺手复跑了一次作为加固（成本近零，而它是第 1 顺位刚转绿、默认判定器看不见的一条）：

    AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q
    → **exit 0** · `3 passed in 2.45s`

**④ 收尾复跑默认环境判定器**：`python3 tools/gates/check_expected_red.py` → **exit 0**
（「门禁 19 项：预期红 7，绿 12，跳过 0 / ✅ 与预期红名单完全一致」）。
`tools/gates/expected-red.txt` **一行未动**（`git diff --stat` 对该路径为空）。

**⑤ 站点无残留**：探针字段由 `live_site` fixture 自己清掉，实跑后站点 Custom Field
仍为 **10 行**、`agenerp_gate_roundtrip` **不在其中**——与 Phase 1 `Explore` 的清点基线一致。

**⑥ 文档落盘**：§11.6 增「定制包写入口径」小节（两个落点、站点读取路径、排版三候选取舍、投影不收窄的理由）
＋「活站点实测」段（命令原文、退出码、两条变异、牙齿边界两条新事实、还原核对、快照回归）；
§11.6 原「残余风险：`export_customizations` 尚未实现，包的真实产出形状还没有活证据」一段改写为实测结论——
**布局 (b) 未被推翻**，`read_pack` 一行未改、`plan_apply` 形状未动。
roadmap 对照表第 6 行归属更正 + 新增「6 现状」行（见下）。

**⑦ 验证范围（明写，不许报成 CI 也验过）**：所有 live 命令**只在本机跑过**。
`missions/p0-foundation.json` 的 `commands.test` 跑不到它们，CI 的 `gates-l1` 也跑不到
（`-m 'not live'`）。代偿控制是上面两条变异验证 + 单测里的排版回归四格。


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

- [x] in-scope behavior is complete（导出真能产出可 diff 的包，不是只有签名）
- [x] relevant docs are aligned（§11.6、roadmap 第 6 行、日志）
- [x] verification has run：`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`
      + `ruff check agenerp tests/unit tests/contracts` + Phase 3 的 live 命令，逐条抄退出码
- [x] **verification scope limited 明写**：live 实跑只在本机做过，不得报成「CI 上也验证过」
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified
- [ ] closure audit was independent —— **未满足，照实记**：本轮执行环境明令不得调用子代理，
      走 AGENTS.md 的 Reviewer-Availability Fallback（solo cold-replay：逐条复跑命令、逐条核对产物与文档）。
      本 plan 不触及受保护区域（`tests/gates/**` / `.github/workflows/**` / `missions/**` / `docs/masterplan/**` 全未改），
      但 fallback 只允许「记录并说明限制」，不允许把它算成已满足。**独立关闭审计仍欠着**，见 Follow-up。
- [x] closure evidence exists in files
- [x] **红线自查**：`git diff --name-only` 不含 `tests/gates/`、`.github/workflows/`、`missions/`、
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

Status Note: **完成，但关闭审计不是独立的**（见下）。三处产物全部落地：`render_doctype_file` +
`export_customizations`（`agenerp/pack.py`）、`tests/unit/test_pack_export.py`（15 条）、
§11.6 与 roadmap 的文档对齐。两条绑定门禁 `test_added_field_exports_into_pack` 与
`test_export_produces_readable_diff_only` **在活站点上实测转绿**；另两条仍红且**逐字红在
`execute_plan` 的 `NotImplementedError`**，归第 3 顺位与工作项 6 的第二个 plan。
`tools/gates/expected-red.txt` **一行未动**，工作项 6 保持 `planned`——与 Non-Goals 一致，
理由是默认判定环境下 L2 恒红，划名单会让 `GATE_VERIFY` 立刻转红。

Closure Audit Evidence:

- Auditor / Agent: **solo cold-replay（非独立）** —— 本轮执行环境明令不得调用子代理，
  按 AGENTS.md 的 Reviewer-Availability Fallback 记录限制。**独立关闭审计仍欠着。**
- Evidence（命令原文 + 退出码，逐条复跑得到）：
  | 命令 | 退出码 |
  |---|---|
  | `python3 tools/gates/check_expected_red.py` | **0** |
  | `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | **0**（144 passed） |
  | `python3 -m pytest tests/unit/test_pack_export.py -q` | **0**（15 passed） |
  | `ruff check agenerp tests/unit tests/contracts` | **0** |
  | `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q` | **1**（`2 failed, 2 passed`；两条导出 PASSED） |
  | `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q` | **0**（3 passed） |
- 红线自查：`git diff --name-only` 不含 `tests/gates/`、`.github/workflows/`、`missions/`、
  `docs/masterplan/`；`tools/gates/expected-red.txt` 未变。本轮**未追加 STATE 证据行**——
  名单矛盾已由第 1 顺位登记进 STATE §3，本 plan 不重复登记。
- commit sha：`e19b64f`（本 plan 的全部产物在这一个提交里；上述所有退出码均在该提交的工作树上取得）。

Follow-up:

- **欠一次独立关闭审计**（本轮 solo）。若人或后续会话可起独立评审者，重点复核三处：
  ① `export_customizations` 与 `resolve_source` 的分界（空包 vs 抛错）是否真的没被合并；
  ② 排版回归四格是否真能替代「站点数据的偶然」；③ §11.6 新增的两条「门禁牙齿边界」是否成立。
- **门禁牙齿边界（新事实，已写进 §11.6）**：`test_export_produces_readable_diff_only` 挡易变噪声，
  **挡不住恒定的多余键**；且丢 `fieldname` 时它仍绿（`name` 里含探针名）。这条不需要改门禁（红线 1），
  只需要知道「谁挡什么」——真正挡多余键的是 `tests/unit/test_pack_export.py` 的往返不变量。
- `test_no_orphan_column_left_behind`（`schema_drift`）归工作项 6 的第二个 plan，重开事件写在
  `## Deferred But Adjudicated`：第 3 顺位 plan 关闭之后。
- 包体扩到 Property Setter / DocPerm / Client Script 归 P2，重开事件同上节。
