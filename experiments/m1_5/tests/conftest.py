import sys
from pathlib import Path

# Repo convention (mirrors experiments/m3/tests/conftest.py): tests insert the
# milestone code dir onto sys.path, plus experiments/m1 so M1.5 can reuse the
# canonical M1 harness (synth, m1_codecs, entropy, chunking, manifest) as the
# single source of truth — never copied.
_M15 = Path(__file__).resolve().parents[1]
_M1 = _M15.parent / "m1"
for _p in (_M15, _M1):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
