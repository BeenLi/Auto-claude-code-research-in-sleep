# M3 — Profitability Sweep (analytical frontier + LLMServingSim cross-check)

Project-wide go/no-go (EXPERIMENT_PLAN Block 3, claim C3): is there a bandwidth-limited profitable
region for KV-cache compression? See `../../refine-logs/EVALUATION_CONTRACT_M3.md` and `M3_REPORT.md`.

**Verdict: YELLOW** — narrow, bandwidth-limited region (≲17 Gbps realistic FPGA; ≲50 Gbps ceiling).

## Layers

- **Layer 1 (analytical oracle, pure stdlib):** the frontier physics + go/no-go verdict.
  - `measured_inputs.json` — committed measured envelope (M1 α, M2 D_eff curve, compress band).
  - `profitability_bridge.py` — re-exports `experiments/m1/profitability.py` (single source of math).
  - `deff_curve.py` — M2 D_egress(chunk) interpolation + the egress→input units reconciliation
    (`D_input = α·D_egress`).
  - `frontier.py` / `policies.py` — per-cell break-even sweep; raw/always/static/gate policies.
  - `analyze_m3.py` — B_crit + GREEN/YELLOW/RED verdict (`python analyze_m3.py`).
  - `plot_m3.py` / `make_figures.py` — Figure 3 (frontier heatmap) + Figure 4 (policy comparison).
- **Layer 2 (LLMServingSim cross-check):**
  - `sim_sweep.py` — reproducible link_bw sweep runner (runs on myDevbox inside the sim repo).
  - `crosscheck.py` — fits TTFT(link_bw) and confirms the sim's PD transfer is bandwidth-limited.
  - `sim_sweep_result.json` — the committed raw sweep data.

## Run

```bash
# Layer 1 (anywhere; stdlib only)
python -m pytest tests/ -q            # 46 unit tests
python analyze_m3.py                  # headline analytical verdict

# Layer 2 sweep (on myDevbox, inside LLMServingSim with the venv on PATH)
PATH=$PWD/env/bin:$PATH python sim_sweep.py --sim-root . --out m3_outputs/sim_sweep.json \
    --input-toks 2048 --link-bw 1 2 4 8 16 32 64

# Figures (where matplotlib is available)
python make_figures.py --out m3_outputs --sweep-json sim_sweep_result.json
```

Notes: the analytical core is dependency-free (scalar math). Only `make_figures.py` needs matplotlib.
The sim PD path requires `--no-enable-prefix-caching` on this branch (prefix-cache PD bug).
