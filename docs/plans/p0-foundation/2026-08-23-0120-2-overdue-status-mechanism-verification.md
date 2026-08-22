# 2026-08-23-0120-2 取证 `_overdue_checks` 的成立机制，并让它的红自解释

> Plan Status: active
> Mission: p0-foundation
> Work Item: 工作项 7 · 种子数据（站点侧对账那一段；**不改工作项 7 的状态值**）
> Last Reviewed: 2026-08-23
> Source: `docs/architecture/system-baseline.md` §14.5 与 `docs/backlog/p0-foundation-roadmap.md:84`
> 逐字登记的**未查证项**；以及 `agenerp/seedsite.py:824` 取回 `due_date` 却一行未用所留下的取证空洞
> Related: `2026-08-22-2325-2-ci-seed-site-verification.md`（登记该未查证项的那个 plan）·
> `2026-08-22-2107-2-seed-documents-site-computed-backlog.md`（交付 `--verify-site` 的 plan）
> Audit: required
> 执行顺序：**2 / 2**。前驱 `2026-08-23-0120-1-ci-unit-and-contracts-coverage.md` 把 `tests/unit` 搬上 CI，
> 本 plan 新增的单测应落在那个复跑面内。⚠️ **该前驱此刻是 `Plan Status: draft`，尚未通过它自己的评审、更未落 `main`**——
> 因此「新单测会被 CI 复跑」目前是**无支撑的假设**，处置见 `## Deferred But Adjudicated` 末条。

## Current Baseline

全部为 2026-08-23 在 `main`（`577e401`，`git status --porcelain` 无输出）上的实读，行号逐条核对过：

1. **代码把一条从未取证的机制写成了事实。** `agenerp/seedsite.py:811-816` 的 docstring，承重句在 `:813-815`：
   「`status` 是站点拿**真实时钟**跟 `due_date` 比出来的，不是拿数据集的 `as_of` 比的。
   种子日期固定在过去，故恒成立 —— 但这条断言依赖『今天 > due_date』，不写出来会被误读成结构性成立。」
   ⚠️ **这句话本仓从未对它取过证**：没有任何一处记录读过 ERPNext 的源码或做过实验来确认「谁写的 `status`、什么时候写」。
2. **owner doc 把相邻的那个未知登记成了未知。** `docs/architecture/system-baseline.md` §14.5 逐字：
   「`status` 是不是由 `scheduler` 而非提交时的即时计算给出，**本 plan 没有查证**……它仍是这个 job 未来最可能先红的一项。」
   `roadmap:84` 是同一句的转录。
   ⚠️ **这两处不是互相矛盾的** —— 第 1 条讲的是「`status` 拿什么跟什么比」，第 2 条讲的是「谁写、什么时候写」，
   是两个命题。⚠️ **下面这半句是推理，不是实读**（本节其余各条都是实读，此处单独标出）：
   「`scheduler` 刷新与提交时即时计算**都**是拿真实时钟比 `due_date`」—— 它是「两处不矛盾」这个结论的前提，
   **由 Proof A① 负责证实或证伪**；若被证伪，Baseline 2 的结论需要重写。
   `docs/context/project-context.md:57` 末句与 `docs/architecture/module-boundaries.md:1149-1151`
   也各自复述了第 1 条的说法，三处**一致**。
   **本 plan 因此不主张「确认的 owner-doc 漂移」，不援引 Minimum Rule 14。** 缺口的诚实名字是：
   **一条被 docstring 加**三处活陈述**反复复述、却从未取证的机制陈述**
   —— `docs/context/project-context.md:57` 末句 · `docs/architecture/module-boundaries.md:1149-1151` ·
   `docs/backlog/gate-proposal-seed-dataset.md:93-94`（⚠️ **第三处是评审第 3 轮才抓出来的**，
   它是给人「采纳时可直接照抄」的门禁提案正文，`:96` 逐字这么写，
   **漏掉它等于把一条未取证的机制陈述留在人将来要照抄的文本里**）。
   ⚠️ **`system-baseline.md:706` 不计入这三处**：它是**前一个 plan 起草理由的历史记录**，
   且已被同节 `:711-713` 当场限定，不是独立的活断言 —— 因此 Phase 3 对它**只追加补记、不改写**
   （**这一条不进分流**：历史记录无所谓「改准」，它记的就是当时的想法）。 上面那三处活陈述是否需要改准，由 Phase 1 的实测决定。
3. **判据实现取回了证据却扔掉了。** `agenerp/seedsite.py:810-832` 的 `_overdue_checks`：
   `:824-825` 取 `("name", "status", "outstanding_amount", "due_date", "docstatus")`，
   `:826` 筛 `status == "Overdue" and int(docstatus) == 1`，`:827` 合计 `outstanding_amount` 与
   `CH.EXPECTED_*_OVERDUE` 比。**`due_date` 取回来了但一行没用。**
   后果具体：站点回零张 `Overdue` 时 `total = 0.0` ≠ 期望值 → 这条**会红**，
   但红出来只有一个对不上的金额与「命中 0 张：无」，**读的人无从判断是哪一半坏了**
   （站点没算出 `Overdue`？`due_date` 还没到期？发票压根没提交？站点上根本没有这两张发票？）。
4. **种子日期是冻结常量，不读时钟**：`agenerp/seed/model.py:50-52` 逐字
   `BASE_DATE = date(2026, 2, 2)` / `INVOICE_TERM_DAYS = 30` / `OVERDUE_DAYS = 3`；
   `model.py:92-93` `day(offset) = (BASE_DATE + timedelta(days=offset)).isoformat()`。
   `documents.py:260` 销售发票 `due_date = day(6 + 30) = day(36)` → **`2026-03-10`**；
   `documents.py:283` 采购发票 `due_date = day(5 + 30) = day(35)` → **`2026-03-09`**（两值已实算核对）。
   `agenerp/seed/checks.py:106-123` 的**本仓侧**判定用数据集自带的 `as_of`（`dataset.py:51` = `day(39)` = `2026-03-13`），
   **与站点侧那条走的是两套不同机制**——本仓侧不读时钟，站点侧读。
5. **装载器不给站点喂 `status`**（支持「站点自己算出来」这个说法的直接证据）：
   `agenerp/seedsite.py:538-547` / `:551-557` 发给站点的**载荷里没有 `status` 这个字段**（载荷本身有十来个字段）；
   `documents.py:262` / `:285` 里那个 `"status": "Overdue"` **只存在于本仓的数据集**，没有被发出去。
6. **compose 起了 `scheduler` 服务**（`docker-compose.yml:250`），因此「`status` 由 scheduler 定期刷新」
   这条路径在本仓栈上**物理可达**，不能靠「没起 scheduler」排除。
7. **唯一一次 CI 实测只到这么窄**：`gates-l2-seed`（run `32585965892`）在一个存活约 40 秒的全新 runner 站点上，
   两条 overdue 各命中 1 张发票并全绿。站点只活了 40 秒这件事**暗示**不是靠日调度刷出来的，
   但 §14.5 已经逐字禁止把暗示读成结论。
8. **本 plan 要改的那个函数**已经有单测覆盖（本条是评审抓出的、初稿漏掉的基线，Minimum Rule 1）：
   `tests/unit/test_seedsite_documents.py:363-401` 有 `FakeVerifySite`（**已经覆盖两个发票 DocType，
   用的就是同一批单据号 / 日期 / `docstatus`**），`:412` 有 `assert len(results) == 9`
   （**即「项数不得变」这条机械判据已经存在，不需要本 plan 新造**），
   `:464-469` 有 `test_verify_site_goes_red_when_an_invoice_is_not_overdue`。
   → 初稿计划「新建一个文件、造第二个假站点」，**属于重复造夹具**，已改为 D3 明确裁定。
9. **`tests/unit` 现为 288 条**（`python3 -m pytest tests/unit -q --collect-only` 实测）。
   该数字被三处 owner doc 写死：`docs/context/project-context.md:57` ·
   `docs/architecture/module-boundaries.md:1142` · `:1212`。
   **本 plan 新增单测会让它变大 → 那三处当场变成假陈述**，处置见 Phase 3。
10. **单据号不是站点承诺，不许拿来做键。** `agenerp/seedsite.py:370-373` 逐字：
   「冷起空站点上序列号恰好等于 `agenerp/seed/names.py` 那几个字面量，**但那是「按顺序建」的巧合，
   不是站点承诺**，幂等不许押在它上面」；装载器的幂等键是 `{company, customer/supplier, posting_date}`
   （`:537` / `:550`），`name` 从不送也从不校验。**这条直接约束 D2 的候选集怎么取。**
11. **`CheckResult` 的形状**（`agenerp/seedsite.py:719-731`）：`label` / `actual` / `expected` / `source` / `ok`，
   `line()` 成功与失败都打。诊断的落点是 `label`——**它已经在承担这个角色**
   （`:829-830` 现在就往 label 里塞「命中 N 张：…」）。

## Goals

- **取证**：`Sales Invoice` / `Purchase Invoice` 的 `status` 变成 `Overdue` 的机制，
  证据形态是**容器内实读的源码路径 + 行号 + 逐字片段**，不是推理。
- **让红自解释**：`_overdue_checks` 红时，消息里必须逐条给出**本仓预期的那两张发票**在站点上的
  `status` / `due_date` / `docstatus` / `outstanding_amount`，读的人一眼能定位是哪一半不成立。
