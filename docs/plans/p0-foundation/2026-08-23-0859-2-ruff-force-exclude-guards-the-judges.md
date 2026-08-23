# 2026-08-23-0859-2 `[tool.ruff] exclude` 挡不住显式路径 —— 让「lint 不许逼着去改裁判」这句注释真的成立

> Plan Status: active
> Mission: p0-foundation
> Work Item: 工作项 9 · L2 门禁的判定与 CI 覆盖（**判据设施**那一半 —— 本 plan 不改工作项 9 的 `done` 判据，也不改任何工作项的状态值）
> Last Reviewed: 2026-08-23
> Source: 实测 —— `pyproject.toml` 的 `[tool.ruff] exclude = ["tests/gates"]` 只在**目录遍历**时生效；
> 显式传路径（`ruff check tests/gates`）会**照样扫裁判目录**并报出 2 条告警，
> 即那段注释「把它排除在 lint 作用域外，免得 lint 逼着去改裁判」**在字面上不成立**（确认的契约/实现漂移）
> Related: `2026-08-23-0859-1-budget-halt-gate-verdict-coverage.md`（本批第一个 plan，**前驱**）·
> `2026-08-23-0337-1-ci-seed-selfverify-and-lint-coverage.md`（建立 `lint` job 的那个 plan）·
> `2026-08-22-0228-1-gate-verdict-failure-forensics.md`（其评审记录 **M2** 已裁定「`tools/**` 明确不扩面」——
> 本 plan 尊重该裁定，见 `## Non-Goals`）
> Audit: required
> 执行顺序：**2 / 2**。与前驱的**代码改动面**零重叠（前驱不动 `pyproject.toml`，本 plan 不动 `tools/**` 与 `tests/unit/**`）。
> ⚠️ **不是「零重叠」** —— 两个 plan 都会写 `docs/architecture/system-baseline.md`、
> `docs/masterplan/STATE.md` 与 `docs/logs/`，只是各写各的**追加**段。措辞按独立评审第 2 轮改准。
>
> ⚠️ **本 plan 已被独立草案评审整体收窄一次，收窄记录见 `## Scope Change Record`** ——
> 初稿名为 `ci-lint-scope-tools`，要新增第 15 个 CI job 把 `tools/**` 纳入 lint 作用域；
> 该 scope 已**整体移出**，理由与去处逐条落纸，**不是静默删除**。

## Scope Change Record

**2026-08-23，草案评审第 1 轮，独立子代理（fresh session）判 `should be dropped or fundamentally rescoped`。
本 plan 接受该结论并整体收窄。** 按 `docs/plans/00-plan-authoring-and-execution-guide.md` Minimum Rule 10
（「Scope narrowing after plan approval is a scope change and must be recorded with rationale；
silently removing items from scope is a violation」），逐条记明：

| 移出的 scope | 移出理由（评审的证据，不是我方的说辞） | 去处 |
|---|---|---|
| 新增第 15 个 job 把 `tools/**` 纳入 lint | `2026-08-22-0228-1` 的评审记录 **M2 就同一处裁定过「明确不扩面，避免把顺手优化拖进来」**，初稿既未引用也未反驳（Minimum Rule 1 要求盘点被抵触的既有裁定） | `docs/backlog/`（Phase 2 落纸），交人裁定 |
| 修 `tools/**` 的 9 条 ruff 告警 | 全是 `F541` / `E401` / `E741` 文体项；且实测 `tools/rotate-state.py` **全仓零调用方**、`tools/bootstrap/homepage_notice.py` 只被 `docker-compose.yml` 的 bootstrap 服务用、`tools/gates/explain_last_gate_failures.py` 已被 `tests/unit/test_gate_verdict.py` 导入测过 —— 前驱 plan 覆盖掉那两个真在循环里的文件之后，增量购买力接近零 | 同上 |
| 4 次 CI 变异实验 | 其中变异 ③（拿掉 `force-exclude` 再让某 job 显式扫 `tests/gates`）**同时改两处**，红了也隔离不出原因；且它验的那个配置**在 `main` 上永不存在**。而它要证的事，**Baseline 2 第三条**已在本机以零成本、带退出码与逐字输出证完 | 删除；`force-exclude` 无 CI 级证伪面这一点**照实写进本 plan 的 §14 小节** |
| 初稿 Baseline 4 的价值论证 | 其核心引用「`tools/**` 是无人值守时唯一还醒着的那套东西（`loop-supervisor.sh` 模块头**逐字**）」**不是逐字** —— 原文是「7×24 监督器 —— 无人值守时唯一还醒着的东西」，主语是**监督器**，「那套」是加上去的 | 整段删除 |

**保留下来的只有一件事**，也是评审逐字建议保留的那件：`force-exclude`。
它是**确认的契约/实现漂移**（Minimum Rule 14 不得降级），触及**零个**受保护文件，
消耗**零轮** CI，且它关的是一个此刻就在的活隐患。

## D0 — 这件事够不够格立一个 plan（独立评审第 2 轮提出异议，此处当面裁定）

**评审的意见逐字**：收窄之后的交付「是一次 trivial local edit —— 一个文件里的一行配置加一句注释改写，
对任何已交付命令零行为改变，零 CI」，按 Plan Decision Table 属 `No plan` 那一行，
「344 行 plan 配一行配置改动，不成比例」。**该意见照实记，不淡化。**

**裁定：保留 plan 形态。三条理由，都可核：**

