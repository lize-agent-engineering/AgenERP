# 2026-08-21-1922-1 站点来源接活站点（工作项 4 的 B 半：`SiteSnapshotSource.read`）

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 4. 工具契约层 v0（先包 10 个只读工具）—— **只做 B 半：站点只读传输 + `SiteSnapshotSource.read`，不做工具执行器**
> Last Reviewed: 2026-08-21
> Source: plan `2026-08-21-1022-2-tool-contract-layer-v0.md` 的 `## Deferred But Adjudicated` 第一条（「工作项 4 的 B 半」，`Successor Required: yes`），其重开事件已于 2026-08-21T11:13Z 由人满足 · `docs/backlog/p0-foundation-roadmap.md` 工作项 4 · `docs/architecture/module-boundaries.md` §11.5「留给工具契约层的接缝」
> Related: `2026-08-21-1922-2-export-customizations-live.md`（第 2 顺位，**依赖本 plan 的站点客户端**）· `2026-08-21-1922-3-execute-plan-site-delete.md`（第 3 顺位，依赖本 plan 与第 2 顺位）· `2026-08-21-1553-1-diff-apply-engine-pure-half.md`（A 半，本 plan 接它留下的两个站点侧落点之一）
> Audit: required

## Current Baseline

起草时（2026-08-21，HEAD `a9de1bb`）逐条读活代码与活门禁得出，不靠记忆、不抄旧 plan。

### 前置已经解开：三个 fixture 由人写完了

- 2026-08-21T11:13Z，人在 `ede5440` 里**实现了** `compose_stack` / `live_site` / `pack_repo` 三个 fixture
  （`tests/gates/conftest.py`，随后 `9dff054` 补端口预检、`1bfd626` 补 URL 编码）。
  这正是 `docs/masterplan/STATE.md` §3 那条 `[open]` 的处置项 **(a)**，也正是本 plan 两个前驱
  （`…-1022-2` 与 `…-1553-1`）在 `Deferred But Adjudicated` 里写下的**重开事件**。
- 三个 fixture 的行为（读活代码确认，不是读注释）：
  - `compose_stack`（`tests/gates/conftest.py:137`）：`AGENERP_LIVE=1` 才真跑，否则 `pytest.fail`；
    自己 `docker compose up -d --wait`，且只拆自己起的栈。
  - `live_site`（`:227`）：经 REST 用 `Administrator` 登录，`add_custom_field` / `has_custom_field` 真打站点，
    teardown 删净探针字段。站点名硬编码 `frontend`（`:40`），HTTP 端口取 `AGENERP_HTTP_PORT`（`:41`，默认 8080）。
  - `pack_repo`（`:302`）：git 管理的临时目录，布局 `<root>/doctypes/<DocType>.json`，
    载荷形状 `{"doctype": ..., "custom_fields": [{"fieldname": ...}, ...]}`（`:241` 起的 `PackRepo`）。
    **它刻意不复用 `agenerp` 的解析函数**——这一点对第 2、3 顺位的 plan 是硬约束，对本 plan 只是背景。
- **`AGENTS.md` 红线 1 依然生效**：本 plan 不改 `tests/gates/**` 任何文件一个字节。fixture 是人写的，不是本 plan 的产物。

### 本 plan 要填的洞

- `agenerp/snapshot.py:146` `SiteSnapshotSource.read` —— 函数体逐字 `raise NotImplementedError(... 工作项 4 · 工具契约层 v0)`。
  **今天仓里不存在任何一行连活站点的产品代码**（`agenerp/` 全树 grep 无 `urllib` / 无 HTTP 客户端）。
- `agenerp/snapshot.py:185` `resolve_source` 的次序是 **显式来源 > `AGENERP_SITE` > 离线来源**，已实现；
  `SiteSnapshotSource(site)` 只带一个站点名字段（`:137` 的 frozen dataclass），**没有 URL、没有凭据的落点**。
- 因此 `capture(scope="doctypes")` 在配了 `AGENERP_SITE` 的环境里今天必然抛 `NotImplementedError`。

### 判据：能被本 plan 关掉的门禁只有一条，而且它要**两个**环境变量

| 门禁 | 今天 | 本 plan 关掉它需要什么 |
|---|---|---|
| `test_snapshot_diff_structured.py::test_field_addition_shows_up_as_structured_change` | 预期红（`tools/gates/expected-red.txt` 第 5 条非注释行）。转绿要 `AGENERP_LIVE=1` **且** `AGENERP_SITE`，**缺一仍红**（下面那段展开） | 活站点 + `SiteSnapshotSource.read` 真能答出「站点现状是什么」 |
| 同文件另两条（L1，已绿） | 走离线来源 | **不得回归**；且见下面那条环境依赖 |

**必须先说清的一件事（起草时读活代码发现，评审复核确认）**：那条门禁调的是
`capture(scope="doctypes")`（无参），来源由 `agenerp/snapshot.py:185` `resolve_source` 按
**显式来源 > `AGENERP_SITE` > 离线来源** 解析。而 `tests/gates/conftest.py` 的三个 fixture
**一个都不设 `AGENERP_SITE`**（该文件全文无此变量），它自己文档化的 L2 跑法也只有
`AGENERP_LIVE=1 python3 -m pytest tests/gates -m live -q`。

→ **只带 `AGENERP_LIVE=1` 跑，这条门禁仍然红**（走离线来源 → 两次空快照 → `d.is_empty()` → 断言失败）。
它转绿需要 `AGENERP_LIVE=1` **和** `AGENERP_SITE=frontend` 两个条件，后者**必须由调用命令给**。

本 plan 的处理，三条都不越线：

1. 本 plan 的 live 命令自带 `AGENERP_SITE=frontend`，并把完整命令写进 `docs/context/project-context.md`。
2. **不改 conftest 去补这个 env**（红线 1），**不在产品代码里把 `AGENERP_LIVE` 当成站点开关**
   （那是把测试环境耦合进产品，且等于绕过 harness 自己的口径）。
