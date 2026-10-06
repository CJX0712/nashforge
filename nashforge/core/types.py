"""NashForge 核心数据类型。作者：晨星。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # 仅在类型检查时引用，避免 core.types -> solvers -> games 循环导入
    from ..solvers.cfr import CFRResult


@dataclass
class Strategy:
    """单个玩家的**行为策略**：infoset -> action -> 概率（行和=1）。"""

    player: int
    infoset_probs: dict[str, dict[str, float]] = field(default_factory=dict)

    def prob(self, infoset: str, action: str) -> float:
        """返回某信息集上某动作的概率；缺失信息集按均匀策略处理。"""
        d = self.infoset_probs.get(infoset)
        if d is None:
            return 0.0
        return float(d.get(action, 0.0))

    def items(self):
        return self.infoset_probs.items()


@dataclass
class StrategyProfile:
    """双方（或多方）策略集合。"""

    strategies: dict[int, Strategy] = field(default_factory=dict)

    def __getitem__(self, player: int) -> Strategy:
        return self.strategies[player]

    def __contains__(self, player: int) -> bool:
        return player in self.strategies


@dataclass
class OracleResult:
    """精确 oracle（序列式 LP）求解结果。"""

    value_p0: float  # 博弈值（玩家 0 视角，零和 ⇒ value_p1 = -value_p0）
    profile: StrategyProfile  # 一个 Nash 均衡策略对
    exploitability: float  # 该均衡的可剥削性（应 ≈ 0）
    solver: str = "sequence_form_lp"
    oracle_v_p0: float | None = None  # P0-LP 原始目标值（应与 value_p0 一致）
    oracle_v_p1: float | None = None  # P1-LP 原始目标值（应与 oracle_v_p0 一致，强对偶）


@dataclass
class GateReport:
    """单条门禁报告。"""

    name: str
    passed: bool
    metric: float
    threshold: float
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "passed": self.passed,
            "metric": self.metric,
            "threshold": self.threshold,
            "detail": self.detail,
        }


@dataclass
class PipelineReport:
    """pipeline 运行报告（cli / demo / CI 统一消费）。

    单向无环：cli -> pipeline -> {games, solvers, eval} -> core。
    """

    n_cards: int
    oracle: OracleResult
    nf_anchor: float
    cfr: dict[str, object] = field(default_factory=dict)  # seed -> CFRResult（朴素 CFR）
    cfr_plus: dict[str, object] = field(default_factory=dict)  # seed -> CFRResult（CFR+ 旗舰）
    cfr_plus_det: tuple[CFRResult, CFRResult] | None = None  # G4 确定性对（同 seed 两次）
    gates: list[GateReport] = field(default_factory=list)
    elapsed: float = 0.0

    def all_pass(self) -> bool:
        return all(g.passed for g in self.gates)

    def as_dict(self) -> dict[str, object]:
        return {
            "n_cards": self.n_cards,
            "oracle_value_p0": self.oracle.value_p0,
            "oracle_exploit": self.oracle.exploitability,
            "nf_anchor": self.nf_anchor,
            "gates": [g.as_dict() for g in self.gates],
            "all_pass": self.all_pass(),
            "elapsed": self.elapsed,
        }
