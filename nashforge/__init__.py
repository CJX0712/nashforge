"""NashForge：不完美信息博弈精确均衡求解。作者：晨星。

提供不完美信息二人零和扩展式博弈（Kuhn poker）的：
  * 序列式线性规划（sequence-form LP）精确 oracle —— Koller-Megiddo-von Stengel 1996，
    强对偶配对，可剥削性 = 0，博弈值经范式 LP 独立交叉验证；
  * CFR / CFR+ 近似求解器（纯 numpy，离线兜底）；
  * 四条交付门禁（oracle 精确 / 收敛速度 / 多 seed 胜基线 / 确定性）。

单向无环调用：cli -> pipeline -> {games, solvers, eval} -> core。
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "晨星"

from .core.config import Config
from .eval import run_all_gates
from .games.kuhn import KuhnPoker
from .pipeline import run_pipeline
from .solvers.cfr import CFRResult, run_cfr
from .solvers.cfr_plus import CFRPlus
from .solvers.cfr_plus import run as run_cfr_plus
from .solvers.sequence_form_lp import OracleResult, available, solve

__all__ = [
    "Config",
    "KuhnPoker",
    "run_cfr",
    "CFRResult",
    "CFRPlus",
    "run_cfr_plus",
    "OracleResult",
    "available",
    "solve",
    "run_all_gates",
    "run_pipeline",
    "__version__",
    "__author__",
]
