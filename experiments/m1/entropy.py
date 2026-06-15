"""Byte-level Shannon entropy (bits per byte, range [0, 8])."""

from __future__ import annotations

import math
from collections import Counter


def shannon_entropy_bits_per_byte(data: bytes) -> float:
    n = len(data)
    if n == 0:
        return 0.0
    h = 0.0
    for count in Counter(data).values():
        p = count / n
        h -= p * math.log2(p)
    return h
