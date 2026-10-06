"""Kuhn poker：二人零和不完美信息扩展式博弈。

规则（标准 Kuhn 1950，n 张牌泛化）：
  - 每玩家 ante 1，底池 2；各发 1 张不重复牌（点数 1..n）。
  - 玩家 0（小盲 SB）先动：check(c) / bet(b)。
      * 若 P0 check：P1 check(c)->摊牌(±1)；P1 bet(b)->P0 二次动 call(c)/fold(f)。
          - P0 call -> 摊牌(±2)；P0 fold -> P0 输 ante(−1)。
      * 若 P0 bet：P1 call(c)->摊牌(±2)；P1 fold(f)->P1 输 ante，P0 赢(+1)。
  - 摊牌收益（玩家 0 视角）：牌大者 +stake，牌小者 −stake（stake=1 单次下注，=2 跟注后）。

信息集（共 12，n=3）：
  P0：首动 (card) 3 个；二次动 (card) 3 个。
  P1：P0 check 后 (card) 3 个；P0 bet 后 (card) 3 个。

博弈值（n=3）：玩家 0 视角 = −1/18（玩家 1 = +1/18），由序列式 LP 精确求得。
作者：晨星。
"""

from __future__ import annotations

import math
from collections.abc import Iterator

from ..core.errors import GameError
from ..core.types import Strategy, StrategyProfile

_TERMINALS = ("cc", "cbc", "cbf", "bc", "bf")
_SHOWDOWN_SINGLE = {"cc"}
_SHOWDOWN_DOUBLE = {"cbc", "bc"}


