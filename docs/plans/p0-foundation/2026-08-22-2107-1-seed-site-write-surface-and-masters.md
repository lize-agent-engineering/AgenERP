# 2026-08-22-2107-1 种子数据 B 半（第一段）：站点写入面 + 主数据在活站点上装得出来

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 7. 种子数据（确定性生成，内置 1,010 米积压这个已知业务荒谬）—— **B 半的第一段**
> Last Reviewed: 2026-08-22
> Source: plan `2026-08-21-1634-1-seed-dataset-deterministic.md` 的 `## Deferred But Adjudicated`
>   第一条「把数据集装载进活站点 + 站点侧的荒谬断言（工作项 7 的 B 半）」，
>   `Successor Required: yes`，**重开事件已满足**（见 Current Baseline 第 1 条）。
> Related: `2026-08-22-2107-2-seed-documents-site-computed-backlog.md`（本批第二个 plan，承接单据段与站点侧对账）·
>   `2026-08-21-1922-1-site-snapshot-source-live.md`（站点**只读**传输的交付者，本 plan 在同一个 `SiteClient` 上加写入面）·
>   `docs/backlog/gate-proposal-seed-dataset.md`（B 半的门禁提案，**采纳者是人**，本 plan 不代人采纳）
> Execution Order: **1 / 2** —— 主数据不存在时，第二个 plan 的任何一张业务单据都提交不了。
> Audit: required

## Current Baseline

以下每一条都是 2026-08-22 在 `478392e` 上实读或实跑得到的，不是回忆。
**⚠️ 本节有三条是独立草案评审第 1 轮推翻起草时写法后重写的**（第 8、9、11 条），逐条标了出处。

1. **重开事件已满足。** `1634-1` 那条 Deferred 逐字写的重开事件是「人对 `STATE.md` §3 的
   (a)/(b)/(c)/(d) 作出选择之后」。那条 §3 行现已 `[resolved]`（`docs/masterplan/archive/STATE-2026-08-22.md:195`），
   人在 `ede5440` 亲手实现了三个 fixture（含 `live_site`），阻塞在 `3fed439` 关闭。
   工作项 4/5/6 的同源 Deferred 已据此重开并各自落地，本 plan 走的是同一条路径。
2. **A 半是活的。** `python3 -m agenerp.seed --seed 42 --verify` → **exit 0**；
   `python3 -m pytest tests/unit -q` → **exit 0**，`221 passed in 0.65s`。
3. **数据集此刻是纯内存/落盘模型，站点一无所知。** `agenerp/seed/ledger.py` 的
   `stock_ledger_and_bins()` / `gl_entries()` **自己构造** `Bin` / `Stock Ledger Entry` / `GL Entry` 三类行
   （`dataset.py` 只做装配）。**这三类恰恰是站点应当自己算出来的**——B 半存在的全部理由。
4. **主数据的形状已经贴着 ERPNext，但不完整。** `masters.items()` 的行含 `item_name` / `item_group` /
   `stock_uom` / `is_stock_item`；`masters.warehouses()` 只有 `name` / `company` / `is_group`，
   **没有 `warehouse_name`**；`masters.bom()` 带 `operations` 三行（织造 / 定型 / 成品检验，各带 `hour_rate`）。
   `agenerp/seed/masters.py` 里**没有 `Account` 的行**，`model.py` 里也没有 `root_type` / `parent_account` /
   `account_type` / `Company.abbr` / `default_currency` —— 装载器要补的字段清单由此确定（见 Phase 3 的 `Decision`）。
5. **站点上此刻没有公司。** 实跑 `bench execute frappe.client.get_list --kwargs "{'doctype':'Company',...}"`
   → **stdout 零字节**；`frappe.db.get_default --kwargs "{'key':'company'}"` → **stdout 零字节**。
   按 `agenerp/oob.py` 已实测写死的口径（`bench execute` 只在返回值为真时才打印，`frappe/commands/utils.py:285` 的 `if ret:`），
   零字节即**假值**。建站只跑了 `bench new-site --install-app erpnext`（`docker-compose.yml:146-150`），**没跑 setup wizard**。
6. **`SiteClient` 今天只有一条写动作。** `agenerp/site.py:139` 的公开面是 `get` / `list_resource` /
   `delete_custom_field`（`:196`）。传输层 `UrllibTransport`（`:105`）**带 cookie jar**；
   `_request`（`:233`）以 `200 <= status < 300` 判成败，不吞异常。
7. **本仓已有一道「写方法必须登记」的守卫，而且它有牙齿。** `tests/unit/test_site_client.py:38`
   逐字为 `WRITE_METHOD_ALLOWLIST: tuple[str, ...] = ("SiteClient.delete_custom_field",)`；
   `:255-258` 拿 `agenerp/contracts.py:40` 的 `WRITE_VERBS = ("create","write","submit","cancel","delete","amend")`
   去扫公开方法名，未登记即 `assert` 失败；`:261` 还有一条专门证明该断言不空转的测例。
   ⚠️ **起草时漏掉了这道守卫**（评审第 1 轮指出）：叫 `insert` / `ensure` 的方法**名字里没有任何一个 `WRITE_VERB`**，
   守卫会**空转着变绿**而一个通用建档面已经落地。命名与登记因此是本 plan 的硬约束，不是风格问题。
   ⚠️ **但这道守卫的设计意图不是禁止新增写方法**：`agenerp/site.py` 约束 4 逐字写着
   「这是**收窄式演进**——每加一个写方法就要付一次 diff 和一次留痕，不是把只读约束取消了」。
   D2 因此走「按它的规矩加」，不是「绕过它」。同段还逐字禁止「**删**任意 DocType 文档的通用方法」，
   本 plan 加的是**建**，不落在那条禁止内。
8. **`agenerp.seed` 有一条模块级不变量，装载器与它直接冲突。** `module-boundaries.md:746` 逐字：
   「模块：`agenerp.seed`（包，非单文件）。零第三方依赖，纯标准库，**不读时钟、不读环境、不联网**。」
   装载器必然读环境（站点凭据）并联网。⚠️ **起草时把装载器放进了 `agenerp/seed/loader.py`**（评审第 1 轮指出），
   那会打掉这条不变量。处置见 Phase 1 的 `Decision`（本 plan 选**保住不变量**而不是改松它）。
9. **期望值有三份副本，`model.py` 不是唯一落点。** ⚠️ **起草时写的「`model.py` 是唯一落点」是错的**（评审第 1 轮指出）：
   `agenerp/seed/checks.py:23-24` 独立持有 `EXPECTED_BACKLOG_QTY = 1010.0` / `EXPECTED_BACKLOG_VALUE = 6450.0`，
   且该段自述「刻意不从 `agenerp.seed.model` 取数」；`tests/gates/test_seed_dataset_absurdity.py:23-24` 是第三份。
   `model.py` 持有的是**输入量**（`RAW_RATE` / `BOM_RAW_QTY` / …），`BACKLOG_VALUE` 是**派生量**。
   本 plan 不改任何一份；本条主要是交给第二个 plan 的输入（防作弊闸该守哪个文件）。
10. **本仓对活站点的写已有一条受保护面，但它只覆盖「删」。** `docs/context/ai-autonomy-policy.md:87`
    那一行标题逐字是「对活站点的**破坏性写**」，落点是 `delete_custom_field` / `execute_plan` 删除路径 /
    `oob.py` · `drop_columns`。**「建」不在字面内**——本 plan 因此自带一条加严（Phase 1）。
11. **⚠️ 工作项 7 有一条绑定门禁，「仍然没有门禁」那句话已经过期。起草时写反了，此处改准**（评审第 1 轮指出）。
    实读：`tests/gates/test_seed_dataset_absurdity.py` **存在**，`grep -c "def test_"` → **6**，
    且**不在** `tools/gates/expected-red.txt` 的 7 行之内（实读该文件全文）。它是 **L1**、断的是**生成器**
    （`:23-24` 自带 `1010.0` / `6450.0` 两个常量副本），与 roadmap 行 `| 7 |` 逐字相符（「**2026-08-21 由人补齐**……实跑全绿」）。
    **因此「判据先行」这条 mission 规则对工作项 7 是满足的，本 plan 不引用任何豁免。**
    **`done` 的真实卡点是另一件事**：`done` 的定义要求「从预期红名单划掉」，而这条 L1 门禁**从未进过名单**，
    该条件在字面上不可满足 —— 与工作项 4/9 同一情形（roadmap 行 `| 9 |`）。
12. **站点侧那一半确实仍没有门禁，这一点没有过期。** 门禁提案拟的三条 **L2** 断言至今是提案文本，
    采纳者是人（`Gates-Change-Approved-By:`）。**本 plan 交付的行为没有属于自己的门禁**，
    代偿控制沿用 §12.7 已写死的那一套（CLI 退出码 + `tests/unit` 单测 + 变异验证 + 独立关闭审计），照实登记，不粉饰。
13. **确认的 owner-doc 漂移三处，Minimum Rule 14 不降级**（Phase 4 逐条改准）：
    ① `module-boundaries.md:852`「工作项『种子数据』本身**仍然没有绑定的门禁测试**」；
    ② `gate-proposal-seed-dataset.md:11`「工作项 7 是八项中**唯一**……写着『尚无门禁』的」；
    ③ `p0-foundation-roadmap.md:93`「工作项 7（种子数据）**仍然没有门禁测试**」。
    ⚠️ ③ 与「roadmap 只许追加」的自查冲突，处置见 Phase 4 的 `Decision`。
14. **整目录 live 判定的最近一次已知绿，是本 plan「装载前后对照」的基线**：
    `main` push 权威运行 `32572618933` 的 `gates-l2-live`（job `97030229667`）逐字
    `门禁 19 项：红 0，绿 19，跳过 0`。**本机侧的装载前一跑由 Phase 3 当场取**，不引用旧结论当基线。
15. **站点状态的复位手段是冷起，不是备份还原。** 本仓已实测过 `docker compose down -v` 冷起
    （plan `2026-08-21-2220-2`：`up -d --wait --wait-timeout 300` → exit 0，62 秒，建站幂等）。
    这是本 plan 唯一可用、且已被本仓证明过的「回到干净站点」手段。

## Goals

1. `agenerp` 长出一个**通用的、幂等的站点写入面**（建 + 读回 + 存在性判断），语义以 Frappe REST 的**实测**返回为准。
   新方法**必须被 `WRITE_METHOD_ALLOWLIST` 守卫看见并登记**。
2. 长出一个**主数据装载段**：把公司、科目、仓库、工序/工位、物料、BOM、客户/供应商
   按 `agenerp/seed/model.py` 的常量装进活站点，**从空站点起连跑两次幂等**。
3. 装载后，**整目录 live 门禁判定仍然 exit 0**。
4. 交付一条可复跑的验收命令，并按本仓既有格式登记进 `docs/context/project-context.md` 的验证命令表。

## Non-Goals

- **不装任何业务单据**（`Sales Order` / `Work Order` / `Stock Entry` / `Delivery Note` /
  `Sales Invoice` / `Purchase Invoice` / `Subcontracting *`），也不断言 `Bin` / `GL Entry` / `Stock Ledger Entry`。
  ⚠️ **归属说明（评审第 1 轮补）**：`Sales Order` 与 `Work Order` 虽然写在 `agenerp/seed/masters.py:95-144`，
  但它们是**业务单据**，归第二个 plan。「masters.py 里的都算主数据」是错的读法，本 plan 按**语义**切，不按文件切。
