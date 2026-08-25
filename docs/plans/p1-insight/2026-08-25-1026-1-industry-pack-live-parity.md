# 行业包的离线↔活站点命中集合逐字比对 —— 把 P1.6 §7.10 的「部分一致」结清，并让这次比对留下可复跑的链

> Plan Status: completed
> Mission: p1-insight
> Work Item: 8. 行业包 v0（离散制造），每条规则带 test_case（P1.6）—— **本 plan 是它的第 2 个 plan**（表规 3 的 1–2 个，本 plan 用掉第 2 个，此后该格满）
> Last Reviewed: 2026-08-25
> Source: `docs/architecture/module-boundaries.md` **§7.10「活站点验证范围（H4 · 2026-08-24）」** 逐字记的
> **「结论是『部分一致』」** · `docs/bugs/02-live-site-sales-order-is-not-closed-so-the-account-green-trap-is-absent.md`
> 的状态行 · `docs/masterplan/STATE.md` §3 `[resolved] 2026-08-25T02:02Z`（人侧处置那条 `[open]`）
> Related: [`2026-08-24-2109-1-industry-pack-v0-discrete.md`](./2026-08-24-2109-1-industry-pack-v0-discrete.md)（P1.6 第 1 个 plan，本 plan 的前身）·
> [`2026-08-25-0225-2-insight-attribution-live-run.md`](./2026-08-25-0225-2-insight-attribution-live-run.md)（**形态先例**：
> `tools/experiments/<name>/run.py` 活跑 + `tests/unit/test_*_harness.py` 离线判据，本 plan 照抄这个形态）
> Audit: required

## 0. 执行前必做：重取基线

**起草期（2026-08-25 10:26）读到的一切都可能在开工时已经变了。** 下面九处**逐条重读**，
把实读值填进 §0.1；与起草期不一致的**照实记、不改起草期原文**。

1. `git log -1 --format=%H` 与 `git status --porcelain`（除本 plan 文件外须无输出）
2. **活站点上那张销售订单的状态**：只读一次 `Sales Order` 的 `name` / `status` / `total_qty` / `per_delivered`
   （起草期实读 `SAL-ORD-2026-00001` / `Closed` / `1000.0` / `99.0`）
3. `docs/architecture/module-boundaries.md` 的 `7.x` 族**当时的最大节号**
   （起草期是 **§7.18**，本 plan 预定落 **§7.19**；被占用就顺延，以开工时实读为准）
4. `docs/bugs/02-…` 的**状态行原文**（起草期逐字 `> 状态：**已确认、未修**（归属不在 P1.6 的交付面）`）
5. `docs/masterplan/STATE.md` §3 里 `2026-08-25T02:02Z` 那条是否仍是 `[resolved]`
6. `industry-packs/discrete/pack.json` 的 `pack_id` 与三条 `rule_id`
   （起草期：`discrete` · `discrete/finished-goods-backlog` ·
   `discrete/subcontracting-issued-not-received` · `discrete/closed-order-short-delivered`）
7. 五个判据面的**开工基线数字**（起草期实跑，逐条 exit 0）：
   `tests/unit` `672 passed` · `tests/contracts` `151 passed` · `tests/tools` `81 passed, 12 skipped` ·
   `tests/routing` `167 passed, 1 skipped` · `tests/context` `54 passed`
8. `python3 tools/gates/check_expected_red.py`（起草期：`门禁 26 项：预期红 0，绿 26，跳过 0`，exit 0）
9. `find agenerp -name '*.py' | wc -l`（起草期 **56**）——
   `tests/routing/test_adapter.py:485` 的 `PRODUCT_MODULES` 按**每个** `agenerp/**/*.py` 参数化一次。
   ⚠️ **本 plan 的 Non-Goals 1 承诺零个新增产品模块 ⇒ 这个数必须开工与收口逐字相同**；
   若它变了，说明本 plan 越出了自己的定界。

### 0.1 执行期重取基线的**实读结果**

（2026-08-25 开工实读。逐条命令原文 + 退出码 + 实读值。**九条与起草期逐字一致，无一条漂移。**）

1. `git log -1 --format=%H` → exit 0 · `ec7416140638374f7979887ffcfe3e6692b90b42`；
   `git status --porcelain` → exit 0 · 只有一行 `?? docs/plans/p1-insight/2026-08-25-1026-1-industry-pack-live-parity.md`
   （即本 plan 自己），**与起草期一致**。
2. 活站点那张销售订单（命令见 §6 H1「实际」列）→ exit 0 ·
   `[{"name": "SAL-ORD-2026-00001", "status": "Closed", "total_qty": 1000.0, "per_delivered": 99.0}]`
   —— **与起草期逐字相同**。
3. `grep -n '^### 7\.' docs/architecture/module-boundaries.md | tail -1` → exit 0 ·
   `2757:### 7.18 P1.0 逐格计数的单一真相源…` ⇒ `7.x` 族当时最大节号仍是 **§7.18**，
   **§7.19 未被占用**，本 plan 照预定落 §7.19（不顺延）。
4. `sed -n '3p' docs/bugs/02-…md` → exit 0 ·
   `> 状态：**已确认、未修**（归属不在 P1.6 的交付面）` —— **与起草期逐字相同**（漂移 A 仍在）。
5. `grep -n '2026-08-25T02:02Z' docs/masterplan/STATE.md` → exit 0 · 命中 `:389`，
   行首逐字 `- [resolved] 2026-08-25T02:02Z ·` —— **仍是 `[resolved]`**。
6. `python3 -c "import json;d=json.load(open('industry-packs/discrete/pack.json'));print(d['pack_id']);print([r['rule_id'] for r in d['rules']])"`
   → exit 0 · `discrete` · `['discrete/finished-goods-backlog', 'discrete/subcontracting-issued-not-received', 'discrete/closed-order-short-delivered']`
   —— **三条 `rule_id` 与起草期逐字相同**。
7. 五个判据面（逐条 exit 0）：`python3 -m pytest tests/unit -q` → `672 passed` ·
   `tests/contracts` → `151 passed` · `tests/tools` → `81 passed, 12 skipped` ·
   `tests/routing` → `167 passed, 1 skipped` · `tests/context` → `54 passed`
   —— **五条与起草期逐字相同**。
8. `python3 tools/gates/check_expected_red.py` → exit 0 ·
   `门禁 26 项：预期红 0，绿 26，跳过 0` / `✅ 与预期红名单完全一致` —— **与起草期逐字相同**。
9. `find agenerp -name '*.py' | wc -l` → exit 0 · **56** —— 与起草期相同。
   ⚠️ 这个数是 Non-Goals 1 的机械判据，**收口时须逐字仍是 56**。

## 1. Current Baseline

### 1.1 本 plan 的授权来自**两处已确认的文档漂移**，不来自一条被触发的 Deferred

**这一节必须先说清楚，因为它决定了本 plan 能做多大。**

`2026-08-24-2109-1`（P1.6 第 1 个 plan）§11 的**四条** Deferred（`rule.lookup` 接线 · 日期算术 ·
D01 转换层 · `thresholds`/`terminology`）**没有一条的重开事件被触发**。
`STATE.md` §3 `[resolved] 2026-08-25T02:02Z` 也**没有指派任何 successor**，
且它的 ② 逐字把那条判据判给**站点侧对账**、逐字写着「**不是行业包**」。

⇒ **本 plan 的授权只有一处**：`00-plan-authoring-and-execution-guide.md` **第 14 条**
逐字把「confirmed owner-doc drift」列为**不可降级项**。今天有两处这样的漂移（§1.2），
它们**必须被修**，而修它们要先跑一次实测才知道该改成什么。**授权到此为止** ——
本 plan 因此**不新增任何产品代码**（Non-Goals 1），把面积压到「修漂移所必需的最小值」。

⚠️ **这一段同时回答 Minimum Rule 4「一个 plan 一个结果面」，不许当成背景话读过去**：
本 plan 的结果面**只有一个** —— 「**§7.10 那一段说的话变成真的**」。
Phase 2（漂移 A）看起来能独立收口，**但它不是第二个结果面**：
漂移 A 与漂移 B 是**同一段文字**（§7.10「活站点验证范围」+ 它指向的 `docs/bugs/02-…`）的两句话，
分两个 phase 改**只是因为一句依赖实测、另一句不依赖**（§1.2）。
把它们拆成两个 plan 会得到「一段文字被改了一半」这种形态，那比合在一起更糟。
Phase 3/4 也不是独立结果面：它们**是为了让那段文字里的新结论有证据可依**才存在的，
**结论一旦不需要，那条链也不需要**。

### 1.2 两处已确认的漂移，逐条写清哪一处依赖实测、哪一处不依赖

**漂移 A（不依赖任何实测，今天就是错的）**：

- `docs/bugs/02-…:3` 逐字 `> 状态：**已确认、未修**（归属不在 P1.6 的交付面）`
- `module-boundaries.md` §7.10 逐字「归属不在本节的交付面 —— 已记 `docs/bugs/02-…`，
  并在 `docs/masterplan/STATE.md` §3 追加了 needs-human」

两句话都被**已入仓的事实**证伪：人于 `484c123` 修了装载面，并把那条 `[open]` 改成
`[resolved] 2026-08-25T02:02Z`。**这两处与站点今天是什么状态无关**，
因此 Phase 2 的修正是**无条件的**，不进任何停机分支。

**漂移 B（依赖一次实测才知道该改成什么）**：

- `module-boundaries.md` §7.10 逐字「**结论是「部分一致」**」，
  其中 `discrete/closed-order-short-delivered` 记「**离线命中 10，站点零命中**」，
  成因是「站点上 `Sales Order.status` 是 `"To Deliver and Bill"`」

**成因已被 `484c123` 消掉。** 起草期只读实测一次（**只读了 `Sales Order` 一张表，没有跑包**——
跑包属执行期，预测必须先写死，见 §6）：

```
[{'name': 'SAL-ORD-2026-00001', 'status': 'Closed', 'total_qty': 1000.0, 'per_delivered': 99.0}]
```

⚠️ **「成因消掉了」不等于「两侧现在一致」** —— 那是一个没跑过的实测。
**起草期不写结论，只写预测**（§6 H2）。

### 1.3 人已交付的那条判据是**另一件事**，本 plan 必须守住这条边界

`484c123` 新增了 `agenerp/seedsite.py` 的 `_trap_precondition_checks` 两条
（订单状态为 `Closed`、交付缺口为 10），站点侧对账 30 → **32 项全过**。
那判的是「**站点上有没有那个可查的事实**」。

**本 plan 判的是另一件事**：「**整份包的命中集合，两侧是否逐字一致**」——
那是 §7.10 自己写死的 H4 纪律（逐字：「整份包在活站点跑一次，命中集合与离线逐字比对，
且先断言集合非空」），属行业包的交付面。

⚠️ **两者混成一句话，就是把「前提事实在」说成「包在真站点上验证过」。**
本 plan **不重复、不改、不在旁边再写一份**那条对账判据，
也**不改 `agenerp/seedsite.py` 一个字**。

### 1.4 那次 H4 核对是**一次性手工的**，仓里没有任何可再跑一次的东西

⇒ 下一次数据集或站点再漂一次，仍然只能靠一个人记得去比 —— 那正是 D-12 点名的失败形态
在**比对这一层**的复现。**本 plan 的实测因此必须留下一条可复跑的链**，
否则它自己就是下一次「一次性手工核对」。

**形态照抄本仓已有的先例，不发明新的**（`2026-08-25-0225-2` 与 `p1-answer-judge` 两次都是这个形态）：

- 活跑脚本 `tools/experiments/p1_pack_parity/run.py`（对照 `tools/experiments/p1_insight_live/run.py`，530 行）
- 它的**离线判据** `tests/unit/test_pack_parity_harness.py`（对照 `tests/unit/test_insight_live_harness.py`，385 行）
- 证据落 `docs/evidence/p1-pack-parity/`（对照 `docs/evidence/p1-insight-live/`）

⚠️ **`tools/` 不在 `ruff` 扫描范围、也不在任何 CI job 里** ——
这是一处**已登记的已知缺口**（`docs/backlog/tools-dir-has-no-static-check-coverage.md`，
`Status: deferred`，处置者是**人**），**本 plan 不代人处置、也不假装它不存在**。
本 plan 的处置与两次先例同形：**判据面放在 `tests/unit`**（它在 CI 里、也在
`missions/p1-insight.json` 的 `commands.test` 里），并**按路径加载出货的那份脚本**（判据 ⑩），
使那份脚本的行为**有一条在 CI 里跑的判据钉着**。
⚠️ **不写成「脚本只做编排」** —— 拆成两个文件之后，判定逻辑就在 `parity.py` 里，
那句话按构造为假（详见 R5）。

### 1.5 比对面比起草期设想的更现成，不必自己发明形状

- `agenerp/inspection/engine.py:263` `run(rules, source, pack_id)` · `:282`
  `inspect_site(rules, client, pack_id)`（后者逐字自述「产品入口……**零 LLM、零写操作**」）
- `InspectionReport.as_dict()` 已输出**三个键**：`rule_ids`（这次查了哪些规则）·
  `request_count`（**站点只读请求数已经是产物的一部分，不必另挂探针**）· `hits`
- `Hit.as_dict()` 输出**七个键**：`pack_id` / `rule_id` / `statement` / `subject` /
  `quantity_name` / `quantity` / `measures`
- `SiteRows.request_count`（`:55`）由 `run()` 经 `getattr(source, "request_count", 0)` 收进报告（`:278`）
- **起草期在离线侧实跑过一次整份包**（`load_pack("discrete")` + `inspect_site(..., client_for(seed_site()))`）：
  `request_count = 10` · `len(hits) = 2` · `len(rule_ids) = 3`。
  ⚠️ **这一跑只跑了离线侧，一次站点请求都没发** —— 活站点侧是 §6 H2 的预测对象，起草期没有碰。
  ⚠️ **它有一个直接后果**：离线侧 `request_count` 是 **10**，而 §7.10 记的活站点侧是 **9** ——
  **两侧的请求数本来就不同**，这是比对器契约 ② 的**实测依据**（不是「按构造想当然」）；
  也意味着 H5 若实测到 10 而不是 9，**那不是异常**，照实记即可

