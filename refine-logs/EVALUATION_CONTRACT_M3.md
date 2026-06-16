# Evaluation Contract — WR-ZipGuard M3 (Profitability Sweep)

> Workflow 1.5 (experiment-bridge) gate, written before implementation.
> **Scope: M3 only** (Block 3 of `EXPERIMENT_PLAN.md`, tracker R012). M3 is the project-wide
> go/no-go: *does a bandwidth-limited profitable region for KV-cache compression exist, before any
> FPGA (M4b) spend?* It consumes the measured M1/M2 envelopes; it introduces no new measurement of
> tensors or silicon.

## Substrate decision

**Two-layer M3** (user-approved):

1. **Layer 1 — analytical frontier (oracle):** self-contained CPU sweep in `experiments/m3/`,
   reusing the unit-tested break-even math in `experiments/m1/profitability.py`. Fast, no external
   deps; serves as the cross-check that validates Layer 2's compression injection.
2. **Layer 2 — LLMServingSim (primary):** the deployed simulator on myDevbox
   (`/home/wanli.99/autoResearch/LLMServingSim`, v1.1.0, ASTRA-Sim backend, PD disaggregation, FP8
   KV, TTFT/TPOT). Compression is injected at the prefill→decode KV transfer
   (`serving/core/router.py:transfer_prefill_request`) behind a flagged `--kv-compression` config
   (raw default); `link_bw` is the link-rate sweep knob. Delivers the real TTFT/TPOT verdict.

## Injected envelope — all from measured M1/M2 sources

| Parameter | Symbol | Source | Value |
|---|---|---|---|
| Compression ratio (FP8_E5M2 deflate) | α | M1 (`EXPERIMENT_LOG.md` L38–42, L86–90) | p50 0.715 synthetic; real gpt2 0.729–0.735; real Qwen2.5-7B 0.732; deflate-1 marginal ≈0.75. Entropy floor 0.686. |
| Decompress egress throughput | D_egress(S) | M2 (`EXPERIMENT_LOG.md` L178–183) | 4KB→6.5, 64KB→75, 256KB→141, 1MB→180, 2MB→188 Gbps |
| Decompress fixed cost | T_fixed | M2 (R005) | ≈ 5 µs/task; amortizes only at ≥256 KB |
| Compress throughput (software) | C_sw | M1 (L65, L72) | 17 MB/s (deflate-6/9), 32 MB/s (deflate-1) — provably never pays |
| Compress throughput (FPGA band) | C_fpga | **assumption** — NetZIP MICRO 2025 + FPGA deflate IP datasheets | 25 / 50 / 100 Gbps band; **to be measured in M4b**, flagged as assumption not measurement |

### Units reconciliation (decisive for correctness)
`profitability.py` models the decompress term as `α·S/D`, where `D` consumes **compressed-input**
bytes. M2's table is **egress (decompressed-output)** rate. They relate by `D_input = α · D_egress`
(decompress reads α·S compressed bytes and writes S bytes in the same time). The log confirms this:
"~135 Gbps input" ≈ 0.72 × "~188 Gbps egress". **The frontier must feed `D = α · D_egress(S)`**,
not `D_egress` directly. `measured_inputs.json` stores the measured egress curve; the conversion is
explicit and unit-tested.

## Compared systems (policies)

- **raw** — no compression (α = 1); the core baseline.
- **always-compress** — compress every chunk (straw-man upper bound).
- **static-threshold(S₀)** — compress iff chunk ≥ S₀ (KVServe/SplitZip-style heuristic).
- **wr_zipguard_gate** — per-chunk: compress iff `is_profitable` under sampled α + estimated B.

## Metrics

- **Decisive:** transfer-time delta and bytes-on-wire vs raw (Layer 1 directly; Layer 2 via the
  ASTRA-Sim transfer cost). TTFT/TPOT is the headline framing, supplied by Layer 2.
- **Supporting:** profitable-region bounds in (B, chunk, α); false-decision rate of the gate
  (compressing a no-gain chunk / bypassing a profitable one).

## Success / go-no-go (project-wide gate)

- **GREEN**: a bandwidth-limited regime exists where `wr_zipguard_gate` improves the end-to-end
  metric over **both** `raw` and `always-compress`, while correctly bypassing the no-gain regime
  (B ≳ D_eff or non-FP8_E5M2) with no regression vs raw. Both layers must agree at matching configs,
  and both must reproduce the M2 triply-bounded region (FP8_E5M2 × B < ~188 Gbps × chunk ≥ 256 KB).
- **YELLOW**: a profitable region exists but only in a narrow bandwidth window (e.g. cross-AZ /
  oversubscribed fabrics) or only with the optimistic α/FPGA band → proceed but flag the narrow window.
- **RED**: no profitable region under the measured envelopes → pivot to the negative-result /
  profitability-atlas paper ("commodity-DPU-decompressible KV compression is not viable under these
  parameters"). Consistent with the Block 2 / M1-RED pivot.

## Known modeling assumptions (recorded, not hidden)

1. **FPGA compress band is an assumption** (M4b will measure it). Software compress is included to
   show it never pays at real link rates — the asymmetric-design justification.
2. **Chunk-aggregation**: the PD transfer granularity ≈ per-request KV
   (`kv_prefill × one_token_kv_size`), which is ≥256 KB for long-context FP8 — the ≥256 KB gate is
   satisfiable. D_eff applies at the aggregated transfer size.
3. **Scaling ceiling caveat from M2** carries forward: the ~188 Gbps boundary may be a PCIe-x8
   artifact, so the true profitable bandwidth ceiling could be ~2× higher on x16 / DPU-local memory.
   The sweep reports the boundary; the caveat is stated alongside.
4. **Analytical backend** for ASTRA-Sim (not ns3) — adequate for a link-rate profitability sweep.

## Outputs

- code: `experiments/m3/` (unit-tested Layer-1 modules + `sim_sweep.py` harness)
- sim change: flagged `--kv-compression` on a branch of `BeenLi/LLMServingSim`
- data/report: `m3_outputs/` (frontier grid, sim CSVs, Figure 3 heatmap, Figure 4 policy comparison,
  `M3_REPORT.md`)
- run log: `refine-logs/EXPERIMENT_LOG.md` (M3 result block), `EXPERIMENT_TRACKER.md` (R012)
