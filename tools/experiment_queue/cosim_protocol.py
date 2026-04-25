#!/usr/bin/env python3
"""Window-level gem5 + Broadcom/csg-htsim co-simulation protocol helpers.

The protocol is intentionally flow/QP summary based. It preserves the
Rx decompression expansion pressure ground truth without committing the first
implementation to packet-level RDMA transport or segment-level retransmission.
"""

RX_PRESSURE_GROUND_TRUTH = "rx_decompression_expansion_pressure"
SCHEMA_VERSION = 1
DEFAULT_HTSIM_VARIANT = "broadcom_csg_htsim"
DEFAULT_WINDOW_US = 100
DEFAULT_SENDER_RETRANSMISSION_POLICY = "rto"

RX_PRESSURE_METRICS = (
    "rx_pressure",
    "rx_buffer_occupancy",
    "decompression_expansion_ratio",
    "accepted_compressed_bytes",
    "dropped_compressed_bytes",
    "drop_reason",
    "host_memory_write_gbps",
    "pcie_utilization",
    "rx_stall_ns",
)

RETRANSMISSION_METRICS = (
    "sender_retransmission_policy",
    "retransmitted_bytes",
    "goodput_bytes",
)


def _time_window(window_id, window_us):
    start_ns = int(window_id * window_us * 1000)
    end_ns = int((window_id + 1) * window_us * 1000)
    return {"start_ns": start_ns, "end_ns": end_ns}


def _flow_for_gem5(flow):
    return {
        "flow_id": flow["flow_id"],
        "src": flow.get("src"),
        "dst": flow.get("dst"),
        "compressed_bytes_arrived": flow.get("compressed_bytes_arrived", 0),
        "raw_bytes_represented": flow.get("raw_bytes_represented", 0),
        "compression_ratio": flow.get("compression_ratio", 1.0),
        "arrival_burstiness": flow.get("arrival_burstiness", 0.0),
        "qos_class": flow.get("qos_class", "default"),
    }


def _flow_for_htsim(flow):
    return {
        "flow_id": flow["flow_id"],
        "src": flow.get("src"),
        "dst": flow.get("dst"),
        "bytes_to_deliver": flow.get("compressed_bytes_arrived", 0),
        "raw_bytes_represented": flow.get("raw_bytes_represented", 0),
        "compression_ratio": flow.get("compression_ratio", 1.0),
        "qos_class": flow.get("qos_class", "default"),
    }


def build_window_inputs(
    run_id,
    window_id,
    flows,
    window_us=DEFAULT_WINDOW_US,
    htsim_variant=DEFAULT_HTSIM_VARIANT,
    network_state=None,
):
    """Build gem5 and htsim JSON payloads for one co-simulation window."""
    time = _time_window(window_id, window_us)
    rdma_semantics = {
        "network": "lossy",
        "completion": "reliable",
        "sender_retransmission_policy": DEFAULT_SENDER_RETRANSMISSION_POLICY,
        "drop_visibility": "receiver_no_ack",
    }
    return {
        "gem5_input": {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "window_id": window_id,
            "time": time,
            "scenario": RX_PRESSURE_GROUND_TRUTH,
            "exchange_unit": "flow_summary",
            "rx_arrivals": [_flow_for_gem5(flow) for flow in flows],
            "network_state": network_state or {},
            "rdma_semantics": rdma_semantics,
        },
        "htsim_input": {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "window_id": window_id,
            "time": time,
            "scenario": RX_PRESSURE_GROUND_TRUTH,
            "htsim_variant": htsim_variant,
            "exchange_unit": "flow_summary",
            "flows": [_flow_for_htsim(flow) for flow in flows],
            "rdma_semantics": rdma_semantics,
        },
    }


def _require_fields(payload, fields, owner):
    missing = [field for field in fields if field not in payload]
    if missing:
        raise ValueError(f"{owner} missing required fields: {', '.join(missing)}")


def summarize_rx_pressure_window(run_id, window_id, gem5_output, htsim_output):
    """Merge one window's simulator outputs into the standard metrics shape."""
    _require_fields(gem5_output, RX_PRESSURE_METRICS, "gem5_output")
    _require_fields(htsim_output, RETRANSMISSION_METRICS, "htsim_output")
    if htsim_output["sender_retransmission_policy"] != DEFAULT_SENDER_RETRANSMISSION_POLICY:
        raise ValueError("htsim_output must model sender-side RTO retransmission")

    metrics = {}
    for field in RX_PRESSURE_METRICS:
        metrics[field] = gem5_output[field]
    for field in RETRANSMISSION_METRICS:
        metrics[field] = htsim_output[field]

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "window_id": window_id,
        "backend": "cosim_gem5_htsim",
        "ground_truth": RX_PRESSURE_GROUND_TRUTH,
        "metrics": metrics,
        "artifacts": {},
    }