- 依 Phase 1 的实测结论，把 docstring 与三处复述该机制的 owner doc 改成与实测一致的说法。

## Non-Goals

- **不改变 `--verify-site` 的判定结果集。** 对账仍是 **9 项**、仍是 9 项全过才退 0；
  本 plan 只让其中两项的**消息**变详细，**不新增结果行、不新增红的入口、更不新增绿的入口**。
  ⚠️ 这一条是刻意的设计选择（见 D1）：改变项数会波及
  `.github/workflows/gates.yml:368` 的 step 名、`system-baseline.md:682`、`project-context.md:57`、
  `module-boundaries.md:1135/1155/1159`、`docs/backlog/gate-proposal-seed-dataset.md:96`（人的采纳提案），
  以及 `docs/masterplan/STATE.md:165/173/176`（**红线 5：只能追加，不得改写**）。
- **不放宽任何断言。** `EXPECTED_*_OVERDUE` 一分不改；承重断言仍是**站点自己算出的 `status`**。
- **不改 `agenerp/seed/**` 的任何日期常量**（`BASE_DATE` / `INVOICE_TERM_DAYS` / `OVERDUE_DAYS` 一个字不动）。
  把 `BASE_DATE` 改成「相对今天推算」是**净变坏**：它会打掉工作项 7 绑定门禁
  `test_seed_dataset_absurdity.py` 的确定性两条。
- **不改 `tests/gates/**`**（红线 1）、**不新增门禁**（要 `Gates-Change-Approved-By:`）、
  **不改 `tools/gates/**`**、**不动 `tools/gates/expected-red.txt`**。
- **不改 `.github/workflows/**`**（前驱 plan 负责 CI；本 plan 一行不动）、**不改 `docker-compose.yml`**
  （不停 `scheduler`、不改任何服务）、**不改 `missions/**`**。
- **不推动工作项 7 从 `planned` 变 `done`**（卡点是「从 `expected-red.txt` 划掉」这条人裁定题）。

## Task Route

- Type: `bug investigation`（主体是取证）+ 一处**只影响失败消息**的可观测性改动
- ⚠️ **诚实说明，免得被读成比实际更「条件化」**：本 plan 的代码改动**无条件落地**，
  **不**由 Phase 1 的结论选定。Phase 1 的分流只决定两件事：**(1) 三处 owner doc 与 docstring 改成什么措辞；
  (2) 要不要往 `docs/masterplan/STATE.md` §3 追加一条升级行。**
- Owner Docs: `docs/architecture/system-baseline.md` §14.5（登记那条未查证项的地方）·
  `docs/architecture/module-boundaries.md` §12.10 · `docs/context/project-context.md:57` 末句 ·
  `docs/backlog/p0-foundation-roadmap.md`（追加一行）
- Skill Selection Basis: `none`。方法是「容器内实读源码 + 冷起站点实跑」，`docs/skills/README.md` 无对应技能。
  ⚠️ **刻意不用 `superpowers:systematic-debugging`**：本 plan 不是在修一个已复现的失败，
  而是在取证一条**至今一直是绿**的断言的成立机制，两者方法不同。
  同理**也不用** `docs/skills/README.md:52` 的 `bug-diagnosis-prompt.md`：它的输入是一个可复现的失败现象，
  本 plan 手上没有失败现象，只有一条未取证的机制陈述。

## Infrastructure And Config Prereqs

- 需要活栈：`AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`，
  且**每次测量前必须 `down -v` 冷起**（`project-context.md:57` 已把干净站点循环定为**强制前置**，
  理由是站点没有单据级撤销手段；`down -v` 丢掉整站数据，首次冷起前先 `bench --site frontend backup`）。
- **端口 18080**（8080 被本机另一套常驻 ERPNext 栈占着，`project-context.md:57` 口径①）。
- **`--site` 只能由 argv 给**：`agenerp/seedsite.py` 的 `main()` 读 `args.site`，**不读 `AGENERP_SITE`**。
- 容器内实读走 `docker compose exec backend`（**只读命令**：`cat` / `grep` / `sed`）。
- 回滚：本 plan 只改 `agenerp/seedsite.py` 的一个函数 + **扩写 `tests/unit/test_seedsite_documents.py`**（见 D3，**不新建文件**）+ 改文档。回滚 = `git revert` 那一个提交。
- **无破坏性写入**：本 plan 不调用 `apply_pack` / `execute_plan` / `drop_columns` 中的任何一个，
  因此 `docs/context/ai-autonomy-policy.md:88`（对活站点的破坏性写那一行）的 Required Evidence **不适用**。
  **这是排除，不是豁免。**

## Execution Plan

### Phase 1 - 取证：`status == "Overdue"` 到底由谁写、什么时候写

Status: completed
Targets: 只读（容器内 ERPNext 源码 · 活站点）—— **本 Phase 一行仓内代码都不改**
Skill: `none`

- Item Types: `Proof`
- Prereqs: 无

- [x] **Proof A（源码面）**：容器内实读 ERPNext v15.119.3，定位 `status` 被写成 `Overdue` 的**全部**代码路径。
      至少覆盖三处，每处给出**容器内绝对路径 + 行号 + 逐字片段**
      （取证强度对齐 `0228-2` 实读 `frappe/commands/utils.py:285` 的 `if ret:`）：
      ① `erpnext/controllers/status_updater.py` —— `Overdue` 分支拿哪个日期跟 `due_date` 比；
      ② `erpnext/accounts/doctype/sales_invoice/sales_invoice.py` 的 `on_submit` / `set_status` 调用链；
      ③ `erpnext/hooks.py` 的 `scheduler_events` —— 有没有定期刷 invoice status 的任务，叫什么、什么频率。
      **只写实读到的，不写「应该是」。**
      - Skill: `none`
- [x] **Proof B（运行面）**：冷起站点上取四个可判事实：
      ① `scheduler` 服务状态（`docker compose ps scheduler`）+ 站点侧 scheduler 是否 enabled/paused；
      ② 装载完单据**立刻**（不等任何调度周期）读回两张发票的 `status` 与 `modified`——
      `modified` 与提交时刻同秒即说明是提交时即时算的；
      ③ 两张发票 `due_date` 的站点实读值，与 Baseline 4 算出的 `2026-03-10` / `2026-03-09` 逐字核对；
      ④ **本仓有没有一条只读路径能读到站点侧的「今天」**（`SiteClient` 现有面只有
      `get(path, params)` / `list_resource` / `find_one`）。**这一条是 Phase 2 的前置**：
      读不到就按 D2 用宿主时钟并**在消息里逐字标注「宿主侧」**，绝不悄悄冒充站点口径。
      - Skill: `none`
- [x] **Proof C（分流结论，必须落成三选一，不许含糊）**：
      | 分流 | 结论 | 对文档措辞的后果 |
      |---|---|---|
      | **(i)** | 提交时即时计算，`scheduler` 不参与 | Baseline 1 那句机制陈述**取证成立**，改写为「已实测，证据在 X:N」 |
      | **(ii)** | 由 `scheduler` 的定期任务写入 | Baseline 1 那句**被证伪** → 此时才成为 Minimum Rule 14 的确认漂移，必须就地改准，**且**往 STATE §3 追加一条「全新站点上存在真实时序竞争」的升级行 |
      | **(iii)** | 两者都写 | 取二者中**更弱**的作为成立条件，措辞按 (ii) 处理 |
      ⚠️ **拿不到可分流证据的处置见 `## Deferred But Adjudicated` 首条** ——
      **注意它只让文档面停下，代码面（Phase 2）仍然落地**，理由写在那一条里。
      - Skill: `none`

#### Phase 1 取证记录（2026-08-23 实做，全部为实读/实跑，非推理）

栈：`AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml`，
容器 `backend` = `frappe/erpnext:v15.119.3`，
`/home/frappe/frappe-bench/apps/erpnext/erpnext/__init__.py:7` 逐字 `__version__ = "15.119.3"`。
以下容器内路径一律省略前缀 `/home/frappe/frappe-bench/apps/erpnext/`。

**Proof A（源码面）—— 起草时点名的三处里有一处点错了，照实记：**

⚠️ **A① 的预设位置为空**：`erpnext/controllers/status_updater.py` 里**没有任何 `Overdue` 字面量**。
命令 `docker compose exec -T backend bash -lc 'grep -n "Overdue" .../controllers/status_updater.py'` → **exit 1，零命中**。
起草时写的「① `status_updater.py` —— `Overdue` 分支拿哪个日期跟 `due_date` 比」**指错了文件**。
实际写 `Overdue` 的路径由 `grep -rn '"Overdue"' --include=*.py erpnext/` 定位，与发票相关的**只有两条**（下面 A①′ / A③）。

