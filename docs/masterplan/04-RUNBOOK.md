# 04 · 7×24 运行手册

> 面向**人**的操作手册。每天 15 分钟，出事按表处置。
> 本文件里的命令都假定已 `set -a; . docs/masterplan/evidence-repo.env; set +a`（需要访问证据仓时）。

---

## 0. 环境前提（这些一旦缺失，下面的命令会以看不懂的方式失败）

主计划的多条验收命令假定了下列环境。**开跑前逐条确认，缺哪条就先补哪条**——这类依赖过去常被写成「假定环境已就绪」，然后在半夜的循环里炸掉。

| 前提 | 谁需要它 | 怎么确认 |
|---|---|---|
| Docker + ERPNext 演示栈能起 | 四个 🚪 关口实验、所有 `-m live` 测试 | `docker compose ps` 在证据仓里有 healthy 服务 |
| `ollama` + `qwen3:14b` 已拉取 | `P1.0` L3 门禁重跑 | `ollama list \| grep qwen3:14b` |
| `node` 可执行 | mission-driver 引擎 | `node --version` |
| `gh` 已登录 | 看 CI 颜色 | `gh auth status` |
| `loopx` 在 PATH 上 | 配额决策（启用 LoopX 时） | `export PATH="$HOME/Library/Python/3.12/bin:$PATH"; loopx doctor` |
| `python3` ≥ 3.11 | spike 复跑、LoopX | `python3 --version`（本机 3.12.9 ✅） |
| **模型路由指向你以为的那个模型** | **一切**（监督会话、子代理、`--driver claude`） | `claude -p "ping"`。⚠️ 2026-08-20 本机实测失败：`~/.claude/settings.json` 把 `ANTHROPIC_BASE_URL`/`ANTHROPIC_MODEL`/`CLAUDE_CODE_SUBAGENT_MODEL` 全指向本地 `deepseek.local`。见 `W0.0b` |

**缺 `ollama`/`qwen3:14b` 只影响 `P1.0` 一行**，不影响其他工作项——按 [02-WBS.md](./02-WBS.md) 把该行标 `blocked` 并写明缺什么，先做别的，不要停在这里。

---

## 1. 冷启动预检（每次开机 / 换机器 / 长时间中断后）

逐条跑，**任何一条不过就不许开 7×24**：

```bash
# 1. 证据仓在不在、sha 对不对
git -C "$XM_PATH" rev-parse HEAD          # 应等于 evidence-repo.env 的 XM_SHA

# 2. 主计划引用没断链
tools/check-masterplan-links.sh           # 期望 exit 0

# 3. 门禁测试还在、没被动过
git log --oneline -- tests/gates | head    # 最近提交应全部出自人，不出自 loop

# 4. CI 上一次是绿的
gh run list --limit 3

# 5. 配额允许开跑（LoopX 启用时）
export PATH="$HOME/Library/Python/3.12/bin:$PATH"
loopx quota should-run

# 6. 引擎能起
node tools/mission-driver/src/engine.js --help
```

`loopx` 不在 PATH 上是常见现象（pip `--user` 装到 `~/Library/Python/3.12/bin`）。**这不算故障**，导出 PATH 即可；若 LoopX 整体不可用，按 [01-EXECUTION-MODEL.md](./01-EXECUTION-MODEL.md) §4 降级为手工 STATE.md，继续开工。

---

## 2. 启动与停止

```bash
./mission-driver.sh p0-foundation          # 启动当前阶段的 mission
```

停止：直接中断进程。**中断后必跑孤儿回收**（引擎自带 `reap-orphans.mjs` + `active-run-registry.mjs`，7×24 下这是刚需，不是可选）：

```bash
node tools/mission-driver/src/reap-orphans.mjs
```

---

## 3. 监控三面板（每天看的就是这三样 + STATE）

