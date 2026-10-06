"""接口契约（Protocol）。作者：晨星。

单向无环调用约定：
``cli -> pipeline -> {data, games, solvers, eval} -> core``。
各模块仅依赖本文件声明的接口与 core，不反向依赖 pipeline。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import StrategyProfile


@runtime_checkable
class Game(Protocol):
    """一个二人零和不完美信息扩展式博弈。"""

    @property
    def num_players(self) -> int: ...

    def information_sets(self, player: int): ...

    def value(self, profile: StrategyProfile) -> tuple:
        """返回 (value_to_p0, value_to_p1)，零和 ⇒ 第二项为第一项的负。"""

    def best_response_value(self, profile: StrategyProfile, br_player: int) -> float:
        """固定对手策略下，br_player 的最佳响应期望收益。"""

    def exploitability(self, profile: StrategyProfile) -> float:
        """联合策略的可剥削性（Nash 均衡处 = 0）。"""


@runtime_checkable
class Solver(Protocol):
    """一个均衡求解器。"""

    def solve(self, game, iters: int, seed: int) -> StrategyProfile: ...