| 编号 | 容器内路径:行号 | 逐字片段 |
|---|---|---|
| **A①′ 提交路径的判定函数** | `erpnext/accounts/doctype/sales_invoice/sales_invoice.py:2077-2100` | `def is_overdue(doc, total):` … `	today = getdate()` … `	if doc.get("is_pos") or not doc.get("payment_schedule"):` / `		return getdate(doc.due_date) < today` … `			if getdate(payment.due_date) < today` |
| **A①″ 写 `Overdue` 的那两行** | `sales_invoice.py:2037-2038` / `purchase_invoice.py:2012-2013` | `				elif is_overdue(self, total):` / `					self.status = "Overdue"`（两文件逐字相同；`purchase_invoice.py:22` 逐字 `	is_overdue,` —— 采购发票**直接 import 销售发票那一个函数**，不是各写一份） |
| **A② 调用链（提交时）** | `sales_invoice.py:274` `def validate(self):` → `sales_invoice.py:350` `		self.set_status()`；`purchase_invoice.py:258` `def validate(self):` → `purchase_invoice.py:292` `		self.set_status()`；`set_status` 本体在 `sales_invoice.py:2022` / `purchase_invoice.py:1997` | `	def set_status(self, update=False, status=None, update_modified=True):` … `			elif self.docstatus == 1:` … `		if update:` / `			self.db_set("status", self.status, update_modified=update_modified)` |
| **A③ scheduler 路径（确实存在）** | `erpnext/hooks.py:444` `	"daily_maintenance": [` → `erpnext/hooks.py:447` | `		"erpnext.controllers.accounts_controller.update_invoice_status",` |
| **A③′ 那个定期任务的本体** | `erpnext/controllers/accounts_controller.py:3530-3583` | `def update_invoice_status():` / `	"""Updates status as Overdue for applicable invoices. Runs daily."""` / `	today = getdate()` … `		conditions = (` / `			(invoice.docstatus == 1)` / `			& (invoice.outstanding_amount > 0)` / `			& (invoice.status.like("Unpaid%") | invoice.status.like("Partly Paid%"))` … `		frappe.qb.update(invoice).set("status", status).where(conditions).run()` |

**A 的两条结论（都是实读支撑的）：**

1. **Baseline 2 里那半句被标为「推理、非实读」的话——「`scheduler` 刷新与提交时即时计算都是拿真实时钟比 `due_date`」——现已被证实。**
   两条路径**各自**逐字写着 `today = getdate()`（`sales_invoice.py:2082` / `accounts_controller.py:3532`），
   `getdate()` 不带参即取真实时钟；两条都拿它跟 `due_date` 比。**Baseline 2 的结论（两处不矛盾）因此不需要重写。**
2. ⚠️ **一处比 docstring 现有措辞更细的实读，照实记**：本仓的两张发票**都有 `payment_schedule` 子表**（见 Proof B 的 SQL 输出），
   因此 `is_overdue` 走的是**后一条分支**（`sales_invoice.py:2088-2100`）——比的是 `payment_schedule.due_date < today`
   而不是 `doc.due_date < today`。**本例中两者同值**（SQL 实读：`ACC-SINV-2026-00001 → 2026-03-10`、
   `ACC-PINV-2026-00001 → 2026-03-09`，与发票头上的 `due_date` 逐字相同），所以结论不变，
   但「拿 `due_date` 比」这个说法的**精确形态是「拿 payment_schedule 那一行的 `due_date` 比」**。

**Proof B（运行面）—— 四条各带命令原文与输出：**

**B①（scheduler 服务 + 站点侧开关）** —— **两者结论相反，必须一起读**：

```
$ docker compose -f docker-compose.yml ps scheduler --format '{{.Name}} {{.Service}} {{.Status}}'
agenerp-scheduler-1 scheduler Up 45 seconds

$ docker compose exec -T backend bash -lc 'cd /home/frappe/frappe-bench && bench --site frontend scheduler status'
Scheduler is disabled for site frontend

$ ... bench --site frontend execute frappe.utils.scheduler.is_scheduler_inactive
true

$ ... bench --site frontend mariadb -e "select count(*) as n from \`tabScheduled Job Log\`;"
n
0
```

→ **容器起着，但站点侧 scheduler 是 disabled，且这个站点上一条 `Scheduled Job Log` 都没有。**
Baseline 6 说的「物理可达」在**服务层**成立，在**站点层不成立**：`update_invoice_status` 在本仓栈的默认站点上**从未运行过一次**。

**B②（装载完立刻读回 `status` 与 `modified`）** —— 冷起循环：`down -v`（exit 0）→ `up -d --wait`（exit 0）
→ `--load-masters`（`合计：新建 40 / 已存在 0`）→ `--load-documents`（**exit 0**，`合计：新建 17 / 已存在 0 / 提交 11`），
装载结束后**立刻**（不等任何调度周期）读回：

```
$ AGENERP_HTTP_PORT=18080 ... python3 -c '<SiteClient.list_resource 两个 DocType>'
Sales Invoice    {'name': 'ACC-SINV-2026-00001', 'status': 'Overdue', 'outstanding_amount': 18612.0,
                  'due_date': '2026-03-10', 'docstatus': 1, 'posting_date': '2026-02-08',
                  'company': 'XM 演示纺织有限公司', 'customer': '杭州春季服饰有限公司',
                  'creation': '2026-08-23 03:05:56.475591', 'modified': '2026-08-23 03:05:56.569227'}
Purchase Invoice {'name': 'ACC-PINV-2026-00001', 'status': 'Overdue', 'outstanding_amount': 2200.0,
                  'due_date': '2026-03-09', 'docstatus': 1, 'posting_date': '2026-02-07',
                  'company': 'XM 演示纺织有限公司', 'supplier': '绍兴染整演示厂',
                  'creation': '2026-08-23 03:05:56.818018', 'modified': '2026-08-23 03:05:56.941119'}
```

→ **`modified` 与 `creation` 相差 94 ms / 123 ms，同秒**。站点此刻建起来不到两分钟（`create-site` 于 03:04 退出），
`status` 已经是 `Overdue`。**这是「提交时即时算出来的」的直接证据**，不是暗示。

**B③（`due_date` 站点实读值 vs Baseline 4 的算值）**：站点回 `2026-03-10`（销售）/ `2026-03-09`（采购），
与 Baseline 4 由 `BASE_DATE + day(36)` / `day(35)` 算出的两值**逐字相同**。✅

**B④（本仓有没有只读路径能读到站点侧的「今天」）—— 答案是没有，但有一条相邻的路，两者都记：**

```
$ <SiteClient.get> /api/method/frappe.utils.nowdate
ERR → HTTP 403（站点 frontend）：frappe.exceptions.PermissionError: You are not permitted to access this resource
$ <SiteClient.get> /api/method/frappe.client.get_time_zone
OK  → {'message': {'time_zone': 'Asia/Kolkata'}}
$ <SiteClient.get> /api/method/frappe.auth.get_logged_user
OK  → {'message': 'Administrator'}
$ ... bench --site frontend execute frappe.utils.nowdate
"2026-08-23"
```

→ **`frappe.utils.nowdate` 没有 whitelist，HTTP 面读不到站点侧的「今天」**（`bench execute` 读得到，但那是容器内命令，不是 `SiteClient` 的只读面）。
唯一读得到的相邻事实是**站点时区**（`Asia/Kolkata`，与宿主的 `CST/UTC+8` **不同**），
拿它加宿主 UTC 时钟能**推算**站点日期，但那仍然是宿主时钟，不是站点时钟的读数。
**因此按 D2 的写死处置：诊断的「今天」用宿主时钟，并在消息里逐字标注「宿主侧」。**
（本次两边同日：`bench execute frappe.utils.nowdate` → `"2026-08-23"`，宿主 `date` → `2026-08-23 CST`。）

**Proof C（分流结论）：落在 (i)。**

> **(i) 提交时即时计算，`scheduler` 不参与。**

四条证据缺一不可：
① `validate()` → `set_status()` → `is_overdue()` 的**同步**调用链（A②/A①′，提交时走这条）；
② 站点侧 scheduler **disabled**、`Scheduled Job Log` **0 行**（B①）——定期任务在本栈上**一次都没跑过**；
③ `modified − creation = 94 ms / 123 ms`，站点存活不到两分钟（B②）；
④ 即使 scheduler 被打开，`update_invoice_status` 的 `conditions` 逐字要求
`invoice.status.like("Unpaid%") | invoice.status.like("Partly Paid%")`（A③′）——
提交时已经写成 `Overdue` 的行**结构性地不在它的更新集里**。
**所以不是 (iii)「两者都写」**：第二条路径存在、但对这两行**按构造不可达**。

**对文档措辞的后果（按 (i) 处理）**：Baseline 1 那句机制陈述**取证成立**，
`seedsite.py` 的 docstring 与三处活陈述**只补取证出处、不改写句子本体**；
**不援引 Minimum Rule 14**（没有确认的漂移）；**不往 `docs/masterplan/STATE.md` §3 追加升级行**
（(ii)/(iii) 才要求追加，本次未触发）。
⚠️ 唯一需要补精度的是 A 结论 2 那条：「拿 `due_date` 比」的精确形态是「拿 `payment_schedule` 那一行的 `due_date` 比」，
本例两者同值。

Exit Criteria:

- [x] A 的三处各有「容器内路径 + 行号 + 逐字片段」记在本 plan 内
- [x] B 的四个事实各有一条命令原文 + 输出记在本 plan 内
- [x] C 明确落在 (i)/(ii)/(iii) 之一，或明确落在「拿不到证据」并已执行首条固定处置
- [x] 本 Phase 结束时 `git diff --stat agenerp/ tests/` **无输出**
- [x] No owner-doc update required (this phase)

### Phase 2 - 让红自解释（不改结果集，只改失败消息）

Status: completed
Targets: `agenerp/seedsite.py`（只改 `_overdue_checks` 及其新增的私有辅助）·
`tests/unit/test_seedsite_documents.py`（扩写既有文件，见 D3）
Skill: `none`

