# 2026-08-21-2220-1 孤儿列巡检与清除（`schema_drift` + apply 后不留残列）

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 6. 定制包往返删除验证（活站点端到端）—— **第二个 plan：`test_no_orphan_column_left_behind` 这一条**
> Last Reviewed: 2026-08-21
> Source: `docs/backlog/p0-foundation-roadmap.md`「6 现状」行逐字登记的「仍未做」；
>   plan `2026-08-21-1922-3` / `2026-08-21-1922-2` / `2026-08-21-1553-1` 三处 `Deferred But Adjudicated` 共同指名的 successor（重开事件已到）
> Related: `2026-08-21-1553-1-diff-apply-engine-pure-half.md`（A 半）·
>   `2026-08-21-1922-2-export-customizations-live.md`（导出半）·
>   `2026-08-21-1922-3-execute-plan-site-delete.md`（删除半，红因就是从它挪到 `schema_drift` 的）
> Audit: required

## Current Baseline

以下每一条都是 2026-08-21 起草时在**活站点上实测**得来的，不是从旧 plan 抄的。
起草基线 sha **`3fed439`**。⚠️ 起草过程中 HEAD 动过：`29b52f4` 之后人在 22:21:59 提交了 `3fed439`
（「关闭三条 fixture 阻塞的 needs-human；更正记账」），**把 `STATE.md` §3 里最后三条 `[open]` 全部转成了 `resolved`**。
本 plan 起草时先写了旧基线，草案评审逐字指出这处过期，已按 `3fed439` 重写——
**`STATE.md` §3 现在一条 `[open]` 都没有**（`grep -c "^- \[open\]" docs/masterplan/STATE.md` → `0`）。
栈以 `AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300` 冷起，exit 0。

**判据侧（红线内，一个字节都不动）**

- `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind` 是本 plan 唯一的结果面。
  它的四步是：建 Custom Field → `export_customizations` → 从包里删掉该字段 → `apply_pack` →
  `orphans = schema_drift(doctype="Item")`，断言 `PROBE_FIELD not in orphans`。
- 该条目前**仍在** `tools/gates/expected-red.txt` 名单内（7 行里的第 3 行）。
- 同文件另外三条（导出两条 + 删除一条）在 live 环境下已实测转绿（roadmap「5 现状」「6 现状」两行）。
- **红因由本 plan 起草时在 `3fed439` 上亲自复跑坐实**（不引自任何旧 plan）：

```
AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend \
AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin \
python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q --tb=line
→ exit 1 ; 1 failed, 3 passed in 5.61s
→ /Users/lize/Claude/Projects/AgenERP/agenerp/snapshot.py:328: NotImplementedError:
  schema_drift 尚未实现 —— 见 docs/backlog/p0-foundation-roadmap.md 的工作项对照表（工作项 5 · 差集 apply 引擎）
```

  同一次运行还打出一条 WARNING：apply 跳过 10 条不在包管辖范围内的删除（`Address` / `Customer` /
  `Print Settings` 等），**这是 plan `1922-3` 的收窄机制在真实生效的正向证据**，顺带记下。

**实现侧**

- `agenerp/snapshot.py:326-328` `schema_drift(doctype)` 只有签名与 `raise`。返回类型标注是 `Any`，**没有定型**。
  ⚠️ 它的 `NotImplementedError` 文本逐字写着「工作项 5」，与 roadmap 归属（工作项 6）不一致；
  plan `2026-08-21-1553-1` 已登记这处漂移并明写「不改那条消息，改它会让红因文本漂移」。
  本 plan 落地实现时那行 `raise` 整条消失，漂移随之消失——**不是「顺手改了」，是被实现取代**。
- `agenerp/apply.py` 的 `execute_plan` 已能对活站点真删 Custom Field，删除面只有一条写方法
  `SiteClient.delete_custom_field`（`agenerp/site.py`，模块头第 4 条：写方法必须登记进
  `tests/unit/test_site_client.py` 的 `WRITE_METHOD_ALLOWLIST`）。
- `agenerp/site.py` 是**目前唯一**打到活站点的地方（`module-boundaries.md` §11.7）。它走 REST，**够不到物理表**。

**孤儿列是真的存在，不是理论风险（本轮实测，这是本 plan 的开工事实）**

在活站点上直接查物理表：

```
docker compose exec -T db sh -c 'mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" -N -B \
  -e "SELECT TABLE_SCHEMA, COLUMN_NAME FROM information_schema.COLUMNS \
      WHERE TABLE_NAME=\"tabItem\" AND COLUMN_NAME LIKE \"agenerp%\";"'
```

得到 6 列（`agenerp_gate_roundtrip` / `agenerp_gate_probe` / `agenerp_explore_probe` /
`agenerp_explore_probe2` / `agenerp_scope_probe_item` / `agenerp_probe_orphan`，库名 `_5e5899d8398b5f7b`）；
同时经 REST 查 `Custom Field` 全表只有 11 行，`dt="Item"` 的**一条都不剩**。
**结论：Frappe 删 Custom Field 不删物理列，Spike 06 的结论在 v15.119.3 上仍然成立。**
6 列的来源分两类，**不含糊**：2 列是门禁自己的探针（`agenerp_gate_roundtrip` = 本门禁的 `PROBE_FIELD`、
`agenerp_gate_probe` = 快照门禁的探针），另 4 列是历轮人工探查留下的。
前者说明**门禁每跑一轮就在站点上留一列**——这一点此前没有任何文档记过。

**Frappe 自带的口径（复用优先，不重造）**

`frappe/model/meta.py:885` 有 `trim_table(doctype, dry_run=True)`，实测（v15.119.3 容器内读源码）它的定义是：

```
ignore_fields = default_fields + optional_fields + child_table_fields
columns = frappe.db.get_table_columns(doctype)
fields  = frappe.get_meta(doctype, cached=False).get_fieldnames_with_value()
is_internal(f) = f not in ignore_fields and not f.startswith("_")
columns_to_remove = [f for f in set(columns) - set(fields) if is_internal(f)]
dry_run=False 时执行 ALTER TABLE `tab<DocType>` DROP `c`, DROP `c2`, …
```

