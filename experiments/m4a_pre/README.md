# M4a preliminaries: T-inverse placement bench + transform-aware break-even

Contract: `refine-logs/EVALUATION_CONTRACT_T_INVERSE.md` (pre-registered before measurement).

- `tinv_bench.c` — C implementation of the receive-side inverses (`bt⁻¹` interleave,
  `chan⁻¹` cache-blocked value transpose; composed for bf16). Correctness anchored to the
  unit-tested Python reference via golden vectors. `verify` and `bench` (multi-chunk
  thread parallelism) modes.
- `make_golden.py` — golden-vector generator (Python forward → C must invert bit-exactly).
  `PYTHONPATH=../m1:../m1_5:../m1_6 ../.m15venv/bin/python make_golden.py`
- `frontier_tinv.py` — transform-aware B_crit scenarios over the measured numbers, using the
  TDD'd closed forms in `m1/profitability.py` (`*_with_transform`).
  `PYTHONPATH=../m1 ../.m15venv/bin/python frontier_tinv.py` → `tinv_frontier.json`
- `tinv_results.jsonl` — raw bench rows from bf3_server host CPU (2026-07-06).

Build: `cc -O3 -march=native -o tinv_bench tinv_bench.c -lpthread`

Verify: `./tinv_bench verify golden/<tag>.orig golden/<tag>.trans <bf16|fp8> <head_dim> <chan|chan_bt>`

Bench: `./tinv_bench bench <chunk_bytes> <head_dim> <bf16|fp8> <chan|chan_bt> <threads> <seconds>`

DPU-ARM leg: BLOCKED — BF3 card absent from bf3_server PCIe bus since the 2026-07-01 reboot
(no 15b3 devices; rescan ineffective). Re-run the same protocol on the ARM when recovered.