- Item Types: `Decision | Fix | Proof`
- Prereqs: Phase 1 全部 Exit Criteria

- [x] **Decision D1：诊断落在既有两条 `CheckResult` 的消息里，`--verify-site` 仍是 9 项。**
      候选四条：
      (a) 只改 docstring 不改代码 —— **否掉**：Baseline 3 的取证空洞原样留着，红了仍然不自解释；
      (b) 把承重断言从「站点算的 `status`」改成「本仓拿 `due_date` 自己比」—— **否掉，净变坏**：
          `2107-2` 的全部价值就在「站点自己算出来」，改了等于退回「生成器自己跟自己对账」；
      (c) 为每个前提新增独立的 `CheckResult` 结果行（9 → N 项）—— **否掉**：
          它会波及 `.github/workflows/gates.yml:368` 的 step 名（而本 plan 声明不动 CI）、
          `system-baseline.md:682`、`project-context.md:57`、`module-boundaries.md:1135/1155/1159`，
          以及 `docs/masterplan/STATE.md:165/173/176`——**后者受红线 5 保护，只能追加不得改写**，
          即这条路会制造一批**按红线不可改准**的陈旧陈述；
      (d) **选它** —— 把前提事实写进既有两条 `CheckResult` 的 `label`（Baseline 8：`label` 已在承担这个角色）。
      **取舍代价照实说**：(d) **既不新增红的入口，也不新增绿的入口**——它不改变任何一次判定的通过与否，
      只改变红的时候能读到什么。⚠️ **因此不得把本 plan 说成「加严了判据」**；
      它加严的是**可诊断性**，不是判据。残余风险：`label` 变长，`--verify-site` 输出变宽。
      - Skill: `none`
- [x] **Decision D2：诊断的候选集取自「装载器的幂等键」，不取自站点的 `Overdue` 过滤结果，
      也不取自 `names.py` 的单据号字面量。**
      两条否定各有出处，缺一不可：
      - ⚠️ **不取 `status == "Overdue"` 过滤结果**：那样站点回零张 `Overdue` 时候选集为空，
        **诊断在它唯一存在理由的那个场景下恰好空转**。这是本 plan 最容易犯、单测最容易漏掉的错。
      - ⚠️ **不取 `agenerp/seed/names.py` 的 `SALES_INVOICE` / `PURCHASE_INVOICE` 字面量**
        （初稿就是这么写的，评审推翻）：Baseline 10 —— `seedsite.py:370-373` 逐字说明那几个号
        「是『按顺序建』的巧合，**不是站点承诺**」。押在它上面的后果是**每一次运行（包括绿的那些）
        都会打印一行「预期的 `ACC-SINV-2026-00001`：站点上没有」**，而单测结构性地看不见这个错
        （任何假站点都会用同一批字面量）。
      **选定取法**：用装载器自己的幂等键 `{company, customer/supplier, posting_date}`
      （`seedsite.py:537` / `:550`）把那两张发票在站点上认出来，**外加**对应 DocType 下全部已提交发票
      （用于发现「站点上多了一张不该有的」）。单据号只作为**显示用**，不作为匹配键。
      **「今天」的口径**按 Proof B④ 的结论取；取不到站点侧口径时用宿主时钟并在消息里逐字标注「宿主侧」。
      ⚠️ **「今天」必须是可注入的参数**，否则单测状态 ③ 会变成随时钟漂移的测试；
      注入点与默认值写进实现，单测显式传值。
      - Skill: `none`
- [x] **Decision D3：扩写既有测试文件，不新建第二个假站点。**
      候选：(i) 新建 `tests/unit/test_seedsite_overdue.py` + 第二个 `FakeVerifySite`（初稿写法）；
      (ii) **选它** —— 在 `tests/unit/test_seedsite_documents.py` 既有 `FakeVerifySite`（`:363-401`）上扩写。
      理由：Baseline 8 —— 那个夹具**已经覆盖两个发票 DocType**（`:388-393`），(i) 会造出两份需要同步维护的同构夹具，
      且 `:412` 的 `assert len(results) == 9` **已经是** Phase 2 Exit Criteria 想要的那条「项数不得变」机械判据，
      重造一遍只会让它有两个来源。残余风险：该文件变长；缓解是新增用例集中成一段并加节注释。
      - Skill: `none`
- [x] **Fix：实现 D1 + D2。** 硬约束五条：**不改任何 `EXPECTED_*` 常量**；**不改 `CheckResult.ok` 的算法**
      （`ok` 仍只由 `_close(total, expected)` 决定）；**不新增结果行**；**不新增写方法**（只用 `SiteClient` 既有只读面）；
      **诊断自身抛错不得吞掉**（读不到字段就让它红，不 `try/except: pass`）；
      **`total` 的输入集也钉死**——筛选条件逐字仍是 `status == "Overdue" and int(docstatus) == 1`（`:826`），
      诊断不得顺手放宽它。状态 ③④ 的期望除消息内容外**还必须断言 `ok is False`**。
      - Skill: `none`
- [x] **Proof：在 `tests/unit/test_seedsite_documents.py` 既有 `FakeVerifySite` 上扩写**，覆盖五态
      ⚠️ **冻结面只到断言行，不到夹具数据**（评审第 3 轮改准）：`:412` 的 `assert len(results) == 9`
      与 `:469` 的那条断言**保持不变、不得改写**（它们是「项数不变 / 承重断言仍在」的现成判据）；
      **但 `:388-393` 的两条发票行与 `:465-467` 的 override 必须补上
      `company` / `customer` 或 `supplier` / `posting_date` 三个键** —— 现夹具里没有它们，
      而 D2 按幂等键匹配，不补就会在 `:464-469` 那条测试上要么 `KeyError`、
      要么打出一行**假的**「站点上没有这张发票」（而那张发票明明在，只是 `status="Paid"`），
      **恰好就是 D2 存在的理由被它自己复现一遍**。补键不是改写断言，两者不得混同。
      五态如下：
      ① 两张都 `Overdue` 且金额对 → `ok=True`，**且消息里必须逐字出现两张发票各自被按键认出的事实**
         （⚠️ **这条正向断言不可省**：`FakeVerifySite.__call__`（`:397-401`）**完全忽略 query 参数**，
         对任何 `filters` 都返回整份 `self.data[doctype]` —— 因此一个「键永远匹配不上」的实现
         会在五态与两条变异下**全部通过**，同时在每一次绿的运行里打印垃圾。这条断言是唯一的堵口）；
      ② 站点回**零张** `Overdue` → `ok=False` 且消息**逐条列出那两张预期发票的 `status` / `due_date` / `docstatus`**
      （**这一条是 D2 反空转的判据**，必须存在）；
      ③ `due_date` 未到期 → 消息逐字点名 `due_date` 与所用「今天」的口径标注；
      ④ `docstatus != 1` → 消息点名未提交；
      ⑤ 金额对不上但两张都 `Overdue` → `ok=False` 且**仍报金额**（证明诊断没把承重断言吃掉）。
      - Skill: `none`
- [x] **Proof：变异验证三条（有牙齿，不是空转）**：
      ① 把诊断的候选集改成「由站点 `Overdue` 过滤得出」（即故意犯 D2 点名的那个错）→
         `python3 -m pytest tests/unit -q` **exit 1** 且**逐字点名第 ② 条**；
      ② 把诊断整段改成恒返回空串 → **exit 1** 且逐字点名 ②③④；
      ③ **把幂等键的一个分量改坏**（例如 `posting_date` 改成一个不存在的日期）→ **exit 1**
         且逐字点名状态 ①（**这条证明「键真的在匹配」，是评审第 3 轮要求补的**）。
      三条各自复原后 exit 0。六次的命令原文与退出码全部记在本 plan 内。
      - Skill: `none`

#### Phase 2 实做记录（2026-08-23）

**落地形态（`agenerp/seedsite.py`，`git diff --numstat` = `70	5`）**：

- 新增模块级常量 `OVERDUE_DOCTYPES` 与 `TODAY_CALIBER = "宿主侧"`（口径按 Proof B④ 的结论写死在代码里）；
- 新增 `_overdue_identity_keys()` —— **直接取 `document_steps()` 里那两步自己的 `key`**，
  不复制第二份键字面量（与 `seedsite.py:715` 那条「写第二份字面量等于给判据加副本」的既有约束同向）；
- 新增 `_matches_key()` / `_overdue_row_facts()` / `_overdue_diagnosis()`；
- `_overdue_checks(client, today=None)` 与 `verify_site(client, today=None)` 各多一个**可注入**的 `today`，
  默认 `date.today().isoformat()`（宿主时钟）；
- **筛选条件逐字未改**：`overdue = [r for r in rows if r["status"] == "Overdue" and int(r["docstatus"]) == 1]`；
  `total` 的算法未改；`_close` / `_numeric_check` / `CheckResult.ok` 一行未动；**结果集仍是 9 项**。
- `list_resource` 的字段元组由 `("name","status","outstanding_amount","due_date","docstatus")`
  扩成 `(… , *keys[doctype])`，**只加读，不加写**；`find_one` **未被使用**（评审第 3 轮 ⑥ 的钉死项）。

