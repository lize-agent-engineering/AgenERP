# 2026-08-22-2107-2 种子数据 B 半（第二段）：单据装载，让**站点自己**算出 1,010 米 / ¥6,450

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 7. 种子数据（确定性生成，内置 1,010 米积压这个已知业务荒谬）—— **B 半的第二段**
> Last Reviewed: 2026-08-22
> Source: plan `2026-08-21-1634-1-seed-dataset-deterministic.md` 的 `## Deferred But Adjudicated`
>   第一条（B 半，`Successor Required: yes`，重开事件已满足）·
>   `docs/backlog/gate-proposal-seed-dataset.md`「它该断言什么」一节的三条拟断言
> Related: `2026-08-22-2107-1-seed-site-write-surface-and-masters.md`（**硬前置**：写入面与主数据）·
>   `docs/architecture/module-boundaries.md` §12.1（¥6,450 与 1,010 米的单价对账，本 plan 要在站点上复现它）
> Execution Order: **2 / 2** —— 主数据不在站点上，任何一张业务单据都提交不了。
> Audit: required

## Current Baseline

以下每一条都是 2026-08-22 在 `478392e` 上实读或实跑得到的。
**⚠️ 第 3、6、7、8 条是独立草案评审第 1 轮推翻起草时写法后重写的**，逐条标了出处。

1. **本 plan 要证明的那句话，此刻一个字都没被证明过。** `agenerp/seed/ledger.py` 的
   `stock_ledger_and_bins()` / `gl_entries()` **自己构造** `Bin` / `Stock Ledger Entry` / `GL Entry` 三类行
   （`documents.py` 造的是源单据，`dataset.py` 只做装配）；`agenerp/seed/checks.py` 再拿这些构造出来的行去断言。
   **这是生成器自己跟自己对账。** 门禁提案逐字：工作项 7「真正没被证明的恰恰是『ERPNext 也这么算』」。
2. **数值与机制已经对过账，但对的是算术不是站点。** §12.1：自制批 1,000 米 @ ¥5.00
   （原料 120 Kg × ¥35 + 工序 600 分钟 × ¥80/小时）、外协批 1,000 米 @ ¥6.40（原料 ¥4,200 + 服务费 ¥2,200），
   **FIFO** 发货 990 米全部出自制批 → 结余 10 × 5.00 + 1,000 × 6.40 = **¥6,450**、数量 **1,010 米**。
3. **期望值有三份副本，`model.py` 不是唯一落点。** ⚠️ **起草时写的「唯一落点」是错的**（评审第 1 轮指出）：
   `agenerp/seed/checks.py:23-24` 独立持有 `EXPECTED_BACKLOG_QTY = 1010.0` / `EXPECTED_BACKLOG_VALUE = 6450.0`，
   且该段自述「刻意不从 `agenerp.seed.model` 取数」；`tests/gates/test_seed_dataset_absurdity.py:23-24` 是第三份。
   `model.py` 持有的是**输入量**（`RAW_RATE` / `BOM_RAW_QTY` / `SUBCONTRACT_FEE` / …），
   `BACKLOG_QTY` / `BACKLOG_VALUE` 是**派生量**。**防作弊闸必须同时守住 `checks.py` 的 `EXPECTED_*`，
   只守 `model.py` 等于守了一个不含期望值的文件。**
4. **A 半是活的**：`python3 -m agenerp.seed --seed 42 --verify` → exit 0；`python3 -m pytest tests/unit -q` → exit 0，`221 passed`。
5. **§12.8 逐字登记着一条推断**：「站点的存货计价方法（FIFO）是**从两个实测数反推出来的**，
   证据仓里没有一行直接写着 `valuation_method`……这仍是推断而非直证。」
   ⚠️ **它说的是冻结证据仓那个站点**（红线 6，只读），**不是本仓的 `frontend` 站点**。
6. **⚠️ 拟断言 ② 里的「销售订单达成率 100%」在站点上算不出来。** ⚠️ **起草时把它当作可达**（评审第 1 轮指出）：
   `checks.py:175` 的 `settled = delivered_qty + approved_loss_quantity`，其中损耗来自
   `dataset.of("Loss Review")` —— **`Loss Review` 是本仓虚构的 DocType**（`documents.py:201` 造出来的），
   `Delivery Note` 还带着自定义字段 `xm_loss_review`（`documents.py:232`）。
   **ERPNext v15 里两者都不存在**，站点会算出 `per_delivered = 990/1000 = 99%`。
   给站点建这个 DocType 会造出一张物理表（**DDL**），而本 plan 逐字禁止发 DDL。处置见 Phase 1 的 `D2`。
7. **⚠️ `Sales Order` 与 `Work Order` 写在 `agenerp/seed/masters.py:95-144`，不在 `documents.py`。**
   ⚠️ **起草时按文件切 scope，会漏掉它们**（评审第 1 轮指出）：漏了 `Sales Order`，
   `Delivery Note` 的 `against_sales_order` 就悬空，达成率也没有订单可量。
   前置 plan 按**语义**切、明确把这两个归本 plan，本 plan 按语义接。
8. **⚠️ 站点没有单据级撤销手段，因此每一次测量都必须从冷起的空站点开始。**
   ⚠️ **起草时让 Phase 1 手工在同一站点上跑一遍链路、再让 Phase 3 在同一站点上测量**（评审第 1 轮指出），
   那会让 `Bin.actual_qty` 变成 2020 而不是 1010，承重判据**按构造不可达**；变异验证 ①② 同理不可执行。
   本仓已实测过的唯一复位手段是 `docker compose down -v` 冷起（plan `2026-08-21-2220-2`：
   `up -d --wait --wait-timeout 300` → exit 0、62 秒、建站幂等）。本稿把「冷起」写进每一次测量的前置。
9. **门禁提案给了三条拟断言与精确期望值**，但它是**提案文本不是测试代码**，采纳者是人。
   本 plan **不创建 `tests/gates/**` 下任何文件**。
10. **工作项 7 已有一条 L1 门禁**（`tests/gates/test_seed_dataset_absurdity.py`，6 条，从未进过
    `expected-red.txt`，断的是**生成器**）。**站点侧那一半仍无门禁**——本 plan 交付的行为
    **没有属于自己的门禁**，判据形态是 CLI 退出码 + `tests/unit` 单测 + 变异验证 + 独立关闭审计
    （§12.7 已写死的代偿控制，与 `tests/contracts` / Seed dataset 两行同一套）。照实登记，不粉饰。

## Goals

