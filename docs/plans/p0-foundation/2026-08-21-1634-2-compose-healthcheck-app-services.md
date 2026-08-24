# 2026-08-21-1634-2 应用侧服务 healthcheck —— 让「全部服务 healthy」先变成可判定的

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 8. 零依赖启动进 CI（L2 慢门禁）—— **只做「healthy 可判定」这半，不解锁 L2 门禁，不做首页文案**
> Last Reviewed: 2026-08-21
> Source: `2026-08-21-1022-1-zero-dep-boot-compose.md` 的 `## Deferred But Adjudicated` 首条（successor required = yes）·`docs/backlog/p0-foundation-roadmap.md` Work Item Status 第 8 项（`todo`）·`docs/masterplan/02-WBS.md` **P0.7**
> Related: `2026-08-21-1022-1-zero-dep-boot-compose.md`（**硬前置，已 completed**：本 plan 改的就是它交付的 `docker-compose.yml`）·`2026-08-21-1634-1-seed-dataset-deterministic.md`（同批第 1 顺位，与本 plan 无依赖，可并行）
> Audit: required

## Current Baseline

以下每条都在 `5d8022e` 上实测读出。

**已就位：**

- `docker-compose.yml` 存在（工作项 3 交付），11 个服务：`db` / `redis-cache` / `redis-queue` / `configurator` / `create-site` /
  `backend` / `websocket` / `queue-short` / `queue-long` / `scheduler` / `frontend`。镜像 `frappe/erpnext:v15.119.3`、`mariadb:10.6`、`redis:6.2-alpine`，全部钉版本。
- L1 门禁 `tests/gates/test_zero_dep_boot.py::test_compose_config_valid_with_empty_env` **已绿**（工作项 3 关闭时从 `expected-red.txt` 划掉）。
- `tests/unit/test_compose_zero_dep.py`（205 行）盯着 compose 的 10 条断言，工作项 3 关闭时做过 9 种缺陷的变异验证，全部被抓。
- 本机 `docker` 在 `/usr/local/bin/docker`，`docker compose version` → **v5.0.2**。
- 2026-08-21 的实测起栈记录（`docs/logs/2026/08-21.md:272-293`，是**证据不是判据**）：
  `AGENERP_HTTP_PORT=18080 docker compose up -d` → **exit 0**，11 个服务全起（`configurator` / `create-site` 两个一次性容器 `Exited (0)`），
  `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/api/method/ping` → **200**；收尾 `docker compose down -v` → exit 0。

**缺口（这就是本 plan 的全部理由）：**

- `grep -c "healthcheck:" docker-compose.yml` → **3**。只有 `db`（`:59`）、`redis-cache`（`:72`）、`redis-queue`（`:85`）有 healthcheck。
  `backend` / `websocket` / `queue-short` / `queue-long` / `scheduler` / `frontend` **一个都没有**。
- 后果是同一份日志里逐字写下的：

  > 本仓 compose 只给 db/redis 写了 `healthcheck`，应用侧服务的 healthy 根本还不可判

  也就是说门禁 `test_stack_boots_and_all_services_healthy` 即便 fixture 被解锁，**此刻也没有东西可断言**——
  Docker 对没有 healthcheck 的容器不报告健康状态，`--wait` 对它们只等到 running。
- `frontend` 的 `depends_on` 用的是 `condition: service_started`（`:225,227`）——**启动即算满足**。
  日志里那次 `frontend` 陷入重启循环、逐字报 `host not found in upstream "backend:8000"`，正是「started ≠ 可用」的实证。
- `expected-red.txt` 里工作项 8 的两条仍在名单内：
  `test_zero_dep_boot.py::test_stack_boots_and_all_services_healthy`、`::test_homepage_states_ai_disabled_instead_of_crashing`。
- `compose_stack` fixture 在 `tests/gates/conftest.py` 抛 `NotImplementedError`，属红线 1；
  `docs/masterplan/STATE.md` §3 有一行 `[open]` 登记了这件事，四个处置项 (a)/(b)/(c)/(d) 只有人能选。

**所以本 plan 的定位要说准：** 它**不解锁**工作项 8 的门禁（那要人先动 `conftest.py`），
它做的是把那条门禁从「解锁了也没东西可断言」变成「解锁即可断言」。这两件事**不能混为一谈**，
本 plan 的 Exit Criteria 里不含任何一条门禁转绿。

## Goals

- 给应用侧服务补上真实的 `healthcheck`，使 `docker compose up -d --wait` 能对 **Phase 2 定义的 healthy 集合**
  做出 healthy/unhealthy 判定。该集合的**下限是 `backend` / `websocket` / `frontend` 三个**（低于这个下限即本 plan 失败）；
  三个 worker（`queue-short` / `queue-long` / `scheduler`）是否进集合由 Phase 1 的实测结果决定，
  **进不了就明确登记为「不可判」**，不用假探针凑数。
