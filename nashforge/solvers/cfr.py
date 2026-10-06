"""反事实遗憾最小化（CFR / CFR+）。作者：晨星。

tabular chance-sampling CFR（Zinkevich et al. 2007）。每轮随机采样一手牌（chance
sampling），递归遍历博弈树，按遗憾匹配（regret matching）更新累积遗憾与平均策略。

  * 朴素 CFR：累积遗憾 R 可正可负，平均策略按 reach 概率加权。
  * CFR+（旗舰，Tammelin 2014）：累积**正**遗憾 R⁺=max(0,R⁺+Δ)，平均策略取
    各步即时策略的等权和（不乘 reach）。收敛显著更快（G2 速度门禁的被测对象）。

纯 numpy 实现，不依赖 scipy，可在 oracle 后端缺失时独立运行（离线兜底）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..core.seed import set_all
from ..games.kuhn import KuhnPoker


@dataclass
class CFRResult:
    """CFR 运行结果。"""

    profile: object  # StrategyProfile
    trace: list[float] = field(default_factory=list)  # 每轮可剥削性
    value_trace: list[float] = field(default_factory=list)  # 每轮博弈值（玩家0视角）
    cross_iter: int = -1  # 首次低于 exploit_eps 的轮次（-1=未达）

    def final_exploit(self) -> float:
        return self.trace[-1] if self.trace else float("nan")


def _sample_deal(rng: np.random.Generator, n_cards: int):
    c0 = int(rng.integers(1, n_cards + 1))
    c1 = int(rng.integers(1, n_cards + 1))
    while c1 == c0:
        c1 = int(rng.integers(1, n_cards + 1))
    return c0, c1


def _recurse(game, c0, c1, history, player, pr0, pr1, regret, strat_sum, use_cfr_plus):
    if game.is_terminal(history):
        return game.terminal_utility(c0, c1, history)
    key = game.infoset_key(player, c0, c1, history)
    acts = game.legal_actions(history)
    r = regret[player].setdefault(key, dict.fromkeys(acts, 0.0))
    pos = [max(0.0, r[a]) for a in acts]
    s = sum(pos)
    strat = [pos[i] / s for i, a in enumerate(acts)] if s > 0 else [1.0 / len(acts)] * len(acts)
    util = {}
    node_util = 0.0
    for i, a in enumerate(acts):
        if player == 0:
            u = _recurse(game, c0, c1, history + a, 1, pr0 * strat[i], pr1, regret, strat_sum, use_cfr_plus)
        else:
            u = _recurse(game, c0, c1, history + a, 0, pr0, pr1 * strat[i], regret, strat_sum, use_cfr_plus)
        util[a] = u
        node_util += strat[i] * u
    # 累积反事实遗憾
    for a in acts:
        delta = pr1 * (util[a] - node_util) if player == 0 else pr0 * (node_util - util[a])
        if use_cfr_plus:
            regret[player][key][a] = max(0.0, regret[player][key][a] + delta)
        else:
            regret[player][key][a] += delta
    # 累积平均策略
    pr_player = pr0 if player == 0 else pr1
    ss = strat_sum[player].setdefault(key, dict.fromkeys(acts, 0.0))
    for i, a in enumerate(acts):
        if use_cfr_plus:
            ss[a] += strat[i]
        else:
            ss[a] += pr_player * strat[i]
    return node_util


def _profile_from_strat_sum(game, strat_sum) -> object:
    p0: dict[str, dict[str, float]] = {}
    p1: dict[str, dict[str, float]] = {}
    for key, d in strat_sum[0].items():
        s = sum(d.values())
        p0[key] = {a: (v / s if s > 0 else 1.0 / len(d)) for a, v in d.items()}
    for key, d in strat_sum[1].items():
        s = sum(d.values())
        p1[key] = {a: (v / s if s > 0 else 1.0 / len(d)) for a, v in d.items()}
    return game.make_profile(p0, p1)


def run_cfr(
    game: KuhnPoker,
    iters: int,
    seed: int,
    use_cfr_plus: bool = False,
    exploit_eps: float = 1e-2,
    track: bool = True,
) -> CFRResult:
    """运行 CFR（或 CFR+）。

    Args:
        game: Kuhn poker 实例。
        iters: 迭代轮数。
        seed: 随机数种子（确定性）。
        use_cfr_plus: True=CFR+ 旗舰；False=朴素 CFR。
        exploit_eps: 收敛阈值（用于 cross_iter）。
        track: 是否每轮记录可剥削性曲线。
    """
    set_all(seed)  # 设齐全局种子（torch 可选）
    rng = np.random.default_rng(seed)
    regret = {0: {}, 1: {}}
    strat_sum = {0: {}, 1: {}}
    trace: list[float] = []
    value_trace: list[float] = []
    cross_iter = -1
    for t in range(iters):
        c0, c1 = _sample_deal(rng, game.n_cards)
        _recurse(game, c0, c1, "", 0, 1.0, 1.0, regret, strat_sum, use_cfr_plus)
        if track:
            prof = _profile_from_strat_sum(game, strat_sum)
            trace.append(game.exploitability(prof))
            value_trace.append(game.value(prof)[0])
            if cross_iter < 0 and trace[-1] < exploit_eps:
                cross_iter = t + 1
    profile = _profile_from_strat_sum(game, strat_sum)
    return CFRResult(profile=profile, trace=trace, value_trace=value_trace, cross_iter=cross_iter)
