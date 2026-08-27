# P2.0R · schema 检索瓶颈定位

配套 plan：[`docs/plans/p2-views/2026-08-26-P2.0R-schema-retrieval-bottleneck-localization.md`](../../../docs/plans/p2-views/2026-08-26-P2.0R-schema-retrieval-bottleneck-localization.md)

**这不是判据，是实验设施。** 验收判据是 `tests/gates/test_schema_retrieval_recall.py`
（WBS §5），**今天还不存在，且红线 1 规定只能由人建**。

## 结论两句话

1. **第一轮：瓶颈在选单据，不在选字段。** 把 DocType 固定住，Top-5 从 **62.5% → 97.5%**（Top-10 = 100%）。
2. **⛔ 第二轮：硬两段式收敛失败 —— 60.0%，比基线 65.0% 还低。**
3. **⛔ 第三轮：分数融合也失败 —— 最好一档 65.0%，与基线一模一样，一分不加。**
   且 `Top-1` 在整条 α 曲线上恒为 30.0。

🔴 **三轮之后的那句话**：第二、三轮**都是拿同一批 embedding 再算一遍 ——
从同一口井里再打一次水**。第一轮 oracle 能跳 35 个点，是因为它从外面注入了
一条这批向量里没有的信息（正确答案在哪张单上）。
**任何不注入新信息的重排，结构上都够不着那 35 个点。**

## 文件

| 文件 | 是什么 |
|---|---|
| `eval-set.json` | 40 条中文业务问句 → 目标字段。**40/40 的 ground truth 在活站点上验过存在**（roadmap 硬约束 ④）。**在跑任何检索之前冻结提交**（`e82f73d`） |
| `dump_schema.py` | 把活站点 schema 导成 JSON（只读）。口径逐条对齐 Spike 07 |
| `index_and_eval.py` | 建索引 + 六格评测。纯标准库，无 numpy / faiss |
| `results.json` | 第一轮全部结果，含每条问句的 rank 与 Top-5 |
| `doctype_disambiguation.py` | 第二轮：DocType / 单据族聚合 + 两段式。**自带设施自检**：重算的字段级基线必须与第一轮逐格相等 |
| `results-round2.json` | 第二轮全部结果 |
| `score_fusion.py` | 第三轮：分数融合 α 扫描。**向量落盘缓存**（带 `texts_sha` + 模型名校验），后续轮次不必再等 145 秒 |
| `results-round3.json` | 第三轮全部结果，**含全部 11 档 α 的曲线** |
| `GATE-DRAFT-test_schema_retrieval_recall.py.txt` | 🔴 **给人的判据草稿**。后缀刻意是 `.txt`、路径刻意不在 `tests/gates/` 下 —— 红线 1。头部有四条落之前必读的实测教训 |

## 原样复跑

前置：本机 Ollama 在 `127.0.0.1:11434` 上，且有 `qwen3-embedding:0.6b`；
`agenerp-backend-1` 容器在跑。**零 LLM API 调用，零额度消耗。**

```bash
docker cp tools/experiments/p2_schema_retrieval/dump_schema.py agenerp-backend-1:/tmp/
docker exec -w /home/frappe/frappe-bench/sites agenerp-backend-1 \
  ../env/bin/python /tmp/dump_schema.py frontend > /tmp/schema.json
```

```bash
python3 tools/experiments/p2_schema_retrieval/index_and_eval.py \
  --schema /tmp/schema.json \
  --eval   tools/experiments/p2_schema_retrieval/eval-set.json \
  --out    tools/experiments/p2_schema_retrieval/results.json
```

建索引耗时：6,350 字段，raw `127s` / described `152s`。

## ⚠️ 读这些数之前必须知道的两件事

1. **`live`（只索引有数据的 DocType）过滤器在本站点是净亏的**（65.0% → 62.5%），
   与 Spike 07 上的 +15 点相反。机制已查明：它新中 4 条、丢掉 5 条，
   而丢掉的 5 条**恰好是答案 DocType 行数为 0 的那 5 条**——本站点种子数据太薄。
   **这个过滤器不能无条件启用**，详见 plan §12.5。
2. **97.5% 是 oracle 数，不是可交付的检索器。** 它假设「已经知道正确 DocType」，
   而那正是待解的部分。**不得把它当作 P2.0R 已达标。**

## 第二轮复跑

```bash
python3 tools/experiments/p2_schema_retrieval/doctype_disambiguation.py \
  --schema /tmp/schema.json \
  --eval   tools/experiments/p2_schema_retrieval/eval-set.json \
  --out    tools/experiments/p2_schema_retrieval/results-round2.json
```

脚本会先自检：重算的字段级 `business × described` 必须与 `results.json` 逐格相等
（`selfcheck_matches_previous`）。**不等就别看后面的数。**

## 第三轮复跑

```bash
python3 tools/experiments/p2_schema_retrieval/score_fusion.py \
  --schema /tmp/schema.json \
  --eval   tools/experiments/p2_schema_retrieval/eval-set.json \
  --out    tools/experiments/p2_schema_retrieval/results-round3.json \
  --cache  /tmp/p2_vectors.json
```

设施自检在 `α = 1.0` 那一格：**必须恰好等于第一轮的 65.0%**，不等于就是算错了。