1. 把种子数据集的**业务单据链**装进活站点并提交，使站点自己产生库存与总账。
2. 交付一条**站点侧对账**命令：读回站点自己算出的成品仓 `Bin`，断言
   `actual_qty == 1010` 且 `stock_value == 6450.00`（容差 ¥0.01，期望值取自 `checks.py` 的 `EXPECTED_*`）——
   即门禁提案拟断言 ①，**这是整个工作项存在的理由**。
3. 覆盖拟断言 ③（两笔逾期可由站点上的 `status == "Overdue"` 查到），
   以及拟断言 ② 中**站点算得出来**的那几项（GL 借贷差额为 0、负库存条目数为 0、毛利与凭证差额 < ¥0.01）；
   **达成率那一项按 Phase 1 的 `D2` 裁定**，不预设它可达。
4. 实读并记录本仓 `frontend` 站点的 `valuation_method`，把 ¥6,450 的成立条件写清楚。
   **不宣称因此闭合 §12.8** —— 那条推断说的是冻结证据仓的站点，红线 6 下不可闭合。
5. 装载后整目录 live 门禁判定仍 exit 0。

## Non-Goals

- **不创建、不修改 `tests/gates/**` 下任何文件**（红线 1）；**不动 `tools/gates/expected-red.txt`**；
  **不代人采纳门禁提案**；**不把工作项 7 置 `done`**。
- **不给站点建 `Loss Review` DocType，也不建 `xm_loss_review` 自定义字段** —— 建 DocType 会造物理表（DDL）。
- 不实现单据的撤销/反冲（cancel + amend），不实现代码级 teardown。复位手段是 `down -v` 冷起。
- **不改任何一份期望值副本**：`agenerp/seed/model.py` 的数值常量、`agenerp/seed/checks.py` 的 `EXPECTED_*`、
  `tests/gates/test_seed_dataset_absurdity.py` 的常量，**在交付面上一个都不许改**。
  ⚠️ **唯一的例外，逐字写清（评审第 2 轮补，否则 R3 与本条直接打架）**：
  R3 的三条变异是**临时实验**，允许在实验期间改 `agenerp/seed/model.py` 的常量
  （① 改 `DELIVERY_QTY`、② 改 `SUBCONTRACT_FEE` 或 `RAW_RATE`），**但必须在 Phase 3 内复原**，
  关闭时 `git diff` 对该段**无输出**。
  **`tests/gates/**` 在任何情形下都不许改**（红线 1），因此实验期间 `--seed 42 --verify` 与
  L1 门禁 `test_seed_dataset_absurdity.py` **一并转红是预期的**——那正是这些判据有牙齿的证据，
  **不得据此放宽任何断言、也不得据此把哪条门禁加进 `expected-red.txt`**。
- **不把派生量当装载输入**：`BACKLOG_QTY` / `BACKLOG_VALUE` / `COGS_VALUE` / `GROSS_PROFIT`
  **不得出现在任何送往站点的载荷里** —— 把答案喂给站点再读回来，等于什么都没证明。
- 不动 `.github/workflows/**`、`missions/**`、`docs/masterplan/DECISIONS.md`；`STATE.md` 只追加。
- 不碰 `agenerp/oob.py` 的 `ALLOWED_CALLS`；不发任何 DDL。

## Task Route

- Type: `implementation-only change` + `verification or audit work`（Goals 2/3 的结果面是判据）
- Owner Docs: `docs/backlog/gate-proposal-seed-dataset.md`（三条拟断言与精确期望值 = 本 plan 的意图定义）·
  `docs/architecture/module-boundaries.md` §12.1 / §12.2 / §12.5 / §12.7 / §12.8 · `docs/context/project-context.md`
- Skill Selection Basis: `docs/skills/` 是 15 份 prompt + 1 份注册表，多为审计类，另有两份重构类，
  **没有一份覆盖「写新实现」**。实现相位 `Skill: none`；评审用 `plan-audit-prompt.md`，关闭审计用 `closure-audit-prompt.md`。

## Infrastructure And Config Prereqs

- **硬前置**：plan `2026-08-22-2107-1` 已关闭（写入面 + 主数据装载 + `agenerp/seedsite.py` 存在）。
- 活站点栈，端口 18080；env 与既有 L2 跑法相同，不新增变量：
  `AGENERP_SITE=frontend` · `AGENERP_SITE_URL=http://127.0.0.1:18080` · `AGENERP_ADMIN_PASSWORD=admin`
- **干净站点循环（本 plan 每一次测量与每一次变异实验的强制前置，命令原文写死在这里）**：
  ① `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down -v`
  ② `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`
  ③ `… python3 -m agenerp.seedsite --load-masters --site frontend`
  ④ `… python3 -m agenerp.seedsite --load-documents --site frontend`
  **每一轮实验都从 ① 开始，不在脏站点上测量。** 单轮成本约 1–2 分钟起栈 + 装载，可接受。
  ⚠️ **代价照实写（评审第 2 轮补）**：`down -v` 会**丢掉整站数据**，其中包括前置 plan
  `2026-08-22-2107-1` 在站点上留下的全部装载结果、以及本机站点上任何别的遗留状态。
  **这是预期的**（③④ 会重新装回来），但**首次 `down -v` 之前必须先跑一次
  `docker compose exec -T backend bench --site frontend backup` 并把字节数记进 `docs/logs/`**，
  否则一次误操作就没有任何回头路。
- **回滚策略，逐字说清（Protected Areas 对动活站点写路径的 plan 的硬要求）**：
  本 plan **不交付任何代码级回滚**。**本次改动之后，站点侧回滚仍然只能手工做**：
  提交过的 ERPNext 单据只能由**人**手工 cancel/amend，或用上面那条 `down -v` 冷起丢掉整站数据，
  或事前 `docker compose exec -T backend bench --site frontend backup` 事后由人 `bench restore`。
  **`restore` 不在 `agenerp/oob.py` 的 `ALLOWED_CALLS` 内，本 plan 不加它。**
  ⚠️ **`submit`（`docstatus` 0→1）本身是不可逆动作**（没有 cancel 就回不去），
  其授权归属按前置 plan D3 新增的「对活站点的非破坏性写」行读，**并同时满足「破坏性写」行那条
  「对『错了能不能回来』说话」的 Required Evidence** —— 本段即是那条陈述。
- 无新第三方依赖。

## Execution Plan

### Phase 1 - 先在**隔离探针**上把链路跑通，再定单据链（Explore 全部结论必须先于 Decision）

Status: completed
Targets: `docs/logs/` · `docs/masterplan/STATE.md`（只追加）
Skill: `none`
Prereqs: plan `2026-08-22-2107-1` 已关闭

