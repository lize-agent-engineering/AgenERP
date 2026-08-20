"""AgenERP —— Agent 驱动的 ERP 应用层（长在 Frappe / ERPNext 之上）。

本模块只声明包，不做任何导入副作用：`import agenerp` 不应拖起子模块，
以免门禁测试的红因被无关的 import 错误污染。
"""

__all__ = ["__version__"]

__version__ = "0.0.0"