- 把 `frontend` 的 `depends_on` **逐服务**收紧：凡是落了 healthcheck 的依赖改成 `service_healthy`，
  消掉日志里实证过的那个重启循环；没落 healthcheck 的保持 `service_started` 并就地注明原因。
  （`service_healthy` 指向一个没有 healthcheck 的服务时 `config -q` 仍退 0，但 `--wait` 永远收敛不了——见 Phase 3。）
- 本机实证：空 AI 环境变量下起栈 → `--wait --wait-timeout 300` 退 0 → **healthy 集合内的服务全部 healthy** →
  首页 200 → 收尾清干净。命令原文与退出码全部落 `docs/logs/`。
- 不破坏既有 L1：`test_compose_config_valid_with_empty_env` 与 `tests/unit/test_compose_zero_dep.py` 的 10 条断言保持绿。
- 把「本仓所谓『全部服务 healthy』到底指哪些服务、用什么探针、超时多少」写进 owner doc，
  让工作项 8 的门禁将来有一个**成文的、可对照的**判定口径，而不是各人各解。

## Non-Goals

- **不改 `tests/gates/**` 任何文件**，包括 `conftest.py` 里的 `compose_stack`。红线 1。
- **不改 `.github/workflows/**`**。给 CI 加一个跑 docker 的 L2 job 是工作项 8 剩下的一半，
  且它牵涉 runner 上的 compose 2.38.2 与本机 v5.0.2 的版本差（`2026-08-21-1022-1` 已登记为 watch-only residual）。红线 2 只禁「变松」，但本 plan 仍不碰，理由是**结果面要单一**。
- **不做首页「AI 能力未配置」文案**（门禁 `test_homepage_states_ai_disabled_instead_of_crashing`）。
  那是应用层交付，要往站点里装东西，与本 plan 的 compose 编排面不是同一个结果面。
- 不声称工作项 8 的任何门禁转绿；不从 `expected-red.txt` 划掉任何一行。
- 不改 `missions/**`、不改 `docs/masterplan/` 已有行、不动本机那个与本仓无关的 frappe 栈（`docker-frontend-1`）。
- 不引入新镜像、不改已钉的镜像版本。

## Task Route

- Type: `implementation-only change`（编排层，判据由 owner doc 与既有门禁给定）
- Owner Docs: `docs/architecture/system-baseline.md` §14 / §14.1 ·`docs/masterplan/02-WBS.md` P0.7 ·`docs/backlog/implementation-roadmap.md` P0 交付表「零依赖启动 CI」行
- Skill Selection Basis: `docs/skills/` **存在且有 15 份技能 + 一张 Skill Registry**（起草时已读 `docs/skills/README.md`）。
  逐条比对：`plan-audit-prompt.md` 用于**本草案的独立评审**（已在 `## Draft Review Record` 用上）、
  `closure-audit-prompt.md` 用于**关闭审计**（Closure Gates 点名）——都不是执行期的方法技能；
  `code-quality-audit-prompt.md` / `code-refactor-*` 针对既有代码行为，本 plan 改的是 compose 编排的 YAML；
  `bug-diagnosis-prompt.md` 需要一个已存在缺陷，而「frontend 重启循环」的原因已在日志里查实、无需再诊断。
  → 按 `docs/skills/README.md` Skill Routing Rule 第 5 条，执行期各阶段记 `Skill: none`。
  （⚠️ `docs/context/project-context.md` 的 Optional Layers 七个框全未勾而七个目录全存在——这处漂移由同批第 1 顺位的
  plan `2026-08-21-1634-1` 的 Phase 4 `Fix` 负责改正，本 plan 不重复动它。）

## Infrastructure And Config Prereqs

- 需要本机 docker daemon 在跑。**已实测在**：`/usr/local/bin/docker`，compose v5.0.2。
- **端口冲突是已知事实，不是意外**：本机另有一个与本仓无关的 frappe 栈 `docker-frontend-1` 占着 `0.0.0.0:8080`
  （`docs/logs/2026/08-21.md:283-285` 实测）。本 plan 全程使用 `AGENERP_HTTP_PORT=18080` 这个 compose 自带的逃生口，
  **不得停止或删除那个无关栈**。
- 需要拉镜像（首次约数 GB）。若网络不可达导致拉取失败，按裁判规则 3 原样复跑一次；仍不行则记「不可复现/环境阻塞」并停在 Phase 1，不猜根因。
- 回滚策略：本 plan 只改 `docker-compose.yml` 一个文件 + 新增文档小节，`git revert` 即可完全撤销。
  运行期回滚是 `docker compose down -v`（实测退 0）。
