# 2026-08-22-0228-1 门禁判定失败取证：junit 报告不再被丢弃（**纯本机，不动 CI**）

> Plan Status: completed
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
- **⚠️ 保留报告之后，「旧报告」这条危险路径并没有消失，只是换了消费者。** `unlink` 前移之后
  判定器自己不会再读到旧报告（它每轮先删再写），但**取证出口会**：报告在盘上长期存在，
  `explain_last_gate_failures.py` 无法凭「文件在不在」区分「这是刚才那轮的证」与「这是三天前那轮的证」。
  这正是本 plan 要消灭的那类失效（「取不到证长得像没红」的同族：「拿旧证当新证」）。
  证据是现成的：评审用 `--this-arg-does-not-exist` 实测过旧 `out.xml` 的 `timestamp=` 原样不变。
  **因此取证出口必须把报告的时间戳一并打出来，让陈旧可见**（判据见 Phase 1 第 4 项与 `Proof` ⑦）。
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
- **`.github/workflows/**` 在 `ai-autonomy-policy.md:80` 是 `blocked | 人工批准`**，
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

Status: completed
Targets: `tools/gates/check_expected_red.py` · `tools/gates/explain_last_gate_failures.py`（新增）· `tests/unit/test_gate_verdict.py`
Skill: `code-quality-audit-prompt.md`（阶段收尾时对受保护面改动做一次行为风险复核）

- Item Types: 共 7 项 —— `Decision` 1、`Fix` 1、`Add` 2、`Proof` 3
- Prereqs: 无

- [x] `Decision`（**草案评审阶段已裁定，执行时照做，不再重议**）：
      出口形态取**备选 A —— 独立小工具** `tools/gates/explain_last_gate_failures.py`，
      它 `from check_expected_red import failure_details` 复用同一套 nodeid 拼法。
      **备选 B（给判定器加 `--explain-last` 子命令）被排除**，理由是实测的：
      `main()` 把 `sys.argv[1:]` **原样转发**给 pytest，加自有开关就必须在转发面上开一个例外，
      而那正是「pytest 收到未知参数 → 不写报告」这条保命闸的触发路径，等于在保护面上加风险。
      **残余风险**：多一个文件要维护，且它与判定器之间多一条 import 依赖——
      缓解是 `failure_details()` 是纯函数、判定器的可执行部分被 `if __name__ == "__main__":` 挡住，
      import 不会触发任何判定副作用（判据见下面第 3 条 `Proof`）。
      - Skill: `none`
- [x] `Fix`：把 `JUNIT.unlink(missing_ok=True)` **从解析之后挪到起 pytest 之前**，
      使报告在判定结束后仍在盘上，同时「pytest 没写报告 → `exit 2` FATAL」这条保命闸**行为不变**。
      - Skill: `none`
- [x] `Add`：在判定器内新增纯函数 `failure_details(junit_xml) -> dict[str, str]`，
      nodeid 拼法与 `classify()` **同源**（不新开第二套口径），
      `<failure>` / `<error>` 的 message 与正文都取；正文缺失时给显式占位而非空串。
      - Skill: `none`
- [x] `Add`：新增 `tools/gates/explain_last_gate_failures.py`，读 `.pytest-gates.xml` 并打印每条红的原文。
      三条硬要求：
      ① **报告不存在时必须报错并非零退出**，不得打印「没有失败」——那会让「取不到证」长得像「没红」；
      ② **必须先打印这份报告的出处与时刻**（junit 根节点的 `timestamp=` 属性 + 文件 mtime），
      让「拿旧证当新证」在肉眼一行内暴露（理由见 `## Current Baseline` 第 6 条）；
      `timestamp` 属性缺失时打显式占位，不得静默省略该行；
      ③ 只读：不得写、不得删 `.pytest-gates.xml`（删了就等于把取证载体又丢一次）。
      - Skill: `none`