1. **交付面不是「一行配置」**。Baseline 4 盘出**同一句不成立的话在仓里有三处**；
   本 plan 就地改准两处（`pyproject.toml` + `docs/context/project-context.md`）、登记一处（`gates.yml`），
   另交付一个新的 backlog 条目与两处追加。
   ⚠️ **此处不做转述式引用**（独立评审第 3 / 4 轮连续抓出初稿把表里的例子写成了
   「simple local bug fix + docs update」，那是两条例子拼出来的，**不是原文** ——
   而本 plan 恰恰因为同类毛病删掉过一整块 scope，自己更不能犯）。
   `docs/plans/00-plan-authoring-and-execution-guide.md:23` 那一行的例子逐字是
   「small UI polish with docs/test update」与「simple local bug fix with clear existing test」，
   **本 plan 与后者同类**（一处确认漂移的 `Fix` + owner-doc 落纸）。
   两条更强的引用同样逐字可核：Decision Table 第三行 **Full plan** 的触发条件里列着
   **`stale-doc conflict`**；指南「When To Write A Plan」列着
   **`modifies more than 5 total files`** —— 本 plan 的交付面是 6 个文件
   （`pyproject.toml` · `project-context.md` · `system-baseline.md` · 新 backlog 文件 ·
   roadmap · `STATE.md`），**直接命中**。
2. **它改的是一层守卫的效力，而那层守卫护的是红线 1 的裁判面**。
   Decision Table 末句逐字「If unsure, use a full plan」。
3. **它引入了一处新的假绿形态**（D1 残余风险二：显式请求被静默判绿）。
   引入假绿的改动**必须**留下独立评审与独立关闭审计的记录，而 `Audit: required` 这套机制
   **只挂在 plan 文件上**，这正是 plan 形态在买的东西。
4. **（独立评审第 3 轮补的一条，本稿采纳）** Minimum Rule 10 要求 `## Scope Change Record` 留存 ——
   **撤掉 plan 形态就等于把那份「曾经想做什么、为什么不做了」的记录一起删掉。**

**代价照实记**：本文件确实比它的代码改动长一个量级。**不辩解**——
其中大部分长度是 `## Scope Change Record` 与两轮评审记录，
即「这个 plan 曾经想做什么、为什么不做了」的留痕，那部分不会随交付面缩小。

## Current Baseline

全部为 2026-08-23 在 `main`（`6001ea0ae15cf3c84cc1bca19f138a738a50a7fc`）上的实读与实跑；
上述每一条都经**独立草案评审**复跑核对过一次（评审报告逐项标 ✅）。

1. **`pyproject.toml` 的 `[tool.ruff]` 现状**（`:24-29`，**引全，不截断**）：

   ```
   [tool.ruff]
   line-length = 100
   target-version = "py312"
   # tests/gates/** 在红线内，loop 不得修改；把它排除在 lint 作用域外，
   # 免得 lint 逼着去改裁判。门禁判定器是 tools/gates/check_expected_red.py，与 ruff 无关。
   exclude = ["tests/gates"]
   ```

   ⚠️ **第二行注释的后半句「门禁判定器是 `tools/gates/check_expected_red.py`，与 ruff 无关」
   在本 plan 收窄之后仍然为真**（本 plan 不把判定器纳入任何 lint 作用域），因此**不改它**。
   初稿要改它，是因为初稿会让它变假 —— 那个 scope 已移出。

2. **前半句不成立，实测三条**：
   - `python3 -m ruff check .` → 输出里 `tests/gates` 命中数 **0**（目录遍历时 `exclude` 生效）；
   - `python3 -m ruff check tests/gates --output-format=concise` → **exit 1，2 条**：
     `tests/gates/conftest.py:29:8: F401 `time` imported but unused` ·
     `tests/gates/test_customization_roundtrip_delete.py:39:39: E741 Ambiguous variable name: `l``
     —— **显式路径绕过了 `exclude`**；
   - `python3 -m ruff check tests/gates --config 'force-exclude = true'` → **exit 0**，逐字
     `warning: No Python files found under the given path(s)` / `All checks passed!`。

3. **隐患是具体的，不是理论的。** 那 2 条告警**此刻就在**，而 `tests/gates/**` 是红线 1 的裁判面
   （loop 一个字节都不许改）。既有 `lint` job（`.github/workflows/gates.yml:426`）的判据 step 是
   **显式列目录**的 `ruff check agenerp tests/unit tests/contracts`；
   下一个把 `.` 或 `tests/gates` 写进那一行的人，会当场拿到两条**只有改裁判才能变绿**的告警。
   ⚠️ **本 plan 不修那 2 条告警**（红线 1），只让它们**扫不到** —— 见 `## Non-Goals`。