- **落地方式：本批改动必须经 PR 落地，不得直推 `main`。** 前一个 plan（`2026-08-21-1022-1`）已把这条写进
  `docs/logs/2026/08-21.md` 的「落地方式」段，理由是 `gates.yml` 的 `on:` 无条件含 `pull_request`，
  PR 会让 `gates-l1` **在真正的 compose 2.38.2 runner 上先跑一遍**。
  对本 plan 这条理由**只成立一半、但成立的那半更重要**：本 plan 不缩短 `expected-red.txt`，
  所以「单向棘轮不可回退」那半不适用；然而本 plan 往 compose 里加的是 `healthcheck:` 与 `condition: service_healthy`
  这些**从未被 2.38.2 解析过的新键**——版本差在这里是真实敞口，只有 PR 能在合并前看见它。
  具体走法（当前分支就是 `main`）：`git push origin main:refs/heads/<分支名>` 再开 PR。
  **开 PR 属对外动作，不由本 plan 执行**——本 plan 只把要求写死在 Closure Gates 里。

## Execution Plan

### Phase 1 - Explore：镜像里有什么探针、各服务怎么判活

Status: completed
Targets: 无代码改动（只跑命令、只记录）
Skill: `none`

- Item Types: 全部 `Proof`（这一阶段只产出实测事实）
- Prereqs: docker daemon 在跑

- [x] 起栈拿现场：`AGENERP_HTTP_PORT=18080 docker compose up -d` → 记录退出码；`docker compose ps -a` 抄下全表。
  - Skill: `none`
- [x] **改动前的 `--wait` 基线**：在**未修改**的 `docker-compose.yml` 上跑
      `AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300` → 记录退出码与耗时。
      没有这个「之前」的数，Phase 4 若 `--wait` 非 0，就分不清是「我加的 healthcheck 写错了」还是
      「`--wait` 在本机 compose v5.0.2 + 本栈上从来就收敛不了」。
      顺带查实一个本 plan 依赖但**尚未验证**的假设：`--wait` 对 `configurator` / `create-site` 这两个
      跑完即退的一次性容器是当作 `completed successfully` 放行，还是会把它们判成失败。
  - Skill: `none`
- [x] **分支裁定（本 plan 的止损阀，不许跳过）**：若上一条的「改动前 `--wait` 基线」**非 0**，
      先按裁判规则 3 原样复跑一次；仍非 0 就地归类，并按类走：
      · **A 类「一次性容器被判失败」**——`configurator` / `create-site` 明明 `Exited (0)` 却被 `--wait` 记成失败。
        这一类与本 plan 要加的应用侧 healthcheck **无关**，是编排面的既有缺口：
        **不得**为了让 Phase 4 退 0 去动一次性容器的语义（套假 healthcheck、改 `restart`、把它们从栈里摘出去，都算）。
        如实记进 `docs/logs/`，往 `STATE.md` §3 **追加**一条 needs-human，**停在 Phase 1，不进 Phase 2**。
      · **B 类「下限三服务里有一个查实没有可用探针」**（`backend` / `websocket` / `frontend`）——
        Goals 写死的下限即不可达，同样如实记录 + `STATE.md` §3 追加 needs-human，**停在 Phase 1**。
      · **C 类「非 0 的原因就是应用侧没有 healthcheck 可等」**——这正是本 plan 要修的，照常进 Phase 2。
      三类都不许猜：归类结论必须引用命令原文与输出片段；归不进任何一类就按 A 类处理（停下等人）。
  - Skill: `none`
- [x] 探针工具盘点：在 `backend` 容器里逐个试 `curl` / `wget` / `python3` 是否存在（`docker compose exec -T backend sh -lc 'command -v curl wget python3'`），
      **记录原文输出**。`frappe/erpnext:v15.119.3` 里有没有 curl 是事实问题，不是常识问题——不许照抄别处的 compose 模板假设它有。
  - Skill: `none`
- [x] 各服务的判活端点实测，每条都记命令原文 + 退出码 + 输出片段：
      `backend` → 容器内打 `http://127.0.0.1:8000/api/method/ping`。
      ⚠️ **这里有一个不是超时的坑，先说破**：Frappe 的 gunicorn 按 **Host 头**解析站点，
      容器内打 `127.0.0.1` 会被解析成一个名叫 `127.0.0.1` 的站点，那个站点不存在——
      **再大的 `start_period` 也救不了**。若探针红了，先试 `-H "Host: frontend"` 或改用 `bench` 侧的自检，
      **不要条件反射地去加 `start_period`**；
      `websocket` → 容器内打 `http://127.0.0.1:9000/`（记录它返回什么，socket.io 的根路径不一定是 200）；
      `frontend` → 容器内打 `http://127.0.0.1:8080/api/method/ping`；
      `queue-short` / `queue-long` / `scheduler` → **没有监听端口**，先查清 `bench` 有没有可用的自检子命令、
      以及 rq worker 的心跳落在 redis 的哪个 key 上。
  - Skill: `none`
