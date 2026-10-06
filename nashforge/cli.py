"""NashForge 命令行入口。作者：晨星。

用法：
    python -m nashforge.cli demo [--n-cards 3] [--seed 20261006]
    python -m nashforge.cli gates
    python -m nashforge.cli solve
    python -m nashforge.cli profile

单向无环：cli -> pipeline -> {games, solvers, eval} -> core。
"""

from __future__ import annotations

import argparse
import sys

from .core.config import Config
from .games.kuhn import KuhnPoker
from .pipeline.pipeline import render, run_pipeline
from .solvers import available, normal_form_value, solve


def _build_game(args) -> KuhnPoker:
    return KuhnPoker(n_cards=args.n_cards)


def cmd_demo(args) -> int:
    cfg = Config.from_env()
    cfg.seed = args.seed
    cfg.n_seeds = args.n_seeds
    cfg.cfr_iters = args.cfr_iters
    cfg.cfr_plus_iters = args.cfr_plus_iters
    game = _build_game(args)
    report = run_pipeline(game, cfg)
    print(render(report))
    return 0 if report.all_pass() else 1


def cmd_gates(args) -> int:
    cfg = Config.from_env()
    cfg.seed = args.seed
    cfg.n_seeds = args.n_seeds
    cfg.cfr_iters = args.cfr_iters
    cfg.cfr_plus_iters = args.cfr_plus_iters
    cfg.exploit_eps = args.exploit_eps
    game = _build_game(args)
    report = run_pipeline(game, cfg)
    ok = report.all_pass()
    for g in report.gates:
        mark = "PASS" if g.passed else "FAIL"
        print(f"[{mark}] {g.name}: metric={g.metric:.6f} (thr={g.threshold}) {g.detail}")
    print(f"[gates] wall={report.elapsed:.3f}s")
    print("ALL GREEN" if ok else "RED")
    return 0 if ok else 1


def cmd_solve(args) -> int:
    if not available():
        print("ERROR: scipy 不可用，无法运行序列式 LP oracle", file=sys.stderr)
        return 2
    game = _build_game(args)
    o = solve(game)
    nf = normal_form_value(game)
    print(f"n_cards            = {game.n_cards}")
    print(f"oracle value_p0   = {o.value_p0}")
    print(f"oracle v_p0 / v_p1 = {o.oracle_v_p0} / {o.oracle_v_p1}  (强对偶)")
    print(f"normal-form anchor = {nf}")
    print(f"exploitability     = {o.exploitability}")
    print("均衡策略（玩家 0）：")
    for k, v in o.profile.strategies[0].infoset_probs.items():
        print(f"  {k}: { {a: round(x, 4) for a, x in v.items()} }")
    print("均衡策略（玩家 1）：")
    for k, v in o.profile.strategies[1].infoset_probs.items():
        print(f"  {k}: { {a: round(x, 4) for a, x in v.items()} }")
    return 0


def cmd_profile(args) -> int:
    game = _build_game(args)
    from .eval.exploitability import summary

    rows = [
        ("uniform", game.uniform_profile()),
    ]
    if available():
        rows.append(("oracle-LP", solve(game).profile))
    for s in range(args.n_seeds):
        from .solvers import run_cfr_plus

        r = run_cfr_plus(game, args.cfr_plus_iters, args.seed + s, exploit_eps=args.exploit_eps)
        rows.append((f"CFR+ seed{s}", r.profile))
    print(summary(game, rows))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nashforge", description="不完美信息博弈精确均衡求解")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--n-cards", type=int, default=3)
    common.add_argument("--seed", type=int, default=20261006)
    common.add_argument("--n-seeds", type=int, default=3)
    common.add_argument("--cfr-iters", type=int, default=2000)
    common.add_argument("--cfr-plus-iters", type=int, default=24000)
    common.add_argument("--exploit-eps", type=float, default=1e-2)

    sub.add_parser("demo", parents=[common]).set_defaults(func=cmd_demo)
    sub.add_parser("gates", parents=[common]).set_defaults(func=cmd_gates)
    sub.add_parser("solve", parents=[common]).set_defaults(func=cmd_solve)
    sub.add_parser("profile", parents=[common]).set_defaults(func=cmd_profile)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
