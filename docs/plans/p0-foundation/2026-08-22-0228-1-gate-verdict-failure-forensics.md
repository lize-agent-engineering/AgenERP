# 2026-08-22-0228-1 门禁判定失败取证：junit 报告不再被丢弃（**纯本机，不动 CI**）

> Plan Status: draft
> Mission: p0-foundation
> Work Item: 9. L2 门禁的判定与 CI 覆盖（把「只在本机验证过」补成 CI 可复跑）—— 取证面
> Last Reviewed: 2026-08-22
> Source: 2026-08-22 实测发现的取证缺口 —— CI run `32509351108`（job `96857746484`）
>   失败步骤的**全部**日志只有判定器那几行加一条 nodeid，没有断言原文、没有
>   `agenerp.apply` 的 WARNING、没有异常类型；本机同样取不到（判定器解析完就删报告）。
> Related: `2026-08-22-0027-1-live-mode-gate-verdict.md`（判定器 live 模式的交付者，本 plan 只加取证不改判定）·
>   `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`（`deferred`，停机中；本 plan **不碰**它的分支与 job）·
>   `2026-08-22-0228-2-orphan-column-clearance-fresh-site.md`（后继，消费本 plan 的取证出口）
> Execution Order: **1 / 2**
> Audit: required

## Current Baseline

每一条都是 2026-08-22 在 `10c737c` 上实测，且已被一轮独立草案评审逐条复核。

- **判定器把唯一的取证载体删了。** `tools/gates/check_expected_red.py:66-76` 的 `run_pytest`
  以 `-q --tb=no --junitxml=<JUNIT>` 起 pytest，`capture_output=True` 吃掉 stdout/stderr，
  解析完在 `:75` 逐字 `JUNIT.unlink(missing_ok=True)`。`proc.stdout` 只在「junit 压根没生成」
  这一分支打印（`:71-72`，`:73` 是 `sys.exit(2)`），门禁**红**的正常路径上一个字都不打。
- **失败详情本来就在 junit 里，`--tb=no` 不影响它。** 本轮实验：
  `python3 -m pytest test_x.py -q --tb=no --junitxml=out.xml` → exit 1，
  `<failure message=...>` 与其正文**同时**含断言原文与 `assert` 展开式。取证不需要新增采集，只需**别删**。
- **⚠️ 现在的 `unlink` 是一道保命闸，不能简单删掉。** 评审实证：
  `pytest … --this-arg-does-not-exist` → pytest 参数解析就失败、**不写**新报告，
  而上一轮的 `out.xml` 原样留在盘上（`timestamp=` 未变）。今天靠 `:75` 的 `unlink` 保证
  `:70` 的 `if not JUNIT.exists()` FATAL 分支能触发。若只把 `unlink` 去掉，判定器会拿**上一轮**的报告
  判出一个根本没发生过的结果，可能打出 `✅ 与预期红名单完全一致` 并 exit 0。
  触发路径是现成的：`main()` 把 `sys.argv[1:]` **原样转发**给 pytest。
  **因此本 plan 的形态是「把 `unlink` 挪到起 pytest 之前」，不是「删掉 `unlink`」。**
- **本机默认判定环境里没有「断言原文」可打。** 实测
  `python3 -m pytest tests/gates -q --tb=no --junitxml=/tmp/gates.xml` → `12 passed, 7 errors`，
  7 条全是 setup error，文本逐字为 `failed on setup with "Failed: compose_stack 需要 AGENERP_LIVE=1。…`；
  真正的断言 `tests/gates/test_customization_roundtrip_delete.py:69` 没有活栈根本走不到。
  **所以本 plan 的判据必须建在合成 junit 上**，不能拿这 7 条冒充。
- `JUNIT = ROOT / ".pytest-gates.xml"` 已在 `.gitignore:7`，保留它不污染 `git status --porcelain`。
- **判定器是 `plan-first` 受保护面**（`docs/context/ai-autonomy-policy.md:88`），逐字要求四件事：
  独立草案评审 + 独立关闭审计 + **默认判定环境输出逐字节不变的前后两次实跑** + 判定器自身的变异验证。
- **停机线在生效中。** `AGENTS.md` 裁判规则 4 的「CI 连续 2 轮红」已因 run `32509351108` 触发；
  STATE §3 那条 `[open]` 写死的重开条件是「successor 修好 `agenerp` 侧清除面之后，往分支推一次」。
  **本 plan 不修 `agenerp/**`，因此不满足重开条件，一次 CI 都不许跑。**
