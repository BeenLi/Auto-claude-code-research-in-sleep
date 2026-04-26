"""Build LZ4 compression profiles from real local payload files."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

from . import trace_payload


def _resolve_lz4(lz4_path: Optional[str]) -> str:
    resolved = lz4_path or shutil.which("lz4")
    if not resolved:
        raise trace_payload.ProvenanceError("lz4 CLI is required for local measurement")
    return resolved


def _lz4_version(lz4_path: str) -> str:
    result = subprocess.run(
        [lz4_path, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    return " ".join(result.stdout.strip().split())


def measure_lz4_bytes(payload_path: Path, *, lz4_path: Optional[str] = None) -> Dict[str, int]:
    """Return original and compressed byte counts for a local payload file."""

    payload_path = Path(payload_path)
    if not payload_path.is_file():
        raise trace_payload.ProvenanceError(f"payload file does not exist: {payload_path}")

    resolved_lz4 = _resolve_lz4(lz4_path)
    result = subprocess.run(
        [resolved_lz4, "-q", "-c", str(payload_path)],
        check=True,
        capture_output=True,
    )
    return {
        "original_bytes": payload_path.stat().st_size,
        "compressed_bytes": len(result.stdout),
    }


def build_lz4_profile(
    payload_path: Path,
    *,
    payload_source: str,
    evidence_level: str,
    dtype: str,
    tensor_role: str,
    chunk_size: int,
    lz4_path: Optional[str] = None,
) -> Dict[str, object]:
    """Measure a local payload file and return a validated compression profile."""

    resolved_lz4 = _resolve_lz4(lz4_path)
    counts = measure_lz4_bytes(payload_path, lz4_path=resolved_lz4)
    if counts["original_bytes"] <= 0:
        raise trace_payload.ProvenanceError("payload file must be non-empty")

    profile = {
        "codec_family": "lz4",
        "payload_source": payload_source,
        "evidence_level": evidence_level,
        "original_bytes": counts["original_bytes"],
        "compressed_bytes": counts["compressed_bytes"],
        "ratio": counts["original_bytes"] / counts["compressed_bytes"],
        "chunk_size": chunk_size,
        "dtype": dtype,
        "tensor_role": tensor_role,
        "provenance": (
            f"Measured local file {Path(payload_path)} with "
            f"{_lz4_version(resolved_lz4)} at {resolved_lz4}."
        ),
    }
    return trace_payload.validate_compression_profiles([profile])[0]
