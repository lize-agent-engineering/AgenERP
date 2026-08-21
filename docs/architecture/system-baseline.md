# 分层架构 · 三端模型 · 数据与安全

> 系统的骨架：四层分层、三端使用模型、数据边界与安全约束。

| | |
|---|---|
| 来源 | 由 `ARCHITECTURE.md`（草案 v0.6，69KB/1159 行）于 2026-08-20 按语义拆分而来 · 证据仓 `1c622c8` |
| 原文 | `${XM}/docs/next/ARCHITECTURE.md`（**冻结，不再更新**；本文件是唯一在演进的版本） |
| 索引 | [docs/architecture/README.md](../architecture/README.md) |

> **章节编号保持原样**（§1、§7、§11.2 …），因为主计划的 `REF:` 表按标题原文定位。**改标题等于断链**，要改先改 [REF 表](../masterplan/README.md)。

---

## 3. 分层架构

### 3.1 全景

```
┌──────────────────────────────────────────────────────────────┐
│  ③ 呈现层                                                     │
│  Desk（系统管理端，原样保留）                                  │
│  AgenERP Web（业务管理端 + 业务操作端，frappe-ui）             │
├──────────────────────────────────────────────────────────────┤
│  ② AgenERP 内核（本项目的全部差异化）                          │
│  ┌────────────┬────────────┬────────────┬─────────────────┐  │
│  │ Agent      │ 工具契约层  │ 风险分级   │ 上下文/知识/记忆 │  │
│  │ Runtime    │            │ 与审批     │                 │  │
│  ├────────────┼────────────┼────────────┼─────────────────┤  │
│  │ 视图 DSL   │ 定制包     │ 状态快照   │ 模型路由        │  │
│  │ + 渲染器   │ GitOps     │ 与 diff    │                 │  │
│  └────────────┴────────────┴────────────┴─────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│  ① 底座（不改动）                                             │
│  ERPNext (GPLv3) — 1000+ DocType、GL、BOM、库存估值           │
│  Frappe (MIT) — DocType 引擎、权限、Workflow、队列、报表      │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 底座白送的能力（不要重造）

| 能力 | 提供者 | 在 AgenERP 中的角色 |
|---|---|---|
| 事实源 | MariaDB + DocType | Agent 不可绕过的唯一真相 |
| 业务动作 | ERPNext | Agent 的「手」 |
| 不可绕过的护栏 | `hooks.doc_events` | Agent 提交时强制触发，prompt 改不了 |
| 工具接口 | `@frappe.whitelist()` + REST | 工具层天然存在 |
| 身份与权限 | Role / DocPerm / User Permission | Agent 的身份边界，SoD 落点 |
| 审计轨迹 | Version / Activity / GL / SLE | Agent 行为天然留痕 |
| 审批流 | Workflow | 风险分级中「要人批」那档的载体 |
| 异步执行 | RQ workers + scheduler | 长任务与定时巡检运行时 |
| **系统形态** | DocType / Custom Field / Workspace / Report **全是数据库记录** | **Agent 能改变系统形态的根本原因** |

**为什么不重写 Desk**：Desk 由 metadata 自动生成，覆盖 ~30 种 fieldtype、8 种视图、子表内联编辑、报表引擎、打印格式、Client Script API。重写必须 100% 完备（漏一个 fieldtype 就有 DocType 打不开），且会作废社区海量 Client Script。Frappe 核心开发者本人的尝试（frappe-deskv3）已于 2022 年停止。

### 3.3 进程模型与 Harness 接入方式

**事实核对（2026-08-19）**：DeepSeek Harness 提供官方 Python SDK。

```bash
python -m pip install deepseek-harness-sdk
```
```python
from deepseek_harness import DeepSeekHarness
with DeepSeekHarness() as harness:
    result = harness.run("...")
```

**但它不是原生 Python 实现。** SDK 是 Python 客户端，通过 **stdio JSON-RPC** 驱动一个 runtime 子进程——安装 `deepseek-harness-sdk` 会同时装入同版本的 `deepseek-harness-runtime-bin` 平台 wheel，其中包含打包好的单文件可执行 `dsh-jsonrpc-agent`。SDK 惰性启动该子进程并跨调用复用（context manager 或显式 `close()`）。

#### 3.3.1 结论：双进程仍在，但不再是技术栈割裂

| | 影响 |
|---|---|
| 用户是否需要安装 Node.js | **否**，runtime 以平台 wheel 分发 |
| 是否引入第二套技术栈 | **否**，Python 侧只见 Python API |
| 是否仍是双进程 | **是**，但降级为实现细节 |

#### 3.3.2 真实约束（这些才是需要设计应对的）

**① 平台限制 —— 不支持 Windows**
runtime-bin 要求 Python 3.10+、Linux x64/arm64 或 macOS 14+ (arm64)。
生产环境走 Docker（Linux）不受影响，但**本地开发的 Windows 贡献者会被挡在门外**。对开源项目而言这是真实的贡献者流失。
→ 因此内置 runtime 必须**纯 Python、可在 Windows 运行**；Harness 是可选增强。

**② 与 Frappe worker 模型的资源冲突**
Frappe 以 RQ workers 承载异步任务（本探索环境即有 `queue-short` / `queue-long` 两个 worker 容器）。若每个 worker 各自持有一个 dsh 子进程，内存开销需实测评估。
→ Agent 执行应集中在专用 worker 队列，而非散布于所有 worker。

**③ 镜像体积**
平台 wheel 内含单文件可执行，会显著增大镜像。对「开箱即用」的发行版是可感知的成本。

**④ 稳定性**
官方明示 developer preview，会有破坏兼容的变更。

#### 3.3.3 接入策略

```
        AgenERP Agent Runtime 接口（Python，内核，接口固定）
                          │
          ┌───────────────┴────────────────┐
          ▼                                ▼
   内置 runtime                     Harness adapter
   纯 Python，零外部依赖              deepseek-harness-sdk
   支持 Windows                      （可选，功能更强）
   保证 clone && up 可跑
