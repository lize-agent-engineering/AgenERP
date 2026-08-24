# 2026-08-23-1056-2 `agenerp/oob.py` 的带外传输产品路径零判据 —— 起不来的 docker 可以被读成「站点很干净」

> Plan Status: deferred
> Deferred: 2026-08-23T04:51Z 由**人**裁定冻结。本 plan 属「判据设施加严」，而工作项 9 已于同日补上终止判据（CI live job 绿 + 预期红名单清空 + 两种模式 exit 0）。产品侧的活已实测完成（live 8 条全绿），当前唯一该做的是**收口**，不是继续加固。
> Reopen: 工作项 9 按终止判据转 `done` 之后，若人仍认为需要这层加严，**作为新工作项重开并排优先级** —— 不得在工作项 9 名下继续追加。

> Mission: p0-foundation
> Work Item: 工作项 9 · 判据设施的加严（`agenerp/oob.py` 侧）
> Last Reviewed: 2026-08-23
> Source: 本轮 mission-driver 起草时在 `main` @ `ffc1be4` 上实跑覆盖率 + 三次变异实验（证据见 `## Current Baseline`）
> Related: `2026-08-23-1056-1-site-write-methods-behavioral-verdict.md`（本批第一个 plan，同一形态、另一个模块）· `2026-08-23-0859-1-budget-halt-gate-verdict-coverage.md`（前驱形态）
> Audit: required

## Current Baseline

**全部为 2026-08-23 在 `main` @ `ffc1be4ce1440746f589ebf45f6ef7504d556fee` 上实跑/实读，不是推理。**

| # | 事实 | 取证命令 → 结果 |
|---|---|---|
| 1 | 判定面此刻是 `tests/unit`，**不含任何 L2 门禁** | `missions/p0-foundation.json:16` 逐字 `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` |
| 2 | 当前测试基线 | `tests/unit` → **exit 0，`320 passed`**；`tests/contracts` → **exit 0，`151 passed`**（合计 471） |
| 3 | `agenerp/oob.py` 覆盖率 87%，14 行未覆盖 | `python3 -m coverage report --include='agenerp/oob.py' -m` → `108  14  87%  81, 123-124, 127-135, 139-140, 248-249, 251`。⚠️ 下面第 4/5/6 行认领了其中 13 行；**剩下的 `81` 刻意不在本 plan 结果面内**（见 `## Non-Goals` 末条），此处点名免得关闭审计留一行无主 |
| 4 | `123-124` 与 `127-135` **就是 `ComposeExecRunner` 的构造与整个 `__call__`** —— 产品路径上**唯一**的带外传输实现，零覆盖 | `awk 'NR>=123&&NR<=135' agenerp/oob.py`；§11.8 的落点表逐字写着「可注入的执行接缝：单测喂假件，**产品走 `docker compose exec -T`**」 |
| 5 | `139-140` 是 `default_compose_file()` 的整个函数体 | 同上；`AGENERP_OOB_COMPOSE_FILE` 的覆盖行为零判据 |
| 6 | `248-249` / `251` 是 `read_site_config` 的两条失败出口（载荷不是 JSON / 载荷不是对象） | `read_site_config` 是 **DDL 拿库名的唯一来源**（模块头与 §11.8 逐字） |
| 7 | 既有 `tests/unit/test_schema_drift.py` 21 条**全部喂假 `Runner`**，因此一条也验不到真传输 | `grep -n "ComposeExecRunner" tests/` → 只有 `tests/unit/test_apply_execute.py:104` 把它整体 `monkeypatch` 掉 |
| 8 | **将发生的 owner-doc 漂移，且是复发性的**：`docs/context/project-context.md` 在 **`:53` 与 `:57` 两处**把 `tests/unit` 的活计数记作 `**320 条**`，`:57` 还把它列为一条具名**代偿控制** | `grep -n "320" docs/context/project-context.md` → 命中 `:53` `:57`；`:53` 自述已被就地改准过三次（`283 → 288 → 293 → 320`）。⚠️ **本批第一个 plan `1056-1` 会先把它改准一次，本 plan 再推一次** —— 两个 plan 各改各的那一次，**本 plan 不得因为「前一个 plan 刚改过」就跳过**。按 Minimum Rule 14 不降级，是 Phase 3 的 `Fix` 项 |

