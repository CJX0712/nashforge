"""端到端 pipeline：构造博弈 → 精确 oracle → 近似求解器（多 seed）→ 四条门禁。

设计要点（单向无环）：
    cli -> pipeline -> {games, solvers, eval} -> core
pipeline 不反向依赖 cli，可独立调用与测试。

输出 PipelineReport 含：oracle 结果、CFR/CFR+ 多 seed 收敛轨迹、四条门禁、
耗时与可读性摘要，供 cli / demo / CI 统一消费。
"""

from __future__ import annotations

import time

from ..core.config import Config
from ..core.types import PipelineReport
from ..eval.gates import run_all_gates
from ..games.kuhn import KuhnPoker
from ..solvers import CFRResult, available, normal_form_value, run_cfr, run_cfr_plus, solve


def run_pipeline(game: KuhnPoker, cfg: Config) -> PipelineReport:
    """运行端到端 pipeline。

    Args:
        game: Kuhn poker 实例（默认 n_cards=3）。
        cfg: 运行配置（种子、迭代次数、阈值等）。

    Returns:
        PipelineReport：含 oracle 精确解、CFR/CFR+ 多 seed 轨迹、四条门禁与耗时。
    """
    t0 = time.perf_counter()
    oracle = solve(game) if available() else None
    nf_anchor = normal_form_value(game) if available() else game.value(game.uniform_profile())[0]

    cfr_results: dict[str, CFRResult] = {}
    cfr_plus_results: dict[str, CFRResult] = {}
    seeds = [cfg.seed + s for s in range(cfg.n_seeds)]
    for s in seeds:
        cfr_results[str(s)] = run_cfr(game, cfg.cfr_iters, s, use_cfr_plus=False, exploit_eps=cfg.exploit_eps)
        cfr_plus_results[str(s)] = run_cfr_plus(game, cfg.cfr_plus_iters, s, exploit_eps=cfg.exploit_eps)

    # G4 确定性对：同 seed 两次 CFR+ 运行逐位一致（独立轻量轨迹，不计入收敛预算）。
    det_a = run_cfr_plus(game, cfg.cfr_det_iters, cfg.seed, exploit_eps=cfg.exploit_eps)
    det_b = run_cfr_plus(game, cfg.cfr_det_iters, cfg.seed, exploit_eps=cfg.exploit_eps)

    report = PipelineReport(
        n_cards=game.n_cards,
        oracle=oracle,
        nf_anchor=nf_anchor,
        cfr=cfr_results,
        cfr_plus=cfr_plus_results,
        cfr_plus_det=(det_a, det_b),
        elapsed=0.0,
    )
    report.gates = run_all_gates(game, cfg, report)
    report.elapsed = time.perf_counter() - t0
    return report


def render(report: PipelineReport) -> str:
    """生成人类可读的 pipeline 摘要（用于 demo / CLI 输出）。"""
    lines: list[str] = []
    lines.append("=" * 64)
    lines.append(f"NashForge pipeline 报告（n_cards={report.n_cards}）")
    lines.append("=" * 64)
    if report.oracle is not None:
        o = report.oracle
        lines.append(f"[oracle] value_p0 = {o.value_p0:.8f}  exploit = {o.exploitability:.2e}")
        lines.append(f"[oracle] LP v_p0 = {o.oracle_v_p0}  LP v_p1 = {o.oracle_v_p1}  (强对偶)")
        lines.append(f"[anchor] normal-form LP value = {report.nf_anchor:.8f}")
    lines.append("-" * 64)
    lines.append("四条交付门禁：")
    for g in report.gates:
        mark = "✅ PASS" if g.passed else "❌ FAIL"
        lines.append(f"  {g.name:24} {mark}  metric={g.metric:.4f}  {g.detail}")
    lines.append("-" * 64)
    lines.append(f"总耗时：{report.elapsed:.3f}s  结论：{'ALL GREEN ✅' if report.all_pass() else 'RED ❌'}")
    lines.append("=" * 64)
    return "\n".join(lines)
