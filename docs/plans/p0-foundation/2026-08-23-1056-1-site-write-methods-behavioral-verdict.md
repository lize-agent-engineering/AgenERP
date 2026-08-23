# 2026-08-23-1056-1 `agenerp/site.py` 在默认判定面上零行为判据 —— 写方法可被改成 no-op、传输失败翻译与基址解析可被改坏，而 `GATE_VERIFY` 全绿

> Plan Status: active
> Mission: p0-foundation
> Work Item: 工作项 9 · 判据设施的加严（`agenerp/site.py` 侧）
> Last Reviewed: 2026-08-23
> Source: 本轮 mission-driver 起草时在 `main` @ `499fe24` 上实跑覆盖率 + 七次变异实验（证据见 `## Current Baseline`）
> Related: `2026-08-23-0859-1-budget-halt-gate-verdict-coverage.md`（同一形态的前驱：给零判据模块补行为判据）
> Audit: required

## Current Baseline

**全部为 2026-08-23 在 `main` @ `499fe24a039f11ee191f036bd7a3a642d30d5024` 上实跑/实读，不是推理。**

| # | 事实 | 取证命令 → 结果 |
|---|---|---|
| 1 | 判定面此刻是 `tests/unit`，**不含任何 L2 门禁** | `missions/p0-foundation.json:16` 的 `commands.test` 逐字 `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`；默认环境无 `AGENERP_LIVE`，`tests/gates/conftest.py` 的 `_require_live()` 直接 `pytest.fail` |
| 2 | 当前测试基线 | `python3 -m pytest tests/unit -q` → **exit 0，`320 passed`**；`python3 -m pytest tests/contracts -q` → **exit 0，`151 passed`**（合计 471） |
| 3 | `agenerp/site.py` 覆盖率 94%，10 行未覆盖 | `python3 -m coverage run -m pytest tests/unit tests/contracts -q && python3 -m coverage report --include='agenerp/site.py' -m` → `155  10  94%  94, 141, 143, 157, 183, 195, 298, 316-318` |
| 4 | 未覆盖的 `316-318` **就是 `delete_custom_field` 的整个函数体** | `awk 'NR>=316&&NR<=318' agenerp/site.py` → `self._ensure_authenticated()` / `name = custom_field_name(...)` / `self._request("DELETE", ...)` |
| 5 | 该方法是 `ai-autonomy-policy.md` Protected Areas「对活站点的破坏性写」那一行**逐字点名的落点之一** | `docs/context/ai-autonomy-policy.md:88` 原文含 `agenerp/site.py` · `SiteClient.delete_custom_field` |
| 6 | `tests/unit/test_site_client.py` 有 32 条，且已把该方法登记进 `WRITE_METHOD_ALLOWLIST` | `grep -c "def test_" tests/unit/test_site_client.py` → `32`；`tests/unit/test_site_client.py:47` 逐字 `"SiteClient.delete_custom_field",` |
| 7 | **留痕有了，行为判据没有** —— 6 与 4 合起来就是本 plan 的缺口 | 见下表的变异 J |
| 8 | **将发生的 owner-doc 漂移，且是复发性的**：`docs/context/project-context.md` 在 **`:53` 与 `:57` 两处**把 `tests/unit` 的活计数记作 `**320 条**`，且 `:57` 把它列为一条具名**代偿控制**；本 plan 会把该数推到 320 以上 | `grep -n "320" docs/context/project-context.md` → 命中 `:53` `:57`；`:53` 自述该数已被就地改准过三次（`283 → 288 → 293 → 320`）。**按 Minimum Rule 14 不得降级为 follow-up**，因此它是 Phase 3 的一个 `Fix` 项，不是收尾时的顺手动作 |

### 七条变异实测**完全隐形**（每条都跑 `python3 -m pytest tests/unit tests/contracts -q`，全部 `471 passed`）

| 变异 | 改法（改完立刻 `cp` 复原，`git diff --stat` 无输出） | 真实后果 |
|---|---|---|
| **J** | `delete_custom_field` 函数体整体换成 `return None` | **破坏性写变成 no-op**，差集 apply 的删除面静默失效，`GATE_VERIFY` 照绿 |
| **K** | `custom_field_name` 返回 `f"{fieldname}-{doctype}"`（顺序对调） | 删除路径打到一个不存在的 name 上 |
| **L** | `submit_doc` 响应缺 `data` 对象时 `return {}` 而不抛 | 「站点回 2xx 但没提交上去」被伪装成成功 |
| **M** | `SiteClient.__init__` 空站点名不抛 `SiteError`（`raise` 换 `pass`） | 空站点名一路带进请求 URL |
| **H** | `UrllibTransport` 把 `HTTPError.code` 改写成 `200` | 站点回的 4xx/5xx 一律读成成功 |
| **I** | `default_base_url` 忽略 `AGENERP_SITE_URL`（`explicit` 恒为 `""`） | 环境变量覆盖失效，live 判定打到错的基址 |
| **O** | `default_base_url` 忽略 `AGENERP_HTTP_PORT`（恒取默认端口） | 同上 |

