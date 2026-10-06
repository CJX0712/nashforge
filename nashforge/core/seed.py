"""全局确定性种子入口。作者：晨星。

所有随机源一次性设齐，保证同 seed 两次运行逐位一致（确定性门禁 G4 的前提）。
"""

from __future__ import annotations

import random

import numpy as np


def set_all(seed: int) -> None:
    """一次性设齐 numpy / random 种子（torch 可选）。

    Args:
        seed: 非负整数种子。
    """
    if not isinstance(seed, int) or seed < 0:
        raise ValueError(f"seed 必须为非负整数，收到 {seed!r}")
    random.seed(seed)
    np.random.seed(seed)
    try:  # torch 为可选依赖，缺失不报错（本系统默认纯 numpy 后端）
        import torch

        torch.manual_seed(seed)
    except Exception:  # pragma: no cover - 依赖可选
        pass