3. 把「harness 官方跑法与这条门禁的 env 需求对不上」作为**事实**追加给人
   （见下一节的处置口径）。可选出路至少三条，loop 不替人选：
   (a) 人在 conftest 里给 live 跑法补 `AGENERP_SITE`（红线 1，只有人能做）；
   (b) 把「L2 跑法」的口径改成本 plan 文档化的完整命令，将来 CI 的 L2 job 照它写；
   (c) 让 `resolve_source` 在站点可达时自动选站点来源——**loop 的建议是不要**，
   自动探测会让「离线也能绿」和「站点没起也能绿」两种假绿都变得可能。

### 账本：名单为什么一行都不能动（人已裁定过一次，本 plan 只补事实）

- `tools/gates/check_expected_red.py:59-60` 跑的是 `pytest tests/gates -q --tb=no --junitxml=…`，
  **没有 `-m 'not live'`**：L2 门禁总是被收集、总是被执行，默认环境下全部 `pytest.fail` → 红 → 留在名单内。
  起草时实测：`python3 tools/gates/check_expected_red.py` → **exit 0**，「门禁 19 项：预期红 7，绿 12，跳过 0」。
- **人在 `STATE.md` §2（2026-08-21T11:20Z）已经就同一件事裁定过**：
  `test_stack_boots_and_all_services_healthy` 在 `AGENERP_LIVE=1` 且端口空闲时实测 PASS，
  但人明写「⚠️ 该条**仍留在预期红名单**……**名单必须反映判定器实际看到的，不是我知道的**」。
  → 本 plan 直接沿用这条既有裁定：**live 环境下转绿不构成划名单的理由**，名单一行不动。
- 由此推得的、本 plan 要实测确认的一条（Phase 3）：带 `AGENERP_LIVE=1` 跑判定器时，
  已转绿的名单内门禁会被判成「名单内的门禁却绿了」→ exit 1。
  **注意还有第二种形态**：`test_two_snapshots_of_unchanged_site_diff_empty` 与 `test_diff_is_structured_not_text`
  **不在名单内**，在配了 `AGENERP_SITE` 的环境里它们改走站点来源，站点若答不上话会红成
  「名单外的门禁红了（真的坏了）」。两种形态同为 exit 1、语义完全不同，实测时不得混为一谈。
- **工作项 4 保持 `planned` 的理由不是「名单没划」**：roadmap 对照表第 4 行给它绑的是
  「提供 `live_site` fixture，解锁 L2 各项」，**它压根没有一条属于自己的门禁测试**，
  「门禁转绿并从名单划掉」这个 `done` 定义对它字面不可满足。这与工作项 7 的情形一模一样，
  而工作项 7 那条已由人在 STATE §3 以 `[resolved]` 处置过：保持 `planned`、不改定义、留痕即可。
  本 plan 照此办理，**不新开 needs-human 条目**，只按 §3 里 P0.7 那条「补充事实行，不另开条目」的先例追加。

### 本机环境的两条实测约束

- 端口 8080 **已被另一套常驻栈占用**（起草时 `lsof -nP -iTCP:8080 -sTCP:LISTEN` 命中 Docker Desktop 的监听，
  `docker ps` 里另有一组 `docker-*` ERPNext 容器）。`compose_stack` 有端口预检并会直接 `fail`，
  所以本仓一切 live 命令**必须带 `AGENERP_HTTP_PORT=18080`**
  （`docker-compose.yml:255` 的映射是 `"127.0.0.1:${AGENERP_HTTP_PORT:-8080}:8080"`，改得动）。
- 起栈的健康判定口径取 `docs/architecture/system-baseline.md` §14.2（**六个服务**这个收窄集合，三个 worker 不可判）；
  「冷起约 68 秒」这个数出自 `docs/context/project-context.md` 的验证命令表与 `STATE.md`，**不在 §14.2 里**，引用别混。

### 实测回填（Phase 3，2026-08-21 · 起草时的预判有两处不准，照实改写）

**起草时的预判 vs 实测**：

| 起草时写的 | 实测 |
|---|---|
| 带 `AGENERP_LIVE=1` 跑判定器 → 「名单内的门禁却绿了」→ exit 1 | **成立**。exit 1，两条：`test_field_addition_shows_up_as_structured_change`（本 plan 让它绿的）+ `test_stack_boots_and_all_services_healthy`（人在 §2 11:20Z 已裁定过的那条） |
| 「第二种形态」：两条 L1 快照门禁改走站点来源后可能红成「名单外的门禁红了」 | **栈预先起好时没有出现**——两条 L1 在活站点上照样绿。但它换了个形态真的发生了，见下一行 |
| （未预见） | **起栈顺序陷阱**：两条 L1 快照门禁**不取任何 fixture**，配了 `AGENERP_SITE` 之后它们在 `compose_stack` 拉起栈**之前**就跑完了 → 红在 connection refused。栈没预起时那条 live 命令 **exit 1（`FF.`，两次复跑逐字一致）**，而第三条 live 门禁在同一次运行里**是绿的**。**栈预先起好再跑同一条命令 → exit 0（3 passed）**。这是接线问题不是实现问题，解法在 harness 侧（红线 1），已按 P0.7 先例写进 STATE §3 |
| 「全新 ERPNext 站点上 `len(capture("doctypes"))` **必须 > 20**，等于 20 就是分页没关掉」 | **这条判据的阈值不成立，照实记**：本站点 Custom Field **总共只有 10 条**，站点自报计数 `frappe.client.get_count` 也是 **10**——两数一致，说明读全了，不是被截断（截断只会给出**恰好 20**）。10 < 20 让原阈值无从判别，故换了一条**更直接**的证明，见下 |

