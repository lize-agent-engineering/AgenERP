# 2026-08-21-1022-1 零依赖启动（compose 语法，L1 部分）

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 3. 零依赖启动（compose 语法 + 首页 AI 未配置降级）
> Last Reviewed: 2026-08-21
> Source: `docs/backlog/p0-foundation-roadmap.md` Work Item Status 第 3 项（起草时 `todo`；本 plan 转 `active` 时由起草步置 `planned`）
> Related: `2026-08-21-1022-2-tool-contract-layer-v0.md`（后继。**依赖关系要说准**：那个 plan 的 A 半不需要活站点、可与本 plan 并行；
> 需要本 plan 交付的栈的是**工作项 4 的 B 半**，那是它之后的另一个 plan）
> Audit: required

## Current Baseline

起草时（2026-08-21，HEAD `2992c73`）在本机实跑得出，不凭记忆：

- roadmap 工作项 3 状态 `todo`，绑定门禁为 `tests/gates/test_zero_dep_boot.py::test_compose_config_valid_with_empty_env`（roadmap §对照表标为 **L1**）。
- **今日红因（原文）**：`python3 -m pytest tests/gates/test_zero_dep_boot.py -q` → `1 failed, 2 errors`；失败断言的 stderr 逐字为
  `open /Users/lize/Documents/claude/AgenERP/docker-compose.yml: no such file or directory`。
  也就是说红在「文件不存在」，不是红在语法——**仓里没有 `docker-compose.yml`**（`find . -name 'docker-compose*'` 除 vendor 外无命中）。
- 同文件另外两条 error 在 `tests/gates/conftest.py:29` 的 `compose_stack` fixture `NotImplementedError`。它们归 **工作项 8**，不归本 plan。
- 门禁调用形状（读 `tests/gates/test_zero_dep_boot.py`）：`subprocess.run(["docker","compose","-f","docker-compose.yml","config","-q"], env={"PATH":…,"HOME":…})`。
  → 文件必须落在**仓库根目录**且文件名逐字为 `docker-compose.yml`；判定命令是 `config -q`，不是 `up`。
- **判定器不过滤 marker**：`tools/gates/check_expected_red.py:35` 固定跑 `[sys.executable,"-m","pytest","tests/gates","-q","--tb=no",--junitxml=…]`，`cwd=ROOT`，不传 `-m`。
  该文件的 `pytestmark = pytest.mark.live` 因此**不会**让它被 deselect；CI 的 `gates-l1` job 跑的正是这个判定器。
  ⚠️ 顺带记一处**尚未咬人的矛盾**，留给后继：`pyproject.toml:21` 写着「L1 快门禁跑 `-m 'not live'`」，
  而 roadmap 把本 plan 这条门禁标为 **L1**、测试文件却带 `live` marker。今天不咬人是因为判定器**根本不传 `-m`**；
  哪天有人按 `pyproject.toml` 那句给判定器加上 `-m 'not live'`，这条门禁会被 deselect 而**静默消失**。本 plan 不改判定器，只登记。
- **实测：`docker compose config` 不需要 daemon。** 在 scratchpad 里用最小 compose 试：
  `env -i PATH=… HOME=… DOCKER_HOST=unix:///nonexistent.sock docker compose config -q` → **exit 0**；`env -i` 干净环境同样 **exit 0**。
  → CI 的 ubuntu runner 只要有 docker CLI + compose 插件即可，daemon 不必可用。本机 `docker compose version` → **v5.0.2**，daemon up。
- **预期红名单已迁出红线。** `tests/gates/EXPECTED_RED.txt` 不存在；名单在 `tools/gates/expected-red.txt`，人于 `4bbe3f5`（带 `Gates-Change-Approved-By: lize`）迁移并写明裁定：
  「**测试代码是裁判（红线保护），预期红名单只是账本**」——loop 可在同一提交里划掉已转绿的行，名单**变长**仍需人工批准（CI `expected-red-ratchet` job 把守）。
  **这是本 plan 与 plan `…-2341-2` 处境的决定性差别：本 plan 的划名单动作本身不需要人批。**
  （唯一仍会停下来等人的情形是 Phase 1 前置确认不通过——那时一步都不做、置 `deferred`，与「划名单卡在人手里」是两回事。）
- 名单当前 8 行，含本 plan 要转绿的 `tests/gates/test_zero_dep_boot.py::test_compose_config_valid_with_empty_env`，以及归工作项 8 的另两行。
- `python3 tools/gates/check_expected_red.py` → **exit 0**（「门禁 13 项：预期红 8，绿 5，跳过 0」）。`missions/p0-foundation.json` 的 `commands.test` 为
  `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`，两条都是 `GATE_VERIFY` 会复跑的。
- **划名单是单向动作，所以 CI 侧的前提在起草时就查实了，不留给执行会话去赌**：
  `git remote -v` → `origin https://github.com/lize-agent-engineering/AgenERP.git`，CI 真的会在 push 时跑；
  Phase 2 划掉那一行之后该门禁就**在名单外**，若 `gates-l1` 的 runner 缺 docker CLI 或 compose 插件，
  `check_expected_red.py` 会报「**名单外的门禁红了**」并退 1；而把它放回名单属**变长**，`expected-red-ratchet` 无 `Gates-Change-Approved-By:` 即拦——**loop 自己回不去**。
  → **已实测查证（2026-08-21 起草时；独立评审复核复现，两次结果一致）**。命令与原文输出：
  ```
  $ gh api -H "Accept: application/vnd.github.raw" \
      repos/actions/runner-images/contents/images/ubuntu/Ubuntu2404-Readme.md \
      | grep -E '^- Docker (Compose|Client|Server)'
  - Docker Compose 2.38.2
  - Docker Client 28.0.4
  - Docker Server 28.0.4                       # exit 0
  # Ubuntu2204-Readme.md → 同样三行，exit 0
  ```
  **结论：`ubuntu-latest` 自带 docker CLI 与 compose 插件，`gates-l1` 无需任何 setup 步骤**（本 plan 也无权加，`.github/workflows/**` 是红线 2）。
  这条风险到此不再是「本机验证不了」。
- **⚠️ 版本差是本 plan 剩下的、真的可能「本机绿 CI 红」的那一处**：runner 是 compose **2.38.2**，本机是 **v5.0.2**——差一个大版本。
  `config -q` 在本机退 0 **不等于**在 runner 上退 0，而划名单不可由 loop 回退（同上）。
  → **这条风险在本机没有缓解措施，本 plan 就这么记着，不发明一个。** 起草过程试过两版，都被独立评审实测否掉，两次都记在这里免得后继再试：
  ① 一份「2.x 以来稳定的键」白名单——**是假装知道**：它会禁掉 frappe/erpnext 栈**必须**用的 `x-*` 锚点与 `entrypoint`，
     而 `entrypoint`/`env_file`/`user`/`working_dir` 早于 compose 2.x、`x-*` 自 3.4 起就有，「2.x 以来稳定」根本支撑不了那份排除。
  ② 「文件头声明用到的键清单 + 断言正文 ⊆ 清单」——**是自证**：清单由 Phase 1 从它刚写的正文里导出、同一个提交落地，
     断言在写下的那一刻按构造就成立；而且纯文本扫描分不清顶层键、服务级键、服务名、卷名与 `<<` 合并键。**零保护，撤回。**
  → **真正的 de-risk 不在本机，在落地方式**：`.github/workflows/gates.yml` 的触发器含 `on: pull_request`，
  所以**只要这批改动经 PR 落地，`gates-l1` 就会在真正的 2.38.2 runner 上先跑一遍，再合进 `main`**——
  不可验证且不可回退的残余，就此变成合并前可见的事实。处置见 Phase 3 与 `## Deferred But Adjudicated`。
  失败特征（若仍直推 `main` 且踩中）：`gates-l1` 报「名单外的门禁红了」并退 1，**恢复只能由人做**（放回名单属变长，须 `Gates-Change-Approved-By:`）。