4. **同一句不成立的话在仓里有三处，逐条盘点**（Minimum Rule 1；独立评审第 2 轮指出初稿只盘了一处）：

   | # | 位置 | 原文（节录） | 本 plan 的处置 |
   |---|---|---|---|
   | ① | `pyproject.toml:27-28` | 「把它排除在 lint 作用域外，免得 lint 逼着去改裁判」 | **就地改准**（Phase 1） |
   | ② | `docs/context/project-context.md:69-70` | 「`tests/gates/**` 已按红线 1 排除在 lint 作用域外（`pyproject.toml` 的 `[tool.ruff].exclude`）」 | **就地改准**（Phase 1）—— 它是本 plan 的 owner doc 之一，可自由编辑 |
   | ③ | `.github/workflows/gates.yml:437-439` | 「不扩到 `tests/gates`（`pyproject.toml` 的 `[tool.ruff] exclude` 已排除它，理由是免得 lint 逼着去改裁判）」 | **不改，登记交人** —— `.github/workflows/**` 是红线 2 的 `blocked` 面，且本 plan 的整个价值就在于「零 CI 消耗」，为一句注释去重摆授权面不划算。见 `## Deferred But Adjudicated` |

   ⚠️ **三处同因**：都把 `exclude` 的效力说成了「排除在 lint 作用域外」，而 Baseline 2 实测它只在目录遍历时成立。
   ⚠️ **`force-exclude` 落地后 ③ 会从「不准确」变成「准确但不完整」**（那时确实排除得掉了，
   只是它不知道是靠 `force-exclude`），**这是弱化不是加剧**，照实记。

5. **`force-exclude = true` 对既有作用域零副作用**（独立评审复跑并额外做了隔离 A/B 确认）：
   `ruff check .` 命中数 9 → 9 · `ruff check agenerp tests/unit tests/contracts` 仍 exit 0 ·
   `ruff check tools` 仍 9 条。对 `tests/gates/conftest.py`（单文件）、`./tests/gates`（带前缀）
   与绝对路径三种写法均生效。

6. **授权面（逐条实读）**：`pyproject.toml` **不在** `docs/context/ai-autonomy-policy.md`
   的 Protected Areas 表内，也**不在** `verdict-tool-untouched` 的 pathspec 内
   （`gates.yml:293` 逐字只有 `tools/gates/check_expected_red.py` 与 `tools/gates/gate-verify.mjs`）。
   **本 plan 一个字节都不动 `.github/workflows/**`（红线 2）、`tests/gates/**`（红线 1）、
   `docs/masterplan/DECISIONS.md`（红线 3）、`missions/**`、证据仓（红线 6）。**
   ⚠️ **因此本 plan 无需重摆「动 `.github/workflows/**` 凭什么」那道授权面** ——
   初稿要摆第八次，收窄之后那一整块不再适用。

7. **现有 `system-baseline.md` 的 §14 最大编号是 §14.8**（`:1093`）。
   前驱 plan `-1` 取 **§14.9**，本 plan 因此按序取 **§14.10**。
   ⚠️ **写死的是「开工时实读到的下一个空号」，不是字面的 `14.10`** —— 若 `-1` 被改号或取消，
   本 plan 取 §14.9。**开工时必须实读确认，不占别人的号。**

8. **既有本机判据基线**（收尾对照用）：`python3 tools/gates/check_expected_red.py` → **exit 0**，三行逐字
   `判定模式：default —— 按 tools/gates/expected-red.txt 判定` / `门禁 19 项：预期红 7，绿 12，跳过 0` /
   `✅ 与预期红名单完全一致`；`python3 -m pytest tests/contracts -q` → **151 passed**；
   `python3 -m ruff check agenerp tests/unit tests/contracts` → **exit 0**。
   ⚠️ `tests/unit` 的计数（此刻 293）**会被前驱 plan `-1` 抬高**，开工时实读，不照抄。

9. **`tools/**` 的静态检查现状（登记，本 plan 不动）**：`find tools -name "*.py"` 实测 6 个文件
   （`tools/bootstrap/homepage_notice.py` · `tools/gates/check_budget.py` ·
   `tools/gates/check_expected_red.py` · `tools/gates/explain_last_gate_failures.py` ·
   `tools/gates/pass_usage.py` · `tools/rotate-state.py`），`tools/mission-driver/**` 下**零个** `.py`；
   `python3 -m ruff check tools` → **exit 1，9 条**。
   ⚠️ **这 9 条本 plan 一条不修，也不把 `tools/` 纳入任何 lint 作用域**（`0228-1` M2 的裁定，见 Related）。
   ⚠️ 前驱 plan `-1` 会改动其中两个文件，**这个数很可能变大**；Phase 2 落纸时实读，不照抄。

## Goals

- **`[tool.ruff]` 那段注释兑现自己**：`tests/gates` 在**任何**调用形态下都不被 ruff 扫到 ——
  包括显式传目录、传单文件、传绝对路径。让「lint 逼着去改裁判」这条路在**配置层**就走不通。
- **把本 plan 放弃掉的那块 scope 登记出去**，而不是让它消失：`tools/**` 的静态检查缺口
  连同 `0228-1` M2 的既有裁定一起写进 `docs/backlog/`，交人。

## Non-Goals

- **不修 `tests/gates/**` 那 2 条 ruff 告警**（红线 1）。⚠️ 本 plan 的处置是让 lint **扫不到**它们，
  **这是「挡住」不是「修好」**，两者不得混为一谈。
- **不把 `tools/**` 纳入 lint 作用域、不修它那 9 条告警、不新增任何 CI job**
  （`0228-1` M2 已裁定「明确不扩面」，本 plan 不重开别人的裁定）。
- **不动 `.github/workflows/**` 一个字节**（红线 2）—— 因此本 plan **零 CI 轮次消耗**。
- **不改 ruff 的规则集**（不加 `select` / `extend-select`）、**不升 ruff 版本**（CI 仍钉 `0.14.1`）。
- **不动 `tools/gates/check_expected_red.py` / `gate-verify.mjs` / `expected-red.txt`**。
- **不动 `missions/**`** —— 因此 `GATE_VERIFY` 仍然跑不到 ruff，见 `## Deferred But Adjudicated`。