```

- **内核接口用 Python 定义**，两种 runtime 实现同一接口
- **内置 runtime 必须纯 Python、零外部依赖、支持 Windows**，保证 `git clone && docker compose up` 与本地开发均可跑
- **Harness adapter 为可选依赖**（`pip install agenerp[harness]`），不进默认安装
- 是否将 Harness 提升为推荐配置，在 P3 阶段依据其稳定性与实测资源开销决策


---

## 4. 三端模型

| 端 | 使用者 | 频率 | 核心需求 | 载体 |
|---|---|---|---|---|
| **① 系统管理端** | 实施顾问、开发者 | 上线密集，之后偶尔 | **完备性 > 美观** | **Desk 原样保留** |
| **② 业务管理端** | 老板、经理 | 每天几分钟 | 直观、有结论、有基准 | AgenERP Web，只读为主 |
| **③ 业务操作端** | 业务员、计划员、工人、质检、仓库、财务 | 全天 | 快、少点击、防错 | AgenERP Web，读写 |

**②③ 共用一套前端**，差别在渲染哪套视图 DSL、默认落在哪个首页。权限由后端强制，前端只做呈现与提示。

**兜底原则（关键）**：凡是新前端未实现的 DocType、fieldtype、报表、罕见操作，**用户点过去自动落回 Desk**。有这条退路，首版工程量从人-年降到人-周，且失败成本仅为「关掉入口」。

---

## 14. 数据与安全

| 主题 | 决策 |
|---|---|
| 密钥管理 | 只从环境变量读取，不入库、不入源码、不入日志 |
| 多租户 | 依托 Frappe site 隔离；跨站点迁移仅通过定制包 |
| 数据出境 | 模型可换本地；默认配置不含任何商业 API |
| 审计 | Agent 每次动作写入 DocType，与 Frappe 原生审计合流 |
| 注入防护 | 见 §7.5（工具结果数据边界）与 §8.4（记忆红线）。**结构性防御，不依赖模型判断力** |
| 零依赖启动 | **`git clone && docker compose up` 必须能起来**，AI 能力降级为「未配置」并明确提示 |

**零依赖启动是开源铁律。** 反面教材：本探索项目的 compose 因 `COHERE_API_KEY` 缺失导致 `docker compose ps` 直接失败——新用户在第一步就会流失，且不会告诉你原因。

**Spike 10 定位了确切成因，并确认应用层本来就是对的。**

成因只是 compose 的三行硬失败语法 `${VAR:?msg}`：

```
$ env -i docker compose -f docker/compose.demo.yml config
error while interpolating x-backend.environment.COHERE_API_KEY:
required variable COHERE_API_KEY is missing a value
```

不是启动失败，是**连 `config` 都解析不了**。改成 `${VAR:-默认值}` 后 `exit=0`。

而「AI 能力降级为未配置并明确提示」这一半**已经达标**：`integrations/cohere.py` 抛
`CohereEmbedError("COHERE_API_KEY is required for pattern search.")`，明确失败、
不静默降级、且有回归测试覆盖。**缺的不是降级设计，只是启动门禁放错了地方。**

→ 三条可执行规则：

| 规则 | 理由 |
|---|---|
| compose 中**禁止 `${VAR:?}`**，一律用 `${VAR:-默认值}` | 一个必填变量就能让 `clone && up` 失败 |
| 一切外部能力缺失即为「未配置」状态，**不是错误状态** | 未配置的系统应当能起来并说明缺什么 |
| **前置检查属于 verify 脚本，不属于启动路径** | 就绪门禁与「能不能起来」是两回事 |

→ **P0 应加一条 CI**：在完全空的环境变量下执行 `docker compose config && up -d` 并做健康检查，
断言全部服务 healthy 且首页明确显示「AI 能力未配置」。这是 P0 里最便宜的一项，
但它守的是开源项目的第一转化率。

⚠️ **附带风险**：把 `DB_PASSWORD:?` 改成 `DB_PASSWORD:-changeit` 解决了启动问题，
却引入默认弱口令。**默认值只用于让容器起得来，必须配合首次启动强制改密或仅监听回环地址。**
零依赖启动不能以默认可用凭据为代价。

---

## 14.1 §14 三条规则在本仓的落点（2026-08-21 追加）

> 本节**只记落点，不改写 §14 任何一行**。§14 是 Spike 10 的结论出处，后继 plan 还要引它。

roadmap 工作项 3（plan `docs/plans/p0-foundation/2026-08-21-1022-1-zero-dep-boot-compose.md`）
把 §14 的规则从散文变成了可执行判据。落点如下：

| §14 出处 | 落在哪 | 判据文件 |
|---|---|---|
| 规则 ① 禁止硬失败插值，一律 `${VAR:-默认值}` | `docker-compose.yml` 全文 | `tests/unit/test_compose_zero_dep.py::test_no_hard_fail_interpolation` · `::test_every_interpolation_has_a_default` |
| 规则 ② 外部能力缺失是「未配置」不是错误 | compose 里 AI 变量全部空默认值，且不进 healthcheck / command 的成败路径 | `tests/unit/test_compose_zero_dep.py::test_ai_variable_defaults_to_empty` |
| 规则 ③ 前置检查属于 verify 脚本，不属于启动路径 | **没有落点** | **无判据** —— 见下 |
| ⚠️ 附带风险：默认口令必须配合强制改密**或**仅监听回环 | 取「仅监听回环」：所有 `ports:` 的宿主 IP **字面写死** `127.0.0.1` | `tests/unit/test_compose_zero_dep.py::test_published_ports_bind_loopback_literally` · `::test_ports_use_short_syntax_only` |

两处必须写明的事实，免得后继当成漏项：

- **规则 ③ 现在没有对象。** 本仓此刻既没有 verify 脚本，也没有任何启动路径上的前置检查。
  给一条无对象的规则写断言只能写成同义反复，那是假判据，比没有更坏。
  重开事件：仓里第一次出现 verify / 就绪检查脚本时（或工作项 8 给 `compose_stack` 加启动前置检查时）。
- **回环绑定的 IP 必须字面写死，不许写成 `${BIND:-127.0.0.1}`。** 判据是对 compose 的**静态文本扫描**，
  而仓根的 `.env` 能在 `docker compose config` 时把变量改掉（实测：`AGENERP_HTTP_PORT=9999` 会把
  `published` 改成 9999）。变量驱动的绑定地址会出现「单测绿、真实绑到 `0.0.0.0`」——默认弱口令就此暴露。

判据为什么不复用门禁：门禁 `test_compose_config_valid_with_empty_env` 只判「空环境下 `config -q` 退 0」。
一份写了硬失败插值的 compose，在**已经配了变量的机器上**照样退 0——红只会在别人 `git clone` 之后才出现。
所以规则要有自己的、扫原始文本的判据。


---

## 14.2 本仓栈的健康判定口径（2026-08-21 追加）

> 本节回答一个此前无人定义的问题：本仓说「全部服务 healthy」时，**到底指哪些服务**。
> 出处是 plan `docs/plans/p0-foundation/2026-08-21-1634-2-compose-healthcheck-app-services.md`，
> 结论全部由该 plan Phase 1 的容器内实测得出，命令原文与退出码在当天的 `docs/logs/` 里。

### 「全部服务 healthy」= 有探针的服务全部 healthy + 其余长驻服务 running + 两个一次性容器 `Exited (0)`

这是一个**收窄过的集合**，不是字面意义的「全部」。收窄的边界必须写明，否则将来采纳门禁的人会以为它覆盖了整个栈。

| 服务 | 有无 healthcheck | 探针 | 判定 |
|---|---|---|---|
| `db` | 有（工作项 3 已有） | `mysqladmin ping` | 在集合内 |
| `redis-cache` / `redis-queue` | 有（工作项 3 已有） | `redis-cli ping` | 在集合内 |
| `backend` | 有 | 容器内 `curl` 打 `/api/method/ping`，**必须带 `Host: frontend` 头** | 在集合内 |
| `websocket` | 有 | 容器内 `curl` 打 socket.io 的 polling 握手端点 | 在集合内 |
| `frontend` | 有 | 容器内 `curl` 打 `:8080/api/method/ping`（经 nginx 转 backend） | 在集合内 |
| `queue-short` / `queue-long` / `scheduler` | **无** | **查实没有可用探针** | **健康不可判**，只判 running |
| `configurator` / `create-site` | 无（一次性容器） | 不适用 | 只判 `Exited (0)` |

### 三个 worker 为什么不给探针（这不是漏项，是查实的结论）

- `bench doctor` 与 `bench --site frontend scheduler status` 都**退 0**，而它们同时在输出里说
  `Scheduler disabled / inactive for frontend`——`bench new-site` 建站时默认就把调度器关了。
  拿这两条当探针等于**永远绿**，那是假判据，比不判更坏。它们还都是全栈级结论，不区分是哪个容器。
- rq 侧确有真信号：worker 会把自己注册进 redis 的 `rq:workers`，每条 `rq:worker:<id>` 记录里的
  `hostname` 与容器 hostname 逐字相符，可用来定位「本容器的 worker」。三条理由让它仍然不合适：
  ① **`scheduler` 根本不是 rq worker**，不在名单里，这条路对它无效，覆盖面天然残缺；
  ② **心跳分辨率是 7 分钟**——rq 的 `DEFAULT_WORKER_TTL` 是 420 秒，本仓实测两次心跳间隔 405 秒。
     一个死掉的 worker 会继续「healthy」将近 8 分钟，这离假判据只有一步；
  ③ 它是**跨服务探针**：worker 的健康会因为 redis 不可达而变红，把故障归错了服务。
- 不采用 `pgrep` 之类的进程存活探针。进程活着不等于 worker 在消费队列，那是一条永远绿的假判据。

**残余风险（采纳门禁时必须知情）**：`test_stack_boots_and_all_services_healthy` 将来被解锁后，
它断言的是上表「在集合内」那六个，**不是十一个**。三个 worker 的健康在本仓此刻不可判。
重开事件：Frappe/ERPNext 提供 worker 自检手段时，或控制循环需要判定 worker 可用性时。

### 探针取值与理由

| 服务 | interval | timeout | retries | start_period | 最迟翻红 |
|---|---|---|---|---|---|
| `backend` | 10s | 5s | 6 | 60s | ~120s |
| `websocket` | 10s | 5s | 6 | 30s | ~90s |
| `frontend` | 10s | 5s | 6 | 30s | ~90s |

配套的 `--wait-timeout` 取 **300 秒**。两者的关系是硬的：`interval × retries + start_period`
决定一个坏掉的服务多久才翻红，这个数**必须小于** `--wait-timeout`，否则 `--wait` 会先超时——
那不是「判据红了」，那是判据根本没给出结论。上表最大值 ~120 秒，加上建站耗时仍在 300 秒内。

**`start_period` 为什么不用调大到覆盖建站耗时**：本仓选的是另一条路——
给 `x-backend-defaults` 补上 `create-site: condition: service_completed_successfully`，
让 `backend` 与三个 worker **等站点建完再启动**。此前该锚点只等 `configurator`，
于是 `backend` 与 `create-site` 并行起，`backend` 在站点存在之前必然探针失败，
只能靠一个巨大的 `start_period` 兜住——而建站耗时是随机器速度变的（本机实测约 50 秒，CI runner 上会更久）。
把它塞进 `start_period` 会同时产生两个坏结果：超时值要跟着机器猜，且一个**真的坏掉**的 backend
也要等同样久才翻红，判据既慢又钝。改成编排层的次序约束之后，`start_period` 只需覆盖 gunicorn 自身启动。
**代价照实记**：该锚点为 `backend` 与三个 worker 共用，这项改动一并推迟了三个 worker 的启动时机
（它们现在也等站点建完），这是本次有意接受的编排语义变更。

**探针写法上的三个坑，都是实测踩出来的**：

- `backend` 的探针**必须带 `Host: frontend` 头**。Frappe 的 gunicorn 按 Host 头解析站点，
  容器内直接打 `127.0.0.1` 会被当成一个名叫 `127.0.0.1` 的站点，返回 404 `does not exist`，
  **再大的 `start_period` 也救不了**。站点名 `frontend` 与 `create-site` 的 `--set-default`、
  `frontend` 服务的 `FRAPPE_SITE_NAME_HEADER` 是同一个值，改站点名要三处一起改。
- `websocket` 的根路径 `/` **不回应**（实测 curl 5 秒超时、0 字节），不能拿来判活；
  可用的是 socket.io 的 polling 握手端点，返回 200 与 engine.io 握手 JSON。
- 所有探针都带 `--max-time`。不带上界时一个不回应的端点会把探针挂死到 healthcheck 自己的 `timeout`，
  故障表现会变成「一直 starting」而不是「unhealthy」。

### 零依赖红线在本节的落点

新增的三条 healthcheck **一个 AI 相关变量都不出现**，也不引入任何 `${…}` 插值——
这是 §14 规则 ② 的直接要求（外部能力缺失是「未配置」状态，不进 healthcheck / command 的成败路径），
判据是 `tests/unit/test_compose_zero_dep.py` 的 `test_ai_variable_defaults_to_empty` 与两条插值断言。

---

## 14.3 「AI 能力未配置」在本仓的表达口径（2026-08-21 追加）

> 本节回答两个此前无人定义的问题：**这句话由站点上的什么东西承载**，以及
> **它要不要随 AI 配置的变化而变**。出处是 plan
> `docs/plans/p0-foundation/2026-08-21-2220-2-homepage-ai-not-configured.md` Phase 1，
> 结论全部由该 plan 起草与执行时在活站点上实测得出，命令原文与退出码在当天的 `docs/logs/` 里。
> 本节**只增不改**，不改写 §14 / §14.1 / §14.2 的任何一行。

### 决策 ①：承载物取 `Website Settings.banner_html`

| 候选 | 实测结论 | 取舍 |
|---|---|---|
| (a) 建一条 `Web Page` + 把 `Website Settings.home_page` 指向它 | plan 起草时实测可行，门禁两条断言都过 | **未采纳** |
| (b) `Website Settings.banner_html` | 执行时实测可行：`GET /` 回 200，正文含该文案（渲染在 navbar 之前） | **采纳** |
| (c) 自建 Frappe app 提供 www 页面 | 要在镜像里装 app，与「零依赖启动不改镜像」冲突 | 起草时即排除 |

取 (b) 的三条理由，按分量排：

1. **它不把 `/` 从登录页上夺走。** (a) 会让 `/` 变成一张静态说明页，登录退到 `/login`——
   本仓此刻唯一的可用界面就是 ERPNext 原生桌面，把登录挤出首页是实打实的产品退化。
   (b) 保留登录页，只在它上面加一条状态横幅。
2. **改动面更小。** (b) 只写一个既有 Single 的一个字段，不新增任何文档、不改路由归属；
   (a) 要建一条 `Web Page` 文档并改写 `home_page`，两处站点态、两处要幂等。
3. **幂等是天然的。** 写字段天然幂等（值相同就跳过），不需要 (a) 那种「已存在则跳过」的分支。

实测记录（活站点，端口 18080，`Host: frontend`）：

- `PUT /api/resource/Website Settings/Website Settings`（`banner_html` 置为含该文案的 HTML）→ `put=200`；
  随后 `GET /` → `status=200`，正文命中该文案 1 次，位置在 `<div>…</div><nav class="navbar …">` 之前。
- **覆盖面的代价照实记**：`banner_html` 出现在**所有 website 层页面**上，不只是 `/`。
  实测 `/login` 同样命中 1 次；`/app` 是 301、`/api/method/ping` 是 200 且都 0 次——
  即桌面与 API 不受影响，覆盖面被限制在 website 层。

### 决策 ②：文案在引导期按环境判定一次，但「AI 能力未配置」这句话无条件常驻

| 候选 | 取舍 |
|---|---|
| (a) 引导时读当时的 `AGENERP_LLM_ENDPOINT`，空/非空写不同文案 | **采纳，但带下面那条硬约束** |
| (b) 固定写「AI 能力未配置」，完全不看环境 | 备选（硬约束若说不通就退回它） |
| (c) 请求时动态判断 | 起草时即排除：静态承载物读不到环境变量，要动态就得有服务端代码，踩红线 7 的边界 |

**硬约束：无论 AI 是否已配置，首页正文都必须逐字包含 `AI 能力未配置`。**
理由是判据侧的事实，不是文案偏好：门禁那条断言是**无条件**的
（`assert "AI 能力未配置" in resp.text`，它不看环境），而 `compose_stack` 起栈时用的是**宿主环境**
（`tests/gates/conftest.py` 的 `_compose()` 不传 `env=`），compose 还会读仓根 `.env` 做插值。
朴素的「非空就改写文案」会让这条门禁**在零代码改动的情况下、只因换了台机器而变红**。
因此「已配置」分支只允许在这句话**之外**追加状态说明——本仓把它写成一张能力清单：
端点配没配是一行，Agent 有没有承担呈现层 / 语言层 / 判断层是另一行，而后者在 P0 阶段**恒为未配置**
（roadmap 首句：P0 不引入任何 LLM）。所以这句话在两个分支里都是真陈述，不是为了迁就断言而说的假话。

### 引导步骤的落点与限制

- 落点：一次性 compose 服务 `bootstrap-homepage`（形状同 `create-site`：`restart: "no"`、
  `depends_on: create-site: service_completed_successfully`、跑完即退），
  跑仓内脚本 `tools/bootstrap/homepage_notice.py`，以**字面写死的相对路径**只读 bind mount 挂进容器。
  路径不许写成变量：判据是对 compose 的静态文本扫描，而仓根 `.env` 能在 `config` 时把变量改掉——
  与 §14.1 「回环绑定 IP 必须字面写死」是同一条理由。
  这是本仓**唯一**的 bind mount；此前 compose 全文只挂命名卷，仓内脚本对容器不可见。
- **一次性服务必须被人依赖，否则 `up -d --wait` 会判它失败。** 实测：`bootstrap-homepage`
  刚落地时没有任何服务依赖它，`up -d --wait` 退 **1**，逐字打
  `container agenerp-bootstrap-homepage-1 exited (0)` —— 正常退出被 `--wait` 当成了失败。
  `configurator` / `create-site` 不踩这个坑，正是因为它们各自被 `service_completed_successfully` 依赖着。
  处置：给 `frontend` 加 `bootstrap-homepage: condition: service_completed_successfully`。
  这一条同时买到了产品语义——nginx 开始对外服务时，横幅一定已经在了。
- **站点名 `frontend` 现在出现在 compose 的四处**（`create-site` 的 `--set-default`、
  `frontend` 的 `FRAPPE_SITE_NAME_HEADER`、`backend` 探针的 `Host` 头、`bootstrap-homepage` 的
  `AGENERP_SITE_NAME`），改站点名要四处一起改。§14.2 写的「三处」是本节落地前的计数。
  引导脚本自己**不写死**站点名，四处都在 `docker-compose.yml` 里。
- **引导脚本必须在 `frappe-bench/sites` 目录下跑。** frappe 的日志路径是
  `os.path.join("..", "logs", …)`，相对 cwd；换个目录跑会直接
  `FileNotFoundError: /home/frappe/logs/database.log`（实测踩过）。
- **限制 ①（残余风险）：文案是引导期一次性判定的。** 事后改了 `.env` 里的 AI 变量，
  首页文案**不会自动跟着变**，要重跑引导步骤（`docker compose up -d bootstrap-homepage`）。
  动态判定要服务端代码，会踩红线 7 的边界，本仓不做。
- **限制 ②（残余风险）：上面那条硬约束意味着文案里永远留着一句「AI 能力未配置」。**
  产品上线前需要人复核它是否仍然贴切——真接上 LLM 之后，这句话的落点应当从「整个产品」
  收窄到「具体哪一层还没接」，否则它会从真陈述退化成噪音。
- 引导脚本读 `AGENERP_LLM_ENDPOINT`，但**它不在成败路径上**：变量为空时脚本照样退 0
  （这正是 §14 规则 ② 的要求）。可执行定义见 `tests/unit/test_compose_zero_dep.py`
  的 `test_ai_vars_absent_from_healthchecks`。

### 红线 7 在本节的落点

交付的横幅内容与引导脚本都**只含静态文本**：不出现 `<script`、不出现 Jinja 定界符、
不建 `Server Script` / `Client Script` 任何一种。这不是只写在文档里的承诺，
判据是 `tests/unit/test_compose_zero_dep.py::test_bootstrap_delivers_no_runtime_code`。

**这条判据的锚点必须自己也有判据。** 它扫的是 `tools/bootstrap/` 这个**写死的目录**，
而 compose 理论上可以挂别处——2026-08-21 的关闭审计实测出两条绕过路径，两条都能让整份单测全绿：
把挂载换成 `./tools/evilboot`（新目录里放脚本标签），或写成 `${AGENERP_BOOTSTRAP_DIR:-./tools/bootstrap}`
（`:-` 默认值满足既有插值判据，而仓根 `.env` 能在 `config` 时把它改掉）。
补上的判据是 `::test_bootstrap_script_dir_is_mounted_literally`：引导服务的宿主侧 bind mount
**必须且只能是字面的 `./tools/bootstrap`**。与 §14.1「回环 IP 必须字面写死」是同一条理由的第三次应用——
**凡是判据依赖的路径，都必须字面写死**，否则判据扫的东西和真正跑起来的东西不是同一个。

---

## 14.4 门禁判定器的两种判定模式，与判定器自身的保护现状（2026-08-22 追加）

> 本节此前是 `## 14.3` 之下一个不带编号的三级标题
> （`### L2 门禁在 CI 上的判定方式，与它换来的残余风险`），属**误归档**——
> 14.3 讲的是首页「AI 能力未配置」的表达口径，与 CI 判定方式无关。
> 2026-08-22 由 plan `docs/plans/p0-foundation/2026-08-22-0027-1-live-mode-gate-verdict.md`
> 提升为独立的 `## 14.4` 并改写。
> **2026-08-22 二次追加**：本节起初只写判定契约本身、不写「CI 怎么用」（写早了是假陈述）；
> CI 消费面已由 plan `docs/plans/p0-foundation/2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`
> 交付，补在下面两个小节（`gates-l2-live` 与 `verdict-tool-untouched`）。