- 成因与修法**已有 owner doc 定论**，不需要本 plan 重新调研：`docs/architecture/system-baseline.md` §14 记 Spike 10 实测——
  成因是 compose 的 `${VAR:?msg}` 硬失败语法让 `config` 都解析不了；并给出三条可执行规则与一条附带风险（默认弱口令）。
- 仓里**没有任何 Frappe app 骨架**，`agenerp/` 只有 `pack.py` / `snapshot.py`；`docs/context/project-context.md` 的 `Run app locally` 写着
  `none（无 docker-compose.yml；roadmap 工作项 3「零依赖启动」的交付物）`——本 plan 落地后这一行必须改。
- 本机有 PyYAML 6.0.3。本 plan 新增的测试仍**只用标准库**，但理由要说准（独立评审校正）：
  `tests/unit` **不被 `.github/workflows/gates.yml` 的任何 job 执行**（六个 job 里 `gates-l1` 只跑 `check_expected_red.py`，而它固定跑 `tests/gates`）。
  它唯一的运行处是本机 `GATE_VERIFY` 复跑 `missions/p0-foundation.json` 的 `commands.test`。
  → 真正的理由是：**不给本机判定面新增任何依赖**——判定面一旦依赖某个包，换台机器就红在环境而不是红在实现上。
- 仓库根目录存在 gitignored 的 `.env`（`MISSION_DRIVER_HOME` 等）。`docker compose` 会自动读它做插值，而 CI 里没有这个文件。
  → compose 内所有变量必须自带默认值，使「有没有 `.env`」不改变 `config` 的**退出码**。
  ⚠️ **只有退出码不变，解析结果会变**（独立评审实测：`.env` 里 `A_PORT=9999` 时 `config` 输出 `published: "9999"`，删掉 `.env` 后是默认的 `8080`）。
  这条对 Phase 2 的判据是硬约束：单测是**静态文本扫描**，管不到 `.env` 的覆盖——所以**绑定地址必须字面写死，不许经变量**。

## Goals

- 仓库根目录落一份 `docker-compose.yml`，**空环境变量下 `docker compose config -q` 退 0**，使
  `python3 -m pytest tests/gates/test_zero_dep_boot.py::test_compose_config_valid_with_empty_env -q` → **exit 0**。
- 把 `system-baseline.md` §14 的规则**变成可执行判据**（`tests/unit/`，纯标准库），而不是只在这一版文件里碰巧成立。
  §14 的三条规则逐字为：**①** compose 中禁止 `${VAR:?}`，一律用 `${VAR:-默认值}`；**②** 一切外部能力缺失即为「未配置」状态，不是错误状态；
  **③** 前置检查属于 verify 脚本，不属于启动路径。另有 `⚠️ 附带风险` 段单独要求：默认口令「**必须配合首次启动强制改密或仅监听回环地址**」。
  本 plan 覆盖 **① + ② + 附带风险的回环绑定**；**③ 的处置见 `## Non-Goals` 与 `## Deferred But Adjudicated`。**
- 同一提交里把 `tools/gates/expected-red.txt` 中转绿的那一行划掉，使 `check_expected_red.py` 仍退 0。
- 如实记录一次本机 `docker compose up` 的尝试与退出码（**证据，不是判据**——「起得来且 healthy」是工作项 8 的门禁）。

## Non-Goals

- **不做工作项 8**：不实现 `compose_stack` fixture、不碰 `test_stack_boots_and_all_services_healthy` 与
  `test_homepage_states_ai_disabled_instead_of_crashing`。那两条的 fixture 在 `tests/gates/conftest.py`，属红线 1。
- **不做首页文案本身**。工作项 3 的标题含「首页 AI 未配置降级」，但 roadmap §对照表把该断言明确划给**工作项 8**；
  仓里也还没有承载首页的应用层。本 plan 只交付它的 compose 侧一半：AI 相关变量一律有空默认值，缺失即「未配置」状态，不让任何服务因此起不来。
- **不做 §14 规则 ③（「前置检查属于 verify 脚本，不属于启动路径」）的判据。** 本仓此刻没有 verify 脚本、也没有启动路径上的前置检查，
  给一条无对象的规则写断言只能写成同义反复。处置记在 `## Deferred But Adjudicated`，带重开事件——**不是悄悄漏掉**。
- 不写 Frappe app 骨架、不做站点初始化脚本以外的应用代码。
- 不改 `tests/gates/**`、`.github/workflows/**`、`missions/**`、`docs/masterplan/**` 已有行、`tools/gates/check_expected_red.py`、`tools/gates/gate-verify.mjs`。
- 不把 docker 加进 `missions/p0-foundation.json` 的 `commands`（`missions/**` 是角色 B 禁区）。

## Task Route

- Type: `implementation-only change`（净新增 compose 与单测；无 API/DB schema/auth 面变更）
- Owner Docs: `docs/architecture/system-baseline.md` §14（三条规则与风险的出处，只读）·`docs/backlog/p0-foundation-roadmap.md`（判据绑定）·`docs/context/project-context.md`（本 plan 要更新的 owner doc）
- Skill Selection Basis: `docs/skills/` 下只有审查/审计类 prompt 模板，无「写 compose」对应的方法技能；判据已是可执行断言。各阶段 `Skill: none`。

## Infrastructure And Config Prereqs

- 依赖 docker CLI + compose 插件在场（本机 v5.0.2；`config` 不需要 daemon，已实测）。
- 新增外部依赖只有**容器镜像**（ERPNext / MariaDB / Redis 官方镜像），不新增任何 Python 包。
- **零必填环境变量**：所有变量写成 `${VAR:-默认值}`，使 `.env` 在场与否不改变 `config` 的**退出码**
  （解析结果**会**变——见 `## Current Baseline`；这正是绑定地址必须字面写死、不经变量的原因）。
- 端口只绑 `127.0.0.1`，与默认口令配套（`system-baseline.md` §14 附带风险的对冲手段）。
- 回滚策略：全是新增文件 + 名单删一行 + 文档填空，`git revert` 即可回到「红在文件不存在」，无数据迁移、无外部副作用。

## Execution Plan

### Phase 1 — 落 `docker-compose.yml`，做到零必填变量

Status: completed
Targets: `docker-compose.yml`、`.env.example`（追加 compose 用变量的说明，不改已有行）
Skill: `none`

- Item Types: `Proof | Add | Decision`
- Prereqs: 无

- [x] `Proof` **开工前置确认（第一步，不做完不许写 compose）**——把起草时查实的两件事复核一遍，不是重新调研：
      1. **CI 侧前提**：`gh api -H "Accept: application/vnd.github.raw" repos/actions/runner-images/contents/images/ubuntu/Ubuntu2404-Readme.md | grep -i 'Docker Compose'`
         → 应含 `Docker Compose 2.x`。起草时读到 **2.38.2**（`Ubuntu2204` 同）。**记退出码与命中的原文行。**
      2. **本机 compose 版本**：`docker compose version`（起草时 v5.0.2）。两个版本都记进 log。
         ⚠️ 记版本**不是缓解措施**（本机没有缓解措施，见 `## Current Baseline`），它只是让「本机绿 CI 红」真发生时不必重新考古。
      3. **记下本 plan 的开工 sha**（`git rev-parse HEAD`）并写进 `docs/logs/`——Phase 2/3 的四条区间 diff 判据全靠它，不记就没法复核。
      4. **确认 roadmap 工作项 3 已是 `planned`；若仍是 `todo`，就地改成 `planned`。**
         - **为什么必须有人认领这一步**（独立评审 NEW-D）：`todo → planned` 没有任何引擎产物负责写——
           `plan-review.md:22` 只说改 plan 自己的 `Plan Status`，`closure-audit.md` 里 `roadmap` 出现 0 次，
           唯一会写 roadmap 的是 `execute.md:11`，而本 plan 明确不照它做（理由见 Phase 3）。**没人写 = 一直是 `todo` = 「引擎取第一个 todo」把工作项 3 反复重选。**
         - 起草步在本 plan 转 `active` 时已写过一次；这一条是**幂等复核**，不是重复劳动。
         - 取值依据：roadmap `:34` 把 `planned` 定义为「已有执行 plan 且通过草案评审」——正是 `draft → active` 那一刻成立的事。
      - **不一致时的处置只有一个，没有分支**：若 readme 里查不到 compose，或 `gh` 跑不起来 →
        **停手**：不写 compose、不划名单、不提交代码，向 `docs/masterplan/STATE.md` §3 **追加一行**说明（只追加），
        把本 plan 置为 `Plan Status: deferred`（该值不在 `ACTIVE_STATUSES` 也不在 `DRAFT_STATUSES`，是唯一能让 plan 停下来等人的值），然后停。
        **不要「先实现、只是不划名单」**——那会让 `check_expected_red.py` 报「名单内的门禁却绿了」退 1，
        `GATE_VERIFY` 判 fail、重试 EXECUTE 三轮后子流程 `failed`，正是 plan `…-2341-2` 踩过的那个坑。要么整件事做完，要么一步都不做。
      - Skill: `none`
