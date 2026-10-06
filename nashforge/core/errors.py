"""NashForge 异常定义（E100~E500）。作者：晨星。"""

from __future__ import annotations


class NashForgeError(Exception):
    """NashForge 所有异常的基类。"""


class ConfigError(NashForgeError):
    """配置校验失败 E100。"""


class GameError(NashForgeError):
    """博弈定义 / 构建错误 E200。"""


class SolverError(NashForgeError):
    """求解器运行错误 E300。"""


class EvalError(NashForgeError):
    """评测 / 门禁错误 E400。"""


class BackendError(NashForgeError):
    """可选后端不可用（如 scipy 缺失）E500。"""
