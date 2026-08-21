# 2026-08-21-1922-3 差集 apply 引擎 · B 半（`execute_plan` 对活站点**真的删除**）

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 5. 差集 apply 引擎（读包 → 求差 → **对差集执行删除**）—— **B 半：对站点执行删除，不做建/改，不做孤儿列巡检**
> Last Reviewed: 2026-08-21
> Source: plan `2026-08-21-1553-1-diff-apply-engine-pure-half.md` 的 `## Deferred But Adjudicated` 第一条（「B 半」，`Successor Required: yes`），其重开事件已于 2026-08-21T11:13Z 由人满足 · `docs/backlog/p0-foundation-roadmap.md` 工作项 5 · `docs/architecture/module-boundaries.md` §11.1
> Related: `2026-08-21-1922-1-site-snapshot-source-live.md`（前置：站点客户端 + `SiteSnapshotSource.read`）· `2026-08-21-1922-2-export-customizations-live.md`（前置：门禁先要能导出，才谈得上从包里删掉再 apply）
> Audit: required

## Current Baseline

起草时（2026-08-21，HEAD `a9de1bb`）逐条读活代码得出。

### 承重条款：这是整个 P0 里唯一证明「revert 撤得回」的判据

`module-boundaries.md` §11.1 的 Spike 06 实测表：从定制包 JSON 里删掉字段再
`sync_customizations`，**站点上的字段纹丝不动**——`sync_customizations_for_doctype` 是纯 upsert，
**没有任何删除分支**。「删除集」这个概念在 Frappe 那条路径上根本不存在。
门禁 `test_removing_from_pack_actually_deletes_on_site`（`tests/gates/test_customization_roundtrip_delete.py:43`）
的 docstring 逐字称它为「**承重条款**」。P2 的「一句话改首页 → revert 撤得回」整条能力压在它上面。

### 已经在仓里的（本 plan 直接复用）——**注意区分「今天在仓里」与「前置 plan 承诺交付」**

- `agenerp/apply.py`：`read_pack`（`:60`）、`ApplyPlan`（`:30`，三序列 `creates` / `updates` / `deletes`）、
  `plan_apply`（`:73`，纯函数求差 + 方向不变量 `_assert_direction`，`:88` 起）——**全部已实现**（A 半，plan `…-1553-1`）。
- `agenerp/pack.py:71` `apply_pack(path, site)` 已改成委派链：
  `read_pack` → `capture(PACK_SCOPE, source=SiteSnapshotSource(site))` → `execute_plan`。签名不变。
- ⚠️ **以下两项起草时（HEAD `a9de1bb`）尚不在仓里**，由前置 plan 交付，本 plan 的 Phase 1 Prereqs 要求它们先关闭：
  第 1 顺位的站点客户端（`agenerp/site.py`，起草时 `ls` 不存在）与第 2 顺位的 `export_customizations`
  （`agenerp/pack.py:66` 起草时仍 `raise`）。写在这一节标题下是为了说明依赖，不是说它们已就绪。

### 本 plan 自己要填的缺口只有一处（站点侧起草时共有三处 `raise`）

起草时站点侧的三处：`agenerp/snapshot.py:147`（`SiteSnapshotSource.read`，第 1 顺位填）、
`agenerp/pack.py:66`（`export_customizations`，第 2 顺位填）、`agenerp/apply.py:107`（`execute_plan`，**本 plan 填**）。

`agenerp/apply.py:105` `execute_plan(plan, site)` —— 函数体 `raise NotImplementedError`（`:107`），
消息逐字写着「B 半（对站点执行）… loop 无权实现」。**那个「无权」的前提已经在 2026-08-21T11:13Z 消失**：
人在 `ede5440` 写完了三个 fixture（`tests/gates/conftest.py`），正是 STATE §3 那行 `[open]` 的处置项 (a)。
本 plan 因此有权做这半边，**但仍不得改 `tests/gates/**` 一个字节**（红线 1 未变）。

### 门禁逐字要求

```
live_site.add_custom_field(doctype="Item", fieldname=PROBE_FIELD, fieldtype="Data")
export_customizations(doctype="Item", into=pack_repo.path)
pack_repo.remove_field("Item", PROBE_FIELD)
apply_pack(pack_repo.path, site=live_site.name)
assert not live_site.has_custom_field("Item", PROBE_FIELD)
```

- `pack_repo.remove_field` 用 `json.dumps(payload, ensure_ascii=False, indent=2)` **重写**包文件
  （`tests/gates/conftest.py:279`）——即包文件在 apply 之前会被换成标准缩进排版。
  → **`read_pack` 必须照样读得懂**（它走 `json.loads`，与排版无关，起草时已确认），
  且第 2 顺位选的排版**不能靠自定义解析**。这条是两个 plan 之间的硬耦合，写在这里以免被漏掉。
- `live_site.name` 是 `"frontend"`（`tests/gates/conftest.py:171`），即 `apply_pack` 的 `site` 参数是**站点名**，
  不是 URL——地址与凭据仍从环境解析（第 1 顺位定的口径）。
- `has_custom_field` 查的是 `/api/resource/Custom Field/<dt>-<fieldname>` 返回 200
  （`_cf_name` 在 `:201`，`has_custom_field` 在 `:212`）→ **Custom Field 的文档名形如 `Item-agenerp_gate_roundtrip`**。
  这是从 fixture 读出来的事实；本 plan 仍要在活站点上实测确认一次（Phase 1 的 `Explore`），不靠推断动删除。

### 一个必须先解决的安全问题（起草时读活代码发现，独立评审已复核确认）

`apply_pack` 里的 `current` 是 `capture(PACK_SCOPE, source=SiteSnapshotSource(site))` ——
**整个 scope 的站点现状，不限于包里出现过的 DocType**（依据是第 1 顺位结构边界表里那行：
`read(scope)` 返回站点上**全部** Custom Field。**若第 1 顺位最终把 `read` 收窄成按 DocType 读，本条前提消失，
下面的收窄 `Decision` 必须重做**）。而门禁给的包只有 `Item.json`
（`export_customizations(doctype="Item", …)` 只导一个 DocType）。
→ 直接把 `plan.deletes` 拿去执行，会把**站点上其他 DocType 的全部定制字段一并删掉**。
门禁那条断言照样会绿（它只看 Item 上的探针没了），但这是一次静默的破坏性误删。
**判据不会替我们挡住这个错误**，所以本 plan 必须自带收窄 + 自己的判据。

**收窄口径的落点是关键，选错了承重条款直接过不了**（评审指出，起草时想错过一次，如实留痕）：

- 收窄集**不能**从 `ApplyPlan` 的条目里推。门禁的执行序是：导出 → `remove_field` 剔掉探针 → apply。
  若探针是 Item 上唯一的 Custom Field，`Item.json` 在 apply 时是**「文件在、数组空」**——
  包里一个 Item 条目都没有。按「包条目里出现过的 DocType」收窄，Item 就不在收窄集内，
  探针**不会被删**，承重条款照样红。
- 收窄集**必须来自包的文件覆盖面**：`<root>/doctypes/*.json` 里存在哪些 DocType 文件。
  「文件在、数组空」= 「这个 DocType 我管，且它应该没有定制」——这正是要执行删除的情形；
  「文件不在」= 「这个 DocType 不归这个包管」——这才是要跳过的情形。
- 因此落点在 `read_pack` / `apply_pack` 那一侧（拿得到目录），不在 `execute_plan` 里（它只拿得到条目）。

### 一处源真相冲突（先分类，再开工）

活代码两处逐字写 `execute_plan`「归工作项 6」（`agenerp/apply.py:11` 的模块 docstring、`:110` 的异常消息），
`module-boundaries.md` §11.6 落点表同样写「`raise`，归工作项 6」；
而 roadmap 对照表**第 5 行**把承重条款 `test_removing_from_pack_actually_deletes_on_site` 绑给**工作项 5**。
**裁定：以 roadmap 对照表为准**（它是判据绑定表，其余两处是叙述）。
`apply.py:11` / `:110` 那两句将随本 plan 的实现一并被替换，§11.6 落点表由 Phase 3 更正。
本 plan 因此挂在工作项 5 名下。