**完整性（不变量 3）在 live 层的证明——换了判据，理由写清**：原判据（条目数 > 20）在这个站点上不可判。
改用同一条代码路径去读一张**行数远超默认页长**的表，并做变异验证：

| 命令 / 动作 | 结果 |
|---|---|
| `client_from_env('frontend').list_resource('Custom Field')` | **10 行**；站点自报 `get_count` = **10**（读全了） |
| `client_from_env('frontend').list_resource('DocType')` | **775 行**；站点自报 `get_count` = **775**（Frappe **认** `limit_page_length=0`） |
| 变异：从 `list_resource` 里删掉 `PAGE_LENGTH_PARAM` 那一行后同一条调用 | **20 行**（Frappe 的默认页长，逐字命中假绿的形态） |
| 还原后同一条调用 | **775 行**；`shasum -a 256 agenerp/site.py` 变异前 / 还原后同为 `22ae0d34…9165d424` |

这一条正是起草时说的「假传输只能证明客户端**发了**那个参数，证明不了 Frappe **认**这个参数」——
现在两边都证到了：单测证明参数被发出，live 的 775 vs 20 证明它被 Frappe 认下。

**live 实跑的全部命令与退出码**（`docs/logs/2026/08-21.md` 同步落盘）：

| 命令 | 退出码 |
|---|---|
| `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q`（栈未预起，plan 原文那条） | **1**（`FF.` · 2 failed, 1 passed · 25.80s；原样复跑 → 同样 exit 1、25.92s、逐字同因） |
| `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait` | **0**（20.5 秒，**热卷**；六个服务 healthy，口径取 `system-baseline.md` §14.2） |
| 同上第一条命令，**栈预先起好** | **0**（3 passed，3.03s） |
| 同上，变异（`SiteSnapshotSource.read` 返回空元组） | **1**（1 failed, 2 passed，逐字红在 `test_field_addition_shows_up_as_structured_change`） |
| 同上，还原后 | **0**（3 passed；`shasum -a 256 agenerp/snapshot.py` 变异前 / 还原后同为 `f3d421f7…e0496e21`） |
| `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 tools/gates/check_expected_red.py` | **1**（「门禁 19 项：预期红 5，绿 14，跳过 0」+「❌ 名单内的门禁却绿了」两条，**只有这一种形态**） |
| `python3 tools/gates/check_expected_red.py`（默认环境） | **0**（门禁 19 项：预期红 7，绿 12，跳过 0） |
| `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down` | **0**（`agenerp-` 容器残留 0 个；站点上 `agenerp_gate_probe` 探针残留 0 条，`live_site` 的 teardown 干净） |

**verification scope limited**：live 实证只在本机做过（compose v5.0.2、端口 18080、**热卷**——站点由此前运行留下，
20.5 秒不是冷起的 68 秒）。CI runner 是 compose 2.38.2，版本差是 plan `…-1022-1` 已登记的 watch-only residual。
**不得报为「CI 上也验证过」。**

### 执行顺序与 roadmap 的表面冲突（先说清，免得被读成矛盾）

roadmap 的 `Work Item Status` 块写「顺序即执行顺序」，列的是 4、5、6。
本批三个 plan 的实际顺序是 **4 的 B 半 → 6 的导出 → 5 的删除**：
删除那条门禁的前四行代码要先能导出（`export_customizations`）才走得到 `apply_pack`，
这是判据本身的依赖，不是偏好。三个 plan 的 `Related` 已互相声明；roadmap 第 5/6 行的
现状说明由各自的 plan 在 Phase 3 补上。

## Goals

- 交付**站点只读传输**：`agenerp` 内一个连活站点的 HTTP 客户端，零第三方依赖（只用标准库），
  凭据与地址全部来自环境变量，**产品代码不内置任何口令默认值**。
- 交付 `SiteSnapshotSource.read`：给定 scope 返回真站点上的条目，口径与离线来源同源
  （同一套 `normalize` 剥易变字段），使「同一站点两次快照 diff 为空」在活站点上也成立。
- 交付**判据**：`tests/unit/` 下用假传输覆盖行为（`GATE_VERIFY` 复跑得到），
  外加一次真站点上的 L2 实跑，让 `test_field_addition_shows_up_as_structured_change` 转绿。
- 交付**一条实测清楚的交接**：预期红名单与 live 环境的矛盾、以及 harness 官方 L2 跑法缺 `AGENERP_SITE` 这件事，
  **按 §3 里 P0.7 的先例补进既有那条 `[open]`**（不新开 needs-human 条目——名单口径人已在 §2 的 11:20Z 裁定过）。

## Non-Goals

- **不做工具执行器**：`agenerp/tools_readonly.py` 里十条契约的**运行时调用**属 P1 控制循环
  （plan `…-1022-2` 已把它登记为 deferred，重开事件是 P1 开工）。本 plan 只交付传输与快照来源两处。
- 不实现 `export_customizations`（第 2 顺位）、不实现 `execute_plan`（第 3 顺位）、不实现 `schema_drift`。
- 不写任何站点侧写操作。本 plan 的客户端**只发 GET**；写与删由第 3 顺位的 plan 扩展。
- **不生成运行时 Server Script**（红线 7）；不装任何第三方依赖（CI 的 `gates-l1` 只 `pip install pytest`）。
- 不改 `tests/gates/**`（红线 1）、不改 `.github/workflows/**`（红线 2）、不改 `missions/**`、
  不改 `docs/masterplan/DECISIONS.md`；`STATE.md` 仅**追加**证据行与一条**补充事实行**，**不新开 needs-human 条目**。
- **不划掉 `tools/gates/expected-red.txt` 任何一行**（理由见 Current Baseline 末节）。
- **不把工作项 4 置为 `done`**，只把它保持在 `planned` 并在 roadmap 上补一行现状说明。
- 不改 `resolve_source` 的解析次序、不改 `capture` / `diff` / `normalize` 的既有语义。

## Task Route

