# NashForge

> 不完美信息博弈精确均衡求解：序列式 LP 精确 oracle + CFR/CFR+ 近似求解 + 四条交付门禁。

作者：**晨星** · 版本：0.1.0 · License：MIT

NashForge 在二人零和不完美信息扩展式博弈（以 **Kuhn poker** 为基准）上提供：

- **精确 oracle**：Koller-Megiddo-von Stengel 1996 的序列式线性规划（sequence-form LP），
  求解出的策略对**可剥削性 = 0**，博弈值经范式 LP 独立交叉验证（强对偶）。
- **近似求解器**：纯 numpy 实现的 CFR 与 CFR+（chance-sampling tabular），离线兜底、确定可复现。
- **四条交付门禁（DoD）**：精确性 / 收敛速度 / 多 seed 胜强基线 / 确定性，全部可自动校验。

---

## 快速开始

```bash
# 创建隔离环境（推荐）
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock.txt
pip install -e .

# 门禁自检（含端到端 ≤60s demo）
python -m nashforge.cli demo

# 或跑测试 + lint
pytest -q
ruff check .
```

依赖：`numpy`、`scipy`（运行时）；`pytest`、`ruff`（开发）。详见 `requirements.lock.txt`。

---

## 命令行

```bash
python -m nashforge.cli demo      # 端到端 pipeline + 四条门禁 + 可读性报告
python -m nashforge.cli gates     # 仅运行四条门禁
python -m nashforge.cli solve     # 打印序列式 LP 精确均衡（博弈值/可剥削性/策略）
python -m nashforge.cli profile   # 多策略评测表（uniform / oracle / 多 seed CFR+）
```

环境变量覆盖：`NASHFORGE_SEED`、`NASHFORGE_N_SEEDS`、`NASHFORGE_CFR_ITERS`、
`NASHFORGE_CFR_PLUS_ITERS`、`NASHFORGE_CFR_DET_ITERS`、`NASHFORGE_EXPLOIT_EPS` 等。

---

## 架构（单向无环）

```
cli ──▶ pipeline ──▶ { games, solvers, eval } ──▶ core
```

- `core`：类型（`Strategy`/`StrategyProfile`/`OracleResult`/`GateReport`/`PipelineReport`）、
  配置、种子、错误。
- `games/kuhn.py`：Kuhn poker 博弈模型（收益、最佳响应、可剥削性、LP 行走生成器）。
- `solvers/`：
  - `sequence_form_lp.py`：精确 oracle（`solve` / `normal_form_value` / `available`）。
  - `cfr.py` / `cfr_plus.py`：CFR / CFR+ 近似求解器。
- `eval/`：可剥削性评测（`exploitability.py`）+ 四条门禁（`gates.py`）。
- `pipeline/`：端到端编排与报告（`run_pipeline` / `render`）。

---

## 四条交付门禁（DoD）

| 门禁 | 含义 | 默认阈值 |
|------|------|----------|
| G1 oracle-exact | 序列式 LP 均衡可剥削性 ≈ 0，且博弈值 = 范式 LP 锚点、强对偶成立 | `lp_value_tol = 1e-9` |
| G2 cfr-convergence | CFR+ 在 `cfr_plus_iters` 内可剥削性跌破 `exploit_eps` | `exploit_eps = 1e-2` |
| G3 multiseed-baseline | 多 seed CFR+ 平均可剥削性严格低于均匀随机基线（n=3 ≈ 0.75） | 基线值 |
| G4 determinism | 同 seed 两次运行逐位一致（oracle + CFR+） | `deterministic_tol = 1e-12` |

---

## 关键不变量（正确性硬标准）

- **强对偶**：`oracle_v_p0 == oracle_v_p1 == value_p0`（序列式 LP 对偶增广双 LP 直接配对）。
- **可剥削性 = 0**：`exploitability(oracle.profile) ≈ 0`（Nash 均衡）。
- **范式锚定**：`value_p0 == normal_form_value(game)`（独立范式 LP 交叉验证）。
- **标准结果**：n=3 博弈值 = `−1/18`（与 Kuhn 1950 一致）。
- **确定性**：同 seed 两次 `run_cfr`/`run_cfr_plus` 策略逐位一致。

数学细节与实现笔记见 [`docs/architecture.md`](docs/architecture.md)；
方法学、指标与局限见 [`docs/model_card.md`](docs/model_card.md)。

---

## 许可

MIT © 2026 晨星。