- [x] `Decision` 定下栈的形状与镜像来源，并写明备选与残余风险。
      - 约束来自门禁与 owner doc，不是自由发挥：文件名/位置由门禁写死；服务集合要能支撑工作项 8 的 `services()` 与 `http_get("/")`。
      - 备选：(a) 完整 frappe/erpnext 多服务栈（db + redis-cache + redis-queue + backend + frontend + websocket + queue worker + scheduler + 建站 init）；
        (b) 单服务占位 compose，只为让 `config` 退 0。
      - **否决 (b)**：那是为让判据变绿而做的手脚，且工作项 8 一开工就得推翻重写。选 (a)。
      - 残余风险：镜像 tag 会漂。缓解——**tag 写死具体版本，不用 `latest`**，并在文件头注明版本来源与升级时该跑什么。
      - Skill: `none`
- [x] `Add` 写 `docker-compose.yml`：**不写 `version:` 顶层键**（compose v2+ 已弃用；实测是告警，见下），
      每个变量一律 `${VAR:-默认值}` 形式，**全文件不得出现 `${VAR:?}` / `${VAR:?msg}`**。
      - `version:` 的实测是**告警，不报错**（评审在本机 v5.0.2 复现：带 `version: "3.9"` 时 `config -q` 仍 **exit 0**，只打 `the attribute 'version' is obsolete`）。
        规则保留（不写它），但不许在文档里写成「会报错」。
      - Skill: `none`
- [x] `Add` AI 能力相关变量（如 LLM endpoint / api key）一律给**空字符串默认值**，且不得出现在任何服务的
      `healthcheck` 或启动 `command` 的成败路径上——「未配置」是合法状态，不是错误状态（`system-baseline.md` §14 规则 2）。
      - Skill: `none`
- [x] `Add` 所有 `ports:` 发布项写成 `127.0.0.1:<host>:<container>` 短语法，**宿主 IP 字面写死、不经变量**，且默认口令只用于本地起栈。
      - 这是 `system-baseline.md` §14 「附带风险」段点名要求的两个对冲手段之一（另一个是首次启动强制改密，属应用层，不在本 plan）。
      - 在文件头用注释写明：默认值仅供本地零依赖启动，**对外暴露前必须改**。
      - Skill: `none`

Exit Criteria:

- [x] `env -i PATH="$PATH" HOME="$HOME" docker compose -f docker-compose.yml config -q` → **exit 0**（复现门禁的调用形状）
- [x] `python3 -m pytest tests/gates/test_zero_dep_boot.py::test_compose_config_valid_with_empty_env -q` → **exit 0（1 passed）**
- [x] ⚠️ **预期之内、不要当故障**：本阶段结束时门禁已绿但名单还没划，所以 `execute.md:3a` 在阶段之间跑的 `{{testCmd}}`
      （即 `check_expected_red.py && pytest tests/unit`）会**退 1** 并报「名单内的门禁却绿了」。Phase 2 划掉那一行后即恢复退 0。
      **不许为了让它中途变绿而提前划名单或改实现**——划名单是 Phase 2 的活，且必须在 Phase 1 前置确认通过之后。
- [x] `! grep -q ':?' docker-compose.yml` → **exit 0**
      - **不写成 `grep -c ':?' … → 0`**：`grep` 无命中时自身退 **1**，一条「成功状态是退 1」的判据在这个仓里就是缺陷
        （草案评审在 plan `…-2341-2` 上抓到过同一类：`ruff check .`）
- [x] 无 owner-doc 更新（归 Phase 3）

### Phase 2 — 把三条规则固化成判据，并划名单

Status: completed
Targets: `tests/unit/test_compose_zero_dep.py`、`tools/gates/expected-red.txt`
Skill: `none`

- Item Types: `Proof`-heavy（5 项中 4 项为 `Proof`，另 1 项为 `Fix`：划名单）
- Prereqs: Phase 1

- [x] `Proof` 写 `tests/unit/test_compose_zero_dep.py`，**只用标准库**（理由见 `## Current Baseline`：不给本机判定面新增任何依赖），
      按原始文本扫描，每条断言都写明失败意味着什么：
      - 全文件无 `${VAR:?}` 形式（规则 1；这正是 Spike 10 的成因）
      - 每个 `${…}` 插值都带 `:-` 默认值（「零必填」的正面表述，比只禁 `:?` 更严）
        - ⚠️ **扫描前必须先剔除 `$$` 转义形式**（独立评审实测：`command: ["sh","-c","echo $${HOME}"]` 经 `config` 后原样是 `echo $${HOME}`，
          那是给容器内 shell 的字面 `$`，不是 compose 插值）。frappe/erpnext 的 `command:` 块大量用它——不剔除，判据会对着正确的 compose 报红
      - 无顶层 `version:` 键
      - 每个 `ports:` 条目的宿主侧都**字面写死** `127.0.0.1`（出处是 §14 的 `⚠️ 附带风险` 段，**不是规则 ③**；防默认口令被暴露到 `0.0.0.0`）
        - **必须字面写死，不许写成 `${BIND:-127.0.0.1}`**：本条判据是对 `docker-compose.yml` 的**静态文本扫描**，
          而 `.env` 能在 `config` 时把变量改掉——变量驱动的绑定地址会「单测绿、真实绑到 0.0.0.0」。
        - 短语法（`- "127.0.0.1:8080:8080"`）与长语法（`host_ip: 127.0.0.1`）**只允许用短语法**，判据据此写；Phase 1 若因某服务不得不用长语法，回来改这条判据，不许在执行时临时放宽
      - 无 `image: …:latest`（tag 必须写死，来自 Phase 1 的 Decision）
      - Skill: `none`
- [x] `Proof` 再加一条**与实现无关的元测试**：`docker-compose.yml` 存在于仓库根目录且非空。
      - 失败意味着有人挪走了它——门禁会红在「文件不存在」，与今天的红因一模一样，这条能先一步指出去哪找。
      - **仓根用 `Path(__file__).resolve().parents[2]` 解析，不用 cwd**：门禁那条本来就是 cwd 相关的，这条元测试的价值恰恰在于不跟着 cwd 一起坏。
      - Skill: `none`
- [x] `Fix` 从 `tools/gates/expected-red.txt` 划掉 `tests/gates/test_zero_dep_boot.py::test_compose_config_valid_with_empty_env` 一行，**与实现同一个提交**。
      - **授权依据（必须逐条核对，不许凭印象）**：该文件已于 `4bbe3f5` 迁出 `tests/gates/`，不在红线 1 范围内；
        人在 `docs/masterplan/STATE.md` §3 的 `[resolved]` 行里裁定「账本允许 loop 在同一提交里划掉已转绿的行」；
        CI 的 `expected-red-ratchet` job 只拦**变长**。名单 8 → 7 是变短，放行。
      - **不得**顺手动另外两行（工作项 8 的），它们仍红。
      - Skill: `none`