### 两个判定环境给出相反判定，这是本节要解决的那个矛盾

`tools/gates/check_expected_red.py` 是本仓**唯一**的门禁判定器
（roadmap「框架/平台复用」表：「已就绪，别再写第二个判定器」）。它被两处消费：
`missions/p0-foundation.json` 的 `commands.test`（`GATE_VERIFY` 子进程复跑的就是它）与
`.github/workflows/gates.yml` 的 `gates-l1` job。

默认判定环境没有 `AGENERP_LIVE`，`tests/gates/conftest.py` 的 `_require_live()` 直接 `pytest.fail`
（**不是 skip**），所以 L2 那几条在那里**恒红**，预期红名单如实登记着它们
（人在 `docs/masterplan/STATE.md` §2（2026-08-21T11:20Z）裁定的口径：**「名单必须反映判定器实际看到的」**）。
而在 live 判定环境下它们都是绿的，同一个判定器会报「名单内的门禁却绿了」并退 1。
两个判定环境用同一份名单，必然互相拆台。

`gates.yml` 的 `gates-l2` job 因此**绕开了判定器**，直接对 `pytest` 的退出码做判定。
**那样做漏掉的唯一硬洞是 skip / xfail**：`pytest` 对全部 skip 的一轮照样退 0，判定器不然；
`tests/gates/conftest.py` 开头逐字写着「不许 `skip`」，而 L2 那条路上没有任何东西在执行这句话。
另外三条（收集期错误的表现不同、两套判定约定、本机 live 跑法是三串手敲 env）是
「难用、易错、口径分裂」，**不是判据失效**，别夸大。