## Task Route

- Type: `implementation-only change`（一处**确认的契约/实现漂移的 `Fix`**）+ 两处 owner-doc 落纸
- Owner Docs: `docs/architecture/system-baseline.md`（新增 §14 的下一个空号）·
  **`docs/context/project-context.md`（`:69-70` 就地改准 —— Baseline 4 表里的 ②）** ·
  `docs/backlog/`（新增一条缺口登记 + roadmap 追加一行）· **`docs/masterplan/STATE.md`（只追加）** ·
  `docs/context/ai-autonomy-policy.md`（**只读引用**，不改）
  ⚠️ 后三项是独立评审第 1 轮的非阻断建议 4 与第 3 轮的阻断项 1 连续点出的遗漏，此处补齐。
- Skill Selection Basis: 本仓 `docs/skills/README.md` 下没有对应技能；
  工作方法由 `AGENTS.md` 红线 1 与 `docs/plans/00-plan-authoring-and-execution-guide.md` 直接给定。各 Phase 记 `Skill: none`。

## Infrastructure And Config Prereqs

- **零新增基础设施**：不起 docker、不连站点、不需要任何 env、不联网、**不推 CI**。
- ⚠️ **本机 ruff 版本须与 CI 钉的一致**才能拿本机结论说话：本机实测 `ruff 0.14.1`
  （`python3 -m ruff --version`），CI 钉 `ruff==0.14.1`。**开工时复核**；不一致就按
  `## Deferred But Adjudicated` 的固定处置走，不硬推。
- 回滚策略：无数据迁移、无站点写、无不可逆动作。回滚 = `git revert`。

## Execution Plan

### Phase 1 — Fix：`force-exclude` 落地，并就地改准那句不成立的注释

Status: planned
Targets: `pyproject.toml` · `docs/context/project-context.md` · `docs/architecture/system-baseline.md`
Skill: `none`

- Item Types: `Fix | Decision | Proof`
- Prereqs: 前驱 plan `2026-08-23-0859-1` 关闭（代码改动面不重叠，但 Baseline 8 / 9 的计数要等它定稿）

- [ ] `Decision` **D1：怎么让 `tests/gates` 在所有调用形态下都被挡住。**
      候选与取舍写进 `system-baseline.md` §14.10。
      - **(i) 靠纪律**：约定「谁都别把 `tests/gates` 传给 ruff」。
        **否决**：靠人记性，而本仓已有一条同类失效被记过（判定器给出两个读数，`STATE.md:86`）。
      - **(ii) `[tool.ruff]` 加 `force-exclude = true`。** **取此。**
        Baseline 2 第三条实测它使 `ruff check tests/gates` 退 0；Baseline 5 实测它对既有作用域零副作用。
        方向是**变严**（挡住的比现在多），不是变松。
      - (iii) 把 `tests/gates` 从 `exclude` 改成 per-file-ignores：那是「扫了但不报」，
        仍会让 ruff 读裁判文件并可能因语法演进而失败。**否决。**
      - **残余风险一（必须写，不粉饰）**：`force-exclude` 挡的是 **ruff**。
        任何**别的**静态检查器、编辑器插件、或有人手工 `--config` 覆盖它，都不受此约束。
        它把「靠纪律」换成了「靠一行配置」，**没有换成「不可能」**。
      - **残余风险二 —— 它把一次显式请求变成了一次静默的绿**（独立评审第 2 轮点名，初稿漏了）：
        `ruff check tests/gates` 落地后退 **0**，输出只有一行 `warning: No Python files found…`
        加一句 `All checks passed!`。**「我检查了，全过」和「我根本没看」在退出码上长得一模一样。**
        ⚠️ 这正是本仓反复点名的那类假绿（`gates.yml` 的判据设计与 `project-context.md` 的
        判定器四态口径都在防它）。**代价是真的，不许写成「方向变严所以没问题」。**
        本 plan 的处置只有两条，都要写进 §14.10：① 改准后的注释必须说明「路径被排除时 ruff 会静默退 0」；
        ② 该 `warning:` 行本身就是唯一的肉眼线索，**不得**再被任何调用方用 `2>/dev/null` 吞掉。
      - Skill: `none`
- [ ] `Fix` 在 `pyproject.toml` 的 `[tool.ruff]` 加 `force-exclude = true`。
- [ ] `Fix` 就地改准 **Baseline 4 表里的 ①**（`pyproject.toml:27-28`）：
      现状「把它排除在 lint 作用域外」在显式路径下不成立（Baseline 2）。
      改准后的措辞必须说明**为什么需要 `force-exclude`**（否则下一个人会以为它是冗余的、顺手删掉）。
      ⚠️ **第二句「门禁判定器是 `tools/gates/check_expected_red.py`，与 ruff 无关」一个字不动** ——
      它仍然为真（Baseline 1）。
- [ ] `Fix` 就地改准 **Baseline 4 表里的 ②**（`docs/context/project-context.md:69-70`）——
      同一处漂移的第二个活实例，该文件是本 plan 的 owner doc、可自由编辑，
      按 Minimum Rule 14 **不得降级为 follow-up**。⚠️ 只改这两行的措辞，**不动该文件其余任何一行**。