- [x] `Explore` **E1 · 在隔离探针上跑通链路，不碰 `XM-LACE-1000`**。
      ⚠️ **隔离是硬要求**（评审第 1 轮指出）：探索必须用一个**从不被 `model.py` 引用**的探针物料 +
      探针仓库（如 `XM-PROBE-CHAIN` / `XM 探针仓 - XM`），因为站点没有单据撤销手段，
      在真物料上试跑会让 Phase 3 的 `Bin` 变成 2020 而不是 1010，承重判据**按构造不可达**。
      在探针上手工走通：期初原料入库 → 自制批入库 → 外协批入库 → 发货 → 开票，
      **每一步的原样输出记进 `docs/logs/`**，重点记站点算出的 `Bin.stock_value` 分层结果。
      - Skill: `none`
- [x] `Explore` **E2 · 计价方法实读**：读回 `Stock Settings.valuation_method` 与 `Item.valuation_method`，
      原样输出记进 `docs/logs/`。**只记不改**——前置 plan 的 `ensure_doc` 逐字「不改已存在的文档」，
      本 plan 也不交付 `update`。若实读值不是 FIFO，**照实记录并进入 D1 的备选评估**，
      不得为了让数对上而悄悄改站点配置又不写出来。
      - Skill: `none`
- [x] `Explore` **E3 · 拟断言 ② 的四项指标各自怎么查**：GL 借贷差额、负库存条目数、
      毛利与凭证差额、销售订单达成率，每项落到一条具体的站点读取路径。
      **查不出来的必须当场说出来**，不许留到 Phase 3 才发现。
      - Skill: `none`
- [x] `Explore` **E4 · 单据的幂等键**：实测 `Stock Entry` / `Delivery Note` / `Sales Invoice` /
      `Purchase Invoice` / `Sales Order` 在显式给 `name` 时站点是否采纳（`names.py` 给的是
      `MAT-STE-2026-00001` 这类命名序列形状）。**这一条决定 `--load-documents` 的幂等靠什么判**。
      - Skill: `none`
- [x] `Decision` **D1 · 用哪条单据链复现 FIFO 分层**（依赖 E1/E2）。备选：
      (a) 完整制造链（`Work Order` + `Subcontracting Order` + 真实 BOM 消耗，站点自己汇总成本）；
      (b) 收窄链（`Stock Entry` 直接按批次价入库 + `Delivery Note` 出库 + 两张发票造逾期）。
      **判定依据两条，按序**：① 站点自己算出 ¥6,450 且 E3 认定可查的指标全绿；
      ② **在 ① 成立的前提下，选「站点自己承担成本汇总最多」的那条链**。
      ⚠️ **② 是评审第 1 轮补进来的**：(b) 把 ¥5.00 / ¥6.40 当**输入**喂给站点，
      站点只算了 FIFO 分层，而 §12.1 里**产生**这两个费率的成本汇总（120 Kg × ¥35 + 600 分钟 ÷ 60 × ¥80；
      ¥4,200 + ¥2,200）完全没被站点验证过——那是比 Goals 宣称的弱得多的结论。
      `Decision` 记录必须**逐字列出**：站点算了 §12.1 的哪几段、哪几段是喂进去的；
      没被站点算的部分作为具名残余风险进 owner doc 与 `## Deferred But Adjudicated`。
      - Skill: `none`
- [x] `Decision` **D2 · 拟断言 ② 的达成率那一项怎么办**（依赖 E3 与 Current Baseline 第 6 条）。备选：
      (a) 给站点建 `Loss Review` DocType + `xm_loss_review` 自定义字段 —— **否决**，建 DocType 造物理表 = DDL，
      本 plan 逐字禁止；且新增 DocType 会改变 `schema_drift` 的观测面，可能弄红既有门禁；
      (b) 把达成率按站点口径重定义为 `Sales Order.per_delivered`（= 99%）并把断言从 100% 改成 99% ——
      **否决**，那是改判据去迁就实现，且会让「已审批损耗」这条业务语义在站点侧彻底消失；
      (c) **采纳（除非 E3 给出第三条路）**：本 plan 的 `--verify-site` 只覆盖 ② 中**站点算得出来**的三项，
      达成率那一项**明确移出本 plan 结果面**并进 `## Deferred But Adjudicated`，
      重开事件写死为「**人裁定是否允许为 `Loss Review` 建 DocType / 自定义字段时**」。
      **同时更新门禁提案**：拟断言 ② 的四项里有一项在当前口径下站点算不出来，这一事实必须写进提案，
      否则人采纳提案时会拿到一条注定红的门禁。
      - Skill: `none`
- [x] `Decision` **D3 · 「站点算出来的数与期望对不上」的固定处置**（本 plan 最可能的失败模式，必须在动手前写死）。
      ⚠️ **起草时只在 Non-Goals 里指了一句「处置见 Phase 3」而 Phase 3 并没有这一条**（评审第 1 轮指出），
      此处补齐并前置到第一次接触点：
      **处置逐字** —— ① 记录站点实得值与全部 `Bin` / `Stock Ledger Entry` 行的原样输出；
      ② 按红线 5 追加进 `STATE.md` §3；③ 本 plan 置 `deferred` 并在文件头写明重开条件；
      ④ 用 Infrastructure 的干净站点循环复位并复跑一次确认基线仍绿。
      **同时被禁止的做法，逐条列名，不许挑一条做**：改 `model.py` 的数值常量 · 改 `checks.py` 的 `EXPECTED_*` ·
      在 `--verify-site` 里写死一个新的期望字面量 · 放宽 `MONEY_TOLERANCE` ·
      改站点的 `valuation_method` 去凑数 · **换一条链直到数对上却不记录被否掉的链**
      （§12.2 逐字：「届时应改的是本节而不是把断言放松」）。
      - Skill: `none`
- [x] `Proof`：E1–E4 的原样输出与 D1–D3 的结论按红线 5 追加进 `STATE.md` §2（含命令原文 + 退出码 + sha），
      并写进 `docs/logs/2026/08-22.md`。
      - Skill: `none`

Exit Criteria:

- [x] E1 全程在**隔离探针**上完成；`docs/logs/` 有每一步原样输出，且**站点算出的 `stock_value` 已得到一个具体数**
- [x] E2 的 `valuation_method` 实读值有留痕；E3 逐项给出读取路径或「查不出来」的明确结论；E4 给出幂等键结论
- [x] D1 记录含「站点算了哪几段成本、哪几段是喂进去的」的逐字列举
- [x] D2 有结论，且门禁提案已按结论更新（若采纳 (c)）
- [x] D3 的固定处置与禁止清单逐字落在本 plan 内
- [x] `docs/logs/` 更新，`STATE.md` §2 追加证据行

### Phase 2 - 单据装载段与站点侧对账命令

