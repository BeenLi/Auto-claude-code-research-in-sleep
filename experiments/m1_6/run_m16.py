"""M1.6 channel-major layout sweep (synthetic corpus + real-KV capture).

For each (dtype, layout method, chunk) it records raw alpha alongside the transformed
single-stream alpha, so analyze_m16 can answer: how much of TRACE's channel-major layout
gain survives the commodity-BF3 single-deflate-stream constraint?

Reuses the canonical M1/M1.5 harness (synth, chunking, MODEL_CONFIGS, m1_codecs via
measure_layout, capture_hf_kv helpers) — no copied codec/generator logic. Caveat encoded
here: chunks must span whole (row, head_dim) value rows, so chunk sizes must be multiples
of head_dim * itemsize (true for 256KB/1MB with head_dim 64/128).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from itertools import product
from pathlib import Path

import chunking
import layout
import measure_layout
import synth
from run_corpus import MODEL_CONFIGS
from synth import TensorSpec

METHODS = ("byte_transpose", "chan", "chan_bt", "chan_bt_delta", "bt_delta", "delta")


def build_row(*, spec, model_size, chunk_size_bytes, measurement, generation_method, seed):
    return {
        "phase": spec.phase,
        "tensor_type": spec.tensor_type,
        "dtype": spec.dtype,
        "model_size": model_size,
        "seq_len": spec.seq_len,
        "layer_idx": spec.layer_idx,
        "chunk_size_bytes": chunk_size_bytes,
        "method": measurement["method"],
        "codec": measurement["codec"],
        "level": measurement["level"],
        "n_values": measurement["n_values"],
        "head_dim": measurement["head_dim"],
        "alpha_raw": measurement["alpha_raw"],
        "alpha_concat": measurement["alpha_concat"],
        "delta_vs_raw": measurement["alpha_raw"] - measurement["alpha_concat"],
        "transform_throughput_mbps": measurement["transform_throughput_mbps"],
        "inverse_cost_class": measurement["inverse_cost_class"],
        "bit_exact": measurement["bit_exact"],
        "generation_method": generation_method,
        "seed": seed,
    }


def _aligned(csize: int, dtype: str, head_dim: int) -> bool:
    return csize % (head_dim * layout.itemsize(dtype)) == 0


def _measure_chunk_rows(*, spec, model_size, chunk, methods, level, generation_method, seed, warmup, repeats):
    rows, failures = [], 0
    for method in methods:
        m = measure_layout.measure(
            chunk, spec.dtype, method, head_dim=spec.head_dim,
            codec="deflate", level=level, warmup=warmup, repeats=repeats,
        )
        if not m["bit_exact"]:
            failures += 1
        rows.append(
            build_row(
                spec=spec, model_size=model_size, chunk_size_bytes=len(chunk),
                measurement=m, generation_method=generation_method, seed=seed,
            )
        )
    return rows, failures


def run(
    *, out_path, models, dtypes, phases, tensor_types, seq_lens, layer_fracs,
    chunk_sizes, methods, seeds, level=6, max_chunks_per_config=2, warmup=1, repeats=3, append=False,
):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    bit_exact_failures = 0
    mode_append = append
    t0 = time.time()

    for model_size, phase, ttype, dtype, seq_len, seed in product(
        models, phases, tensor_types, dtypes, seq_lens, seeds
    ):
        cfg = MODEL_CONFIGS[model_size]
        for frac in layer_fracs:
            layer_idx = int(round(frac * (cfg["num_layers"] - 1)))
            spec = TensorSpec(
                phase=phase, tensor_type=ttype, dtype=dtype,
                num_heads=cfg["num_heads"], head_dim=cfg["head_dim"],
                seq_len=seq_len, layer_idx=layer_idx, seed=seed,
            )
            buf = synth.to_bytes(synth.generate_kv_tensor(spec))
            rows = []
            for csize in chunk_sizes:
                if csize > len(buf) or not _aligned(csize, dtype, spec.head_dim):
                    continue
                taken = 0
                for chunk in chunking.iter_chunks(buf, csize):
                    if taken >= max_chunks_per_config:
                        break
                    cr, f = _measure_chunk_rows(
                        spec=spec, model_size=model_size, chunk=chunk, methods=methods,
                        level=level, generation_method="synthetic", seed=seed,
                        warmup=warmup, repeats=repeats,
                    )
                    rows.extend(cr)
                    bit_exact_failures += f
                    taken += 1
            if rows:
                with out_path.open("a" if mode_append else "w", encoding="utf-8") as fh:
                    for r in rows:
                        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                mode_append = True
                rows_written += len(rows)
            del buf

    return {
        "rows_written": rows_written,
        "bit_exact_failures": bit_exact_failures,
        "elapsed_s": round(time.time() - t0, 2),
        "out_path": str(out_path),
    }


def capture_real_kv(
    *, model_name, out_path, dtypes, chunk_sizes, methods, layer_fracs, phases,
    seq_len=512, max_new_tokens=64, level=6, max_chunks_per_config=3, warmup=1, repeats=3,
):
    """Real-KV verdict data: pull actual K/V from an HF CPU forward and layout-measure them.

    Mirrors m1_5/run_split.capture_real_kv; the KV slice layout is (heads, tokens, head_dim)
    C-contiguous, so head_dim is the fastest axis — exactly what layout.channel_major assumes.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    import capture_hf_kv as cap

    torch.manual_seed(0)
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.bfloat16)
    model.eval()
    model_tag = model_name.split("/")[-1].lower()
    enc = tok(cap._DEFAULT_TEXT, return_tensors="pt", truncation=True, max_length=seq_len)
    prompt_len = enc["input_ids"].shape[1]

    captures = {}
    with torch.no_grad():
        if "prefill" in phases:
            captures["prefill"] = (cap._kv_layers(model(**enc, use_cache=True).past_key_values), 0, prompt_len)
        if "decode" in phases and max_new_tokens > 0:
            gen = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                                 return_dict_in_generate=True, use_cache=True)
            captures["decode"] = (cap._kv_layers(gen.past_key_values), prompt_len, prompt_len + max_new_tokens)

    import hashlib
    n_layers = len(next(iter(captures.values()))[0])
    seed = int(hashlib.sha256(model_tag.encode()).hexdigest()[:8], 16)
    rows, failures = [], 0

    for phase, (kv, lo, hi) in captures.items():
        for frac in layer_fracs:
            layer_idx = int(round(frac * (n_layers - 1)))
            k_full, v_full = kv[layer_idx]
            for ttype, full in (("K", k_full), ("V", v_full)):
                sliced = full[0, :, lo:hi, :]
                heads, span, head_dim = sliced.shape
                for dtype in dtypes:
                    buf = cap._to_bytes(sliced, dtype)
                    spec = TensorSpec(phase=phase, tensor_type=ttype, dtype=dtype,
                                      num_heads=heads, head_dim=head_dim, seq_len=span,
                                      layer_idx=layer_idx, seed=seed)
                    for csize in chunk_sizes:
                        if csize > len(buf) or not _aligned(csize, dtype, head_dim):
                            continue
                        taken = 0
                        for chunk in chunking.iter_chunks(buf, csize):
                            if taken >= max_chunks_per_config:
                                break
                            cr, f = _measure_chunk_rows(
                                spec=spec, model_size=model_tag, chunk=chunk, methods=methods,
                                level=level, generation_method="captured", seed=seed,
                                warmup=warmup, repeats=repeats,
                            )
                            rows.extend(cr)
                            failures += f
                            taken += 1

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(out_path).open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"rows_written": len(rows), "bit_exact_failures": failures, "model": model_name,
            "n_layers": n_layers, "out_path": str(out_path)}