- [x] `Proof` 复跑 `python3 tools/gates/check_expected_red.py`，**如实记录退出码与输出原文**。
      - 预期：**exit 0**，计数变为「预期红 7，绿 6，跳过 0」。
      - 若退 1 且报「名单内的门禁却绿了」→ 说明还漏划；若报「名单外的门禁红了」→ 说明本 plan 弄坏了别的门禁，**先原样复跑那条命令再说，不许猜根因**。
      - Skill: `none`
- [x] `Proof` 确认本 plan **没有让工作项 8 的两条意外变绿或变成别的红因**：它们必须仍红在
      `tests/gates/conftest.py:29` 的 `compose_stack` `NotImplementedError`。
      - Skill: `none`

Exit Criteria:

- [x] `python3 -m pytest tests/unit -q` → **exit 0**
- [x] `python3 tools/gates/check_expected_red.py` → **exit 0**，输出计数为「预期红 7，绿 6，跳过 0」
- [x] `git diff <本 plan 开工时的 sha>..HEAD -- tools/gates/expected-red.txt` 显示**只删了一行**，且删的是本 plan 转绿的那一行
      - **必须用区间 diff**：裸 `git diff` 只看未提交改动，本轮改动一提交它就输出为空，判据静音（Phase 3 的红线自查同理，理由一致）
- [x] `python3 -m pytest tests/gates/test_zero_dep_boot.py -q --tb=line` 的两条 error 仍逐字指向 `compose_stack` `NotImplementedError`
- [x] `ruff check agenerp tests/unit` → exit 0
- [x] 无 owner-doc 更新（归 Phase 3）

### Phase 3 — 起栈尝试（证据）、文档、日志

Status: completed
Targets: `docs/context/project-context.md`、`docs/architecture/system-baseline.md`（**只在 §14 后追加一小节**）、`docs/backlog/p0-foundation-roadmap.md`、`docs/logs/2026/08-21.md`
Skill: `none`

- Item Types: `Proof | Fix | Add`
- Prereqs: Phase 1, Phase 2

- [x] `Add` 在 `docs/logs/2026/08-21.md` 与本 plan 的 `## Deferred But Adjudicated` 里**写死落地方式**：
      **本批改动必须经 PR 落地，不得直推 `main`。**
      - 依据：`.github/workflows/gates.yml` 的 `on:` 含 `pull_request`，所以 PR 会让 `gates-l1` **在真正的 2.38.2 runner 上先跑一遍**；
        而划名单不可由 loop 回退（放回名单属变长，`expected-red-ratchet` 无 `Gates-Change-Approved-By:` 即拦）。
        先验证再合并，是把「不可验证 + 不可回退」变成「合并前可见」的唯一办法——也是本 plan 一开头就定下的原则
        （「划名单是单向动作，CI 侧的前提在起草时就查实，不留给执行会话去赌」）在落地环节的同一句话。
      - **这条不是 loop 能自己保证的**：push 与开 PR 属对外动作，本 plan 不做。它的交付物是**把这条要求写在人看得到的地方**——
        log 一次、Deferred 一次——而不是默默指望谁记得。
      - **要给出具体走法，不能只写一句禁止**（评审 nit）：当前分支就是 `main`，且 `git log --oneline origin/main..HEAD` 显示本地 `main`
        已经积了若干**未推送**的提交（起草时至少 `2992c73` / `084c17e` / `6b52f3b`），`build-verify.md` 的提交策略又是往当前分支提交——
        所以本批也会落在本地 `main` 上。可行走法写进 log：`git push origin main:refs/heads/<分支名>` 再开 PR。
      - **并写明一个连带事实**：那个 PR 会**一并带上前几个 plan 的未推送提交**，所以 `gates-l1` 的首次实跑覆盖的不只是本批的活；
        结果无论红绿都要回写进 log，红的那部分要分清是本批引入的还是存量的。
      - Skill: `none`
- [x] `Fix` 修 `docs/backlog/p0-foundation-roadmap.md` 里三处**确认存在的 owner-doc 漂移**：
      `:13`、`:35`、`:78` 仍写着从 `tests/gates/EXPECTED_RED.txt` 划掉，而该文件已于 `4bbe3f5` 迁至 `tools/gates/expected-red.txt`（`ls tests/gates/EXPECTED_RED.txt` → 不存在）。
      - **为什么是本 plan 的活**：roadmap 是本 plan 的 `Source` 与 Owner Doc，而本 plan 正是第一个真的要去划名单的 plan。
        照着 `:78` 执行的会话会去写 `tests/gates/**` 下的文件——那是红线 1 事件。确认存在的 owner-doc 漂移按计划指南规则 14 不可降级为 follow-up，故记 `Fix`。
      - 只改这三处指向，**不动 `## Work Item Status` 块的任何一行**：
        `todo → planned` 已在 Phase 1 首项第 4 点做完（幂等复核），`planned → done` 归 `## Closure Gates`（理由见下一条记录的产物冲突）。
      - Skill: `none`
- [x] `Proof` **不在本阶段**把工作项 3 置为 `done`，并把这处产物冲突如实记进 log（**冲突由人消解，不由本 plan 消解**）：
      - `tools/mission-driver/prompts/execute.md:11` 要求 `EXECUTE` 步在 plan 完成时就去改 roadmap 的工作项；
        而 `docs/backlog/p0-foundation-roadmap.md:9` 写着该文件「由引擎在 **closure 审计通过后**回写」，`:35` 又把 `done` 定义为「完成，**且通过 closure 审计**」。
        Phase 3 跑在 `EXECUTE` 内、在独立关闭审计**之前**——照 `execute.md:11` 做就等于在审计前宣称通过审计。
      - 按 `AGENTS.md` 开头声明的优先级次序（红线 > `docs/masterplan/` 执行协议 > AGENTS.md 其余 > 上游模板默认），
        `execute.md` 是**上游模板默认**，roadmap 是本项目自己的产物且与裁判规则 1/2（「无权自报通过」）同向——**roadmap 胜出**。
      - 因此：`planned → done` 记在 `## Closure Gates`，由关闭审计通过后落地；本阶段只**记录冲突**，不改状态。
      - 依据 §对照表，工作项 3 只绑定 `test_compose_config_valid_with_empty_env` 一条（标题里的「首页降级」划给工作项 8），所以审计通过后置 `done` 是成立的。
      - 附注（不属本 plan 范围）：工作项 1 至今仍是 `todo` 而它的门禁早已转绿并划掉，那是 plan `…-2341-2` 停在 `deferred` 未走关闭审计的后果，**不由本 plan 处置**。
      - Skill: `none`
- [x] `Proof` 在本机跑一次 `docker compose up -d`，**无论结果如何都如实记录命令原文与退出码**，随后 `docker compose down -v` 清理。
      - **这条的交付物是「记录」，不是「绿」**：镜像拉取可能因体积/网络而失败或超时，那也是要写下来的事实。
      - 判定归属写清楚：「起得来且全部 healthy」是**工作项 8** 的门禁（`test_stack_boots_and_all_services_healthy`），
        本 plan 不拿它当 Exit Criteria，也**不得**因为它没绿就去改 compose 以外的任何判据。
      - 失败时的处置：按 `AGENTS.md` 裁判规则 3，原样复跑一次；仍失败则记「未起栈成功 + 原文错误」，并在 Phase 3 的 log 里点名它归工作项 8 处理。**不猜根因、不改门禁。**
      - Skill: `none`
- [x] `Fix` 更新 `docs/context/project-context.md` 的 `Run app locally` 一行：由 `none（无 docker-compose.yml；…）`
      改为真命令 `docker compose up -d`，并按该文件自己的规矩注明它此刻验证到哪一步（`config` 已绿 / 起栈证据见 log）。
      - 这是一处确认存在的活漂移（该行明写「工作项 3 的交付物」，交付后不改就是过期文档），按计划指南规则 14 记 `Fix`。
      - Skill: `none`
- [x] `Add` 在 `docs/architecture/system-baseline.md` §14 之后**追加**一小节，记录三条规则在本仓的落点与判据文件名。
      - **只追加，不改写 §14 已有任何一行**（该文件不在 `docs/masterplan/`，但同一份 Spike 10 结论是后继 plan 的依据，改写等于销毁出处）。
      - Skill: `none`