Status: completed
Targets: `agenerp/seedsite.py` · `agenerp/site.py` · `tests/unit/`
Skill: `none`
Prereqs: Phase 1（链路必须先在隔离探针上跑通，D1/D2/D3 必须先有结论）

- [x] `Add`：`SiteClient.submit_doc(doctype, name) -> dict` —— 把 `docstatus` 由 0 推到 1，
      具体路径以 E1 实测为准。失败不吞、非 2xx 抛 `SiteError`。
      **方法名含 `WRITE_VERBS` 里的 `submit`，必须同时登记进 `tests/unit/test_site_client.py` 的
      `WRITE_METHOD_ALLOWLIST`**（否则守卫会红，这正是它该有的行为）。
      - Skill: `none`
- [x] `Add`：`agenerp/seedsite.py` 的单据段 —— 按 D1 选定的链路装载并提交。
      **覆盖面逐条列名**：`Sales Order`（来自 `masters.py:95`）· `Work Order`（`masters.py` —— 若 D1 选 (b) 则显式排除并写明）·
      `Stock Entry` · `Subcontracting Order` / `Subcontracting Receipt` · `Delivery Note` ·
      `Sales Invoice` · `Purchase Invoice`。**`Loss Review` 按 D2 处理，不建 DocType。**
      依赖顺序写死在装载器里；幂等键按 E4 结论选。
      - Skill: `none`
- [x] `Add`：CLI `python3 -m agenerp.seedsite --load-documents --site <site>` —— 幂等
      （已提交过的单据命中读回分支，不重复提交），失败即停退非 0，不留半装状态。
      **`--seed 42 --verify` 与 `--load-masters` 的既有行为逐字节不变。**
      - Skill: `none`
- [x] `Add`：CLI `python3 -m agenerp.seedsite --verify-site --site <site>` —— **站点侧对账**。
      **期望值一律 `from agenerp.seed.checks import EXPECTED_*` 取**，
      **不得在本模块里写任何新的期望字面量**（Current Baseline 第 3 条：`checks.py` 才是判官侧那份副本）。
      输出要求：成功与失败**都**必须打出**带出处的实得值与期望值**，形如
      `Bin(XM-LACE-1000, XM 成品仓 - XM).stock_value = <站点实得> / expected = <checks.EXPECTED_BACKLOG_VALUE>`。
      ⚠️ **只打「通过」或只回显期望值不算数**（评审第 1 轮指出：那样的输出用 grep 就能伪造）。
      - Skill: `none`
- [x] `Proof`（纯逻辑半）：`tests/unit/` 补单据映射与对账判定的单测（FakeTransport），
      含一条「`--verify-site` 的期望值确实来自 `checks.EXPECTED_*` 而非本地字面量」的结构断言。
      `python3 -m pytest tests/unit -q` → exit 0。
      - Skill: `none`

Exit Criteria:

- [x] 三个 CLI 面（`--load-masters` / `--load-documents` / `--verify-site`）各自行为落地并互不干扰
- [x] `submit_doc` 已登记进 `WRITE_METHOD_ALLOWLIST`，守卫仍绿且仍有牙齿
- [x] `--verify-site` 的期望值来自 `checks.EXPECTED_*`，有单测把这条结构约束钉住
- [x] `python3 -m pytest tests/unit -q` → exit 0；`ruff check agenerp tests/unit tests/contracts` → exit 0
- [x] `python3 -m agenerp.seed --seed 42 --verify` → exit 0（A 半未被打坏）
- [x] `docs/logs/` 更新

### Phase 3 - 从干净站点实跑：站点自己算出 1,010 米 / ¥6,450

Status: completed
Targets: 活站点 · `docs/logs/` · `docs/masterplan/STATE.md`（只追加）
Skill: `none`
Prereqs: Phase 2

- Item Types: `Proof`-heavy（5/5 项为 `Proof`）

- [x] `Proof` **R1 · 基线轮**：跑一次 Infrastructure 的干净站点循环 ①②，
      然后在**装载前**跑一次整目录 live 判定取本机基线（命令见 R5）→ 必须 exit 0。
      随后 ③ `--load-masters` → exit 0，④ `--load-documents` → exit 0；
      **`--load-documents` 原样再跑一次** → exit 0 且新建计数为 0（幂等的判据是第二跑的计数）。
      - Skill: `none`
- [x] `Proof` **R2 · 承重判据**：`… python3 -m agenerp.seedsite --verify-site --site frontend` → **exit 0**，
      输出含**带出处标注**的站点实得 `actual_qty` / `stock_value` 与 `checks.EXPECTED_*` 的期望值。
      **若不等，走 Phase 1 的 D3 固定处置，一个字不许绕。**
      - Skill: `none`
- [x] `Proof` **R3 · 变异验证，每条都从干净站点重来**。
      ⚠️ **「先复位再变异」是评审第 1 轮补的硬要求**：站点没有单据撤销手段，
      在已装载的站点上追加一张 980 米的发货得到的是 `Bin = 30`，不是 1020——原写法的 ①② 根本跑不出声称的红。
      三条实验，**每条各自完整跑一遍干净站点循环 ①②③**，再按下述改动装载。
      ⚠️ **变异落在哪里，说清楚**：①② 改的是 `agenerp/seed/model.py` 的常量
      （`DELIVERY_QTY` / `SUBCONTRACT_FEE`），这是 Non-Goals 里写明的**唯一例外**（临时实验，Phase 3 内复原）。
      实验期间 `--seed 42 --verify` 与 L1 门禁一并转红是**预期**，**不许**为此改 `tests/gates/**` 或加名单。
      三条实验：
      ① 发货量由 990 改成 980 → `--verify-site` 必须红在数量断言，且打出站点实得 `1020` 与期望 `1010`；
      ② 外协批入库价改掉 → 必须红在 `stock_value`，且打出站点实得金额与期望 `6450.0`；
      ③ 把 `--verify-site` 的 `stock_value` 断言删掉 → `tests/unit` 必须转红并点名对应测例（纯逻辑，不需起站点）。
      **每条都要记：改动内容 · 命令原文 · 退出码 · 站点读回的 `Bin` 原样输出 · 复原后的复跑退出码。**
      ⚠️ **代码复原不等于站点复原**：①② 复原后必须再跑一次干净站点循环并复跑 R2 回到 exit 0。
      - Skill: `none`
- [x] `Proof` **R4 · 计价条件留痕**：把 E2 实读的 `valuation_method` 与 R2 的实得值并排记进 `docs/logs/`，
      写清「¥6,450 是在**这个** `valuation_method` 下成立的」。**不写「§12.8 已闭合」**（Goals 4）。
      - Skill: `none`