⇒ **比对的对象就是两份 `InspectionReport.as_dict()`**，本 plan 不新增任何数据形状。

### 1.6 与本 plan 相关的既有事实（只列，不重复登记）

- 期望侧常量在产品代码里：`agenerp/seed/checks.py` 的 `EXPECTED_BACKLOG_QTY = 1010.0`
  与 `EXPECTED_SHORTFALL_QTY = 10.0`
- 离线那一侧的行源在**测试夹具**里：`tests/unit/inspection_fakes.py:133` 的 `seed_site()`
  由 `agenerp.seed.generate()` 派生，但含成形逻辑（`_retimed` / `_child_items` / `_bins` /
  补 `doctype` 键四处）。⚠️ **本 plan 不下沉它、不重写它、不复制它**（Non-Goals 1），
  离线那一侧由脚本按 `load_repo_module` 先例**加载**那份夹具取得
- `rule.lookup` **仍未接线**且**本 plan 不接**：翻转它会让
  `tests/gates/test_tool_execution_live.py:119` 由绿转红（红线 1，已登记归人）
- 判定器现为 **26 项**（人于 `913d515` 补齐 P1.4/P1.5/P1.7 三个 🔴 验收件，带 `Gates-Change-Approved-By: lize`）
- `.github/workflows/gates.yml:532-535` 第 ⑦ 步把测试目录集合写死成
  `contracts context experiments fixtures gates routing tools unit`，多出目录当场 `exit 1`
  ⇒ **本 plan 不新增任何 `tests/` 顶级目录**

## 2. Goals

1. **两处已确认的文档漂移改准**（§1.2）：漂移 A **无条件**；漂移 B 按实测结论改准。
2. **跑一次、比一次、落一次账**：整份 `industry-packs/discrete/` 在活站点与离线固定测例上各跑一遍，
   两份 `InspectionReport.as_dict()` **逐字比对** —— 一致就写一致，仍不一致就写仍不一致。
3. **这次比对留下可复跑的链**（§1.4 的形态），且**那条链的判定逻辑本身有判据挡着**：
   「两个空集相等」「只比条数」「只比 `rule_id` 不比数」「顺序敏感」四种假实现各有一条判据打红。
4. **越权处停机**：站点若不在「已关单」状态，**不跑装载器把它做出来**，记 blocked 交人。

## 3. Non-Goals

1. **零新增产品代码**：本 plan **不新增、不修改任何 `agenerp/**/*.py`**
   （收口自查：`git status --porcelain -- agenerp/` **无输出**，且 `find agenerp -name '*.py' | wc -l`
   与开工时逐字相同）。**不加 CLI 子命令** —— `python3 -m agenerp.packs validate` 是
   `02-WBS.md` §4 P1.6 的验收原文，本 plan 一个字节不碰 `agenerp/packs/__main__.py`。
2. **不对活站点做任何写**。点名覆盖：`python3 -m agenerp.seedsite --load-*` 任何形态 ·
   任何 `POST`/`PUT`/`DELETE` 到站点（**除** `POST /api/method/login` 换会话这一条既有路径）·
   `bench` 的任何写子命令。站点不在预期状态 ⇒ **记 blocked 停机**，不是「先装载一下」。
3. **不重复人已交付的站点侧对账判据**（`_trap_precondition_checks`，`484c123`）,
   **也不改 `agenerp/seedsite.py` 一个字**（§1.3 的边界）。
4. **不接线 `rule.lookup`**（会把一条 L2 门禁由绿转红，红线 1，已登记归人）。
5. **不改任何一条规则去迁就站点**。两侧仍不一致就**照实记不一致**，
   `industry-packs/` 一个字节不动（那是照答案写规则，P1.6 已立的纪律）。
6. **不新增 `tests/` 顶级目录**（§1.6 的 CI 第 ⑦ 步；修它属红线 2）。
7. **不改** `tests/gates/**` · `.github/workflows/**` · `missions/*.json` ·
   `docs/masterplan/DECISIONS.md`；`docs/masterplan/STATE.md` **只追加**（红线 1/2/3/5）。
8. **不改 `docs/backlog/p1-insight-roadmap.md` 的 Work Item Status 块**（由引擎回写）。
9. **一个模型都不调**（D-15：巡检器零 LLM）。不碰 `agenerp/routing/**` 与 `agenerp/explain/**`。
10. **不做 P1.6 已显式定界的四件事**：`thresholds` / `terminology` 两个顶层块 ·
    行业包分发机制（P5）· `anomaly.scan` / `benchmark.compare` · 日期算术那一维。
11. **不新增第二个行业包**，也不给 `discrete` 加规则 —— 输入是**今天盘上那三条**。
12. **不下沉、不重写 `tests/unit/inspection_fakes.py`**（§1.6）。本 plan 对它**只读加载**，
    收口自查 `git status --porcelain -- tests/unit/inspection_fakes.py` 无输出。

## 4. Task Route

- Type: `verification or audit work`（主体是一次实测与两处文档漂移的改准；
  唯一的代码产物是**实验设施 + 它的离线判据**，不是产品面）
- Owner Docs：
  - `docs/architecture/module-boundaries.md` **§7.10**（**本 plan 改它的「活站点验证范围」那一段** ——
    唯一被授权改写既有行的架构落点，理由是 §1.2 的已确认漂移；该节其余各段**只读不改**）
  - `docs/architecture/module-boundaries.md` **§7.9 / §7.16**（**只读**：巡检器落点 · 归因活跑落点）
  - `docs/masterplan/DECISIONS.md` **D-12 / D-15 / D-16**（**只读**，红线 3）
  - `docs/context/ai-autonomy-policy.md` **Protected Areas**（**只读** ——「对活站点的写」两行是停机线）
  - `docs/bugs/00-bug-fix-note-writing-guide.md`（改 `docs/bugs/02-…` 的格式源）
  - `docs/backlog/tools-dir-has-no-static-check-coverage.md`（**只读**，§1.4 那条已知缺口的出处）
- Skill Selection Basis：
  Phase 1 是只读实测 → `Skill: none`；Phase 3 的裁定用 `development-wisdom-gate-prompt.md` 自查
  （required input「assumption inventory」正是 §6）；草案评审 `plan-audit-prompt.md`；
  关闭审计 `closure-audit-prompt.md`。

## 5. Infrastructure And Config Prereqs

- **活栈**：`AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300`。
  ⚠️ 裸跑 `docker compose up -d` 会落到 **8080**，而 8080 被本机另一套常驻 ERPNext 栈占着
  （起草期实读：`agenerp-frontend-1` 映射 `127.0.0.1:18080->8080/tcp`；`docker-frontend-1` 占 `0.0.0.0:8080`）。
- **站点只读访问**：`AGENERP_SITE=frontend` · `AGENERP_SITE_URL=http://127.0.0.1:18080` ·
  `AGENERP_ADMIN_PASSWORD`（本仓一贯取值 `admin`，出处 `docs/context/project-context.md`）。
- **LLM 凭据**：**本 plan 不需要**（Non-Goals 9）。一个模型都不调。
- **回滚**：本 plan 对活站点**只读**，站点侧无需回滚；仓内改动 `git revert` 即完整回滚。
  **不跑 `bench backup`** —— 它会往共用的 `sites:` volume 里写文件，正撞 §5.1 见即停。

### 5.1 见即停清单（起草期写死，执行期不许现编）

**看见就停下来记进 `STATE.md` §3，不许绕、不许试、不许「先跑一下看看」**：

1. 任何 `python3 -m agenerp.seedsite` 的**非 `--verify-site`** 形态（`--load-*` 一律停）
2. 任何 `bench` 子命令中的：`new-app` · `install-app` · `build` · `migrate` · `backup` ·
   `restore` · `set-config` · `execute`
3. 任何 `POST` / `PUT` / `DELETE` 到站点 —— **除** `POST /api/method/login` 一条白名单。
   ⚠️ **按实际发出的 HTTP 动词判，不按方法名听起来是不是只读判**（`SiteClient.call_method` /
   `post_method` 内部走 `POST`；`0119-1` 的先例就是在这条缝上越过一次）
4. 任何对 `docker-compose.yml` 的编辑；`docker cp` 任何方向
5. 任何 `pip install` / `npm install`（本 plan 不引任何第三方依赖）
6. 任何对 `tests/gates/**` · `.github/workflows/**` · `missions/*.json` ·
   `docs/masterplan/DECISIONS.md`（以及 `docs/masterplan/` 除 `STATE.md` 追加外的一切）的写
7. 任何对 `agenerp/**` 或 `industry-packs/**` 的写（Non-Goals 1 / 5）
8. 任何 `import agenerp.routing` / `agenerp.explain` 出现在本 plan 新增的任何文件里（Non-Goals 9）

## 6. 开工前写死的假设（硬约束②：预测在前、结果在后、逐条吻合）

**下面每一格在开工前写死，执行期只填「实际」列，预测列一个字不改。**
不吻合的**照实记并说清前提哪里错了**，不许事后改写预测。

⚠️ **本表共九格（H1–H9），其中 H1 是「复核项」不是预测**（起草期已实读过同一个值，
它没有证伪力，写在表里只是为了让「开工时它变了」这件事有处可记）。
**逐条吻合的计数不许把 H1 算成一格命中；H4 是 H2① 的推论，也不单独计一格。**
H2–H9 是**真预测**：起草期只读了 `Sales Order` 一张表，**没有跑过包**。

