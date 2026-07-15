# E0 — Hardware-Encoder-Constrained α Pre-Check (ISCAS 2027 topic gate)

Pre-registered contract: `refine-logs/EVALUATION_CONTRACT_E0.md` (thresholds fixed 2026-07-15,
**before** any number below was produced). Decides Topic A (KV compression egress datapath on
VCU118) vs Topic B (PSP FPGA) by measuring what FPGA-encoder constraints — level-1-class match
search, static Huffman (`Z_FIXED`), independent 32 KB blocks — cost against the locked software
zlib-6 α (M1/M1.5/M1.6).

| module | role |
|---|---|
| `e0_codecs.py` | proxy variants V0–V5 (all stay stock-zlib-decodable; blocked = concatenated independent standard streams, container overhead included) |
| `measure_e0.py` | one transform pass per chunk, all six variant α + bit-exact gates (reuses `m1_6/layout.py`) |
| `run_e0.py` | synthetic sweep + real-KV capture (protocol-parity with m1_6: prefill, seq_len 512) |
| `analyze_e0.py` | the contract's decision rule verbatim + CLI; `locked_reference.json` = m16 V0 medians for the ±0.005 reproduction gate |

```bash
# on the box (myDevbox), venv = ../m1/.venv
PYTHONPATH=../m1:../m1_5:../m1_6 python run_e0.py synthetic --out e0_outputs/e0_synth.jsonl --seq-lens 8192 --seeds 42,43
PYTHONPATH=../m1:../m1_5:../m1_6 python run_e0.py capture --model gpt2 --out e0_outputs/e0_gpt2.jsonl
HF_ENDPOINT=https://hf-mirror.com PYTHONPATH=../m1:../m1_5:../m1_6 python run_e0.py capture --model Qwen/Qwen2.5-7B --out e0_outputs/e0_qwen7b.jsonl
HF_ENDPOINT=https://hf-mirror.com PYTHONPATH=../m1:../m1_5:../m1_6 python run_e0.py capture --model NousResearch/Meta-Llama-3.1-8B --out e0_outputs/e0_llama31_8b.jsonl
python analyze_e0.py --corpus e0_outputs/e0_gpt2.jsonl e0_outputs/e0_qwen7b.jsonl e0_outputs/e0_llama31_8b.jsonl e0_outputs/e0_synth.jsonl \
    --reference locked_reference.json --out e0_outputs/e0_verdict.json
```

Tests: `python -m pytest tests/` (52). Results land in `e0_results.json` + `E0_REPORT.md` after the
captured runs; the GO/NO-GO verdict is read per contract, then user sign-off is recorded in the
contract's Status line.
