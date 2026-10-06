"""NashForge 演示：精确 oracle + 近似求解器 + 四条门禁。

运行：python examples/run_demo.py
（需先 pip install -e . 或在仓库根目录以 PYTHONPATH=. 运行）

作者：晨星。
"""

from __future__ import annotations

import sys
import time

from nashforge import Config, KuhnPoker, run_pipeline
from nashforge.pipeline.pipeline import render


def main() -> int:
    cfg = Config()
    cfg.n_seeds = 3
    cfg.cfr_iters = 2000
    cfg.cfr_plus_iters = 24000
    cfg.cfr_det_iters = 1500
    game = KuhnPoker(3)

    t0 = time.perf_counter()
    report = run_pipeline(game, cfg)
    wall = time.perf_counter() - t0

    print(render(report))
    print(f"\n[demo] 端到端耗时 {wall:.3f}s（应 ≤ 60s）")
    if not report.all_pass():
        print("[demo] 门禁未全绿，退出码 1")
        return 1
    print("[demo] 全部门禁通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
