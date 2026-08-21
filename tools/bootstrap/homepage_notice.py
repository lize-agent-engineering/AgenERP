"""引导步骤 · 把「AI 能力未配置」写进站点首页。

由 compose 的一次性服务 `bootstrap-homepage` 在建站之后跑一次。承载物是
`Website Settings.banner_html`，它渲染在所有 website 层页面（含 `/` 与 `/login`）的 navbar 之前。
口径出处：`docs/architecture/system-baseline.md` §14.3（决策 ①、②、残余风险、红线 7 落点）。

**必须在 `frappe-bench/sites` 目录下跑。** frappe 的日志路径写死成 `os.path.join("..", "logs", …)`，
是相对 cwd 的；换个目录跑会直接 `FileNotFoundError: /home/frappe/logs/database.log`。

**只写静态文本**：交付的横幅不含脚本标签、不含模板定界符，也不建任何运行时代码类 DocType
（AGENTS.md 红线 7）。判据是 `tests/unit/test_compose_zero_dep.py::test_bootstrap_delivers_no_runtime_code`。

两条残余风险，与 §14.3 同文并列在此，改这个文件的人先读它们：

1. **文案是引导期一次性判定的。** 下面读一次 `AGENERP_LLM_ENDPOINT` 就定稿；事后改了 `.env` 里的
   AI 变量，首页文案**不会自动跟着变**，要重跑 `docker compose up -d bootstrap-homepage`。
   要做到请求时动态判断就得有服务端代码，那踩红线 7 的边界，本仓不做。
2. **无论 AI 配没配，正文都必须逐字含「AI 能力未配置」。** 这不是文案偏好，是判据侧的事实：
   门禁 `test_homepage_states_ai_disabled_instead_of_crashing` 的断言是无条件的，而门禁起栈时用的是
   宿主环境、compose 还会读仓根 `.env` —— 让文案随环境整段改写，会使门禁在零代码改动下只因换台机器而变红。
   「已配置」分支只允许在这句话**之外**追加状态行。产品真接上 LLM 之后，需要人复核这句话是否仍然贴切。

读 `AGENERP_LLM_ENDPOINT` 不在成败路径上：变量为空是正常状态，本脚本照样退 0（§14 规则 ②）。
"""

import os

import frappe

SITE = os.environ.get("AGENERP_SITE_NAME") or "frontend"
SITES_PATH = "."

_STYLE = (
    "padding:10px 16px;border-bottom:1px solid #e2e8f0;background:#f8fafc;"
    "color:#334155;font-size:13px;line-height:1.7"
)

_NOT_CONFIGURED = (
    '<div style="' + _STYLE + '">'
    "<b>AI 能力未配置</b>　"
    "AgenERP 要让 ERP 的呈现层 / 语言层 / 判断层由 Agent 承担；本栈现在没有接入任何大模型，"
    "这三层仍由 ERPNext 原生界面承担。"
    "为什么是这样：AI 接入变量 AGENERP_LLM_ENDPOINT / AGENERP_LLM_API_KEY / AGENERP_LLM_MODEL 默认全为空，"
    "而外部能力缺失在本仓是「未配置」状态、不是错误状态，所以栈照常起得来。"
    "怎么配上：见仓内 docs/architecture/system-baseline.md 的 §14.3。"
    "</div>"
)

_ENDPOINT_SET = (
    '<div style="' + _STYLE + '">'
    "<b>AI 能力状态</b>　"
    "大模型接入端点：<b>已配置</b>（AGENERP_LLM_ENDPOINT 非空）。　"
    "Agent 承担呈现层 / 语言层 / 判断层：<b>AI 能力未配置</b>"
    "—— P0 阶段本仓不发起任何 LLM 调用，端点配上了也还没有东西去用它。"
    "详见仓内 docs/architecture/system-baseline.md 的 §14.3。"
    "</div>"
)


def notice() -> str:
    endpoint = (os.environ.get("AGENERP_LLM_ENDPOINT") or "").strip()
    return _ENDPOINT_SET if endpoint else _NOT_CONFIGURED


def main() -> None:
    target = notice()
    frappe.init(site=SITE, sites_path=SITES_PATH)
    frappe.connect()
    try:
        settings = frappe.get_doc("Website Settings")
        if (settings.banner_html or "") == target:
            print("引导：首页横幅已是目标内容，跳过")
            return
        settings.banner_html = target
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        print("引导：首页横幅已写入（AI 能力状态）")
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
