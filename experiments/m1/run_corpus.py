"""Streaming synthetic KV-compressibility corpus (M1_CHECKLIST §1, §2).

Generate tensor -> chunk -> measure each codec -> append JSONL row -> discard
tensor. Disk stays ~MB (rows only); the tensors are reproducible from seeds, so
nothing large is persisted (avoids the §0.3 50 GB requirement).

CLI run is glue; the pure assembly (`build_row`) is unit-tested.
"""

from __future__ import annotations

import argparse
import sys
import time
from itertools import product
from pathlib import Path

import chunking
import entropy
import m1_codecs
import manifest
import synth
from synth import TensorSpec

# Llama-2-style configs (num_heads, head_dim, num_layers).
MODEL_CONFIGS = {
    "7b": {"num_heads": 32, "head_dim": 128, "num_layers": 32},
    "13b": {"num_heads": 40, "head_dim": 128, "num_layers": 40},
    "tiny": {"num_heads": 4, "head_dim": 64, "num_layers": 4},  # smoke only
}


def build_row(*, spec, model_size, chunk, measurement, generation_method, seed):
    chunk_size_bytes = len(chunk)
    chunk_id = manifest.make_chunk_id(
        phase=spec.phase,
        tensor_type=spec.tensor_type,
        dtype=spec.dtype,
        model_size=model_size,
        seq_len=spec.seq_len,
        layer_idx=spec.layer_idx,
        chunk_size_bytes=chunk_size_bytes,
        seed=seed,
    )
    return manifest.MeasurementRow(
        chunk_id=chunk_id,
        phase=spec.phase,
        tensor_type=spec.tensor_type,
        dtype=spec.dtype,
        model_size=model_size,
        seq_len=spec.seq_len,
        layer_idx=spec.layer_idx,
        chunk_size_bytes=chunk_size_bytes,
        shannon_entropy=entropy.shannon_entropy_bits_per_byte(chunk),
        codec=measurement.codec,
        level=measurement.level,
        original_size=measurement.original_size,
        compressed_size=measurement.compressed_size,
        ratio=measurement.ratio,
        compress_time_us_p50=measurement.compress_time_s * 1e6,
        compress_throughput_mbps=measurement.compress_throughput_mbps,
        is_bit_exact=measurement.is_bit_exact,
        generation_method=generation_method,
    )


def run(
    *,
    out_path,
    models,
    dtypes,
    phases,
    tensor_types,
    seq_lens,
    layer_fracs,
    chunk_sizes,
    codecs,
    seeds,
    max_chunks_per_config,
    warmup,
    repeats,
    append,
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
                phase=phase,
                tensor_type=ttype,
                dtype=dtype,
                num_heads=cfg["num_heads"],
                head_dim=cfg["head_dim"],
                seq_len=seq_len,
                layer_idx=layer_idx,
                seed=seed,
            )
            buf = synth.to_bytes(synth.generate_kv_tensor(spec))
            rows = []
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
                                build_row(
                                    spec=spec,
                                    model_size=model_size,
                                    chunk=chunk,
                                    measurement=m,
                                    generation_method="synthetic",
                                    seed=seed,
                                )
                            )
                    taken += 1
            if rows:
                manifest.write_jsonl(rows, out_path, append=mode_append)
                mode_append = True
                rows_written += len(rows)
            del buf

    return {
        "rows_written": rows_written,
        "bit_exact_failures": bit_exact_failures,
        "elapsed_s": round(time.time() - t0, 2),
        "out_path": str(out_path),
    }


def _csv_ints(s):
    return [int(x) for x in s.split(",") if x.strip()]


def _csv_strs(s):
    return [x.strip() for x in s.split(",") if x.strip()]


def _csv_floats(s):
    return [float(x) for x in s.split(",") if x.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description="M1 streaming synthetic compressibility corpus")
    ap.add_argument("--out", default="m1_outputs/compressibility_corpus.jsonl")
    ap.add_argument("--models", type=_csv_strs, default=["7b"])
    ap.add_argument("--dtypes", type=_csv_strs, default=["bf16", "fp8_e4m3", "fp8_e5m2"])
    ap.add_argument("--phases", type=_csv_strs, default=["prefill", "decode"])
    ap.add_argument("--tensor-types", type=_csv_strs, default=["K", "V"])
    ap.add_argument("--seq-lens", type=_csv_ints, default=[1024, 8192, 32768])
    ap.add_argument("--layer-fracs", type=_csv_floats, default=[0.0, 0.5, 1.0])
    ap.add_argument("--chunk-sizes", type=_csv_ints, default=[4096, 65536, 1048576, 4194304])
    ap.add_argument("--codecs", type=_csv_strs, default=["none", "deflate", "lz4", "zstd"])
    ap.add_argument("--seeds", type=_csv_ints, default=[42, 43, 44])
    ap.add_argument("--max-chunks-per-config", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--append", action="store_true")
    args = ap.parse_args(argv)

    summary = run(
        out_path=args.out,
        models=args.models,
        dtypes=args.dtypes,
        phases=args.phases,
        tensor_types=args.tensor_types,
        seq_lens=args.seq_lens,
        layer_fracs=args.layer_fracs,
        chunk_sizes=args.chunk_sizes,
        codecs=args.codecs,
        seeds=args.seeds,
        max_chunks_per_config=args.max_chunks_per_config,
        warmup=args.warmup,
        repeats=args.repeats,
        append=args.append,
    )
    print(summary)
    if summary["bit_exact_failures"]:
        print(f"WARNING: {summary['bit_exact_failures']} bit-exact roundtrip failures", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
