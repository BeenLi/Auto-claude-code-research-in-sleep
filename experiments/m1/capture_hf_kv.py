"""Capture REAL KV-cache bytes via HuggingFace CPU forward (M1_CHECKLIST §1.2.4).

The validity anchor for the synthetic sweep: run an ungated decoder LM on real
text, pull actual K/V from past_key_values, and measure the same codec matrix on
the real bytes (tagged generation_method="captured"). No GPU needed; no HF token
needed (default model is ungated gpt2; use --model qwen2.5-7b / mistral-7b for
larger anchors). torch/transformers are imported lazily so the rest of the M1
package stays importable on the torch-free dev venv.

Emits the SAME MeasurementRow schema as run_corpus.py so validate_overlap can
compare synthetic vs captured directly at matching (phase, dtype, codec, size).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import ml_dtypes
import numpy as np

import chunking
import m1_codecs
import manifest
import run_corpus
from synth import TensorSpec

_DEFAULT_TEXT = (
    "The transfer of key-value cache state between prefill and decode workers is a "
    "first-order bottleneck in disaggregated large language model inference. This "
    "paragraph exists to give a real trained model real tokens to attend over so that "
    "the captured attention key and value tensors carry realistic byte-level statistics "
    "rather than synthetic noise. Repeat, vary, and extend as needed for longer contexts. "
) * 8

_FP8 = {"fp8_e4m3": ml_dtypes.float8_e4m3fn, "fp8_e5m2": ml_dtypes.float8_e5m2}


def _to_bytes(kv_layer_tensor, dtype: str) -> bytes:
    """kv_layer_tensor: torch tensor (heads, seq, head_dim) float -> (seq, heads, head_dim) bytes."""
    arr = kv_layer_tensor.transpose(0, 1).contiguous().float().numpy()  # (seq, heads, head_dim) fp32
    if dtype == "bf16":
        return arr.astype(ml_dtypes.bfloat16).tobytes()
    if dtype in _FP8:
        return arr.astype(_FP8[dtype]).tobytes()
    raise ValueError(f"unsupported dtype: {dtype}")


def _kv_layers(past):
    """Normalize any transformers cache to a list[(K, V)] per layer.

    Handles legacy tuple, transformers 5.x DynamicCache (cache.layers[i].keys/.values),
    older .key_cache/.value_cache lists, and the to_legacy_cache() fallback.
    """
    if isinstance(past, (tuple, list)):
        return list(past)
    if hasattr(past, "layers"):
        return [(layer.keys, layer.values) for layer in past.layers]
    if hasattr(past, "key_cache") and hasattr(past, "value_cache"):
        return list(zip(past.key_cache, past.value_cache))
    if hasattr(past, "to_legacy_cache"):
        return list(past.to_legacy_cache())
    raise TypeError(f"unsupported cache type: {type(past)}")


def capture(
    *,
    model_name,
    out_path,
    dtypes,
    chunk_sizes,
    codecs,
    layer_fracs,
    phases,
    seq_len,
    max_new_tokens,
    max_chunks_per_config,
    warmup,
    repeats,
):
    import torch  # lazy
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(0)
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.bfloat16)
    model.eval()

    model_tag = model_name.split("/")[-1].lower()
    enc = tok(_DEFAULT_TEXT, return_tensors="pt", truncation=True, max_length=seq_len)
    prompt_len = enc["input_ids"].shape[1]

    captures = {}  # phase -> legacy kv tuple
    with torch.no_grad():
        if "prefill" in phases:
            captures["prefill"] = (_kv_layers(model(**enc, use_cache=True).past_key_values), 0, prompt_len)
        if "decode" in phases and max_new_tokens > 0:
            gen = model.generate(
                **enc,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                return_dict_in_generate=True,
                use_cache=True,
            )
            captures["decode"] = (_kv_layers(gen.past_key_values), prompt_len, prompt_len + max_new_tokens)

    n_layers = len(next(iter(captures.values()))[0])
    seed = int(hashlib.sha256(model_tag.encode()).hexdigest()[:8], 16)
    rows = []
    bit_exact_failures = 0

    for phase, (kv, lo, hi) in captures.items():
        for frac in layer_fracs:
            layer_idx = int(round(frac * (n_layers - 1)))
            k_full, v_full = kv[layer_idx]  # each (batch, heads, seq, head_dim)
            for ttype, full in (("K", k_full), ("V", v_full)):
                sliced = full[0, :, lo:hi, :]  # (heads, span, head_dim)
                heads, span, head_dim = sliced.shape
                for dtype in dtypes:
                    buf = _to_bytes(sliced, dtype)
                    spec = TensorSpec(
                        phase=phase,
                        tensor_type=ttype,
                        dtype=dtype,
                        num_heads=heads,
                        head_dim=head_dim,
                        seq_len=span,
                        layer_idx=layer_idx,
                        seed=seed,
                    )
                    for csize in chunk_sizes:
                        if csize > len(buf):
                            continue
                        taken = 0
                        for chunk in chunking.iter_chunks(buf, csize):
                            if taken >= max_chunks_per_config:
                                break
                            for codec in codecs:
                                for level in m1_codecs.codec_levels(codec):
                                    m = m1_codecs.measure(chunk, codec, level, warmup=warmup, repeats=repeats)
                                    if not m.is_bit_exact:
                                        bit_exact_failures += 1
                                    rows.append(
                                        run_corpus.build_row(
                                            spec=spec,
                                            model_size=model_tag,
                                            chunk=chunk,
                                            measurement=m,
                                            generation_method="captured",
                                            seed=seed,
                                        )
                                    )
                            taken += 1

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    manifest.write_jsonl(rows, out_path)
    return {
        "rows_written": len(rows),
        "bit_exact_failures": bit_exact_failures,
        "model": model_name,
        "n_layers": n_layers,
        "prompt_len": prompt_len,
        "out_path": str(out_path),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="M1 real KV capture via HF CPU forward")
    ap.add_argument("--model", default="gpt2", help="ungated decoder LM (gpt2, Qwen/Qwen2.5-7B, ...)")
    ap.add_argument("--out", default="m1_outputs/captured_corpus.jsonl")
    ap.add_argument("--dtypes", type=run_corpus._csv_strs, default=["bf16", "fp8_e4m3", "fp8_e5m2"])
    ap.add_argument("--chunk-sizes", type=run_corpus._csv_ints, default=[4096, 65536, 1048576])
    ap.add_argument("--codecs", type=run_corpus._csv_strs, default=["none", "deflate", "lz4", "zstd"])
    ap.add_argument("--layer-fracs", type=run_corpus._csv_floats, default=[0.0, 0.5, 1.0])
    ap.add_argument("--phases", type=run_corpus._csv_strs, default=["prefill", "decode"])
    ap.add_argument("--seq-len", type=int, default=512)
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument("--max-chunks-per-config", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args(argv)

    summary = capture(
        model_name=args.model,
        out_path=args.out,
        dtypes=args.dtypes,
        chunk_sizes=args.chunk_sizes,
        codecs=args.codecs,
        layer_fracs=args.layer_fracs,
        phases=args.phases,
        seq_len=args.seq_len,
        max_new_tokens=args.max_new_tokens,
        max_chunks_per_config=args.max_chunks_per_config,
        warmup=args.warmup,
        repeats=args.repeats,
    )
    print(summary)
    if summary["bit_exact_failures"]:
        print(f"WARNING: {summary['bit_exact_failures']} bit-exact failures", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