| # | 假设（预测，逐字） | 怎么测 | 实际 |
|---|---|---|---|
| **H1**（复核项，非预测） | 开工时活站点上 `SAL-ORD-2026-00001.status == "Closed"` 且 `per_delivered == 99.0` | 只读一次那张表 | **吻合**。命令：`AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -c` 里 `client_from_env("frontend").get("/api/resource/Sales Order", {"fields": json.dumps(["name","status","total_qty","per_delivered"]), "limit_page_length":"0"})` → **exit 0**，载荷原文 `[{"name": "SAL-ORD-2026-00001", "status": "Closed", "total_qty": 1000.0, "per_delivered": 99.0}]`。⇒ **停机分支未触发**，Phase 4 / Phase 5 照常执行 |
| **H2**（承重格） | 整份包两侧各跑一遍，**三条规则的命中集合逐字一致**，逐条为：① `discrete/finished-goods-backlog` 两侧**各 1 条**，`quantity == 1010.0`（`= EXPECTED_BACKLOG_QTY`）；② `discrete/subcontracting-issued-not-received` 两侧**各 0 条**；③ `discrete/closed-order-short-delivered` 两侧**各 1 条**，`quantity == 10.0`（`= EXPECTED_SHORTFALL_QTY`） | 用 Phase 3 建好的那条链跑，`Hit.as_dict()` 七个键逐字比对 | **三条逐条吻合 —— `verdict: identical`**。命令：`AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 /tmp/agenerp-parity-driver.py`（D2 的短驱动器：装替身 + 调 `run.main(sys.argv[1:], wiring=run.live_wiring)`）→ **exit 0**。① `discrete/finished-goods-backlog` 两侧**各 1 条**，`quantity = 1010.0`（`= EXPECTED_BACKLOG_QTY`），`subject = {"item_code": "HRD-PACK-5K", "warehouse": "成品仓 - HRD"}`；② `discrete/subcontracting-issued-not-received` 两侧**各 0 条**；③ `discrete/closed-order-short-delivered` 两侧**各 1 条**，`quantity = 10.0`（`= EXPECTED_SHORTFALL_QTY`），`subject = {"name": "SAL-ORD-2026-00001"}`。`parity.json` 逐字 `"matched": 2` / `"count": {"offline": 2, "live": 2}` / `"equal": true`。⇒ **触发的是「三条全一致」那一种处置** |
| **H3** | 两份报告的 `rule_ids` **逐字相同**（同一份包、同一个顺序）—— 它与命中集合是**两个独立的量**：规则一条没查到、而恰好也一条都没命中时，只比 `hits` 会绿 | 比对 `InspectionReport.as_dict()["rule_ids"]` | **吻合**。两侧同为 `['discrete/finished-goods-backlog', 'discrete/subcontracting-issued-not-received', 'discrete/closed-order-short-delivered']`（三条、同序），`parity.json` 的 `rule_ids.equal = true` |
| **H4** | 两侧命中集合**都非空**（各 ≥ 1 条）—— 没有这一格，「两个空集相等」也叫「逐字一致」。⚠️ **照实说清它的地位**：H2① 若成立，「各 ≥ 1」**就是它的算术推论**，本格**不是一条独立的预测**。它留在表里的价值只有一个 —— **逼出「非空断言写在比对之前」这个实现约束**（比对器契约 ③）：一个先比后判的实现在两侧都空时会返回「一致」，而那正是要挡的假实现 | 比对前先断言两侧非空，断言写在比对之前；判据 ⑤ 是它的反测 | **吻合**：两侧**各 2 条**命中，`parity.json` 的 `empty_sides` 为 `[]`。实现约束按预期被逼出来了 —— `parity.compare()` 里那段非空检查**写在任何比对之前**（`if len(empty) == len(SIDES): return {... INCOMPARABLE ...}`），反测是判据 ⑤，变异 M1 把它改成 `if False:` 后 **2 failed** |
| **H5** | 站点侧 `InspectionReport.request_count` **== 9**（P1.6 那次 H4 实测值，§7.10 逐字记着「9 次只读请求」）。⚠️ **本格不是承重格**：不吻合就照实记多/少在哪，**不改规则、不改巡检器去凑那个 9** | 直接读报告里那个字段（**不另挂探针** —— 引擎已经在数了，另挂一个会双计） | **不吻合：实测 `10`，不是 `9`**。`live-hits.json` 的 `request_count = 10`（离线侧也是 10）。传输层实录 **11 条 HTTP 请求**：`GET` 10 条 + `POST /api/method/login` 1 条（登录换会话不经 `SiteRows`，因此不计进 `request_count`）。⚠️ **本格不是承重格，起草期已写死「实测到 10 不是异常，照实记」** —— **没有为了凑那个 9 改任何一条规则或巡检器**。多出来的那一次相对 §7.10 记的 9，本 plan **不猜根因**（裁判规则 3），只记下这次的逐端点分布：`Sales Order Item` 5 · `Sales Order` 1 · `Stock Ledger Entry` 1 · `Subcontracting Order` 1 · `Subcontracting Order Item` 1 · `Subcontracting Receipt Item` 1 |
| **H6** | 比对器在**人为制造的分歧**下发红，四种各一条：删掉一侧任一条命中 · 把一侧任一条的 `quantity` 改 1.0 · 只比 `rule_id` 不比数的弱比对 · 把一侧的命中列表倒序（**这一条预测是「仍判一致」** —— 顺序不该是判别面） | Phase 3 的离线判据，**假两侧，不碰站点** | **四条逐条吻合**（`python3 -m pytest tests/unit/test_pack_parity_harness.py -q` → exit 0，`25 passed`）：① 删掉一侧任一条命中 → `verdict=different` 且差异指名 `rule_id=discrete/closed-order-short-delivered` / `subject={"name": "SAL-ORD-2026-00001"}`（`test_a_hit_missing_on_one_side_is_named_by_rule_id_and_subject`）；② `quantity` 10.0→11.0 → `different`，`differing_keys == ["quantity"]`（`test_a_one_point_zero_quantity_drift_is_judged_different`）；③ 弱比对「只比 `rule_id` 不比数」由**变异 M3** 施加 → 判据 ③/④ 打红（2 failed）；④ 一侧倒序 → **仍判 `identical`**，`matched == 2`（`test_reversing_one_sides_hit_list_is_still_identical`）—— **预测的「仍判一致」成立** |
| **H7** | **本轮零模型调用**，两个可观测量都成立：① 全新解释器里 `import` **比对器模块** `tools/experiments/p1_pack_parity/parity.py` 之后 `agenerp.routing` **不在 `sys.modules`**；② `ChatAdapter` 构造面整体替身在整条比对链上的调用计数为 **0**，**且两条对照都成立** —— **阳性对照**（故意调一次 → 探针发红）与**探针默认关闭对照**（`test_inspection_rules.py:254` `test_h2_the_probe_is_off_by_default`，其 docstring 逐字「否则上面那条阳性对照**可能红在别的原因上**」）。 **先例有三条腿就抄三条**。⚠️ **① 的主语刻意只是比对器，不是整个脚本** —— 起草期实测：按路径加载 `tests/unit/inspection_fakes.py` **会**把 `agenerp.routing` 拉进 `sys.modules`（它 `:39` 取 `explain_fakes.FakeSite`，那条链 import 了 routing）。**把 ① 写成「整个脚本」按构造为假，本 plan 不提出那个主张，也不靠删依赖去凑它** | 照抄 `tests/unit/test_inspection_rules.py` 的 `no_model_calls` 替身（`:211-226`）· 阳性对照（`:239`）· **探针默认关闭对照（`:254`）** · 进程级探针（`:264` 起）**四处**已有口径 | **两个可观测量都成立，三条腿齐**：① 全新子进程里按路径 `import tools/experiments/p1_pack_parity/parity.py` 之后 `'agenerp.routing' not in sys.modules` **且 `[k for k in sys.modules if k.startswith('agenerp')] == []`**（`test_h7a_importing_the_comparator_never_pulls_in_the_model_face`，子进程 returncode 0）；② `ChatAdapter` 构造面整体替身（`__init__`/`chat`/`_send`/`_post`/`_ssl_context` 五处）在整条比对链上 **`calls == 0`**（`test_h7b_the_whole_parity_chain_makes_zero_model_calls`）；**阳性对照**成立 —— 故意 `route("explain", …)` 一次，探针发红且 `calls` 由 0 变 **1**（`test_h7b_positive_control_a_path_that_does_touch_the_model_is_caught`）；**探针默认关闭对照**成立 —— 不装探针时同一条路径通，`adapter.chat(...).text == "hi"`（`test_h7b_the_probe_is_off_by_default`）。⚠️ **① 的主语确实只能是比对器**：实测按路径加载 `tests/unit/inspection_fakes.py` 后 `'agenerp.routing' in sys.modules` 为 `True`，起草期的记录被复现，**本 plan 不提出「整个脚本」那个主张** |
| **H8** | **五个既有判据面逐字不变**：`tests/contracts` `151 passed` · `tests/tools` `81 passed, 12 skipped` · `tests/routing` `167 passed, 1 skipped` · `tests/context` `54 passed`；`tests/unit` **只增不减**（基线 `672 passed`）。⚠️ **`tests/routing` 这次预测「逐字不变」是有前提的**：Non-Goals 1 承诺零新增 `agenerp/**/*.py`，而 `test_adapter.py:485` 按每个产品模块参数化 —— **它若变了，说明本 plan 越界了，不是「正常增长」** | 五条命令逐条跑，逐条记退出码与数字 | **五条全部吻合**（逐条 exit 0）：`python3 -m pytest tests/contracts -q` → `151 passed`（逐字不变）· `tests/tools` → `81 passed, 12 skipped`（逐字不变）· `tests/routing` → **`167 passed, 1 skipped`（逐字不变）** ⇒ **零新增产品模块，未越界** ·`tests/context` → `54 passed`（逐字不变）· `tests/unit` → **`697 passed`**（基线 `672` **+25**，只增不减）。另一条机械判据同样吻合：`find agenerp -name '*.py' | wc -l` 开工与收口同为 **56** |
| **H9** | **对活站点零写**：比对前后各取一次四类可数文档计数（`Sales Order` / `Delivery Note` / `Stock Ledger Entry` / `Bin`）**逐条相等**，且 `SAL-ORD-2026-00001` 的 `modified` 时间戳前后**逐字相同** | 两种读回口径各一次（照抄 `0119-1` Phase 1 的做法） | **【前】**（Phase 1 实读，exit 0）口径①「`GET /api/resource/<dt>` fields=["name"] limit_page_length=0 → 行数」`{"Sales Order": 1, "Delivery Note": 1, "Stock Ledger Entry": 10, "Bin": 4}`；口径②「`GET /api/method/frappe.client.get_count?doctype=<dt>`」`{"Sales Order": 1, "Delivery Note": 1, "Stock Ledger Entry": 10, "Bin": 4}`；`SAL-ORD-2026-00001.modified = "2026-08-25 07:30:46.926828"`、`status = "Closed"`。**【后】**（Phase 4 实读，exit 0）两种口径**逐条与「前」相同**，`modified` 与 `status` 亦**逐字相同** ⇒ **H9 吻合，本轮对活站点零写**。另有运行期挡板：`ReadOnlyTransport` 白名单外当场抛，本次 `denied` 为空、`other_verbs` 为空。⚠️ 它排除的是「本轮自己写了」，**排除不掉「别人在同一分钟写了」**（R2），照实记，不说成「已隔离」 |

**⚠️ H2 的三种结果各有起草期就写死的处置，执行期不许现编**：

- **三条全一致** ⇒ §7.10 那一段的结论由「部分一致」改成「逐字一致」，
  并**逐字保留** 2026-08-24 那次的观测（追加式，不抹掉）。
- **第三条仍零命中** ⇒ **不是本 plan 的失败，是一个新观测**。照实记，**规则一个字不动**，
  按 `docs/bugs/00-bug-fix-note-writing-guide.md` 在 `docs/bugs/` 立**新的一条**
  （不改写 02 的 §1–§3 诊断部分），并在 `STATE.md` §3 追加一条 needs-human。
  **不许把它写成「基本一致」。**
- **出现前两条之外的第三种偏差** ⇒ 同上照实记，且**先原样复跑那条命令**
  （裁判规则 3：复跑优先于分析），复跑不出来就记「不可复现」，**不猜根因**。

## 7. Execution Plan

**执行顺序即下列顺序，不许并行、不许跳。**
⚠️ **顺序是刻意的**：**先把带判据的比对链建起来（Phase 3），再用它去跑那一次（Phase 4）** ——
反过来会让「落进架构文档的那个结论」由一条没有判据的临时路径产出，
而被判据挡着的那条路径从未跑过真实的两侧。**两条路径必须是同一条。**

### Phase 1 — 只读探测：站点是否还在「已关单」状态

Status: completed
Targets: 无仓内改动（实读值填进 §0.1 与 §6）
Skill: `none`
Item Types: `Proof`（2/2 项，phase 级统一类型）
Prereqs: 活栈已 Up；`AGENERP_ADMIN_PASSWORD` 已设

- [x] **Proof P1**：只读一次 `Sales Order` 的四个字段 → 回填 **H1**
- [x] **Proof P2**：取一次 **H9 的「前」** 计数与 `modified` 时间戳（四类可数文档 + 那张单）

Exit Criteria:

- [x] H1「实际」列已填，附**命令原文 + 退出码 + 载荷原文**
- [x] H9 的「前」侧已落盘（§6 H9「实际」列的【前】半，两种读回口径逐条在案）
- [x] **H1 不成立时的分支已按起草期写死的口径执行**（下面三条**同时**成立才算执行到位）：
      ① **Phase 2 照常做完**（漂移 A 不依赖任何实测，§1.2）；
      ② **Phase 3 照常做完**（它是离线的，一次站点请求都不发）；
      ③ **Phase 4 的活跑与 Phase 5 的「漂移 B」两项**转 `Deferred But Adjudicated`，
      重开事件逐字为「**活站点被重新装载到『订单已关闭』状态（由人）**」，并写进 `STATE.md` §3。
      ⚠️ **不许跑装载器把状态做出来**（§5.1 第 1 条）。
      ⇒ **本次实测 H1 成立（`Closed` / `99.0`），停机分支未触发，本条空过。**
- [x] `docs/logs/` 更新

### Phase 2 — 漂移 A 改准（**无条件，不依赖任何实测**）

Status: completed
Targets: `docs/bugs/02-live-site-sales-order-is-not-closed-so-the-account-green-trap-is-absent.md` ·
`docs/architecture/module-boundaries.md` §7.10（**只改「归属」那一句**）
Skill: `none`
Item Types: `Fix`（2/2 项，phase 级统一类型）
Prereqs: 无 —— **本 phase 与 Phase 1 的结果无关**（§1.2 漂移 A）

- [x] **Fix** `docs/bugs/02-…`：状态行由 `> 状态：**已确认、未修**（归属不在 P1.6 的交付面）`
      改准为「**已由人修复**」并带 sha `484c123`；**§4 Fix 节**补写人侧的两条裁定
      （`status` 是受控字段 → 提交后调 `update_status`；判据归站点侧对账）。
      **§1–§3（Problem / Diagnostic Method / Root Cause）一个字不动** ——
      那是当时的诊断记录，改它就是改历史。
      ⚠️ **只写实测/已入仓得到的那一半**：本 phase 引用的是 `484c123` 的提交信息与
      `STATE.md:389`，**没有复跑**「干净站点从头重建也得到 `Closed`」（那是人做过的，**引用不复跑**）。
- [x] **Fix** `module-boundaries.md` §7.10 里「归属不在本节的交付面 —— 已记 `docs/bugs/02-…`，
      并在 `STATE.md` §3 追加了 needs-human」这**一句**：指针改指
      `[resolved] 2026-08-25T02:02Z`。**结论那一句（「部分一致」与三条逐条记录）本 phase 一个字不动** ——
      它归 Phase 5，因为它要等实测。

Exit Criteria:

- [x] `docs/bugs/02-…` 的 §1–§3 逐字未变（自查：`git diff -U0 -- docs/bugs/02-….md | grep -n '^-[^-]'` → exit 0，
      **删除行共 5 行**：`> 状态：…` / `> 交接：…`（两行都在 §1 之前的前言里）+ §4 的三行；**无一落在 §1–§3 内**）
- [x] §7.10 本 phase 的删除行**只落在「归属」那一句上**（自查：`git diff -U0 -- docs/architecture/module-boundaries.md | grep -n '^-[^-]'`
      → **仅 1 行**，逐字 `  已记 \`docs/bugs/02-…\`，并在 \`docs/masterplan/STATE.md\` §3 追加了 needs-human。`）
- [x] `docs/logs/` 更新（`docs/logs/2026/08-25.md` 顶部新增 Phase 1–2 条目）

### Phase 3 — 先把带判据的比对链建起来（**离线，一次站点请求都不发**）

Status: completed
Targets: `tools/experiments/p1_pack_parity/parity.py`（新建，**纯比对器：两份 dict 进、结构化差异出，
零 import 本仓任何模块**）· `tools/experiments/p1_pack_parity/run.py`（新建，**只做编排**：
加载夹具 / 建站点客户端 / 落盘）· `tests/unit/test_pack_parity_harness.py`（新建）
Skill: `development-wisdom-gate-prompt.md`（自查）
Item Types: `Decision | Add | Proof`
Prereqs: 无站点依赖 —— **本 phase 在 H1 不成立时照常做完**（Phase 1 Exit Criteria ②）

- [x] **Decision D1 · `request_count` 排除在一致性判定之外**（比对器契约 ②）
      - 选中：**记录但不判定**。实测依据（§1.5）：离线侧 `request_count = 10`，§7.10 记的活站点侧是 **9**。
      - 备选①「把它算进判定」→ **否决**：两侧本来就不同，比对会**永远不一致**，
        那不是一条严格的判据，是一条**恒红**的判据 —— 恒红与恒绿一样没有判别力。
      - 备选②「把它归一化后再判」（例如只判「两侧都 > 0」）→ **否决**：那等于发明一个
        本仓没有依据的口径；「> 0」还挡不住任何一种本 plan 要挡的假实现（假实现照样会打请求）。
      - **残余风险，照实登记**：把某个键排除在判定之外这件事**没有守卫** ——
        将来有人给 `InspectionReport.as_dict()` 加第三个键、又顺手排除掉，比对器不会有任何反应。
        今天挡它的只有判据 ①–⑧ 逐键写死这一点，**那不是一条通用规则**，写进 §7.19。
      - Skill: `development-wisdom-gate-prompt.md`
