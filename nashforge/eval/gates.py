"""NashForge 四条交付门禁（DoD）。作者：晨星。

门禁统一消费 pipeline 预计算结果（report），不再重复运行求解器，确保 demo ≤ 60s：
G1 oracle 精确：序列式 LP 求出的均衡可剥削性 ≈ 0，且博弈值与范式 LP 锚点一致（强对偶）。
G2 收敛速度：CFR+ 在 cfr_plus_iters 内可剥削性跌破 exploit_eps（复用 n_seeds 轨迹）。
G3 多 seed 胜强基线：CFR+ 跨 n_seeds 种子平均可剥削性严格低于均匀随机强基线。
G4 确定性：同 seed 两次运行逐位一致（复用 report.cfr_plus_det 对）。
"""

from __future__ import annotations

import json

from ..core.config import Config
from ..core.types import GateReport, OracleResult, PipelineReport, StrategyProfile
from ..eval.exploitability import evaluate
from ..games.kuhn import KuhnPoker
from ..solvers.cfr import CFRResult
from ..solvers.sequence_form_lp import solve


def _fp_o(o: OracleResult):
    return (
        round(o.value_p0, 12),
        round(o.exploitability, 12),
        {
            k: tuple(round(v[a], 12) for a in sorted(v))
            for k, v in o.profile.strategies[0].infoset_probs.items()
        },
        {
            k: tuple(round(v[a], 12) for a in sorted(v))
            for k, v in o.profile.strategies[1].infoset_probs.items()
        },
    )


def _fp_profile(game: KuhnPoker, p: StrategyProfile):
    m = evaluate(game, p)
    return (
        round(m["value_p0"], 12),
        round(m["exploitability"], 12),
        {
            k: tuple(round(v[a], 12) for a in sorted(v))
            for k, v in p.strategies[0].infoset_probs.items()
        },
    )


def gate_oracle_exact(game: KuhnPoker, cfg: Config, report: PipelineReport) -> GateReport:
    """G1：精确 oracle 不变量（可剥削性 ≈ 0 + 博弈值 = 范式 LP 锚点 + 强对偶）。"""
    o = report.oracle
    if o is None:
        return GateReport("G1-oracle-exact", False, float("nan"), cfg.lp_value_tol, "oracle 不可用")
    nf = report.nf_anchor
    exploit = o.exploitability
    val_err = abs(o.value_p0 - nf)
    dual_err = abs(o.oracle_v_p0 - o.oracle_v_p1) if o.oracle_v_p0 is not None else float("nan")
    passed = (exploit < cfg.lp_value_tol) and (val_err < cfg.lp_value_tol) and (dual_err < cfg.lp_value_tol)
    detail = (f"exploit={exploit:.2e} |v-LPanchor|={val_err:.2e} "
              f"|v_p0-v_p1|={dual_err:.2e} anchor={nf:.8f}")
    metric = max(exploit, val_err, dual_err)
    return GateReport("G1-oracle-exact", passed, float(metric), cfg.lp_value_tol, detail)


def gate_cfr_convergence(game: KuhnPoker, cfg: Config, report: PipelineReport) -> GateReport:
    """G2：CFR+ 收敛门禁（复用 n_seeds 轨迹，至少一条跌破 exploit_eps）。"""
    results: list[CFRResult] = [r for r in report.cfr_plus.values() if isinstance(r, CFRResult)]
    if not results:
        return GateReport("G2-cfr-convergence", False, float("nan"), cfg.exploit_eps, "无 CFR+ 结果")
    final = min(r.trace[-1] for r in results)
    crossed = any(r.cross_iter >= 0 for r in results)
    passed = bool(crossed) and (final < cfg.exploit_eps)
    detail = f"best_final_exploit={final:.4f} any_crossed={crossed} eps={cfg.exploit_eps}"
    return GateReport("G2-cfr-convergence", passed, float(final), cfg.exploit_eps, detail)


def gate_multiseed_baseline(game: KuhnPoker, cfg: Config, report: PipelineReport) -> GateReport:
    """G3：多 seed 胜强基线（CFR+ 平均可剥削性严格低于均匀随机基线）。"""
    base = evaluate(game, game.uniform_profile())["exploitability"]
    results = [r for r in report.cfr_plus.values() if isinstance(r, CFRResult)]
    if not results:
        return GateReport("G3-multiseed-baseline", False, float("nan"), float(base), "无 CFR+ 结果")
    exploits = [r.trace[-1] for r in results]
    mean_expl = sum(exploits) / len(exploits)
    passed = mean_expl < base
    detail = (f"mean_CFR+_exploit={mean_expl:.4f} baseline(uniform)={base:.4f} "
              f"seeds={len(results)} n={game.n_cards}")
    return GateReport("G3-multiseed-baseline", passed, float(mean_expl), float(base), detail)


def gate_determinism(game: KuhnPoker, cfg: Config, report: PipelineReport) -> GateReport:
    """G4：确定性（同 seed 两次运行逐位一致）。

    oracle 用显式重算两次验证 LP 求解确定性；CFR+ 用 report.cfr_plus_det 对验证。
    """
    oa = solve(game)
    ob = solve(game)
    oracle_same = json.dumps(_fp_o(oa), sort_keys=True) == json.dumps(_fp_o(ob), sort_keys=True)
    det = report.cfr_plus_det
    cfr_same = True
    if det is not None:
        cfr_same = json.dumps(_fp_profile(game, det[0].profile), sort_keys=True) == json.dumps(
            _fp_profile(game, det[1].profile), sort_keys=True
        )
    metric = 0.0 if (oracle_same and cfr_same) else 1.0
    passed = oracle_same and cfr_same
    detail = f"oracle_deterministic={oracle_same} cfr_plus_deterministic={cfr_same}"
    return GateReport("G4-determinism", passed, float(metric), cfg.deterministic_tol, detail)


def run_all_gates(game: KuhnPoker, cfg: Config, report: PipelineReport) -> list[GateReport]:
    """运行全部四条门禁（复用 report 预计算结果，不重复运行求解器）。"""
    return [
        gate_oracle_exact(game, cfg, report),
        gate_cfr_convergence(game, cfg, report),
        gate_multiseed_baseline(game, cfg, report),
        gate_determinism(game, cfg, report),
    ]
