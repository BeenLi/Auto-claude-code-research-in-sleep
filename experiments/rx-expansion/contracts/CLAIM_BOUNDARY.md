# Claim Boundary for M0/M1

## Allowed With P0 Only

- Analytical sensitivity to literature-derived compression ratios.
- Break-even surfaces under explicitly stated codec-family assumptions.
- Discussion of which codec families could create output-byte pressure.

## Allowed With P1

- Real tensor bytes can create output-byte pressure in the analytical model.
- Tensor-payload plausibility for entering M2 standalone simulation.

P1 does not prove real communication payload compressibility because checkpoint, KV, activation, or weight files may not match actual RDMA/DDP bucket contents.

## Allowed With P2 or P3

- Real communication payloads show compressed-wire versus decompressed-output mismatch.
- The work may claim real compressed communication payload risk, still subject to RDMA contract and simulator validation.

## Disallowed In M0/M1

- Chakra/ASTRA-sim traces prove payload compressibility.
- Synthetic payloads are real tensor or communication payloads.
- Line-rate RoCE correctness.
- Production DCQCN/PFC behavior.
- PCIe transaction-level validation.
- Energy, timing closure, or end-to-end LLM serving speedup.
