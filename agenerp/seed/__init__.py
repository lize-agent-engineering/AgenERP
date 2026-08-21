"""确定性种子数据集：一条离散制造最小闭环，内置 1,010 米积压这个已知业务荒谬。

零第三方依赖、纯标准库。同 `seed` 可复现，生成路径上不读时钟、不读环境、不联网。

判据是 `python3 -m agenerp.seed --seed 42 --verify` 的退出码。
⚠️ 它**不在** `missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到它；
代偿控制是变异验证 + 独立关闭审计（`docs/architecture/module-boundaries.md` §12.7）。

结构边界、数值对账与取舍见 `docs/architecture/module-boundaries.md` §12。
"""

from agenerp.seed.checks import verify
from agenerp.seed.dataset import generate
from agenerp.seed.model import SCOPE, Dataset
from agenerp.seed.store import read, to_snapshot, write

__all__ = ["SCOPE", "Dataset", "generate", "read", "to_snapshot", "verify", "write"]
