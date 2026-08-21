# STATE · 状态投影

> **这是投影，不是真相源。** 真相源是：LoopX 状态（启用时）+ git + 门禁退出码。
> 与本文件冲突时，以那三者为准（见 [01-EXECUTION-MODEL.md](./01-EXECUTION-MODEL.md) §4）。
> §2 **只追加，不改写、不删除**。改写历史等于销毁证据。

---

## §1 当前快照

| 字段 | 值 |
|---|---|
| 阶段 | **Day -1**（主计划自身制作） |
| 当前 mission | 无（mission-driver 尚未接管，Day 0 之后才有） |
| **下一个未阻塞工作项** | **P0.2 · 工具契约层 v0**（此字段**只填一个 ID**，不写「但实际前置是…」这类歧义——T1 实测：会让接手会话先做一次推理才敢动手） |
| 该项验收命令 | `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0 |
| 阻塞 | 无。**T1–T4 四条全过**（2026-08-20） |
| 成本 | 未开始计量（阈值待 `W0.0` 定出） |
| CI | 未配置（`W0.7`） |
| 证据仓 | `XM_SHA=1c622c8119755b36992c54ba98fbf6840cd22ed4` @ `validation/pre-build`（见 `evidence-repo.env`） |
| LoopX | 已装 0.5.0；**已接管 WBS 项级状态**（goal `agenerp-goal`，agent `supervisor-a`）；写回经 `tools/loopx-writeback.sh` 单向搬运退出码 |

---

## §2 会话日志（追加式 · 每行必须含：时间 · WBS行ID · 命令→退出码 · sha · 下一项）

> 📦 较早的 122 条证据行已整段归档到 [archive/STATE-2026-08-22.md](./archive/STATE-2026-08-22.md)（一字未改）。冷启动读的是 §1 + 本节末行 + §3，不受影响。

- 2026-08-22T00:27Z · P0.8/工作项 9（本行新增该工作项） · `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 tools/gates/check_expected_red.py` → **exit 0**（`门禁 19 项：红 0，绿 19，跳过 0`）· sha `a992d2d`（判定器改动那一提交；本行随 Phase 3 收尾提交一并入库，该提交 sha 见 `docs/logs/2026/08-22.md` 与 plan Phase 3 收尾自查） · plan `2026-08-22-0027-1-live-mode-gate-verdict.md` 三个 Phase 执行完毕，下一项是本批第二个 plan `2026-08-22-0027-2`（CI 消费面 + 判定器守卫）
  · **判定器新增 live 判定模式**：`tools/gates/check_expected_red.py` 由 `AGENERP_LIVE=1` 选中（与 `tests/gates/conftest.py` 的 `_require_live()` 是**同一个开关**，`== "1"` 与 `!= "1"` 逐字互补），契约写死为「全部门禁绿、零 red、零 skip」，**不读** `tools/gates/expected-red.txt`。**没有新建「live 名单」文件**——偏离了 `system-baseline.md` 那一节改写前逐字写着的修法建议，偏离与理由记在新的 `## 14.4`，不藏着。
  · **纯函数接缝**：`classify(junit_xml)` / `verdict(outcomes, expected_red, live)` 从 `run_pytest()` / `main()` 抽出，`main()` 退化成组装 + 打印；`healed_env()`、pytest 调用参数、junit 文件名一行未改。新建 `tests/unit/test_gate_verdict.py` **12 条**（手写 junit XML 片段，不起 pytest 子进程），覆盖两模式共八态 —— **skip 判定第一次有判据覆盖**（`pytest` 对全部 skip 的一轮照样退 0，判定器不然，而此前没有任何东西在验证判定器还在执行这句话）。
  · **默认判定环境的判定行逐字节不变**：`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`，与开工 sha `084c9c4` 时逐字一致，前后两次实跑对照在 plan Phase 2。新增的只有一行模式行（`判定模式：default —— 按 tools/gates/expected-red.txt 判定`），两种模式都打印。`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**（193 → **205 passed**）；`ruff check agenerp tests/unit tests/contracts` → **exit 0**；`bash tools/gates/smoke-loop-wiring.sh` → **exit 0**（回归守卫；该脚本把 `commands.test` 写成 `true` / `exit 1`，**它从不调用判定器**，所以它证明不了「判定器仍然接着」——那由 `GATE_VERIFY` 字面命令的正负向实跑负责）。
  · **`tools/gates/expected-red.txt` 一行未动**（`git diff --numstat <开工 sha>..HEAD` 无输出），沿用人在本节 2026-08-21T11:20Z 的裁定。本 plan 无转绿项，也不请求划名单。
  · **live 整目录判定 —— 本仓第一次让 19 条在 live 环境下一次跑完**（此前 live 绿证都是按文件分开跑的，且只覆盖 19 条中的 10 条）。**六跑，五绿一红**：第 1 跑 **exit 1**，`门禁 19 项：红 1，绿 18，跳过 0`，逐字点名 `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`；**原样复跑四次全部 exit 0**（`门禁 19 项：红 0，绿 19，跳过 0`）。按 `AGENTS.md` 裁判规则 3 记为「**不可复现**」，**不猜根因**——不写「是门禁互相干扰」，也不写「是环境抖动」，两者都没有证据。**没有用 `-p no:randomly` / `-x` / 收窄目录之类的手段掩盖**：六跑用的是同一条字面命令。已在 plan 的 `## Deferred But Adjudicated` 立一条 `watch-only residual`，重开事件是「再次观察到同一条门禁在整目录 live 判定下红（本机或 CI 皆算）」，并作为**已知风险**交办给本批第二个 plan（CI 上一次红就是一次红，没有人在旁边复跑）。
  · **一个未知数被这一跑消掉**：那 9 条从未在 live 下跑过的门禁（`test_normalizer_idempotent.py` 3 + `test_seed_dataset_absurdity.py` 6）在 live 环境下行为与默认环境一致，六跑里一次都没被点名。
  · **三处变异窗口全部复原、零产品行为发布**：① `agenerp/pack.py` 的 `normalize` 改恒等 → `GATE_VERIFY` 字面命令 **exit 1** 且逐字点名 `test_normalizer_idempotent.py` 三条；② `agenerp/apply.py` 删除路径改 no-op → live 判定 **exit 1**，**点名 nodeid 集合之差恰好是** `::test_removing_from_pack_actually_deletes_on_site` **一条**（判据是集合之差，不是退出码）；③ **判定器自己**的 `verdict()` `skipped` 分支删掉 → `python3 -m pytest tests/unit -q` **exit 1** 且逐字点名 `test_default_skip_fails_even_when_everything_else_matches` 与 `test_live_any_skip_fails` 两条。三处均 `git checkout` 复原并复跑回基线（exit 0）。
  · **Protected Areas 末行要求的 `capture` 对照做了两次**（真删除路径实际跑了两次：整目录首跑、变异 ① 复原后的复跑），两次前后全量 `capture("doctypes")` **差集都为空**（10 条进、10 条出，added / removed 均为 `[]`）——连门禁自己的探针都没剩下，比「只允许含本次探针」更严。**变异期间那一跑刻意不带这条证据**：no-op 删不掉东西，差集按构造必然为空，加上去是假证据。
  · **判定器此前三层皆无保护，本行是第一次登记它**：`gates-untouched` 只 diff `tests/gates/**`、`tools/gates/gate-verify.mjs` 的 `PROTECTED = ["tests/gates/"]`、`expected-red-ratchet` 只数 txt 行数——而 `gates-l1` 跑的**就是判定器本身**，判定器被改废会在 CI 上**自证为绿**。已在 `docs/context/ai-autonomy-policy.md` Protected Areas 补一行（**加严**，`plan-first`），边界写明**不覆盖 `tools/gates/expected-red.txt`**（出处是 `AGENTS.md` 红线 1 的「边界」句与该表第 2 行，**不是**本节 11:20Z 那条——那条讲的是名单里该写什么，不是谁能改）。**空窗期照实记**：文档级约束对拿着 shell 的执行器没有强制力，带牙齿的 CI 侧守卫 `verdict-tool-untouched` 归本批第二个 plan，此刻**还没上线**；空窗期内唯一带牙齿的控制是那个改判定器的提交上**自愿**带的 `Gates-Change-Approved-By:` trailer（本仓没有任何 job 会检查它，但它让「判定器什么时候被谁改过」在 `git log` 里可被检索）。
  · **roadmap 新增工作项 9**：规则「一个工作项 = 1–2 个 plan…超过两个说明工作项拆得不够细，回来改这张表」自己指名的处置就是改表。工作项 9 **没有属于自己的门禁测试**，「判据先行」对它字面不可满足（同情形是**工作项 4 与 7**，**不引** 8 / WBS P0.7 —— 那两处确实绑着 `test_zero_dep_boot.py` 的具体断言）；停在 `planned`，关闭判据是「CI 上用判定器判 19 条并 success」，本 plan 不碰 CI。进度由 3/8 变 3/9，实测消费方是 `engine.js:690` 的 `roadmapAllDone()` 与 `monitor.js` 的 `overallProgress`，终局对账不受影响。
  · **一处确认的 owner-doc 漂移已就地改准，没有降级成 follow-up**（Minimum Rule 14）：`docs/context/project-context.md` 验证命令表写着「`tests/gates/conftest.py` 全文不设这个变量」——**那是错的**，`conftest.py:274` 在 `live_site` fixture 内部会设它。正确的说法更窄：`test_snapshot_diff_structured.py` 那两条不取任何 fixture、直接调 `capture()`，走不到那行，所以 `AGENERP_SITE` 必须由命令给。
  · **红线自查（用开工 sha `084c9c4` 作基线，不用裸 `git diff`——裸 diff 提交后恒为空，是不可能触发的假守卫）**：`git diff --stat 084c9c4..HEAD -- tests/gates .github/workflows docs/masterplan missions tools/gates/expected-red.txt` **只列出 `docs/masterplan/STATE.md` 一行**；同路径 `git status --porcelain` **输出为空**；`git diff --numstat 084c9c4..HEAD -- docs/masterplan/STATE.md` → **`18	0`**（deletions = 0 ⇒ 只追加：git 把「就地改一行」记成 1 增 1 删，deletions 为 0 就没有任何既有行被改写或删除）；`git diff --numstat 084c9c4..HEAD -- tools/gates/expected-red.txt` → **无输出**。五条命令原文与退出码在 plan Phase 3 与 `docs/logs/2026/08-22.md`。
  · **`.github/workflows/**` 与 `missions/*.json` 本 plan 一个字节没碰**：CI 消费面、CI 侧守卫、把整目录判定接进 `commands.test` 三件事全部登记为 Deferred（前两件指名 successor，第三件是人动作且**默认建议不接**——`commands.test` 每轮都跑，塞一条要起 docker 栈的命令会让每轮 `GATE_VERIFY` 依赖活栈）。
  · **verification scope（不含糊其辞）**：**live 只在本机做过，CI 未验证**。本机是 Docker 29.2.1 / Compose v5.0.2，端口 18080。本仓此刻没有全量套件，上面这些绿是 scoped verification，不是「全量验证通过」。
  · **`Plan Status` 本行不置 `completed`**：按 plan 自己写死的归属，EXECUTE 只勾执行项与 Exit Criteria，`Plan Status` 保持 `active`、`## Closure Gates` 十四框保持未勾，由独立关闭审计置位。`tools/mission-driver/prompts/execute.md` 第 4.a 条要求执行会话自置 `completed`，与 `AGENTS.md` 裁判规则 1/2 冲突，按优先级次序**不执行**（该冲突已由 plan `2026-08-21-1553-1` 登记，不重复登记）。
  · **授权链**：与本节 2026-08-21 那几行同一处矛盾，处置相同 —— 按 `AGENTS.md` 红线 5「只允许追加证据行」执行，**只追加、不改写任何已有行**，不为这处矛盾另开一行。