### 已经有牙齿的两条，照实记，本 plan 不重复造判据

| 变异 | 结果 |
|---|---|
| **G** `UrllibTransport` 把「连不上」吞成 `SiteResponse(200, "{}")` | `1 failed, 470 passed` —— 该文件模块 docstring 写死的「连不上那条必须走真 `UrllibTransport`」用例抓到了 |
| **N** `submit_doc` 的 `docstatus` 不符分支不再抛 | `1 failed, 470 passed` |

### 缺口的准确表述（不得夸大）

⚠️ 上表七条**不是全部无人可管**：`delete_custom_field` 被 L2 门禁
`tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site`
真正走过，且该门禁已在 CI 的 `gates-l2-live` job 上绿过。
**缺的是「默认判定面上没有任何东西看得见它」** —— 每轮 `GATE_VERIFY` 与 `gates-l1` 都复跑不到 L2，
所以 loop 可以在一轮里把它改成 no-op、当轮自证为绿，要等到起了 docker 的那个 job 才炸。
本 plan 补的正是这一层，**不是**「它此刻完全没有覆盖」。

## Goals

- 上表 **J / K / L / M / H / I / O 七条变异**，落地后各自至少被一条 `tests/unit` 断言**逐字点名**（改坏 → `pytest tests/unit` 非零退出且输出里出现对应用例名）。
- 新增断言全部落在 `tests/unit/**`，因此**每轮 `GATE_VERIFY` 都复跑得到**，不依赖 docker、不依赖活站点、不依赖网络。

## Non-Goals

- **不改 `agenerp/site.py` 的任何一行行为。** 本 plan 只加判据，不加 fail-closed 开关、不加前置备份、不改错误措辞。代码级前置那件事是 `docs/backlog/irreversible-ddl-has-no-code-level-precondition.md` 里的**人裁定题**，本 plan 不重开。
- **不碰 `tests/gates/**`**（红线 1）、**不碰 `.github/workflows/**`**（红线 2）、**不碰 `missions/**`**（角色 B 禁区）、**不碰 `tools/gates/expected-red.txt`**。
- 不起真站点、不起本地 `http.server`、不绑任何端口 —— 沿用 `tests/unit/test_site_client.py` 模块 docstring 已写死的口径（本机 8080 端口冲突是实测事实）。
- 不引入覆盖率阈值门槛，也不把覆盖率数字写成判据（判据是**点名的行为**，不是行数）。
- 不处置 `agenerp/oob.py` 的同类缺口 —— 那是本批第二个 plan `2026-08-23-1056-2` 的结果面。

## Task Route

- Type: `verification or audit work`
- Owner Docs: `docs/architecture/module-boundaries.md` §11.7（`agenerp/site.py` 的落点与「不伪装成功」约定；**本 plan 对该节 `No owner-doc update required`** —— 零行为改动，落点表与约定措辞不因本 plan 变化。⚠️ 若 Phase 3 实读发现该节与代码有出入，按 Minimum Rule 14 就地改准并升级为 `Fix`，不降级）· `docs/context/ai-autonomy-policy.md` Protected Areas · `docs/context/project-context.md`（`:53` / `:57` 两处 `tests/unit` 活计数 —— Baseline 8 的确认漂移，Phase 3 的 `Fix` 项）· `docs/architecture/system-baseline.md`（本 plan 的口径落 §14.11，开工时须实读 `grep '^## 14\.' docs/architecture/system-baseline.md` 取下一个空编号；起草时实测最大为 §14.10）
- Skill Selection Basis: `none` —— `docs/skills/README.md` 里没有「补行为判据」这类可复用 skill；前驱 `2026-08-23-0859-1` 走的也是 `Skill: none`。

### Protected Areas 自查（`delete_custom_field` 在「对活站点的破坏性写」那一行内，必须逐条应答）

