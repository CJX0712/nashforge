"""CFR / CFR+ 近似求解器单测。作者：晨星。

不变量：
  * 确定性（G4）：同 seed 两次运行逐位一致；
  * 收敛性（G2 前置）：CFR+ 可剥削性随迭代单调趋势下降并最终 < 0.1；
  * 基线（G3）：CFR+ 收敛后平均可剥削性显著低于均匀随机强基线（n=3 时 ≈ 0.75）。
"""

from __future__ import annotations

from nashforge.eval.exploitability import evaluate
from nashforge.games.kuhn import KuhnPoker
from nashforge.solvers.cfr import run_cfr
from nashforge.solvers.cfr_plus import run as run_cfr_plus


def test_cfr_deterministic() -> None:
    g = KuhnPoker(3)
    r1 = run_cfr(g, 800, 12345, use_cfr_plus=True)
    r2 = run_cfr(g, 800, 12345, use_cfr_plus=True)
    assert r1.profile.strategies[0].infoset_probs == r2.profile.strategies[0].infoset_probs
    assert r1.profile.strategies[1].infoset_probs == r2.profile.strategies[1].infoset_probs
    assert r1.trace[-1] == r2.trace[-1]


def test_cfr_converges() -> None:
    g = KuhnPoker(3)
    r = run_cfr(g, 6000, 7, use_cfr_plus=True, exploit_eps=1e-2)
    assert r.trace[-1] < r.trace[0]  # 整体下降
    assert r.trace[-1] < 0.1  # 已接近收敛


def test_uniform_baseline_exploitability() -> None:
    g = KuhnPoker(3)
    m = evaluate(g, g.uniform_profile())
    # 均匀随机策略可剥削性高（≈0.75），作为强基线
    assert m["exploitability"] > 0.5


def test_cfr_plus_beats_uniform() -> None:
    g = KuhnPoker(3)
    base = evaluate(g, g.uniform_profile())["exploitability"]
    r = run_cfr_plus(g, 8000, 99, exploit_eps=1e-2)
    prof_expl = evaluate(g, r.profile)["exploitability"]
    assert prof_expl < base
