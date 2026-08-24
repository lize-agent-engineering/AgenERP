# 入口关口实验的轨迹（P1.0，2026-08-24）

本目录是 plan [`2026-08-24-P1.0-entry-gate-experiment.md`](../../plans/p1-insight/2026-08-24-P1.0-entry-gate-experiment.md)
Phase 3 的落盘证据：**2×2 网格（门禁开/关 × 弱/强模型）× 每格 3 次 = 12 次运行**。

## 怎么读

每份 `run-NN.json` 是一次完整运行的结构化轨迹：

| 键 | 内容 |
|---|---|
| `model` / `gate` | 这一跑落在哪一格 |
| `question` / `prompt_sha256` / `prompt_bytes` | 问题与提示词的身份。**四格必须完全相同** |
| `turns[]` | 逐轮：`kind` 为 `tools` 时带 `calls[]`（工具名、参数、`ok`、违约阶段与原因、站点请求数），为 `answer` 时带答案文本 |
| `gate_checks[]` | 每次作答时的门禁判定：`enforced`（这一格是否真的回注）、`facts`（五条事实的当次取值）、`failed[]`（哪条规则红了、还缺几项） |
| `final_answer` | 判定的**唯一**对象 |
| `usage` | `prompt` / `completion` / **`reasoning`** / `total`，三项分开记 |
| `invalid` | 非 `null` 即这一跑无效（token 超限 / 模型侧失败 / 超轮数），**照实记录，不静默丢弃** |
| `tool_calls_total` | H4（门禁的代价）用的就是这个数 |

## 判定的口径

- 判定对象**只有 `final_answer`**，不看轨迹、不看模型名（plan §2 的判定协议）。
  工作单由 `python3 -m tools.experiments.p1_entry_gate.worksheet docs/evidence/p1-entry-gate`
  生成，它**只输出 run_id 与答案文本**。
- 三条判据逐条打勾，判完再揭配置。判定表落在
  [`verdicts.md`](./verdicts.md)，逐条命中/未命中可见，不只写总评。

## 一处**做不到**的事，照实写在这里

**真正的盲判做不到**：本轮的执行者与判定者是同一个（都是循环）。
做到的是「**先只看答案文本逐条打勾、再看配置**」，且判定表与工作单都落盘可复核。
`run-NN` 与格位的对应关系是**打乱**的（不是 01–03 一格、04–06 一格），
这降低了「按编号顺序猜格位」的便利，但**不等于盲判**。
判定时按此折价 —— 见审计文件里的「与预期相反的结果」一节。