- Type: `app-layer design change`（新增一个连外部系统的模块，P1/P2 的 Agent 都会经它读站点）
- Owner Docs: 读 `docs/architecture/module-boundaries.md` §11.5（快照三部件的职责与两条显式拒绝）、
  §7.2（只读工具的返回口径）· 读 `docs/architecture/system-baseline.md` §14.2（起栈与健康判定口径）·
  待更新：`docs/architecture/module-boundaries.md`（**追加**一小节 §11.7 记站点来源的落点与凭据口径）与
  `docs/context/project-context.md`（验证命令表增一行 L2 实跑命令）
- Skill Selection Basis: `docs/skills/README.md` 的技能表里没有「接外部系统 HTTP 传输」对应的**工作方法**技能；
  形状被 §11.5 已定稿的 `SnapshotSource` 协议约束，属受限选择。各执行阶段 `Skill: none`；
  草案评审用 `docs/skills/plan-audit-prompt.md`，关闭审计用 `docs/skills/closure-audit-prompt.md`。

## Infrastructure And Config Prereqs

- **无新增第三方依赖**：客户端只用标准库（`urllib` / `json` / `http.cookiejar`）。
- 环境变量（本 plan 定稿，写进 owner doc）：

| 变量 | 含义 | 默认 |
|---|---|---|
| `AGENERP_SITE` | 站点名，同时用作 HTTP `Host` 头 | 无（未设即走离线来源，既有行为不变） |
| `AGENERP_SITE_URL` | 站点基址 | `http://127.0.0.1:${AGENERP_HTTP_PORT:-8080}`（与 `docker-compose.yml` 的端口映射同源） |
| `AGENERP_API_KEY` / `AGENERP_API_SECRET` | Frappe token 认证 | 无 |
| `AGENERP_ADMIN_USER` / `AGENERP_ADMIN_PASSWORD` | 会话登录（token 未配时的回退） | 用户名默认 `Administrator`；**口令无默认值** |

- **口令绝不内置默认值**：`tests/gates/conftest.py:44` 给 fixture 自己留了 `admin` 默认值，那是测试脚手架；
  产品代码内置口令等于把「本地默认口令」变成一条对外暴露时会咬人的隐性配置。缺凭据时**显式报错并指名缺哪个变量**。
- `Host` 头必须等于站点名：`docker-compose.yml` 的 `backend` 探针注释逐字写着「gunicorn 按 Host 解析站点，
  打 127.0.0.1 会被当成一个叫 127.0.0.1 的站点而 404」。这条不是猜的，是仓里已实测的结论。
- 路径必须 URL 编码：DocType 名带空格（`Custom Field`），不编码时 `http.client` 直接以
  `URL can't contain control characters` 拒掉（`tests/gates/conftest.py:183` 的注释，`1bfd626` 那次修复）。
- 回滚策略：一个新模块 + `SiteSnapshotSource.read` 一处实现 + 文档追加。`git revert` 即回到今天的状态；
  无数据迁移。**站点侧无副作用**——本 plan 只发 GET。

## 结构边界（本 plan 定稿的接口契约）

按计划指南规则 6 的例外：这是模块边界定义，不是实现伪代码。

| 落点 | 契约 | 谁实现 |
|---|---|---|
| `agenerp/site.py` · `SiteClient` | 连活站点的**唯一**传输落点。构造只需站点名，其余从环境解析；`get(path, params) -> dict`（非 2xx 抛，不返回空）。**本 plan 内只有读方法** | 本 plan |
| `agenerp/site.py` · `SiteError` | 站点侧一切失败的统一异常类型（连不上 / 认证失败 / 非 2xx / 载荷不是 JSON）。**绝不降级成空结果** | 本 plan |
| `agenerp/site.py` · `client_from_env(site)` | 环境 → 客户端的组装点，缺凭据时抛 `SiteError` 并指名缺哪个变量 | 本 plan |
| `agenerp/snapshot.py` · `SiteSnapshotSource` | 增一个**可选**注入字段（默认 `None` → 走 `client_from_env`），既有构造式 `SiteSnapshotSource(site)` 两处调用点不变 | 本 plan |
| `agenerp/snapshot.py` · `SiteSnapshotSource.read(scope)` | `scope == "doctypes"` → 站点上**全部** Custom Field 转成 `SnapshotEntry`，载荷先过 `normalize`，按 `key` 排序；**未知 scope 显式抛，不返回空元组**。**必须显式关掉分页**（Frappe 的 `/api/resource` 默认只回 20 条）并显式要全部字段——少读一页会让「未改动 → diff 为空」在缺条目时照样绿，是一条假绿 | 本 plan |
| 条目身份的取值 | `SnapshotEntry.doctype` 取站点行的 **`dt`**（Custom Field 的归属 DocType 存在 `dt` 列，**不叫 `doctype`**；`agenerp/snapshot.py:37` 的 `_DOCTYPE_KEY = "doctype"`（`:172` 是它的使用处）是**包文件**那侧的键，不能照搬），`fieldname` 取 `fieldname`。身份是 `(doctype, fieldname)` 二元组（§11.5），这一格错了整份快照就错了 | 本 plan |
| `agenerp/snapshot.py` · **站点行 → `attributes` 的投影** | 「一行 Custom Field 变成条目的哪些属性」**只能有一个落点**，本 plan 交付的版本是「剥易变键之后全留」。第 2 顺位若为了 diff 可读性收窄它（例如再剥空值），**必须改这一个落点**：导出与站点读取用不同投影，会让 `plan_apply` 把每个字段都算成 `changed` | 本 plan（第 2 顺位可收窄） |
| `agenerp/site.py` · 写/删方法 | **不在本 plan 内**，第 3 顺位扩展 | successor |

**四条不变量**（每条都要有自己的判据，不许只写在注释里）：

