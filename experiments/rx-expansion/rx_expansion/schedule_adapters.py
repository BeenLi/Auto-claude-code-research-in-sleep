"""Schedule-only adapters for communication execution traces."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional

from . import trace_payload


COMM_NODE_TYPES = {
    "COMM_SEND_NODE",
    "COMM_RECV_NODE",
    "COMM_COLL_NODE",
    5,
    6,
    7,
}


def _attr_value(attr: Mapping[str, object]) -> Optional[object]:
    for key in (
        "string_val",
        "int64_val",
        "int32_val",
        "uint64_val",
        "uint32_val",
        "float_val",
        "double_val",
        "bool_val",
        "value",
    ):
        if key in attr:
            return attr[key]
    return None


def _attrs_to_dict(raw_attrs: object) -> Dict[str, object]:
    attrs: Dict[str, object] = {}
    if not raw_attrs:
        return attrs
    if isinstance(raw_attrs, Mapping):
        return dict(raw_attrs)
    for attr in raw_attrs:
        if not isinstance(attr, Mapping) or "name" not in attr:
            continue
        value = _attr_value(attr)
        if value is not None:
            attrs[str(attr["name"])] = value
    return attrs


def _first(attrs: Mapping[str, object], *names: str, default: object = None) -> object:
    for name in names:
        if name in attrs:
            return attrs[name]
    return default


def chakra_nodes_to_schedule_trace(
    nodes: Iterable[Mapping[str, object]],
    *,
    schedule_source: str,
) -> List[Dict[str, object]]:
    """Normalize Chakra-like communication nodes into schedule-only rows."""

    schedule_rows: List[Dict[str, object]] = []
    for node in nodes:
        if node.get("type") not in COMM_NODE_TYPES:
            continue
        attrs = _attrs_to_dict(node.get("attr"))
        message_bytes = _first(attrs, "message_bytes", "comm_size", "num_bytes")
        if message_bytes is None:
            raise trace_payload.ProvenanceError(
                f"Chakra communication node {node.get('id')} is missing message_bytes"
            )

        timestamp_ns = int(node.get("start_time_micros", 0)) * 1000
        op_type = _first(
            attrs,
            "collective",
            "collective_comm_type",
            "comm_type",
            default=node.get("name", node.get("type")),
        )

        row = {
            "timestamp_ns": timestamp_ns,
            "op_type": str(op_type),
            "message_bytes": int(message_bytes),
            "src": str(_first(attrs, "src", "source", default="unknown_src")),
            "dst": str(_first(attrs, "dst", "destination", default="unknown_dst")),
            "flow_id": str(_first(attrs, "flow_id", default=f"chakra_node_{node.get('id')}")),
            "tenant_id": str(_first(attrs, "tenant_id", default="default")),
            "phase": str(_first(attrs, "phase", default="unknown")),
        }
        schedule_rows.append(row)

    return trace_payload.validate_schedule_trace(
        schedule_rows,
        schedule_source=schedule_source,
    )