- [x] 收尾 `docker compose down -v` → 记录退出码；`docker ps -a` 确认那个无关的 `docker-frontend-1` 未受影响。
  - Skill: `none`

Exit Criteria:

- [x] 六个应用侧服务各有一条「可用的判活手段」或「查实没有可用手段」的结论，**每条都带命令原文与退出码**
- [x] 结论写进 `docs/logs/`；若某条实测失败，按裁判规则 3 原样复跑一次后如实记「复现 / 不可复现」，**不写猜测的根因**
- [x] 本机无关栈未受影响（`docker ps -a` 输出抄下）
- [x] **改动前的 `--wait` 基线有退出码原文**；若非 0，已完成 A/B/C 归类并留下证据
      （落在 A 类或 B 类时本 plan **停在 Phase 1**，Phase 2–5 不启动，`STATE.md` §3 已追加 needs-human）
- [x] No owner-doc update required（本阶段只产出实测记录，判定口径的落盘在 Phase 2）

### Phase 2 - Decision：本仓「全部服务 healthy」的定义

Status: completed
Targets: `docs/architecture/system-baseline.md`（在 §14.1 之后追加 §14.2）
Skill: `none`

- Item Types: `Decision`
- Prereqs: Phase 1

- [x] **Decision：无端口的三个 worker（`queue-short` / `queue-long` / `scheduler`）怎么判 healthy。**
      候选：
      (a) 不给它们 healthcheck，把定义收窄为「**有 healthcheck 的服务全部 healthy** + 其余长驻服务 running + 两个一次性容器 `Exited (0)`」；
      (b) 用 Phase 1 查到的 `bench` 自检子命令做 healthcheck；
      (c) 探 redis 里的 rq worker 心跳 key；
      (d) 退化成 `pgrep` 进程存活探针。
      **(d) 是要警惕的那一个**：进程活着不等于 worker 在消费队列，它会产出一个永远绿的假判据——本仓反复禁止的东西。
      倾向由 Phase 1 的实测结果决定；**若 (b)/(c) 都不可得，选 (a) 并把「worker 的 healthy 不可判」如实写进 owner doc**，
      而不是用 (d) 把它糊过去。
      残余风险：选 (a) 会让工作项 8 的门禁将来只能断言一个收窄过的集合——**这条必须写进 owner doc 和门禁提案里**，
      否则将来有人会以为「全部 healthy」真的是全部。
  - Skill: `none`
- [x] **Decision：`interval` / `timeout` / `retries` / `start_period` 取值。**
      约束是硬的：`create-site` 建站要跑一段时间，`backend` 在建站完成前打 ping 必然失败——
      `start_period` 给不够就会把「还没起完」误判成 unhealthy。取值要有理由，理由写进 owner doc。
      **候选不止「把 `start_period` 调大」一条**：`backend_defaults` 此刻只 `depends_on` `configurator`
      （`condition: service_completed_successfully`），**并不等 `create-site`**——
      所以另一条候选是给它补上 `create-site: condition: service_completed_successfully`，
      把「建站耗时」从探针的 `start_period` 里挪出去。代价是 `backend_defaults` 是 `backend` 与三个 worker
      共用的锚点，改它会一并改掉 worker 的启动次序，且这是本 plan 之外的编排语义变更。
      两条候选选哪条、还是都不选，都要写明理由，**不许默认落到第一条上**。
      残余风险：本机与 CI runner 的机器速度不同，本机够用的 `start_period` 在 runner 上可能不够；
      这一条属工作项 8 剩下那一半的事，本 plan 只如实登记。
  - Skill: `none`
- [x] **Decision：零依赖红线怎么守住。**
      `docker-compose.yml` 文件头 `:10` 逐字写着「外部能力（LLM 等）缺失是『未配置』状态，不是错误状态 ——
      空默认值，且**不进 healthcheck/command 的成败路径**」，`:42` 又重复一次，且 `tests/unit/test_compose_zero_dep.py`
      有断言盯着。新增的 healthcheck **一个 AI 相关变量都不许出现在里面**。
      这是既有约束，不是新决定——记在这里是为了让执行期有一条明确的自检项。
  - Skill: `none`

Exit Criteria:

- [x] 三条 Decision 有结论、有备选、有残余风险
- [x] `docs/architecture/system-baseline.md` 新增小节 **「§14.2 本仓栈的健康判定口径」**（接在既有 §14.1 之后；
      §3 是「分层架构」，健康判定塞进去会错位），
      写清：**哪些服务在「全部 healthy」的集合里、各自用什么探针、超时取值与理由、以及哪些服务的健康不可判**
- [x] `docs/logs/` 追加本阶段条目

### Phase 3 - Add：落 healthcheck 并收紧依赖

Status: completed
Targets: `docker-compose.yml`
Skill: `none`

- Item Types: `Add`
- Prereqs: Phase 2

