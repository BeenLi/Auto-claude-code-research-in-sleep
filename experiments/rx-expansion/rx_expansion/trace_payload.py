"""Trace/payload evidence separation for compressed RDMA experiments."""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Mapping


SCHEDULE_REQUIRED_FIELDS = {
    "timestamp_ns",
    "op_type",
    "message_bytes",
    "src",
    "dst",
    "flow_id",
    "tenant_id",
    "phase",
}

COMPRESSION_REQUIRED_FIELDS = {
    "codec_family",
    "payload_source",
    "evidence_level",
    "original_bytes",
    "compressed_bytes",
    "ratio",
    "chunk_size",
    "dtype",
    "tensor_role",
    "provenance",
}

EVIDENCE_LEVELS = {
    "P0_literature_ratio": "literature_ratio",
    "P1_real_tensor_bytes": "real_tensor_bytes",
    "P2_real_comm_bucket": "real_comm_bucket",
    "P3_artifact_payload": "artifact_payload",
}


class ProvenanceError(ValueError):
    """Raised when trace/payload evidence provenance is unsafe or incomplete."""


def _missing(required: Iterable[str], row: Mapping[str, object]) -> List[str]:
    return sorted(field for field in required if field not in row)


def _as_positive_int(row: Mapping[str, object], field: str) -> int:
    value = row[field]
    if isinstance(value, bool):
        raise ProvenanceError(f"{field} must be a positive integer, got bool")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ProvenanceError(f"{field} must be a positive integer") from exc
    if parsed <= 0:
        raise ProvenanceError(f"{field} must be a positive integer")
    return parsed


def _as_positive_float(row: Mapping[str, object], field: str) -> float:
    value = row[field]
    if isinstance(value, bool):
        raise ProvenanceError(f"{field} must be a positive float, got bool")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ProvenanceError(f"{field} must be a positive float") from exc
    if parsed <= 0:
        raise ProvenanceError(f"{field} must be a positive float")
    return parsed


def _looks_synthetic(row: Mapping[str, object]) -> bool:
    haystack = " ".join(
        str(row.get(field, ""))
        for field in ("payload_source", "provenance", "tensor_role")
    ).lower()
    return "synthetic" in haystack or "generated" in haystack


def validate_schedule_trace(
    rows: Iterable[Mapping[str, object]],
    *,
    schedule_source: str,
) -> List[Dict[str, object]]:
    """Validate communication schedule rows without assigning payload realism."""

    if not schedule_source:
        raise ProvenanceError("schedule_source is required")

    normalized: List[Dict[str, object]] = []
    for index, row in enumerate(rows):
        missing = _missing(SCHEDULE_REQUIRED_FIELDS, row)
        if missing:
            raise ProvenanceError(f"schedule row {index} missing fields: {', '.join(missing)}")

        message_bytes = _as_positive_int(row, "message_bytes")
        timestamp_ns = int(row["timestamp_ns"])
        if timestamp_ns < 0:
            raise ProvenanceError("timestamp_ns must be non-negative")

        item = dict(row)
        item["timestamp_ns"] = timestamp_ns
        item["message_bytes"] = message_bytes
        item["schedule_source"] = schedule_source
        item["schedule_realism"] = "schedule_only"
        normalized.append(item)
    return normalized


def validate_compression_profiles(
    profiles: Iterable[Mapping[str, object]],
) -> List[Dict[str, object]]:
    """Validate codec/payload compression profiles with explicit provenance."""

    normalized: List[Dict[str, object]] = []
    for index, profile in enumerate(profiles):
        missing = _missing(COMPRESSION_REQUIRED_FIELDS, profile)
        if missing:
            raise ProvenanceError(f"compression profile {index} missing fields: {', '.join(missing)}")

        evidence_level = str(profile["evidence_level"])
        if evidence_level not in EVIDENCE_LEVELS:
            raise ProvenanceError(f"unknown evidence_level: {evidence_level}")

        if evidence_level != "P0_literature_ratio" and _looks_synthetic(profile):
            raise ProvenanceError("synthetic payload cannot be marked as P1/P2/P3 evidence")

        original_bytes = _as_positive_int(profile, "original_bytes")
        compressed_bytes = _as_positive_int(profile, "compressed_bytes")
        chunk_size = _as_positive_int(profile, "chunk_size")
        ratio = _as_positive_float(profile, "ratio")

        measured_ratio = original_bytes / compressed_bytes
        if abs(measured_ratio - ratio) > max(0.02, 0.03 * ratio):
            raise ProvenanceError(
                "ratio must match original_bytes/compressed_bytes within tolerance"
            )

        item = dict(profile)
        item["original_bytes"] = original_bytes
        item["compressed_bytes"] = compressed_bytes
        item["chunk_size"] = chunk_size
        item["ratio"] = ratio
        item["payload_realism"] = EVIDENCE_LEVELS[evidence_level]
        normalized.append(item)
    return normalized