- **`verdict-tool-untouched` 对本 plan 没有合法通路。** 该 job（只在分支
  `ci/0027-2-l2-full-live-gate` 上）比 `git diff --name-only $BASE $HEAD -- tools/gates/check_expected_red.py …`，
  而 PR #1 的 `baseRefOid` 钉在 `7b0f585`（`gh pr view 1 --json baseRefOid,headRefOid` 实测），
  比两棵树时「main 有而分支没有」同样算命中。放行的唯一方式是提交信息里的
  `^Gates-Change-Approved-By:` trailer —— 那是**人工批准**，AI 自己加等于伪造。
  另：本机 `main`（`10c737c`）比 `origin/main`（`3425dae`）**领先 6 个提交**，未推。
- **`.github/workflows/**` 在 `ai-autonomy-policy.md:84` 是 `blocked | 人工批准`**，
  不只是红线 2 的「不得放松」。本 plan 因此**一行 workflow 都不改**。

## Goals

1. **门禁红的时候，红因不再丢失** —— 判定器保留 junit 报告，另有一个只读出口把每条红的
   `<failure>` / `<error>` 原文打出来。
2. **保命闸不被削弱** —— 「pytest 自己没跑起来」仍然是 `exit 2` FATAL，不得退化成拿旧报告判定。
3. **全部在本机完成，零 CI 消耗** —— 停机线在生效，本 plan 不具备重开条件。

## Non-Goals

- **不改 `agenerp/**`**（孤儿列清除面归后继 plan `0228-2`）。
- **不改 `.github/workflows/**`**（`blocked | 人工批准`），**不推任何分支**，**不跑任何 CI**。
- **不改判定逻辑**：`classify()` / `verdict()` 的返回值与退出码语义一个字节不动。
- **不改 `tests/gates/**`**（红线 1），**不划 `tools/gates/expected-red.txt`**，**不动 `missions/**`**。
- 不补 `0027-2` 欠的 `verdict-tool-untouched` 三次变异实证。

## Task Route

- Type: `implementation-only change`（受保护面的最小增量）
- Owner Docs: `docs/architecture/system-baseline.md` §14.4 · `docs/context/ai-autonomy-policy.md` Protected Areas
- Skill Selection Basis: `docs/skills/README.md` 的 `code-quality-audit-prompt.md` 覆盖「改动的行为风险复核」，
  用于 Phase 1 收尾；无其他对口 skill。

## Infrastructure And Config Prereqs

- 无新增 env / 端口 / 外部服务 / 第三方依赖（沿用 `xml.etree` + `pathlib`）。
- **不需要 docker 栈**：全部判据建在合成 junit 上。
- 回滚：纯增量，`git revert` 单个提交即可。

## Execution Plan

### Phase 1 - 判定器保留并暴露失败详情（唯一实现阶段）

Status: planned
Targets: `tools/gates/check_expected_red.py` · `tools/gates/explain_last_gate_failures.py`（新增）· `tests/unit/test_gate_verdict.py`
Skill: `code-quality-audit-prompt.md`（阶段收尾时对受保护面改动做一次行为风险复核）

- Item Types: 共 7 项 —— `Decision` 1、`Fix` 1、`Add` 2、`Proof` 3
- Prereqs: 无

- [ ] `Decision`（**草案评审阶段已裁定，执行时照做，不再重议**）：
      出口形态取**备选 A —— 独立小工具** `tools/gates/explain_last_gate_failures.py`，
      它 `from check_expected_red import failure_details` 复用同一套 nodeid 拼法。
      **备选 B（给判定器加 `--explain-last` 子命令）被排除**，理由是实测的：
      `main()` 把 `sys.argv[1:]` **原样转发**给 pytest，加自有开关就必须在转发面上开一个例外，
      而那正是「pytest 收到未知参数 → 不写报告」这条保命闸的触发路径，等于在保护面上加风险。
      **残余风险**：多一个文件要维护，且它与判定器之间多一条 import 依赖——
      缓解是 `failure_details()` 是纯函数、判定器的可执行部分被 `if __name__ == "__main__":` 挡住，
      import 不会触发任何判定副作用（判据见下面第 3 条 `Proof`）。
      - Skill: `none`
- [ ] `Fix`：把 `JUNIT.unlink(missing_ok=True)` **从解析之后挪到起 pytest 之前**，
      使报告在判定结束后仍在盘上，同时「pytest 没写报告 → `exit 2` FATAL」这条保命闸**行为不变**。
      - Skill: `none`