本轮实测调用可行且快（0.5 秒）：

```
docker compose exec -T backend bench --site frontend execute \
  frappe.model.meta.trim_table --kwargs "{'doctype':'Item','dry_run':True}"
→ ["agenerp_gate_probe","agenerp_explore_probe2","agenerp_gate_roundtrip",
   "agenerp_explore_probe","agenerp_probe_orphan","agenerp_scope_probe_item"]
```

自建 SQL 也能算出同一集合（本轮实测，用 `information_schema.COLUMNS` 减去
`tabDocField.parent='Item'` 与 `` `tabCustom Field`.dt='Item' ``，多出来的恰好是
`name/creation/modified/modified_by/owner/docstatus/idx/_user_tags/_comments/_assign/_liked_by` 这 11 个基础列）
—— 但那等于把 Frappe 的字段口径抄第二遍。**两套口径是本仓明令禁止的**（§11.5「不该有第二份」）。

**缺口**

1. `schema_drift` 没有实现，也**没有传输**——`agenerp` 全树没有任何够得到物理表的路径。
2. 即使 `schema_drift` 诚实实现了，门禁**仍然红**：`apply_pack` 只删 Custom Field 不删列，
   探针列会被如实报成孤儿列。**要让这条转绿，必须同时做「巡检」和「清除」两半。**
   这一点起草时必须说穿，否则执行会以为只写一个只读函数就完事。
3. 站点上已积累 6 条孤儿列：5 条早于本 plan（2 条门禁探针 + 3 条历轮人工探查），
   1 条（`agenerp_probe_orphan`）是本轮起草做可行性实测时留下的，**如实记账**。
   它们会让「清除」这一步的作用域问题**立刻**咬人。

## Goals

- `agenerp.snapshot.schema_drift(doctype)` 在活站点上给出**真实**的孤儿列集合，口径与 Frappe 自己的一致。
- `apply_pack` 删掉一个 Custom Field 之后，**它的物理列不再残留**——且只清除本次 apply 自己造成的残留。
- `tests/gates/test_customization_roundtrip_delete.py` 四条在 live 环境下**全绿**（本条是唯一的结果面）。
- 「物理表这条传输」在架构文档里有明确落点，不是散落在实现里的一次性 shell 调用。

## Non-Goals

- **不划 `tools/gates/expected-red.txt`。** 依据是人在 `STATE.md` §2（2026-08-21T11:20Z）的裁定，
  逐字：**「名单必须反映判定器实际看到的，不是我知道的」**——默认判定环境无 `AGENERP_LIVE`，L2 恒红，
  所以本条即使在 live 下转绿也不构成划名单的理由。
  **这条依据与 §3 无关**：§3 的三条 `[open]` 已由人在 `3fed439`（2026-08-21T14:21Z）全部关闭，
  本 plan 不声称任何 needs-human 项仍开着。
  因此工作项 6 收尾仍置 `planned` 不置 `done`，与工作项 4/5/7 同一情形。
- **不碰 `tests/gates/**`**（红线 1）、不碰 `.github/workflows/**`（红线 2）、不碰 `missions/**`、
  不改 `docs/masterplan/DECISIONS.md`、不写证据仓。
- **不生成运行时 Server Script**（红线 7）。见下方 Phase 1 的 `Decision`：本 plan 采用的是
  「在容器里调用 Frappe **已存在的**函数」，不是「往站点里装一段会被站点自己执行的脚本」——
  两者的区别必须在决策记录里写清楚，不许含糊过去。
- 不做 `creates` / `updates` 的执行（plan `1922-3` 已显式拒绝，successor 是 P2）。
- 不清理站点上**历史遗留**的 5 条孤儿列作为交付物的一部分（它们是观测对象，见 Phase 2 的作用域裁定）。
- 不做事务/回滚语义（`02-WBS.md` 划给 P3.1）。
- 不给 CI 加 L2 job —— 它归 plan `2026-08-21-2220-2` 的 Phase 4（工作项 8），本 plan 不碰 `.github/workflows/**`。

## Task Route

- Type: `architecture change + implementation-only change`（新增一条打到物理表的传输接缝 = 架构面；其余是实现）
- Owner Docs: `docs/architecture/module-boundaries.md` §11.1 / §11.5 / §11.6 / §11.7 ·
  `docs/backlog/p0-foundation-roadmap.md`（工作项 6） · `docs/architecture/system-baseline.md` §14
- Skill Selection Basis: `docs/skills/README.md` 的 Skill Routing Rule 里没有覆盖
  「往既有 Python 模块补一个受判据约束的实现」的条目；本 plan 全程 `Skill: none`，
  唯一例外是 Phase 3 的复跑纪律，那由 `AGENTS.md` 裁判规则直接约束，不经 skill。

## Infrastructure And Config Prereqs

- docker + `docker compose`（本机 v5.0.2）。**起草时栈已被拉起并留着没拆**（`AGENERP_HTTP_PORT=18080`，
  六个服务 healthy）——执行时先 `docker compose ps` 看它还在不在，在就复用，不在就按下面这条冷起。
- 端口 **18080**：8080 被本机另一套常驻 ERPNext 占着，`compose_stack` 有端口预检并会直接 fail。
- L2 门禁完整跑法（缺 `AGENERP_SITE` 跑不绿）。⚠️ `docs/context/project-context.md` 的验证命令表
  **只收录了 `test_snapshot_diff_structured.py` 那一行**，没有 `test_customization_roundtrip_delete.py` 的行；
  两者 env 完全相同所以命令照用，但「已收录」是不准的说法，Phase 3 会补上那一行：

```
AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait
AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend \
AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin \
python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q
```

- **必须先起栈再跑**：那两条 L1 快照门禁不取任何 fixture，栈没预起时会红在 connection refused
  （`STATE.md` §3「新事实三」，两次复跑一致）。
