# 2026-08-22-0027-1 判定器的 live 判定模式（`AGENERP_LIVE=1` 下全绿即通过）

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 9. L2 门禁的判定与 CI 覆盖（**本 plan Phase 1 新增该工作项**，理由见其 `Decision`）—— 第一个 plan：判定设施半
> Last Reviewed: 2026-08-22
> Source: `docs/architecture/system-baseline.md` 第 381–393 行 `### L2 门禁在 CI 上的判定方式，与它换来的残余风险`
>   逐字登记的「真正的修法是给判定器加一份「live 名单」」；
>   plan `2026-08-21-2220-2` 的 `Deferred But Adjudicated`「判定器没有「live 名单」这个概念」，
>   重开事件逐字为「**当 CI 的 L2 覆盖面扩到 `test_zero_dep_boot.py` 之外时**」——该扩面由本批第二个 plan 执行，故本 plan 先行
> Related: `2026-08-21-2220-2-homepage-ai-not-configured.md`（登记该 Deferred 的 plan）·
>   `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`（本批第二个 plan，本 plan 的唯一消费者，且是 B2 那条 CI 守卫的 owner）
> Audit: required

## 术语约定：本 plan 说的「那一节」到底在哪

**本仓没有 `§14.4` 这个编号。** 起草时实测：`docs/architecture/system-baseline.md` 共 393 行，
最后一个带编号的节是 `## 14.3 「AI 能力未配置」在本仓的表达口径`（第 286 行），
而描述 CI L2 判定方式的那段是它**下面一个不带编号的三级标题**：

```
381:### L2 门禁在 CI 上的判定方式，与它换来的残余风险
```

`grep -rn "14\.4" docs/ tools/ .github/` 在本批两个 plan 之外**零命中**。
本 plan 下文一律称它为 **「判定方式节」**（= `system-baseline.md` 第 381–393 行那一节），
不用任何编号指代。**它当前挂在 `## 14.3` 之下属于误归档**——14.3 讲的是首页「AI 能力未配置」的表达口径，
与 CI 判定方式无关。Phase 1 会把它**提升为独立的 `## 14.4`** 并改写，该动作是 `Fix`（确认的文档漂移），
不是顺手重排。

## Current Baseline

**以下每条都在 2026-08-22 起草时读过活文件；被独立评审逐条复核过，复核指出的错处已就地改准。**

### 判定器现状

- `tools/gates/check_expected_red.py` 是**本仓唯一的门禁判定器**。这句「别再写第二个判定器」的出处是
  **`docs/backlog/p0-foundation-roadmap.md:75`**（「框架/平台复用」表），**不是 `AGENTS.md`**——
  `AGENTS.md` 里没有这张表。按 `AGENTS.md` 开篇的优先级次序（红线 > masterplan 执行协议 > AGENTS.md 其余 > 上游模板），
  它是 **mission roadmap 级别的约束**，不是红线级别。本 plan 引用它时按这个强度用，不拔高。
- 它被**两处**消费：`missions/p0-foundation.json` 的 `commands.test`（`GATE_VERIFY` 子进程复跑的就是它）
  与 `.github/workflows/gates.yml` 的 `gates-l1` job。
- 行为：读 `tools/gates/expected-red.txt` → 跑
  `python -m pytest tests/gates -q --tb=no --junitxml=.pytest-gates.xml` → 解析 junit →
  三态分类 `red` / `green` / `skipped` → 四条判据（名单外红 = 失败、名单内绿 = 失败、出现 skip = 失败、其余通过）
  → 退出码 `0` / `1` / `2`（`2` = 跑不起来）。
- `healed_env()` 只**追加** `/usr/local/bin`、`/usr/local/sbin`，不前置；注释里记着一次踩坑的 sha（`0f2c59a`），
  另一次只有日期没有 sha。本 plan 不动它。
- 分类逻辑此刻**内联在 `run_pytest()` 与 `main()` 里**，没有可从 `tests/unit` 直接喂输入的纯函数接缝。
- `run_pytest(sys.argv[1:])`：命令行参数原样透传给 pytest。

### 名单现状（实测）

`tools/gates/expected-red.txt` 去掉注释后 **7 行**（`test_customization_roundtrip_delete.py` 四条 ·
`test_snapshot_diff_structured.py::test_field_addition_shows_up_as_structured_change` ·
`test_zero_dep_boot.py` 两条）。