### 三条变异实测**完全隐形**（每条都跑 `python3 -m pytest tests/unit tests/contracts -q`，全部 `471 passed`）

| 变异 | 改法（改完立刻 `cp` 复原，`git diff --stat` 无输出） | 真实后果 |
|---|---|---|
| **B** | `ComposeExecRunner.__call__` 的 `raise OobError(…)` 换成 `return OobResult(0, "", "")` | **起不来的命令被伪装成「exit 0 + 空 stdout」** → `_run` 回 `""` → `run_json` 回 `FALSY_RESULT` → `schema_drift` 翻成 `()` → **docker 根本没跑，门禁读出「这个 DocType 上一条孤儿列都没有」**。这正是模块头第 1 条与 §11.8「不伪装成功」要挡的形状，而它**没有任何机械手段挡着** |
| **A** | argv 里的 `"-T"` 删掉 | 带 TTY 时 docker 往 stdout 混控制字符，JSON 解析随之失败 —— 模块 docstring 逐字把 `-T` 记为承重项，却无判据 |
| **C** | `default_compose_file()` 忽略 `AGENERP_OOB_COMPOSE_FILE`（恒返回默认路径） | 环境变量覆盖失效；§11.8 的「配置口径」表把它列为三个带默认值的变量之一 |

### 缺口的准确表述（不得夸大）

⚠️ **不得读成「`agenerp/oob.py` 没有覆盖」**：该模块的**白名单 / 收窄 / 参数钉死 / 哨兵翻译**四面判据扎实
（`tests/unit/test_schema_drift.py` 21 条，起草时实测变异「对调 `backend` / `db` 两个服务名默认值」
→ **`7 failed, 464 passed`**，有牙齿）。
**缺的只有一块：把注入的假件拔掉之后，产品路径那条真传输自己的行为。**
它此刻只被起了 docker 的 L2 门禁间接走到，而默认判定面（`GATE_VERIFY` / `gates-l1`）复跑不到那里。

## Goals

- 上表 **B / A / C 三条变异**，落地后各自至少被一条 `tests/unit` 断言**逐字点名**。
- `read_site_config` 的两条失败出口（载荷不是 JSON / 载荷不是对象）各有一条断言。
- 新增断言零 docker、零网络、零活站点，**每轮 `GATE_VERIFY` 都复跑得到**。

## Non-Goals

- **不改 `agenerp/oob.py` 的任何一行行为。** 不加 fail-closed、不加前置备份、不加列级取证 —— 那三档是 `docs/backlog/irreversible-ddl-has-no-code-level-precondition.md` 里的**人裁定题**，本 plan 不重开、不代人选。
- **不动 `ALLOWED_CALLS`**（放宽带外执行面要重划红线 7 的界线，见 §11.8）。
- **不碰 `tests/gates/**`**（红线 1）、**不碰 `.github/workflows/**`**（红线 2）、**不碰 `missions/**`**、**不碰 `tools/gates/expected-red.txt`**。
- 不真起 docker、不真发任何 DDL、不连任何站点。
- 不处置 `agenerp/site.py` 的同类缺口 —— 那是本批第一个 plan `2026-08-23-1056-1` 的结果面。
- 不引入覆盖率阈值门槛。
- **不覆盖 `agenerp/oob.py:81`**（`_FalsyResult.__repr__` 的 `return "FALSY_RESULT"`）：它只影响错误信息的可读性，**不参与任何判定分支**。本 plan 落地后它将是该模块唯一剩下的未覆盖行，**照实点名，不假装已清零**。

## Task Route