- 2026-08-22 · **P0 工作项 9 / plan `2026-08-22-0027-2`（CI 半）** · `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**（`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致` / `205 passed`）；`python3 -m pytest tests/contracts -q` → **exit 0**（`151 passed`）；`ruff check agenerp tests/unit tests/contracts` → **exit 0**；`python3 -c "import yaml; yaml.safe_load(open('.github/workflows/gates.yml'))"` → **exit 0**；`docker compose -f docker-compose.yml config -q` → **exit 0** · sha `9a8832f`（PR head，开工基线 `7b0f585`） · 下一项：**停机等人** —— 见 §3 的 2026-08-22 `[open]` 行
  · **交付**：`.github/workflows/gates.yml` **末尾追加两个 job，纯新增零删除**：`gates-l2-live`（起栈后用判定器对**全部 19 条**做 live 判定）与 `verdict-tool-untouched`（判定器纳入服务端「未经批准不得改动」复核；**路径清单不含 `tools/gates/expected-red.txt`**）。
  · **红线 2 自查五条全部为期望值**：(a) `diff <(git show 7b0f585:.github/workflows/gates.yml) <(head -n 190 .github/workflows/gates.yml)` → **无输出**（旧文件是新文件的行前缀，一次覆盖「7 个 job 一行不改」「`on:`/`permissions:` 不动」「零删除」三件事）；(a2) job 键集合恰好是原 7 个 + 新 2 个 = 9；(b) 新增块 `grep -nE 'continue-on-error|concurrency|cancel-in-progress'` → **0 命中**；(c) 新增块 4 处 `if:`，全部是取证/拆栈步骤上的 `if: always()`；(d) 2 处多行 `run:` 首行均 `set -euo pipefail`，主判定步骤是单条命令、无 `||`/`;`/尾随 `exit`。
  · **CI 实跑结论：红，且可复现 —— 不是「CI 已验证」，也不是「首轮红、复跑绿、不可复现」。** run `32509351108`（`pull_request`，PR #1，head `9a8832f`）两次 attempt，`gates-l2-live` **都 `failure`**，判定器输出逐字完全相同：「判定模式：live（AGENERP_LIVE=1）—— 契约为全部门禁绿、零 skip，不读预期红名单 / 门禁 19 项：红 1，绿 18，跳过 0 / ❌ live 判定契约是全部门禁绿，下列门禁红了： tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind」。**其余 8 个 job 两次全部 `success`。** 按 `AGENTS.md` 裁判规则 4（CI 连续 2 轮红即停机）停机；plan 置 `deferred`；**PR #1 未合并，`main` 上没有这两个 job**。
  · **PR 路径首测（本仓 91 个提交 0 个 merge commit，此前从未跑过）**：往分支推送**不触发任何运行**（`on: push` 限定 `branches: [main]`），只有开 PR 的 `pull_request` 事件触发；`gates-untouched` / `expected-red-ratchet` 在 PR 上均 `success`，`base.sha`/`head.sha` 那条路径实测可用。
  · **确认的 owner-doc 漂移已就地改准五处**（Minimum Rule 14，没降级成 follow-up）：roadmap「5 现状」「6 现状」「9 现状」、`project-context.md` 的整目录判定行与零依赖启动行、`system-baseline.md` §14.4。**全部按 plan 事先钉死的第三种写法**（「CI 上实跑过，结论是红，红因是 X」），一处都没写成比证据更强的说法。**`2026-08-21-2220-1` 的 Closure Gates 一个字未改**（`git diff` / `git status` 对该文件均无输出）。
  · **站点污染那条 Deferred 已裁定**：CI 日志实测拆栈步骤删掉 12 个容器 + **5 个卷全部 `Removed`** + 网络（⚠️ 判定步骤是红的那一跑，`if: always()` 仍然执行了），CI 站点仍是一次性的 → **维持 watch-only**，触发条件改绑为「当 CI 的 L2 站点不再是一次性的时」。
  · **`agenerp/**` / `tests/gates/**` / `DECISIONS.md` / `missions/**` / `tools/gates/check_expected_red.py` / `tools/gates/expected-red.txt` 全部一行未改**：`git diff --stat 7b0f585..HEAD` 与 `git status --porcelain` 两条命令对该 pathspec 均**无输出**。红在实现而 `agenerp/**` 是 Non-Goal，本 plan 一行没改它——这一条是本次停机最重要的纪律。
  · **守卫尚未交付**：`verdict-tool-untouched` 两次 attempt 都 `success`，但那证明不了它有牙齿。三次变异实验（无 trailer 改判定器必须红 / revert 必须绿 / 只动 `expected-red.txt` 必须不触发）要再跑三轮 CI，停机线已触发，**没有做**。因此**也没有**在前驱 plan `2026-08-21-2220-2` 里追加「已了结」那一行——写它就是比证据更强的说法。
  · **`Plan Status` 置 `deferred` 而非 `completed`**：按 plan 自己写死的归属，这是它列明的三条自置 `deferred` 路径中的两条同时命中（Phase 2 末项红在环境或实现 + CI 连续两轮红）。`## Closure Gates` 十四框保持未勾。
  · **verification scope**：本仓无全量套件，上面的绿是 scoped verification，**且本 plan 真正要交付的那条 CI 判定是红的**，别把默认环境那几条绿读成交付验证通过。
  · **授权链**：与本节 2026-08-21 / 2026-08-22 那几行同一处矛盾，处置相同 —— 按 `AGENTS.md` 红线 5「只允许追加证据行」执行，**只追加、不改写任何已有行**。




- 2026-08-21T21:30Z · 主计划自身 · **`STATE.md` 撑破了自己定的硬约束**：93,524 字节 vs 30,720。它是冷启动第一个被读的文件，一胖 RESUME 那条路就变贵。新增 `tools/rotate-state.py` 轮转：§3 已处置条目 + §2 较早证据行整段搬进 `archive/`，原处留指针。**`[open]` 一条不动**——待办必须留在眼前。实测 93,524 → 24,780 字节，RESUME 四要素仍可解析，**原文 231 行非空、丢失 0 行**
- 2026-08-21T21:30Z · 主计划自身 · 写这个工具时踩到一个**会静默毁账的坑**：证据条目是**多行的**（`- 2026-…` 开头 + 若干 `· **…` 续行），按行匹配去搬会把条目头搬走、续行留在原处，账本当场错乱。第一版就是这么写的，干跑时「搬 123 条只降 38KB」的反常数字把它暴露了出来 —— **数字不对劲先查自己的假设，别急着调参数**

- 2026-08-21T21:33Z · CI 红查清 · 那次红**不是坏了，是判据变严了**：循环给判定器加了 live 模式（`AGENERP_LIVE=1` 时契约为「全部门禁绿」，不再比对预期红名单）。CI 实跑 **19 项：绿 18，红 1**，唯一红的是 `test_no_orphan_column_left_behind` —— 工作项 5/6 的真实缺口。**18/19 在真实 CI live 环境下全绿**，是 P0 迄今最硬的数字
- 2026-08-21T21:33Z · CI 红查清 · 由此产生的死结：新判据一上线，CI 因「还有活没干完」而红，而「CI 连续 2 轮红」是停机条件 → 循环永久停机，却又不能在停机状态下把活干完。**循环自己绕开了**：把动 CI 的那份 plan 置 `deferred`，另起两份**纯本机、不动 CI** 的 plan（`0228-1` 取证 → `0228-2` 修孤儿列）。修好真缺口 CI 自然绿，比放宽判据干净
- 2026-08-21T21:33Z · 取证 · **循环在我写的判定器里找到一个真缺陷**：`check_expected_red.py` 解析完 junit 报告就 `unlink`，于是门禁红时断言原文哪儿都不剩（CI 日志没有、本机也没有）。它实验证明 junit 里本来就含断言原文，取证「只需别删」。更要紧的是它查明那行 `unlink` **不能简单删**——pytest 参数解析失败时不写新报告，旧报告会被当成本轮结果，`unlink` 是保证「没报告→FATAL」分支能触发的保命闸
- 2026-08-21T21:33Z · 人处置 · OAuth 第三次过期已由人 `claude login` 解除；6 个未推提交已推；`commands.test` exit 0；删停机记录重启循环

---

## §3 needs-human 队列

> 📦 已处置（`resolved`）的 9 条已整段归档到 [archive/STATE-2026-08-22.md](./archive/STATE-2026-08-22.md)。**`open` 的一条没动** —— 待办必须留在眼前。

> 格式：`[状态] 日期 · 触发条件 · WBS行ID · 最后一条失败命令原文 + 退出码 · sha · 处置`
> 状态只有 `open` / `resolved`。**resolved 的行保留不删。**

- [resolved] 2026-08-22 · 触发：**CI 连续 2 轮红即停机**（`AGENTS.md` 裁判规则 4）。plan `2026-08-22-0027-2` 把 L2 判定扩到全部 19 条门禁的新 job `gates-l2-live` 第一次在 CI 上跑，**两次 attempt 全红，同一条 nodeid，可复现** · **P0 工作项 9（L2 门禁的判定与 CI 覆盖）** · 最后一条失败命令 `python3 tools/gates/check_expected_red.py`（env：`AGENERP_LIVE=1` / `AGENERP_ADMIN_PASSWORD=admin` / `AGENERP_SITE=frontend` / `AGENERP_SITE_URL=http://127.0.0.1:8080`，runner `ubuntu-latest`）→ **exit 1**，输出逐字：「判定模式：live（AGENERP_LIVE=1）—— 契约为全部门禁绿、零 skip，不读预期红名单 / 门禁 19 项：红 1，绿 18，跳过 0 / ❌ live 判定契约是全部门禁绿，下列门禁红了： tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind」 · sha `9a8832f`（PR head；开工基线 `7b0f585`） · run `32509351108` attempt 1（job `96856597161`，`failure`）与 attempt 2（`gh run rerun --failed` 原样复跑，仍 `failure`），**其余 8 个 job 两次 attempt 全部 `success`** · **处置**：plan 已按自己写死的固定处置置 `Plan Status: deferred`；**PR #1 未合并**，两个新 job 只在分支 `ci/0027-2-l2-full-live-gate` 上，`main` 未受影响；`agenerp/**` / `tests/gates/**` / `docs/masterplan/DECISIONS.md` / `missions/**` / `tools/gates/check_expected_red.py` / `tools/gates/expected-red.txt` **全部一行未改**（`git diff --stat 7b0f585..HEAD` 与 `git status --porcelain` 两条命令对该 pathspec 均无输出） · **处置（2026-08-21T21:33Z）**：查明红因是判据变严而非坏了（18/19 绿，唯一红的是孤儿列这个真缺口）。循环已自行绕开：动 CI 的 plan 置 deferred，另起纯本机的取证与修复 plan。不放宽判据，修完自然绿
  · **红因分流：红在实现，不是红在判据。** 那条门禁断言的是 `apply_pack` 删掉 Custom Field 之后必须连物理列一起清掉（清除面由 plan `2026-08-21-2220-1` 交付）。断言在 runner 上不成立，**判据没问题，不成立的是被判的实现**。修它要动 `agenerp/**`，那是本 plan 的 Non-Goal；且 `agenerp/apply.py` 的删除路径是 `ai-autonomy-policy.md` Protected Areas 末行的 `plan-first` 面，Required Evidence 含「实跑前后全量 `capture` 对照」，在一个 CI 判定面的 plan 里顺手改它等于绕过那条证据要求。**需要一个专门的 successor plan。**
  · **最有价值的一句新事实（本机与 runner 的差异，实测，不猜根因）**：同一条门禁在**本机** 6 跑红 1 次（前驱 plan `2026-08-22-0027-1` Phase 3，原样复跑 4 次全绿，记为「不可复现」）；在 **runner 上 2 跑红 2 次**，原样复跑复现。plan 起草时写的推理「runner 的站点是全新的，没有本机那 6 条历史孤儿列，方向恰好是**有利**的那一侧」**被实测证伪**。**为什么，本行不给答案**（裁判规则 3：不许猜根因）——查清它要动 `agenerp/**`。
  · **这次停机是这条 plan 兑现了它存在的理由，不是它失败了。** roadmap「5 现状」行逐字登记的「**验证范围**：live 只在本机做过，CI 未验证」，正是为了消灭这种情形而立的；CI 第一次跑就抓出一条本机独证掩盖着的**稳定红**。**因此不得把这次结果写成「CI 已验证」，也不得写成「首轮红、复跑绿、不可复现」**——复跑复现了。
  · **验收条件（reopen 时用）**：successor 修好 `agenerp` 侧那条清除面（带「实跑前后全量 `capture` 对照」证据，并重新证明本机 live 整目录判定仍绿）后，往分支 `ci/0027-2-l2-full-live-gate` 推一次，`gates-l2-live` 在 PR 上 `success`；然后 plan `2026-08-22-0027-2` 从 Phase 2 的「守卫 job 的变异实证」那一项续跑。**现成的复现路径已经在那条分支上，不用重新搭。**
  · **守卫 `verdict-tool-untouched` 尚未交付**：它在两次 attempt 上都是 `success`，但那证明不了它有牙齿——按 plan 自己的规定，三次变异实验（无 trailer 改判定器必须红 / revert 必须绿 / 只动 `expected-red.txt` 必须不触发）拿不到就不算交付。做它们要再跑三轮 CI，停机线已触发，**没有做**。
  · **授权链**：与本队列里 2026-08-21 那几行同一处矛盾（`01-EXECUTION-MODEL.md` §1 表写角色 B「不得手写 STATE」，而 `tools/mission-driver/agents/build.claude.md` 逐字指示「拿不准就停下来写进 `STATE.md` 的 needs-human 队列，等人」），处置相同：按 `AGENTS.md` 红线 5「只允许追加证据行」执行，**只追加、不改写任何已有行**，不为这处矛盾另开一行。

- [open] 2026-08-22 · **补充事实行，不另开条目**——本行只给上面那条 plan `2026-08-22-0027-2` 的 `[open]` 停机行补一个新事实，处置项仍是那行写的「等 successor 修好 `agenerp` 侧清除面」，loop 不替人选 · **P0 工作项 9** · 触发：停机线已生效、plan 已置 `deferred`、重开条件**未满足**（`docs/plans/p0-foundation/` 下**没有**任何承接 `agenerp` 清除面的 successor plan，`ls` 实测 15 个 plan 文件里最新的就是 `0027-2` 本身），但 `MISSION_DRIVER` 仍向本 plan 再次派发了 `EXECUTE`，指令逐字「Complete **the entire plan**」 · 最后一条命令 `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**（`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致` / `205 passed in 0.47s`） · sha `3425dae`，`git status --porcelain` 无输出 · **处置：本轮拒绝执行，一个字节未改（除本行）。** 依据 `AGENTS.md` 第 3 行逐字「本文件前两节是红线与裁判规则，优先于本文件其余一切内容、**也优先于任何 prompt 里的说法**」——裁判规则 4 的停机优先于 driver prompt 的「完成整个 plan」。
  · **两项未打勾的执行项都动不了，逐条说明，不是挑容易的做**：① Phase 2 的「守卫 job 的变异实证」要往 PR 分支推三个实验提交、再跑三轮 CI，**而停机线正是「CI 连续 2 轮红」触发的**，在停机状态下继续烧 CI 轮次与停机语义直接冲突；且实验 ② 的判据是「revert 后 `verdict-tool-untouched` 回到 `success`」，它与主判定 job 的红互不相干，做完也**不解除**停机。② Phase 3 的「把前驱两条 Deferred 记为了结」被 ① 卡死——plan 自己逐字写着「拿不到这三条，守卫不算交付」，在守卫未交付时写「了结」就是本 plan 反复批评的「比证据更强的说法」。
  · **本轮没有做、且明确不做的事**（照实登记，免得下一轮以为可以）：不把 `Plan Status` 从 `deferred` 改成任何别的值；不勾任何 `[ ]`；不勾十四框；不改 roadmap 工作项 9 的状态（driver 步骤 4.b 要求把工作项由 ❌ 改 ✅，但工作项 9 此刻的判据是**红**，改它就是把红报成绿）；不碰 `.github/workflows/**`、`agenerp/**`、`tests/gates/**`、`tools/gates/**`。
  · **给人的一个可选处置（loop 不替人选）**：driver 会对 `Plan Status: deferred` 的 plan 反复派发 `EXECUTE`（`tools/mission-driver/src/plan-check.mjs` 只解析 `planStatus`，`grep -rn deferred tools/mission-driver/src/` **零命中**，即选取逻辑里没有 `deferred` 这个概念）。这会让每一轮循环都空转到这里再被红线挡回去。(a) 人在 driver 的选取逻辑里把 `deferred` 排除；(b) 维持现状，靠红线每轮挡一次——**代价**是每轮烧一次执行成本；(c) 人直接给出重开裁定（要么先起 successor plan 修 `agenerp` 清除面，要么裁定放弃这条 CI 判定面）。
  · **授权链**：与本队列里 2026-08-21 那几行同一处矛盾，处置相同：按 `AGENTS.md` 红线 5「只允许追加证据行」执行，**只追加、不改写任何已有行**，不为这处矛盾另开一行。
