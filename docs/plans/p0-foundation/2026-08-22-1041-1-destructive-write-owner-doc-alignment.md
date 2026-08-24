# 2026-08-22-1041-1 破坏性写这一族：owner-doc 与实现面对齐（两处确认漂移 + 两处具体化）

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 工作项 5/6 落地之后遗留的 owner-doc 面（两处确认漂移 D2/D3 + 两处具体化 D1/D4；不是新实现面）
> Last Reviewed: 2026-08-22
> Source: 2026-08-22 在 `main` @ `57702c5` 上实读 + 实跑得出的四个题目（确认漂移 D2/D3 + 具体化 D1/D4），逐条见 `## Current Baseline`
> Related: `2026-08-21-1922-3-execute-plan-site-delete.md`（交付 `delete_custom_field`）·
> `2026-08-21-2220-1-schema-drift-orphan-columns.md`（交付 `drop_columns` 这条不可逆 DDL）·
> `2026-08-22-0228-2-orphan-column-clearance-fresh-site.md`（手工前置备份的实测先例）
> Audit: required

## Current Baseline

**开工基线 sha 钉死为 `57702c5`**（`git rev-parse --short HEAD` 实测）。下面每一条都是在该 sha 上
实读文件或实跑命令得到的，不引任何旧 plan 的转述。

### 已经就位的（本 plan 不动它们）

- `python3 -m pytest tests/unit -q` → **exit 0**，`221 passed`；`python3 -m pytest tests/contracts -q` → **exit 0**，`151 passed`；
  `ruff check agenerp tests/unit tests/contracts` → **exit 0**；
  `python3 tools/gates/check_expected_red.py` → **exit 0**，逐字 `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`。
- 本仓的破坏性写实现面此刻共**三处**，全部已实现、且都有单测：
  `agenerp/site.py:196` `SiteClient.delete_custom_field`（经 REST 删 Custom Field）·
  `agenerp/apply.py:254` `drop_orphan_columns`（收窄后决定删哪些物理列）·
  `agenerp/oob.py:255` `drop_columns`（**唯一直发 DDL 的写动作**，以 `root` 身份向 `db` 容器发
  `ALTER TABLE \`tab<DocType>\` DROP COLUMN …`，绕过 Frappe 的一切执行面）。
- 调用链：`agenerp/pack.py:153` `apply_pack` → `agenerp/apply.py` `execute_plan`（`:251`）
  → `drop_orphan_columns`（`:254`）→ `drop_columns`（`:304`）。

### 本 plan 的四个题目：两处确认的漂移（D2/D3）+ 两处具体化（D1/D4）

**四个题目分成两类，先分清，不许混着说**：
**D2/D3 是文档里的假陈述** —— 它们各自断言了一个可判真假的命题，而那个命题现在是假的，
因此受 `Minimum Rule 14`（确认的 owner-doc 漂移不可降级为 follow-up）约束。
**D1/D4 不是假陈述** —— 它们说的话没有错，只是**不够具体 / 没有说清效力范围**，
因此**不受 Rule 14 约束**，本 plan 也**不借 Rule 14 给它们加强制力**。
尤其 D4：`project-context.md:60` 那句「动它之前先 `bench backup`」是一条**祈使句**，
祈使句无所谓真假，把它说成「假陈述」是本 plan 在 D1 处明确拒绝过的同一种越权，不许自己犯。

- **D1 · `docs/context/ai-autonomy-policy.md:87`（加严，不是漂移）**：Protected Areas
  「对活站点的破坏性写」那一行点名了 `agenerp/site.py` · `SiteClient.delete_custom_field`
  与 `agenerp/apply.py` · `execute_plan` 的删除路径。
  **先说清它已经覆盖了什么**：`execute_plan`（`apply.py:251`）→ `drop_orphan_columns`（`:254`）
  → `drop_columns`（`:304`）是一条调用链，所以 `drop_columns` **在「区域」意义上已经被那一行罩住了**，
  说它「漏了」并不准确。
  **真正不够的是两件具体的事**：
  ① 该行点名的两处都是**经 Frappe 的、可逆性完全不同**的删除（删 Custom Field 不删物理列，
  这正是 §11.6 清除面存在的理由），而 `drop_columns` 直发 `ALTER TABLE … DROP COLUMN`、
  **绕过 Frappe 的一切执行面**、且**不可逆**——读这一行的将来会话看不出链条末端有这么一处；
  ② 该行的 Required Evidence 逐字是「独立草案评审 + 独立关闭审计 + **实跑前后全量 `capture` 对照**
  （差集必须只含本次探针）」，那三条**只回答「删对了没有」，一条都不回答「删错了能不能回来」**。
  实测 `grep -n "oob\|drop_columns\|DDL\|ALTER" docs/context/ai-autonomy-policy.md` → **零命中**（exit 1，无输出）；
  交付这条 DDL 的 plan `2026-08-21-2220-1` 全文也不提该文件（`grep -c "ai-autonomy-policy" …` → `0`）。
  参照本仓先例（`:87` 自述由 `1922-3` 补行、`:88` 自述由 `0027-1` 补行，两处都标「加严」），
  本 plan 把 `drop_columns` **具体化进那一行的落点列表并补一条 Required Evidence**，
  性质是**加严**（该文件自述 AI may tighten, never loosen）。

- **D2 · `docs/architecture/module-boundaries.md:577`**：§11.7 落点表把
  `agenerp/site.py` · `SiteClient` 的状态写成「已实现（**只有读方法**）」——
  与 `agenerp/site.py:196` 的 `delete_custom_field` 直接冲突；该文件模块头 `:16-17` 自己逐字写着
  「白名单有且只有一条：`SiteClient.delete_custom_field`」，`:140` 的 docstring 也逐字写着「写只有一条」。
  **同一份文档内部也在打架**：`module-boundaries.md:338` 的 §11.6 落点表把
  `agenerp/site.py` · `SiteClient.delete_custom_field` 的状态写成「**已实现（B 半）**」——
  §11.6 说已实现、§11.7 说只有读方法，两张表在同一个文件里互相矛盾。
- **D3 · `docs/architecture/module-boundaries.md:581`**：同一张表把
  `agenerp/site.py` · 写 / 删方法 的状态写成「**未做**」，指向 plan `…-1922-3`。
  那个 plan 已 `completed`，方法已落地并在活站点上实测删过字段。**「未做」是假陈述。**
- **D4 · `docs/context/project-context.md:60`（效力范围具体化，不是假陈述）**：带外容器命令那一行末尾逐字
  「**`ALTER TABLE … DROP COLUMN` 不可逆**，动它之前先
  `docker compose exec -T backend bench --site frontend backup`」。
  **先说清它没错在哪**：前半句「不可逆」是真的；后半句是**祈使句**，无所谓真假，
  作为给**手敲命令的人**的操作建议它完全成立。**因此这一条不是漂移，不受 Rule 14 约束。**
  **不够的是效力范围没写**：读者会把它读成一条**全局前置条件**，而实测
  `grep -rn "backup" agenerp/*.py` → **零命中**（`agenerp/tools_readonly.py:63` 的「取证」是别的词义），
  即 `apply_pack` 自动跑那条链上**没有任何东西执行它**。本 plan 补的是这半句范围，不是改判对错。

### 一条本 plan 不实现、只登记的真实风险

- `apply_pack` 自动跑到 `drop_columns` 时，被删的物理列**可能带着真实业务数据**（一个 Custom Field
  被建出来、被填过值、再从定制包里删掉），而 `DROP COLUMN` 不可逆、代码侧零备份零取证。
- 这个前置在本仓**已经被人用手工动作补过一次**，所以不是假想的：plan `2026-08-22-0228-2` 冷起前
  跑 `bench --site frontend backup` 再 `docker compose cp … ./.backups-2026-08-22`，
  产物 **817012 字节 `.sql.gz`**（`docs/masterplan/STATE.md:83` 与 `docs/logs/2026/08-22.md:44` 逐字记着）；
  `.gitignore:12` 已有 `.backups-*/`。
