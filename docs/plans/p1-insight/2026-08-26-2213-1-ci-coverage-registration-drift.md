# 2026-08-26-2213-1 · §7.7 的复跑面登记改准，并把「哪些测试目录被谁复跑得到」钉成单一真相源

> Plan Status: completed
> Mission: p1-insight
> Work Item: 4. 上下文层 v0：即时上下文注入 + 会话落 DocType（P1.2）—— **本 plan 是它的第 2 个 plan**
> （表规 3 逐字「一个工作项 = 1–2 个 plan」；起草期实点 `docs/plans/p1-insight/*.md` 的 `> Work Item:` 首行归组，
> 工作项 4 名下此前只有 `2026-08-24-1457-2-context-layer-v0.md` **一份** ⇒ 该格 `1/2`，本 plan 用掉最后一格，
> **不需要人加预算、不需要拆行**）
> Last Reviewed: 2026-08-26
> Source: 起草步自查 —— `docs/architecture/module-boundaries.md` §7.7 末节「判据缺口，如实记在这里」
> 逐字与今天的 `.github/workflows/gates.yml` 相反
> Related: `docs/plans/p1-insight/2026-08-26-2101-1-routing-guard-registration-drift.md`
> （**同一失败形态的第一例，也是本 plan 的形状来源**：owner doc 里一句覆盖断言在人补上判据之后挂了一天没人改）
> Audit: required

## Current Baseline

### B1 · 一段逐字与仓库相反的登记文字（本 plan 的处置对象）

`docs/architecture/module-boundaries.md:485-487`（§7.7 上下文层的落点节，owner = 工作项 4 / P1.2）逐字：

> `tests/context` **不在** `missions/p1-insight.json` 的 `commands.test` 里，
> 也不在 `.github/workflows/gates.yml` 的 `unit-and-contracts` / `lint` 任何一个 job 的作用域里
> （那两个 job 的作用域是 `tests/unit` `tests/contracts`）。因此 **`GATE_VERIFY` 与 CI 都复跑不到本层的主判据**。

**实读反证**（`.github/workflows/gates.yml`，只读，一个字节未改）：

- `:620-621` `- name: ⑤ 上下文层（tests/context）` / `run: python3 -m pytest tests/context -q` —— 在 `unit-and-contracts` job 里。
- `:682` `run: ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui`
  —— `tests/context` 在 `lint` job 的作用域里。
- ⇒ **括号里那句「那两个 job 的作用域是 `tests/unit` `tests/contracts`」在两个 job 上各错一次。**
- ⚠️ **同一段里仍然成立的那一半**：`missions/p1-insight.json:16` 的 `commands.test` 逐字仍是
  `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`（起草期 `json.load` 实取）
  ⇒ **`GATE_VERIFY` 确实复跑不到 `tests/context`**。**这一半不许一并改掉。**

### B2 · 同一失败形态的**全部已知处，以本表为准**（正文不复述处数）

🔴 **本表是这份清单的唯一形态，正文任何地方都不再写「一共有 N 处」。**
理由是实测出来的，不是洁癖：**处数在四轮评审里被改了三次**（四处 → 五处 → 六处 → 八处），
**每一次都是「表改了、正文的数字没跟上」**（第 5 轮 BL-3、第 6 轮 BL-2、第 7 轮 BL-4 —— 同一形态复发三次）。
⇒ **把数字从正文里去掉，是本 plan 对自己犯的那个病的处置**；`B3` 与 `Closure Gates` 一律改为「**B2 表的每一行**」。

| # | 位置 | 逐字问题 | 今天的真值 | 本 plan |
|---|---|---|---|---|
| 1 | `module-boundaries.md:485-487`（§7.7） | 「不在 `unit-and-contracts` / `lint` 任何一个 job 的作用域里」 | 在（第 ⑤ 步 + ruff 作用域） | **改**（事实就地改准） |
| 2 | `docs/backlog/p1-insight-roadmap.md:41`（工作项 1 行尾） | 「⚠️ 仍待人做：`tests/tools` 本身未进 `gates.yml` 的 `unit-and-contracts` / `lint` 两个 job」 | 已进（第 ③ 步 + ruff 作用域） | **追加一条纯指针**（Phase 3 的 `Decision`） |
| 3 | `model-management.md:373-382`（**§12.5**） | 「`tests/routing` 既不在 `commands.test` 里，也不在 `gates.yml` 的任何 job 里……不得声称 CI 覆盖了 `tests/routing`」 | CI 侧已覆盖（第 ④ 步 + ruff）；`commands.test` 侧仍未覆盖 | **就地改准**（Phase 3 的 `Fix`，逐从句） |
| 4 | `model-management.md:384-386`（**§12.5**，第 3 处下方 2 行） | 「`pyproject.toml` 没有声明 `dependencies`，`certifi` 至今是一个未声明的依赖」 | `pyproject.toml:14-16` 逐字 `dependencies = ["certifi>=2024.2.2"]`（`d5f0a04`，`lize`，2026-08-24） | **就地改准**（同上） |
| 5 | `module-boundaries.md:488`（§7.7，第 1 处下方 1 行） | 「`missions/**` 与 `.github/workflows/**` 都在红线内，loop 无权自己补」 | workflows 那半已由 `b0ad632` 接完；`missions/**` **不在红线内**（`AGENTS.md:8-16` 实读无它，出处是 `ai-autonomy-policy.md:87` 的 Protected Areas） | **改**（Phase 3 的 `Fix`，与 §12.5 `:378` 同一处置） |
| 6 | `module-boundaries.md:4424-4442`（**§7.23.6**「CI 覆盖面：本节落地后**三处零覆盖**，全部归人（红线 2）」） | 三条编号项 + 两句结论：① 第 ⑦ 步「**会红**」② 「`tests/ui/test_sidebar.py` **不会被任何 job 跑到一次**」③ 「`tests/ui` 在 CI 上**零 lint 覆盖**，ruff 参数是**七个**目录」④ 「六件全部落在 `.github/workflows/**` 里 ⇒ **本节与本 plan 一个字节都不碰**」⑤ 「`gates.yml:640` 那句『三个目录』**仍然是错的**；真相源八个而参数七个，**两边仍然不等**」 | **五条今天逐条相反**：① `:631` `COVERED` 含 `ui`（9 项）== `ls -d tests/*/ \| wc -l` 实测 **9** ⇒ **不红** ② `gates.yml:326` `- name: ⌘K 侧边栏活体门禁（零 skip）` + `:337` 逐字 `python3 -m pytest -m live tests/ui/test_sidebar.py -q | tee /tmp/ui-gate.log`，在 `gates-l2-live`（job 键 `:236`）里 ③ `:682` ruff 参数**含 `tests/ui`** ④ `STATE.md:1152-1153` 逐字「**六件全部做掉**（`f795e47`，带 `Gates-Change-Approved-By:`）」，`git log -1 f795e47` → `lize` 2026-08-26 ⑤ `:674` 今天逐字「作用域**八个目录**（2026-08-26 随 tests/ui 落地改准）」，`:682` 亦八个 ⇒ **两边已相等** | **改**（Phase 3 的 `Fix`，逐条按三分口径判） |
| 7 | `docs/context/project-context.md:52`（`Lint / static check` 行内的 ⚠️ 注解） | ①「`gates.yml` 那句注释逐字写的是「**作用域三个目录**」，改完之后**仍然是错的**」②「本行现在是**八个**目录而 `lint` job 是**七个** —— 两边**仍然不等**」③「`tests/ui` …**在 CI 上是零 lint 覆盖，直到人把它加进 `lint` job**」+「残余的两处都落在 `.github/workflows/**` 里 ⇒ 红线 2，**逐字交人**」 | **三条全反**：① `gates.yml:674` 今天逐字「作用域**八个目录**（2026-08-26 随 tests/ui 落地改准）」② `:682` 八个参数、含 `tests/ui` ⇒ **集合已相等** ③ `f795e47`（`lize`，2026-08-26）已做完，`STATE.md:1153` 逐字「**六件全部做掉**」 | **改**（Phase 3 的 `Fix`，口径同 §7.7）。⚠️ 该文件**不在任何红线 / Protected Areas 内**（`ai-autonomy-policy.md:77-90` 实读无 `docs/context/**`；`module-boundaries.md:4439` 自己也写着「它不在任何红线内」）⇒ loop 有权就地改准 |
| 8 | `docs/backlog/p1-insight-roadmap.md:108`（+ `:109` 括号内半句） | 「⚠️ **`tests/ui/` 在 CI 上今天零覆盖**…… `COVERED` **少一个 `ui`**（第 ⑦ 步**必红**）· `gates-l2-live` **没有跑它的 step** · `lint` job 的 ruff 参数**不含 `tests/ui`**」+ `:109`「（`tests/ui/` **不在任何 job 作用域里**，本门禁在 CI 上的行为**零数据**）」 | **三条全反**：`gates.yml:631` `COVERED` 含 `ui` · `:326` `- name: ⌘K 侧边栏活体门禁（零 skip）` / `:337` 逐字跑 `tests/ui/test_sidebar.py`（`gates-l2-live`，job 键 `:236`）· `:682` ruff 含 `tests/ui` | **改**（Phase 3 的 `Fix`）。⚠️ **形态与第 2 处（`roadmap:41`）相同、不与第 1/6/7 处相同**：它是**引擎回写的账本行** ⇒ **不改写已有的任何一个字，只追加一句指向 §7.26 的指针 + 证据路径**（取舍已由 `D5` 写死，直接复用） |
| 9 | `docs/architecture/system-baseline.md:1016-1017`（§14.7「`lint` 判什么」）**与 `:1587-1588`（§14.10）** | ① `:1016` 逐字「一条判据命令，逐字 `ruff check agenerp tests/unit tests/contracts`」 ② `:1017` 逐字「**作用域三个目录**逐字照抄 `docs/context/project-context.md` 的 `Lint / static check` 一行，**一个字不加不减**」 ③ `:1587-1588` 逐字「**既有** `lint` job（`.github/workflows/gates.yml:426`）的判据 step 是**显式列目录**的 `ruff check agenerp tests/unit tests/contracts`」 | **三条今天全反 + 两处行号漂**：`gates.yml:663` 才是 `lint` job 键（`:426` 已漂）· `:682` 逐字八个目录 · `project-context.md:52` 亦八个 ⇒ 「三个目录」与「一个字不加不减」两句同时失效（同批次落地人 `lize`，`f795e47` 与其前序） | **改**（Phase 3 的 `Fix`）。⚠️ **形态与第 6 处（§7.23.6）不同、与 `:4270` 相同**：两处都在 `## 14.x <plan> 交付` 这种**按 plan 分节的交付记录**里 ⇒ **不改写记录本身，只加一句时点限定 + 指向 §7.26 的指针**（口径与 `:4270` 逐字相同） |

🔴 **第 9 处是评审第 8 轮查出来的 —— 同一个病在起草过程中的第五次现场复发，且这一次最难堪的形态又重演了一遍**：
`docs/architecture/system-baseline.md:1016-1017` **本 plan 自己早就点到过** —— Phase 1 那条「§7.26 点名今天仍在别处
重复登记同一事实的位置」的执行项里，`system-baseline.md:1016-1017` **逐字列在清单里**（第 7 轮 SF 补进去的），
**却只被当成「要在 §7.26 里点名的重复登记」，没有任何一条执行项认领它本身已经为假**。
按本 plan 自己在下一段写死的口径（**补扫是执行期的 `Proof`，不构成范围内的认领**；指南规则 14：确认的 owner-doc 漂移不可降级）
⇒ **它必须进 B2 表、必须给 `Fix`**。`:1587-1588` 此前只作为 Phase 3 补扫的**待判候选**挂着，
本轮已实读判定为 `已过期` + `行号漂移` ⇒ **一并从候选升进范围**，不留给执行期再判一次。

⚠️ **第 7、8 处是评审第 7 轮查出来的 —— 这已是同一个病在起草过程中的第四次现场复发。**
**第 8 处尤其难堪**：它就在**本 plan 已经要动的那个文件里**（`roadmap`），只隔了 67 行。
⚠️ **它们会不会被 Phase 3 的十二词补扫捞到？会**（`零覆盖` / `COVERED` / `ruff` 三个词各自命中，且两个目录都在扫描范围内）——
**但补扫是执行期的 `Proof`，不构成范围内的认领**（指南规则 14：确认的 owner-doc 漂移不可降级）。
⇒ **两处都写进 B2 表、都给 `Fix`，不靠补扫兜底。**