- [ ] `Proof` **隔离 A/B**：本 plan 除 `force-exclude` 与注释外没有别的代码改动，
      所以只需在加/去该行的前后各跑一遍并逐字对照（记录时写明这一点，别把「碰巧干净」当成「做了隔离」）：
      `python3 -m ruff check .`（期望命中数**不变**）·
      `python3 -m ruff check agenerp tests/unit tests/contracts`（期望 **exit 0**，输出 `diff` 无输出）·
      `python3 -m ruff check tools`（期望命中数**不变**）。
      ⚠️ **必须隔离**：本 plan 没有别的代码改动，所以这条 A/B 是干净的；记录时写明这一点。
- [ ] `Proof` 三种调用形态各实测一次，逐条记退出码与输出原文：
      `python3 -m ruff check tests/gates` · `python3 -m ruff check tests/gates/conftest.py` ·
      `python3 -m ruff check "$PWD/tests/gates"` —— **三者全部期望 exit 0**。
- [ ] `Proof` **变异验证（本机，零 CI）**：把 `force-exclude = true` 去掉 →
      期望 `python3 -m ruff check tests/gates` **exit 1** 且逐字点名 Baseline 2 那 2 条；
      复原后回 exit 0。⚠️ **点名集合必须逐字写下**，只写「红了」不算证据。
- [ ] `Proof` 全量复跑：`python3 tools/gates/check_expected_red.py`（期望 exit 0 且与 Baseline 8 的**三行**
      逐字节相同）· `python3 -m pytest tests/unit -q` · `python3 -m pytest tests/contracts -q` ·
      `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`（GATE_VERIFY 原文命令）。
- [ ] `Proof` 红线机械自查：`git diff --stat -- tests/gates .github/workflows tools missions docs/masterplan`
      **必须无输出**。⚠️ **本条的作用域是 Phase 1 那一个提交**（独立评审第 2 轮：
      Phase 2 要往 `docs/masterplan/STATE.md` 追加一行，全局套用这条判据会与它自相矛盾）；
      Phase 2 对 `docs/masterplan/` 的判据是**只许新增行**，写在该 phase 自己的 Exit Criteria 里。

Exit Criteria:

- [ ] 三种调用形态（目录 / 单文件 / 绝对路径）传 `tests/gates` 给 ruff **全部 exit 0**，三条输出原文入档
- [ ] 隔离 A/B 的三条对照全部为「无变化」，`diff` 输出入档
- [ ] 变异一次：去掉 `force-exclude` → exit 1 且点名那 2 条；复原 → exit 0。**六个字（红/绿）不许省成一句「有牙齿」**
- [ ] `python3 tools/gates/check_expected_red.py` 输出与 Baseline 8 的三行 `diff` 无输出
- [ ] **在 Phase 1 的提交上**，`git diff --stat -- tests/gates .github/workflows tools missions docs/masterplan` 无输出
- [ ] **两处注释改准都可核**（Rule 14 的非降级交付面，独立评审第 3 轮要求单列一条）：
      `pyproject.toml:27-28` 与 `docs/context/project-context.md:69-70` 改准后**均不再声称
      「排除在 lint 作用域外」**；`pyproject.toml` 侧还须写明 `force-exclude` 的必要性
      **与「路径被排除时 ruff 静默退 0」**（D1 残余风险二写死的处置①）
- [ ] `git diff -- docs/context/project-context.md` **只显示那两行的变更**，该文件其余一行未动
- [ ] `docs/architecture/system-baseline.md` 的新 §14 小节落地（编号已实读确认未被占用），
      D1 的取舍与**两条残余风险**（挡不住 ruff 以外的东西 · 显式请求被静默判绿）都在内
- [ ] `docs/logs/` 更新

### Phase 2 — 把放弃掉的 scope 登记出去（不是让它消失）

Status: planned
Targets: `docs/backlog/tools-dir-has-no-static-check-coverage.md`（新建）·
`docs/backlog/p0-foundation-roadmap.md`（**纯追加**一行）· `docs/masterplan/STATE.md`（**只追加**一行）
Skill: `none`

- Item Types: `Add | Follow-up`（新建 backlog 文件与三处追加都是净新增内容；
  ⚠️ 初稿把建文件标成 `Follow-up`、把 roadmap 追加标成 `Proof`，两处都不对，已按独立评审第 2 轮改准）
- Prereqs: Phase 1

- [ ] `Add` 新建 `docs/backlog/tools-dir-has-no-static-check-coverage.md`，
      按本仓既有 backlog 条目的形态（`Status:` / 事实与取证 / 为什么 loop 不能自己做 / 触发条件 / 可选处置）写。
      **必须包含且不许省的四件事**：
      ① 实测事实（6 个 Python 文件、9 条告警、`tools/mission-driver/**` 零 `.py`）；
      ② **`0228-1` M2 的既有裁定原文**，以及「本 plan 不重开它」这句；
      ③ **反向证据照实记**：`tools/rotate-state.py` 全仓零调用方、`homepage_notice.py` 只被 compose 的
      bootstrap 服务用、`explain_last_gate_failures.py` 已被 `tests/unit/test_gate_verdict.py` 导入测过，
      而循环真正调用的 `check_budget.py` / `pass_usage.py` 已由前驱 plan `-1` 补上**行为判据**
      —— **也就是说扩面的增量购买力接近零，这条要写在「可选处置」前面，不许只列好处**；
      ④ **代价照实记**：把 `check_expected_red.py`（`plan-first` + 服务端守卫）纳入 lint 作用域，
      等于让它**长期人质于将来的 ruff 版本**；以及 job 数 14 → 15 这条已被连续登记五次的增长。