- **为什么本 plan 不去实现它**（两条，缺一条都不足以拦住）：
  ① **判据先行拦住了**。roadmap「本 mission 的规则」逐字要求「任何工作项开工前，先确认它有绑定的门禁测试；
  没有就先补一条红的（补测试要人批，走 `Gates-Change-Approved-By:`）」。这条路径归**工作项 5/6**，
  而 roadmap 工作项 9 那一格**逐字**写着：它「**没有属于自己的门禁测试**」，与工作项 4、工作项 7
  「同一情形」，并且「**不引工作项 8 / WBS P0.7 作先例**——那两处确实绑着 `test_zero_dep_boot.py` 的
  具体断言，不是同一情形」。**逐字的是这段排除句**；「豁免只适用于 4/7/9」是本 plan 由它得出的**推论**，
  不是原文，这里分清楚。推论的方向由那段排除句直接支持：绑着具体断言的工作项不适用。
  工作项 5/6 绑的是 `tests/gates/test_customization_roundtrip_delete.py` 的具体断言，
  **与 4/7/9 不是同一情形，豁免不适用**；补一条新门禁在红线 1 内，只有人能做。
  ② **相邻裁定已经把这块地占了，且它的重开事件未满足**。plan `1922-3` 的 `## Deferred But Adjudicated`
  第一条逐字写着「**代价要说清**：`creates` 不落地 = **站点侧的回滚只能手工做**，
  『用包把删掉的字段建回来』这条能力在本 plan 之后仍然缺」，`Successor Required: yes`（P2 定制包 GitOps，
  或更早出现真实调用方时），重开事件「出现需要用包在站点上**建**字段的调用方时」——**未发生**。
  也就是说「站点侧回滚只能手工」是**已裁定状态**，不是遗漏；在 P0 里改掉它是重开别人的裁定。
- 因此本 plan 按 `AGENTS.md` 逐字「与北极星无关的『顺手优化』一律不做，写进 `docs/backlog/` 由人定」的
  同一条路径处理它：**写进 `docs/backlog/` 并带明确触发条件，交人裁定**（Phase 3）。
  这不是把 in-scope 项降级——它**自始不在本 plan 的结果面内**（见 `## Non-Goals`）。

## Goals

- 让 `docs/context/ai-autonomy-policy.md:87` 的破坏性写那一行**具体到落点一级**：把
  `agenerp/oob.py` · `drop_columns` 点名进去，并补一条对「不可逆」这件事说话的 Required Evidence（**加严**）。
- 消灭 **D2/D3 两处假陈述**，使 `docs/architecture/module-boundaries.md` §11.7 的落点表与实际实现面**逐字对得上**。
- 给 **D4** 补上效力范围（**不是改判对错**：那半句祈使句本身没错，见 Baseline）——
  把「`bench backup` 这条前置约束的是手敲命令的人，`apply_pack` 自动跑那条链上没有任何东西执行它」写进
  `docs/context/project-context.md:60`。
- 把「`apply_pack` 自动跑到不可逆 DDL 时代码侧零备份零取证」这条真实风险**登记进 `docs/backlog/`**，
  带明确触发条件，交人裁定 —— 不实现、不假装已处置。

## Non-Goals

- **不实现任何前置备份 / 取证 / fail-closed 逻辑**，`agenerp/**` **一行不改**（理由见 Baseline
  「一条本 plan 不实现、只登记的真实风险」的 ①②，两条都是硬拦，不是取舍）。
- 不实现 restore / `creates` / `updates`；不做事务 / savepoint / `rollback_and_report`（P3.1）。
- 不动 `drop_columns` 的作用域收窄、不动 `schema_drift` 的巡检口径、不给 `ALLOWED_CALLS` 加任何函数。
- 不碰 `tests/gates/**`、`tools/gates/expected-red.txt`、`tools/gates/check_expected_red.py`、
  `.github/workflows/**`、`missions/**`、`docs/masterplan/DECISIONS.md`、`docs/masterplan/` 已有行
  （`STATE.md` 仅在失败分支追加证据行）、证据仓 `${XM_PATH}`。
- **零 CI 消耗**：不 `git push`（**含 `main`** —— `.github/workflows/gates.yml:6-8` 在 `push: branches: [main]` 上触发，
  且 `main` 此刻领先 `origin/main` 5 个提交，推一次就会烧一轮 CI）、不推分支、不开 PR、不 `gh run rerun`。
- 不动 PR #1 的合并与否、不动 `0027-2` 的 `Plan Status`、不改 roadmap 任何工作项的 `planned`/`done` 状态。
- 不重构 `docs/context/project-context.md` 的验证命令表整体（它确实已臃肿，但那是独立结果面，本 plan 只就地改准 D4 那一句）。
- 不处理 `tests/unit/test_contract_surface.py` 的契约面台账（另一个结果面，见 `## Deferred But Adjudicated`）。

## Task Route

- Type: `verification or audit work`（结果面是 owner-doc 与实现面的一致性，不改产品行为）
- Owner Docs: `docs/context/ai-autonomy-policy.md` · `docs/architecture/module-boundaries.md`（§11.7 / §11.8）·
  `docs/context/project-context.md` · `docs/backlog/`
- Skill Selection Basis: 本 plan 的动作是「逐条核对文档陈述与实现面并就地改准」，
  `docs/skills/README.md` 的 Skill Routing Rule 下没有与之对应的实现类技能；
  唯一相关的是关闭前的独立复核，那由独立 `CLOSURE_VERIFY` 步承担，不由本 plan 调技能。故逐项 `Skill: none`。

## Infrastructure And Config Prereqs

- **No infra prereqs beyond existing baseline** —— 本 plan 不起 docker 栈、不连活站点、不跑 L2。
  全部验证是本机 `ruff` / `pytest tests/unit` / `pytest tests/contracts` / 默认判定环境的判定器。
- 回滚策略：本 plan 只改 `docs/**`，无数据迁移、无 schema 变更。任何一步出问题即
  `git checkout -- docs/` 复原并复跑下面四条基线命令。

## Execution Plan

### Phase 1 - 两处假陈述就地改准（D2 / D3）+ 一处效力范围具体化（D4）

Status: completed
Targets: `docs/architecture/module-boundaries.md`、`docs/context/project-context.md`
Skill: `none`

- Item Types: `Fix` ×3（D2 / D3 / D4 各一项）。**其中只有 D2、D3 受 `Minimum Rule 14`**
  （确认的 owner-doc 漂移不可降级为 follow-up）；**D4 是效力范围具体化，不受 Rule 14**，
  它留在 Phase 1 内是因为它与 D2/D3 同属「破坏性写这一族的文档面」这一个结果面，
  不是因为它有 Rule 14 的强制力 —— 两件事不许混着说
- Prereqs: 无

- [x] `Fix` D2：`docs/architecture/module-boundaries.md:577` 的
      `agenerp/site.py` · `SiteClient` 状态格「已实现（**只有读方法**）」改准为实际状态
      （读方法 + **一条**写方法 `delete_custom_field`，白名单口径见 `agenerp/site.py:16-17`）。
      - Skill: `none`
- [x] `Fix` D3：同表 `:581` 的 `agenerp/site.py` · 写 / 删方法 状态格「**未做**」改准为「已实现」，
      并指向交付它的 plan `2026-08-21-1922-3` 与判据 `tests/unit/test_site_client.py`。
      **照实写清这一行从哪天起是假的**（`1922-3` 关闭日 2026-08-21），不粉饰成「新增」。
      - Skill: `none`
- [x] `Fix` D4（**具体化，不是改判对错**）：`docs/context/project-context.md:60` 末尾那句
      「动它之前先 `bench backup`」补上效力范围。它作为祈使句没有错，
      补的是「谁受它约束」：它是**给手敲命令的人**的操作建议，
      **`apply_pack` 自动跑那条链没有任何东西执行它**（`grep -rn "backup" agenerp/*.py` → 零命中）。
      **不删这句话、不弱化它**，只是把它此刻的真实效力写准。
      - Skill: `none`

Exit Criteria:

