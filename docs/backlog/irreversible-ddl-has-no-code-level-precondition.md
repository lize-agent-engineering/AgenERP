# 不可逆 DDL 没有代码级前置 —— `apply_pack` 自动跑到 `DROP COLUMN` 时，零备份零取证

> Status: `deferred`（**登记，不处置**；处置需要人）
> Created: 2026-08-22
> 由 plan `docs/plans/p0-foundation/2026-08-22-1041-1-destructive-write-owner-doc-alignment.md` 的 Phase 3 产出
> 处置者：**人**（三条可选处置各自撞在不同的红线/裁定上，见「为什么 loop 不能自己做」）

## 事实（2026-08-22 在 `main` @ `4ac3517` 上实读 + 实跑，不是推理）

**调用链，一路自动，中间没有任何人工确认点**：

`agenerp/pack.py:153` `apply_pack`
→ `agenerp/apply.py:251` `execute_plan`
→ `agenerp/apply.py:254` `drop_orphan_columns`
→ `agenerp/oob.py:255` `drop_columns`

链条末端的 `drop_columns` 是**本仓唯一直发 DDL 的写动作**：以 `root` 身份向 `db` 容器发
``ALTER TABLE `tab<DocType>` DROP COLUMN …``，**绕过 Frappe 的一切执行面**。

**四条可判事实**：

| # | 事实 | 取证 |
|---|---|---|
| 1 | `ALTER TABLE … DROP COLUMN` **不可逆** | MariaDB 语义；`docs/context/project-context.md:60` 逐字记着 |
| 2 | 代码侧**零备份** | `grep -rn "backup" agenerp/*.py` → **零命中**（exit 1，无输出）。`agenerp/tools_readonly.py:63` 的「取证」是别的词义，不是备份 |
| 3 | 代码侧**零取证**：删之前不落盘被删列的内容 | `agenerp/oob.py` 的 `drop_columns` 只发 DDL，不 `SELECT`、不导出 |
| 4 | 被删的物理列**可能带着真实业务数据** | 一个 Custom Field 被建出来、被填过值、再从定制包里删掉 —— `drop_orphan_columns` 的收窄口径（「本次删掉的 fieldname ∩ `schema_drift(doctype)`」）**只管列是不是本次造成的残留，不管列里有没有数据** |

**这不是假想的风险 —— 本仓已经被人用手工动作补过一次**：plan `2026-08-22-0228-2` 冷起前
先跑 `docker compose exec -T backend bench --site frontend backup`，
再 `docker compose cp … ./.backups-2026-08-22`，产物 **817012 字节 `.sql.gz`**
（`docs/masterplan/STATE.md:83` 与 `docs/logs/2026/08-22.md` 逐字记着）；`.gitignore:12` 已有 `.backups-*/`。
**那次备份是人手敲的，不是代码跑的。** 换成 `apply_pack` 自动跑，这一步不存在。

## 现状：文档层已加严，代码层一行没动

plan `2026-08-22-1041-1` 的 Phase 2 把 `docs/context/ai-autonomy-policy.md:87`
「对活站点的破坏性写」那一行加严了：落点列表点名了 `agenerp/oob.py` · `drop_columns`，
并补了一条 Required Evidence —— 动这条不可逆路径的 plan 必须逐字写明
「站点侧回滚仍然只能手工做」（含手工前置命令原文），或写明它交付了什么代码级前置/取证并给出实跑证据。

**那是文档层，不是代码层。** 该文件自己就写着残余风险：
**文档级约束对拿着 shell 的执行器没有强制力**。本条登记的正是代码层那个缺口。

## 为什么 loop 不能自己做（两条硬拦，缺一条都不足以拦住）

**① 判据先行拦住了，而豁免不适用于这条路径。**
roadmap「本 mission 的规则」逐字要求「任何工作项开工前，先确认它有绑定的门禁测试；
没有就先补一条红的（补测试要人批，走 `Gates-Change-Approved-By:`）」。

`docs/backlog/p0-foundation-roadmap.md` 工作项 9 那一格**逐字**写着：它
「**没有属于自己的门禁测试**」，与**工作项 4**、**工作项 7**「同一情形」，
并且「**不引工作项 8 / WBS P0.7 作先例**——那两处确实绑着 `test_zero_dep_boot.py` 的具体断言，
不是同一情形」。

**逐字的是这段排除句**；「豁免只适用于 4/7/9」是**由它得出的推论**，不是原文 —— 这里分清楚。
推论的方向由那段排除句直接支持：**绑着具体断言的工作项不适用豁免**。
而本条这条路径归**工作项 5/6**，绑的是 `tests/gates/test_customization_roundtrip_delete.py`
的具体断言（`::test_removing_from_pack_actually_deletes_on_site` /
`::test_no_orphan_column_left_behind`）——**与 4/7/9 不是同一情形，豁免不适用**。