- **不创建、不修改 `tests/gates/**` 下任何文件**（红线 1），**不动 `tools/gates/expected-red.txt`**。
- **不代人采纳** `docs/backlog/gate-proposal-seed-dataset.md`；不把工作项 7 置 `done`。
- **不实现代码级 teardown / 回滚**。站点复位手段是 `docker compose down -v` 冷起（人或执行者手动跑）。
- 不动 `.github/workflows/**`、`missions/**`、`docs/masterplan/**`（`STATE.md` 只追加证据行）。
- 不碰 `agenerp/oob.py` 的 `ALLOWED_CALLS`；不发任何 DDL。
- **不改 `agenerp/seed/` 下任何既有模块的行为**（只读引用），不改 `checks.py` 的 `EXPECTED_*`。

## Task Route

- Type: `implementation-only change`（Goals 1/2/4）+ `app-layer design change`（Phase 1 的授权面、模块归属与写入语义 `Decision`）
- Owner Docs: `docs/architecture/module-boundaries.md` §11.7 · §12（含 `:745` 的模块不变量、`:852` 的漂移）·
  `docs/backlog/gate-proposal-seed-dataset.md` · `docs/context/ai-autonomy-policy.md` · `docs/context/project-context.md`
- Skill Selection Basis: `docs/skills/` 下是 15 份 prompt + 1 份 `README.md` 注册表；其中多数是审计类，
  另有两份重构类（`code-refactor-prompt.md` / `code-refactor-discovery-prompt.md`），**没有一份覆盖「写新实现」这个工作方法**。
  实现相位记 `Skill: none`；评审用 `plan-audit-prompt.md`，关闭审计用 `closure-audit-prompt.md`。

## Infrastructure And Config Prereqs

- 活站点栈（仓根 `docker-compose.yml`）。**端口 18080**：8080 被本机另一套常驻 ERPNext 栈占着。
  起栈：`AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`
- env 与既有 L2 跑法完全相同，不新增变量：
  `AGENERP_SITE=frontend` · `AGENERP_SITE_URL=http://127.0.0.1:18080` · `AGENERP_ADMIN_PASSWORD=admin`
- **站点复位（本 plan 唯一的「回到干净状态」手段，命令原文写死在这里）**：
  `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down -v` 然后
  `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`
  （本仓实测先例：plan `2026-08-21-2220-2`，冷起 exit 0、62 秒、建站幂等）。
- **回滚策略，逐字说清（Protected Areas 对动活站点写路径的 plan 的硬要求）**：
  本 plan **不交付任何代码级回滚或 teardown**。**本次改动之后，站点侧回滚仍然只能手工做**，手段有二：
  ① 上面那条 `down -v` 冷起（丢掉整站数据，回到刚建站的状态）；
  ② 事前 `docker compose exec -T backend bench --site frontend backup`（本仓实测先例：
  plan `2026-08-22-0228-2`，817012 字节 `.sql.gz`；`.gitignore:12` 已有 `.backups-*/`），
  事后由**人**手工 `bench --site frontend restore <path>`。
  **`restore` 不在 `agenerp/oob.py` 的 `ALLOWED_CALLS` 内，本 plan 不加它**（放宽带外执行面是另一条已登记的人裁定题）。
- 无新第三方依赖：`agenerp` 保持零第三方依赖可导入。

## Execution Plan

### Phase 1 - 先探明站点，再定授权面与模块归属（Explore 全部结论必须先于 Decision）

Status: completed
Targets: `docs/logs/` · `docs/context/ai-autonomy-policy.md` · `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md`
Skill: `none`
Prereqs: 无

- [x] `Explore` **E1 · REST 写语义**：在活站点上逐条实测并把**原样输出**记进 `docs/logs/`：
      ① 会话 cookie 下 `POST /api/resource/<DocType>` 是否需要 `X-Frappe-CSRF-Token`；
      ② 建重名回什么状态码与错误类型；③ `PUT` 改已存在文档回什么；
      ④ 建一条无害探针（`Item Group`）再读回。**`delete_custom_field` 走得通不等于 `POST` 走得通。**
      - Skill: `none`
- [x] `Explore` **E2 · `Company` 与自动科目表**：实测 `POST /api/resource/Company`
      （含 `abbr` / `default_currency` / `country` / `create_chart_of_accounts_based_on`）在 v15.119.3 上的真实行为，
      以及建完之后站点上**实际生成了哪些科目**（原样列出）。
      - Skill: `none`
- [x] `Explore` **E3 · 自动命名**：实测 `Warehouse` / `Account` / `BOM` / `Customer` / `Supplier` / `Operation`
      在**显式给 `name`** 时站点是否采纳。`model.py` 的 `WH_RAW = "XM 原料仓 - XM"` / `ACC_RAW = "原材料 - XM"`
      是 ERPNext **派生**出来的名字（`warehouse_name`/`account_name` + 公司缩写），
      而 `masters.warehouses()` **不给 `warehouse_name`**；`names.py` 的 `BOM = "BOM-XM-LACE-1000-001"` 走命名序列。
      **这一条直接决定幂等能不能靠 name 判**（评审第 1 轮指出的风险）。
      - Skill: `none`
- [x] `Explore` **E4 · BOM 的前置**：实测 `BOM.operations` 的 `operation` 是否 Link 到 `Operation` DocType、
      是否强制要 `workstation`；把最小可提交的 `Operation` / `Workstation` 载荷记下来。
      - Skill: `none`
- [x] `Decision` **D1 · 装载器放哪个模块**（依赖 E1）。备选：(a) `agenerp/seed/loader.py` ——
      **否决**，`module-boundaries.md:746` 逐字规定 `agenerp.seed` 「不读时钟、不读环境、不联网」，
      装载器必然两者都做，放进去等于把一条**好的**不变量改松；(b) 改松 §12 的那句不变量 —— 否决，同上；
      (c) **采纳**：新建**独立模块** `agenerp/seedsite.py`，`agenerp/seed/` 保持纯生成器、零改动。
      残余风险：多一个模块、多一处文档落点；比起丢掉「生成路径纯净」这条已被 31 条单测依赖的不变量，代价小得多。
      - Skill: `none`
- [x] `Decision` **D2 · 写方法命名与守卫登记**（依赖 E1）。`tests/unit/test_site_client.py:38` 的
      `WRITE_METHOD_ALLOWLIST` 守卫按 `WRITE_VERBS` 扫方法名，`insert` / `ensure` **不含任何 verb，会让守卫空转变绿**。
      备选：(a) 沿用 `insert`/`ensure` 不管守卫 —— 否决，等于让一道有牙齿的守卫变成摆设；
      (b) 放宽守卫 —— 否决，方向是变松；(c) **采纳**：方法名带 verb（`create_doc` / `ensure_doc`），
      并在 `WRITE_METHOD_ALLOWLIST` 里**逐条登记**（`tests/unit/**` 不受红线保护，可改）。
      同时裁定「写面从**结构定制**扩到**业务主数据**」这件事本身：`agenerp/site.py` 模块 docstring 与
      `module-boundaries.md` §11.7 都写着「只覆盖结构定制」，本 plan 扩了它，**必须就地改准而不是默默扩**（Phase 4）。
      残余风险：`SiteClient` 从此是一个通用写客户端，误用面变大；缓解是 D3 的授权面加严 + 装载器是唯一调用方。
      - Skill: `none`
- [x] `Decision` **D3 · Protected Areas 加严一行**。现有行只覆盖「破坏性写」，本 plan 第一次引入「建」。
      备选：(a) 靠现有行覆盖 —— 否决，该行标题逐字是「破坏性」，靠读者推断等于没有约束；
      (b) 定级 `blocked` —— 否决，会让本 plan 自身无法执行，且过度收紧会阻断 P1/P2；
      (c) **采纳**：新增一行「对活站点的**非破坏性写**（建/改）」，定级 `plan-first`，
      Required Evidence 三条：独立草案评审 + 独立关闭审计 + **一条对可逆性说话的**
      （「本次改动之后站点侧回滚是否仍只能手工做」必须逐字写明）。方向是**加严**。
      残余风险：文档级约束对拿着 shell 的执行器没有强制力（该文件自述），本条不改变这一点。
      - Skill: `none`
- [x] `Decision` **D4 · 工作项 7 将有 3 个 plan，超出「一个工作项 = 1–2 个 plan」**。备选：
      (a) roadmap 新增一个工作项行 —— 否决，工作项表是**引擎的选取输入**（「引擎取第一个 `todo`」），
      新增行会改引擎语义，代价超出本 plan 结果面；
      (b) **把 B 半压成一个 plan（总数 2，规则满足）** —— **否决，理由必须具体**：
      B 半含两个互不相同的结果面——「主数据装得进去」与「站点自己算出 1,010 米 / ¥6,450」；
      后者的判据依赖前者**已经关闭**（否则每次单据实验都要连带怀疑主数据），
      合成一个 plan 会让 Minimum Rule 4「One plan, one result surface」失效，
      且单一 plan 的关闭判据会同时挂着两组互不相干的证据。**规则冲突时选 Minimum Rule 4**，理由：
      它是 `docs/plans/00-plan-authoring-and-execution-guide.md` 的最小规则，
      而「1–2 个 plan」是 roadmap 的启发式，其原文自己指的路是「回来改这张表」；
      (c) 违规不记 —— 否决；
      (d) **采纳**：在 roadmap 工作项 7 处**追加**一条说明行（追加，不改写既有行），
      逐字写明 B 半被拆成本批两个 plan、拆法依据、以及这确实偏离了那条启发式与为什么。
      - Skill: `none`
- [x] `Decision` **D5 · 命名隔离**：装载器写进站点的对象名沿用 `model.py` 已有的 `XM` 前缀常量，
      **不新造命名规则**；隔离是否成立由 Phase 3 的「装载前后各跑一次整目录 live 判定」**判**，不靠声明。
      - Skill: `none`
- [x] `Proof`：E1–E4 的原样输出与 D1–D5 的落点/理由写进 `docs/logs/2026/08-22.md`，
      并按红线 5 往 `STATE.md` §2 **追加**一条证据行（命令原文 + 退出码 + sha）。
      - Skill: `none`

Exit Criteria:

- [x] E1–E4 四组实测各有原样输出，`docs/logs/` 可查；**E3 给出「幂等能不能靠 name 判」的明确结论**
- [x] D1–D5 各有选项、理由、残余风险；D1 结论落到具体模块路径
- [x] `ai-autonomy-policy.md` Protected Areas 多出一行「对活站点的非破坏性写（建/改）」，定级 `plan-first`，
      表下有一段说明本次是**加严**及加严的两件具体事
- [x] roadmap 工作项 7 处多出一条**追加**的说明行（D4）
- [x] `docs/logs/` 更新，`STATE.md` §2 追加一行（只追加，不改写）

### Phase 2 - `SiteClient` 的写入面（纯逻辑可判的那一半）

Status: completed
Targets: `agenerp/site.py` · `tests/unit/test_site_client.py`
Skill: `none`