- [x] **Add** 脚本**分成两个文件，这不是洁癖、是 H7 ① 逼出来的**：
      `parity.py` 是**纯比对器**（两份 `InspectionReport.as_dict()` 的 dict 进、结构化差异出，
      **不 import 本仓任何模块**）；`run.py` 只做编排。
      **起草期实测的理由逐字写在文件头**：按路径加载 `tests/unit/inspection_fakes.py`
      **会**把 `agenerp.routing` 拉进 `sys.modules`（`:39` → `explain_fakes` → `routing`），
      所以「零模型接缝」这个主张**只有比对器担得起**，`run.py` 担不起 —— **照实分开，不假装 `run.py` 也干净**。
      整体形态照抄 `tools/experiments/p1_insight_live/run.py`（**不发明新形态**）。
      **比对器的契约四条，起草期写死**：
      ① 比对面是两份 `InspectionReport.as_dict()` 的**全部三个键**（`rule_ids` / `request_count` / `hits`），
        其中 `hits` 逐条比 `Hit.as_dict()` 的**全部七个键**；
      ② **`request_count` 只记录、不参与一致性判定** ——
        **实测依据**（§1.5）：离线侧 `request_count = 10`，而 §7.10 记的活站点侧是 **9**，
        **两侧本来就不同**；把它算进判定会让比对**永远不一致**。
        ⚠️ **这是一条取舍，不是最佳实践**，正反两面见 Phase 3 的 `Decision D1`；
      ③ **比对前先断言两侧命中集合非空**，空集判为「**比不了**」而不是「一致」（H4）；
      ④ 输出是**结构化差异**（不是布尔）：哪条 `rule_id`、哪个 `subject`、两侧各是什么，都要读得出来。
      - **离线那一侧由 `run.py` 按路径加载 `tests/unit/inspection_fakes.py`**
        （**不复制夹具、不下沉它**，Non-Goals 12）。
        ⚠️ **`run.py` 用哪个加载器都行** —— 它按构造已经不干净（加载夹具就会拉进 `agenerp.routing`，§6 H7），
        所以这里不设约束；**但判据文件必须用 `_load_run()` 那种纯 `importlib` 的写法**（判据 ⑩），
        **两处要求不同不是自相矛盾，是因为两个进程要承担的主张不同**
      - Skill: `development-wisdom-gate-prompt.md`
- [x] **Proof** `tests/unit/test_pack_parity_harness.py`，**至少十一条**（每条注明挡哪种假实现，
      **全部走假两侧、零站点、零 LLM**）：
      ① 两侧逐字相同 → 判一致；
      ② 一侧少一条命中 → 判不一致，**且差异对象指名是哪条 `rule_id` 的哪个 `subject`**；
      ③ 一侧的 `quantity` 差 1.0 → 判不一致（挡「只比 `rule_id` 不比数」）；
      ④ 一侧的 `measures` 内容不同而 `quantity` 相同 → 判不一致（挡「只比七个键里的一个」）；
      ⑤ **两侧都空 → 判「比不了」，不判「一致」**（挡 H4 那种假实现）；
      ⑥ 一侧空、另一侧非空 → 判不一致（且不许崩）；
      ⑦ **顺序无关**：一侧命中列表倒序 → 仍判一致（否则比对器在测排序，不是在测内容）；
      ⑧ `rule_ids` 不同而 `hits` 相同 → 判不一致（挡 H3 那种假实现）；
      ⑨ **零 LLM 两条**：(a) 全新解释器（子进程）里 `import`
        `tools/experiments/p1_pack_parity/parity.py` 之后 `agenerp.routing` **不在 `sys.modules`**
        —— ⚠️ **主语是比对器，不是 `run.py`**，理由见 §6 H7 那一格的实测；
        (b) `ChatAdapter` 构造面整体替身在整条比对链上计数为 **0**，
        **并配两条对照**：**阳性对照**（故意调一次 → 该探针必须发红；没有它，(b) 是恒真的）
        与**探针默认关闭对照**（照抄 `tests/unit/test_inspection_rules.py:254`
        `test_h2_the_probe_is_off_by_default`，它的 docstring 逐字「否则上面那条阳性对照
        **可能红在别的原因上**」）—— **三条腿都要，先例有三条就抄三条，不抄两条** → 回填 **H7**；
      ⑩ **判据测的必须是出货的那份代码**：本文件按路径加载
        `tools/experiments/p1_pack_parity/parity.py`，**照抄 `tests/unit/test_insight_live_harness.py`
        的 `_load_run()`（纯 `importlib`）而不是 `explain_fakes.py:39` 的 `load_repo_module`** ——
        后者会把 `agenerp.routing` 拖进判据进程，白白污染 ⑨(b) 的观测面；
        **且必须继承那条纪律：源文件不存在就是红，不是少跑几条判据**
        （`explain_fakes.py:40` 逐字「**源文件没了就是红**，不是少跑几条判据」）。
        **不在判据文件里另写一份比对逻辑。**
        ⚠️ **没有这一条，R5 的整个缓解就是空的** —— `tools/` 没有 CI 覆盖，
        判据若测的是自己的副本，那份出货的脚本就一条判据都没有；
      ⑪ **离线那一支一次网络都不打**：把 `urllib.request.urlopen` 换成一被碰就炸的替身
        （照抄 `no_model_calls` 的手法），⑪ 之外的全部判据在该替身下**照样全绿**
      - Skill: `none`
- [x] **Proof · 变异自查 M1–M9**（见下表），逐条施加 → 复跑 → 还原，
      **逐条记红在哪一条断言上**；有绿的**就地补断言并登记为新的 M 编号**
      - Skill: `none`

#### 变异自查清单（起草期写死）

| # | 变异 | 预期打红的判据 |
|---|---|---|
| M1 | 比对器把「两侧都空」判为一致 | Phase 3 ⑤ |
| M2 | 比对器只比命中**条数** | Phase 3 ② 或 ③ |
| M3 | 比对器只比 `rule_id`，不比 `quantity` | Phase 3 ③ |
| M4 | 比对器只比 `quantity`，不比 `measures` | Phase 3 ④ |
| M5 | 比对器把一侧缺失的规则**静默跳过** | Phase 3 ② |
| M6 | 比对器按列表下标比（顺序敏感） | Phase 3 ⑦ |
| M7 | 比对器把 `rule_ids` 排除在比对面之外 | Phase 3 ⑧ |
| M8 | 在 **`parity.py`** 里 `import agenerp.routing`，并在链上调一次 `ChatAdapter` | Phase 3 ⑨ **两条各打红一条**（(a) 进程级探针 · (b) 替身计数）—— **两条都要红**，只红一条就说明另一条是恒真的 |
| M9 | 把 `parity.py` 的比对逻辑改坏（例如只比 `rule_id`），**判据文件一个字不动** | Phase 3 ⑩ 那条按路径加载 ⇒ ①–⑧ 里至少一条必须红。**若全绿，说明判据测的是自己的副本、不是出货的那份**，就地改成按路径加载并复跑 |

⚠️ **M8 刻意同时触碰两个可观测量**：本仓已实测过「同一个变异对函数级绿、对子进程红」这种形态
（`2026-08-24-2109-1` §12.3 的 M8），**一个观测量不够**。

#### 变异自查的**实测结果**（执行期填 · 逐条施加 → 复跑 → 还原）

复跑命令一律 `python3 -m pytest tests/unit/test_pack_parity_harness.py -q`；
基线 **25 passed**（本文件判据 25 条，含 ①–⑪ 与编排面 4 条）。
还原自查：`diff /tmp/parity.orig.py tools/experiments/p1_pack_parity/parity.py` → **逐字相同**。
**九条无一留在绿。**

| # | 施加的变异（逐字） | 实测结果 | 红在哪一条断言上（测例名） |
|---|---|---|---|
| M1 | `if len(empty) == len(SIDES):` → `if False:`（两侧都空判为一致） | **2 failed, 23 passed** | `test_two_empty_sides_are_incomparable_not_identical` · `test_two_empty_sides_stay_incomparable_even_when_rule_ids_match`（判据 ⑤）|
| M2 | `"equal": not only_offline and not only_live` → `len(offline) == len(live)`（只比条数） | **2 failed, 23 passed** | `test_a_one_point_zero_quantity_drift_is_judged_different`（判据 ③）· `test_measures_drift_with_an_unchanged_quantity_is_judged_different`（判据 ④）。⚠️ **照实记**：判据 ② 在此变异下**仍绿**（那条测例两侧条数是 2 vs 1，条数比对照样发红），预期表写的是「② 或 ③」，红的是 ③ |
| M3 | `_fingerprint` 只取 `pack_id`/`rule_id`/`subject`（只比 `rule_id`，不比数） | **2 failed, 23 passed** | `test_a_one_point_zero_quantity_drift_is_judged_different`（判据 ③）· `test_measures_drift_…`（判据 ④）|
| M4 | `_fingerprint` 排除 `measures`（只比 `quantity`，不比 `measures`） | **1 failed, 24 passed** | `test_measures_drift_with_an_unchanged_quantity_is_judged_different`（判据 ④）|
| M5 | `_hit_diff` 把「只在一侧出现的 `rule_id`」整条静默滤掉 | **3 failed, 22 passed** | `test_a_hit_missing_on_one_side_is_named_by_rule_id_and_subject`（判据 ②）· `test_one_empty_side_is_judged_different_and_does_not_crash`（判据 ⑥）· `test_main_exits_non_zero_and_still_lands_the_evidence_when_sides_differ`（编排面）|
| M6 | `_hit_diff` 开头改成按列表下标逐位比（顺序敏感） | **6 failed, 19 passed** | `test_reversing_one_sides_hit_list_is_still_identical`（判据 ⑦，靶心）· 另五条：② ③ ④ · `test_a_duplicate_hit_on_one_side_is_still_different` · 编排面那条 |
| M7 | `rule_ids["equal"]` 硬写成 `True`（把 `rule_ids` 排除在判定之外） | **2 failed, 23 passed** | `test_rule_ids_drift_with_identical_hits_is_judged_different`（判据 ⑧）· `test_rule_ids_are_compared_with_their_order`（判据 ⑧ 的顺序半）|
| M8 | 在 **`parity.py`** 顶部 `from agenerp.routing.adapter import ChatAdapter`，并在 `compare()` 里 `try: ChatAdapter(None) except Exception: pass` | **2 failed, 23 passed** —— **两个可观测量各红一条，正是预期** | `test_h7a_importing_the_comparator_never_pulls_in_the_model_face`（判据 ⑨(a)，子进程导入图）· `test_h7b_the_whole_parity_chain_makes_zero_model_calls`（判据 ⑨(b)，替身计数由 0 变 1）|
| M9 | `_fingerprint` → `{"rule_id": hit["rule_id"]}`（把出货的 `parity.py` 改坏，**判据文件一个字不动**） | **2 failed, 23 passed** | `test_a_one_point_zero_quantity_drift_is_judged_different`（判据 ③）· `test_measures_drift_…`（判据 ④）⇒ **判据测的确实是出货那份**，不是自己的副本 |

Exit Criteria:

- [x] **十一条**判据（①–⑪，其中 ⑨ 含 (a) + (b) 及其两条对照，共四条断言）全绿；**回填 H6 与 H7**；
      `python3 -m pytest tests/unit -q` **只增不减** —— 实跑 exit 0 · **`697 passed`**（基线 `672` **+25**，
      新增的 25 条全在 `tests/unit/test_pack_parity_harness.py`：①–⑪ 之外另有 4 条编排面与 2 条比对面形状守卫）
- [x] M1–M9 逐条有红/绿记录，且**逐条指名是哪一条断言红的**；无一条留在绿
      （见上「变异自查的**实测结果**」表；还原自查 `diff` 逐字相同）
- [x] **本 phase 一次站点请求都没发** —— 判据是 ⑪ 那条替身（`urlopen` 一被碰就炸），
      **不是**「判据文件里零 `SiteClient` 真实构造」：`fakes` 建的假站点**本来就要**真构造一个
      `SiteClient` 再塞进假 transport，那句话按构造为假，**不写它**。
      ⚠️ 实现上那个替身是 **`autouse` 的**：本文件除 ⑨(a) 的子进程外**每一条**判据都在它下面跑，
      并且 ⑪ 自己先反证替身在位（`pytest.raises(NetworkCallDetected)` 打一次 `urlopen`）
- [x] **出货那个入口点自己被跑过一次**：`python3 tools/experiments/p1_pack_parity/run.py --offline-only`
      → **exit 0**（**无站点、无凭据**，因此与 `Decision D2` 不冲突）。
      实跑打印 `离线命中 2 条；行源请求 10 次`。
      ⚠️ **这一条补的是 D2 记下的那笔残余**：D2 把活跑改成同进程驱动器之后，
      `if __name__ == "__main__"` 那一段成了**没人跑过的死代码**，
      而它所在的目录 `ruff` 与 CI 都看不到（R5）。**离线支跑一次就够，不需要站点。**
- [x] `git status --porcelain -- agenerp/ industry-packs/ tests/unit/inspection_fakes.py` → **无输出**（exit 0）
- [x] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → exit 0
      （`All checks passed!`）
      （⚠️ **作用域不含 `tools/`** —— §1.4 的已登记缺口，**照实记，不代人处置**：
      本 plan 新增的 `parity.py` 与 `run.py` **没有被 `ruff` 扫过一次**，
      钉着它们的只有判据 ⑩ + 变异 M9 那条「按路径加载出货那份」的纪律）
- [x] `docs/logs/` 更新

### Phase 4 — 用 Phase 3 那条链跑一次两侧

Status: completed
Targets: `docs/evidence/p1-pack-parity/`（新建：`offline-hits.json` · `live-hits.json` ·
`parity.json` · `README.md`）。⚠️ **前两个文件名叫 `-hits` 但存的是整份
`InspectionReport.as_dict()`**（三个键都在：`rule_ids` 撑 H3 · `request_count` 撑 H5 · `hits` 撑 H2/H4）——
只存 `hits` 会让 H3 与 H5 在复算时取不到数
Skill: `none`
Item Types: `Proof | Decision`（4 项 `Proof` + 1 项 `Decision`）
Prereqs: Phase 1 的 H1 成立；Phase 3 完成（**落进架构文档的那个结论必须由被判据挡着的那条链产出**）

- [x] **Proof · 跑一次**：由 `Decision D2` 选定的**短驱动器**在**同一个进程里**调
      `run.main(argv, wiring=…)`（离线侧 + 活站点侧各一遍；**不是裸 `python3 run.py`**，理由见 D2），
      三份 JSON 落盘 → 回填 **H2 / H3 / H4 / H5**。
      ⚠️ **不许在这一步临时另写一个比对** —— 结论只能来自 Phase 3 那条链（本 phase 的存在理由）。