- [x] `Proof`：`tests/unit/test_gate_verdict.py` 追加判据，**全部建在合成 junit 字符串上**
      （本机默认环境的 7 条是 setup error，没有断言原文，冒充不了）：
      ① `<failure>` 取得到 message + 正文；② `<error>` 同样取得到；③ `skipped` 不被算成失败；
      ④ 全绿时返回空 dict；
      ⑤ **保命闸**（**方法在此定死，执行期不再选**）：对 `run_pytest` 的 FATAL 分支做单元断言 ——
      把 `JUNIT` 指向一个确定不存在的临时路径、并把 `subprocess.run` 换成不写文件的替身，
      断言它 `SystemExit` 且 code 为 `2`。**不在 tests/unit 里起真 pytest 子进程**（tests/gates 要活栈、
      跑起来以分钟计，且会把判据绑到环境上）；端到端那一路由下面 Exit Criteria 第 2 条的 CLI 实跑覆盖，
      两者分工不重叠。
      ⑥ import 判定器模块不产生任何判定副作用；
      ⑦ **陈旧可见**：喂一份带 `timestamp=` 的合成报告，断言取证出口的首行原样打出该时刻；
      再喂一份**无** `timestamp=` 的，断言打的是显式占位而不是空行。
      命令：`python3 -m pytest tests/unit -q` → exit 0。
      - Skill: `none`
- [x] `Proof`：**受保护面强制项之一** —— 默认判定环境前后两次实跑对照。
      改动前 `python3 tools/gates/check_expected_red.py > /tmp/verdict-before.txt 2>&1; echo $?`，
      改动后同一条命令写 `/tmp/verdict-after.txt`，
      `diff /tmp/verdict-before.txt /tmp/verdict-after.txt` **必须无输出**，两次退出码都是 0。
      三条命令的原文与输出抄进本 plan。
      - Skill: `none`
- [x] `Proof`：**受保护面强制项之二** —— 判定器自身的变异验证。
      把 `failure_details` 改成恒返回空 dict → `python3 -m pytest tests/unit -q` 必须 exit 1
      且逐字点名新增判据；复原后复跑回 exit 0。两次输出抄进本 plan。
      - Skill: `none`

Exit Criteria:

- [x] `python3 tools/gates/explain_last_gate_failures.py` 在一次红判定之后能打出该条门禁的原文；
      报告缺失时非零退出（两种情形各跑一次，命令原文 + 退出码在案）
- [x] 保命闸未被削弱：**每次实跑前先 `rm -f .pytest-gates.xml`**，再
      `python3 tools/gates/check_expected_red.py --this-arg-does-not-exist; echo $?` → **exit 2**
      （改动前后各跑一次，退出码相同；两条 `rm` 与两条实跑的原文与输出都抄进本 plan）。
      **`rm` 不是走过场**：改动前若盘上留着上一轮的报告，判定器会拿旧报告判出 0 或 1 而不是 2，
      「前后退出码相同」就会因环境残留而假红 —— 这恰恰是 `## Current Baseline` 第 3 条实证过的那条路径。
- [x] `diff /tmp/verdict-before.txt /tmp/verdict-after.txt` 无输出，两次 exit 0
- [x] `python3 -m pytest tests/unit -q` exit 0 · `python3 -m pytest tests/contracts -q` exit 0 ·
      `ruff check agenerp tests/unit tests/contracts` exit 0
- [x] **新增文件也过 lint**：`ruff check tools/gates/check_expected_red.py tools/gates/explain_last_gate_failures.py`
      → exit 0。（本仓惯用的 lint 面是 `agenerp tests/unit tests/contracts`，`tools/` 不在内，
      新文件否则一次都不会被 lint 到。**不扩到整个 `tools/gates`**：实测该目录另有 3 条既存告警
      落在 `check_budget.py` / `pass_usage.py` 上，与本 plan 无关，扩面等于把顺手优化拖进来。）
