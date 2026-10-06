"""全局配置：ENV_NASHFORGE_* 覆盖 + schema 校验。作者：晨星。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import ConfigError


@dataclass
class Config:
    """NashForge 运行配置。

    所有字段均可通过环境变量 ``NASHFORGE_*`` 覆盖（见 :meth:`from_env`）。
    """

    seed: int = 20261006
    n_seeds: int = 3
    cfr_iters: int = 2000
    cfr_plus_iters: int = 24000
    cfr_det_iters: int = 1500  # G4 确定性对：同 seed 两次 CFR+ 轻量轨迹（不计入收敛预算）
    exploit_eps: float = 1e-2  # G2 速度门禁阈值：可剥削性 < 此值视为收敛
    lp_value_tol: float = 1e-9  # G1 oracle 博弈值容差
    deterministic_tol: float = 1e-12  # G4 确定性逐位一致容差（elapsed 除外）
    repo: str = "nashforge"

    @classmethod
    def from_env(cls) -> Config:
        """从环境变量读取覆盖；非法值抛 ConfigError。"""
        mapping = {
            "NASHFORGE_SEED": ("seed", int),
            "NASHFORGE_N_SEEDS": ("n_seeds", int),
            "NASHFORGE_CFR_ITERS": ("cfr_iters", int),
            "NASHFORGE_CFR_PLUS_ITERS": ("cfr_plus_iters", int),
            "NASHFORGE_CFR_DET_ITERS": ("cfr_det_iters", int),
            "NASHFORGE_EXPLOIT_EPS": ("exploit_eps", float),
            "NASHFORGE_LP_VALUE_TOL": ("lp_value_tol", float),
            "NASHFORGE_DETERMINISTIC_TOL": ("deterministic_tol", float),
            "NASHFORGE_REPO": ("repo", str),
        }
        kw: dict = {}
        for env, (attr, caster) in mapping.items():
            if env in os.environ:
                raw = os.environ[env]
                try:
                    kw[attr] = caster(raw)
                except (ValueError, TypeError) as exc:
                    raise ConfigError(f"环境变量 {env}={raw!r} 无法转换为 {caster.__name__}") from exc
        return cls(**kw)

    def validate(self) -> None:
        """校验配置合法性，非法抛 ConfigError。"""
        if self.seed < 0:
            raise ConfigError("seed 必须 >= 0")
        if self.n_seeds < 1:
            raise ConfigError("n_seeds 必须 >= 1")
        if self.cfr_iters < 1 or self.cfr_plus_iters < 1 or self.cfr_det_iters < 1:
            raise ConfigError("迭代次数必须 >= 1")
        if not (0.0 < self.exploit_eps < 1.0):
            raise ConfigError("exploit_eps 必须在 (0,1) 区间")
        if self.lp_value_tol <= 0 or self.deterministic_tol <= 0:
            raise ConfigError("容差必须 > 0")
