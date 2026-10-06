"""序列式 LP oracle 正确性单测。作者：晨星。

不变量（G1）：
  * 任意 n（2..5）oracle 求出的均衡可剥削性 ≈ 0；
  * 强对偶：oracle_v_p0 == oracle_v_p1 == value_p0；
  * 博弈值 = 范式 LP 锚点 normal_form_value（独立交叉验证）；
  * n=3 精确博弈值 = −1/18（Kuhn 1950 标准结果）。
"""

from __future__ import annotations

import pytest

from nashforge.games.kuhn import KuhnPoker
from nashforge.solvers.sequence_form_lp import normal_form_value, solve

TOL = 1e-9


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_oracle_exact_for_all_n(n: int) -> None:
    g = KuhnPoker(n)
    o = solve(g)
    nf = normal_form_value(g)
    assert abs(o.exploitability) < TOL, f"n={n} exploit={o.exploitability}"
    assert abs(o.value_p0 - o.oracle_v_p0) < TOL
    assert abs(o.oracle_v_p0 - o.oracle_v_p1) < TOL  # 强对偶
    assert abs(o.value_p0 - nf) < TOL  # 与范式 LP 锚点一致


def test_normal_form_anchor_n3() -> None:
    g = KuhnPoker(3)
    # Kuhn poker n=3 标准博弈值（玩家 0 视角）= −1/18
    assert abs(normal_form_value(g) - (-1.0 / 18.0)) < 1e-12


def test_oracle_profile_is_nash() -> None:
    """oracle 给出的策略对应为 Nash 均衡：双方各自最佳响应收益相互抵消。"""
    g = KuhnPoker(3)
    o = solve(g)
    br0 = g.best_response_value(o.profile, 0)
    br1 = g.best_response_value(o.profile, 1)
    # 联合可剥削性 ≈ 0 ⟺ 两方最佳响应收益均 ≈ 0（零和对称）
    assert abs(br0 + br1) < TOL


def test_oracle_deterministic() -> None:
    """同输入两次求解逐位一致（确定性）。"""
    g = KuhnPoker(3)
    o1 = solve(g)
    o2 = solve(g)
    assert o1.value_p0 == o2.value_p0
    assert o1.exploitability == o2.exploitability
    for p in (0, 1):
        assert o1.profile.strategies[p].infoset_probs == o2.profile.strategies[p].infoset_probs