- [x] **Proof · 零写读回**：取一次 **H9 的「后」** 计数与 `modified`，与 Phase 1 的「前」逐条对照 → 回填 **H9**
- [x] **Proof · 活跑那一次自己的零模型观测**（**不许把 Phase 3 的结论搬过来当证据**）：
      Phase 3 的 H7 是在**假两侧**上测的，而 §7.19 与证据 README 要声称的是**这一跑**零模型调用 ——
      **两者不是同一次跑**。本项要求**这一跑自己**留下两个可观测量：
      ① **驱动器进程自己的 `os.environ` 里没有任何 LLM 凭据键**：
      在驱动器里断言 `sorted(k for k in os.environ if "DASHSCOPE" in k or "AGENERP_LLM" in k) == []`，
      并把那个（空）清单原样落进 README。
      ⚠️ **不用 `env | grep -c …`**：两处都错 —— ⓐ D2 之后活跑在**驱动器进程**里发生，
      shell 的环境不是那个进程的环境；ⓑ `grep -c` 在计数为 0 时**退出码是 1**，
      在 `set -euo pipefail` 下**通过的那一支反而会把记录步骤打断**；
      ② **替身计数为 0**，且**替身由观测方装、不由被观测方自装**（`Decision D2`，下）。
      ⚠️ **「Non-Goals 9 写了不许调」不是观测量** —— 硬约束 ① 逐字禁止用「说好了不会」代替判据。
      ⚠️ **① 单独不够，必须与 ② 合取**：凭据未设只能证明「调了也会失败」，
      **区分不了「没调」与「调了但失败」** —— 它是前置条件检查，不是对这一跑的观测。
      - Skill: `none`
- [x] **Decision D2 · 那个替身装在哪一侧（起草期裁定，执行期不许现编）**
      - **选中 (a)：给 `run.py` 开一条注入接缝，活跑由一个短驱动器在**同一个进程里**发起。**
        接缝形状**照抄** `tools/experiments/p1_insight_live/run.py:469`
        （实读逐字 `def main(argv: list[str] | None = None, *, wiring: Callable[[Any], dict] | None = None) -> int`）。
        Phase 4 第 1 项的命令随之**就是那个驱动器**，不是裸 `python3 run.py` ——
        **子进程里 monkeypatch 不到父进程的类，「在外层套一个替身」对子进程调用按构造做不到。**
      - 备选 (b)「`run.py` 自己在启动时装一个一碰就炸的替身，观测量是『装着替身跑完且退 0』」
        → **否决**：那是**被观测方自报**的证据。同一份先例自己的规矩 3 逐字写着
        「账本条数与**独立计数探针**对账 —— **从账本自己数账本是同义反复**」。
        ⚠️ **否决它不是因为它没用**（它确实能挡住真调用），是因为它把证据的独立性丢了；
        本 plan 取更贵但独立的那条。
      - 备选 (c)「跑完之后静态 grep `run.py` 有没有 `ChatAdapter`」→ **否决**：
        静态文本判不了运行期，且 `run.py` 按构造 import 得到 `agenerp.routing`（§6 H7），
        grep 出 0 与真的没调**不是同一件事**。
      - **残余风险**：(a) 让活跑走一条**与裸命令不同的入口**（驱动器 vs `python3 run.py`）。
        缓解是驱动器**只做两件事**：装替身、调 `run.main(argv, wiring=...)`；
        **它不复制 `run.py` 的任何逻辑**，且这一点由判据 ⑩ 的同一条纪律（按路径加载出货那份）覆盖。
        ⚠️ **照实记**：活跑那一支「裸 `python3 run.py` 也能跑通」**本 plan 没有判据**。
        **入口点本身**由 Phase 3 Exit 那条 `--offline-only` 子进程跑覆盖（exit 0，无站点无凭据），
        **但那覆盖的是离线支，不是活跑支** —— 两者别混。
      - Skill: `none`
- [x] **Proof · 证据 README**：`docs/evidence/p1-pack-parity/README.md` 逐字写明**没证明什么**：
      「**这是一次跑，不是分布**」「**本轮零模型调用**」
      「**两侧一致证明的是『站点装载忠实于数据集』，不证明数据集本身对**」
      「**一致不等于规则表达对** —— 规则表达由它自己的 `test_case` 与阳性/阴性对照证明，不由本次比对证明」

Exit Criteria:

- [x] H2 / H3 / H4 / H5 / H9 五格「实际」列已填，每格附**命令原文 + 退出码 + 数值**
- [x] H9 两种读回口径逐条落进证据文件，**零写自证成立**（`docs/evidence/p1-pack-parity/README.md`
      「对活站点零写（H9）」那张表，前后两列逐条相同）
- [x] **这一跑自己的零模型观测两项都落进 README**，且那句「本轮零模型调用」**逐字指名它靠的是这两项**，
      不指向 Phase 3（README 里逐字写着「Phase 3 的 H7 是在**假两侧**上测的，与这一跑不是同一次跑，
      不搬过来当证据」）。
      ⚠️ **第 1 项没有吻合起草期写死的谓词，照实记在 README 与 §6 两处**：
      `sorted(k for k in os.environ if "DASHSCOPE" in k or "AGENERP_LLM" in k)` 实读**非空**，
      原样为 `["AGENERP_LLM_MODEL", "DASHSCOPE_BASE_URL"]` —— 那个过滤器**按名字前缀抓，
      抓到的不全是凭据**（模型名 + 端点地址，两个都不是凭据）。
      **预测一个字没改**；另测真正的那一条并成立：以 `_API_KEY` / `_API_SECRET` 结尾的键 → `[]`
      （`AGENERP_LLM_API_KEY` 未设 ⇒ `config_from_env()` 起不来）。第 2 项**替身计数 = 0** 吻合。
      ⚠️ 起草期就写死「第 1 项只是前置条件检查，区分不了『没调』与『调了但失败』，必须与第 2 项合取」——
      本次正是靠第 2 项承重。
- [x] H2 **吻合**（三条全一致），按 §6 写死的**第一种处置**执行（§7.10 结论由「部分一致」改成
      「逐字一致」并**追加式保留** 2026-08-24 的观测，落在 Phase 5）；
      `git status --porcelain -- industry-packs/` → **无输出**
- [x] 三份 JSON + README 落盘；**结论可复算**：把落盘的
      `offline-hits.json` 与 `live-hits.json` **两份报告**重新读回、再喂给比对器算一次，
      输出与 `parity.json` **逐字相等** —— 实跑 **exit 0**（复算脚本原文落在 README「怎么复算」一节）。
      ⚠️ **不是「把 `parity.json` 喂回比对器」** —— 它是差异输出、不是报告，类型对不上，
      那样写出来的自查跑都跑不起来
- [x] `docs/logs/` 更新

### Phase 5 — 漂移 B 改准 + 落点节 + 交接

Status: completed
Targets: `docs/architecture/module-boundaries.md`（§7.10 的「结论」半 + 新增 §7.19）·
`docs/masterplan/STATE.md`（**只追加**）· `docs/logs/2026/08-25.md`
Skill: `none`
Item Types: `Fix | Add | Proof`
Prereqs: Phase 4 完成（措辞由实测定，不由预测定）

- [x] **Fix** `module-boundaries.md` §7.10「活站点验证范围」的**结论那一半**，
      按 §6 H2 写死的三种处置之一改准。**两条硬约束**：
      ① 2026-08-24 那次的观测（`离线命中 10，站点零命中` 与它的成因）**逐字保留**，
      新结论**追加在其后**并注明日期与出处 —— 这是追加式账本，不是覆盖；
      ② **§7.10 的其余各段一个字不动**（自查：`git diff` 该文件本 phase 的删除行
      必须只落在这一段内）
- [x] **Add** `module-boundaries.md` **§7.19**（开工时若被占用则顺延，§0 第 3 条）：
      本 plan 的落点节，含 ——
      **比对器的四条契约**（尤其「`request_count` 只记录不判定」这条取舍的理由）·
      **「一致不等于数据集本身对」那句残余** ·
      **「本节判命中集合，站点侧对账（`_trap_precondition_checks`）判前提事实，
      两者不是同一件事」** 这条边界（§1.3）·
      **「比对链在 `tools/`，而 `tools/` 不在 `ruff` 与 CI 的作用域里」** 这条已知缺口
      （出处 `docs/backlog/tools-dir-has-no-static-check-coverage.md`，**归人**）·
      变异 M1–M9 的红点逐条记名
- [x] **Proof** 六条验证命令逐条跑过并记原文与退出码（§10），另加两条本 plan 专属
- [x] **Proof** `STATE.md` §3 **追加**一条证据行（只追加，红线 5），逐条含：
      ① H1–H9 九格的实测值（**并注明 H1 是复核项、不计入逐条吻合的计数**）；
      ② H2 的结论与它触发的哪一种处置；
      ③ 本 plan **未做**的四件事（未接线 `rule.lookup` · 未改任何规则 · 未对站点写 ·
      **零新增产品代码**）；④ `tools/` 无静态检查覆盖这条已知缺口**照实点名、不代人处置**；
      ⑤ **本行只追加，不改写本节任何已有行**

Exit Criteria:

- [x] §7.10 的改动**只落在「活站点验证范围」那一段**（Phase 2 改归属那一句 + 本 phase 改结论那一半，
      两次合起来的删除行不得出现在该段之外）—— 自查
      `git diff -U0 -- docs/architecture/module-boundaries.md | grep -n '^-[^-]'` → **共 3 行**，
      逐行为：「在本地活站点…跑过**一次**」「整份包（9 次只读请求），…**结论是「部分一致」，照实记**：」
      （本 phase 的两行，它们的内容**逐字重新出现在**新的「**第一次核对（2026-08-24）**」引导句里）+
      「已记 `docs/bugs/02-…`，并在…追加了 needs-human。」（Phase 2 那一行）。**三行全部落在该段之内。**
- [x] §7.19 落地，含四条契约、两条残余、一条边界、一条已知缺口
      （另加「零模型接缝的主张主语只能是比对器」与 M1–M9 红点逐条记名两小节）
- [x] `bash tools/check-masterplan-links.sh` → **exit 0**（`共校验 35 条引用，断链 0 条`）
- [x] **六条**验证命令 + **两条**专属命令逐条跑过并记退出码（§10 共 **八条**）→ **回填 H8**
- [x] `STATE.md` §3 只追加（判据：逐行子序列检查，**不用 `grep '^-[^-]'`** ——
      那条 grep 对「删掉一整条 bullet」是盲的，`2026-08-24-2311-1` 的 Closure 已实证）。
      实跑：原文件 769 行全部按顺序出现在新文件（779 行）里，**未按顺序找到的条数 = 0**
- [x] `docs/logs/2026/08-25.md` 更新

## 8. 风险

- **R1 · 「两侧一致」可能是同义反复。** 若离线那一侧的行最终来自站点，
  比对就在拿站点跟站点比，**永远绿**。缓解：离线侧**只**来自
  `tests/unit/inspection_fakes.py` 的 `seed_site()`（它由 `agenerp.seed.generate()` 派生，
  **一次站点请求都不发**），且 Phase 3 判据①–⑧ 全部走假两侧。
  ⚠️ **「有人把离线侧改成读站点」由判据 ⑪ 挡着**：把 `urllib.request.urlopen` 换成一被碰就炸的替身，
  离线那一支**照样全绿** ⇒ 它一次网络都没打。**起草期已实测这条替身可行**（离线侧在替身下跑通，
  `request_count = 10` / 2 条命中），因此 ⑪ 不是一句写着好看的话。
  另有 Non-Goals 12（`inspection_fakes.py` 只读加载）与它的 `git status` 自查作为第二层。
- **R2 · 一次跑不是分布。** 本 plan 只跑一次两侧。任何一次并发写入都会让这次比对失去意义。
  缓解：H9 的前后读回把「本轮自己写了」排除掉，**排除不掉「别人在同一分钟写了」** ——
  照实记，不说成「已隔离」。⚠️ 本仓已实证过并发写入（`0850-1` 收口时
  `tests/unit` 有 5 条被另一条工作线的改动打红）。
- **R3 · §7.10 是别人交付面的落点节，本 plan 改它的一段。** 缓解：分两次改
  （Phase 2 只改归属那一句、Phase 5 只改结论那一半）、只追加不覆盖 2026-08-24 的观测、
  `git diff -U0` 逐块核对删除行的落点。
  ⚠️ **若评审或人认为这段该由人改**（如同 `docs/audits/` 的措辞归人），**停机交人**：
  判别方式逐字为「§7.10 是否属 `docs/masterplan/`」—— 它不属（红线 5 不覆盖 `docs/architecture/`），
  且本仓已有多次先例在 `module-boundaries.md` 里「把失效归属改准」。
- **R4 · H2 若不吻合，Goal 2 仍成立、Goal 1 的漂移 B 那一半要改写。**
  起草期已把三种处置写死（§6），**执行期不许现编**，
  也不许把「仍不一致」修饰成「基本一致」。
- **R5 · 比对链落在 `tools/`，那里没有静态检查也没有 CI 覆盖。**
  这是**已登记的已知缺口**（`docs/backlog/tools-dir-has-no-static-check-coverage.md`，
  `Status: deferred`，处置者是**人**，理由是本仓已就同一处裁定过「明确不扩面」，
  **重开别人的裁定只有人能做**）。
  ⚠️ **两文件拆分之后，「脚本只做编排」这句话已经不成立** —— 判定逻辑就在
  `tools/experiments/p1_pack_parity/parity.py` 里，也就是在那个没覆盖的目录里。**照实改口**：
  真正的缓解是**判据 ⑩ + 变异 M9** —— 判据文件**按路径加载出货的那份 `parity.py`**，
  M9 把它改坏而判据一个字不动时**必须红**。⇒ 那份脚本虽然不在 `ruff`/CI 的作用域里，
  **却有一条在 CI 里跑的判据钉着它的行为**。
  ⚠️ **这是缓解不是消除**：`ruff` 仍然扫不到它（风格与未用变量一类问题无人看管），
  照实写进 §7.19。
