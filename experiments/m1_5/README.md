# M1.5 — Float-Split / Bit-Plane Compressibility

Does an **exponent-grouping layout transform before deflate** (à la DietGPU / UCCL-Zip / NetZIP) move a
KV dtype across the 0.75 profitability gate that **M1** measured on **raw** bytes — under WR-ZipGuard's
constraint that the receiver is **commodity BF3 doing one standard deflate decompress**?

**Verdict: GREEN.** A cheap reversible **byte-transpose** rehabilitates **bf16** (the default KV dtype)
from α≈0.79–0.80 to **≈0.70–0.71** on real gpt2 + Qwen2.5-7B KV — clearing 0.75. The split does **not**
help fp8 (no-op for 1-byte formats; bit-split makes them worse). It widens the *dtype* set, **not** the
M3 *bandwidth* region. See `M1_5_REPORT.md` and `../../refine-logs/EVALUATION_CONTRACT_M1.5.md`.

## Modules (reuses the M1 harness via `tests/conftest.py` path shim — no copied codec/generator)

| File | Role |
|---|---|
| `floatsplit.py` | Reversible transforms: `byte_transpose` (SoA permutation) and `bitplane` (field split). Bit-exact `transform`/`invert`, `split_planes`/`join_planes`, `split_fields`. |
| `split_measure.py` | `measure_transform(chunk, dtype, method)` → raw vs concat vs per-plane α, exponent/mantissa plane α, transform throughput, bit-exact assertion. Reuses `m1_codecs`. |
| `run_split.py` | Sweep driver: `synthetic` (reuses `synth`) and `capture` (real KV via `capture_hf_kv` helpers) → JSONL. |
| `analyze_split.py` | Aggregate + go/no-go. `classify` (rehabilitated/improved/regressed/neutral), `aggregate`, `decide` (GREEN requires rehabilitation on **captured** KV). |
| `m15_results.json` | Distilled committed result (per-source medians + verdict + provenance). |

## Run

```bash
# tests (49)
../m1/.venv/bin/python -m pytest tests/ -q

# synthetic sweep + real captures (on the box; PYTHONPATH adds the reused M1 modules)
PYTHONPATH=../m1 python run_split.py synthetic --out m15_outputs/split_synth.jsonl
PYTHONPATH=../m1 python run_split.py capture --model gpt2 --out m15_outputs/split_gpt2.jsonl
PYTHONPATH=../m1 HF_ENDPOINT=https://hf-mirror.com python run_split.py capture \
    --model Qwen/Qwen2.5-7B --out m15_outputs/split_qwen7b.jsonl --phases prefill --max-new-tokens 0

# verdict
PYTHONPATH=../m1 python analyze_split.py \
    --corpus m15_outputs/split_gpt2.jsonl m15_outputs/split_qwen7b.jsonl m15_outputs/split_synth.jsonl \
    --out m15_outputs/split_analysis.json
```

Claimable α is **`concat`** (one deflate stream BF3 decompresses). `per-plane` (mantissa stored raw) is
the DietGPU-style **ceiling, not BF3-claimable**. Verdict is decided on **captured** KV; the
standard-normal synthetic generator inflates the exponent plane.