- [x] `git diff --name-only` 与 `git status --porcelain` 均**未触及**
      `tests/gates/` · `.github/workflows/` · `tools/gates/expected-red.txt` · `missions/` · `docs/masterplan/DECISIONS.md`
      （逐条命令输出在案）
- [x] `docs/architecture/system-baseline.md` §14.4 **追加**一小节说明取证出口与保命闸口径；
      `git diff -- docs/architecture/system-baseline.md | grep '^-[^-]'` **无输出**（证明只追加不改写）
- [x] `docs/logs/2026/08-22.md` 更新

Execution Evidence（2026-08-22 实跑，命令原文 + 输出）:

```
# 保命闸 · 改动前（先清残留，否则旧报告会让判定器判出 0/1 而非 2）
$ rm -f .pytest-gates.xml
$ python3 tools/gates/check_expected_red.py --this-arg-does-not-exist; echo $?
FATAL: pytest 没产出 junit 报告，它自己就跑挂了：
 ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: unrecognized arguments: --this-arg-does-not-exist
  inifile: /Users/lize/Claude/Projects/AgenERP/pyproject.toml
  rootdir: /Users/lize/Claude/Projects/AgenERP
判定模式：default —— 按 tools/gates/expected-red.txt 判定
2

# 保命闸 · 改动后（同一条命令，同一前置）
$ rm -f .pytest-gates.xml
$ python3 tools/gates/check_expected_red.py --this-arg-does-not-exist; echo $?
（输出与改动前逐字相同）
2

# 保命闸 · 改动后新增的一路：盘上留着上一轮报告时仍 FATAL（`unlink` 前移换来的）
$ ls -la .pytest-gates.xml
-rw-r--r--@ 1 lize  staff  6817 Aug 22 06:06 .pytest-gates.xml
$ python3 tools/gates/check_expected_red.py --this-arg-does-not-exist; echo $?
2

# 受保护面强制项之一 · 默认判定环境前后两次实跑逐字节对照
$ python3 tools/gates/check_expected_red.py > /tmp/verdict-before.txt 2>&1; echo $?
0
$ python3 tools/gates/check_expected_red.py > /tmp/verdict-after.txt 2>&1; echo $?
0
$ diff /tmp/verdict-before.txt /tmp/verdict-after.txt; echo $?
0
# 两份内容均为：
判定模式：default —— 按 tools/gates/expected-red.txt 判定
门禁 19 项：预期红 7，绿 12，跳过 0
✅ 与预期红名单完全一致

# 取证出口 · 报告在（判定完报告留在盘上，此前它会被删）
$ python3 tools/gates/explain_last_gate_failures.py; echo $?
报告：/Users/lize/Claude/Projects/AgenERP/.pytest-gates.xml｜junit timestamp=2026-08-22T06:06:44.657199+08:00｜文件 mtime=2026-08-22T06:06:44
红 7 条，逐条原文如下：

=== tests/gates/test_customization_roundtrip_delete.py::test_added_field_exports_into_pack
<error> failed on setup with "Failed: compose_stack 需要 AGENERP_LIVE=1。
L2 门禁默认不跑（要拉起完整 ERPNext，分钟级）。真要跑：
    AGENERP_LIVE=1 python3 -m pytest tests/gates -m live -q
这不是 skip —— 判定器不接受 skip，未跑就是红。"
E   Failed: compose_stack 需要 AGENERP_LIVE=1。
（下略 6 条同型）
0

# 取证出口 · 报告不在（必须报错并非零退出，不得打印「没有失败」）
$ python3 tools/gates/explain_last_gate_failures.py; echo $?
FATAL: 取不到证 —— junit 报告不存在：/Users/lize/Claude/Projects/AgenERP/.pytest-gates.xml
       先跑一次 python3 tools/gates/check_expected_red.py 生成它。（报告不在 ≠ 没有红）
2

# 受保护面强制项之二 · 判定器自身的变异验证（failure_details 恒返回空 dict）
$ python3 -m pytest tests/unit -q; echo $?
FAILED tests/unit/test_gate_verdict.py::test_failure_details_keeps_message_and_body_of_a_failure
FAILED tests/unit/test_gate_verdict.py::test_failure_details_keeps_message_and_body_of_an_error
FAILED tests/unit/test_gate_verdict.py::test_failure_details_uses_explicit_placeholders_instead_of_empty_strings
FAILED tests/unit/test_gate_verdict.py::test_failure_details_and_classify_agree_on_nodeids
FAILED tests/unit/test_gate_verdict.py::test_explain_prints_every_red_verbatim_and_never_touches_the_report
5 failed, 212 passed in 0.56s
1
# 复原后复跑：
$ python3 -m pytest tests/unit -q; echo $?
217 passed in 0.54s
0

# 常规验证
$ python3 -m pytest tests/unit -q; echo $?          → 217 passed / 0
$ python3 -m pytest tests/contracts -q; echo $?      → 151 passed / 0
$ ruff check agenerp tests/unit tests/contracts; echo $?                                    → All checks passed! / 0
$ ruff check tools/gates/check_expected_red.py tools/gates/explain_last_gate_failures.py; echo $?  → All checks passed! / 0

# 红线自查
$ git status --porcelain
 M docs/architecture/system-baseline.md
 M docs/backlog/p0-foundation-roadmap.md
 M docs/logs/2026/08-22.md
 M docs/plans/p0-foundation/2026-08-22-0228-1-gate-verdict-failure-forensics.md
 M tests/unit/test_gate_verdict.py
 M tools/gates/check_expected_red.py
?? tools/gates/explain_last_gate_failures.py
$ git status --porcelain | grep -E 'tests/gates/|\.github/workflows/|tools/gates/expected-red\.txt|missions/|docs/masterplan/DECISIONS\.md'; echo $?
1   # 无命中
$ git diff -- docs/architecture/system-baseline.md | grep '^-[^-]'; echo $?
1   # 无删除行，§14.4 为纯追加

# 零 CI 消耗（执行前 / 执行后各一次）
$ gh run list --branch ci/0027-2-l2-full-live-gate --limit 100 | wc -l   → 1（前）/ 1（后）
$ gh run list --branch main --limit 100 | wc -l                          → 36（前）/ 36（后）
$ diff /tmp/ci-runs-before.txt /tmp/ci-runs-after.txt; echo $?           → 无输出 / 0
```

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
- Independent draft review iteration 2: **accept（修复后）**（fresh session，2026-08-22，
  MISSION_DRIVER `2026-08-22-055517-mission-driver`）—— 逐条复核了 `## Current Baseline` 的每一处引用，
  实测确认：`check_expected_red.py:66-76` 的 `run_pytest` 形态、`:75` 的 `unlink`、`:70-73` 的 FATAL 分支、
  `.gitignore:7`、`ai-autonomy-policy.md:88` 的 `plan-first` 行与其逐字四要求、
  `tests/unit/test_gate_verdict.py` 已按文件路径 `exec_module` 加载判定器、
  `system-baseline.md:383` 的 §14.4、`docs/skills/README.md:53` 的 `code-quality-audit-prompt.md`、
  `tests/gates/test_customization_roundtrip_delete.py:69` 的断言 —— **全部属实**。
  格式合规（模板必需节齐备，Phase 结构合法，`Item Types` 计数与逐项标签一致，
  `Decision` 具备候选/理由/残余风险，Status 与 checkbox 一致）。评审期直接改掉 4 条 Major + 1 条 Minor：
  **M1** 保命闸 Exit Criterion 缺前置状态 —— 改动前若盘上留着旧报告，判定器会读旧报告判出 0/1 而非 2，
  「前后退出码相同」会因环境残留假红；已加 `rm -f .pytest-gates.xml` 为强制前置并写明理由。
  **M2** 新增的 `tools/gates/explain_last_gate_failures.py` 无 lint 覆盖 ——
  本仓惯用 lint 面 `agenerp tests/unit tests/contracts` 不含 `tools/`；已加**文件级** ruff 判据，
  并实测 `tools/gates` 整目录另有 3 条既存告警（`check_budget.py` / `pass_usage.py`），
  故明确不扩面，避免把顺手优化拖进来。
  **M3** `unlink` 前移后报告长期驻盘，取证出口无法区分「刚才那轮的证」与「三天前那轮的证」——
  这是本 plan 要消灭的失效的同族（「拿旧证当新证」）；已在 Baseline 补第 6 条，
  并给取证出口加三条硬要求（时间戳首行 / 缺失时显式占位 / 只读不删）与 `Proof` ⑦。
  **M4** `Proof` ⑤ 用「或」把方法推给执行期（iteration 1 判过同型 BLOCKING）——
  已定死为对 `run_pytest` FATAL 分支的单元断言，端到端一路交给 Exit Criteria 的 CLI 实跑，分工不重叠。
  **Minor**：`.github/workflows/**` 的引用 `ai-autonomy-policy.md:84` 漂移，实为 `:80`，已订正。
  修复后无遗留 Blocker/Major，`Plan Status` 由 `draft` 改为 `active`。

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（`system-baseline.md` §14.4 追加节 · `docs/logs/2026/08-22.md`）
- [x] verification has run：`pytest tests/unit -q` · `pytest tests/contracts -q` ·
      `check_expected_red.py`（前后两次 `diff` 无输出）· `check_expected_red.py --this-arg-does-not-exist`（exit 2）·
      `explain_last_gate_failures.py`（有报告 / 无报告各一次）· `ruff check`