- **R6 · 本 plan 用掉工作项 8 的第 2 个 plan 预算（表规 3）。** 此后该格 `2/2` 满，
  §11 的任何 Deferred 若要重开，须由**人**在 `02-WBS.md` 拆行/加行（红线 5，loop 无权）。
  **这一条起草期就写在这里，不等收口时才发现。**
- **R7 · 本 plan 的授权面窄，越界的诱惑具体而明确。**
  最容易越的三条：把比对器「顺手」做成 `agenerp/packs/` 的产品模块 ·
  「顺手」加一个 `parity` 子命令 · 「顺手」把 `inspection_fakes.py` 的成形逻辑下沉到产品侧。
  **三条全部在 Non-Goals 1 / 12 里点名**，且有两条机械自查钉着
  （`git status --porcelain -- agenerp/` 无输出 · `find agenerp -name '*.py' | wc -l` 逐字不变）。
  ⚠️ **这三件事本身是合理的工程改进，本 plan 不否定它们的价值** ——
  否定的是「在没有被触发的重开事件、且预算即将用尽时顺手做掉它们」。
  它们的去处是 §11 的第一条 Deferred。
- **R8 · 「零 LLM」在本 plan 是承诺也是判据。** 巡检器今天没有模型接缝（P1.5 已实测），
  但新增的脚本有可能顺手 import 进来。缓解：H7 的两个可观测量（含阳性对照）+ M8 变异。

## 9. Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理 `aaba266e7e5042029`，
  fresh session，不带起草上下文；**独立复跑了全部七个基线数字与十处出处引用，未采信起草者的转述**）
  because 两条 BLOCKING：
  **B1** Phase 1 的停机分支把「confirmed owner-doc drift」整体降级进 `Deferred` ——
  而那处漂移里有**一半（归属那一句 + `docs/bugs/02-…` 的状态行）与站点今天是什么状态无关**，
  是已入仓的事实证伪的，降级它同时违反指南第 14 条与本 plan 自己的 Closure Gate；
  **B2** 落进架构文档的那个结论由 Phase 1 一条**没有判据**的临时比对产出，
  而 Phase 3/4 建的那条**带判据**的链从未跑过真实的两侧 ——
  「两个半边只有一个有落点」，且 plan 标题承诺的「做成可复跑的东西」没有任何 Exit Criteria 关得掉。
  另四条 MAJOR（H6 两个可观测量只落地一个、阳性对照缺席 ·
  **净新增产品面（`parity.py` + CLI 子命令）不被任何已触发的重开事件覆盖，却要用掉最后一格预算** ·
  Minimum Rule 4：三个结果面各自可独立满足 ·
  §11 第三条 Deferred 谎称「从 `2109-1` 继承」——那条在前身 plan 的 §11 里根本不存在）
  与七条 MINOR（H1 不是预测 · H4 是 H2 的算术推论且在最需要它的分支里失效 ·
  Phase 2 Exit「八条」与 D1(B) 要求的第九条自相矛盾 ·
  H3 自造探针而 `InspectionReport.request_count` 早已存在 ·
  STATE 证据行被错标成 `Follow-up` · Phase 4 Exit 的「六条」与 §10 的八条对不上 ·
  Phase 2 Targets 在批准时血缘未定）。
- **上述十三条逐条已改，改法逐条如下**：
  **B1** → Phase 结构重排：漂移 A 单独成 **Phase 2「无条件」**，Phase 1 的停机分支改成三条
  （Phase 2 照常 · Phase 3 照常 · 只有 Phase 4 活跑与 Phase 5 的漂移 B 转 Deferred）；
  **B2** → **顺序整体倒过来**：先 Phase 3 建带判据的链，再 Phase 4 用它跑，
  并加一条 Exit Criteria「`parity.json` 重新喂给比对器复算，结果逐字相等」+ §7 开头逐字写死「两条路径必须是同一条」；
  **MAJOR-1** → H7 明写两个可观测量，Phase 3 判据 ⑨ 拆成 (a)(b) 并**要求阳性对照**，M8 同时触碰两者；
  **MAJOR-2** → **整个净新增产品面被删掉**：Non-Goals 1 改成「零新增产品代码」，
  比对链改落 `tools/experiments/` + `tests/unit`（本仓两次先例的形态），
  `agenerp/packs/__main__.py` 一个字节不碰，`D1` 三候选整节删除，§1.1 逐字写清「授权只有第 14 条这一处」；
  **MAJOR-3** → 结果面收敛成一个（「这次比对的实测结论 + 产出它的那条可复跑链」），
  Phase 2 的文档修正与它同源（漂移 A 是「授权来源」本身，不是另一个交付面）；
  **MAJOR-4** → §11 第三条改成「**本 plan 首次登记**」并写新的重开事件；
  **MINOR** 七条：H1 标「复核项，非预测」且逐字禁止计入吻合计数 · H4 改成「两侧各 ≥ 1」
  并逐字写明「不是 H2 的算术推论」 · D1 整节删除，第九条判据固定存在 ·
  H5 改成直接读 `InspectionReport.request_count` 并逐字写明「不另挂探针，会双计」 ·
  STATE 证据行改标 `Proof` · §10 与 Phase 5 Exit 统一成「六条 + 两条 = 八条」 ·
  Phase 2/3 Targets 全部写死。
  另**主动补了一条评审未提的自查**：`find agenerp -name '*.py' | wc -l` 开工与收口必须逐字相同
  （Non-Goals 1 的机械判据），并把 H8 的 `tests/routing` 从「+N 增长」改成「逐字不变，变了就是越界」。
- Independent draft review iteration 2: **needs revision（1 BLOCKING + 4 MAJOR）**
  （同一独立子代理 `aaba266e7e5042029`，fresh 上下文重读全文 621 行，**并独立复跑了全部七个基线数字
  与十处出处引用，未采信起草者的转述**）—— 审计器确认 v1 的两条 BLOCKING 与四条 MAJOR 里的三条
  **是实质修好的，不是改措辞**（尤其「净新增产品面被整段删掉」这一条），
  但**替代方案引入了一处新的、可测量的硬矛盾**：
  **B1** 「离线侧加载 `tests/unit/inspection_fakes.py`」与判据 ⑨(a)「`import` 脚本后
  `agenerp.routing` 不在 `sys.modules`」**按构造不能同时成立**，而绕开它的每条路要么撞红线、
  要么把判据写成恒真；
  **M1** 「判据文件里零 `SiteClient` 真实构造」**按构造为假**（假站点本来就要真构造一个再塞假 transport）；
  **M2** H6 / H8 在改版重排里**丢了回填落点**；
  **M3** 「把 `parity.json` 重新喂给比对器」**类型对不上**（它是差异输出不是报告），那条自查跑不起来；
  **M4** **没有任何东西把 `tests/unit` 的判据绑到 `tools/` 那份出货脚本上** ——
  而 R5 的整个缓解正是建立在「判据面在 CI 里」上，判据若测的是自己的副本，出货那份一条判据都没有。
- **上述五条逐条已改，改法逐条如下**：
  **B1** → 起草期**实测复现了这条矛盾**（按路径加载 `inspection_fakes.py` 后
  `'agenerp.routing' in sys.modules` → `True`，链路是 `:39` → `explain_fakes` → `routing`），
  处置是**把脚本拆成两个文件**：`parity.py` 是纯比对器（两份 dict 进、结构化差异出，
  **不 import 本仓任何模块**），`run.py` 只做编排；**⑨(a) 的主语随之收窄到 `parity.py`**，
  并在 §6 H7 与判据 ⑨ 两处**逐字写明「整个脚本那个版本按构造为假，本 plan 不提出那个主张，
  也不靠删依赖去凑它」**；
  **M1** → 那条自查整条换掉，改成判据 ⑪（`urllib.request.urlopen` 换成一被碰就炸的替身），
  并**逐字写明原来那句话为什么是假的**；
  **M2** → Phase 3 Exit 加「回填 H6 与 H7」、Phase 5 Exit 加「回填 H8」；
  **M3** → 改成「把 `offline-hits.json` 与 `live-hits.json` **两份报告**读回复算，
  输出与 `parity.json` 逐字相等」，并逐字写明原写法类型对不上；
  **M4** → 新增判据 ⑩（按 `load_repo_module` 先例**按路径加载出货的那份 `parity.py`**，
  判据文件里不许另写一份比对逻辑）+ 新增变异 **M9**（改坏 `parity.py`、判据一个字不动 ⇒ 必须红；
  全绿就说明判据在测自己的副本）。判据数 **九条 → 十一条**，变异 **M1–M8 → M1–M9**。
- Independent draft review iteration 3: **needs revision（2 MAJOR + 8 MINOR，零 BLOCKING）**
  （同一独立子代理，fresh 上下文重读全文 671 行；**并实测复核了本轮的修法** ——
  它把 `urllib.request.urlopen` 换成替身后真跑了一遍离线比对，确认「其余判据照样全绿」这个前提成立）。
  审计器确认 iteration 2 的 1 BLOCKING + 4 MAJOR **逐条是实质修好的**，
  并逐字记「两文件拆分是对的选择：plan 现在**把自己主张里不可能的那一半说出声**，
  而不是悄悄把判据改松」。本轮新出的两条 MAJOR **都是上一轮修法自己带出来的**：
  **J1** Phase 4 那一跑**没有自己的零模型观测量**，却要在证据 README 里声称「本轮零模型调用」——
  H7 是在 Phase 3 的**假两侧**上测的，**不是同一次跑**；而 `run.py` 因 B1 的修法已被明确排除在
  零 import 主张之外，靠的只剩 Non-Goals 9 与 §5.1 #8 两条**停机条件**（不是判据），
  正是硬约束 ① 禁止的「说好了不会」；
  **J2** R1 的缓解**指向一条已被 M1 的修法删掉的 Exit Criteria**，
  closure 审计照着查会查到一个幻影（实质更强了，但契约必须指向存在的东西）。
  八条 MINOR **全部是 iteration 2 那份被截断的报告里未送达的部分**。
- **上述十条逐条已改，改法逐条如下**：
  **J1** → Phase 4 新增一项 `Proof`（3/3 → **4/4**）：**这一跑自己**留两个可观测量 ——
  ① 跑前 LLM 凭据环境变量计数为 `0`；② 活跑外层套 ⑨(b) 那个 `ChatAdapter` 替身、计数须为 `0`
  （一被碰就炸 ⇒ 真调了当场非 0、落不了盘），并在 Exit 与 README 两处逐字写明
  **「不许把 Phase 3 的结论搬过来当证据」**；
  **J2** → R1 的缓解改指判据 ⑪，并附起草期的实测（替身下离线侧跑通、`request_count = 10` / 2 条命中）；
  **m1** → **H4 的「不是 H2 的算术推论」这句话是错的，整句删掉**，改成照实写「H2① 成立时它就是推论、
  不单独计一格」，并把它留在表里的真实价值写清（逼出「非空断言写在比对之前」这个实现约束）；
  **m2** → 起草期**补跑了一次离线侧**（`request_count = 10` · 2 条命中 · 3 条规则），
  §1.5 记下实测值，契约 ② 由「按构造必然不同」改成**援引实测的 10 vs 9**，
  并顺带写明「H5 若实测到 10 不是异常」；
  **m3** → 契约 ② 升格成正式的 **`Decision D1`**（选中 / 两个备选各自的否决理由 / 残余风险），
  Phase 3 的 Item Types 由 `Add | Proof` 改成 `Decision | Add | Proof`；
  **m4** → ⑨(b) 由两条腿补成**三条**（阳性对照 + **探针默认关闭对照**，
  照抄 `test_inspection_rules.py:254`，其 docstring 逐字「否则上面那条阳性对照**可能红在别的原因上**」）；
  **m5** → 证据文件的形状写死：`*-hits.json` 存的是**整份 `InspectionReport.as_dict()`**（三个键都在），
  只存 `hits` 会让 H3 与 H5 复算时取不到数；
  **m6** → ⑩ 的加载器由 `explain_fakes.py:39` 的 `load_repo_module` 改成
  `test_insight_live_harness.py` 的 `_load_run()`（纯 `importlib`，**不把 `agenerp.routing` 拖进判据进程**），
  并补上「源文件没了就是红」这条纪律；
  **m7** → Minimum Rule 4 的论证**从评审记录搬进 §1.1 正文**（closure 审计会去看的地方），
  逐字说清「漂移 A 与漂移 B 是同一段文字的两句话，分 phase 只因一句依赖实测」；
  **m8** → §11 第一条的重开事件由**析取改成合取**，逐字写明「第二个行业包」不是第二条出路，
  预算那一半照样要人先开 —— 免得下一轮盘点误读成「有了第二个包就能直接派」。
- Independent draft review iteration 4: **needs revision（1 MAJOR + 3 MINOR，零 BLOCKING）**
  （同一独立子代理，fresh 上下文重读全文 760 行，**并独立复跑了本轮新记的三个数**
  —— 离线 `request_count = 10` / 2 条命中 / 3 条规则，与起草者所记逐字相同）。
  iteration 1–3 的全部findings 经它逐条复核**均已实质关闭**；本轮新出的一条 MAJOR
  **又是上一轮修法自己带出来的**：
  **K1** J1 加的第二个观测量写的是「在 `run.py` 的活跑外层套上 `ChatAdapter` 替身」，
  而同一 phase 第 1 项用的是 `python3 …/run.py` —— **子进程里 monkeypatch 不到父进程的类**，
  这条判据**按构造跑不起来**，等于把机制留给执行期现编（而本 plan 处处禁止现编）；
  且本仓其实已有两条现成机制（`p1_insight_live/run.py:469` 的 `wiring` 注入接缝 ·
  `:145-167` 的自装计数探针），**两者在「证据是不是自报的」这一点上不等价**，
  plan 抄了那个脚本的形态却一条都没点名。
  另三条 MINOR：**k2** §6 H7 仍写「两个可观测量 + 阳性对照」而判据 ⑨(b) 已加到三条腿，
  **冻结的预注册比判据预测得少**；**k3** Phase 3 两处 bullet 指定了相反的加载器；
  **k4** R5 与 §1.4 仍写「脚本只做编排」，而两文件拆分之后判定逻辑就在 `parity.py` 里 —— 那句话已为假。