- **独立草案评审 + 独立关闭审计**：本 plan 走完整流程，见 `## Draft Review Record` 与 `## Closure`。
- **实跑前后全量 `capture` 对照（差集必须只含本次探针）**：**不适用，且不伪造**。本 plan
  零 docker、零网络、零活站点（见 `## Non-Goals`），**不存在「前后」两个站点快照可对照**；
  `agenerp/site.py` 一行未改，删除路径的行为面与 `main` @ `499fe24` 逐字相同。
  该条以「本 plan 的作用域内无对照对象」记，**不以「已做」记**；机械替代证据是
  `git diff --numstat agenerp/site.py` 无输出。
- **对不可逆性说话的 Required Evidence**：本 plan **零代码级前置/取证交付**。逐字声明——
  **站点侧的回滚仍然只能手工做**，手工前置命令原文是
  `docker compose exec -T backend bench --site frontend backup`（`docs/context/project-context.md:63`）。
  本 plan **不改变**这条现状，也**不宣称**改善了它。

## Infrastructure And Config Prereqs

- 无。新增断言纯标准库、零 docker、零网络、零环境变量依赖（涉及环境变量的三条用 `monkeypatch` 设/清）。
- 无数据迁移，无回滚脚本需求（本 plan 只新增测试文件内容）。

## Execution Plan

### Phase 1 — 写方法的行为判据（J / K / L / M）

Status: completed
Targets: `tests/unit/test_site_client.py`
Skill: `none`

- Item Types: `Add | Proof`（5/6 项为 `Add`，≥80%，按 Minimum Rule 7 声明为 phase 级统一类型；末项为 `Proof`）
- Prereqs: 无

- [x] `delete_custom_field` 的行为判据：喂既有的假 transport，断言**恰好发出一次**请求，且 `method == "DELETE"`、URL 逐字以 `/api/resource/Custom%20Field/<doctype>-<fieldname>` 结尾（**断言落在编码后的形态上** —— `agenerp/site.py:350` 是 `self.base_url + encode_path(path)`，`Custom Field` 的空格在这一步变成 `%20`；写未编码的字面量会让断言与真发出的请求对不上）。**变异 J 必须被这一条点名。**
- [x] `delete_custom_field` 的失败面判据：站点回 404 时抛 `SiteError`（该方法 docstring 逐字写着「要删的东西不在」判为失败、不静默吞掉）。
- [x] `custom_field_name` 的形状判据：`custom_field_name("Item", "agenerp_x") == "Item-agenerp_x"`，并断言 `delete_custom_field` 发出的 name 与它同源（**不手抄字符串**，用函数本身求值，否则两处一起改错时判据失效）。**变异 K 必须被点名。**
- [x] `submit_doc` 响应缺 `data` 对象时抛 `SiteError`（载荷为 `{"data": "ok"}` / `{}` / `[]` 三种非 dict 形态各一条）。**变异 L 必须被点名。**
- [x] `SiteClient(site="")` 抛 `SiteError` 且消息含 `AGENERP_SITE`。**变异 M 必须被点名。**
- [x] Proof：`python3 -m pytest tests/unit -q` → exit 0；四条变异逐一施加，**每一条都走这四步，缺一步该条不算数**：
      (a) 施加后先 `git diff --numstat agenerp/site.py`，**必须非空** —— 空则说明替换根本没落上，
      「471 passed」会与「变异隐形」长得一模一样（起草期的独立评审实测踩到过一次）；
      (b) 跑 `python3 -m pytest tests/unit -q`，记录**退出码 + 逐字的 `FAILED …::<用例名>` 行**；
      (c) `git checkout agenerp/site.py` 复原；
      (d) 复原后 `git diff --stat agenerp/site.py` **必须无输出**，**每条变异后各查一次**，不是收尾时查一次。
      **`agenerp/site.py` 在被变异的状态下一次都不得提交。**

Exit Criteria:

- [x] J / K / L / M 四条变异各自至少让一条新断言红，且红时输出逐字点名该用例
- [x] `agenerp/site.py` **一行未改**（`git diff --numstat agenerp/site.py` 无输出）
- [x] `python3 -m pytest tests/unit -q` exit 0，`passed` 计数比基线 320 增加，且增量等于**新增的、被 pytest 收集到的 test id 数（`parametrize` 按展开后逐条计）**，用 `python3 -m pytest tests/unit --collect-only -q | tail -1` 前后对照，不靠手数
- [x] `docs/logs/2026/08-23.md` 追加条目

### Phase 2 — 传输失败翻译与基址解析的行为判据（H / I / O）