- [x] 按 Phase 2 的结论给应用侧服务补 `healthcheck`（能判的都补，判不了的按 (a) 明确不补并在文件里就地写一行注释说明为什么）。
  - Skill: `none`
- [x] `frontend.depends_on` **逐服务**收紧：**只有上一条里真的落了 healthcheck 的服务**才由
      `condition: service_started` 改成 `condition: service_healthy`；没落 healthcheck 的**保持 `service_started`**，
      并在该行就地写一行注释说明原因，同时记进 owner doc。
      ⚠️ 这个条件不能省：实测过一份合成 compose——`service_healthy` 指向一个没有 healthcheck 的服务时，
      `docker compose config -q` 仍然 **退 0**（静态校验抓不到），但 `up -d --wait` **永远收敛不了**，
      会把 Phase 4 的判据卡死在超时上。
      这一条直接对应日志里实证过的 `host not found in upstream "backend:8000"` 重启循环。
  - Skill: `none`
- [x] 自检（先自检省一轮往返，全部对应 `tests/unit/test_compose_zero_dep.py` 的既有断言）：
      新增内容里不出现任何 AI 相关变量；不新增顶层 `version:`；不引入 `latest` tag；不改任何已钉的镜像版本；
      不改 `ports` 的回环绑定写法。
      ⚠️ **最容易被手写探针字符串踩到的是插值那两条，单列出来**：
      `test_no_hard_fail_interpolation` 禁 `${VAR:?}`，`test_every_interpolation_has_a_default` 要求每个 `${VAR}` 都带 `:-` 默认值。
      还有一个**两条断言都抓不到**的陷阱：既有 healthcheck 用的是 `$$MYSQL_ROOT_PASSWORD`（双 `$`，交给容器 shell 展开），
      若新探针写成单 `$VAR`，compose 会在解析期把它插成空串而**没有任何断言会报警**——
      要用容器内环境变量就写双 `$$`。
  - Skill: `none`

Exit Criteria:

- [x] `env -i PATH="$PATH" HOME="$HOME" docker compose -f docker-compose.yml config -q`（**与门禁同口径**：`tests/gates/test_zero_dep_boot.py` 的 `CLEAN_ENV` 只留 `PATH` / `HOME`）→ exit 0
- [x] `python3 -m pytest tests/unit/test_compose_zero_dep.py -q` → exit 0
- [x] `python3 -m pytest tests/gates/test_zero_dep_boot.py -q` 的结果与改动前一致：
      `test_compose_config_valid_with_empty_env` 仍绿，另两条仍以 **setup ERROR** 的形式红在
      `NotImplementedError: compose_stack 尚未实现 —— 见 docs/backlog/implementation-roadmap.md 的 P0 交付表（P0 · 零依赖启动 CI）`
      （**红因必须逐字一致**——若红因变了，说明本 plan 踩到了别的东西。注意它是 ERROR 不是 FAILED，
      整条命令的退出码是 1，`1 passed, 2 errors`）
- [x] No owner-doc update required（判定口径已在 Phase 2 落进 §14.2，其余写回集中在 Phase 5）
- [x] `docs/logs/` 追加本阶段条目

### Phase 4 - Proof：起栈实证

Status: completed
Targets: 无代码改动
Skill: `none`

- Item Types: `Proof`
- Prereqs: Phase 3

- [x] `AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300` → 记录退出码与实际耗时。
      **这条命令的退出码就是本 plan 的核心判据**：`--wait` 会等到所有带 healthcheck 的服务 healthy，
      任一 unhealthy 或超时即非 0。
      **`--wait-timeout` 必须给死**：不给上界时，一个卡在 `starting` 的探针会让命令无限期挂着，
      那不是「判据红了」，那是判据根本没给出结论。300 秒是起草时的取值，
      Phase 2 若把 `start_period` 定得更长，这里同步调大并在 owner doc 记下两者的关系。
  - Skill: `none`
- [x] `docker compose ps --format '{{.Service}}\t{{.State}}\t{{.Health}}'` → 抄下全表，逐行对照 Phase 2 定的集合。
  - Skill: `none`
- [x] `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/api/method/ping` → 期望 200（与工作项 3 那次实测同口径，便于对照）。
  - Skill: `none`
- [x] **变异验证（判据有没有牙齿）**：临时把某个 healthcheck 的探测目标改成一个必然失败的地址 →
      `docker compose up -d --wait --wait-timeout 300` 应**非 0** 且能指出是哪个服务 unhealthy → 还原 →
      用**变异前**先记下的 `shasum -a 256 docker-compose.yml` 与**还原后**的同一条命令输出比对，确认逐字节还原。
      （Phase 3 的改动此刻未必已提交，`git diff` 非空是正常的、证明不了还原，所以判据取哈希对照而非 `git diff`。）
      注意 `interval × retries + start_period` 决定了这个变异要多久才翻红——若超过 300 秒，说明超时值给小了，
      调大并如实记录，**不要因为「等太久」就把这步跳过**。
      不做这步就不知道 `--wait` 是真在判还是空转。
  - Skill: `none`