def _csv_strs(s):
    return [x.strip() for x in s.split(",") if x.strip()]


def _csv_ints(s):
    return [int(x) for x in s.split(",") if x.strip()]


def _csv_floats(s):
    return [float(x) for x in s.split(",") if x.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description="M1.6 channel-major layout sweep")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("synthetic")
    s.add_argument("--out", default="m16_outputs/layout_corpus.jsonl")
    s.add_argument("--models", type=_csv_strs, default=["7b"])
    s.add_argument("--dtypes", type=_csv_strs, default=["bf16", "fp8_e4m3", "fp8_e5m2"])
    s.add_argument("--phases", type=_csv_strs, default=["prefill", "decode"])
    s.add_argument("--tensor-types", type=_csv_strs, default=["K", "V"])
    s.add_argument("--seq-lens", type=_csv_ints, default=[2048, 8192])
    s.add_argument("--layer-fracs", type=_csv_floats, default=[0.0, 0.5, 1.0])
    s.add_argument("--chunk-sizes", type=_csv_ints, default=[262144, 1048576])
    s.add_argument("--methods", type=_csv_strs, default=list(METHODS))
    s.add_argument("--seeds", type=_csv_ints, default=[42, 43])
    s.add_argument("--level", type=int, default=6)
    s.add_argument("--max-chunks-per-config", type=int, default=2)
    s.add_argument("--append", action="store_true")

    c = sub.add_parser("capture")
    c.add_argument("--model", default="gpt2")
    c.add_argument("--out", default="m16_outputs/layout_captured.jsonl")
    c.add_argument("--dtypes", type=_csv_strs, default=["bf16", "fp8_e4m3", "fp8_e5m2"])
    c.add_argument("--chunk-sizes", type=_csv_ints, default=[262144, 1048576])
    c.add_argument("--methods", type=_csv_strs, default=list(METHODS))
    c.add_argument("--layer-fracs", type=_csv_floats, default=[0.0, 0.5, 1.0])
    c.add_argument("--phases", type=_csv_strs, default=["prefill", "decode"])
    c.add_argument("--seq-len", type=int, default=512)
    c.add_argument("--max-new-tokens", type=int, default=64)
    c.add_argument("--level", type=int, default=6)
    c.add_argument("--max-chunks-per-config", type=int, default=3)

    args = ap.parse_args(argv)
    if args.cmd == "synthetic":
        summary = run(
            out_path=args.out, models=args.models, dtypes=args.dtypes, phases=args.phases,
            tensor_types=args.tensor_types, seq_lens=args.seq_lens, layer_fracs=args.layer_fracs,
            chunk_sizes=args.chunk_sizes, methods=args.methods, seeds=args.seeds, level=args.level,
            max_chunks_per_config=args.max_chunks_per_config, append=args.append,
        )
    else:
        summary = capture_real_kv(
            model_name=args.model, out_path=args.out, dtypes=args.dtypes, chunk_sizes=args.chunk_sizes,
            methods=args.methods, layer_fracs=args.layer_fracs, phases=args.phases, seq_len=args.seq_len,
            max_new_tokens=args.max_new_tokens, level=args.level,
            max_chunks_per_config=args.max_chunks_per_config,
        )
    print(summary)
    if summary["bit_exact_failures"]:
        print(f"WARNING: {summary['bit_exact_failures']} bit-exact failures", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