### 判定面与名单

- 行为判据落 `tests/unit/`（假客户端），`GATE_VERIFY` 复跑得到；L2 转绿只能 live 实测，复跑不到。
- **不划 `tools/gates/expected-red.txt` 任何一行**（默认环境下 L2 恒红，划了立刻假红）；
  工作项 5 因此停在 `planned`。该矛盾**将由第 1 顺位**在它的 Phase 3 实测并按 P0.7 先例补进 STATE §3 既有那条 `[open]`
  （起草时 §3 里**还没有**这一条，只有 fixture 那条 `[open]` 与 P0.7 的补充事实行）；本 plan 不重复登记。
- 本 plan 关闭后，`test_no_orphan_column_left_behind` **仍然红**，且红因会从
  `execute_plan` 挪到 `schema_drift`——这是预期结果，要在关闭时逐字记下来。

## Goals

- 交付 `execute_plan(plan, site)` 的**删除路径**：对差集里的 `deletes` 在活站点上真的删掉 Custom Field。
- 交付**作用域安全**：apply 只对**包里出现过的 DocType** 生效，绝不因为包没覆盖某个 DocType 就把它的定制删光。
- 交付**不静默**：`creates` / `updates` 非空时显式拒绝（本 plan 不做建/改），不假装执行成功。
- 让 `test_removing_from_pack_actually_deletes_on_site` 在 live 环境实测转绿，并用变异验证证明它有牙齿。

## Non-Goals

- **不实现建（creates）与改（updates）的执行**：P0 没有任何判据覆盖它们，现在写等于交付一段没人验的破坏性代码。
- 不实现 `schema_drift`、不删物理表残留列（`test_no_orphan_column_left_behind` 归工作项 6 的第二个 plan）。
- 不做事务/回滚语义（`rollback_and_report`、savepoint）——`02-WBS.md` 把写契约划给 **P3.1**。
- 不动 `plan_apply` 的求差**逻辑**、不动 `read_pack` 的签名与返回类型（A 半已定稿的公共面）。**方向不变量的失败机制要动**：
  裸 `assert` 换成显式 `raise`，理由见结构边界表——这是加严，不是改判定。
- 不改 `tests/gates/**`（红线 1）、`.github/workflows/**`、`missions/**`、`docs/masterplan/DECISIONS.md`；
  `STATE.md` 仅在停手分支追加证据行。
- **不划名单**；**不把工作项 5 置为 `done`**。
- 不生成运行时 Server Script（红线 7）。

## Task Route

- Type: `app-layer design change`（这是本项目第一条**对活站点做破坏性写操作**的路径，P2/P3 的回滚能力压在它的形状上）
- Owner Docs: 读 `docs/architecture/module-boundaries.md` §11.1（Spike 06 实测表与三个必须自建的部件）、
  §11.6（A 半落点表与方向约定）· 读 `docs/architecture/integration-and-transaction-patterns.md`（事务/副作用口径）·
  待更新：§11.6 的落点表（`execute_plan` 由 `raise` 改为「删除已实现，建/改显式拒绝」）
- Skill Selection Basis: 技能表无「对外部系统做破坏性写操作」的工作方法技能；
  形状被 `ApplyPlan` 与门禁双向钉死，属受限选择。各阶段 `Skill: none`；
  草案评审 `docs/skills/plan-audit-prompt.md`，关闭审计 `docs/skills/closure-audit-prompt.md`。
- 文档新鲜度：`project-context.md` 的 freshness 是 `partially stale`，其策略要求逐切片核实。
  本 plan 触碰的 owner doc（§11.1 / §11.6）与代码区已在 Current Baseline 里逐条读活代码核实；
  `docs/context/codebase-map.md` **全篇仍是未替换的模板占位符**，故**不作为权威**，以活仓为准。
  这是全仓既有欠账（前几个 plan 同样未管），本 plan 只如实记录，不顺手改它。
  **另**：本 plan 属破坏性路径，关闭审计额外套 `docs/skills/open-ended-audit-prompt.md`（找清单外的隐藏风险）。

## Infrastructure And Config Prereqs

- 依赖第 1 顺位的站点客户端（本 plan 为其**新增删除方法**——它此前只读）与第 2 顺位的 `export_customizations`。
- 无新增环境变量、无新增第三方依赖。**本 plan 引入 `agenerp` 的第一处 `logging` 用法**
  （被收窄掉的条目要可观测；起草时 `grep -rn "import logging\|getLogger" agenerp/` 无命中）。
- live 实跑必须带 `AGENERP_HTTP_PORT=18080`。
- **回滚策略（本 plan 唯一有站点侧副作用的 plan，必须写明，且必须诚实）**：
  代码侧 `git revert` 即回到今天。**站点侧只能手工重建**（REST `POST /api/resource/Custom Field` 或 Desk）——
  因为本 plan **显式拒绝 `creates`**，拿包去 `apply_pack` 只会立刻抛错，
  「用包把删掉的字段建回来」这条路要等 `creates` 落地（Deferred 第一条）。
  §11.1 表里「从定制包 sync 回来 → 字段回来」走的是 Frappe `sync_customizations`，**本项目不用它**。
  物理列未被删（Spike 06 实测「删 Custom Field 不删列、数据仍在」），故重建后业务数据**很可能**仍在，
  但这条未在本仓实测过，**不得当成保证**。
- **保护区**：本 plan 引入本仓第一条「对活站点的破坏性写」路径。
  `docs/context/ai-autonomy-policy.md` 的 Protected Areas 表现在没有对应行
  （表里「数据删除」逐字写着 `none（本项目当前无自有实现面）`，并注明「将来出现时，先在本表补行再动手」）。
  → Phase 1 首项就是补这一行（**只允许加严**，符合该文件「AI 可以收紧、不得放宽」的规则）。

## 结构边界（本 plan 定稿的接口契约）

| 落点 | 契约 | 谁实现 |
|---|---|---|
| `agenerp/site.py` · 删除方法 | 站点侧删除的**唯一**出口：删一条 Custom Field，路径 URL 编码，非 2xx 抛 `SiteError`。**不提供「删任意 DocType 文档」的通用方法**——通用删除接口是把业务数据交出去 | 本 plan |
| `agenerp/apply.py` · `execute_plan(plan, site)` | 执行 `plan.deletes`：逐条调站点删除方法，**顺序确定**（按 `key` 排序），失败即抛不吞。`plan.creates` / `plan.updates` 非空 → 抛 `NotImplementedError` 并指名 successor。空计划 → 无副作用直接返回 | 本 plan |
| `agenerp/apply.py` · `pack_doctypes(path, scope)`（新增函数） | 算出收窄集 = **包目录里存在文件的 DocType 集合**（不是包条目里出现过的 DocType——见 Current Baseline 的「文件在、数组空」）。**口径与 `entries_from_payload` 同源**：载荷 `doctype` 键优先、文件名 stem 兜底（`agenerp/snapshot.py:172`）——只按文件名算，一份 `Item.json` 内写 `{"doctype": "Customer"}` 会让管辖面与条目面对不上 | 本 plan |
| `agenerp/apply.py` · `read_pack` | **签名与返回类型不变**（`-> Snapshot`）。收窄集从上面那个独立函数拿，不塞进它的返回值——那是 A 半已定稿的公共面 | 不动 |
| 收窄的执行位置 | 在 `apply_pack` 的委派链里：`plan_apply` 正常求差 → **按收窄集过滤 `plan.deletes`** → `execute_plan`。不塞进 `plan_apply`（Non-Goals），也不塞进 `execute_plan`（它拿不到目录）。方向不变量在过滤前已对全集通过，过滤只做删减，不受影响 | 本 plan |
| 被收窄掉的条目的**可观测面** | `logging.getLogger("agenerp.apply")` 发一条 WARNING，逐条列出被跳过的 `(doctype, fieldname)`；单测用 `caplog` 断言。**这是「不许静默丢弃」这个安全承诺的唯一判据**，落地面必须现在写死——`agenerp/` 全树今天没有任何 logging，这是第一处 | 本 plan |
| `agenerp/apply.py` · `_assert_direction`（`:88`） | 裸 `assert` 改成显式 `raise`（新异常类型）。A 半时它只是纯逻辑自检；B 半接上真删除之后，它是**唯一**挡住「`desired`/`current` 传反 → 把整站定制算成待删」的运行时闸门，而 `python -O` / `PYTHONOPTIMIZE=1` 会把裸 `assert` 整条剥掉 | 本 plan（Non-Goals 里「不动方向不变量」指的是**不动它的判定逻辑**，不是不动它的失败机制） |
| `agenerp/pack.py` · `apply_pack` | **签名不变**（门禁逐字 `apply_pack(pack_repo.path, site=live_site.name)`），**委派链增加一步收窄** | 本 plan |
| `agenerp/snapshot.py` · `schema_drift` | **不动**，仍 `raise` | 工作项 6 的第二个 plan |

