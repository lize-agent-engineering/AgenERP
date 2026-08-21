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
| **下一个未阻塞工作项** | **P0.2 · 修过期的契约测试并关闭工作项 1/2**（交给下一轮循环）（此字段**只填一个 ID**，不写「但实际前置是…」这类歧义——T1 实测：会让接手会话先做一次推理才敢动手） |
| 该项验收命令 | `--driver claude` 能跑通一次最小 prompt 往返，且**不泄漏本仓 CLAUDE.md / hooks / skills**（对策见 `REF:SPIKE02-MODELS`） |
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

---

## §3 needs-human 队列

> 格式：`[状态] 日期 · 触发条件 · WBS行ID · 最后一条失败命令原文 + 退出码 · sha · 处置`
> 状态只有 `open` / `resolved`。**resolved 的行保留不删。**

- [open] 2026-08-21T02:00Z · 触发：Claude Code 订阅 OAuth 过期，无头执行器全部起不来 · P0 第二轮 · `claude -p ...` → `Failed to authenticate: OAuth session expired and could not be refreshed`；mission 退 1，13 秒死在 step 1 · sha `ec759ba` · **处置只能由人做**：在交互式终端跑 `claude login` 重新登录（AI 不得代做认证动作）。恢复后验收：`claude -p "ping"` 返回非空 → 重跑 `tools/loopx-writeback.sh p0-foundation todo_175c903f50e3`

- [resolved] 2026-08-20 · 触发：W0.7 需要建 GitHub 远程仓才能验证「push 触发 CI」 · W0.7 · 处置：人选定**先建私有仓**，`lize-agent-engineering/AgenERP` 已建并 push，CI 已实跑。公开时机留待 P2 有演示价值时由人再定

- [resolved] 2026-08-20 · 触发：同一 plan 连续 3 轮 GATE_VERIFY fail · P0.4 · 最后失败命令 `pytest tests/gates/test_normalizer_idempotent.py -q` → 记录为 exit 1，**复跑得 exit 4（file not found）**；`git cat-file -t deadbee` → exit 128 · sha `deadbee`（不存在） · 处置：**不可复现 → 关单**。这是 T4 演习的模拟桩，由演习会话按 01 §2 五步正确识破并处置


- [resolved] 2026-08-21 · 触发：工作项 1（定制包规范化器）实现到位，三条门禁转绿，`check_expected_red.py` 报名单过期；划掉 `tests/gates/EXPECTED_RED.txt` 三行属红线 1，需带 `Gates-Change-Approved-By:` trailer 的人工提交 · P0.4 · 最后一条命令 `python3 tools/gates/check_expected_red.py` → **exit 1**（「门禁 13 项：预期红 10，绿 3，跳过 0 / ❌ 名单内的门禁却绿了」，列出 `test_normalize_is_stable_across_reexport` / `test_normalize_orders_deterministically` / `test_normalize_strips_volatile_fields`） · sha `37ffc5d` · 处置：open —— 等人提交划名单，验收 `python3 tools/gates/check_expected_red.py` → exit 0；plan 已自置 `deferred`，详见 `docs/plans/p0-foundation/2026-08-20-2341-2-customization-pack-normalizer.md` 的 `## Human Handoff` · **处置（人，2026-08-21）**：循环指出的矛盾属实且是我的设计缺陷——build-verify prompt、判定器输出、gate-verify 回灌三处都命令它划名单，而红线 1 禁止碰 `tests/gates/**`。裁定：**测试代码是裁判（红线保护），预期红名单只是账本** → 名单迁至 `tools/gates/expected-red.txt`（红线外），loop 可在同一提交里划掉已转绿行，变长仍需人工批准。已划掉 5 行，`check_expected_red.py` → exit 0
