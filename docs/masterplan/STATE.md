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
| **下一个未阻塞工作项** | **W0.8b · 新增 `--driver claude`**（此字段**只填一个 ID**，不写「但实际前置是…」这类歧义——T1 实测：会让接手会话先做一次推理才敢动手） |
| 该项验收命令 | `--driver claude` 能跑通一次最小 prompt 往返，且**不泄漏本仓 CLAUDE.md / hooks / skills**（对策见 `REF:SPIKE02-MODELS`） |
| 阻塞 | 无。**T1–T4 四条全过**（2026-08-20） |
| 成本 | 未开始计量（阈值待 `W0.0` 定出） |
| CI | 未配置（`W0.7`） |
| 证据仓 | `XM_SHA=1c622c8119755b36992c54ba98fbf6840cd22ed4` @ `validation/pre-build`（见 `evidence-repo.env`） |
| LoopX | 已装 0.5.0，`doctor ok:True`；**尚未接管状态**（`W0.12`，2 小时上限） |

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

---

## §3 needs-human 队列

> 格式：`[状态] 日期 · 触发条件 · WBS行ID · 最后一条失败命令原文 + 退出码 · sha · 处置`
> 状态只有 `open` / `resolved`。**resolved 的行保留不删。**

- [resolved] 2026-08-20 · 触发：W0.7 需要建 GitHub 远程仓才能验证「push 触发 CI」 · W0.7 · 处置：人选定**先建私有仓**，`lize-agent-engineering/AgenERP` 已建并 push，CI 已实跑。公开时机留待 P2 有演示价值时由人再定

- [resolved] 2026-08-20 · 触发：同一 plan 连续 3 轮 GATE_VERIFY fail · P0.4 · 最后失败命令 `pytest tests/gates/test_normalizer_idempotent.py -q` → 记录为 exit 1，**复跑得 exit 4（file not found）**；`git cat-file -t deadbee` → exit 128 · sha `deadbee`（不存在） · 处置：**不可复现 → 关单**。这是 T4 演习的模拟桩，由演习会话按 01 §2 五步正确识破并处置


