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

- 2026-08-20T13:39Z · W-1.1 · `git -C $XM_PATH commit docs/next/{ARCHITECTURE,ROADMAP}.md` → exit 0 · sha `1c622c8` · XM 冻结为只读证据仓，下一项 W-1.2
- 2026-08-20T13:39Z · W-1.2 · `git init -b main` + `mkdir -p docs/masterplan tools` → exit 0 · sha `(pending)` · 新仓建立于 `/Users/lize/Documents/claude/AgenERP`
- 2026-08-20T13:39Z · W-1.3 · `pip3 install --user loopx` → exit 0 · **loopx 0.5.0**；`loopx doctor` → `ok: True`；`loopx quota should-run` 命令存在 · D-6 的 Day -1 部分成立
- 2026-08-20T13:39Z · W-1.3 · `loopx slash-commands --install` → exit 0 · `created=50`，`~/.claude/skills` 已含 `/loopx` · Claude Code 适配器就位
- 2026-08-20T13:39Z · W-1.3 · 技能装机核验：`~/.claude/plugins/installed_plugins.json` 仅含 `superpowers@6.2.0` 与 `frontend-design` → **mattpocock / grill-me / tospec 未装**，按 D-4 走 [03](./03-SKILL-GATE-MAP.md) 附录 A 内置清单，不阻塞
- 2026-08-20T13:39Z · W-1.2 · 九件套落盘（8 份 md + 校验脚本），`tools/check-masterplan-links.sh` 待跑 · 下一项 W-1.5（T1–T4）

- 2026-08-20T13:45Z · W-1.2 · `git commit` → exit 0 · sha `63fbd96` · 八份文档 + 两个校验脚本落盘
- 2026-08-20T13:45Z · W-1.4 · CP1 质询（§A1 十问）→ 两处修订落盘（P1+ 验收命令标为占位形状；新增环境前提表）· 记录 `docs/audits/2026-08-20-CP1-masterplan-grill.md`
- 2026-08-20T13:45Z · W-1.5 · `tools/check-masterplan-links.sh` → **exit 0**（35 条引用，断链 0，未登记 REF 0）· **T2 通过**
- 2026-08-20T13:45Z · W-1.5 · `tools/check-state-consistency.sh` → **exit 0**（RESUME 四要素静态可解析）· T1 的机械部分通过，行为部分未测
- 2026-08-20T13:45Z · W-1.5 · `claude -p "回复两个字：在线"` → **失败**：`There's an issue with the selected model (deepseek.local)` · **T1/T3/T4 全部阻塞**，转 §3

- 2026-08-20T13:53Z · W-1.6 · `plan.html` 写完（23.7K 字符，全内联无外部资源，明暗双主题）· 发布 Artifact **失败**：`essential-traffic-only`（`~/.claude/settings.json` 的 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`）→ 以本地文件交付
- 2026-08-20T13:53Z · W-1.7 · `git tag masterplan-v1` → exit 0 · Day -1 收尾，下一项 W0.0（实际前置 W0.0b）

- 2026-08-20T13:56Z · W-1.3 · marketplace 搜索安装 mattpocock / grill-me / tospec → **无法尝试**：`SearchPlugins` 与 `SearchSkills` 均返回 `unavailable`（同一条 `essential-traffic-only` 限制）· 按 D-4 走内置等效清单，不阻塞

- 2026-08-20T14:01Z · W0.0b · 项目级覆盖尝试**失败**（两次）：`.claude/settings.local.json` 里把 `ANTHROPIC_*` 置空 → 仍解析为 `deepseek.local`；`claude --model opus -p` → 同样被 `env.ANTHROPIC_MODEL` 压过。**结论：`env.ANTHROPIC_MODEL` 优先于 `--model` 参数与项目级覆盖，只能改 `~/.claude/settings.json`**
- 2026-08-20T14:01Z · W0.0b · Keychain 中**存在 Claude Code 订阅凭据**（`security find-generic-password -s "Claude Code-credentials"` 命中），`~/.claude/.credentials.json` 不存在 → 移除代理配置后可退回订阅登录，无需重新走 OAuth
- 2026-08-20T14:01Z · D-7 · 用户拍板：坚持在 ERPNext 之上做，不重造会计内核 · 已落台账，含翻案条件

- 2026-08-20T14:14Z · W0.0b · 改 `~/.claude/settings.json`：移除 `ANTHROPIC_BASE_URL`/5 个模型键/`CLAUDE_CODE_SUBAGENT_MODEL`/`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`/`apiKeyHelper`，`model` 置 `opus`；备份在 `~/.claude/settings.opencreate.bak.json`（一条 `cp` 可切回本地模型）
- 2026-08-20T14:14Z · W0.0b · `claude -p "回复两个字：在线"` → **exit 0，返回「在线」** · sha `834e74a` · 订阅路径打通。⚠️ 当前桌面会话的进程环境仍是旧的（`env` 里还有 `ANTHROPIC_MODEL=deepseek.local`），**需重启桌面端才干净**；本轮测试用 `env -u …` 清掉后跑
- 2026-08-20T14:14Z · W-1.5/T1 · 全新 headless 会话仅给 RESUME 命令 → **通过**：四件事一条回复给全，并自行识破 STATE §1「W0.0 但实际前置是 W0.0b」的歧义 · sha `834e74a` · 据此收紧该字段为「只填一个 ID」
- 2026-08-20T14:14Z · W-1.5/T3 · 全新会话只读 masterplan 干跑 W0.1 → **通过**：不提问，产出完整步骤 + 三分支证据行格式 · sha `834e74a` · 并揪出 DECISIONS「只增不改」与「结论写回 D-1」的冲突 → 已补边界定义
- 2026-08-20T14:14Z · W-1.5/T4 · 演习会话按 01 §2 五步处置模拟停机 → **通过**：`pytest tests/gates/test_normalizer_idempotent.py -q` → exit 4（记录为 exit 1）、`git cat-file -t deadbee` → exit 128，判「不可复现」拒绝猜根因 · sha `834e74a` · 并揪出第 4 步缺「不可复现」处置路径 → 已补为四选一
- 2026-08-20T14:14Z · W-1.5 · `tools/check-state-consistency.sh` 一度 **exit 1**（`02-WBS 里没有 W0.0b 这一行`）→ 判据写窄了（表里 ID 是加粗的），修 grep 后 exit 0 · sha `834e74a` · 校验脚本本身也归判据管

- 2026-08-20T14:39Z · W0.0b · 重启桌面端后 `env | grep -E '^ANTHROPIC|NONESSENTIAL'` → 只剩 `ANTHROPIC_BASE_URL=https://api.anthropic.com`，模型覆盖与流量开关均已消失 · 进程环境干净，W0.0b **完成**
- 2026-08-20T14:39Z · W-1.6 · Artifact 发布 → 成功：<https://claude.ai/code/artifact/88e80606-2137-4df4-923b-94ccdf5dff3b> · sha `7cd909b` · 之前的 `essential-traffic-only` 拦截随重启解除
- 2026-08-20T14:39Z · W-1.3 · 流量开关关闭后重试 marketplace 搜索：`SearchPlugins`/`SearchSkills` 均返回**空结果**（非报错）· mattpocock / grill-me / tospec **不在本账号可见的目录里**，需自行 add marketplace 才有；按 D-4 继续走 03 文件的内置等效清单，**此项就此关闭，不再重试**

- 2026-08-20T14:43Z · W0.1 · `curl -sS -o /dev/null -w '%{http_code}' -L https://github.com/AgenERP` → HTTP 404 / exit 0；`gh api /users/AgenERP` → exit 1 · sha `7ced79d` · GitHub 命名空间未占用
- 2026-08-20T14:43Z · W0.1 · `curl … https://pypi.org/pypi/agenerp/json` → HTTP 404 / exit 0；`… /agen-erp/json` → HTTP 404 / exit 0 · sha `7ced79d` · PyPI 两个名都未注册；「过于相似」拒绝风险仍在，记录不阻塞
- 2026-08-20T14:43Z · W0.1 · `curl … https://rdap.verisign.com/com/v1/domain/agenerp.com` → HTTP 200 / exit 0 · sha `7ced79d` · 域名仍被他人持有，符合 D-1 已接受风险，不触发翻案
- 2026-08-20T14:43Z · W0.1 · 结论：**D-1 维持 AgenERP**，复核行已追加进 DECISIONS D-1（只增不改，按 T3 演练确定的落点）

