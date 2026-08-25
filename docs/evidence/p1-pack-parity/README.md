# p1-pack-parity · 行业包的离线↔活站点命中集合逐字比对（**一次跑**，2026-08-25）

plan：[`docs/plans/p1-insight/2026-08-25-1026-1-industry-pack-live-parity.md`](../../plans/p1-insight/2026-08-25-1026-1-industry-pack-live-parity.md)
落点节：[`docs/architecture/module-boundaries.md` §7.19](../../architecture/module-boundaries.md)

## 这里有什么

| 文件 | 是什么 |
|---|---|
| `offline-hits.json` | **整份** `InspectionReport.as_dict()`（三个键都在），离线固定测例那一侧 |
| `live-hits.json` | **整份** `InspectionReport.as_dict()`，活站点（`frontend@http://127.0.0.1:18080`）那一侧 |
| `parity.json` | `tools/experiments/p1_pack_parity/parity.py` 的 **结构化差异**输出（不是布尔） |

⚠️ 前两个文件名叫 `-hits` 但存的是**整份报告**：只存 `hits` 会让
`rule_ids`（H3）与 `request_count`（H5）在复算时取不到数。

## 结论

**`verdict: identical` —— 三条规则的命中集合两侧逐字一致。**

| 规则 | 离线 | 活站点 | 数 |
|---|---|---|---|
| `discrete/finished-goods-backlog` | 1 条 | 1 条 | `on_hand = 1010.0`（`= agenerp/seed/checks.py` 的 `EXPECTED_BACKLOG_QTY`）|
| `discrete/subcontracting-issued-not-received` | 0 条 | 0 条 | —（种子外协链完整，**零命中是正确行为**）|
| `discrete/closed-order-short-delivered` | 1 条 | 1 条 | `shortfall = 10.0`（`= EXPECTED_SHORTFALL_QTY`）|

`rule_ids` 两侧逐字相同（三条、同序）。命中集合两侧**都非空**（各 2 条），
非空断言写在比对之前 —— 「两个空集相等」在这里不会被叫作「逐字一致」。

⚠️ **2026-08-24 那次 H4 核对的结论是「部分一致」**（`closed-order-short-delivered`
离线命中 10、站点零命中）。成因是站点上那张单没被人工关闭，已由**人**于 `484c123`
在种子装载面修掉。本次是那之后的第一次比对，**追加一次新观测，不抹掉上一次**。

## 这次没有证明什么（逐字写清）

- **这是一次跑，不是分布。** 只跑了一次两侧。任何一次并发写入都会让这次比对失去意义 ——
  H9 的前后读回只排除掉「本轮自己写了」，**排除不掉「别人在同一分钟写了」**。不说成「已隔离」。
- **两侧一致证明的是「站点装载忠实于数据集」，不证明数据集本身对。**
  后者由 `tests/gates/test_seed_dataset_absurdity.py`（裁判）与 `agenerp/seed/checks.py` 各自负责。
- **一致不等于规则表达对。** 规则表达由它自己的 `test_case` 与阳性/阴性对照证明，
  **不由本次比对证明**。两侧都用同一份规则跑，规则写错了两侧会一起错。
- **本节判的是「命中集合是否逐字一致」，站点侧对账（`_trap_precondition_checks`）判的是
  「站点上有没有那个可查的事实」——** 两者不是同一件事，混成一句话就是把
  「前提事实在」说成「包在真站点上验证过」。
- 外协那条规则**两侧都零命中**，因此这次跑**没有**给它一次真实数据上的阳性对照。

## 本轮零模型调用 —— 它靠的是下面**这两项**，不是 Phase 3 的结论

⚠️ Phase 3 的 H7 是在**假两侧**上测的，**与这一跑不是同一次跑**，不搬过来当证据。
⚠️「Non-Goals 写了不许调」**不是观测量**，不用它代替判据。

1. **驱动器进程自己的环境**（不是 shell 的环境 —— 活跑发生在驱动器进程里）：
   `sorted(k for k in os.environ if "DASHSCOPE" in k or "AGENERP_LLM" in k)` 实读原样为
   **`["AGENERP_LLM_MODEL", "DASHSCOPE_BASE_URL"]`**。
   ⚠️ **plan 起草期写死的预测是这条清单为空 —— 它没吻合，照实记，不改写预测。**
   原因是那个过滤器**按名字前缀抓，抓到的不全是凭据**：`AGENERP_LLM_MODEL` 是模型名、
   `DASHSCOPE_BASE_URL` 是端点地址，**两个都不是凭据**。
   真正的那一条另测并成立：`[k for k in 上表 if k.endswith("_API_KEY") or k.endswith("_API_SECRET")]`
   → **`[]`**（`AGENERP_LLM_API_KEY` 未设 ⇒ `config_from_env()` 起不来）。
   ⚠️ **本项只是前置条件检查，不是独立观测量**：凭据未设只能证明「调了也会失败」，
   **区分不了「没调」与「调了但失败」**。必须与第 2 项合取。