- [ ] `Follow-up` 该 backlog 条目必须写明**触发条件**（Anti-Slacking Rule：不许「以后有空再说」），
      至少含：**人裁定推翻 `0228-1` M2 时** · **第一次出现「`tools/**` 被改坏、当轮 `GATE_VERIFY` 绿、
      无人值守时才炸」时** · **人裁定给本仓引入 shellcheck / 扩 lint 面时**。
- [ ] `Add` 往 `docs/backlog/p0-foundation-roadmap.md` **纯追加**一行 `9 现状 · <本 plan 的判据设施加严>`。
      ⚠️ **既有行一个字不改**（`git diff` 只许显示新增），且必须逐字写明：
      本 plan **不改工作项 9 的 `done` 判据**（那条判据是「用判定器对 `tests/gates` 全部 19 条
      live 判定并 `success`」，与 ruff 的作用域**互不重叠**），
      **不得被读成「工作项 9 因此可以 `done`」**；**所有工作项的状态值一个字未改**。
- [ ] `Add` 往 `docs/masterplan/STATE.md` **追加**一行证据（红线 5：只追加，不改写既有行）。

Exit Criteria:

- [ ] `docs/backlog/tools-dir-has-no-static-check-coverage.md` 存在，四件必含事项逐条可核，触发条件已写明
- [ ] `docs/backlog/p0-foundation-roadmap.md` 的 `git diff` **只显示新增行，零删除零修改**
- [ ] `docs/masterplan/STATE.md` 的 `git diff` **只显示新增行**
- [ ] No owner-doc update required beyond the above
- [ ] `docs/logs/` 更新

## Draft Review Record

- Independent draft review iteration 1: **should be dropped or fundamentally rescoped**
  （独立子代理，fresh session，2026-08-23）—— 九条阻断项。**结论被整体接受**，本 plan 据此收窄，
  收窄逐条落在 `## Scope Change Record`。对应关系：
  **①** 价值论证的核心引用不是逐字，且从未查过那 6 个文件谁在调用 → 整段删除，
  连同反向证据一起写进 backlog 条目（Phase 2 ③）。
  **②** `0228-1` M2 已就同一处裁定「明确不扩面」，初稿既未引用也未反驳 →
  Related 与 `## Non-Goals` 逐字引入该裁定，**本 plan 不重开它**。
  **③** 两处 `逐字` 引用被截断，且被截掉的那半句正好会因初稿的改动而变假 →
  Baseline 1 引全，并写明「该半句在收窄之后仍为真，因此不改」。
  **④** 变异 ③ 同时改两处、隔离不出原因，且它验的配置在 `main` 上永不存在 →
  四次 CI 变异全部删除，改为 Phase 1 的**本机零成本变异**；
  `force-exclude` 无 CI 级证伪面这一点按评审建议**照实写进 §14.10**，不假装有。
  **⑤** Phase 3 未写裁判规则 4 口径 → 已无 CI 阶段，该风险随之消失（不是「已处理」，是**不再适用**）。
  **⑥** D1 把「纯追加先例」写成**授权依据**，而 §14.7 明确否决该措辞 →
  已无 `.github/workflows/**` 改动，整块授权面不再适用（**Baseline 6** 逐字写明这一点）。
  **⑦** 一个 plan 两个结果面（lint 扩面 / `force-exclude`）→ **只留后者**，Minimum Rule 4 满足。
  **⑧** `--help` / `--dry-run` 都走不到 `rotate-state.py` 的 6 个 `E741` 位点，
  而真跑会写 `STATE.md`（红线 5；评审实测该文件 **98,031 字节** 对 `BUDGET = 30720`，真跑必然触发轮转）→
  该文件已整体移出 scope。
  **⑨** Phase 1 的 `Item Types` 漏了 `Proof` → 已改为 `Fix | Decision | Proof`。
  非阻断建议 4（Owner Docs 漏了 roadmap 与 `STATE.md`）、5（A/B 须隔离）、6（§14.10 是下一个空号）、
  7（`Targets` 应是路径）亦已采纳；建议 1/2/3 随 CI 阶段一并移出，不再适用。
- Independent draft review iteration 2: **needs revision**（独立子代理，fresh session，2026-08-23）——
  确认收窄后的九条**全部 closed**（其中 ④⑤⑥⑧ 是**因 scope 被真正移除**而关闭，评审逐条复核过移除是真的、
  且记录未粉饰；⑦ 判 `PARTIALLY CLOSED` —— Phase 2 的 backlog 登记是 Rule 10 的履约而非干净的 Rule 4，
  本稿接受该定性，不再拆）。评审并复跑了全部 Baseline，逐项 ✔。
  **三条新阻断项已在本稿改掉**：
  **N1** 同一句不成立的话在仓里**有三处**，初稿只盘了一处 → 新增 Baseline 4 的三行盘点表，
  `project-context.md:69-70` 升为**在 scope 的 `Fix`**，`gates.yml:437-439` 登记进 Deferred 交人。
  **N2** `force-exclude` 把一次显式请求变成**静默的绿**（`ruff check tests/gates` 退 0 且只有一行 `warning:`），
  初稿只写「方向变严」→ D1 新增**残余风险二**，并写死两条处置。
  **N3** Phase 1 的红线自查 pathspec 含 `docs/masterplan`，与 Phase 2 要往 `STATE.md` 追加自相矛盾 →
  该判据收窄到 Phase 1 那一个提交。
  非阻断 1（「零重叠」措辞过强）、2（`Item Types` 标错）、3（§14.10 应写成「下一个空号」）、
  4（`git stash` 是空动作）亦已采纳。
  ⚠️ **评审的判断 (a)「这件事不该立 plan」未被采纳**，异议原文与三条裁定理由落在 `## D0`，
  **不是静默驳回**。
