# NashForge 实现陷阱记录（Round 2）

作者：晨星。以下为“看似合理但结果错误/失败”的典型坑，留存以警醒后续系统。

## 1. 序列式 LP 数学坑

- **P0 可作弊**：朴素约束 `∀j: Σ_i M[j][i] r0[i] ≥ v` 缺少对偶增广，LP 值飘到 +0.19 量级。
  → 改用 von Stengel 1996 对偶增广双 LP（`Eᵀu ≤ Mᵀx`，`v ≤ e1ᵀu`）。
- **M 缩放错**：无放回发牌使实现权重乘积多算 `n/(n-1)`；`scale` 须为 `n/(n-1)`（n=3 → 1.5），
  否则 LP 值偏到 −1/9 或 −1/12。
- **配对非均衡**：误以为需对任一方做最佳响应恢复对偶；实际 von Stengel 直接配对
  P0-LP 原始解 `x*` 与 P1-LP 原始解 `y*` 即 Nash 均衡（可剥削性 = 0）。
- **P1 根归一化错（终极坑）**：P1 在「P0 check 后」与「P0 bet 后」是**两个独立根信息集**，
  须各自归一到 `1/n`；按牌号把两信息集合并到 1/n 会低估 P1 实现权重、使博弈值偏离。
  → 按信息集键 `s[0][0]` 分组归一化。

## 2. 工程/架构坑

- **循环导入**：`gates → pipeline.PipelineReport` 与 `pipeline → eval → gates` 成环，
  导入时报 `cannot import name 'run_all_gates' from partially initialized module`。
  → `PipelineReport` 上移到 `core/types.py`；求解器类型用 `TYPE_CHECKING` 引用，避开
  `core.types → solvers → games` 回环。
- **门禁接口不一致**：`run_all_gates` 签名曾为 `(report)`，内部读 `report._game/_cfg`（不存在）；
  `pipeline` 又误调 `run_all_gates(game, cfg)`。→ 统一为 `run_all_gates(game, cfg, report)`，
  gates 仅消费 report 预计算结果，不重复求解。
- **确定性比较含墙钟**：`PipelineReport.as_dict()` 含 `elapsed`（非确定性），
  pipeline 级确定性测试须剔除 `elapsed` 再比较。
- **`cfr_plus_iters` 不足**：默认 2000 时 CFR+ final≈0.0105 仅“中途跌破”但未在末轮低于 `1e-2`，
  G2 失败；提到 24000 使 final≈0.0079 稳过（wall≈42s，仍 ≤60s）。
- **`Dict` 遗留/弃用**：`pipeline.py` 曾漏 `Dict` 导入（F821），且 ruff UP035 要求 `dict` 而非 `typing.Dict`；
  统一用内置 `dict[...]` 注解。

## 3. 质量门禁

- ruff 0.16.10 须**零违规**（E/F/I/W/UP/B/C4/SIM 全选）；长行采用 `line-length=120`。
- 测试标记 `slow`：端到端 G1–G4 与确定性测试标记 `@pytest.mark.slow`，CI 全量运行。
- 单向无环：`cli → pipeline → {games, solvers, eval} → core`，无反向依赖。