### 判定契约：`AGENERP_LIVE=1` 选中 live 模式，契约为「全部绿、零 red、零 skip」

- **模式选择用环境变量 `AGENERP_LIVE=1`**，与 `conftest.py` 的 `_require_live()` **同一个开关**——
  两者不可能各判各的。没选用命令行参数 `--live` 是因为判定器把 `sys.argv[1:]` 原样透传给 pytest，
  加位置参数与透传语义打架；没选「探测栈是否起着」是因为那是隐式判定，
  会让「栈碰巧起着」悄悄改变判定口径。
  **残余风险**：默认环境误设 `AGENERP_LIVE=1` 且栈没起 → 要求全绿 → 退 1。
  这是**更严的失败**而非假绿，可接受；但输出必须逐字标明判定模式，否则会被误读成实现回归。
  因此**两种模式都打印一行模式行**，只在 live 打的话，日志答不出「这条绿是谁判的」。
- **live 模式不读 `tools/gates/expected-red.txt`**，也不建第二份「live 名单」文件。
  **这一条偏离了本节改写前逐字写着的修法建议**（「真正的修法是给判定器加一份『live 名单』」），
  偏离照实记在这里：① 可推定 live 下 19 条应当全绿，那份文件落地后**内容为空**，
  与「全绿」是同一个契约；② 加一份名单就要给它再配一条棘轮，而棘轮是 `.github/workflows/**` 的改动。
  **不声称「写死更紧」**——把逃生口从一份有棘轮的文本文件挪进代码，不是变紧而是**换了个位置**
  （判定器此刻的保护现状见下一小节）。写死的真实优点只有两条：省一个可被写长的面、不需要动 CI。