- [x] `Add` 按 `docs/logs/00-log-writing-guide.md` 写 `docs/logs/2026/08-21.md` 条目：交付内容 + 每条验证命令原文 + 退出码 + commit sha。
      - Skill: `none`
- [x] `Proof` 红线自查，用**区间 diff**（不用 `git diff HEAD`，那只看未提交改动，把改动提交掉就静音了）：
      `git diff --name-only <本 plan 开工时的 sha>..HEAD -- tests/gates/ .github/workflows/ missions/ docs/masterplan/DECISIONS.md tools/gates/check_expected_red.py tools/gates/gate-verify.mjs` → **输出必须为空**；
      再单查一次 `docs/masterplan/`，两条都要是空输出：
      `git diff --name-only <sha>..HEAD -- docs/masterplan/ | grep -v '^docs/masterplan/STATE\.md$' | wc -l` → **0**（除 STATE 外无文件被改）、
      `git diff --numstat <sha>..HEAD -- docs/masterplan/STATE.md | awk '{print $2}'` → **0 或空**（STATE 的删除行数为 0）。
      - 第一条用 `| wc -l → 0` 收口，**不用「grep 无输出」**：`grep` 无命中时自身退 1，那正是本仓已修过两次的判据反转。
      - 第二条**必须用 `--numstat` 数删除行，不要拿 `git diff` 的原始输出去 grep `^-`**：
        评审拿真提交实测过（`084c17e` 对 `STATE.md` 是 +5/-0 的纯追加）——原始 diff 里 git 自己的文件头 `--- a/docs/masterplan/STATE.md` 会被 `^-` 命中，
        而 `grep -v '^---$'` 只排掉「恰好三个短横」的行，排不掉它。结果是**每一次合法的追加都会让判据报红**。`--numstat` 没有这个歧义。
      - **分两条查是有原因的**：把整个 `docs/masterplan/` 塞进「必须为空」那条，会和 Phase 1 停手分支「向 STATE §3 追加一行」直接打架——
        红线 5 的原文是「`STATE.md` **只允许追加**证据行」，追加是允许的，不是禁止的。
        （授权链与 plan `…-2341-2` Phase 3 记的一致：`AGENTS.md` 红线 5 与执行器人格都指示往 STATE §3 写 needs-human，
        次序上高于 `01-EXECUTION-MODEL.md` §1 表里「角色 B 不得手写 STATE」；这处矛盾已登记在交接文档，本 plan 不擅自消解。）
      - Skill: `none`

Exit Criteria:

- [x] `docs/context/project-context.md` 的 `Run app locally` 不再是 `none`，且未引入 `<fill real command>` 占位符
- [x] `git diff <本 plan 开工时的 sha>..HEAD -- docs/architecture/system-baseline.md` 显示**只有新增行**（区间 diff，理由同上）
- [x] `docs/logs/2026/08-21.md` 已更新，含命令原文 + 退出码 + sha，**且写明「本批改动必须经 PR 落地，不得直推 `main`」及其理由**
- [x] 区间红线自查输出为空
- [x] `! grep -q 'EXPECTED_RED' docs/backlog/p0-foundation-roadmap.md` → **exit 0**（三处漂移已修）
      - **模式不带路径前缀**：`:35` 写的是「并从 EXPECTED_RED 划掉」，没有 `tests/gates/` 前缀，带前缀的模式扫不到它（`grep -c 'EXPECTED_RED' …` 今日为 **3**，带前缀只有 2）。
      - **判据写成 `! grep -q`**：`grep -c` 无命中时自身退 1，`… → 0` 的成功态是 exit 1，与 Phase 1 那条已修的缺陷同类。
- [x] roadmap `## Work Item Status` 第 3 项为 `planned`（起草步已写、Phase 1 首项第 4 点复核过；
      `planned → done` 归 `## Closure Gates`，理由见上一项记录的产物冲突）
- [x] owner doc 已更新：`docs/context/project-context.md`、`docs/architecture/system-baseline.md`、`docs/backlog/p0-foundation-roadmap.md`
- [x] 收尾复跑：`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**

## `Plan Status` 由谁写（写死，免得烧循环）

`flows/plan-execution.json` 的步序是 `EXECUTE → CLOSURE_SCRIPT_CHECK →（fail）CLOSURE_AUDIT → BUILD_VERIFY → GATE_VERIFY`。
独立关闭审计是**同一子流程里更靠后的一步**，所以在 `EXECUTE` 内部「审计已通过」永远为假——状态切换不能写在 Phase 里。

- `EXECUTE`（Phase 1–3）：只打勾执行项与 Exit Criteria，`Plan Status` **保持 `active`**，`## Closure Gates` 九框**保持未勾**。
- `CLOSURE_AUDIT`（独立审计会话）：通过 → 勾九框 + 置 `completed` + 补 `## Closure` 证据 + 把 roadmap 工作项 3 由 `planned` 置 `done`（plan `…-2341-3` 正是这么关的）；
  不通过且需改代码 → 保持 `active` 让子流程回 `EXECUTE`；不通过且阻塞于人 → 置 `deferred` 并写明重开条件（plan `…-2341-2` 正是这么停的）。
- ⚠️ **不要为了让 `CLOSURE_SCRIPT_CHECK` 变绿去勾那九个框**——其中「closure audit was independent」「closure evidence exists in files」在 `EXECUTE` 阶段是假的，
  勾上就是自证关闭（违反 `AGENTS.md` 裁判规则 1/2 与计划指南规则 13）。`closureScriptCheck` 判 fail 是**预期**，它正是把流程送进 `CLOSURE_AUDIT` 的那一步。
- ⚠️ `tools/mission-driver/prompts/execute.md:10` 逐字要求「a. Update the plan's `Plan Status` to `completed`」——那是**上游模板默认**，
  按 `AGENTS.md` 开头声明的次序低于裁判规则 1/2（「无权自报通过」），**不执行**。矛盾原文记在此处与 `docs/logs/`，不擅自消解。

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，agent `aab83df862087e9ce`）—— 9 条 blocking。
  要害：① §14 的三条规则被记错（回环绑定出自「⚠️ 附带风险」段而非规则 ③，且规则 ③ 因此没有任何判据）；
  ② roadmap `## Work Item Status` 的状态转换无人认领；③ roadmap `:13`/`:35`/`:78` 仍指向已不存在的 `tests/gates/EXPECTED_RED.txt`——照做即红线 1 事件；
  ④ `grep -c ':?' → 0` 的成功态是 exit 1（与 plan `…-2341-2` 抓到的 `ruff check .` 同类）；
  ⑤ 「`.env` 在场与否不改变 `config` 结果」为假，只有**退出码**不变（实测 `A_PORT=9999` 会改掉 `published`）；
  ⑥ 「CI 只装 pytest 所以要标准库」理由不成立——`tests/unit` 根本不被任何 CI job 执行；
  ⑦ **划名单是单向的**：名单变短后 loop 无法放回（棘轮拦「变长」），而 `gates-l1` 的 runner 是否自带 docker/compose 未经验证；
  ⑧ 文本扫描判据会被 `$$` 转义与 `ports` 长语法误伤；⑨ 两条 `git diff` 判据在改动提交后静音。
  另收下 nit 若干（`version:` 实测只告警不报错、Phase 2 的 `Item Types` 漏 `Fix`、`## Closure` 缺两个子节、`Related` 夸大依赖、红线自查 pathspec 比 Non-Goals 窄、元测试应以 `__file__` 定位仓根、`pyproject.toml:21` 的 `-m 'not live'` 与本门禁标 L1 的潜在矛盾）。