- Type: `verification or audit work`
- Owner Docs: `docs/architecture/module-boundaries.md` §11.8（带外传输的落点、三个 exec 目标、配置口径、与红线 7 的界线）· `docs/context/ai-autonomy-policy.md` Protected Areas · `docs/context/project-context.md`（`:53` / `:57` 两处 `tests/unit` 活计数 —— Baseline 8 的确认漂移，Phase 3 的 `Fix` 项）· `docs/architecture/system-baseline.md`（本 plan 的口径落 §14.x —— **规则只有一条：开工时实读 `grep '^## 14\.' docs/architecture/system-baseline.md`，取下一个空编号**。起草时实测最大为 §14.10，本批第一个 plan 预定 §14.11。**允许出现编号空洞，不允许编号冲突**）
- Skill Selection Basis: `none` —— 理由同本批第一个 plan。

### Protected Areas 自查（`drop_columns` 在「对活站点的破坏性写」那一行内，必须逐条应答）

- **独立草案评审 + 独立关闭审计**：本 plan 走完整流程。
- **实跑前后全量 `capture` 对照（差集必须只含本次探针）**：**不适用，且不伪造**。本 plan
  零 docker、零网络、零活站点、零 DDL（见 `## Non-Goals`），**不存在「前后」两个站点快照可对照**；
  `agenerp/oob.py` 一行未改。该条以「本 plan 的作用域内无对照对象」记，**不以「已做」记**；
  机械替代证据是 `git diff --numstat agenerp/oob.py` 无输出。
- **对不可逆性说话的 Required Evidence**：本 plan **零代码级前置/取证交付**。逐字声明——
  **站点侧的回滚仍然只能手工做**，手工前置命令原文是
  `docker compose exec -T backend bench --site frontend backup`（`docs/context/project-context.md:63`）。
  本 plan **不改变**这条现状，也**不宣称**改善了它。
- ⚠️ 本 plan 对 `drop_columns` **一个字节未改**，新增断言只覆盖它上游的 `read_site_config` 与传输层。

## Infrastructure And Config Prereqs

- 无。新增断言纯标准库；不装 docker、不起容器。
- 无数据迁移，无回滚脚本需求。

## Execution Plan

### Phase 1 — 真传输的行为判据（B / A / C）

Status: planned
Targets: `tests/unit/test_schema_drift.py`（或新建 `tests/unit/test_oob_transport.py`，由下面的 Decision 定）
Skill: `none`

- Item Types: `Decision | Add | Proof`
- Prereqs: 无

- [ ] **Decision 1：断言落在哪个文件。** 候选：(a) 追加进既有 `tests/unit/test_schema_drift.py`（该文件已是 `oob` 的判据主场，但它的模块 docstring 讲的是孤儿列巡检，传输判据挂进去会让文件名与内容错开）；(b) 新建 `tests/unit/test_oob_transport.py`（文件名与结果面一致，代价是本仓多一个测试文件）。写明选择与残余风险。
- [ ] **Decision 2：怎么把 `subprocess.run` 换成假件。** 候选：(a) `monkeypatch.setattr("agenerp.oob.subprocess.run", fake)`（不碰私有名，覆盖面精确）；(b) 注入一个自定义 `Runner`（**证明不了 `ComposeExecRunner` 本身**，等于绕开本 plan 的整个结果面 —— 明确排除）；(c) 真起 docker（`## Non-Goals` 已排除）。写明选择与残余风险。
- [ ] `ComposeExecRunner` 的 **argv 形状**判据：断言假件收到的 argv 逐字为 `["docker","compose","-f",<compose 文件>,"exec","-T",<service>, …]`，且 `-T` **紧跟在 `exec` 之后**。**变异 A 必须被这一条点名。**
- [ ] `ComposeExecRunner` 的**失败翻译**判据：`subprocess.run` 抛任意异常（含 `subprocess.TimeoutExpired`）时**必须抛 `OobError`**，且**绝不返回任何 `OobResult`**。再补一条**端到端方向**的断言：同一情形下 `schema_drift`/`run_json` 必须抛 `OobError`，**不得**回 `()`。**变异 B 必须被这两条点名。**
- [ ] `ComposeExecRunner` 的**非零退出不吞**判据：假件回 `returncode=1` 时 `__call__` 原样返回 `OobResult(1, …)`（翻译成异常是 `_run` 的职责，两层不得互相顶替）。
- [ ] `default_compose_file()` 判据：设 `AGENERP_OOB_COMPOSE_FILE=/tmp/x.yml` → 返回该路径；设成空串/纯空白 → 回落默认；不设 → 回落默认。**变异 C 必须被点名。**
- [ ] Proof：三条变异逐一施加，**每一条都走这四步，缺一步该条不算数**：
      (a) 施加后先 `git diff --numstat agenerp/oob.py`，**必须非空** —— 空则说明替换根本没落上，
      「471 passed」会与「变异隐形」长得一模一样（本批第一个 plan 的独立评审实测踩到过一次）；
      (b) 跑 `python3 -m pytest tests/unit -q`，记录**退出码 + 逐字的 `FAILED …::<用例名>` 行**；
      (c) `git checkout agenerp/oob.py` 复原；
      (d) 复原后 `git diff --stat agenerp/oob.py` **必须无输出**，**每条变异后各查一次**。
      **`agenerp/oob.py` 在被变异的状态下一次都不得提交。**

