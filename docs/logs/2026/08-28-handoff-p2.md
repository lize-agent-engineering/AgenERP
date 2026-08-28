# 交接 · P2 后续（2026-08-28）

> 给下一个会话。**这一场用血换来的东西都在这儿**，不看的话会被重新踩一遍。

---

## 0. 先做：换到主检出、去掉 worktree

人 2026-08-28：「我不想使用 worktree，想要在主项目上的 p2 分支上进行开发。」

⚠️ **上一个会话做不了这件事** —— 它被隔离在 `AgenERP-p2-views` worktree 里，
既动不了主检出，也不能删自己脚下的那个 worktree。**下面的命令要在主检出里跑。**

```bash
cd /Users/lize/Claude/Projects/AgenERP
git worktree remove ../AgenERP-p2-views   # 工作树是干净的，不会丢东西
git switch p2-views
git worktree list                          # 应只剩主检出这一条
```

🔴 **动手前先确认 loop 不会打架**：`launchctl list | grep agenerp` 里有
`com.agenerp.loop`（已注册，当时无 PID）。它此前跑的是 **main 上的 mission**。
把主检出切到 `p2-views` 之后，**它会在 p2-views 上跑** —— 这是不是你要的，
**由人确认**。不确定就先 `launchctl bootout` 停掉它再切。

---

## 1. P2 现在到哪儿了

| 项 | 状态 |
|---|---|
| P2.0 入口关口 Spike 11 | ✅ |
| **P2.0R** schema 检索 | ✅ **2026-08-28 判过**（D-29） |
| P2.1 视图 DSL v0 | ✅ |
| P2.2 渲染器 | ✅ |
| **P2.3** 视图 Agent：自然语言 → DSL | ❌ **下一项**，判据文件 `tests/agents/test_view_agent.py` **还不存在** |
| **P2.4** 定制包 GitOps v0 | ❌ 前置 P2.3 |
| **P2.5** `schema.drift` 巡检 | ❌ 前置 P2.4 |
| P2.6 角色首页 | ✅ 门禁已落地 |
| P2.7 术语层 | ✅ |
| P2.8 CP9 · P2 复盘 | ⏸ **状态源 = 人** |

**剩 3 项串行 + 1 项人工。** P2.3 的验收：`pytest tests/agents/test_view_agent.py -q` 退 0。

---

## 2. 红线（人定的，不许自己放宽）

1. `tests/gates/**` 与**被门禁加载的断言体**只能由人改，提交带 `Gates-Change-Approved-By:`
   - ⚠️ 本场人两次明确指派 loop 代落地（`33101cd` / `abc9c4a`），**那是指派，不是常设授权**
   - 已知的门禁断言体：`tests/unit/test_explain_cost_accounting_body.py`（被
     `tests/gates/test_explain_cost_accounting.py:44` 加载）· `tests/unit/test_live_conformance.py`
2. `.github/workflows/**` 同上
3. `docs/masterplan/**` 只能由人改；`STATE.md` §3 **只追加不改写**
4. `.env` 里永远不放敏感信息；凭据在 `~/.config/agenerp/secrets.env`（0600，仓外）
5. 仓库**公开**。提交前 `git diff --cached | grep -inE "api[_-]?key|password|secret|token"`
   并**逐行读** —— **数量不是判据，判据是 `=` 后面有没有真值**
6. **39 条提交尚未 push**（`origin/p2-views` 落后 39）。push 是对外发布，**要人明说**

---

## 3. 🔴 这一场栽过的跟头 —— 每一条都花了真金白银

### ① 「按工具名数重复」这个信号**骗了四次**
同一批轨迹：按工具名重复 **17/16/37/12** 次，按**工具名+参数**只有 **2/0/1/0** 次。
同一个工具、不同参数是**探索，不是打转**。每次误判都把人引向「做调用去重」——
**那个修法什么也修不了**。判重复**只许**看 `trajectory_full`（名字+参数）。

### ② 把自己配置造成的失败记成 agent 的能力问题 —— **五次**
`max_turns` 太小 · 单条 token 闸 · 总闸 · 输出上限被思考打满 · 判官 JSON 崩。
**每一次的症状都是「agent 答不出来」。** 归因前先问：**是不是我们自己的闸停的？**