- 无回滚脚本。**回滚策略**：本 plan 的写动作只有一种——`ALTER TABLE … DROP COLUMN`，**不可逆**。
  因此 Phase 2 落地前必须先跑 `docker compose exec -T backend bench --site frontend backup`
  并记下备份路径；这条写进 Phase 2 的执行项，不是口头约定。

## Execution Plan

### Phase 1 — 观测面：物理表传输 + `schema_drift`

Status: completed
Targets: `agenerp/oob.py`（新建）· `agenerp/snapshot.py` ·
  `tests/unit/test_schema_drift.py`（新建）· `docs/architecture/module-boundaries.md`
Skill: `none`

- Item Types: `Proof | Decision | Add | Fix`（6 项里 4 项 `Add`，未过 80% 阈值，**逐项标**）
- Prereqs: 无（Phase 2 依赖本阶段）

- [x] `Proof` **先复跑坐实红因**：按上面的完整命令跑 `test_customization_roundtrip_delete.py`，
      确认 exit 1 且唯一 FAILED 的是 `::test_no_orphan_column_left_behind`，红因逐字是
      `schema_drift` 的 `NotImplementedError`。**退出码与失败原文照抄进 plan**。
      若红因不是这个（例如另外三条掉绿了），**停下来写 `STATE.md` 的 needs-human，不猜根因**。
      - Skill: `none`
- [x] `Decision` **定传输选型**。三个候选，起草时已各自实测过一次：
      **(a) `docker compose exec -T backend bench --site <site> execute frappe.model.meta.trim_table`**
      —— 复用 Frappe 自己的孤儿列定义，`dry_run` 参数同时给出巡检与清除两个模式，输出是 JSON 数组；
      **(b) `docker compose exec -T db mariadb …` 直查 `information_schema`** —— 只读 SQL、不执行任何代码，
      但要把 Frappe 的 `default_fields + optional_fields + child_table_fields` 与 `_` 前缀规则**抄一遍**；
      **(c) 经 REST** —— 起草时已排除：`docker-compose.yml` 未对宿主发布 db 端口，且 Frappe 没有
      任何白名单方法回物理列，这不是取舍问题而是够不到。
      **推荐 (a)**，理由是 §11.5 的「不该有第二份」：(b) 会产生第二套字段口径，Frappe 一次升级就能让两边错开，
      而错开的表现是「孤儿列漏报」——最难发现的那种假绿。
      **残余风险（必须写进决策记录，不许省略）**：(a) 是在容器里执行任意 Python 函数名，
      与红线 7「不得生成运行时 Server Script」**形似而不同** —— 红线 7 禁的是把可执行脚本
      **装进站点**、由站点在处理请求时自己执行（那是持久化的 RCE 面）；(a) 是运维侧的一次性
      带外调用，不留任何站点态，进程退出即结束。**本 plan 必须把「函数名 + 允许的 kwargs」一起钉死**
      ——只钉名字不钉参数挡不住任何东西，见下一项的接口契约。
      **本项同时定下模块的名字与管辖面**（草案评审第二轮指出：叫 `bench.py` 会在 Phase 2 之后变成谎话，
      那时它还要 `exec` 进 `db` 容器跑 SQL，跟 bench 没关系）：模块名定为 **`agenerp/oob.py`**
      （out-of-band，「带外容器命令传输」），管辖面从一开始就写成**三个 exec 目标**——
      `backend` 上 `cat` 站点配置（读）、`backend` 上 `bench execute`（读）、`db` 上 `mariadb`（Phase 2 的写）。
      这样 `### 11.8` 一次写对，不需要 Phase 2 回头改措辞。
      - Skill: `none`
- [x] `Add` 新建 `agenerp/oob.py`：`agenerp` 里**第二条**打到活站点的传输，也是唯一一条打到物理层的。
      接口契约（结构边界，按 guide 规则 6 的例外必须写明）：
      · `class OobError(RuntimeError)` —— 与 `SiteError` 平级，**绝不降级成空结果**（空列表 = 「没有孤儿列」，
        和「命令没跑起来」长得一样，会让门禁假绿）；
      · `ALLOWED_CALLS` 是**「函数名 → 钉死的 kwargs」映射**，不是名字集合。v0 只有一条：
        `"frappe.model.meta.trim_table" → {"dry_run": True}`。**调用方只能给 `doctype`，给不了 `dry_run`。**
        草案评审第二轮指出：原契约 `run_json(function, kwargs: dict)` 的 `kwargs` 是调用方自由传的，
        `{"dry_run": False}` 能穿过名字白名单直接删光该 DocType 的**全部**孤儿列——
        那正是 Phase 2 明文排除的候选 (iii)，被一条「散文里的排除」放行。**钉死 kwargs 才是真的排除。**
      · `read_site_config(site) -> dict` —— `docker compose exec -T <backend> cat sites/<site>/site_config.json`。
        **这是 Phase 2 的 DDL 唯一能拿到库名的地方**（起草时实测该文件回
        `{"db_name": "_5e5899d8398b5f7b", "db_password": "…", "db_type": "mariadb"}`；
        `docker-compose.yml` 的 `db` 服务只设 `MYSQL_ROOT_PASSWORD`、**不设 `MYSQL_DATABASE`**，
        所以 `mariadb` 没有默认库，库名也**推不出来**，只能读）。
        它是一条 `cat`，不执行任何 Python，因此**不进 `ALLOWED_CALLS`**；
      · 站点名、compose 服务名、compose 文件路径全部来自环境变量并带默认值
        （`AGENERP_SITE` / `AGENERP_OOB_BACKEND_SERVICE` 默认 `backend` / `AGENERP_OOB_DB_SERVICE` 默认 `db`）；
      · 零第三方依赖（只用 `subprocess` + `json`），与 `agenerp/site.py` 同一条约束。
      - Skill: `none`
- [x] `Add` 实现 `agenerp.snapshot.schema_drift(doctype)`：**返回类型定型为 `tuple[str, ...]` 并排序**
      （现签名是 `Any`，不定型的话调用方只能靠猜；门禁用的是 `in`，元组满足）。
      语义逐字写进 docstring：「物理表上存在、但按 Frappe 自己的口径不属于任何字段的列」。
      站点不可达时抛 `OobError`，**不返回空元组**。
      - Skill: `none`