因此这条路径开工前必须先有一条绑定的门禁。补一条新门禁**在 `AGENTS.md` 红线 1 内**
（`tests/gates/**` 是裁判，loop 一个字节都不许改），**只有人能做**，且要走 `Gates-Change-Approved-By:` trailer。

**② 相邻裁定已经把这块地占了，且它的重开事件未满足。**
plan `docs/plans/p0-foundation/2026-08-21-1922-3-execute-plan-site-delete.md` 的
`## Deferred But Adjudicated` 第一条逐字写着：

> **代价要说清**：`creates` 不落地 = 站点侧的回滚只能手工做，
> 「用包把删掉的字段建回来」这条能力在本 plan 之后仍然缺（见 Infrastructure 的回滚策略）。

`Successor Required: yes`（P2 定制包 GitOps，或更早出现真实调用方时），
重开事件是「**出现需要用包在站点上建字段的调用方时**」—— **未发生**。

也就是说「**站点侧回滚只能手工做**」是一条**已裁定状态**，不是遗漏。
在 P0 里自行改掉它，是重开别人的裁定。

## 触发条件（按 Anti-Slacking Rule 必须写明，不是「以后有空再说」）

三者**任一**发生即触发，届时必须处置、不得再挂着：

1. **人从下面「可选处置」里选定一档时** —— 这是本条最直接的触发路径，本条就是为它写的。
2. **人出具 `Gates-Change-Approved-By:` trailer 为这条路径补一条门禁时** —— 判据先行的拦阻消失，
   ① 那条硬拦不再成立，可以起 plan。
3. **`1922-3` Deferred 第一条的重开事件发生时**（出现需要用包在站点上**建**字段的调用方）——
   届时「站点侧回滚只能手工做」这条已裁定状态本身被重开，② 那条硬拦不再成立。

**在此之前不处置的理由（照实说，不是「没空」）**：两条硬拦都在，任何一条都足以让 loop 自行动手
变成越权。而**风险此刻的实际暴露面有限**：`apply_pack` 目前唯一的调用方是门禁与本机实测，
被删的列都是探针列；真实业务数据落进删除集，要等到 P2 定制包 GitOps 有真实调用方。
**但这不等于风险不存在** —— 它只是还没被踩到，而代码侧确实一点防护都没有。

## 可选处置（loop 不替人选，每项都标出代价）

- **(a) 前置备份**：在 `drop_columns` 之前调 `bench --site <site> backup`，失败则 fail-closed 不发 DDL。
  **代价**：① `agenerp/oob.py` 的 `ALLOWED_CALLS` 要加函数 —— 那是被钉到**参数一级**的白名单，
  加一条就是放宽一次带外执行面，与红线 7 的界线（见 `docs/architecture/module-boundaries.md` §11.8）要重划；
  ② 全站备份对「删一列」是重量级动作，每次 apply 都跑会让门禁慢到不可接受；
  ③ 产物落盘位置与保留策略要定，`.gitignore` 要跟。
- **(b) 列级取证**：删之前 `SELECT` 出该列的非空行并落盘（JSON/CSV），再发 DDL。
  **代价**：① 同样要动 `ALLOWED_CALLS`；② **取证产物本身就是业务数据落盘**，
  它的存放、权限与清理是新的一类问题，本仓此前没有任何这类面；
  ③ 大表上 `SELECT` 全列可能很慢，且它**不是备份** —— 恢复要人手工回灌，只是把「不可逆」变成「难逆」。
- **(c) fail-closed 开关**：`drop_columns` 默认拒绝，要显式传参 / 设环境变量才真发 DDL。
  **代价**：① `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`
  **正在判这条路径**，默认拒绝会让**一条绿着的门禁立刻转红**；
  ② 要让它继续绿，就得动 `tests/gates/**` 去传那个开关 —— **红线 1，loop 不许碰，只有人能做**；
  ③ 开关本身不解决「删错了能不能回来」，只是把不可逆动作往后推一步。
- **(d) 维持现状**，接受代码侧零前置，靠 `ai-autonomy-policy.md:87` 的文档级约束 + 人手工备份。
  **代价**：文档级约束对拿着 shell 的执行器**没有强制力**（该文件自述）；
  P2 出现真实调用方时，第一次踩到就是不可逆的数据丢失。

## 现在就能做的（不需要人裁定，也不碰任何红线）

**手敲那条链之前先备份** —— 命令原文已经写在 `docs/context/project-context.md:60`：

```
docker compose exec -T backend bench --site frontend backup
```

本仓有过一次实测先例（plan `2026-08-22-0228-2`，817012 字节 `.sql.gz`）。
**注意这条只覆盖手敲路径**：`apply_pack` 自动跑那条链上没有任何东西执行它 —— 那正是本条登记的缺口。
