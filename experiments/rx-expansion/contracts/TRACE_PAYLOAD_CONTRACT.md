# Trace/Payload Contract for Compressed RDMA M0/M1

## Schedule Trace

`schedule_trace` is the communication-shape input. Chakra and ASTRA-sim traces are schedule-only sources: they may provide operation type, timing, message size, source/destination, dependencies, and phase, but they do not provide tensor payload values or codec compressibility.

Required normalized fields:

| Field | Meaning |
| --- | --- |
| `timestamp_ns` | Communication event time in nanoseconds |
| `op_type` | Collective or point-to-point operation name |
| `message_bytes` | Original uncompressed message size represented by the event |
| `src` | Source rank/node identifier |
| `dst` | Destination rank/node identifier |
| `flow_id` | Flow or logical communication stream |
| `tenant_id` | Tenant/workload class |
| `phase` | Model/runtime phase, such as backward, activation, checkpoint, or control |

Normalized schedule rows must be marked with `schedule_realism = schedule_only`.

## Compression Profile

`compression_profile` is the payload/codec evidence input. It is independent of the schedule trace.

Required fields:

| Field | Meaning |
| --- | --- |
| `codec_family` | Codec or codec-like family, such as LZ4, EBPC, Quad/e4m3, ZipServ-like |
| `payload_source` | Exact source of payload or literature ratio |
| `evidence_level` | `P0_literature_ratio`, `P1_real_tensor_bytes`, `P2_real_comm_bucket`, or `P3_artifact_payload` |
| `original_bytes` | Bytes before compression |
| `compressed_bytes` | Bytes after compression |
| `ratio` | `original_bytes / compressed_bytes` |
| `chunk_size` | Chunk size used by the ratio-trace composition step |
| `dtype` | Payload dtype or dtype family |
| `tensor_role` | Role such as gradient bucket, activation, checkpoint, KV, weight, control |
| `provenance` | Human-readable source note sufficient for reviewer audit |

Synthetic or generated payloads may be useful for software smoke tests, but they cannot be marked as `P1`, `P2`, or `P3`.

## Composition Rule

The ratio trace is a Cartesian composition of communication schedule rows and compression profiles. Every composed row must retain:

- `schedule_source`
- `schedule_realism`
- `payload_source`
- `payload_realism`
- `evidence_level`
- `source_pair`
- `provenance`

No figure, table, or review packet may label a row as a real compressed communication workload unless the compression profile evidence level is `P2_real_comm_bucket` or `P3_artifact_payload`.