- 2026-08-20T14:45Z · W0.2 · 克隆上游模板 `entropy-cloud/attractor-guided-engineering-template` @ `58f7df70`（MIT）→ 先读 `install-age.sh`/`install-age.mjs`：只按 manifest 拷贝、跳过已存在文件、无 rm/unlink/强制覆盖，确认后才执行
- 2026-08-20T14:45Z · W0.2 · `./install-age.sh /Users/lize/Documents/claude/AgenERP "AgenERP"` → exit 0，**copied 88 / skipped 0** · sha `4ad71b2` · `docs/{architecture,design,backlog,context,testing,archive,plans}` 七个目录全部存在，验收通过；`docs/masterplan/` 未被触碰
- 2026-08-20T14:45Z · W0.2 · ⚠️ 遗留：安装器把 `.env` 的 `MISSION_DRIVER_HOME` 指向了 scratchpad 里的临时克隆（`/private/tmp/.../age/tools/mission-driver`）· **W0.8 把引擎 vendor 进 `tools/mission-driver/` 后必须改掉**，否则临时目录一清就断
- 2026-08-20T14:48Z · W0.3 · `ARCHITECTURE.md`（69805 字节/1159 行）按语义拆成 8 份（architecture 5 + design 3），**覆盖校验：未覆盖的非空行 0 行** · sha `b705106` · 章节编号原样保留，因为 REF 表按标题原文定位
- 2026-08-20T14:48Z · W0.3 · `find docs -name '*.md' -size +30k` → **输出为空**（最大 11220 字节：design/agents-and-roles.md）· 验收通过
- 2026-08-20T14:48Z · W0.3 · REF 表 6 条 ARCHITECTURE 的 **M 行**重指向仓内路径后 `tools/check-masterplan-links.sh` → exit 0（35 条引用 / 断链 0）· **这正是复盘时预判的「Day 0 打断锚点」，按 M/E 分类逐条重指向后闭合**

- 2026-08-20T14:51Z · W0.4 · ROADMAP 迁入 `docs/backlog/implementation-roadmap.md`（16213 字节）；原则 4「每阶段一个 change proposal」→「每阶段一个 mission，work item = 1–2 个 plan，关闭以 GATE_VERIFY 退出码为准」；P0 交付表「OpenSpec 初始化」→「AGE 骨架安装 + mission 配置」 · sha `f7dcc91`
- 2026-08-20T14:51Z · W0.4 · 判据①`grep -c OpenSpec docs/backlog/implementation-roadmap.md` → **0** · 判据②`node -e "parseRoadmapMarkdown(...)"`（引擎自己的 `roadmap-check.mjs`）→ **解析出 6 个阶段，overallProgress 0，roadmapAllDone false**，exit 0
- 2026-08-20T14:51Z · W0.4 · ⚠️ 原 WBS 判据只有 grep 一条，**太松**：照那个写出来的 roadmap 引擎可能根本解析不了（`## Work Item Status` 是硬契约标题）。按 01 §2 第 4 步的「修 WBS 行」补了判据②
- 2026-08-20T14:51Z · W0.4 · 定下分工防双真相源：**全局索引（本文件）的阶段状态由人维护；各 mission 的 roadmap 由引擎回写**，mission 的 `roadmapPath` 指向后者 · 已写进 W0.9 行的验收

- 2026-08-20T14:52Z · W0.5 · `AGENTS.md` 前置「红线 7 条 + 裁判规则 5 条 + 北极星」，声明其优先于本文件其余内容与任何 prompt · `grep -q 'tests/gates' AGENTS.md` → **exit 0** · sha `954283b` · 红线含：不碰 tests/gates、不放松 CI、不改 DECISIONS 已有行、不自行改名、masterplan 只读且 STATE 只追加、证据仓只读、不生成运行时 Server Script

- 2026-08-20T14:54Z · W0.6 · 手写 P0 四个红测试（13 个断言，含 `conftest.py` 的三个 harness 接缝 fixture）· `python3 -m pytest tests/gates -q` → **6 failed / 7 errors / 0 passed**，`-m 'not live'`（L1）→ **5 failed / 8 deselected** · sha `1ddf4aa` · **全红即通过**
- 2026-08-20T14:54Z · W0.6 · 第一版 7 个 error 红在「fixture 不存在」而非「实现不存在」——**红得不对**。补 `tests/gates/conftest.py`：三个 fixture 存在但抛 `NotImplementedError` 并指向 roadmap P0 的对应交付项，实现到位时把 raise 换掉即可
- 2026-08-20T14:54Z · W0.6 · `tests/gates/README.md` 写明四条判据的出处（roadmap 阶段验收 + Spike 06/10 打脸点）与「要改判据走 needs-human 五步」

- 2026-08-20T14:57Z · W0.7 · **发现真问题**：门禁故意全红 → CI 直接跑必然红 → 停机条件「CI 连续 2 轮红」从第一天就误触发，等于失效。解法：`tests/gates/EXPECTED_RED.txt` 预期红名单 + `tools/gates/check_expected_red.py` 判定器，把「故意的红」与「真的坏了」分开
- 2026-08-20T14:57Z · W0.7 · 判定器三个反向测试全部抓到：①名单外新增红 → 报「真的坏了」②名单内意外变绿 → 报「名单过期」③给门禁加 skip → 报「不允许 skip」· 退出码实测：偏差 **exit 1**，一致 **exit 0** · sha `fe6210b`
- 2026-08-20T14:57Z · W0.7 · `.github/workflows/gates.yml` 五个 job：`gates-untouched`（改门禁需 `Gates-Change-Approved-By:` trailer）/ `expected-red-ratchet`（名单只能变短）/ `gates-l1` / `masterplan-links` / `roadmap-parseable` · YAML 语法校验通过
- 2026-08-20T14:57Z · W0.7 · ⏸ **未完成部分**：「一次 push 触发 CI，结果可见」需要 GitHub 远程仓，建仓属对外发布动作 → 转 §3 等人拍板（公开/私有）

- 2026-08-20T15:05Z · W0.8 · vendor 引擎 `tools/mission-driver/`（5.7M/202 文件），钉死上游 `58f7df70`；`node tools/mission-driver/src/main.js --help` → exit 0 · sha `bbbffc5`
- 2026-08-20T15:05Z · W0.8 · 三个补丁全部落地并端到端验证：**未注册 gate-verify 时 flow 加载 throw `Unknown scriptId`**（证明 P1 必要）→ 注册后 flow 步骤变为 `EXECUTE → CLOSURE_SCRIPT_CHECK → CLOSURE_AUDIT → BUILD_VERIFY → GATE_VERIFY`，`BUILD_VERIFY.pass` 改为 `goto GATE_VERIFY`，`GATE_VERIFY.run` 是可调用函数
- 2026-08-20T15:05Z · W0.8 · P2 `tools/gates/gate-verify.mjs` 四情形实测：全绿→pass；`test` 退 1→fail 且**真实报错原文回灌**（含「期望 3 实际 4」）；无命令→fail；**改动 `tests/gates/README.md` → 立即 fail 并列出被改文件**（写保护第 1 层生效）
- 2026-08-20T15:05Z · W0.8 · 引擎回归：上游原始克隆 621 pass / **2 fail**（`mission-check Case D`、`FlowEngine null marker`），本仓打补丁后失败集合**逐条相同** → 补丁未引入新失败。基线记入 `tools/mission-driver/VENDOR.md`
- 2026-08-20T15:05Z · W0.8 · 中途 `doc-line-refs` 多挂一条，查明是 vendor 边界漏了兄弟文件 `tools/check-doc-references.mjs`；补齐后该检查扫出**我们自己文档的 6 处问题**（2 处行号引用会烂、1 处迁移后指向证据仓的悬空路径、3 处模板遗留），已逐条修，`node tools/check-doc-references.mjs` → **exit 0，24 份文档全部通过**
- 2026-08-20T15:05Z · W0.8 · `.env` / `.env.example` 的 `MISSION_DRIVER_HOME` 由 scratchpad 临时路径改为 `tools/mission-driver`；`./tools/mission-driver.sh list` → exit 0，列出 base/demo/onboarding

