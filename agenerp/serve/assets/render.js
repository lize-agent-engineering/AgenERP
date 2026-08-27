/* AgenERP · 视图渲染器 v0（P2.2 · plan 2026-08-27-P2.2 · 路线 C）
 *
 * 由 agenerp/serve/app.py 的 RENDER_ASSET_PATH 发出（不认人、不接受路径参数），
 * 经 nginx 那一跳同源送到页面。
 *
 * ## 三条硬约束，与 desk.js 同源（module-boundaries.md §7.23），改之前先读
 *
 *   1. **建 DOM 只走 textContent / createTextNode。** 本文件里
 *      innerHTML / outerHTML / insertAdjacentHTML / document.write 必须是零命中。
 *      判据用静态扫描守着。
 *   2. **权限由后端强制，前端只做提示。** 数据一律同源直打 Frappe 的 /api/resource
 *      并带浏览器自己的 sid（credentials: "same-origin"）——
 *      渲染器**从不自行放行任何一条数据**，403 就照实显示 403。
 *   3. **未支持的一律落回 Desk，且说清为什么。** 一块凭空消失的内容比一句
 *      「这里画不了，因为…」危险得多。
 *
 * ## 两处刻意的降级，代价写在明处
 *
 *   · 富文本（Text Editor）**剥标签只显纯文本**。渲染 HTML 会开一个注入面，
 *     而那正是约束 1 挡的东西。代价：用户看不到格式 ⇒ 给一个「在 Desk 中查看格式」的入口。
 *   · 附件（Attach / Attach Image）的值是**用户可写字段**里的 URL。
 *     只放行站内相对路径与 https —— 其余降级成纯文本并说明原因。
 */
