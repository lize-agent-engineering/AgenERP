Verify that the build passes for mission '{{missionName}}'.

改完代码后必须跑一遍验证命令。用 mission 配置里的命令，不要自己编。

## 这个项目的语境（读之前先知道）

Python / Frappe（ERPNext）项目。三件事决定了怎么验证：

1. **门禁测试按 TDD 故意全红。** `{{testCmd}}` 不是 `pytest`，而是 `tools/gates/check_expected_red.py`：
   它比对「实际结果 vs `tools/gates/expected-red.txt`」。名单内红 = 正常；名单内**绿** = 名单过期，
   实现已到位，你必须**在同一个提交里**把它从名单划掉；名单外红 = 真的坏了；出现 skip = 有人放松裁判。
2. **你的 pass 不是最终判定。** 这一步之后还有 `GATE_VERIFY`，由引擎自己 spawn 子进程复跑同样的命令，
   以退出码裁定。你若在这里谎报 pass，下一步立刻打脸，白白多烧一轮。**如实报 fail 比虚报 pass 便宜。**
3. **`tests/gates/**` 与 `.github/workflows/**` 是红线。** 一个字都不许改（包括加 skip/xfail、放松断言）。
   `git diff` 一旦触及，GATE_VERIFY 直接判失败并停机。测试挡路时，**改实现，不许改判据**。

## 步骤

1. 在项目根目录依次执行 mission 配置里非空的命令：
   - `{{typecheckCmd}}`
   - `{{buildCmd}}`
   - `{{lintCmd}}`
   - `{{testCmd}}`
   空的跳过。目前只有 `{{testCmd}}` 是配了的——ruff / mypy / docker 本身是 P0 的交付物，装上后才会出现在这里。
2. 有命令失败时：
   a. **先原样复跑一次**确认失败真实存在（Frappe 的 fixture 与 DB 状态偶发抖动）；复跑不出来就记「不可复现」，**不要猜根因**。
   b. 定位真实原因：Python 报错读**最后一层** traceback，不是第一层；断言失败读实际值与期望值的差。
   c. 改**实现**，再跑一遍确认转绿。
   d. 若结论是「判据本身错了」——停下来，别改测试。在结果里说明，交给人处置。
3. 全绿后进入下面的提交策略。

## 提交策略

动手前先看 `git status` 与 `git log --oneline -5`：

- **工作区干净** → 跳过提交，直接输出结果标记。
- **有未提交改动** → 按下面拆分提交（本项目 EXECUTE 不做逐项提交，一律在这里成批提交）：

  a. 从 `{{PLAN_FILE}}` 文件名前 15 个字符取 `YYYY-MM-DD-HHmm`；scope 用 `{{missionName}}`。
  b. 按 `AGENTS.md` 的提交风格拆成两个提交（**代码与其测试永不分开**）：

     **代码提交**
     ```
     feat(<scope>): plan-{YYYY-MM-DD-HHmm} <plan 标题>

     - 交付项 1
     - 交付项 2

     Plan: {{plansDir}}/{YYYY-MM-DD-HHmm}-...md
     ```

     **文档提交**（plan 文件 + owner 文档 + roadmap + 当日日志）
     ```
     docs(<scope>): plan-{YYYY-MM-DD-HHmm} 文档/日志/roadmap 更新

     - 更新 docs/architecture/...md
     - 更新 {{roadmapPath}}（工作项 N → done）
     - 更新 docs/logs/{YYYY}/{MM-DD}.md

     Plan: {{plansDir}}/{YYYY-MM-DD-HHmm}-...md
     ```

  c. **若本轮让某条门禁测试转绿**：把它从 `tools/gates/expected-red.txt` 删掉，**并入代码提交**。
     该文件**不在** `tests/gates/**` 红线内——测试代码是裁判（不许碰），这份名单只是「哪些裁判现在预期是红的」的账本（可以划）。
     名单只能变短——CI 的棘轮 job 盯着这件事，变长会被拦下。
  d. `git commit` 失败时：修根因后重试，最多 2 次。**永远不要** `--no-verify`、`--force`、
     或 reset 共享分支。修不好就保留工作区原样，输出 `fail` 并说明，让下一轮接手。
  e. 提交完跑 `git log --oneline -5` 确认。

全绿时按 `AGENTS.md` 在 `docs/logs/{year}/{month}-{day}.md` 记一笔，提交信息里写明 `full-green verification`。

## 输出

结尾必须且只能有一个 `<AI_STEP_RESULT>pass</AI_STEP_RESULT>` 或 `<AI_STEP_RESULT>fail</AI_STEP_RESULT>`。
这是唯一被解析的标记；缺失或格式不对会触发额外的纠正轮，白烧一轮 token。