- [x] scoped verification is not conflated with full verification —— 本仓无全量套件，
      本 plan 全部为本机 scoped 验证，**须在关闭记录里显式写明「verification scope limited」**
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（至少两轮，第二轮为 `accept`）
- [x] text consistency verified: status, phases, gates, and log all agree
- [x] closure audit was independent —— 由 loop 的独立 `CLOSURE_VERIFY` 步（fresh session，MISSION_DRIVER
      `2026-08-22-055517-mission-driver`）执行，**执行器未自审**（`AGENTS.md` Reviewer-Availability Fallback：
      受保护面不适用 solo cold-replay）。审计侧复跑命令与退出码见 `## Closure`。
- [x] closure evidence exists in files
- [x] 受保护面四条：独立草案评审（两轮，第二轮 `accept`）✅ · 默认判定环境逐字节不变的前后两跑 ✅ ·
      判定器自身变异验证 ✅ · **独立关闭审计 ✅ 已做**（同上条，由独立 `CLOSURE_VERIFY` 完成并自行复跑了变异验证）
- [x] **零 CI 消耗**：`gh run list --branch ci/0027-2-l2-full-live-gate` 与
      `gh run list --branch main` 在本 plan 执行前后条数不变（前后两次输出在案）

## Deferred But Adjudicated