- Revision after iteration 1: §14 三条规则逐字写入，回环绑定归「附带风险」段，规则 ③ 显式移出范围并带重开事件；
  Phase 3 新增三项——**划名单前先确认 CI 假设**（不确认则不划、改走 needs-human 并自置 `deferred`）、修 roadmap 三处指向漂移（`Fix`）、显式认领 `todo → done` 并引 `execute.md:11` 说明执行者是 `EXECUTE` 步；
  `grep -c` 改 `! grep -q`；`.env` 说法收窄为「退出码不变」并据此要求**绑定地址字面写死、不经变量**；标准库理由改为「不给本机判定面新增依赖」；
  文本扫描判据补 `$$` 剔除规则与「只允许短语法」；两条 `git diff` 改区间形式；红线自查 pathspec 加宽到与 Non-Goals 对齐；nit 全部应用。
- Independent draft review iteration 2: **needs revision**（同一独立子代理，重读磁盘版本并实跑）—— 原 9 条中 4 条 RESOLVED、5 条 PARTIALLY；新增 5 条 blocking。
  要害：**NEW-2/3/4 同源** —— 那个「划名单前确认 CI 假设，不确认就走 (b) 分支」的设计本身是坏的：
  它被放在 Phase 3 却要求在 Phase 2 之前跑（`execute.md:5` 按顺序执行阶段）；(b) 分支会让 Phase 2 的 Exit Criteria、Phase 3 的收尾判据、Closure Gate 三处同时不可满足，
  且 `commands.test` 退 1 → `GATE_VERIFY` fail → 重试三轮 → 子流程 `failed`，正是 `…-2341-2` 那个坑；(b) 要往 STATE §3 追加，又与刚加宽的红线自查 pathspec 直接打架。
  **NEW-1**：`grep -c 'tests/gates/EXPECTED_RED' → 0` 又一次退出码反转，且模式漏掉 `:35`（那行没有路径前缀，`grep -c 'EXPECTED_RED'` 今日为 3、带前缀只有 2）。
  **NEW-5**：`todo → done` 写在 Phase 3 太早——roadmap `:9` 说「由引擎在 closure 审计通过后回写」、`:35` 把 `done` 定义为「通过 closure 审计」，
  而 Phase 3 跑在 `EXECUTE` 内；且 `planned` 这个状态从未被用上。另有遗留：Prereqs 与 Phase 2 各残留一句已被推翻的旧说法，`version:` 一项自相矛盾。
- Revision after iteration 2: **把「CI 假设」从分支变成已核实的事实**——起草时用 `gh api` 读 `actions/runner-images` 官方 readme 原文，
  `Ubuntu2404`/`Ubuntu2204` 均列 `Docker Compose 2.38.2` / `Docker Client 28.0.4` / `Docker Server 28.0.4`，写进 `## Current Baseline`（含 2.38.2 vs 本机 v5.0.2 的版本差告诫）；
  (b) 分支整个删除，改为 Phase 1 首项的**前置确认**——「一致就继续，不一致就停手置 `deferred`」，并写明「不许先实现只是不划名单」及其为什么正是 `…-2341-2` 那个坑。
  NEW-2/3/4 随之消解。`grep -c` 改 `! grep -q` 并去掉路径前缀；`todo → done` 移出 Phase 3、改由 `CLOSURE_AUDIT` 落地并逐字记下与 `execute.md:11` 的冲突与优先级裁定，
  工作项 3 在转 `active` 时先置 `planned`；红线自查拆成两条（`DECISIONS.md` 必须为空 + `STATE.md` 只允许新增行），授权链照 `…-2341-2` 引全；
  新增 `## Plan Status 由谁写` 一节写死三种归属；补「记下开工 sha」；补「阶段之间 `{{testCmd}}` 会中途退 1 属预期」；两处旧说法与 `version:` 的自相矛盾一并修掉。
- Independent draft review iteration 3: **needs revision**（同一独立子代理，独立复现了 runner-images 事实：`Ubuntu2404`/`Ubuntu2204` 两份 readme 均 `Docker Compose 2.38.2` / `Docker Client 28.0.4` / `Docker Server 28.0.4`，exit 0）
  —— iteration 2 的 NEW-1..NEW-5 全部 RESOLVED，但新增 5 条：
  **NEW-A** 那条已查实的 runner 事实**没进 `## Current Baseline`**，而 Baseline 仍写着「本机无法验证」并指向已被删除的「Phase 3 首项」；
  **NEW-B** `## Deferred But Adjudicated` 第 4 条整条是孤儿，还在描述已删掉的 (b) 分支；
  **NEW-C** 2.38.2 vs 本机 v5.0.2 的版本差在正文里没有落点、没有缓解，而划名单不可回退；
  **NEW-D** `todo → planned` **没有任何执行者**——`plan-review.md:22` 只改 plan 自己的状态、`closure-audit.md` 里 `roadmap` 出现 0 次、唯一会写的 `execute.md:11` 又被本 plan 明确不采纳，
  于是判据「第 3 项仍为 `planned`」断言了一个没人造出来的状态，且 roadmap 停在 `todo` 会让引擎反复重选工作项 3；
  **NEW-E** `Infrastructure And Config Prereqs` 里那句被推翻的 `.env` 说法第三次残留。
  另有 nit：第二条红线自查是散文不是可跑命令、Baseline 那句「不会因划名单而阻塞于人」与 Phase 1 停手分支需调和。
- Revision after iteration 3: runner-images 的命令与原文输出整段搬进 `## Current Baseline`（含 exit 0 与读取日期），旧的「本机无法验证」段落删除；
  版本差单列一条并**变成可执行约束**——compose 只许用 2.x 以来稳定的键（顶层 `services`/`volumes`/`networks`，服务级十个键的白名单），判据落在 Phase 2 的键白名单断言上，失败特征写明；
  孤儿 Deferred 条目改写为「runner 的 2.38.2 与本机 v5.0.2 的版本差」并给新的重开事件；
  `todo → planned` 由起草步实际写入 + Phase 1 首项加第 4 点幂等复核，并写明「没人写 = 一直 `todo` = 工作项 3 被反复重选」；
  `.env` 那句第三次修正；第二条红线自查给出两条可跑命令；Baseline 那句补上「唯一仍会等人的情形是前置确认不通过」。
- Independent draft review iteration 4: **needs revision**（同一独立子代理）—— NEW-A/B/D/E 已解决，两条新问题：
  **NEW-C 未解决**：三处都声称「判据落在 Phase 2 的键白名单断言上」，而 Phase 2 里**根本没有那条断言**——是个悬空指针。
  **NEW-F**：更要命的是那份白名单本身是编的——评审实测证明它会禁掉 frappe/erpnext 栈**必须**用的 `x-*` 锚点与 `entrypoint`，
  而 `entrypoint`/`env_file`/`user`/`working_dir` 早于 compose 2.x、`x-*` 自 3.4 起就有，「2.x 以来稳定」这个理由根本支撑不了那份排除。
  且 Phase 1 从头到尾没被告知有这条约束——写的人不知道，查的人却要查。
  **NEW-G**：Phase 3 里「不动 Work Item Status（那是引擎/EXECUTE 步的地盘）」与 Phase 1 首项第 4 点自相矛盾。
  nit：第一条红线自查命令在输出正确为空时退 1；第二条的 `^-[^-]` 漏掉以 `--` 开头的删除行（`STATE.md` 里有 3 条 `---`）；`> Source:` 行会在起草步写 `planned` 后过期。
- Revision after iteration 4: **撤回那份编造的白名单**，换成一条站得住的约束——「compose 文件头声明本文件用到的键清单，Phase 2 断言正文不超出它」，
  并在 plan 里写明它**不假装消灭版本差**，只是让「加一个新键」变成必须先改清单的动作；同一段落逐字记下白名单为什么被撤回，免得后继再编一份。
  Phase 1 新增一条写作规则（文件头写清单，按这份 compose 真实需要什么来定，**不许照抄任何预设的安全键名单**），Phase 2 新增对应断言，Deferred 条目同步改写。
  NEW-G 改为指向 Phase 1 第 4 点与 Closure Gates；两条红线自查改用 `| wc -l → 0` 收口、正则改为「先取 `^-` 再排掉 `^---$`」；`> Source:` 行注明会转 `planned`。
