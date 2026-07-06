import sys
from pathlib import Path

# Repo convention (mirrors experiments/m1_5/tests/conftest.py): tests insert the
# milestone code dir onto sys.path, plus m1_5 and m1 so M1.6 reuses the canonical
# harness (floatsplit, split_measure, synth, m1_codecs, chunking) — never copied.
_M16 = Path(__file__).resolve().parents[1]
_M15 = _M16.parent / "m1_5"
_M1 = _M16.parent / "m1"
for _p in (_M16, _M15, _M1):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