- Item Types: `Add`-heavy（4/5 项为 `Add`）
- Prereqs: Phase 1（E1/E3 与 D2 必须先出结论）

- [x] `Add`：`SiteClient.create_doc(doctype, payload) -> dict` —— `POST /api/resource/<DocType>`，回 `data`。
      **不吞任何错误**：非 2xx 沿用 `_request` 抛 `SiteError`，站点错误原文进消息。
      - Skill: `none`
- [x] `Add`：存在性判断 —— **以 E3 的结论选形态**：若站点不采纳显式 `name`，
      则 `find_one(doctype, filters) -> dict | None` 走 `filters` 查询；若采纳，则 `get_doc(doctype, name)` 以 404 判不存在。
      **两种形态都必须「只把『查不到』判成不存在」**：其余非 2xx 一律抛，否则站点挂掉会被静默读成「不存在」进而重复建。
      这一条要有专门的单测。
      - Skill: `none`
- [x] `Add`：`SiteClient.ensure_doc(doctype, key, payload) -> tuple[dict, bool]` —— 幂等落地：
      命中则读回返回 `(doc, False)`，未命中则建并返回 `(doc, True)`。
      **`ensure_doc` 不改已存在的文档**（不做 upsert 的 update 半）；理由与代价写进 owner doc。
      - Skill: `none`
- [x] `Add`：把 `SiteClient.create_doc` / `SiteClient.ensure_doc` 逐条加进
      `tests/unit/test_site_client.py:38` 的 `WRITE_METHOD_ALLOWLIST`，并**保留** `:261` 那条「断言不空转」的测例。
      同步改准 `agenerp/site.py` 模块 docstring —— 它逐字写着「写只有一条（`delete_custom_field`）」
      与「本模块的写面只该覆盖『结构定制』」，本 plan 之后**两句都不成立**（确认的 owner-doc 漂移，Rule 14 不降级）。
      - Skill: `none`
- [x] `Proof`：`tests/unit/test_site_client.py` 补至少 9 条：create 成功 / create 非 2xx 抛 /
      存在性命中 / 存在性未命中 / 存在性遇 5xx 必须抛（不得判成不存在）/ `ensure_doc` 命中时**零 POST**（用 FakeTransport 的请求记录断言）/
      `ensure_doc` 未命中时恰好一次 POST / 认证未就绪的报错文案 / 白名单登记后守卫仍为绿。
      命令：`python3 -m pytest tests/unit -q` → exit 0。
      **变异验证两条**：① 把「只把查不到判成不存在」改成「任何非 2xx 都判不存在」→ 必须转红并逐字点名那条；
      ② 把 `create_doc` 从 `WRITE_METHOD_ALLOWLIST` 里删掉 → 守卫必须转红并点名该方法。两条均复原并复跑回 exit 0。
      - Skill: `none`

Exit Criteria:

- [x] 三个方法落地，行为、错误路径、单测三者齐备（不是「签名存在」）
- [x] `WRITE_METHOD_ALLOWLIST` 已登记新方法，且 `:261` 的空转守卫测例仍在且仍绿
- [x] `python3 -m pytest tests/unit -q` → exit 0；两条变异验证各有「转红 → 点名 → 复原转绿」的完整留痕
- [x] `ruff check agenerp tests/unit tests/contracts` → exit 0
- [x] `agenerp/site.py` docstring 的「写只有一条」与「只覆盖结构定制」两句已改准
- [x] `docs/logs/` 更新

### Phase 3 - 主数据装载段 + 从**冷起的空站点**实跑

Status: completed
Targets: `agenerp/seedsite.py`（新建，路径以 D1 结论为准；**CLI 入口就在该模块内**）· `tests/unit/`
Skill: `none`
Prereqs: Phase 2

- [x] `Add`：装载器 —— 把主数据映射成 ERPNext 载荷并经 `ensure_doc` 落地。**依赖顺序写死在装载器里**：
      `Company` → `Account`（`model.py` 的 11 个科目常量）→ `Warehouse`（4 个）→ `Item Group`（成品/原材料/服务）→
      `UOM`（Meter/Kg/Nos）→ **`Workstation` → `Operation`（织造/定型/成品检验）** → `Item`（3 个）→
      `Customer` / `Supplier` → `BOM`。
      ⚠️ **`Workstation` / `Operation` 是评审第 1 轮补进来的**：`masters.bom()` 的 `operations` 三行 Link 到 `Operation`，
      少了它 `BOM` 建不出来，CLI 会按「失败即停」退非 0，Phase 3 的退出判据直接不可达。
      - Skill: `none`
- [x] `Decision`（依赖 **E2**：科目表的实际生成结果决定还要补建哪些科目）：**装载器可以拥有哪些常量**。`masters.py` 没有 `Account` 行，`model.py` 也没有
      `root_type` / `parent_account` / `account_type` / `Company.abbr` / `default_currency` / `country`
      与 `Workstation` 的字段。备选：(a) 往 `model.py` 加这些字段 —— 否决，`model.py` 自述是
      「参与断言的数量、单价、日期」的落点，塞进 ERPNext 结构字段会稀释它；
      (b) **采纳**：**参与断言的数值一律从 `model.py` 取，装载器里不得出现第二份**；
      **纯 ERPNext 结构字段**（科目类型、父科目、公司缩写、币种、国别、工位归属）由装载器自己拥有，
      并在 owner doc 里逐条列名，说明它们**不参与任何断言**。
      残余风险：这条边界靠人读，没有机械判据；缓解是第二个 plan 的对账会把「结构字段填错」表现成数对不上。
      - Skill: `none`
- [x] `Add`：CLI `python3 -m agenerp.seedsite --load-masters --site <site>` —— 幂等，
      成功打印每个 DocType 的「新建 N / 已存在 M」并退 0；任一步失败**立即停并退非 0**，不留半装状态。
      不带 `--site` 时报错退 2。**`python3 -m agenerp.seed --seed 42 --verify` 的既有行为逐字节不变。**
      - Skill: `none`
- [x] `Proof`（纯逻辑半）：`tests/unit/` 新增装载器映射单测（FakeTransport，不连站点）：
      依赖顺序（含 `Workstation`/`Operation` 在 `BOM` 之前）、载荷字段、幂等（第二次跑零 POST）、失败即停。
      `python3 -m pytest tests/unit -q` → exit 0。
      - Skill: `none`
- [x] `Proof`（活站点半，**必须从冷起的空站点开始**）：
      ① `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down -v`，
      再 `… up -d --wait --wait-timeout 300` → exit 0；
      ② 装载前跑一次整目录 live 判定（见下一项），取得**本机基线**；
      ③ `… python3 -m agenerp.seedsite --load-masters --site frontend` → exit 0；
      ④ **原样再跑一次** → exit 0 且**「新建 0」**（幂等的判据是第二跑的计数，不是「没报错」）；
      ⑤ 逐条读回 Company / 4 个仓库 / 3 个物料 / 3 个 Operation / BOM，原样输出记进 `docs/logs/`。
      - Skill: `none`