| 面板 | 地址 / 命令 | 看什么 | 异常信号 |
|---|---|---|---|
| **引擎** | `http://localhost:9300` | 当前 flow 步骤、plan 状态、循环次数 | 同一步骤反复出现（引擎自带 `maxCycleVisits: 8` / `pingPongWindow: 6` 会先报） |
| **CI** | `gh run list` | 最终裁判的颜色 | **连续 2 轮红 → 停机条件** |
| **成本** | `W0.0` 定出的统计脚本 | 本 mission 累计消耗 vs 阈值 | 超阈值 → 停机条件 |
| （状态） | [STATE.md](./STATE.md) §1 + §3 | 下一项是什么、有没有 needs-human 排队 | §3 有未 `resolved` 的行 → 先处理它 |

---

## 4. 配额策略（7×24 的现实约束）

**限流窗口是常态，不是故障。** Opus 5 订阅在连续运行下必然撞到窗口，此时正确的行为是**安静等待**，不是重试、不是换模型、更不是降级成「先写点文档」。

| 场景 | 做什么 |
|---|---|
| `loopx quota should-run` 说等 | 等。不重试，不改配置 |
| 撞窗口时 loop 正跑到一半 | 让当前 plan 跑完 `GATE_VERIFY` 再停；停在门禁之前的中间态最难恢复 |
| 恢复后 | 从 STATE §1 的「下一项」继续，**不重跑已 `done` 的行** |
| LoopX 未启用 | 人工判断：撞窗口就停机，恢复后重新 `./mission-driver.sh` |

**不要**为了绕开限流去开多个并发会话跑同一个 mission——两个会话同时写同一批文件是 7×24 里最难查的故障源。LoopX 的 todo 认领/租约（`loopx todo claim` / `task-lease`）就是为这件事准备的。

---

## 5. 停机条件响应表

判据正文见 `REF:HALT`。**四条都是「宁可停，不带病狂奔」**。

| 触发 | 第一反应 | 禁止的反应 | 处置 |
|---|---|---|---|
| 同一 plan 连续 3 轮 `GATE_VERIFY` fail | 走 CP6：**先原样复跑那条命令** | 直接改测试让它过 | 复现 → 根因 → 修实现或修 WBS 行（判据错了也是一种可能，但要人拍板） |
| `git diff` 触及 `tests/gates/**` | **立即停机**，查是谁改的 | 「这次是善意修改」 | 若出自 loop → 视为门禁失效事件，回滚改动、记 R-3、检查 CI 是否也漏放 |
| 单 mission 成本超阈值 | 停机，算清楚钱花在哪 | 提高阈值继续跑 | 复盘单 plan 平均消耗；必要时缩小 plan 粒度 |
| CI 连续 2 轮红 | 停机 | 本地绿就当过了 | **CI 是唯一本地 AI 篡改不了的裁判**，本地绿 CI 红一律以 CI 为准 |

处置全程走 [01-EXECUTION-MODEL.md](./01-EXECUTION-MODEL.md) §2 的五步，产物是 STATE §3 的一条 `needs-human` 记录 + 解除时的证据行。

---

## 5.5 人与 loop 并发写同一个仓库时的操作纪律

**7×24 的默认状态是：loop 正在写这个工作树。** 人在同一时间做任何事，都得
按「有另一个作者正在改文件」来做。三条，都是踩出来的。

### ① **不许 `git add -A` / `git add .`**

2026-08-24 实测踩到：人做 CI 配置修复时用了 `git add -A`，把 loop **还没写完**的
`agenerp/orchestration/` 三个模块一起提交了。后果不是冲突（那反而好办），
而是**归属错乱**——loop 收口时按 sha 记证据，那三个模块的产出 sha 变成了
人的那笔 CI 提交。它自己发现并改准了（`ed63c68`），但这属于运气。

> **只 add 自己实际动过的文件，逐个写路径。**
> `git add docs/masterplan/STATE.md .github/workflows/gates.yml` ✅
> `git add -A` ❌

### ② 动手前先看 `git status`，动手后再看一次