**夹具补键（`tests/unit/test_seedsite_documents.py`）**：给 `FakeVerifySite` 的两条发票行与
`test_verify_site_goes_red_when_an_invoice_is_not_overdue` 的 override 各补上
`company` / `customer|supplier` / `posting_date`。⚠️ **补键前先实测到了评审第 3 轮预言的那个失败**：
`python3 -m pytest tests/unit -q` → **exit 1，7 failed**，逐字 `KeyError: 'company'`（`agenerp/seedsite.py:831`）。
补键后回 exit 0。**两条冻结断言未被改写**（`git diff` 对 `assert len(results) == 9`
与 `assert any("Sales Invoice" in r.label and not r.ok for r in results)` **零命中**）。

**改动后两条 overdue 行的实际输出（本机纯逻辑夹具跑出来的，绿的那次）**：

```
✅ Sales Invoice 中 status == 'Overdue' 的 outstanding_amount 合计（命中 1 张：ACC-SINV-2026-00001；本仓预期 —— ACC-SINV-2026-00001：status=Overdue / due_date=2026-03-10（已到期，今天 2026-08-23（宿主侧）） / docstatus=1（已提交） / outstanding_amount=18612.00） = 18612.00 / expected = 18612.00（出处：agenerp.seed.checks.EXPECTED_RECEIVABLE_OVERDUE）
✅ Purchase Invoice 中 status == 'Overdue' 的 outstanding_amount 合计（命中 1 张：ACC-PINV-2026-00001；本仓预期 —— ACC-PINV-2026-00001：status=Overdue / due_date=2026-03-09（已到期，今天 2026-08-23（宿主侧）） / docstatus=1（已提交） / outstanding_amount=2200.00） = 2200.00 / expected = 2200.00（出处：agenerp.seed.checks.EXPECTED_PAYABLE_OVERDUE）
```

承重的 `= 18612.00 / expected = 18612.00` / `= 2200.00 / expected = 2200.00` **仍在行尾，没有被诊断挤掉**。

**五态单测（新增 5 条，`tests/unit` 288 → 293）**，都同时断言 `ok` 与消息内容：

| 态 | 测试名 | 断言要点 |
|---|---|---|
| ① | `test_overdue_diagnosis_names_both_expected_invoices_when_everything_is_right` | `ok` 均为真，且两张各自逐字出现 `ACC-*：status=Overdue`，`"认不出"` 不出现 |
| ② | `test_overdue_diagnosis_still_lists_the_expected_invoices_when_the_site_found_none` | 站点回零张 `Overdue` 时 `ok is False`、`命中 0 张：无`，**仍逐条打出** `status=Unpaid` / `due_date=…` / `docstatus=1（已提交）`；另覆盖「站点上根本没有这张发票」→ `认不出这张发票` |
| ③ | `test_overdue_diagnosis_points_at_due_date_and_labels_whose_today_it_used` | `ok is False`，逐字 `due_date=2026-03-10（未到期，今天 2026-03-01（宿主侧））` |
| ④ | `test_overdue_diagnosis_points_at_an_unsubmitted_invoice` | `ok is False`，逐字 `docstatus=0（未提交）` |
| ⑤ | `test_overdue_diagnosis_does_not_eat_the_load_bearing_amount_assertion` | `ok is False`、`actual == "17000.00"`，且 `= 17000.00 / expected = 18612.00` 仍在 `line()` 里 |

**三条变异验证，六次退出码逐条记（1 → 0 → 1 → 0 → 1 → 0，命令原文均为 `python3 -m pytest tests/unit -q`）**：

| 变异 | 改法 | 退出码 | 逐字点名的用例 |
|---|---|---|---|
| ① | 诊断候选集由 `rows` 改成 `overdue`（即由站点 `Overdue` 过滤得出，D2 点名的那个错） | **1**（3 failed, 290 passed） | `::test_overdue_diagnosis_still_lists_the_expected_invoices_when_the_site_found_none`（**状态 ②，预测命中**）· `::…points_at_due_date_and_labels_whose_today_it_used` · `::…points_at_an_unsubmitted_invoice` |
| ①′ | 复原 | **0**（293 passed） | — |
| ② | `_overdue_diagnosis` 首行 `return ""`（整段恒返回空串） | **1**（5 failed, 288 passed） | `::…names_both_expected_invoices_when_everything_is_right` · `::…still_lists_the_expected_invoices_when_the_site_found_none`（**②**）· `::…points_at_due_date_and_labels_whose_today_it_used`（**③**）· `::…points_at_an_unsubmitted_invoice`（**④**）· `::…does_not_eat_the_load_bearing_amount_assertion` |
| ②′ | 复原 | **0**（293 passed） | — |
| ③ | 幂等键的 `posting_date` 分量改成 `"1999-01-01"`（不存在的日期） | **1**（5 failed, 288 passed） | `::…names_both_expected_invoices_when_everything_is_right`（**状态 ①，预测命中 —— 这条证明键真的在匹配**）+ 其余四条 |
| ③′ | 复原 | **0**（293 passed） | — |

⚠️ **两处实测比预测更宽，照实记、不粉饰**：变异 ② 预测点名 ②③④，实测**还**点名了 ① 与 ⑤；
变异 ③ 预测点名 ①，实测**还**点名了其余四条。方向一致（都是「更红」而不是「漏红」），
但**预测不精确这件事本身要记下来**，不能写成「与预测逐字一致」。

**本 Phase 的其余验证（命令原文 + 退出码）**：

```
$ python3 tools/gates/check_expected_red.py                       -> 0
  判定模式：default —— 按 tools/gates/expected-red.txt 判定
  门禁 19 项：预期红 7，绿 12，跳过 0
  ✅ 与预期红名单完全一致
$ python3 -m pytest tests/unit -q                                 -> 0   （293 passed）
$ python3 -m pytest tests/contracts -q                            -> 0   （151 passed）
$ ruff check agenerp tests/unit tests/contracts                   -> 0   （All checks passed!）
$ git diff --stat agenerp/seed/                                   -> 无输出
$ git status --porcelain tests/gates .github tools/gates missions docker-compose.yml docs/masterplan
                                                                  -> 无输出
```

Exit Criteria:

- [x] `_overdue_checks` 仍**只返回 2 条** `CheckResult` —— 机械判据是既有 `test_seedsite_documents.py:412`
      的 `assert len(results) == 9` **仍然绿且未被改写**（`git diff` 该行无输出）
- [x] 五态单测齐全，其中 ②（反空转）与 ⑤（承重断言未被吃掉）不得缺
- [x] **三条**变异验证的六次退出码（1 → 0 → 1 → 0 → 1 → 0）记在本 plan 内
- [x] `agenerp/seed/**` **一个字节未改**（`git diff --stat agenerp/seed/` 无输出）
- [x] `tests/gates/**` / `tools/gates/**` / `.github/workflows/**` / `missions/**` / `docker-compose.yml` 零改动
- [x] `docs/logs/` 更新

### Phase 3 - 活站点实证 + 按 Phase 1 的分流改准文档

Status: planned
Targets: `agenerp/seedsite.py:811-816`（docstring）· `docs/architecture/system-baseline.md` §14.5 ·
`docs/architecture/module-boundaries.md` §12.10 + `:1149-1151` + `:1142` + `:1212` · `docs/context/project-context.md:57` ·
`docs/backlog/gate-proposal-seed-dataset.md:93-94` · `docs/backlog/p0-foundation-roadmap.md`
Skill: `none`

- Item Types: `Fix | Add | Proof`
- Prereqs: Phase 2 全部 Exit Criteria

- [ ] **Proof：从 `down -v` 冷起的空站点跑完整条链**，四条命令各判退出码（端口 18080，每条带 `--site frontend`）：
      `--load-masters` → 0 · `--load-documents` → 0 · 原样复跑（`^合计：新建 0 `）→ 0 · `--verify-site` → **0**。
      **`--verify-site` 必须仍打「9 项，通过 9，失败 0」**；承重两行 `actual_qty = 1010.00` /
      `stock_value = 6450.00` 必须与 `2107-2` / `2325-1` / `2325-2` 的记录**逐字相同**——
      任一个数变了即说明动到了不该动的东西，**立即停并回 Phase 2**。
      - Skill: `none`
- [ ] **Proof：贴出改动后两条 overdue 行的实际输出原文**（绿的那次），供审计确认诊断内容真的出现在消息里、
      且没有把承重的 `= 18612.00 / expected = 18612.00` 挤掉。
      - Skill: `none`
- [ ] **Fix：按 Phase 1 C 的分流改准 `agenerp/seedsite.py:813-815` 的 docstring。**
      - 分流 (i)：把「是……比出来的」改成「**已实测**：……，证据见 `<容器内路径>:<行号>`」；
      - 分流 (ii)/(iii)：该句**被证伪**，此时才是 Minimum Rule 14 的确认漂移，就地改准为实测结论。
      - Skill: `none`
- [ ] **Fix：`docs/architecture/system-baseline.md` §14.5「起草时点名的头号候选，被实测证伪」段。**
      该段逐字写着「**本 plan 没有查证**」——本 plan 查证了，那句话的效力就此被接管。
      按本仓已固化做法**追加一段「⚠️ 2026-08-23 补记」**，⚠️ **保留原句不删**
      （它是当时诚实的限定，删掉等于抹掉「曾经不知道」这个事实），只指明其现时效力已被接管。
      ⚠️ **不动同节 `:682` 的「9 项对账全过」那一行** —— D1 选了 (d)，项数没变，该行仍然为真。
      ⚠️ **但同节 `:709-710` 逐字引用的那两行 overdue 输出会因 `label` 变长而不再逐字等于现时输出**：
      它仍是**当时那次运行的真实记录**，处置是在补记段里点明「那两行是 run `32585965892` 的历史记录，
      不是改动后的现时输出」，**不改写它**。
      - Skill: `none`