- **残余风险**：将来若真出现「live 下也必须红」的门禁，写死的契约会把它变成硬阻塞，需要人改判定器。
  届时应当把契约从「全绿」改成「读一份 live 名单」，**并同时给那份名单配棘轮**——
  两件事必须一起做，只加名单不加棘轮是净放松。

### 判定器自身的保护现状，与那段还没闭合的空窗期

2026-08-22 逐条实测：**三层既有保护没有一层覆盖判定器**——
`gates-untouched` job 只 diff `tests/gates/**`；`tools/gates/gate-verify.mjs` 的
`PROTECTED = ["tests/gates/"]`；`expected-red-ratchet` job 只数 `expected-red.txt` 的行数。
而 `gates-l1` job 跑的**就是判定器本身**：判定器被改废之后会在 CI 上**自证为绿**。

已落地的加严是**文档级**的：`docs/context/ai-autonomy-policy.md` 的 Protected Areas 表新增了
`tools/gates/check_expected_red.py` 一行（`plan-first`），边界写明**不覆盖 `expected-red.txt`**
（账本允许在同一提交里划短，出处是 `AGENTS.md` 红线 1 的「边界」句与该表第 2 行；
把账本圈进守卫会让每一次合法的划短在 CI 上失败）。

**空窗期照实记**：文档级约束对拿着 shell 的执行器没有强制力，真正带牙齿的是 CI 侧守卫
（把 diff 范围扩到 `tools/gates/check_expected_red.py` 的 `verdict-tool-untouched` job），
它由 plan `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md` 承接。
**空窗期的两个端点照实记**：起点是本节被写下的那一刻（守卫还没上线），
终点是 `verdict-tool-untouched` 合并进 `main` 的那一刻（见下面第二个小节）。
空窗期内唯一带牙齿的控制是**自愿**在改判定器的提交上带一行 `Gates-Change-Approved-By:` trailer——
它当时不是本仓要求的（判定器不在 `gates-untouched` 的路径里，没有任何 job 会检查它），
但它让那次改动在 `git log` 里**可被检索**。