- Independent draft review iteration 5: **needs revision**（同一独立子代理）—— NEW-C/F/G 与三条 nit 中的一条已解决，但**判定那条替代约束「largely theatre」，且判得对**：
  「文件头声明键清单 + 断言正文 ⊆ 清单」由 Phase 1 从它刚写的正文里导出、同一提交落地，**按构造即成立**，对版本差是**零保护**；
  **NEW-H** 它还根本不可实现——纯文本扫描分不清顶层键 / 服务级键 / 服务名 / 卷名 / `<<` 合并键，评审在一份带 `x-*` 与 `entrypoint` 的最小 compose 上逐层列出了歧义；
  **NEW-I** 第二条红线自查命令**现在是错的**（不只是松）：评审拿真提交 `084c17e`（对 `STATE.md` 是 +5/-0 的纯追加）实测，
  `grep '^-' | grep -v '^---$'` 会命中 git 自己的文件头 `--- a/docs/masterplan/STATE.md`，于是**每一次合法追加都报红**。
  并指出**真正的 de-risk 从未被裁定**：`gates.yml` 的 `on:` 含 `pull_request`，经 PR 落地就能让 `gates-l1` 在真正的 2.38.2 runner 上先跑一遍再合进 `main`。
- Revision after iteration 5: **两版缓解全部撤回**（Phase 1 的写作规则、Phase 2 的断言、Deferred 的描述一并删除/改写），
  `## Current Baseline` 改为直说「这条风险在本机没有缓解措施」，并把两次失败的尝试与证据留在原地，免得后继发明第三版；
  采纳评审指出的真 de-risk：Phase 3 新增一项，把「**本批改动必须经 PR 落地，不得直推 `main`**」写进 log 与 Deferred，并写明开 PR 属对外动作、不由本 plan 执行；
  第二条红线自查改用 `git diff --numstat … | awk '{print $2}'` → 0；「记两个 compose 版本」补注「这不是缓解措施」。
- Independent draft review iteration 6: **accept**（同一独立子代理，agent `aab83df862087e9ce`）—— 撤回是干净的
  （`grep '键清单\|白名单\|清单闭合\|⊆'` 只剩 Baseline 的撤回记录、Draft Review Record 的历史、Deferred 的说明，无孤儿引用）；
  NEW-I 的新命令在**三个真实提交**上验证通过（`084c17e` +5/-0 → 0、`8d73ee5` +3/-1 → 1、无改动 → 空）；
  PR 前提复核属实（`gates.yml` 的 `on:` 里 `pull_request` 无条件）；每条判据可达且非显然的都被独立复跑过。
  评审结论原文：「六轮下来这个 plan 没有红线隐患、没有无主的状态转换、没有编造的事实（两次编造都已撤回且证据留在原地免得后继重新发明）、
  每条判据可达且都被独立复跑过，唯一那处不可逆的残余被归为 `watch-only residual` 并配齐了失败特征、恢复路径与重开事件——
  这在 Anti-Slacking Rule 之下是一次正当的裁定。」
  另给三条非阻塞 nit：PR 那条只写了禁止没给走法（且本地 `main` 已积压未推送提交）、重开事件会连带覆盖前几个 plan 的活、PR 项的第二个交付物在执行前就已半满足。
- Revision after iteration 6: 前两条 nit 采纳——Phase 3 的 PR 项补上具体走法（`git push origin main:refs/heads/<分支名>` 再开 PR）
  与「那个 PR 会一并带上前几个 plan 的未推送提交，回写时要分清红的是本批引入的还是存量的」，Deferred 的重开事件同步补注。
  第三条不改：那是文档类交付项的正常形态（Deferred 小节由起草写、log 由执行写），改成两个框反而虚增。
- **共识达成，转 `active`。**

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned
- [x] verification has run：`python3 tools/gates/check_expected_red.py`（exit 0）/ `python3 -m pytest tests/unit -q`（exit 0）/ `python3 -m pytest tests/gates/test_zero_dep_boot.py::test_compose_config_valid_with_empty_env -q`（exit 0）/ `ruff check agenerp tests/unit`（exit 0）/ `docker compose up -d`（如实记录）
- [x] scoped verification is not conflated with full verification —— 本仓无全量套件（无 build、无 typecheck，L2 门禁未解锁），上列即当前可跑的全部；「栈起得来且 healthy」**未验证**，归工作项 8
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [x] closure audit was independent
- [x] closure evidence exists in files
- [x] 独立关闭审计通过**之后**，`docs/backlog/p0-foundation-roadmap.md` 的工作项 3 由 `planned` 置为 `done`
      （不在 Phase 3 做，理由见 Phase 3 对应项记录的产物冲突）

## Deferred But Adjudicated

### `compose_stack` fixture 与「全部服务 healthy / 首页显示 AI 能力未配置」

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: roadmap §对照表把这两条断言明确划给**工作项 8**；其 fixture 在 `tests/gates/conftest.py`，属红线 1，loop 不得改。
- Successor Required: `yes` —— 工作项 8 的 plan
- 重开事件：工作项 8 开工时；届时把 `conftest.py` 的 `raise` 换成真实现需要人的 `Gates-Change-Approved-By:` 提交，本 plan 已在 log 里点名这件事。

### 把 `docker compose config` 接进 `missions/p0-foundation.json` 的 `commands`

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: `missions/**` 是角色 B 禁区（`01-EXECUTION-MODEL.md` §1 禁止项 ③），loop 无权改；且该判据已由门禁本身覆盖，接不接进 `commands` 不改变判定结果。
- Successor Required: `no`（人动作）
- 重开事件：人决定把 docker 相关命令纳入 `GATE_VERIFY` 时。

### §14 规则 ③「前置检查属于 verify 脚本，不属于启动路径」没有判据

- Classification: `watch-only residual`
- Why Not Blocking Closure: 本仓此刻既没有 verify 脚本，也没有任何启动路径上的前置检查——规则 ③ 现在**没有对象**。
  给无对象的规则写断言只能写成同义反复，那是假判据，比没有更坏。规则 ① ② 与「附带风险」的回环绑定本 plan 已全部落成可执行判据。
- Successor Required: `no`
- 重开事件：仓里第一次出现 verify / 就绪检查脚本时（或工作项 8 给 `compose_stack` 加启动前置检查时），把规则 ③ 补成断言。

### runner 的 compose 2.38.2 与本机 v5.0.2 的版本差

- Classification: `watch-only residual`
- Why Not Blocking Closure: 「runner 有没有 compose」已由起草时的 `gh api` 查实（见 `## Current Baseline`），不再是未知数。
  剩下的是**版本差，且它在本机没有缓解措施**——这一条就是照实记着，不粉饰。
  起草过程试过两版缓解，都被独立评审实测否掉并撤回（一份编造的「2.x 稳定键白名单」，一条按构造即成立的「键清单闭合」断言），
  两次的证据都留在 `## Current Baseline` 里，免得后继再发明第三版。
  **降低它的唯一办法不在本机，在落地方式**：经 PR 落地，让 `gates-l1` 在真正的 2.38.2 runner 上先跑一遍再合进 `main`
  （`gates.yml` 的 `on:` 含 `pull_request`）。该要求已写进 Phase 3 与 `docs/logs/`；**开 PR 属对外动作，不由本 plan 执行**。
- Successor Required: `no`
- 重开事件：首次 push 后 `gates-l1` 的实跑结果出来时（**无论红绿都要回写进 log**）；若红，恢复需人带 `Gates-Change-Approved-By:` 把该行放回名单。
  ⚠️ 那次实跑会**一并覆盖前几个 plan 的未推送提交**（本地 `main` 已积压若干），所以回写时要分清红的是本批引入的还是存量的。
  - **执行期更正（2026-08-21，Phase 3 实测）**：这个前提已经过期。`git fetch origin` 后
    `git log --oneline origin/main..HEAD` **只有本批的 `327bb01` 一条**，`origin/main` 已在 `fc0c823`——
    前几个 plan 的提交都推过了。所以那次 `gates-l1` 实跑**只覆盖本批**，红了就是本批引入的，不必再分辨存量。

## Closure

