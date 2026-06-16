# M3 Report — Profitability Sweep (analytical frontier + LLMServingSim cross-check)

**Milestone gate (EXPERIMENT_PLAN Block 3, claim C3):** does a bandwidth-limited profitable region
for KV-cache compression exist, before any FPGA (M4b) spend?

**Verdict: YELLOW — a profitable region exists but is narrow and bandwidth-limited.** Proceed with a
*narrowed* claimed regime: KV compression pays on **bandwidth-limited fabrics (≲17 Gbps with a
realistic FPGA compressor; ≲50 Gbps as a hard ceiling)** — i.e. cross-AZ / oversubscribed / WAN-ish
links, **not** mainstream 100–400 Gbps datacenter interconnects. This is consistent with the M1
"GREEN (narrow)" result and the project thesis (compression for bandwidth-limited, not line-rate,
flows).

## Method — two layers

1. **Analytical frontier (oracle, `experiments/m3/`)** — reuses the unit-tested break-even math from
   `experiments/m1/profitability.py`, with the decompress rate chunk-coupled as `D = α·D_egress(S)`
   (M2 measured curve). 46 unit tests. Inputs are the committed measured envelope
   (`measured_inputs.json`): FP8_E5M2 deflate α≈0.73 (M1), D_egress(chunk) (M2), T_fixed≈5µs (M2),
   software 17 MB/s + FPGA band 25/50/100 Gbps.
2. **LLMServingSim cross-check (scoped)** — the deployed simulator on myDevbox (v1.1.0, PD
   disaggregation, ASTRA-Sim analytical backend). Rather than patching the sim's policy logic, we
   verify its PD KV-transfer cost obeys the same `bytes/link_bw` physics the frontier assumes.

## Result 1 — analytical frontier (the go/no-go)

For the measured envelope (FP8_E5M2 α=0.732, 2 MB chunk), the critical link rate below which
compression beats raw:

| FPGA compress band | B_crit (profitable iff B <) |
|---|---|
| 25 Gbps | 5.9 Gbps |
| 50 Gbps | 10.5 Gbps |
| 100 Gbps | 17.2 Gbps |

**Why so narrow:** α≈0.73 yields only ~27% wire saving, which must exceed the compress + decompress
+ fixed overheads. Even with a *free, infinitely fast* compressor, the decompress egress ceiling
caps the region at `B < (1-α)·D_egress ≈ 0.27 × 188 ≈ 50 Gbps`. So realistic-KV compression
**structurally cannot** pay at mainstream datacenter rates, independent of compressor speed.
Software compress (17 MB/s) **never** pays at any real link rate — confirming the asymmetric design
(FPGA compress + commodity decompress) is mandatory.

Figures (data in `m3_outputs/`, render with `make_figures.py` where matplotlib is available):
- **Figure 3** — profitability frontier heatmap (gain vs link rate × chunk).
- **Figure 4** — policy comparison (raw / always / static / gate transfer time vs link rate). The
  gate never regresses vs raw (bypasses unprofitable chunks); always-compress loses to raw in the
  no-gain regime — which is most of the datacenter-rate range.

## Result 2 — LLMServingSim cross-check (PASS)

Setup: `single_node_pd_instance.json`, Llama-3.1-8B, bf16, one 2048-token prompt (2 decode tokens),
`--no-enable-prefix-caching` (the PD+prefix-cache path crashes on this branch), `link_bw` swept
1→64 GB/s. Raw data: `sim_sweep_result.json`.

| link_bw (GB/s) | 1 | 2 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|---|
| TTFT (ms) | 751 | 376 | 188 | 94.7 | 83.0 | 83.0 | 83.0 |

- **Transfer-limited regime (bw ≤ 8):** TTFT follows `A + M/bw` with **R² = 1.000000** — a clean
  `1/link_bw` law. This confirms the sim's PD KV transfer time is **bandwidth-limited, scaling as
  bytes/bandwidth** — exactly the physics the analytical frontier rests on, and precisely the
  low-bandwidth regime where compression matters.
- **Compute-limited regime (bw ≥ 16):** TTFT floors at the prefill compute time (~83 ms); transfer
  is hidden. **TPOT is invariant to link_bw** (decode is compute-bound), as expected.
- **Payload factor:** implied transferred payload ≈ 750 MB = **2.79×** the minimal KV-cache size
  (256 MB). The sim moves a larger payload than raw KV (likely activation/hidden state alongside the
  KV handoff). This does **not** affect the validated scaling law; it is recorded as a modeling note.

**Cross-check conclusion:** the simulator independently corroborates that PD KV transfer is
bandwidth-limited (`transfer_time ∝ bytes / link_bw`), so the analytical frontier's transfer model —
and therefore its profitable-region geometry — is sound.

## Caveats & honest scope

- **bf16, not FP8, in the sim:** only a bf16 profile exists in the deployed sim
  (`profiler/perf/.../Llama-3.1-8B/bf16`); the cross-check validates the transfer *model* (scaling),
  not FP8-specific TTFT numbers.
- **M2 decompress ceiling caveat carries forward:** the ~188 Gbps D_egress may be a PCIe-x8 artifact
  (host write-back saturated), so the true profitable window could be ~2× wider (~100 Gbps) on a x16
  slot / DPU-local memory. The frontier reports the boundary; the caveat travels with it.
- **Full policy injection deferred:** measuring real TTFT/TPOT under the four policies inside the sim
  would require deep Chakra/ASTRA comm instrumentation, an FP8-KV profile, and long-context
  workloads — out of scope for this scoped cross-check (user-approved).

## Bottom line for the pipeline

M3 is **YELLOW**: a real but narrow, bandwidth-limited profitable region. The per-WR gate is
*essential* (not optional) precisely because the profitable region is narrow — it must bypass the
large no-gain regime without regression. Recommend proceeding to M4a (integrated RDMA prototype) /
M4b (FPGA compressor) with the **claimed regime narrowed to bandwidth-limited fabrics (≲~50 Gbps,
possibly ~100 Gbps if the M2 ceiling is x8-limited)**.