## Execution Plan

### Phase 1 — 实测删除语义（`Explore`）+ 作用域裁定（`Decision`）

Status: completed
Targets: `docs/context/ai-autonomy-policy.md`、`docs/architecture/module-boundaries.md` §11.6、本 plan（无 `agenerp/` 代码产物）
Skill: `none`
Prereqs: 第 1、2 顺位 plan 均已关闭

- Item Types: `Explore | Decision | Add`

- [x] `Add` **首项**：`docs/context/ai-autonomy-policy.md` 的 Protected Areas 表补一行
      「对活站点的破坏性写（删除 Custom Field）」，规则取 `plan-first`，
      Required Evidence 写明「独立草案评审 + 独立关闭审计 + 实跑前后全量 `capture` 对照」。**只加严，不放宽。**
- [x] `Explore` 在活站点上实测四件事，命令原文与响应一并抄进 plan：
      ① Custom Field 的文档名是否确为 `<dt>-<fieldname>`；
      ② `DELETE /api/resource/Custom Field/<name>` 的返回码与副作用（字段是否真消失）；
      ③ 删完之后 `capture` 再读一次，条目是否真的少了一条（**站点说删了 ≠ 快照看得见**）；
      ④ **全站 Custom Field 清点**，含 `is_system_generated`（或等价标记）的分布——
      这是判断「按 DocType 收窄会不会连带删掉应用自带字段」的唯一依据。
- [x] `Explore` **不执行删除的预演，且是停手闸**（它对站点有写副作用——要建探针，别叫「只读」）：
      载体是 `_tmp/` 下一段一次性脚本（用第 1 顺位的客户端建探针 + 第 2 顺位的 `export_customizations`
      + 手工改包 JSON + `read_pack` / `capture` / `plan_apply`，跑完删探针）；
      **不 import `tests/gates/` 的任何东西**（红线 1）。按门禁那五行的形状走一遍但**不执行删除**，
      把 `plan.summary()` 与 `len(creates)/len(updates)/len(deletes)` 逐字抄进 plan。
      **`creates` 或 `updates` 非空即停手**，退回第 2 顺位修投影（那说明导出投影与站点投影不同源，
      往返不变量 1 破了），而不是等到 Phase 3 撞上——那时的红因是 `NotImplementedError`，
      与「B 半还没实现」逐字难以区分，极易误判。
- [x] `Decision` **作用域收窄口径**：取「收窄集 = 包目录里**存在文件**的 DocType 集合」。
      备选：① 不收窄（**已被 Current Baseline 的安全问题排除**：一个只含 Item 的包会删光全站定制）；
      ② 按**包条目**里出现过的 DocType 收窄（**已被排除**：「文件在、数组空」时 Item 不在集内，承重条款红）；
      ③ 给 `apply_pack` 加显式 `doctypes=` 参数（更精确，但门禁的调用式是
      `apply_pack(pack_repo.path, site=live_site.name)`，加必填参数就改不了调用方，加可选参数则默认路径仍不安全）；
      ④ 让 `capture` 只读包里的 DocType（把安全约束塞进快照层，污染职责边界，且 `capture` 是共享件）。
      残余风险：包里**故意删掉整个 DocType 文件**表达「清空这个 DocType 的定制」这一意图，在收窄口径下**表达不出来**——
      如实登记为 deferred，重开事件是 P2 出现该需求时。
- [x] `Decision` **应用自带 / `is_system_generated` 的 Custom Field 是否排除在删除集外**。
      依 Explore ④ 的实测分布决定；默认建议**排除**（ERPNext 与区域化设置会往 DocType 上装 Custom Field，
      删掉可能直接弄坏应用功能，而按 DocType 收窄挡不住这一类）。
      残余风险若排除：包不再是该 DocType 的完整真相源，`git revert` 撤不掉系统生成的定制——如实登记。
- [x] `Decision` **建/改一律显式拒绝**。备选：① 一并实现（无判据覆盖的破坏性代码，未取）；
      ② 静默跳过（**明令禁止**：假装成功正是本仓反复挡的那种事）。
      残余风险：`apply_pack` 对「包里有站点上没有的字段」这类真实场景暂时用不了——P2 之前没有调用方，可接受。

Exit Criteria:

- [x] Protected Areas 表已补行（只加严）
- [x] 四条 Explore 结论 + 不执行删除的预演的三个计数（含命令原文与响应）落进 plan
- [x] 三条 `Decision` 各有选择、备选、残余风险，并写进 `module-boundaries.md` §11.6
- [x] 不执行删除的预演的 `creates` / `updates` **均为空**；非空则本 plan 停手，按停手分支处理（追加 STATE 证据行 + 退回第 2 顺位）
- [x] `docs/logs/2026/08-21.md` 追加条目

### Phase 2 — `execute_plan` 落地 + 判据

Status: completed
Targets: `agenerp/site.py`、`agenerp/apply.py`、`tests/unit/test_apply_execute.py`（新文件）
Skill: `none`
Prereqs: Phase 1

- Item Types: `Add | Proof`

- [x] `Fix | Decision` **先处理与第 1 顺位判据的冲突**：第 1 顺位的不变量 4 是一条结构断言——
      「公共方法名里出现 `agenerp/contracts.py:40` 的 `WRITE_VERBS`（含 `delete`）的，必须在**显式白名单**里」，
      本 plan 加的删除方法正好命中。**处置：把 `delete_custom_field` 加进白名单并说明理由**——
      这是收窄式演进（每加一个写方法留一次痕），不是取消判据；同步第 1 顺位在 `module-boundaries.md` 追加的小节。
      **不这么做，Phase 2 的退出判据 `pytest tests/unit -q → exit 0` 在合同层面就不成立。**
- [x] `Add` 站点客户端增删除方法（只删 Custom Field，路径编码，非 2xx 抛）。
- [x] `Add` 新增 `pack_doctypes(path, scope)` 算收窄集（口径与 `entries_from_payload` 同源），
      并在 `apply_pack` 的委派链里过滤 `plan.deletes`；`read_pack` 签名与返回类型不动。
- [x] `Add` 被收窄掉的条目发 WARNING（`logging.getLogger("agenerp.apply")`），逐条列出 `(doctype, fieldname)`。
- [x] `Add` `execute_plan` 实现删除路径：按 `key` 排序 → 逐条删 → 任一条失败即抛。
- [x] `Fix` `_assert_direction`（`agenerp/apply.py:88`）的裸 `assert` 换成显式 `raise`（新异常类型），
      理由见结构边界表（`python -O` 下裸 `assert` 整条消失，而它是挡住灾难性误删的最后一道闸）。
