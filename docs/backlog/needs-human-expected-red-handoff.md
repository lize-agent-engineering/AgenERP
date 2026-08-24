# needs-human · 四组交接（EXPECTED_RED 权属 · 后果链 · 划名单时机 · 状态账本漂移）

> Created: 2026-08-20
> Raised by: `docs/plans/p0-foundation/2026-08-20-2341-1-agenerp-package-skeleton.md` Phase 3
> Status: `open` —— 每一组都**只有人能决**。loop 不得自行处置，也不得据此改任何红线内文件。
> 规则：下面每条冲突都写「谁说的 + 原文出处 + 与谁矛盾」，**不写结论式转述**。
> 引用的行号是 2026-08-20 在 `69b7f30` 上的实测位置，文件变动后请以章节名为准。

---

## 冲突 1 · 谁有权改 `tests/gates/EXPECTED_RED.txt`（四方，不是两方）

### 要求 loop 去改的（三处，全都活着、每轮都被读到）

**(i) `missions/prompts/build-verify.md`** —— 这份 prompt 就是 `BUILD_VERIFY` 步下发给执行器的正文。

- `:63-64`，「提交策略」步骤 c，原文：

  > c. **若本轮让某条门禁测试转绿**：把它从 `tests/gates/EXPECTED_RED.txt` 删掉，**并入代码提交**。
  >    名单只能变短——CI 的棘轮 job 盯着这件事，变长会被拦下。

- 同一文件 `:9-11`，「这个项目的语境」第 1 条又重复了一次：

  > 名单内**绿** = 名单过期，实现已到位，你必须**在同一个提交里**把它从名单划掉

**(ii) `tools/gates/check_expected_red.py:78`** —— 判定器自己的输出：

> `print("\n❌ 名单内的门禁却绿了 —— 实现已到位，请在同一个提交里把它从 EXPECTED_RED.txt 划掉：")`

**(iii) `tools/gates/gate-verify.mjs:110-122`** —— 失败时把上面这段**真实 stdout** 装进 `fail()` 的 `details`
（`:117-118` 的「真实输出：」+ `r.output`），由引擎 append 进下一轮 `EXECUTE` 的 prompt。
也就是说 (ii) 的措辞会被原样回灌给执行器当指令读。

### 禁止 loop 去改的（三处）

- **`AGENTS.md` 红线 1**（§🚫 红线 表第 1 行）：

  > 不得以任何方式修改 `tests/gates/**` —— 包括改断言、加 skip/xfail、改 fixture 使其变松、删文件、改文件名
  > …… `git diff` 触及该路径 → **立即停机**，标 needs-human

- **`tests/gates/EXPECTED_RED.txt:12`**（文件头自述）：`⚠️ 本文件在 tests/gates/** 红线内，loop 不得修改。`

- **`.github/workflows/gates.yml`** 的 `gates-untouched` job（`:16-48`）：`git diff --name-only` 命中 `tests/gates/**`
  且提交信息里没有 `^Gates-Change-Approved-By:` trailer → `exit 1`（`:45-48`）。
  另有 `expected-red-ratchet` job（`:50-85`）拦「名单变长」。

### 当前处置与仍待人决的部分

按 `AGENTS.md` 开头声明的次序（红线 > `docs/masterplan/` 执行协议 > `AGENTS.md` 其余 > 上游模板默认），
**红线胜出**。plans 2/3 据此不改 `EXPECTED_RED.txt`。

但 (i) 是**项目侧自己写的 prompt**，不是上游模板默认——它与红线的矛盾**不在那条优先级次序能消解的范围内**，只能由人消。

附注：`missions/prompts/build-verify.md` **不是** `missions/*.json`，不在
`docs/masterplan/01-EXECUTION-MODEL.md` §1 角色 B 禁止项 ③ 的字面范围内。plan 1 仍不动它——
改执行器每轮读的行为指令属于改控制面，超出「建包骨架」的授权。这正是交给人的第一个决定。

---

## 冲突 2 · 后果链要说准（实测校正，别照抄文档说法）

**文档说法**：`AGENTS.md` §⚖️ 裁判规则 第 4 条：

> **停机条件**（任一触发即停，宁可停不带病跑）：同一 plan 连续 3 轮 `GATE_VERIFY` fail｜`git diff` 触及 `tests/gates/**`｜单 mission 累计成本超阈值｜CI 连续 2 轮红。

**实测链条**（逐个文件读出来的，不是推测）：

1. 实现正确 → 对应门禁转绿 → `tools/gates/check_expected_red.py:61,82-83` 判 `unexpected_green` → **exit 1**
2. `tools/gates/gate-verify.mjs:102-124` 复跑 `commands.test` 拿到非 0 → 返回 `{ marker: "fail" }`
3. `tools/mission-driver/flows/plan-execution.json:103-106`：`GATE_VERIFY.transitions.fail` → `{"retry": "EXECUTE", "maxRetries": 3}`
4. 同文件 `:111-113`：`onMaxRetries` → `{"done": "failed"}` —— 这**只是该 plan 子流程的终局**
5. `tools/mission-driver/flows/mission-driver.json:52-57`：`EXEC_PLANS` 把 `all_complete` / `some_failed` / `all_failed` **一律** `goto DRAFT_PLANS`

也就是说：**不停机、不落 `.mission-halt.json`、不自动写 STATE。**
`AGENTS.md` 裁判规则 4 里的「同一 plan 连续 3 轮 `GATE_VERIFY` fail → 停机」是**纸面规定，没有实现**。
（对照：同规则里的「`git diff` 触及 `tests/gates/**`」**是**实现了的——`gate-verify.mjs:59-99` 走独立
marker `halt`、写 `.mission-halt.json`、`process.exit(2)`。两者待遇不同。）