- [x] `Add` `tests/unit/test_schema_drift.py`：注入假 `bench` 执行器（与 `SiteSnapshotSource` 的
      `client` 可注入是同一手法），覆盖 ——排序与去重、非列表载荷抛错、执行失败抛 `OobError` 而非返回空、白名单外的函数名被拒、
      以及**被钉死的 kwargs（`dry_run=False`）传不进去**。**不连真站点**（`tests/unit` 必须零依赖可跑）。
      - Skill: `none`
- [x] `Fix | Add` 往 `docs/architecture/module-boundaries.md` 追加 **`### 11.8`「带外容器命令传输在本仓的落点」**（用 `### 11.x` 与既有小节同形，文中沿用 §11.8 指代）：
      为什么需要第二条传输、为什么不是 §11.7 的扩展（REST 够不到物理表）、白名单机制、
      以及与红线 7 的界线。**四处「唯一」的表述必须同步改准**（起草时逐条查实的行号，执行时以实际为准）：
      · `agenerp/site.py:1` 模块 docstring「`agenerp` 里**唯一**打到真站点的地方」；
      · `module-boundaries.md:510`「`agenerp/site.py` 是 `agenerp` 里**唯一**打到真站点的模块」；
      · `module-boundaries.md:515`「连活站点的**唯一**传输落点」；
      · `module-boundaries.md:338`「`SiteClient.delete_custom_field` 是站点侧删除的**唯一**出口」
        —— 这一条要到 Phase 2 的 `drop_columns` 落地后才漂移，那次由 Phase 2 改。
      留着不改就是 owner-doc 漂移（Minimum Rule 14 的非降级项，见 Closure Gates）。
      - Skill: `none`

Exit Criteria:

- [x] `schema_drift(doctype="Item")` 在活站点上返回**非空**集合，且与下面这条 SQL 的结果满足
      **写死的等式**（草案评审第二轮指出：原表述含糊，`Current Baseline` 里有两条 SQL，
      前缀过滤那条证明不了口径、后一条是超集，「一致」两个字都对不上）：

```
docker compose exec -T db sh -c 'mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" -N -B <DB_NAME> -e "
SELECT c.COLUMN_NAME FROM information_schema.COLUMNS c
WHERE c.TABLE_SCHEMA=DATABASE() AND c.TABLE_NAME=\"tabItem\"
AND c.COLUMN_NAME NOT IN (SELECT fieldname FROM tabDocField WHERE parent=\"Item\")
AND c.COLUMN_NAME NOT IN (SELECT fieldname FROM \`tabCustom Field\` WHERE dt=\"Item\");"'
```

      **等式**：`set(schema_drift("Item"))` == `SQL 结果集` − `{name, creation, modified, modified_by,
      owner, docstatus, idx, _user_tags, _comments, _assign, _liked_by}`（这 11 个是起草时实测到的基础列）。
      两侧的**原始输出都要逐字贴进 plan**，不许只写「一致」。
      ⚠️ **不拿 `trim_table(dry_run=True)` 做交叉验证**：Decision (a) 下 `schema_drift` 就是它的包装，
      那是拿函数和自己的后端对账，什么也证明不了。SQL 侧只做**这一次性**交叉验证，
      **不留成第二套常驻口径**（§11.5 禁止）。
      ⚠️ 若两侧对不上，**优先怀疑那 11 个基础列的清单**（它是本仓抄下来的常量，不是 Frappe 的真相源），
      记为「不可复现/口径待查」并停下，**不许调整任一侧去凑等式**。
- [x] `python3 -m pytest tests/unit -q` 与 `python3 -m pytest tests/contracts -q` 均 exit 0
- [x] `ruff check agenerp tests/unit tests/contracts` exit 0
- [x] `test_no_orphan_column_left_behind` 的红因**从 `NotImplementedError` 挪到断言失败**
      （逐字应是「留下了孤儿列：…」）——这是本阶段完成的**正向证据**，红仍是红，如实记录
- [x] `module-boundaries.md` §11.8 落地，§11.7 的「唯一」表述已改准
- [x] `docs/logs/` 更新

### Phase 2 — 清除面：apply 之后不留残列

Status: completed
Targets: `agenerp/oob.py` · `agenerp/apply.py` · `agenerp/pack.py` ·
  `tests/unit/test_apply_execute.py` · `docs/architecture/module-boundaries.md`
Skill: `none`

- Item Types: `Decision | Add | Proof`
- Prereqs: Phase 1 完成（没有巡检就无法判定清除是否奏效）

- [x] `Proof` **先备份再动 DDL**：`docker compose exec -T backend bench --site frontend backup`，
      把备份文件路径与退出码抄进 plan。`DROP COLUMN` 不可逆，这是本 plan 唯一的不可逆动作。
      - Skill: `none`
- [x] `Decision` **定清除的作用域**。两个候选：
      **(a) 直接调 `trim_table(doctype, dry_run=False)`** —— Frappe 自己的语义，一次把该 DocType 上
      **所有**孤儿列删光。起草时实测：`Item` 上现有 6 条孤儿列，其中 **5 条不是本次 apply 造成的**
      （历史门禁残留）。选 (a) 等于让一次 apply 顺手删掉五列历史数据；
      **(b) 只删「本次 apply 真的删掉了 Custom Field」的那些列** —— 取
      `execute_plan` 收窄后的 `deletes` 与 `schema_drift` 的交集，逐列 `ALTER TABLE … DROP COLUMN`。
      **推荐 (b)**，理由是它与 plan `1922-3` 已确立的「作用域收窄」是同一条原则——那个 plan 实测过
      不收窄会连删 11 条（10 条是应用自带字段），而门禁**照样绿**（判据挡不住这个错误）。
      这里是同一个陷阱换了一层：门禁只看探针列没了，删掉另外 5 列它一个字都不会说。
      **残余风险**：(b) 需要自己拼一条 DDL，因此**列名必须先经 `schema_drift` 的返回集合验证**
      （只允许删「已被 Frappe 判定为孤儿」且「本次 apply 删过同名字段」的列，两个条件同时成立），
      DocType 名与列名再各过一次 `^[A-Za-z0-9_ ]+$` 白名单——不接受任何未经验证的标识符进 SQL。
      **备选未选的记录**：(a) 更省代码且完全复用框架，但它把「清理」和「apply」两件事混成一件，
      违反本仓反复强调的「apply 只做包表达过的意图」。
      - Skill: `none`
