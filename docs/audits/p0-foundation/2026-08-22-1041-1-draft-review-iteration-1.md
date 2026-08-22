# 草案评审留痕 · `2026-08-22-1041-1` 第 1 轮（对**已作废的前一稿**）

> Created: 2026-08-22
> Kind: `draft review`（**不是** closure audit —— 本文件不构成任何 mission 级审计证据）
> Reviewer: 独立子代理，fresh session，MISSION_DRIVER `2026-08-22-055517-mission-driver`
> 评审对象: `docs/plans/p0-foundation/2026-08-22-1041-1-ddl-drop-rollback-evidence.md`
> —— **该文件已被删除，且从未提交，因此不在 git 历史里。本文件是它唯一的留痕。**
> 现存后继: [`2026-08-22-1041-1-destructive-write-owner-doc-alignment.md`](../../plans/p0-foundation/2026-08-22-1041-1-destructive-write-owner-doc-alignment.md)

## 为什么留这份文件

第 2 轮评审（另一个 fresh session）指出：后继 plan 的 `## Draft Review Record` 引用了第 1 轮的
8 条 Blocking / 3 条 Non-blocking，而被评审的那一稿**在盘上和 git 历史里都找不到**
（`git log --all` 零命中），于是那些引用**无法被独立核对**，只能「取信」。
本文件把第 1 轮的结论落成durable 证据，消除那个「取信」缺口。**不改写、不美化，照实抄。**

## 前一稿是什么

题目：给 `agenerp/oob.py` · `drop_columns`（本仓唯一不可逆的 `ALTER TABLE … DROP COLUMN`）
加**代码级前置取证 + fail-closed**（取不到取证产物就拒绝发 DDL），四个 Phase：
Explore/Decision 定取证形态 → 实现 + 判据 + 变异验证 → live 路径实证 → owner-doc 加严。

## 第 1 轮结论

**VERDICT: `needs revision`**

### Blocking（8 条，原文要点）

1. **判据先行未处理，且所引先例被明文排除。** 前一稿把自己挂在「工作项 5/6 的实现面残余」上，
   而 `docs/backlog/p0-foundation-roadmap.md` 工作项 9 那一格逐字写着「不引工作项 8 / WBS P0.7 作先例——
   那两处确实绑着 `test_zero_dep_boot.py` 的具体断言，不是同一情形」；工作项 5/6 绑的正是
   `test_customization_roundtrip_delete.py` 的具体断言。要做，得先由人出 `Gates-Change-Approved-By:` 补门禁。
2. **Baseline 第 1 条说错了范围。** 「本仓唯一的写动作」与 `agenerp/oob.py:262` docstring 的
   「本**模块**唯一」不符；`agenerp/site.py:196` `delete_custom_field` 是第二条写路径。
3. **给 D1 安 `Minimum Rule 14` 站不住。** `ai-autonomy-policy.md:87` 已点名
   `agenerp/apply.py` · `execute_plan` 的删除路径，而那是 `drop_columns` 的调用链
   （`apply.py:251`→`:254`→`:304`），区域意义上已罩住。应改述为「加严 / 具体化」，
   并停止拿它当合法性锚点。
4. **`1922-3` 的引用被截断在承重的那半句。** 该 plan `## Deferred But Adjudicated` 第一条
   （`:716` 一带）逐字含「**代价要说清**：`creates` 不落地 = **站点侧的回滚只能手工做**」——
   即「手工回滚」是**已裁定状态**，重开事件未发生。
5. **Decision 候选表不对称**：只给候选 (a) 记了「要开第四个 exec 目标」的代价，
   而候选 (b) 需要在 `db` 上新开一个**读**方向（§11.8 的 `db` 行只有写方向），同样是新 exec 目标。
6. **红线自查里的 `<基线>` 没绑定**，与 `0027-1:959` 已修过的同一处缺陷（「一律用开工 sha，不用裸 `git diff`」）。
7. **「零 CI 消耗」没有兑现手段**：漏了「不推 `main`」，而 `.github/workflows/gates.yml:6-8`
   在 `push: branches: [main]` 上触发，且 `main` 领先 `origin/main` 5 个提交。
8. **取证产物落盘路径与 `.gitignore` 无判据**：候选 (b) 会把真实业务列值写到盘上，
   而没有任何 Phase 把 `.gitignore` 列进 Targets，也没有保留策略。

### Non-blocking（9 条，本文件只抄被后继 plan 用到的三条）

1. Baseline 漏了相邻的真漂移：`docs/architecture/module-boundaries.md:577` 说
   `SiteClient`「只有读方法」、`:581` 说写/删方法「未做」，而 `agenerp/site.py:196` 已实现。
6. Deferred 第三条（契约面台账）的触发条件循环。
8. Phase 1 与 Phase 3 的 Exit Criteria 没有可跑命令。

### 推荐

**(ii) 收窄到 `ai-autonomy-policy.md:87` 的加严一项**，把取证 / fail-closed 的正文写进
`docs/backlog/` 交人裁定。理由逐字：那条 policy 行「tightening-only，不需要绑门禁，
对正绿着的 live 门禁零风险」，而前一稿的 Phase 1–3「往那条门禁的执行路径里插 fail-closed 代码，
既没有绑定判据、没有确认的缺陷，也没有取证产物的消费方」。

## 处置

后继 plan **是照推荐 (ii) 重写的，不是修补**：前一稿删除，`agenerp/**` 从「要改」变成「一行不改」。
B1/B3/B4/B6/B7 逐条落进后继 plan 的 `## Current Baseline` 与 `## Non-Goals`；
B2 改述为三处落点并列；B5/B8 随前一稿的三个 Phase 一起消失（它们只对取证实现成立）；
NB1 成为后继 plan 的 D2/D3；NB6/NB8 已在后继 plan 内改掉。
