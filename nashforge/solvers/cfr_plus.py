"""CFR+ 旗舰求解器封装（实现 Solver 接口）。作者：晨星。"""

from __future__ import annotations

from ..core.interfaces import Game, Solver
from ..games.kuhn import KuhnPoker
from .cfr import CFRResult, run_cfr


class CFRPlus(Solver):
    """CFR+（正累积遗憾 + 平均策略等权和）旗舰求解器。"""

    def __init__(self, iters: int = 2000, exploit_eps: float = 1e-2) -> None:
        self.iters = iters
        self.exploit_eps = exploit_eps

    def solve(self, game: Game, iters: int | None = None, seed: int = 0) -> object:
        if not isinstance(game, KuhnPoker):
            raise TypeError("CFRPlus 目前仅支持 KuhnPoker")
        n = iters if iters is not None else self.iters
        res: CFRResult = run_cfr(
            game, n, seed, use_cfr_plus=True, exploit_eps=self.exploit_eps
        )
        return res.profile


def run(game: KuhnPoker, iters: int, seed: int, exploit_eps: float = 1e-2) -> CFRResult:
    """便捷入口：运行 CFR+ 旗舰。"""
    return run_cfr(game, iters, seed, use_cfr_plus=True, exploit_eps=exploit_eps)