- **上述四条逐条已改，改法逐条如下**：
  **K1** → 新增 **`Decision D2`**（Phase 4 的 Item Types 随之由 `Proof 4/4` 改成
  `Proof | Decision`）：**选中 (a) 注入接缝 + 同进程驱动器**，接缝形状照抄
  `p1_insight_live/run.py:469` 的实读签名；**否决 (b) 自装替身**（理由是同一份先例自己的规矩 3
  逐字「**从账本自己数账本是同义反复**」—— 否决它**不是因为它没用，是因为它把证据的独立性丢了**）；
  **否决 (c) 事后静态 grep**（静态文本判不了运行期，且 `run.py` 按构造 import 得到 routing）。
  Phase 4 第 1 项的命令随之改成那个驱动器，并**照实登记残余**：
  「裸 `python3 run.py` 也能跑通」这件事本 plan **没有判据**。
  另把 ① 那条从独立观测量降级为**必须与 ② 合取**的前置检查，
  逐字写明它「区分不了『没调』与『调了但失败』」；
  **k2** → H7 补第三条腿与 `:254` 出处，怎么测那栏由「三处」改「四处」；
  **k3** → 逐字写明「`run.py` 用哪个加载器都行（它按构造已不干净），
  **判据文件必须用 `_load_run()`**；两处要求不同不是自相矛盾，是两个进程承担的主张不同」；
  **k4** → R5 与 §1.4 两处**照实改口**：不再说「脚本只做编排」，
  改成「真正的缓解是判据 ⑩ + 变异 M9 —— 出货那份 `parity.py` 有一条在 CI 里跑的判据钉着它的行为」，
  并保留「这是缓解不是消除，`ruff` 仍然扫不到它」。
- Independent draft review iteration 5: **needs revision（1 MAJOR + 2 MINOR，零 BLOCKING）**
  （同一独立子代理，fresh 上下文重读全文 824 行）。它逐条复核后记
  「**iteration 1–4 的全部 findings 无一仍敞着**」，并把 `Decision D2` 评为
  「本 plan 里最强的一条决定 —— 它选了更贵的那个、说清为什么、并且把因此欠下的账记下来而不是藏起来」，
  同时**独立读了先例源码而不是读 plan 对先例的转述**，确认 `wiring` 接缝返回的是**一个 pieces 字典**、
  不是一个模型，因此 D2(a) 是**照抄惯用法而不是硬套**。它另外替本 plan 复核出一条
  **plan 恰好做对了的事**：`agenerp/site.py:142` 的 `UrllibTransport` 活跑时需要真的 `urllib`，
  **把 `no_model_calls` 整份搬进 Phase 4 会当场把活跑打死** —— 本 plan 把 `urlopen` 替身
  限定在 ⑪（只在离线支）、Phase 4 只用 `ChatAdapter` 那一半，六处提及口径一致。
  本轮三条：
  **L1** §6 的 **H7 那一行被硬换行断成四行** —— 那是 k2 修法把行加长带出来的。
  GFM 的表格行必须是一个物理行，⇒ 表格在 H7 处**当场终止**，
  **H8 / H9 掉出表外渲染成普通文本**。⚠️ **这不是排版洁癖**：§6 是硬约束 ② 的**冻结预注册件**，
  收口时逐格回填的就是它；两格假设在渲染视图里根本不作为假设存在，是实打实的证据损失；
  **l2** D2 把活跑改成同进程驱动器之后，**出货脚本的 `if __name__ == "__main__"` 成了没人跑过的死代码**，
  而它所在目录 `ruff` 与 CI 都看不到；
  **l3** 观测量 ① 的命令**测错了进程、且退出码是反的** ——
  D2 之后环境在**驱动器进程**里，shell 的 `env` 不是它；且 `grep -c` 计数为 0 时**退出码是 1**，
  在 `set -euo pipefail` 下**通过的那一支反而把记录步骤打断**。
  ⚠️ **评审同时正面回答了起草者问的「(b) 是不是更务实」**：逐字「**(a) 是对的工程判断，不是洁癖论证**」——
  (b) 确实让被观测方成了自己清白的报告人。**本 plan 不因此改判。**
- **上述三条逐条已改**：
  **L1** → H7 那四行**重新接成一个物理行**（**内容一个字未改**，只改物理行数）；
  已机械复核：`| **H1**` … `| **H9**` **九行逐行自成一行且以 `|` 收尾**，
  分隔行 `|---|---|---|---|` 在位，M 表 9 行同样逐行完整；
  **l2** → Phase 3 Exit 新增一条：`python3 tools/experiments/p1_pack_parity/run.py --offline-only` → **exit 0**
  （**无站点、无凭据，与 D2 不冲突**），并逐字写明它补的是 D2 记下的那笔残余；
  D2 的残余句同步改准为「**入口点本身**由那条离线子进程跑覆盖，**但那覆盖的是离线支、不是活跑支，两者别混**」；
  **l3** → ① 改成**在驱动器里断言**
  `sorted(k for k in os.environ if "DASHSCOPE" in k or "AGENERP_LLM" in k) == []`
  并把那个空清单原样落进 README，且**逐字写明原写法错在哪两处**（测错进程 · 退出码反）。
- Independent draft review iteration 6: **acceptable as-is（零 BLOCKING / 零 MAJOR / 零 MINOR）**
  （同一独立子代理，fresh 上下文重读全文 863 行）。**它没有靠眼睛看**：
  对全部 863 行做了一次机械扫描（凡以 `|` 开头却不以 `|` 收尾、或以 `|` 收尾且含 ≥2 个 `|` 却不以 `|` 开头即报），
  输出 `BROKEN ROWS: none`，两张表各 **11 个连续物理行**（表头 + 分隔行 + 9 个数据行）；
  并确认 **H7 的内容与 iteration 5 时逐字相同**（L1 改的只是物理行数）。
  另三处它读源码复核、而不是读本 plan 的转述：
  ① `--offline-only` 那条 Exit **自足**（形态另有先例 `p1_insight_live/run.py` 的 `--inspect-only`）；
  ② l3 的过滤器 `"AGENERP_LLM" in k` **覆盖到了适配器能配置的全部三个变量**
  （`agenerp/routing/config.py:23-27` 的 `REQUIRED_ENV` 三项都以它开头），
  ⇒ 那条前置检查是**完整的**、不是部分的（`DASHSCOPE` 只是多加的一道厂商名兜底）；
  ③ 逐条核对 §9 的五轮记账与它自己发过的报告：**it1 13 条 / it2 5 条 / it3 10 条 / it4 4 条 / it5 3 条，
  五轮结论全部如实记为 `needs revision`，无一条被软化、合并或丢掉**，
  含那几条不好看的原话（「§11 第三条 Deferred 谎称『从 `2109-1` 继承』」·「按构造为假」·
  「测错了进程、且退出码是反的」），且评审给的正面评价与「(b) 是不是更务实」的回答
  **都记成评审说的，不据为起草者所有** ⇒ 满足 Minimum Rule 13 与指南的「record the iterations」。
  → **共识达成，`Plan Status` 由 `draft` 转 `active`。**
  ⚠️ 六轮之间**本 plan 之外的仓库零变更**（评审末轮实读 `git status --porcelain` 只有这份未入仓的 plan）。

## 10. Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（§7.10 两处改准 · §7.19 落地 · `docs/bugs/02-…` 状态行与 §4 改准 ·
      `docs/logs/2026/08-25.md` 有条目）