Exit Criteria:

- [ ] B / A / C 三条变异各自至少让一条新断言红，且红时输出逐字点名该用例
- [ ] 变异 B 的端到端方向也红（`schema_drift` 不再把「起不来」读成 `()`）
- [ ] `agenerp/oob.py` **一行未改**（`git diff --numstat agenerp/oob.py` 无输出）
- [ ] 两条 Decision 的候选、选择、残余风险已写进文件
- [ ] `docs/logs/2026/08-23.md` 追加条目

### Phase 2 — `read_site_config` 失败出口的行为判据

Status: planned
Targets: 与 Phase 1 同一文件
Skill: `none`

- Item Types: `Add | Proof`
- Prereqs: Phase 1（Decision 1 决定文件落点）

- [ ] 载荷不是 JSON（stdout 为 `not json` / 空串）→ 抛 `OobError`，消息含站点名。**必须实测变异「改成返回 `{}`」有牙齿。**
- [ ] 载荷是合法 JSON 但**不是对象**（`[]` / `"x"` / `3`）→ 抛 `OobError`，消息逐字含读到的类型名。
- [ ] 端到端方向：上述两种情形下 `drop_columns` **必须在发出任何 DDL 之前**抛 `OobError` —— 断言假件收到的命令列表里**没有**任何打到 `db` 服务的条目。⚠️ 这条是本 plan 唯一贴着不可逆写动作的判据，**它判的是「不发」，不是「发得对」**。
- [ ] Proof：两条变异（`read_site_config` 的两个 `raise` 各换成返回空 dict）**逐条走 Phase 1 Proof 那四步**（施加后 `numstat` 非空 → 跑并记退出码与 `FAILED …::<用例名>` 原文 → `git checkout` → `git diff --stat` 无输出）；两条跑完后整体回到 exit 0。

Exit Criteria:

- [ ] 两条失败出口各有断言，且各自的变异实测有牙齿
- [ ] 「库名读不出来时一条 DDL 都不发」有一条独立断言
- [ ] `agenerp/oob.py` 仍是一行未改
- [ ] `docs/logs/2026/08-23.md` 已更新

### Phase 3 — owner-doc 对齐与登记

Status: planned
Targets: `docs/architecture/system-baseline.md` · `docs/context/project-context.md` · `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md` · `docs/logs/2026/08-23.md`
Skill: `none`

- Item Types: `Fix | Add`（`Fix` 项是 Baseline 8 的确认 owner-doc 漂移，Minimum Rule 14 不降级。⚠️ **若 §11.8 实读发现措辞与代码有出入，那一项也按 Rule 14 升级为 `Fix`**；起草时实读 §11.8 该行为准确，改准分支预期不触发）
- Prereqs: Phase 1、Phase 2