🔴 **第 6 处是评审第 6 轮查出来的，而本 plan 自己的五关键词补扫**证明**命不中它** ——
`grep -n "commands.test\|unit-and-contracts\|复跑不到\|未声明\|dependencies" docs/architecture/module-boundaries.md | awk -F: '$1>4400 && $1<4500'` → **只有 `:4407` 与 `:4411` 两行**，`4424-4442` **一行都不命中**。
⚠️ **更难堪的一点，照实记**：本 plan 的 Phase 1 执行项自己引用了 `gates.yml:337`（说 `tests/ui` 在别的 job 里确实跑着），
B1 又自己引用了 `:682`（ruff 含 `tests/ui`）—— **两处真值都被本 plan 读到过，却没回头认领说它们假的那一段**。
**这是同一个病在起草过程中的第三次现场复发。**

⚠️ **第 6 处与前五处是不是同一个结果面？是**（第 3 轮曾对第 4 处逐字要求过同一句，第 6 处并进来时漏了补，
评审第 7 轮 SF-4 指出）：本 plan 的结果面是「**判定面缺口登记说真话**」，
而 §7.23.6 整节就是一份**判定面缺口登记**（标题逐字「CI 覆盖面：本节落地后**三处零覆盖**」）
⇒ 与 §7.7 / §12.5 是同一件事的不同落点，**不是另起一个 CI 治理的面**。第 7、8 处同理。

⚠️ **第 5 处是评审第 5 轮查出来的，起草稿与前四轮都漏了它** —— 它就在第 1 处（`:485-487`）**下方一行**，
同一节、同一段论证链上。**这是本 plan 要治的病在起草过程中的第二次现场复发**（第一次见下方第 4 处那条 🔴）。

⚠️ **第 4 处与前三处是不是同一个结果面？是 —— 一句话说清（评审第 3 轮要求）**：
本 plan 的结果面是「§12.5 / §7.7 这两段**判定面缺口登记**说真话」，
而第 4 处**就在第 3 处所在的同一段登记里、同一个「所以这层没被覆盖」的论证链上**
（原文逐字「真正解决要和"把 `tests/routing` 接进 CI"一起做」），**不是另起一个依赖治理的面**：
本 plan 不碰 `pyproject.toml` 一个字节，只删掉那句已被 `d5f0a04` 证伪的描述。

🔴 **第 4 处是独立评审查出来的，不是起草步查出来的** —— 起草步按关键词扫到了第 3 处，
**却把它下方 4 行的第 4 处漏掉，还把那句已过期的话当真话抄进了自己的 Non-Goals**。
照实记在这里：**这正是本 plan 要治的病在起草过程中的一次现场复发。**

### B3 · 是谁、什么时候把它们证伪的 —— 不是「还没来得及」

- `git log -S "③ 工具执行层（tests/tools）" -- .github/workflows/gates.yml` → **`b0ad632`，author `lize`，2026-08-24**，
  标题逐字「ci: 把 270 条裸奔的判据接进 CI，并加一条防再次漏接的判据」。
- 同一次落地还加了 **`:628` 第 ⑦ 步「没有测试目录被漏在 CI 之外」**，
  其 `:631` `COVERED` 逐字是 `contracts context experiments fixtures gates routing tools ui unit`
  —— **CI 侧已经有一条防漏接的元判据；owner doc 侧一条都没有。**
- 依赖那一处由 **`d5f0a04`（`lize`，2026-08-24）** 落地，标题逐字「fix(deps): certifi 从未被声明为依赖 —— CI 上 tests/routing 直接 ModuleNotFoundError」。
- **同源登记里只有 §7.6a 跟上了，B2 表里的每一行都没跟上**：
  `module-boundaries.md:324-326`（§7.6a 编排层）逐字已写着「`tests/tools`……**已在 CI 的 `unit-and-contracts` job 里**
  （2026-08-24 由人接进…），`lint` job 的 ruff 作用域也已含它」。
  ⇒ **这不是「文档整体滞后」，是同一批落地之后，除 §7.6a 外的每一处登记都留在原地。**
  ⚠️ **本节不写处数**（B2 顶部已说明理由：同一个「数字没跟上」的病在本 plan 正文里复发过三次）。
  ⚠️ **第 6 处不是 `b0ad632`/`d5f0a04` 那一批，是 `f795e47`（`lize`，2026-08-26）那一批** —— 同形态、不同批次。
- `module-boundaries.md` 此后被改过多次（最近 `38969b1`，2026-08-26），§7.7 那段始终没被碰。

### B4 · 这处漂移有实际代价，照实记

- **本仓已经为同一失败形态付过一次代价**：`STATE.md` §3 `[open] 2026-08-26T21:40Z` 逐字记着，
  `:751` 那条 `[open]` 的「今天没有任何判据拦得住这条路」被起草步**当活缺口反复读了四轮**（`:940` / `:952` / `:1543` / `:1551`）。
- **本例方向相反、更危险**：§7.7 末句逐字是「**不得因为本层测试自己是绿的就说「已被门禁覆盖」**」，
  §12.5 末句逐字是「**在人接进去之前，不得声称 CI 覆盖了 `tests/routing`**」——两句都是**行为禁令**。
  今天读它们的人会**低估**已有覆盖，从而 ① 为已解决的事重复登记 needs-human，
  ② 在评估「改坏了会不会被拦住」时按错误前提折价。
- **第三次复发就在本 plan 的起草过程里**（B2 第 4 处）。

### B5 · 今天的判定面实测（起草期本机实跑，收尾须原样复跑）