（空。本 plan 无被推迟的 in-scope 项；CI 消费面自始在 `## Non-Goals` 内，见 `## Human Handoff`。）

## Closure

Status Note: Phase 1 全部执行完毕，本机 scoped 验证全绿（命令原文与退出码见 Phase 1 的 `Execution Evidence`），**独立关闭审计已完成并接受关闭**。**verification scope limited**：本仓无全量套件，本 plan 全部为本机 scoped 验证，**CI 一次未跑**（停机线在生效，且本 plan 不满足 STATE §3 的重开条件；`git log --oneline origin/main -1` → `508c75b`，交付提交 `57ad6d5` **未推送**，因此审计期同样零 CI 消耗）。判定器是 `ai-autonomy-policy.md` 的 `plan-first` 受保护面，关闭审计由**执行器之外**的独立 `CLOSURE_VERIFY` 步做，执行器未自审。

Closure Audit Evidence:

- Auditor / Agent: 独立 `CLOSURE_VERIFY` 步（fresh session，MISSION_DRIVER `2026-08-22-055517-mission-driver`），
  非本 plan 的执行器；审计期不改任何交付文件，只复跑命令并回填本节与 `## Closure Gates` 两条。
- Evidence（执行侧）: Phase 1 的 `Execution Evidence` 代码块 · `docs/logs/2026/08-22.md` 首条 ·
  `docs/architecture/system-baseline.md` §14.4 末节（`git show 57ad6d5 -- docs/architecture/system-baseline.md | grep '^-[^-]'` → 无输出，exit 1，纯追加）·
  `docs/backlog/p0-foundation-roadmap.md` 工作项 9「三次补记」· 交付提交 `57ad6d5`（8 files，+615/-68）