- [ ] `Add`：在判定器内新增纯函数 `failure_details(junit_xml) -> dict[str, str]`，
      nodeid 拼法与 `classify()` **同源**（不新开第二套口径），
      `<failure>` / `<error>` 的 message 与正文都取；正文缺失时给显式占位而非空串。
      - Skill: `none`
- [ ] `Add`：新增 `tools/gates/explain_last_gate_failures.py`，读 `.pytest-gates.xml` 并打印每条红的原文。
      **报告不存在时必须报错并非零退出**，不得打印「没有失败」——那会让「取不到证」长得像「没红」。
      - Skill: `none`
- [ ] `Proof`：`tests/unit/test_gate_verdict.py` 追加判据，**全部建在合成 junit 字符串上**
      （本机默认环境的 7 条是 setup error，没有断言原文，冒充不了）：
      ① `<failure>` 取得到 message + 正文；② `<error>` 同样取得到；③ `skipped` 不被算成失败；
      ④ 全绿时返回空 dict；⑤ **保命闸**：pytest 未写报告时判定器仍 `exit 2`（用不存在的 pytest 参数触发，
      或直接对 `run_pytest` 的 FATAL 分支断言）；⑥ import 判定器模块不产生任何判定副作用。
      命令：`python3 -m pytest tests/unit -q` → exit 0。
      - Skill: `none`
- [ ] `Proof`：**受保护面强制项之一** —— 默认判定环境前后两次实跑对照。
      改动前 `python3 tools/gates/check_expected_red.py > /tmp/verdict-before.txt 2>&1; echo $?`，
      改动后同一条命令写 `/tmp/verdict-after.txt`，
      `diff /tmp/verdict-before.txt /tmp/verdict-after.txt` **必须无输出**，两次退出码都是 0。
      三条命令的原文与输出抄进本 plan。
      - Skill: `none`
- [ ] `Proof`：**受保护面强制项之二** —— 判定器自身的变异验证。
      把 `failure_details` 改成恒返回空 dict → `python3 -m pytest tests/unit -q` 必须 exit 1
      且逐字点名新增判据；复原后复跑回 exit 0。两次输出抄进本 plan。
      - Skill: `none`

Exit Criteria:

- [ ] `python3 tools/gates/explain_last_gate_failures.py` 在一次红判定之后能打出该条门禁的原文；
      报告缺失时非零退出（两种情形各跑一次，命令原文 + 退出码在案）
- [ ] 保命闸未被削弱：`python3 tools/gates/check_expected_red.py --this-arg-does-not-exist` → **exit 2**
      （改动前后各跑一次，退出码相同）
- [ ] `diff /tmp/verdict-before.txt /tmp/verdict-after.txt` 无输出，两次 exit 0
- [ ] `python3 -m pytest tests/unit -q` exit 0 · `python3 -m pytest tests/contracts -q` exit 0 ·
      `ruff check agenerp tests/unit tests/contracts` exit 0
- [ ] `git diff --name-only` 与 `git status --porcelain` 均**未触及**
      `tests/gates/` · `.github/workflows/` · `tools/gates/expected-red.txt` · `missions/` · `docs/masterplan/DECISIONS.md`
      （逐条命令输出在案）
- [ ] `docs/architecture/system-baseline.md` §14.4 **追加**一小节说明取证出口与保命闸口径；
      `git diff -- docs/architecture/system-baseline.md | grep '^-[^-]'` **无输出**（证明只追加不改写）
- [ ] `docs/logs/2026/08-22.md` 更新

## Human Handoff（**本 plan 交不出来的那半，只有人能开**）

CI 侧消费面（在 `gates-l2-live` 上加一个 `if: failure()` 取证步骤，让红因进 CI 日志）
**不在本 plan 范围内**，且 AI 无合法通路。要落地它，需要人做两件事之一或全部：

1. **解除或豁免停机线** —— `AGENTS.md` 裁判规则 4 的「CI 连续 2 轮红」已触发，
   STATE §3 写死的重开条件是「successor 修好 `agenerp` 侧清除面后推一次」。本 plan 不修 `agenerp`，
   不满足该条件，因此不跑 CI。