| 命令 | 退出码 | 输出 |
|---|---|---|
| `python3 tools/gates/check_expected_red.py` | **0** | `判定模式：default` · `门禁 29 项：预期红 0，绿 29，跳过 0` |
| `python3 -m pytest tests/unit tests/tools -q` | **0** | `920 passed, 29 skipped` |
| `python3 -m pytest tests/contracts tests/routing tests/context -q` | **0** | `386 passed, 1 skipped` |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` | **0** | `All checks passed!` |

`git rev-parse HEAD` → `bc7f13f` · `git status --porcelain | wc -l` → **2**
（两条都是同一轮起草步自己的产物：`?? docs/plans/p1-insight/2026-08-26-2213-1-…md`（本 plan）与
`?? docs/plans/p1-insight/2026-08-26-2213-2-case-ledger-marker-drift.md`（**同批起草的兄弟 plan**，
其 `Related:` 指回本 plan，自称同一失败形态的第 3 例）；
⚠️ **两次改准，两次都留痕**：起草首稿写 `0`，评审第 2 轮实跑证伪改成 `1`；
评审第 6 轮实跑再次证伪（兄弟 plan 此时已落盘），按实测改成 `2`）·
`git log --format='%an' -12 | sort -u` → 只有 `Email Agent Developer` ⇒ **人侧零新增提交、零新交办**。

### B6 · 仓里已有的同类判据（形状来源，不重新发明）

`tests/routing/test_routing_guard_registration.py`（164 行，`2101-1` 交付）已把
「owner doc 的登记表 ↔ 仓里真实判据」做成**双向同构 + 存活守卫 + 纳管边界**三件套，
文件头逐字声明「**本条只验存在性同构，不验语义**」。**本 plan 沿用它的形状，换掉它的两端。**

⚠️ **它踩过的坑逐字抄在这里**：`A == B` 而 `B` 由表自己导出 ⇒ 整表删空则 `A = B = ∅`，**判据静默绿**。
⚠️ **本 plan 的 `B` 不同源**：目录集合来自**文件系统实扫**、步骤来自 `gates.yml` 实读、`commands.test` 来自 `missions/*.json` 实读，
**三者都不由表导出** ⇒ `A == B == ∅` 那个陷阱在本条上按构造不成立，因此**不需要 `_REGISTERED_FILES` 那样的纳管常量**。
**这一句必须写进判据文件头**：省掉一个先例有过的守卫，必须说明为什么省得掉，而不是默默不写（见 `Phase 2` 的 `Decision` 与 `D3`）。

## 归属：本 plan 归工作项 4，且它**没有**占用任何其它工作项的 plan 预算

**先把规则的原文摆出来。** `02-WBS.md` 表规 3 逐字：「一个工作项 = **1–2 个 plan**（超过就拆行）」；
`DECISIONS.md` D-24 逐字：「loop 仍然不得自行加行」。
⇒ **这条规则计的是「一个工作项底下挂着几个 plan 文件」，不是「一个 plan 允许改哪些文档小节」。**

- **本 plan 是一个 plan 文件，`> Work Item:` 写死为工作项 4。** 处置对象 §7.7 是工作项 4 / P1.2 自己的落点节，该格 `1/2`。
- **它不为任何其它工作项创建 plan** ⇒ 工作项 1 / 3 / **11** 名下的 plan 计数**保持不变**
  （**工作项 11 是评审第 7 轮补进来的**：第 6 处 §7.23.6 与 Phase 1 要加时点限定的 `:4270`（§7.23.1）同属
  `module-boundaries.md:4255` 的 §7.23，其标题逐字 `⌘K 侧边栏本体……（**P1.8b 第 2 个 plan** · 2026-08-26）` = 工作项 11。
  ⚠️ **本节的唯一职责就是穷举「碰了谁的落点节」，而它此前漏了这一格** —— 照实记。
  另：第 7 处 `docs/context/project-context.md` **不属任何工作项的落点节**，不涉预算）（收口时以
  `grep -l '> Work Item: *3\.' docs/plans/p1-insight/*.md | wc -l` 一类命令实点复核）。
- **它对 §12.5 与 `roadmap:41` 的动作被限死成同一种形态：一条纯指针，重述零个事实**
  （删掉已被证伪的那半句 + 指向 §7.26），**不改那两处的任何结论、不碰 `agenerp/routing/**` 与 `tests/routing/**` 一个字节、
  不交付任何 P1.1 / P1.0a 能力**。
- ⚠️ **两轮独立评审在这一点上给出过相反的判读，照实记，不藏**：
  第 1 轮判「改 §12.5 = 洗白工作项 3 的预算」，要求收窄；本 plan 首稿据此收窄成「交人」。
  第 2 轮**实读表规 3 与 D-24 原文后推翻它**：逐字指出「表规 3 caps *plan count*, not which doc sections a plan may append to」，
  并指出首稿**自相矛盾** —— `roadmap:41` 那一行本身就写着工作项 1「表规 3 的 1–2 个 plan 预算就此用满（2/2）」，
  首稿却改它、不改 §12.5。**本稿取第 2 轮的读法，并把它写成一条可被人一次 `git revert` 推翻的取舍**（见 `D1`）。
- **决定性仓内先例（评审第 3 轮实读给出）**：`STATE.md:840` 记着工作项 6 的 plan
  `2026-08-25-0225-1-answer-judge-v0.md` 往 **§12.5**（工作项 3 的落点节）落过
  「`model-management.md` §12.5 落点指针（**5 增 0 删**）」，**独立收口审计通过、未记任何预算占用**。
  ⇒ **本 plan 与它同形态**（纯指针 + 删被证伪的从句）。
- **指南规则 14 的要求由此得到满足**：§12.5 那两句是**确认在线的 owner-doc 漂移**，
  且落在本 plan 自己声明的结果面上 ⇒ **它们必须在范围内被处置，不得降级为 follow-up**。

## Goals

- **G1** —— `module-boundaries.md` §7.7 末节**改准**：把已过期的事实**删掉、换成指向 §7.26 的指针**
  （**不在 §7.7 里重述一遍**，否则第二处真相源当场诞生）；原句逐字留痕在证据文件里。
- **G2** —— 新增**唯一一张机器可读的登记表**（`<!-- machine-read: ci-coverage -->` … `<!-- /machine-read: ci-coverage -->`），
  把 `tests/` 下**每一个**目录的判定面逐行写实，作为这件事在本仓的**单一真相源**。
- **G3** —— 新增一条判据，把该表与 `.github/workflows/gates.yml` + `missions/p1-insight.json` + 真实目录集合
  钉成**双向同构**，并覆盖「步骤被 `if:` / `continue-on-error:` 悄悄关掉」这一形态。
- **G4** —— `docs/backlog/p1-insight-roadmap.md:41` 追加**一条纯指针**（不改写已有字、不重述事实）。
- **G5** —— `model-management.md` §12.5 的 `:373-386` **逐从句改准**（删被证伪的从句 + 加指针，重述零个事实；
  判「真」的三行一个字不动），**同口径认领 §7.7 `:488` 的同一句与 §7.23.6（`:4424-4442`）的五条**，
  并在 `STATE.md` §3 追加一条行，写明归属取舍与它的推翻方式（一次 `git revert`）。
- **G6** —— 对**按 plan 分节的交付记录 / 带日期的探针快照**这一类（`module-boundaries.md:4270` ·
  `system-baseline.md` §14.7 `:1016-1017` 与 §14.10 `:1587-1588`）**不改写记录本身**，
  各加**一句时点限定 + 指向 §7.26 的指针**，使 G2 的「单一真相源」在 `docs/architecture/` 内部不被自己的副本推翻。
  ⚠️ **这一类与 G1/G5 的「就地删被证伪的从句」是两种口径，不许互相套用**：判断依据是「该段是否为带时点的账本/交付记录」。

## Non-Goals

1. **不改 `.github/workflows/**` 一个字节**（红线 2）—— 只读它、只登记它。
2. **不改 `missions/**` 一个字节** ⇒ **不把任何目录接进 `commands.test`**；
   「`GATE_VERIFY` 复跑不到 `tests/context` 等目录」这条缺口**一格都不修**，只写准并钉住。
3. **不改 `tests/gates/**` 一个字节**（红线 1）。表里关于 `tests/gates` 的行是**登记**，不是改动。
4. **不动 §7.6a**（`module-boundaries.md:324-331`）**与 §7.7 的 `:489`** —— 两者今天说的都是真话：
   `:329-330` 逐字是「loop 都无权自己动」（**真**，不是「在红线内」那种说法），`:331` 与 `:489` 同句式、
   **都没有「只有」** ⇒ **不是封闭计数**。有「只有三条」的只是 `model-management.md:381`（第 3 处，在范围内）。
   ⚠️ 起草稿曾把 `:489` 定性为封闭计数并为它开过一条 `Fix`，**评审第 5 轮实读推翻**，已删，原读法留痕在 Phase 3。
5. **不改 §12.5 的任何仍然成立的结论**：只删被证伪的从句、只加指针；
   §12.5 的档位表、判据表、`routing-guards` 登记表、`explain` 档指针、
   以及「不得声称……」那条禁令中仍成立的 `commands.test` 那一半**一个字不动**。
6. **不改任何产品代码**（`agenerp/**` 零改动），不交付任何 P1.2 运行时能力。
7. **不引入新依赖** —— 判据用纯文本行扫描读 `gates.yml`，**不 import `yaml`**。
   ⚠️ **理由是 CI 的实装面，不是 `pyproject` 缺声明**（后者已由 `d5f0a04` 解决，见 B2 第 4 处）：
   `gates.yml:601` 逐字 `pip install pytest certifi` ⇒ **runner 上没有 `yaml`**，import 它会让 `unit-and-contracts` 当场 `error`。
8. **不改 `docs/masterplan/` 的任何已有行**（红线 5），只在 `STATE.md` §3 **追加**。
9. **不评价 CI 的编排是否合理、不建议改 job 划分** —— 那是人的面。

## Task Route

- Type: `verification or audit work`（登记面改准 + 机械判据）
- Owner Docs: `docs/architecture/module-boundaries.md`（§7.7 改准 · 新增 §7.26）·
  `docs/architecture/model-management.md`（§12.5 两处**只删被证伪的从句 + 加指针**）·
  `docs/backlog/p1-insight-roadmap.md`（追加指针）
- 只读参照：`.github/workflows/gates.yml` · `missions/p1-insight.json` · `pyproject.toml` · `tests/`
- Skill Selection Basis: `none` —— `docs/skills/README.md` 下无对应技能；形状来源是仓内先例
  `tests/routing/test_routing_guard_registration.py`，不是外部技能。

## Infrastructure And Config Prereqs

- **No infra prereqs beyond existing baseline** —— 全程离线：零 docker、零网络、零凭据、零 LLM 调用、零 token 成本。
- 变异自查 **N1–N10 全部**在 `/tmp` 的整仓副本上施加（Phase 3 硬约束），**活仓工作树除本 plan 自己的产物外零改动**。

## Execution Plan

### Phase 1 — 把判定面的真值实测出来，并落成唯一一张登记表

Status: completed
Targets: `docs/architecture/module-boundaries.md`（新增 §7.26）· `docs/evidence/p1-ci-coverage-registration/`
Skill: `none`

- Item Types: `Proof | Decision | Add`
- Prereqs: 无

- [x] **Proof** · 逐目录实测四张来源，命令原文与输出**逐条落进** `docs/evidence/p1-ci-coverage-registration/README.md`：
      ① `ls -d tests/*/ | xargs -n1 basename | sort` ·
      ② `unit-and-contracts` job 里每条 `run: python3 -m pytest tests/<dir>` 步骤（含步骤序号、含该步是否带 `if:` / `continue-on-error:`）·
      ③ `lint` job 那条 **`run:`** 行的 `ruff check` 参数逐字 ·
      ④ `python3 -c "import json;print(json.load(open('missions/p1-insight.json'))['commands']['test'])"` ·
      ⑤ `gates.yml:631` 的 `COVERED` 字面值。
      ⚠️ 五条都是「读」——收尾 `git diff --name-only -- .github/ missions/` 必须无输出。
      - Skill: `none`
- [x] **Decision** · **纳管口径 = `tests/` 下的目录，不是文件。**
      备选 (A) 按文件纳管（`2101-1` 的口径）—— **否决**：表会退化成全量测试清单（`tests/unit` 一个目录就 60+ 文件）。
      备选 (B) 只纳管今天有缺口的三个目录 —— **否决**：那样「新增目录且忘了登记」不会红，
      而那正是 `gates.yml:628` 第 ⑦ 步在 CI 侧防的事。
      **选定 (C) 全目录纳管。** 残余风险照实记：`tests/fixtures` 是数据目录、没有 `def test_*`，
      它在表里也占一行，第 2/3 列写「不跑 / 不在」——**这是事实，不是缺口**。
      - Skill: `none`
- [x] **Add** · 在 `module-boundaries.md` **文末新增 §7.26**（§7.25 起于 `:4611`、文件止于 `:4715`，
      **§7.25 及其之前一个字不改**），含**成对**标记 `<!-- machine-read: ci-coverage -->` …
      `<!-- /machine-read: ci-coverage -->`（对齐先例 `model-management.md:98`/`:162`），表六列：
      `目录` · `unit-and-contracts 里的哪一步`（`①`–`⑦` 或 **`本 job 里不跑`**）· `步骤是否被条件/软失败削弱`（`否` / 逐字写出该条件）·
      `lint（ruff）作用域`（`在` / `不在`）· `missions/p1-insight.json 的 commands.test`（`在` / `不在`）· `实测日期 · 证据路径`。
      - Skill: `none`
- [x] **Add** · 第 2 列的措辞必须是「**本 job 里**不跑」，并在表下逐字点名
      **在别的 job 里确实跑着的两项**：`tests/ui`（`gates.yml:337`，`gates-l2-live`）·
      `tests/gates`（`:208` `gates-l2` / `:561` `gates-l2-seed` / `check_expected_red.py`）。
      ⚠️ 少了这一句，这张表就会复刻 B4 诊断的那种**低估**。
      - Skill: `none`
- [x] **Add** · §7.26 正文逐字写清**这张表不管什么**：不管 live 面的 job（`gates-l2` / `gates-l2-live` / `gates-l2-seed`）、
      不管 `tools/gates/check_expected_red.py` 的判定域、不管条数、不管断言质量。
      ⚠️ 理由：`docs/audits/2026-08-26-CP9-P1-retrospective.md:95` 逐字「核了门禁绿不绿，没核绿的门禁在测什么」
      （⚠️ 起草稿把出处写成 §1.2，评审第 3 轮实读为 `:95`、属 §3，按实测改准）——
      一条判据有义务先说清自己名字之外的边界。
      - Skill: `none`
- [x] **Add** · §7.26 逐字声明它是**这件事的单一真相源**，并点名今天仍在别处重复登记同一事实的位置
      （`gates.yml:631` 的 `COVERED`、`model-management.md` §12.5、**`module-boundaries.md:4270`**、
      **`docs/context/project-context.md:52`**、**`docs/architecture/system-baseline.md:1016-1017`**），**说明各自归谁**。
      ⚠️ **`:4270` 的判词是「已过期的快照」，不是「已过期的断言」**（评审第 6 轮 BL-4）：它是 §7.23.1
      **执行期探针 `H1` 的实际值**（逐字 `相等：context contracts experiments fixtures gates routing tools unit`，**八项**），
      而两端今天都是**九项**（含 `ui`）、引的 `gates.yml:597` 已漂到 `:628`/`:631`。
      **带日期的探针快照按本仓惯例是追加式账本，不改写内容** ⇒ 处置只有一件：
      **加一句指向 §7.26 的时点限定**（「该值为 <日期> 的观测；当期真值见 §7.26」）。
      **不加这一句，G2 的『单一真相源』会在同一份 owner doc 内当场被推翻。**
      - Skill: `none`

Exit Criteria:

- [x] §7.26 存在，成对标记齐全，表的数据行数 == `ls -d tests/*/ | wc -l` 实测值
      （**起草期实测为 `9`**：`context contracts experiments fixtures gates routing tools ui unit`；
      钉死这个数，执行期才分得清「目录真的新增了」与「表漏了一行」），逐行与 Phase 1 ① 一致
- [x] `git diff --numstat bc7f13f -- docs/architecture/module-boundaries.md` 的**删除列为 0**
      —— ⚠️ **判定时点限定为「Phase 1 的提交落地时」**（`git diff --numstat bc7f13f <Phase1 提交 sha> -- …`）。
      Phase 3 会对同一文件的 §7.7 与 `:488` 删从句 ⇒ **收口时刻整体复跑必然非 0，那是正常的**，不许拿来判本条不达标
- [x] `docs/evidence/p1-ci-coverage-registration/README.md` 落盘，五条实测命令原文 + 输出俱全
- [x] `docs/logs/2026/08-26.md` 更新

### Phase 2 — 判据：登记表与三张判定面双向同构

Status: completed
Targets: `tests/unit/test_ci_coverage_registration.py`（新增）
Skill: `none`

- Item Types: `Decision | Add | Proof`
- Prereqs: Phase 1（表必须先存在）

- [x] **Decision** · **判据落 `tests/unit/`。**
      备选 (A) 落 `tests/context/`（本 plan 归工作项 4）—— **否决**：本条判的是全仓复跑面登记，不是上下文层行为；
      且 `tests/context` 不在 `commands.test` 里，**一条防漂移的判据自己复跑不到等于降一档**。
      备选 (B) 落 `tests/gates/` —— **红线 1，无权**。
      **选定 (C) `tests/unit/`**：`module-boundaries.md:541-543` 逐字记着 `tests/unit` 是今天**唯一**同时进
      `commands.test` 与 CI 的目录，§7.8 的 D5 是同一选择的先例。
      **残余风险**见 `D2`，缓解写进下一条。
      - Skill: `none`
- [x] **Add** · 失败文案硬要求：任何一条断言失败都必须逐字打印
      「哪一行 · 表说什么 · 仓里实际是什么 · 该改哪个文件的哪一列」。
      ⚠️ **这是 `D2` 的唯一缓解** —— 不接受「把判据挪出 `commands.test` 以免拖红」这种缓解。
      - Skill: `none`
- [x] **Add** · **七条断言**，逐条对应一种漂移：
      ① **目录集合三向同构**：表的目录列 == `ls -d tests/*/` 实扫 == `gates.yml:631` 的 `COVERED`
      （三者两两相等；`COVERED` 是 SF 指出的第二份机器可读副本，一并咬住）·
      ② **`unit-and-contracts` 步骤列双向**，**两个方向逐字分开写死**：
      **②a（表 → CI）** 表说「第 N 步」的目录必须真有一条 `run: … pytest tests/<dir>` 步骤且序号一致；表说「本 job 里不跑」的必须真的没有 ·
      **②b（CI → 表）** `unit-and-contracts` 里每一条裸目录 `pytest tests/<dir>` 步骤都必须在表里有对应行且序号一致 ·
      ⚠️ **变异表里凡写「红 · 断言②」的，一律指 ②a 与 ②b 中的哪一支要逐条写明**（**N4 / N7 红在 ②a**「表说有、CI 里没有」；**N10 与 N8 的两次「去掉约束则转红」红在 ②b**「CI 里有、表里没有」） ·
      ③ **`lint` 列双向**：只与 `lint` job 里那条 **`run:`** 行的 `ruff check` 参数对齐
      （⚠️ **不许匹配 `name:` 行** —— 评审实测：首匹配解析器会把 `name:` 行读成 `['tests/']`）·
      ④ **`commands.test` 列双向**：与 `missions/p1-insight.json` 的 `commands.test` 里
      **全部** `tests/<dir>` 路径参数对齐（⚠️ **不许只读第一个** —— 评审实测：首 token 解析器在
      `pytest tests/unit tests/context -q` 上只读到 `tests/unit`，`N6` 会**保持绿**）·
      ⑤ **存活守卫**：表的数据行非空，**且七条断言各自在「表为空」时立即短路返回**，
      使整表删空**只红在⑤上**。⚠️ **评审第 3 轮实测：去掉逐条短路后是 `2 failed`（①与⑤），不是 `7 failed`**
      —— 起草稿写的 `7` 已被证伪，按实测改准，原值留痕于此；**要求不变**（N3 必须单点红在⑤）。
      先例是 `tests/routing/test_routing_guard_registration.py:118-124` 的存活守卫，
      ⚠️ 但那是**一条测试内部的顺序**，本条是**七条各自短路**，形态不同，不许写成「口径同先例」 ·
      ⑥ **第 6 列可判定的那一半**：日期可 `date.fromisoformat`、证据路径存在
      （⚠️ **钉不住「日期是否新鲜」**，见 `D3`）·
      ⑦ **步骤未被悄悄关掉**：第 2 列点名的每一步**不得**带 `if:` 或 `continue-on-error:`，
      且 `unit-and-contracts` job 本身不得带 `if:`；表的第 3 列必须逐字反映实际。
      ⚠️ **⑦ 必须跳过「表里点了名、但步骤表里根本查不到」的目录**（那种情形归②报）——
      不跳则 `N2` 会额外把⑦也打红（评审实测 `4 failed`）。
      ⚠️ **这一条是评审在 `/tmp` 原型上实测出来的缺口**：只有前六条时，给第 ⑤ 步加 `if: false`
      或 `continue-on-error: true`，判据**仍然 exit 0**，而表和 §7.7 仍宣称「CI 复跑得到」。
      两种写法在该文件里**都已实际存在**（`gates.yml:211` · `:367-368`）。
      - Skill: `none`
- [x] **Add** · 解析器写死为**纯文本行扫描**（不 import `yaml`，Non-Goals 7），**两条形状约束缺一不可**：
      ① **认出 job 边界** —— 只在 `unit-and-contracts:` 与下一个 job 之间找步骤 ·
      ② **步骤的目录参数必须是「裸目录」**（`pytest tests/<dir>` 后面紧跟空白或行尾），
      **不认文件路径** —— 否则 `gates.yml:208` 的 `pytest tests/gates/test_zero_dep_boot.py` 会把 `gates` 算成一步。
      ⚠️ **两条约束在今天的基线上互为「另一条的替身」，照实记（评审第 3 轮实测，起草稿与第 2 轮的说法均被证伪）**：
      去掉①保留② → 基线 `7 passed`；去掉②保留① → 基线 `7 passed`；**两条都去掉 → 基线 `1 failed`（`test_02`）**。
      成因是 `unit-and-contracts` 里今天六条步骤**全是裸目录**（`:604 :607 :615 :618 :621 :624`），
      而 `:208` / `:337` / `:561` 都在别的 job 里。
      ⇒ **起草稿那句「不加②则基线就红」是假的**，原句留痕于此。
      **两条的活性各由一对变异证明，缺一不可**：`①` 由 `N7`（去边界则转绿）+ `N8`（去边界则转红）；
      `②` 由 `N10`（去②则转红，见 Phase 3）。
      - Skill: `none`
- [x] **Add** · 判据文件头逐字写清三件事：① 本条只验存在性同构、不验语义（沿用先例措辞）·
      ② **为什么本条不需要 `_REGISTERED_FILES` 那样的纳管常量**（`B` 三路来源都不由表导出，
      `A == B == ∅` 按构造不成立）· ③ `D2` 那条残余风险。
      - Skill: `none`
- [x] **Proof** · `python3 -m pytest tests/unit/test_ci_coverage_registration.py -q` → exit 0，
      **收集条数 == 断言体里 `def test_` 条数**（「零 skip」在一条都没跑时也成立，由条数钉住）。
      - Skill: `none`

Exit Criteria:

- [x] 七条断言全部落地且默认全绿
- [x] `python3 tools/gates/check_expected_red.py` → exit 0，**`门禁 29 项` 不变**（本 plan 不新增门禁）
- [x] `python3 -m pytest tests/unit tests/tools -q` → exit 0，`passed` 数**只增不减**（基线 920）
- [x] `ruff check …`（B5 那条原样）→ exit 0
- [x] No owner-doc update required（判据说明已在 Phase 1 的 §7.26 落地）
- [x] `docs/logs/2026/08-26.md` 更新

### Phase 3 — 变异自查（活仓零改动）+ §7.7 与 §12.5 就地改准 + 收口落盘

Status: completed
Targets: `docs/architecture/module-boundaries.md`（§7.7 · `:488` · §7.23.6）· `docs/architecture/model-management.md`（§12.5）·
`docs/architecture/system-baseline.md`（§14.7 / §14.10，**仅追加时点限定**）· `docs/context/project-context.md`（`:52`）·
`docs/backlog/p1-insight-roadmap.md` · `docs/backlog/tools-dir-has-no-static-check-coverage.md`（**仅追加时点限定**，补扫查出）·
`docs/masterplan/STATE.md`（**仅追加**）· `docs/evidence/p1-ci-coverage-registration/`
Skill: `none`

- Item Types: `Proof | Fix | Decision`
- Prereqs: Phase 2，且 **Phase 1/2 的产物必须先提交** ——
  否则「活仓工作树零改动」这条判据是自欺。⚠️ 口径逐字定死为
  **`git status --porcelain` 除 `docs/plans/p1-insight/2026-08-26-2213-*.md` 两个文件外无输出**
  （B5 实测：开工时该命令输出 **2** 行 —— 本 plan 与同批起草的 `…-2213-2-case-ledger-marker-drift.md`。
  ⚠️ **口径点名到那两个文件，不写「本 plan 自己」** —— 后者按字面在执行期必然判不达标，评审第 6 轮 BL-3 实测）

- [x] **Proof** · 🔴 **硬约束：N1–N10 十条全部在 `/tmp` 的整仓副本上施加**（`cp -r` 到 `/tmp`），
      **活仓工作树除 `docs/plans/p1-insight/2026-08-26-2213-*.md` 两个文件外零改动**。⚠️ 不许「反正会复原」就在活仓施加 ——
      那一步一旦中断，仓里就留着一个被改松的门禁面或一份被改假的 owner doc。
      每条施加后在副本上复跑判据、记录退出码与失败文案首行，然后**丢弃整份副本重新拷贝**（比逐条复原更难出错）。
      - Skill: `none`
- [x] **Proof** · **变异表，逐条先写死预测再施加**：

      | # | 变异 | 预测 |
      |---|---|---|
      | N1 | 删掉表里 `context` 那一行 | 红 · 断言① |
      | N2 | 表里 `routing` 改成 `routinq` | 红 · **①②③ 三条同时红**（评审实测；本条不要求单点红，⑦ 因其跳过规则不红） |
      | N3 | 整表删空 | 红 · **仅断言⑤**（七条各自对空表短路，⑤ 守在①之前） |
      | N4 | 副本 `gates.yml` 删掉第 ⑤ 步 | 红 · 断言**②a**（表说第 ⑤ 步、CI 里已没有）（⑦ 跳过 ⇒ 单点红；评审实测：不跳则 `2 failed`） |
      | N5 | 副本 `ruff check` 参数删掉 `tests/context` | 红 · 断言③ |
      | N6 | 副本 `commands.test` 加进 `tests/context` | 红 · 断言④ |
      | N7 | 副本把第 ⑤ 步**整条挪进 `gates-l2-live`** | 红 · 断言**②a**（表说它在 `unit-and-contracts` 第 ⑤ 步、该 job 里已没有）（⑦ 跳过 ⇒ 单点红）。**去掉 job 边界则转绿** ⇒ 边界活性证明之一 |
      | N8 | 副本在 `gates-l2-live` 里**插入** `- run: python3 -m pytest tests/fixtures -q` | **必须保持绿**（**两条 must-stay-green 之一，另一条是 N10**）。**去掉 job 边界则转红在断言②b** ⇒ 边界活性证明之二 |
      | N9 | 副本给第 ⑤ 步加 `continue-on-error: true`（另跑 `if: false` 与 job 级 `if:` 各一遍） | 红 · 断言⑦（三个变体各一次） |
      | N10 | 副本在 `unit-and-contracts` 里**插入** `- run: python3 -m pytest tests/fixtures/x.py -q` | **必须保持绿**（第二条 must-stay-green）。**去掉「裸目录」约束则红在断言②b** ⇒ ②b 的活性证明 |

      **任何一条与预测不符 ⇒ 当场补断言并全表复跑，经过逐字记进证据文件；不许把打不红的那条从表里删掉。**
      - Skill: `none`
- [x] **Fix** · `module-boundaries.md` §7.7 末节**就地改准**：把已过期的 CI 那半句**删掉**，
      **不在此处重述新事实**，改成一句指向 §7.26 的指针；
      `commands.test` 那一半与末句「不得因为本层测试自己是绿的就说「已被门禁覆盖」」**逐字保留**。
      **原段落逐字留痕进证据文件。**
      - Skill: `none`
- [x] **Decision** · `roadmap:41` 的处置形态 = **一条纯指针，不重述事实**。
      备选 (A) 在 roadmap 行内写出新事实 —— **否决**：那是 G2 要消灭的第二处真相源。
      备选 (B) 一个字不动 —— **否决**：它是引擎每轮实读的文件，留着已知为假的话有实测代价（B4）。
      **选定 (C)**：追加一句「该句已过期，`tests/tools` 的复跑面以 `module-boundaries.md` §7.26 表为准」+ 证据路径。
      **残余风险**（指南规则 9）：`roadmap` 由引擎在 closure 审计后回写，**本 plan 的追加句可能被后续回写挤远、被读者错过**，
      而该行已有的假话仍在原地；缓解只有「追加句紧贴假话之后」这一条，**挡不住整行被后续追加淹没**。
      ⇒ 登记为 `D5`，重开事件写在那里。
      - Skill: `none`
- [x] **Fix** · 按上一条落地 `roadmap:41` 的追加（**不改写该行已有的任何一个字**）。
      - Skill: `none`
- [x] **Proof** · **再扫一遍同形态**：`grep -rn "commands.test\|unit-and-contracts\|复跑不到\|未声明\|dependencies\|零覆盖\|COVERED\|ruff\|任何 job\|不会被任何\|会红\|仍然不等" docs/architecture/ docs/backlog/ docs/context/ docs/design/`
      逐条读原文，把「今天仍成立 / 已过期」逐条判出来记进证据文件。
      ⚠️ **关键词表被两次实测证伪过，两次都留痕**：起草期只按前三个词扫 ⇒ 漏了 B2 第 4 处（评审第 2 轮）；
      扩到五个词之后**仍然命不中 B2 第 6 处**（评审第 6 轮用 `awk` 机械证明：`4424-4442` 区间零命中）
      ⇒ 本轮再扩到十二个词，范围由两个目录扩到**四个**（补 `docs/context/` 与 `docs/design/`，SF-4）。
      ⚠️ **它仍然是关键词扫描，不是全文逐行复核** —— 已经漏过两次，**不许写成「扫完就没有了」**，边界见 `D4`。
      ⚠️ **判词口径先写死，三分不合一**（评审第 5 轮指出本条必然命中 `module-boundaries.md:4407`，
      它引的 `gates.yml:567` 是**内容真、行号漂**）：**`成立`**（内容与行号都对）·
      **`行号漂移`**（引文内容仍能在该文件里逐字找到，只是行号变了）· **`已过期`**（内容本身已被证伪）。
      **起草期已实读到的候选先写进来，执行期只做增补、不从零扫**：`module-boundaries.md:4407` ·
      `system-baseline.md:1623` ·（⚠️ **`system-baseline.md:1587-1588` 已于评审第 8 轮实读判为 `已过期` + `行号漂移`，升进 B2 第 9 处的范围内 `Fix`，不再是本条的待判候选**） `docs/backlog/tools-dir-has-no-static-check-coverage.md:18` ·
      `docs/backlog/gates-and-tools-leak-env-across-directories.md:37`（评审第 7 轮 SF-7 点名，逐条判词由执行期定）。
      **同一行可同时判两个词**（`已过期` + `行号漂移`，例如 §7.23.6 的 `:4428` `:4433` 与 `:4270` 引的 `gates.yml:597`）
      —— **判词是集合不是单选**。**只有集合里含 `已过期` 的才进本 plan 的改准范围**；判 `行号漂移` 的**逐条记进证据文件并留在原地**
      （改行号不是本 plan 的结果面，且行号会随任何一次编辑再漂）。
      - Skill: `none`
- [x] **Fix** · `model-management.md` **§12.5 的 `:373-386` 两段，逐从句处置**（评审第 3、4 轮逐行实读补齐，
      **十行逐条点名，不许整段重写：3 行判真逐字保留、7 行须改（4 假 + 2 半真 + 1 前提已失效）**）：

      | 行 | 逐字 | 今天 | 处置 |
      |---|---|---|---|
      | `:374` | `tests/routing` 不在 `commands.test` 里 | **真** | 逐字保留 |
      | `:375-376` | 「也不在 `gates.yml` 的任何 job 里（作用域是 `tests/unit` `tests/contracts`…）」 | **假**（`:617-618` ④ + `:682` ruff） | 删，换指向 §7.26 的指针 |
      | `:377` | 「`tests/tools` 是**同形态的**第一条缺口，`tests/routing` 是第二条」 | **半真**（缺口只剩 `commands.test` 那一侧） | 就地收窄到 `commands.test` 一侧 |
      | `:378` | 「两者都要人来接（`missions/**` 与 `.github/workflows/**` 都在红线内，loop 不得动）」 | **半真，且错在两处**：① workflows 那半已由 `b0ad632` 接完 ② **`missions/**` 根本不在红线内** —— `AGENTS.md:8-16` 七条红线实读无它，出处是 `docs/context/ai-autonomy-policy.md:87` 的 Protected Areas（`missions/*.json` 标 `blocked`） | 收窄到 `missions/**` 一侧，**并把「在红线内」改成「在 `ai-autonomy-policy.md` 的 Protected Areas 里标 `blocked`」**（仓内已有正确写法可照抄：`STATE.md:762`） |
      | `:379` | 「已在 `STATE.md` §3 追加 needs-human」 | **真** | 逐字保留 |
      | `:380` | 「**在人接进去之前，不得声称 CI 覆盖了 `tests/routing`**」 | **前提已失效**（人 2026-08-24 就接进去了） | 删，换成与今天相符的禁令：**不得声称 `GATE_VERIFY` 复跑得到 `tests/routing`** |
      | `:381-382` | 「本层现有的代偿控制**只有三条**」 | **假**（漏了 `d18c05c` 的门禁、§12.5 自己的 `routing-guards` 表、以及 CI 第 ④ 步） | 删「只有三条」这个封闭计数，换指针 |
      | `:384` | 「`pyproject.toml` 没有声明 `dependencies`，`certifi` 至今是未声明的依赖」 | **假**（`pyproject.toml:14-16`，`d5f0a04`） | 删，换指向 `pyproject.toml:14-16` 的指针 |
      | `:385` | 「本层用惰性 import 与两道反测把它挡在被 CI import 到的路径之外」 | **真** | 逐字保留 |
      | `:386` | 「这不等于依赖问题解决了 —— 真正解决要和把 `tests/routing` 接进 CI 一起做，同属人的活」 | **假**（两件事今天都已发生） | 删 |

      **口径：只删被证伪的从句 + 加指针，重述零个事实；表里判「真」的三行（`:374` / `:379` / `:385`）一个字不动。**
      **原两段逐字留痕进证据文件。**
      ⚠️ **为什么七行一起改**：指南规则 14 逐字「确认的 owner-doc 漂移不可降级」，
      七行**同源同因**（`b0ad632` / `d5f0a04` / `d18c05c` 三次人侧落地），留下任何一处等于把本 plan 要治的病留在原地。
      ⚠️ **`:380` 是评审第 4 轮才挖出来的**：起草稿与前三轮都把它当成「含 `commands.test` 那一半、可以整句保留」，
      **实读它一个 `commands.test` 都没有** —— 那一半在 `:374`。照实记，原读法留痕于此。
      - Skill: `none`
- [x] **Fix** · `module-boundaries.md` **`:488`**（§7.7，逐字「`missions/**` 与 `.github/workflows/**` 都在红线内，loop 无权自己补。」）
      —— 与 §12.5 `:378` **同一句、同两处错**：① workflows 那半已由 `b0ad632` 接完 ② `missions/**` 不在红线内。
      **同一处置**：收窄到 `missions/**` 一侧 + 把「在红线内」改成「在 `ai-autonomy-policy.md` 的 Protected Areas 里标 `blocked`」。
      ⚠️ **它此前未被任何一条执行项认领**（评审第 5 轮实读，plan 全文 grep `488` 零命中）——照实补上。
      ⚠️ **不动 `:489`**（「代偿控制：……」那一行）：评审第 5 轮实读它与 §7.6a `:331` **同句式、都没有「只有」**，
      **不是封闭计数** —— 有「只有三条」的只是 `model-management.md:381`。起草稿把它定性为「封闭计数」是**误读**，
      原读法留痕于此，处置按 Non-Goals 4 归入不动之列。
      - Skill: `none`
- [x] **Fix** · `module-boundaries.md` **§7.23.6（`:4424-4442`）逐条处置**（B2 第 6 处；评审第 6 轮查出，
      **本 plan 自己的补扫命不中它**）。按三分口径逐条判，**判词集合里含 `已过期` 的才改**：

      | 行 | 逐字 | 今天 | 处置 |
      |---|---|---|---|
      | `:4428` | 「`gates.yml:597` 第 ⑦ 步……**会红**」 | **已过期 + 行号漂移**（`COVERED` 含 `ui`，9 == 9 ⇒ 不红；`:597` 已漂到 `:628`/`:631`） | 删「会红」这个断言 + 指向 §7.26；行号一并改准 |
      | `:4430-4431` | 「**新门禁在 CI 上零覆盖**……`tests/ui/test_sidebar.py` **不会被任何 job 跑到一次**」 | **已过期**（`gates.yml:337` 在 `gates-l2-live` 里逐字跑它） | 删被证伪的从句 + 指向 §7.26 |
      | `:4433` | 「`tests/ui` 在 CI 上**零 lint 覆盖**：`gates.yml:646` 的 ruff 参数是**七个**目录」 | **已过期 + 行号漂移**（`:682` 八个参数，含 `tests/ui`；`:646` → `:682`） | 删被证伪的从句 + 指向 §7.26；**行号一并改准**（口径与 `:4428` 逐字相同，不写「同上」） |
      | `:4436-4437` | 「六件全部落在 `.github/workflows/**` 里 ⇒ 红线 2，**本节与本 plan 一个字节都不碰**」 | **已过期**（`STATE.md:1152-1153`：六件全部由 `f795e47` 做掉，带 `Gates-Change-Approved-By:`） | 删「待人做」的口吻 + 加结案指针；**「红线 2 归人」这条仍然成立，逐字保留** |
      | `:4440-4442` | 「`gates.yml:640` 那句『三个目录』**仍然是错的**；真相源八个而 `:646` 七个，**两边仍然不等**」 | **已过期**（`:674` 今天逐字「作用域**八个目录**」，`:682` 亦八个 ⇒ 相等） | 删被证伪的两句 + 指向 §7.26 |

      **口径与 §7.7 / §12.5 完全相同：只删被证伪的从句 + 加指针，重述零个事实。原段落逐字留痕进证据文件。**
      ⚠️ **标题里的「三处零覆盖」也已过期**，随正文一并改准。
      ⚠️ **本处与前五处不同批次**：前者源于 `b0ad632` / `d5f0a04`（2026-08-24），本处源于 **`f795e47`**（`lize`，2026-08-26）。
      - Skill: `none`
- [x] **Fix** · `docs/context/project-context.md:52`（B2 第 7 处）**就地改准**：删掉被 `f795e47` 证伪的三段
      （① `gates.yml` 注释「三个目录」仍错 ② 八 vs 七「仍然不等」 ③ `tests/ui` 在 CI 上零 lint 覆盖 + 「残余两处逐字交人」），
      换成指向 §7.26 的指针。**该行其余部分（真相源本体、2026-08-23 追加段、`F401` 变异实测、规则集边界）一个字不动。**
      ⚠️ **它不在任何红线 / Protected Areas 内** —— `ai-autonomy-policy.md:77-90` 实读无 `docs/context/**`，
      且 `module-boundaries.md:4439` 自己就写着「它不在任何红线内」⇒ **loop 有权改，改它不是越界。**
      ⚠️ **本处是「入口文件」** —— `project-context.md` 是每轮 mission-driver 第一个读的文件，
      留着已知为假的话，代价比 owner doc 深处那几处大。
      - Skill: `none`
- [x] **Fix** · `docs/architecture/system-baseline.md` **§14.7 `:1016-1017` 与 §14.10 `:1587-1588`**（B2 第 9 处）——
      **处置形态与 `:4270` 逐字相同、与第 1/6/7 处不同**：两处都在 `## 14.x …（plan <X> 交付）` 这种**按 plan 分节的交付记录**里
      ⇒ **不改写记录本身的任何一个字**，各加**一句时点限定 + 指向 §7.26 的指针**
      （「该形态为 <该节交付日> 的记录；`lint` job 的当期作用域见 `module-boundaries.md` §7.26」）。
      ⚠️ **行号漂移（`:1587` 引的 `gates.yml:426`，今天 `lint` job 键在 `:663`）按三分口径记进证据文件、留在原地**，
      与 `:4428` / `:4433` 那两条「行号一并改准」的口径**不同** —— 那两条是因为同一句本来就要改，这两处一个字都不改写。
      ⚠️ **该文件不在任何红线 / Protected Areas 内**（`ai-autonomy-policy.md:77-90` 实读无 `docs/architecture/**`）⇒ loop 有权追加。
      ⚠️ **不加这两句，G2 的『单一真相源』会被同一份 `docs/architecture/` 里的第三、第四份副本当场推翻** —— 与第 6 轮 BL-4 同一条理由。
      - Skill: `none`
- [x] **Fix** · `docs/backlog/p1-insight-roadmap.md:108`（+ `:109` 括号半句，B2 第 8 处）——
      **形态与 `roadmap:41` 相同，不与第 1/6/7 处相同**：它是**引擎回写的账本行**
      ⇒ **不改写该两行已有的任何一个字，只追加一句纯指针 + 证据路径**（取舍已由 `D5` 写死，本条直接复用，不另立）。
      ⚠️ **它就在本 plan 已经要动的那个文件里，只隔 67 行，而起草稿与前六轮都没看见** —— 照实记。
      - Skill: `none`
- [x] **Proof** · `STATE.md` §3 追加**一条** `[open]` 证据行：命令原文 + 退出码 + commit sha + 红线自证 +
      `verification scope limited`，并**逐字记下归属节那条取舍与两轮评审的相反判读**，
      写明**推翻方式**：人若不认同，`git revert` 掉 §12.5 那一处 hunk 即可，其余交付物不受影响。
      - Skill: `none`

Exit Criteria:

- [x] N1–N10 **十条全部与预测吻合**（含 N8 / N10 两条保持绿、N9 的三个变体各红一次），经过逐字落进证据文件
- [x] `git diff --name-only bc7f13f -- .github/ missions/ tests/gates/ docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md` → **无输出**
- [x] `model-management.md` §12.5 的改动**只有删从句 + 加指针**：`git diff` 逐 hunk 复核，
      **零新增事实（删除除外）、零仍成立结论被改动**
- [x] §7.7 改准且**不含任何被重述的事实**；原段落逐字留痕在证据文件里
- [x] `roadmap:41` 追加完成，该行已有字**零改动**（`git diff` 逐字复核）
- [x] `roadmap:108-109` · `project-context.md:52` · `system-baseline.md` §14.7 / §14.10 三处按各自口径落地：
      前二者见 B2 第 7/8 行；`system-baseline.md` 的改动**只有追加时点限定** ——
      `git diff --numstat <Phase3 起点 sha> -- docs/architecture/system-baseline.md` 的**删除列为 0**
- [x] B5 四条命令**收尾原样复跑**，退出码与输出记进 `STATE.md` 追加行
- [x] `STATE.md` §3 的 `[open]` 行已落地，含归属取舍、两轮相反判读、推翻方式
- [x] `docs/logs/2026/08-26.md` 更新

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，全新会话，2026-08-26，task `ae3b673`）——
  开出 **6 条 blocking + 9 条 should-fix**，并在 `/tmp` 整仓副本上**跑了一版判据原型**（活仓零改动）。
  **逐条处置**：
  - **BL-1 预算洗白**（自称结果面是「全仓」却只记工作项 4 的账，而 §12.5 属工作项 3、该格 `2/2` 已满）
    →**采纳其 fallback**：范围收窄成 §7.7 + §7.26 + 判据 + `roadmap` 指针；
    §12.5 两处**改为交人**（新增 `D1` + Phase 3 的 `[needs-human]` 执行项），并新增专节写明归属论证。
  - **BL-2 首稿 Non-Goals 抄了一句已过期的话**（`pyproject.toml 没有声明 dependencies`，实为
    `pyproject.toml:14-16` 已由 `d5f0a04` 声明 `certifi`）→ Non-Goals 7 的理由改成 CI 实装面
    （`gates.yml:601` 只装 `pytest certifi`）；该处作为 **B2 第 4 处**入表；新增 Phase 3 的关键词补扫项。
  - **BL-3 判据在 `if: false` / `continue-on-error: true` 下静默绿**（评审在原型上实测）→ 新增**断言⑦**与变异 **N9**。
  - **BL-4 `G2` 的「单一真相源」被 Phase 3 自己推翻**（同一事实又写进 §7.7 / §12.5 / roadmap 三处）
    → §7.7 与 roadmap 改成**纯指针、不重述事实**；§12.5 交人时也逐字建议同一修法。
  - **BL-5 无变异覆盖 job 边界解析**（原 N7 打的是别的靶）→ 变异表重写为 N1–N9，
    新增 **N7（挪步骤进 `gates-l2-live`）** 与 **N8（当时是唯一一条 must-stay-green；`N10` 于第 3 轮才新增）**。
  - **BL-6 Phase 1 的「Proof-heavy 3/5」是假的、且不满足指南规则 7 的 80% 门槛** → 删掉该声明，改用逐项标签。
  - **SF-1**（`ruff` 只匹配 `run:` 行）· **SF-2**（⑤ 短路在 ① 之前，点名先例行号）· **SF-3**（Phase 3 前置：先提交）·
    **SF-4**（九条变异全部落 `/tmp` 副本）· **SF-5**（成对标记）· **SF-6**（`COVERED` 一并咬住，写进断言①）·
    **SF-7**（说明为什么不需要纳管常量，写进判据文件头与 `D3`）· **SF-8**（全文 `§12.x` 改为 `§12.5`）·
    **SF-9**（`D4` 的依据改准）—— **九条全部采纳并落到具体条目上。**
- Independent draft review iteration 2: **needs revision**（独立子代理，全新会话，2026-08-26，task `a91b587`）——
  **在 `/tmp` 整仓副本上跑通了七条断言的原型并实跑九条变异**（活仓零改动），
  报「**With a compliant parser, all nine predictions hold exactly as written**」，
  并开出 **3 条 blocking + 10 条 should-fix**。**逐条处置**：
  - **BL-A 首稿自相矛盾**：一边以「工作项 3 预算 2/2 满」为由不改 §12.5，一边改了 `roadmap:41` ——
    **而那一行本身就写着工作项 1「表规 3 的 1–2 个 plan 预算就此用满（2/2）」**；
    且评审实读表规 3 原文，指出它 caps *plan count*，不 caps 可改的文档小节。
    → **本稿取评审的读法**：§12.5 两处改为**同一形态的纯指针**（Phase 3 的 `Fix`），
    重写「归属」专节写死规则原文与两轮相反判读，`D1` 改成记这条取舍本身并给出一次 `git revert` 的推翻方式，
    Non-Goals 5 由「一个字节不动」改成「只删被证伪的从句 + 加指针，结论一个字不动」。
  - **BL-B `git status --porcelain | wc -l → 0` 是假的**（实为 `1`，即本 plan 文件自己）
    → B5 改准并留痕；Phase 3 的「零改动」口径逐字改成「除本 plan 自己的产物外无输出」。
  - **BL-C 「job 边界在基线上是死代码」是假的**：不加「裸目录参数」约束时，`gates.yml:208`
    的 `pytest tests/gates/test_zero_dep_boot.py` 会让**基线本身就红** → Phase 2 的解析器项补上第 ② 条形状约束，
    删掉那句被证伪的理由并留痕；`N7`/`N8` 的边界活性说明改准（去掉边界 → N7 转绿、N8 转红）。
  - **SF 1–10 全部采纳**：⑤ 的短路改成**七条各自对空表短路**（否则 N3 会 `7 failed`）·
    ⑦ 补「跳过步骤表里查不到的目录」（否则 N2 会 `4 failed`、N4/N7 各多红一条）·
    第 2 列措辞改成「**本 job 里**不跑」并补一条点名 `tests/ui`（`:337`）与 `tests/gates`（`:208`/`:561`）在别的 job 里确实跑着 ·
    三个 Phase 补 `- Item Types:` · Phase 1 Exit 的 `git diff --numstat` 补基线 `bc7f13f` ·
    `D4` 的 `:2762` / `:2804` 依据改准 · Closure Gates 把红线与自设围栏**分成两条** ·
    并在下一条逐字披露工作项 4 计数的那个近似命中。
- ⚠️ **工作项 4 计数的近似命中，照实披露**（评审 SF-6）：`2026-08-24-2311-1-immediate-context-into-explain-loop.md`
  的 `> Work Item:` 首行是 **`10`**，但同一行逐字写着「同时结清工作项 4（P1.2）Non-Goals 3 留下的接线缺口」。
  **本 plan 的计数口径是 `> Work Item:` 首行**（与前十轮起草步、`STATE` 各轮逐格重数同口径）⇒ 工作项 4 记 `1/2`。
  **若人改用「凡自称结清了工作项 4 的都算一格」的口径，该格即为 `2/2`，本 plan 就需要人加预算** —— 口径归人，本行只披露。
- Independent draft review iteration 3: **needs revision**（独立子代理，全新会话，2026-08-26，task `a59b0e2`）——
  **在 `/tmp` 整仓副本上把七条断言与 §7.26 表完整实现并跑完全部变异**（活仓零改动），
  逐字报「**baseline `7 passed`，N1–N9 all match the plan's predictions exactly**」，
  含 `N8` must-stay-green 与 `N7`/`N8` 的边界活性对；⑦-skip 与短路的理由亦被实测印证
  （无 ⑦-skip 时 N2 `4 failed`、N4 `2 failed`）。开出 **3 条 blocking + 9 条 should-fix**。
  - **归属问题由本轮裁断（前两轮判读相反，本轮是决胜局）**：逐字实读 `02-WBS.md:6` 表规 3
    与 `DECISIONS.md:362` D-24 后判 **legitimate as written; do not narrow, do not hold for a human** ——
    表规 3 是 plan **文件计数**，D-24 禁的是**加 WBS 行**，两者都不含「文档小节」这个词。
    并给出**决定性仓内先例**：`STATE.md:840` 记着工作项 6 的 plan `2026-08-25-0225-1`
    往 §12.5（工作项 3 的落点节）**加过一条指针（5 增 0 删）**，独立收口审计通过、未记任何预算。
    ⇒ 归属节据此补上该先例。
  - **BL-1 首稿自相矛盾**：Phase 3 标题与 Closure Gate 仍写「两处交人」，正文却已改成 `Fix` → 两处措辞改准。
  - **BL-2 「只改两处」会留下三句仍然为假的话**（`:377-379` 两者都要人来接 · `:381-382` 代偿控制只有三条 ·
    `:386` 要和接 CI 一起做），而 Non-Goals 5 还写着「三条代偿控制一个字不动」
    → **`Fix` 扩到五处**，Non-Goals 5 改成「不改**仍然成立的**结论」，Phase 3 Exit 的「零新增事实」加「删除除外」。
  - **BL-3 「不加②则基线就红」是假的**：实测 `去①留② → 7 passed` / `去②留① → 7 passed` / `两条都去 → 1 failed`
    ⇒ 两条在今天的基线上互为替身 → 该理由整段改准并留痕，新增 **`N10`**（第二条 must-stay-green）专门证明②的活性。
  - **SF 1–9 全部采纳**：⑤ 的「`7 failed`」实为 `2 failed`（改准并留痕）· 先例行号改 `:118-124` 并说明形态不同 ·
    CP9 引文出处由「§1.2」改准为 `:95` · 删掉那条**按构造永远不会红**的假 Exit Criteria（工作项 3 计数）·
    `missions/**` 从红线清单挪进「自设围栏」并注明出处是 `ai-autonomy-policy.md` 的 Protected Areas ·
    断言④ 补「读**全部** `tests/<dir>` 参数」（否则 `N6` 会保持绿）· B2 第 4 处补一句同结果面的论证 ·
    `d5f0a04` 标题补全 · 修掉 ⑤ 那处断行与孤立的「·」。
- Independent draft review iteration 4: **needs revision**（独立子代理，全新会话，2026-08-26，task `a46a015`）——
  **在 `/tmp` 副本上把 iteration 3 的三条 blocking 逐条复核并把 `N10` 也实跑了**：
  `去①留② → PASS` / `去②留① → PASS` / `两条都去 → FAIL（断言②）`，
  `N10` 插在 ⑤ 之前与 ⑥ 之后各跑一次，**带裸目录约束 → PASS、去掉 → FAIL 在②** ⇒ 预测成立。
  判 **BL-1/BL-3 已修**，另开 **1 条 blocking + 7 条 should-fix**。
  - **BL-1（本轮）`model-management.md:380` 被误读**：起草稿与前三轮都以为它「含 `commands.test` 那一半、可整句保留」，
    **实读它一个 `commands.test` 都没有**（那一半在 `:374`），且它的前提「在人接进去之前」**2026-08-24 就已失效** ——
    保留它等于把本 plan 自己在 B4 点名的那种**低估**原样留下。
    → Phase 3 的 `Fix` 重写成**逐从句表**（`:374`–`:386` 十行，**六假四真**，`:380` 换成与今天相符的禁令），
    Non-Goals 5 与 G5 一并改准。
  - **SF 1–7 全部采纳**：`/tmp` 副本硬约束扩到 `N1–N10`（`N10` 动的是 `gates.yml`，红线 2）·
    B2 两行的处置指针由 `Decision` 改 `Fix` · B2 第 3 行范围补成 `:373-382` · 第 4 行「下方 4 行」改准为「下方 2 行」·
    `:377` / `:378` / `:386` 由「整段删」细化成「只删被证伪的子句」· `:385` 判真保留 ·
    **新增一条 `Fix` 认领 `module-boundaries.md:489`**（§7.7 里同形态的封闭计数，此前无人认领）· G5 补上「删从句」这一半。
- Independent draft review iteration 5: **needs revision**（独立子代理，全新会话，2026-08-26，task `ab8e905`）——
  **在 `/tmp` 整仓副本上把七条断言与 §7.26 表完整实现并跑完 N1–N10（含 N9 三变体、两条 must-stay-green、①/② 两对活性证明）**，
  逐字报「**十条全部与 plan 的预测逐条吻合**」「七条断言的技术设计、两条形状约束、⑦-skip、逐条短路——全部经实测成立，**无一条需要补断言**」
  ⇒ **技术面已收敛，本轮四条 blocking 全部落在「登记文字自身的计数与认领」上。** 开出 **4 条 blocking + 5 条 should-fix**，**九条全部采纳**：
  - **BL-1 `六处假、四处真` 三处计数与表自身 10 行对不上**（实为 3 真 + 2 半真 + 1 前提失效 + 4 假 ⇒ 保留 3 行、须改 7 行）
    → 三处计数一律改成「**3 行判真逐字保留、7 行须改（4 假 + 2 半真 + 1 前提已失效）**」，`G5` 的「四行」改「三行」，「为什么六处一起改」改「七行」。
  - **BL-2 `missions/** 在红线内` 本身就是假的，而逐从句表放过了它；§7.7 `:488` 同句式、全文零认领**
    （`AGENTS.md:8-16` 七条实读无 `missions/**`；出处是 `ai-autonomy-policy.md:87` 的 Protected Areas；仓内已有正确写法 `STATE.md:762`）
    → `:378` 行的处置列补上「把『在红线内』改成 Protected Areas 的说法」；**新增一条 `Fix` 认领 `module-boundaries.md:488`**。
  - **BL-3 B2 宣称「一共四处」而实际处置五处** → 标题改「五处」，`:488` 补成第 5 行（三列齐全），并照实记「**这是同一个病在起草过程中的第二次现场复发**」。
  - **BL-4 对 `:489` 的定性「封闭计数」是误读、且与 Non-Goals 4 自相矛盾**
    （评审实读：`:489` 与 §7.6a `:331` **同句式、都没有「只有」**；有「只有三条」的只是 `model-management.md:381`）
    → **删掉那条 `Fix`**，`:489` 归入 Non-Goals 4（与 `:331` 同口径），**原误读留痕在 Phase 3 那条 `Fix` 的 ⚠️ 里**。
  - **SF-1**（断言② 的「双向」拆成 **②a 表→CI** / **②b CI→表** 并逐条写死变异红在哪一支；顺带修掉 N8「唯一一条 must-stay-green」与 N10「第二条」的自相矛盾）·
    **SF-2**（`roadmap:41` 那条 `Decision` 补残余风险 → 新增 `D5`）· **SF-3**（补扫判词口径三分：`成立` / `行号漂移` / `已过期`，
    只有 `已过期` 才进改准范围 —— 评审点名 `module-boundaries.md:4407` 引的 `gates.yml:567` 属「内容真、行号漂」）·
    **SF-4**（Closure Gates 两条自证的 `<BASE>` 占位钉死为 `bc7f13f`）· **SF-5**（Phase 1 Exit 的「删除列为 0」加时点限定 ——
    Phase 3 会对同一文件删从句，收口整体复跑必然非 0）。
- Independent draft review iteration 6: **needs revision**（独立子代理，全新会话，2026-08-26，task `a127397`）——
  **逐条实读复核第 5 轮的四条 blocking，判「①②③④ 全部已修干净」**（含逐从句表 10 行与三处计数逐行对账、
  `AGENTS.md:8-16` 七条实读无 `missions/**`、`:489` 与 §7.6a `:331` 同句式均无「只有」）。
  本轮 blocking **全部来自它自己独立扫出来的第六处**，开出 **4 条 blocking + 6 条 should-fix**，**十条全部采纳**：
  - **🔴 BL-1 同一失败形态还有第六处：`module-boundaries.md:4424-4442`（§7.23.6），plan 全文零认领，
    且本 plan 的五关键词补扫**被机械证明命不中它***（评审用 `awk` 限定 `4400<行<4500` 实测：只有 `:4407` `:4411`）。
    该节三条编号项 + 两句结论今天**五条逐条相反**（`COVERED` 含 `ui` 9==9 不红 · `gates.yml:337` 逐字跑
    `tests/ui/test_sidebar.py` · `:682` ruff 含 `tests/ui` · `STATE.md:1152-1153` 记「六件全部做掉」`f795e47` ·
    `:673` 已是「八个目录」两边相等），落地人 `lize` 2026-08-26。
    → B2 改「六处」并补第 6 行（三列齐全）· Phase 3 **新增一条五行逐条 `Fix`** · 补扫关键词由五个扩到**十二个**、
    范围由两个目录扩到**四个** · 并照实记「**这是同一个病在起草过程中的第三次现场复发**」——
    ⚠️ **最难堪的一点也照实记**：`gates.yml:337` 与 `:682` 这两个真值**本 plan 自己都引用过**（Phase 1 执行项与 B1），
    读到了真值却没回头认领说它假的那一段。
  - **BL-2 B3 的两处计数仍是第 5 轮之前的旧值**（「五处/四处」），与已改准的 B2「五处」自相矛盾
    → 改成「**七处同源登记里有六处漏改**」，并逐字写死**本计数随 B2 表联动**。
  - **BL-3 B5 的工作树登记已被证伪**：`git status --porcelain` 实为 **2** 行（第二行是同批起草的兄弟 plan
    `…-2213-2-case-ledger-marker-drift.md`），而 Phase 3 的 Prereq 逐字写「除本 plan 自己的文件外无输出」
    ⇒ **按字面在执行期必然判不达标** → B5 改准为 `2`（两次改准均留痕），口径改成**点名那两个文件**。
  - **BL-4 §7.26 的「点名重复登记」清单漏了同一 owner doc 里的第三份副本 `module-boundaries.md:4270`**
    → 补进清单，且**判词定为「已过期的快照」而非「已过期的断言」**（它是 §7.23.1 探针 `H1` 的带日期实测值，
    按本仓惯例是追加式账本 ⇒ 处置只有「加一句时点限定 + 指向 §7.26」，不改写内容）。
  - **SF 1–6 全部采纳**：`:377` 的「逐字」列补上「同形态的」· 第 1 轮记录里的「N8 唯一一条」补时点限定 ·
    `D5` 与 `D4` 顺序改准 · 补扫范围补 `docs/context/` 与 `docs/design/` ·
    三分口径改成**判词是集合不是单选**（同一行可同时 `已过期` + `行号漂移`）· Phase 1 Exit 钉死起草期实测值 `9`。
- Independent draft review iteration 7: **needs revision**（独立子代理，全新会话，2026-08-26，task `acb6b1e`）——
  评审自行设计检索口径（**未照抄本 plan 的十二个关键词**）独立复扫，**又查出两处**，开 **6 条 blocking + 8 条 should-fix**，**全部采纳**：
  - 🔴 **BL-1 第七处 `docs/context/project-context.md:52`**（`Lint / static check` 行内的 ⚠️ 注解，三段全反：
    `gates.yml:674` 今天已是「作用域**八个目录**」· `:682` 八个参数含 `tests/ui` ⇒ 集合已相等 ·
    `f795e47` 已把「逐字交人」的六件做完）。**该文件不在任何红线 / Protected Areas 内**
    （`ai-autonomy-policy.md:77-90` 实读无 `docs/context/**`）⇒ loop 有权改。
    ⚠️ **它是每轮 mission-driver 第一个读的入口文件**，留着假话的代价比 owner doc 深处大。
  - 🔴 **BL-2 第八处 `docs/backlog/p1-insight-roadmap.md:108`（+ `:109`）** —— 三个分句今天逐条相反。
    **它就在本 plan 已经要动的那个文件里，只隔 67 行**，而起草稿与前六轮都没看见。
    处置形态同 `roadmap:41`（引擎回写的账本行 ⇒ 只追加纯指针，不改已有字，复用 `D5`）。
  - **BL-3 `gates.yml:673` 引错行**（`:673` 是空行，正文在 `:674`）→ 三处一律改准。
  - 🔴 **BL-4 「六处 / 七处 / 六处漏改」三处计数同时失效** —— 这是同一形态的**第三次复发**
    （第 5 轮 BL-3 → 第 6 轮 BL-2 → 本轮）。
    → **不再第四次改数字，改结构**：B2 顶部逐字声明「**本表即清单，正文任何地方不再写「一共有 N 处」**」，
    `B3` 与 `Closure Gates` 一律改成「**B2 表的每一行**」。**把数字从正文里去掉，是本 plan 对自己犯的那个病的处置。**
  - **BL-5 `D4` 仍写「五关键词补扫」**而 Phase 3 已扩到十二词 / 四目录 → 改准；BL-1/BL-2 两处
    **从 `D4` 的重开事件挪进正文范围**（规则 14：确认的 owner-doc 漂移不可降级为 `Deferred`）。
  - **BL-6 归属节的「碰了谁的落点节」枚举漏了工作项 11** —— §7.23.6 与 `:4270` 同属
    `module-boundaries.md:4255` 的 §7.23，其标题逐字含「**P1.8b 第 2 个 plan**」= 工作项 11。
    **该节的唯一职责就是穷举这份清单，而它漏了一格** → 补入，并补一条复核命令。
  - **SF 1–8 全部采纳**（`:4436-4437` 行范围 · `:4433` 行号处置口径写死不写「同上」· 第 6 处真值补 `:326` 与行尾 `| tee` ·
    第 6 处补「是不是同一结果面」判词 · §7.26 点名清单补 `project-context.md:52` 与 `system-baseline.md:1016-1017` ·
    `D5` 标题前补空行 · 三分判词的已知候选先写进 plan · 并照实记「评审第 7 轮未复跑 `/tmp` 原型，
    对七条断言与 N1–N10 不作独立背书，只接受第 3–5 轮的实测记录」）。
- ⚠️ **连续四轮各查出一处新的同形态漂移**（第 4 轮 `:380` · 第 5 轮 `:488` · 第 6 轮 §7.23.6 · 第 7 轮 `project-context.md:52` + `roadmap:108`）。
  **这本身就是一个结论，写在这里而不是藏起来**：这一形态在本仓的分布**比起草期以为的广**，
  且**每一次都是靠「独立评审自己设计检索口径去扫」发现的，没有一次是靠读 plan 的文字发现的**。
  ⇒ `D4` 逐字保留「关键词扫描不是全文逐行复核」这条边界，**不许写成「这次扫干净了」**。
- Independent draft review iteration 8: **accept（已就地修完，无遗留 blocking）**（独立评审步，全新会话，2026-08-26）——
  评审**自行设计检索口径独立复扫**（未照抄本 plan 的十二个关键词，用的是
  `零覆盖 / 任何 job / 不会被任何 / 复跑不到 / 漏在 CI / 不在…作用域 / 未被 CI / 裸奔` 八个词，
  范围 `docs/architecture` `docs/backlog` `docs/context` `docs/masterplan`），并逐条实读复核 B1 / B5 / B2 全部 8 行。
  **实读复核通过的**：`gates.yml:620-621` ⑤ 步 · `:682` 八个目录 · `:631` `COVERED` 九项 · `:326`/`:337` `gates-l2-live` 跑 `tests/ui` ·
  `ls -d tests/*/ | wc -l` → **9** · `commands.test` 逐字仍是 `check_expected_red.py && pytest tests/unit -q` ·
  `mb:485-489` · §7.6a `:324-331`（**今天仍为真，Non-Goals 4 成立**）· `STATE.md:1152-1154` · `roadmap:108-109` · `mb:4270` ·
  `AGENTS.md:8-16` 七条红线实读**无 `missions/**`、无 `docs/architecture/**`、无 `docs/context/**`**；
  格式面：模板必备节齐全 · 三个 Phase 的 `Status`/`Targets`/`Skill`/`Item Types`/`Prereqs`/`Exit Criteria` 齐全 ·
  每条执行项带类型标签与 `Skill:` · 三条 `Decision` 均有备选与否决理由 · 反偷懒禁用词**零命中** ·
  规则 12 自检 `grep -B5 "\- \[ \]" … | grep "Status: completed"` → **空**。
  开出 **1 条 blocking + 2 条 should-fix，全部由本轮就地修完**：
  - 🔴 **BL-1 第九处 `docs/architecture/system-baseline.md:1016-1017`（§14.7「`lint` 判什么」）与 `:1587-1588`（§14.10）** ——
    三句今天全反（「一条判据命令，逐字 `ruff check agenerp tests/unit tests/contracts`」·「**作用域三个目录**……**一个字不加不减**」·
    「**既有** `lint` job（`gates.yml:426`）……**显式列目录**的 `ruff check agenerp tests/unit tests/contracts`」），
    而 `gates.yml:663` 才是 `lint` job 键、`:682` 逐字八个目录、`project-context.md:52` 亦八个。
    **最难堪处与第 6 轮同形**：`:1016-1017` **本 plan 自己在 Phase 1 的执行项里逐字列过**（第 7 轮 SF 补进去的），
    却只当成「要在 §7.26 里点名的重复登记」，**没有任何一条执行项认领它本身已为假**；`:1587-1588` 则一直挂在
    Phase 3 补扫的**待判候选**里 —— 两者都撞在本 plan 自己写死的那条口径上（补扫是执行期 `Proof`，不构成范围内的认领）。
    → **B2 补第 9 行**（三列齐全 + 处置口径）· **Phase 3 新增一条 `Fix`** · **新增 `G6`** 写死「按 plan 分节的交付记录 /
    带日期的探针快照」这一类的**第二种口径**（不改写记录，只加时点限定 + 指针，与 `:4270` 逐字相同）·
    `:1587-1588` 从补扫候选**升进范围**· Phase 3 Exit 补一条「`system-baseline.md` 删除列为 0」。
  - **SF-1 Phase 3 的 `Targets` 漏了三个本阶段确实要动的文件**（`model-management.md` §12.5 · `project-context.md:52` ·
    `module-boundaries.md` §7.23.6 —— 都是第 4–7 轮扩范围时加的执行项，`Targets:` 一行没跟上）→ 补齐。
  - **SF-2 `Closure Gates` 前两条的落地清单与 B2 表不同步**（缺第 9 处）→ 两条一并补齐；
    第 1 条「逐行对着 B2 表点，不按记忆里的数字点」这句口径本轮**实测有效** —— 正是它让漏项只表现为「表少一行」而非「数字对不上」。
- ⚠️ **连续五轮各查出一处新的同形态漂移**（第 4 轮 `:380` · 第 5 轮 `:488` · 第 6 轮 §7.23.6 · 第 7 轮 `project-context.md:52` + `roadmap:108` ·
  第 8 轮 `system-baseline.md` §14.7 / §14.10）。**第 8 轮把这条结论又推进了一格，照实记**：
  **本轮那两处，本 plan 的文字里其实都已经写着**（一处在 Phase 1 的清单里、一处在 Phase 3 的候选里）——
  ⇒ 漏的不是「没扫到」，是**「读到了却没认领」**。`D4` 那条边界（关键词扫描不是全文逐行复核）逐字保留，
  并**追加一条同等重要的**：**本 plan 自己已引用过的每一处位置，都必须被显式判过「它今天是真是假」**。

## Closure Gates

- [x] in-scope behavior is complete —— **B2 表的每一行都已落地**（收口时逐行对着 B2 表点，不按记忆里的数字点）：
      §7.7 `:485-487` · `roadmap:41` 指针 · §12.5 七行 · §7.7 `:488` · §7.23.6 五条 ·
      `project-context.md:52` · `roadmap:108-109` 指针 · `system-baseline.md:1016-1017` 与 `:1587-1588` 时点限定；
      外加 §7.26 表 + `:4270` 时点限定 + 七条断言 + N1–N10
- [x] relevant docs are aligned（§7.7 · §7.23.6 · §7.26 · §12.5 · `:4270` · `roadmap:41` · `roadmap:108-109` ·
      `project-context.md:52` · `system-baseline.md` §14.7 `:1016-1017` 与 §14.10 `:1587-1588`）
- [x] verification has run：`python3 tools/gates/check_expected_red.py` ·
      `python3 -m pytest tests/unit tests/tools -q` · `python3 -m pytest tests/contracts tests/routing tests/context -q` ·
      `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui`
- [x] scoped verification is not conflated with full verification —— 未跑整仓 `pytest tests -q -m "not live"`
      （**已知基线即红**，见 `docs/backlog/gates-and-tools-leak-env-across-directories.md`）、未起 docker 栈、
      未跑任何 `-m live`、**未经 CI 服务端复跑** ⇒ 收口逐字写 `verification scope limited`
- [x] no in-scope item downgraded to deferred/follow-up（§12.5 两处**在范围内、已处置**，见归属节与 Phase 3）
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [x] closure audit was independent —— **由独立收口审计步补勾**（全新会话，非本 plan 执行者；
      逐条实测与开出的那一条 blocking 见下方 `Closure Audit Evidence`）
- [x] closure evidence exists in files
- [x] **红线自证（`AGENTS.md` 的七条，逐条）**：`git diff --name-only bc7f13f -- tests/gates/ .github/workflows/
      docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md` → 无输出（红线 1/2/3/5，
      项目名/包名未改 = 红线 4）；`git diff --numstat bc7f13f -- docs/masterplan/STATE.md` 删除列为 0（红线 5 的追加口径）；
      全程未读写 `${XM_PATH}`（红线 6）；未生成运行时 Server Script（红线 7）
- [x] **本 plan 自设的围栏（不是红线，分开列，不许与上一条混为一谈）**：
      `git diff --name-only bc7f13f -- missions/ agenerp/ tests/routing/ tests/context/ tests/tools/ tests/contracts/
      docker-compose.yml industry-packs/ pyproject.toml` → 无输出。
      ⚠️ **`missions/**` 列在这里而不是上一条**：`AGENTS.md` 的七条红线里没有它，
      它的禁令出处是 `docs/context/ai-autonomy-policy.md` 的 Protected Areas（标 `blocked`）——
      **两者不许混为一谈**（评审第 3 轮指出起草稿把它错列进红线）

## Deferred But Adjudicated

### D1 · 「一个 plan 可否给别的工作项的落点节加纯指针」这条读法本身

- Classification: `watch-only residual`
- Why Not Blocking Closure: **不是漂移、不是缺陷，是一条规则读法的取舍**，两轮独立评审给出过相反判读
  （归属节逐字记着经过）。本稿取第 2 轮的读法：表规 3 计 plan 数，不计文档小节。
  **它可被人一次 `git revert` 推翻**（§12.5 那一处 hunk 独立成段），其余交付物不受影响；
  推翻方式已写进 `STATE.md` §3 的追加行。
- Successor Required: `no`（若人不认同，人 revert 一个 hunk 即可；无需后继 plan）
- 重开事件：**人明确裁定「改别的工作项的落点节要占那一格预算」**，
  或**人在 `02-WBS.md` 就此加一条表规**。

### D2 · 本条判据可能因人正当改 CI 而红在 `GATE_VERIFY` 上

- Classification: `watch-only residual`
- Why Not Blocking Closure: 这是 Phase 2 `Decision` 选 (C) 的**已知代价**，不是遗漏；
  缓解（失败文案逐字指出改哪个文件的哪一列）已是执行项。
  **不接受「把判据挪出 `commands.test` 以免拖红」这种缓解** —— 那是用降低判别力换绿。
- Successor Required: `no`
- 重开事件：**本仓实际发生一次「人改 CI → 本条红 → 循环停机」**（有轨迹为证），届时由人裁定是否换落点。

### D3 · 第 6 列只钉「日期可解析 + 证据路径存在」，钉不住「日期是否新鲜」

- Classification: `watch-only residual`
- Why Not Blocking Closure: 与 `tests/routing/test_routing_guard_registration.py` 第 ⑤ 条同一取舍、同一措辞；
  本 plan 沿用并**逐字声明它钉不住什么**。同理，本条**不需要**先例那种 `_REGISTERED_FILES` 纳管常量
  （`B` 三路来源都不由表导出），**这一点也逐字写进判据文件头，不默默省掉**。
- Successor Required: `no`
- 重开事件：**出现一次「表里日期很旧、而判定面已变」却没被任何断言打红的实例**。

### D4 · `docs/architecture/` 其余各节的同类登记文字未逐节复核

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: Phase 3 已加一条**十二关键词、四个目录的补扫**（`docs/architecture/` `docs/backlog/` `docs/context/` `docs/design/`），
  但那仍是**关键词扫描 + 逐条读原文**，不是全文逐行复核。
  ⚠️ **评审第 8 轮追加一条同等重要的边界**：**本 plan 自己在任何一节里引用过的每一处位置，
  都必须被显式判过「它今天是真是假」** —— 第 8 轮那两处（`system-baseline.md:1016-1017` 在 Phase 1 的清单里、
  `:1587-1588` 在 Phase 3 的候选里）漏的不是「没扫到」，是**读到了却没认领**。
  起草期读过的其余命中今天仍成立，其中 `module-boundaries.md:238`（指 `missions/p0-foundation.json`）·
  `:2762`（**逐字点名 `missions/p1-insight.json` 的 `commands.test`**）·
  `:2804`（**只说「也不在 `commands.test` 里」，没点文件名** —— 起草首稿把它写成点了名，评审第 2 轮实读改准，原文留痕于此）·
  `:2826-2827`（指 `tools/**`）。
- Successor Required: `no`
- 重开事件：**再发现一处逐字与仓库相反的覆盖断言**，届时并进 §7.26 或另起 plan。

### D5 · `roadmap:41` / `roadmap:108-109` 的追加句可能被后续引擎回写淹没

- Classification: `watch-only residual`
- Why Not Blocking Closure: 这是 Phase 3 那条 `Decision` 选 (C) 的**已知代价**（评审第 5 轮 SF-2 要求补写）：
  `docs/backlog/p1-insight-roadmap.md` 由引擎在 closure 审计后回写，追加句只能紧贴假话之后，
  **挡不住整行被后续追加淹没**。**不接受「把假话直接删掉」这种缓解** —— 该行是引擎回写的账本行，
  本 plan 的口径逐字是「不改写该行已有的任何一个字」。
- Successor Required: `no`
- 重开事件：**实际发生一次「有人读 `roadmap:41` 时只读到假话、没读到追加句」**（有轨迹为证），
  届时由人裁定该行的改写权归属。


## Closure

Status Note: 三个 Phase 全部 `completed`，执行项与 `Exit Criteria` 零 `[ ]` 残留，
`Closure Gates` 十条全 `[x]`。最后一条 `closure audit was independent` **由独立收口审计步补勾**
—— 执行期它留 `[ ]`，**本轮执行者不代跑、不代批、不预填结论**（同 `2101-1` / `1728-1` / `1618-1` 先例）；
补勾它的是独立审计步自己，逐条实测附在下方。

**逐条命令与退出码（`BASE = bc7f13f`，全部本轮实跑）**：

| 命令 | 退出码 | 首行 |
|---|---|---|
| `python3 tools/gates/check_expected_red.py` | **0** | `门禁 29 项：预期红 0，绿 29，跳过 0`（**本 plan 不新增门禁**） |
| `python3 -m pytest tests/unit/test_ci_coverage_registration.py -q` | **0** | `8 passed`（收集 **8** 条 == 断言体里 `def test_` **8** 条，**零 skip 由条数钉住**） |
| `python3 -m pytest tests/unit tests/tools -q` | **0** | `928 passed, 29 skipped`（基线 `920`，**只增不减**，+8 即本 plan 新增的八个 `def test_`） |
| `python3 -m pytest tests/contracts tests/routing tests/context -q` | **0** | `386 passed, 1 skipped`（与基线逐字相同 —— 本 plan 未动这三个目录） |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` | **0** | `All checks passed!` |

**变异自查 N1–N10**：**十条全部在 `/tmp` 的整仓副本上施加，活仓工作树零改动**，
十条与预测吻合（含 N8 / N10 两条 must-stay-green 真的保持绿、N9 三个变体各红一次）。
🔴 **N3 首跑不符，照实记**：解析器只用了成对标记的**起始**那一半 ⇒ 表删空后越界读到 §7.26.2 的四列表，
**存活守卫从未被触发**（`8 failed`）；当场补「在闭合标记处截断」（commit `a52a5d7`）并全表复跑 →
N3 `1 failed`（仅 `test_05`），无一条回归。逐条实测与失败文案实样见
`docs/evidence/p1-ci-coverage-registration/README.md` §3。

⚠️ **verification scope limited**：未跑整仓 `pytest tests -q -m "not live"`（**已知基线即红**，
见 `docs/backlog/gates-and-tools-leak-env-across-directories.md`）· 未起 docker 栈 · 未跑任何 `-m live` ·
**未经 CI 服务端复跑** · 全程离线（零 docker、零网络、零凭据、零 LLM 调用、零 token 成本）。

Closure Audit Evidence:

- Auditor / Agent: **独立收口审计步**（全新会话，非本 plan 执行者；`MISSION_DRIVER:2026-08-26-205222`）。
- Evidence（**逐条本轮独立实跑，不照抄执行期记录**，`BASE = bc7f13f`）：
  - **四条复跑命令原样复跑，退出码逐条与 `## Closure` 表相符**：
    `python3 tools/gates/check_expected_red.py` → **exit 0**（`门禁 29 项：预期红 0，绿 29，跳过 0`）·
    `python3 -m pytest tests/unit tests/tools -q` → **exit 0**（`928 passed, 29 skipped`）·
    `python3 -m pytest tests/contracts tests/routing tests/context -q` → **exit 0**（`386 passed, 1 skipped`）·
    `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → **exit 0**（`All checks passed!`）。
  - **红线自证独立复跑**：`git diff --name-only bc7f13f -- tests/gates/ .github/workflows/ docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md`
    → **无输出** · 自设围栏那条 → **无输出** · `git diff --numstat bc7f13f -- docs/masterplan/STATE.md` → **`13 0`（删除列 0）**。
  - **B2 表逐行对着活仓点（不按数字点）**：§7.26 存在且成对标记齐全、数据行 **9** == `ls -d tests/*/ | wc -l` 实测 **9** ·
    表的六列与 `gates.yml` 实读逐行相符（步骤序号 `①`–`⑥` 落在 `:604 :607 :615 :618 :621 :624`、`:631` `COVERED` 九项、`:682` ruff 八参）·
    §7.7 `:485-488` · §12.5 十行（判真的 `:374`/`:379`/`:385` 三句确未被改写）· §7.23.6 五条 · `:4270` 时点限定 ·
    `project-context.md:52` · `roadmap:41` / `:108-109` 纯指针 · `system-baseline.md` §14.7 / §14.10 时点限定（该文件 `numstat` **11 0**）——
    **九处逐处实读确认已落地**。
  - **反空壳**：`tests/unit/test_ci_coverage_registration.py` 逐条读完（459 行、8 个 `def test_`、七条断言各自有真实解析器与失败文案），
    落在 `tests/unit/` ⇒ **真的进 `commands.test` 与 CI 的 `unit-and-contracts` 第 ① 步**，无空函数体 / 无 `return None` 占位 / 无被吞异常。
  - 🔴 **本轮开出并当场修完的一条 blocking**：`module-boundaries.md` §7.26.2 正文逐字写着「同一个事实被登记在**五个地方**」，
    而它自己下方的表是 **6 行** —— **这正是本 plan 要治的那个病（表改了而正文的数字没跟上）在交付物里复发第四次**。
    按本 plan 第 7 轮 BL-4 已写死的处置口径修（**不再第四次改数字，改结构**）：把数字从正文里去掉，
    改成「下表即这份清单的唯一形态，本节正文任何地方都不再写「一共有 N 处」」。
    ⚠️ `docs/logs/2026/08-26.md:25` 与 `STATE.md:1659` 记的是「**六处**」，**与表一致、无需改**（后者亦属红线 5 只追加）。
  - **SF（一并补齐）**：Phase 3 的 `Targets:` 漏了本阶段确实动过的 `docs/backlog/tools-dir-has-no-static-check-coverage.md`
    （补扫判为 `已过期 + 行号漂移`，按 `:4270` 那一档口径只追加时点限定，`numstat` 删除列 **0**，证据 §5.1 / §6.2 已记）→ 已补入。
  - **五点一致复核**：`Plan Status: completed` · 三个 Phase `Status: completed` · 全部 `Exit Criteria` `[x]` ·
    `Closure Gates` 十条全 `[x]` · `docs/logs/2026/08-26.md` 条目与 `STATE.md` §3 追加行三方口径相符（含 `verification scope limited`）。
  - **Deferred 诚实性复核**：`D1`–`D5` 五条各自带分类与重开事件，**无一条是被降级的范围内确认缺陷**；
    `Follow-up` 逐字为「无」。规则 12 自检 `grep -B5 "\- \[ \]" <plan> | grep "Status: completed"` → **空**。
  - ⚠️ **本审计的边界，照实记**：未起 docker 栈、未跑 `-m live`、未跑整仓 `pytest tests -q -m "not live"`（已知基线即红）、
    **未经 CI 服务端复跑**；N1–N10 的 `/tmp` 变异**未由本轮独立重跑**，本审计只接受执行期落在证据文件 §3 的记录
    与「活仓工作树零改动」这一点的可验证结果（`git diff --name-only bc7f13f -- .github/ missions/ tests/gates/` → 无输出）。

Follow-up:

- 无。**确认的缺陷一条都没有进这里**：`D1`–`D5` 五条各自是 `watch-only residual` /
  `out-of-scope improvement`，都带重开事件，不是被降级的范围内项。