- Evidence（审计侧复跑，2026-08-22，命令原文 + 退出码）:
  - `python3 -m pytest tests/unit -q` → `217 passed`，exit 0
  - `python3 -m pytest tests/contracts -q` → `151 passed`，exit 0
  - `ruff check agenerp tests/unit tests/contracts` → `All checks passed!`，exit 0
  - `ruff check tools/gates/check_expected_red.py tools/gates/explain_last_gate_failures.py` → `All checks passed!`，exit 0
  - 保命闸：`rm -f .pytest-gates.xml && python3 tools/gates/check_expected_red.py --this-arg-does-not-exist` → exit 2
  - 取证出口 · 报告不在：`python3 tools/gates/explain_last_gate_failures.py` → `FATAL: 取不到证 …（报告不在 ≠ 没有红）`，exit 2
  - 端到端：`python3 tools/gates/check_expected_red.py` → exit 0（`门禁 19 项：预期红 7，绿 12，跳过 0`）；
    紧接 `python3 tools/gates/explain_last_gate_failures.py` → exit 0，首行为
    `报告：…/.pytest-gates.xml｜junit timestamp=2026-08-22T06:12:19.520045+08:00｜文件 mtime=2026-08-22T06:12:19`，
    其后 `红 7 条，逐条原文如下：` 并逐条打出 `<error> failed on setup with "Failed: compose_stack 需要 AGENERP_LIVE=1。…` 原文
  - **审计自行复跑的变异验证**（不采信执行器的抄录）：把 `failure_details()` 首行改成恒 `return details`
    → `python3 -m pytest tests/unit -q` → `5 failed, 212 passed`，逐字点名
    `test_failure_details_keeps_message_and_body_of_a_failure` / `…_of_an_error` /
    `…_uses_explicit_placeholders_instead_of_empty_strings` / `test_failure_details_and_classify_agree_on_nodeids` /
    `test_explain_prints_every_red_verbatim_and_never_touches_the_report`；复原后 `217 passed`，exit 0，
    `git status --porcelain` 无输出（工作区已还原）
- Anti-Hollow: `failure_details()` 被 `explain_last_gate_failures.py` 的 `report_lines()` 实调用（非注册即孤儿），
  端到端实跑已打出真实红因原文；`unlink` 前移后 FATAL 分支实测仍 exit 2，无空函数体 / `return null` 占位 / 吞异常。
- 红线自查（审计侧独立复核）: `git show --stat 57ad6d5` 的 8 个文件**未触及**
  `tests/gates/` · `.github/workflows/` · `tools/gates/expected-red.txt` · `missions/` · `docs/masterplan/DECISIONS.md`；
  `git status --porcelain` 在审计结束时为空。

Follow-up:

- 无。CI 侧取证消费面见 `## Human Handoff`，自始在 `## Non-Goals` 内，**不是**被降级的 in-scope 项。
