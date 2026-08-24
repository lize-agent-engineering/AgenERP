# `tools/**` 零静态检查覆盖 —— 6 个 Python 文件 9 条 ruff 告警在名单外，全部 shell 一条检查都没有

> Status: `deferred`（**登记，不处置**；处置需要人）
> Created: 2026-08-23
> 由 plan `docs/plans/p0-foundation/2026-08-23-0859-2-ruff-force-exclude-guards-the-judges.md` 的 Phase 2 产出
> 处置者：**人**（`2026-08-22-0228-1` 的评审记录 M2 已就同一处裁定过「明确不扩面」，
> 重开别人的裁定只有人能做）
> ⚠️ 本条是那个 plan 被独立评审整体移出的 scope，**不是静默删除** ——
> 收窄记录见该 plan 的 `## Scope Change Record`

## 事实（2026-08-23 在 `main` @ `702893a` / `dc7e54f` 上实读 + 实跑，不是推理）

| # | 事实 | 取证 |
|---|---|---|
| 1 | `tools/**` 下有 **6 个** Python 文件 | `find tools -name "*.py"` → `tools/bootstrap/homepage_notice.py` · `tools/gates/check_budget.py` · `tools/gates/check_expected_red.py` · `tools/gates/explain_last_gate_failures.py` · `tools/gates/pass_usage.py` · `tools/rotate-state.py` |
| 2 | `tools/mission-driver/**` 下 **零个** `.py` | `find tools/mission-driver -name "*.py" \| wc -l` → **0**（driver 是 `.mjs`，ruff 本来就管不着） |
| 3 | 这 6 个文件此刻共 **9 条** ruff 告警 | `python3 -m ruff check tools` → **exit 1，9 条**：`check_budget.py:142,143` `F541` · `pass_usage.py:14` `E401` · `rotate-state.py:53,54,65,96,103,105` `E741` |
| 4 | 既有 `lint` job **不含 `tools/`** | `.github/workflows/gates.yml:426` 的判据 step 逐字是 `ruff check agenerp tests/unit tests/contracts` |
| 5 | shell 侧**一条静态检查都没有** | 本仓无 shellcheck 配置、无对应 CI job；`tools/loop-supervisor.sh` / `tools/ab-run.sh` 等零覆盖 |

**这 9 条全是文体项**（`F541` f-string 无占位符 · `E401` 一行多 import · `E741` 变量名 `l`），
**没有一条是行为缺陷**。照实说，不夸大。

## 既有裁定：`2026-08-22-0228-1` 的评审记录 M2 已就同一处裁定过「明确不扩面」

原文逐字（`docs/plans/p0-foundation/2026-08-22-0228-1-gate-verdict-failure-forensics.md:317-320`）：

> **M2** 新增的 `tools/gates/explain_last_gate_failures.py` 无 lint 覆盖 ——
> 本仓惯用 lint 面 `agenerp tests/unit tests/contracts` 不含 `tools/`；已加**文件级** ruff 判据，
> 并实测 `tools/gates` 整目录另有 3 条既存告警（`check_budget.py` / `pass_usage.py`），
> 故明确不扩面，避免把顺手优化拖进来。

**`2026-08-23-0859-2` 不重开这条裁定。** 它是别人做过的取舍，重开只有人能做。
本条登记的是「这条裁定留下的缺口仍然在」，**不是**「这条裁定错了」。

## 反向证据（照实记，写在「可选处置」前面，不许只列好处）

**扩面的增量购买力接近零，这是实测出来的，不是推理**：

| 文件 | 谁在调用它 | 取证 | 因此扩面能买到什么 |
|---|---|---|---|
| `tools/rotate-state.py` | **全仓零调用方** | `grep -rn "rotate-state"` 全仓（排除 `.git/` 与 `docs/`）**只命中它自己的 docstring 第 18 行** | 它那 6 条 `E741` 修不修，运行时无人受影响 |
| `tools/bootstrap/homepage_notice.py` | **只**被 `docker-compose.yml:174` 的 bootstrap 服务用 | 同一条 `grep` 全仓唯一命中 | 它此刻**零告警**，扩面对它是空动作 |
| `tools/gates/explain_last_gate_failures.py` | 已被 `tests/unit/test_gate_verdict.py` **导入测过** | `grep -rln` 命中该测试文件 | 已有**行为判据**，比 lint 强 |
| `tools/gates/check_budget.py` · `pass_usage.py` | 循环真正调用的两个 | 前驱 plan `2026-08-23-0859-1` 已补上行为判据（`tests/unit/test_budget_gate.py` 16 条 + `tests/unit/test_pass_usage.py` 11 条，`tests/unit` 293 → 320） | 那 3 条文体告警之外，**行为面已经被判据盖住** |
| `tools/gates/check_expected_red.py` | 判定器本体 | —— | 它此刻**零告警**；见下面「代价」那条 |