(function () {
	"use strict";

	var MARK = { name: "agenerp-render", version: "0.1.0", plan: "2026-08-27-P2.2" };

	try {
		Object.defineProperty(window, "agenerpRender", {
			value: Object.freeze(MARK),
			writable: false,
			configurable: false,
			enumerable: true,
		});
	} catch (err) {
		// 已经挂过：不抢、不覆盖，让「恰好 1 次」的失败可见。
		return;
	}

	var VIEW_PLAN_PATH = "/agenerp/view";
	var RESOURCE_PATH = "/api/resource";
	var ROOT_ID = "agenerp-view-root";

	// 附件 URL 的 scheme 白名单。**封闭**，与 agenerp/dsl/fallback.py 的
	// ALLOWED_ATTACHMENT_SCHEMES 一字对应。
	var SAFE_URL_PREFIXES = ["/", "https:"];

	// ---- DOM 小工具：**只有这三个**，别处不许自己建元素 ----

	function el(tag, className, text) {
		var node = document.createElement(tag);
		if (className) { node.className = className; }
		if (text !== undefined && text !== null) { node.textContent = String(text); }
		return node;
	}

	function put(parent, child) { parent.appendChild(child); return child; }

	function deskLink(doctype, name) {
		var a = el("a", "agenerp-desk-link", "在 Desk 中打开");
		// 站内相对路径，写死前缀 —— doctype/name 只做 encodeURIComponent，不拼 scheme。
		a.setAttribute(
			"href",
			"/app/" + encodeURIComponent(String(doctype || "").toLowerCase().split(" ").join("-"))
				+ (name ? "/" + encodeURIComponent(String(name)) : "")
		);
		a.setAttribute("rel", "noopener");
		return a;
	}

	// ---- 安全判定：URL 能不能当链接/图片用 ----

	function isSafeUrl(value) {
		if (typeof value !== "string" || value === "") { return false; }
		var v = value.trim();
		// 相对路径必须以单个 "/" 开头；"//host" 是协议相对，等于放行任意 host，**不放**。
		if (v.charAt(0) === "/" && v.charAt(1) !== "/") { return true; }
		for (var i = 0; i < SAFE_URL_PREFIXES.length; i++) {
			var p = SAFE_URL_PREFIXES[i];
			if (p !== "/" && v.slice(0, p.length).toLowerCase() === p) { return true; }
		}
		return false;
	}

	// ---- 富文本：剥标签。**不是消毒，是丢弃** ----

	function stripTags(html) {
		if (typeof html !== "string") { return ""; }
		// 刻意不用 innerHTML 反序列化再取 textContent —— 那会真的解析一次 HTML，
		// 顺带触发 <img onerror> 那一族。这里只做纯字符串处理。
		return html
			.replace(/<[^>]*>/g, " ")
			.replace(/&nbsp;/g, " ")
			.replace(/&amp;/g, "&")
			.replace(/&lt;/g, "<")
			.replace(/&gt;/g, ">")
			.replace(/&quot;/g, "\"")
			.replace(/\s+/g, " ")
			.trim();
	}

	// ---- 取数：一律同源带 sid，权限由后端说了算 ----

	function getJSON(url) {
		return fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
			.then(function (res) {
				return res.json().catch(function () { return {}; }).then(function (body) {
					return { status: res.status, body: body };
				});
			});
	}

	function resourceUrl(block) {
		// `name` 一律带上：detail 块靠它去取单据详情（子表只在详情里）。
		var fields = (block.fields || []).slice();
		if (fields.indexOf("name") === -1) { fields.push("name"); }
		var q = RESOURCE_PATH + "/" + encodeURIComponent(block.doctype)
			+ "?fields=" + encodeURIComponent(JSON.stringify(fields))
			+ "&limit_page_length="
			+ encodeURIComponent(String(block.type === "detail" ? 1 : (block.limit || 20)));
		if (block.filters && block.filters.length) {
			q += "&filters=" + encodeURIComponent(JSON.stringify(block.filters));
		}
		if (block.sort && block.sort.length === 2) {
			q += "&order_by=" + encodeURIComponent(block.sort[0] + " " + block.sort[1]);
		}
		return q;
	}

	// ---- 各种块 ----

	function renderDenied(host, status) {
		// 约束 2：前端不判权限，**只把后端说的那句照实显示**。
		var box = put(host, el("div", "agenerp-denied"));
		put(box, el("p", null, status === 403
			? "你看不到这个，因为后端没有放行这条数据（HTTP 403）。"
			: "取数失败（HTTP " + status + "）。"));
		return box;
	}

	function renderValueCell(row, doctype, fieldname, fieldtypes) {
		var value = row[fieldname];
		var kind = fieldtypes && fieldtypes[doctype + "." + fieldname];
		var cell = el("td");
		if (value === null || value === undefined || value === "") {
			cell.textContent = "—";
			return cell;
		}
		if (kind === "Text Editor") {
			cell.textContent = stripTags(value);
			cell.setAttribute("data-agenerp-degraded", "text-editor");
			return cell;
		}
		if (kind === "Attach" || kind === "Attach Image") {
			if (!isSafeUrl(value)) {
				// 白名单之外**不产出可点击元素**，且说清为什么。
				cell.textContent = String(value);
				cell.setAttribute("data-agenerp-blocked-url", "1");
				put(cell, el("span", "agenerp-note", "（这个地址不在放行的协议里，没有做成链接）"));
				return cell;
			}
			if (kind === "Attach Image") {
				var img = el("img", "agenerp-attach-image");
				img.setAttribute("src", String(value));
				img.setAttribute("alt", fieldname);
				put(cell, img);
			} else {
				var a = el("a", "agenerp-attach", String(value));
				a.setAttribute("href", String(value));
				a.setAttribute("rel", "noopener");
				put(cell, a);
			}
			return cell;
		}
		cell.textContent = String(value);
		return cell;
	}

	function renderTable(host, doctype, fields, rows, fieldtypes) {
		var table = put(host, el("table", "agenerp-table"));
		var head = put(put(table, el("thead")), el("tr"));
		fields.forEach(function (f) { put(head, el("th", null, f)); });
		var body = put(table, el("tbody"));
		if (!rows.length) {
			var empty = put(put(body, el("tr")), el("td", "agenerp-empty", "没有数据"));
			empty.setAttribute("colspan", String(fields.length || 1));
			return table;
		}
		rows.forEach(function (row) {
			var tr = put(body, el("tr"));
			fields.forEach(function (f) { put(tr, renderValueCell(row, doctype, f, fieldtypes)); });
		});
		return table;
	}

	function renderFallback(host, fb) {
		// 约束 3：明说画不了、说清为什么、给一个跳去 Desk 的入口。
		var box = put(host, el("section", "agenerp-fallback"));
		box.setAttribute("data-agenerp-fallback", String(fb.index));
		put(box, el("h3", null, "这一块这一版画不了"));
		put(box, el("p", "agenerp-reason", fb.reason));
		if (fb.doctype) { put(box, deskLink(fb.doctype)); }
		return box;
	}

	function renderDegradedNote(host, note) {
		var p = put(host, el("p", "agenerp-degraded", note.reason));
		p.setAttribute("data-agenerp-degraded-field", note.field);
		return p;
	}

	// ---- 主流程 ----

	function fieldtypeIndex(plan) {
		// 渲染器需要知道每个字段的类型才能决定「剥标签」还是「当图片」。
		// 计划里没带类型时**一律按纯文本处理** —— 不猜，且纯文本是最保守的那一档。
		return plan.fieldtypes || {};
	}

	function renderBlock(host, block, fieldtypes) {
		var section = put(host, el("section", "agenerp-block"));
		section.setAttribute("data-agenerp-block-type", block.type);
		if (block.title) { put(section, el("h2", null, block.title)); }

		if (block.type === "explain") {
			// v0 只渲染壳与问题本身，不发真请求（plan §11：接真模型要先量成本）。
			put(section, el("p", "agenerp-explain-question", block.question));
			put(section, el("p", "agenerp-note", "解释还没接上，这一版只显示问题本身。"));
			return Promise.resolve(section);
		}

		return getJSON(resourceUrl(block)).then(function (res) {
			if (res.status !== 200) { renderDenied(section, res.status); return section; }
			var rows = (res.body && res.body.data) || [];
			if (block.type === "metric") {
				var total = 0;
				var f = block.fields[0];
				rows.forEach(function (r) { total += Number(r[f]) || 0; });
				put(section, el("p", "agenerp-metric-value",
					block.agg === "count" ? String(rows.length) : String(total)));
				return section;
			}
			if (block.type !== "detail" || !(block.childFields || []).length) {
				renderTable(section, block.doctype, block.fields, rows, fieldtypes);
				return section;
			}
			// ⚠️ **detail 块必须走单据详情接口，不能用列表响应。**
			// Frappe 的列表接口（/api/resource/<DocType>?fields=…）**从不返回子表** ——
			// 拿列表行去展开子表，画出来的永远是「没有数据」。
			// 这不是推断：P2.2 的活体判据实测撞出来的（工人读得到 Item，表却是空的）。
			return renderDetail(section, block, rows, fieldtypes);
		});
	}

	function renderDetail(section, block, rows, fieldtypes) {
		var first = rows[0];
		if (!first || !first.name) {
			renderTable(section, block.doctype, block.fields, [], fieldtypes);
			return Promise.resolve(section);
		}
		var url = RESOURCE_PATH + "/" + encodeURIComponent(block.doctype)
			+ "/" + encodeURIComponent(first.name);
		return getJSON(url).then(function (res) {
			if (res.status !== 200) { renderDenied(section, res.status); return section; }
			var doc = (res.body && res.body.data) || {};
			renderTable(section, block.doctype, block.fields, [doc], fieldtypes);
			(block.childFields || []).forEach(function (child) {
				put(section, el("h3", null, child.tableField));
				renderTable(section, child.doctype, child.fields,
					doc[child.tableField] || [], fieldtypes);
			});
			return section;
		});
	}

	function render(viewName, host) {
		host.textContent = "";
		return getJSON(VIEW_PLAN_PATH + "?name=" + encodeURIComponent(viewName))
			.then(function (res) {
				if (res.status !== 200) {
					put(host, el("p", "agenerp-error",
						"打不开这个视图（HTTP " + res.status + "）："
						+ ((res.body && res.body.error) || "")));
					return host;
				}
				var plan = res.body;
				put(host, el("h1", null, plan.title || plan.view));
				var fieldtypes = fieldtypeIndex(plan);
				(plan.degraded || []).forEach(function (n) { renderDegradedNote(host, n); });
				(plan.fallbacks || []).forEach(function (fb) { renderFallback(host, fb); });
				return (plan.blocks || []).reduce(function (chain, block) {
					return chain.then(function () { return renderBlock(host, block, fieldtypes); });
				}, Promise.resolve()).then(function () {
					host.setAttribute("data-agenerp-rendered", plan.view);
					return host;
				});
			});
	}

	function mount(viewName) {
		var host = document.getElementById(ROOT_ID);
		if (!host) { host = put(document.body, el("div", "agenerp-view")); host.id = ROOT_ID; }
		return render(viewName, host);
	}

	// 判据要能直接驱动它，所以挂一个**只读的**入口。
	try {
		Object.defineProperty(window, "agenerpRenderView", {
			value: mount, writable: false, configurable: false, enumerable: true,
		});
	} catch (err) { /* 已挂过：同上，不抢 */ }
})();