1. **不伪装成功**：站点连不上 / 认证失败 / 返回非 2xx → 抛 `SiteError`。
   返回空快照会让「未改动 → diff 为空」这条判据在站点宕机时照样绿——那是本仓明令禁止的假判据。
   （注意与 §11.5「位置不存在 → 空元组，不抛」的分界：那条讲的是**离线目录**不存在，
   「这个 scope 还没有定制」是合法状态；而**站点答不上话**不是合法状态。）
2. **确定性**：同一站点连读两次，条目集合必须逐条相同 —— 剥易变字段用的是 `agenerp.pack.normalize`
   同一个函数，不开第二套口径（§11.5「不该有第二份」）。
3. **完整性**：`read` 拿到的必须是站点上**全部** Custom Field，条数可核对（Phase 3 抄实测条目数）。
   分页截断与「站点真的只有这么多」在快照层长得一模一样，只能靠显式关分页 + 断请求参数来挡。
4. **只读**：本 plan 的客户端不提供任何写方法。判据是一条**显式白名单**结构断言——
   「公共方法名里出现 `agenerp/contracts.py:40` 的 `WRITE_VERBS`（`create` / `write` / `submit` / `cancel` /
   `delete` / `amend`）的，必须在白名单里；**本 plan 内白名单为空**」。
   **为什么不写成「一个写动词都不许出现」**：第 3 顺位要在同一个 `agenerp/site.py` 上加删除方法
   （`plan …-1922-3` Phase 2），那时这条断言会当场把它打红，而它是一条已关闭 plan 交付的判据，
   届时只有「动别人的判据」和「卡住」两条路——两条都不该走。
   白名单形式让它按**收窄**演进：第 3 顺位把 `delete_custom_field` 加进白名单并说明理由，
   判据始终在，且每加一个写方法都要留一次痕。

## Execution Plan

### Phase 1 — 站点传输落盘（`agenerp/site.py`）

Status: completed
Targets: `agenerp/site.py`（新文件）、`tests/unit/test_site_client.py`（新文件）
Skill: `none`
Prereqs: 无

- Item Types: 3 `Add` / 1 `Decision` / 1 `Proof`（未到 80% 门槛，故不作 phase 级统一声明）

- [x] `Add` 实现 `SiteClient` / `SiteError` / `client_from_env`，只用标准库，只有读方法。
- [x] `Add` 凭据解析：token 优先，回退会话登录；**缺凭据时抛 `SiteError` 并指名缺哪个环境变量**。
- [x] `Add` `Host` 头 = 站点名；路径 URL 编码（保留 `/` 分隔）。
- [x] `Decision` **认证方式取「token 优先、会话登录回退」**。备选：① 只做会话登录（最省事，但把口令带进每次运行，且
      Frappe 的登录端点有速率限制）；② 只做 token（更贴生产，但零依赖栈上没有现成 key，L2 门禁跑不起来）。
      取两者兼容的理由与残余风险（回退路径把口令读进内存）写进 `module-boundaries.md` 追加小节。
- [x] `Proof` 单测（`tests/unit/test_site_client.py`，**不连真站点**，**用注入式假传输**——
      不起本地 `http.server`：本机端口冲突在本 plan 的 Current Baseline 里已经是实测事实，
      CI 的 `gates-l1` 与 `GATE_VERIFY` 里再绑一个端口是自找的不稳定源）：
      非 2xx → 抛 `SiteError`；连不上 → 抛 `SiteError`（用一个立即关闭的 socket 构造）；缺凭据 → 抛且消息含变量名；
      `Host` 头、URL 编码、**显式关分页的请求参数**各一条；
      **写动词白名单**一条——「公共方法名里出现 `WRITE_VERBS` 的必须在**显式白名单**内，本 plan 白名单为空」，
      且测试里的白名单是一个**可见的字面量列表**（不是「`site.py` 内一律放行」式的宽松匹配）。
      写成「一个写动词都不许出现」的话，第 3 顺位加 `delete_custom_field` 时会被一条已关闭 plan 的判据当场打红。

Exit Criteria:

- [x] `python3 -m pytest tests/unit -q` → exit 0，且新文件的用例真在其中（记录用例数增量）
- [x] `ruff check agenerp tests/unit tests/contracts` → exit 0
- [x] `docs/architecture/module-boundaries.md` 追加小节落盘（凭据口径 + 认证 Decision）
- [x] `docs/logs/2026/08-21.md` 追加条目

### Phase 2 — 接上 `SiteSnapshotSource.read`

Status: completed
Targets: `agenerp/snapshot.py`、`tests/unit/test_snapshot_capture.py`、`docs/architecture/module-boundaries.md` §11.5
Skill: `none`
Prereqs: Phase 1

- Item Types: `Add | Fix | Proof`

- [x] `Add` `SiteSnapshotSource` 增可选注入字段；`read("doctypes")` 经客户端读 Custom Field，
      载荷过 `normalize` 后转 `SnapshotEntry`，按 `key` 排序。
- [x] `Add` 未知 scope 显式抛（不返回空元组），错误消息指名收到的 scope。
- [x] `Proof` 单测（假客户端注入）：两次 read 结果相同；含 `modified` / `creation` / `owner` 的原始行
      被剥干净（**否则同站点两次快照会 diff 出差异**）；同名字段挂在两个 DocType 上不被混成一条
      （身份是 `(doctype, fieldname)` 二元组，§11.5）；站点抛错时 `capture` **不吞异常**。
- [x] `Proof` 既有 L1 两条快照门禁在**无 `AGENERP_SITE`** 时行为逐字不变（跑判定器复核）。
- [x] `Proof` **完整性**：假客户端喂 25 条（超过 Frappe 默认页长 20）→ `read` 必须拿到 25 条，
      且断言请求里带了关掉分页的参数。少一条就是假绿的入口。