**更贵的一层**：plan 若仍是 `active`，`tools/mission-driver/src/flow-loader.js:157-159` 的 `activePlans()`
（`ACTIVE_STATUSES` 在 `:19-30`，含 `active` / `planned`）**下一轮还会再选中它**，把已完成的活重跑一遍——
按 `missions/p0-foundation.json` `_notes.budget` 记录的 W0.0 实测（一个完整循环 ≈ 5–8 步、约 160 万输入 token），
到 `maxTotalSteps: 120` 烧光为止。

plans 2/3 因此在收尾时把自己置为 `deferred`：该值既不在 `ACTIVE_STATUSES`（`flow-loader.js:19-30`）
也不在 `DRAFT_STATUSES`（`:31-38`），是**唯一能让 plan 停下来等人**的状态。

**处置项（人选一）**：

- (A) 补实现，让「连续 3 轮 fail」真的停机，使 `AGENTS.md` 规则 4 与代码一致。
- (B) 维持现状 + 靠 plan 自置 `deferred`；同时把 `AGENTS.md` 规则 4 那一句标注为「未实现」，免得下一个会话再被它误导。

---

## 冲突 3 · 划名单的时机（四选一）

- **(a) 维持现状**：实现落地后，由人补一次带 `Gates-Change-Approved-By:` trailer 的划名单提交。
- **(b) ~~开工前预先划掉~~ —— 实测不成立，此选项作废。**
  理由：测试此刻还是红的。一旦不在名单里，`check_expected_red.py:60` 会把它算作 `unexpected_red`
  （`:72-75` 打印「名单外的门禁红了（真的坏了）」）并 `return 1`，等于让整个工作项**从第一轮就红**。
  留在文档里是为了记住它为什么不行，别再被重新提出来。
- **(c) 改判定机制**（例如让判定器接受「已实现待划名单」的中间态）—— 属**放松裁判**，须人批。
- **(d) 把 plan 关闭与划名单解耦**：plan 以自己的判据关闭（直接跑那几条门禁 → exit 0，且 `pytest tests/unit -q` 绿），
  划名单登记为人的后继动作。这一条是独立评审提出、本批 plan **未采用**的选项，一并交给人。

---

## 冲突 4 · 状态账本自身的两处漂移 + 一处过时注释

### 4.1 `STATE.md` §1 的 ID 与名字对不上

`docs/masterplan/STATE.md:15`：

> \| **下一个未阻塞工作项** \| **P0.1 · 定制包规范化器**（Day 0 出口门禁四项已全绿）…… \|

但 `docs/masterplan/02-WBS.md:63,66`：

> \| P0.1 \| 零依赖启动（compose 语法修法） \| Day 0 出口 \| 🔴 `tests/gates/test_zero_dep_boot.py` \| …
> \| P0.4 \| 定制包规范化器（剥离 `modified`/`creation`/`owner`/`_comments` 并稳定排序） \| P0.3 \| 🔴 `tests/gates/test_normalizer_idempotent.py` \| …

名字对，**ID 错**：P0.1 是零依赖启动，P0.4 才是规范化器。

为什么会一直烂着不报：`tools/check-state-consistency.sh:21-26` 只校验「抽出的 ID 存在于 WBS 表」
（`grep -E "^\| *\*{0,2}${esc}\*{0,2} *\|" 02-WBS.md`），**不校验 ID 与名字相符**。

⚠️ `docs/masterplan/**` 在红线 5 内，loop 只能追加证据行、不得改写已有行。**这一处必须由人改。**

### 4.2 `02-WBS.md` 与 `p0-foundation-roadmap.md` 执行顺序相反

- `02-WBS.md:65-66`：P0.3（状态快照与 diff，前置 **P0.2 工具契约层 v0**）→ P0.4（定制包规范化器，前置 P0.3）
- `docs/backlog/p0-foundation-roadmap.md:20-21` 且 `:18` 明说「前三项是纯逻辑，不需要活站点或 docker，先做」：
  1. 定制包规范化器 → 2. 状态快照与结构化 diff

引擎取的是 roadmap（`missions/p0-foundation.json:10` 的 `"roadmapPath": "docs/backlog/p0-foundation-roadmap.md"`），
本批 plan 也按 roadmap 排序。**WBS 那张表的前置与顺序需要人来对齐**（尤其 P0.3 前置写着 P0.2 工具契约层，
而 roadmap 认为快照 diff 是纯逻辑、不需要活站点）。

### 4.3 `missions/p0-foundation.json` 的 `_notes.commands` 已过时

原文（`:23`）：

> 只列现在真跑得起来的。**本机 ruff / mypy / docker 都还没有**，写进去等于每个 plan 一开局就 fail ……

2026-08-20 本机实测：

- `which ruff` → `/Library/Frameworks/Python.framework/Versions/3.12/bin/ruff`（**在**）
- `which docker` → `/usr/local/bin/docker`（**在**）
- `which mypy` → 未命中（确实不在）

这是注释与事实的漂移，不影响任何可执行判据；且 `missions/*.json` 在角色 B 禁区内
（`01-EXECUTION-MODEL.md` §1 禁止项 ③），loop 不改。人下次编辑该 mission 文件时顺手修正即可。

顺带：plan 1 已把 `[tool.ruff]` 配置落盘（`pyproject.toml`）并把 `ruff check agenerp tests/unit`
写进 `docs/context/project-context.md` 的验证命令表。**把 lint 接进 `missions.commands` 由人做。**