- [x] `Add` `creates` / `updates` 非空时抛 `NotImplementedError`，消息指名 successor 与本 plan 的 `Decision`。
- [x] `Proof` 单测（假客户端，不连真站点）：
      ① 只对 `deletes` 发删除请求，条数与目标逐条相符；
      ② **作用域收窄，正反两断言写在同一个用例里**：包只含 `Item.json`、站点上有 `Item.probe` 与 `Customer.probe`
      → **恰好发出一条删除请求且目标是 `Item-probe`**（正），**且对 Customer 零请求**（反）。
      只写反断言的话，一个什么都不删的空实现完美通过——那正是最可能发生的失败模式；
      ③ **「文件在、数组空」回归**：`Item.json` 存在但 `custom_fields` 为空、站点上有 `Item.probe`
      → 必须发出删除请求。这条直接对应承重条款在门禁里的真实状态，漏了它门禁会红而单测全绿；
      ④ 被收窄掉的条目可观测：`caplog` 里有 WARNING 且逐条列出 `(doctype, fieldname)`；
      ④b **covered 口径同源**：`Item.json` 内写 `{"doctype": "Customer", …}` 时，管辖面按载荷 `doctype` 算（不按文件名）；
      ⑤ 站点删除失败 → 抛，且**不继续删后面的**；
      ⑥ 空计划（且包目录为空）→ 零请求；
      ⑦ `creates`/`updates` 非空 → 抛且消息指名；
      ⑧ 方向传反 → 抛新异常类型（而不是靠裸 `assert`）。
- [x] `Proof` 端到端纯逻辑回归（不连站点）：包里删掉一个字段 → `plan_apply` 把它算进 `deletes`
      → `execute_plan` 对它发出删除请求。**反 upsert 回归**的完整链路在单测里跑通一次。

Exit Criteria:

- [x] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0，
      且 `tests/unit/test_apply_execute.py` 存在、用例数 **≥ 8**（上列八条），记录用例数增量
- [x] `ruff check agenerp tests/unit tests/contracts` → exit 0
- [x] `agenerp/apply.py` 内 `execute_plan` 不再无条件 `raise`
- [x] **owner-doc 更新集中在 Phase 3**（理由：§11.6 落点表要等 live 实测结论才写得准）——
      本 phase 无 owner-doc 更新是**有意的**，不是遗漏
- [x] `docs/logs/2026/08-21.md` 追加条目

### Phase 3 — 活站点实跑承重条款 + 变异验证 + 文档

Status: completed
Targets: `docs/architecture/module-boundaries.md` §11.6、`docs/backlog/p0-foundation-roadmap.md`、`docs/logs/`
Skill: `none`
Prereqs: Phase 2

- Item Types: `Proof`

- [x] `Proof` **实跑必须跑在 fixture 自己拉起的一次性栈上**：先确认本仓的栈没在跑
      （`compose_stack` 只在 `started_by_us` 时 `down`，`tests/gates/conftest.py:157` 起；
      栈本来就跑着的话它会复用别人的站点且用完不拆）。命令与判断依据抄进 plan。
- [x] `Proof` **全量 `capture("doctypes")` 前后对照，两处边界各自写清期望值**（唯一能看住「误删了别的东西」的判据，不许省）：
      ① 围绕**整个 pytest 文件的运行**取前后快照 → 期望**差集为空**。
      理由：`live_site` 的 teardown 会把每条测试自建的探针删净（`tests/gates/conftest.py:219` 起），
      一次完全正确的运行不会留下任何探针——写成「恰好只有探针」的话，正确的运行反而不满足退出判据。
      ② 围绕**单次 `apply_pack`**（下一条的手工作用域实验里）取前后 → 期望**差集恰好只有那一个探针**。
      收窄失效时 after 会少掉别的 DocType 的字段，差集非空且方向是「消失」，两处都抓得住。前后清单与差集逐字抄进 plan。
- [x] `Proof` live 实跑，命令原文：
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q`
      → 期望三条绿（导出两条 + 删除一条），`test_no_orphan_column_left_behind` 仍红**且红因是 `schema_drift` 未实现**
      （本 plan 落地后它才第一次走得到那一步；落地前它红在 `execute_plan`）。
      退出码、失败原文、红因逐字照抄。**若红因是 `NotImplementedError: creates/updates 非空`，
      那是投影不同源（往返不变量 1 破了），不是本 plan 未实现**——按 Phase 1 停手闸处理。
- [x] `Proof` **变异验证（承重条款必须做）**：临时把 `execute_plan` 的删除改成 no-op，
      `test_removing_from_pack_actually_deletes_on_site` 必须**转红**并逐字报「字段仍在站点上」。
      不转红说明判据是空转的，那比实现没写更危险。验证后还原，并复核工作区**相对变异前的基线**无残留
      （Phase 2 的产物此时可能尚未提交，`git diff` 天然非空，别用「`git diff` 为空」当判据）。
- [x] `Proof` **作用域安全的活站点验证**：在站点上另建一个别的 DocType 的探针字段，
      跑一次只含 Item 的包的 apply，确认它**没被删掉**，随后手动清理。命令与结果照抄。
      （单测里的假客户端证明不了真站点上的行为，这条不能省。）
- [x] `Proof` 收尾复跑**默认环境**判定器 `python3 tools/gates/check_expected_red.py` → exit 0，名单一行未动。
      **live 环境下的判定器退 1 是预期**（本 plan 让第二条名单内门禁在 live 下转绿，把第 1 顺位预告的矛盾放大了一档）：
      逐字抄进日志并指回 STATE §3 那行，不得被读成回归。
- [x] `Add` §11.6 落点表更新：`execute_plan` 由「`raise`，归工作项 6」改为「删除已实现（本 plan），建/改显式拒绝」；
      并把 Spike 06 那条「revert 撤不回」的结论补上本仓的实测反证（现在撤得回了）。
- [x] `Add` roadmap 工作项 5 保持 `planned`，对照表第 5 行注明：承重条款已在 live 环境实测转绿、名单未动、
      原因指向 STATE §3 那行 needs-human。

Exit Criteria:

- [x] 全部命令原文 + 退出码落进 plan 与日志
- [x] 实跑前后的全量 `capture` 清单与差集落进 plan，两处边界各自达标：
      **整文件运行 → 差集为空**（探针由各 test 的 teardown 清掉）；**单次 `apply_pack` → 差集恰好一个探针**
- [x] 变异验证与作用域安全验证都有实测记录
- [x] `tools/gates/expected-red.txt` 一行未动
- [x] `module-boundaries.md` §11.6 与 roadmap 第 5 行已更新

## 实测回填

### Phase 1 · `Explore` —— 活站点上的删除语义（2026-08-21，栈端口 18080）

载体：`_tmp/explore_delete_semantics.py` 与 `_tmp/explore_probe_flag.py`（一次性脚本，
**不 import `tests/gates/` 的任何东西**，红线 1）。命令原文：

```
AGENERP_HTTP_PORT=18080 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
  AGENERP_ADMIN_PASSWORD=admin python3 _tmp/explore_delete_semantics.py
```

**① Custom Field 的文档名确为 `<dt>-<fieldname>`（实测，不是从 fixture 推断的）**

```
[①] POST /api/resource/Custom Field → HTTP 200
    返回的 name = 'Item-agenerp_explore_probe'；期望 Item-'agenerp_explore_probe' 形状 → 相符：True
    GET /api/resource/Custom Field/<name> → 200
```

**② `DELETE /api/resource/Custom Field/<name>` 的返回码与副作用**

```
[②] DELETE /api/resource/Custom Field/Item-agenerp_explore_probe → HTTP 202；body[:120]='{"data":"ok"}'
    删后 GET 同一路径 → 404 （404 = 真消失）
[②b] DELETE 一个不存在的 name → HTTP 404；body[:120]='{"exc_type":"DoesNotExistError"}'
```

→ 成功码是 **202**（不是 200/204）。客户端的成败判据因此必须写成 `200 <= status < 300`
（`SiteClient._request` 本就是这个口径，无需为删除另开分支）；`404` 会被判为失败并抛 `SiteError`，
即**「要删的东西不在」不被静默吞掉**——这正是不伪装成功那条约束要的行为。

**③ 站点说删了 ≠ 快照看得见 —— 复读 `capture` 确认条目真的少了一条**

```
    删除前 capture 条目数：11；含探针：True
[③] 删除后 capture 条目数：10（前 11）；含探针：False
    差集： [('Item', 'agenerp_explore_probe')]