- [x] `Proof` **单测层的变异验证**（`GATE_VERIFY` 唯一看得见的层）：把投影里 `normalize` 那一步摘掉，
      `python3 -m pytest tests/unit -q` 必须转红并指名；还原后复跑转绿。
      不做这条，「两次快照相同」可能靠假客户端返回同一个字典而空转。
- [x] `Fix` **owner-doc drift（确认的，按指南规则 14 不可降级）**：`module-boundaries.md` §11.5 不变量表
      逐字写 `SnapshotSource` → 「位置不存在 → 空元组，不抛异常」，`agenerp/snapshot.py:109` 的 Protocol
      docstring 复述了同一句。本 plan 让站点来源在站点答不上话时**抛**，两处随即变成陈述性错误。
      **同一个 phase 里改掉**：§11.5 那一格改成「离线来源：位置不存在 → 空元组；站点来源见追加小节」，
      并同步 docstring。（`module-boundaries.md:11` 只禁止改**标题**，改表格内容不在禁令内。）

Exit Criteria:

- [x] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0
- [x] `SiteSnapshotSource.read` 不再 `raise NotImplementedError`；`agenerp/` 全树只剩
      `export_customizations`（`pack.py:66`）/ `schema_drift`（`snapshot.py:256`）/ `execute_plan`（`apply.py:107`）
      三处 `NotImplementedError`（逐条列出复核结果，行号以实际为准）
- [x] §11.5 不变量表与 `agenerp/snapshot.py:109` 的 Protocol docstring 已同步（owner-doc drift 已消）
- [x] `docs/logs/2026/08-21.md` 追加条目

### Phase 3 — 活站点实跑 + 名单矛盾实测 + 交接

Status: completed
Targets: `docs/masterplan/STATE.md`（**只追加**）、`docs/context/project-context.md`、`docs/backlog/p0-foundation-roadmap.md`
Skill: `none`
Prereqs: Phase 2

- Item Types: `Proof | Decision`