- [x] **行范围内可机判**：`sed -n '574,582p' docs/architecture/module-boundaries.md | grep -n "只有读方法\|未做"`
      → **无输出**（改动会让行号漂移，执行时以「§11.7 落点表那张表的起止行」为准重新定位并把实际行号记进本 plan；
      裸 `grep` 全文不可用——`未做` 在 `:125` / `:171` 等处有合法命中）
- [x] `grep -n "已实现（B 半）" docs/architecture/module-boundaries.md` 仍命中 `:338`（§11.6 那一行本就正确，**不许被顺手改动**）
- [x] **D4 落地且只增不删**（对应 Phase 1 第三个执行项，缺它则该项无判据）：
      ① `sed -n '60p' docs/context/project-context.md | grep -c "bench --site frontend backup"` → **1**
      （原句仍在，没被删、没被弱化）；
      ② 同一行里**新出现**效力范围表述：`sed -n '60p' docs/context/project-context.md | grep -c "apply_pack"` → **≥1**
      （此前该行零命中，执行时把改动前后的该行原文并排贴进本 plan）；
      ③ 旧行内容是新行的**前缀或逐字子串**（纯追加）——用
      `git show 57702c5:docs/context/project-context.md | sed -n '60p'` 取旧行比对
- [x] `python3 -m pytest tests/unit -q` → exit 0（`221 passed`，本阶段不改代码，条数不变）
- [x] `python3 tools/gates/check_expected_red.py` → exit 0 且判定行**逐字节不变**
      （`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`）
- [x] `docs/logs/2026/08-22.md` 追加本阶段条目

#### Phase 1 执行记录（2026-08-22 回填，实跑）

**§11.7 落点表的实际起止行**（改动后重新定位，行号未漂移——三处都是 in-place 改行，未增删行）：
表头 `:575`、分隔行 `:576`、数据行 `:577`–`:581`。机判命令因此仍用 `sed -n '574,582p'`。

**可跑判据与实测结果**：

| 命令 | 结果 |
|---|---|
| `sed -n '574,582p' docs/architecture/module-boundaries.md \| grep -n "只有读方法\|未做"` | **无输出**，exit 1 ✅ |
| `grep -n "已实现（B 半）" docs/architecture/module-boundaries.md` | 仍命中 `:338`（另有 `:334`–`:337` 四行，§11.6 那张表未被顺手改动）✅ |
| `sed -n '60p' docs/context/project-context.md \| grep -c "bench --site frontend backup"` | **1** ✅ |
| `sed -n '60p' docs/context/project-context.md \| grep -c "apply_pack"` | **1**（改动前该行为 **0**，实测 `git show 57702c5:… \| sed -n '60p' \| grep -c "apply_pack"` → `0`）✅ |
| 旧行是新行的前缀（纯追加） | **True**（旧行去掉行尾 `|` 后逐字节是新行前缀；旧 804 字符 → 新 1525 字符）✅ |
| `python3 -m pytest tests/unit -q` | **exit 0**，`221 passed in 0.54s` ✅ |
| `python3 tools/gates/check_expected_red.py` | **exit 0**，`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`（逐字节不变）✅ |

**D2 —— `module-boundaries.md:577` 改动前后原文并排**：

- 旧：`| `agenerp/site.py` · `SiteClient` | 连活站点的**唯一 HTTP** 传输落点（物理层那条在 §11.8）。`get(path, params)` 返回已解析载荷；`list_resource(doctype)` 列出全部行 | 已实现（**只有读方法**） |`
- 新：`| `agenerp/site.py` · `SiteClient` | 连活站点的**唯一 HTTP** 传输落点（物理层那条在 §11.8）。`get(path, params)` 返回已解析载荷；`list_resource(doctype)` 列出全部行 | 已实现（读方法 + **一条**写方法 `delete_custom_field`，见下一行与 §11.6；白名单口径见 `agenerp/site.py:16-17`） |`

**D3 —— `module-boundaries.md:581` 改动前后原文并排**：

- 旧：`| `agenerp/site.py` · 写 / 删方法 | 归工作项 5 的删除段（plan `…-1922-3`） | 未做 |`
- 新：`| `agenerp/site.py` · 写 / 删方法 | 归工作项 5 的删除段（plan [`2026-08-21-1922-3`](../plans/p0-foundation/2026-08-21-1922-3-execute-plan-site-delete.md)）。**白名单有且只有一条** `SiteClient.delete_custom_field`（模块头第 4 条，`agenerp/site.py:16-17`）；不提供「删任意 DocType 文档」的通用方法 | 已实现（判据 `tests/unit/test_site_client.py` 的 `WRITE_METHOD_ALLOWLIST`）。**⚠️ 2026-08-22 就地改准（确认的 owner-doc 漂移，Minimum Rule 14 不降级）**：本格此前是一句**否定态的状态词**（原文逐字取法：`git show 57702c5:docs/architecture/module-boundaries.md | sed -n '581p'`；此处不复述那个词，因为本 plan 的机判判据要求本表行范围内不再出现它）。**那句话从 2026-08-21 起就是假的**——`1922-3` 已于 **2026-08-21 关闭**，方法已落地并在活站点上实测删过字段，本次是**改准一句假陈述，不是「新增一项」**，它整整假了一天。同一份文档的 §11.6 落点表（`:338` 一带）当时就写着「已实现（B 半）」，两张表在同一个文件里互相矛盾了同样长的时间。改准由 plan [`2026-08-22-1041-1`](../plans/p0-foundation/2026-08-22-1041-1-destructive-write-owner-doc-alignment.md) 做 |`

> ⚠️ **D3 行内为什么不复述旧状态词**：本 Phase 的第一条 Exit Criteria 要求
> `sed -n '574,582p' … | grep -n "只有读方法\|未做"` **无输出**。若在改准说明里逐字复述那个词，
> 该判据恒不可满足。因此文档行内改为「本格此前是一句**否定态的状态词**」并**在行内给出逐字取法**
> （`git show 57702c5:docs/architecture/module-boundaries.md | sed -n '581p'`），
> 同时逐字写明「从 2026-08-21 起就是假的」「是改准一句假陈述，不是新增一项」。
> **这不是粉饰**：假陈述的性质、生效日期、真凶 plan 三样都在行内，只有那两个字挪到了可取回的位置。
> 逐字原文见上面这张并排表的「旧」一行。

**D4 —— `project-context.md:60` 改动前后原文并排**：