```

**④ 全站 Custom Field 清点（收窄口径能否挡住应用自带字段的唯一依据）**

```
[④] 全站 Custom Field 共 10 行
    is_system_generated 分布： {(1,): 10}
    覆盖 DocType 数：7；Top10：[('Print Settings', 3), ('Address', 2), ('Communication', 1),
                                ('Contact', 1), ('Customer', 1), ('Email Account', 1), ('Quotation', 1)]
    is_system_generated 为真的条目数：10
    Item 上现有： []
```

逐条清单（`_tmp/explore_probe_flag.py`）：`Address.is_your_company_address`、`Address.tax_category`、
`Communication.company`、`Contact.is_billing_contact`、`Customer.crm_deal`、`Email Account.company`、
`Print Settings.compact_item_print`、`Print Settings.print_taxes_with_zero_amount`、
`Print Settings.print_uom_after_quantity`、`Quotation.crm_deal` —— **10 条全部 `is_system_generated = 1`**，
全部由 ERPNext / CRM 应用装上去，**没有一条在 `Item` 上**。
REST 建出来的探针实测 `is_system_generated = 0`（`_tmp/explore_probe_flag.py`：
`probe is_system_generated = 0`），且 `normalize` 不剥这个键（它不含 modified / creation / owner / `_comments`），
所以它在快照条目的 `attributes` 里读得到——`Decision` 2 的判据面因此是存在的，不是推测。

### Phase 1 · 不执行删除的预演（停手闸，2026-08-21）

载体：`_tmp/rehearse_no_delete.py`（一次性脚本，建探针 → `export_customizations` → 手工按
`pack_repo.remove_field` 的口径重写包文件 → `read_pack` / `capture` / `plan_apply` → **到此为止，不删** →
清理探针）。命令原文：

```
AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
  AGENERP_ADMIN_PASSWORD=admin python3 _tmp/rehearse_no_delete.py
```

逐字输出：

```
① add_custom_field → 200
② export_customizations → 文件存在： True
   导出后 Item.json 条目数： 1
③ remove_field 后条目数： 0 · 文件仍在： True
   read_pack 条目数： 0 · capture 条目数： 11
④ plan.summary() = scope=doctypes · 删除 11：Address.is_your_company_address, Address.tax_category,
   Communication.company, Contact.is_billing_contact, Customer.crm_deal, Email Account.company,
   Item.agenerp_gate_roundtrip, Print Settings.compact_item_print,
   Print Settings.print_taxes_with_zero_amount, Print Settings.print_uom_after_quantity, Quotation.crm_deal
   len(creates)=0 len(updates)=0 len(deletes)=11
   ⚠️ 不执行删除 —— 本脚本到此为止
cleanup DELETE 探针 → 202
```

**停手闸判定：`creates` = 0、`updates` = 0 → 通过，本 plan 继续。**
（意味着导出投影与站点投影确实同源——往返不变量 1 成立，Phase 3 若红在 `NotImplementedError`
就不该被读成「投影不同源」。）

**同时实测坐实了 Current Baseline 那条安全问题，一个字不用改**：包只含 `Item.json`（且条目为空），
而 `plan.deletes` 有 **11** 条，其中 **10 条是别的 DocType 上应用自带的字段**。
直接执行 `plan.deletes` 会把它们全删光，而门禁那条断言（只看 Item 上探针没了）照样绿。
**「文件在、数组空」也被实测坐实**：`remove_field` 之后 `Item.json` 仍在、条目数 0、`read_pack` 读到 0 条——
按「包**条目**里出现过的 DocType」收窄的话 `Item` 不在收窄集内，承重条款会红。

### Phase 1 · `Decision` 1 —— 作用域收窄口径取「包目录里**存在文件**的 DocType 集合」

- **取此**。落点是 `agenerp/apply.py` 新增的 `pack_doctypes(path, scope)`，在 `apply_pack` 的委派链里
  过滤 `plan.deletes`（`plan_apply` 与 `read_pack` 都不动）。
- 备选与排除理由：
  - ① 不收窄 —— **实测排除**：上面的预演里 `deletes` 是 11 条而包只管 Item，会删光 10 条应用自带字段。
  - ② 按**包条目**里出现过的 DocType 收窄 —— **实测排除**：`remove_field` 后 `Item.json` 是「文件在、数组空」，
    `Item` 不在集内，探针不会被删，承重条款照样红。
  - ③ 给 `apply_pack` 加显式 `doctypes=` 参数 —— 未取：门禁的调用式是
    `apply_pack(pack_repo.path, site=live_site.name)`，加必填参数改不了调用方；加可选参数则默认路径仍不安全。
  - ④ 让 `capture` 只读包里的 DocType —— 未取：把安全约束塞进共享的快照层，污染职责边界。
- **残余风险**：靠**删除包文件**表达「清空该 DocType 的全部定制」这一意图表达不出来
  （删文件 = 「不管这个 DocType」）。「文件在、数组空」这条路是通的，P0 无此需求，
  且默认口径偏保守（少删），错的方向在安全那一侧。已登记在 `## Deferred But Adjudicated` 第二条。

### Phase 1 · `Decision` 2 —— `is_system_generated` 的 Custom Field **排除在删除集外**

- **取此（排除）**。依据是 Explore ④ 的实测分布：站点上 10 条 Custom Field **全部** `is_system_generated = 1`，
  分布在 7 个 DocType 上，全部由 ERPNext / CRM 应用装上去；REST 建出来的探针是 `0`。
  **按 DocType 收窄挡不住这一类**——只要包里出现过 `Address.json` / `Customer.json`，
  该 DocType 上应用自带的字段就落进删除集，删掉可能直接弄坏应用功能（`Customer.crm_deal` 之类）。
- 备选：不排除（即「包是该 DocType 的完整真相源」）—— 未取，理由同上；它把「包一时没导全」
  这种很常见的状态直接放大成破坏性删除。
- **残余风险（如实登记）**：包因此**不是**该 DocType 的完整真相源——从包里删掉一条
  `is_system_generated` 的字段，apply 不会照做，`git revert` 撤不掉这一类定制。
  代价被限定在「应用自己装的字段」上，而那一类本就不该由定制包管辖。
  可观测面与收窄同源：被排除的条目一并发 WARNING（不静默）。

### Phase 1 · `Decision` 3 —— 建（`creates`）/ 改（`updates`）一律**显式拒绝**

- **取此**。`execute_plan` 在 `plan.creates` 或 `plan.updates` 非空时抛 `NotImplementedError`，
  消息指名 successor（`## Deferred But Adjudicated` 第一条）与本 `Decision`。
- 备选：① 一并实现 —— 未取：P0 没有任何判据覆盖它们，现在写等于交付一段没人验的破坏性代码；
  ② 静默跳过 —— **明令禁止**：假装成功正是本仓反复挡的那种事。
- **残余风险**：`apply_pack` 对「包里有站点上没有的字段」这类真实场景暂时用不了；P2 之前没有调用方，可接受。
  代价还包括：站点侧的回滚只能手工做（见 `## Infrastructure And Config Prereqs` 的回滚策略）。

### Phase 2 · 落地与判据（2026-08-21）

产物（全部在 `agenerp/` 与 `tests/unit/`，**`tests/gates/**` 一个字节未动**）：

| 落点 | 交付 |
|---|---|
| `tests/unit/test_site_client.py` · `WRITE_METHOD_ALLOWLIST` | `()` → `("SiteClient.delete_custom_field",)`，注释里写明理由与「不提供删任意 DocType 文档的通用方法」这条边界 |
| `agenerp/site.py` · `SiteClient.delete_custom_field` | 站点侧删除的唯一出口；文档名口径抽成模块级 `custom_field_name()` |
| `agenerp/snapshot.py` · `doctype_from_payload` | 新增，与 `entries_from_payload` 共用 `_normalized_payload`（不开第二套解析口径） |
| `agenerp/apply.py` · `pack_doctypes` / `narrow_deletes` / `ApplyDirectionError` | 收窄集、纯函数收窄 + WARNING、方向不变量的显式失败类型 |
| `agenerp/apply.py` · `execute_plan(plan, site, client=None)` | 删除路径；建/改显式拒绝；空删除集零副作用 |
| `agenerp/pack.py` · `apply_pack` | 委派链三步 → **四步**（读包 → 求差 → **收窄** → 执行），签名不变 |
| `tests/unit/test_apply_execute.py` | 新文件，**19 条用例**（plan 要求 ≥ 8） |
| `tests/unit/test_apply_plan.py` | 那条「必须红在执行未实现」如实改写 + 新增一条反向断言（退回 `raise` 就红） |