前看是为了知道 loop 正在碰哪些文件（`??` 与 `M` 都算），**避开它们**；
后看是为了确认自己没扫到别的。两次都要看 —— loop 在你编辑的这几分钟里
可能又新建了文件。

### ③ 红线内的文件由人改，但**改完要让 loop 知道**

`tests/gates/**`、`.github/workflows/**`、`AGENTS.md` 这些 loop 碰不了，
只能人改。改完**必须**在 STATE §3 把对应的 needs-human 条目收掉 ——
否则 loop 会一直把它当未决项挂着，每轮都重新提一遍。

### 为什么不干脆让 loop 停下来等人

试过这个念头，否决理由记下来：**停机是有成本的**（一轮 opus 调用的上下文
要重建），而人改配置往往只要几分钟。用「避开它正在写的文件」换「不停机」
是划算的 —— 前提是上面三条真的照做。

---

## 6. 崩溃恢复

| 症状 | 处置 |
|---|---|
| 机器重启 / 进程被杀 | `reap-orphans.mjs` → 冷启动预检 → 从 STATE §1 继续 |
| 工作区一团糟（半成品改动） | **不要 `reset --hard`**。先 `git status` 看清、`git stash` 存档，再从 STATE §2 最后一条证据行的 sha 出发判断做到哪了 |
| STATE 与 LoopX 打架 | 以 LoopX 为准（STATE 是投影）；把差异记进 STATE §2 |
| STATE 与 git 打架 | 以 **git + 门禁退出码**为准。STATE 可能是上一个会话没写完 |
| 不知道跑到哪了 | `git log --oneline -10` + `ls docs/plans/<mission>/` + STATE §2 末尾三行。三者交叉能定位 |

---

## 7. 仪式

### 7.1 每日 15 分钟

1. STATE §1 快照——**当前阶段 / 下一项 / 有没有 needs-human**（2 分钟）
2. `:9300` 面板扫一眼有没有原地打转（3 分钟）
3. `gh run list` 看 CI 颜色（2 分钟）
4. 成本对一下阈值（2 分钟）
5. 抽查**一条**昨天写的证据行：把命令原样重跑，看是不是真的退 0（5 分钟）

第 5 步是整套仪式里最有价值的一步——**抽查是让「只认退出码」这条规矩真正生效的唯一手段**。

### 7.2 每周 / 每阶段关口（CP9）

走 [03-SKILL-GATE-MAP.md](./03-SKILL-GATE-MAP.md) §A9 模板。**阶段关口必答第 6 项：方法论续用复评**，判据事先写死如下：

| 对象 | 续用 | 停用 |
|---|---|---|
| **AGE / mission-driver** | 本阶段有 ≥1 个工作项**完整地**由循环推完（drafted → executed → 门禁绿 → 关闭），且门禁误放行（判 pass 但其实错）次数 = 0 | 出现门禁误放行 ≥1 次且根因在引擎；或全阶段没有任何工作项能不靠人接管跑完 |
| **LoopX** | 跨会话恢复实际生效 ≥3 次（新会话靠 LoopX 状态正确接上），且与 mission-driver 无「谁说了算」的冲突 | 出现 ≥2 次状态冲突；或跨会话恢复从未真正用上（说明它只是多一层账） |

**结论只有「续用」「停用」两种，不许写「继续观察」。** 观察期就是这一个阶段。

---

## 8. 一页速查

```
开工   → tools/check-masterplan-links.sh && loopx quota should-run && ./mission-driver.sh <mission>
看状态 → docs/masterplan/STATE.md §1   |  http://localhost:9300  |  gh run list
出事   → 先复跑失败命令，再分析。三连败走 CP6，触碰 tests/gates 立即停机
收工   → 往 STATE.md §2 追加证据行：时间 · WBS行ID · 命令→退出码 · sha · 下一项
恢复   → claude "按 docs/masterplan/README.md §2 恢复监督会话"
```