- 2026-08-20T15:09Z · W0.7 · 建私有仓 `lize-agent-engineering/AgenERP` 并 push（15 个提交）· 首次 CI 运行 `32384206077`：**5 个 job 中 4 绿 1 红**
- 2026-08-20T15:09Z · W0.7 · 红的是 `masterplan-links`——**又是「注定红」的病**：CI 里没有证据仓，E 类引用必然断，而我却让它 exit 1。一个注定红的检查等于没有检查，还会废掉「CI 连续 2 轮红 → 停机」。改判定器：证据仓不在场时 E 类跳过、M 类照查
- 2026-08-20T15:09Z · W0.7 · 改完后暴露真问题：**14 条 M 类引用在 CI 里断**——方案 C 设计文档（12 条）与建设前验证报告（2 条）标着「随仓迁移」却从没迁。两份都已迁入 `docs/analysis/` 并重指向 · 模拟证据仓缺失：`bash tools/check-masterplan-links.sh` → **exit 0**（29 条校验 0 断链，跳过 6 条 E 类）；本机全量 → exit 0（35 条 0 断链）
- 2026-08-20T15:09Z · W0.7 · 补 `LICENSE`（GPL-3.0，675 行）——架构 §16 早已裁定但仓里一直缺这个文件

- 2026-08-20T15:16Z · W0.8b · 按 pi/cline 的既有模式加 `--driver claude`：`CLAUDE_DEFAULTS` + `resolveDriverFields` + 三个 return 点透传 + 帮助文本 3 处 · `node --check` 全过
- 2026-08-20T15:16Z · W0.8b · **设计假设被实测打脸**：原以为 `claude -p` 会自动加载项目根的 `AGENTS.md`（红线所在）。实测问它「红线第 1 条是什么」→ **回答「上下文里没有」**。一个不知道红线的执行器，第一件事就可能去改门禁 → 改为显式下发：新增 `agents/build.claude.md`（压缩版红线+裁判规则），由 runner.js 读内容注入 `--append-system-prompt`（照 cline 的 `-s` 注入模式）
- 2026-08-20T15:16Z · W0.8b · 验收：用 `_buildDriverArgs` 拼出的**真实 argv** 跑一次 → 两问都答对（「不得修改 tests/gates/**」「由 GATE_VERIFY 退出码裁定，我无权自报通过」）· sha `864fa5d`
- 2026-08-20T15:16Z · W0.8b · token 实测：基线（不带 settings）**25,605** / 带 loop settings **21,709** / 带 settings+人格 **22,765**。净省约 2,800/轮。⚠️ 注意此处泄漏量远小于 spike/02 记录的 ~37K —— 那是在装了 SessionStart hook 的 XM 仓测的，泄漏量取决于本机装了什么，**不是常数**
- 2026-08-20T15:16Z · W0.0 · 成本基线第一个数据点：单轮最小往返（opus，22,765 输入 token）CLI 报 **\$0.231**。⚠️ 这是 API 计价口径的换算，订阅下不直接扣款，但可作 burn 代理指标。单 mission 阈值待 W0.9 跑通后按真实步数测算

- 2026-08-20T15:19Z · W0.9 · `missions/p0-foundation.json` + `docs/backlog/p0-foundation-roadmap.md`（8 个工作项，逐项绑定门禁测试）· 引擎校验器 `mission-check.mjs` → `valid: true`；`parseRoadmapMarkdown` 解析出 **8 项，第一个 todo = 定制包规范化器** · sha `fa0ce94`
- 2026-08-20T15:19Z · W0.9 · `node ... p0-foundation --dry-run` → **exit 0，run-state.status = completed**，Model 显示 `opus`。验收通过
- 2026-08-20T15:19Z · W0.9 · `commands` 只放**现在真跑得起来的那一条**（`check_expected_red.py`）。本机 ruff/mypy/docker 都没有，写进去等于每个 plan 一开局就 fail —— 它们本身就是 P0 的交付物，装上再加
- 2026-08-20T15:19Z · W0.9 · **上游两处坑，均实测确认**：① `base.json` 自称 shared defaults，但主运行路径上 `loadBaseAndInjectEnv()` 只注入 env、返回值被丢弃 → `base.model`/`base.driver` **安静地不生效**，必须写进各 mission；② 上游 base.json 预置了 `REPLACE_WITH_YOUR_TEST_COMMAND` 之类占位符，一旦某 mission 写了 `extends` 又忘覆盖，GATE_VERIFY 会去执行这条字符串 → 已清空并写明原因

- 2026-08-20T15:21Z · W0.10 · `missions/prompts/build-verify.md` 覆盖上游版（走上游自带的同名覆盖机制，不改 vendor 原件）· `grep -ciE 'maven|jira|-pl '` → **0** · 引擎实测加载到的是项目侧版本（含「门禁按 TDD 故意全红」段，Maven 段消失），2333 字符 vs 上游 4995 · sha `865982d`
- 2026-08-20T15:21Z · W0.10 · 初稿留了一段「Maven/Jira 在这里不适用」的解释，judged 判据不过。想清楚后判据是对的：**覆盖之后模型根本看不到上游那份**，每轮再花 token 讲一遍不适用什么纯属噪声 → 删掉，理由留在提交信息里

- 2026-08-20T15:27Z · W0.14 · 空转冒烟三场景（`--dry-run`，agent 步 mock、script 步真跑，零 token、不产业务代码）：A `commands.test` 通过 → GATE_VERIFY **pass**；B 退非 0 → **fail 且 retry EXECUTE**；C 改动 `tests/gates/**` → **停机** · sha `dbf0469`
- 2026-08-20T15:27Z · W0.14 · **场景 C 抓到设计与实现的缺口（两层）**：① 碰门禁原本只返回 `fail`，会被 flow **重试 3 轮 EXECUTE** 才终局——一次红线违规白烧三轮，且与「测试没过」混为一谈 → 新增独立 marker `halt`，`halt → done: failed` 不重试；② 更严重：plan 层终局后 **mission 层仍继续跑到 `completed`**，等于「碰了裁判之后照常干活」 → gate-verify 违规时 `process.exit(2)` 并落 `.mission-halt.json`
- 2026-08-20T15:27Z · W0.14 · 停机闸：`tools/mission-driver.sh` 启动前检查 `.mission-halt.json`，**存在即拒绝启动（退 2）**。7×24 靠反复重启，不设这道闸「停机」只停一轮。清除由人做
- 2026-08-20T15:27Z · W0.14 · 固化为 `tools/gates/smoke-loop-wiring.sh`（9 项断言）并进 CI · 本机 exit 0；**首次进 CI 挂第 9 条**——`.env` 是 gitignored，全新克隆里 shim 找不到引擎，看着像「闸放行不了」实为没 bootstrap → 脚本改为缺 `.env` 时自 `.env.example` 生成、结束删除
- 2026-08-20T15:27Z · W0.14 · RESUME 协议新增**第 0 步：先看停机记录**，存在即一切让路

- 2026-08-20T15:34Z · W0.0 · **首次真实（非 dry-run）循环跑通**：`--driver claude` + opus，冒烟 mission 在 `_smoke/` 内写出 `artifact.md`（「hello from loop」），CHECK→EXECUTE→CLOSURE_SCRIPT_CHECK→CLOSURE_AUDIT→DRAFT_PLANS→DEEP_AUDIT 全走完，**产品代码一个字未动**（`git status` 仅多出未跟踪的临时 mission 文件）· sha `6cc80f5`
- 2026-08-20T15:34Z · W0.0 · **成本基线（驱动方式：claude driver / Opus 5 订阅）**：一个完整循环 = 4 个无头会话 / 56 条助手消息 / **输入 1,599,358 token、输出 22,978**、墙钟 **3 分 36 秒**，按 Opus API 价换算 **≈ \$2.31**。测法：读 `~/.claude/projects/-Users-lize-Documents-claude-AgenERP/*.jsonl` 逐条加总 usage，**排除监督会话自身**（第一次没排除，读出 1,994 万 token 的假数，其中 1,844 万是我自己的）
- 2026-08-20T15:34Z · W0.0 · 据此定阈值：`missions/p0-foundation.json` 设 `maxTotalSteps: 120`（≈15–20 个循环 ≈2,500 万输入 token ≈\$35 当量），上游默认 500 步对 7×24 太松。⚠️ 外推：3.6 分钟/循环 → 约 400 循环/日 → 日当量近千美元级 —— **订阅下不是钱的问题，是必然撞限流窗口**，这正是 D-6 采用 LoopX 配额调度的实测依据
- 2026-08-20T15:34Z · W0.0 · ⚠️ 已知缺口：「单 mission 累计成本超阈值 → 停机」目前**由步数上限代理**，没有真正的 token 计量器。真要按 token 停机，需要一个读 transcript 的预算检查器 —— 记在此，P0 复盘时决定要不要做

- 2026-08-20T15:38Z · W0.12 · LoopX 闭环跑通（用时约 25 分钟，远在 2 小时上限内）：`bootstrap` → `register-agent supervisor-a` → `todo add`（WBS 项级）→ `refresh-state` → `quota should-run --goal-id --agent-id` → **`decision=run, should_run=True`** · sha `f90eae4`
- 2026-08-20T15:38Z · W0.12 · **决定性实验**：给工作项 1 的 todo 挂上 `--validation-command "pytest tests/gates/test_normalizer_idempotent.py"`（现在是红的），然后**谎报完成**（evidence 写「我做完了，测试应该能过」）→ LoopX **自己复跑校验命令**，`exit_code:1 passed:false`，**拒收，todo 仍为 open**。反面：校验命令退 0 的那条 → `ok:true` 接受，状态转 `done`
- 2026-08-20T15:38Z · W0.12 · 写回闸 `tools/loopx-writeback.sh`：配额闸 → 跑 mission → **按退出码单向写回**（0 → 请求完成；2 → 标 blocked 并说明撞停机；其他 → 保持 open）。端到端实测：mission 退 0，但工作项**仍未被接受**，因为它自己的校验命令没过 —— 「mission 成功 ≠ 工作项完成」这条分层契约在实现层成立，不只是文档说法
- 2026-08-20T15:38Z · W0.12 · 两处工程细节：① `loopx` 是 `pip --user` 装的，**不在非登录 shell 的 PATH 上** → 脚本用 `LOOPX_BIN` 兜底；② `.loopx/` 与 `.codex/` 已进 `.gitignore`（LoopX 自己也警告 registry 应当 gitignore）

- 2026-08-21T01:56Z · P0 首轮循环 · **限 2 循环、墙钟 1h09m51s**，产出 7 个提交 / 1,499 行 / **5 条门禁转绿**（规范化器 3 + 快照 diff 2）。成本：15 个无头会话 / 387 条助手消息 / 输入 **29,900,540**（cache_read 占 2,865 万）/ 输出 376,397 / 按 Opus API 价 **≈\$31.5**
- 2026-08-21T01:56Z · P0 首轮循环 · **循环的表现是对的**：撞上「三处命令它划名单 vs 红线 1 禁止碰 `tests/gates/**`」的矛盾后，**没有自己找理由绕过**，而是逐条引原文写了 153 行交接文档、把 plan 置 `deferred`、往 STATE §3 追加 needs-human，然后停下。它还自己起子代理做了独立 plan 评审（12 条 blocking）
- 2026-08-21T01:56Z · P0 首轮循环 · **实测暴露我的三处缺陷**：① 名单放在红线内 → 已迁至 `tools/gates/expected-red.txt`；② `commands.test` 只有门禁判定器、**不含单测** → 循环实现了 `snapshot.capture/diff` 却看不见自己写的契约测试已过期（判定面漏一块，循环就不会自己发现）→ 已补 `pytest tests/unit`；③ 写回脚本把「引擎超限终止」和「红线停机」都当成退出码 2 处理，把 todo 误标 blocked → 已按 `.mission-halt.json` 是否存在区分
- 2026-08-21T01:56Z · P0 首轮循环 · 在途工作（snapshot.py 237 行）被 `--max-cycles 2` 截断在提交之前，人工代为落盘、内容未改一字。当前 `commands.test` → **exit 1**（契约测试过期），这正是下一轮的活

- 2026-08-21T01:59Z · W0.0 · **成本阈值按实测校准**：原 `maxTotalSteps: 120` 基于冒烟的 1.6M token/循环，而真实工作实测 **约 1,500 万/循环**，估偏近十倍 → 改为 **60**（≈7–8 循环 ≈\$110 当量）。教训记在这：**用「什么都不干」的空转数字去定「干活时」的阈值，必然定松**

- 2026-08-21T02:00Z · P0 第二轮 · **13 秒即死在 step 1**：`Failed to authenticate: OAuth session expired and could not be refreshed` → mission 退出码 1，零提交、工作区干净。写回闸判定正确（无 `.mission-halt.json` → 非红线停机 → 保持 open）
- 2026-08-21T02:00Z · P0 第二轮 · 复跑确认：`claude -p --settings ...` 直接回同一句认证错误 · Keychain 里 `Claude Code-credentials` 条目仍在但已过期 · **监督会话（桌面端）不受影响**——它自己持有并刷新 token，无头子进程用的是钥匙串那份
- 2026-08-21T02:00Z · P0 第二轮 · **暴露 7×24 的一个真空白**：订阅 OAuth 会过期，而**刷新只能由人完成**（登录属认证动作，AI 不得代做）。循环撞上这个只会一路 `failed`，且写回闸会把它当成普通失败保持 open、下一轮继续撞。**没有任何机制把「认证过期」与「代码有问题」区分开** —— 记为待补的停机条件

- 2026-08-21T02:04Z · 停机条件 · **新增第 5 条：认证失败即停机**。原四条（3 连败 / 碰门禁 / 成本超阈 / CI 两连红）都假设「失败是代码问题，重试有意义」，而认证过期重试一万次也没用且**只能由人修**。实现在 `tools/loopx-writeback.sh`：从运行输出匹配 `OAuth session expired` / `Failed to authenticate` / `401 unauthorized` / `authentication_error` → 落 `.mission-halt.json` 并标 todo blocked → 退 2 · 自测：认证特征命中；普通测试失败不误报


- 2026-08-21T10:20Z · P0 第三轮 · 工作项 2（快照 diff）· plan-3 Phase 1–3 执行完毕：Phase 1 的 `agenerp/snapshot.py` 早在 `e145e43` 已落盘，本轮补完 Phase 2 的真实语义覆盖（`tests/unit/test_snapshot_capture.py` 9 条非空夹具 + `test_snapshot_diff.py` 11 条增删改语义）与 Phase 3 的结构边界文档（`docs/architecture/module-boundaries.md` §11.5）· `python3 -m pytest tests/unit -q` → **exit 0**（40 passed）· `python3 tools/gates/check_expected_red.py` → **exit 0**（门禁 13 项：预期红 8，绿 5，跳过 0）· `ruff check agenerp tests/unit` → **exit 0** · sha `9ae88bf` · 下一项：独立 `CLOSURE_AUDIT`
- 2026-08-21T10:20Z · P0 第三轮 · 工作项 2 · **`e145e43` 自记的「已知遗留」已清**：`tests/unit/test_contract_surface.py` 把 `capture` / `diff` 由 `NOT_YET_IMPLEMENTED` 迁入 `IMPLEMENTED`。这正是 `2026-08-21T01:56Z` 那条记的「当前 `commands.test` → exit 1（契约测试过期），这正是下一轮的活」——**判定面补上单测后，循环这一轮自己看见并修掉了它**，验证了缺陷 ② 的修法有效 · `python3 -m pytest tests/unit/test_contract_surface.py -q` → **exit 0**（9 passed，其中 3 条仍断言 `schema_drift` / `export_customizations` / `apply_pack` 抛 `NotImplementedError`）
- 2026-08-21T10:20Z · P0 第三轮 · 工作项 2 · **§3 本轮不新增 `open` 行，理由如实记录**：plan-3 的 Phase 3 原规定「追加一行 needs-human，处置栏留 `open`」，前提是 `check_expected_red.py` 会因名单过期退 1。而人已在 `920ce0e`（带 `Gates-Change-Approved-By: lize`）划掉含本工作项两条 L1 在内的 5 行，该判据**在执行前就已退 0**——本 plan `## Human Handoff` 的验收条件已满足，再登记一条 `open` 就是凭空造一个人的待办。plan 末步据此保持 `Plan Status: active`（而非 `deferred`）交独立关闭审计，偏差与授权链已写进 plan 与 `docs/logs/2026/08-21.md`
- 2026-08-21T10:20Z · P0 第三轮 · 红线自查（区间 diff，非 `git diff HEAD`）· `git diff --name-only b8aadbf..HEAD -- tests/gates/ .github/workflows/ docs/masterplan/DECISIONS.md` → **输出为空**；`tests/gates/test_snapshot_diff_structured.py::test_field_addition_shows_up_as_structured_change` 仍红且红因仍是 `tests/gates/conftest.py:17` 的 `live_site` `NotImplementedError`（属工作项 4/6，未被本 plan 弄成别的错）
- 2026-08-21T03:32Z · P0 第二轮 · 认证恢复后重跑，**跑约 1 小时后被会话退出误杀**（输出末尾 `[killed]`，非停机、非失败）。产出 4 个提交 / 1,715 行：**自己修掉了上一轮留下的过期契约测试**（`commands.test` 由 exit 1 转 **exit 0**，40 条单测全过），roadmap **工作项 1、2 置 `done`**，并起草了工作项 3（零依赖启动）与 4（工具契约层）的 plan 置 `planned`
- 2026-08-21T03:32Z · P0 第二轮 · 成本：4 个无头会话 / 268 条助手消息 / 输入 **42,972,116** / 输出 368,181 / ≈**\$35.6**
- 2026-08-21T03:32Z · 基础设施 · **7×24 的第一个前提之前不成立**：循环挂在交互会话的后台任务下，会话一退子进程即被杀。新增 `tools/run-loop.sh`（`setsid` + `nohup` 双管齐下脱离进程组，带 pidfile / status / stop / log），停止时杀整个进程组以免引擎 spawn 的 claude 变孤儿

- 2026-08-21T03:52Z · 7×24 · 监督器与预算闸就位：`tools/loop-supervisor.sh`（五道闸：停机记录 / 日预算 / LoopX 配额 / 跑一趟 / 退 2 即停）· `tools/gates/pass_usage.py` 按趟计量 · `tools/gates/check_budget.py` 读台账判 24h 用量。**这补上了「单 mission 累计成本超阈值」此前只有步数代理、没有真计量器的空缺**
- 2026-08-21T03:52Z · 7×24 · 计量方式的一个坑：不能靠 `entrypoint` 之类标记区分循环会话与人的会话——**实测循环起的 `claude -p` 继承父进程的 `CLAUDE_CODE_ENTRYPOINT`，49 个会话全标成 `claude-desktop`**。改用文件集差分（跑前拍快照，跑完新出现的即本趟产生）
- 2026-08-21T03:52Z · 7×24 · **launchd 开机自启受阻于 macOS TCC**：代理起来即 `Operation not permitted`。探针确认 —— launchd 代理**读不了 `~/Documents` 下的仓库**，而家目录普通子目录与 `/tmp` 都能读。不是脚本问题，是仓库位置问题
- 2026-08-21T03:52Z · P0 · 停机前的进度：**工作项 1、2、3 均 `done`**（规范化器 / 快照与结构化 diff / 零依赖启动），工作项 4（工具契约层）plan 已起草置 `planned`。`commands.test` → exit 0。docker 实为 29.2.1 已装（先前报「没有」是我的检查命令引号写错）
- 2026-08-21T03:52Z · 用户指令 · **暂停等额度**：已 `tools/run-loop.sh stop`、`install-loop-agent.sh uninstall`，无残留进程，工作区已提交推送

- 2026-08-21T07:11Z · 迁库 · `~/Documents/claude/AgenERP` → **`/Users/lize/Claude/Projects/AgenERP`**（整目录 `mv`，保住 `.env`/`.loopx`/`.codex`/`_tmp` 等未跟踪文件）· 迁后自检：git 完好（remote 在、0 改动）、引擎 `--help` exit 0、`commands.test` exit 0、断链 exit 0、证据仓指针仍可达
- 2026-08-21T07:11Z · 迁库 · **TCC 确已解开**：launchd 探针在新路径下 cd／读仓库／跑 git／跑引擎**四项全可**（旧路径下四项全被 `Operation not permitted`）。这是迁库的唯一理由，已证实
- 2026-08-21T07:11Z · 迁库 · 两处需手工修正：① `.loopx/registry.json` 的 `repo` 仍指旧路径 → 已改；② STATE §1「下一项」原写「P0 工作项 4」不是 WBS 行 ID，一致性检查退 1 → 改填 **`P0.2`**。顺带把 WBS 的 P0 行与循环实际进度对齐（P0.1/P0.3/P0.4 置 done，P0.2 in progress）
- 2026-08-21T07:11Z · 7×24 · **launchd 代理已上线**：`com.agenerp.loop`，`RunAtLoad` + `KeepAlive.Crashed`（只在真崩溃时重拉——撞停机条件是正常退出，重拉等于绕过停机闸）。监督器 pid 35188、PPID=1，已过三道闸开跑
- 2026-08-21T07:11Z · 7×24 · 堵掉一个并发隐患：launchd 起的监督器原本不写 pidfile，`run-loop.sh supervise` 会再起第二个 → 改为监督器自己认领 `_tmp/supervisor.pid`，两个入口共用同一份真相。自测：再叫一次 supervise → 被拒（「监督器已在运行」）

- 2026-08-21T11:03Z · 跨模型对照 · **首版结论更正**：codex/sol 臂并未违反协议。它按上游 plan-review 的 escape hatch 正确处理受阻 plan —— 写 `> Review Hold:`、连做 **15 轮**独立评审、每轮实时核对仓库事实（`STATE.md` harness 项仍 `[open]`、`tests/support/live_site.py` 不存在），判定外部阻塞无法在评审内合法解除，保持 draft。**我第一版直接把「停在 draft」读成「没按协议提升」，没去看有没有 Review Hold 行 —— 看到反常先查协议允不允许，别先假定对方错**
- 2026-08-21T11:03Z · 跨模型对照 · codex 臂**指出两个真缺陷，都已修**：① 引擎终局判定只问 activePlans/openAudits，被 Review Hold 扣住的 draft 不在其中 → 「活被扣住」被判成「没活干」（**补丁 P6**：`_heldDraftPlans()`，有受阻 plan 时拒判 completed）；② 流程是 EXECUTE → CLOSURE → BUILD → GATE，**plan 先写成 completed 门禁才开跑**，GATE 失败退回 EXECUTE 时磁盘那份已声称完成 —— 「AI 自报通过」的文件形态（**补丁 P7**：判失败时降回 active 并留时间戳原因）
- 2026-08-21T11:03Z · 跨模型对照 · P6/P7 双向实测通过；引擎回归与主干失败集合逐条一致。中途 `Monitor` 那条一度多挂，单独跑 84 全过、全量复跑不复现 → **全量并发下的抖动，不是补丁所致**（差点误记成自己打坏的）
- 2026-08-21T11:03Z · 主干 · 循环在 `module-boundaries.md` 写了行号引用 `...pre-build-validation.md:143`，触发引擎自带的 `mdc-1 R3`（架构文档禁行号引用，行号会烂）→ 改为按节名引用，`check-doc-references` exit 0

- 2026-08-21T11:13Z · 门禁 · **三个 fixture 已由人写完**（`compose_stack` / `live_site` / `pack_repo`，`tests/gates/conftest.py`）。三条规矩写在文件最前：绝不伪装成功（环境不具备就 `fail`，不许 `skip`）、不碰不属于自己的东西（栈本来就跑着就不拆，探针字段 teardown 删干净）、默认不跑（需 `AGENERP_LIVE=1`，否则快门禁每轮拉一次 ERPNext 循环没法用）
- 2026-08-21T11:13Z · 门禁 · `pack_repo` 刻意**不复用** `agenerp` 的读写函数：fixture 是判据的一部分，与被测实现共用解析代码的话，实现里的口径错误会在两边同时发生、互相抵消而测不出来
- 2026-08-21T11:13Z · 门禁 · 快门禁不变（6 绿 / 7 预期红，判定器一致），但**红的理由变了**：从「实现不存在」变成「本轮没打算跑 L2」。L2 真跑命令：`AGENERP_LIVE=1 python3 -m pytest tests/gates -m live -q`
- 2026-08-21T11:13Z · 红线 · **红线 1 的三层拆分暂不做**（断言体=人 / fixture=接缝 / 新增门禁=加严）。理由是它自带前置：在工作项 8（CI 真跑 L2）落地之前，**没有任何东西能戳穿一个假 fixture**。在能抓住滥用的机制存在之前放宽红线等于白放。绑在 item 8，届时再议
- 2026-08-21T11:13Z · 梳理 · `feat/codex-driver` 与 `feat/planstate-guard` 已并入 main 并删除（worktree 一并清）。`ab/codex-sol` **不并主干**——它带两个 `Review Hold` 的 draft plan，而刚做的 P6 会让带 hold 的 draft 阻止 mission 判完成，并进去等于立刻卡死主循环；已推 `origin/ab/codex-sol` 留作实验记录

- 2026-08-21T11:20Z · 门禁 · 新增 `test_seed_dataset_absurdity.py` 六条，**全绿故不进预期红名单**（名单只登记预期红的）。判定器：13 → **19 项，12 绿 / 7 预期红**，一致
- 2026-08-21T11:20Z · L2 · fixture 修 URL 编码后复跑：`test_stack_boots_and_all_services_healthy` **PASS**（栈真起、全服务 healthy、用完自拆）；其余红的**性质变了** —— 从「fixture 自己坏了」变成「实现确实不存在」。⚠️ 该条**仍留在预期红名单**：它只在 `AGENERP_LIVE=1` 且端口空闲时过，判定器走的是快门禁路径，那条路上它仍红。**名单必须反映判定器实际看到的，不是我知道的**

- 2026-08-21T14:21Z · 记账更正 · 我上一轮向人报「三条 needs-human 全部关闭」是**错的**：当时只把工作项 7 那条标了 `resolved`，fixture 那两条只补了证据行、状态没改。本轮核对队列才发现。**「我做完了那件事」不等于「账上记了」** —— 状态字段是给下一个接手的人看的，不是给我自己回忆用的

---

## §3 needs-human 队列

> 格式：`[状态] 日期 · 触发条件 · WBS行ID · 最后一条失败命令原文 + 退出码 · sha · 处置`
> 状态只有 `open` / `resolved`。**resolved 的行保留不删。**

- [resolved] 2026-08-21T03:52Z · 触发：launchd 开机自启被 macOS TCC 拦（仓库在 `~/Documents` 下）· 7×24 基础设施 · 探针实测：launchd 代理读 `~/Documents/claude/AgenERP` → `Operation not permitted`；读家目录普通子目录与 `/tmp` → 正常 · sha `dab4ca5` · **两条出路，都需人决**：① 把仓库迁到 `~/Documents` 之外（如 `~/agenerp`），一条 `git clone` 即可，之后 launchd 直接可用；② 在系统设置里给 `/bin/bash` 完全磁盘访问权限（授权面很宽，不推荐）。**在此之前 7×24 只能靠 `tools/run-loop.sh start` 手动起**——它能扛住终端关闭，但扛不住重启 · **处置（2026-08-21T07:11Z）**：人选定出路 ① —— 仓库迁至 `/Users/lize/Claude/Projects/AgenERP`。launchd 探针复验四项全可，代理已装载运行。未采用「给 /bin/bash 完全磁盘访问」那条，授权面太宽

- [resolved] 2026-08-21T02:00Z · 触发：Claude Code 订阅 OAuth 过期，无头执行器全部起不来 · P0 第二轮 · `claude -p ...` → `Failed to authenticate: OAuth session expired and could not be refreshed`；mission 退 1，13 秒死在 step 1 · sha `ec759ba` · **处置只能由人做**：在交互式终端跑 `claude login` 重新登录（AI 不得代做认证动作）。恢复后验收：`claude -p "ping"` 返回非空 → 重跑 `tools/loopx-writeback.sh p0-foundation todo_175c903f50e3` · **处置（2026-08-21T02:04Z）**：人已 `claude login` 重新登录；`claude -p` 复验返回「在线」。并补上第五条停机条件：写回闸从运行输出识别认证失败特征 → 落 `.mission-halt.json`（`condition: auth-expired`）→ 拒绝后续重启。自测：认证特征命中、普通测试失败不误报

- [resolved] 2026-08-20 · 触发：W0.7 需要建 GitHub 远程仓才能验证「push 触发 CI」 · W0.7 · 处置：人选定**先建私有仓**，`lize-agent-engineering/AgenERP` 已建并 push，CI 已实跑。公开时机留待 P2 有演示价值时由人再定

- [resolved] 2026-08-20 · 触发：同一 plan 连续 3 轮 GATE_VERIFY fail · P0.4 · 最后失败命令 `pytest tests/gates/test_normalizer_idempotent.py -q` → 记录为 exit 1，**复跑得 exit 4（file not found）**；`git cat-file -t deadbee` → exit 128 · sha `deadbee`（不存在） · 处置：**不可复现 → 关单**。这是 T4 演习的模拟桩，由演习会话按 01 §2 五步正确识破并处置


- [resolved] 2026-08-21 · 触发：工作项 1（定制包规范化器）实现到位，三条门禁转绿，`check_expected_red.py` 报名单过期；划掉 `tests/gates/EXPECTED_RED.txt` 三行属红线 1，需带 `Gates-Change-Approved-By:` trailer 的人工提交 · P0.4 · 最后一条命令 `python3 tools/gates/check_expected_red.py` → **exit 1**（「门禁 13 项：预期红 10，绿 3，跳过 0 / ❌ 名单内的门禁却绿了」，列出 `test_normalize_is_stable_across_reexport` / `test_normalize_orders_deterministically` / `test_normalize_strips_volatile_fields`） · sha `37ffc5d` · 处置：open —— 等人提交划名单，验收 `python3 tools/gates/check_expected_red.py` → exit 0；plan 已自置 `deferred`，详见 `docs/plans/p0-foundation/2026-08-20-2341-2-customization-pack-normalizer.md` 的 `## Human Handoff` · **处置（人，2026-08-21）**：循环指出的矛盾属实且是我的设计缺陷——build-verify prompt、判定器输出、gate-verify 回灌三处都命令它划名单，而红线 1 禁止碰 `tests/gates/**`。裁定：**测试代码是裁判（红线保护），预期红名单只是账本** → 名单迁至 `tools/gates/expected-red.txt`（红线外），loop 可在同一提交里划掉已转绿行，变长仍需人工批准。已划掉 5 行，`check_expected_red.py` → exit 0

- [resolved] 2026-08-21 · 触发：工作项 4 的 **B 半**（接活站点）被红线 1 挡住——它要的三个 fixture 全部定义在 `tests/gates/**` 内，loop 一个字节都不许改 · **P0.2**（挡的是 B 半与工作项 5/6/8，**不挡本 plan 的 A 半交付，本行不阻塞 plan `2026-08-21-1022-2` 关闭**） · 最后一条命令 `python3 -m pytest tests/gates/test_zero_dep_boot.py -q --tb=line` → **exit 1**，逐字红在 `NotImplementedError: compose_stack 尚未实现` · sha `091a150` · **需要人做一个红线决定，四个处置项 loop 不替人选**：(a) 人带 `Gates-Change-Approved-By:` trailer 把 `live_site` / `compose_stack` / `pack_repo` 三个 fixture 的 `raise` 换成真实现；(b) 比照 `expected-red.txt` 的先例，把 harness 接缝也迁出 `tests/gates/`（「测试代码是裁判，harness 是接线」）；(c) 维持现状——**代价**：工作项 5/6/8 的判据将永远不可达；(d) **明确禁止或授权 hook 级绕道**——loop 的建议是**明确禁止并写进红线说明**，因为它能让门禁绿而实现不到位，但这是人的决定。 · **处置（2026-08-21T14:21Z，人写）**：三个 fixture 已实现（`compose_stack` / `live_site` / `pack_repo`，见 `tests/gates/conftest.py`），本条与下面两条「补充事实行」同一根因，一并关闭。实据：`AGENERP_LIVE=1 pytest tests/gates -m live` 由 **2 过 → 5 过 3 红**，其中 `test_stack_boots_and_all_services_healthy`（栈真起、全服务 healthy、用完自拆）与 `test_field_addition_shows_up_as_structured_change`（真站点建字段 → `SiteSnapshotSource.read` 读到 → diff 精确指出）双双转绿。剩余 3 条红全是真实现缺口（`execute_plan` 未实现、首页无「AI 能力未配置」），不再是红线阻塞
  · **事实**（供决策，已核对）：`live_site` 定义在 `tests/gates/conftest.py:15`（`:17` 是 `raise`）；同文件 `:5` 写着「实现到位时把 raise 换成真东西即可」，`:7` 紧接着写「⚠️ 本文件同样在 `tests/gates/**` 红线内：loop 不得修改」——**那句话是写给人的，不是给 loop 的指令，两句并不冲突**；`tests/gates/README.md` 也明写「这个目录里的文件，loop 一律不得修改」。**这不是第二个「冲突 1」**：冲突 1 已由人在 `920ce0e` 裁定关闭，`tests/gates/EXPECTED_RED.txt` 已不存在。
  · **实测**：同名 fixture 覆盖**不可能**（就近者胜，`NotImplementedError: inner`）；但 `pytest_fixture_setup` hook 级绕道**可行**（scratchpad 复刻：根级 conftest 即可让门禁 `1 passed`，不碰 `tests/gates/**` 一个字节）。plan 已把它写进 `## Non-Goals` 禁止本 plan 使用，**但仓里没有任何规则禁止下一个会话这么做**——这正是 (d) 要人拍板的原因。
  · **授权链（往 STATE 写这件事本身有争议，如实引出）**：`AGENTS.md` 红线 5 明文「`STATE.md` 只允许**追加**证据行」，执行器人格 `tools/mission-driver/agents/build.claude.md:16` 逐字指示「拿不准就停下来写进 `STATE.md` 的 needs-human 队列，等人」；二者按 `AGENTS.md` 开头声明的次序高于 `01-EXECUTION-MODEL.md` §1 表里「角色 B 不得手写 STATE」。⚠️ **这处矛盾尚未被任何交接文档登记**（`needs-human-expected-red-handoff.md` 的四组冲突都不是它）——本行按更高优先级那条执行，把矛盾原文摆出来，**不擅自消解，也不为它另开一行**。

- [resolved] 2026-08-21 · 触发：工作项 7（种子数据）**没有绑定的门禁测试**——roadmap 对照表第 7 行逐字写着「尚无门禁——开工前先补一条，否则这一项没有判据」，而补 `tests/gates/**` 下的文件在红线 1 内，loop 一个字节都不许写 · **P0.6** · 最后一条命令 `python3 -m agenerp.seed --seed 42 --verify` → **exit 0**（本 plan 交付的 A 半自验命令，做过变异验证：故意破坏一条断言即转红并指名道姓）；⚠️ **该命令不在 `missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 子进程复跑不到它**——这条绿是 loop 自己给自己判的分，代偿控制是变异验证 + 独立关闭审计复跑 · sha `d45698a`（开工基线） · **三个处置项 loop 不替人选**：(a) 采纳 `docs/backlog/gate-proposal-seed-dataset.md`，带 `Gates-Change-Approved-By:` trailer 提交那条 L2 红门禁（三条断言：荒谬在站点上成立 / 四项账面指标全绿 / 两笔逾期可由字段查到），同一提交里把三行加进 `tools/gates/expected-red.txt`（名单变长只有人能批）；(b) 裁定主计划 WBS P0.6 的验收命令即本项判据，把 roadmap 对照表第 7 行改成指向 `python3 -m agenerp.seed --seed 42 --verify`，并把它加进 `commands.test`（`missions/**` 是角色 B 禁区）；(c) 维持现状——**代价**：工作项 7 永远停在 `planned`，B 半（装载进活站点 + 站点侧断言）永远没有判据。 · **处置（2026-08-21T11:20Z，人写）**：`tests/gates/test_seed_dataset_absurdity.py` 六条实跑**全绿**。性质说明：实现先于门禁（循环被红线挡着写不了门禁），属**特征化门禁**不是 TDD —— 价值在把判据锁死，尤其此前无人管的三条：不含图片、无第三方权利、积压对规则可见（成品库存量 > 未交付订单量，否则规则不报警、测例作废）。**数字由判据自带，不 import `agenerp.seed.checks`**：import 实现的常量等于让它自己判自己的卷
  · **事实**（供决策，已核对）：本 plan 只交付 A 半（纯逻辑生成 + 自验），**A/B 切分的责任在本 plan 自己**，理由是 B 半要 `live_site` fixture，它定义在 `tests/gates/conftest.py`（红线 1），与本队列里那行工作项 4 的 `[open]` 是同一个前置。工作项 7 收尾时置 `planned` 而非 `done`，不存在「把没做完的活报成 done」。`tools/gates/expected-red.txt` 一行未动，本次没有任何门禁由红转绿。
  · **对账副产品**（不需人决，记在此处只为留痕）：在冻结的证据仓里查到了含单价的原始记录，¥6,450 与 1,010 米**对得上**，机制是两档批次单价（自制 ¥5.00/米、外协 ¥6.40/米）按 FIFO 分层，不是移动加权均价（均价口径应得 ¥5,757）。本仓此前登记的「单价对不上」那处数值漂移**不存在，已关闭**；对账过程落在 `docs/architecture/module-boundaries.md` §12.1。**证据仓全程只读，未写入一个字节**（红线 6）。
  · **授权链（与本队列里工作项 4 那行同一处矛盾，照实引出、不擅自消解）**：`01-EXECUTION-MODEL.md` §1 的表写角色 B「不得手写 STATE」，而执行器人格 `tools/mission-driver/agents/build.claude.md` 逐字指示「拿不准就停下来写进 `STATE.md` 的 needs-human 队列，等人」；`AGENTS.md` 红线 5 允许**追加**证据行。本行按更高优先级那条执行，只追加、不改写任何已有行。

- [resolved] 2026-08-21 · **补充事实行，不另开条目**——本行只给本队列里那条工作项 4 / `compose_stack` 的 `[open]` 补新事实，处置项仍是那行的 (a)/(b)/(c)/(d)，loop 不替人选 · **P0.7** · 触发：plan `2026-08-21-1634-2` 已把「应用侧服务 healthy」从**不可判**变成**可判**，但门禁本身仍被 `compose_stack` 挡着，两件事不可混为一谈 · 最后一条命令 `python3 -m pytest tests/gates/test_zero_dep_boot.py -q` → **exit 1**（`1 passed, 2 errors`），红因与开工前**逐字未变**：`NotImplementedError: compose_stack 尚未实现 —— 见 docs/backlog/implementation-roadmap.md 的 P0 交付表（P0 · 零依赖启动 CI）` · sha `09f88c8`（开工基线） · **新事实一**：`backend` / `websocket` / `frontend` 三个服务已落真实 healthcheck，`AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300` 冷起 → **exit 0（68 秒）**；变异验证（把 `frontend` 探针指向必然失败的地址）→ **exit 1（87 秒）**并逐字报 `container agenerp-frontend-1 is unhealthy`——判据有牙齿，不是空转。改动前同一条命令是 **exit 0 但只用 4 秒**，那 4 秒里站点还没建出来，是一条空判据。`tools/gates/expected-red.txt` **一行未动**，本次没有任何门禁由红转绿。 · **处置（2026-08-21T14:21Z，人写）**：三个 fixture 已实现（`compose_stack` / `live_site` / `pack_repo`，见 `tests/gates/conftest.py`），本条与下面两条「补充事实行」同一根因，一并关闭。实据：`AGENERP_LIVE=1 pytest tests/gates -m live` 由 **2 过 → 5 过 3 红**，其中 `test_stack_boots_and_all_services_healthy`（栈真起、全服务 healthy、用完自拆）与 `test_field_addition_shows_up_as_structured_change`（真站点建字段 → `SiteSnapshotSource.read` 读到 → diff 精确指出）双双转绿。剩余 3 条红全是真实现缺口（`execute_plan` 未实现、首页无「AI 能力未配置」），不再是红线阻塞
  · **新事实二（采纳门禁时必须知情，这是本行存在的主要理由）**：本仓的「全部服务 healthy」是一个**收窄过的集合**——`db` / `redis-cache` / `redis-queue` / `backend` / `websocket` / `frontend` 六个在集合内；**`queue-short` / `queue-long` / `scheduler` 三个 worker 的健康在本仓查实不可判**，只判 running；`configurator` / `create-site` 两个一次性容器只判 `Exited (0)`。判定口径与逐条弃选理由写在 `docs/architecture/system-baseline.md` §14.2。弃选证据：`bench doctor` 与 `bench --site frontend scheduler status` **都退 0**却同时输出 `Scheduler disabled / inactive`（永远绿的假判据）；rq 心跳分辨率实测 **405 秒**（`DEFAULT_WORKER_TTL = 420`）且 `scheduler` 根本不是 rq worker；`pgrep` 类进程存活探针属本仓明令禁止的假判据。**人若采纳 `test_stack_boots_and_all_services_healthy`，它断言的是 6 个服务不是 11 个**——这一点不写明，将来会有人以为「全部」是字面意义的全部。
  · **未做、也不由本 plan 做**（照实登记，不降级成隐性 follow-up）：① 首页「AI 能力未配置」文案（门禁 `test_homepage_states_ai_disabled_instead_of_crashing`），是应用层交付；② 给 CI 加跑 docker 的 L2 job（`.github/workflows/**`，红线 2 的关注面，且 `compose_stack` 未解锁前加了也只能跑到一个抛 `NotImplementedError` 的 fixture 上）。两项同属工作项 8 的第二个 plan。
  · **verification scope limited**：上述起栈实证**只在本机 compose v5.0.2 上做过**，CI runner 是 2.38.2，两者的版本差是 plan `2026-08-21-1022-1` 已登记的 watch-only residual。**不得报为「CI 上也验证过」。**

- [resolved] 2026-08-21 · **补充事实行，不另开条目**——本行只给本队列里那条工作项 4 / `compose_stack` 的 `[open]` 补新事实，处置项仍是那行的 (a)/(b)/(c)/(d)，loop 不替人选；名单口径人已在 §2 的 2026-08-21T11:20Z 裁定过（「名单必须反映判定器实际看到的，不是我知道的」），本行不请求划名单 · **P0.2** · 触发：plan `2026-08-21-1922-1` 已把工作项 4 的 **B 半**（站点只读传输 + `SiteSnapshotSource.read`）落地，`test_field_addition_shows_up_as_structured_change` 在活站点上实测转绿，但默认判定环境下它仍红、名单一行未动 · 最后一条命令 `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 tools/gates/check_expected_red.py` → **exit 1**，输出原文：「门禁 19 项：预期红 5，绿 14，跳过 0 / ❌ 名单内的门禁却绿了 —— 实现已到位，请在同一个提交里把它从 tools/gates/expected-red.txt 划掉： tests/gates/test_snapshot_diff_structured.py::test_field_addition_shows_up_as_structured_change / tests/gates/test_zero_dep_boot.py::test_stack_boots_and_all_services_healthy」 · sha `826cdf8`（开工基线） · **处置（2026-08-21T14:21Z，人写）**：三个 fixture 已实现（`compose_stack` / `live_site` / `pack_repo`，见 `tests/gates/conftest.py`），本条与下面两条「补充事实行」同一根因，一并关闭。实据：`AGENERP_LIVE=1 pytest tests/gates -m live` 由 **2 过 → 5 过 3 红**，其中 `test_stack_boots_and_all_services_healthy`（栈真起、全服务 healthy、用完自拆）与 `test_field_addition_shows_up_as_structured_change`（真站点建字段 → `SiteSnapshotSource.read` 读到 → diff 精确指出）双双转绿。剩余 3 条红全是真实现缺口（`execute_plan` 未实现、首页无「AI 能力未配置」），不再是红线阻塞
  · **新事实一（本行存在的主要理由）：harness 官方文档化的 L2 跑法与这条门禁的 env 需求对不上。** `tests/gates/conftest.py` 自己写的跑法是 `AGENERP_LIVE=1 python3 -m pytest tests/gates -m live -q`，而该文件**全文不设 `AGENERP_SITE`**（三个 fixture 一个都不设）。那条门禁调的是无参 `capture(scope="doctypes")`，来源由 `resolve_source` 按「显式来源 > `AGENERP_SITE` > 离线来源」解析 → **只带 `AGENERP_LIVE=1` 跑，它走离线来源、两次空快照、`d.is_empty()` 断言失败，仍然红**。它转绿需要 `AGENERP_LIVE=1` **和** `AGENERP_SITE=frontend` 两个条件，后者只能由调用命令给。**三条可选出路，loop 不替人选**：(a) 人在 conftest 里给 live 跑法补 `AGENERP_SITE`（红线 1，只有人能做）；(b) 把「L2 跑法」的口径改成 plan 文档化的完整命令（已落进 `docs/context/project-context.md` 的验证命令表），将来 CI 的 L2 job 照它写；(c) 让 `resolve_source` 在站点可达时自动选站点来源——**loop 的建议是不要**，自动探测会让「离线也能绿」和「站点没起也能绿」两种假绿同时变得可能。
  · **新事实二：实测只出现了「名单内的门禁却绿了」这一种形态，两条。** 一条是本 plan 让它转绿的 `test_field_addition_shows_up_as_structured_change`；另一条 `test_stack_boots_and_all_services_healthy` 正是人在 §2 11:20Z 已裁定过的那条。**plan 起草时预判的第二种形态（「名单外的门禁红了」）在栈已起的前提下没有出现**——两条 L1 快照门禁在配了 `AGENERP_SITE` 的活站点上照样绿。
  · **新事实三（采纳 (a)/(b) 任一条时必须知情的执行顺序陷阱，实测两次可复现）**：两条 L1 快照门禁 `test_two_snapshots_of_unchanged_site_diff_empty` / `test_diff_is_structured_not_text` **不取任何 fixture**，所以配了 `AGENERP_SITE` 之后，它们在 `compose_stack` 把栈拉起来**之前**就已经跑完了。栈没预先起时实测 `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q` → **exit 1（`FF.`，两次复跑逐字一致）**，红因逐字 `agenerp.site.SiteError: POST http://127.0.0.1:18080/api/method/login 连不上：<urlopen error [Errno 61] Connection refused>`——**注意第三条（live 那条）在同一次运行里是绿的**，红的恰恰是两条 L1。栈**预先起好**再跑同一条命令 → **exit 0（3 passed）**。这是接线问题不是实现问题，但它会让采纳方案 (a) 的人在 CI 上得到一条难读的红；解法在 harness 侧（红线 1，只有人能做），loop 不动。
  · **未做、也不由本 plan 做**：`tools/gates/expected-red.txt` **一行未动**（沿用人在 §2 11:20Z 的既有裁定：live 环境下转绿不构成划名单的理由，名单必须反映判定器实际看到的）；工作项 4 保持 `planned` 不置 `done`——roadmap 给它绑的是「提供 `live_site` fixture，解锁 L2 各项」，**它压根没有一条属于自己的门禁测试**，`done` 的字面定义对它不可满足，与工作项 7 已 `[resolved]` 的情形同一性质。
  · **verification scope limited**：live 实证只在本机做过（compose v5.0.2、端口 18080、**卷是热的**——站点由此前的运行留下，`up -d --wait` 用了 **20.5 秒**而不是冷起的 68 秒）。CI runner 是 compose 2.38.2，两者版本差是 plan `2026-08-21-1022-1` 已登记的 watch-only residual。**不得报为「CI 上也验证过」。**
  · **授权链（与本队列里工作项 4、P0.7 两行同一处矛盾，照实引出、不擅自消解）**：`01-EXECUTION-MODEL.md` §1 的表写角色 B「不得手写 STATE」，而执行器人格 `tools/mission-driver/agents/build.claude.md` 逐字指示「拿不准就停下来写进 `STATE.md` 的 needs-human 队列，等人」；`AGENTS.md` 红线 5 允许**追加**证据行。本行按更高优先级那条执行，只追加、不改写任何已有行，也不为这处矛盾另开一行。