**用例数增量：`tests/unit` 由 144 passed → 164 passed（+20）**，其中新文件 19 条、
`test_apply_plan.py` 净增 1 条。

退出判据（命令原文 + 退出码，退出码单独取 `$?`）：

```
python3 tools/gates/check_expected_red.py         → 0（门禁 19 项：预期红 7，绿 12，跳过 0 · ✅ 与预期红名单完全一致）
python3 -m pytest tests/unit -q                   → 0（164 passed）
ruff check agenerp tests/unit tests/contracts     → 0（All checks passed!）
python3 -m pytest tests/contracts -q              → 0（151 passed）
```

`agenerp/apply.py` 的 `execute_plan` **不再无条件 `raise`**：反向判据是
`tests/unit/test_apply_plan.py::test_execute_plan_no_longer_reds_unconditionally`
（把实现退回接缝状态就红）。

### Phase 3 · 活站点实跑、变异验证与文档（2026-08-21）

#### 前置：确认本仓的栈没在跑，实跑落在 fixture 自己拉起的一次性栈上

起手时本仓的栈**正跑着**（前一个 plan 的 live 会话留下的，端口 18080）。按 plan 的要求先拆掉：

```
docker compose -f docker-compose.yml down            → exit 0
docker compose -f docker-compose.yml ps --format json → 无输出
lsof -nP -iTCP:18080 -sTCP:LISTEN                     → 无输出（端口空闲）
```

判断依据逐字复刻 `tests/gates/conftest.py` 的 `_running_frontend_port()`（按 `Service == "frontend"`
且 `State == "running"` 找 `TargetPort == 8080` 的 `PublishedPort`）→ 返回空串，即
`already_up = False` → fixture 会**自己 `up`、用完 `down`**。实跑结束后复查
`docker compose ps --format json` **无输出**，证实那套栈已被 fixture 拆掉。

#### 承重条款 live 实跑（一次性栈）

```
AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q
```

→ **exit 1**，`1 failed, 3 passed in 28.88s`。

- **三条 PASSED**：`test_added_field_exports_into_pack`、`test_export_produces_readable_diff_only`、
  **`test_removing_from_pack_actually_deletes_on_site`（承重条款，本 plan 的目标）**。
- 唯一 FAILED 的是 `test_no_orphan_column_left_behind`，**红因已按预判从 `execute_plan` 挪到 `schema_drift`**，
  逐字：`agenerp/snapshot.py:328: NotImplementedError: schema_drift 尚未实现 …（工作项 5 · 差集 apply 引擎）`。
  它**第一次走得到那一步**——落地前它红在 `agenerp/apply.py:107` 的 `execute_plan`。
- 红因**不是** `NotImplementedError: creates/updates 非空`，即 Phase 1 停手闸的结论（投影同源）在 live 也成立。
- 同一次运行里 `agenerp.apply` 的 WARNING 逐字出现在 `Captured log call` 里：
  `apply 跳过 10 条**不在定制包管辖范围内**的删除（包覆盖的 DocType：['Item']）：('Address', 'is_your_company_address'), …`
  —— 收窄在真站点上生效，且**不静默**。

#### 全量 `capture` 前后对照 · 边界 ①：整个 pytest 文件的运行 → 差集为空

（这一格与下一格跑在**我自己 `up` 起来的**一套栈上，因为「围绕整文件运行取前后快照」要求栈在
pytest 之外也活着；一次性栈在 teardown 时就没了，量不到 after。两套栈用同一批持久卷，站点数据相同。
如实分栈记录，不含糊成「都在一次性栈上做的」。）

前后各一次 `capture("doctypes")` 全量清点，**两次都是 10 条、逐条相同**：

```
Address.is_your_company_address / Address.tax_category / Communication.company /
Contact.is_billing_contact / Customer.crm_deal / Email Account.company /
Print Settings.compact_item_print / Print Settings.print_taxes_with_zero_amount /
Print Settings.print_uom_after_quantity / Quotation.crm_deal
```

```
diff _tmp/capture-before-file.txt _tmp/capture-after-file.txt   → exit 0，无输出
```

→ **差集为空，达标**（探针由 `live_site` 的 teardown 清掉，一次完全正确的运行不留任何东西）。
本次运行本身：`… python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q` → exit 1，
`1 failed, 3 passed in 5.50s`（与一次性栈上那次逐条一致）。

#### 全量 `capture` 前后对照 · 边界 ②：单次 `apply_pack` → 差集恰好一个探针（并入作用域安全实测）

载体 `_tmp/scope_safety_live.py`：站点上**同时**建 `Item.agenerp_scope_probe_item` 与
`Customer.agenerp_scope_probe_customer`，只 `export_customizations(doctype="Item", …)`，
从包里剔掉 Item 探针（包里因此只有 `Item.json` 一个文件），跑**一次** `apply_pack`。

```
包里剩下的 DocType 文件： ['Item.json']
[apply_pack 前] 条目数 12
[apply_pack 后] 条目数 11
差集·消失： [('Item', 'agenerp_scope_probe_item')]
差集·新增： []
判定 ①（差集恰好只有那一个探针）： True
判定 ②（Customer 探针仍在，作用域收窄生效）： True
```

同一次运行发出的 WARNING 逐字：
`apply 跳过 11 条**不在定制包管辖范围内**的删除（包覆盖的 DocType：['Item']）：…, ('Customer', 'agenerp_scope_probe_customer'), ('Customer', 'crm_deal'), …`

→ **不收窄的话这一次会连删 11 条**（其中 10 条应用自带 + 1 条 Customer 探针），而门禁照样绿。
收窄真的在活站点上挡住了它。随后手动清理：Customer 探针 `DELETE → 202`；
Item 探针 `DELETE → 404`（**它已被 apply 删掉了**，正是本条要证明的事），清理后站点回到 10 条。

#### 变异验证（承重条款必须做）

变异前基线：`shasum -a 256 agenerp/apply.py` → `861d9f20…f1b574fd`，
`git status --porcelain` 存档为 `_tmp/status-before-mutation.txt`（**不用「`git diff` 为空」当判据**——
Phase 2 的产物此时尚未提交，工作区天然非空）。

把 `execute_plan` 的删除改成 no-op 后：

```
… python3 -m pytest "tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site" -q
```

→ **exit 1**，`1 failed`，逐字：

```
E       AssertionError: 从定制包删除并 apply 之后，字段仍在站点上 —— 说明 apply 是纯 upsert，revert 撤不掉定制
E       assert not True
E        +  where True = has_custom_field('Item', 'agenerp_gate_roundtrip')
```

→ **判据有牙齿。** 还原后 `shasum -a 256 agenerp/apply.py` 仍为 `861d9f20…f1b574fd`，
`git status --porcelain` 与变异前基线 `diff` **无差异**（工作区相对变异前无残留）。
还原后复跑整文件：exit 1，`1 failed, 3 passed`（承重条款回到 PASSED）。

#### 判定器：live 环境退 1 是预期，默认环境退 0 且名单一行未动

```
AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 … python3 tools/gates/check_expected_red.py   → exit 1
```

逐字输出：

```
门禁 19 项：预期红 2，绿 17，跳过 0

❌ 名单内的门禁却绿了 —— 实现已到位，请在同一个提交里把它从 tools/gates/expected-red.txt 划掉：
   tests/gates/test_customization_roundtrip_delete.py::test_added_field_exports_into_pack
   tests/gates/test_customization_roundtrip_delete.py::test_export_produces_readable_diff_only
   tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site
   tests/gates/test_snapshot_diff_structured.py::test_field_addition_shows_up_as_structured_change
   tests/gates/test_zero_dep_boot.py::test_stack_boots_and_all_services_healthy
```

