# Optional P2 DDP Bucket Capture

P2 evidence requires bytes that actually entered a communication bucket. For PyTorch DDP, the intended hook point is `torch.distributed.GradBucket.buffer()` inside a registered DDP communication hook.

Minimum capture record per bucket:

| Field | Meaning |
| --- | --- |
| `payload_source` | Stable name such as `ddp_rank0_bucket7_step3` |
| `original_bytes` | Number of bytes in `GradBucket.buffer()` |
| `codec_family` | Codec used after capture, such as `lz4` |
| `compressed_bytes` | Bytes after the measured codec run |
| `dtype` | Bucket dtype |
| `tensor_role` | `gradient_bucket` |
| `provenance` | Training script, rank, step, bucket index, hook name, codec command |

The helper `rx_expansion.ddp_capture.profile_grad_bucket_bytes` verifies that any recorded bucket size matches the captured buffer length before labeling a profile as `P2_real_comm_bucket`.