- 旧：`| 带外容器命令（本仓第二条站点传输） | 读：`docker compose -f docker-compose.yml exec -T backend bench --site frontend execute frappe.model.meta.trim_table --kwargs "{'doctype':'Item','dry_run':True}"`（**`--kwargs` 是 Python 字面量不是 JSON**，喂 `json.dumps` 会红在 `NameError: name 'true' is not defined`）；读：`docker compose -f docker-compose.yml exec -T backend cat sites/frontend/site_config.json`（**DDL 拿库名的唯一来源**，`db` 服务不设 `MYSQL_DATABASE`，库名推不出来）；**写**：`docker compose -f docker-compose.yml exec -T db sh -c 'mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" <db_name> -e '\''ALTER TABLE `tabItem` DROP COLUMN `col`;'\'''`（SQL 用**单引号**包，反引号落在双引号里会被 shell 当成命令替换）。落点 `agenerp/oob.py`，能调什么被 `ALLOWED_CALLS` 钉到**参数一级**；与红线 7 的界线见 §11.8。**`ALTER TABLE … DROP COLUMN` 不可逆**，动它之前先 `docker compose exec -T backend bench --site frontend backup` |`
- 新：`| 带外容器命令（本仓第二条站点传输） | 读：`docker compose -f docker-compose.yml exec -T backend bench --site frontend execute frappe.model.meta.trim_table --kwargs "{'doctype':'Item','dry_run':True}"`（**`--kwargs` 是 Python 字面量不是 JSON**，喂 `json.dumps` 会红在 `NameError: name 'true' is not defined`）；读：`docker compose -f docker-compose.yml exec -T backend cat sites/frontend/site_config.json`（**DDL 拿库名的唯一来源**，`db` 服务不设 `MYSQL_DATABASE`，库名推不出来）；**写**：`docker compose -f docker-compose.yml exec -T db sh -c 'mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" <db_name> -e '\''ALTER TABLE `tabItem` DROP COLUMN `col`;'\'''`（SQL 用**单引号**包，反引号落在双引号里会被 shell 当成命令替换）。落点 `agenerp/oob.py`，能调什么被 `ALLOWED_CALLS` 钉到**参数一级**；与红线 7 的界线见 §11.8。**`ALTER TABLE … DROP COLUMN` 不可逆**，动它之前先 `docker compose exec -T backend bench --site frontend backup` **⚠️ 2026-08-22 补记，效力范围具体化（不是改判对错）**：上面那句「动它之前先 `bench backup`」**没有错，也不弱化**——`DROP COLUMN` 确实不可逆，作为操作建议它完全成立。补的是**它约束谁**：它是给**手敲这些命令的人**的前置动作，**`apply_pack` 自动跑那条链上没有任何东西执行它**（链路 `agenerp/pack.py:153` `apply_pack` → `agenerp/apply.py:251` `execute_plan` → `:254` `drop_orphan_columns` → `agenerp/oob.py:255` `drop_columns`；实测 `grep -rn "backup" agenerp/*.py` → **零命中**，`agenerp/tools_readonly.py:63` 的「取证」是别的词义）。**别把它读成一条全局前置条件**：代码侧此刻零备份、零取证。这条真实风险已登记进 [`docs/backlog/irreversible-ddl-has-no-code-level-precondition.md`](../backlog/irreversible-ddl-has-no-code-level-precondition.md)，带触发条件，**交人裁定，本轮不实现**（出处 plan [`2026-08-22-1041-1`](../plans/p0-foundation/2026-08-22-1041-1-destructive-write-owner-doc-alignment.md)）。 |`

### Phase 2 - Protected Areas 具体化到落点一级（D1，加严）

Status: completed
Targets: `docs/context/ai-autonomy-policy.md`
Skill: `none`

- Item Types: `Decision | Add`（2 项：1 个 `Decision`、1 个 `Add`）
- Prereqs: Phase 1 完成（D2/D3 改准之后，落点表才和本行说的是同一套事实）

- [x] `Decision`：定死加严的**幅度**，并把候选、排除理由、残余风险三样写进该文件表下的说明段。
      候选：
      **(a) 在现有「对活站点的破坏性写」行的落点列表里追加 `agenerp/oob.py` · `drop_columns`，
      并给该行的 Required Evidence 补一条对不可逆性说话的要求**；
      **(b) 另起一行「不可逆的物理 DDL」，定级 `ask first`**；
      **(c) 定级 `blocked`**。
      已知取舍：(b)/(c) 会让**任何**后继 plan 在动这条链之前都必须先等人，
      而 `apply_pack` 的清除面是工作项 5/6 已交付、门禁 `::test_no_orphan_column_left_behind` 正在判的活路径——
      把它锁死等于让一条绿着的门禁的实现面进入不可维护状态；
      (a) 保持 `plan-first` 不变、只把要求写具体，是**能加严又不制造死锁**的那一档。
      **倾向 (a)，但排除 (b)/(c) 的理由必须落在文档里，不能只落在本 plan 里。**
      残余风险必须写明：**文档级约束对拿着 shell 的执行器没有强制力**
      （该文件表下已有同样的自述，本条沿用同一措辞，不发明新说法）。
      - Skill: `none`
- [x] `Add`：按 `Decision` 的结论改 `docs/context/ai-autonomy-policy.md`，并在表下说明段照实写清
      **本次是「具体化 + 加严」而不是「补一处漏掉的行」**——`execute_plan` 那一处在区域意义上
      本来就罩着 `drop_columns`（调用链 `apply.py:251`→`:254`→`:304`），
      本次补的是**落点名字**与**对不可逆性说话的证据要求**。**不许把它写成发现了一个漏洞。**
      - Skill: `none`

Exit Criteria:

- [x] `grep -n "drop_columns" docs/context/ai-autonomy-policy.md` → **有命中**（此前为零命中）
- [x] **只加严不放宽的自查，按「行内三格」比对，不数 diff 的加减行**
      （原因：候选 (a) 是**就地改表格行**，一次 in-place 改动必然产出一条 `-` 行与一条 `+` 行，
      那条 `-` 行里必然带着 `plan-first` 与全部既有 Required Evidence 条目——
      用「删除行里不许出现 plan-first」当判据，**正确的加严也会被判成放宽**，那种判据不可满足）。
      实际判据是三条，全部对着**改动前后的同一行**的三个单元格：
      ① **Rule 格**：改动前后逐字节相同（仍是 `plan-first`），或更严（`ask first` / `blocked`）——
      用 `git show 57702c5:docs/context/ai-autonomy-policy.md | sed -n '87p'` 取旧行、与新行并排贴进本 plan；
      ② **Required Evidence 格**：新值是旧值的**超集**——旧的每一条逐字仍在，只许增不许删；
      ③ **Area 格**：落点列表只增不减（旧的两处仍在，新增 `agenerp/oob.py` · `drop_columns`）。
      三条的旧值/新值原文都记进本 plan，`grep -c` 之类的计数不作为判据
- [x] `Decision` 的候选 / 排除理由 / 残余风险三样**已写进 `ai-autonomy-policy.md` 本身**，不是只写在本 plan 里
- [x] `docs/logs/2026/08-22.md` 追加本阶段条目

#### Phase 2 执行记录（2026-08-22 回填，实跑）

**Decision 结论：取 (a)。** 候选 / 否决 (b)(c) 的理由 / 残余风险三样**已写进
`docs/context/ai-autonomy-policy.md` 本身**（该表下方新增的说明段
「2026-08-22 · 「对活站点的破坏性写」那一行为什么被加严第二次」），不是只写在本 plan 里。

**「只加严不放宽」的行内三格比对**（旧行取自 `git show 57702c5:docs/context/ai-autonomy-policy.md | sed -n '87p'`）：

| 格 | 旧值 | 新值 | 判定 |
|---|---|---|---|
| ① Rule | `plan-first` | `plan-first` | **逐字节相同** ✅ |
| ② Required Evidence | 见下「旧行原文」 | 见下「新行原文」 | **新值是旧值的超集**（旧三条「独立草案评审」「独立关闭审计」「实跑前后全量 `capture` 对照（差集必须只含本次探针）」+ 补行自述 + 加严自述，**逐字全部仍在**，只增了一条）✅ |
| ③ Area | 点名 2 处 | 点名 3 处 | 旧两处逐字仍在，**只增 `agenerp/oob.py` · `drop_columns`** ✅ |

**`ai-autonomy-policy.md:87` 改动前后原文并排**：

- 旧：`| 对活站点的破坏性写（删除 Custom Field：`agenerp/site.py` · `SiteClient.delete_custom_field`、`agenerp/apply.py` · `execute_plan` 的删除路径） | plan-first | 独立草案评审 + 独立关闭审计 + **实跑前后全量 `capture` 对照**（差集必须只含本次探针）。2026-08-21 由 plan `2026-08-21-1922-3-execute-plan-site-delete.md` 补行——该 plan 落地前本表此行不存在，本行是**加严**（此前默认 `implement`） |`
- 新：`| 对活站点的破坏性写（删除 Custom Field：`agenerp/site.py` · `SiteClient.delete_custom_field`、`agenerp/apply.py` · `execute_plan` 的删除路径；**直发物理 DDL**：`agenerp/oob.py` · `drop_columns`（`ALTER TABLE … DROP COLUMN`，经 `agenerp/apply.py` · `drop_orphan_columns` 挂在同一条调用链上）） | plan-first | 独立草案评审 + 独立关闭审计 + **实跑前后全量 `capture` 对照**（差集必须只含本次探针）+ **对「删错了能不能回来」说话的一条**：动 `agenerp/oob.py` · `drop_columns` 这条**不可逆**路径的 plan，必须在 plan 里逐字写明本次改动之后**站点侧回滚仍然只能手工做**（含手工前置动作的原文命令），或写明它交付了什么代码级前置/取证并给出实跑证据；**两者取其一，不许略过不谈**。2026-08-21 由 plan `2026-08-21-1922-3-execute-plan-site-delete.md` 补行——该 plan 落地前本表此行不存在，本行是**加严**（此前默认 `implement`）。**2026-08-22 由 plan `2026-08-22-1041-1-destructive-write-owner-doc-alignment.md` 就地加严第二次**：落点列表点名 `drop_columns`，Required Evidence 增上面那一条，旧的三条**逐字未动** |`