- [x] `Decision` **定 DDL 的执行机制**（草案评审逐字指出的硬矛盾：Phase 1 把 `ALLOWED_CALLS`
      钉死成只有 `frappe.model.meta.trim_table`（且 `dry_run` 恒为 `True`），而 `ALTER TABLE … DROP COLUMN` 不是任何一个
      Frappe 白名单函数，「走同一条白名单校验」这句话在原草案里是空的）。三个候选：
      **(i) `bench execute frappe.db.sql_ddl --kwargs "{'query': …}"`** —— 调用方给整条 SQL 字符串。
      **起草时即排除**：这正是 Phase 1 拒绝过的「通用 RCE 接口」，把它加进白名单等于把白名单作废；
      **(ii) 第三条传输：`docker compose exec -T db mariadb -e "ALTER TABLE …"`** ——
      DDL 走 db 容器，不经任何 Python 执行面。它**不与 Phase 1 的 (a) 冲突**：Phase 1 排除 (b) 的理由是
      「不要第二套**字段口径**」，而这里不做任何字段判断——判断已由 `schema_drift` 做完，
      db 侧只执行一条列名已被验证过的 DDL。**代价**：`agenerp/oob.py` 里出现两个 exec 目标
      （`backend` 读、`db` 写），模块名与 §11.8 的措辞要相应写准；
      **(iii) 扩白名单到 `frappe.model.meta.trim_table(dry_run=False)`** —— 一次删光该 DocType 全部孤儿列，
      与本阶段作用域裁定 (b) 直接冲突，**排除**。
      **推荐 (ii)**。**残余风险**：(ii) 自己拼 SQL，因此列名必须**同时**满足两个条件才允许进 DDL ——
      ① 在 `schema_drift` 的返回集合里（Frappe 判定它是孤儿），② 在本次 apply 真删掉的 fieldname 集合里；
      再加标识符白名单（见下一项）。任一条件不成立就跳过并 WARNING。
      - Skill: `none`
- [x] `Add` 在 `agenerp/oob.py` 里加**第一个写动作** `drop_columns(doctype, columns)`（模块的第三个公开方法——前两个是 `run_json` / `read_site_config`——也是唯一一个写的），
      按上一项定下的机制实现（推荐 (ii) 时它走 db 容器，与只读的 `run_json` 是两个 exec 目标，
      **不共用 `ALLOWED_CALLS`**——那张表管的是 Python 函数调用，管不到 DDL）。
      库名来自 Phase 1 的 `read_site_config(site)["db_name"]`，**不写死、不猜**。
      约束：`columns` 为空时**直接返回不发命令**（不发空 DDL）；
      DocType 名与列名各过一次 `^[A-Za-z0-9_ ]+$`（**这是 v0 的刻意收窄**：它会拒掉含 `-` / `&` 的
      合法 DocType 名，本 plan 只需覆盖 `Item`，拒掉即抛错而不是静默放行）；失败抛 `OobError`。
      与 `agenerp/site.py` 模块头第 4 条同一条纪律——**写方法必须登记**：在 `tests/unit/` 里加一条与
      `WRITE_METHOD_ALLOWLIST` 等价的名单断言，让「又多了一个写方法」这件事必须付一次 diff。
      同时改准 `module-boundaries.md:338`「站点侧删除的**唯一**出口」那句（Phase 1 已点名的第四处漂移）。
      - Skill: `none`
- [x] `Add` 在 `agenerp/apply.py` 的 `execute_plan` 里，删完 Custom Field 之后按 (b) 的口径清列。
      **被跳过的列一条都不静默**：沿用该模块已有的 `LOGGER.warning` 纪律，逐条列出
      `(doctype, column, 跳过原因)`。
      - Skill: `none`
- [x] `Add` `tests/unit/test_apply_execute.py` 补例：注入假 bench，覆盖 ——
      只删交集内的列、交集为空时不发任何 DDL、`schema_drift` 抛错时 `execute_plan` **也抛**
      （不吞掉、不当成「没有孤儿列」）、白名单外的列名被拒。
      - Skill: `none`

Exit Criteria:

- [x] `test_no_orphan_column_left_behind` 在 live 环境下**转绿**
- [x] **作用域实测**：apply 前后各跑一次 `schema_drift(doctype="Item")`，
      **方向是「减少」而不是「新增」**——`agenerp_gate_roundtrip` 今天就已经是孤儿列，
      门禁跑完那一轮它应当**从集合里消失**，且**消失的恰好只有它一列**；
      起草时记录的另外 5 列（`agenerp_gate_probe` / `agenerp_explore_probe` / `agenerp_explore_probe2` /
      `agenerp_scope_probe_item` / 以及本轮起草留下的 `agenerp_probe_orphan`）**一条不少地还在**
      （这是「没有顺手多删」的正向证据，必须逐条抄进 plan）
- [x] `python3 -m pytest tests/unit -q` / `tests/contracts -q` / `ruff check` 三条均 exit 0
- [x] `module-boundaries.md` §11.6 补记清除面的落点与作用域裁定；
      **§11.8 的「三个 exec 目标」措辞与实际落地一致**（Phase 1 已按 Phase 2 的选择预先写对，
      此处只做核对；若不一致就是 Phase 1 的 `Decision` 没落实，改文档而不是改说法）
- [x] `module-boundaries.md:338`「站点侧删除的**唯一**出口」已改准（Phase 1 点名的第四处漂移）
- [x] `bench --site frontend backup` 的备份路径与退出码已记进 plan（DDL 不可逆，这是唯一的退路）
- [x] `docs/logs/` 更新