- [ ] **`Fix`** —— `docs/context/project-context.md` 的 `:53` 与 `:57` **两处** `tests/unit` 活计数就地改准为**本 plan 落地后**当次 `python3 -m pytest tests/unit -q` 的实测通过数，并按该文件既有写法追加一句改准出处（指向本 plan）。⚠️ **两处都要改**：只改一处会让同一份文件对同一个量给出两个读数，本仓已有一次同形态事故留痕（`STATE.md:86`）。⚠️ **不因 `1056-1` 刚改过而跳过**。
- [ ] `system-baseline.md` 新增一节（**开工时实读取下一个空编号**，起草时最大为 §14.10、本批第一个 plan 预定 §14.11），记：缺口原文、五条变异的实测退出码、**以及「本 plan 只加判据、`agenerp/oob.py` 零行为改动、`ALLOWED_CALLS` 一字未动」这条限定**。
- [ ] `p0-foundation-roadmap.md` **纯追加**一行 `9 现状 · …`（不改写既有任何一行），逐字写明：**这是判据设施的加严，不是工作项 9 `done` 判据的替换**；**所有工作项状态值一个字不改**。
- [ ] `STATE.md` §2 **追加**一行证据（命令原文 + 退出码 + sha），不改写已有行（红线 5）。
- [ ] `module-boundaries.md` §11.8 的落点表里 `Runner` / `ComposeExecRunner` 那一行**只在「状态」列补一句判据出处**（纯追加，不改写既有措辞）；若实读发现该行措辞与代码有出入，按 Minimum Rule 14 就地改准并在本项记录原文。

Exit Criteria:

- [ ] 新增小节编号与既有不冲突
- [ ] `grep -n "320 条" docs/context/project-context.md` **零命中**，且 `:53` / `:57` 两处的数与当次 `python3 -m pytest tests/unit -q` 的通过数逐字相同
- [ ] roadmap 与 `STATE.md` 的 `git diff --numstat` 删除列均为 `0`
- [ ] `git diff --numstat docs/architecture/module-boundaries.md` 删除列为 `0`；**若走了 Minimum Rule 14 的就地改准分支，删除列可非 0，但必须在该项里逐字记下被改的原文与改后原文** —— 两条分支必须二选一地留痕，不得两条都不写
- [ ] `python3 -m ruff check agenerp tests/unit tests/contracts` → exit 0
- [ ] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0

## Draft Review Record