2. **`ChatAdapter` 构造面整体替身的计数为 `0`**（`__init__` / `chat` / `_send` / `_post` /
   `_ssl_context` 五处，一被碰就计数并炸 ⇒ 真调了当场非 0 且落不了盘）。
   **替身由观测方（驱动器）装，不由被观测方（`run.py`）自装** —— 被观测方自报的证据
   不是独立证据（先例自己的规矩 3 逐字「从账本自己数账本是同义反复」）。

实读输出原文：

```json
{"driver_exit_code": 0, "llm_named_env_keys_verbatim": ["AGENERP_LLM_MODEL", "DASHSCOPE_BASE_URL"], "llm_credential_env_keys": [], "chat_adapter_probe_calls": 0}
```

## 对活站点零写（H9）

两种读回口径，比对**前后**各取一次，**逐条相等**：

| 口径 | 前 | 后 |
|---|---|---|
| `GET /api/resource/<dt>?fields=["name"]&limit_page_length=0` 的行数 | `{"Sales Order": 1, "Delivery Note": 1, "Stock Ledger Entry": 10, "Bin": 4}` | 同左 |
| `GET /api/method/frappe.client.get_count?doctype=<dt>` | `{"Sales Order": 1, "Delivery Note": 1, "Stock Ledger Entry": 10, "Bin": 4}` | 同左 |
| `SAL-ORD-2026-00001.modified` | `2026-08-25 07:30:46.926828` | `2026-08-25 07:30:46.926828` |
| `SAL-ORD-2026-00001.status` | `Closed` | `Closed` |

另有一层运行期的挡板：站点请求全部经 `run.py` 的 `ReadOnlyTransport`，
白名单只有**任意 `GET`** 与 **`POST /api/method/login`**（换会话那条既有路径），
白名单外当场抛。本次实录 **11 条请求：`GET` 10 条 + `POST /api/method/login` 1 条，`denied` 为空**。

## 站点只读请求数（H5）：预测 9，实测 **10**

`live-hits.json` 的 `request_count` 是 **10**，而 §7.10 记的 2026-08-24 那次是 **9**。
⚠️ **本格不是承重格，也不是异常** —— plan 起草期就写死了「实测到 10 不是异常，照实记」。
**没有为了凑那个 9 改任何一条规则或巡检器。**
比对器按契约 ② **只记录、不判定** `request_count`（`"judged": false`）：
两侧的取数路径本来就不同，把它算进判定会让比对**恒红**。

## 怎么复算

```bash
python3 - <<'PY'
import importlib.util, json, pathlib, sys
E = pathlib.Path("docs/evidence/p1-pack-parity")
spec = importlib.util.spec_from_file_location("parity", "tools/experiments/p1_pack_parity/parity.py")
m = importlib.util.module_from_spec(spec); sys.modules["parity"] = m; spec.loader.exec_module(m)
recomputed = m.compare(json.loads((E/"offline-hits.json").read_text()),
                       json.loads((E/"live-hits.json").read_text()))
on_disk = json.loads((E/"parity.json").read_text())
sys.exit(0 if json.dumps(recomputed, sort_keys=True) == json.dumps(on_disk, sort_keys=True) else 1)
PY
```

实跑 → **exit 0**（两份报告重新喂给比对器，输出与 `parity.json` **逐字相等**）。

⚠️ **不是**「把 `parity.json` 喂回比对器」—— 它是差异输出、不是报告，类型对不上，那样写跑都跑不起来。

## 已知缺口（照实点名，不代人处置）

比对链落在 `tools/`，而 **`tools/` 不在 `ruff` 的作用域里、也不在任何 CI job 里**
（`docs/backlog/tools-dir-has-no-static-check-coverage.md`，`Status: deferred`，处置者是**人**）。
钉着那份出货脚本行为的，只有 `tests/unit/test_pack_parity_harness.py` **按路径加载它**
这一条纪律（判据 ⑩）+ 变异 M9。**这是缓解不是消除**：`ruff` 仍然扫不到它。