- Independent draft review iteration 3: **needs revision**（独立子代理，fresh session，2026-08-23）——
  **N2 / N3 与非阻断 1–4 全部判 CLOSED；N1 判 PARTIALLY CLOSED**。三条待改已在本稿改掉：
  ① N1 的剩余半边 —— `docs/context/project-context.md` 只在 Phase 1 的**执行项列表**里在 scope，
  却缺席 `Task Route > Owner Docs`、`Phase 1 Targets` 与 `Closure Gates`（`system-baseline.md` 同病）→ 三处补齐；
  ② **两处注释改准这个 Rule 14 非降级交付面没有任何 Exit Criterion 看着** → 新增两条可 grep / 可 diff 的判据；
  ③ 插入 Baseline 4 之后**四处 Baseline 交叉引用变旧**（`Baseline 7 三行` 实为 8、`Baseline 4 已证完` 实为 2 第三条 等）→ 改准。
  ⚠️ **本条当时写的「逐处改准」不准确**：第 4 轮实测**四处只改了三处**，
  漏掉的第四处在本记录自己的 ⑥ 行（`Baseline 5` 实为 `Baseline 6`），已在第 4 轮补上。
  D0 的两处纰漏当时记作已采纳，⚠️ **第 4 轮实测其中「改成引原文」那半条当时并没有真的落到 D0 里**
  （只落在本记录里），已在第 4 轮补上。当时采纳的是：把「转述当逐字引用」改成引原文，并补上评审送的两条更强论据
  （Decision Table 第三行逐字列着 `stale-doc conflict`；指南逐字列着「modifies more than 5 total files」，
  本 plan 交付面 6 个文件直接命中）。
  ⚠️ **`## D0` 被评审明确 ACCEPT**，且评审自述「round 2 自己要求的 N1 修复反过来推翻了 round 2 的『太琐碎』前提」。
- Independent draft review iteration 4: **needs revision → 两条一行改动后达成共识**
  （独立子代理，fresh session，2026-08-23）。
  第 3 轮的**阻断项 1、2 与 D0 纰漏 B 判 CLOSED**；**阻断项 3 判「四处只改了三处」**、
  **D0 纰漏 A 判「记录里说改了、D0 里没改」** —— ⚠️ **两条都是本方上一轮的失实自述，照实记在上面的第 3 轮条目里，
  不改写那条记录的其余部分**。两处均已改掉：① 第 3 轮记录 ⑥ 行的 `Baseline 5` → `Baseline 6`；
  ② D0 理由 1 的转述式引用换成 `00-plan-authoring-and-execution-guide.md:23` 的原文，
  并把两条更强论据（`stale-doc conflict` 行 · `modifies more than 5 total files`）从评审记录搬进 D0 正文。
  整体一致性通过：无其余 Baseline 串号、Baseline / phase / Exit Criteria / Closure Gates / Deferred 互相自洽、
  N3 的作用域收窄对 Phase 2 的 `STATE.md` 追加成立、Exit Criteria 全部可 grep / diff / 判退出码、
  **零个受保护文件被触及**（红线 1/2/3/5/6 均显式排除且有机械自查）、Rule 7 / 9 / 10 / 11 / 12 与
  Anti-Slacking 全部满足。评审逐字：「Apply those two single-line edits … and it is ready ——
  **no further review round is warranted**」。
- **共识达成（四轮）**：第 1 轮 `should be dropped or fundamentally rescoped` → 整体收窄 →
  第 2 轮 `needs revision`（九条全 CLOSED，新增 N1/N2/N3，并对「该不该立 plan」提异议）→
  第 3 轮 `needs revision`（**`## D0` 被 ACCEPT**，三条待改）→
  **第 4 轮：两条一行改动后 ready，评审明言无需再评一轮**。
  据此把 `Plan Status` 由 `draft` 改为 `active`。

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned（`system-baseline.md` 新 §14 小节 · **`project-context.md:69-70` 就地改准** ·
      新建 backlog 条目 · `p0-foundation-roadmap.md` 追加行 · `STATE.md` 追加行）
- [ ] verification has run：`ruff check tests/gates`（三种调用形态）· `ruff check .` ·
      `ruff check agenerp tests/unit tests/contracts` · `ruff check tools` · 一次本机变异 ·
      `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` · `pytest tests/contracts -q`
- [ ] scoped verification is not conflated with full verification —— ⚠️ **本 plan 的验证范围逐字是「本机」**；
      它**零 CI 消耗**，因此**不得**宣称任何 CI 侧结论。`force-exclude` 在 CI 上**没有**证伪面
      （交付的 job 从不把 `tests/gates` 传给 ruff），这一点已写进 §14.10，**不许略过不谈**
- [ ] no in-scope item downgraded to deferred/follow-up —— ⚠️ 本 plan 有一次**记录在案的 scope 收窄**，
      见 `## Scope Change Record`；移出的部分**全部落进 `docs/backlog/` 并带触发条件**，不是静默丢弃
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files

## Deferred But Adjudicated