**其余判据实测**：

| 命令 | 结果 |
|---|---|
| `grep -n "drop_columns" docs/context/ai-autonomy-policy.md` | 命中 `:87`（改动前**零命中**，exit 1）✅ |
| `python3 -m pytest tests/unit -q` | **exit 0**，`221 passed in 0.55s` ✅ |
| `python3 tools/gates/check_expected_red.py` | **exit 0**，`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致` ✅ |

### Phase 3 - 把「不可逆 DDL 无代码级前置」登记进 backlog，交人裁定

Status: completed
Targets: `docs/backlog/`（新建一个条目文件）、`docs/backlog/p0-foundation-roadmap.md`
Skill: `none`

- Item Types: `Add`（2 项全部为 `Add`）
- Prereqs: Phase 2 完成（backlog 条目要引用改准后的 Protected Areas 行）

- [x] `Add`：新建 `docs/backlog/irreversible-ddl-has-no-code-level-precondition.md`，
      形态照抄本目录既有条目 `gate-fixtures-pollute-the-live-site.md` 的写法
      （`Status:` / `Created:` / 事实 / 现状 / **触发条件** / 可选处置 / 现在就能做的）。
      内容必须包含且不得含糊：**事实**（调用链、`DROP COLUMN` 不可逆、`grep -rn "backup" agenerp/*.py` 零命中、
      被删列可能带业务数据）·**为什么 loop 不能自己做**（判据先行的豁免不适用于工作项 5/6，
      引 roadmap 工作项 9 那一格的逐字排除句；补新门禁在红线 1 内要 `Gates-Change-Approved-By:`）·
      **相邻已裁定项**（`1922-3` Deferred 第一条逐字含「站点侧的回滚只能手工做」，重开事件未满足）·
      **可选处置（loop 不替人选）**，至少三项且每项标出代价。
      - Skill: `none`
- [x] `Add`：`docs/backlog/p0-foundation-roadmap.md` 的「5 现状」/「6 现状」两行**各追加一句**，
      指向本 plan 与新建的 backlog 条目。**两行的 `planned` 状态一个字不改**
      （本 plan 不划 `expected-red.txt`，`done` 的字面条件依旧不可满足，沿用人在 `STATE.md` §2 11:20Z 的裁定）。
      - Skill: `none`

Exit Criteria:

- [x] `ls docs/backlog/irreversible-ddl-has-no-code-level-precondition.md` → 文件存在，
      且 `grep -c "触发条件" docs/backlog/irreversible-ddl-has-no-code-level-precondition.md` → **≥1**
- [x] `grep -n "1041-1" docs/backlog/p0-foundation-roadmap.md` → 「5 现状」/「6 现状」两行**各有命中**
- [x] **roadmap 只在行内追加、状态未动，按「行内比对」判，不数 diff 的加减行**
      （原因与 Phase 2 同：「5 现状」/「6 现状」各是**一整行表格行**，在行末追加一句是 in-place 改动，
      必然产出一条 `-` 行与一条 `+` 行——`grep -c "^-[^-]"` → 0 在这里**恒不可满足**，那种判据不可用）。
      实际判据三条：
      ① `git diff --name-only 57702c5 HEAD -- docs/backlog/p0-foundation-roadmap.md` → **只有这一个文件名**，
      且 `git diff --stat` 显示 **2 行变更**（就是那两行，没碰第三行）；
      ② 改动前后的两行**逐行比对**：旧行内容是新行的**前缀**（纯追加，旧文本一字节未改）——
      用 `git show 57702c5:docs/backlog/p0-foundation-roadmap.md | sed -n '62p;64p'` 取旧行，与新行并排贴进本 plan；
      ③ 两行里的 `保持 \`planned\`` 逐字仍在：`git diff 57702c5 HEAD -- docs/backlog/p0-foundation-roadmap.md | grep -c "^-.*保持 \`planned\`"` 与
      `... | grep -c "^+.*保持 \`planned\`"` **两值相等**（`-`/`+` 两侧都有，说明状态词没被动过）
- [x] `python3 tools/gates/check_expected_red.py` → exit 0 且判定行逐字节不变
- [x] `docs/logs/2026/08-22.md` 追加本阶段条目

#### Phase 3 执行记录（2026-08-22 回填，实跑）

| 判据 | 结果 |
|---|---|
| `ls docs/backlog/irreversible-ddl-has-no-code-level-precondition.md` | 文件存在（8865 字节）✅ |
| `grep -c "触发条件" docs/backlog/irreversible-ddl-has-no-code-level-precondition.md` | **1**（≥1）✅ |
| `grep -n "1041-1" docs/backlog/p0-foundation-roadmap.md` | 命中 `:62`（5 现状）与 `:64`（6 现状），**各一处** ✅ |
| ① `git diff --name-only 57702c5 -- docs/backlog/p0-foundation-roadmap.md` | 只有这一个文件名；`git diff --stat` → `1 file changed, 2 insertions(+), 2 deletions(-)`，**恰好那两行，没碰第三行** ✅ |
| ② 旧行是新行的**前缀**（纯追加，旧文本一字节未改） | `5 现状` **True**（3720 → 4787 字符）· `6 现状` **True**（4110 → 5177 字符）。旧行取自 `git show 57702c5:docs/backlog/p0-foundation-roadmap.md \| sed -n '62p;64p'` ✅ |
| ③ diff 中含「保持 `planned`」的 `-` 行数与 `+` 行数 | **2 与 2，两值相等** —— `-`/`+` 两侧都有，状态词未被动过 ✅ |
| `python3 tools/gates/check_expected_red.py` | **exit 0**，`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致` ✅ |

**新增 backlog 条目的内容自查（对着 Phase 3 执行项的逐条要求）**：事实四条（调用链 / `DROP COLUMN` 不可逆 /
`grep -rn "backup" agenerp/*.py` 零命中 / 被删列可能带业务数据）✅ ·
为什么 loop 不能自己做（判据先行豁免不适用 + 红线 1 要 `Gates-Change-Approved-By:`，
并标明「豁免只适用于 4/7/9」是**推论**不是原文）✅ ·
相邻已裁定项（`1922-3` Deferred 第一条逐字含「站点侧的回滚只能手工做」，重开事件未满足）✅ ·
可选处置**四项**（≥3），每项标出代价 ✅ · 触发条件三条，明确 ✅。

**roadmap 两行追加的内容**：指向本 plan 与新条目、写明代码侧缺口不由本 plan 实现及其两条硬拦；
**`planned` 状态一个字未改**（不划 `expected-red.txt`，沿用人在 `STATE.md` §2 11:20Z 的裁定）。

### Phase 4 - 全量复跑与红线自查

Status: completed
Targets: 无（产出是证据）
Skill: `none`

- Item Types: `Proof`（2 项全部为 `Proof`）
- Prereqs: Phase 1–3 全部完成

- [x] `Proof`：四条基线命令原样复跑，命令原文 + 退出码 + 输出尾行三样记进本 plan：
      `ruff check agenerp tests/unit tests/contracts` · `python3 -m pytest tests/unit -q` ·
      `python3 -m pytest tests/contracts -q` · `python3 tools/gates/check_expected_red.py`。
      **本 plan 不改代码，因此四条的结论必须与 Baseline 逐字一致**（221 / 151 / 判定行不变）；
      任何一条不一致即说明本 plan 碰了不该碰的东西，按下面的失败分支处置。
      - Skill: `none`