def compose_ratio_trace(
    schedule_rows: Iterable[Mapping[str, object]],
    compression_profiles: Iterable[Mapping[str, object]],
    *,
    schedule_source: str,
) -> List[Dict[str, object]]:
    """Compose schedule rows with codec profiles while preserving both sources."""

    schedules = validate_schedule_trace(schedule_rows, schedule_source=schedule_source)
    profiles = validate_compression_profiles(compression_profiles)

    ratio_trace: List[Dict[str, object]] = []
    for schedule in schedules:
        for profile in profiles:
            remaining = int(schedule["message_bytes"])
            chunk_id = 0
            chunk_size = int(profile["chunk_size"])
            ratio = float(profile["ratio"])

            while remaining > 0:
                original_bytes = min(chunk_size, remaining)
                compressed_bytes = max(1, int(math.ceil(original_bytes / ratio)))
                row = {
                    "timestamp_ns": schedule["timestamp_ns"],
                    "op_type": schedule["op_type"],
                    "flow_id": schedule["flow_id"],
                    "qp_id": schedule.get("qp_id", schedule["flow_id"]),
                    "tenant_id": schedule["tenant_id"],
                    "message_id": schedule.get(
                        "message_id",
                        f"{schedule['flow_id']}:{schedule['timestamp_ns']}",
                    ),
                    "chunk_id": chunk_id,
                    "src": schedule["src"],
                    "dst": schedule["dst"],
                    "phase": schedule["phase"],
                    "original_bytes": original_bytes,
                    "compressed_bytes": compressed_bytes,
                    "codec_family": profile["codec_family"],
                    "payload_source": profile["payload_source"],
                    "payload_realism": profile["payload_realism"],
                    "evidence_level": profile["evidence_level"],
                    "schedule_source": schedule["schedule_source"],
                    "schedule_realism": schedule["schedule_realism"],
                    "source_pair": (
                        f"{schedule['schedule_source']} + "
                        f"{profile['evidence_level']}:{profile['payload_source']}"
                    ),
                    "dtype": profile["dtype"],
                    "tensor_role": profile["tensor_role"],
                    "provenance": profile["provenance"],
                    "is_control": str(profile["tensor_role"]).lower() == "control",
                    "is_incompressible": ratio <= 1.01,
                }
                ratio_trace.append(row)
                remaining -= original_bytes
                chunk_id += 1
    return ratio_trace


def claim_scope_from_evidence(profiles: Iterable[Mapping[str, object]]) -> Dict[str, object]:
    """Return the strongest claim allowed by the available payload evidence."""

    levels = {str(profile["evidence_level"]) for profile in profiles}
    if levels & {"P2_real_comm_bucket", "P3_artifact_payload"}:
        return {
            "claim_scope": "real_communication_payload_claim_allowed",
            "allowed_claim": "real communication payload shows expansion pressure risk",
            "evidence_levels": sorted(levels),
        }
    if "P1_real_tensor_bytes" in levels:
        return {
            "claim_scope": "tensor_payload_plausibility",
            "allowed_claim": "real tensor bytes can create output pressure in the model",
            "evidence_levels": sorted(levels),
        }
    return {
        "claim_scope": "analytical_sensitivity_only",
        "allowed_claim": "codec-ratio sensitivity under stated literature assumptions",
        "evidence_levels": sorted(levels),
    }