### Phase 3 — 变异验证与收尾

Status: completed
Targets: `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md`（**只追加**）·
  `docs/context/project-context.md` · `docs/logs/`
Skill: `none`

- Item Types: `Proof | Add | Follow-up`（8 项里 4 项 `Proof`，未过 80% 阈值，**逐项标**）
- Prereqs: Phase 1、Phase 2 完成

- [x] `Proof` **变异验证一：这条门禁测不出「巡检坏掉」，如实记录。**
      把 `schema_drift` 临时改成返回空元组，跑
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q`
      → 预期**绿**。
      ⚠️ **绿的原因必须写准**：Phase 2 的清除集是 `本次删掉的 fieldname ∩ schema_drift(...)`，
      空巡检 → 空交集 → **一列都没删**；门禁绿只是因为断言拿到的 `orphans` 也是空的。
      **这是一次假绿，不是「列真的被删了」**（原草案在这里写错了因果，草案评审逐字指出）。
      因此本项的结论是「门禁对巡检坏掉零覆盖」，**补偿证据是 Phase 1 那次 `information_schema` SQL 交叉验证**，
      不是变异验证二。
      - Skill: `none`
- [x] `Proof` **变异验证二：清除有牙齿。** 把 Phase 2 的清列改成 no-op，跑上面同一条命令 →
      该条必须**逐字转红**在「留下了孤儿列：…」。这是本 plan 真正的牙齿所在。改回后复跑转绿，两次退出码都记。
      - Skill: `none`
- [x] `Proof` 全量复跑 `test_customization_roundtrip_delete.py` 四条（同上命令，去掉 `--tb=line`），
      期望 exit 0 / `4 passed`。退出码与原文照抄。
      - Skill: `none`
- [x] `Proof` 复跑 `python3 tools/gates/check_expected_red.py`（默认环境，不带 `AGENERP_LIVE`），
      确认没有名单外的门禁变红。**名单一行不动**（见 Non-Goals）。
      - Skill: `none`
- [x] `Add` 更新 `docs/backlog/p0-foundation-roadmap.md`：改写「6 现状」行为实测结论，
      工作项 6 **保持 `planned`**；同时在「5 现状」行补一句——`execute_plan` 的交付面被本 plan 扩过
      （多了清列一步），免得工作项 5 的记录与代码脱节。
      - Skill: `none`
- [x] `Add` 往 `docs/masterplan/STATE.md` **§2（会话日志，只追加）**写一条证据行。
      ⚠️ **不写 §3**：§3 是 needs-human 队列，本 plan 没有任何要人拍板的事项
      （§3 此刻一条 `[open]` 都没有），把证据行塞进 §3 是给队列注水。
      同时按本 mission 的既有先例（`1922-1` 的 `## Closure` 段、`1022-2`、`2341-2`；
      ⚠️ `1922-3` **没有**做这个披露，不要拿它当先例），**照实引出授权链矛盾**：
      `01-EXECUTION-MODEL.md` §1 的表写角色 B「不得手写 STATE」，而执行器人格
      `tools/mission-driver/agents/build.claude.md` 指示「拿不准就写进 `STATE.md` 的 needs-human 队列」，
      `AGENTS.md` 红线 5 允许**追加**证据行——按更高优先级那条执行，只追加、不改写任何已有行，不擅自消解。
      **格式必须照 §2 表头**（`STATE.md:25`）：`时间 · WBS行ID · 命令→退出码 · sha · 下一项`；
      WBS 行ID 用 **P0.2**（`schema_drift` 归在快照/契约面，与 `1922-1` 同一行），
      这也正好满足裁判规则 2 的「命令原文 + 退出码 + commit sha」。
      - Skill: `none`
- [x] `Add` 往 `docs/context/project-context.md` 的验证命令表补一行：
      `test_customization_roundtrip_delete.py` 的完整 L2 跑法（含 `AGENERP_SITE=frontend` 与「必须先起栈」），
      以及本 plan 新引入的两条带外命令（`bench execute` 读、`db` 侧 DDL 写）。
      - Skill: `none`
- [x] `Follow-up` 往 `docs/backlog/` 新开一条：**门禁自己在污染站点**——每轮跑完留一条孤儿列。
      触发条件（按 Anti-Slacking Rule 必须写明）：**当 CI 真的开始跑 L2 时**（plan
      `2026-08-21-2220-2` 的 CI 阶段落地），残留会随每次 CI 累积，届时必须处置。
      现在不处置的理由：teardown 在 `tests/gates/conftest.py`（红线 1）。
      - Skill: `none`

Exit Criteria:

- [x] 两条变异验证的命令原文、退出码、失败原文均已落进 plan，且变异验证一的**因果结论写的是「假绿」**
- [x] roadmap「6 现状」行更新为实测结论；工作项 6 **保持 `planned`**（不置 `done`，理由见 Non-Goals）；
      「5 现状」行补记 `execute_plan` 交付面的扩张
- [x] `STATE.md` **§2** 追加一条证据行（只追加，不改写任何已有行），**§3 不动**，授权链矛盾已照实引出
- [x] `docs/context/project-context.md` 验证命令表补上 `test_customization_roundtrip_delete.py` 一行
      与本 plan 新引入的 bench/db 带外命令
- [x] 全量复跑 `test_customization_roundtrip_delete.py` → exit 0 / `4 passed`，原文已抄
- [x] 默认环境 `python3 tools/gates/check_expected_red.py` → exit 0，无名单外门禁变红
- [x] `docs/backlog/` 下已新开「门禁污染站点」那条 follow-up，且写明了触发条件
- [x] `docs/logs/2026/08-21.md`（或执行当日）更新

## Draft Review Record

