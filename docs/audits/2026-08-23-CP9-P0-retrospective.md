# CP9 · P0 阶段复盘

> **判据事先写死**（`docs/masterplan/04-RUNBOOK.md` §7），本文只负责对着证据判，不重新定义判据。
> **结论只有「续用」「停用」两种，不许写「继续观察」。**

日期：2026-08-23 · sha `8ca4629` · 分支 `p1-insight`

---

## 1. AGE / mission-driver → **续用**

| 事先写死的判据 | 实测 | 判 |
|---|---|---|
| 本阶段有 ≥1 个工作项**完整地**由循环推完（drafted → executed → 门禁绿 → 关闭） | `docs/plans/p0-foundation/` 下 32 份 plan，至少 4 份走完整轮并置 `Status: completed`：`2026-08-22-1041-1-destructive-write-owner-doc-alignment`、`2026-08-23-0337-2-expected-red-ratchet-set-check`、`2026-08-23-0859-2-ruff-force-exclude-guards-the-judge`、`2026-08-23-1056-1-site-write-methods-behavioral-verdict` | ✅ |
| 门禁误放行（判 pass 但其实错）次数 **= 0** | 见下节逐条核 | ✅ |

### 门禁误放行的逐条核查（这条最要紧，CP1 把它列为头号风险）

搜到三处相关记录，逐条判定**没有一条构成误放行实例**：

**① `STATE:184` 两个新 CI job 的变异实证** —— 这是门禁**有效**的证据，不是失效：
分支 `ci/0337-1-seed-lint-coverage`、PR #8、5 次 run，**四条 CI 预测在推之前逐字写死、事后逐条吻合**。

**② `STATE:218` ruff 的假绿形态** —— **是主动发现并已缓解的形态，不是「判 pass 但其实错」的实例**。
排除生效时 ruff 静默退 0，输出只有 `warning: No Python files found` + `All checks passed!`——
「我检查了，全过」与「我根本没看」在退出码上一模一样。处置已落地两条：`pyproject.toml` 与
`project-context.md` 明写此事；那行 `warning:` 是唯一肉眼线索，**不得**被任何调用方 `2>/dev/null` 吞掉。

> **这是本阶段离误放行最近的一次**，虽不构成实例，仍照实登记：它说明「退出码为 0」本身
> 从来不是充分判据，判据必须能区分「跑了且过」与「根本没跑」。P1 的门禁设计要继承这条。

**③ `docs/audits/2026-08-20-CP1-masterplan-grill.md:15`** —— CP1 把门禁误放行识别为
「唯一能静默通过全部防线的失败」并要求在 CP9 单列。这是**判据的来源**，不是实例。

### 支持续用的正面证据

守卫 `verdict-tool-untouched` 拿到**四次变异实证 + 三次基线跑**，
**七条 CI 预测（⓪–⑥）在推之前逐字写死、事后全部命中、零条未预测的红**
（实验分支 `ci/0337-2-experiments`，PR #10，永不合并）。
「预测在前、结果在后、逐条吻合」是这套方法论最硬的自证形式。

---

## 2. LoopX → **停用**

| 事先写死的判据 | 实测 | 判 |
|---|---|---|
| 跨会话恢复实际生效 **≥3 次** | `loopx status`：**`run-history goals=1 runs=1`** —— 只有一次 run | ❌ |
| 与 mission-driver 无「谁说了算」的冲突 | 未发现冲突记录 | ✅（但不足以救） |
| 停用条件：**跨会话恢复从未真正用上**（说明它没在解决真问题） | 见下 | **命中** |

### 决定性证据

`loopx status` 自己报了两条 finding：

```
action source_registry_missing goal=agenerp-goal: 源注册表缺失
action state_file_missing      goal=agenerp-goal: 活动状态文件缺失
    action: preview `loopx retire-global-goal --goal-id agenerp-goal`
```

**LoopX 自己建议退役这个 goal。** 状态文件缺失意味着「跨会话恢复」这个核心能力
在本阶段实际上无状态可恢复——它从未在真实的会话切换里被依赖过。

而本阶段实际发生的跨会话恢复（多次，包括几次网络中断与配额停机后的续跑），
靠的是 **`docs/masterplan/STATE.md` 的 RESUME 协议 + git**，不是 LoopX。
STATE 开头那句「这是投影，不是真相源。真相源是：LoopX 状态（启用时）+ git + 门禁退出码」
在实践中被推翻了一半：**真相源实际是 git + 门禁退出码 + STATE 本身**。

### 停用的处置

1. **不删除**已安装的 LoopX，也不动 `.loopx/registry.json`——停用是「不再依赖」，不是「清除痕迹」
2. `STATE.md` 顶部那句真相源声明**改为不含 LoopX**，使文档与实际一致
3. D-6（LoopX 采用，试点）在 DECISIONS 里标注本次复盘结论
4. 若 P1 出现「STATE 手工维护成本过高」的实测证据，可由**人**重启评估——但那是新的采用决策，不是恢复旧的

---

## 3. 给 P1 的三条继承项

**① 退出码 0 不是充分判据。** ruff 那处假绿形态说明「跑了且过」与「根本没跑」
必须在判据层面可区分。P1 的 Agent 门禁（证据充分性、消融测试）尤其危险——
「Agent 答对了」与「Agent 蒙对了」在结果层面也长得一样。

**② 预测在前、结果在后、逐条吻合。** 这是 P0 最有效的自证形式，
P1 的关口实验（P1.0）应沿用：**实验假设在跑之前逐字写死**。

**③ 真相源是 git + 门禁退出码。** 不要再引入第二个状态内核，除非它能证明自己
在解决一个 git + 门禁解决不了的问题。
