# M1 Go/No-Go Report

## Scope

This is a P0-only analytical sensitivity pack. It combines schedule-only smoke traces with literature-derived codec ratios. It does not claim real communication payload compressibility.

## Go/No-Go

- Decision: **Conditional Go for M2 model plumbing only**.
- Rows evaluated: 960.
- Output-unsafe rows: 384.
- Codec families: ebpc, quad_e4m3, zipserv_like.
- Output paths: cxl_or_pcie6_staging_like, gpu_direct_pcie5_x16_like, host_dram_pcie4_x16_like, host_dram_pcie5_x16_like.
- Offered-load modes: compressed_line_rate_saturated, same_original_bytes.

## Unsafe Rows by Codec / Payload / Mode

| Codec | Payload source | Offered-load mode | Unsafe rows |
| --- | --- | --- | ---: |
| ebpc | ebpc_alexnet_literature | compressed_line_rate_saturated | 72 |
| ebpc | ebpc_alexnet_literature | same_original_bytes | 24 |
| ebpc | ebpc_resnet34_literature | compressed_line_rate_saturated | 48 |
| ebpc | ebpc_resnet34_literature | same_original_bytes | 24 |
| ebpc | ebpc_vgg16_literature | compressed_line_rate_saturated | 72 |
| ebpc | ebpc_vgg16_literature | same_original_bytes | 24 |
| quad_e4m3 | quad_e4m3_literature | compressed_line_rate_saturated | 24 |
| quad_e4m3 | quad_e4m3_literature | same_original_bytes | 24 |
| zipserv_like | zipserv_max_model_size_reduction_literature | compressed_line_rate_saturated | 48 |
| zipserv_like | zipserv_max_model_size_reduction_literature | same_original_bytes | 24 |

## Interpretation Notes

- compressed_line_rate_saturated unsafe rows indicate ratio-driven output pressure under the P0 assumptions.
- same_original_bytes unsafe rows are fixed-output-path bottlenecks, not compression-created receiver pressure.

## Claim Boundary

- Claim scope: `analytical_sensitivity_only`.
- P0-only results can justify sensitivity discussion and Go/No-Go triage.
- P0-only results cannot justify a real communication payload claim.
- P1/P2/P3 collection is intentionally out of scope for this M1 pack.