- [ ] **Fix（两分支，与 docstring 那项同构）：`docs/context/project-context.md:57` 末句**
      （「⚠️ 两张发票的 `Overdue` 依赖真实时钟（今天 > `due_date`），不是结构性成立」）。
      - 分流 (i)：该句**取证成立** → **只在句末补上取证出处**，句子本体不动；
      - 分流 (ii)/(iii)：该句**被证伪** → 此时它是 Minimum Rule 14 的确认漂移，**必须就地改准**
        （改写句子本体），**不受本 Phase「只补句末」那条限制的约束** —— 那条限制说的是**表格结构**，
        这里改的是**一句已经变假的陈述**，两者不冲突。
      ⚠️ 该行「整体臃肿」是 `1041-1` 登记、`2107-1` 就地裁定过的条目，重开事件逐字是
      「下一个需要往该表新增一行或改写既有行的 plan 开工时」——**本 plan 触发它**，
      处置沿用同一裁定：**只在既有句末补出处，不重构结构、不新增行**。
      - Skill: `none`
- [ ] **Fix（两分支）：`docs/architecture/module-boundaries.md` §12.10。**
      ① 无条件：补一小段说明诊断与承重断言的分工。
      ② **`:1149-1151` 那段机制复述**按分流处理：(i) 句末补取证出处；
      (ii)/(iii) **就地改准**（Rule 14）。⚠️ 承重那半句「但这条断言的成立条件是『今天 > `due_date`』」
      在 **`:1151`**，改准时不得漏掉它。
      ⚠️ **`:1135` 的「覆盖 9 项」与 `:1155-1159` 的「9 项是打印行数、独立约束是 8 条」两处一个字不改**——
      D1 选了 (d)，两处仍然为真。**这是刻意不改，不是遗漏。**
      - Skill: `none`
- [ ] **Fix（两分支）：`docs/backlog/gate-proposal-seed-dataset.md:93-94`。**
      它是**给人照抄用的门禁提案正文**（`:96` 逐字「采纳时可直接照抄」），因此比另两处更要紧：
      (i) 句末补取证出处；(ii)/(iii) 就地改准。**本 plan 不改该文件的 `Status: proposed`，不代人采纳。**
      - Skill: `none`
- [ ] **Add：`docs/backlog/p0-foundation-roadmap.md` 追加一行「7 现状 · overdue 机制取证」**，
      **纯追加，既有行一个字不改**（`:83` / `:84` / `:123` 的「9 项」是历史证据记录，**按红线式做法不改写**），
      并逐字写明：**工作项 7 的状态值不因此变动**（卡点仍是「那条 L1 门禁从未进过 `expected-red.txt`，
      『划掉』这个动作没有对象」），**也不得**被读成「站点侧那三条断言已成为门禁」。
      - Skill: `none`
- [ ] **Fix（本 plan 自己制造的 owner-doc 漂移，Minimum Rule 14，必须同一批改掉）：三处 `tests/unit` 条数就地改准。**
      Baseline 9：`tests/unit` 现为 **288 条**，本 plan 的 Phase 2 会新增用例 → 三处写死 288 的陈述当场变假：
      `docs/context/project-context.md:57` · `docs/architecture/module-boundaries.md:1142` · `:1212`。
      **口径与前例一致**（`STATE.md:169` / `docs/logs/2026/08-23.md` 记的 `283 → 288` 那次）：
      取 `python3 -m pytest tests/unit -q` 的**实测通过数**就地改准，**不是估算**。
      ⚠️ **这一项不受本 Phase 其他项「只补句末 / 不新增行」限制的约束** —— 那些限制说的是**结构**，
      这里改的是**一个已经变假的数字**，两者不冲突；**是本 plan 自己造成的漂移，必须自己收拾。**
      - Skill: `none`
- [ ] **Proof：陈旧陈述复核（两条 grep，不只一条）。**
      ① `grep -rn "9 项" docs/ .github/ agenerp/ tools/ | grep -v "门禁 19 项"` —— 逐条确认**每一处仍然为真**
      （D1 选 (d) 的直接收益）；
      ② `grep -rn "288 条" docs/ | grep -v "^docs/logs/\|^docs/plans/\|^docs/masterplan/STATE"` ——
      逐条确认已按上一项改准（历史证据文件 `docs/logs/` / `STATE.md` / 既有 plan **不改写**，红线 5 与追加式惯例）。
      **两份清单与逐条结论都记在本 plan 内。**
      ⚠️ **一句跨 plan 的说明，免得后来的审计误判**：前驱 `0120-1` 会把 `288 passed` 写进它自己的
      §14.6 与取证记录 —— 那是**某一次运行的历史证据**，不是本 plan owns 的活陈述，grep ② 也扫不到它，
      **不得当成本 plan 遗漏的漂移**。
      ⚠️ 若发现任一处因本 plan 而不再为真，**立即停并回 Phase 2**——因为那意味着 D1 (d) 没有被真正贯彻。
      - Skill: `none`

Exit Criteria:

- [ ] 四条 CLI 的退出码 + 「9 项，通过 9，失败 0」+ 两个承重数字的逐字对照记在本 plan 内
- [ ] 改动后两条 overdue 行的输出原文贴在本 plan 内
- [ ] docstring 与 §14.5 的新文并列贴在本 plan 内，供审计逐字比对
- [ ] `grep -rn "9 项"` 的清单与「每一处仍然为真」的逐条结论记在本 plan 内
- [ ] 三处 `tests/unit` 条数已按实测改准（`project-context.md:57` · `module-boundaries.md:1142` · `:1212`），
      且第二条 grep 的清单记在本 plan 内
- [ ] roadmap 与（若触发）`STATE.md` 均为**纯追加**（`git diff --numstat` 的删除列为 `0`）
- [ ] 工作项 7 / 9 的状态值**一个字未改**（仍 `planned`）
- [ ] `docs/logs/` 更新

## Draft Review Record

- Independent draft review iteration 1: `needs revision`（独立子代理，fresh session）—— 提出 9 条阻塞项。
  其中三条推翻了初稿的承重前提，**逐条照实记，不粉饰**：
  ① **初稿主张的「确认的 owner-doc 漂移」是伪造的**：`seedsite.py` docstring 讲「`status` 拿什么跟什么比」，
  §14.5 讲「谁写、什么时候写」，两个命题不冲突；`project-context.md:57` 与 `module-boundaries.md:1149-1151`
  还各自复述了 docstring 的说法且一致。初稿据此援引 Minimum Rule 14 把文档改动定为「不可降级」——
  **属于误引规则**。已重写 Source / Baseline 1–2 / Goals，改称「**一条从未取证的机制陈述**」，
  **不再援引 Rule 14**（仅在分流 (ii)/(iii) 证伪时它才成立）。
  ② **初稿四处行号错**（`seedsite.py` docstring 实为 `:811-816`、承重句 `:813-815`，非 `815-819`；
  `_overdue_checks` 实为 `:810-832`，非 `810-834`；`checks.py::_check_overdue` 实为 `:106-123`，非 `108-119`），
  且 Phase 3 的 Fix 指向了错误行段。已全部核对改准。
  ③ **初稿的「9 项 → N 项」会制造一批按红线不可改准的陈旧陈述**：实测 `grep` 命中
  `.github/workflows/gates.yml:368`（而初稿声明不动 CI）、`STATE.md:165/173/176`（**红线 5 只能追加**）、
  `gate-proposal-seed-dataset.md:96`（人的采纳提案），而初稿的 Exit Criteria 逐字要求「**全部**改准」，
  与它自己的「roadmap 纯追加」判据直接冲突。评审同时给出了初稿漏掉的第四候选。
  已采纳为 **D1 (d)**：诊断折进既有两条 `CheckResult` 的 `label`，**项数仍是 9**，整个波及面消失。
  ④ 其余已修：D1 不再假装「由 Phase 1 选定」（Task Route 已就此逐字澄清）；
  新增 Proof B④ 先证站点侧时钟读法是否存在，再决定 Phase 2 的口径；
  新增 D2 把诊断候选集钉在本仓预期上（评审指出按站点 `Overdue` 过滤会**在唯一需要它的场景下空转**），
  并为它补了专门的反空转单测②与变异验证①；Phase 3 `Item Types` 补上 `Add`；
  `ai-autonomy-policy` 的引用行号由 `:87` 改准为 `:88`；`## Deferred But Adjudicated` 首条
  已改成「只让文档面停下，代码面照常落地」，不再把独立交付面绑死在取证结果上。
