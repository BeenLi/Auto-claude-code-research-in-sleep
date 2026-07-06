# M1.6 — Channel-Major Layout Transforms (TRACE-inspired), BF3-single-stream constrained

Measures how much of TRACE's (arXiv 2509.03377) channel-major layout gain survives
WR-ZipGuard's constraint: the result must be **ONE standard deflate stream** that commodity
BF3 hardware decompresses (M2-proven bit-exact), with an off-GPU permutation/prefix-sum
inverse at the receiver. Pre-registered criteria: `refine-logs/EVALUATION_CONTRACT_M1.6.md`.

Transforms (all size-preserving, bit-exact reversible; see `layout.py`):

| method | what it does | inverse class |
|---|---|---|
| `chan` | channel-major reorder: `(rows, head_dim)` → `(head_dim, rows)` values | permutation |
| `chan_bt` | `chan` then M1.5 byte-transpose (groups per-channel exponent bytes) | permutation |
| `chan_bt_delta` | `chan_bt` then byte-wise delta mod 256 | permutation + prefix-sum |
| `bt_delta` | byte-transpose + delta, **no reorder** (isolates reorder's contribution) | permutation + prefix-sum |
| `delta` | delta alone (control) | prefix-sum |
| `byte_transpose` | M1.5 reference baseline (passthrough to `floatsplit`) | permutation |

## Usage

```bash
# tests (local venv or box venv)
../.m15venv/bin/python -m pytest tests/ -q

# synthetic sweep (mechanism control: standard-normal KV has NO per-channel structure,
# so chan* should be ~neutral here; the verdict comes from captured KV only)
PYTHONPATH=../m1:../m1_5 python run_m16.py synthetic --out m16_outputs/layout_synth.jsonl

# real captures (on the box)
PYTHONPATH=../m1:../m1_5 python run_m16.py capture --model gpt2 --out m16_outputs/layout_gpt2.jsonl
PYTHONPATH=../m1:../m1_5 HF_ENDPOINT=https://hf-mirror.com python run_m16.py capture \
    --model Qwen/Qwen2.5-7B --out m16_outputs/layout_qwen7b.jsonl --phases prefill --max-new-tokens 0

# verdict (pre-registered thresholds; captured KV only; worst model)
PYTHONPATH=../m1:../m1_5 python analyze_m16.py \
    --corpus m16_outputs/layout_gpt2.jsonl m16_outputs/layout_qwen7b.jsonl m16_outputs/layout_synth.jsonl \
    --out m16_outputs/layout_analysis.json
```

Alignment constraint (also enforced in code): chunks must be multiples of
`head_dim × itemsize`, so the gate must aggregate KV on row boundaries (true for
256 KB / 1 MB with head_dim 64/128).

Results: `m16_results.json` + `M1_6_REPORT.md` (written after the captured runs).