- [x] 收尾：`docker compose down -v` → 退出码；`docker ps -a` 确认无关栈未受影响。
  - Skill: `none`

Exit Criteria:

- [x] `AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300` → **exit 0**，命令原文、退出码与耗时抄进 `docs/logs/`
- [x] `docker compose ps` 全表落 `docs/logs/`，且与 Phase 2 定的「healthy 集合」逐行相符
- [x] 首页 `ping` → 200
- [x] 变异验证做过且如实记录（含**变异前 / 还原后两条 `shasum -a 256 docker-compose.yml` 的原文，且两者相同**）
- [x] No owner-doc update required（本阶段只产出实证记录，写回在 Phase 5）
- [x] 收尾 `down -v` 退 0，无关栈未受影响
- [x] `docs/logs/` 追加本阶段条目

### Phase 5 - 文档、roadmap 写回与交接

Status: completed
Targets: `docs/architecture/system-baseline.md` ·`docs/backlog/p0-foundation-roadmap.md` ·`docs/context/project-context.md` ·`docs/masterplan/STATE.md`（**只追加**）·`docs/logs/`
Skill: `none`

- Item Types: `Add | Decision`
- Prereqs: Phase 4

- [x] Add：`docs/context/project-context.md` 的 “Run app locally” 一行更新——
      它此刻写着「『栈起得来且全部 healthy』**尚未验证**」。本 plan 把「起得来」与「有 healthcheck 的服务全 healthy」验了，
      **但没有解锁 L2 门禁**。改写时必须把这两件事分开说，不许写成「工作项 8 已验证」。
  - Skill: `none`
- [x] **Decision：roadmap 工作项 8 的状态怎么写。**
      候选：(a) `todo` → `planned`（本 plan 是它的第一个 plan，已通过草案评审）；(b) 留 `todo`；(c) 写 `done`。
      **选 (a)**：(c) 是谎报（两条门禁一条没绿）；(b) 会让引擎下一轮把它当成没人做过的活再取一次——
      依据是 roadmap 自己的 `:18`「顺序即执行顺序，引擎取第一个 `todo`」与 `:33-34` 的状态值定义，
      **不是** `flow-loader.js` 的 `activePlans()`（那个扫的是 plan 文件的 `Plan Status`，与 roadmap 工作项状态是两回事，别张冠李戴）。
      落点：本 plan 自带幂等写入——工作项 4/5 的先例已证明没有任何引擎产物会替你写这一步。
      残余风险：工作项 8 会停在 `planned` 直到人处置 `STATE.md` §3 的红线决定 + 有人做完首页文案那一半。
  - Skill: `none`
- [x] Add：按红线 5 往 `STATE.md` §3 **追加**一行，登记本 plan 交出的两件事：
      ① 「healthy 已可判定，但门禁仍被 `compose_stack` 挡着」——指向已有那行 `[open]`，**不另开重复条目**，只补充新事实；
      ② 若 Phase 2 选了 (a)，登记「三个 worker 的健康不可判」这个收窄口径，供人在采纳门禁时知情。
  - Skill: `none`
- [x] Add：`docs/logs/` 写入本 plan 的聚合条目：五个阶段、每条命令原文 + 退出码 + 收尾 sha。
  - Skill: `none`

Exit Criteria:

- [x] `system-baseline.md` **§14.2** 存在，含健康判定口径与「哪些不可判」；
      ⚠️ 写进 `docs/architecture/**` 的文字不得使用 `文件:行号` 形式的引用（`check-doc-references.mjs` 的 line-ref 规则），只按小节名引
- [x] `project-context.md` 的 “Run app locally” 行已更新，且**明确区分**「起栈已验证」与「工作项 8 门禁未解锁」
- [x] roadmap 工作项 8 由 `todo` → `planned`
- [x] `git diff --numstat docs/masterplan/STATE.md` 第二列为 **0**（只增不删）
- [x] `docs/logs/` 已更新
- [x] `bash tools/check-masterplan-links.sh` 与 `node tools/check-doc-references.mjs` 均退 0

## Draft Review Record

