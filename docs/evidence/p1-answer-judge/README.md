# 答案判定器 v0 的证据（P1.4 第 2 个交付面，2026-08-25）

本目录是 plan
[`2026-08-25-0225-1-answer-judge-v0.md`](../../plans/p1-insight/2026-08-25-0225-1-answer-judge-v0.md)
Phase 2 / Phase 3 的落盘证据。判定器本体在 `agenerp/judging/`，实验设施在
`tools/experiments/p1_answer_judge/run.py`。

## 复跑

```bash
set -a; . ./.env; . ~/.config/agenerp/secrets.env; set +a
export AGENERP_LLM_BASE_URL="$DASHSCOPE_BASE_URL" \
       AGENERP_LLM_API_KEY="$DASHSCOPE_API_KEY" \
       AGENERP_LLM_MODEL=qwen3.7-plus-2026-05-26
python3 -m tools.experiments.p1_answer_judge.run --all
python3 -m tools.experiments.p1_answer_judge.run --stability
python3 -m tools.experiments.p1_answer_judge.run --controls
```

**凭据一个字节不在本目录里。** 判定模型由 `--requested` 侧的常量 `JUDGE_MODEL` 点名
（`qwen3.7-plus-2026-05-26`，plan `Decision D2` 起草期写死），不从命令行传。

## 文件

| 文件 | 内容 |
|---|---|
| `all.json` | **第 1 轮**（也是唯一一轮）全量判 24 条：逐条 `run_id` / 产出模型 / 人标签 / 判定标签 / 是否一致 / 三项 usage / 端点原始 usage / 回包原文 + 账本 |
| `stability.json` | H3：6 条（5 条负例全收 + `run-01`）× 3 次 |
| `controls.json` | H5（截断，**判据**）与 O1（剥离，**观测，不作证据**）各 3 次，含变换后的输入全文 |

## 怎么读 `all.json`

- `summary.meets_acceptance` 就是 plan §6 **H2** 那一个口径的取值。口径**只有一处实现**，
  在 `tests/unit/answer_judge_fixture.py` 的 `meets_acceptance()`；本脚本按路径加载它，不另写。
- `summary.by_answer_model` 是 §1.3c 要求的**按产出模型分组** —— 判定器自评的那 6 条
  （`qwen3.7-plus-2026-05-26` 产出的 `r2-01`–`r2-06`）可以单独摘出来看。
- `ledger` 是 P1.7 的 `CallLedger`：**一次 `chat()` 一条记录**，条数即这一趟真花掉的调用次数。

## 第 1 轮的数字（2026-08-25，`qwen3.7-plus-2026-05-26`）

| 项 | 值 |
|---|---|
| 判定行数 | **24**，失败调用 **0** |
| 负例三分类**逐条精确** | **5 / 5**（`run-07` → `truncated`；`run-02` / `run-05` / `run-13` / `r2-07` → `incomplete`） |
| 正例保住 | **19 / 19** |
| 逐条一致 | **24 / 24**（`overall_agreement`） |
| `meets_acceptance` | **true** —— H2 在**第 1 轮**即达标，**修订次数 0、全量轮数 1** |
| 账本条数 | **24**（== `chat()` 调用次数） |
| 累计 token | prompt 33,970 · completion 14,713 · **reasoning 14,416** · total 48,683 |
| `total_matches_endpoint` | **24 / 24** |

按产出模型分组（§1.3c / §8 风险⑥）：**四个模型各 6 条，四组各 6/6 一致。**
其中 `qwen3.7-plus-2026-05-26` 的那 6 条是**判定器自评**（`r2-01`–`r2-06`，人标全 `correct`）。
⚠️ **自评偏向照实登记，不做加权、不做剔除**：正例准确率那一半里有 6/19 是它自己写的答案。
承重的 5 条负例**一条都不是它写的**（`run-02` / `run-05` / `run-07` / `run-13` 出自 `qwen-plus`，
`r2-07` 出自 `qwen3.8-max`）。

## ⚠️ 这份证据**不能**支撑什么（逐字照抄 plan §8 风险①）

- **没有留出集**（plan `Decision D7`：5 条负例分不动）⇒ **不许写成"泛化已验证"**。
- 集子之外的证据只有 `controls.json` 里的 **H5 一条**，而 H5 自己就写死了
  "一个长度阈值规则同样能通过它" ⇒ **对"集子之外的判别力"的实证支撑接近于零**。
- **O1（剥离）是观测，不是证据**：删哪些句子由脚本自列的关键词表决定，
  而 roadmap 逐字「标签只能由人读原文定，不能由任何判定器产生」。
- **已验证的适用范围只有 P1.0 那一道题**。跨题族使用按 D-16 只能写「待复验」。
- **`meets_acceptance` 为真是必要条件，不是充分条件**：plan §1.3 已实测，一个两行规则
  （`len<300 → truncated；否则 '外协' in a`）**照样通过同一个口径**（负例 5/5、正例 18/19）。
  "判定器不是关键词正则"这句话的证据在 `tests/unit/test_answer_judge.py` 的**结构判据**上
  （H7 三级），不在这份数字上。
