# P2.0R · schema 检索瓶颈定位

配套 plan：[`docs/plans/p2-views/2026-08-26-P2.0R-schema-retrieval-bottleneck-localization.md`](../../../docs/plans/p2-views/2026-08-26-P2.0R-schema-retrieval-bottleneck-localization.md)

**这不是判据，是实验设施。** 验收判据是 `tests/gates/test_schema_retrieval_recall.py`
（WBS §5），**今天还不存在，且红线 1 规定只能由人建**。

## 结论一句话

**瓶颈在选单据，不在选字段。** 把 DocType 固定住，Top-5 从 **62.5% → 97.5%**（Top-10 = 100%）。

## 文件

| 文件 | 是什么 |
|---|---|
| `eval-set.json` | 40 条中文业务问句 → 目标字段。**40/40 的 ground truth 在活站点上验过存在**（roadmap 硬约束 ④）。**在跑任何检索之前冻结提交**（`e82f73d`） |
| `dump_schema.py` | 把活站点 schema 导成 JSON（只读）。口径逐条对齐 Spike 07 |
| `index_and_eval.py` | 建索引 + 六格评测。纯标准库，无 numpy / faiss |
| `results.json` | 本轮全部结果，含每条问句的 rank 与 Top-5 |

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