### CI 怎么用这个判定模式（`gates-l2-live` job，plan `2026-08-22-0027-2` 交付）

`.github/workflows/gates.yml` 末尾的 **`gates-l2-live`** job 是 live 判定模式在服务端的唯一消费者：
它在 runner 上起栈，然后用 **`python3 tools/gates/check_expected_red.py`** 对**全部 19 条门禁**做一次判定，
env 为 `AGENERP_LIVE=1` · `AGENERP_ADMIN_PASSWORD=admin` · `AGENERP_SITE=frontend` ·
`AGENERP_SITE_URL=http://127.0.0.1:8080`（`AGENERP_HTTP_PORT` 不设，走 compose 默认 8080）。

**它与 `gates-l2` 的覆盖面是包含关系**：`gates-l2` 只跑 `tests/gates/test_zero_dep_boot.py` 三条，
`gates-l2-live` 跑的 19 条**完全包住**它。两个 job 因此**冗余**——保留 `gates-l2` 是因为
本仓对红线 2 的自查已固化成「新文件以旧文件为行前缀」，删 job 会直接打掉那条判据；
退休它是删除动作，已登记为人动作 Deferred（见 plan `2026-08-22-0027-2` 的 `Deferred But Adjudicated`）。
**不要把两个 job 读成「判的是不同东西」**，它们判的是同一批门禁，后者是前者的超集。