- Independent draft review iteration 1: **acceptable as-is with noted nits**（独立子代理，fresh session；`agentId a9e63b36b8fe1356f`）—— 评审**逐条复跑**了全部 Baseline 与三条变异，结论与本文记录**逐字相符**（`320` / `151` / 覆盖率 `108 14 87% 81, 123-124, 127-135, 139-140, 248-249, 251` 逐字节相同；A / B / C 各 `471 passed`；服务名对调 `7 failed, 464 passed` 且首条点名 `test_drop_columns_does_not_share_the_bench_allowlist`），**零 blocking**。三条独立确认：① **变异 B 的因果链是真的、且比本文写得更强** —— 评审逐行核到 `_run` → `run_json:213` `if not stdout.strip(): return FALSY_RESULT` → `agenerp/snapshot.py:351` `if columns is FALSY_RESULT: return ()`，并指出健康栈上的 `subprocess.TimeoutExpired` 同样会被洗成「零孤儿列」，`drop_orphan_columns` 随之静默空转；② **Phase 2 的 `drop_columns` 那一项钉的是既有行为，不是新增前置** —— `agenerp/oob.py:280-299` 的顺序是「空集 → 标识符校验 → 读库名 → 才发 `db` 命令」，`read_site_config` 抛错在任何 db 命令被构造之前就传播出去；因此**不重开** `irreversible-ddl-has-no-code-level-precondition.md` 的人裁定，该 backlog 的两条硬拦（新门禁要 trailer、`1922-3` 的已裁定状态）均未被触碰；③ **Minimum Rule 4 判「不拆」** —— 两个 Phase 共用一份 Closure Gates、一组验证命令、一个目标文件、一条关闭谓词。六条 nit：M1 Protected Areas 四条 Required Evidence 只答了三条（`实跑前后全量 capture 对照` 缺席，而本 plan 自己的 Closure Gate 写着「已逐条应答」）· M2 §11.8 那一项同时含「纯追加」承诺与「就地改准」逃生口却无对应 Exit 检查 · M3 两处行号锚点错（`missions:18→16` / `project-context:60→63`，**引文逐字正确**；`:60` 是从 backlog 文件继承来的错，跨本批两个 plan 传播）· M4 Baseline 列了 `81` 却在随后三行里把它漏掉，落地后会是唯一无主的未覆盖行 · M5 §14.12 的写法与「取下一个空编号」自相矛盾 · M6 Phase 3 的 `Item Types: Add` 盖不住它自己的条件式 `Fix` 分支。
- Independent draft review iteration 2: **accept**（独立子代理，fresh session；`agentId a1b000edc0bb75088`）—— 评审逐条复核六条 nit 与两条跨 plan 采纳项**全部落实**，独立重跑了 Baseline（`320` / `151`、`test_schema_drift.py` 21 条、`grep -rn ComposeExecRunner tests/` 只命中 `test_apply_execute.py:104`）与**变异 B**：`git diff --numstat agenerp/oob.py` → `1	1`（**确认变异真的落上了**）→ `python3 -m pytest tests/unit tests/contracts -q` → **exit 0，`471 passed`**（完全隐形）→ `git checkout` 后 `git diff --stat` 无输出。评审另给一条**比变异更强的结构性证明**：覆盖率逐字节复现 `108 14 87% 81, 123-124, 127-135, 139-140, 248-249, 251`，即 `127-135` / `139-140` **从未被 `tests/unit` 执行过**，因此变异 A 与 C 是**可证明**不可见，不只是「实测没被发现」。红线自查全过；确认 Phase 2 的 `drop_columns` 那一项钉的是既有行为、**不重开** `irreversible-ddl-has-no-code-level-precondition.md`（三条重开触发条件均未被触碰）；无过度宣称。**零 blocking、零遗留 findings。** 评审另记两处「看了但判定不是缺陷」：Phase 3 无独立 `docs/logs/` Exit（Minimum Rule 9 允许聚合条目，且 Phase 1/2 已各要求追加、Closure Gate 亦覆盖）；`grep "320 条" 零命中` 在姊妹 plan 先落地后会空转（但同一判据的第二半「两处等于当次实测通过数」仍然咬得住）。
- 收敛结论：**两轮独立评审已收敛**（iteration 1 `acceptable as-is with noted nits` → 六条修毕；iteration 2 `accept`，零遗留），`Plan Status` 由 `draft` 置 `active`。
- （iteration 1 的修订记录）六条 nit 已全部就地修订（M1 补第三条应答并加 Closure Gate；M2 加 `numstat` 双分支留痕判据；M3 两处锚点已实读改准；M4 在 Baseline 与 Non-Goals 两处点名 `81`；M5 改成单一规则「实读取下一个空编号，允许空洞不允许冲突」；M6 Phase 3 类型改 `Fix | Add`）。**另外跨 plan 采纳了姊妹 plan `1056-1` 评审的两条**：① `docs/context/project-context.md` `:53` / `:57` 的复发性计数漂移升为 Phase 3 的 `Fix` 项（Rule 14 不降级，本 plan 起草时**漏了**它，照实记）；② 变异协议补上「先确认变异真的落上了」那一步。

## Closure Gates

