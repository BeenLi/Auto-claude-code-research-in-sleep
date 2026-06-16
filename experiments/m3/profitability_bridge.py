"""Re-export M1's break-even math as the single source of truth (no copy).

M3 reuses the unit-tested derivation in ``experiments/m1/profitability.py`` rather than
duplicating it, so the frontier and the M1 corpus can never disagree on the math.
"""

from __future__ import annotations

import sys
from pathlib import Path

# experiments/m1 holds the canonical profitability module.
_M1 = Path(__file__).resolve().parents[1] / "m1"
if str(_M1) not in sys.path:
    sys.path.insert(0, str(_M1))

from profitability import (  # noqa: E402,F401
    alpha_threshold,
    alpha_threshold_simplified,
    is_profitable,
    transfer_times,
)

__all__ = [
    "transfer_times",
    "alpha_threshold",
    "alpha_threshold_simplified",
    "is_profitable",
]
