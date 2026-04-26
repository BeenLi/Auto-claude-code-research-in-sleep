"""DDP GradBucket payload evidence helpers.

This module is intentionally torch-optional. The real DDP hook can pass a
``torch.distributed.GradBucket`` whose ``buffer()`` is tensor-like, while tests
can use ``BytesGradBucket`` to exercise the provenance and size checks without
requiring PyTorch in the ARIS environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from . import trace_payload


@dataclass
class BytesGradBucket:
    """Small test/dry-run stand-in for ``torch.distributed.GradBucket``."""

    payload: bytes

    def buffer(self) -> bytes:
        return self.payload


def buffer_to_bytes(buffer: object) -> bytes:
    """Convert a DDP bucket buffer or bytes-like test object to bytes."""

    if isinstance(buffer, bytes):
        return buffer
    if isinstance(buffer, bytearray):
        return bytes(buffer)
    if isinstance(buffer, memoryview):
        return buffer.tobytes()
    if hasattr(buffer, "detach"):
        buffer = buffer.detach()
    if hasattr(buffer, "cpu"):
        buffer = buffer.cpu()
    if hasattr(buffer, "numpy"):
        return buffer.numpy().tobytes()
    if hasattr(buffer, "tobytes"):
        return buffer.tobytes()
    raise trace_payload.ProvenanceError("GradBucket buffer must be bytes-like or tensor-like")


def capture_grad_bucket_bytes(bucket: object) -> bytes:
    """Extract raw bytes from a GradBucket-like object."""

    if not hasattr(bucket, "buffer"):
        raise trace_payload.ProvenanceError("DDP GradBucket object must expose buffer()")
    return buffer_to_bytes(bucket.buffer())


def profile_grad_bucket_bytes(
    bucket: object,
    *,
    payload_source: str,
    codec_family: str,
    compressed_bytes: int,
    dtype: str,
    tensor_role: str,
    chunk_size: int,
    provenance: str,
    recorded_original_bytes: Optional[int] = None,
) -> Dict[str, object]:
    """Build a P2 profile from an already captured/compressed DDP bucket."""

    payload = capture_grad_bucket_bytes(bucket)
    original_bytes = len(payload)
    if recorded_original_bytes is not None and recorded_original_bytes != original_bytes:
        raise trace_payload.ProvenanceError(
            f"bucket size mismatch: recorded {recorded_original_bytes}, captured {original_bytes}"
        )

    profile = {
        "codec_family": codec_family,
        "payload_source": payload_source,
        "evidence_level": "P2_real_comm_bucket",
        "original_bytes": original_bytes,
        "compressed_bytes": compressed_bytes,
        "ratio": original_bytes / compressed_bytes,
        "chunk_size": chunk_size,
        "dtype": dtype,
        "tensor_role": tensor_role,
        "provenance": provenance,
    }
    return trace_payload.validate_compression_profiles([profile])[0]