- **Independent draft review iteration 1: needs revision**（独立子代理，fresh session）。
  7 条 blocking：① 引用了 `STATE.md` §3 一条**已不存在**的 `[open]`（起草期间 HEAD 从 `29b52f4` 动到
  `3fed439`，人把最后三条 `[open]` 全转成 `resolved`）；② Phase 2 的 `drop_columns` 没有传输，
  且与 Phase 1 的白名单自相矛盾；③ Phase 3 变异验证一的因果结论写错了；
  ④ Phase 3 有三条 exit criteria 没有对应的执行项；⑤ 证据行写去了 §3（needs-human 队列）而不是 §2，
  且漏了同期 plan 都做过的授权链披露；⑥ `Current Baseline` 的承重红因引自旧 plan 而非现场复跑
  （违反 Minimum Rule 1）；⑦ Phase 1 拿 `schema_drift` 和它自己的后端 `trim_table` 对账，什么也证明不了。
- **Revision after iteration 1**：基线 sha 改成 `3fed439` 并写明 HEAD 动过；红因改成起草时亲自复跑的原文
  （exit 1 / `1 failed, 3 passed in 5.61s` / `agenerp/snapshot.py:328`）；Phase 2 新增 DDL 执行机制的
  `Decision`（三候选，选 db 容器直发 DDL）；变异验证一改写成「这是假绿，门禁对巡检坏掉零覆盖」；
  Phase 3 补齐三条执行项；证据行改投 §2 并补披露；交叉验证改用 `information_schema` SQL。
- **Independent draft review iteration 2: needs revision**（另一个独立子代理）。确认 1/3/5/6 已修，
  2/4/7 未修透，另发现新问题。5 条 blocking：① `## Draft Review Record` 还空着而正文已三处引用评审结论；
  ② `run_json(function, kwargs)` 的 `kwargs` 仍由调用方自由传，`{"dry_run": False}` 能穿过名字白名单
  把该 DocType 的孤儿列删光——正是 Phase 2 明文排除的候选 (iii)，「散文里的排除」没有强制力；
  ③ 选定的 DDL 传输**拿不到库名**（`db` 服务不设 `MYSQL_DATABASE`，库名 `_5e5899d8398b5f7b`
  从 `AGENERP_SITE=frontend` 推不出来），而所有显而易见的解法都被 Phase 1 的白名单堵死了；
  ④ 替换后的交叉验证仍不可执行（`Current Baseline` 里有两条 SQL，一条是前缀过滤、一条是超集，
  「一致」两个字对不上任何一条）；⑤ 模块叫 `bench.py`，但 Phase 2 之后它还要 `exec` 进 `db` 跑 SQL，
  Phase 1 写下的 `### 11.8` 会被 Phase 2 当场证伪，且没有任何 exit criteria 兜住这次改写。
  另有 8 条非阻塞 nit（item type 计数、探针列归属自相矛盾、先例引用不准、§2 行格式、
  `Fix` 标签缺失、三条执行项没有对应 exit criteria、`### 11.x` 标题层级、措辞自相矛盾）。
- **Revision after iteration 2**：`ALLOWED_FUNCTIONS`（名字集合）改成 `ALLOWED_CALLS`
  （**名字 → 钉死的 kwargs** 映射，v0 把 `dry_run` 钉成 `True`，调用方给不了）；
  新增 `read_site_config(site)` 并写明它是库名的唯一来源（起草时实测
  `docker compose exec -T backend cat sites/frontend/site_config.json` 回 `{"db_name": "_5e5899d8398b5f7b", …}`，
  它是 `cat` 不执行 Python，故不进白名单）；模块改名 `agenerp/oob.py` 并在 Phase 1 就把**三个 exec 目标**
  写进 `### 11.8`，Phase 2 只做核对；交叉验证改成一条**写死的 SQL + 写死的等式**（SQL 结果集减去 11 个基础列），
  并规定对不上时停下、不许调整任一侧去凑；8 条 nit 全部就地修掉。

- **Independent draft review iteration 3: accept**（第三个独立子代理）。逐条复核后确认 5 条 blocking
  **全部由结构性改动关闭，不是措辞打补丁**，并在活栈上亲自复验了两条承重事实：
  `docker compose exec -T backend cat sites/frontend/site_config.json` → exit 0 且回 `db_name`；
  Phase 1 exit criterion 的那条 SQL 原样跑 → exit 0、17 行 = 11 个基础列 + 6 条孤儿列，
  **等式今天就成立**，且 `trim_table(dry_run=True)` 回的正是那 6 条。
  该轮还带回一条 plan 里没写、但对设计成立与否关键的事实（记在此处备查）：
  Frappe 把列清单缓存在 Redis 的 `table_columns` 里，带外 `ALTER TABLE` 本会让它变陈旧、
  从而让门禁继续红——但 `trim_table` 的**第一行**就是 `frappe.cache.hdel("table_columns", …)`，
  所以每次 `schema_drift` 调用都会先把缓存打掉，Decision (a) 与 Decision (ii) 因此能安全组合。
  余下 7 条均为非阻塞 nit，其中「第四个公开方法」的计数错、备份 `Proof` 缺 exit criterion、
  STATE §2 行缺 WBS 行ID、roadmap「5 现状」里一句已过期的 §3 引用，四条已就地修掉。
- **共识达成**：三轮独立评审，第三轮 `acceptable as-is`，`Plan Status` 由 `draft` 改为 `active`。

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（§11.6 / 四处「唯一」表述（`site.py:1` · §11.7 的 510、515 · 338）/
      新增 §11.8 / roadmap 的「5 现状」「6 现状」两行 / project-context / STATE §2）
- [x] 确认的 owner-doc 漂移（四处「唯一」）已就地改准，**没有被降级成 follow-up**（Minimum Rule 14）
- [x] verification has run：`tests/unit` · `tests/contracts` · `ruff check` ·
      live 的 `test_customization_roundtrip_delete.py` · 默认环境的 `check_expected_red.py`
- [x] scoped verification is not conflated with full verification —— **live 只在本机做过，CI 未验证**，
      这句必须逐字出现在 Closure 里
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files

## Deferred But Adjudicated

### 站点上先于本次 apply 存在的 5 条孤儿列不由本 plan 清理