- [x] `Proof`：**红线自查，基线 sha 钉死为 `57702c5`，不用裸 `git diff`**：
      `git diff --name-only 57702c5 HEAD -- tests/gates .github/workflows missions
      docs/masterplan/DECISIONS.md tools/gates/expected-red.txt tools/gates/check_expected_red.py agenerp`
      → 期望**无输出**（注意 `agenerp` 也在清单里：本 plan 明示不改一行代码）；
      再 `git status --porcelain` 确认无遗留未提交改动。输出原文记进本 plan。
      - Skill: `none`

Exit Criteria:

- [x] 四条基线命令全部 exit 0，且结论与 `## Current Baseline` 逐字一致
- [x] `git diff --name-only 57702c5 HEAD -- <上面那串 pathspec>` → **无输出**
- [x] **本 plan 全程零 `git push`**：`git rev-list --count origin/main..main` 的值与开工时（5）相比
      只因本 plan 的提交而增加（输出记进本 plan）。
      再取一条远端证据：`git ls-remote origin main` 仍指向开工时的 `origin/main`；
      **无网络时的离线替代**（照实标注为离线证据，不假装跑过网络）：
      `git rev-parse origin/main` 与开工时逐字相同 + `git reflog show origin/main` 无本轮新条目
- [x] `docs/logs/2026/08-22.md` 的本 plan 条目覆盖 Phase 1–4 **四个阶段**，不是只到 Phase 3

#### Phase 4 执行记录（2026-08-22 回填，实跑）

**四条基线命令原样复跑，命令原文 + 退出码 + 输出尾行**：

| 命令原文 | 退出码 | 输出尾行 | 与 Baseline 一致 |
|---|---|---|---|
| `ruff check agenerp tests/unit tests/contracts` | **0** | `All checks passed!` | ✅ |
| `python3 -m pytest tests/unit -q` | **0** | `221 passed in 0.55s` | ✅ 条数不变 |
| `python3 -m pytest tests/contracts -q` | **0** | `151 passed in 0.09s` | ✅ 条数不变 |
| `python3 tools/gates/check_expected_red.py` | **0** | `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致` | ✅ 判定行逐字节不变 |

四条结论与 `## Current Baseline` **逐字一致** —— 本 plan 确实一行代码未改。

**红线自查（基线 sha 钉死 `57702c5`，不用裸 `git diff`）**：

```
$ git diff --name-only 57702c5 HEAD -- tests/gates .github/workflows missions \
    docs/masterplan/DECISIONS.md tools/gates/expected-red.txt \
    tools/gates/check_expected_red.py agenerp
<无输出>
$ git status --porcelain
<无输出>
```

**✅ 无输出，红线自查通过（`agenerp` 也在清单里，本 plan 明示不改一行代码）；工作区无遗留未提交改动。**

**本 plan 全部变更文件（`git diff --name-only 57702c5 HEAD`，8 个，全部在 `docs/**` 下）**：

```
docs/architecture/module-boundaries.md
docs/audits/p0-foundation/2026-08-22-1041-1-draft-review-iteration-1.md
docs/backlog/irreversible-ddl-has-no-code-level-precondition.md
docs/backlog/p0-foundation-roadmap.md
docs/context/ai-autonomy-policy.md
docs/context/project-context.md
docs/logs/2026/08-22.md
docs/plans/p0-foundation/2026-08-22-1041-1-destructive-write-owner-doc-alignment.md
```

**三个提交**：`266f824`（Phase 1）· `2762a6d`（Phase 2）· `b69d4e0`（Phase 3）。
iteration 2 评审要求入库的 durable 证据
`docs/audits/p0-foundation/2026-08-22-1041-1-draft-review-iteration-1.md` 已随 `266f824` 一起入库。

**零 `git push` 的证据（**在线证据，不是离线替代**）**：

- `git rev-list --count origin/main..main` → **8**。开工时是 **5**，增量 **3** = 本 plan 的三个提交，
  **没有任何提交被推走**（推走会让计数下降）。
- **远端证据**：`git ls-remote origin main` → `3ed5f5bad05f3c8d05d512bc58c1115b0b2a0713`，
  与 `git rev-parse origin/main` **逐字节相同** —— `origin/main` 仍停在开工时那个 sha。
- `git reflog show --date=iso origin/main` 最新一条是 `3ed5f5b … @{2026-08-22 05:55:52 +0800}: update by push`，
  **本轮（2026-08-22 11:20 起）无新条目**。
- 因此 `.github/workflows/gates.yml` 的 `push: branches: [main]` **本轮一次都没被触发，零 CI 消耗**。

**验证范围（照实写，不得报成 full green）**：本仓**无全量套件**（无 build、无 typecheck，见
`docs/context/project-context.md`），且本 plan **不跑 L2 / 不起 docker 栈 / 不连活站点**。
上面四条是本机 L1 判定环境的全部可跑验证。**CI 未跑，且本 plan 明示不跑** —— 不得被读成「CI 已验证」。

**失败分支的固定处置（现在写死，执行时不许临场发挥）**：
任一阶段的 Exit Criteria 拿不到 → 记录所有已跑命令与输出原文 → 追加进 `docs/masterplan/STATE.md` §3
（**只追加，不改写任何已有行**）→ 本 plan 置 `Plan Status: deferred` 并在文件头写明重开条件
→ `git checkout -- docs/` 复原 → **不猜根因、不放宽任何收窄、不碰 `tests/gates/**`**。

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，2026-08-22，
  MISSION_DRIVER `2026-08-22-055517-mission-driver`）—— 评审对象是本 plan 的**前一稿**
  `2026-08-22-1041-1-ddl-drop-rollback-evidence.md`（题目是「给 `drop_columns` 加前置取证 + fail-closed」）。
  8 条 Blocking 里有 3 条是**对题目本身**的，不是对写法的：
  **B1** 判据先行的豁免不适用 —— roadmap 工作项 9 那一格逐字排除了「绑着具体断言」的工作项，
  而这条路径归工作项 5/6，绑的是 `test_customization_roundtrip_delete.py` 的具体断言；
  **B3** 「Protected Areas 漏了 `drop_columns`」这个 `Minimum Rule 14` 强制力**站不住**——
  `:87` 已点名 `execute_plan` 的删除路径，而那是 `drop_columns` 的调用链，区域意义上已罩住；
  **B4** `1922-3` Deferred 第一条被截断引用，漏掉的正是承重的那半句「站点侧的回滚只能手工做」——
  即「手工回滚」是**已裁定状态**，在 P0 里改掉它是重开别人的裁定。
  评审的推荐是「(ii) 收窄到 `ai-autonomy-policy.md:87` 的加严，把取证/fail-closed 写进 `docs/backlog/` 交人裁定」。
  **本稿是照这条推荐重写的，不是修补**：前一稿已删除，`agenerp/**` 从「要改」变成「一行不改」，
  D1 的性质从「漂移」改述为「加严 + 具体化」（B3），`1922-3` 的引用补全承重半句（B4），
  判据先行的排除句逐字写进 Baseline（B1）。
  其余 5 条 Blocking 随前一稿的三个 Phase 一起消失（B5 候选表不对称 / B8 取证产物落盘与 `.gitignore`
  只对取证实现成立；B2 「本仓唯一的写动作」已改述为三处落点并列；
  **B6** 裸 `<基线>` 已钉死为 `57702c5`；**B7** 零 CI 消耗已补上「不 `git push`（含 `main`）」并写明理由）。
  Non-blocking 里被采纳进本稿的：NB1（`module-boundaries.md:577/:581` 两处真漂移 → 本稿的 D2/D3）、
  NB6（契约面台账那条的触发条件循环 → 本稿已改写）、NB8（Exit Criteria 无可跑命令 → 本稿**除四条 `docs/logs/` 追加项之外**每条都配了可跑命令；
  那四条沿用指南模板的默认写法，判据是「日志条目存在且覆盖该阶段」，由关闭审计肉眼核对）。
