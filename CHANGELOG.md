# Changelog

所有版本作者：晨星。

## [0.1.0] — 2026-10-06

首个发布版本（S 级交付）。

### 特性
- **序列式 LP 精确 oracle**（Koller-Megiddo-von Stengel 1996 实现权重序列式 LP）：
  - 对偶增广双 LP（P0-LP `max v` / P1-LP `min v`），原始解直接配对即构成 Nash 均衡；
  - 强对偶 `v_p0 == v_p1`、博弈值经范式 LP 独立锚定（`normal_form_value`）；
  - n=2..5 经验证可剥削性 = 0、LP 值 = 范式 LP 锚点。
- **CFR / CFR+ 近似求解器**（纯 numpy，离线兜底）：
  - 朴素 CFR（累积遗憾）与 CFR+（正累积遗憾 + 平均策略等权和）；
  - chance-sampling tabular 实现，同 seed 确定性。
- **四条交付门禁（DoD）**：
  - G1 精确 oracle（可剥削性 ≈ 0 + 博弈值 = 锚点 + 强对偶）；
  - G2 CFR+ 收敛速度（在 `cfr_plus_iters` 内可剥削性跌破 `exploit_eps`）；
  - G3 多 seed 胜强基线（平均可剥削性严格低于均匀随机基线 ≈0.75）；
  - G4 确定性（同 seed 两次运行逐位一致）。
- **单向无环架构**：`cli -> pipeline -> {games, solvers, eval} -> core`。
- **端到端 pipeline + demo**：默认 n=3，全部门禁通过且端到端 ≤ 60s。

### 验证
- ruff 0.16.10：零违规。
- pytest：13 项全绿（含 G1–G4 集成与 pipeline 级确定性）。
- 博弈值 n=3 = −1/18（与 Kuhn 1950 标准结果一致）。

### 依赖
- 运行时：numpy>=1.26、scipy>=1.11。
- 开发：pytest>=8、ruff==0.16.10。
