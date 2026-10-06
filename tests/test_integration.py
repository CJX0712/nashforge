"""端到端集成测试（慢，标记 slow）。作者：晨星。

覆盖：
  * 四条交付门禁（G1 精确 / G2 收敛 / G3 多 seed 胜基线 / G4 确定性）全部通过；
  * pipeline 级确定性：同 Config 两次运行 report.as_dict() 逐位一致（S 级硬约束）。
用 ``pytest -m slow`` 运行；CI 默认运行全集。
"""

from __future__ import annotations

import pytest

from nashforge import Config, KuhnPoker
from nashforge.pipeline.pipeline import run_pipeline


def _demo_config() -> Config:
    cfg = Config()
    cfg.n_seeds = 3
    cfg.cfr_iters = 2000
    cfg.cfr_plus_iters = 24000
    cfg.cfr_det_iters = 1500
    return cfg


@pytest.mark.slow
def test_pipeline_gates_all_green() -> None:
    g = KuhnPoker(3)
    rep = run_pipeline(g, _demo_config())
    assert rep.all_pass(), {g_.name: g_.passed for g_ in rep.gates}


@pytest.mark.slow
def test_pipeline_deterministic_bit_identical() -> None:
    g = KuhnPoker(3)
    cfg = _demo_config()
    rep1 = run_pipeline(g, cfg)
    rep2 = run_pipeline(g, cfg)
    assert rep1.all_pass()

    def _stripped(rep):
        # 剔除墙钟耗时（非确定性），校验计算结果逐位一致
        d = rep.as_dict()
        d.pop("elapsed", None)
        return d

    assert _stripped(rep1) == _stripped(rep2)  # 同 seed 逐位一致