默认判定环境最近一次实跑（`docs/logs/2026/08-22.md`，`HEAD` = `8b1e95c`，干净树）：
`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**，
前半输出逐字 `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`，后半 `193 passed`。
起草时 `HEAD` = `084c9c4`，**工作树除本批两个未跟踪的 plan 文件外干净**。

### 两个判定环境给出相反判定 —— 这是本 plan 要处理的那个矛盾

人已在 `docs/masterplan/STATE.md` §2（2026-08-21T11:20Z）裁定过口径：**「名单必须反映判定器实际看到的」**。
默认判定环境没有 `AGENERP_LIVE`，`tests/gates/conftest.py:53` 的 `_require_live()` 直接 `pytest.fail`
（**不是 skip**），所以名单里 7 条在那里**恒红**。而在 live 判定环境下它们都是绿的，
同一个判定器会报「名单内的门禁却绿了」并 exit 1。判定方式节因此逐字记着 CI **绕开了判定器**，
并给出修法与重开条件（「加一份 live 名单」/「CI 的 L2 覆盖面扩到 `test_zero_dep_boot.py` 之外时」）。

**该措辞不构成约束**：它是一段残余风险说明里提出的修法建议，不是契约。本 plan 若偏离它，
在改写同一节时把偏离逐字记下即可（Phase 1 `Decision` 一）。

### 「直接判 pytest 退出码」到底漏了什么

1. **skip / xfail 漏判 —— 唯一的硬漏洞。** `pytest` 对全部 skip 的一轮照样退 0；判定器不然。
   `tests/gates/conftest.py:8` 逐字写着「不许 `skip`」，但 CI 的 L2 那条路上**没有任何东西在执行这句话**。
2. **收集期错误的表现不同**（判定器 exit 2 vs exit 1 分开，裸 pytest 混在一起）。
3. **两套判定约定**，与 roadmap:75 那条抵触（roadmap 级强度）。
4. **本机 live 跑法是三串各不相同的手敲 env**（`project-context.md` 第 56–58 行），没有单一入口。

**不夸大**：第 2、3、4 条是「难用、易错、口径分裂」，不是「判据失效」。真正会让假绿溜过去的只有第 1 条。

### 判定器自身**没有任何保护** —— 本 plan 打开这个面，必须同时说清它

起草时逐条实测：

| 层 | 覆盖 | 是否护住 `check_expected_red.py` |
|---|---|---|
| CI `gates-untouched` job | `git diff --name-only … -- 'tests/gates/**'` | **否** |
| `GATE_VERIFY`（`tools/gates/gate-verify.mjs:22`） | `const PROTECTED = ["tests/gates/"]` | **否** |
| CI `expected-red-ratchet` job | 只数 `tools/gates/expected-red.txt` 的行数 | **否** |
| `ai-autonomy-policy.md` Protected Areas 表 | 十行，无一行提到判定器 | **否** |

**而 `gates-l1` job 跑的就是判定器本身**——判定器被改废之后会在 CI 上**自证为绿**。
`AGENTS.md` 裁判规则 1 把「测试过没过」的裁定权交给 `GATE_VERIFY` 的退出码，
而产出那个退出码的脚本此刻三层皆无保护。**这不是本 plan 造成的，但本 plan 是第一个真的去改它的 plan，
因此由本 plan 负责把它登记并加严**（Phase 1 第三项 + 本 plan 的 Deferred 指名 successor）。

### 一个必须先查清的未知（Phase 3 的第一项就为它而设）

**live 判定环境下 19 条一次跑完是否互不干扰，本仓没有任何证据。** 迄今 live 绿证都是**按文件分开跑的**，
且**只覆盖 19 条中的 10 条**：`test_snapshot_diff_structured.py` 3 条（plan `1922-1`）·
`test_customization_roundtrip_delete.py` 4 条（plan `2220-1`）· `test_zero_dep_boot.py` 3 条（plan `2220-2`）。
另外 9 条（`test_normalizer_idempotent.py` 3 + `test_seed_dataset_absurdity.py` 6）是**默认环境**的 L1 绿，
**没有在 live 环境下跑过**。而判定器只会整目录跑 `pytest tests/gates`。
已知干扰面真实存在：两个文件都在同一个 `Item` 上建/删探针 Custom Field，
且 `docs/backlog/gate-fixtures-pollute-the-live-site.md` 实测记着删 Custom Field 不删物理列。
唯一一次整目录 live 跑的留痕在 STATE §3（sha `826cdf8`，`预期红 5，绿 14，跳过 0`），
但那是删除路径与首页文案都还没实现之前的快照，对今天没有证明力。

### 三处 live 跑法口径（缺一条就跑不出绿，出处 `project-context.md:56`）

1. **端口 18080** —— 8080 被本机另一套常驻 ERPNext 占着，`compose_stack` 有端口预检并会直接 fail。
2. **`AGENERP_SITE=frontend` 必须由命令给。** ⚠️ `project-context.md:56` 对此的措辞是
   「`tests/gates/conftest.py` 全文不设这个变量」——**这句话是错的**，实测 `conftest.py:274`
   在 `live_site` fixture 内部会设它。正确的说法更窄：
   `test_snapshot_diff_structured.py` 里那两条 **不取任何 fixture**、直接调 `capture()`，
   永远走不到那行代码，所以必须由命令给。**这是确认的 owner-doc 漂移**，
   按 Minimum Rule 14 不得降级成 follow-up，Phase 3 有一条 `Fix` 就地改准（第 56 行与第 57 行同措辞处一起）。
3. **必须先起栈** —— 同样因为那两条不取 fixture，栈没预起时它们在 `compose_stack` 之前就跑完并红在 connection refused。

**这三条对判定器同样成立**，它只是换个进程去跑同一组 pytest。

### 受保护面自查（起草时逐条核对）

| 面 | 本 plan 是否触及 | 依据 |
|---|---|---|
| `tests/gates/**` | **否，一个字节都不改** | 红线 1 |
| `tools/gates/expected-red.txt` | **否，一行不划**（live 模式压根不读它） | 账本可变短，但本 plan 无转绿项 |
| `tools/gates/check_expected_red.py` | **是** —— 三层皆无保护（上表），Protected Areas 表也没有它 | 红线 1 的边界逐字划在 `tests/gates/**`。**但「没规则挡着」不等于「安全」**，见 Phase 1 第三项：本 plan 就地补一条**加严**规则 |
| `agenerp/apply.py` 的 `execute_plan` 删除路径 | **是（仅 Phase 3 的临时变异，必须复原）** | `ai-autonomy-policy.md` Protected Areas 末行：`plan-first`，Required Evidence 含「实跑前后全量 `capture` 对照」。处置见 Phase 3 变异 ①（该阶段第三项） |
| `.github/workflows/**` | **否**（含 B2 那条 CI 守卫，全部归本批第二个 plan） | 红线 2 / Protected Areas `blocked` |
| `missions/*.json` | **否** | 角色 B 禁区 |
| `docs/masterplan/**` | 仅 `STATE.md` §2 **追加**一行证据 | 红线 5 |

## Goals

- `tools/gates/check_expected_red.py` 增加一个 **live 判定模式**：由 `AGENERP_LIVE=1` 选中，
  契约是**全部门禁绿、零 red、零 skip**；该模式**不读** `expected-red.txt`。
- **默认判定环境的判定行逐字节不变**（口径见 Phase 2：`门禁 N 项：…` 与四条判据的输出行；
  新增的模式行不计），由 `tests/unit` 的单测 + 前后两次实跑逐字对照钉住。
- 把三态分类与判定逻辑抽成可从 `tests/unit` 直接喂输入的纯函数，让 **skip 判定本身**第一次有判据覆盖。
- **给判定器补上它此刻缺的那层保护**：在 `ai-autonomy-policy.md` 的 Protected Areas 表新增一行（**加严**），
  并把「CI 侧守卫」指名交给本批第二个 plan，不留无主。
- 在本机 live 环境下用新模式对 **19 条一次性**做出判定，并附**正向对照**（证明它真能返回 0），
  退出码与输出逐字进 `docs/logs/` 与 STATE §2。
- roadmap 新增工作项 9，使本批两个 plan 不违反「一个工作项 = 1–2 个 plan」。

## Non-Goals

- **不改 `.github/workflows/`** 下任何文件 —— CI 消费面与 B2 那条守卫全部归本批第二个 plan。
  本 plan 落地后 CI 行为一字不变。
- **不新建「live 名单」文件**（理由见 Phase 1 `Decision` 一，偏离已记）。
- **不划 `expected-red.txt` 的任何一行**，也不请求人划。
- **不改 `agenerp/` 的产品行为** —— Phase 3 的变异是临时的，必须复原并复跑确认。
- **不解决站点污染**（孤儿列累积）——在红线 1 内。
- **不把新命令接进 `missions/*.json`** —— 角色 B 禁区，登记为 Deferred。

## Task Route

- Type: `architecture change + implementation-only change`
- Owner Docs: `docs/architecture/system-baseline.md` 判定方式节（第 381–393 行，本 plan 提升为 `## 14.4` 并改写）·
  `docs/context/ai-autonomy-policy.md` Protected Areas 表 · `docs/backlog/p0-foundation-roadmap.md`
  （工作项表 + 第 75 行「别再写第二个判定器」）· `docs/context/project-context.md` 验证命令表 ·
  `AGENTS.md` 裁判规则 1/2/3
- Skill Selection Basis: `docs/skills/README.md` 没有覆盖「改判据设施本身」的条目；全程 `Skill: none`。

## Infrastructure And Config Prereqs

- docker + `docker compose`（本机 v5.0.2 / Docker 29.2.1）。**端口 18080**。
- **开工第一步必须记下开工 sha**（写进 Phase 1 首项）。后续所有红线自查都用
  `git diff <开工 sha>..HEAD -- <paths>` 与 `git status --porcelain -- <paths>` 两条一起，
  **不用裸 `git diff`**——裸 `git diff` 比的是工作树 vs 暂存区，一旦提交就恒为空，是一条不可能触发的假守卫。
- Phase 3 起栈：`AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`
- 新判定命令的预期形态（实际以 Phase 1 `Decision` 二为准）：

```
AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend \
AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin \
python3 tools/gates/check_expected_red.py
```

- **回滚策略**：写动作全是文本文件，`git revert` 即可。
  **本 plan 一共开三个变异窗口，全部必须复原**（独立评审 BLOCKING-4：起草时只列了两个，且用了一个不存在的标号）：

  | 标号 | 文件 | 出处 |
  |---|---|---|
  | Phase 2 负向对照 | `agenerp/pack.py`（`normalize` 改成恒等） | Phase 2 第 5 项 |
  | 变异 ① | `agenerp/apply.py`（删除路径改 no-op） | Phase 3 第 3 项 |
  | 变异 ② | `tools/gates/check_expected_red.py`（`verdict()` 的 `skipped` 分支） | Phase 3 第 4 项 |

  每一处复原后都必须**复跑确认回到基线**，退出码抄进 plan。
  **本 plan 的整个安全性叙事就建立在「三处变异全部复原、零产品行为发布」上**，
  所以这张表的条目数必须与实际开的窗口数一致——对不上就是文本不一致（Closure Gate 会咬）。
- live 实测会在站点上留探针孤儿列——既有残留，本 plan **不加剧也不清理**。

## Execution Plan

### Phase 1 — 判定契约、判定器的保护、工作项归属

Status: completed
Targets: `docs/backlog/p0-foundation-roadmap.md` · `docs/context/ai-autonomy-policy.md` ·
  `docs/architecture/system-baseline.md`（判定方式节） · 本 plan 文件
Skill: `none`

- Item Types: `Proof | Decision | Add | Fix`
- Prereqs: 无（本 plan 是本批第一顺位）

- [x] `Proof` **记下开工 sha**：`git rev-parse HEAD` 与 `git status --porcelain`，两者输出抄进本节。
      后续所有红线自查以这个 sha 为基线。
      - Skill: `none`
- [x] `Decision` **定 live 模式的判定契约**。
      **(a) 真加一份 live 名单文件**（判定方式节逐字建议的形态）；
      **(b) 不加文件，契约写死为「全部绿、零 red、零 skip」**。
      **推荐 (b)**：① 起草时可推定 live 下 19 条应当全绿（10 条有直接绿证，9 条是 L1 且不依赖 live 环境），
      所以 (a) 落地后那份文件**内容为空**，与「全绿」是同一个契约；
      ② (a) 需要给新名单再配一条棘轮，而那是 `.github/workflows/**` 的改动，本 plan 的 Non-Goals 排除。
      **⚠️ 不再声称 (b)「严格更紧」。** 独立评审指出该理由是假的：判定器此刻三层皆无保护
      （见 Current Baseline 那张表），把逃生口从一份有棘轮的文本文件挪进**无保护的代码**，
      不是变紧而是**换了个位置**。(b) 的真实优点只有两条：省一个可被写长的面、不需要动 CI。
      **这也正是本 Decision 必须与下一项（补保护）捆绑落地的原因**——单独选 (b) 是净损失。
      **残余风险**：将来若真出现「live 下也必须红」的门禁，(b) 会把它变成硬阻塞，需要人改判定器。
      这一条写进判定方式节，不藏着。
      **备选未选的记录**：(a) 与 owner doc 措辞一致、扩展性好，但要多配一条棘轮，且本仓此刻一条 live 预期红都没有。
      - Skill: `none`
- [x] `Fix | Add` **给判定器补上保护（加严，`ai-autonomy-policy.md` 明文允许 AI 加严、禁止放松）。**
      三件事，缺一不可：
      · **①** 在 Protected Areas 表新增一行：
        `tools/gates/check_expected_red.py`（**判定器本体**）| `plan-first` |
        Required Evidence = 独立草案评审 + 独立关闭审计 + **「默认判定环境输出逐字节不变」的前后两次实跑** +
        **判定器自身的变异验证**（改坏它必须让 `tests/unit` 红）。
        表下补一句说明**为什么此前没有这一行**：三层保护（`gates-untouched` / `gate-verify.mjs` 的
        `PROTECTED` / `expected-red-ratchet`）全部只覆盖 `tests/gates/**` 与那份 txt，
        而 `gates-l1` 跑的就是判定器本身——判定器被改废会在 CI 上自证为绿。
      · **②** 明确边界：**新增的这一行只覆盖 `check_expected_red.py`，不覆盖 `tools/gates/expected-red.txt`。**
        **出处（逐字，不用二手转述）**：`AGENTS.md` 红线 1 的「边界」句——「预期红名单
        `tools/gates/expected-red.txt` 不在此列——它是账本不是裁判，测试转绿时应当在同一提交里划掉对应行
        （只能变短）」；以及 `ai-autonomy-policy.md` Protected Areas 第 2 行——
        `tools/gates/expected-red.txt` | **allowed（只能变短）**，「名单**变长**仍需 `Gates-Change-Approved-By:`」，
        服务端控制是 `expected-red-ratchet` job。把账本圈进守卫，会让**每一次合法的划短**在 CI 上失败
        （除非人加 trailer），直接抵触红线 1 自己开的这个口子。
        ⚠️ 起草时曾把这条边界的出处写成「人在 STATE §2（11:20Z）对账本的裁定」——**那是误引**：
        §2 11:20Z 逐字是「名单必须反映判定器实际看到的，不是我知道的」，讲的是**名单里该写什么**，
        不是**谁可以改它**。误引已改准，此处留痕免得后继再引错。
      · **③** 把「CI 侧守卫」（服务端复核 `tools/gates/check_expected_red.py` 未经批准的改动）
        **指名交给本批第二个 plan**，并在本 plan 的 `Deferred But Adjudicated` 里登记，
        `Successor Required: yes`。理由：它是 `.github/workflows/**` 改动，与本 plan 的 Non-Goals 冲突，
        且本批第二个 plan 本来就要动那份文件一次，合并一次改动比分两次安全。
      **残余风险照实记**：① 是文档级约束，对拿着 shell 的执行器没有强制力；真正的强制力在 ③，
      而 ③ 在本 plan 关闭时**还没落地**。这段空窗期必须写进判定方式节，不粉饰。
      **空窗期内唯一带牙齿的控制**：在 Phase 2 那个改判定器的提交上**自愿**带一行
      `Gates-Change-Approved-By:` trailer——它不是本仓要求的（判定器不在 `gates-untouched` 的路径里，
      没有任何 job 会检查它），但它让这次改动在 `git log` 里**可被检索**，
      将来复盘「判定器什么时候被谁改过」时有据可查。本 plan 采纳这一条。
      ⚠️ 同时照实记：新增那条 Protected Areas 行的 Required Evidence
      （独立评审 + 独立关闭审计 + 前后两次实跑 + 判定器变异验证）**恰好就是本 plan 已经在做的事**，
      因此它对**本次**改动没有任何增量约束，只对**将来的会话**有约束。不夸大它。
      - Skill: `none`
- [x] `Decision` **定模式的选择开关**。
      **(a) 环境变量 `AGENERP_LIVE=1`**（与 `conftest.py:53` 的 `_require_live()` 同一个开关）；
      **(b) 新增命令行参数 `--live`**；**(c) 探测栈是否起着**。
      **推荐 (a)**：判定器把 `sys.argv[1:]` 原样透传给 pytest，加位置参数与透传语义打架；
      (c) 是隐式判定，会让「栈碰巧起着」悄悄改变判定口径。(a) 与 fixture 用同一个开关，两者不可能各判各的。
      **残余风险**：默认环境误设 `AGENERP_LIVE=1` 且栈没起 → 要求全绿 → 退 1。这是**更严的失败**而非假绿，
      可接受；但输出必须逐字标明判定模式，否则会被误读成实现回归。
      **两种模式都要打印模式行**（独立评审的 nit，采纳）——只在 live 打，日志就答不出「这条绿是谁判的」。
      - Skill: `none`
- [x] `Decision | Add` **给 roadmap 新增工作项 9**。
      mission 规则逐字：「**一个工作项 = 1–2 个 plan。** 超过两个说明工作项拆得不够细，回来改这张表。」
      工作项 8 已有两个 plan，本批两个若挂在 8 下就是第三、第四个。
      **候选 (a) 挂在 8 下并记一次规则偏离**；**候选 (b) 新增工作项 9**。**推荐 (b)**——规则自己指名的处置
      就是「回来改这张表」，且两个结果面（判定设施 / CI 覆盖面）与「零依赖启动」不是同一件事。
      **落地形态**：`## Work Item Status` 块末尾追加
      `- 9. L2 门禁的判定与 CI 覆盖（把「只在本机验证过」补成 CI 可复跑）: <status>`，
      并在「工作项 → 门禁测试对照」表补一行。
      **关闭判据**：`gates.yml` 上存在一个 job，在 live 判定环境下用判定器对**全部 19 条**判定并 `success`。
      **⚠️ 必须同时记下的三件事（独立评审指出，采纳）**：
      · **工作项 9 没有属于自己的门禁测试。** mission 规则「判据先行：任何工作项开工前，先确认它有绑定的门禁测试」
        对它**在字面上不可满足**——与**工作项 4 和 7** 同一情形（4 绑的是「提供 `live_site` fixture」，
        7 在人补齐 L1 门禁之前压根没有门禁）。**不引工作项 8 / WBS P0.7 作先例**：那两处**确实**绑着
        `test_zero_dep_boot.py` 的具体断言，不是同一情形。
      · 因此工作项 9 与 4/5/6/7/8 一样，**大概率长期停在 `planned`**；本 plan 只写到 `planned`。
      · 工作项 9 的关闭判据（CI 上判 19 条）**覆盖面包含**工作项 8 的 CI 判据（`test_zero_dep_boot.py` 三条）。
        两行必须各自写清这层包含关系，否则将来会被读成互相矛盾。
      **残余风险 / 消费方核对（按实测写，不按推测写）**：新增行会改动引擎读的动态状态块。
      实测消费方是 `roadmapAllDone()`（`tools/mission-driver/…/engine.js:690`，终局对账）与
      `monitor.js` 的 `overallProgress`；`.github/workflows/gates.yml` 的 `roadmap-parseable` job
      只 grep **另一个文件**（`implementation-roadmap.md`）。加一行 `planned` 使进度由 3/8 变 3/9，
      终局对账不受影响。「引擎取第一个 `todo`」是 roadmap 与 `draft-from-roadmap.md` 里的散文约定，
      **不是代码**——本行按代码事实写。
      - Skill: `none`
- [x] `Fix` **把判定方式节提升为 `## 14.4` 并改写**（它当前误挂在 `## 14.3` 首页文案那一节之下）。
      改写内容：live 判定契约是什么、为什么不加名单文件、判定器保护的现状与那段空窗期。
      **本阶段不写「CI 怎么用」**——那归第二个 plan，写早了是假陈述。
      - Skill: `none`

#### Phase 1 执行记录（2026-08-22）

**开工 sha**（`Proof` 第一项，后续所有红线自查以它为基线）：

```
$ git rev-parse HEAD
084c9c443cd7db6c3f9189addcad59edf0c191ff

$ git status --porcelain
?? docs/plans/p0-foundation/2026-08-22-0027-1-live-mode-gate-verdict.md
?? docs/plans/p0-foundation/2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md
```

（两个未跟踪文件就是本批两个 plan，与起草时记录的工作树状态一致。）

**`Decision` 一 —— live 判定契约取 (b)：不加名单文件，契约写死为「全部绿、零 red、零 skip」。**
选择理由只有两条，**不含**「(b) 严格更紧」那条已被证伪的理由：① 可推定 live 下 19 条应当全绿
（10 条有直接 live 绿证，9 条是纯 L1、不依赖 live 环境），(a) 落地后那份文件内容为空，与「全绿」同一个契约；
② (a) 要给新名单再配一条棘轮，那是 `.github/workflows/**` 的改动，本 plan 的 Non-Goals 排除。
**照实记**：把逃生口从一份有棘轮的文本文件挪进**无保护的代码**不是变紧，是**换了个位置**；
所以本 Decision 与下一项（补保护）**捆绑落地**，单独选 (b) 是净损失。
**残余风险**：将来出现「live 下也必须红」的门禁时，(b) 会把它变成硬阻塞，需要人改判定器。
**备选未选**：(a) 与改写前的 owner doc 措辞一致、扩展性好，但要多配一条棘轮，且本仓此刻一条 live 预期红都没有。
以上全部写进了 `docs/architecture/system-baseline.md` 新 `## 14.4` 的「判定契约」小节。

**`Fix | Add` —— 判定器的保护（加严）三件事，全部落地：**

- **①** `docs/context/ai-autonomy-policy.md` Protected Areas 表**新增一行**
  `tools/gates/check_expected_red.py`（**门禁判定器本体**）| `plan-first` |
  Required Evidence = 独立草案评审 + 独立关闭审计 + 「默认判定环境输出逐字节不变」的前后两次实跑 +
  判定器自身的变异验证。表下补了「为什么此前没有这一行」的说明（三层保护实测全部不覆盖判定器，
  而 `gates-l1` 跑的就是判定器本身，被改废会在 CI 上自证为绿）。
  表的引言句同步改准（此前写「第九条是…加严行」，而 `missions/*.json` 插在中间使编号对不上，
  现按行名指代，不用序号）。
- **②** 边界写在同一行内：**只覆盖 `check_expected_red.py`，不覆盖 `tools/gates/expected-red.txt`**，
  出处逐字引 `AGENTS.md` 红线 1 的「边界」句与本表第 2 行（`allowed（只能变短）`），
  **不是** STATE §2 11:20Z（那条讲的是名单里该写什么，不是谁可以改）。
- **③** 「CI 侧守卫」已指名交给 `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`，
  登记在本 plan `## Deferred But Adjudicated` 第一条，`Successor Required: yes`。
  核对（Exit Criteria 那条有区分度的 grep）：

```
$ grep -n 'verdict-tool-untouched' docs/plans/p0-foundation/2026-08-22-0027-2-*.md
278:- [ ] `Add` 在 `gates.yml` **末尾追加判定器守卫 job**（形如 `verdict-tool-untouched`），
301:        提交信息**不带** trailer → `verdict-tool-untouched` 必须 `failure`。
350:        守卫变异实证的 **experiment ①**（无 trailer 改判定器 → `verdict-tool-untouched` 必须 `failure`）
531:  **追加一个独立的守卫 job**（`verdict-tool-untouched`），两个新 job 都 append 在文件末尾。
540:  · **NB1**：`verdict-tool-untouched` 是一条**没有任何牙齿证据**的安全守卫——
590:  （限定 job 名 `verdict-tool-untouched`、限定 experiment ①、限定必需结论 `failure`），
653:### 两个守卫 job 逻辑近似重复（`gates-untouched` 与 `verdict-tool-untouched`）
```

  **只有第 278 行以 `- [ ] \`Add\`` 开头**（守卫执行项本身），且该项第 281–285 行逐字写着
  「**硬边界（前驱定的）：路径清单里不得出现 `tools/gates/expected-red.txt`**」并引了
  `AGENTS.md` 红线 1 边界句 + Protected Areas 第 2 行。**本条 Exit Criteria 成立。**
  空窗期（文档级加严已在、CI 守卫未上线）已写进 `## 14.4`，并采纳「自愿带
  `Gates-Change-Approved-By:` trailer」这条空窗期内唯一带牙齿的控制——Phase 2 那个改判定器的提交带它。

**`Decision` 二 —— 模式开关取 (a) 环境变量 `AGENERP_LIVE=1`。**
(b) `--live` 与「`sys.argv[1:]` 原样透传给 pytest」的语义打架；(c) 探测栈是隐式判定，
会让「栈碰巧起着」悄悄改变判定口径。(a) 与 `conftest.py` 的 `_require_live()` 是同一个开关，
两者不可能各判各的。**残余风险**：默认环境误设 `AGENERP_LIVE=1` 且栈没起 → 要求全绿 → 退 1，
这是更严的失败而非假绿。**两种模式都打印模式行**（只在 live 打，日志答不出「这条绿是谁判的」）。

**`Decision | Add` 三 —— roadmap 新增工作项 9（取候选 (b)）。**
规则「一个工作项 = 1–2 个 plan…超过两个说明工作项拆得不够细，回来改这张表」自己指名的处置就是改表；
且判定设施 / CI 覆盖面与「零依赖启动」不是同一件事。落地形态：
`## Work Item Status` 末尾追加 `- 9. L2 门禁的判定与 CI 覆盖（把「只在本机验证过」补成 CI 可复跑）: \`planned\``，
「工作项 → 门禁测试对照」表补一行。同时写明三件事：
· 工作项 9 **没有属于自己的门禁测试**，「判据先行」对它字面不可满足，同情形是**工作项 4 与 7**
  （**不引** 8 / WBS P0.7 —— 那两处确实绑着 `test_zero_dep_boot.py` 的具体断言）；
· 因此它与 4/5/6/7/8 一样大概率长期停在 `planned`，本 plan 只写到 `planned`；
· 工作项 9 的关闭判据（CI 上判 19 条）**覆盖面包含**工作项 8 的 CI 判据，两行各自写清了这层包含关系。
**消费方核对（按代码事实，不按散文）**：`roadmapAllDone()`（`tools/mission-driver/…/engine.js:690`）
与 `monitor.js` 的 `overallProgress` 是实际消费方，`gates.yml` 的 `roadmap-parseable` job 只 grep
`implementation-roadmap.md`（另一个文件）。加一行 `planned` 使进度由 3/8 变 3/9，终局对账不受影响。

**`Fix` —— 判定方式节提升为 `## 14.4` 并改写。**
`docs/architecture/system-baseline.md` 原第 381–393 行那个不带编号的 `###` 误挂在 `## 14.3` 之下，
现提升为独立的 `## 14.4 门禁判定器的两种判定模式，与判定器自身的保护现状`，内容为：
两个判定环境的矛盾、live 判定契约与偏离 owner doc 建议的记录、判定器保护现状与空窗期、
以及原节那条「L2 在 CI 上不受棘轮保护」的残余风险（原样保留）。
**本节不写「CI 怎么用」**——归 successor。核对：`grep -n '^## 14' docs/architecture/system-baseline.md`
→ `131 / 178 / 208 / 286 / 383`，`## 14.4` 在第 383 行。

**Phase 1 收尾复跑**（文档改动，判定器与 `tests/unit` 应逐字不变）：

```
$ python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q
门禁 19 项：预期红 7，绿 12，跳过 0
✅ 与预期红名单完全一致
193 passed in 0.52s
$ echo $?
0
```


Exit Criteria:

- [x] 开工 sha 已记录
- [x] 三个 `Decision` 各自写下选择、备选与残余风险；`Decision` 一**不含**「(b) 严格更紧」这类已被证伪的理由
- [x] `ai-autonomy-policy.md` Protected Areas 多出判定器那一行，且边界（不含 txt）写明，
      出处引的是 `AGENTS.md` 红线 1 边界句与该表第 2 行（**不是** STATE §2 11:20Z）
- [x] 「CI 侧守卫」已在本 plan Deferred 里指名 successor，**且 successor 文件里确实有承接它的执行项**——
      **判据必须用有区分度的 token**（第三轮独立评审 BLOCKING-A：原写法 grep 的是
      `check_expected_red.py`，而 successor 里有 10 处命中，其中三处是与守卫无关的普通验证步骤
      —— 守卫项被删掉这条 grep 照样命中，抓不到它该抓的那件事）：
      `grep -n 'verdict-tool-untouched' docs/plans/p0-foundation/2026-08-22-0027-2-*.md`
      必须至少有一处命中落在形如 `- [ ] \`Add\`` 的**执行项行**上，
      且该执行项写明了「不覆盖 `expected-red.txt`」的边界。
      **起草时已核**：successor 的 Phase 2 第 2 项是一个新增守卫 job（形如 `verdict-tool-untouched`），
      硬边界逐字写着不得含 `expected-red.txt`。**若 successor 在评审中被改掉了这一项，本项不成立**，
      回来按 Deferred 里那条「空窗期终止条件」升级进 STATE §3
- [x] roadmap 多出工作项 9，「无绑定门禁 → 判据先行不可满足」与「与工作项 8 的包含关系」两点写明
- [x] `system-baseline.md` 出现 `## 14.4`，内容为判定契约口径，且**没有**提前描述 CI 行为
- [x] `docs/logs/` 更新

### Phase 2 — 实现 + 单测（默认行为逐字节不变，由判据钉住）

Status: completed
Targets: `tools/gates/check_expected_red.py` · `tests/unit/test_gate_verdict.py`（新建）
Skill: `none`

- Item Types: `Add | Proof`
- Prereqs: Phase 1 完成

- [x] `Add` **把三态分类与判定逻辑抽成纯函数**。接口边界（结构性定义，按 Minimum Rule 6 写进 plan）：
      · `classify(junit_xml_text) -> dict[nodeid, "red"|"green"|"skipped"]` —— 只吃 junit 文本，不碰进程；
      · `verdict(outcomes, expected_red, live: bool) -> (exit_code, list[str])` —— 只吃分类结果与名单；
        **`live=True` 时 `expected_red` 参数不被读取**。
      `main()` 退化成「组装 + 打印」。**不改** `healed_env()`、pytest 调用参数、junit 文件名。
      - Skill: `none`
- [x] `Add` **live 模式实现**：`AGENERP_LIVE=1` 时走 `verdict(..., live=True)`，判据为「零 red、零 skipped」，
      且**不调** `load_allowlist()`（免得名单缺失时在 live 模式误退 2）。
      **两种模式都打印模式行**，形如
      `判定模式：live（AGENERP_LIVE=1）—— 契约为全部门禁绿、零 skip，不读预期红名单` /
      `判定模式：default —— 按 tools/gates/expected-red.txt 判定`。
      **「逐字节不变」的契约收窄到判定行本身**（`门禁 N 项：…` 与四条判据的输出），
      模式行是新增的一行，不算违约——这一点必须写进 Phase 2 的实跑对照里，免得对照时自相矛盾。
      - Skill: `none`
- [x] `Proof` **单测钉住两模式共八态**（`tests/unit/test_gate_verdict.py`，新建）。
      默认模式：名单内红 → 0 / 名单外红 → 1 / 名单内绿 → 1 / 出现 skip → 1。
      live 模式：全绿 → 0 / 任意一条红 → 1 / 任意一条 skip → 1 / 名单内那条绿了 → 0（不再报错）。
      输入用**手写的 junit XML 片段**，不起 pytest 子进程。
      - Skill: `none`
- [x] `Proof` **默认判定环境前后逐字对照**：`python3 tools/gates/check_expected_red.py` →
      期望 **exit 0**，判定行仍为 `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`
      （多出的模式行按上一项的收窄口径不计）。**判定行有一个字不同就算行为改变，回来改实现。**
      再跑 `python3 -m pytest tests/unit -q` 与 `ruff check agenerp tests/unit tests/contracts`，退出码抄进 plan。
      - Skill: `none`
- [x] `Proof` **`GATE_VERIFY` 那条命令的端到端实跑 + 负向对照**（独立评审 B6，采纳）。
      跑 mission 里那条**字面命令**：
      `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → 期望 exit 0。
      **负向对照**：临时把 `agenerp/pack.py` 的 `normalize` 改成恒等返回
      （`test_normalizer_idempotent.py` 三条不在名单内，会变成「名单外的门禁红了」）→
      期望该组合命令 **exit 1** 且判定器逐字点名那几条；**复原并复跑确认回到 exit 0**。
      两次退出码与输出都抄进 plan。⚠️ 变异只许改 `agenerp/**`，不得触碰 `tests/gates/**`（红线 1）。
      - Skill: `none`
- [x] `Proof` **循环联动冒烟**：`bash tools/gates/smoke-loop-wiring.sh` → 期望 exit 0。
      **理由更正（独立评审 B6）**：该脚本把 `commands.test` 写成 `true` / `exit 1`，
      **它从不调用判定器**，所以它证明不了「判定器改动后 `GATE_VERIFY` 仍然接着」。
      跑它的真实理由只有一个：**回归守卫**——确认本 plan 没有把循环联动碰坏。
      「判定器仍然接着」由上一项的端到端实跑 + 负向对照负责，不由这一项负责。
      - Skill: `none`

#### Phase 2 执行记录（2026-08-22）

**纯函数接缝落地**（`tools/gates/check_expected_red.py`）：

- `classify(junit_xml: str) -> dict[nodeid, "red"|"green"|"skipped"]` —— 只吃 junit **文本**，不碰进程。
  `run_pytest()` 相应改为返回 junit 文本（`ET.parse(路径)` → `ET.fromstring(文本)`）。
- `verdict(outcomes, expected_red, live) -> (exit_code, lines)` —— 只吃分类结果与名单，
  不读文件、不起子进程、不打印；**`live=True` 时 `expected_red` 一次都不被读取**
  （判据 `test_live_ignores_the_allowlist_entirely`：连一份根本对不上的名单也不影响 live 判定）。
- `main()` 退化成「组装 + 打印」：选模式 → 打印模式行 → `load_allowlist()`（live 下跳过）→
  `classify(run_pytest(sys.argv[1:]))` → `verdict(...)` → 逐行打印 → 返回退出码。
- **未改**：`healed_env()`、pytest 调用参数（含 `sys.argv[1:]` 透传，所以 `--ignore=` 仍原样到达 pytest）、
  junit 文件名 `.pytest-gates.xml`。

**live 模式**：`AGENERP_LIVE=1` 选中（`os.environ.get("AGENERP_LIVE") == "1"`，
与 `tests/gates/conftest.py` 的 `_require_live()` 的 `!= "1"` **逐字互补**，两者不可能各判各的）；
判据为「零 red、零 skipped」；**不调 `load_allowlist()`**（免得名单缺失时在 live 模式误退 2）。
两种模式都打印模式行：
`判定模式：live（AGENERP_LIVE=1）—— 契约为全部门禁绿、零 skip，不读预期红名单` /
`判定模式：default —— 按 tools/gates/expected-red.txt 判定`。
**「逐字节不变」的契约收窄到判定行本身**（`门禁 N 项：…` 与四条判据的输出）；
模式行是新增的一行，按 Phase 2 第 2 项定的口径**不计**，下面的前后对照按这个口径读。

**单测**（`tests/unit/test_gate_verdict.py`，新建，12 条，输入全是手写 junit XML 片段，不起 pytest 子进程）：
`classify` 两条（三态映射 + nodeid 重建；`<error>` 也算 red）·
default 四态（名单内红 → 0 / 名单外红 → 1 / 名单内绿 → 1 / **出现 skip → 1**）·
live 四态（全绿 → 0 / 任意一条红 → 1 / **任意一条 skip → 1** / 名单内那条绿了 → 0）·
两条接缝性质（live 忽略名单、空输入下两模式都退 0）。

**默认判定环境前后逐字对照**（判定行）：

| | 开工前（`084c9c4`，`docs/logs/2026/08-22.md` 与 Phase 1 收尾复跑） | 本阶段实现之后 |
|---|---|---|
| 判定行 1 | `门禁 19 项：预期红 7，绿 12，跳过 0` | `门禁 19 项：预期红 7，绿 12，跳过 0` |
| 判定行 2 | `✅ 与预期红名单完全一致` | `✅ 与预期红名单完全一致` |
| 退出码 | 0 | 0 |
| 新增 | —— | `判定模式：default —— 按 tools/gates/expected-red.txt 判定`（模式行，按上面的口径不计） |

```
$ python3 tools/gates/check_expected_red.py
判定模式：default —— 按 tools/gates/expected-red.txt 判定
门禁 19 项：预期红 7，绿 12，跳过 0
✅ 与预期红名单完全一致
$ echo $?
0

$ ruff check agenerp tests/unit tests/contracts
All checks passed!
$ echo $?
0
```

**`GATE_VERIFY` 字面命令的端到端实跑 —— 正向**：

```
$ python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q
判定模式：default —— 按 tools/gates/expected-red.txt 判定
门禁 19 项：预期红 7，绿 12，跳过 0
✅ 与预期红名单完全一致
205 passed in 0.55s
$ echo $?
0
```

（`193 passed` → `205 passed`：新增的 12 条就是本阶段那份单测。）

**负向对照（变异窗口一，`agenerp/pack.py` 的 `normalize` 改成恒等返回）**：

```
$ python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q
判定模式：default —— 按 tools/gates/expected-red.txt 判定
门禁 19 项：预期红 10，绿 9，跳过 0

❌ 名单外的门禁红了（真的坏了）：
   tests/gates/test_normalizer_idempotent.py::test_normalize_is_stable_across_reexport
   tests/gates/test_normalizer_idempotent.py::test_normalize_orders_deterministically
   tests/gates/test_normalizer_idempotent.py::test_normalize_strips_volatile_fields
$ echo $?
1
```

判定器**逐字点名**了那三条，且组合命令在判定器这一段就短路（`&&` 右边没跑）。**变异只改了 `agenerp/pack.py`，
`tests/gates/**` 一个字节没碰。**

**复原并复跑确认回到基线**：

```
$ git checkout -- agenerp/pack.py
$ python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q
判定模式：default —— 按 tools/gates/expected-red.txt 判定
门禁 19 项：预期红 7，绿 12，跳过 0
✅ 与预期红名单完全一致
205 passed in 0.51s
$ echo $?
0

$ git diff --stat 084c9c4..HEAD -- agenerp/pack.py     # 输出为空
$ git status --porcelain -- agenerp/pack.py            # 输出为空
```

**循环联动冒烟（回归守卫，不是「证明判定器接着」）**：

```
$ bash tools/gates/smoke-loop-wiring.sh
A · commands.test 通过 → GATE_VERIFY pass
  ✓ 引擎退出码 0
  ✓ GATE_VERIFY 判 pass
B · commands.test 退非 0 → GATE_VERIFY fail → retry EXECUTE
  ✓ GATE_VERIFY 判 fail
  ✓ 失败后回到 EXECUTE 重试
C · 改动 tests/gates/** → 停机
  ✓ 引擎退出码 2（停机）
  ✓ 落下停机记录
  ✓ 记录写明触发条件
  ✓ 停机记录还在时拒绝启动（退 2）
  ✓ 人处置后可重启（退 0）
----
✅ 循环联动三条链全通
$ echo $?
0
```

该脚本把 `commands.test` 写成 `true` / `exit 1`，**它从不调用判定器**——跑它的理由只有一个：
确认本阶段没有把循环联动碰坏。「判定器仍然接着」由上面那条端到端实跑 + 负向对照负责。

**实现未偏离 Phase 1 的 `Decision`**（`AGENERP_LIVE=1` 开关 · 契约写死为全绿 · 不读名单 · 两种模式都打印模式行），
因此 `## 14.4` 无需再改。

**本阶段那个改判定器的提交自愿带 `Gates-Change-Approved-By:` trailer**（Phase 1 第三项定的
空窗期内唯一带牙齿的控制）：它不是本仓要求的（判定器不在任何 job 的路径清单里），
但让这次改动在 `git log` 里可被检索。


Exit Criteria:

- [x] 纯函数接缝落地，`main()` 不再内联分类逻辑
- [x] live 模式可用；两种模式都打印模式行
- [x] 新单测覆盖两模式共八态，其中 skip 态两条
- [x] 默认环境**判定行**与开工前逐字一致（两次实跑输出都抄进 plan）
- [x] `GATE_VERIFY` 字面命令的正向（exit 0）与负向（变异后 exit 1、复原后回 exit 0）各有实测输出，
      且 `agenerp/pack.py` 已复原 —— **用开工 sha，不用裸 `git diff`**（本 plan 第 174 行自己定的规矩）：
      `git diff --stat <开工 sha>..HEAD -- agenerp/pack.py` **与** `git status --porcelain -- agenerp/pack.py`
      两条都为空
- [x] `smoke-loop-wiring.sh` exit 0，且 plan 里写的是「回归守卫」而非「证明判定器接着」
- [x] 判定方式节（`## 14.4`）无需再改；若实现偏离 Phase 1 的 `Decision`，回去改它再收尾

### Phase 3 — live 实测、三条变异验证与收尾

Status: completed
Targets: `docs/context/project-context.md` · `docs/logs/2026/08-22.md` ·
  `docs/masterplan/STATE.md`（**只追加**）· `docs/backlog/p0-foundation-roadmap.md`
Skill: `none`

- Item Types: `Proof | Fix`
- Prereqs: Phase 2 完成

- [x] `Proof` **19 条一次跑完的 live 实测**（本仓第一次查这个未知数）。先起栈，再跑 Infrastructure 那条命令，
      **退出码与完整输出逐字抄进 plan**。三种结局的处置事先写死：
      · **exit 0** —— live 判定环境的首个整目录绿证。
      · **exit 1 且红因是门禁之间互相干扰** —— **这是本 plan 的重要发现，不是失败**。
        逐字记进 plan / log / STATE §2，把「整目录 live 判定不可用」作为**阻塞第二个 plan 的事实**交出去。
        **此时本 plan 仍可关闭，但必须先满足下一项的正向对照**（否则 live 模式从未被证明能返回 0）。
        **绝不用 `-p no:randomly`、`-x`、收窄目录之类的手段把它糊过去**——那等于换个方式放松裁判。
      · **exit 2** —— 判定器自己跑挂了，属 Phase 2 的实现缺陷，回 Phase 2。
      **⚠️ 本项必须携带 Protected Areas 末行要求的证据（独立评审 BLOCKING-1，采纳）**：
      这一跑是 `agenerp/apply.py` 的**真删除路径**第一次与另外 18 条门禁一起对活站点执行，
      正是那条 `plan-first` 规则写给的场景。因此本项要在**跑之前与跑之后**各做一次
      全量 `capture("doctypes")` 并记下差集，**差集只允许含本次门禁自己的探针**
      （`agenerp_gate_probe` / `agenerp_gate_roundtrip`）。
      **调用方式说明**：`agenerp.snapshot.capture` **没有 CLI**（实测 `agenerp/` 下无 `__main__` / `argparse`），
      plan `1922-3` 当时是用一次性脚本做的——本 plan 照做，**该脚本不提交**，
      但它的原文与两次输出要抄进 plan。
      - Skill: `none`
- [x] `Proof` **正向对照：live 模式必须被证明能返回 exit 0**（独立评审 B3，采纳）。
      · 上一项若是 **exit 0**，本项由它满足，写一行「由上一项满足」即可。
      · 上一项若是 **exit 1**，必须补一次**收窄范围的正向对照**：用
        `python3 tools/gates/check_expected_red.py --ignore=<文件1> [--ignore=<文件2> …]` 在 live 环境下跑，
        期望 **exit 0**，并把**每一个**被排除的文件名与理由逐字记下（干扰发生在两个都动 `Item` 的文件之间，
        排掉一个未必够，允许多条 `--ignore`）。
        **`--ignore` 的可行性已在起草期由独立评审实测**：判定器把 `sys.argv[1:]` 追加在 `--junitxml` 之后，
        `--ignore=` 原样到达 pytest，被排除的 nodeid 直接不出现在 `outcomes` 里（实测
        `--ignore=tests/gates/test_seed_dataset_absurdity.py` → `门禁 13 项`，exit 0）。
        **这是诊断用的一次性对照，不是新的判定跑法**，绝不写进 `project-context.md` 当作可用命令。
        **拿不到 exit 0 就不许关闭本 plan**——live 模式没有正向证据 = 交付物未证明可用。
      - Skill: `none`
- [x] `Proof` **变异 ①：live 模式对真实现回归有牙齿。**
      临时把 `agenerp/apply.py` 的删除路径改成 no-op（plan `1922-3` 实测过该变异会让
      `::test_removing_from_pack_actually_deletes_on_site` 逐字转红），跑 live 判定。
      **判据不是「退出码变了」而是「点名的 nodeid 集合变了」**（独立评审 B3）：
      记录变异前与变异后判定器**逐字点名的 nodeid 集合**，两者之差必须**恰好**是
      `::test_removing_from_pack_actually_deletes_on_site` 这一条。
      **`git checkout -- agenerp/apply.py` 复原并复跑确认回到基线**，退出码与点名集合都抄进 plan。
      **Protected Areas 合规（独立评审 B8 → BLOCKING-1，按第二轮意见重新安放）**：
      `ai-autonomy-policy.md` 末行把 `agenerp/apply.py` 的删除路径列为 `plan-first`，
      Required Evidence 含「实跑前后全量 `capture` 对照」。
      **变异期间那一跑不需要这条证据，且给它加也是假证据**——变异把删除改成 no-op，
      no-op 删不掉任何东西，前后 `capture` 差集**按构造必然为空**，证明不了任何事。
      **真正需要这条证据的是两处**：① Phase 3 第一项那次整目录实跑（真删除路径跑了）；
      ② **本项复原之后的那次复跑**（真删除路径又跑了一次）。②的对照结果抄进本项。
      同时在 plan 里写明「本项不发布任何行为改变（变异已复原）」。
      ⚠️ 变异只许改 `agenerp/**`，不得触碰 `tests/gates/**`（红线 1）。
      - Skill: `none`
- [x] `Proof` **变异 ②：判定器的 skip 分支真的在起作用**（独立评审 B4，采纳——旧写法只是复述 Phase 2 的单测，
      不含变异、不可能失败）。**变异对象是判定器自己**：把 `verdict()` 里的 `skipped` 分支删掉（或反转），
      跑 `python3 -m pytest tests/unit -q` → 期望 **exit 1 且逐字点名那两条 skip 单测**；
      复原后复跑 → 期望 exit 0。两次退出码与被点名的测试名都抄进 plan。
      **这同时是 Phase 1 新增那条 Protected Areas 行所要求的「判定器自身的变异验证」**，两处引同一份证据。
      - Skill: `none`
- [x] `Fix` **改准 `project-context.md` 第 56 行（及第 57 行同措辞处）的确认漂移**：
      「`tests/gates/conftest.py` 全文不设这个变量」是错的（`conftest.py:274` 在 `live_site` 内会设它），
      正确说法是「`test_snapshot_diff_structured.py` 那两条不取任何 fixture、直接调 `capture()`，
      走不到那行，所以必须由命令给」。**Minimum Rule 14：确认的 owner-doc 漂移不得降级成 follow-up。**
      - Skill: `none`
- [x] `Fix` **给 `project-context.md` 验证命令表新增一行「L2 live 门禁（整目录判定）」**，
      写清命令、三处口径、以及 Phase 3 实测到的退出码。**现有三行照留**（按文件定位红因时仍是正确工具）。
      ⚠️ 若整目录实测是 exit 1，新增行必须**如实写它红在哪**，不得只收录绿的那部分，
      也**不得**把上一项那条 `--ignore` 诊断命令写进表里。
      - Skill: `none`
- [x] `Fix` **roadmap 「9 现状」行**：本 plan 关闭时工作项 9 停在 `planned`（关闭判据是「CI 上跑绿」，
      本 plan 不碰 CI）。行内写明本 plan 交付了什么、live 整目录实测退出码、仍未做的那半（CI 消费面 + CI 侧守卫）。
      - Skill: `none`
- [x] `Proof` **收尾复跑与红线自查（用开工 sha 作基线，不用裸 `git diff`）**：
      · `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → 期望 exit 0；
      · `git diff --stat <开工 sha>..HEAD -- tests/gates .github/workflows docs/masterplan missions tools/gates/expected-red.txt`
        → 期望**只列出 `docs/masterplan/STATE.md` 一行**（本 plan 只往 §2 追加），其余路径零命中；
      · `git status --porcelain -- tests/gates .github/workflows docs/masterplan missions tools/gates/expected-red.txt`
        → 期望**输出为空**（与上一条一起才覆盖「已提交」与「未提交」两种情形。
        **口径按第二轮独立评审 BLOCKING-3 扩过**：原写法只列 `DECISIONS.md`，
        而红线 5 覆盖**整个** `docs/masterplan/`；且 `expected-red.txt` 原来只有 `--diff` 一条，
        未提交的改动会从两条命令之间溜走）；
      · **STATE 的「只追加」要有可执行判据**：
        `git diff --numstat <开工 sha>..HEAD -- docs/masterplan/STATE.md` →
        期望输出形如 **`N	0`**（新增 N 行、删除 0 行；`--numstat` 在文件完全未被触碰时**什么都不打印**，
        那种情形也算通过）。这才是「只追加」的可执行形态，此前它一直只是口头约定。
        **为什么 deletions=0 就等于只追加**：git 把「就地改一行」记成 1 增 1 删、把「移动一行」也记成 1 增 1 删，
        所以 deletions 只要为 0，就没有任何既有行被改写或删除。
      · `git diff --numstat <开工 sha>..HEAD -- tools/gates/expected-red.txt` → 期望**输出为空**。
      五条命令原文、退出码与 commit sha 一并写进 log 与 STATE §2（**只追加**）。
      **⚠️ 执行顺序**：这五条要在**写完 STATE §2 并提交之后**跑——本 plan 合法地会改 `docs/masterplan/STATE.md`，
      在提交之前跑第二条会拿到一个**伪失败**，那时千万别去放松判据，先提交再跑。
      **这条 append-only 判据不是仪式**：实测本仓真实历史 `git diff --numstat bd32959^..bd32959 -- docs/masterplan/STATE.md`
      → **`1	1`**——那次提交确实就地改写了 STATE 的一行。这条判据当时会咬。
      - Skill: `none`

#### Phase 3 执行记录（2026-08-22）

**起栈**：`AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`
→ **exit 0**（六个服务 Healthy，`configurator` / `create-site` / `bootstrap-homepage` 三个一次性服务 Exited）。
本机 Docker 29.2.1 / Compose v5.0.2。

**`capture` 的调用方式**：`agenerp.snapshot.capture` **没有 CLI**（`agenerp/` 下无 `__main__` / `argparse`），
按 plan `1922-3` 的先例用一次性脚本，**该脚本不提交**（写在 `/tmp/agenerp_capture.py`）。原文：

```python
# 一次性诊断脚本（不提交）：全量 capture("doctypes") 快照 → JSON 到 stdout。
import json
import sys

sys.path.insert(0, "/Users/lize/Claude/Projects/AgenERP")
from agenerp.snapshot import capture

snap = capture("doctypes")
print(json.dumps(
    sorted([e.doctype, e.fieldname] for e in snap.entries),
    ensure_ascii=False, indent=1,
))
```

---

##### 第一项 · 19 条一次跑完的 live 实测 —— **结局是「exit 1 一次，exit 0 五次，且那一次不可复现」**

**跑前全量 `capture("doctypes")`**（10 条，全是应用自带字段，无探针）：

```
[["Address","is_your_company_address"],["Address","tax_category"],["Communication","company"],
 ["Contact","is_billing_contact"],["Customer","crm_deal"],["Email Account","company"],
 ["Print Settings","compact_item_print"],["Print Settings","print_taxes_with_zero_amount"],
 ["Print Settings","print_uom_after_quantity"],["Quotation","crm_deal"]]
```

**第 1 跑**（Infrastructure 那条字面命令）：

```
$ AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend \
  AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin \
  python3 tools/gates/check_expected_red.py
判定模式：live（AGENERP_LIVE=1）—— 契约为全部门禁绿、零 skip，不读预期红名单
门禁 19 项：红 1，绿 18，跳过 0

❌ live 判定契约是全部门禁绿，下列门禁红了：
   tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind
$ echo $?
1
```

**跑后全量 `capture("doctypes")` 与差集**（Protected Areas 末行要求的证据——这一跑里
`agenerp/apply.py` 的**真删除路径**第一次与另外 18 条门禁一起对活站点执行）：

```
before: 10 after: 10
added  : []
removed: []
```

**差集为空**，连本次门禁自己的探针（`agenerp_gate_probe` / `agenerp_gate_roundtrip`）都没剩下——
门禁自己清干净了，比「只允许含本次探针」这条判据更严，通过。

**按 `AGENTS.md` 裁判规则 3「复跑优先于分析」，原样复跑**（同一条命令，一字未改）：

```
第 2 跑：门禁 19 项：红 0，绿 19，跳过 0 / ✅ live 判定：全部门禁绿，零 red、零 skip  → exit 0
第 3 跑：门禁 19 项：红 0，绿 19，跳过 0 / ✅ live 判定：全部门禁绿，零 red、零 skip  → exit 0
第 4 跑：门禁 19 项：红 0，绿 19，跳过 0 / ✅ live 判定：全部门禁绿，零 red、零 skip  → exit 0
第 5 跑：门禁 19 项：红 0，绿 19，跳过 0 / ✅ live 判定：全部门禁绿，零 red、零 skip  → exit 0
```

**处置（照实写，不套 plan 事先写死的三种结局中的任何一种）**：
plan 起草时写死的三个分支是 exit 0 / exit 1 且红因是门禁互相干扰 / exit 2。
实测落在**第四种**：exit 1 一次、原样复跑四次全绿。
**这一跑的红因「不可复现」，按裁判规则 3 不猜根因**——
不写「是门禁互相干扰」（没有证据），也不写「是环境抖动」（同样没有证据）。
**绝没有用 `-p no:randomly` / `-x` / 收窄目录之类的手段把它糊过去**：五跑用的是同一条字面命令。

**这条不可复现的红是本 plan 交出去的一条实测事实，不是被藏起来的失败**：
它意味着 `test_no_orphan_column_left_behind` 在整目录 live 判定下**是间歇性的**，
本批第二个 plan 要在 CI 上跑同一条命令，**必须知道这件事**——CI 上一次红就是一次红，没有人在旁边复跑。
已写进 `docs/context/project-context.md` 新增那行、roadmap 「9 现状」行、`docs/logs/2026/08-22.md` 与 STATE §2，
并在本 plan `## Deferred But Adjudicated` 新增一条 `watch-only residual` 登记它与重开事件。

**顺带被这一跑消掉的一个未知数**：那 9 条从未在 live 下跑过的门禁
（`test_normalizer_idempotent.py` 3 条 + `test_seed_dataset_absurdity.py` 6 条）
在 live 环境下**行为与默认环境一致**（六跑里没有一次点名过它们中的任何一条），
对应 Deferred「9 条从未在 live 环境下跑过的门禁」的重开事件**未触发**。

---

##### 第二项 · 正向对照：live 模式能返回 exit 0

**由上一项满足**——第 2/3/4/5 跑均为整目录 19 条全绿、**exit 0**，
所以**不需要**那条收窄范围的 `--ignore` 诊断对照，也没有跑它（因此没有任何 `--ignore` 命令进
`project-context.md`，符合第六项的禁令）。

---

##### 第三项 · 变异 ①：live 模式对真实现回归有牙齿

**变异**：`agenerp/apply.py` 的 `execute_plan` 删除路径第一行插入 `return`（改成 no-op），
只改 `agenerp/**`，**`tests/gates/` 下一个字节没碰**。

**判据是「点名的 nodeid 集合之差」，不是退出码**：

| | 判定器逐字点名的 nodeid 集合 | 退出码 |
|---|---|---|
| 变异前（第 5 跑，基线） | **∅**（`✅ live 判定：全部门禁绿，零 red、零 skip`） | 0 |
| 变异后 | `{tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site}` | 1 |
| **差** | **恰好一条**：`::test_removing_from_pack_actually_deletes_on_site` | |

变异后的完整输出：

```
判定模式：live（AGENERP_LIVE=1）—— 契约为全部门禁绿、零 skip，不读预期红名单
门禁 19 项：红 1，绿 18，跳过 0

❌ live 判定契约是全部门禁绿，下列门禁红了：
   tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site
```

**为什么变异期间那一跑不带 `capture` 对照**：变异把删除改成 no-op，no-op 删不掉任何东西，
前后差集**按构造必然为空**，加上去是假证据。真正需要那条证据的是复原之后的复跑（下面）。

**复原并复跑确认回到基线**（`git checkout -- agenerp/apply.py`）：

```
$ AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend \
  AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin \
  python3 tools/gates/check_expected_red.py
判定模式：live（AGENERP_LIVE=1）—— 契约为全部门禁绿、零 skip，不读预期红名单
门禁 19 项：红 0，绿 19，跳过 0
✅ live 判定：全部门禁绿，零 red、零 skip
$ echo $?
0
```

点名集合回到 **∅**，与基线一致。**这一跑的前后全量 `capture` 对照**（真删除路径又跑了一次）：

```
before: 10 after: 10
added  : []
removed: []
```

差集为空，通过。**本项不发布任何行为改变（变异已复原）。**

---

##### 第四项 · 变异 ②：判定器自己的 `skipped` 分支真的在起作用

**变异对象是判定器自己**（`tools/gates/check_expected_red.py` 的 `verdict()`）：
删掉 `if skipped:` 那个消息块，并把 `skipped` 从 live 与 default 两条失败条件里一并去掉
（只删消息块不删条件，退出码不会变，那样的变异证明不了任何事）。

```
$ python3 -m pytest tests/unit -q
...
FAILED tests/unit/test_gate_verdict.py::test_default_skip_fails_even_when_everything_else_matches
FAILED tests/unit/test_gate_verdict.py::test_live_any_skip_fails - assert 0 == 1
2 failed, 203 passed in 0.56s
$ echo $?
1
```

**逐字点名的就是那两条 skip 单测**（default 一条、live 一条），两条都断在 `assert code == 1` → `assert 0 == 1`。

**复原后复跑**（`git checkout -- tools/gates/check_expected_red.py`）：

```
$ python3 -m pytest tests/unit -q
205 passed in 0.48s
$ echo $?
0
$ git status --porcelain -- tools/gates/check_expected_red.py    # 输出为空
$ grep -n "skipped" tools/gates/check_expected_red.py
85:        elif tc.find("skipped") is not None:
86:            outcomes[nodeid] = "skipped"
97:    skipped = sorted(n for n, o in outcomes.items() if o == "skipped")
100:        lines = [f"门禁 {len(outcomes)} 项：红 {len(reds)}，绿 {len(greens)}，跳过 {len(skipped)}"]
103:                 f"绿 {len(greens)}，跳过 {len(skipped)}"]
105:    if skipped:
108:        lines += [f"   {n}" for n in skipped]
115:        if reds or skipped:
134:    if unexpected_red or unexpected_green or skipped:
```

第 105/115/134 三行就是被变异删掉又复原回来的那三处（消息块 + 两条失败条件）。
**这份证据同时满足 Phase 1 新增那条 Protected Areas 行所要求的「判定器自身的变异验证」**，两处引同一份。

---

##### 第五、六项 · `project-context.md` 两处改动

- **确认漂移已就地改准**（Minimum Rule 14，不降级成 follow-up）：验证命令表里「L2 live 门禁（快照）」
  那一行的 ② 此前写「`tests/gates/conftest.py` 全文不设这个变量」，**那是错的**——
  `conftest.py:274` 在 `live_site` fixture 内部会设它。已改写成更窄的正确说法：
  `test_snapshot_diff_structured.py` 那两条不取任何 fixture、直接调 `capture()`，走不到那行，所以必须由命令给。
  「定制包往返」那一行引用这三处口径时的措辞同步指向改准后的窄说法，免得两行读起来自相矛盾。
- **新增一行「L2 live 门禁（整目录判定）」**：命令、三处口径、六次实测的退出码全部写进去，
  **如实写了第一跑的 exit 1 与「不可复现」**，没有只收录绿的那部分；**没有**把 `--ignore` 写进表里
  （本次压根没跑它）。现有三行照留（按文件定位红因时仍是正确工具）。

##### 第七项 · roadmap 「9 现状」行

已补，工作项 9 停在 `planned`（关闭判据是「CI 上跑绿」，本 plan 不碰 CI）。
行内写明本 plan 交付了什么（live 判定模式 / 纯函数接缝 + 12 条单测 / Protected Areas 加严行）、
live 整目录实测的六次退出码与那次不可复现的红、以及仍未做的那半（CI 消费面 + CI 侧守卫 `verdict-tool-untouched`）。

##### 第八项 · 收尾复跑与红线自查

见本节末尾「收尾自查（STATE §2 提交之后跑）」小节——按 plan 自己定的执行顺序，
这五条必须在写完 STATE §2 并提交**之后**才跑，否则第二条会拿到一个伪失败。

##### 收尾自查（STATE §2 提交之后跑，`HEAD` = `ef01d12`）

**执行顺序说明**：这五条必须在写完 STATE §2 **并提交之后**才跑——本 plan 合法地会往
`docs/masterplan/STATE.md` 追加证据行，提交之前跑第二条会拿到一个**伪失败**，
那时不许去放松判据，先提交再跑。以下是提交之后的实测。

```
① $ python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q
判定模式：default —— 按 tools/gates/expected-red.txt 判定
门禁 19 项：预期红 7，绿 12，跳过 0
✅ 与预期红名单完全一致
205 passed in 0.46s
$ echo $?
0

② $ git diff --stat 084c9c4..HEAD -- tests/gates .github/workflows docs/masterplan missions tools/gates/expected-red.txt
 docs/masterplan/STATE.md | 18 ++++++++++++++++++
 1 file changed, 18 insertions(+)
   → 只列出 docs/masterplan/STATE.md 一行，其余四条路径零命中 ✅

③ $ git status --porcelain -- tests/gates .github/workflows docs/masterplan missions tools/gates/expected-red.txt
   （无输出）✅  —— 与 ② 一起才覆盖「已提交」与「未提交」两种情形

④ $ git diff --numstat 084c9c4..HEAD -- docs/masterplan/STATE.md
18	0
   → deletions = 0 ⇒ **只追加** ✅
   为什么 deletions=0 就等于只追加：git 把「就地改一行」记成 1 增 1 删、把「移动一行」也记成 1 增 1 删，
   所以 deletions 只要为 0，就没有任何既有行被改写或删除。
   **这条判据不是仪式**：`git diff --numstat bd32959^..bd32959 -- docs/masterplan/STATE.md` → `1	1`，
   本仓真实历史上那次提交确实就地改写了 STATE 的一行，这条判据当时会咬。

⑤ $ git diff --numstat 084c9c4..HEAD -- tools/gates/expected-red.txt
   （无输出）✅  —— 名单一行未动
```

**三处变异窗口的复原判据（按路径分开写，一律用开工 sha，不用裸 `git diff`）**：

```
$ git diff --stat 084c9c4..HEAD -- agenerp      # 无输出 ✅（Non-Goals 禁止任何净改动）
$ git status --porcelain -- agenerp             # 无输出 ✅
$ git status --porcelain -- tools/gates/check_expected_red.py   # 无输出 ✅
$ git diff 084c9c4..HEAD -- tools/gates/check_expected_red.py | grep -n skipped
51:             outcomes[nodeid] = "skipped"
69:     skipped = sorted(n for n, o in outcomes.items() if o == "skipped")
79:     if skipped:
85:+        lines += [f"   {n}" for n in skipped]
92:+        if reds or skipped:
117:     if unexpected_red or unexpected_green or skipped:
```

判定器的 diff 里 `if skipped:`（第 79 行，**上下文行、无前缀**）与两条失败条件
（第 92 行 live 侧新增、第 117 行 default 侧**上下文行、无前缀**）**都在**——
**变异 ② 已复原**。这一条要人读 diff，不能只看退出码：判定器 **Phase 2 本来就要改**，
对它写「diff 为空」本身就是错的。

**文本一致性**：`grep -B5 '^- \[ \]' <plan> | grep -c 'Status: completed'` → **0**
（没有任何 `Status: completed` 的 Phase 还留着未勾项）；
全文剩余 14 个未勾项**全部落在 `## Closure Gates`**，按本 plan「`Plan Status` 由谁写」一节的归属，
EXECUTE 阶段不勾它们、`Plan Status` 保持 `active`，由独立关闭审计置位。



Exit Criteria:

- [x] live 整目录判定已实跑，退出码与完整输出逐字在 plan 与 log 里
- [x] **live 模式已被证明能返回 exit 0**（整目录绿，或收窄范围的正向对照绿）
- [x] 变异 ① 有「点名 nodeid 集合之差恰好为一条」的证据，且附变异前后全量 `capture` 差集
- [x] 变异 ② 是对判定器自身的变异，有「红 → 复原 → 绿」两次退出码
- [x] Phase 3 的两处变异（变异 ① / 变异 ②）均已复原并复跑确认；Phase 2 的负向对照变异由该阶段自己的 Exit Criteria 覆盖
- [x] `project-context.md` 第 56/57 行的漂移已就地改准，且多出整目录判定那一行
- [x] roadmap 有「9 现状」行，工作项 9 停在 `planned`
- [x] 红线自查五条命令输出为期望值
- [x] `docs/logs/2026/08-22.md` 与 STATE §2 各有对应记录（STATE 只追加）

## `Plan Status` 由谁写（写死，免得烧循环）

沿用 plan `2026-08-21-1022-2` / `2026-08-21-1553-1` 已确立的三种归属，不再论证：

- `REVIEW_PLANS`：评审收敛后 `draft` → `active`。
- `EXECUTE`（Phase 1–3）：只打勾执行项与 Exit Criteria，`Plan Status` **保持 `active`**，
  `## Closure Gates` 十四框**保持未勾**。
- `CLOSURE_AUDIT`：通过 → 勾框 + 置 `completed` + 补 `## Closure`；需改代码 → 保持 `active`；
  阻塞于人 → 置 `deferred` 并写明重开条件。

⚠️ `tools/mission-driver/prompts/execute.md` 第 4.a 条要求执行会话自置 `completed`，
与 `AGENTS.md` 裁判规则 1/2 冲突，按优先级次序**不执行**。该冲突已由 plan `2026-08-21-1553-1` 登记，不重复登记。

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，2026-08-22）。
  逐条复核了 `Current Baseline` 的每一条事实，确认 20 余条、**证伪 6 条**，并给出 **10 条 blocking**：
  · **B1** 引用的 `§14.4` **不存在**（`system-baseline.md` 393 行，最后一个编号节是 `## 14.3`，
    目标文本是它下面一个不带编号的 `###`，第 381–393 行）；全文引用了 11 次。
  · **B2** 改判定器的边界论证**自相矛盾**：一边说「没规则挡着所以可改」，一边用「只能由人改代码」当作
    `Decision` (b) 的安全性理由。实测判定器**三层皆无保护**（`gates-untouched` 只 diff `tests/gates/**`、
    `gate-verify.mjs:22` 的 `PROTECTED = ["tests/gates/"]`、`expected-red-ratchet` 只数 txt 行数），
    且 `gates-l1` 跑的就是判定器本身——改废后会自证为绿。该洞在本批两个 plan 里**无人认领**。
  · **B3** 变异 ① 在「整目录 exit 1」分支下**变成空转**（基线本就退 1），且全 plan 没有任何一步证明
    live 模式能返回 0。
  · **B4** 变异 ② 只是 Phase 2 单测的复述，不含变异、不可能失败。
  · **B5** 红线自查用裸 `git diff`，提交后恒为空，是不可能触发的假守卫。
  · **B6** `smoke-loop-wiring.sh` 把 `commands.test` 写成 `true` / `exit 1`，**从不调用判定器**，
    plan 给它写的理由不成立。
  · **B7** 工作项 9 的先例引错：工作项 8 与 WBS P0.7 **确实**绑着 `test_zero_dep_boot.py` 的断言，
    真正同情形的是**工作项 4 / 7**；且没说清「判据先行」对工作项 9 不可满足。
  · **B8** 受保护面自查表漏了 Phase 3 真的会碰的那一行——`agenerp/apply.py` 的删除路径是
    `plan-first` 且 Required Evidence 含「实跑前后全量 `capture` 对照」。
  · **B9** 「别再写第二个判定器」被误标成 `AGENTS.md`，实际出处是
    `docs/backlog/p0-foundation-roadmap.md:75`（强度低一档）。
  · **B10** plan 自己查出 `project-context.md:56` 的措辞是错的，却又写「三行照留…口径不变」，
    与 Minimum Rule 14 冲突。
  另有 8 条 nit（`_require_live` 在 53 行非 54、注释里只有一个 sha、起草时工作树有两个未跟踪文件、
  「19 条按文件分开跑全绿」实际只有 10 条跑过 live、「引擎取第一个 todo」不是代码而是散文
  （代码消费方是 `engine.js:690` 的 `roadmapAllDone()` 与 `monitor.js` 的 `overallProgress`，
  实测新增 bullet 可被 `BULLET_RE` 正确解析）、默认模式不打印模式行、
  工作项 9 与 8 的判据包含关系需写明、`Non-Goals` 里 `**…`.github/workflows/**`**` 的 markdown 星号相撞）。
- Revision after iteration 1（本次修订，逐条对应）：
  新增 `## 术语约定` 一节写死「判定方式节 = 第 381–393 行」并把 Phase 1 末项改为
  **提升为 `## 14.4` 并改写**（B1）；`Decision` 一删掉「(b) 严格更紧」这条被证伪的理由、
  改写为「换了个位置、必须与补保护捆绑」，并新增 Phase 1 第三项**给判定器补 Protected Areas 行 + 划定
  不含 txt 的边界 + 把 CI 侧守卫指名交给第二个 plan**（B2）；Phase 3 新增**正向对照**一项并把变异 ① 的
  判据从退出码改为**点名 nodeid 集合之差**（B3）；变异 ② 改为**对判定器自身的变异**（B4）；
  全部红线自查改为 `git diff <开工 sha>..HEAD` + `git status --porcelain` 两条并列，Phase 1 首项新增
  「记下开工 sha」（B5）；`smoke-loop-wiring.sh` 的理由改写为「回归守卫」并新增
  **`GATE_VERIFY` 字面命令的端到端实跑 + 负向对照**（B6）；工作项 9 的先例改引**工作项 4 / 7**、
  写明「判据先行不可满足」与「与工作项 8 的包含关系」（B7）；受保护面自查表补
  `agenerp/apply.py` 一行、变异 ① 补「前后全量 `capture` 对照」（B8）；
  三处出处改标 `roadmap:75` 并按 roadmap 级强度使用（B9）；
  Phase 3 新增一条 `Fix` 就地改准 `project-context.md` 第 56/57 行（B10）。
  八条 nit 全部就地采纳（行号、sha、工作树、10/19、引擎消费方按实测重写、两种模式都打印模式行、
  包含关系、markdown 星号）。
- Independent draft review iteration 2: **needs revision**（同一独立评审者，2026-08-22）。
  逐条判定 B1–B10：**B1 / B3 / B4 / B6 / B7 / B9 / B10 已解决**（并实测验证了两处关键可行性：
  `--ignore=` 确实原样到达 pytest —— `--ignore=tests/gates/test_seed_dataset_absurdity.py` → `门禁 13 项`、exit 0；
  以及把 `agenerp/pack.py` 的 `normalize` 改成恒等**确实**能让 `test_normalizer_idempotent.py` 三条全红，
  负向对照成立）；**B2 部分解决、B5 部分解决、B8 未解决（改名而已）**。新增 5 条 blocking：
  · **BLOCKING-1**（B8 的实质）：`capture` 对照被挂在**唯一不可能失败**的那一跑上——
    变异 ① 把删除改成 no-op，no-op 删不掉东西，前后差集按构造必为空；而真删除路径实际跑的两处
    （Phase 3 第一项的整目录实跑、变异 ① 复原后的复跑）**一条证据都没有**。
  · **BLOCKING-2**：交办给 successor 的守卫「无牙齿」——plan 不能靠断言给另一个 plan 加 scope，
    且本 plan 没有任何 Exit Criteria / Closure Gate 去核对 successor 是否真的接了。
  · **BLOCKING-3**：红线自查仍有两条逃逸路径——`expected-red.txt` 只有 `--diff` 没有 `status`
    （未提交的改动溜走）；路径清单只写 `DECISIONS.md` 而红线 5 覆盖**整个** `docs/masterplan/`，
    且「STATE 只追加」全程没有可执行判据。
  · **BLOCKING-4**（本次重写引入）：变异窗口实际有**三个**，回滚策略只列两个且用了一个不存在的标号「变异 ③」。
  · **BLOCKING-5**（与 B9 同一失效模式，出现在为修 B9 而写的新文本里）：
    「账本可划短」的出处被写成 STATE §2 11:20Z，而那条逐字讲的是**名单里该写什么**，不是谁能改；
    真正的出处是 `AGENTS.md` 红线 1 的「边界」句与 `ai-autonomy-policy.md` Protected Areas 第 2 行。
    边界本身**判定为正确**，错的只是引证。
  另有 7 条 nit（Protected Areas 是 **10** 行不是九行、Closure Gates 是 **12** 框不是十一、
  Goals 仍写「判定输出」而下文已收窄为「判定行」、交叉引用「Phase 3 第二项」实为第三项、
  `--ignore` 应允许多个、新增那条 Protected Areas 行对**本次**改动零增量约束应点明、空窗期缺终止条件）。
  评审同时确认：Anti-Slacking 清零违规，6 条 Deferred 全部带重开事件；
  并逐条复核了本次重写引入的全部新事实（`gate-verify.mjs:22`、`engine.js:690`、`roadmap:75`、
  `conftest.py:8/53/274`、393 行 / `## 14.3`@286 / `###`@381、10-of-19 的 live 覆盖切分）——**全部确认**。
- Revision after iteration 2（本次修订，逐条对应）：
  `capture` 对照从变异 ① **移到** Phase 3 第一项与变异 ① 的**复原后复跑**，并在变异 ① 处写明
  「no-op 删不掉东西，那里的证据按构造为空，是假证据」，同时补上「`capture` 没有 CLI、
  用一次性脚本、脚本不提交」的调用说明（BLOCKING-1）；
  新增一条**可 grep 核对**的 Exit Criteria 与一条 Closure Gate，要求 successor 文件里确实存在承接守卫的执行项，
  并给空窗期加了终止条件（两轮内没落地就升级进 STATE §3）（BLOCKING-2）；
  红线自查扩成五条——路径清单加 `docs/masterplan` 与 `expected-red.txt`、
  `status --porcelain` 与 `diff` 成对覆盖已提交/未提交、并把「STATE 只追加」落成
  `git diff --numstat … -- STATE.md` 的 **deletions 列为 0**（BLOCKING-3）；
  回滚策略改成三行的表（Phase 2 负向对照 / 变异 ① / 变异 ②），Exit Criteria 相应改口径（BLOCKING-4）；
  两处边界引证改为 `AGENTS.md` 红线 1 边界句 + Protected Areas 第 2 行，并**留痕说明误引已改准**，
  同一处修正也同步进了 successor plan（BLOCKING-5）。七条 nit 全部就地采纳。
- Independent draft review iteration 3: **needs revision**（同一独立评审者，2026-08-22）。
  第二轮五条 blocking 中 **BLOCKING-1 / 3 / 4 / 5 判定为已解决**，评审并做了两处独立实证：
  ① `capture("doctypes")` 是真作用域（`agenerp/snapshot.py:46` `SITE_SCOPE_DOCTYPES = {"doctypes": "Custom Field"}`，
  未知作用域会抛），所以那条差集**能**装进探针以外的东西，判据可失败；
  ② `--numstat` 的 append-only 语义按本仓真实历史验过——纯追加是 `15 0` / `9 0` / `8 0`，
  而就地改一行是 `1 1`（`bd32959` 对 STATE.md 正是如此），**这条判据在真实历史上会咬**。
  新增 2 条 blocking，都是一行级的机械错：
  · **BLOCKING-A**：用来核对 successor 是否接了守卫的那条 grep **没有区分度**——
    `grep 'check_expected_red.py'` 在 successor 里有 10 处命中，其中三处是与守卫无关的普通验证步骤，
    守卫项被删掉它照样命中。**这正是本 plan 自己第 174 行禁止的「不可能触发的假守卫」同一类错误**。
  · **BLOCKING-B**：为「零产品行为发布」把关的两条判据又写成了**裸 `git diff`**（Phase 2 Exit 与 Closure Gate 各一），
    提交后恒为空；且其中一条对判定器断言「为空」本身就错——Phase 2 本来就要改它。
  另有 6 条 nit（Closure Gates 实为 **14** 框而文中写十二、Exit 写「四条」而命令有五条、
  `git status -- docs/masterplan` 必须在 STATE 提交之后跑否则伪失败、
  `--numstat` 在文件未触碰时不打印任何东西所以「deletions 列为 0」措辞不严、
  「两轮」未定义单位、以及建议把 `bd32959` 那个真实历史反例写进 plan）。
  评审同时复核了本轮改动的全部计数与交叉引用（Protected Areas 10 行 / Goals 已改「判定行」/
  变异 ① 确为 Phase 3 第三项）——**全部确认**；并明写「把这两行改掉，本 plan 即为可执行合同」。
- Revision after iteration 3（本次修订，逐条对应）：
  grep token 由 `check_expected_red.py` 换成有区分度的 **`verdict-tool-untouched`**，
  并要求命中落在形如 `- [ ] \`Add\`` 的执行项行上（BLOCKING-A）；
  两条裸 `git diff` 全部改为「开工 sha + `git status --porcelain`」成对形式，
  并按路径分开写——`agenerp/` 断言为空、判定器断言「`skipped` 分支没有被删」而不是「文件为空」（BLOCKING-B）；
  六条 nit 全部就地采纳（14 框、五条、STATE 提交后再跑的执行顺序、`--numstat` 措辞与
  「为什么 deletions=0 等于只追加」的解释、「两个 mission 循环」明确单位、
  以及把 `bd32959` → `1	1` 这个真实历史反例写进判据旁边作为「这条判据不是仪式」的证据）。
- Independent draft review iteration 4: **acceptable as-is** —— **共识达成**（同一独立评审者，2026-08-22）。
  逐条复验了本轮六处改动，全部确认，并把 BLOCKING-A 的新 grep **端到端跑了一遍**：
  `grep -n 'verdict-tool-untouched' docs/plans/p0-foundation/2026-08-22-0027-2-*.md` → 3 处命中，
  其中**只有第 266 行**以 `- [ ] \`Add\`` 开头（即守卫执行项本身），另两处（叙述行、`###` 标题）
  **不满足**该模式——**守卫项被删掉这条判据就会失败，区分度成立**；
  并确认 successor 第 266–272 行确实带着「不覆盖 `expected-red.txt`」的边界与已改准的引证。
  BLOCKING-B 处逐个扫过全文的 `git diff` 出现位置：剩下的裸 `git diff` 只出现在
  「引用 CI 自己的命令」「陈述那条规矩本身」「评审记录叙述」三类地方，**没有任何一条判据在用它**。
  另复核：Closure Gates 实测 14 框与文中「十四框」一致、五条自查与命令数一致、
  STATE 提交后再跑的执行顺序在位、`--numstat` 措辞与 `bd32959` → `1	1` 的实证一致、
  「两个 mission 循环」单位明确。回归检查：Anti-Slacking 零违规、
  `grep -B5 '^- \[ \]' | grep -c 'Status: completed'` → **0**、三个 Phase 均 `planned`、6 条 Deferred 全带重开事件。
  评审结论逐字：「The plan crosses no red line; it does not loosen any gate and closes one pre-existing unprotected surface.」
  留了 1 条 nit（Closure Gate 的 grep 比 Exit Criteria 少要求了「边界写明」那半句）——**已就地采纳**，两处现在逐字同口径。
- **共识达成**：四轮独立评审，第四轮 `acceptable as-is`，`Plan Status` 由 `draft` 改为 `active`。

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（`system-baseline.md` 新 `## 14.4` / `ai-autonomy-policy.md` Protected Areas /
      roadmap 工作项 9 与「9 现状」/ `project-context.md` 第 56–58 行 + 新增行 / STATE §2）
- [x] 确认的 owner-doc 漂移（`project-context.md:56` 的措辞、判定方式节的误归档）已就地改准，
      **没有被降级成 follow-up**（Minimum Rule 14）
- [x] verification has run：判定器默认环境前后各一次 · `GATE_VERIFY` 字面命令正向 + 负向 ·
      `pytest tests/unit` · `ruff check` · `smoke-loop-wiring.sh` · live 整目录判定 · 三条变异
- [x] **live 模式已被证明能返回 exit 0**（整目录绿，或收窄范围的正向对照绿）——没有这条不许关闭
- [x] scoped verification is not conflated with full verification —— **live 只在本机做过，CI 未验证**，
      这句必须逐字出现在 `## Closure` 里（本仓无全量套件，见 `project-context.md` 第 61–62 行）
- [x] 默认判定环境的**判定行**与开工前逐字一致，且有两次实跑输出作证
- [x] no in-scope item downgraded to deferred/follow-up
- [x] **「CI 侧守卫」的空窗期已闭合或已升级**：
      `grep -n 'verdict-tool-untouched' docs/plans/p0-foundation/2026-08-22-0027-2-*.md`
      至少有一处命中落在 `- [ ] \`Add\`` 执行项行上，**且该执行项写明了「不覆盖 `expected-red.txt`」的边界**
      （与 Exit Criteria 逐字同口径）；否则本 plan 不得关闭，须把守卫升级进 STATE §3 needs-human
- [x] 三处变异窗口（Phase 2 负向对照 / 变异 ① / 变异 ②）全部复原。
      **判据按路径分开写，且一律用开工 sha**（第三轮独立评审 BLOCKING-B：原写法是两条裸 `git diff`，
      提交后恒为空；且对判定器写「为空」本身就是错的——Phase 2 **本来就要改它**）：
      · `agenerp/`：`git diff --stat <开工 sha>..HEAD -- agenerp` **与**
        `git status --porcelain -- agenerp` 两条都为空（Non-Goals 禁止任何净改动）；
      · 判定器：`git status --porcelain -- tools/gates/check_expected_red.py` 为空，
        且 `git diff <开工 sha>..HEAD -- tools/gates/check_expected_red.py` 里
        **`verdict()` 的 `skipped` 分支没有被删**（变异 ② 已复原）——这一条要人读 diff，不能只看退出码
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [x] closure audit was independent
- [x] closure evidence exists in files

## Deferred But Adjudicated

### CI 侧守卫：把 `gates-untouched` 的 diff 范围扩到 `tools/gates/check_expected_red.py`

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 它是 `.github/workflows/**` 改动，与本 plan 的 Non-Goals 冲突；
  且本批第二个 plan 本来就要动那份文件一次，合并成一次改动比分两次安全。
  **本 plan 已在文档层先加严**（`ai-autonomy-policy.md` 新增 Protected Areas 行），
  空窗期的存在写进了 `## 14.4`，不粉饰。
- Successor Required: `yes` —— `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`，**必须在其 scope 内**
- 重开事件：本 plan 关闭之后立即。
- **边界（交给 successor 的硬约束）**：守卫**只覆盖 `check_expected_red.py`（可含 `gate-verify.mjs`），
  不得覆盖 `tools/gates/expected-red.txt`** —— 出处是 `AGENTS.md` 红线 1 的「边界」句
  （账本不是裁判，**只能变短**）与 `ai-autonomy-policy.md` Protected Areas 第 2 行
  （`allowed（只能变短）`，变长才需 trailer，服务端控制是 `expected-red-ratchet`）。
  把账本圈进去会让每一次合法的划短在 CI 上失败。**不要引 STATE §2 11:20Z**——那条讲的是名单里该写什么，不是谁能改。
- **空窗期的终止条件**（Anti-Slacking：不许无限期开着）：successor 关闭、或人另行落地守卫。
  **若 successor 在两个 mission 循环（`missions/p0-foundation.json` 的 `maxCycles` 计数单位，不是评审轮次、不是自然日）
  内没能落地**，由本 plan 的关闭审计把它升级进 STATE §3 needs-human 队列。

### CI 消费这个 live 判定模式

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: `.github/workflows/**` 是 `ai-autonomy-policy.md` 表里的 `blocked` 面，
  且与判定契约不是同一个结果面。本 plan 关闭时工作项 9 停在 `planned`，不存在「把没做完的活报成 done」。
- Successor Required: `yes` —— `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`
- 重开事件：本 plan 关闭之后立即。

### 把整目录 live 判定接进 `missions/p0-foundation.json` 的 `commands.test`

- Classification: `out-of-scope improvement`（out-of-authority）
- Why Not Blocking Closure: `missions/**` 是角色 B 禁区，loop 无权改。且它**不该**被接进去：
  `commands.test` 是默认判定环境每轮复跑的命令，塞一条要起 docker 栈的命令进去，
  会让每轮 `GATE_VERIFY` 都依赖活栈。与 Contract tests / Seed dataset 两行同样的处理
  （`project-context.md` 第 53–54 行）。
- Successor Required: `no`（人动作）
- 重开事件：人决定让 `GATE_VERIFY` 依赖活栈时。**默认建议是不接**，理由如上。

### live 契约写死为「全绿」，将来登记一条 live 预期红需要改代码

- Classification: `watch-only residual`
- Why Not Blocking Closure: 这是 Phase 1 `Decision` 一的明示取舍，已写进 `## 14.4`。
  本仓此刻一条 live 预期红都没有，这堵墙现在没有对象。
- Successor Required: `no`
- 重开事件：第一次出现「判据先行、实现未到、且只在 live 下可判」的门禁时。届时把契约从「全绿」
  改成「读一份 live 名单」，并同时给那份名单配棘轮——**两件事必须一起做**，只加名单不加棘轮是净放松。

### 9 条从未在 live 环境下跑过的门禁

- Classification: `watch-only residual`
- Why Not Blocking Closure: `test_normalizer_idempotent.py` 3 条与 `test_seed_dataset_absurdity.py` 6 条
  都是纯 L1（不取任何 fixture、不碰站点），在 live 环境下没有理由改变结果。
  **但「没有理由」不是证据**——Phase 3 的整目录实测正是它们第一次在 live 下跑，结果照实记。
- Successor Required: `no`
- 重开事件：整目录实测若显示这 9 条中任意一条在 live 下行为不同，立即转为 blocking 并回 Phase 2。

### 整目录 live 判定实测到一次**不可复现**的红（`::test_no_orphan_column_left_behind`）

- Classification: `watch-only residual`
- **本条是 Phase 3 实测新增的，不是起草时就有的。** 第 1 跑 exit 1 并逐字点名
  `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`，
  **原样复跑四次全部 exit 0（19 条全绿）**。按 `AGENTS.md` 裁判规则 3，记为「不可复现」，**不猜根因**。
- Why Not Blocking Closure: live 模式的正向证据已经拿到（四跑 exit 0），交付物「被证明可用」这条成立；
  且本 plan **不碰 CI**，这条间歇性此刻不会让任何自动化判定变红。
  **但它必须被交出去**：本批第二个 plan 要在 CI 上跑同一条命令，而 CI 上一次红就是一次红，没有人在旁边复跑。
- Successor Required: `yes` —— `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`，
  **作为已知风险交办**（不是给它加 scope：它本来就要跑这条命令，这条事实只是它必须知道的输入）。
- 重开事件：**再次观察到同一条门禁在整目录 live 判定下红**（本机或 CI 皆算）。
  届时它就从「不可复现」变成「可复现的间歇性」，应当立即立案查根因并回到判据侧，
  **不得**用 `-p no:randomly` / `-x` / 收窄目录之类的手段掩盖。
- 相关既有登记：`docs/backlog/gate-fixtures-pollute-the-live-site.md`（门禁在活站点上留孤儿列）
  与本条**可能**相关，但本 plan **不断言**两者有因果关系——那是猜根因。

### 门禁每跑一轮在本机常驻站点上留孤儿列

- Classification: `watch-only residual`
- Why Not Blocking Closure: 已由 `docs/backlog/gate-fixtures-pollute-the-live-site.md` 登记，
  修法在 `tests/gates/conftest.py`（红线 1）。本 plan 的 live 实测走既有跑法，**不加剧**它。
- Successor Required: `no`（由该 backlog 文档承接；触发条件由本批第二个 plan 重新裁定）
- 重开事件：见该文档「新的触发条件」两条。

## Closure

Status Note: 三个 Phase 的执行项与 Exit Criteria 全部落地并在活仓复核通过，
`## Closure Gates` 十四框由本次独立关闭审计逐条实跑核对后置位，`Plan Status` 由 `active` 改为 `completed`。
交付物（判定器的 live 判定模式 + `classify()` / `verdict()` 纯函数接缝 + 12 条单测 + Protected Areas 加严行）
**已接进运行时**：`main()` 按 `AGENERP_LIVE` 选模式、live 下跳过 `load_allowlist()` 并调
`verdict(..., live=True)`，不是挂着不通电的接口。工作项 9 仍停在 `planned`（关闭判据是 CI 上跑绿，本 plan 不碰 CI），
不存在把没做完的活报成 done。

**verification scope（逐字，Closure Gate 第 6 条要求）：live 只在本机做过，CI 未验证。**
本仓此刻没有全量套件（无 build、无 typecheck），上面这些绿是 scoped verification，不是「全量验证通过」。

Closure Audit Evidence:

- Auditor / Agent: 独立关闭审计子代理（fresh session，与起草/执行会话分离，2026-08-22）。
  四轮独立草案评审记录在 `## Draft Review Record`，第四轮 `acceptable as-is`。
- 审计基线：`HEAD` = `488df9e`（`git status --porcelain` 输出为空，干净树），开工 sha = `084c9c4`。
- **实跑复核（审计会话现场跑的，不是抄执行记录）**：

  | 命令 | 结果 |
  |---|---|
  | `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | `判定模式：default …` / `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致` / `205 passed` → **exit 0** |
  | `ruff check agenerp tests/unit tests/contracts` | `All checks passed!` → **exit 0** |
  | `git diff --stat 084c9c4..HEAD -- tests/gates .github/workflows docs/masterplan missions tools/gates/expected-red.txt` | 只列出 `docs/masterplan/STATE.md` 一行（18 insertions），其余四条路径零命中 |
  | `git status --porcelain -- tests/gates .github/workflows docs/masterplan missions tools/gates/expected-red.txt` | 无输出 |
  | `git diff --numstat 084c9c4..HEAD -- docs/masterplan/STATE.md` | `18	0` → deletions = 0 ⇒ **只追加** |
  | `git diff --numstat 084c9c4..HEAD -- tools/gates/expected-red.txt` | 无输出 ⇒ 名单一行未动 |
  | `git diff --stat 084c9c4..HEAD -- agenerp` / `git status --porcelain -- agenerp` | 两条均无输出 ⇒ 变异 ① 与 Phase 2 负向对照均已复原，零产品行为发布 |
  | `git status --porcelain -- tools/gates/check_expected_red.py` | 无输出；活文件第 105 / 115 / 134 行 `if skipped:`、live 侧 `if reds or skipped:`、default 侧 `unexpected_red or unexpected_green or skipped` **三处俱在** ⇒ 变异 ② 已复原 |
  | `grep -n 'verdict-tool-untouched' docs/plans/p0-foundation/2026-08-22-0027-2-*.md` | 7 处命中，**只有第 278 行**以 `- [ ] \`Add\`` 开头（守卫执行项本身），其第 281–285 行逐字写着「**硬边界（前驱定的）：路径清单里不得出现 `tools/gates/expected-red.txt`**」并引 `AGENTS.md` 红线 1 边界句 + Protected Areas 第 2 行 ⇒ 空窗期已被 successor 承接，本 plan 无须升级进 STATE §3 |

- **落地面逐条核对（读活文件，不信 `[x]`）**：
  `tools/gates/check_expected_red.py:79` `classify()` · `:92` `verdict()` · `:140` `main()` 按 `AGENERP_LIVE` 选模式并
  两种模式都打印模式行 · `:148` live 下 `expected_red` 为空集且**不调** `load_allowlist()`；
  `tests/unit/test_gate_verdict.py` 11 个测试函数（末一个 `test_verdict_never_touches_the_process` 参数化两态）
  = 12 条，与 `193 → 205 passed` 的增量吻合；
  `docs/architecture/system-baseline.md:383` `## 14.4`（`## 14` 编号序列为 131/178/208/286/**383**）；
  `docs/context/ai-autonomy-policy.md:88` Protected Areas 判定器本体行（`plan-first`，边界写明不覆盖 txt，
  出处引红线 1 边界句与本表第 2 行）；
  `docs/backlog/p0-foundation-roadmap.md:28` 工作项 9 `planned` · `:68` 判据先行不可满足与含 8 的关系 · `:69` 「9 现状」行；
  `docs/context/project-context.md` 第 56 行漂移已改准为窄说法 + 新增「L2 live 门禁（**整目录判定**）」一行
  （如实收录第一跑 exit 1 与「不可复现」，且未把 `--ignore` 诊断命令写进表）；
  `docs/logs/2026/08-22.md` 三个 Phase 各一条记录；`docs/masterplan/STATE.md` §2 追加 18 行。
- **审计发现并就地修掉的一处文本缺陷**：Phase 1 最后一条 Exit Criteria（第 406 行）里那条判据 grep 的
  **字面量**被 EXECUTE 阶段的整体勾选误伤，写成了 `- [x] \`Add\``。successor 的守卫项尚未执行，
  本就应当是 `- [ ] \`Add\``——按误伤后的写法这条判据**不可满足**，且与同口径的 Closure Gate（仍为 `- [ ] \`Add\``）
  自相矛盾。已改回 `- [ ] \`Add\``，两处现在逐字同口径，实跑核对见上表最后一行。
- **五点一致性**：`Plan Status: completed` · 三个 Phase 均 `Status: completed` 且全部执行项与 Exit Criteria `[x]` ·
  `## Closure Gates` 十四框全 `[x]` · 本节证据 · `docs/logs/2026/08-22.md` 与 STATE §2 —— 逐条相符。
  `grep -B5 '^- \[ \]' <plan> | grep -c 'Status: completed'` → **0**。
- **Deferred 诚实性复核**：6 条 Deferred 全部带重开事件，无一条藏着确认的活体缺陷或契约漂移。
  两条确认的 owner-doc 漂移（`project-context.md:56` 的措辞、判定方式节误归档）都在 Phase 3 / Phase 1 就地 `Fix` 了，
  **没有降级成 follow-up**（Minimum Rule 14）。那条不可复现的红是**实测事实**，已作为 `watch-only residual`
  登记并作为已知风险交办给 successor，不是被藏起来的失败。
- **红线自查**：`tests/gates/**` / `.github/workflows/**` / `missions/**` / `expected-red.txt` 零改动；
  `docs/masterplan/` 仅 `STATE.md` 追加 18 行、删 0 行；未写入证据仓；未生成运行时 Server Script。

Follow-up:

- 本批第二个 plan `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md` 承接两件事：
  CI 消费面（`gates.yml` 上用判定器对 19 条做 live 判定）与 CI 侧守卫 `verdict-tool-untouched`。
  重开事件逐字为「本 plan 关闭之后立即」——本节落笔即触发。
- 那条不可复现的红（`::test_no_orphan_column_left_behind`）作为已知风险随之交办；
  CI 上一次红就是一次红，没有人在旁边复跑。
