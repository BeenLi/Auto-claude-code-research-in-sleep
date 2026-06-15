# M1 — Real Tensor Compressibility Corpus

Cheapest go/no-go for WR-ZipGuard (`refine-logs/M1_CHECKLIST.md`,
`refine-logs/EVALUATION_CONTRACT.md`): measure the lossless compression-ratio
distribution of real LLM KV bytes under BF3-relevant codecs (deflate, LZ4) plus
references (zstd), and decide GREEN / YELLOW / RED.

## Design

Two-legged corpus, cross-validated:

- **Synthetic (primary, breadth)** — `run_corpus.py`. numpy + ml_dtypes generate
  BF16/FP8 K/V tensors over the full coverage grid; streaming (generate → measure →
  append JSONL row → discard), so disk stays ~MB and the 50 GB requirement is moot.
- **Captured (anchor, ground truth)** — `capture_hf_kv.py`. HF CPU forward on an
  ungated model (gpt2 default; Qwen2.5-7B / Mistral-7B for larger anchors) yields
  real K/V from `past_key_values`, measured through the same codec matrix.
- **Validity guard** — `validate_overlap.py`. At overlapping configs, synthetic vs
  captured ratio distributions must match, else recalibrate the generator. This is
  what earns the word "measured" in the negative-result framing.

Pure logic (break-even math, codecs, chunking, entropy, schema, go/no-go decision,
overlap comparator) is unit-tested; the CLI loops are glue.

## Setup

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# capture leg only:
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-capture.txt
```

## Run

```bash
pytest tests/ -q                                   # 62 tests

# smoke (seconds):
python run_corpus.py --out m1_outputs/smoke.jsonl --models tiny --seq-lens 256 \
  --seeds 42 --max-chunks-per-config 2 --repeats 2
python capture_hf_kv.py --model gpt2 --out m1_outputs/cap_smoke.jsonl \
  --seq-len 128 --max-new-tokens 16 --max-chunks-per-config 2 --repeats 2

# full synthetic sweep (hours; embarrassingly parallel over the grid):
python run_corpus.py --out m1_outputs/compressibility_corpus.jsonl

# analysis + go/no-go:
python analyze.py --corpus m1_outputs/compressibility_corpus.jsonl \
  --out m1_outputs/threshold_analysis.json

# validity guard:
python validate_overlap.py --synthetic m1_outputs/compressibility_corpus.jsonl \
  --captured m1_outputs/captured_corpus.jsonl
```