Status: planned
Targets: `tests/unit/test_site_client.py`
Skill: `none`

- Item Types: `Decision | Add | Proof`
- Prereqs: Phase 1（同一文件，避免两段并行改同一处 import 块）

- [ ] **Decision**：`UrllibTransport` 的 HTTP 错误路径怎么造假件。候选与取舍必须写进本项或紧邻注释：
      (a) 替换实例的 `_opener`（私有属性，测试与实现耦合）；
      (b) `monkeypatch` `agenerp.site.urllib.request.build_opener`（构造期注入，不碰私有名）；
      (c) 起本地 `http.server` 回 4xx（**已被该文件模块 docstring 逐字排除**：端口冲突是实测事实）。
      残余风险照实写。**(c) 不选的理由是既有裁定，不重开。**
- [ ] `UrllibTransport` 收到 `HTTPError(404)` 时返回 `SiteResponse(404, <body>)` —— **状态码不得被改写成 2xx**，且 body 逐字透传。**变异 H 必须被点名。**
- [ ] `default_base_url()` 在 `AGENERP_SITE_URL=http://example.test:9/` 下返回 `http://example.test:9`（**末尾 `/` 被剥掉**）。**变异 I 必须被点名。**
- [ ] `default_base_url()` 在只设 `AGENERP_HTTP_PORT=19999` 时返回 `http://127.0.0.1:19999`；两个变量都不设时返回默认端口那条。**变异 O 必须被点名。**
- [ ] Proof：三条变异逐一施加，**逐条走 Phase 1 Proof 那四步（施加后 `numstat` 非空 → 跑并记退出码与 `FAILED …::<用例名>` 原文 → `git checkout` → `git diff --stat` 无输出）**；三条跑完后整体回到 exit 0。

Exit Criteria:

- [ ] H / I / O 三条变异各自至少让一条新断言红并被逐字点名
- [ ] Decision 的候选、选择、残余风险已写进文件
- [ ] `agenerp/site.py` 仍是一行未改
- [ ] `docs/logs/2026/08-23.md` 已更新

### Phase 3 — owner-doc 对齐与登记

Status: planned
Targets: `docs/architecture/system-baseline.md` · `docs/context/project-context.md` · `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md` · `docs/logs/2026/08-23.md`
Skill: `none`

- Item Types: `Fix | Add | Decision`（`Fix` 项是 Baseline 8 的确认 owner-doc 漂移，Minimum Rule 14 不降级）
- Prereqs: Phase 1、Phase 2

- [ ] **`Fix`** —— `docs/context/project-context.md` 的 `:53` 与 `:57` **两处** `**320 条**` 就地改准为 Phase 1/2 落地后 `python3 -m pytest tests/unit -q` 的实测通过数，并按该文件既有写法追加一句改准出处（指向本 plan）。⚠️ **两处都要改**：只改一处会让同一份文件对同一个量给出两个读数，本仓已有一次同形态事故留痕（`STATE.md:86`）。
- [ ] `system-baseline.md` 新增 §14.11（**开工时先实读确认该编号未被占用**，此刻最大是 §14.10），记：缺口原文、七条变异的实测退出码、**以及「本 plan 只加判据、`agenerp/site.py` 零行为改动」这条限定**。
- [ ] `p0-foundation-roadmap.md` **纯追加**一行 `9 现状 · …`（不改写既有任何一行），逐字写明：**这是判据设施的加严，不是工作项 9 `done` 判据的替换**；**所有工作项状态值一个字不改**。
- [ ] `STATE.md` §2 **追加**一行证据（命令原文 + 退出码 + sha），不改写已有行（红线 5）。
- [ ] **Decision**：是否把新增用例数写进 `.github/workflows/gates.yml:390` 的 job 名 `单测与契约测试（439 条）`。**选「不改」**（不是「暂缓」，是本轮的裁定）—— 三条理由：① 它在红线 2 的 `blocked` 面内，改它要重摆一次授权面并烧一轮 CI；② `2026-08-23-0859-1` 已就同一处裁定过，重开事件逐字是「下一个因任何理由要动 `gates.yml` 的 plan 开工时」，而本 plan **不动 `gates.yml`**，事件未满足；③ 它**不影响判定**（job 判的是 pytest 退出码，不是那个数字）。**残余风险照实记**：该 job 名会因本 plan 变得更旧，且没有任何机械手段会提醒后来者。执行时把这三条与残余风险原样抄进本项留痕。