**这不是回归**：本 plan 让名单内第三条（承重条款）在 live 下也转绿，把第 1 顺位预告的那个矛盾放大了一档
（live 下变绿的由 2 条变成 3 条，另两条是别的工作项的）。处置权在 `docs/masterplan/STATE.md` §3 那行
needs-human，本 plan **不重复登记、不划名单**。

收尾复跑**默认环境**判定器（栈已 `down`）：

```
docker compose -f docker-compose.yml down     → exit 0
python3 tools/gates/check_expected_red.py     → exit 0（门禁 19 项：预期红 7，绿 12，跳过 0 · ✅ 与预期红名单完全一致）
git diff --numstat tools/gates/expected-red.txt → 无输出（名单一行未动）
```

#### 文档更新

- `docs/architecture/module-boundaries.md` §11.6：标题由「A 半」改为「A 半 + B 半均已落地」；
  落点表把 `execute_plan` 从「`raise`，归工作项 6」改为「删除已实现；建/改显式拒绝」，
  并补进 `pack_doctypes` / `narrow_deletes` / `ApplyDirectionError` / `delete_custom_field` 四行；
  「未让任何门禁转绿」那一段改写为实测转绿的事实与 `expected-red.txt` 未动的理由。
- §11.1 的 Spike 06 表补上本仓的实测反证：**「从 JSON 里删掉字段再 sync → 字段纹丝不动」那一行说的是
  走 Frappe 那条路径**；换成自建引擎后同一动作实测字段真的消失。**未被推翻的是「删 Custom Field 不删列」**，
  它归第三个部件 `schema_drift`。
- `docs/backlog/p0-foundation-roadmap.md`：新增「5 现状」行（保持 `planned`，记录 live 转绿、变异验证、
  作用域安全实测、名单未动的理由与 needs-human 指向）。

## Draft Review Record

- 独立草案评审第 1 轮：**needs revision**（独立子代理，全新会话，2026-08-21，按高风险/破坏性路径对待）。主要发现，逐条已改：
  1. **[阻断]** 收窄口径的**落点**选错：按「包**条目**里出现过的 DocType」收窄，遇上门禁真实状态
     「`Item.json` 文件在、数组空」时 Item 不在收窄集内，探针不会被删，**承重条款照样红**。
     → 改为「包目录里**存在文件**的 DocType 集合」，落点挪到 `read_pack` / `apply_pack`（拿得到目录的那一侧），
     并增一条「文件在、数组空」的回归单测。
  2. **[阻断]** `ai-autonomy-policy.md` 的 Protected Areas 表没有「对活站点的破坏性写」这一行，
     而该表自己写着「将来出现时，先在本表补行再动手」。→ Phase 1 首项补行（只加严）。
  3. **[重要]** `updates` 在门禁那条路径上**未必为空**——取决于导出投影与站点投影是否同源，
     而失败形态是 `NotImplementedError`，与「B 半还没实现」逐字难以区分。
     → Phase 1 增「不执行删除的预演」`Explore` 并设为**停手闸**；Phase 3 写明这种红因的正确解读。
  4. **[重要]** 回滚策略自相矛盾：写着「可由包重建」，而本 plan 恰恰**拒绝 `creates`**。→ 改成「站点侧只能手工重建」，
     并把这条代价补进 Deferred 第一条。
  5. **[重要]** 最重要的那条单测（作用域收窄）能被一个**什么都不删**的空实现通过 → 改为同一用例里的正反两断言。
  6. **[重要]** 第一次破坏性实跑是盲的 → 增「实跑前后各一次全量 `capture` 对照，差集恰好只有探针」，
     增全站 Custom Field 清点与 `is_system_generated` 的 `Decision`，并要求跑在 fixture 自己拉起的一次性栈上。
  7. **[重要]** `_assert_direction` 是裸 `assert`，`python -O` 下整条消失——B 半接上真删除后它是最后一道闸。
     → Phase 2 增一条 `Fix` 换成显式 `raise`，Non-Goals 相应澄清。
  8. **[次要]** 五处行号漂移（`read_pack:60`、`ApplyPlan:30`、`plan_apply:73`、`remove_field:279`、`has_custom_field:212`）→ 全部更正。
  9. **[次要]** `execute_plan` 归工作项 5 还是 6 的源真相冲突未分类 → Current Baseline 增一节，裁定以 roadmap 对照表为准。
  10. **[次要]** Phase Targets/doc-update/`git diff` 基线/live 判定器退 1 的口径 → 逐条修。
  11. **[次要]** 文档新鲜度前提未记录（`codebase-map.md` 全篇是模板占位符）→ Task Route 增一段。
  评审独立复核并**确认**了本 plan 声称的安全问题（包只含 Item 而 `current` 是全 scope → 不收窄会误删全站定制，
  且门禁照样绿），称其为「这份草案最有价值的部分」。
- **第 1 轮我漏记、也未处置的两条，如实补记**（评审记录漏掉未处置项，比记下「不采纳 + 理由」更坏）：
  ① **[重要] `WRITE_VERBS` 冲突**：第 1 顺位的「只读」结构断言会把本 plan 加的删除方法当场打红，
     令 Phase 2 的退出判据在合同层面不成立。→ 第 2 轮已改：第 1 顺位的不变量 4 改成**显式白名单**形式，
     本 plan Phase 2 首项负责把 `delete_custom_field` 加进白名单并留痕（两个 plan 同时改）。
  ② **[阻断] Current Baseline 的诚实性**：把两个起草时不在仓里的产物（`agenerp/site.py`、`export_customizations`）
     写在「已经在仓里的」标题下；「缺口只有一处」也不准（站点侧有三处 `raise`）；
     「矛盾已由第 1 顺位追加进 STATE §3」是将来时写成了完成时。→ 第 2 轮已逐条改。
- 独立草案评审第 3 轮（确认轮）：**accept**。评审逐条核过十项，全部落地，并确认跨 plan 的白名单改法合规
  （两份 plan 当时都还是 `draft`，不存在追溯改写已关闭判据；白名单是棘轮式收窄，不是取消判据）。
  它同时点出两处文字残留（Phase 3 Exit Criteria 的「恰好只有探针」未跟上正文拆分；Phase 1 里两处旧名「只读预演」），
  明说不构成执行阻塞——**已一并扫掉**。原话：作为执行合同，现在可以开工。
- 独立草案评审第 2 轮：**needs revision → 已改**（同一独立评审者，带上下文复评）。它**逐行重走了门禁那五行**，
  确认新收窄口径（按包目录里存在文件的 DocType）在两种站点状态下都走得通，并确认收窄落在
  `read_pack`/`apply_pack` 侧**不破坏** A 半的求差语义与方向不变量（前过滤、后过滤都安全）。剩余七条，逐条已改：
  1. **[阻断]** 上面的 ①（`WRITE_VERBS`）。
  2. **[阻断]** 上面的 ②（baseline 诚实性）。
  3. **[重要]** 结构边界表自相矛盾：收窄要落进 `apply_pack`，而下一行仍写「委派链不变」；
     且「`read_pack` / `apply_pack`」二选一没选（改 `read_pack` 返回类型会动 A 半公共面）。
     → 新增 `pack_doctypes(path, scope)` 独立函数，`read_pack` 签名与返回类型不动，
     `apply_pack` 行改成「签名不变，委派链增加一步收窄」，Non-Goals 同步。
  4. **[重要]** 「实跑前后差集**恰好只有探针**」在整文件运行的边界上是错的——`live_site` 的 teardown 会清掉探针，
     正确运行反而不满足退出判据。→ 拆成两处边界，各自写清期望值（整文件运行 → 差集为空；单次 `apply_pack` → 恰好一个探针）。
  5. **[重要]** 「被收窄掉的条目必须可观测」没有落地面（两个函数都返回 `None`，`agenerp/` 全树无 logging），
     单测 ④ 因此写不出断言。→ 写死为 `logging.getLogger("agenerp.apply")` 的 WARNING + `caplog` 断言，
     并在 Infrastructure 记明这是本仓第一处 logging。
  6. **[次要]** covered 按文件名还是按载荷 `doctype` 键没说死 → 写死为与 `entries_from_payload` 同源，并加单测 ④b。
  7. **[次要]** Deferred 第二条标题与新口径打架（空数组文件其实表达得出「清空」）→ 标题收窄为「靠**删除包文件**表达」；
     「不执行删除的预演」改名为「不执行删除的预演」并写明载体（`_tmp/` 一次性脚本，不 import `tests/gates/`）；
     Closure Gates 的「四条 live 命令」改为「每一次实跑」。
  评审的结论原话：改完这几条即可 accept，不需要第三轮实质讨论。

