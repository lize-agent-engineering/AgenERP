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
| **下一个未阻塞工作项** | **W0.5 · 写 AGENTS.md（含红线）**（此字段**只填一个 ID**，不写「但实际前置是…」这类歧义——T1 实测：会让接手会话先做一次推理才敢动手） |
| 该项验收命令 | `grep -q 'tests/gates' AGENTS.md` |
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

---

## §3 needs-human 队列

> 格式：`[状态] 日期 · 触发条件 · WBS行ID · 最后一条失败命令原文 + 退出码 · sha · 处置`
> 状态只有 `open` / `resolved`。**resolved 的行保留不删。**

- [resolved] 2026-08-20 · 触发：同一 plan 连续 3 轮 GATE_VERIFY fail · P0.4 · 最后失败命令 `pytest tests/gates/test_normalizer_idempotent.py -q` → 记录为 exit 1，**复跑得 exit 4（file not found）**；`git cat-file -t deadbee` → exit 128 · sha `deadbee`（不存在） · 处置：**不可复现 → 关单**。这是 T4 演习的模拟桩，由演习会话按 01 §2 五步正确识破并处置