2. **给判定器改动出具 `Gates-Change-Approved-By:` trailer** —— 分支上的 `verdict-tool-untouched`
   会因为「main 有而分支没有该改动」而红（`git diff BASE HEAD` 比两棵树，PR #1 的 base 钉在 `7b0f585`）。
   trailer 是人工批准，AI 自加即伪造。

本条**不是** `Follow-up`，也不是被降级的 in-scope 项：它自始不在本 plan 的结果面内（见 `## Non-Goals`）。

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（fresh session，2026-08-22）—— 判 5 条 BLOCKING：
  ① 停机线在生效，原 Phase 3「预期红的一次 CI 实跑」是在停机状态下继续烧 CI 轮次，与上一轮
  `e5e644f` 的拒绝执行直接冲突；② 原 Phase 1 的「删掉 `unlink`」会把「pytest 没跑起来 → exit 2」
  这条保命闸变成「拿上一轮旧报告判定」，评审用 `--this-arg-does-not-exist` 实证旧报告 `timestamp=` 不变；
  ③ 原 Phase 2 对 `verdict-tool-untouched` 的缓解（`git diff main <branch>`）**不是** CI 实际算的比较，
  PR #1 的 `baseRefOid` 钉在 `7b0f585`、本机 `main` 还领先 `origin/main` 6 个提交，
  合并 main 进分支反而**必然**触发该 job，而放行只能靠人工 trailer；
  ④ 原 Phase 1 的 Exit Criterion「本机用现成的 7 条预期红实证断言原文」不可满足——
  实测那 7 条全是 setup error（`failed on setup with "Failed: compose_stack 需要 AGENERP_LIVE=1`），
  且默认环境下它们是预期红、判定器 exit 0；⑤ 出口形态的 `Decision` 把选择推给执行期，
  违反 Minimum Rule 9，且让 Phase 2 没有可写的命令。另有 6 条 non-blocking（Item Types 计数与逐项标签不符、
  Goal 3 把「实跑前后全量 `capture` 对照」误读成 CI 前置、`.github/workflows/**` 实为 `blocked`
  而非仅「不得放松」、Deferred 首条无重开事件且本不属该节、两条 Exit Criteria 无命令、`:71-73` 引用漂移）。
- Draft revision 1（同日）：按上述逐条改写 —— **删除原 Phase 2 / Phase 3，本 plan 变为纯本机、零 CI**；
  CI 消费面移入新增的 `## Human Handoff`（不是 Follow-up，也不是降级）；
  `Fix` 由「删掉 `unlink`」改为「**把 `unlink` 挪到起 pytest 之前**」并新增保命闸判据；
  `Decision` 在草案期定死为备选 A 并写明排除 B 的实测理由与残余风险；
  全部判据改建在**合成 junit** 上；Item Types 改为逐项计数；Goal 3 改为「零 CI 消耗」，
  不再声称 CI 取证是后继 plan 的政策性前置；补 `.github/workflows/**` 的 `blocked` 定级；
  Deferred 一节清空（失败分支处置本就写在阶段内）；Exit Criteria 全部配上可跑命令；引用改为 `:71-72`。
- Independent draft review iteration 2: <pending>

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned（`system-baseline.md` §14.4 追加节 · `docs/logs/2026/08-22.md`）
- [ ] verification has run：`pytest tests/unit -q` · `pytest tests/contracts -q` ·
      `check_expected_red.py`（前后两次 `diff` 无输出）· `check_expected_red.py --this-arg-does-not-exist`（exit 2）·
      `explain_last_gate_failures.py`（有报告 / 无报告各一次）· `ruff check`
- [ ] scoped verification is not conflated with full verification —— 本仓无全量套件，
      本 plan 全部为本机 scoped 验证，**须在关闭记录里显式写明「verification scope limited」**
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded（至少两轮，第二轮为 `accept`）
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] 受保护面四条（独立草案评审 / 独立关闭审计 / 默认环境逐字节不变的前后两跑 / 判定器自身变异验证）逐条在案
- [ ] **零 CI 消耗**：`gh run list --branch ci/0027-2-l2-full-live-gate` 与
      `gh run list --branch main` 在本 plan 执行前后条数不变（前后两次输出在案）

## Deferred But Adjudicated

（空。本 plan 无被推迟的 in-scope 项；CI 消费面自始在 `## Non-Goals` 内，见 `## Human Handoff`。）

## Closure

Status Note: <待关闭审计填写>

Closure Audit Evidence:

- Auditor / Agent: <待填>
- Evidence: <待填>

Follow-up:

- <待填；确认的缺陷不得写在这里>