- Independent draft review iteration 2: `needs revision`（独立子代理，fresh session）—— 5 条阻塞项。
  评审独立复核确认轮次 1 的修法**成立**：Baseline 1–8 的行号与逐字引文全部核准；
  **框架改准是对的**（`seedsite.py:813-815` 讲「拿什么跟什么比」、`system-baseline.md:711-713` 讲「谁写、什么时候写」，
  确为两个命题，**Minimum Rule 14 正确地没有被援引**）；**D1 (d) 确实消灭了波及面**
  （评审复跑 `grep -rn "9 项"`，每一处在 (d) 下**仍然为真**）；**不存在假绿路径**
  （`ok` 只源自 `_numeric_check` → `_close`，`label` 只被 `line()` 消费，诊断抛错一律走红侧）；
  **D2 的反空转推理成立**。**5 条阻塞项逐条照实记**：
  ① **`module-boundaries.md` 的引用行号错**：机制复述句在 `:1148-1150`，初稿写的 `:1141-1143`
  是「本段交付的行为没有属于自己的门禁」那段。**这条正是「三处一致」的支撑、也是不援引 Rule 14 的依据**，
  而初稿第 18 行自称「行号逐条核对过」。已改准两处。
  ② **`:823-824` 错**：`:823` 是 for 元组的 `):`，调用在 `:824`、字段元组整个在 `:825`。已改为 `:824-825`。
  ③ **本 plan 会自己制造 owner-doc 漂移且没安排修**：`tests/unit` 现为 288 条，被
  `project-context.md:57` / `module-boundaries.md:1142` / `:1212` 三处写死；Phase 2 新增用例后三处当场变假，
  而初稿的 Phase 3 只 grep `9 项`、且把那两份文档限制成「只补句末 / 只加新段」，**没有任何一项授权改这个数**。
  已新增一条 Phase 3 `Fix` 项（按实测通过数就地改准，口径沿用 `283 → 288` 那次前例）并把陈旧陈述复核扩成两条 grep。
  ④ **Minimum Rule 1 漏盘点**：`tests/unit/test_seedsite_documents.py:363-405` **早就有** `FakeVerifySite`
  且已覆盖两个发票 DocType，`:412` 的 `assert len(results) == 9` **就是**本 plan 想要的那条「项数不变」机械判据，
  `:464-469` 还有一条 overdue 转红的用例。初稿计划「新建文件 + 造第二个假站点」属重复造夹具。
  已补进 Baseline 8，并新增 **D3** 明确裁定为「扩写既有文件」。
  ⑤ **D2 押在了仓库明令禁止押的那个等式上**：初稿把候选集钉在 `names.py` 的单据号字面量上，
  而 `seedsite.py:370-373` 逐字写着那几个号「是『按顺序建』的巧合，**不是站点承诺**」；
  后果是**每一次运行（含绿的）都会多打一行假的「站点上没有」**，且单测结构性看不见
  （任何假站点都用同一批字面量）。已改为按装载器自己的幂等键 `{company, customer/supplier, posting_date}` 匹配，
  单据号只作显示用。
  非阻塞项亦已吸收：Baseline 2 把「两种写法都是拿真实时钟比 `due_date`」**标注为推理而非实读**并交 Proof A① 证实；
  Fix 硬约束补上「`total` 的筛选条件逐字不变」与状态 ③④ 的 `ok is False`；
  「今天」写明**必须可注入**，免得单测随时钟漂移；Baseline 5 措辞改准为「载荷里没有 `status`」；
  Non-Goals 的波及面清单补上 `gate-proposal-seed-dataset.md:96`；
  Phase 3 补上「`system-baseline.md:709-710` 那两行输出引文将变成历史记录，点明但不改写」；
  Closure Gate 的 downgrade 一条改用 Anti-Slacking 的 `adjudicated as residual-risk-only` 口径；
  验证命令补 `ruff check`；技能选型补上「也不用 `bug-diagnosis-prompt.md`」的理由。
- Independent draft review iteration 3: `needs revision`（独立子代理，fresh session）—— **6 条阻塞项**。
  评审复核确认：Baseline 除一条外行号全对；**D1 (d) 确实消灭了波及面**（复跑 grep，11 处「9 项」全部仍为真）；
  **仍无假绿路径**（`ok` 只源自 `_numeric_check` → `_close`，`label` 只被 `line()` 消费）；
  **D2 的取法对 `SiteClient` 读面可行**（`list_resource` 接受任意字段元组，装载器确实送
  `company`/`customer`/`supplier`/`posting_date`）。六条阻塞项：
  ① **`module-boundaries.md` 行号连错三轮**：`:1148` 是空行，机制句在 **`:1149-1151`**，
  且承重那半句「但这条断言的成立条件是『今天 > `due_date`』」在 **`:1151`，落在轮次 2 所写范围之外**。已改准。
  ② **落下了第四处活陈述**：`docs/backlog/gate-proposal-seed-dataset.md:93-94` 也逐字复述了该机制，
  而它是**给人「采纳时可直接照抄」的门禁提案正文**（`:96`）——漏掉它等于把一条未取证的陈述
  留在人将来要照抄的文本里。已补进 Baseline 2 并新增一条 Phase 3 处置项。
  同时改准计数口径：**活陈述是三处**，`system-baseline.md:706` 是前一个 plan 起草理由的**历史记录**、不计入。
  ③ **Phase 3 承诺了它没授权的改动**：Goals 说「把 docstring 与三处 owner doc 改成与实测一致」，
  但 Phase 3 给 `project-context.md:57` 只授权「补句末」、给 §12.10 只授权「补新段」，
  **在分流 (ii)/(iii)（机制被证伪）下两处都必须就地改准，而没有一项允许**。已把两项都改成两分支写法。
  ④ **Rule 11 自相矛盾**：`Infrastructure` 的回滚句还写着「新增一个单测文件」，与 D3「扩写既有文件」直接打架。已改。
  ⑤ **D2 的按键匹配会撞上被冻结的夹具**：既有 `FakeVerifySite` 的发票行（`:388-393`）与
  `:465-467` 的 override **都没有** `company`/`customer`/`posting_date`，而 plan 又把 `:464-469` 整段冻结 ——
  结果要么 `KeyError`，要么对一张明明在站点上（只是 `status="Paid"`）的发票打出**假的**「站点上没有」，
  **恰好把 D2 存在的理由自己复现一遍**。已把冻结面收窄到**断言行**（`:412` / `:469`），
  并明确要求给夹具三行补上那三个键。
  ⑥ **五态与两条变异都证明不了「键真的在匹配」**：`FakeVerifySite.__call__`（`:397-401`）
  **完全忽略 query 参数**，对任何 `filters` 都返回整份数据 —— 因此一个「键永远匹配不上」的实现
  会在全部用例下通过，同时在每一次绿的运行里打印垃圾。已三处堵口：实现**钉死走 `list_resource` + 仓内比对、
  禁用 `find_one`**；状态 ① 补一条「两张发票各自被按键认出」的正向断言；**新增第三条变异**
  （改坏幂等键的一个分量 → 必须 exit 1 且点名状态 ①）。
  非阻塞项亦已吸收：`:539`/`:552` 改准为 `:538-547`/`:551-557`；`FakeVerifySite` 范围改准为 `:363-401`；
  grep ② 去掉重复的同一分支；「转为 `deferred`」改用 Anti-Slacking 的 `adjudicated as residual-risk-only`；
  评审轮次改为「以实际轮次为准」；补一句跨 plan 说明（前驱写进取证记录的 `288 passed` 是历史证据，
  不是本 plan owns 的漂移）。
- Independent draft review iteration 4: **`accept`**（独立子代理，fresh session）—— **零阻塞项，达成共识**。
  评审对 `577e401` 逐条复核了轮次 3 的六条修法，全部确认：
  ① `module-boundaries.md:1149-1151` **是对的**（`:1148` 空行、`:1151` 承载那半句成立条件），
  且 Phase 3 逐字点名了 `:1151` 不得漏；② `gate-proposal-seed-dataset.md:93-94` 与 `:96` 的引文逐字核准，
  已入 Baseline 并有自己的两分支处置项，且 `Status: proposed` 明确不动；
  ③ 两处 owner doc 的 Phase 3 项**确实是两分支**，(ii)/(iii) 下可就地改准，Goals 第三条第一次有授权项兜底；
  ④ 夹具冻结面收窄正确 —— 评审实读确认 `:388-393` / `:465-467` **今天确实没有那三个键**，
  因此「必须补键」不是可选项，而其理由（`KeyError` 或对一张 `status="Paid"` 的在站发票打出**假的**「站点上没有」）成立；
  ⑤ **「键永远匹配不上却全绿」那个洞已经堵上**，且堵法有结构性依据：`SiteClient` **根本没有带 filter 的列表方法**，
  `list_resource(doctype, fields)` 不吃 filters，所以钉死它就等于强制仓内比对，
  而忽略 query 的 `FakeVerifySite.__call__` 伪造不了仓内比对；`find_one` 则会无视 filters 直接回 `rows[0]`，
  **禁用它是承重的、不是装饰**；夹具补上真实键值之后，变异 ③ 会真正打断匹配并让状态 ① 的正向断言失败。
  ⑥ **仍无假绿路径**（`verify_site:837` 只做拼接、`ok` 只源自 `_numeric_check` → `_close`、`label` 只被 `line()` 消费），
  无红线问题；评审另点名确认 `tests/unit` 的两条 AST 结构测试（`:227` / `:245`）只管
  `DERIVED_CONSTANTS` 与 `EXPECTED_*` 金额字面量，**给 `_overdue_checks` 加 `M.COMPANY` / `M.day(...)` 不会触发它们**。
  非阻塞项已全部吸收：Phase 2 标题与 Closure Gate 里残留的「两条变异 / 四次」改准为「三条 / 六次」；
  `gate-proposal-seed-dataset.md:93-94` 补进 Phase 3 `Targets`；
  Baseline 2 里关于 `system-baseline.md:706` 的那处措辞张力已消除（历史记录不进分流）；
  Closure Gate 不再写死评审轮数。
  **共识达成，`Plan Status` 由 `draft` 改为 `active`。**