- Independent draft review iteration 1: `needs revision` → 已就地修订为 `accept`
  （mission-driver `2026-08-21-171157` 的 review 步，独立于起草会话；评审时 HEAD 为 `3032866`，
  草案 Baseline 读的是 `5d8022e`——其间唯一一个提交 `3032866` 只改 `tools/ab-run.sh` 一个文件，
  与本 plan 涉及的 `docker-compose.yml` / `tests/**` / `tools/gates/**` 无交集，故 Baseline 的结论仍然成立）。
  复核方式是逐条实跑核对可验证断言，不是通读。**实跑核准的有**：
  `grep -n "healthcheck:" docker-compose.yml` → 只有 `:59` / `:72` / `:85` 三处（db / redis-cache / redis-queue），
  应用侧六个服务确实一个都没有；`frontend.depends_on` 的两条确为 `condition: service_started`；
  `tools/gates/expected-red.txt` 里工作项 8 的两行仍在名单内；
  `tests/gates/conftest.py` 的 `compose_stack` 逐字抛 `NotImplementedError: compose_stack 尚未实现 —— 见 docs/backlog/implementation-roadmap.md 的 P0 交付表（P0 · 零依赖启动 CI）`
  （草案 Phase 3 引的红因原文与之逐字相符）；
  `tests/gates/test_zero_dep_boot.py` 的 `CLEAN_ENV` 确实只留 `PATH` / `HOME`（Phase 3 的「同口径」成立）；
  `tests/unit/test_compose_zero_dep.py` 的 `test_no_hard_fail_interpolation` / `test_every_interpolation_has_a_default` 两条断言名属实；
  `docs/architecture/system-baseline.md` 的最后一节确为 §14.1，追加 §14.2 的落点成立；
  roadmap 第 8 项确为 `todo`；`STATE.md` 的 `[open]` 行确有 (a)/(b)/(c)/(d) 四个处置项；
  `docs/logs/2026/08-21.md` 里被引的那句「应用侧服务的 healthy 根本还不可判」逐字属实；
  Closure Gates 点名的 `tools/gates/check_expected_red.py` / `tools/check-masterplan-links.sh` / `tools/check-doc-references.mjs` 三个文件都在；
  草案称「Optional Layers 漂移由 `2026-08-21-1634-1` 的 Phase 4 `Fix` 负责」——该 plan 的 Phase 4 确有这条 `Fix` 项且已是 `active`，交接不落空。
  **修掉的问题**：
  (1) **Major——判据可能不可达却没有止损分支**：草案已诚实地把「`--wait` 对一次性容器如何裁决」列为未验证假设，
      却没写「若改动前基线就非 0 该怎么办」。Phase 4 的核心 Exit Criteria 是 `--wait` 退 0，
      这会逼执行期在「判据不可达」时去动一次性容器的语义来凑绿。已在 Phase 1 补一条 A/B/C 分支裁定项与对应 Exit Criteria：
      A 类（一次性容器被判失败）与 B 类（下限三服务无可用探针）一律**停在 Phase 1** 并往 `STATE.md` §3 追加 needs-human，
      明文禁止为凑退出码去改一次性容器语义。
  (2) **Major——Phase 4 变异验证的还原判据不成立**：草案用 `git diff docker-compose.yml` 证明「还原后字节一致」，
      但 Phase 3 的改动此刻未必已提交，`git diff` 非空是正常态，证明不了任何事。改为记录变异前 / 还原后两条
      `shasum -a 256 docker-compose.yml` 并要求相同。
  (3) **Major（格式，指南规则 6）**：Phase 1 / 3 / 4 的 Exit Criteria 缺「相关文档已更新 或 No owner-doc update required」一行，已补齐。
  (4) **Minor 补强（指南规则 9 的备选完整性）**：Phase 2 的 `start_period` 决策原本只有「调大超时」一条路。
      实读 compose 后发现 `backend_defaults` 只 `depends_on` `configurator`、**并不等 `create-site`**，
      故补上「给 `backend_defaults` 加 `create-site: service_completed_successfully`」这条候选及其代价
      （该锚点为 `backend` 与三个 worker 共用，改它会一并改掉 worker 启动次序）。
  **未发现**：红线 1/2/3/4/5/6/7 的越线设计；无主的状态转换；编造的事实；被禁词（`optional` / `考虑` / `视情况` 等）；
  Exit Criteria 自报通过（全部落在子进程退出码或文件存在性上）。

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（`system-baseline.md` ·`project-context.md` ·roadmap ·`STATE.md` §3）
- [x] verification has run：`docker compose config -q`（空环境）·`AGENERP_HTTP_PORT=18080 docker compose up -d --wait` ·`docker compose ps` ·`curl … /api/method/ping` ·`python3 -m pytest tests/unit -q` ·`python3 -m pytest tests/gates/test_zero_dep_boot.py -q` ·`python3 tools/gates/check_expected_red.py` ·`bash tools/check-masterplan-links.sh` ·`node tools/check-doc-references.mjs`
- [x] **verification scope limited 已显式声明**：起栈实证只在**本机 compose v5.0.2** 上做过，
      CI runner 是 2.38.2，两者的版本差是 `2026-08-21-1022-1` 已登记的 watch-only residual。不得report为「CI 上也验证过」
- [x] **不得宣称工作项 8 的门禁转绿**：`expected-red.txt` 在本 plan 前后**逐字不变**
      （执行时跑 `git diff --numstat tools/gates/expected-red.txt` 并抄下输出，期望无变化）
