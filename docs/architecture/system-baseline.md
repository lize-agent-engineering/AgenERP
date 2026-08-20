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