Exit Criteria:

- [ ] §14.11 落地且编号未与既有冲突
- [ ] `grep -n "条" docs/context/project-context.md | grep "tests/unit"` 实读确认 `:53` 与 `:57` **两处都等于**当次 `python3 -m pytest tests/unit -q` 的实测通过数，且**两处彼此相等**（`grep -c "<当次通过数> 条" docs/context/project-context.md` **必须等于 `2`**），并且旧读数已清（`grep -n "320 条" docs/context/project-context.md` **零命中**）
- [ ] roadmap 追加行的 `git diff --numstat` 删除列为 `0`
- [ ] `STATE.md` 的 `git diff --numstat` 删除列为 `0`
- [ ] `python3 -m ruff check agenerp tests/unit tests/contracts` → exit 0
- [ ] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session；`agentId a62971bf383dc04c7`）—— 评审**逐条复跑**了本 plan 的全部 Baseline 与九条变异，结论与本文记录**逐字相符**（七条隐形各 `471 passed`；G / N 各 `1 failed, 470 passed` 且分别点名 `::test_unreachable_site_raises_site_error` 与 `::test_submit_doc_raises_when_the_site_answers_2xx_but_the_doc_is_still_a_draft`），**未推翻任何一条事实**。两条 blocking：**M1** `docs/context/project-context.md` `:53` / `:57` 的复发性计数漂移无归属（Minimum Rule 14 不可降级）；**M2** Protected Areas 四条 Required Evidence 只答了三条，`实跑前后全量 capture 对照` 缺席。另六条：M3 四处行号锚点错（`missions:18→16` / `policy:87→88` / `test_site_client:46→47` / `project-context:60→63`，**引文本身逐字正确**）· M4 变异协议缺「确认变异真的落上了」这一步（评审自己实测踩到过一次静默未替换）· M5 标题只覆盖 7 条中的 4 条 · M6 §11.7 无处置 · M7 计数判据在 `parametrize` 下有歧义 · M8 两处措辞（`四档可选处置` 命中禁用词扫描 / `Decision` 写成「默认选」）。**Minimum Rule 4 明确判「不拆」**：同一模块、同一测试文件、同一条关闭判据、同一条「不伪装成功」契约，拆开反而制造跨 plan 的同文件串行依赖。红线自查全过（评审实读 `tools/gates/check_expected_red.py:74` 只 shell `pytest tests/gates`，新增 `tests/unit` 用例动不了棘轮）。
- Independent draft review iteration 2: **acceptable as-is with noted nits**（独立子代理，fresh session；`agentId ac205918d736e1af9`）—— 评审逐条复核了八条修订**全部落实**，并独立重跑了全部 Baseline（`320` / `151` / 覆盖率 `155 10 94% 94, 141, 143, 157, 183, 195, 298, 316-318` 逐字节相同，且**未覆盖行集合与本 plan 的七个目标一一对上**：`94→K` `141/143→H` `157→I` `183→M` `298→L` `316-318→J`）、四处锚点、以及四条 Exit Criteria 命令的**可运行性**（`--collect-only -q | tail -1` → `320 tests collected`；`ruff` exit 0；`check_expected_red.py` exit 0）。红线自查全过，无过度宣称。三条遗留：① should-fix，Phase 1 的 `Item Types` 括注写着 `4/5` 而修订后已是 6 项；② nit，计数 Exit Criterion 只验「旧读数已清」，验不到「两处彼此相等」；③ nit，删除路径的「逐字」字面量写的是未编码形态，而 `agenerp/site.py:350` 走 `encode_path`，真 URL 是 `Custom%20Field`。**三条均已就地修订**（① 改 `5/6` 并点明 ≥80% 的 Rule 7 依据；② 加 `grep -c … 必须等于 2`；③ 改成编码后形态并附 `:350` 出处）。⚠️ 评审同时点明：`## Draft Review Record` 里逐字转录的 `四档可选处置` 会命中禁用词扫描，但 Anti-Slacking 的禁用词只约束 **in-scope item**，逐字保留评审记录是对的，**不改**。
- 收敛结论：**两轮独立评审已收敛**（iteration 1 `needs revision` → 两条 blocking 修毕；iteration 2 `acceptable as-is with noted nits` → 三条遗留修毕，零 blocking），`Plan Status` 由 `draft` 置 `active`。
- （iteration 1 的八条修订记录）上述八条已全部就地修订（M1 升为 Phase 3 的 `Fix` 项 + Owner Docs + 独立 Exit Criterion；M2 补第三条应答并加一条 Closure Gate；M3 四处锚点已实读改准；M4 写死四步变异协议；M5 标题改；M6 补 `No owner-doc update required` 并写明 Rule 14 升级分支；M7 改为 `--collect-only` 前后对照；M8 两处措辞改）