- [ ] in-scope behavior is complete（五条变异全部有牙齿）
- [ ] relevant docs are aligned（新小节 + roadmap 追加行 + STATE 追加行 + §11.8 状态列 + 日志）
- [ ] verification has run：`python3 -m pytest tests/unit -q` · `python3 -m pytest tests/contracts -q` · `python3 -m ruff check agenerp tests/unit tests/contracts` · `python3 tools/gates/check_expected_red.py`，四条各记退出码
- [ ] scoped verification is not conflated with full verification —— **本 plan 零 CI 轮次消耗、零 docker、零活站点**，因此**不得宣称任何 CI 侧或 live 侧结论**；「verification scope limited」须逐字写进关闭记录
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] Protected Areas 的「对活站点的破坏性写」Required Evidence **四条逐条应答**：①独立草案评审 ②独立关闭审计 ③**实跑前后全量 `capture` 对照 —— 本 plan 作用域内无对照对象**（零活站点、零 DDL、`agenerp/oob.py` 零改动，`git diff --numstat agenerp/oob.py` 无输出为替代证据；**不以「已做」记**）④「站点侧回滚仍只能手工做」那句原文已在 plan 内

## Deferred But Adjudicated

### 假件证明不了「真的 docker 会那样答」

- Classification: `watch-only residual`（**本 plan 自己的方法论上限，登记而不消除**）
- Why Not Blocking Closure: 本 plan 判的是 `ComposeExecRunner` **拼出什么 argv、把失败翻成什么**，
  判不了 `docker compose` 自己的行为。⚠️ **不得写成「带外传输已被端到端验证」** ——
  端到端那一半仍然只有起了 docker 的 L2 门禁看得见，而默认判定面复跑不到它。
  造一个默认判定面上的真 docker 判据要引入一条新的 CI/本机依赖，是独立的结果面。
- Successor Required: `no`
- 重开事件：**人裁定给本仓引入「默认判定面可跑的容器级判据」时**，或**真传输第一次在活站点上给出与本 plan 断言不一致的行为时**。

### `agenerp/oob.py` 的代码级破坏性写前置仍然没有

- Classification: `watch-only residual`
- Why Not Blocking Closure: 人裁定题（`docs/backlog/irreversible-ddl-has-no-code-level-precondition.md`）。本 plan 的 Phase 2 只交付「库名读不出来时一条 DDL 都不发」这一条**既有行为的判据**，⚠️ **不是**新增前置，**不得**被读成缺口已补。
- Successor Required: `no`（**人动作**）
- 重开事件：见该 backlog 条目写死的三条触发条件。

### `tools/**` 与全部 shell 仍零静态检查、`tests/unit` 仍无棘轮

- Classification: `watch-only residual`（`0859-1` / `0859-2` 已登记，本 plan 继续挂着）
- Why Not Blocking Closure: 前者是 `docs/backlog/tools-dir-has-no-static-check-coverage.md` 的人裁定题；后者红线 1 只圈 `tests/gates/**`，本 plan 新增的断言同样可被合法删掉，CI 只会看到 `passed` 计数变小。
- Successor Required: `no`
- 重开事件：各自 backlog / 前驱 plan 写死的条件，本 plan 不重裁。

### 结果与预测不符时的固定处置（写死，不临场决定）

- Classification: `watch-only residual`（失败分支的写死处置，不是被推迟的工作项）
- 处置逐字：原样复跑一次（裁判规则 3）→ 仍不符则记录所有已跑命令与输出原文 → 追加进 `docs/masterplan/STATE.md` §3（**只追加，不改写既有行**）→ **不放宽任何断言**、**不改 `agenerp/oob.py` 去迁就断言**、**不动 `ALLOWED_CALLS`**、**不改 `tests/gates/**` 与 `.github/workflows/**`**、**不猜根因** → 本 plan 置 `deferred` 并在文件头写明重开条件。
- Successor Required: `no`
- 重开事件：**人裁定继续**，或不符之因被一个独立 plan 查清之后。

## Closure

Status Note: <pending>

Closure Audit Evidence:

- Auditor / Agent: <pending>
- Evidence: <pending>