- [x] `Proof`（不弄脏既有判据）：**装载前后各跑一次**
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 tools/gates/check_expected_red.py`
      → 两次都必须 exit 0 且逐字 `门禁 19 项：红 0，绿 19，跳过 0`。
      **固定处置（若装载后转红）**：记录原样输出 → 按红线 5 追加进 `STATE.md` §3 →
      本 plan 置 `deferred` 并在文件头写明重开条件 → 用 Infrastructure 里那条 `down -v` 冷起把站点复位并复跑一次确认基线仍绿
      → **不放宽任何判据、不改 `tests/gates/**`、不猜根因**。
      - Skill: `none`

Exit Criteria:

- [x] 冷起后 `--load-masters` 连跑两次均 exit 0，第二次「新建 0」
- [x] 读回证据（Company / 仓库 / 物料 / Operation / BOM）原样输出在 `docs/logs/` 可查
- [x] 装载前后两次整目录 live 判定均 exit 0，输出逐字记录；装载前那次即本机基线
- [x] `python3 -m agenerp.seed --seed 42 --verify` → exit 0（A 半未被打坏）
- [x] `python3 -m pytest tests/unit -q` → exit 0；`ruff check agenerp tests/unit tests/contracts` → exit 0
- [x] `docs/logs/` 更新，`STATE.md` §2 追加证据行

### Phase 4 - owner doc 就地改准 + 交接

Status: completed
Targets: `docs/architecture/module-boundaries.md` · `docs/context/project-context.md` · `docs/backlog/gate-proposal-seed-dataset.md` · `docs/backlog/p0-foundation-roadmap.md` · `docs/logs/`
Skill: `none`
Prereqs: Phase 3

- [x] `Fix`：`module-boundaries.md:852`「工作项『种子数据』本身**仍然没有绑定的门禁测试**」——**假陈述**，就地改准为：
      工作项 7 已有一条 **L1** 门禁 `tests/gates/test_seed_dataset_absurdity.py`（6 条，人于 2026-08-21 补齐，
      断的是**生成器**，从未进过 `expected-red.txt`）；**站点侧那一半仍无门禁**，提案待人采纳。
      **不得写成「工作项 7 站点侧已有门禁」——那是假的。**
      - Skill: `none`
- [x] `Fix`：同段那句「装载进活站点与站点侧断言那一半**被红线 1 挡着**」就地改准 ——
      被红线 1 挡着的只有「站点侧断言**作为一条门禁**」；**装载器在 `agenerp/**`，红线 1 不挡它**。
      改准句必须保留「门禁仍需人批」这一半，不得抹掉。
      - Skill: `none`
- [x] `Fix`：`gate-proposal-seed-dataset.md:11`「工作项 7 是八项中**唯一**……写着『尚无门禁』的」——**假陈述**，
      就地改准（该文件本 plan 本就要动）。**不改它的 `Status: proposed`，不代人采纳。**
      同时标注「主数据段已就绪」并指向本批两个 plan。
      - Skill: `none`
- [x] `Decision | Fix`：`p0-foundation-roadmap.md:93`「工作项 7（种子数据）**仍然没有门禁测试**」也是**假陈述**，
      但本 plan 的 D4 与 Phase 1 退出判据要求 roadmap **只许追加**。两条义务冲突，就地裁定：
      (a) 静默留着假陈述 —— 否决，Rule 14 明写确认的 owner-doc 漂移不可降级；
      (b) 全文只许追加、把漂移登记进 backlog 等人 —— 否决，这是把一句**已被同一份文件第 65 行自我推翻**的假话继续挂着；
      (c) **采纳**：把「只许追加」的自查**收窄到「工作项状态块」与「工作项 → 门禁测试对照表」**
      （那两处是引擎与判据的落点，改写有真实代价），`## 当前基线` 一节的假陈述**就地改准**。
      关闭时的机械判据随之改为：`git diff` 对 roadmap 的改动**只含** `## 当前基线` 那一处改准 + D4 的追加行，
      状态块与对照表**零删除**。
      - Skill: `none`
- [x] `Add`：`module-boundaries.md` 新增 §12.9「主数据装载在本仓的落点」—— 写清模块归属（为什么装载器**不在**
      `agenerp/seed/` 内，见 D1）、依赖顺序（含 `Workstation`/`Operation`）、幂等口径（`ensure_doc` 不改已存在文档）、
      装载器自有的纯结构字段清单（不参与断言）、命名隔离，**以及「装了就留在站点上、无代码级 teardown、复位靠 `down -v` 冷起」这条代价**，不粉饰。
      - Skill: `none`
- [x] `Fix`：`module-boundaries.md` §11.7 里「站点传输只读 / 写只覆盖结构定制」的表述随写入面同步改准
      （Phase 2 已改代码侧 docstring，这一项管文档侧）。
      - Skill: `none`
- [x] `Add`：`project-context.md` 验证命令表新增一行「种子主数据装载」，含完整 env、端口 18080、
      必须先起栈、以及「⚠️ 它不在 `missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到它」
      四条口径（与 Contract tests / Seed dataset 两行同处理）。
      ⚠️ 动这张表即触发 plan `2026-08-22-1041-1` 登记的 Deferred「验证命令表整体臃肿」的重开事件 ——
      处置写在 `## Deferred But Adjudicated`，**不静默略过**。
      - Skill: `none`

Exit Criteria:

- [x] §12.7 两处假陈述已就地改准，且未出现「站点侧已有门禁」这类新假陈述
- [x] 门禁提案 `:11` 已改准，`Status: proposed` 未被改动，并已标注主数据段现状
- [x] roadmap `## 当前基线` 的假陈述已改准；`git diff` 对 roadmap 的改动仅含该处 + D4 追加行，
      **工作项状态块与对照表零删除**
- [x] §12.9 存在，含模块归属理由、依赖顺序、幂等口径、纯结构字段清单、无 teardown 代价
- [x] §11.7 与 `agenerp/site.py` docstring 的「只读 / 只覆盖结构定制」表述与代码一致
- [x] `project-context.md` 验证命令表新增一行，四条口径齐备
- [x] `docs/logs/` 更新

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，agent `ae3587562e390c33b`）——
  11 条 blocking。要点：① 起草时「工作项 7 没有绑定门禁」是**假陈述**（`test_seed_dataset_absurdity.py` 6 条、
  从未进名单、全绿），据此建立的「判据先行豁免」整个不成立；② 新写方法会绕过
  `tests/unit/test_site_client.py:38` 的 `WRITE_METHOD_ALLOWLIST` 守卫，让它空转变绿；
  ③ 装载器放 `agenerp/seed/` 会打掉 `module-boundaries.md:746` 的模块不变量；
  ④ 依赖顺序缺 `Operation`/`Workstation`，`BOM` 建不出来；⑤ `ensure` 靠 name 判幂等对派生名/自动命名不成立；
  ⑥ Phase 3 的 `Decision` 依赖一个没排进 Phase 1 的 Explore；⑦ 红路径处置没有复位步骤；
  ⑧ 三个 Phase 的 `Item Types` 声明计数不实且不足 80%；⑨ Phase 4 的 `Follow-up` 是 in-scope 工作被误标；
  ⑩ 另两处确认的 owner-doc 漂移未修，且其中一处与「roadmap 只许追加」的自查冲突；
  ⑪ 「3 个 plan」的 `Decision` 漏了唯一不违规的备选（B 半压成一个 plan）。
  **全部 11 条已在本稿逐条落地**：①→Current Baseline 11/12 改写 + 删除豁免主张；②→D2 + Phase 2 登记项 + 变异验证②；
  ③→D1（新建 `agenerp/seedsite.py`，保住不变量而非改松它）；④→Phase 3 依赖顺序补 `Workstation`/`Operation`；
  ⑤→E3 + Phase 2 的存在性判断按 E3 结论选形态；⑥→E2/E3/E4 新增并前置；⑦→Infrastructure 与 Phase 3 固定处置写死 `down -v` 冷起；
  ⑧→三处 `Item Types` 声明删除，只留 Phase 2 那条 4/5；⑨→改标 `Fix`；⑩→Phase 4 补三条 `Fix` + D 裁定自查冲突；
  ⑪→D4 补备选 (b) 并给出具体否决理由。
  **同时采纳的非阻塞更正**：`docs/skills/` 计数与性质、`Bin`/`GL Entry`/`SLE` 的构造归属（`ledger.py` 非 `dataset.py`）、
  `XM` 缩写并非 `model.py` 既有常量、`masters.py` 含 `sales_order`/`work_order` 属第二个 plan 的归属澄清、
  以及「整目录 live 判定基线」补进 Current Baseline 第 14 条。
- Independent draft review iteration 2: **needs revision（单条）**（同一独立子代理，agent `ae3587562e390c33b`，
  重新从盘上读全文并对 8 处实读复核）—— 逐条判定：**11 条 blocking 全部 `RESOLVED`**，
  其中第 3 条评审员记为「比它自己提的修法更强」（选择保住 `agenerp.seed` 的不变量并加一条
  「`agenerp/seed/**` 一个字节未改」的关闭闸，而不是改松那条不变量）。
  **新增 1 条 blocking（N1）**：Phase 3 的 `Targets` 里写了「`agenerp/seed/__main__.py` **或**独立 CLI 入口」，
  这个「或」分支一旦被选中，会同时打掉本 plan 自己的 Non-Goals（「不改 `agenerp/seed/` 下任何既有模块的行为」）
  与 Closure Gate（「`agenerp/seed/**` 一个字节未改」），也是全文仅剩的一处模糊状态。
  **已修**：`Targets` 删去该分支，CLI 入口固定在 `agenerp/seedsite.py` 内。
  **同时采纳的非阻塞更正**：Phase 3 的常量归属 `Decision` 补上「依赖 E2」的显式声明。
  评审员另行实测确认为**无问题**的三处：`python3 -m <单文件模块>` 是合法入口（实跑 `python3 -m agenerp.site` 干净退出）；
  新建 `agenerp/seedsite.py` 不打破任何不变量（`:746` 的规则只约束 `agenerp.seed`，且 `agenerp/oob.py` 已是同级模块的先例）；
  Phase 4 收窄 roadmap 自查**不越红线**（`docs/backlog/**` 既不在 `AGENTS.md` 红线内，也不在 Protected Areas 表内，
  「只许追加」本就是 plan 自设的自查）。
- Independent draft review iteration 3: **accept**（N1 为单行修正，评审员已给出确定修法，修法逐字落地，无新增面）

## Deferred But Adjudicated`
>   第一条「把数据集装载进活站点 + 站点侧的荒谬断言（工作项 7 的 B 半）」，
>   `Successor Required: yes`，**重开事件已满足**（见 Current Baseline 第 1 条）。
> Related: `2026-08-22-2107-2-seed-documents-site-computed-backlog.md`（本批第二个 plan，承接单据段与站点侧对账）·
>   `2026-08-21-1922-1-site-snapshot-source-live.md`（站点**只读**传输的交付者，本 plan 在同一个 `SiteClient` 上加写入面）·
>   `docs/backlog/gate-proposal-seed-dataset.md`（B 半的门禁提案，**采纳者是人**，本 plan 不代人采纳）
> Execution Order: **1 / 2** —— 主数据不存在时，第二个 plan 的任何一张业务单据都提交不了。
> Audit: required

## Current Baseline

以下每一条都是 2026-08-22 在 `478392e` 上实读或实跑得到的，不是回忆。
**⚠️ 本节有三条是独立草案评审第 1 轮推翻起草时写法后重写的**（第 8、9、11 条），逐条标了出处。

1. **重开事件已满足。** `1634-1` 那条 Deferred 逐字写的重开事件是「人对 `STATE.md` §3 的
   (a)/(b)/(c)/(d) 作出选择之后」。那条 §3 行现已 `[resolved]`（`docs/masterplan/archive/STATE-2026-08-22.md:195`），
   人在 `ede5440` 亲手实现了三个 fixture（含 `live_site`），阻塞在 `3fed439` 关闭。
   工作项 4/5/6 的同源 Deferred 已据此重开并各自落地，本 plan 走的是同一条路径。
2. **A 半是活的。** `python3 -m agenerp.seed --seed 42 --verify` → **exit 0**；
   `python3 -m pytest tests/unit -q` → **exit 0**，`221 passed in 0.65s`。
3. **数据集此刻是纯内存/落盘模型，站点一无所知。** `agenerp/seed/ledger.py` 的
   `stock_ledger_and_bins()` / `gl_entries()` **自己构造** `Bin` / `Stock Ledger Entry` / `GL Entry` 三类行
   （`dataset.py` 只做装配）。**这三类恰恰是站点应当自己算出来的**——B 半存在的全部理由。
4. **主数据的形状已经贴着 ERPNext，但不完整。** `masters.items()` 的行含 `item_name` / `item_group` /
   `stock_uom` / `is_stock_item`；`masters.warehouses()` 只有 `name` / `company` / `is_group`，
   **没有 `warehouse_name`**；`masters.bom()` 带 `operations` 三行（织造 / 定型 / 成品检验，各带 `hour_rate`）。
   `agenerp/seed/masters.py` 里**没有 `Account` 的行**，`model.py` 里也没有 `root_type` / `parent_account` /
   `account_type` / `Company.abbr` / `default_currency` —— 装载器要补的字段清单由此确定（见 Phase 3 的 `Decision`）。
5. **站点上此刻没有公司。** 实跑 `bench execute frappe.client.get_list --kwargs "{'doctype':'Company',...}"`
   → **stdout 零字节**；`frappe.db.get_default --kwargs "{'key':'company'}"` → **stdout 零字节**。
   按 `agenerp/oob.py` 已实测写死的口径（`bench execute` 只在返回值为真时才打印，`frappe/commands/utils.py:285` 的 `if ret:`），
   零字节即**假值**。建站只跑了 `bench new-site --install-app erpnext`（`docker-compose.yml:146-150`），**没跑 setup wizard**。
6. **`SiteClient` 今天只有一条写动作。** `agenerp/site.py:139` 的公开面是 `get` / `list_resource` /
   `delete_custom_field`（`:196`）。传输层 `UrllibTransport`（`:105`）**带 cookie jar**；
   `_request`（`:233`）以 `200 <= status < 300` 判成败，不吞异常。
7. **本仓已有一道「写方法必须登记」的守卫，而且它有牙齿。** `tests/unit/test_site_client.py:38`
   逐字为 `WRITE_METHOD_ALLOWLIST: tuple[str, ...] = ("SiteClient.delete_custom_field",)`；
   `:255-258` 拿 `agenerp/contracts.py:40` 的 `WRITE_VERBS = ("create","write","submit","cancel","delete","amend")`
   去扫公开方法名，未登记即 `assert` 失败；`:261` 还有一条专门证明该断言不空转的测例。
   ⚠️ **起草时漏掉了这道守卫**（评审第 1 轮指出）：叫 `insert` / `ensure` 的方法**名字里没有任何一个 `WRITE_VERB`**，
   守卫会**空转着变绿**而一个通用建档面已经落地。命名与登记因此是本 plan 的硬约束，不是风格问题。
   ⚠️ **但这道守卫的设计意图不是禁止新增写方法**：`agenerp/site.py` 约束 4 逐字写着
   「这是**收窄式演进**——每加一个写方法就要付一次 diff 和一次留痕，不是把只读约束取消了」。
   D2 因此走「按它的规矩加」，不是「绕过它」。同段还逐字禁止「**删**任意 DocType 文档的通用方法」，
   本 plan 加的是**建**，不落在那条禁止内。
8. **`agenerp.seed` 有一条模块级不变量，装载器与它直接冲突。** `module-boundaries.md:746` 逐字：
   「模块：`agenerp.seed`（包，非单文件）。零第三方依赖，纯标准库，**不读时钟、不读环境、不联网**。」
   装载器必然读环境（站点凭据）并联网。⚠️ **起草时把装载器放进了 `agenerp/seed/loader.py`**（评审第 1 轮指出），
   那会打掉这条不变量。处置见 Phase 1 的 `Decision`（本 plan 选**保住不变量**而不是改松它）。
9. **期望值有三份副本，`model.py` 不是唯一落点。** ⚠️ **起草时写的「`model.py` 是唯一落点」是错的**（评审第 1 轮指出）：
   `agenerp/seed/checks.py:23-24` 独立持有 `EXPECTED_BACKLOG_QTY = 1010.0` / `EXPECTED_BACKLOG_VALUE = 6450.0`，
   且该段自述「刻意不从 `agenerp.seed.model` 取数」；`tests/gates/test_seed_dataset_absurdity.py:23-24` 是第三份。
   `model.py` 持有的是**输入量**（`RAW_RATE` / `BOM_RAW_QTY` / …），`BACKLOG_VALUE` 是**派生量**。
   本 plan 不改任何一份；本条主要是交给第二个 plan 的输入（防作弊闸该守哪个文件）。
10. **本仓对活站点的写已有一条受保护面，但它只覆盖「删」。** `docs/context/ai-autonomy-policy.md:87`
    那一行标题逐字是「对活站点的**破坏性写**」，落点是 `delete_custom_field` / `execute_plan` 删除路径 /
    `oob.py` · `drop_columns`。**「建」不在字面内**——本 plan 因此自带一条加严（Phase 1）。
11. **⚠️ 工作项 7 有一条绑定门禁，「仍然没有门禁」那句话已经过期。起草时写反了，此处改准**（评审第 1 轮指出）。
    实读：`tests/gates/test_seed_dataset_absurdity.py` **存在**，`grep -c "def test_"` → **6**，
    且**不在** `tools/gates/expected-red.txt` 的 7 行之内（实读该文件全文）。它是 **L1**、断的是**生成器**
    （`:23-24` 自带 `1010.0` / `6450.0` 两个常量副本），与 roadmap 行 `| 7 |` 逐字相符（「**2026-08-21 由人补齐**……实跑全绿」）。
    **因此「判据先行」这条 mission 规则对工作项 7 是满足的，本 plan 不引用任何豁免。**
    **`done` 的真实卡点是另一件事**：`done` 的定义要求「从预期红名单划掉」，而这条 L1 门禁**从未进过名单**，
    该条件在字面上不可满足 —— 与工作项 4/9 同一情形（roadmap 行 `| 9 |`）。
12. **站点侧那一半确实仍没有门禁，这一点没有过期。** 门禁提案拟的三条 **L2** 断言至今是提案文本，
    采纳者是人（`Gates-Change-Approved-By:`）。**本 plan 交付的行为没有属于自己的门禁**，
    代偿控制沿用 §12.7 已写死的那一套（CLI 退出码 + `tests/unit` 单测 + 变异验证 + 独立关闭审计），照实登记，不粉饰。
13. **确认的 owner-doc 漂移三处，Minimum Rule 14 不降级**（Phase 4 逐条改准）：
    ① `module-boundaries.md:852`「工作项『种子数据』本身**仍然没有绑定的门禁测试**」；
    ② `gate-proposal-seed-dataset.md:11`「工作项 7 是八项中**唯一**……写着『尚无门禁』的」；
    ③ `p0-foundation-roadmap.md:93`「工作项 7（种子数据）**仍然没有门禁测试**」。
    ⚠️ ③ 与「roadmap 只许追加」的自查冲突，处置见 Phase 4 的 `Decision`。
14. **整目录 live 判定的最近一次已知绿，是本 plan「装载前后对照」的基线**：
    `main` push 权威运行 `32572618933` 的 `gates-l2-live`（job `97030229667`）逐字
    `门禁 19 项：红 0，绿 19，跳过 0`。**本机侧的装载前一跑由 Phase 3 当场取**，不引用旧结论当基线。
15. **站点状态的复位手段是冷起，不是备份还原。** 本仓已实测过 `docker compose down -v` 冷起
    （plan `2026-08-21-2220-2`：`up -d --wait --wait-timeout 300` → exit 0，62 秒，建站幂等）。
    这是本 plan 唯一可用、且已被本仓证明过的「回到干净站点」手段。

## Goals

1. `agenerp` 长出一个**通用的、幂等的站点写入面**（建 + 读回 + 存在性判断），语义以 Frappe REST 的**实测**返回为准。
   新方法**必须被 `WRITE_METHOD_ALLOWLIST` 守卫看见并登记**。
2. 长出一个**主数据装载段**：把公司、科目、仓库、工序/工位、物料、BOM、客户/供应商
   按 `agenerp/seed/model.py` 的常量装进活站点，**从空站点起连跑两次幂等**。
3. 装载后，**整目录 live 门禁判定仍然 exit 0**。
4. 交付一条可复跑的验收命令，并按本仓既有格式登记进 `docs/context/project-context.md` 的验证命令表。

## Non-Goals

- **不装任何业务单据**（`Sales Order` / `Work Order` / `Stock Entry` / `Delivery Note` /
  `Sales Invoice` / `Purchase Invoice` / `Subcontracting *`），也不断言 `Bin` / `GL Entry` / `Stock Ledger Entry`。
  ⚠️ **归属说明（评审第 1 轮补）**：`Sales Order` 与 `Work Order` 虽然写在 `agenerp/seed/masters.py:95-144`，
  但它们是**业务单据**，归第二个 plan。「masters.py 里的都算主数据」是错的读法，本 plan 按**语义**切，不按文件切。
- **不创建、不修改 `tests/gates/**` 下任何文件**（红线 1），**不动 `tools/gates/expected-red.txt`**。
- **不代人采纳** `docs/backlog/gate-proposal-seed-dataset.md`；不把工作项 7 置 `done`。
- **不实现代码级 teardown / 回滚**。站点复位手段是 `docker compose down -v` 冷起（人或执行者手动跑）。
- 不动 `.github/workflows/**`、`missions/**`、`docs/masterplan/**`（`STATE.md` 只追加证据行）。
- 不碰 `agenerp/oob.py` 的 `ALLOWED_CALLS`；不发任何 DDL。
- **不改 `agenerp/seed/` 下任何既有模块的行为**（只读引用），不改 `checks.py` 的 `EXPECTED_*`。

## Task Route

- Type: `implementation-only change`（Goals 1/2/4）+ `app-layer design change`（Phase 1 的授权面、模块归属与写入语义 `Decision`）
- Owner Docs: `docs/architecture/module-boundaries.md` §11.7 · §12（含 `:745` 的模块不变量、`:852` 的漂移）·
  `docs/backlog/gate-proposal-seed-dataset.md` · `docs/context/ai-autonomy-policy.md` · `docs/context/project-context.md`
- Skill Selection Basis: `docs/skills/` 下是 15 份 prompt + 1 份 `README.md` 注册表；其中多数是审计类，
  另有两份重构类（`code-refactor-prompt.md` / `code-refactor-discovery-prompt.md`），**没有一份覆盖「写新实现」这个工作方法**。
  实现相位记 `Skill: none`；评审用 `plan-audit-prompt.md`，关闭审计用 `closure-audit-prompt.md`。

## Infrastructure And Config Prereqs

- 活站点栈（仓根 `docker-compose.yml`）。**端口 18080**：8080 被本机另一套常驻 ERPNext 栈占着。
  起栈：`AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`
- env 与既有 L2 跑法完全相同，不新增变量：
  `AGENERP_SITE=frontend` · `AGENERP_SITE_URL=http://127.0.0.1:18080` · `AGENERP_ADMIN_PASSWORD=admin`
- **站点复位（本 plan 唯一的「回到干净状态」手段，命令原文写死在这里）**：
  `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down -v` 然后
  `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`
  （本仓实测先例：plan `2026-08-21-2220-2`，冷起 exit 0、62 秒、建站幂等）。
- **回滚策略，逐字说清（Protected Areas 对动活站点写路径的 plan 的硬要求）**：
  本 plan **不交付任何代码级回滚或 teardown**。**本次改动之后，站点侧回滚仍然只能手工做**，手段有二：
  ① 上面那条 `down -v` 冷起（丢掉整站数据，回到刚建站的状态）；
  ② 事前 `docker compose exec -T backend bench --site frontend backup`（本仓实测先例：
  plan `2026-08-22-0228-2`，817012 字节 `.sql.gz`；`.gitignore:12` 已有 `.backups-*/`），
  事后由**人**手工 `bench --site frontend restore <path>`。
  **`restore` 不在 `agenerp/oob.py` 的 `ALLOWED_CALLS` 内，本 plan 不加它**（放宽带外执行面是另一条已登记的人裁定题）。
- 无新第三方依赖：`agenerp` 保持零第三方依赖可导入。

## Execution Plan

### Phase 1 - 先探明站点，再定授权面与模块归属（Explore 全部结论必须先于 Decision）

Status: completed
Targets: `docs/logs/` · `docs/context/ai-autonomy-policy.md` · `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md`
Skill: `none`
Prereqs: 无

- [x] `Explore` **E1 · REST 写语义**：在活站点上逐条实测并把**原样输出**记进 `docs/logs/`：
      ① 会话 cookie 下 `POST /api/resource/<DocType>` 是否需要 `X-Frappe-CSRF-Token`；
      ② 建重名回什么状态码与错误类型；③ `PUT` 改已存在文档回什么；
      ④ 建一条无害探针（`Item Group`）再读回。**`delete_custom_field` 走得通不等于 `POST` 走得通。**
      - Skill: `none`
- [x] `Explore` **E2 · `Company` 与自动科目表**：实测 `POST /api/resource/Company`
      （含 `abbr` / `default_currency` / `country` / `create_chart_of_accounts_based_on`）在 v15.119.3 上的真实行为，
      以及建完之后站点上**实际生成了哪些科目**（原样列出）。
      - Skill: `none`
- [x] `Explore` **E3 · 自动命名**：实测 `Warehouse` / `Account` / `BOM` / `Customer` / `Supplier` / `Operation`
      在**显式给 `name`** 时站点是否采纳。`model.py` 的 `WH_RAW = "XM 原料仓 - XM"` / `ACC_RAW = "原材料 - XM"`
      是 ERPNext **派生**出来的名字（`warehouse_name`/`account_name` + 公司缩写），
      而 `masters.warehouses()` **不给 `warehouse_name`**；`names.py` 的 `BOM = "BOM-XM-LACE-1000-001"` 走命名序列。
      **这一条直接决定幂等能不能靠 name 判**（评审第 1 轮指出的风险）。
      - Skill: `none`
- [x] `Explore` **E4 · BOM 的前置**：实测 `BOM.operations` 的 `operation` 是否 Link 到 `Operation` DocType、
      是否强制要 `workstation`；把最小可提交的 `Operation` / `Workstation` 载荷记下来。
      - Skill: `none`
- [x] `Decision` **D1 · 装载器放哪个模块**（依赖 E1）。备选：(a) `agenerp/seed/loader.py` ——
      **否决**，`module-boundaries.md:746` 逐字规定 `agenerp.seed` 「不读时钟、不读环境、不联网」，
      装载器必然两者都做，放进去等于把一条**好的**不变量改松；(b) 改松 §12 的那句不变量 —— 否决，同上；
      (c) **采纳**：新建**独立模块** `agenerp/seedsite.py`，`agenerp/seed/` 保持纯生成器、零改动。
      残余风险：多一个模块、多一处文档落点；比起丢掉「生成路径纯净」这条已被 31 条单测依赖的不变量，代价小得多。
      - Skill: `none`
- [x] `Decision` **D2 · 写方法命名与守卫登记**（依赖 E1）。`tests/unit/test_site_client.py:38` 的
      `WRITE_METHOD_ALLOWLIST` 守卫按 `WRITE_VERBS` 扫方法名，`insert` / `ensure` **不含任何 verb，会让守卫空转变绿**。
      备选：(a) 沿用 `insert`/`ensure` 不管守卫 —— 否决，等于让一道有牙齿的守卫变成摆设；
      (b) 放宽守卫 —— 否决，方向是变松；(c) **采纳**：方法名带 verb（`create_doc` / `ensure_doc`），
      并在 `WRITE_METHOD_ALLOWLIST` 里**逐条登记**（`tests/unit/**` 不受红线保护，可改）。
      同时裁定「写面从**结构定制**扩到**业务主数据**」这件事本身：`agenerp/site.py` 模块 docstring 与
      `module-boundaries.md` §11.7 都写着「只覆盖结构定制」，本 plan 扩了它，**必须就地改准而不是默默扩**（Phase 4）。
      残余风险：`SiteClient` 从此是一个通用写客户端，误用面变大；缓解是 D3 的授权面加严 + 装载器是唯一调用方。
      - Skill: `none`
- [x] `Decision` **D3 · Protected Areas 加严一行**。现有行只覆盖「破坏性写」，本 plan 第一次引入「建」。
      备选：(a) 靠现有行覆盖 —— 否决，该行标题逐字是「破坏性」，靠读者推断等于没有约束；
      (b) 定级 `blocked` —— 否决，会让本 plan 自身无法执行，且过度收紧会阻断 P1/P2；
      (c) **采纳**：新增一行「对活站点的**非破坏性写**（建/改）」，定级 `plan-first`，
      Required Evidence 三条：独立草案评审 + 独立关闭审计 + **一条对可逆性说话的**
      （「本次改动之后站点侧回滚是否仍只能手工做」必须逐字写明）。方向是**加严**。
      残余风险：文档级约束对拿着 shell 的执行器没有强制力（该文件自述），本条不改变这一点。
      - Skill: `none`
- [x] `Decision` **D4 · 工作项 7 将有 3 个 plan，超出「一个工作项 = 1–2 个 plan」**。备选：
      (a) roadmap 新增一个工作项行 —— 否决，工作项表是**引擎的选取输入**（「引擎取第一个 `todo`」），
      新增行会改引擎语义，代价超出本 plan 结果面；
      (b) **把 B 半压成一个 plan（总数 2，规则满足）** —— **否决，理由必须具体**：
      B 半含两个互不相同的结果面——「主数据装得进去」与「站点自己算出 1,010 米 / ¥6,450」；
      后者的判据依赖前者**已经关闭**（否则每次单据实验都要连带怀疑主数据），
      合成一个 plan 会让 Minimum Rule 4「One plan, one result surface」失效，
      且单一 plan 的关闭判据会同时挂着两组互不相干的证据。**规则冲突时选 Minimum Rule 4**，理由：
      它是 `docs/plans/00-plan-authoring-and-execution-guide.md` 的最小规则，
      而「1–2 个 plan」是 roadmap 的启发式，其原文自己指的路是「回来改这张表」；
      (c) 违规不记 —— 否决；
      (d) **采纳**：在 roadmap 工作项 7 处**追加**一条说明行（追加，不改写既有行），
      逐字写明 B 半被拆成本批两个 plan、拆法依据、以及这确实偏离了那条启发式与为什么。
      - Skill: `none`
- [x] `Decision` **D5 · 命名隔离**：装载器写进站点的对象名沿用 `model.py` 已有的 `XM` 前缀常量，
      **不新造命名规则**；隔离是否成立由 Phase 3 的「装载前后各跑一次整目录 live 判定」**判**，不靠声明。
      - Skill: `none`
- [x] `Proof`：E1–E4 的原样输出与 D1–D5 的落点/理由写进 `docs/logs/2026/08-22.md`，
      并按红线 5 往 `STATE.md` §2 **追加**一条证据行（命令原文 + 退出码 + sha）。
      - Skill: `none`

Exit Criteria:

- [x] E1–E4 四组实测各有原样输出，`docs/logs/` 可查；**E3 给出「幂等能不能靠 name 判」的明确结论**
- [x] D1–D5 各有选项、理由、残余风险；D1 结论落到具体模块路径
- [x] `ai-autonomy-policy.md` Protected Areas 多出一行「对活站点的非破坏性写（建/改）」，定级 `plan-first`，
      表下有一段说明本次是**加严**及加严的两件具体事
- [x] roadmap 工作项 7 处多出一条**追加**的说明行（D4）
- [x] `docs/logs/` 更新，`STATE.md` §2 追加一行（只追加，不改写）

### Phase 2 - `SiteClient` 的写入面（纯逻辑可判的那一半）

Status: completed
Targets: `agenerp/site.py` · `tests/unit/test_site_client.py`
Skill: `none`

- Item Types: `Add`-heavy（4/5 项为 `Add`）
- Prereqs: Phase 1（E1/E3 与 D2 必须先出结论）

- [x] `Add`：`SiteClient.create_doc(doctype, payload) -> dict` —— `POST /api/resource/<DocType>`，回 `data`。
      **不吞任何错误**：非 2xx 沿用 `_request` 抛 `SiteError`，站点错误原文进消息。
      - Skill: `none`
- [x] `Add`：存在性判断 —— **以 E3 的结论选形态**：若站点不采纳显式 `name`，
      则 `find_one(doctype, filters) -> dict | None` 走 `filters` 查询；若采纳，则 `get_doc(doctype, name)` 以 404 判不存在。
      **两种形态都必须「只把『查不到』判成不存在」**：其余非 2xx 一律抛，否则站点挂掉会被静默读成「不存在」进而重复建。
      这一条要有专门的单测。
      - Skill: `none`
- [x] `Add`：`SiteClient.ensure_doc(doctype, key, payload) -> tuple[dict, bool]` —— 幂等落地：
      命中则读回返回 `(doc, False)`，未命中则建并返回 `(doc, True)`。
      **`ensure_doc` 不改已存在的文档**（不做 upsert 的 update 半）；理由与代价写进 owner doc。
      - Skill: `none`
- [x] `Add`：把 `SiteClient.create_doc` / `SiteClient.ensure_doc` 逐条加进
      `tests/unit/test_site_client.py:38` 的 `WRITE_METHOD_ALLOWLIST`，并**保留** `:261` 那条「断言不空转」的测例。
      同步改准 `agenerp/site.py` 模块 docstring —— 它逐字写着「写只有一条（`delete_custom_field`）」
      与「本模块的写面只该覆盖『结构定制』」，本 plan 之后**两句都不成立**（确认的 owner-doc 漂移，Rule 14 不降级）。
      - Skill: `none`
- [x] `Proof`：`tests/unit/test_site_client.py` 补至少 9 条：create 成功 / create 非 2xx 抛 /
      存在性命中 / 存在性未命中 / 存在性遇 5xx 必须抛（不得判成不存在）/ `ensure_doc` 命中时**零 POST**（用 FakeTransport 的请求记录断言）/
      `ensure_doc` 未命中时恰好一次 POST / 认证未就绪的报错文案 / 白名单登记后守卫仍为绿。
      命令：`python3 -m pytest tests/unit -q` → exit 0。
      **变异验证两条**：① 把「只把查不到判成不存在」改成「任何非 2xx 都判不存在」→ 必须转红并逐字点名那条；
      ② 把 `create_doc` 从 `WRITE_METHOD_ALLOWLIST` 里删掉 → 守卫必须转红并点名该方法。两条均复原并复跑回 exit 0。
      - Skill: `none`

Exit Criteria:

- [x] 三个方法落地，行为、错误路径、单测三者齐备（不是「签名存在」）
- [x] `WRITE_METHOD_ALLOWLIST` 已登记新方法，且 `:261` 的空转守卫测例仍在且仍绿
- [x] `python3 -m pytest tests/unit -q` → exit 0；两条变异验证各有「转红 → 点名 → 复原转绿」的完整留痕
- [x] `ruff check agenerp tests/unit tests/contracts` → exit 0
- [x] `agenerp/site.py` docstring 的「写只有一条」与「只覆盖结构定制」两句已改准
- [x] `docs/logs/` 更新

### Phase 3 - 主数据装载段 + 从**冷起的空站点**实跑

Status: completed
Targets: `agenerp/seedsite.py`（新建，路径以 D1 结论为准；**CLI 入口就在该模块内**）· `tests/unit/`
Skill: `none`
Prereqs: Phase 2

- [x] `Add`：装载器 —— 把主数据映射成 ERPNext 载荷并经 `ensure_doc` 落地。**依赖顺序写死在装载器里**：
      `Company` → `Account`（`model.py` 的 11 个科目常量）→ `Warehouse`（4 个）→ `Item Group`（成品/原材料/服务）→
      `UOM`（Meter/Kg/Nos）→ **`Workstation` → `Operation`（织造/定型/成品检验）** → `Item`（3 个）→
      `Customer` / `Supplier` → `BOM`。
      ⚠️ **`Workstation` / `Operation` 是评审第 1 轮补进来的**：`masters.bom()` 的 `operations` 三行 Link 到 `Operation`，
      少了它 `BOM` 建不出来，CLI 会按「失败即停」退非 0，Phase 3 的退出判据直接不可达。
      - Skill: `none`
- [x] `Decision`（依赖 **E2**：科目表的实际生成结果决定还要补建哪些科目）：**装载器可以拥有哪些常量**。`masters.py` 没有 `Account` 行，`model.py` 也没有
      `root_type` / `parent_account` / `account_type` / `Company.abbr` / `default_currency` / `country`
      与 `Workstation` 的字段。备选：(a) 往 `model.py` 加这些字段 —— 否决，`model.py` 自述是
      「参与断言的数量、单价、日期」的落点，塞进 ERPNext 结构字段会稀释它；
      (b) **采纳**：**参与断言的数值一律从 `model.py` 取，装载器里不得出现第二份**；
      **纯 ERPNext 结构字段**（科目类型、父科目、公司缩写、币种、国别、工位归属）由装载器自己拥有，
      并在 owner doc 里逐条列名，说明它们**不参与任何断言**。
      残余风险：这条边界靠人读，没有机械判据；缓解是第二个 plan 的对账会把「结构字段填错」表现成数对不上。
      - Skill: `none`
- [x] `Add`：CLI `python3 -m agenerp.seedsite --load-masters --site <site>` —— 幂等，
      成功打印每个 DocType 的「新建 N / 已存在 M」并退 0；任一步失败**立即停并退非 0**，不留半装状态。
      不带 `--site` 时报错退 2。**`python3 -m agenerp.seed --seed 42 --verify` 的既有行为逐字节不变。**
      - Skill: `none`
- [x] `Proof`（纯逻辑半）：`tests/unit/` 新增装载器映射单测（FakeTransport，不连站点）：
      依赖顺序（含 `Workstation`/`Operation` 在 `BOM` 之前）、载荷字段、幂等（第二次跑零 POST）、失败即停。
      `python3 -m pytest tests/unit -q` → exit 0。
      - Skill: `none`
- [x] `Proof`（活站点半，**必须从冷起的空站点开始**）：
      ① `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down -v`，
      再 `… up -d --wait --wait-timeout 300` → exit 0；
      ② 装载前跑一次整目录 live 判定（见下一项），取得**本机基线**；
      ③ `… python3 -m agenerp.seedsite --load-masters --site frontend` → exit 0；
      ④ **原样再跑一次** → exit 0 且**「新建 0」**（幂等的判据是第二跑的计数，不是「没报错」）；
      ⑤ 逐条读回 Company / 4 个仓库 / 3 个物料 / 3 个 Operation / BOM，原样输出记进 `docs/logs/`。
      - Skill: `none`
- [x] `Proof`（不弄脏既有判据）：**装载前后各跑一次**
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 tools/gates/check_expected_red.py`
      → 两次都必须 exit 0 且逐字 `门禁 19 项：红 0，绿 19，跳过 0`。
      **固定处置（若装载后转红）**：记录原样输出 → 按红线 5 追加进 `STATE.md` §3 →
      本 plan 置 `deferred` 并在文件头写明重开条件 → 用 Infrastructure 里那条 `down -v` 冷起把站点复位并复跑一次确认基线仍绿
      → **不放宽任何判据、不改 `tests/gates/**`、不猜根因**。
      - Skill: `none`

Exit Criteria:

- [x] 冷起后 `--load-masters` 连跑两次均 exit 0，第二次「新建 0」
- [x] 读回证据（Company / 仓库 / 物料 / Operation / BOM）原样输出在 `docs/logs/` 可查
- [x] 装载前后两次整目录 live 判定均 exit 0，输出逐字记录；装载前那次即本机基线
- [x] `python3 -m agenerp.seed --seed 42 --verify` → exit 0（A 半未被打坏）
- [x] `python3 -m pytest tests/unit -q` → exit 0；`ruff check agenerp tests/unit tests/contracts` → exit 0
- [x] `docs/logs/` 更新，`STATE.md` §2 追加证据行

### Phase 4 - owner doc 就地改准 + 交接

Status: completed
Targets: `docs/architecture/module-boundaries.md` · `docs/context/project-context.md` · `docs/backlog/gate-proposal-seed-dataset.md` · `docs/backlog/p0-foundation-roadmap.md` · `docs/logs/`
Skill: `none`
Prereqs: Phase 3

- [x] `Fix`：`module-boundaries.md:852`「工作项『种子数据』本身**仍然没有绑定的门禁测试**」——**假陈述**，就地改准为：
      工作项 7 已有一条 **L1** 门禁 `tests/gates/test_seed_dataset_absurdity.py`（6 条，人于 2026-08-21 补齐，
      断的是**生成器**，从未进过 `expected-red.txt`）；**站点侧那一半仍无门禁**，提案待人采纳。
      **不得写成「工作项 7 站点侧已有门禁」——那是假的。**
      - Skill: `none`
- [x] `Fix`：同段那句「装载进活站点与站点侧断言那一半**被红线 1 挡着**」就地改准 ——
      被红线 1 挡着的只有「站点侧断言**作为一条门禁**」；**装载器在 `agenerp/**`，红线 1 不挡它**。
      改准句必须保留「门禁仍需人批」这一半，不得抹掉。
      - Skill: `none`
- [x] `Fix`：`gate-proposal-seed-dataset.md:11`「工作项 7 是八项中**唯一**……写着『尚无门禁』的」——**假陈述**，
      就地改准（该文件本 plan 本就要动）。**不改它的 `Status: proposed`，不代人采纳。**
      同时标注「主数据段已就绪」并指向本批两个 plan。
      - Skill: `none`
- [x] `Decision | Fix`：`p0-foundation-roadmap.md:93`「工作项 7（种子数据）**仍然没有门禁测试**」也是**假陈述**，
      但本 plan 的 D4 与 Phase 1 退出判据要求 roadmap **只许追加**。两条义务冲突，就地裁定：
      (a) 静默留着假陈述 —— 否决，Rule 14 明写确认的 owner-doc 漂移不可降级；
      (b) 全文只许追加、把漂移登记进 backlog 等人 —— 否决，这是把一句**已被同一份文件第 65 行自我推翻**的假话继续挂着；
      (c) **采纳**：把「只许追加」的自查**收窄到「工作项状态块」与「工作项 → 门禁测试对照表」**
      （那两处是引擎与判据的落点，改写有真实代价），`## 当前基线` 一节的假陈述**就地改准**。
      关闭时的机械判据随之改为：`git diff` 对 roadmap 的改动**只含** `## 当前基线` 那一处改准 + D4 的追加行，
      状态块与对照表**零删除**。
      - Skill: `none`
- [x] `Add`：`module-boundaries.md` 新增 §12.9「主数据装载在本仓的落点」—— 写清模块归属（为什么装载器**不在**
      `agenerp/seed/` 内，见 D1）、依赖顺序（含 `Workstation`/`Operation`）、幂等口径（`ensure_doc` 不改已存在文档）、
      装载器自有的纯结构字段清单（不参与断言）、命名隔离，**以及「装了就留在站点上、无代码级 teardown、复位靠 `down -v` 冷起」这条代价**，不粉饰。
      - Skill: `none`
- [x] `Fix`：`module-boundaries.md` §11.7 里「站点传输只读 / 写只覆盖结构定制」的表述随写入面同步改准
      （Phase 2 已改代码侧 docstring，这一项管文档侧）。
      - Skill: `none`
- [x] `Add`：`project-context.md` 验证命令表新增一行「种子主数据装载」，含完整 env、端口 18080、
      必须先起栈、以及「⚠️ 它不在 `missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到它」
      四条口径（与 Contract tests / Seed dataset 两行同处理）。
      ⚠️ 动这张表即触发 plan `2026-08-22-1041-1` 登记的 Deferred「验证命令表整体臃肿」的重开事件 ——
      处置写在 `## Deferred But Adjudicated`，**不静默略过**。
      - Skill: `none`

Exit Criteria:

- [x] §12.7 两处假陈述已就地改准，且未出现「站点侧已有门禁」这类新假陈述
- [x] 门禁提案 `:11` 已改准，`Status: proposed` 未被改动，并已标注主数据段现状
- [x] roadmap `## 当前基线` 的假陈述已改准；`git diff` 对 roadmap 的改动仅含该处 + D4 追加行，
      **工作项状态块与对照表零删除**
- [x] §12.9 存在，含模块归属理由、依赖顺序、幂等口径、纯结构字段清单、无 teardown 代价
- [x] §11.7 与 `agenerp/site.py` docstring 的「只读 / 只覆盖结构定制」表述与代码一致
- [x] `project-context.md` 验证命令表新增一行，四条口径齐备
- [x] `docs/logs/` 更新

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，agent `ae3587562e390c33b`）——
  11 条 blocking。要点：① 起草时「工作项 7 没有绑定门禁」是**假陈述**（`test_seed_dataset_absurdity.py` 6 条、
  从未进名单、全绿），据此建立的「判据先行豁免」整个不成立；② 新写方法会绕过
  `tests/unit/test_site_client.py:38` 的 `WRITE_METHOD_ALLOWLIST` 守卫，让它空转变绿；
  ③ 装载器放 `agenerp/seed/` 会打掉 `module-boundaries.md:746` 的模块不变量；
  ④ 依赖顺序缺 `Operation`/`Workstation`，`BOM` 建不出来；⑤ `ensure` 靠 name 判幂等对派生名/自动命名不成立；
  ⑥ Phase 3 的 `Decision` 依赖一个没排进 Phase 1 的 Explore；⑦ 红路径处置没有复位步骤；
  ⑧ 三个 Phase 的 `Item Types` 声明计数不实且不足 80%；⑨ Phase 4 的 `Follow-up` 是 in-scope 工作被误标；
  ⑩ 另两处确认的 owner-doc 漂移未修，且其中一处与「roadmap 只许追加」的自查冲突；
  ⑪ 「3 个 plan」的 `Decision` 漏了唯一不违规的备选（B 半压成一个 plan）。
  **全部 11 条已在本稿逐条落地**：①→Current Baseline 11/12 改写 + 删除豁免主张；②→D2 + Phase 2 登记项 + 变异验证②；
  ③→D1（新建 `agenerp/seedsite.py`，保住不变量而非改松它）；④→Phase 3 依赖顺序补 `Workstation`/`Operation`；
  ⑤→E3 + Phase 2 的存在性判断按 E3 结论选形态；⑥→E2/E3/E4 新增并前置；⑦→Infrastructure 与 Phase 3 固定处置写死 `down -v` 冷起；
  ⑧→三处 `Item Types` 声明删除，只留 Phase 2 那条 4/5；⑨→改标 `Fix`；⑩→Phase 4 补三条 `Fix` + D 裁定自查冲突；
  ⑪→D4 补备选 (b) 并给出具体否决理由。
  **同时采纳的非阻塞更正**：`docs/skills/` 计数与性质、`Bin`/`GL Entry`/`SLE` 的构造归属（`ledger.py` 非 `dataset.py`）、
  `XM` 缩写并非 `model.py` 既有常量、`masters.py` 含 `sales_order`/`work_order` 属第二个 plan 的归属澄清、
  以及「整目录 live 判定基线」补进 Current Baseline 第 14 条。
- Independent draft review iteration 2: **needs revision（单条）**（同一独立子代理，agent `ae3587562e390c33b`，
  重新从盘上读全文并对 8 处实读复核）—— 逐条判定：**11 条 blocking 全部 `RESOLVED`**，
  其中第 3 条评审员记为「比它自己提的修法更强」（选择保住 `agenerp.seed` 的不变量并加一条
  「`agenerp/seed/**` 一个字节未改」的关闭闸，而不是改松那条不变量）。
  **新增 1 条 blocking（N1）**：Phase 3 的 `Targets` 里写了「`agenerp/seed/__main__.py` **或**独立 CLI 入口」，
  这个「或」分支一旦被选中，会同时打掉本 plan 自己的 Non-Goals（「不改 `agenerp/seed/` 下任何既有模块的行为」）
  与 Closure Gate（「`agenerp/seed/**` 一个字节未改」），也是全文仅剩的一处模糊状态。
  **已修**：`Targets` 删去该分支，CLI 入口固定在 `agenerp/seedsite.py` 内。
  **同时采纳的非阻塞更正**：Phase 3 的常量归属 `Decision` 补上「依赖 E2」的显式声明。
  评审员另行实测确认为**无问题**的三处：`python3 -m <单文件模块>` 是合法入口（实跑 `python3 -m agenerp.site` 干净退出）；
  新建 `agenerp/seedsite.py` 不打破任何不变量（`:746` 的规则只约束 `agenerp.seed`，且 `agenerp/oob.py` 已是同级模块的先例）；
  Phase 4 收窄 roadmap 自查**不越红线**（`docs/backlog/**` 既不在 `AGENTS.md` 红线内，也不在 Protected Areas 表内，
  「只许追加」本就是 plan 自设的自查）。
- Independent draft review iteration 3: **accept**（N1 为单行修正，评审员已给出确定修法，修法逐字落地，无新增面）

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（§12.7 两处 / §11.7 / §12.9 / 门禁提案 / roadmap 当前基线 / `project-context.md`）
- [x] verification has run：`python3 -m pytest tests/unit -q` · `ruff check agenerp tests/unit tests/contracts` ·
      `python3 -m agenerp.seed --seed 42 --verify` · `python3 -m agenerp.seedsite --load-masters --site frontend`（冷起后连跑两次）·
      装载前后两次 live `python3 tools/gates/check_expected_red.py` · 两条变异验证
- [x] scoped verification is not conflated with full verification —— 本仓无全量套件，
      上列命令全部 scoped，关闭记录必须逐字写「verification scope limited」
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [x] closure evidence exists in files
- [x] **`tests/gates/**` 与 `tools/gates/expected-red.txt` 一个字节未改**
      （`git diff --stat <base>..HEAD -- tests/gates tools/gates/expected-red.txt` 无输出）
- [x] **`agenerp/seed/**` 一个字节未改**（本 plan 只读引用它；装载器在 `agenerp/seedsite.py`）
- [x] **`WRITE_METHOD_ALLOWLIST` 守卫仍有牙齿**：删掉任一登记项 → `tests/unit` 必红并点名
  —— ⚠️ **这一条在自查时被实测证伪过一次**：删掉 `ensure_doc` 的登记，`tests/unit` **照样绿**
  （它名字里一个 `WRITE_VERB` 都没有，扫描守卫看不见它）。**处置是补齐判据，不是把 gate 勾掉或改宽**：
  新增 `NON_VERB_WRITE_METHODS` 与两条测例后，三条登记项**逐条**实测「转红 → 点名 → 复原转绿」。
  详见 `docs/logs/2026/08-22.md` 的「关闭自查」条。
- [x] **工作项 7 未被置 `done`**；roadmap 的工作项状态块与对照表零删除

## Deferred But Adjudicated

### `docs/context/project-context.md` 验证命令表整体臃肿（重开事件由本 plan 触发）

- Classification: `optimization candidate`
- Why Not Blocking Closure: plan `2026-08-22-1041-1` 登记本条时写死的重开事件是
  「下一个需要往该表新增一行或改写既有行的 plan 开工时」——**本 plan 正是那个 plan，事件已发生**。
  但重构那张表是**独立的结果面**，且每一条「二次/三次补记」都是证据，重构有丢证据的风险；
  本 plan 只**新增一行**、不动既有行结构。
- Successor Required: `no` —— 重开事件：**人明确裁定要重构该表时**。本 plan 不代人裁定。
- **执行时的实际处置（2026-08-22 回填，不静默略过）**：重开事件**确已发生**——本 plan 的 Phase 4
  往该表新增了「种子主数据装载」一行。**处置照上面写的执行，一字未改**：
  只**新增一行**，不动任何既有行的结构。实测 `git diff --numstat docs/context/project-context.md`
  → **`3	1`**，那 1 行删除是表头说明句（「2026-08-20 定表，Contract tests 一行 2026-08-21 补入并实测」
  → 同句加上「种子主数据装载一行 2026-08-22 补入并实测」并折行），**不是任何一条命令行**。
  该表此刻仍然臃肿，**本 plan 没有让它变好，也没有让它更坏**；重构仍待人裁定。

### 装载器没有 teardown，装进站点的对象删不掉

- Classification: `watch-only residual`
- Why Not Blocking Closure: 见 `## Non-Goals` 与 §12.9 —— **显式不做**，不是遗漏。
  代偿是命名隔离（`XM` 前缀）+ Infrastructure 写死的两条手工复位路径（`down -v` 冷起 / `bench backup` + 人工 `restore`）。
- Successor Required: `no` —— 重开事件：**门禁开始依赖「站点上没有种子数据」这个前提时**，
  或**人要求把种子站点做成可反复重置的 fixture 时**。

### `ensure_doc` 只建不改，站点上已存在但字段不对的对象不会被纠正

- Classification: `watch-only residual`
- Why Not Blocking Closure: 方向偏保守（少写），错的方向是安全的那一侧；且第二个 plan 的对账
  会把「主数据不对」表现成站点自己算出的数对不上，**不会静默通过**。
- Successor Required: `no` —— 重开事件：**第二个 plan 的对账因主数据字段不符而红时**
  （届时应补一条显式的「已存在但不符即报错」，而不是悄悄改写站点）。

### `SiteClient` 从此是通用写客户端，误用面变大

- Classification: `watch-only residual`
- Why Not Blocking Closure: 缓解有三条且都可判：D3 的 Protected Areas 加严行、
  `WRITE_METHOD_ALLOWLIST` 的登记守卫（有牙齿，Phase 2 变异验证②证明）、装载器是唯一调用方。
- Successor Required: `no` —— 重开事件：**出现第二个调用方时**（届时应评估是否要把写面收进一个更窄的门面）。

### 工作项 7 仍卡在「从预期红名单划掉」这条 `done` 定义上

- Classification: `watch-only residual`
- Why Not Blocking Closure: 这是**已登记的人裁定题**（`docs/backlog/needs-human-expected-red-handoff.md`）。
  ⚠️ **不得把理由写成「工作项 7 没有门禁」**——它有一条 L1 门禁，只是那条门禁从未进过名单，
  所以「划掉」这个动作没有对象，定义在字面上不可满足（与工作项 4/9 同一情形）。
  本 plan 关闭时工作项 7 保持 `planned`。
- Successor Required: `no` —— 重开事件：**人从那份 handoff 文档的候选处置里选定时**。

### `agenerp/seed/model.py` 的 `ACC_OPERATING` 少一个空格，在活站点上永远命不中

- Classification: `confirmed defect, blocked by this plan's own Closure Gate`
- Why Not Blocking Closure: 缺陷**不在本 plan 的交付面上**，且本 plan 的 Closure Gate 逐字要求
  「`agenerp/seed/**` 一个字节未改」——修它就会打掉自己的关闭判据。
  **本 plan 交付的是「不让它静默」**：装载器把站点回的真名与 `agenerp.seed` 的**原始常量**比对，
  不符就打印告警行（活站点上实测打出来了），并有两条单测（报告 + 不空转）钉住这个行为。
  完整记录见 `docs/bugs/01-acc-operating-constant-can-never-match-a-live-account-name.md`。
  ⚠️ **不得把它读成「已经修好」**：`M.ACC_OPERATING` 此刻仍然是错的。
- Successor Required: `yes` —— 重开事件：**第二个 plan（`2026-08-22-2107-2`）的站点侧对账开工时**。
  那个 plan 不受本 plan 的 Closure Gate 约束，且它按科目名取数时会**直接撞上**这个常量。
  修的时候必须连带补一条「11 个 `ACC_*` 常量都能由 `" - ".join([account_name, abbr])` 产出」的单测——
  **现有测试一条都不会替你确认改对了**（它们判的是金额，不是科目名）。

## Closure

Status Note: **四个 Phase 全部执行完毕，`Plan Status: completed`。**

**verification scope limited** —— 本仓**无全量套件**（无 build、无 typecheck）。
下列命令全部 scoped，**不得读成 full green**；其中三条活站点命令**不在**
`missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到它们。

| 命令原文 | 退出码 | 关键输出 |
|---|---|---|
| `python3 -m pytest tests/unit -q` | **0** | `248 passed`（开工基线 221） |
| `ruff check agenerp tests/unit tests/contracts` | **0** | `All checks passed!` |
| `python3 -m agenerp.seed --seed 42 --verify` | **0** | `✅ 种子 42：两次生成 diff 为空，场景断言全过`（A 半未被打坏） |
| `python3 tools/gates/check_expected_red.py`（默认判定环境） | **0** | `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`（逐字节不变） |
| `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down -v` 然后 `… up -d --wait --wait-timeout 300` | **0** | 冷起 **59.6 秒**，九容器 Healthy |
| `… python3 -m agenerp.seedsite --load-masters --site frontend`（第一跑） | **0** | `合计：新建 40 / 已存在 0` |
| **原样第二跑** | **0** | `合计：新建 0 / 已存在 40` —— **幂等的判据是这一行** |
| `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 … python3 tools/gates/check_expected_red.py`（**装载前**） | **0** | `门禁 19 项：红 0，绿 19，跳过 0` —— 本机基线 |
| 同上（**装载后**） | **0** | `门禁 19 项：红 0，绿 19，跳过 0` —— 与装载前**逐字节相同** |

**变异验证四条，各有「转红 → 点名 → 复原转绿」的完整留痕**：
① `find_one` 改成「任何非 2xx 都判不存在」→ `4 failed`，点名
`test_find_one_raises_on_any_non_2xx_and_never_reads_it_as_absent[401]/[403]/[500]/[502]`；
② 删 `create_doc` 登记 → `1 failed`，`AssertionError: 未登记的写方法：['SiteClient.create_doc']`；
③ 删 `ensure_doc` 登记 → `1 failed`，点名 `test_deliberately_registered_write_methods_stay_registered`；
④ 删 `delete_custom_field` 登记 → `1 failed`，`AssertionError: 未登记的写方法：['SiteClient.delete_custom_field']`。

**⚠️ 关闭自查时有一条 Closure Gate 被实测证伪并当场补齐，不是一路顺过来的**：
「删掉**任一**登记项必红」这条在 `ensure_doc` 上**不成立**（扫描守卫看不见没有 verb 的名字）。
处置是**补判据**（新增 `NON_VERB_WRITE_METHODS` + 两条测例），不是勾掉 gate、也不是把 gate 改宽。

**红线自查（锚开工 sha `478392e`）**：`tests/gates` / `tools/gates/expected-red.txt` / `agenerp/seed`
三条路径的 `git diff --stat` 与 `git status --porcelain` **全部无输出**。
roadmap 的删除行**恰好两行**且都在 `## 当前基线`，工作项状态块与对照表**零删除**；
工作项 7 仍是 `planned`，**未被置 `done`**。

**本 plan 交付的行为没有属于自己的门禁**（站点侧那三条 L2 断言仍是提案文本，采纳者是人）。
代偿控制照 §12.7 已写死的那一套登记，**不粉饰**。

Closure Audit Evidence:

- Auditor / Agent: <独立子代理，fresh session —— **执行器不自审，本行留给关闭审计**>
- Evidence: <task id / log link>

Follow-up:

- **无。** 本次发现的两处真缺陷都**没有**被放进这里：
  ① `model.ACC_OPERATING` 少一个空格 → 有 bug note
  （`docs/bugs/01-acc-operating-constant-can-never-match-a-live-account-name.md`，`Status: open`）
  + `## Deferred But Adjudicated` 条目 + 装载器的运行时告警行；
  ② 「删任一登记项必红」这条 gate 在 `ensure_doc` 上不成立 → **本轮已补齐判据，不是遗留**。
  确认的缺陷不得出现在 Follow-up 里，这两条都没出现在这里。