**`AGENERP_SITE=frontend` 是 job 级的，它有一个必须点名的副作用**：
它把 `tests/gates/test_snapshot_diff_structured.py` 的
`::test_two_snapshots_of_unchanged_site_diff_empty` 与 `::test_diff_is_structured_not_text`
**从离线来源翻到活站点上**——这两条不取任何 fixture、直接调 `capture()`，所以只能由命令行 env 供给站点。
实测影响面**恰好只有这两条**（`test_normalizer_idempotent.py` / `test_seed_dataset_absurdity.py` /
`test_zero_dep_boot.py` 都不调 `capture()`）。**后果**：两条原本是纯离线的绿 L1，
进 `gates-l2-live` 之后变成**依赖活站点**；它们在 `gates-l1` 里仍按离线判定，两处判据来源不同。

**「L2 在 CI 上不受预期红名单棘轮保护」这条残余风险已被覆盖**：`gates-l2-live` 走的是判定器，
而 **live 模式的契约是「全部绿、零 red、零 skip」，比预期红名单棘轮更紧**——
棘轮只拦「名单变长」，live 契约连一条 skip 都不放过，且没有任何名单可以把一条红登记成「预期」。
上一小节那条风险因此在 `gates-l2-live` 的覆盖面（19 条全部）上收口；
`gates-l2` 自己那条绕开判定器的路径仍然存在，但它的覆盖面是 `gates-l2-live` 的子集。

