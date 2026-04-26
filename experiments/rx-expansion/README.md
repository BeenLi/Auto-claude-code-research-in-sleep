# Rx Expansion Trace/Payload Evidence

This experiment package enforces the reviewer-requested split between communication schedule realism and payload compression realism.

- `schedule_trace` describes when communication happens and how large each message is. Chakra/ASTRA-sim traces belong here and are **schedule-only** evidence.
- `compression_profile` describes what byte pattern was compressed by which codec and how many bytes remained. This is the only source allowed to claim payload compressibility.
- A composed ratio trace is `schedule_trace x compression_profile`; every row keeps both `schedule_source` and `payload_source`.

## Evidence Levels

| Level | Meaning | Strongest Allowed Claim |
| --- | --- | --- |
| `P0_literature_ratio` | Ratio reported or derived from papers | Analytical sensitivity only |
| `P1_real_tensor_bytes` | Real tensor/checkpoint/KV/activation bytes, not necessarily communication payload | Tensor-payload plausibility |
| `P2_real_comm_bucket` | PyTorch DDP `GradBucket.buffer()` or equivalent real communication bucket | Real communication payload risk |
| `P3_artifact_payload` | NetZIP-like public artifact payload | Real communication payload risk |

Synthetic bytes are never allowed to be labeled as `P1`, `P2`, or `P3`.