- Independent draft review iteration 2: **needs revision**（独立子代理，fresh session，2026-08-22）——
  评审对象是**本稿**。唯一 Blocking：本文件的 iteration 1 记录引用了一份**已删除且从未提交**的前一稿
  （`git log --all` 零命中），那些引用无法被独立核对。**处置**：把第 1 轮结论落成 durable 证据
  `docs/audits/p0-foundation/2026-08-22-1041-1-draft-review-iteration-1.md`（照实抄，不改写），
  缺口消除。该文件此刻仍是未提交状态（`git status` 显示 `?? docs/audits/p0-foundation/`），
  执行本 plan 时随第一个提交一起入库。
- Independent draft review iteration 3: **accept**（独立评审步 MISSION_DRIVER `2026-08-22-112156-mission-driver`，
  fresh session，2026-08-22）—— 在 `57702c5` 上逐条复核了 Baseline 的可判事实，全部对得上：
  `sed -n '577p;581p;338p' docs/architecture/module-boundaries.md` 三格状态与 D2/D3 所述**逐字一致**；
  `ai-autonomy-policy.md:87`/`:88` 与 `project-context.md:60` 行号命中；
  `grep -n "oob\|drop_columns\|DDL\|ALTER" docs/context/ai-autonomy-policy.md` → **exit 1 零输出**；
  `grep -rn "backup" agenerp/*.py` → **exit 1 零输出**；`git rev-list --count origin/main..main` → **5**；
  `agenerp/site.py:196` · `apply.py:254`/`:304` · `oob.py:255` · `pack.py:153` 定义行全部对得上；
  roadmap「5 现状」`:62` /「6 现状」`:64` 与工作项 9 那一格的排除句逐字存在。
  **本轮就地改掉四处 Blocking/Major**：① 标题与 `Work Item` 的「四处确认漂移」与正文分类相反（正文只认 D2/D3）；
  ② `## Goals` 把 D4 说成「假陈述」，与 Baseline 明文「D4 不是漂移」直接打架；
  ③ Phase 3 的 `grep -c "^-[^-]"` → 0 与它自己的执行项（就地在既有行末追加）**互斥、恒不可满足**，
  已换成与 Phase 2 同款的「行内比对」三条判据；④ Phase 1 三个执行项里 D4 无任何 Exit Criteria，已补三条可跑判据。
  改完后判据覆盖完整、口径自洽，**置 `active`**。

## Closure Gates

- [x] in-scope behavior is complete（D1 加严 + D2/D3/D4 三处改准 + backlog 条目 + roadmap 追加，五件事全落地）
- [x] relevant docs are aligned：`ai-autonomy-policy.md` · `module-boundaries.md` §11.7 ·
      `project-context.md` · `docs/backlog/`（新条目 + roadmap 两行）
- [x] verification has run：`ruff check agenerp tests/unit tests/contracts` ·
      `python3 -m pytest tests/unit -q` · `python3 -m pytest tests/contracts -q` ·
      `python3 tools/gates/check_expected_red.py`（四条命令原文与退出码记在 Phase 4）
- [x] **verification scope limited** —— 本仓无全量套件（无 build、无 typecheck，见 `project-context.md`），
      且本 plan **不跑 L2 / 不起 docker 栈 / 不连活站点**；关闭记录必须逐字写明这一句，不得报成 full green
- [x] **CI 未跑，且本 plan 明示不跑**（零 CI 消耗，含不 `git push` `main`）；这一点写进关闭记录，
      不得被读成「CI 已验证」
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（**两轮**：前一稿的 needs revision + 本稿的评审）
- [x] text consistency verified: status, phases, gates, and log all agree。
      判据命令**必须行首锚定**：`grep -B5 '^- \[ \]' <本文件> | grep '^Status: completed'` → **无输出**。
      ⚠️ 指南 Minimum Rule 12 给的裸形态（不锚定）在本文件上**恒不可满足**——本行自己引的这条命令
      就是文件里的一段文本，裸 `grep` 会把它当命中。实测过，因此这里锚定行首，不是放宽判据
- [x] closure audit was independent（执行器自勾即自审，不算）
- [x] closure evidence exists in files
- [x] 红线自查通过：Phase 4 那条以 `57702c5` 为基线的 `git diff --name-only` 无输出（**含 `agenerp`**）

## Deferred But Adjudicated

### 给不可逆 DDL 加代码级前置（备份 / 取证 / fail-closed）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: **自始不在本 plan 的结果面内**（见 `## Non-Goals`），
  且有两条硬拦：判据先行的豁免不适用于工作项 5/6（roadmap 工作项 9 那一格的逐字排除句），
  补新门禁在红线 1 内；`1922-3` Deferred 第一条已把「站点侧的回滚只能手工做」定成已裁定状态。
  本 plan 的处置是 **Phase 3 把它写进 `docs/backlog/` 并带触发条件**，不是静默丢弃。
- Successor Required: `yes` —— 由人从 backlog 条目的可选处置里选定之后，起一个专门的 plan
- 重开事件：**人对 `docs/backlog/irreversible-ddl-has-no-code-level-precondition.md` 的
  可选处置作出选择时**，或**人出具 `Gates-Change-Approved-By:` trailer 为这条路径补一条门禁时**，
  或 `1922-3` Deferred 第一条的重开事件（出现需要用包在站点上建字段的调用方）发生时。三者任一即重开。

### `tests/unit/test_contract_surface.py` 的 `NOT_YET_IMPLEMENTED` 仍挂着已实现的 `apply_pack`

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 这是**另一个结果面**（判据台账，不是 owner-doc），
  且按 `docs/plans/00-plan-authoring-and-execution-guide.md` 的 Plan Decision Table 属
  「test-only cleanup → No plan」。One plan, one result surface，本 plan 不顺手改它。
- Successor Required: `no`
- 重开事件：**下一个改动 `agenerp/pack.py::apply_pack` 或 `tests/unit/test_contract_surface.py` 的 plan
  开工时**（该文件 `:54` 自述「函数真正实现之后把名字搬进 IMPLEMENTED」，届时顺手改准即可，
  不需要为它单起一个 plan）。

### `docs/context/project-context.md` 的验证命令表整体臃肿

- Classification: `optimization candidate`
- Why Not Blocking Closure: 该表的单行已长到数千字、且含三层「二次/三次补记 就地改准」的相互推翻，
  确实妨碍阅读；但**重构它是独立的结果面**，且有丢失事实的风险（每一条补记都是证据）。
  本 plan 只就地改准 D4 那一句，不动结构。
- Successor Required: `no`
- 重开事件：**下一个需要往该表新增一行或改写既有行的 plan 开工时**（届时它已经要动这张表，
  顺带评估结构是否还撑得住是同一次动作的一部分）；或**人明确裁定要重构该表时**。二者任一即重开。
  本 plan 不代人裁定，也不为此新建 backlog 条目——该事实已由本条与 `## Non-Goals` 记着。

## Closure

Status Note: 四个 Phase 全部执行完毕，逐项证据写在各 Phase 的「执行记录」小节下（命令原文 + 退出码 + sha）。
交付面五件事全部落地：D1 加严（`ai-autonomy-policy.md:87` 点名 `drop_columns` + 补一条对不可逆性说话的
Required Evidence，行内三格比对确认只加严不放宽）· D2/D3 两处假陈述就地改准（`module-boundaries.md` §11.7）·
D4 效力范围具体化（`project-context.md:60`，纯追加，原句一字未删未弱化）· 新建 backlog 条目
`irreversible-ddl-has-no-code-level-precondition.md`（三条触发条件 + 四档可选处置，交人裁定）·
roadmap「5 现状」/「6 现状」行内追加（`planned` 一个字未改）。

**`agenerp/**` 一行未改**，红线自查（基线 `57702c5`，含 `agenerp` 的 pathspec）**无输出**。
提交三个：`266f824` · `2762a6d` · `b69d4e0`。