**也就是说**：真在 7×24 循环里跑的两个文件已经有了行为判据（比 lint 强的一层），
零调用方的那个文件占了 9 条里的 6 条，剩下的要么零告警要么已被单测导入。
**扩面此刻买到的主要是文体一致性，不是可靠性。**

## 代价（照实记，不是只有好处）

1. **把 `tools/gates/check_expected_red.py` 纳入 lint 作用域 = 让判定器长期人质于将来的 ruff 版本。**
   它是本仓的判定器本体（`plan-first` + 服务端 `verdict-tool-untouched` 守卫双重保护）。
   ruff 升一次版新增一条规则，就可能让**判定器所在的 job 变红**，而那个红与判定器对不对毫无关系。
   本仓已经为「lint 逼着去改受保护文件」这件事付过一次代价 —— 见 `system-baseline.md` §14.10。
2. **CI job 数 14 → 15。** 这条增长已被**连续登记五次**（§14.5 / §14.6 / §14.7 / §14.8 / §14.9 各一次）。
   实测当前 `.github/workflows/gates.yml` 的 job 数是 **14**。
3. **改 `.github/workflows/**` 是红线 2 的 `blocked` 面**：要重摆一次授权面、烧一轮 CI 轮次。

## 触发条件（按 Anti-Slacking Rule 必须写明，不是「以后有空再说」）

三者**任一**发生即触发，届时必须处置、不得再挂着：

1. **人裁定推翻 `2026-08-22-0228-1` 的 M2 时** —— 那条「明确不扩面」是本条唯一的硬拦，
   它一旦被人推翻，扩面就不再是重开别人的裁定。
2. **第一次出现「`tools/**` 被改坏、当轮 `GATE_VERIFY` 绿、无人值守时才炸」时** ——
   这是本条真正要防的失效形态。`missions/p0-foundation.json` 的 `commands.test` 逐字是
   `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`，
   它复跑不到 `tools/loop-supervisor.sh` 与 `tools/ab-run.sh` 的任何一行。
   **一旦踩到这一次，上面「增量购买力接近零」的结论当场作废。**
3. **人裁定给本仓引入 shellcheck / 扩 lint 面时** —— 那时这 9 条与 shell 侧的零覆盖应一并处置，
   避免只做一半。

**在此之前不处置的理由（照实说，不是「没空」）**：M2 那条裁定在，且实测增量购买力接近零。
**但这不等于缺口不存在** —— 那 6 个 Python 文件与**全部 shell** 此刻确实零静态检查覆盖。
⚠️ **不得把本条读成「`tools/**` 已被覆盖」。**

## 可选处置（loop 不替人选，每项都标出代价）

- **(a) 扩既有 `lint` job 的路径列表**，把 `tools` 加进 `ruff check agenerp tests/unit tests/contracts`。
  **代价**：① 改 `.github/workflows/**`（红线 2）；② 那 9 条要先修，而修 `rotate-state.py` 的 6 条 `E741`
  是给一个**零调用方**的文件做整容；③ 判定器就此人质于 ruff 版本（见「代价」①）。
- **(b) 新增第 15 个 job 只扫 `tools/`**，与判据 job 隔离，红了不挡判定面。
  **代价**：① job 数增长第六次；② 同样要改 `.github/workflows/**`；③ 隔离意味着它红了也没人管，
  那就退化成一个装饰性的 job。
- **(c) 文件级判据**（`0228-1` M2 走过的那条路）：只把新增/改动的单个文件加进判据 step。
  **代价**：① 每加一个文件就要动一次 `gates.yml`；② 覆盖面靠人记性维持 —— 而本仓已有一条
  同类失效被记过（判定器给出两个读数，`STATE.md:86`）。
- **(d) 维持现状**，接受 `tools/**` 零静态检查。
  **代价**：触发条件 2 那个失效形态没有任何机械手段拦得住；且 shell 侧的零覆盖同样一直挂着。

## 现在就能做的（不需要人裁定，也不碰任何红线）

**本机随时可跑，零成本**：

```
python3 -m ruff check tools
```

它此刻 **exit 1，9 条**。**这不是门禁**，没有任何自动化会跑它 —— 那正是本条登记的缺口。