class KuhnPoker:
    """Kuhn poker 博弈模型。"""

    def __init__(self, n_cards: int = 3) -> None:
        if n_cards < 2:
            raise GameError("n_cards 必须 >= 2")
        self.n_cards = n_cards
        self.num_players = 2

    # ---- 基础拓扑 -------------------------------------------------------
    @staticmethod
    def is_terminal(history: str) -> bool:
        return history in _TERMINALS

    @staticmethod
    def current_player(history: str) -> int:
        """返回当前行动玩家；终局返回 −1。"""
        if history in _TERMINALS:
            return -1
        if history in ("", "cb"):
            return 0
        return 1  # "c", "b"

    @staticmethod
    def legal_actions(history: str) -> list[str]:
        if history == "":
            return ["c", "b"]
        if history == "c":
            return ["c", "b"]
        if history == "cb":
            return ["c", "f"]
        if history == "b":
            return ["c", "f"]
        return []

    def terminal_utility(self, c0: int, c1: int, history: str) -> float:
        """玩家 0 视角的终局净收益。"""
        if history == "cc":
            return 1.0 if c0 > c1 else -1.0
        if history in _SHOWDOWN_DOUBLE:
            return 2.0 if c0 > c1 else -2.0
        if history == "cbf":
            return -1.0  # P0 在 P1 bet 后弃牌
        if history == "bf":
            return 1.0  # P1 在 P0 bet 后弃牌
        raise GameError(f"非终局历史 {history!r}")

    def infoset_key(self, player: int, c0: int, c1: int, history: str) -> str:
        """返回当前节点的信息集标识（含该玩家可见的私有信息）。"""
        if player == 0:
            if history == "":
                return f"P0:{c0}"
            if history == "cb":
                return f"P0b:{c0}"
            raise GameError(f"非法 P0 节点 history={history!r}")
        else:
            if history == "c":
                return f"P1:{c1}:P0c"
            if history == "b":
                return f"P1:{c1}:P0b"
            raise GameError(f"非法 P1 节点 history={history!r}")

    # ---- 信息集枚举 -----------------------------------------------------
    def p0_infosets(self) -> list[str]:
        keys = [f"P0:{c}" for c in range(1, self.n_cards + 1)]
        keys += [f"P0b:{c}" for c in range(1, self.n_cards + 1)]
        return keys

    def p1_infosets(self) -> list[str]:
        keys = [f"P1:{c}:P0c" for c in range(1, self.n_cards + 1)]
        keys += [f"P1:{c}:P0b" for c in range(1, self.n_cards + 1)]
        return keys

    def information_sets(self, player: int) -> list[str]:
        return self.p0_infosets() if player == 0 else self.p1_infosets()

    @staticmethod
    def actions_for_infoset(key: str) -> list[str]:
        """二次动（P0b:*）与 P1 在 P0 下注后应叫用 c/f；其余（首动 / P1 在 P0 check 后）用 c/b。"""
        if key.startswith("P0b:") or ":P0b" in key:
            return ["c", "f"]
        return ["c", "b"]

    def deals(self) -> Iterator[tuple[int, int]]:
        for c0 in range(1, self.n_cards + 1):
            for c1 in range(1, self.n_cards + 1):
                if c0 != c1:
                    yield c0, c1

    def deal_prob(self) -> float:
        n = self.n_cards
        return 1.0 / (n * (n - 1))

    def all_pure_strategies(self, player: int) -> list[dict[str, str]]:
        """枚举该玩家所有纯行为策略（每个信息集各指定一个动作）。"""
        keys = self.p0_infosets() if player == 0 else self.p1_infosets()
        acts_per = [self.actions_for_infoset(k) for k in keys]
        results: list[dict[str, str]] = [{}]
        for k, acts in zip(keys, acts_per, strict=True):
            new_results: list[dict[str, str]] = []
            for combo in results:
                for a in acts:
                    nc = dict(combo)
                    nc[k] = a
                    new_results.append(nc)
            results = new_results
        return results

    # ---- 期望值 / 最佳响应 / 可剥削性 -----------------------------------
    def _uniform(self, history: str) -> dict[str, float]:
        acts = self.legal_actions(history)
        p = 1.0 / len(acts)
        return dict.fromkeys(acts, p)

    def _value(self, c0: int, c1: int, history: str, player: int, profile: StrategyProfile) -> float:
        if self.is_terminal(history):
            return self.terminal_utility(c0, c1, history)
        key = self.infoset_key(player, c0, c1, history)
        strat = profile.strategies[player].infoset_probs.get(key, self._uniform(history))
        node = 0.0
        for a in self.legal_actions(history):
            node += strat.get(a, 0.0) * self._value(c0, c1, history + a, 1 - player, profile)
        return node

    def value(self, profile: StrategyProfile) -> tuple[float, float]:
        """返回 (value_to_p0, value_to_p1)。零和 ⇒ 第二项为第一项取负。"""
        nd_inv = self.deal_prob()
        v0 = 0.0
        for c0, c1 in self.deals():
            v0 += self._value(c0, c1, "", 0, profile) * nd_inv
        return v0, -v0

    def _br(self, c0: int, c1: int, history: str, player: int, profile: StrategyProfile, br_player: int) -> float:
        if self.is_terminal(history):
            u0 = self.terminal_utility(c0, c1, history)
            return u0 if br_player == 0 else -u0
        key = self.infoset_key(player, c0, c1, history)
        acts = self.legal_actions(history)
        if player == br_player:
            best = -math.inf
            for a in acts:
                v = self._br(c0, c1, history + a, 1 - player, profile, br_player)
                if v > best:
                    best = v
            return best
        strat = profile.strategies[player].infoset_probs.get(key, self._uniform(history))
        node = 0.0
        for a in acts:
            node += strat.get(a, 0.0) * self._br(c0, c1, history + a, 1 - player, profile, br_player)
        return node

    def best_response_value(self, profile: StrategyProfile, br_player: int) -> float:
        """固定对手策略下，br_player 的最佳响应期望收益（per-infoset 行为 BR 的真实值）。

        注意：最佳响应须按「对手到达该信息集的概率」在信息集层面统一取最大动作——
        同一信息集在不同牌局中不可选不同动作。故复用 best_response_strategy 构造的
        确定性策略并对其求博弈值，等价于全局最大（Kuhn 定理，完美回忆博弈）。
        """
        br = self.best_response_strategy(profile, br_player)
        if br_player == 0:
            opp = {k: dict(v.items()) for k, v in profile.strategies[1].infoset_probs.items()}
            return self.value(self.make_profile(br.infoset_probs, opp))[0]
        opp = {k: dict(v.items()) for k, v in profile.strategies[0].infoset_probs.items()}
        return -self.value(self.make_profile(opp, br.infoset_probs))[0]

    def exploitability(self, profile: StrategyProfile) -> float:
        """联合策略可剥削性 = BR0 + BR1（Nash 处 = 0）。"""
        return self.best_response_value(profile, 0) + self.best_response_value(profile, 1)

    # ---- 最佳响应策略（per-infoset 纯策略，oracle 恢复用）-----------------
    def best_response_strategy(self, profile: StrategyProfile, br_player: int) -> Strategy:
        """返回 br_player 对 profile 的（per-infoset）最佳响应纯策略。

        在每个信息集处，按「对手到达该信息集的概率」加权，选取期望收益最大的动作。
        与对手的全局最优策略配对即构成一个 Nash 均衡（可剥削性 ≈ 0）。
        """
        from collections import defaultdict

        acc = defaultdict(lambda: defaultdict(float))  # infoset -> action -> Σ(value·reach)
        reach_acc = defaultdict(float)  # infoset -> Σ reach

        def rec(c0, c1, history, player, reach):
            if self.is_terminal(history):
                u0 = self.terminal_utility(c0, c1, history)
                return u0 if br_player == 0 else -u0
            p = self.current_player(history)
            if p == br_player:
                key = self.infoset_key(br_player, c0, c1, history)
                for a in self.legal_actions(history):
                    val = rec(c0, c1, history + a, 1 - p, reach)
                    acc[key][a] += val * reach
                    reach_acc[key] += reach
                return 0.0  # 不向上聚合单值
            strat = profile.strategies[p].infoset_probs.get(
                self.infoset_key(p, c0, c1, history), self._uniform(history)
            )
            node = 0.0
            for a in self.legal_actions(history):
                node += strat.get(a, 0.0) * rec(c0, c1, history + a, 1 - p, reach * strat.get(a, 0.0))
            return node

        for c0, c1 in self.deals():
            rec(c0, c1, "", 0, 1.0)

        # 仅构造 br_player 的确定性策略（Strategy），不返回整份 profile。
        infoset_best: dict[str, str] = {}
        for key, ad in acc.items():
            infoset_best[key] = max(ad, key=lambda a: ad[a])
        probs: dict[str, dict[str, float]] = {}
        for k in self.information_sets(br_player):
            a = infoset_best.get(k, self.actions_for_infoset(k)[0])
            probs[k] = {x: (1.0 if x == a else 0.0) for x in self.actions_for_infoset(k)}
        return Strategy(br_player, self._normalize(probs))

    # ---- 策略构造辅助 ---------------------------------------------------
    @staticmethod
    def _normalize(infoset_probs: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for k, d in infoset_probs.items():
            s = sum(d.values())
            if s <= 0:
                out[k] = {a: 1.0 / len(d) for a in d}
            else:
                out[k] = {a: v / s for a, v in d.items()}
        return out

    def make_profile(
        self,
        p0: dict[str, dict[str, float]],
        p1: dict[str, dict[str, float]],
    ) -> StrategyProfile:
        """由 infoset->action->prob 字典构造（并归一化）StrategyProfile。"""
        return StrategyProfile(
            strategies={
                0: Strategy(0, self._normalize(p0)),
                1: Strategy(1, self._normalize(p1)),
            }
        )

    def uniform_profile(self) -> StrategyProfile:
        """双方均匀随机策略（离线兜底基线）。"""
        p0 = {k: dict.fromkeys(self.actions_for_infoset(k), 1.0) for k in self.p0_infosets()}
        p1 = {k: dict.fromkeys(self.actions_for_infoset(k), 1.0) for k in self.p1_infosets()}
        # 归一化后各动作等概
        return self.make_profile(p0, p1)

    def fixed_profile(self, policy: dict[str, str]) -> StrategyProfile:
        """由 infoset->action 字典构造确定性策略；未指定信息集按均匀处理。"""
        p0: dict[str, dict[str, float]] = {}
        p1: dict[str, dict[str, float]] = {}
        for k in self.p0_infosets():
            a = policy.get(k, self.actions_for_infoset(k)[0])
            p0[k] = {x: (1.0 if x == a else 0.0) for x in self.actions_for_infoset(k)}
        for k in self.p1_infosets():
            a = policy.get(k, self.actions_for_infoset(k)[0])
            p1[k] = {x: (1.0 if x == a else 0.0) for x in self.actions_for_infoset(k)}
        return self.make_profile(p0, p1)

    # ---- LP 行走生成器（供 solvers/sequence_form_lp.py 构建矩阵）--------
    def walk_p0_fixed(self, s0: dict[str, str], c0: int, c1: int, history: str = ""):
        """固定 P0 纯策略 s0，枚举每个 P1 决策点及其动作，yield (cont_value, (p1_key, p1_action))。

        cont_value = 在该 P1 动作之后，P0 按 s0 确定性行动抵达终局的期望收益（玩家 0 视角）。
        Kuhn poker 每个路径恰有一个 P1 决策，该决策之后仅余 P0 二次行动与终局；故 cont_value
        即为该 P1 动作的精确 LP 系数——按 P0 纯策略对后续分支加权，不再把多个终局收益直接相加。
        """
        player = self.current_player(history)
        if player == 0:
            a = s0[self.infoset_key(0, c0, c1, history)]
            yield from self.walk_p0_fixed(s0, c0, c1, history + a)
        elif player == 1:
            key = self.infoset_key(1, c0, c1, history)
            for a in self.legal_actions(history):
                cont = self._expected_after_p1(s0, c0, c1, history + a)
                yield (cont, (key, a))
        # player == -1（终局）：P0 节点在抵达 P1 前不会直接终局，无需产出

    def _expected_after_p1(self, s0: dict[str, str], c0: int, c1: int, history: str) -> float:
        """P1 已行动一步后的期望收益：此后仅 P0 按 s0 行动（Kuhn 无更多 P1 决策）。"""
        if self.is_terminal(history):
            return self.terminal_utility(c0, c1, history)
        a = s0[self.infoset_key(0, c0, c1, history)]
        return self._expected_after_p1(s0, c0, c1, history + a)

    def walk_p1_fixed(self, s1: dict[str, str], c0: int, c1: int, history: str = ""):
        """固定 P1 纯策略 s1，枚举每个 P0 决策点及其动作，yield (cont_value, (p0_key, p0_action))。

        cont_value = 在该 P0 动作之后，P1 按 s1 确定性行动抵达终局的期望收益（玩家 0 视角）。
        Kuhn poker 每个路径恰有一个 P0 首动、至多一个 P0 二次动；该动作之后仅余 P1 行动与终局，
        故 cont_value 即该 P0 动作的精确 LP 系数（按 P1 纯策略对后续分支加权）。用于构造 P0-LP。
        """
        player = self.current_player(history)
        if player == 1:
            a = s1[self.infoset_key(1, c0, c1, history)]
            yield from self.walk_p1_fixed(s1, c0, c1, history + a)
        elif player == 0:
            key = self.infoset_key(0, c0, c1, history)
            for a in self.legal_actions(history):
                cont = self._expected_after_p0(s1, c0, c1, history + a)
                yield (cont, (key, a))
        # player == -1（终局）：P1 节点在抵达 P0 决策前不会直接终局，无需产出

    def _expected_after_p0(self, s1: dict[str, str], c0: int, c1: int, history: str) -> float:
        """P0 已行动一步后的期望收益：此后仅 P1 按 s1 行动（Kuhn 无更多 P0 决策）。"""
        if self.is_terminal(history):
            return self.terminal_utility(c0, c1, history)
        a = s1[self.infoset_key(1, c0, c1, history)]
        return self._expected_after_p0(s1, c0, c1, history + a)