**verification scope limited（逐字写明，不得报成 full green）**：本仓**无全量套件**（无 build、无 typecheck，
见 `docs/context/project-context.md`），且本 plan **不跑 L2 / 不起 docker 栈 / 不连活站点**。
可跑验证只有四条本机 L1 命令，全部 exit 0 且结论与 Baseline 逐字一致（221 / 151 / 判定行不变）。
**CI 未跑，且本 plan 明示不跑**（零 CI 消耗，全程零 `git push` 含 `main`；`git ls-remote origin main` 仍是
`3ed5f5b`，与开工时逐字节相同）—— **这一点不得被读成「CI 已验证」。**

**上面的 Closure Gates 十一框（本节此前写「十二框」，实际是 11 条，本次按实际条数照实改准）
由独立 `CLOSURE_VERIFY` 步回填，执行器未自勾**（`AGENTS.md` 裁判规则：执行器自勾即自审，不算）。

Closure Audit Evidence:

- Auditor / Agent: 独立关闭审计步 MISSION_DRIVER `2026-08-22-112156-mission-driver`，fresh session，
  非本 plan 的执行器会话。审计基线为**关闭时的 HEAD `3a0a648`**（执行器的三个交付提交
  `266f824` · `2762a6d` · `b69d4e0` + 置 `completed` 的 `3a0a648`），全部命令由审计方自己复跑，
  不采信 plan 内已记录的任何输出。
- Evidence · 四条基线命令自行复跑（命令原文 + 退出码 + 输出尾行）：
  `ruff check agenerp tests/unit tests/contracts` → **exit 0**，`All checks passed!` ·
  `python3 -m pytest tests/unit -q` → **exit 0**，`221 passed` ·
  `python3 -m pytest tests/contracts -q` → **exit 0**，`151 passed` ·
  `python3 tools/gates/check_expected_red.py` → **exit 0**，
  `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`。
  四条与 `## Current Baseline` 逐字一致（221 / 151 / 判定行不变）。
- Evidence · 红线自查自行复跑：
  `git diff --name-only 57702c5 HEAD -- tests/gates .github/workflows missions docs/masterplan/DECISIONS.md tools/gates/expected-red.txt tools/gates/check_expected_red.py agenerp`
  → **无输出**；`git status --porcelain` → **无输出**；
  `git diff --name-only 57702c5 HEAD` → **8 个文件，全部在 `docs/**` 下**（与 Phase 4 记录的清单逐字相同）。
- Evidence · 交付面逐条对着**活仓**核验（不采信 `[x]`）：
  ① `sed -n '574,582p' docs/architecture/module-boundaries.md | grep -n "只有读方法\|未做"` → **exit 1，无输出**；
  ② `sed -n '577p'` 状态格实为「已实现（读方法 + **一条**写方法 `delete_custom_field`…）」（D2 已改准）；
  ③ `sed -n '581p'` 状态格实为「已实现（判据 `tests/unit/test_site_client.py` 的 `WRITE_METHOD_ALLOWLIST`）」
  且行内含「从 2026-08-21 起就是假的」「改准一句假陈述，不是新增一项」（D3 已改准，未粉饰）；
  ④ `grep -n "已实现（B 半）" docs/architecture/module-boundaries.md` → 仍命中 `:334`–`:338`，§11.6 未被顺手改动；
  ⑤ `sed -n '60p' docs/context/project-context.md` 中 `bench --site frontend backup` → **1 次命中**、
  `apply_pack` → **1 次命中**；用 `git show 57702c5:` 取旧行程序化比对：**旧行（去行尾 `|`）逐字节是新行前缀**
  （804 → 1525 字符，纯追加，D4 原句未删未弱化）；
  ⑥ `grep -n "drop_columns" docs/context/ai-autonomy-policy.md` → 命中 `:87`（落点行）与 `:93`/`:94`/`:107`/`:120`（Decision 说明段）；
  ⑦ **D1「只加严不放宽」的行内三格由审计方独立程序化比对**（旧行取自
  `git show 57702c5:docs/context/ai-autonomy-policy.md | sed -n '87p'`，按 `|` 切格）：
  **Rule 格** 旧 `plan-first` == 新 `plan-first`，逐字节相同；
  **Required Evidence 格** 旧的三条（`独立草案评审` / `独立关闭审计` / `实跑前后全量 capture 对照` +
  `差集必须只含本次探针`）与 `1922-3` 补行自述**逐字全部仍在**，只增一条——
  需注意旧格**不是新格的连续子串**（新增那条插在补行自述之前），所以判据是「逐条片段仍在」的超集判定，
  不是子串判定，plan 内「逐字全部仍在，只增了一条」的表述与实测相符；
  **Area 格** 旧点名的两处逐字仍在，新增 `agenerp/oob.py` · `drop_columns`，只增不减；
  ⑧ `docs/context/ai-autonomy-policy.md` 表下说明段内含候选 (a)/(b)/(c) 三行表、否决 (b)/(c) 的理由
  （锁死会让绿着的门禁 `test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`
  的实现面进入不可维护状态）、残余风险（文档级约束对拿着 shell 的执行器没有强制力 + 代码侧仍零备份零取证）
  —— Decision 三要素确实落在**该文件本身**，不是只落在 plan 里；
  ⑨ `docs/backlog/irreversible-ddl-has-no-code-level-precondition.md` 存在（**8865 字节**），
  `grep -c "触发条件"` → **1**；
  ⑩ `grep -n "1041-1" docs/backlog/p0-foundation-roadmap.md` → `:62`（5 现状）与 `:64`（6 现状）各一处；
  程序化比对确认**两行旧内容均为新内容前缀**（3720→4787 / 4110→5177 字符，纯追加），
  且「保持 `planned`」在新旧两侧**都在**，状态词未被动过。
- Evidence · 零 CI 消耗自行取证：`git rev-parse origin/main` → `3ed5f5bad05f3c8d05d512bc58c1115b0b2a0713`，
  与 Phase 4 记录的 `git ls-remote origin main` 值**逐字节相同**，`origin/main` 仍停在开工时那个 sha；
  `git rev-list --count origin/main..main` → **9**（开工 5 + 交付 3 + 置 `completed` 的 `3a0a648` 1 个；
  Phase 4 当时记的是 8，差的正是其后那一个 `docs/**` 提交，**没有任何提交被推走**）。
  `.github/workflows/gates.yml` 的 `push: branches: [main]` 本轮未被触发。
- Evidence · Anti-Hollow：本 plan 的结果面是 owner-doc 与 backlog 文本，`agenerp/**` 与 `tests/**`
  **一行未改**（上面的红线 pathspec 含 `agenerp`，无输出），因此不存在「新代码未接线」这一类空壳风险；
  **代码侧零备份零取证这条真实缺口没有被藏进 Deferred**——它在 `ai-autonomy-policy.md` 说明段、
  `project-context.md:60`、backlog 新条目、roadmap 两行**四处都逐字写着「本轮不实现、交人裁定」**。
- Evidence · 五点一致性：`Plan Status: completed`（`:3`）· 四个 Phase `Status: completed` ·
  四个 Phase 的 Exit Criteria 全部 `[x]` · Closure Gates 11 框全部 `[x]`（本次由审计方回填）·
  `docs/logs/2026/08-22.md` 内 `1041-1` 条目覆盖 **Phase 1/2/3/4 四个阶段**（`:88` / `:61` / `:27` / `:3`）
  —— 五处互不矛盾。行首锚定判据 `grep -B5 '^- \[ \]' <本文件> | grep '^Status: completed'` → **无输出**；
  全文 `grep -c "^- \[ \]"` → **0**。
- Evidence · **verification scope limited（照抄，不改判）**：本仓无全量套件（无 build、无 typecheck），
  本轮**不跑 L2 / 不起 docker 栈 / 不连活站点 / CI 未跑**。上面四条本机 L1 命令是全部可跑验证，
  **不得读成「CI 已验证」或 full green**。

Follow-up:

- 本文件 `## Closure` 原写「Closure Gates 十二框」，实际是 11 条；已在本次关闭审计中照实改准为十一框。
  非缺陷，记录在此以免后续会话按「十二」去对账。
- `docs/backlog/irreversible-ddl-has-no-code-level-precondition.md` 等人裁定；其重开事件已写在
  `## Deferred But Adjudicated` 第一条，本 plan 不代人选。
