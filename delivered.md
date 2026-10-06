# NashForge 交付记录（Round 2）

作者：晨星 · 日期：2026-10-06 · 等级：**S**

技能：`random-ai-system-delivery`（全自动随机世界顶级 AI 系统，推送 GitHub `CJX0712`，作者署名晨星）。

## 系统定位

不完美信息二人零和扩展式博弈的**精确均衡求解**系统：序列式 LP 精确 oracle（Kuhn poker）
+ CFR/CFR+ 近似求解 + 四条交付门禁（DoD）。

## 交付物

- 源码（单向无环）：`nashforge/{core,games,solvers,eval,pipeline}` + `cli.py`。
- 锁定依赖：`requirements.lock.txt`（numpy==2.5.3 / scipy==1.16.3 / pytest==9.1.1 / ruff==0.16.10）。
- 工程：`pyproject.toml`（ruff 0.16.10 门禁 + pytest 配置）、`Makefile`、`Dockerfile`、`.gitignore`、
  `requirements.txt`、`LICENSE`（MIT）、`README.md`、`CHANGELOG.md`。
- 文档：`docs/architecture.md`、`docs/model_card.md`。
- CI：`.github/workflows/ci.yml`（py3.12+3.13 × ubuntu+windows；ruff 门禁 + 全量 pytest）。
- 测试：`tests/`（13 项；oracle 精确、CFR 收敛/确定性、基线、G1–G4 集成 + pipeline 级确定性）。

## 验证结果（DoD 全绿）

| 项 | 结果 |
|----|------|
| G1 oracle 精确 | ✅ exploit=−5.55e-17；`|v−NF|=0`；`|v_p0−v_p1|=8.33e-17` |
| G2 CFR+ 收敛 | ✅ best final≈0.0079 < 1e-2；cross_iter≈16130 ≤ 24000 |
| G3 多 seed 胜基线 | ✅ mean≈0.0094 ≪ uniform 0.7500 |
| G4 确定性 | ✅ oracle 重算一致；CFR+ 同 seed 逐位一致；pipeline `as_dict` 一致（剔除墙钟） |
| ruff 0.16.10 | ✅ 零违规 |
| pytest | ✅ 13 passed（含慢测） |
| 端到端 demo | ✅ `run_pipeline` 全绿，wall≈42s（≤60s） |
| 标准结果 | ✅ n=3 博弈值 = −1/18（Kuhn 1950） |
| 仓库 / 标签 / Release | ✅ `CJX0712/nashforge` @ v0.1.0 |

## 数学正确性（不变量）

- 强对偶：`oracle_v_p0 == oracle_v_p1`。
- 可剥削性 = 0（Nash 均衡）。
- 范式锚定：`value_p0 == normal_form_value(game)`（n=2..5 全部一致）。
- 对偶增广双 LP 直接配对 `x*, y*` 即均衡（von Stengel 1996）。

## 发布

- 仓库：`https://github.com/CJX0712/nashforge`
- Tag：`v0.1.0`（对应 CHANGELOG 0.1.0）
- GitHub Release：自动关联 tag，正文含 DoD 摘要与标准结果。