- [x] 判据有牙齿：Phase 4 的变异验证做过并记录
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent（独立子代理，fresh session）
- [x] closure evidence exists in files
- [x] `git diff --name-only` 对 `tests/gates/**`、`.github/workflows/**`、`missions/**` 全部零命中

## Deferred But Adjudicated

### 首页「AI 能力未配置」文案（门禁 `test_homepage_states_ai_disabled_instead_of_crashing`）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 它是**应用层**交付（要往站点里装东西），与本 plan 的 compose 编排面不是同一个结果面；
  `2026-08-21-1022-1` 已把它与 `compose_stack` 一并划给工作项 8，且该门禁的 fixture 同样被红线 1 挡着。
- Successor Required: `yes` —— 工作项 8 的第二个 plan（roadmap 规则允许一个工作项 1–2 个 plan）
- 重开事件：人对 `STATE.md` §3 那行 `[open]` 的 (a)/(b)/(c)/(d) 作出选择之后

### 给 CI 加跑 docker 的 L2 job

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: `.github/workflows/**` 在红线 2 的关注面上；且在 `compose_stack` 解锁之前，
  加了 job 也只能跑到一个抛 `NotImplementedError` 的 fixture 上。先后顺序反了。
- Successor Required: `yes` —— 与上一条同一个 successor
- 重开事件：`compose_stack` 被人解锁之后

### worker 服务（`queue-short` / `queue-long` / `scheduler`）的健康不可判

- Classification: `watch-only residual`
- Why Not Blocking Closure: 仅当 Phase 2 选了候选 (a) 时成立。届时「全部 healthy」是一个**收窄过的集合**，
  该收窄已写进 owner doc 与 `STATE.md` §3，人在采纳门禁时看得见。
  用 `pgrep` 之类的进程存活探针把它糊成绿的，比不判更坏——那是假判据。
- Successor Required: `no`
- 重开事件：Frappe/ERPNext 提供 worker 自检手段时；或 P1 的控制循环需要判定 worker 可用性时

### 本机 compose v5.0.2 与 CI runner 2.38.2 的版本差

- Classification: `watch-only residual`
- Why Not Blocking Closure: 已由 `2026-08-21-1022-1` 登记；本 plan 不引入新的版本敏感语法就不加剧它。
  `--wait` 与 `depends_on: service_healthy` 都是 compose 2.x 早已稳定的特性，但**这句话本 plan 没有在 2.38.2 上实测过**，
  照实记着，不粉饰。
- Successor Required: `no`
- 重开事件：首次让 CI 真跑 docker 时（即上面那个 L2 job 的 successor）

## Closure

Status Note: 五个阶段全部执行完毕并逐项打勾，`Plan Status` 置 `completed`。
交付面只有 `docker-compose.yml` 一个代码文件（`healthcheck:` 由 3 处增至 6 处，
`frontend.depends_on` 两条由 `service_started` 收紧为 `service_healthy`，
`x-backend-defaults` 补 `create-site: condition: service_completed_successfully`），其余六个文件是文档写回。

**本 plan 交出的是「healthy 可判定」，不是「门禁转绿」**——`tools/gates/expected-red.txt` 逐字未动
（`git diff --numstat` 无输出），`test_stack_boots_and_all_services_healthy` 与
`test_homepage_states_ai_disabled_instead_of_crashing` 两条仍在名单内，`compose_stack` 仍抛 `NotImplementedError`。
Exit Criteria 从起草时就不含任何一条门禁转绿，收尾时也没有。

⚠️ **`## Closure Gates` 里唯一未勾的是「closure audit was independent（独立子代理，fresh session）」——
本次执行没有做独立关闭审计**，它属循环的 `CLOSURE_VERIFY` 步，由 fresh session 复跑判定。
不自勾，也不把它记成已做。

Closure Audit Evidence:

- Auditor / Agent: <pending —— 待独立 fresh session 复跑>
- Evidence: 本次执行期的命令原文、退出码与 `docker compose ps` 全表落在
  `docs/logs/2026/08-21.md` 的五条 `EXECUTE` 条目里（Phase 1–5，倒序在最前）；
  判定口径落在 `docs/architecture/system-baseline.md` **§14.2**；
  交接与收窄口径落在 `docs/masterplan/STATE.md` §3 的追加行（`--numstat` 为 `5	0`，只增不删）。

Follow-up:

- 工作项 8 的第二个 plan（首页「AI 能力未配置」文案 + CI 的 L2 docker job），
  重开事件是人对 `STATE.md` §3 那条 `[open]` 的 (a)/(b)/(c)/(d) 作出选择。
- 本批改动应经 PR 落地（compose 的 `healthcheck:` / `condition: service_healthy` 是 2.38.2 runner 上从未解析过的新键）。
  **开 PR 属对外动作，本次未执行。**