- [x] `Proof` **R5 · 不弄脏既有判据**：装载前（R1 第二步）与装载后各跑一次
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 tools/gates/check_expected_red.py`
      → 两次都必须 exit 0 且逐字 `门禁 19 项：红 0，绿 19，跳过 0`。
      **固定处置（若装载后转红）**：记录原样输出 → 按红线 5 追加进 `STATE.md` §3 →
      本 plan 置 `deferred` 并写明重开条件 → 用干净站点循环复位并复跑确认基线仍绿
      → **不放宽判据、不改 `tests/gates/**`、不猜根因**。
      - Skill: `none`

Exit Criteria:

- [x] R2 在干净站点上 exit 0，输出含带出处标注的站点实得值与 `checks.EXPECTED_*` 期望值
- [x] `--load-documents` 连跑两次均 exit 0，第二次新建计数为 0
- [x] R3 三条变异各有「干净站点 → 变异 → 转红 → 点名 → 复原（含站点复位）→ 转绿」的完整留痕
- [x] R4 的 `valuation_method` 与实得值并排留痕，且**未出现「§12.8 已闭合」这类陈述**
- [x] 装载前后两次整目录 live 判定均 exit 0
- [x] `docs/logs/` 更新，`STATE.md` §2 追加证据行

### Phase 4 - owner doc 对齐 + 把门禁提案交回给人

Status: completed
Targets: `docs/architecture/module-boundaries.md` · `docs/context/project-context.md` · `docs/backlog/gate-proposal-seed-dataset.md` · `docs/backlog/p0-foundation-roadmap.md` · `docs/logs/`
Skill: `none`
Prereqs: Phase 3

- [x] `Fix`：`module-boundaries.md` §12.7 按本 plan 实际交付**就地改准** ——
      站点侧断言现在有**可执行形式**（`--verify-site` 的退出码），**但它不是门禁**。
      **不得写成「工作项 7 已有站点侧门禁」——那是假的。**
      （§12.7 里「仍然没有绑定的门禁测试」那句由前置 plan 改准，本 plan 不重复改。）
      - Skill: `none`
- [x] `Fix`：`module-boundaries.md` §12.8 就地补一条**本仓站点**的实读事实
      （`valuation_method` = E2 实读值，¥6,450 在该配置下由站点实算成立），
      **并明确保留**「冻结证据仓那个站点的计价方法仍是推断」这一条 —— 红线 6 下它在本仓不可闭合。
      ⚠️ **不许把这条推断写成已闭合**（评审第 1 轮指出：那会往 owner doc 里写进一条假的关闭）。
      - Skill: `none`
- [x] `Add`：`module-boundaries.md` 新增小节「单据装载与站点侧对账在本仓的落点」，含：
      D1 选定的单据链与被否选项、**站点算了 §12.1 哪几段成本 / 哪几段是喂进去的逐字列举**、
      幂等口径、干净站点循环为什么是强制前置、D2 对达成率的裁定、以及无 teardown 的代价。
      - Skill: `none`
- [x] `Add`：`project-context.md` 验证命令表新增一行「种子数据站点侧对账」，
      含完整 env、端口 18080、**干净站点循环是前置**、以及「不在 `commands.test` 里」四条口径。
      本行触发的「验证命令表整体臃肿」重开事件，处置沿用前置 plan 已作出的裁定，见 `## Deferred But Adjudicated`。
      - Skill: `none`
- [x] `Fix`：更新 `docs/backlog/gate-proposal-seed-dataset.md` —— 逐条标注三条拟断言的现状：
      ① 与 ③ 「实现已就绪，站点上实测通过，期望值 = <实测值>」；
      ② **按 D2 的裁定拆开标注**，其中达成率那一项要写明「当前口径下站点算不出来，原因是 `Loss Review` 是本仓虚构 DocType」，
      **否则人采纳提案时会拿到一条注定红的门禁**。写明人采纳只差带 trailer 的一次提交。
      **`Status: proposed` 不改，不代人采纳。**
      - Skill: `none`
- [x] `Add`：往 roadmap 工作项 7 处**追加**一条现状行（追加，不改写既有行）：
      B 半两段均已落地、判据形态是 CLI 退出码而非门禁、达成率那一项的裁定、
      **工作项 7 仍保持 `planned`** 及其真实卡点（L1 门禁从未进过名单，「划掉」没有对象）。
      **不自行改工作项状态值**——状态由引擎在 closure 审计通过后回写。
      - Skill: `none`

Exit Criteria:

- [x] §12.7 已改准且未出现「工作项 7 已有站点侧门禁」这类假陈述
- [x] §12.8 补了本仓站点的实读事实，且**证据仓那条推断仍明确开着**
- [x] 新增小节含单据链裁定与「站点算了哪几段成本」的逐字列举
- [x] `project-context.md` 新增一行，四条口径齐备
- [x] 门禁提案三条拟断言逐条标注现状，达成率那项的不可达原因已写明，`Status` 未改
- [x] roadmap 只有追加：`git diff --numstat` 对该文件删除列为 `0`
- [x] `docs/logs/` 更新

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，agent `a463f30dea948c4aa`）——
  9 条 blocking。要点：① Phase 1 的手工探索会污染 Phase 3 要测量的同一站点，
  在无撤销手段下让 `Bin` 变 2020，承重判据**按构造不可达**；② 「站点算出别的数」这个最可能的失败模式
  **没有任何处置**，Non-Goals 里那句「处置见 Phase 3」指向一条不存在的分支；
  ③ 「`model.py` 是期望值唯一落点」是**假陈述**，`checks.py:23-24` 有独立第二份、门禁里还有第三份，
  防作弊闸守错了文件；④ 变异验证 ①② 在无站点复位手段时不可执行，是仪式；
  ⑤ 拟断言 ② 的达成率靠虚构 DocType `Loss Review`，站点上算不出来，且 `Sales Order`/`Work Order`
  落在两个 plan 的 scope 缝里；⑥ Goal 4「把 `valuation_method` 变直证」是循环论证
  （自己配的值读回来证明不了证据仓那个站点），且 `ensure` 不改已存在文档、没有 `update` 面，「显式设定」无实现路径；
  ⑦ Phase 4 命令执行者保留「工作项 7 没有门禁」这句已过期的话；
  ⑧ 单据链 `Decision` 的唯一判据是「哪条能凑出期望值」，且被推荐的收窄链把成本汇总整段喂给站点；
  ⑨ `Fix | Follow-up` 与自己的 Closure Gate 冲突。
  **全部 9 条已在本稿逐条落地**：①→干净站点循环写进 Infrastructure 并成为每次测量/实验的强制前置，E1 改到隔离探针上；
  ②→新增 `D3` 固定处置 + 六条具名禁止做法，前置到第一次接触点；③→Current Baseline 第 3 条改写，
  `--verify-site` 强制从 `checks.EXPECTED_*` 取值，Closure Gate 改守三份副本；④→R3 三条实验各自从干净站点重来，
  并写明「代码复原不等于站点复原」；⑤→`D2` 三备选裁定 + Phase 2 覆盖面逐条列名 + 提案必须写明不可达原因；
  ⑥→Goals 4 改写为「实读并记录」，删掉「直证/闭合」，§12.8 明确保留证据仓那条推断；
  ⑦→Current Baseline 第 10 条与 Phase 4 改准；⑧→`D1` 判定依据改成两条（先可行、再取站点承担成本汇总最多的），
  并要求逐字列出哪几段是喂进去的；⑨→改标 `Fix`。
  **同时采纳的非阻塞更正**：`Bin`/`GL Entry`/`SLE` 的构造归属（`ledger.py`）、`valuation_method` 项由 `Decision` 改为 `Explore`、
  单据自动命名对幂等的威胁（新增 E4）、`submit` 的授权归属说明、`project-context` 臃肿条目的指向、
  以及退出判据要求「带出处标注」而非可被 grep 伪造的回显。
- Independent draft review iteration 2: **needs revision（两条窄修正）**（同一独立子代理，agent `a463f30dea948c4aa`，
  重新从盘上读全文并对 5 处实读复核）—— 逐条判定：**9 条 blocking 中 7 条 `RESOLVED`，2 条 `PARTIAL`**
  （第 4 条「变异是仪式」与第 8 条「D1 只按能否凑出期望值来选链」），另**新增 2 条 blocking**：
  **B-1**：R3 的变异 ①② 无处可落——`DELIVERY_QTY` / `SUBCONTRACT_FEE` 正是 Non-Goals 里「一个都不许改」的常量，
  执行者会撞上一条正面冲突，然后要么跳过变异、要么自行重新解释规则，两条都会毁掉本 plan 赖以成立的牙齿。
  **B-2**：派生量零命中闸只守了四个**终值**常量（`BACKLOG_*` / `COGS_VALUE` / `GROSS_PROFIT`），
  漏了 `INHOUSE_RATE`（¥5.00）/ `SUBCON_RATE`（¥6.40）/ `INHOUSE_VALUE` / `SUBCON_VALUE`
  ——而 D1 备选 (b) 恰恰把这四个当入库价喂给站点，于是闸子会在「站点被喂了除最后一次减法之外的一切」时照样变绿，
  正好放过 D1 判定依据 ② 要暴露的弱点。
  **两条均已逐字落地**：B-1 → Non-Goals 增设唯一例外（临时实验、Phase 3 内复原、关闭时 `git diff` 无输出，
  并写明实验期间 `--seed 42 --verify` 与 L1 门禁一并转红是**预期**、不得据此放宽任何断言或改 `tests/gates/**`），
  R3 处同步写明变异落点；B-2 → Closure Gates 拆成两条，第二条要求对那四个费率常量**二选一且必须选定**
  （零命中，或如实登记「站点未承担 §12.1 哪几段成本汇总」并禁止把结论写成「站点验证了 §12.1」）。
  **同时采纳的非阻塞更正**：`Infrastructure` 补上「`down -v` 会丢掉前置 plan 在站点上的全部装载结果，
  首次冷起前必须先 `bench backup` 并记字节数」。
  评审员另行确认为**无问题**的三处：干净站点循环安全且充分（`down -v` 限于本仓 compose project，
  `create-site` 服务会自愈，且 R1 在冷起**之后**重取 19 绿基线而不是沿用旧结论，顺序正确）；
  D2 的 (c) 让拟断言 ② 保持自洽（Goals 3 已预先只承诺三项，提案更新是必做的 `Fix`，没有断言被静默丢弃）；
  R2 的退出判据不可被 grep 伪造（要求带出处标注、点名 `Bin` 与 `checks.EXPECTED_*` 出处）。**无红线越界。**
- Independent draft review iteration 3: **accept**（B-1 / B-2 均为评审员给出确定修法的窄修正，逐字落地，
  未引入新结果面；`PARTIAL` 的第 4、8 两条按评审员原话「issues 4 and 8 close with them」随之关闭）

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（§12.7 / §12.8 / 新增小节 / `project-context.md` / 门禁提案 / roadmap）
- [x] verification has run：`python3 -m pytest tests/unit -q` · `ruff check agenerp tests/unit tests/contracts` ·
      `python3 -m agenerp.seed --seed 42 --verify` · 干净站点循环 · `--load-documents`（连跑两次）· `--verify-site` ·
      装载前后两次 live `python3 tools/gates/check_expected_red.py` · R3 三条变异验证
- [x] scoped verification is not conflated with full verification —— 本仓无全量套件，
      上列命令全部 scoped，关闭记录必须逐字写「verification scope limited」
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [x] closure audit was independent
- [x] closure evidence exists in files
- [x] **`tests/gates/**` 与 `tools/gates/expected-red.txt` 一个字节未改**
- [x] **三份期望值副本一个未改**：`git diff` 对 `agenerp/seed/model.py` 的数值常量段、
      `agenerp/seed/checks.py` 的 `EXPECTED_*` 段、`tests/gates/test_seed_dataset_absurdity.py`
      **均无输出**；且 `--verify-site` 里**没有新的期望值字面量**（结构单测已钉住）
- [x] **派生量未被当作装载输入**：`BACKLOG_QTY` / `BACKLOG_VALUE` / `COGS_VALUE` / `GROSS_PROFIT`
      在 `agenerp/seedsite.py` 里**零命中**（`grep` 可判）
- [x] **单位成本类派生量的处置是显式的，不是默认放行**（评审第 2 轮补）：
      `INHOUSE_RATE`（¥5.00）/ `SUBCON_RATE`（¥6.40）/ `INHOUSE_VALUE` / `SUBCON_VALUE`
      **二选一，且必须选定**：(i) 在 `agenerp/seedsite.py` 里**零命中**（站点自己汇总出成本）；
      或 (ii) 若 D1 选了收窄链、它们确实作为入库价喂进了站点，则
      **D1 记录与 owner doc 新增小节必须逐字登记「站点未承担 §12.1 的哪几段成本汇总」**，
      且门禁提案与 roadmap 追加行都不得把结论写成「站点验证了 §12.1」。
      ⚠️ **只守四个终值常量而放任这四个费率常量，会让闸子在「站点被喂了除最后一次减法之外的一切」时照样变绿**
      —— 那恰好是 D1 判定依据 ② 要暴露的弱点
- [x] **未发任何 DDL**，未新建 DocType 或自定义字段
- [x] **工作项 7 未被置 `done`**

## Deferred But Adjudicated

### 拟断言 ② 的「销售订单达成率 100%」在当前口径下站点算不出来

- Classification: `out-of-scope improvement`（**人动作项**）
- Why Not Blocking Closure: 它依赖本仓虚构的 `Loss Review` DocType 与 `xm_loss_review` 自定义字段；
  给站点建它们会造物理表（DDL），本 plan 逐字禁止，且会改变 `schema_drift` 的观测面。
  处置不是静默丢弃——D2 要求把这条不可达**写进门禁提案**，免得人采纳时拿到一条注定红的门禁。
- Successor Required: `no`（**人动作**）—— 重开事件：**人裁定是否允许为 `Loss Review`
  建 DocType / 自定义字段时**，或**人给出一条站点可表达的达成率口径时**。

### §12.1 里没被站点承担的那几段成本汇总

- Classification: `watch-only residual`
- Why Not Blocking Closure: D1 要求逐字列出站点算了哪几段、哪几段是喂进去的，
  所以结论的**强度**是被写明的，不是被夸大的。
- Successor Required: `no` —— 重开事件：**P1/P2 需要站点自己承担完整成本汇总时**，
  或**有人引用「站点验证了 §12.1」这个比实际更强的说法时**。

### 冻结证据仓那个站点的 `valuation_method` 仍是推断

- Classification: `watch-only residual`
- Why Not Blocking Closure: 证据仓已冻结在一个 sha 上、只读（红线 6），本仓无法对它取新证。
  本 plan 只把**本仓站点**的实读值补上，不宣称闭合 §12.8 的原推断。
- Successor Required: `no` —— 重开事件：**人解冻证据仓或另行提供其站点配置的直接证据时**。

### 三条断言的**门禁形态**仍未落地（只有 CLI 形态）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 新建 `tests/gates/test_seed_dataset_backlog.py` 在红线 1 内，**只有人能做**。
  本 plan 的处置是把提案更新到「实现已就绪、期望值已实测、②的一项不可达及其原因」——
  把人要做的动作压缩到一次提交，而不是静默丢弃。
- Successor Required: `no`（**人动作**）—— 重开事件：**人出具 `Gates-Change-Approved-By:` trailer 采纳提案时**。

### 装进站点的单据无法撤销（无 teardown / 无 cancel）

- Classification: `watch-only residual`
- Why Not Blocking Closure: `## Non-Goals` 显式排除；代偿是干净站点循环（`down -v` 冷起），
  它已被本仓实测过且被本 plan 定为每次测量的强制前置。
- Successor Required: `no` —— 重开事件：**门禁开始依赖「站点上没有种子单据」这个前提时**，
  或**人要求把种子站点做成可反复重置的 fixture 时**。

### 站点侧对账不覆盖「装载器本身报错了但对账仍绿」的假绿入口

- Classification: `watch-only residual`
- Why Not Blocking Closure: 与 `schema_drift` 那条已登记的假绿面同一类问题。
  代偿是 R3 的三条变异验证 + `--load-documents` 幂等第二跑的新建计数 + 失败即停退非 0。
- Successor Required: `no` —— 重开事件：**第一次出现「装载失败而 `--verify-site` 仍退 0」时**。

### `docs/context/project-context.md` 验证命令表整体臃肿

- Classification: `optimization candidate`
- Why Not Blocking Closure: 该条由 plan `2026-08-22-1041-1` 登记、由本批第一个 plan
  `2026-08-22-2107-1` 就地裁定为「只新增行、不重构结构」。本 plan 沿用同一裁定，不重复裁。
- Successor Required: `no` —— 重开事件：**人明确裁定要重构该表时**。

### 工作项 7 仍卡在「从预期红名单划掉」这条 `done` 定义上

- Classification: `watch-only residual`
- Why Not Blocking Closure: 已登记的人裁定题（`docs/backlog/needs-human-expected-red-handoff.md`）。
  ⚠️ **不得把理由写成「工作项 7 没有门禁」**——它有一条 L1 门禁，只是那条门禁从未进过名单，
  「划掉」这个动作没有对象。本 plan 关闭时工作项 7 保持 `planned`。
- Successor Required: `no` —— 重开事件：**人从那份 handoff 文档的候选处置里选定时**。

## Closure

Status Note: **四个 Phase 全部执行完毕，承重判据在干净站点上成立。**

**承重判据的原样输出**（`python3 -m agenerp.seedsite --verify-site --site frontend` → **exit 0**）：

- `✅ Bin(XM-LACE-1000, XM 成品仓 - XM).actual_qty = 1010.00 / expected = 1010.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_QTY）`
- `✅ Bin(XM-LACE-1000, XM 成品仓 - XM).stock_value = 6450.00 / expected = 6450.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_VALUE）`
- 另七项全过；`站点侧对账：9 项，通过 9，失败 0`。

**verification scope limited** —— 本仓无全量套件，下列命令**全部 scoped**，
其中五条活站点命令 `GATE_VERIFY` 复跑不到：

| 命令原文 | 退出码 |
|---|---|
| `python3 -m pytest tests/unit -q` | **0**（248 → **283 passed**） |
| `ruff check agenerp tests/unit tests/contracts` | **0** |
| `python3 -m agenerp.seed --seed 42 --verify` | **0**（A 半未被打坏） |
| `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down -v` | **0**（本 plan 共跑 4 次） |
| `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300` | **0**（59.1 秒） |
| `… python3 -m agenerp.seedsite --load-masters --site frontend` | **0**（`新建 40 / 已存在 0`） |
| `… python3 -m agenerp.seedsite --load-documents --site frontend`（第一跑） | **0**（`新建 17 / 已存在 0 / 提交 11`） |
| `… python3 -m agenerp.seedsite --load-documents --site frontend`（原样第二跑） | **0**（`新建 0 / 已存在 17 / 提交 0`） |
| `… python3 -m agenerp.seedsite --verify-site --site frontend` | **0**（9 项全过） |
| `… AGENERP_LIVE=1 … python3 tools/gates/check_expected_red.py`（装载**前**） | **0**（`门禁 19 项：红 0，绿 19，跳过 0`） |
| `… AGENERP_LIVE=1 … python3 tools/gates/check_expected_red.py`（装载**后**） | **0**（同上逐字） |

**R3 三条变异验证，各自「干净站点 → 变异 → 转红 → 点名 → 复原（含站点复位）→ 转绿」**：
① `DELIVERY_QTY` 990→980 → `--verify-site` **exit 1**，`❌ …actual_qty = 1020.00 / expected = 1010.00`；
② `SUBCONTRACT_FEE` 2200.0→2100.0 → **exit 1**，数量仍 `1010.00` 而 `❌ …stock_value = 6350.00`；
③ 删掉 `--verify-site` 的 `stock_value` 断言 → `tests/unit` **4 failed, 279 passed**，点名四条测例。
实验期间 `--seed 42 --verify` 与 L1 门禁 `test_seed_dataset_absurdity.py` 一并转红，**这是预期的**；
**没有据此放宽任何断言，也没有把任何门禁加进 `tools/gates/expected-red.txt`**。
复原后 `git diff --stat agenerp/seed/` **无输出**，`283 passed`。

**照实登记、不粉饰的四条**：

1. **本 plan 交付的行为没有属于自己的门禁。** 判据形态是 CLI 退出码，`GATE_VERIFY` 与 CI 都复跑不到。
   站点侧那三条 L2 断言仍是提案文本（`Status: proposed`，采纳者是人）。
2. **拟断言 ② 的「销售订单达成率 100%」在当前口径下站点算不出来**（`per_delivered` 实测 99.0），
   已按 D2 (c) 移出结果面并写进门禁提案。
3. **外协批走的 DocType 不是 `Subcontracting Receipt`**，是 `Stock Entry(Manufacture)` + 服务费附加成本。
4. **不宣称闭合 §12.8**：那条推断说的是冻结证据仓那个站点（红线 6），本仓取不到它的新证。
5. **「9 项」是打印行数，独立约束只有 8 条**（第 7 项「毛利」= 第 5 项 − 第 6 项，
   而 `EXPECTED_GROSS_PROFIT` 本身就是 `18612 − 4950`，故它不可能在前两项都绿时单独发红）。
   由独立关闭审计当场指出，已就地记进 §12.10。**引用「9 项全过」时不得读成 9 条独立判据。**
6. **`EXPECTED_RECEIVABLE_OVERDUE` 被复用在了它声明含义之外的一处**（`checks.py` 声明它是
   「应收**逾期**合计」，而第 5 项拿它当「GL 收入贷方合计」的期望值；两者此刻相等只因那张发票
   100% 未收款）。**没有违反本 plan 的要求**（要求是不得引入新的期望值字面量，此处确实没有），
   但打给操作者的 `出处` 标注比实际含义窄。同样由独立关闭审计指出，已记进 §12.10。
7. **「派生量零命中」的可判形式是 `M.<NAME>` / `model.<NAME>`，不是裸名**：裸名 `grep` 在
   `agenerp/seedsite.py` 里**有命中**（三处 `CH.EXPECTED_*`，全部在**对账侧**，那正是本模块该做的事）。
   **装载输入侧的 `M.<NAME>` 命中数实测为 0。** 下面那条 Closure Gate 的文字**未改**
   （改判据去迁就实现是本 plan 逐字禁止的），此处只把它的可判读法记准。

Closure Audit Evidence:

- Auditor / Agent: **独立子代理，fresh session，agent `a091942e83e9a237d`** —— **非本 plan 的执行者**。
  方法是不读执行者的结论当证据，在活仓与活站点（18080）上逐条复跑，并自选变异做证伪尝试。
- Evidence: 审计复跑取得的退出码（与执行者所记一致）：`python3 -m pytest tests/unit -q` → **0**
  （`283 passed in 0.66s`）· `ruff check agenerp tests/unit tests/contracts` → **0** ·
  `python3 -m agenerp.seed --seed 42 --verify` → **0** · `… --verify-site --site frontend` → **0**
  （`站点侧对账：9 项，通过 9，失败 0`，两条 `Bin` 行逐字一致）·
  `… --load-documents --site frontend`（**第三跑**）→ **0**，`合计：新建 0 / 已存在 17 / 提交 0`
  —— **幂等在审计侧独立复现** · `AGENERP_LIVE=1 … check_expected_red.py` → **0**，`门禁 19 项：红 0，绿 19，跳过 0`。
  红线复核：五条禁区路径 `git status --porcelain` **空**；`STATE.md` 删除列 **0**；
  `git diff --stat agenerp/seed/` **空**（三份期望值副本一个未改）；六份文档全部纯追加。
- **审计方自选的四条变异，全部拿到「转红 → 点名 → 复原 → 转绿」**（执行者的三条之外）：
  ① 把 `_close` 的容差改成 `1e9` → `3 failed, 280 passed` 并点名三条对账测例；
  ② 把 `CH.EXPECTED_BACKLOG_VALUE` 换成字面量 `6450.0` → `2 failed`，点名那两条防作弊结构断言；
  ③ **专挑执行者自己写明的那处盲点**（裸整数）：给成品行喂 `"basic_rate": 5` → `1 failed`，
  点名 `test_manufacture_entries_never_send_the_finished_item_rate` —— **那处盲点实际上被结构断言兜住了**；
  ④ 复现执行者的 R3 ③ → `4 failed, 279 passed`，与 plan 所记逐字一致。复原后 `283 passed`，`git status` 与变异前一致。
- **审计裁定：第一轮 `needs revision`，两条 blocking + 三条非阻塞，已全部当场处置后接受关闭。**
  · **blocking ①（真缺陷，执行者引入，照实记不粉饰）**：**本 plan 文件被执行者的收尾编辑弄成了 917 行，
  其中 382 行是重复**——`## Closure Gates` 那个标题被写坏成 `## Deferred But Adjudicated\``，
  从 front matter 尾部到 `## Draft Review Record` 的整段被复制了第二份（含四个 Phase 的全部勾选）。
  成因是一处下标弄反的脚本编辑（`s[:a] + s[b:]` 在 `b < a` 时会复制 `[b, a)`）。
  **已修复**：删掉重复段并恢复标题，文件回到 **535 行**；机械核对
  `diff <(git show HEAD:<plan> | 抹掉勾选与 Status) <(现文件 | 同样抹掉)` 的输出**只剩 `## Closure` 段的填写**，
  **没有任何一条 gate 文本被改写**；章节结构与 HEAD 逐字一致；`## Deferred But Adjudicated` 出现次数 **1**。
  · **blocking ②**：`text consistency verified` 在缺陷 ① 存在时被勾了。**已随 ① 的修复重新成立**，
  修复后重新机械核对（未勾项只剩 `closure audit was independent` 一条，五处 `Status` 全为 `completed`）。
  · **非阻塞三条**（审计判为「说法比实际强/窄」，不是实现缺陷）：已按审计建议就地记准 ——
  在 `## Status Note` 的第 5 / 6 / 7 条与 `module-boundaries.md` §12.10 末尾各留一份，
  并改准了 `agenerp/seedsite.py` 里那条自己写错口径的注释。**Closure Gate 的文字一个字未改。**

Follow-up:

- **无。** 确认的缺陷不在这里；`## Deferred But Adjudicated` 的八条各自带 Classification 与重开事件。