- [x] `Proof` 冷起并实跑 L2 快照门禁，命令原文（端口 18080，理由见 Current Baseline）：
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q`
      → 期望 exit 0（三条全绿）。**退出码与命令原文一并抄进 plan 与日志**，抄不到就不算过。
- [x] `Proof` **变异验证**（判据有没有牙齿）：临时把 `SiteSnapshotSource.read` 改成返回空元组，
      同一条命令必须**转红**且红在 `test_field_addition_shows_up_as_structured_change`；
      验证后立即还原（`git diff` 复核为空）。空转的判据等于没有判据。
- [x] `Proof` **完整性在 live 层的核对**（不变量 3 承诺了这一项，不能只落在假传输上）：
      在同一 live 环境里打印 `len(capture("doctypes"))` 并把数与命令原文抄进 plan 与日志。
      全新 ERPNext 站点上该数**必须 > 20**——**等于 20 就是分页没关掉**。
      假传输只能证明「客户端发了 plan 假定的那个参数」，证明不了 Frappe 认这个参数
      （写成 `limit` 而不是 `limit_page_length` 时，25 条那个单测照样绿而 live 上仍只读回 20 条）。
- [x] `Proof` **实测名单矛盾**：同样的 live 环境里跑 `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 tools/gates/check_expected_red.py`，
      记录退出码与输出原文。**不要预设结论**，且注意两种形态别混：
      「名单内的门禁却绿了」（本 plan 让它转绿的那条）与「名单外的门禁红了」
      （两条 L1 快照门禁改走站点来源后若站点答不上话）——同为 exit 1，语义相反。
      实际是什么就照抄什么，并据实改写 Current Baseline 那一节。
- [x] `Decision` 往 `docs/masterplan/STATE.md` §3 追加一行，**照 §3 里 P0.7 那条「补充事实行，不另开条目」的先例写**
      （挂在既有那条工作项 4 / `compose_stack` 的 `[open]` 上，**不新开 needs-human 条目**——
      名单口径人已在 §2 的 11:20Z 裁定过，本 plan 只补新事实）。要补的事实两条：
      ① harness 官方 L2 跑法不设 `AGENERP_SITE`，`test_field_addition_shows_up_as_structured_change`
      因此在那条跑法下仍红；三条可选出路（conftest 补 env / 改口径为完整命令 / 自动探测）loop 不替人选。
      ② 带 `AGENERP_LIVE=1` 跑判定器的实测退出码与输出原文。
      **同时如实引出授权链矛盾**（`01-EXECUTION-MODEL.md` §1 表禁止角色 B 手写 STATE vs 执行器人格要求写进
      needs-human 队列 vs 红线 5 允许追加），照既有两行的写法处理，不擅自消解。
- [x] `Add` `docs/context/project-context.md` 验证命令表增一行「L2 live 门禁」，写明完整命令、端口理由与
      **它不在 `missions/p0-foundation.json` 的 `commands.test` 里**（`GATE_VERIFY` 复跑不到，代偿控制是变异验证 + 独立关闭审计）。
- [x] `Add` `docs/backlog/p0-foundation-roadmap.md` 工作项 4 保持 `planned`（理由见 Current Baseline：
      它没有属于自己的门禁，`done` 的字面定义不可满足，与已 `[resolved]` 的工作项 7 同一情形），
      在对照表第 4 行补一句现状：
      B 半已落地、`test_field_addition_shows_up_as_structured_change` 在 live 环境实测转绿、
      但名单未动（原因指向 STATE §3 新增那行）

Exit Criteria:

- [x] live 三条命令的原文 + 退出码全部落进 plan 与 `docs/logs/2026/08-21.md`
- [x] 变异验证有牙齿（转红且指名），还原后工作区相对变异前基线无残留
- [x] live 环境下 `len(capture("doctypes"))` 的实测数已落盘且 > 20（分页确已关掉）
- [x] STATE §3 **按 P0.7 先例追加一条补充事实行**，挂在既有那条工作项 4 / `compose_stack` 的 `[open]` 上，
      **未新开 needs-human 条目**；**§2 与 §3 已有行一字未改**（用 `git diff` 复核）
- [x] `tools/gates/expected-red.txt` **一行未动**
- [x] `python3 tools/gates/check_expected_red.py`（默认环境）→ exit 0

## Draft Review Record

- 独立草案评审第 1 轮：**needs revision**（独立子代理，全新会话，2026-08-21）。八条发现，逐条已改：
  1. **[阻断]** `test_field_addition_shows_up_as_structured_change` 转绿需要 `AGENERP_LIVE=1` **和** `AGENERP_SITE` 两个条件，
     而 conftest 的三个 fixture 与它文档化的 L2 跑法都不设后者——原草案没说，等于头号交付物在 harness 官方跑法下绿不了。
     → 新增「判据……而且它要**两个**环境变量」整节，列三条出路交给人选。
  2. **[阻断]** 漏了**完整性**不变量：Frappe `/api/resource` 默认只回 20 条，分页截断会造出一条「两次快照 diff 为空」的假绿。
     → 结构边界表与不变量表各增一条，Phase 1/2 各增一条判据（含 25 条超页长的用例）。
  3. **[阻断]** 「工作项 4 因此停在 `planned`」归因错误——工作项 4 压根没有绑定门禁，情形与已 `[resolved]` 的工作项 7 相同；
     且人已在 STATE §2（11:20Z）就名单口径裁定过。→ 重写「账本」一节，Phase 3 的 `Decision` 从「新开 needs-human」降为
     「照 §3 里 P0.7 的先例追加补充事实行」。
  4. **[重要]** owner-doc drift：§11.5 不变量表与 `agenerp/snapshot.py:109` 的 Protocol docstring 都写「不抛异常」，
     会被本 plan 推翻。→ Phase 2 增一条 `Fix`（指南规则 14，不可降级）。
  5. **[重要]** 站点行 → 条目的投影没定 `dt → doctype`（Custom Field 的归属 DocType 存在 `dt` 列）。→ 结构边界表增一行。
  6. **[次要]** Phase 1 的 Proof 留了「`http.server` 或注入式假传输」的岔路未选。→ 定为注入式假传输，并增单测层变异验证。
  7. **[次要]** 四处行号/引用漂移（判定器 `:59-60`、名单「第 5 条」、conftest `:183`、68 秒不在 §14.2）。→ 全部更正。
  8. **[次要]** 执行顺序 4→6→5 与 roadmap「顺序即执行顺序」表面冲突。→ 新增一节说明。
  评审独立复核并确认的事实：判定器不带 `-m 'not live'`、默认环境 exit 0「19 项 / 7 预期红」、
  三个 fixture 由人在 `ede5440` 写完、8080 被占、`SiteSnapshotSource(site)` 正好两处调用点、无红线风险。
- 独立草案评审第 3 轮（确认轮）：**needs revision（一行）→ 已改 → accept**。评审指出第 7 条（白名单）
  只改了不变量表、没改真正落断言的 Phase 1 `Proof` 项——与第 2 轮 [阻断-1]「散文改了清单没改」同一个失败模式。
  → Phase 1 的 Proof 已改为白名单断言并要求白名单是可见字面量。评审对白名单改法的裁定：
  **成立，且确实是收窄不是放松**（断言仍在、默认拒绝；本 plan 白名单为空故与原写法严格等价；
  第 3 顺位加条目要付一次 diff + 一次留痕，是显式加宽自己的面，而不是削弱裁判）。原话：改完即 accept，不需要再送。
- 独立草案评审第 2 轮：**needs revision → 已改**（同一独立评审者，带上下文复评）。它逐条复核了第 1 轮八条：
  六条实质解决、一条「散文改了清单没改」、一条「只落了一半」。剩余四条，逐条已改：
  1. **[阻断]** 「不新开 needs-human」只写进了散文，而 Phase 3 的 **Exit Criteria**、Non-Goals、Deferred 重开事件、
     Goals 四处仍命令执行器新开一条——checklist 拦不住散文里的禁令。→ 四处全改成「按 P0.7 先例追加补充事实行 / 指向既有 `[open]`」。
  2. **[重要]** 完整性不变量承诺了「Phase 3 抄实测条目数」，而 Phase 3 没有这一项。假传输只能证明客户端**发了**关分页参数，
     证明不了 Frappe **认**这个参数（写成 `limit` 而非 `limit_page_length` 时 25 条那个单测照样绿）。
     → Phase 3 增 `Proof` + Exit Criteria：live 下 `len(capture("doctypes"))` 必须 > 20，等于 20 就是分页没关掉。
  3. **[次要]** 新引入的行号漂移 `snapshot.py:172` → `_DOCTYPE_KEY` 的赋值在 `:37`（`:172` 是使用处）；
     Phase 2 `Targets` 缺 `module-boundaries.md`、`Item Types` 缺 `Fix`；Phase 1 的「4/5 项为 `Add`」实为 3/5；
     判据表第 1 行的红因单元格没跟上散文。→ 全部更正。
  4. 评审同时确认：与 plan 2/3 无冲突；`apply_pack` 传的是**显式** source，所以第 3 顺位的四条 roundtrip 门禁
     **不需要** `AGENERP_SITE`，本 plan 把 env 耦合精确限定在裸 `capture()` 那条门禁上没有过度声张；红线仍然干净。
- **第 3 顺位的评审带回来一条跨 plan 冲突，本 plan 一并修**：不变量 4（只读）原写成「公共方法名里不出现写动词」，
  而第 3 顺位要在同一个 `agenerp/site.py` 上加删除方法——那会让一条已关闭 plan 的判据当场打红它的 Phase 2。
  → 改成**显式白名单**形式（本 plan 内白名单为空），让它按收窄演进而不是被推翻。

## Closure Gates

- [x] in-scope behavior is complete（`agenerp/site.py` 的传输 + `SiteSnapshotSource.read` 两处都落地并有行为判据，不是只有签名）
- [x] relevant docs are aligned（`module-boundaries.md` **新增 §11.7** + §11.5 不变量表与「接缝」段 + §11.6 红因段 + §7.6 的一条陈述、
      `project-context.md` 命令表新增「L2 live 门禁（快照）」一行、roadmap 对照表新增「4 现状」一行）
- [x] verification has run：`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`（默认环境）→ **exit 0**
      + `ruff check agenerp tests/unit tests/contracts` → **exit 0** + Phase 3 的 live 命令**逐条抄了退出码**（见「实测回填」表）
- [x] **verification scope limited 明写**：live 实跑只在本机（compose v5.0.2、端口 18080、**热卷 20.5 秒**而非冷起 68 秒）做过，
      CI runner 是 2.38.2，不得报成「CI 上也验证过」（沿用 plan `…-1022-1` 已登记的 watch-only residual）
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（三轮，见 `## Draft Review Record`）
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent（`docs/skills/closure-audit-prompt.md`）—— **本轮未做，属 `CLOSURE_VERIFY` 步骤的活**。
      执行会话内无可用的独立评审者，且执行器不得自审自判（`AGENTS.md` 裁判规则 1）。
      **本条未打勾即为如实状态**，不得据此把 plan 报成「已通过关闭审计」。
