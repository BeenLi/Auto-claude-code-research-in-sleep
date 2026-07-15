# Evidence — ISCAS 2027 single-board pivot survey (2026-07-15)

Immutable snapshot of the 11-agent web survey (7 domain sweeps + 4 primary-source
verifiers, 10/10 usable reports; the `platform_matrix` sweep died mid-run but its
load-bearing questions were covered by the `v_board`/`v_shells` verifiers) that grounds
the ISCAS 2027 single-board pivot decision. Run 2026-07-14/15, workflow run id
`wf_31b78323-7b6`, ~1.19M subagent tokens, 517 tool calls.

## Files

- `survey-workflow-reports.json` — all 10 structured reports verbatim (summary, details,
  sources with URLs). Report keys:
  - `venue_fit` / `v_iscas` — ISCAS 2027 CFP verified: deadline 2026-10-13, 4 pages
    technical + references-only 5th page, single-blind, ~45% target acceptance,
    "High-Performance Computing for AI" track; precedent papers incl. XNC (ISCAS'25)
    and the ZSTD-FSE accelerator (ISCAS'25); LEXI (arXiv 2603.15589) flagged as the
    closest technical neighbor / must-cite threat.
  - `v_board` — VCU118 verified from UG1224/DS890/PG203: 2× QSFP28 on independent GTY
    quads, 9 hard CMACs on XCVU9P, 2×100G simultaneous OK → one-board port-to-port
    100G loopback; PCIe Gen3 x16 (~10–13 GB/s streaming); 2×2.5 GB DDR4.
  - `v_shells` — Corundum is the only open NIC shell with first-class VCU118 support
    (2×100G CMAC variants; repo dormant-but-stable); Coyote v2 / OpenNIC = Alveo-only;
    ERNIC = $92,400/yr license, not viable.
  - `compression_cores` / `v_deflate` — Vitis DCL gzip/zlib compress: 2 GB/s per CU,
    dynamic Huffman, ratio 2.70 Silesia (≈ zlib-1 class, −13% vs zlib-6), ~54K
    LUT/CU on VU9P-class silicon; 2–3 CUs cover the M3 profitable region; static-Huffman
    designs pay −20…−27% on text corpora. Transform = buffering problem (URAM), not logic.
  - `single_board_eval` — peer-reviewed single-board eval precedents: PIEO (SIGCOMM'19,
    on-chip traffic gen + token-bucket rate limiters 0.1–32 Gbps), Tonic (NSDI'20),
    nanoPU (OSDI'21), NetZIP (MICRO'25, no RDMA stack, SimAI headline); claim-boundary
    phrasing patterns.
  - `gating_prior_art` — gate novelty verdict: broad claims REFUTED (Intel IAA
    early-abort, WD entropy-detector patents US9710166/US9946464, 3Com US6763031,
    IBM US5555377, V.42bis, IPComp, NEC US9807189); the narrow conjunction
    (per-message × pre-compression streaming estimator × measured wire-time
    profitability arithmetic × lossless commodity-decodable stream on a NIC TX path)
    NOT FOUND — with the prior art recast as the on-board gate baseline suite.
  - `kv_offload_landscape` — the sender-FPGA "transform + standard deflate + gate →
    stock-BF3-decodable KV stream" combination is unpublished; nearest attack surfaces
    ShadowServe / NetZIP / TRACE with their exact eval setups (all ≤ single-node,
    emulated, or simulation-only); ShadowServe's ≤20 Gbps profitable window
    independently corroborates M3.
  - `fresh_alternatives` — ranked alternative ideas (C1 verbs-preserving inline
    transform engine, C2 layout-transform circuit, C3 Google PSP first FPGA impl,
    C4 in-NIC KV prefix-match, C5 UET packet trimming) + saturation-evidence rejection
    table (PIFO/shapers/AES-GCM/ML-classification/RPC/collectives/CXL).

## What this decided

Plan of record: `/Users/bytedance/.claude/plans/wr-zipguard-obsidian-users-bytedance-li-crispy-goose.md`
(approved interactively 2026-07-15). User decisions: topic fully open → maximize
acceptance → half-time budget → **run E0 pre-check, then choose Topic A (KV egress
datapath) vs Topic B (PSP)**. E0 contract: `refine-logs/EVALUATION_CONTRACT_E0.md`
(pre-registered before data). E0 outcome lives in `experiments/m_e0/`, not here —
this directory never mutates.
