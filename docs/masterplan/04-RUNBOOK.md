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

## 3.5 起循环只走 `tools/run-loop.sh`，不要直接调 `mission-driver.sh`

```bash
tools/run-loop.sh                  # 单趟
tools/run-loop.sh supervise        # 7×24（监督器）
```

⚠️ **不要 `nohup ./tools/mission-driver.sh <mission> &`。** 它能跑起来，
但**绕过了 pidfile**（`_tmp/loop.pid`）—— 而监督器正是靠这个文件判断
「有没有一趟在跑」：

```bash
# loop-supervisor.sh:55
if [ -f "$ROOT/_tmp/loop.pid" ] && kill -0 "$(cat ...)" 2>/dev/null; then
  log "已有一趟在跑，等它结束"
```

**后果**：装了 launchd 代理之后，监督器看不见那个手工起的循环，
于是**并发起第二个**。两个循环同时写同一个工作树 —— 那正是 §4 末尾
逐字禁止的「7×24 里最难查的一类故障」。

2026-08-24 实测踩到：人侧手工起循环、随后准备装 launchd，
检查时才发现 `_tmp/loop.pid` 根本不存在。

**若已经手工起了**，补一句就能对上：

```bash
pgrep -f mission-driver | head -1 > _tmp/loop.pid
```

---

## 3.6 shell 里从管道取值：**默认当作会拿到多行**

2026-08-24 一天之内同一形态**踩了两次**，两次都是「安静地坏」——
不报错、不崩溃，只是比较不成立、代码悄悄走了另一条分支。

### 形态一：`|| echo` 在管道已输出后又追加一行

```bash
DEC=$(loopx ... | python3 -c '...' 2>/dev/null || echo unknown)
```

`loopx` 自身退非零，但管道里的 python **已经打印了** `loopx-unavailable`。
`||` 于是**又追加**一行：

```
DEC = "loopx-unavailable\nunknown"     # 长度 25，两行
```

任何 `[ "$DEC" = "..." ]` 都不成立 → 旁路永不触发 → 监督器一趟都跑不了。

### 形态二：`grep -c` 在管道里每个输入流各输出一个计数

```bash
LEAK=$(git log -3 -p | grep -icE "sk-..." || echo 0)
# LEAK = "0\n0"  →  [ "$LEAK" != "0" ] 为真  →  每轮误报
```

### 规矩

**凡从管道/子命令取值，取完立刻规整**：

```bash
V=$(... | head -1 | tr -d '[:space:]')          # 取一个词
N=$(... | awk '{s+=$1} END{print s+0}')          # 取一个计数
```

### ⚠️ 排查这类 bug 的方法（比推理省十倍时间）

我为形态一逐层推了**五轮**都没找到：脚本顺序对、逻辑单独测对、
变量单独取出来也对、plist 路径对、`kickstart` 也做了 ——
**每一层单独看都是对的**。

最后是加一行让脚本自己报告：

```bash
log "调试：DEC=[$DEC] 长度=${#DEC}"
#  → 闸 3 调试：DEC=[loopx-unavailable
#    unknown] 长度=25
```

**一行就够了。** 遇到「每层都对但合起来不生效」时，**先让程序自己说，
别继续推**。这与 AGENTS.md 裁判规则 3「不可复现不许猜根因」同一条理路。

---

## 4.1 GitHub Actions 配额（与 §4 的模型配额是两码事）

**症状与模型限流完全不同，别混。** 2026-08-24 实测踩到，卡了不少时间。

### 怎么认出来

| 现象 | 判读 |
|---|---|
| **全部 job 一起红**，含「主计划引用不断链」这种纯文档检查 | 不是判据问题 —— 判据不会集体失效 |
| job 存活 **3–9 秒**，`steps` 数为 **0** | 一步都没跑，是 GitHub 侧没启动 |
| 上一次成功的 run 时长是 **200–700 秒** | 对比即知：真跑过的 run 是分钟级 |

一条命令区分「真跑了红在判据」与「压根没跑」：

```bash
gh run list --branch main --limit 10 --json headSha,conclusion,createdAt,updatedAt \
  | python3 -c "import json,sys,datetime
for x in json.load(sys.stdin):
    a=datetime.datetime.fromisoformat(x['createdAt'].replace('Z','+00:00'))
    b=datetime.datetime.fromisoformat(x['updatedAt'].replace('Z','+00:00'))
    print(x['headSha'][:7], x['conclusion'], f\"{(b-a).total_seconds():.0f}s\")"
```

**< 30 秒 = 没跑起来；> 200 秒 = 真跑了。**

### 确诊：读 annotation

错误信息**不在日志里**（日志根本不存在），在 check-run 的 annotation 上：

```bash
RID=$(gh run list --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
JID=$(gh api "repos/{owner}/{repo}/actions/runs/$RID/jobs" --jq '.jobs[0].id')
gh api "repos/{owner}/{repo}/check-runs/$JID/annotations" --jq '.[].message'
```

实测拿到的原文：

> The job was not started because recent account payments have failed or your
> spending limit needs to be increased.