- [x] verification has run —— **八条命令逐条记原文与退出码**（**八条逐条 exit 0**：① `门禁 26 项：预期红 0，绿 26，跳过 0` + `697 passed` · ② `151 passed` · ③ `81 passed, 12 skipped` · ④ `167 passed, 1 skipped`（**逐字不变**）· ⑤ `54 passed` · ⑥ `All checks passed!` · ⑦ 3 条规则 + 各自 `test_case` 全过 · ⑧ `共校验 35 条引用，断链 0 条`）（六条基线 + 两条本 plan 专属）：
      ① `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`
      ② `python3 -m pytest tests/contracts -q`（预期 `151 passed`，逐字不变）
      ③ `python3 -m pytest tests/tools -q`（预期 `81 passed, 12 skipped`，逐字不变）
      ④ `python3 -m pytest tests/routing -q`（预期 **`167 passed, 1 skipped`，逐字不变** ——
         Non-Goals 1 承诺零新增产品模块；**变了就是越界，不是正常增长**）
      ⑤ `python3 -m pytest tests/context -q`（预期 `54 passed`，逐字不变）
      ⑥ `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
      ⑦ `python3 -m agenerp.packs validate --pack discrete` → exit 0（**WBS §4 P1.6 的验收原文，
         本 plan 一个字节没碰它，这一条是回归守卫**）
      ⑧ `bash tools/check-masterplan-links.sh` → exit 0
- [x] scoped verification is not conflated with full verification —— **逐字写明：verification scope limited**。未跑 `pytest tests -q -m "not live"`（整仓一次性），也未拿到 CI 服务端复跑；上面八条是**逐目录**跑的 —— 若未跑
      `pytest tests -q -m "not live"` 或未过 CI 服务端复跑，**逐字写「verification scope limited」**。
      ⚠️ **另有一条必须逐字写清的作用域限制**：⑥ 的 `ruff` 作用域**不含 `tools/`**，
      而本 plan 的比对脚本正落在那里（§1.4 / R5 的已登记缺口）。
      **事后补记（独立收口审计，2026-08-25）**：整仓一次性那条**已由审计者补跑** ——
      `python3 -m pytest tests -q -m "not live"` → **exit 0** · `1186 passed, 12 skipped, 21 deselected`。
      ⚠️ **「verification scope limited」这句话仍然成立、不撤销**：**CI 服务端复跑仍未拿到**，
      且 `ruff` 作用域不含 `tools/` 这条**一个字没变**
- [x] no in-scope item downgraded to deferred/follow-up —— **零降级**：H1 成立（`Closed` / `99.0`），**停机分支未触发**，Phase 1–5 五个 phase 全部照常做完 ——
      ⚠️ **若 H1 不成立触发了停机分支，这一格要逐字说清**：转 Deferred 的是
      **Phase 4 活跑与 Phase 5 的漂移 B 两项**，且那是**起草期写死的分支被实测触发**，
      不是执行期缩范围；**漂移 A（Phase 2）与整条比对链（Phase 3）零降级**
- [x] independent draft review completed and recorded（§9，六轮，第六轮 `acceptable as-is`）
- [x] text consistency verified: status, phases, gates, and log all agree（`Plan Status: completed` · 五个 phase 全 `Status: completed` 且无 `[ ]` 遗留 · `docs/logs/2026/08-25.md` 四条条目 · §6 九格全填）
- [x] closure audit was independent —— **已做**：由**独立收口审计器**（`2026-08-25-084253-mission-driver`，
      fresh session，**不带执行期上下文**）在 `65971aa` 落盘之后独立复跑并核对，记录见
      §Closure 的「**独立收口审计（事后补做，2026-08-25）**」一节。
      ⚠️ **时序照实记，不修饰**：执行期落盘时这一格是**空的** ——
      `65971aa` 的提交信息与 `docs/logs/2026/08-25.md` 都逐字记着「未做」。
      本格是**事后**由独立审计者补满的，**不是执行期就有的**
- [x] closure evidence exists in files（`docs/evidence/p1-pack-parity/` 三份 JSON + README · `docs/masterplan/STATE.md` §3 的 `[Proof] 2026-08-25T11:41Z` 证据行 · `docs/architecture/module-boundaries.md` §7.10 第二次核对与 §7.19）
- [x] **红线自证**（逐条实跑，见下）：`git status --porcelain -- tests/gates/ .github/workflows/ missions/
      docs/masterplan/DECISIONS.md docker-compose.yml industry-packs/ agenerp/
      tests/unit/inspection_fakes.py` → **无输出**；
      `find agenerp -name '*.py' | wc -l` 与开工时**逐字相同**；
      —— 实跑 **无输出**；
      `find agenerp -name '*.py' | wc -l` 与开工时**逐字相同**（开工 **56** / 收口 **56**）；
      `docs/masterplan/STATE.md` 逐行子序列检查「只增不改」—— 实跑 **原有 769 行全部按顺序在案，缺 0 行**；
      `ls tests/` 的目录集合与开工时**逐字相同**（`context contracts experiments fixtures gates routing tools unit`）
- [x] **逐字声明**：本 plan **零新增产品代码**，**未接线** `rule.lookup`，**未改任何一条规则**，
      **未对活站点做任何写**，**一个模型都没调**

## 11. Deferred But Adjudicated

### 把比对做成产品面（`agenerp/packs/parity.py` + 一个 `parity` 子命令 + 离线行源下沉）

- Classification: `out-of-scope improvement`（**不是能力问题，是授权与预算问题**）
- Why Not Blocking Closure: 本 plan 的授权只有指南第 14 条那一处（§1.1）——
  它覆盖「修两处已确认的漂移」及其必需的实测，**不覆盖净新增产品面**。
  `2109-1` §11 的四条 Deferred **无一被触发**，`STATE.md` `[resolved] 02:02Z` **未指派 successor**，
  且它的 ② 逐字把判据判给站点侧对账「**不是行业包**」。
  比对链落在 `tools/experiments/` + `tests/unit` 已足以让本 plan 的结论**被判据挡着**（Goal 3）；
  把它升格成产品面是**另一个交付面**。
- **升格时要一并解决的三件事，起草期先写清**（免得下一个 plan 重新发现）：
  ① 离线那一侧的行源今天在 `tests/unit/inspection_fakes.py`，产品入口够不着 ——
  下沉它必须配一条「两侧派生出的行逐字相等」的判据，否则是把一份数据抄成两份；
  ② 新增子命令必须证明 `validate` 的定义与帮助文本逐字未变（它是 WBS 验收原文）；
  ③ 新增 `agenerp/**/*.py` 会让 `tests/routing` 按文件数增长（`test_adapter.py:485`），
  那是正常增长，**须在该 plan 的假设表里预先算清**。
- Successor Required: `yes`。**重开事件（逐字，且刻意写成合取而不是析取）**：
  **人在 `02-WBS.md` 给它拆行/加行**（工作项 8 在本 plan 之后 `2/2` 满，
  表规 3 逐字「超过就拆行」，红线 5 只有人能做）—— **这一条是必要条件，绕不过去**。
  ⚠️ **起草期就写清，免得下一轮误读**：「出现第二个行业包 / 第二个消费者」**不是第二条出路**，
  它只是**让这件事变得值得做**的那一半；**预算那一半照样要人先开**。
  把它写成「或」会让某一轮盘点误以为「有了第二个包就能直接派」，那是错的。

### `rule.lookup` 接线

- Classification: `out-of-scope improvement`（被红线 1 保护的裁判挡住，非能力问题）
- Why Not Blocking Closure: 与 `2026-08-24-2109-1` §11 同一条，**本 plan 不重复登记、不代人裁定**。
- Successor Required: `yes` —— 由**人**裁定（批准改门禁并接线 / 维持报错并改写重开事件）。
- 重开事件：**人给出上述任一裁定时**（原文未被本 plan 改松）。
  ⚠️ 重开时须注意预算：工作项 8 在本 plan 之后 **`2/2` 满**。

### 外协那条规则的真实数据阳性对照

- Classification: `watch-only residual`
- ⚠️ **本 plan 是它的第一次登记**：`2026-08-24-2109-1` §11 只有四条 Deferred，
  **不含这一条** —— 它当时只写在该 plan 的正文与 `module-boundaries.md` §7.10 的一个小节里，
  从未被登记成带重开事件的 Deferred。**「继承」这个词在这里是错的，照实改。**
- Why Not Blocking Closure: 种子外协链完整（发多少收多少），两侧零命中是**正确行为**；
  种子被 `tests/gates/test_seed_dataset_absurdity.py`（裁判，红线 1）钉着，
  **不许为了造阳性对照往种子里加异常**。它的阳性对照落在自己的 `test_case`（合成行）。
- Successor Required: `no`。**重开事件（本 plan 新写）**：
  **出现一份真实存在外协欠收的数据集或站点**（届时才第一次有「真实数据上的阳性」可验）。

### 数据集本身对不对

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 本 plan 证的是「站点装载忠实于数据集」，
  **不证「数据集本身对」** —— 后者由 `tests/gates/test_seed_dataset_absurdity.py`（裁判，红线 1）
  与 `agenerp/seed/checks.py` 各自负责，不是比对器的活。
- Successor Required: `no`。重开事件：**出现一条「数据集本身把业务建模错了」的实测**。

## Closure

### Status Note

**`completed`（2026-08-25）。五个 phase 全部执行到底，零降级。**

结果面只有一个，它成立了：**§7.10 那一段说的话变成了真的** ——
「部分一致」被一次实测结清为 **`identical`**，且产出这个结论的是**被判据挡着的那条链**
（Phase 3 建、Phase 4 用，同一份 `parity.py`），不是临时另写的比对。

- **漂移 A（无条件）** 已改准：`docs/bugs/02-…` 的状态行与 §4 · `module-boundaries.md` §7.10 的归属那一句。
- **漂移 B（依赖实测）** 已改准：§7.10 的结论由「部分一致」改成「逐字一致」，
  **2026-08-24 那次的观测逐字保留、新结论追加在其后**（追加式，不覆盖）。
- **可复跑的链已落地**：`tools/experiments/p1_pack_parity/{parity.py,run.py}` +
  `tests/unit/test_pack_parity_harness.py`（**25 条判据**，`tests/unit` 672 → **697**）+
  `docs/evidence/p1-pack-parity/`。**结论可复算**（两份报告重新喂给比对器 → 与 `parity.json` 逐字相等，exit 0）。
- **落点节 §7.19** 已立：四条契约 · 两条残余 · 一条边界 · 一条已知缺口 · M1–M9 红点逐条记名。

**照实记两格不吻合与一处执行期发现，一个字没改预测**：

1. **H5 不吻合**：站点侧 `request_count` 实测 **10**，预测 9。起草期已写死「实测到 10 不是异常」。
   **没有为了凑那个 9 改任何一条规则或巡检器，也不猜根因。**
2. **Phase 4 零模型观测 ① 的谓词在本机不成立**：
   `sorted(k for k in os.environ if "DASHSCOPE" in k or "AGENERP_LLM" in k)` 实读
   `["AGENERP_LLM_MODEL", "DASHSCOPE_BASE_URL"]` —— 那个过滤器**按名字前缀抓，抓到的不全是凭据**。
   另测真正的那条并成立（以 `_API_KEY`/`_API_SECRET` 结尾的键 → `[]`）。
   起草期已写死「本项只是前置条件检查，必须与替身计数合取」—— 本次靠 ② **替身计数 `0`** 承重。
3. **变异 M2 的红点落在 ③④ 而不是预期表写的「② 或 ③」里的 ②**：
   判据 ② 那条测例两侧条数是 2 vs 1，纯条数比对照样发红，所以它在 M2 下**仍绿**。
   预期表写的是「② **或** ③」，红的是 ③ ⇒ **吻合**，但差别照实记下来。

**⚠️ `closure audit was independent` 的时序照实记，不修饰**：
**执行期落盘（`65971aa`）时这一格是空的** —— 当时由单一执行器完成，没有独立子代理做收口审计，
提交信息与 `docs/logs/2026/08-25.md` 都逐字记着「未做」。
该 gate 由**事后**的独立收口审计补满（记录见下「独立收口审计（事后补做，2026-08-25）」），
**不是执行期就有的**。

**⚠️ verification scope limited（仍然成立，不撤销）**：八条验证命令是**逐目录**跑的；
整仓一次性那条**已由事后的独立审计者补跑**（`pytest tests -q -m "not live"` → exit 0 ·
`1186 passed, 12 skipped, 21 deselected`），但 **CI 服务端复跑仍未拿到**。
另一条作用域限制**一个字没变**：⑥ 的 `ruff` **不含 `tools/`**，而本 plan 的比对脚本正落在那里。

### Closure Audit Evidence

**八条验证命令**（命令原文 + 退出码，逐条实跑）：

| # | 命令 | 退出码 | 输出 |
|---|---|---|---|
| ① | `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | **0** | `门禁 26 项：预期红 0，绿 26，跳过 0` + `697 passed` |
| ② | `python3 -m pytest tests/contracts -q` | **0** | `151 passed`（逐字不变）|
| ③ | `python3 -m pytest tests/tools -q` | **0** | `81 passed, 12 skipped`（逐字不变）|
| ④ | `python3 -m pytest tests/routing -q` | **0** | `167 passed, 1 skipped`（**逐字不变 ⇒ 零新增产品模块**）|
| ⑤ | `python3 -m pytest tests/context -q` | **0** | `54 passed`（逐字不变）|
| ⑥ | `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | **0** | `All checks passed!`（⚠️ **作用域不含 `tools/`**）|
| ⑦ | `python3 -m agenerp.packs validate --pack discrete` | **0** | 3 条规则 + 各自 `test_case` 全过（回归守卫，本 plan 一个字节没碰它）|
| ⑧ | `bash tools/check-masterplan-links.sh` | **0** | `共校验 35 条引用，断链 0 条` |

**本 plan 专属的两条实跑**：

- `python3 tools/experiments/p1_pack_parity/run.py --offline-only` → **exit 0**
  （`离线命中 2 条；行源请求 10 次` —— 出货入口点自己被跑过一次，无站点无凭据）
- `AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 /tmp/agenerp-parity-driver.py`
  （`Decision D2` 的短驱动器：装替身 + 调 `run.main(sys.argv[1:], wiring=run.live_wiring)`）→ **exit 0**，
  实读 `{"driver_exit_code": 0, "llm_named_env_keys_verbatim": ["AGENERP_LLM_MODEL", "DASHSCOPE_BASE_URL"], "llm_credential_env_keys": [], "chat_adapter_probe_calls": 0}`

**红线自证**（逐条实跑）：

- `git status --porcelain -- tests/gates/ .github/workflows/ missions/ docs/masterplan/DECISIONS.md docker-compose.yml industry-packs/ agenerp/ tests/unit/inspection_fakes.py` → **无输出**
- `find agenerp -name '*.py' | wc -l` → **56**（开工 56，**逐字相同**）
- `ls tests/` → `context contracts experiments fixtures gates routing tools unit`（与开工**逐字相同**，未新增顶级目录）
- `docs/masterplan/STATE.md` 逐行子序列检查 → 原有 **769 行全部按顺序在案，缺 0 行**（779 行，只增不改）
- 证据仓 `XM_PATH` 未写入（红线 6）；未生成任何运行时 Server Script（红线 7）

**收口时的仓库状态**（`git status --porcelain`）：

```
 M docs/architecture/module-boundaries.md
 M docs/bugs/02-live-site-sales-order-is-not-closed-so-the-account-green-trap-is-absent.md
 M docs/logs/2026/08-25.md
 M docs/masterplan/STATE.md
?? docs/evidence/p1-pack-parity/
?? docs/plans/p1-insight/2026-08-25-1026-1-industry-pack-live-parity.md
?? tests/unit/test_pack_parity_harness.py
?? tools/experiments/p1_pack_parity/
```

**逐字声明**：本 plan **零新增产品代码**，**未接线** `rule.lookup`，**未改任何一条规则**，
**未对活站点做任何写**，**一个模型都没调**。

### 独立收口审计（事后补做，2026-08-25）

- **Auditor / Agent**：独立收口审计器 `2026-08-25-084253-mission-driver` ——
  **fresh session，不带执行期上下文**，按 `docs/plans/00-plan-authoring-and-execution-guide.md`
  的「When Closing」逐条核。
- **它不是冷读，是复跑**：审计者**自己重跑**了下列各项，**未采信执行期的转述**：
  - **八条验证命令逐条自跑** → **八条全部 exit 0**，输出与上表**逐字相同**：
    `门禁 26 项：预期红 0，绿 26，跳过 0` + `697 passed` · `151 passed` ·
    `81 passed, 12 skipped` · `167 passed, 1 skipped` · `54 passed` ·
    `All checks passed!` · `packs validate --pack discrete` 三条规则全过 ·
    `共校验 35 条引用，断链 0 条`。
  - **补跑整仓一次性**：`python3 -m pytest tests -q -m "not live"` → **exit 0** ·
    `1186 passed, 12 skipped, 21 deselected`（执行期未跑的那条，审计期补上）。
  - **自己重施了一条变异（M1）**：把出货的 `parity.py` 里
    `if len(empty) == len(SIDES):` 改成 `if False:`（文件级 `cp` 备份，**全程未用 `git checkout`**，
    未触碰任何红线路径）→ `python3 -m pytest tests/unit/test_pack_parity_harness.py -q` →
    **`2 failed, 23 passed`**，红点是 `test_two_empty_sides_are_incomparable_not_identical` ·
    `test_two_empty_sides_stay_incomparable_even_when_rule_ids_match` ——
    **与变异表记录逐字相同**；随后按备份还原，`git status --porcelain -- tools/` → **无输出**。
    ⇒ **判据确实钉在出货那份 `parity.py` 上**（R5 的缓解为真，不是一句写着好看的话）。
  - **自己复算了结论**：按证据 README「怎么复算」一节原样执行 ——
    把 `offline-hits.json` 与 `live-hits.json` 重新喂给出货的 `compare()`，
    输出与 `parity.json` **逐字相等** → **exit 0**。
  - **逐处核对落盘的文档**：`module-boundaries.md` §7.10 的「第二次核对（2026-08-25）」
    与 §7.19（四条契约 · 两条残余 · 一条边界 · 一条已知缺口 · M1–M9 红点记名）**均在案**；
    `docs/bugs/02-…:3` 状态行已是「**已由人修复**（`484c123`）」；
    `docs/masterplan/STATE.md:770` 的 `[Proof] 2026-08-25T11:41Z` 证据行在案；
    `docs/logs/2026/08-25.md` 四条条目在案。
  - **红线独立复核**（按 `git show --name-only 65971aa` 的实际改动清单，不看执行期的自述）：
    该提交触碰的 12 个文件里**没有一个**落在 `tests/gates/**` · `.github/workflows/**` ·
    `missions/**` · `docs/masterplan/DECISIONS.md` · `agenerp/**` · `industry-packs/**` ·
    `tests/unit/inspection_fakes.py`；`git show 65971aa -- docs/masterplan/STATE.md | grep -c '^-[^-]'`
    → **0**（只追加）；`git show 65971aa -- docs/architecture/module-boundaries.md | grep '^-[^-]'`
    → **恰 3 行**，逐行落在 §7.10「活站点验证范围」小节内，**与 Phase 5 Exit 的自查逐字吻合**；
    `find agenerp -name '*.py' | wc -l` → **56**；
    `ls tests/` → `context contracts experiments fixtures gates routing tools unit`（未新增顶级目录）。
- **审计结论**：`accept` —— 五点一致性成立（`Plan Status: completed` · 五个 phase 全
  `Status: completed` 且无 `[ ]` 遗留 · 各 phase Exit Criteria 全 `[x]` ·
  Closure Gates 全 `[x]` · Closure 证据在文件里可查），**没有发现被藏进 Deferred 的在场缺陷或契约漂移**：
  H5 的 `10 vs 9`、`tools/` 无 `ruff`/CI 覆盖、变异 M2 红点落在 ③④ 而非 ② ——
  **三处都在正文里逐字记着，不是藏起来的**。
- ⚠️ **审计者没有做、因此不声称的两件事**：① **未拿到 CI 服务端复跑**（本机复跑不等于 CI）；
  ② **未重新对活站点跑一次比对**（那需要活栈；本次比对的活站点侧数据由审计者
  **从落盘证据复算**核对，不是重新观测一次站点）。

### Follow-up
- §11 的四条 Deferred **一条未动**，重开事件逐条如原文。
  ⚠️ **工作项 8 的 plan 预算此后 `2/2` 满**（表规 3）：其中任何一条要重开，
  须由**人**在 `02-WBS.md` 拆行/加行（红线 5，loop 无权）。
- **H5 的 10 vs 9 没有根因** —— 本 plan 按裁判规则 3 不猜。
  下一次比对若仍是 10，那条差异就该由一个专门看取数路径的 plan 去解释。
- **`tools/` 无静态检查与 CI 覆盖**这条已知缺口仍敞着
  （`docs/backlog/tools-dir-has-no-static-check-coverage.md`，`Status: deferred`，**处置者是人**）。
  本 plan 又往那个目录里放了两份脚本，**照实点名，不代人处置**。
