"""E0b capture runner: NetZIP-algorithm arms on real captured KV (bf16 only).

Same capture protocol as run_e0 / m1_6 (prefill, seq_len 512, layer_fracs 0/0.5/1,
K and V, chunks 256KB/1MB, <=3 chunks/config) so the E0b rows are chunk-comparable
with the E0a corpus. Port certified by check_netzip_equivalence.py on the box.

    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=../m1:../m1_5:../m1_6 \
        python run_netzip.py --model gpt2 --out e0_outputs/netzip_gpt2.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import netzip_kv


def measure_chunk_rows(*, chunk, model_size, phase, tensor_type, layer_idx, chunk_size_bytes):
    rows = []
    for m in netzip_kv.measure(chunk):
        rows.append(
            {
                "model_size": model_size,
                "dtype": "bf16",
                "phase": phase,
                "tensor_type": tensor_type,
                "layer_idx": layer_idx,
                "chunk_size_bytes": chunk_size_bytes,
                "generation_method": "captured",
                **m,
            }
        )
    return rows


def capture(*, model_name, out_path, chunk_sizes=(262144, 1048576), layer_fracs=(0.0, 0.5, 1.0),
            seq_len=512, max_chunks_per_config=3):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    import capture_hf_kv as cap
    import chunking

    torch.manual_seed(0)
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.bfloat16)
    model.eval()
    model_tag = model_name.split("/")[-1].lower()
    enc = tok(cap._DEFAULT_TEXT, return_tensors="pt", truncation=True, max_length=seq_len)

    with torch.no_grad():
        kv = cap._kv_layers(model(**enc, use_cache=True).past_key_values)

    n_layers = len(kv)
    rows = []
    for frac in layer_fracs:
        layer_idx = int(round(frac * (n_layers - 1)))
        k_full, v_full = kv[layer_idx]
        for ttype, full in (("K", k_full), ("V", v_full)):
            sliced = full[0, :, :, :]
            buf = cap._to_bytes(sliced, "bf16")
            for csize in chunk_sizes:
                if csize > len(buf):
                    continue
                taken = 0
                for chunk in chunking.iter_chunks(buf, csize):
                    if taken >= max_chunks_per_config:
                        break
                    rows.extend(
                        measure_chunk_rows(
                            chunk=chunk, model_size=model_tag, phase="prefill",
                            tensor_type=ttype, layer_idx=layer_idx, chunk_size_bytes=len(chunk),
                        )
                    )
                    taken += 1

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(out_path).open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"rows_written": len(rows), "model": model_name, "n_layers": n_layers,
            "out_path": str(out_path)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="E0b NetZIP-on-KV capture")
    ap.add_argument("--model", default="gpt2")
    ap.add_argument("--out", default="e0_outputs/netzip_captured.jsonl")
    ap.add_argument("--seq-len", type=int, default=512)
    args = ap.parse_args(argv)
    print(capture(model_name=args.model, out_path=args.out, seq_len=args.seq_len))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
