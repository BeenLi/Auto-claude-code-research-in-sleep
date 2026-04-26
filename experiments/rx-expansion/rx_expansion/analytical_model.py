"""M1 analytical break-even model for compressed RDMA Rx expansion."""

from __future__ import annotations

from typing import Dict


SUPPORTED_OFFERED_LOAD_MODES = {
    "same_original_bytes",
    "compressed_line_rate_saturated",
}


def _effective_output_budget_gbps(
    *,
    output_bw_gbps: float,
    decompressor_output_gbps: float,
) -> float:
    return min(float(output_bw_gbps), float(decompressor_output_gbps))


def evaluate_profile(
    *,
    ratio: float,
    link_gbps: float,
    output_bw_gbps: float,
    decompressor_input_gbps: float,
    decompressor_output_gbps: float,
    offered_load_mode: str,
    observation_window_us: float,
) -> Dict[str, float]:
    """Evaluate one codec ratio/resource point.

    `same_original_bytes` holds original-byte demand fixed at link rate. This
    mode checks whether compression merely shortens wire occupancy without
    increasing total receiver output demand.

    `compressed_line_rate_saturated` assumes senders keep the compressed wire
    link saturated. This is the mode that can expose receiver output-byte
    pressure.
    """

    if offered_load_mode not in SUPPORTED_OFFERED_LOAD_MODES:
        raise ValueError(f"unsupported offered_load_mode: {offered_load_mode}")
    if ratio <= 0:
        raise ValueError("ratio must be positive")
    if link_gbps <= 0:
        raise ValueError("link_gbps must be positive")
    if output_bw_gbps <= 0:
        raise ValueError("output_bw_gbps must be positive")
    if decompressor_input_gbps <= 0:
        raise ValueError("decompressor_input_gbps must be positive")
    if decompressor_output_gbps <= 0:
        raise ValueError("decompressor_output_gbps must be positive")
    if observation_window_us <= 0:
        raise ValueError("observation_window_us must be positive")

    link_gbps = float(link_gbps)
    ratio = float(ratio)
    output_bw_gbps = float(output_bw_gbps)
    decompressor_input_gbps = float(decompressor_input_gbps)
    decompressor_output_gbps = float(decompressor_output_gbps)
    output_budget_gbps = _effective_output_budget_gbps(
        output_bw_gbps=output_bw_gbps,
        decompressor_output_gbps=decompressor_output_gbps,
    )

    if offered_load_mode == "compressed_line_rate_saturated":
        compressed_ingress_gbps = link_gbps
        decompressed_output_gbps = compressed_ingress_gbps * ratio
    else:
        decompressed_output_gbps = link_gbps
        compressed_ingress_gbps = link_gbps / ratio

    input_utilization = compressed_ingress_gbps / decompressor_input_gbps
    output_utilization = decompressed_output_gbps / output_budget_gbps
    decompressor_output_utilization = decompressed_output_gbps / decompressor_output_gbps
    ratio_threshold = output_budget_gbps / compressed_ingress_gbps
    excess_output_gbps = max(0.0, decompressed_output_gbps - output_budget_gbps)

    # 1 Gbps = 125 bytes/us.
    max_expansion_debt_bytes = excess_output_gbps * 125.0 * float(observation_window_us)

    is_input_safe = input_utilization <= 1.0
    is_output_safe = output_utilization <= 1.0
    is_safe = is_input_safe and is_output_safe

    return {
        "compressed_ingress_gbps": compressed_ingress_gbps,
        "decompressed_output_gbps": decompressed_output_gbps,
        "effective_output_budget_gbps": output_budget_gbps,
        "input_utilization": input_utilization,
        "output_utilization": output_utilization,
        "decompressor_output_utilization": decompressor_output_utilization,
        "ratio_threshold": ratio_threshold,
        "max_expansion_debt_bytes": max_expansion_debt_bytes,
        "is_input_safe": is_input_safe,
        "is_output_safe": is_output_safe,
        "is_safe": is_safe,
    }