### ⚠️ 去哪看：**Budgets and alerts，不是 Overview**

这是当时最耽误事的一点。Billing Overview 页只显示用量与抵扣：

```
Current metered usage   $12.00
Current included usage  $12.00     ← 抵扣正好等于用量 = 免费额度已用满
Next payment due        –          ← 没欠款，所以「付款失败」是误导
```

**「没欠款」不等于「没问题」**：免费额度用满后，继续跑需要一个 > $0 的预算，
而消费上限现在在左栏 **Budgets and alerts** 里，不在 Overview。

### 处置

设一个 Actions 预算（本项目实测 **$12/月**，$20 上限绰绰有余）。

⚠️ **不要为了省这点钱去删库或改公开。** 当时评估过，代价是：
70 处 GitHub 侧证据（12 个 PR + 58 个 run/job ID）永久失效 —— 那是
「预测在前、结果在后、逐条吻合」全部实证的追溯依据；改公开还要额外
改写 259 个提交（个人邮箱在 88 个提交的作者字段里），连带 103 处 sha 引用。
**用 $20 换一条完整的审计链，这个交易不用犹豫。**

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
人的那笔 CI 提交。它自己发现并改准了（`44ce646`），但这属于运气。

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

## 5.6 凭据放哪（`.env` 里永远不放）

**规矩一句话：真凭据一律放仓库目录之外。**

```
~/.config/agenerp/secrets.env      # 0600，仓库目录之外
```

加载：

```bash
set -a; . ~/.config/agenerp/secrets.env; set +a
```

### 为什么不放 `.env`

`.env` **就在仓库目录里**。它今天被 `.gitignore` 挡着，但那是一层**约定**，
不是一道**墙**：

- 一次 `git add -A`（人侧刚踩过，见 §5.5）
- 一次 `.gitignore` 被谁改动
- 一次把目录整个打包 / 拷贝 / 同步到别处
- 一次 `docker cp` 或挂载整个工作目录进容器

凭据就出去了。**放在仓库目录之外，这些路径全部不存在** —— 不是「更难出错」，
是「那条路不通」。

### 当前放着什么

| 变量 | 用途 |
|---|---|
| `DASHSCOPE_API_KEY` | 百炼端点（P1 起的 LLM 调用）|
| `AGENERP_WORKER_PASSWORD` | 受限身份口令（`permission.scope` 判别力判据的前置）|

`.env` 里只留**非敏感配置**（引擎路径、端口、模型名这类），并留一行指路。
`.env.example` 里的凭据槽位**值一律留空**，只用来说明「能配什么」。

### 一条不许省的自查

**任何提交之前**，确认这条为空：

```bash
git diff --cached | grep -iE "api[_-]?key|password|secret|token" 
```

有输出就停下来**逐行看清楚再决定**。公开仓库上，提交过的 key 几分钟内会被
爬走，**撤销提交没用 —— 要当作已泄露去轮换**。

⚠️ **「停下来看」不是「看到数字就过」。** 这条规矩写完第一次用就被违反了：
人侧看到 `命中：1` 直接提交，事后补看才确认是虚警。**命中数不是判据，
命中的那一行才是。** 命令改成直接打印命中行，不打印计数：

```bash
git diff --cached | grep -inE "api[_-]?key|password|secret|token"
```

### 已知的虚警形态（看到这些可以过，但仍要看清是哪一行）

| 形态 | 例子 |
|---|---|
| 中文里的「token 账目 / token 用量 / reasoning token」 | 成本记账相关的正文 |
| `.env.example` 里的**空槽位** | `AGENERP_LLM_API_KEY=`（`=` 后无值）|
| `package-lock.json` 的 `integrity` 值 | `sha512-...` 中间可能含形似 `AKIA` 的片段 |
| 文档里说明「口令放哪」的句子 | 本节自身 |

**判据是「`=` 后面有没有真值」，不是「有没有出现这几个词」。**

---

## 5.7 `auth-expired` 停机的固定处置（今天已触发三次）

**这是 7×24 守护挡不住的唯一一类停机**，且会反复发生。

```
launchd    进程死了能重拉        ✓
监督器     循环挂了能重起        ✓
认证过期   谁都拉不起来          ✗  重拉起来的进程照样认证失败
```

### 三步

```bash
# ① 先验条件是否已消失 —— **不许跳过这步**
claude -p "只回两个字：在线"

# ② 回「在线」才清；没回就说明真过期，需人在交互式终端 claude login
rm .mission-halt.json

# ③ 重启
launchctl kickstart -k "gui/$(id -u)/com.agenerp.loop"
```

### ⚠️ 为什么第①步不能省

停机闸的设计意图是「**停机记录还在，就一次都不许再启动**」——
否则「停机」只是停了一轮，下一轮照常带病狂奔。

**不验就清 = 绕过闸。** 验了发现条件已消失再清 = 条件不再成立，这是两回事。

实测规律：token 常在过期后不久由别处的交互刷新掉，因此**多数情况下**
你来看时条件已经没了。但「多数情况」不是「总是」——必须每次验。

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
