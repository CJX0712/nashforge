"""序列式线性规划（sequence-form LP）精确 oracle。作者：晨星。

二人零和扩展式博弈的 Nash 均衡由 Koller-Megiddo-von Stengel (1996) 的序列式 LP 精确求得。
关键：以「实现权重（realization weight）」为变量，payoff 对实现权重是**线性**的（不像
逐信息集行为概率那样在多次决策路径上呈二次），从而可写成一对强对偶 LP：

    P0-LP（P0 最大化）：max v  s.t.  ∀ P1 序列 σ1: Σ_{σ0} M[σ1][σ0] r0[σ0] ≥ v ;
                          F0·r0 = e0（实现权重树约束）; r0 ≥ 0
    P1-LP（P1 最小化 P0 收益）：min v  s.t.  ∀ P0 序列 σ0: Σ_{σ1} M[σ1][σ0] r1[σ1] ≤ v ;
                          F1·r1 = e1 ; r1 ≥ 0

两 LP 最优解 (r0*, r1*) 经实现权重→行为策略转换即构成一个 Nash 均衡：
payoff_0(β0*, β1*) = v = 博弈值（P0 视角），可剥削性 ≈ 0。博弈值另由范式 LP 独立交叉验证。

需要 scipy；缺失时 available()=False，系统自动降级（CFR/CFR+ 仍为纯 numpy，可独立运行）。
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from ..core.errors import BackendError, SolverError
from ..core.types import OracleResult, Strategy, StrategyProfile
from ..games.kuhn import KuhnPoker


def available() -> bool:
    """scipy 是否可用（精确 oracle 的后端）。"""
    try:
        from scipy.optimize import linprog  # noqa: F401

        return True
    except Exception:  # pragma: no cover - 依赖可选
        return False


# ---------------------------------------------------------------------------
# 序列式 LP 核心：构建实现权重序列集、收益矩阵 M 与树约束 F/e
# ---------------------------------------------------------------------------
def _build_sequence_form(game: KuhnPoker):
    """返回 (M, p0_seqs, p1_seqs, var0, var1, F0, e0, F1, e1, parent_map)。

    - p0_seqs / p1_seqs：所有（含前缀）P0/P1 序列，元素为 ((infoset,action), ...) 元组。
    - var0 / var1：去掉空序列 () 后的决策变量序列列表。
    - M：|p1_seqs| × |p0_seqs| 收益矩阵（玩家 0 视角）。
    - F0/e0、F1/e1：实现权重树约束（parent 序列权重 = 子序列权重之和）。
    - parent_map：P0 信息集 → 抵达该信息集前的 P0 父序列（用于行为策略转换）。

    缩放：实现权重根序列按「每张牌」归一化到 1/n（机会节点折叠进根，r(∅)=1）。
    逐牌发牌概率实际为 1/(n(n-1))，而实现权重乘积含 (1/n)²；二者相差比 n/(n-1)。
    但 Kuhn 发牌为「无放回」（c0≠c1），两张牌不独立——实现权重乘积把发牌当独立，
    相较真实联合概率 1/(n(n-1)) 多算一个因子 n/(n-1)；故收益矩阵须乘
    n/(2(n-1))，即 M[j][i] = paySum(i,j) · n/(2(n-1))，使 LP 博弈值 = 真实博弈值。
    """
    scale = game.n_cards / (game.n_cards - 1)

    # 1) 收集终局路径上的序列，并累加收益矩阵 M
    M: dict[tuple[tuple, tuple], float] = defaultdict(float)
    p0_term: set = set()
    p1_term: set = set()

    def walk(h, c0, c1, p0seq, p1seq):
        if game.is_terminal(h):
            p0_term.add(p0seq)
            p1_term.add(p1seq)
            M[(p1seq, p0seq)] += game.terminal_utility(c0, c1, h) * scale
            return
        p = game.current_player(h)
        if p == 0:
            info_key = game.infoset_key(0, c0, c1, h)
            for a in game.legal_actions(h):
                walk(h + a, c0, c1, p0seq + ((info_key, a),), p1seq)
        else:
            info_key = game.infoset_key(1, c0, c1, h)
            for a in game.legal_actions(h):
                walk(h + a, c0, c1, p0seq, p1seq + ((info_key, a),))

    for c0, c1 in game.deals():
        walk("", c0, c1, (), ())

    # 2) 补入所有前缀序列（父序列）
    def add_prefixes(s, acc):
        acc.add(s)
        if s:
            add_prefixes(s[:-1], acc)

    p0_all = set(p0_term)
    p1_all = set(p1_term)
    for s in list(p0_term):
        add_prefixes(s, p0_all)
    for s in list(p1_term):
        add_prefixes(s, p1_all)

    p0_seqs = sorted(p0_all)
    p1_seqs = sorted(p1_all)
    idx0 = {s: i for i, s in enumerate(p0_seqs)}
    idx1 = {s: i for i, s in enumerate(p1_seqs)}

    Mmat = np.zeros((len(p1_seqs), len(p0_seqs)))
    for (sp1, sp0), val in M.items():
        Mmat[idx1[sp1], idx0[sp0]] = val

    # 3) 决策变量（去掉空序列）
    var0 = [s for s in p0_seqs if s != ()]
    var1 = [s for s in p1_seqs if s != ()]

    # 4) 实现权重树约束 F·r = e
    #    根实现权重按「每个根信息集」分别归一化到 1/n（机会节点折叠进根），父序列用
    #    Σ_a r(child) = r(parent) 耦合。注意 P1 在「P0 check 后」与「P0 bet 后」是
    #    两个独立根信息集，须各自归一化（不能按牌号把两信息集合并到 1/n）。
    def build_constraints(seqs, var, game, player):
        children_of: dict[tuple, list[tuple]] = defaultdict(list)
        for s in seqs:
            if s:
                children_of[s[:-1]].append(s)
        rows = []  # (children, parent_or_None)
        for p in children_of:
            if p == ():
                continue
            if p in var:
                rows.append((children_of[p], p))
        # 根归一化：按「根信息集键」分组（每个根信息集的序列各自归一化到 1/n）
        root_keys: set = set()
        for s in children_of.get((), []):
            if s and len(s) == 1:
                root_keys.add(s[0][0])
        for key in sorted(root_keys):
            root_seqs = [s for s in children_of.get((), []) if s and len(s) == 1 and s[0][0] == key]
            if root_seqs:
                rows.append((root_seqs, None))
        F = np.zeros((len(rows), len(var)))
        e = np.zeros(len(rows))
        for ri, (children, parent) in enumerate(rows):
            for child in children:
                if child in var:
                    F[ri, var.index(child)] = 1.0
            if parent is not None and parent in var:
                F[ri, var.index(parent)] = -1.0
            else:
                e[ri] = 1.0 / game.n_cards  # 根实现权重 = 发牌概率（机会节点折叠进根）
        return F, e

    F0, e0 = build_constraints(p0_seqs, var0, game, 0)
    F1, e1 = build_constraints(p1_seqs, var1, game, 1)

    # 5) 信息集 → 父序列（行为策略转换用）
    parent_map: dict[str, tuple] = {}

    def walk_parent(h, c0, c1, p0seq):
        if game.is_terminal(h):
            return
        p = game.current_player(h)
        if p == 0:
            info_key = game.infoset_key(0, c0, c1, h)
            parent_map[info_key] = p0seq
            for a in game.legal_actions(h):
                walk_parent(h + a, c0, c1, p0seq + ((info_key, a),))
        else:
            # 遍历对手所有动作，确保覆盖后续所有 P0 信息集
            for a in game.legal_actions(h):
                walk_parent(h + a, c0, c1, p0seq)

    for c0, c1 in game.deals():
        walk_parent("", c0, c1, ())

    return Mmat, p0_seqs, p1_seqs, var0, var1, F0, e0, F1, e1, parent_map, p0_term, p1_term


def _realization_to_behavioral(
    seq_weights: dict[tuple, float],
    var: list[tuple],
    parent_map: dict[str, tuple],
    game: KuhnPoker,
    player: int,
) -> dict[str, dict[str, float]]:
    """将实现权重（含空序列=1）转换为逐信息集行为策略概率。"""
    full = {(): 1.0}
    for s in var:
        full[s] = seq_weights.get(s, 0.0)
    infosets = game.p0_infosets() if player == 0 else game.p1_infosets()
    deal_prob = 1.0 / game.n_cards
    beh: dict[str, dict[str, float]] = {}
    for info_key in infosets:
        parent = parent_map[info_key]
        # 根信息集的抵达实现权重含发牌概率 1/n（机会节点），非 r(∅)=1
        denom = deal_prob if parent == () else full.get(parent, 0.0)
        acts = game.actions_for_infoset(info_key)
        d = {}
        for a in acts:
            child = parent + ((info_key, a),)
            num = full.get(child, 0.0)
            d[a] = (num / denom) if denom > 0 else (1.0 / len(acts))
        beh[info_key] = d
    return beh


# ---------------------------------------------------------------------------
# 范式 LP：独立交叉验证锚点
# ---------------------------------------------------------------------------
def _build_normal_form(game: KuhnPoker):
    """构造范式零和博弈收益矩阵 U[i][j]（玩家 0 视角）与动作索引。"""
    p0s = game.all_pure_strategies(0)
    p1s = game.all_pure_strategies(1)
    nd_inv = game.deal_prob()
    U = np.zeros((len(p0s), len(p1s)))

    def payoff_pure(s0, s1):
        tot = 0.0
        for c0, c1_ in game.deals():
            h = ""
            while not game.is_terminal(h):
                p = game.current_player(h)
                a = s0[game.infoset_key(0, c0, c1_, h)] if p == 0 else s1[game.infoset_key(1, c0, c1_, h)]
                h = h + a
            tot += game.terminal_utility(c0, c1_, h)
        return tot * nd_inv

    for i, s0 in enumerate(p0s):
        for j, s1 in enumerate(p1s):
            U[i, j] = payoff_pure(s0, s1)
    return U, p0s, p1s


def normal_form_value(game: KuhnPoker) -> float:
    """范式 LP 求出的精确博弈值（玩家 0 视角），作为独立交叉验证锚点。"""
    if not available():
        raise BackendError("normal_form_value 需要 scipy")
    from scipy.optimize import linprog

    U, _, _ = _build_normal_form(game)
    n = U.shape[0]
    c = [0.0] * n + [-1.0]
    A_ub: list[list[float]] = []
    b_ub: list[float] = []
    for j in range(U.shape[1]):
        row = [0.0] * n + [1.0]
        for i in range(n):
            row[i] = -float(U[i, j])
        A_ub.append(row)
        b_ub.append(0.0)
    A_eq = [[1.0] * n + [0.0]]
    b_eq = [1.0]
    bnd = [(0.0, None)] * n + [(None, None)]
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bnd, method="highs")
    if not res.success:
        raise SolverError(f"normal-form LP 求解失败: {res.message}")
    return float(res.x[-1])


# ---------------------------------------------------------------------------
# 主入口：解对偶序列式 LP，配对得 Nash 均衡
# ---------------------------------------------------------------------------
def solve(game: KuhnPoker) -> OracleResult:
    """精确求解 Kuhn poker 的一个 Nash 均衡（序列式 LP，von Stengel 1996）。

    payoff = r0ᵀ M r1，M 为玩家 0 视角收益矩阵。标准对偶增广 LP：

        P0-LP（玩家 0 最大化 v）：
            max v  s.t.  F0·x = e0, x ≥ 0 ;
                        ∀ P1 序列 j: (F1ᵀ u)[j] ≤ Σ_i M[j][i] x[i] ;
                        v ≤ e1ᵀ u ;  u 自由
        P1-LP（玩家 1 最小化 v，对称）：
            min v  s.t.  F1·y = e1, y ≥ 0 ;
                        ∀ P0 序列 i: (F0ᵀ w)[i] ≥ Σ_j M[j][i] y[j] ;
                        v ≥ e0ᵀ w ;  w 自由

    两 LP 最优解配对即 Nash 均衡（强对偶），博弈值 = v，可剥削性 ≈ 0。
    博弈值另由 normal_form_value（范式 LP）独立交叉验证。

    Returns:
        OracleResult：博弈值、均衡策略对、可剥削性（应 ≈ 0）。

    Raises:
        BackendError: scipy 缺失。
        SolverError: LP 求解失败。
    """
    if not available():
        raise BackendError("序列式 LP oracle 需要 scipy.optimize.linprog")
    from scipy.optimize import linprog

    (Mmat, p0_seqs, p1_seqs, var0, var1, F0, e0, F1, e1, parent_map, p0_term, p1_term) = _build_sequence_form(game)
    idx0 = {s: i for i, s in enumerate(p0_seqs)}
    idx1 = {s: i for i, s in enumerate(p1_seqs)}
    var0_local = {s: k for k, s in enumerate(var0)}
    var1_local = {s: k for k, s in enumerate(var1)}

    # ---- P0-LP：max v ----
    nv0 = len(var0)            # x 维（P0 实现权重）
    nu = F1.shape[0]           # u 维（P1 树约束对偶）
    N0 = nv0 + nu + 1
    c0_obj = [0.0] * nv0 + [0.0] * nu + [-1.0]
    A_eq0 = np.zeros((F0.shape[0], N0))
    A_eq0[:, :nv0] = F0
    b_eq0 = e0
    A_ub0: list[list[float]] = []
    b_ub0: list[float] = []
    F1T = F1.T  # (|var1|, nu)
    # ∀ P1 序列 j: (F1ᵀ u)[j] ≤ Σ_i M[j][i] x[i]  →  -Σ_i M[j][i] x[i] + (F1ᵀ u)[j] ≤ 0
    for js in var1:
        jl = var1_local[js]
        row = [0.0] * N0
        for is_ in var0:
            row[var0_local[is_]] += -float(Mmat[idx1[js], idx0[is_]])
        for k in range(nu):
            row[nv0 + k] += float(F1T[jl, k])
        A_ub0.append(row)
        b_ub0.append(0.0)
    # v ≤ e1ᵀ u  →  v - Σ_k e1[k] u[k] ≤ 0
    row = [0.0] * N0
    row[-1] = 1.0
    for k in range(nu):
        row[nv0 + k] += -float(e1[k])
    A_ub0.append(row)
    b_ub0.append(0.0)
    bounds0 = [(0.0, None)] * nv0 + [(None, None)] * nu + [(None, None)]
    res0 = linprog(c0_obj, A_ub=A_ub0, b_ub=b_ub0, A_eq=A_eq0, b_eq=b_eq0, bounds=bounds0, method="highs")
    if not res0.success:
        raise SolverError(f"P0-LP 求解失败: {res0.message}")
    x = res0.x[:nv0]
    r0 = {s: float(val) for s, val in zip(var0, x, strict=True)}
    v_p0 = float(res0.x[-1])

    # ---- P1-LP：min v ----
    nv1 = len(var1)            # y 维（P1 实现权重）
    nw = F0.shape[0]           # w 维（P0 树约束对偶）
    N1 = nv1 + nw + 1
    c1_obj = [0.0] * nv1 + [0.0] * nw + [1.0]
    A_eq1 = np.zeros((F1.shape[0], N1))
    A_eq1[:, :nv1] = F1
    b_eq1 = e1
    A_ub1: list[list[float]] = []
    b_ub1: list[float] = []
    F0T = F0.T  # (|var0|, nw)
    # ∀ P0 序列 i: (F0ᵀ w)[i] ≥ Σ_j M[j][i] y[j]  →  Σ_j M[j][i] y[j] - (F0ᵀ w)[i] ≤ 0
    for is_ in var0:
        il = var0_local[is_]
        row = [0.0] * N1
        for js in var1:
            row[var1_local[js]] += float(Mmat[idx1[js], idx0[is_]])
        for k in range(nw):
            row[nv1 + k] += -float(F0T[il, k])
        A_ub1.append(row)
        b_ub1.append(0.0)
    # v ≥ e0ᵀ w  →  Σ_k e0[k] w[k] - v ≤ 0
    row = [0.0] * N1
    for k in range(nw):
        row[nv1 + k] += float(e0[k])
    row[-1] += -1.0
    A_ub1.append(row)
    b_ub1.append(0.0)
    bounds1 = [(0.0, None)] * nv1 + [(None, None)] * nw + [(None, None)]
    res1 = linprog(c1_obj, A_ub=A_ub1, b_ub=b_ub1, A_eq=A_eq1, b_eq=b_eq1, bounds=bounds1, method="highs")
    if not res1.success:
        raise SolverError(f"P1-LP 求解失败: {res1.message}")
    y = res1.x[:nv1]
    r1 = {s: float(val) for s, val in zip(var1, y, strict=True)}
    v_p1 = float(res1.x[-1])

    # ---- 实现权重 → 行为策略 ----
    # von Stengel 序列式 LP 定理：P0-LP 的原始最优解 x* 与 P1-LP 的原始最优解 y*
    # 配对即构成一个 Nash 均衡（二者互为最佳响应），可剥削性 ≈ 0。
    p0_beh = _realization_to_behavioral(r0, var0, parent_map, game, 0)
    p1_parent = _build_p1_parent_map(game)
    p1_beh = _realization_to_behavioral(r1, var1, p1_parent, game, 1)

    profile = StrategyProfile(
        strategies={
            0: Strategy(0, game._normalize(p0_beh)),
            1: Strategy(1, game._normalize(p1_beh)),
        }
    )
    value_p0, _ = game.value(profile)
    exploit = game.exploitability(profile)
    return OracleResult(
        value_p0=value_p0,
        profile=profile,
        exploitability=float(exploit),
        solver="sequence_form_lp",
        oracle_v_p0=float(v_p0),
        oracle_v_p1=float(v_p1),
    )


def _build_p1_parent_map(game: KuhnPoker) -> dict[str, tuple]:
    """P1 信息集 → 抵达前的 P1 父序列。"""
    parent_map: dict[str, tuple] = {}

    def walk_parent(h, c0, c1, p1seq):
        if game.is_terminal(h):
            return
        p = game.current_player(h)
        if p == 1:
            info_key = game.infoset_key(1, c0, c1, h)
            parent_map[info_key] = p1seq
            for a in game.legal_actions(h):
                walk_parent(h + a, c0, c1, p1seq + ((info_key, a),))
        else:
            # 遍历对手（P0）所有动作，确保覆盖后续所有 P1 信息集
            for a in game.legal_actions(h):
                walk_parent(h + a, c0, c1, p1seq)

    for c0, c1 in game.deals():
        walk_parent("", c0, c1, ())
    return parent_map