## Closure Gates

- [ ] in-scope behavior is complete（七条变异全部有牙齿）
- [ ] relevant docs are aligned（§14.11 + roadmap 追加行 + STATE 追加行 + 日志）
- [ ] verification has run：`python3 -m pytest tests/unit -q` · `python3 -m pytest tests/contracts -q` · `python3 -m ruff check agenerp tests/unit tests/contracts` · `python3 tools/gates/check_expected_red.py`，四条各记退出码
- [ ] scoped verification is not conflated with full verification —— **本 plan 零 CI 轮次消耗、零 docker、零活站点**，因此**不得宣称任何 CI 侧或 live 侧结论**；「verification scope limited」须逐字写进关闭记录
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] Protected Areas 的「对活站点的破坏性写」Required Evidence **四条逐条应答**：①独立草案评审 ②独立关闭审计 ③**实跑前后全量 `capture` 对照 —— 本 plan 作用域内无对照对象**（零活站点、`agenerp/site.py` 零改动，`git diff --numstat agenerp/site.py` 无输出为替代证据；**不以「已做」记**）④「站点侧回滚仍只能手工做」那句原文已在 plan 内
- [ ] Baseline 8 的确认 owner-doc 漂移已作为 `Fix` 落地（`project-context.md` `:53` / `:57` 两处），**未被降级为 follow-up**

## Deferred But Adjudicated

### `agenerp/site.py` 的代码级破坏性写前置仍然没有

- Classification: `watch-only residual`
- Why Not Blocking Closure: 已登记为人裁定题（`docs/backlog/irreversible-ddl-has-no-code-level-precondition.md`，写死了三条触发条件与四档由人挑选的处置方案）。本 plan 交付的是**判据**，⚠️ **不得被读成「破坏性写现在有前置了」** —— 它只是不再能被静默改成 no-op。
- Successor Required: `no`（**人动作**）
- 重开事件：见该 backlog 条目写死的三条触发条件。

### `tests/unit` 不受任何棘轮保护，本 plan 新增的断言同样可被合法删掉

- Classification: `watch-only residual`（`0120-1` / `0859-1` 已连续登记，本 plan 继续挂着并说明它对本 plan 的具体后果）
- Why Not Blocking Closure: 红线 1 只圈 `tests/gates/**`。⚠️ **对本 plan 尤其要紧**：删掉这些断言等于把 `agenerp/site.py` 退回今天的状态，CI 只会看到 `passed` 计数变小、不会红。
- Successor Required: `no`
- 重开事件：**第一次出现「单测被删/放宽而 CI 仍绿」时**，或**人裁定给该目录加计数棘轮时**。

### `.github/workflows/gates.yml:390` 的 job 名 `单测与契约测试（439 条）` 会被本 plan 推得更旧

- Classification: `watch-only residual`（**红线 2 内，只有人能做**）
- Why Not Blocking Closure: 该数字已经对不上（实测 471），本 plan 会让它更旧。但它**不影响判定**（job 判的是 pytest 退出码）。Phase 3 的 Decision 已就地重裁一次并选「不改」，理由写在那里。
- Successor Required: `no`（**人动作**，可与将来任何一次动 `gates.yml` 的 plan 搭车）
- 重开事件：**下一个因任何理由要动 `gates.yml` 的 plan 开工时**。

### 结果与预测不符时的固定处置（写死，不临场决定）

- Classification: `watch-only residual`（失败分支的写死处置，不是被推迟的工作项）
- 处置逐字：原样复跑一次（裁判规则 3：复跑优先于分析）→ 仍不符则记录所有已跑命令与输出原文 → 追加进 `docs/masterplan/STATE.md` §3（**只追加，不改写既有行**）→ **不放宽任何断言**、**不改 `agenerp/site.py` 去迁就断言**、**不改 `tests/gates/**` 与 `.github/workflows/**`**、**不猜根因** → 本 plan 置 `deferred` 并在文件头写明重开条件。
- Successor Required: `no`
- 重开事件：**人裁定继续**，或不符之因被一个独立 plan 查清之后。

## Closure

Status Note: <pending>

Closure Audit Evidence:

- Auditor / Agent: <pending>
- Evidence: <pending>