- [x] closure evidence exists in files（plan 的「实测回填」表 + `docs/logs/2026/08-21.md` 三条阶段条目 + STATE §3 补充事实行）
- [x] **红线自查**：`git diff --name-only -- tests/gates/ .github/workflows/ missions/ docs/masterplan/DECISIONS.md tools/gates/expected-red.txt`
      → **输出为空**；`git diff --numstat docs/masterplan/STATE.md` → **`8	0`**（第二列为 0，只增不改）

## Deferred But Adjudicated

### 十条只读工具契约的**运行时执行器**

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: plan `…-1022-2` 已把它连同 §7.4 熔断、§7.5 包裹动作一起登记为 P1 的活；
  P0 没有控制循环去消费它，现在实现只能得到「结构存在」的空断言。本 plan 交付的 `SiteClient` 正是它将来要用的传输。
- Successor Required: `yes`（P1 建控制循环时）
- 重开事件：P1 解释 Agent 控制循环开工。

### 预期红名单与 live 环境的矛盾

- Classification: `watch-only residual`（**对本 plan 而言**；对 mission 而言是硬阻塞，已登记）
- Why Not Blocking Closure: 本 plan 的交付物是站点来源，不是判据设施。矛盾已由 Phase 3 实测清楚并
  追加进 STATE §3，处置项只有人能选。本 plan 不动名单、不改判定器、不把工作项报成 `done`。
- Successor Required: `yes` —— 人做出选择之后，由工作项 8 的第二个 plan（CI 真跑 L2）承接
- 重开事件：人对 STATE §3 **既有那条 `[open]`** 的 (a)/(b)/(c)/(d) 作出选择。

### `doc.links` 字段名漂移（`from_is_submittable` vs `is_submittable`）

- Classification: `watch-only residual`
- Why Not Blocking Closure: plan `…-1022-2` 已登记，重开条件逐字是「接活站点实现 `doc.links` 时」。
  本 plan **不实现 `doc.links`**（那属工具执行器），因此重开条件未触发。
- Successor Required: `no`
- 重开事件：P1 实现 `doc.links` 的真实调用时。

## Closure

Status Note: 三个 Phase 全部执行完毕并逐项打勾。交付两处落点（`agenerp/site.py` 的站点只读传输、
`agenerp/snapshot.py` 的 `SiteSnapshotSource.read`）+ 26 条新单测（`tests/unit` 104 → **130**）。
`test_field_addition_shows_up_as_structured_change` 在活站点上**实测转绿**（exit 0，3 passed），
这是本仓第一条在真站点上绿的 L2 门禁。**`tools/gates/expected-red.txt` 一行未动、工作项 4 保持 `planned`**
（理由见 Current Baseline 的「账本」一节，沿用人在 STATE §2 11:20Z 的既有裁定）。

**起草时的两处预判不准，已在「实测回填」一节照实改写，不粉饰**：
① plan 原文那条 live 命令实测 **exit 1**——两条 L1 快照门禁不取 fixture、在栈起来之前就跑完了；
栈预先起好再跑同一条命令才是 exit 0。② 完整性判据「条目数 > 20」在本站点上不可判（Custom Field 总共 10 条，
站点自报计数也是 10），改用 `list_resource('DocType')` 的 **775 vs 变异后恰好 20** 证明 Frappe 确实认 `limit_page_length=0`。

Closure Audit Evidence:

- Auditor / Agent: **未做（本轮）**。执行会话内无可用的独立评审者；执行器不得自审自判（`AGENTS.md` 裁判规则 1）。
  该审计属 `CLOSURE_VERIFY` 步骤，Closure Gates 里对应那条**如实留空**。
- Evidence（执行侧，命令原文 + 退出码；本机实测，非 CI）：
  - `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **0**（门禁 19 项：预期红 7，绿 12，跳过 0；130 passed）
  - `ruff check agenerp tests/unit tests/contracts` → **0**
  - `python3 -m pytest tests/contracts -q` → **0**（151 passed）
  - `bash tools/check-masterplan-links.sh` → **0**（35 条引用，断链 0）· `node tools/check-doc-references.mjs` → **0**（24 篇活文档）
  - live 七条命令与退出码见「实测回填」一节的表，逐条抄了原文
  - 开工基线 sha `826cdf8`

Follow-up:

- 独立关闭审计（`docs/skills/closure-audit-prompt.md`）—— 归 `CLOSURE_VERIFY`，不是缺陷。
- STATE §3 那条补充事实行等人处置（三条出路 loop 不替人选）；处置后由工作项 8 的第二个 plan（CI 真跑 L2）承接。