## Closure Gates

- [x] in-scope behavior is complete（删除真的发生在站点上，且作用域收窄真的生效）——
      承重条款 live PASSED；单次 `apply_pack` 前后差集**恰好一个探针**、Customer 探针未被动
- [x] relevant docs are aligned（§11.6 落点表与三条裁定、§11.1 Spike 06 的实测反证、
      roadmap 新增「5 现状」行、`ai-autonomy-policy.md` Protected Areas 补行、日志三条）
- [x] verification has run：默认环境 `check_expected_red.py && pytest tests/unit -q` + `ruff`
      + Phase 3 **每一次** live 实跑（命令原文与退出码逐条落在 `## 实测回填` 的 Phase 3 节与日志里）
- [x] **verification scope limited 明写**：live 实跑**只在本机做过**，`missions/p0-foundation.json` 的
      `commands.test` 跑不到 L2，**CI 亦未验证**——不得报成「CI 上也验证过」
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（三轮，见 `## Draft Review Record`）
- [x] text consistency verified
- [ ] closure audit was independent，且**额外套一轮 `open-ended-audit-prompt.md`**（破坏性路径）——
      **执行会话未满足**：本轮执行环境明令不得调用子代理，按 `AGENTS.md` 的
      Reviewer-Availability Fallback 记 solo cold-replay 并**如实留空**。
      本 plan 属**保护区**（`ai-autonomy-policy.md` 新增的「对活站点的破坏性写」行，规则 `plan-first`，
      Required Evidence 含「独立关闭审计」），该 Fallback **不足以替代**独立审计 ——
      这一格必须由 `CLOSURE_VERIFY` 的独立审计者补齐，补齐前不得报成「已独立审计」。
- [x] closure evidence exists in files（`## 实测回填` 的 Phase 1/2/3 三节 + `docs/logs/2026/08-21.md` 三条）
- [x] **红线自查**：`git status --porcelain -- tests/gates/ .github/workflows/ missions/ docs/masterplan/ tools/gates/expected-red.txt`
      → **输出为空**（零命中）；`tools/gates/expected-red.txt` 一行未变

## Deferred But Adjudicated

### 建（creates）与改（updates）的执行

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: P0 的判据一条都不覆盖它们；本 plan 的处理是**显式拒绝**而非静默跳过，
  所以不存在「假装做到了」。**代价要说清**：`creates` 不落地 = 站点侧的回滚只能手工做，
  「用包把删掉的字段建回来」这条能力在本 plan 之后仍然缺（见 Infrastructure 的回滚策略）。
- Successor Required: `yes`（P2 定制包 GitOps，或更早出现真实调用方时）
- 重开事件：出现需要用包在站点上**建**字段的调用方时。

### 靠**删除包文件**表达「清空该 DocType 的全部定制」这一意图无法表达（空数组文件可以）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 新收窄口径下，「文件在、数组空」**就是**「清空这个 DocType」，这条路是通的；
  表达不出来的只有「**删掉文件**也算清空」那一种写法——删掉文件 = 「不管这个 DocType」。
  P0 没有这个需求，且默认口径**偏保守（少删）**，错的方向是安全的那一侧。
- Successor Required: `no`
- 重开事件：P2 需要用包表达「清空」时（届时应加显式意图标记，而不是靠文件缺席推断）。

### 孤儿列：删了 Custom Field 不等于删了物理列

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: `test_no_orphan_column_left_behind` 是独立的一条门禁，归工作项 6 的第二个 plan；
  它要的物理表列清单查询走不通 REST（compose 未对宿主发布 db 端口），是一条独立的传输决策。
  **本 plan 关闭时它仍红，红因挪到 `schema_drift`——这一点会被逐字记进关闭证据，不含糊过去。**
- Successor Required: `yes`
- 重开事件：本 plan 关闭之后立即（它是工作项 6 剩下的最后一条 L2 断言）。

### 事务与回滚语义（`rollback_and_report` / savepoint）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: `02-WBS.md` 划给 P3.1（工具契约层 v1），判据是 `tests/contracts/test_write_contract.py`。
  本 plan 的删除是逐条独立请求，失败即停并抛——中途失败会留下**部分应用**的状态，
  这一点如实写进 §11.6，不假装有事务。
- Successor Required: `yes`（P3.1）
- 重开事件：P3 开工。

## Closure

Status Note: **三个 Phase 全部执行完毕、验证全绿；独立关闭审计尚缺一轮（见 Closure Gates 第 8 格）。**

交付：`SiteClient.delete_custom_field`（站点侧删除的唯一出口）、`pack_doctypes` / `narrow_deletes`
（作用域收窄 + 不静默的 WARNING）、`execute_plan` 的删除路径（建/改显式拒绝）、
`_assert_direction` 的裸 `assert` → `ApplyDirectionError`、`apply_pack` 委派链增一步收窄、
`tests/unit/test_apply_execute.py`（19 条）。

**承重条款 `test_removing_from_pack_actually_deletes_on_site` 在活站点上实测转绿**，
变异验证证明它有牙齿。`tools/gates/expected-red.txt` **一行未动**、roadmap 工作项 5 保持 `planned`
（与 Non-Goals 一致：默认判定环境下 L2 恒红，划名单会让 `GATE_VERIFY` 立刻转红；
处置权在 `docs/masterplan/STATE.md` §3 那行 needs-human，本 plan 不重复登记）。

**关闭时仍红且是预期的**：`test_no_orphan_column_left_behind`，红因**已从 `execute_plan` 挪到
`agenerp/snapshot.py` 的 `schema_drift`**（它第一次走得到那一步），归工作项 6 的第二个 plan。

Closure Audit Evidence:

- Auditor / Agent: **solo cold-replay（非独立）** —— 本轮执行环境明令不得调用子代理，
  按 `AGENTS.md` 的 Reviewer-Availability Fallback 记录该限制。**本 plan 属保护区，
  该 Fallback 不足以替代独立审计**，独立那一轮由 `CLOSURE_VERIFY` 补。
- Evidence（本机复跑，命令原文 + 退出码，退出码单独取 `$?`；**非 CI**）:
  - `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **0**
    （「门禁 19 项：预期红 7，绿 12，跳过 0 · ✅ 与预期红名单完全一致」/ **164 passed**）
  - `ruff check agenerp tests/unit tests/contracts` → **0**（All checks passed!）
  - `python3 -m pytest tests/contracts -q` → **0**（151 passed）
  - live 七条命令的原文与退出码见 `## 实测回填` 的 Phase 3 节
  - commit sha: <关闭提交时回填>
- 红线自查: `git status --porcelain -- tests/gates/ .github/workflows/ missions/ docs/masterplan/ tools/gates/expected-red.txt`
  → **输出为空**

Follow-up:

- **独立关闭审计（含 `open-ended-audit-prompt.md` 一轮）** —— 唯一未闭合的 Closure Gate。
- `schema_drift` / 孤儿列（`test_no_orphan_column_left_behind`）—— 工作项 6 的第二个 plan，重开事件已到。
- `creates` / `updates` 的执行 —— `## Deferred But Adjudicated` 第一条，重开事件未到（P2 或更早的真实调用方）。