Status Note: 独立关闭审计（CLOSURE_AUDIT 步，独立子会话）**不采信 plan 里的 `[x]`**，逐条读活代码与活文档，
并把每条验证命令原样复跑、退出码单独取 `$?`（不经管道）。全部与 plan 声称一致，故关闭。
审计基线 **HEAD `f53fe51`**（实现提交 `327bb01`，文档提交 `f53fe51`；开工 sha `fc0c823`）。

Closure Audit Evidence:

- Auditor / Agent: 独立关闭审计子会话（`MISSION_DRIVER:2026-08-21-113253-mission-driver`，与起草/执行会话不同），非自审。
- 基线 sha: `f53fe51`（`git rev-parse --short HEAD`）
- 原样复跑（命令原文 + 退出码）：

  | 命令 | 退出码 | 关键输出 |
  | --- | --- | --- |
  | `python3 tools/gates/check_expected_red.py` | **0** | `门禁 13 项：预期红 7，绿 6，跳过 0` / `✅ 与预期红名单完全一致` |
  | `python3 -m pytest tests/unit -q` | **0** | `50 passed` |
  | `python3 -m pytest tests/gates/test_zero_dep_boot.py::test_compose_config_valid_with_empty_env -q` | **0** | `1 passed` |
  | `ruff check agenerp tests/unit` | **0** | `All checks passed!` |
  | `env -i PATH="$PATH" HOME="$HOME" docker compose -f docker-compose.yml config -q` | **0** | 无输出 |
  | `! grep -q ':?' docker-compose.yml` | **0** | 无输出 |
  | `! grep -q 'EXPECTED_RED' docs/backlog/p0-foundation-roadmap.md` | **0** | 无输出（三处漂移确已修到 `tools/gates/expected-red.txt`） |
  | `python3 -m pytest tests/gates/test_zero_dep_boot.py -q --tb=line` | 非 0（**预期**） | `1 passed, 2 errors`；两条 error 仍逐字为 `NotImplementedError: compose_stack 尚未实现`，红因未被本 plan 改变 |

- 红线自查（区间 diff，基线 `fc0c823..HEAD`，与 Phase 3 判据同形）：
  - `git diff --name-only fc0c823..HEAD -- tests/gates/ .github/workflows/ missions/ docs/masterplan/DECISIONS.md tools/gates/check_expected_red.py tools/gates/gate-verify.mjs | wc -l` → **0**
  - `git diff --name-only fc0c823..HEAD -- docs/masterplan/ | wc -l` → **0**（本轮连 `STATE.md` 都未动）
  - `git diff --numstat fc0c823..HEAD -- docs/architecture/system-baseline.md` → **`28  0`**（纯追加，§14 无一行被改写）
  - `git diff --stat fc0c823..HEAD` 的全部落点：`.env.example` / `docker-compose.yml` / `docs/architecture/system-baseline.md` /
    `docs/context/project-context.md` / `docs/logs/2026/08-21.md` / 本 plan / `tests/unit/test_compose_zero_dep.py` /
    `tools/gates/expected-red.txt`(-1 行) —— 无一处越红线。
- 反空壳复核（不只看签名，看运行时是否真被调用）：
  - `docker-compose.yml`（234 行）是 frappe/erpnext 真实多服务栈（`configurator` / `db` / `redis-cache` / `redis-queue` /
    `backend` / `frontend` / `websocket` / queue worker / scheduler / 建站 init），**不是**为让 `config` 退 0 而写的单服务占位——
    与 Phase 1 `Decision` 否决备选 (b) 的记录一致；镜像 tag 全部写死（`frappe/erpnext:v15.119.3` / `mariadb:10.6` / `redis:6.2-alpine`），无 `latest`。
    它被门禁 `test_compose_config_valid_with_empty_env` 在每次 `check_expected_red.py` 里真实执行，不是死文件。
  - `tests/unit/test_compose_zero_dep.py`（205 行）**逐条断言、无空 body、无 `pass` 占位**：文件存在性（用
    `Path(__file__).resolve().parents[2]` 解析仓根，不跟 cwd 走）、禁 `${VAR:?}`、每个插值必须带 `:-`、
    AI 三变量默认必须为空串、发布端口宿主侧字面 `127.0.0.1`、只许短语法、无顶层 `version:`、无 `:latest`。
    `$$` 转义已在 `_text_without_escapes()` 里先行剔除（评审 iteration 中实测要求），断言不会对着正确的 compose 报红。
    它随 `python3 -m pytest tests/unit -q` 在 `GATE_VERIFY` 每轮复跑，是活判据。
  - **判据非同义反复（审计当场实跑的反证，不是推理）**：把 `docker-compose.yml` `:222` 的宿主侧临时改成 `0.0.0.0:` 后
    `python3 -m pytest tests/unit/test_compose_zero_dep.py -q --tb=line` → **`1 failed, 9 passed`**，失败原文逐字为
    `test_compose_zero_dep.py:156: AssertionError: 端口条目 '0.0.0.0:${AGENERP_HTTP_PORT:-8080}:8080' 的宿主侧不是字面的 127.0.0.1。`
    随即原样还原（`git diff --stat docker-compose.yml` → 空，`python3 -m pytest tests/unit -q` → exit 0）。
    → 判据对实现有真实约束，不是「按构造即成立」的那种假判据。
- 五点一致性复核：`Plan Status: completed` · Phase 1/2/3 `Status: completed` 且执行项与 Exit Criteria 全 `[x]` ·
  `## Closure Gates` 十框全 `[x]` · 本节证据落盘 · `docs/logs/2026/08-21.md` 有对应条目（含开工 sha `fc0c823`、
  各命令原文与退出码、`docker compose up -d` 的如实记录与「必须经 PR 落地」条款）——五处一致，无 `completed` 配 `draft` 的错配。
- Deferred 诚实性复核：四条 `Deferred But Adjudicated` 全部有归属与重开事件，**无一条是在藏本 plan 范围内的活缺陷**——
  工作项 8 的两条门禁由 roadmap §对照表明确划走、`missions/**` 属角色 B 禁区、§14 规则 ③ 在本仓当前**无对象**（无 verify 脚本、无启动路径前置检查）、
  compose 版本差已如实记为 `watch-only residual` 并配齐失败特征与恢复路径。规则 ① ② 与「附带风险」的回环绑定都已落成可执行判据，未降级。
- 验证范围声明：**verification scope limited**——本仓无全量套件（无 build、无 typecheck，L2 门禁未解锁），上表即当前可跑的全部。
  「栈起得来且全部 healthy」**未验证**，按 roadmap §对照表归工作项 8；本机 `docker compose up -d` 的尝试与退出码已如实写入 log，是证据不是判据。
- 审计后落地动作：`docs/backlog/p0-foundation-roadmap.md` `## Work Item Status` 第 3 项由 `planned` 置 `done`
  （依 roadmap `:9`「由引擎在 closure 审计通过后回写」与 `Status values` 表对 `done` 的定义；`execute.md:11` 的上游模板默认按 `AGENTS.md` 优先级次序不采纳，冲突原文已记在 Phase 3 与 log）。

Follow-up:

- **本批必须经 PR 落地，不得直推 `main`**：`git push origin main:refs/heads/<分支名>` 再开 PR，让 `gates-l1` 在真正的 compose 2.38.2 runner 上先跑一遍。
  开 PR 属对外动作，不由 loop 执行。实跑结果**无论红绿都要回写进 `docs/logs/2026/08-21.md`**。
  （`git fetch origin` 后 `git log --oneline origin/main..HEAD` 实测只有本批提交，红了就是本批引入的。）
- `pyproject.toml:21` 写「L1 快门禁跑 `-m 'not live'`」而本条门禁所在文件带 `live` marker——今日不咬人（判定器不传 `-m`），
  已在 `## Current Baseline` 登记，触发条件：有人给 `check_expected_red.py` 加上 `-m` 过滤时。
- 工作项 1 至今仍是 `todo` 而其门禁早已转绿并划掉（plan `…-2341-2` 停在 `deferred` 未走关闭审计的后果）——**不属本 plan 范围**，留给人处置。