### `tools/**` 的静态检查缺口（本 plan 放弃的 scope）

- Classification: `out-of-scope improvement`（**人动作项**）
- Why Not Blocking Closure: `0228-1` 的评审记录 M2 已就同一处裁定「明确不扩面，避免把顺手优化拖进来」，
  且独立评审实测该扩面在前驱 plan `-1` 之后增量购买力接近零（三个文件：一个零调用方、
  一个只被 compose bootstrap 用、一个已被单测导入）。本 plan 不重开别人的裁定。
  ⚠️ **不得读成「`tools/**` 已被覆盖」**：那 6 个 Python 文件与全部 shell 仍零静态检查。
- Successor Required: `no` —— 已落 `docs/backlog/tools-dir-has-no-static-check-coverage.md`（Phase 2 交付）
- 重开事件：见该 backlog 条目写死的三条触发条件。

### `tests/gates/**` 那 2 条既有 ruff 告警仍在，本 plan 不修

- Classification: `watch-only residual`（**红线 1 内，只有人能做**）
- Why Not Blocking Closure: `tests/gates/conftest.py:29` 的 `F401` 与
  `test_customization_roundtrip_delete.py:39` 的 `E741` 是真告警，但那是裁判面，
  loop 一个字节都不许改。⚠️ 本 plan 的处置是让 lint **扫不到**它们 ——
  **「挡住」不是「修好」**，两者不得混为一谈。
- Successor Required: `no`（**人动作**：一次带 `Gates-Change-Approved-By:` 的清理）
- 重开事件：**人出具 trailer 清理裁判目录的 lint 告警时**。

### `force-exclude` 在 CI 上没有证伪面

- Classification: `watch-only residual`（**登记而不消除**，独立评审第 1 轮点名）
- Why Not Blocking Closure: 交付形态里没有任何 job 会把 `tests/gates` 传给 ruff，
  所以「`force-exclude` 是否还在生效」在 CI 上**不可证伪**；它是一个**潜伏的守卫**。
  造一个 CI 级证伪面要新增 job 并让它故意扫裁判目录，那是初稿被否决的那条路。
  ⚠️ **不得写成「已在 CI 上验证」**。代偿只有一条且要写明其弱：
  Phase 1 的本机变异只在**关闭当次**做过一次，**此后不再复核**。
- Successor Required: `no`
- 重开事件：**有人提议删掉 `force-exclude` 时**（届时本 plan 的 §14.10 就是它为何存在的记录），
  或**人裁定给守卫本身造 CI 级证伪面时**。

### 同一处漂移的第三个活实例在 `.github/workflows/gates.yml:437-439`，本 plan 不改

- Classification: `out-of-scope improvement`（**人动作项**）
- Why Not Blocking Closure: 它逐字说「不扩到 `tests/gates`（`pyproject.toml` 的
  `[tool.ruff] exclude` 已排除它…）」，与 Baseline 4 表里 ①② 同因。
  但 `.github/workflows/**` 是红线 2 的 `blocked` 面，改一句注释要重摆一次授权面并烧一轮 CI，
  而本 plan 的整个形态建立在「零 CI 消耗」上。
  ⚠️ **`force-exclude` 落地之后，这句话从「不准确」变成「准确但不完整」**（排除确实生效了，
  只是它不知道靠的是 `force-exclude`）——**方向是弱化，不是加剧**，这是它可以挂着的理由，
  **不是**「它本来就没问题」。
- Successor Required: `no`（**人动作**：一次带批准的注释改准，可与将来任何一次动 `gates.yml` 的 plan 搭车）
- 重开事件：**下一个因任何理由要动 `gates.yml` 的 plan 开工时**（届时必须把这处注释一并纳入 scope），
  或**人裁定单独改它时**。

### `GATE_VERIFY` 仍然跑不到 `ruff`（`missions/**` 是角色 B 禁区）

- Classification: `watch-only residual`（`0120-1` / `0337-1` 已连续登记，本 plan 继续挂着）
- Why Not Blocking Closure: `missions/p0-foundation.json` 的 `commands.test` 逐字是
  `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`，改它是人的动作。
  ⚠️ 本 plan 连 CI 都不动，**更不得**被读成「ruff 已进判定面」。
- Successor Required: `no`（**人动作**）
- 重开事件：**人裁定改 `missions/**` 时**。

### 结果与预测不符时的固定处置（写死，不临场决定）

- Classification: `watch-only residual`（失败分支的写死处置，不是被推迟的工作项）
- Why Not Blocking Closure: 本条不是一件待办，而是失败分支的固定处置；它不占用任何 Exit Criterion。
- 处置逐字：原样复跑一次（裁判规则 3：复跑优先于分析）→ 仍不符则记录所有已跑命令与输出原文 →
  追加进 `docs/masterplan/STATE.md` §3（**不改写既有行**）→ **不放宽任何断言**、
  **不改 `tests/gates/**`、`tools/gates/check_expected_red.py` 与 `.github/workflows/**`** →
  **不猜根因** → 本 plan 置 `deferred` 并在文件头写明重开条件。
- Successor Required: `no`
- 重开事件：**人裁定继续**，或不符之因被一个独立 plan 查清之后。

## Closure

Status Note: <待关闭时填写>

Closure Audit Evidence:

- Auditor / Agent: <独立子代理>
- Evidence: <命令原文 + 退出码 + commit sha>

Follow-up:

- <仅非阻塞项；确认的活缺陷不得出现在这里>
