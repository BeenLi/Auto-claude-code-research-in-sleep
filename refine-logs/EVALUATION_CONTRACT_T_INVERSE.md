# Evaluation Contract — T-inverse Off-GPU Placement (M4a preliminary #1)

**Status:** RESOLVED **YELLOW (both paths)** on the host-CPU leg, 2026-07-06 (same day; DPU-ARM leg
still BLOCKED — card absent). Measured on bf3_server 192-core x86, gcc -O3, bit-exact vs Python
golden vectors on all 6 pairs (C fresh-implementation cross-check):
**bf16 chan_bt⁻¹**: 2.04 GB/s single-thread @2MiB (< R_f) → needs **2 threads** for R_f, **12** for
R_e; linear scaling (16T = 32.3 GB/s). **fp8 chan⁻¹**: 1.39 GB/s single-thread → **3 threads** for
R_f, **~17** for R_e (16T = 22.2, just under). No GREEN because single-thread misses R_f; no RED.
**Break-even integration** (`experiments/m4a_pre/tinv_frontier.json`, closed forms in
`m1/profitability.py`): charging the inverse *narrows B_crit materially* — fp8_e5m2 raw (no
transform) 16.2 Gbps vs chan@8T-inverse 10.7 / @16T 13.4 Gbps → **on the B_crit axis the chan
transform does NOT pay vs raw fp8 on host-CPU inverse**; its α win is repaid only if the inverse is
~free (DPU-ARM/engine/FPGA — M4a/M4b design requirement, now with a number attached). bf16 (no raw
fallback): FPGA-sender + 8T inverse → B_crit 12.2 Gbps (vs 17.9 hypothetical-free); software sender
kills both paths (≤3.9 Gbps). Raw data `experiments/m4a_pre/tinv_results.jsonl`.

## Question

Can the receive-side inverse transform (bf16: `bt⁻¹` then `chan⁻¹`; fp8: `chan⁻¹` alone) run
**off-GPU** — on the receive host's CPU (and eventually the BF3 DPU-ARM) — at a throughput that does
not erase the wire-time savings? This has been an open item since M1.5: **if the inverse cannot run
off-GPU at line rate, the "receiver GPU untouched" differentiator (C2) is void.**

## Why now / context

- bf3_client is down (user-reported); **the BF3 card on bf3_server has been absent from the PCIe
  bus since the 2026-07-01 reboot** (zero 15b3 devices in lspci/sysfs; rescan ineffective; kernel
  log shows the card never enumerated this boot). The DPU-ARM leg is therefore **BLOCKED** pending
  card recovery. The **host-CPU leg needs no card**: bf3_server's x86 host (192 cores) IS the
  receive-side host CPU of the deployment story.
- Measurement implementation is **C** (gcc on bf3_server; no numpy/pip there, Python 3.7 only) —
  which is also the honest deployment-grade measurement. Correctness is anchored by **golden
  vectors** generated from the unit-tested Python reference (`experiments/m1_6/layout.py`,
  69 tests): the C inverse must reproduce the original buffer **bit-exactly** from the Python
  forward transform's output.

## Pre-registered thresholds (host-CPU leg)

Let X_inv = median inverse throughput in **original (decompressed) bytes per second**, measured on
bf3_server host CPU, chunk sizes 256 KB / 1 MB / 2 MB, head_dim 64 and 128, after warmup, ≥5
repeats. Two reference rates (both fixed before measurement):

- **Frontier rate** `R_f` ≈ **3.75 GB/s** — decompressed egress needed at the widest measured
  B_crit (~21 Gbps compressed wire at α≈0.70 ⇒ ~30 Gbps ≈ 3.75 GB/s of inverse work).
- **Engine rate** `R_e` ≈ **23.5 GB/s** — M2's measured decompress egress ceiling (~188 Gbps);
  above this the inverse can never be the added bottleneck in THIS setup.

Verdict (per dtype-path: bf16 = chan_bt⁻¹ composed, fp8_e5m2 = chan⁻¹):

- **GREEN** — single-thread X_inv ≥ R_f **and** aggregate X_inv with ≤ 8 threads ≥ R_e, bit-exact.
  (Inverse keeps up at the frontier on one core and disappears as a bottleneck with a modest core
  budget.)
- **YELLOW** — aggregate X_inv ≥ R_f with ≤ 16 threads, but single-thread < R_f or reaching R_e
  needs > 8 threads. (Feasible with parallelism; report the core budget as a deployment cost.)
- **RED** — aggregate X_inv < R_f even at 16 threads: the off-GPU inverse cannot keep up at the
  frontier → the layout-transform path (M1.5/M1.6) loses its off-GPU claim; fall back to raw-fp8
  path or move the inverse into hardware (FPGA/engine) — a scope change to be recorded, not spun.
- **Disqualifier** regardless of throughput: any bit-exact mismatch vs the Python golden vectors.

## Scope

- Measures the inverse **in isolation** (memory-to-memory, warm buffers). Overlap with decompress
  and RDMA arrival is M4a's job; numbers here are the *upper bound* on inverse cost, used
  additively (conservative) in the extended break-even model (see companion change to
  `experiments/m1/profitability.py`).
- Forward-transform throughput X_fwd is NOT re-measured here; the M1.6 medians (single-thread
  numpy on myDevbox: chan_bt ≈ 1.45 GB/s, chan ≈ 2.36 GB/s) are used as the conservative sender
  cost until an optimized sender exists (M4b's problem).
- **DPU-ARM leg (SHOULD, blocked):** same protocol, same thresholds scaled by no fixed factor —
  pre-register only the *question* (can BF3's ARM cores sustain ≥ R_f?); numbers to be filled when
  the card is back. Also blocked: the M2 host-vs-DPU-memory ceiling test.

## What we CAN claim if GREEN/YELLOW

- The receive-side inverse is a real off-GPU operation at deployment-relevant rates on commodity
  host CPUs (with the measured core budget); C2's "receiver GPU untouched" survives the layout
  transforms.

## What we CANNOT claim (any verdict)

- Nothing about DPU-ARM placement until measured.
- Nothing about overlapped/pipelined behavior (M4a).
- The C implementation is cache-blocked but not SIMD-hand-tuned; numbers are a floor, not a ceiling.