### 判定器的 CI 侧守卫（`verdict-tool-untouched` job）与它的实证边界

上一小节说的那段空窗期，由 `gates.yml` 末尾的 **`verdict-tool-untouched`** job 闭合：
逻辑与 `gates-untouched` 同构（同一套 `BASE`/`HEAD` 推导、同一个全零 sha 分支、
同一个 `^Gates-Change-Approved-By:` 匹配式），只有 diff 路径不同——
它盯的是 **`tools/gates/check_expected_red.py`** 与 **`tools/gates/gate-verify.mjs`**。

**硬边界：路径清单里没有 `tools/gates/expected-red.txt`，这是刻意的。**
账本允许在同一提交里划短（`AGENTS.md` 红线 1 的「边界」句 + 本仓 Protected Areas 表第 2 行
`allowed（只能变短）`），服务端控制是既有的 `expected-red-ratchet` job。
把账本圈进守卫会让**每一次合法的划短**在 CI 上失败。

**⚠️ 实证边界，不得读成「守卫已全面实证」**：守卫的三次变异实验全部在 **PR 分支**上做，
因此**只证明了 `pull_request` 那条 `BASE`/`HEAD` 推导路径**。
`gates.yml` 的 `on: push` 限定 `branches: [main]`，所以 **`push` 那条分支在合并前无法实测**；
而交付证据又以合并后 `main` 上那次 `push` 运行为权威运行。
两条路径的代码是同构的，但「同构」是读出来的，不是跑出来的。

**顺带记一条待人处理的措辞不一致**：`docs/context/ai-autonomy-policy.md` 的 Protected Areas 表把
`.github/workflows/**` 标为 `blocked`，而该表第 72 行自称是 `AGENTS.md` 红线表的**转录**
（「下表前八条全部照抄⋯此处不新增、不放宽任何一条」），红线 2 原文只禁**变松**。
纯新增、零删除、不变松的改动落不落在禁止面内，两处措辞给不出同一个答案。
已登记为人动作 Deferred（plan `2026-08-22-0027-2` 的 `Deferred But Adjudicated` 首条），
**下一个要动 `gates.yml` 的 plan 直接引它，不必从零再论证一遍**。

### L2 门禁在 CI 上不受预期红名单棘轮保护（既有残余风险，原样保留）

`gates-l2` job 的那几条门禁在 CI 上不受预期红名单棘轮保护：有人把它们改绿而不改实现，棘轮不会响。
**代偿控制**：`gates-untouched` job 仍然拦着对 `tests/gates/**` 的无批准改动，
而那几条断言就在 `tests/gates/**` 内。
**这条风险已由上面的 `gates-l2-live` 收口**（它走判定器，live 契约比棘轮更紧，且覆盖面是 `gates-l2` 的超集）；
本小节原样保留，是因为 `gates-l2` 那条绕开判定器的路径**仍然存在**——
它只是不再是本仓对 L2 的唯一服务端判定。
