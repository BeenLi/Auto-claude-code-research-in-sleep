import sys
from pathlib import Path

# Repo convention (mirrors experiments/m1_6/tests/conftest.py): tests insert the
# milestone code dir onto sys.path, plus m1_6/m1_5/m1 so E0 reuses the canonical
# harness (layout, synth, m1_codecs, chunking, capture helpers) — never copied.
_ME0 = Path(__file__).resolve().parents[1]
_M16 = _ME0.parent / "m1_6"
_M15 = _ME0.parent / "m1_5"
_M1 = _ME0.parent / "m1"
for _p in (_ME0, _M16, _M15, _M1):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
