# NashForge 架构与设计笔记

作者：晨星。

本文记录 NashForge 的核心数学与工程决策，尤其是序列式 LP oracle 的正确性推导，
以及实现过程中踩过的坑（这些坑是“看似合理但结果错误”的典型，留存以警醒）。

---

## 1. 博弈模型

**Kuhn poker**（Kuhn 1950，n 张牌泛化）是二人零和不完美信息扩展式博弈：
- 各发 1 张不重复牌（点数 1..n），ante 1，底池 2。
- 玩家 0（SB）先动：`check(c)` / `bet(b)`。
  - P0 check → P1 `c`（摊牌 ±1）/ `b`（P0 二次动 `call(c)`±2 / `fold(f)`−1）。
  - P0 bet → P1 `call(c)`（摊牌 ±2）/ `fold(f)`（P1 输 ante，P0 +1）。
- 信息集共 `4n` 个（n=3 时为 12）。

博弈值（n=3，玩家 0 视角）= **−1/18**，由范式 LP / CFR 收敛 / 序列式 LP 三重交叉验证。

---

## 2. 序列式 LP 精确 oracle

### 2.1 实现权重（realization weight）

Kuhn 是完美回忆博弈，可用序列式表达（sequence form）：以**实现权重** `r(s)` 为变量，
其中 `s` 是「玩家 × 动作序列」元组。收益对实现权重**线性**，故均衡可写为一对强对偶 LP。

关键技巧（`_build_sequence_form`）：
- 发牌为**无放回**抽样，实现权重根归一化须按「每个根信息集」分别归一到 `1/n`，
  而非按牌号耦合。机会节点概率 `1/(n(n-1))` 在实现权重乘积中会多算 `n/(n-1)`，
  故收益矩阵 `M` 须整体缩放 `scale = n/(n-1)`（n=3 时为 1.5），
  才能使 LP 值等于真实博弈值（否则偏到 −1/9 或 −1/12）。

### 2.2 对偶增广双 LP（von Stengel 1996）

朴素约束 `∀j: Σ_i M[j][i] r0[i] ≥ v` 会让 P0 “作弊”（LP 值飘到 +0.19 量级）。
正确形式为**对偶增广**：

```
P0-LP:  max v
        s.t. F0·r0 = e0,  r0 ≥ 0
              ∀P1 序列 j:  E_jᵀu  ≤  Σ_i M[j][i] r0[i]      (A_ub)
              v  ≤  e1ᵀu                                  (A_ub)
P1-LP:  min v   （对称，F0ᵀw ≥ Σ M y；v ≥ e0ᵀw）
```

其中 `u`（P1-LP 对偶变量）承载 P1 策略，约束 `Eᵀu ≤ Mᵀx` 正是对偶增广。
**P0-LP 原始解 `x*` 与 P1-LP 原始解 `y*` 直接配对即构成 Nash 均衡**（可剥削性 = 0），
无需再对任一方做最佳响应恢复。

### 2.3 强对偶与交叉验证

- `oracle_v_p0 = oracle_v_p1`（强对偶，数值 ´|Δ| < 1e-16）。
- `value_p0 == normal_form_value(game)`（独立范式 LP 锚点，n=2..5 全部一致）。
- `exploitability(oracle.profile) ≈ 0`（Nash 均衡不变量）。

---

## 3. CFR / CFR+

- **朴素 CFR**：累积遗憾 `R` 可正可负，平均策略按 reach 概率加权。
- **CFR+（旗舰）**：累积**正**遗憾 `R⁺ = max(0, R⁺+Δ)`，平均策略取各步即时策略等权和，
  收敛显著更快。
- 纯 numpy、chance-sampling tabular；每轮随机采样一手牌递归遍历博弈树。
- 同 seed（`numpy.random.default_rng(seed)`）两次运行逐位一致 → G4 确定性。

实测（n=3）：CFR+ 约 16130 轮可剥削性跌破 `1e-2`；默认 `cfr_plus_iters=24000`
使最终可剥削性 ≈ 0.0079（best seed），稳妥满足 G2。

---

## 4. 四条门禁（DoD）

| 门禁 | 校验对象 | 通过条件 |
|------|----------|----------|
| G1 oracle-exact | `solve(game)` | `exploit < 1e-9` 且 `|v − NF| < 1e-9` 且 `|v_p0 − v_p1| < 1e-9` |
| G2 cfr-convergence | 多 seed CFR+ 轨迹 | 至少一 seed 在预算内跌破 `exploit_eps` 且最终 `< eps` |
| G3 multiseed-baseline | 多 seed CFR+ 均值 | `mean_exploit < uniform_baseline` |
| G4 determinism | oracle 重算 + `cfr_plus_det` 对 | 同 seed 两次逐位一致 |

`pipeline` 预计算所有轨迹，`gates` **仅消费 report 不重复求解**，保证 demo ≤ 60s。

---

## 5. 工程约束（单向无环 + 确定性）

- 调用方向严格 `cli → pipeline → {games, solvers, eval} → core`，无反向依赖。
- `PipelineReport` 置于 `core/types.py`；`gates` 通过 `TYPE_CHECKING` 规避与 `solvers` 的循环导入。
- 所有随机源经 `core/seed.set_all(seed)` 设齐（numpy / random / 可选 torch）。
- `demo` 端到端 ≤ 60s（默认 n=3，`cfr_plus_iters=24000`，`n_seeds=3`，wall ≈ 42s）。

---

## 6. 实现陷阱（踩坑记录）

1. **P0 可作弊**：朴素 `Σ M r ≥ v` 约束让 P0 LP 值偏离真实博弈值 → 改用 von Stengel 对偶增广双 LP。
2. **M 缩放错**：无放回发牌使实现权重多算 `n/(n-1)` → `scale = n/(n-1)`。
3. **配对非均衡**：误用最佳响应恢复对偶 → 实际 von Stengel 直接配对 `x*, y*` 即均衡。
4. **P1 根归一化错**：P1 在「P0 check 后」与「P0 bet 后」是**两个独立根信息集**，须各自归一到 `1/n`
   （不能按牌号把两信息集合并到 1/n，否则 P1 实现权重被低估、博弈值偏离）。
5. **循环导入**：`gates → pipeline.PipelineReport` 与 `pipeline → eval → gates` 成环 →
   `PipelineReport` 上移到 `core/types.py` 并 `TYPE_CHECKING` 引用求解器类型。