### ③ 「补丁 ID 匹配不上 ≠ 内容不在」—— **踩了两次**
`git cherry` 报「main 里没有」，但 rebase/squash 之后 ID 就变了。
判分支能不能删，**必须逐条查内容**，不能只看 cherry / `--merged` / `git diff`。

### ④ 每一次「能力失败」往下查都是 harness —— **直到最后一轮才第一次不是**
修掉的（全部有实测 + 变异验证）：
- 工具结果上限 6000 切在答案前面（**7 条题的正解不可见**）→ 20000
- `meta.fields` **无条件剔除 hidden 字段**（2 条正解永久不可见）→ 保留并标记
- 大单据整表 38,000 字符被截 → 加 `keywords` 过滤
- 子表引用要模型自己拼 → 每行给 `ref`（可照抄）
- `schema.search` 只搜**有数据的**单据（**搜对了词回 0**）→ 覆盖全部业务 DocType，没数据的标记
- `meta.fields` **不回 `description`**（分辨点全丢）→ 非空才回
- 任务类目错配：schema 问题走 `task_class="explain"`，背着业务作答的证据义务
- 答案门禁 / 工具前置在 schema 问题上误挂义务
- 判官贪婪 JSON 解析 + 提示词**引导证人**（「不在集合里」当理由 = 循环论证）
- `/agenerp/home` 三个生产 bug（缺 `uid` · POST 被 CSRF 拦 · schema 工厂不给 sid）

### ⑤ 「在最终位置跑一遍」和「跑过」是两件事
门禁在草稿位置 5 passed，落进 `tests/gates/` 后**一格跑不了**（fixture 依赖变了）。
**换位置本身就是一个变量。**

---

## 4. 额度状态（截至 2026-08-28）

| 模型 | 免费额度 |
|---|---|
| `glm-5.2` | 剩约 4 万 |
| `kimi-k3` | **耗尽** |
| `qwen3.8-flash` | **耗尽** |
| `qwen3.7-flash` | 剩约 14 万 |
| `deepseek-v4-pro-0813` | 已用约 70 万/100 万 |
| `qwen3.8-2.4t-a95b` | **满格 100 万**（一个 token 没花）|
| `qwen3.7-flash-2026-07-15` | **满格 100 万**（一个 token 没花）|

⚠️ **「调得通」证明不了「免费」** —— 额度在控制台，不在响应里。**有真跑判据前先算账**（D-17）。
⚠️ 跑评测**一道闸都不要设**（人两次要求）：`--per-question-budget 0 --budget 0 --max-tool-calls 0`。
设了闸，实测 **42% 的题会被闸砍掉**，而那些失败会**伪装成能力不足**。

---

## 5. P2.0R 的结论（别拿旧数）

**57/60 = 95.0%** · `deepseek-v4-pro-0813` · 独立评测集 60 条全跑 · 一道闸不设 ·
`infrastructure` 排除 **0 条** · 634,442 token。按**点估计**判过（D-29）；
⚠️ 95% 置信下界只有 **87.6%**，D-28 括号里「零失败」并未满足。

⚠️ 之后又补了 `description`，同模型重跑那 3 条失败：**2 条翻过来了**。
**但不得写成 59/60 = 98.3%** —— 只重跑失败项系统性偏高，且 `description`
给每条题都加了上下文，**此前通过的 57 条有没有回退没测过**。

**残余**：近似单据混淆（`Quotation` vs `Request for Quotation`）—— 那张表一个字段说明都没有。
人裁定「留作后续再优化」。

---

## 6. 常用命令

```bash
# 全量判据（除需活栈的三个目录）
python3 -m pytest tests/ -q --ignore=tests/gates --ignore=tests/render --ignore=tests/ui

# 门禁判定器
python3 tools/gates/check_expected_red.py

# 活栈环境
set -a; . ~/.config/agenerp/secrets.env; set +a
export AGENERP_LLM_API_KEY="$DASHSCOPE_API_KEY"
export AGENERP_LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin

# 重新量 P2.0R（**三个 0，一道闸都不设**）
python3 tools/experiments/p2_schema_retrieval/task_completion_eval.py \
  --eval tools/experiments/p2_schema_retrieval/eval-set-independent.jsonl \
  --out  tools/experiments/p2_schema_retrieval/results-final-<模型>.json \
  --max-turns 40 --max-tool-calls 0 \
  --per-question-budget 0 --budget 0 --judge-model <模型>
```