## Closure Gates

- [ ] in-scope behavior is complete（机制取证到位、红自解释、文档按分流改准）
- [ ] relevant docs are aligned（`seedsite.py` docstring · §14.5 · §12.10 · `project-context.md:57` · roadmap 追加行）
- [ ] verification has run：`python3 tools/gates/check_expected_red.py`（默认判定环境，判定行必须**逐字节不变**，
      基线三行逐字为 `判定模式：default —— 按 tools/gates/expected-red.txt 判定` /
      `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`，exit 0）·
      `python3 -m pytest tests/unit -q` · `python3 -m pytest tests/contracts -q` ·
      `ruff check agenerp tests/unit tests/contracts`（`project-context.md:52`；本 plan 动了 `tests/unit` 里的文件）·
      冷起站点四条 CLI · **三条**变异验证共六次
- [ ] scoped verification is not conflated with full verification —— **本 plan 的活站点证据只在本机取得**；
      合并后由既有 `gates-l2-seed` 在 `main` 上自然复跑一次，**该 run id 必须补记进 `## Closure`**。
      在拿到它之前，必须逐字记「verification scope limited：活站点证据限于本机」
- [ ] **合并后 `main` 上 `gates-l2-seed` 为 `success`**（本 plan 改的 `--verify-site` 正是它的第 ④ 步；
      若它红，走 `## Deferred But Adjudicated` 的落 `main` 后处置）
- [ ] no in-scope item downgraded to deferred/follow-up —— ⚠️ 若走首条固定处置，
      「按分流改准措辞」那三项的落点是 `adjudicated as residual-risk-only`（Anti-Slacking 允许的四态之一），
      **不是** downgrade 成 follow-up，两者不得混同
- [ ] independent draft review completed and recorded —— 轮次以 `## Draft Review Record` 的**实际记录**为准，
      **本行刻意不写死一个数**（首轮推翻了承重前提，此后每轮都在改，写死就会立刻过期）
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] **红线自查五条**：① `tests/gates/**` 零改动 ② `.github/workflows/**` 零改动
      ③ `docs/masterplan/DECISIONS.md` 零改动、无新增 `R-x` ④ `missions/**` 零改动
      ⑤ `docs/masterplan/STATE.md` 只追加不改写（仅分流 (ii)/(iii) 或停机时才写）

## Deferred But Adjudicated

### 拿不到可分流取证证据时的固定处置（写死，不临场决定）

- Classification: `watch-only residual`（失败分支的写死处置，不是被推迟的工作项）
- 处置逐字：记录所有已跑命令与输出原文 → 追加进 `docs/masterplan/STATE.md` §3（**不改写既有行**）→
  **docstring 与三处 owner doc 一个字不改**（在查清之前把「未取证」改成任何别的说法都是伪造）→
  **不猜根因**（裁判规则 3）。
- ⚠️ **它只让文档面停下，代码面照常落地。** Phase 2 的诊断**不依赖** Phase 1 的分流结论
  （Task Route 已逐字澄清这一点），把一个独立的交付面绑死在另一件事的取证结果上，
  正是评审第 8 条点名的耦合错误。**Phase 2 与 Phase 3 的实证项照常执行**，
  只有「按分流改准措辞」那几项落到 `adjudicated as residual-risk-only`
  （Anti-Slacking 的四态之一；**不是** `deferred`，也不是 downgrade 成 follow-up）。
- Successor Required: `no`
- 重开事件：**取得容器内可实读的源码证据时**，或**该断言在任一环境上第一次真的红时**（届时红因本身即证据）。

### `EXPECTED_*_OVERDUE` 仍依赖「今天 > 2026-03-10」这个单向前提

- Classification: `watch-only residual`
- Why Not Blocking Closure: `BASE_DATE` 冻结在 `2026-02-02`（源码常量，不读时钟），墙钟只单向前进，
  因此这个前提**随时间只会更成立**。**⚠️ 唯一的失效入口是把 `BASE_DATE` 改成未来日期或改成相对今天推算**，
  而后者已被 `## Non-Goals` 逐字排除（它会打掉门禁的确定性两条）。
  本 plan 交付的诊断**正是**这个入口的报警器。
- Successor Required: `no`
- 重开事件：**有人提议改 `agenerp/seed/model.py` 的 `BASE_DATE` 时**（届时必须先跑一遍本 plan 的诊断路径）。

### `gates-l2-seed` 的 step 名 `④ 站点侧对账（9 项）` 把项数写死在 CI 里

- Classification: `watch-only residual`
- Why Not Blocking Closure: D1 选 (d) 之后项数不变，该 step 名**此刻仍然为真**，本 plan 不需要改它。
  但它确实是一处**把可变数字写进 step 名**的耦合：将来任何一个真要改项数的 plan 都会被它绊一下，
  而改它要动 `.github/workflows/**`。**照实登记，不粉饰成「无风险」。**
- Successor Required: `no`
- 重开事件：**下一个真要改 `--verify-site` 项数的 plan 开工时**（届时它必须把这处 step 名一并纳入 scope）。

### 诊断用的「今天」可能是宿主时钟而非站点时钟

- Classification: `watch-only residual`
- Why Not Blocking Closure: 取决于 Proof B④ 的结论。**即使退到宿主时钟也不会造成假绿**——
  诊断不参与 `CheckResult.ok` 的计算（D1 的硬约束），它只出现在消息里，且 D2 要求逐字标注「宿主侧」。
  宿主与站点时钟若有差，表现是**诊断文字略有偏差**，不是判定结果错。
- Successor Required: `no`
- 重开事件：**站点侧只读时钟路径出现时**（届时应把口径切过去），
  或**第一次出现「诊断说没到期、站点却算出 `Overdue`」的自相矛盾输出时**。

### 拟断言 ② 的「销售订单达成率 100%」在当前口径下站点算不出来

- Classification: `out-of-scope improvement`（**人动作项**，`2107-2` 已登记，本 plan 继续挂着）
- Why Not Blocking Closure: 它依赖本仓虚构的 `Loss Review` DocType；给站点建它会造物理表（DDL），
  与本 plan 的 Non-Goals 直接冲突。本 plan 不重裁。
- Successor Required: `no`
- 重开事件：**人裁定是否允许为 `Loss Review` 建 DocType / 自定义字段时**，
  或**人给出一条站点可表达的达成率口径时**。

### 种子链的三条站点侧断言仍无门禁形态

- Classification: `watch-only residual`
- Why Not Blocking Closure: 新建 `tests/gates/**` 在红线 1 内，只有人能做
  （`docs/backlog/gate-proposal-seed-dataset.md`，`Status: proposed`）。
  ⚠️ **本 plan 交付的是可诊断性，不是门禁形态** —— 两者不得混为一谈：
  `GATE_VERIFY` 与 `check_expected_red.py` 仍然复跑不到 `--verify-site`。
- Successor Required: `no`（**人动作**）
- 重开事件：**人出具 `Gates-Change-Approved-By:` trailer 采纳提案时**。

### 工作项 7 仍卡在「从预期红名单划掉」这条 `done` 定义上

- Classification: `watch-only residual`
- Why Not Blocking Closure: 已登记的人裁定题（`docs/backlog/needs-human-expected-red-handoff.md`）。
  ⚠️ **不得把理由写成「工作项 7 没有门禁」**——它有一条 L1 门禁，只是那条门禁从未进过名单，
  「划掉」这个动作没有对象。本 plan 关闭时工作项 7 保持 `planned`。
- Successor Required: `no`
- 重开事件：**人从那份 handoff 文档的候选处置里选定时**。

### `--verify-site` 不覆盖「装载器本身报错了但对账仍绿」的假绿入口

- Classification: `watch-only residual`
- Why Not Blocking Closure: `2107-2` 已登记，本 plan 不扩大也不缩小它。
  本 plan 的诊断**只覆盖 overdue 那两项**，不是通用的装载完整性检查。
- Successor Required: `no`
- 重开事件：**第一次出现「装载失败而 `--verify-site` 仍退 0」时**（`2107-2` 写死的同一条）。

### 新单测的 CI 复跑依赖前驱 plan，而前驱此刻只是 `active`、尚未执行

- Classification: `watch-only residual`
- Why Not Blocking Closure: 本 plan 新增的单测是否被 CI 复跑，取决于 `2026-08-23-0120-1` 是否已落 `main`——
  它此刻是 `Plan Status: active`（已过评审）但**尚未执行、尚未落 `main`**。若它未落地，本 plan 的新单测**只在本机跑**。
  这不阻塞本 plan 的结果面（诊断行为已由本机两条变异验证钉住），
  但**必须在 `## Closure` 里逐字记明**，⚠️ **不得含糊成「已有 CI 覆盖」**。
- Successor Required: `no`
- 重开事件：前驱 plan 落 `main` 之后（届时把 CI run id 补记进本 plan 的 `## Closure`）。

## Closure

Status Note: <待关闭时填写>

Closure Audit Evidence:

- Auditor / Agent: <independent subagent>
- Evidence: <命令原文 + 退出码 + commit sha>

Follow-up:

- <非阻塞项；确认的缺陷不得出现在这里>