- Classification: `watch-only residual`
- Why Not Blocking Closure: 它们是本 plan 的**观测对象**（作用域实测靠「它们还在」来证明没有多删）。
  清掉它们等于毁掉这条正向证据。**口径**：这 5 条指 apply 之后仍应留在站点上的那些，
  其中 `agenerp_probe_orphan` 是本轮起草实测留下的、其余 4 条早于本 plan——两者都不该被这次 apply 碰到。
- Successor Required: `no`（人可随时 `bench --site frontend trim-tables` 自行清理）

### 门禁 teardown 不删物理列，每轮跑完留一条孤儿列

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: teardown 在 `tests/gates/conftest.py`（红线 1），loop 不得改。
- Successor Required: `yes` —— **人动作**（带 `Gates-Change-Approved-By:` trailer），
  重开事件：**CI 开始真跑 L2 时**（plan `2026-08-21-2220-2` 的 CI 阶段落地）。

### `schema_drift` 只覆盖 `Custom Field` 造成的列，不覆盖 Property Setter / 改字段类型造成的表结构漂移

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 包体此刻只认 `custom_fields`（plan `1922-2` 已登记）；
  没有包就没有「不在包里」这个判断的对象。
- Successor Required: `yes`（P2 定制包 GitOps，与 `1922-2` 那条同一个 successor）

### `expected-red.txt` 在默认环境与 live 环境下给出相反判定

- Classification: `watch-only residual`
- Why Not Blocking Closure: 人已在 `STATE.md` §2（2026-08-21T11:20Z）裁定过口径——
  「名单必须反映判定器实际看到的」，默认环境即判定环境，L2 在那里恒红，名单该留就留。
  **本 plan 不请求划名单，也不声称这里有未决的 needs-human 项**（§3 已无 `[open]`）。
  真正会被它咬到的是「CI 真跑 L2」那一步，而那一步不属于本 plan。
- Successor Required: `yes` —— plan `2026-08-21-2220-2` 的 CI 阶段（它必须为 live 判定环境定出名单口径）

## Closure

Status Note: **三个 Phase 全部执行完毕，判据面四条在 live 环境全绿。** 交付基线 sha `e1c9104`。

- **结果面**：`AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q`
  → **exit 0**，`4 passed in 10.29s`（含此前唯一仍红的 `::test_no_orphan_column_left_behind`）。
- **其余验证**：`python3 -m pytest tests/unit -q` → exit 0 `189 passed`；
  `python3 -m pytest tests/contracts -q` → exit 0 `151 passed`；
  `ruff check agenerp tests/unit tests/contracts` → exit 0；
  默认环境 `python3 tools/gates/check_expected_red.py` → exit 0（「门禁 19 项：预期红 7，绿 12，跳过 0」）。
- **红线核对**：`git diff --stat -- tests/gates .github/workflows docs/masterplan`（相对开工基线）→ 无输出；
  `git diff --numstat tools/gates/expected-red.txt` → 无输出（名单一行未动）；
  `STATE.md` 的改动是 **9 insertions, 0 deletions**（只追加 §2 证据行，§3 未动）；
  `DECISIONS.md` / 证据仓 / `missions/**` 均未触及；未生成任何运行时 Server Script。
- **scoped verification is not conflated with full verification —— live 只在本机做过，CI 未验证。**
- **本 plan 不划 `expected-red.txt`，工作项 6 保持 `planned` 不置 `done`**（理由见 Non-Goals，
  依据是人在 `STATE.md` §2 2026-08-21T11:20Z 的裁定）。这不是把没做完的活报成完成，
  也不是把做完的活报成没做——`done` 的字面定义（「已从预期红名单划掉」）在此处不可满足。

Closure Audit Evidence:

- Auditor / Agent: **待填** —— 独立关闭审计尚未进行。本轮是 `EXECUTE` 步骤，
  独立子代理的关闭审计归 `CLOSURE_VERIFY` 步骤，不由执行步骤自审
  （自审等于让被裁判者当裁判，与本仓反复强调的那条原则冲突）。
- Evidence: 待填。可复跑的证据入口：本文件 Phase 1/2/3 各项的命令原文与退出码 ·
  `docs/logs/2026/08-21.md` 的三条 `EXECUTE` 记录 · `docs/masterplan/STATE.md` §2 的证据行 · commit `e1c9104`。
- **需要审计特别复核的三处**（执行侧自己点名，不藏）：
  ① 变异验证一的因果结论是否写准了「假绿」（门禁对巡检坏掉零覆盖），而不是被读成「清除有效」；
  ② `agenerp/oob.py` 与红线 7 的界线是否真的靠机制立住（`ALLOWED_CALLS` 钉到参数一级、
     无通用 SQL / 通用函数入口），而不是靠散文里的一句排除；
  ③ 作用域收窄是否真的只删了交集（跑前 6 条 → 跑后 5 条，消失的恰好只有 `agenerp_gate_roundtrip`）。

Follow-up:

- `docs/backlog/gate-fixtures-pollute-the-live-site.md` —— **门禁自己在污染站点**。
  本 plan 已止血一半（走 `apply_pack` 的探针现在会被清掉），**没覆盖的是另一半**：
  `test_snapshot_diff_structured.py` 的 `agenerp_gate_probe` 由 `live_site` fixture 直接建删、
  **不经 `apply_pack`**，因此它的列仍每轮累积。修法在 `tests/gates/conftest.py`（红线 1），
  触发条件是 **CI 真的开始跑 L2 时**（plan `2026-08-21-2220-2` 的 CI 阶段）。
  **这不是确认的缺陷被塞进 follow-up**：它是本 plan `Deferred But Adjudicated` 第二条的落盘，
  且 loop 无权处置。
- 执行过程中**实测红过两次，两条都已就地修掉并各配一条判据**，不留成 follow-up：
  ① `bench execute --kwargs` 是 Python 字面量不是 JSON（`NameError: name 'true' is not defined`）；
  ② MariaDB 的反引号落在 `sh -c` 的双引号里被当成命令替换（`sh: 1: tabItem: not found`）。
