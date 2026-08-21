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
