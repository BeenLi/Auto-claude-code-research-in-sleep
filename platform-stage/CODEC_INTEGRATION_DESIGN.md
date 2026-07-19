# Codec insertion (transform + Vitis DCL gzip CU, store-and-forward) — 平台可用期工作项 ④

> 旧名 `PLATFORM_USABLE_P4_CODEC_DESIGN.md`（"P4" = 平台可用期第 ④ 项，2026-07-19 改为描述名）。

Design document for platform-usable item **④**, the entry point of the dual-length-verbs
research phase. Grounds a store-and-forward compression CU in verified recon of three
substrates: the AMD Vitis Data Compression Library (**2024.2 branch** — user decision
2026-07-17; AMD removed data_compression from 2025.x), the platform L0/L1 datapath at
code-repo `@c5820d0`, and the E0 transform/α methodology the paper claims rest on.

**Scope (this phase): simulation-level integration.** Board bring-up of the codec waits
for the joint bench session; synthesis of the codec build (build#4) happens only after
the sim gate is green. Nothing here touches the certified Stage C/D/E golden path.

---

## Part 0 — Decisions up front

| # | Decision | Rationale |
|---|---|---|
| D1 | Kernel = `gzipMulticoreCompressAxiStream` (L1), integration top = project-owned shim `codec/hls/gzipc_cu.cpp` with **NUM_CORES=8, BLOCKSIZE_IN_KB=16, STRTGY=0 (gzip), TUSER_DWIDTH=32** — the AMD-shipped `gzipc_16KB` configuration | Only maintained pure-AXIS ap_ctrl_none compressor in DCL 2024.2; dynamic Huffman confirmed (per-block treegen). **BLOCKSIZE=16 is a Gate-1 measurement decision**: the per-block Huffman tree straddles the plane0/plane1 entropy boundary of a 32 KB chan_bt WR when blocks are 32 KB (α 0.772); 16 KB blocks land exactly on the plane boundary → α **0.716** (better than even software V3's 0.724), neutral on e5m2 and 256 KB. **NUM_CORES=8 is a Gate-3 hard lesson** (first tried 1 core as "smallest config"): the L1 core's internal FIFO depths scale with NUM_BLOCKS (`c_thriceNumBlocks=3·N`, `c_blckEosDepth=N²+N`, `zlib_compress.hpp:404-471`) — at N=1 they are 3/2 and the RTL **deadlocks on the second sequential block through the same core** (48 bytes out then silence; csim can't see it — untimed streams are unbounded, and csim itself reported max stream occupancy 4355 ≫ 3). 8-core is the envelope AMD RTL-tests with multi-MB files (routine same-core block reuse). Core count does not affect output bytes (packer is block-order-preserving; verified by cmp). Gzip output = stock-decodable (commodity-decode story). |
| D2 | Insertion = **store-and-forward CU beside the doorbell**, host-sequenced: preload original → CODEC start → poll done → read LEN_OUT → submit WQE with `laddr=DST, len=LEN_OUT` | RETH.DMALen is committed at 0x70 push time (doorbell splitter feeds `seg_len` to both SQ meta and pusher, `rdma_doorbell_l0.sv:287-321`); dynamic-Huffman length is unknowable before compression finishes ⇒ inline insertion is structurally impossible without this buffering anyway. Zero changes to roce_stack / HLS / splitter / pusher / port B. |
| D3 | Staging access = **port A sharing** (2:1 mux in `roce_l0_top`), host absolute priority | Port A is host-only and idle whenever the host is not touching the 0x8xxxxx window (`rdma_doorbell_l0.sv:241-254`); port B carries the certified placement-priority + pusher timing (`rdma_uram_staging.sv:199,248-252`) and must not gain a third contender. Compressed bytes must land **in staging** because the pusher reads `laddr` from staging port B — redirecting the pusher would touch the certified path. |
| D4 | Transform (chan / chan_bt) = **address-generator on the CU's staging read side**, byte-serial | chan_bt is a pure byte permutation (`layout.py:49-54` + `floatsplit.py:142-149`); reading bytes in permuted order from the random-access URAM implements it with **zero intermediate buffer**. 1 B/cycle ≈ 131 µs per 32 KB at 250 MHz — irrelevant for sim and for JTAG-paced board tests; a wide-path transform is a later throughput work item, not a correctness item. |
| D5 | Golden discipline = **csim `.gz` byte-identity** | csim and csynth RTL come from the same HLS source ⇒ deterministic byte-identical output. The RTL CU's compressed output (placement readback AND wire payload) must equal the csim-produced `.gz` for the same *python-transformed* input. This simultaneously proves the HW transform equals E0's `layout.transform` and the datapath is lossless. Independent second check: stock `gzip.decompress` + `layout.invert` roundtrip == original KV bytes. |
| D6 | α expectations are **measured at Gate 1, not inherited from E0** | E0's 0.708/0.721 were: transform over the whole 256KB/1MB chunk, then independent per-32KB zlib streams (`measure_e0.py:24`, `e0_codecs.py:25-49`). Our RTL path transforms per-WR (32 KB) and emits one gzip member. Deviations are real but small; Gate 1 measures the kernel's α on the same bytes at both granularities (32 KB WR-sized and 256 KB E0-sized) and those numbers become the recorded facts. Do NOT claim E0's α for the hardware path. |

---

## Part A — DCL kernel facts (recon-verified)

| Fact | Evidence | Consequence |
|---|---|---|
| Top candidates are thin shims over `xf::compression::gzipMulticoreCompressAxiStream<STRTGY, BLOCK_SIZE_IN_KB, NUM_BLOCKS, TUSR_DWIDTH>` | `L1/include/hw/zlib_compress.hpp:558-585`; L2 shim `L2/src/gzip_compress_multicore_stream.cpp:36-53`; L1 test shim `L1/tests/gzipc/gzip_compress_test.cpp:43-51` | We write our own 10-line shim (`codec/hls/gzipc_cu.cpp`) pinning template params; AXIS + ap_ctrl_none pragmas copied from the L1 test shim. |
| Pure streaming: `hls::stream<ap_axiu<64,0,0,0>>` in, `hls::stream<ap_axiu<64,32,0,0>>` out; ap_ctrl_none free-running; zero m_axi / XRT | `gzip_compress_test.cpp:43-51`; grep-verified no m_axi in the kernel | Drops straight onto an AXIS interface in RTL; no BAR, no host runtime. |
| Input contract: one TLAST-delimited packet = one file; **all beats before TLAST must be full 8 B**; TKEEP honored (popcounted, LSB-contiguous) only on the TLAST beat | `axi_stream_utils.hpp:147-190` | CU input packer must emit full beats + tail keep. Arbitrary `LEN_IN` supported. |
| Output contract: per-beat contiguous TKEEP=TSTRB; TLAST on final beat; **TUSER = total compressed bytes, valid only on the TLAST beat** (else 0) | `axi_stream_utils.hpp:88-145` (accumulator at 124-131) | `CODEC_LEN_OUT` latches TUSER at TLAST; cross-check = Σ popcount(TKEEP). |
| Output format: standard **gzip member** — 12 B header `1F 8B 08 08 00000000 00 03 'x' 00`, per-32KB dynamic-Huffman deflate blocks (BFINAL=0), <64 B tail as stored block, final empty stored block `01 00 00 FF FF`, CRC32(LE)+ISIZE trailer | `zlib_compress_details.hpp:374-460`; checksums on-chip via xf_security | `python gzip.decompress` / gunzip work stock. STRTGY=1 would give zlib+Adler32 — not used now. |
| Dynamic Huffman confirmed: `lz77Compress → zlibMultiTreegenStream (per-block) → zlibHuffmanEncoder` | `zlib_compress.hpp:536-544` | Matches the E0 requirement (static Huffman was catastrophic on KV). |
| Compile knobs: NUM_BLOCKS ∈ {1,2,4,8} (assert), BLOCKSIZE_IN_KB ∈ {8,16,32}, URAM_BUFFER, STATIC_MODE | assert `zlib_compress.hpp:419`; knobs `L2/include/gzip_compress_multicore_stream.hpp:39-59` | NUM_CORES=1 is legal but **AMD ships no 1-core test** → Gate 1 csims both 8-core (stock) and 1-core (ours); fallback 2. |
| Documented footprint (8-core/32KB dyn): 54 K LUT / 141 BRAM / 64 URAM @300 MHz, CR 2.70 Silesia; static variant 35 K LUT | `L2/tests/gzipc/README.rst`, `docs/src/source/L2/gzipc*.rst` | 1-core will be well under; VU9P usage is 7.63 % LUT — area is a non-issue, 250 MHz timing is the (later, build#4) risk. |
| 2025.2 toolchain fixups: xf_security headers must exist at `../security/L1/include` (**installed 2026-07-18** via Mac sparse-clone + tar); Makefile cfg-generator uses dead tps python → hand-write cfg; drop the directory-valued `tb.file` line; carry `syn.dataflow` FIFO-depth keys; `if constexpr` (C++17) in `axi_stream_utils.hpp:112,127` may need `-std=c++17`; stream payload structs are default-constructible PODs (Stage-A 2025.2 constraint satisfied) | recon 2026-07-18; `checksum_wrapper.hpp:31-32`; `compress_utils.hpp:48-64` | csim flow: `vitis-run --mode hls --config codec.cfg --csim </dev/null`; csynth: `v++ -c --mode hls`. Part `xcvu9p-flga2104-2L-e`, clock 4.0 ns. |
| Dead code warning: L2 single-core `xilGzipCompressStreaming` / `...FixedStreaming` call functions with **no definition in 2024.2** | grep-verified | Do not use; smallest working config = multicore top, NUM_CORES=1. |

## Part B — platform facts the CU builds on (recon-verified @c5820d0)

| Fact | Evidence | Consequence |
|---|---|---|
| WQE `len` is 28 b and **opaque end-to-end**; no module compares it to any "original" length; goldens already prove arbitrary lens (64/8K/12K) through identical machinery | `lynx_pkg.sv:111,145`; `rdma_doorbell_l0.sv:408`; splitter `:269-321`; `roce_stack.sv:106` | A compressed-length WR is **purely a host-programming difference**. Store-and-forward requirement satisfied at 0x70 push. |
| Doorbell auto-splits > PMTU into FIRST/MID/LAST, `seg_len = min(rem, 4096)`; RETH.DMALen = per-segment len (known IBTA deviation, CX-5 watch item) | `rdma_doorbell_l0.sv:269-272`; Stage B seam B4 | A ~23 KB compressed WR exercises the proven multi-segment path **plus** a non-64B-multiple tail — new coverage for free. |
| Constraints on the codec WR: `laddr` 64 B-aligned (sim assert), `len ≥ 1` (0x70 ignores len==0), non-64B-multiple len OK (dense tkeep on last beat) | `rdma_uram_staging.sv:223-226,206-209`; `rdma_doorbell_l0.sv:410` | `CODEC_DST` must be 64 B-aligned; `LEN_OUT` needs no rounding. |
| Staging = 256 KiB single XPM URAM tdpram, 4096×512 b, BYTE_WRITE_WIDTH 8, READ_LATENCY 1, no_change, 8×URAM288; window `addr[23]`, index `addr[17:0]` | `rdma_uram_staging.sv:52-53,255-308`; `rdma_doorbell_l0.sv:202,244` | Copy this exact XPM pattern for any new memory (8-12186 inference trap). Byte *i* of the buffer = word `i[17:6]`, lanes `[8*i[5:0] +: 8]` (LE lanes — same convention as the 32 b host preload replication). |
| Port A: host-only, single-cycle write strobes, read = strobe + sample 2 cycles later (doorbell samples at `rd_cnt==4`); idle between host window accesses. Port B: placement-priority + pusher — certified timing | `rdma_uram_staging.sv:75-82,119,199,248-252`; `rdma_doorbell_l0.sv:241-254,507-513` | CU attaches to port A behind a host-wins mux; port B untouched ⇒ all byte-level goldens structurally preserved. |
| Register decode is `case(addr[7:0])`; free gaps 0x74-0x7C, **0xB4-0xE0**, 0xE8-0xFC | `rdma_doorbell_l0.sv:364-420,455-490` | Codec block at 0xC0-0xDC fits with room to spare. |
| Clock/reset: single 250 MHz `clk_core`; active-low `rstn_core` from the build#3 two-stage `max_fanout=256` pipeline; CMAC domains isolated behind async FIFOs | `fpga_stage_d.sv:79-140`; `stage_d_core.sv:74-89,167-282` | CU is single-clock; replicate the local piped-reset pattern (reset fanout was the build#2 WNS killer). |
| Sim + synth both glob `roce-rtl-sim/rtl/l0/*.sv`; tb dispatches on `+TEST` string; TX wire capture `out/rtl_tx_<test>.txt` (`F%0d B%0d DATA=… KEEP=… LAST=…`) parsed by python checkers; watchdog 8 ms | `run_xsim_d.sh:21-45`; `create_project.tcl:37-58`; `tb_stage_d.sv:258-262,549+` | New CU file + generated kernel RTL slot in with two script edits (add `rtl/hls_codec/*.v` to both globs); `c_codec` is one new tb branch + one new checker. |
| E0 transform semantics: `chan` = `reshape(-1, head_dim).T` over the **whole chunk**; `chan_bt` = chan then whole-chunk byte-plane split (byte0 plane, then byte1 plane); e5m2 `chan_bt` ≡ `chan` (itemsize 1) | `layout.py:49-54,78-92`; `floatsplit.py:142-149` | The CU's address generator must reproduce exactly this, over the WR payload as "the chunk". bf16 LE: byte0 = exp-lsb+mantissa (high entropy), byte1 = sign+exp7 (low entropy). |
| KV stimulus: **no raw KV bytes persisted anywhere** — regenerated 2026-07-18 from cached Qwen2.5-7B (prefill K, mid layer, head_dim=128) via `capture_hf_kv._to_bytes`; layout `(seq, heads, head_dim)` LE | recon C; `capture_hf_kv.py:41-48`; generator `codec/data/gen_kv_blocks.py` + `blocks_manifest.json` (sha256) | Test payloads are real-model KV, reproducible from the committed script. |

---

## Part C — CU design (`rdma_codec_cu.sv`)

```
                         roce_l0_top (mux added; port B & pusher untouched)
 host (jtag_axi)          ┌──────────────────────────────────────────────┐
 ┌──────────────┐ regs    │ rdma_codec_cu                                │
 │ 0xC0-0xDC    │────────▶│ ┌─────────┐ bytes ┌────────┐ 64b AXIS ┌────┐ │
 │ CODEC_*      │         │ │addr-gen │──────▶│ 8B pack│─────────▶│HLS │ │
 └──────────────┘         │ │raw/chan/│       └────────┘ in       │gzip│ │
 staging port A ◀──mux───▶│ │chan_bt  │  ┌───────────┐  64b AXIS  │ CU │ │
 (host wins)              │ └─────────┘  │64B collect│◀───────────│1core │
                          │   reads      └───────────┘ out+TUSER  └────┘ │
                          │              writes → DST; TUSER→LEN_OUT     │
                          └──────────────────────────────────────────────┘
```

### C.1 Register block (decoded in `rdma_doorbell_l0`, exported to the CU)

| Addr | Name | Acc | Meaning |
|---|---|---|---|
| 0xC0 | CODEC_CTRL | W1 | bit0 START — snapshot SRC/DST/LEN_IN/CFG, clear done/err, go. Ignored while busy. |
| 0xC4 | CODEC_STATUS | RO | `{err_len[3], err_align[2], done[1], busy[0]}` — done sticky until next START |
| 0xC8 | CODEC_SRC | RW | staging byte offset of original (any byte alignment) |
| 0xCC | CODEC_DST | RW | staging byte offset for compressed output — **64 B-aligned** (checked; also the future WQE laddr) |
| 0xD0 | CODEC_LEN_IN | RW | original length in bytes, [17:0] (max 2^18−1; window-bounded) |
| 0xD4 | CODEC_LEN_OUT | RO | compressed bytes (TUSER at TLAST); the value the host then writes to WQE 0x68 |
| 0xD8 | CODEC_CFG | RW | `mode[1:0]` 0=raw 1=chan 2=chan_bt; `hd_log2[7:4]` head_dim=1<<hd_log2; `item16[8]` 0=1 B (e5m2) 1=2 B (bf16) |
| 0xDC | CODEC_CYCLES | RO | busy-cycle counter (perf hook for the research phase) |

Alignment checks at START (else `err_align`, no start): mode≠raw ⇒ `LEN_IN % (head_dim<<item16) == 0`
(the E0 gate, `run_e0.py:52-53`); `DST[5:0]==0`; `LEN_IN>0`. `err_len` set if TUSER(TLAST) ≠ Σ popcount(TKEEP)
(cross-check of the two length witnesses).

Submit-time snapshot discipline (C-R1 precedent): START latches all four registers into shadow
copies; mid-run register writes cannot affect the running job.

### C.2 Transform address generator (D4)

One generic 3-level counter covers all modes. With `rows = LEN_IN >> (hd_log2 + item16)`,
`P = 1<<item16` planes, `C = head_dim` channels:

```
chan_bt (mode 2):                         chan (mode 1):
for p in 0..P-1:      # plane OUTER       for c in 0..C-1:
  for c in 0..C-1:                          for r in 0..rows-1:
    for r in 0..rows-1:                       for p in 0..P-1:   # plane INNER
      emit SRC+((r<<hd_log2|c)<<item16|p)       emit SRC+((r<<hd_log2|c)<<item16|p)
raw (mode 0): emit byte SRC + i, i = 0..LEN_IN-1
```

(Review finding, lens 2: for bf16 the two modes differ only in plane-loop position —
`chan` keeps intra-value byte order (p innermost), `chan_bt` splits planes (p outermost);
for e5m2 (P=1) they coincide, matching `byte_transpose` = identity at itemsize 1. Both
loop orders are implemented; a bf16 `chan` job is legal but is not a claim path.)

Equivalence proof sketch (recorded here, asserted by D5's golden): `channel_major` output
value index `j = c*rows + r` maps to input value `r*C + c` (`layout.py:53` transpose);
`byte_transpose` then emits byte-plane p of the value sequence in order (`floatsplit.py:148`
`u8.T`), so transformed byte `p*N + j` = input byte `(r*C+c)*itemsize + p`. The generator
walks output offsets `p*N + j` in ascending order emitting exactly that input byte. For
e5m2 P=1 ⇒ pure `chan`, matching `byte_transpose` = identity at itemsize 1.

Shifts only (head_dim restricted to powers of two — all E0 models: 64/128). Reads are
issued non-pipelined, 3 cycles/byte (ISSUE→WAIT→CAPTURE; race-free analysis in C.3).

### C.3 Port-A arbitration (D3) — simpler than first sketched (source-verified)

The CU speaks the **same 5-signal 32-bit port-A protocol as the doorbell**
(`stg_en/we/addr[17:0]/wdata[31:0]/wstrb[3:0]` + shared `stg_rdata[31:0]`), so
`rdma_uram_staging.sv` is **completely untouched**; the only new logic is a 2:1 bundle
mux in `roce_l0_top` and one exported signal from the doorbell.

- Doorbell exports `stg_host_active = (aw_got & w_got & wr_is_stg & ~bvalid) |
  (ar_got & rd_is_stg & ~rvalid)` — every cycle in which the doorbell may strobe port A
  or has a staging read transaction in flight (covers the `rd_cnt==4` sample window,
  `rdma_doorbell_l0.sv:237-254,502-513`).
- Mux: doorbell bundle wins whenever the doorbell strobes; CU only strobes when
  `!stg_host_active`, so the two never collide by construction.
- **CU read timing is race-free without any replay** (traced against
  `rdma_uram_staging.sv:84-91`): a CU read strobed at T is captured from `stg_rdata`
  at T+2; that value is a function of `a_q`/`a_lane_q` during T+1, which a host strobe
  at T+1 cannot affect (its effects land at T+2/T+3), a host **write** never touches
  them (XPM no_change holds `douta`), and a host strobe at T is impossible (CU gated).
  CU reads are therefore issued non-pipelined ISSUE→WAIT→CAPTURE, 3 cycles/byte
  (32 KB ≈ 393 µs at 250 MHz — irrelevant vs the 8 ms watchdog; a pipelined 1 B/cycle
  upgrade is future throughput work, not correctness).
- CU **writes** are single-cycle 32-bit strobes (`wstrb` for the tail), only issued when
  `!stg_host_active` — delayed, never corrupted. Output beats (8 B) become two 32-bit
  writes at the DST cursor.
- CU-internal interleave: output writes take priority over input reads (output must
  drain so the free-running kernel never wedges; input stalling is always safe).
- Consequence: a host poke of the staging window mid-run only **stalls** the CU;
  results are unaffected — asserted in sim (`c_codec` performs a deliberate staging
  read during busy). Driver discipline: poll CODEC_STATUS (a plain register), not the
  staging window, while busy.

### C.4 Kernel integration

- `codec/hls/gzipc_cu.cpp`: project-owned shim `void gzipc_cu(in, out)` calling
  `gzipMulticoreCompressAxiStream<0, 16, 1, 32>` (D1 final: 16 KB blocks) with the
  AXIS/ap_ctrl_none pragmas from the L1 test shim. csynth `@ 4.0 ns`, part
  `xcvu9p-flga2104-2L-e`; generated Verilog copied to `roce-rtl-sim/rtl/hls_codec/`
  (both script globs extended). Generated top ports (Gate 2): TDATA/TKEEP/TSTRB/TLAST
  each side + TUSER[31:0] out, ap_clk/ap_rst_n, no TID/TDEST; drive TSTRB = TKEEP.
- Input side: 8-byte pack register → AXIS beat (`data[8j+:8]` = j-th byte, LSB-first —
  the `axiu2hlsStream` convention); TLAST + contiguous tail TKEEP on the final beat.
- Output side: keep-masked bytes stream through a small accumulator into **32-bit
  port-A writes** at the DST cursor (two per full 8 B beat, `wstrb` on the tail) — the
  port-A write path is 32-bit-with-byte-enables by construction
  (`rdma_uram_staging.sv:75-82`), nothing wider is expressible, staging is untouched
  (review MAJOR, lens 1 — resolved by dropping the earlier 64 B-accumulate wording).
  TUSER at TLAST → LEN_OUT; the CU's strobe count is compared to TUSER (`err_len`) —
  both derive from kernel strobes, so this catches CU accumulation bugs only; the
  independent witness is the csim golden + stock decode (D5).
- Reset: CU + kernel `ap_rst_n` from a local two-FF `rstn` pipe off `rstn_core`
  (`shreg_extract="no", max_fanout=256` — build#2 lesson). ap_ctrl_none kernels need
  the reset held for a few cycles: tb + shell hold reset ≥ 16 cycles already.
- xsim watch item: Stage B's X-init BRAM deadlock precedent → if the generated kernel
  RTL wedges in xsim, first run standalone HLS **cosim** (Gate 2) to separate
  "kernel-RTL sim health" from "integration bug", then apply the SIM_ZERO_INIT
  treatment if needed.

---

## Part D — verification plan

**Gate 1 — kernel csim under 2025.2 — ✅ PASSED 2026-07-18 (user-flagged 07-17).**
Data: `codec/data/` per `gen_kv_blocks.py` (Qwen2.5-7B prefill-K L14, head_dim=128,
sha256 manifest). Measured (all TB_PASS, TUSER law held, `verify_gz.py` roundtrips
7/7 PASS, **no 2025.2 fixups needed beyond the security-headers install** — no
`-std=c++17` flag, no cfg surgery):

| input | α @ blk32 | α @ blk16 | software V3 |
|---|---|---|---|
| bf16 32 KB chan_bt | 0.7723 | **0.7162** | 0.7240 |
| e5m2 32 KB chan | 0.7362 | 0.7365 | 0.7545 |
| bf16 256 KB chan_bt | 0.7005 | 0.7005 | 0.7101 |
| bf16 4 KB raw | 0.8506 | 0.8506 | — |

Findings of record: (1) the per-block Huffman-tree/plane-boundary interaction (D1) —
blk16 fixes the 32 KB chan_bt WR case; (2) **1-core vs 8-core output byte-identical**
(`cmp` clean) — core count is pure throughput; (3) kernel α at E0 granularity (0.7005)
lands 0.01 *better* than the software V3 proxy — the D6 honesty note cuts both ways.
The `golden16/*.gz` files are the Gate-3 goldens.

**Gate 2 — csynth ✅ DONE 2026-07-18 / cosim smoke pending.** `v++ -c --mode hls`
@4.0 ns, VU9P: final config (1-core/blk16) = **54,659 LUT (4 %) / 20,933 FF / 65 BRAM /
8 URAM**, 247 generated .v files (blk32 control: 46,364 LUT / 29 BRAM / 12 URAM).
**HLS slack estimate −1.90 ns** — recorded as the build#4 risk; Stage B precedent says
HLS estimates are pessimistic (151.9 MHz est → 250 MHz closed), and the decoupled
store-and-forward CU admits a clean fallback: its own slower clock domain (CDC at the
CU boundary), since P4 throughput is irrelevant. RTL cosim on the 4 KB raw case still
to run (kernel-RTL health; dataflow FIFO depths carried via cfg keys).

**Gate 3 — RTL integration (`P4-RTL`).**
1. `c_codec_raw` — 4 KB raw mode, **run TWICE back-to-back** (review MINOR, lens 3: the
   free-running kernel is never reset between jobs — the second job proves re-arm):
   preload → codec → LEN_OUT → WQE(laddr=DST, len=LEN_OUT) → loopback → placement
   readback, both iterations. Checks: RTL compressed bytes ≡ csim `.gz` (D5) each time;
   placement ≡ wire payload ≡ LEN_OUT bytes; `gzip.decompress` == original.
2. `c_codec` — 32 KB bf16 chan_bt: same + HW-transform-vs-python equivalence via D5;
   multi-segment (~6 segs incl. non-64B tail); mid-run host staging read (C.3 assert);
   frame accounting tx = segs+ACKs, `CNT_RETRANS==0`, CQE=1.
3. `c_codec_e5m2` — 32 KB chan (P=1 path).
4. **Full regression** — all 10 existing tests byte-identical (structural argument: port B,
   pusher, splitter, stack untouched; mux defaults to host; codec idle unless started).
5. Checker `check_codec.py`: parses `rtl_tx_<test>.txt` + placement dump + `codec/data`
   goldens; asserts the D5 identity, the roundtrip, RETH/DMALen-vs-LEN_OUT accounting,
   and prints α.

Watchdog: 32 KB feed ≈ 131 µs + kernel latency ≪ 8 ms tb watchdog — no change needed;
`c_codec` total sim wall-clock dominated by the 8192 AXI-Lite preload writes (precedent:
c_write8k/12k).

**Deliberately deferred** (recorded so they are not silently lost): decompression path on
RX (asymmetric commodity-decode is the design), inline/cut-through codec, gate circuit,
rate sweep, WRITE_WITH_IMM(orig_len) dual-length verb surface for CX-5, >1-core scaling,
build#4 synthesis + board codec STEP.

## Implementation log (P4-RTL, 2026-07-18)

- Files: NEW `roce-rtl-sim/rtl/l0/rdma_codec_cu.sv` (CU + kernel instance),
  `roce-rtl-sim/rtl/hls_codec/` (268 csynth .v + 11 ROM .dat), `codec/`
  (hls shim, csim/csynth runners, goldens, data + manifest),
  `stage_d_shell/sim/check_codec.py`, `run_gate_p4.sh`. MODIFIED
  `rdma_doorbell_l0.sv` (regs 0xC0-0xDC, `stg_host_active`, ID→**0x0C1A_0004**),
  `roce_l0_top.sv` (port-A bundle mux + CU instance), `tb_stage_d.sv`
  (3 codec branches + tasks + probe), both sim scripts + synth tcl (hls_codec
  glob), `tb_stage_c.sv` (ID). Zero changes to `rdma_uram_staging.sv`,
  the pusher, splitter, stack.
- **Mine #1 (fixed): missing explicit `F_IDLE` case arm.** The feed-engine
  `case` had `default: f_state <= F_IDLE;` which executes in the same
  `always_ff` AFTER the start block's `f_state <= F_ISSUE` — last nonblocking
  assignment wins, CU never leaves idle (busy=1, fed=0 forever). Same class
  as P3's `sq_fetch` declaration-init freeze: SV intra-block ordering bites.
- **Mine #2: HLS ROM `.dat` files.** The generated kernel reads 11 ROM images
  via `$readmemh("./gzipc_cu_*.dat", …)` — resolved against xsim's RUN
  directory, not the RTL directory. They must be copied into every sim run
  dir (`stage_d_shell/sim/`, `roce-rtl-sim/`) and — for build#4 — made
  visible to Vivado synthesis (watch item).
- **Mine #3: HLS cosim harness broken in this env** (`xsim_53.c` C-compile
  fail inside the AESL deadlock-monitor infra, with or without the Stage-B
  LIBRARY_PATH fix; plus missing `zip` utility). Not pursued: the integration
  xsim compiles and runs the same kernel RTL directly, which answers the
  "kernel-RTL sim health" question the cosim smoke existed for.
- Module-namespace check: 54 rocev2 vs 131 codec generated modules,
  **zero collisions** (HLS prefixes everything with the top name).
- **Mine #5 (STACK CONTRACT, found by the first non-4B-multiple wire length in
  platform history): the icrc reinsertion stage only handles last-beat TKEEPs
  at 4-byte granularity** (`icrc.sv:735-860` — the if-else chain enumerates
  keeps of 4,8,…,60 bytes + full-64; a 62-byte last beat matches NO arm →
  stale data/keep emitted, observed as the final beat vanishing from the wire
  and 38 payload bytes placed as zeros). This is IBTA reality leaking through:
  RoCE payloads are PadCount-padded to 4 B, so the stack never generates such
  frames — every certified test (64/8K/12K, and compressed 3484/3656) is a
  4 B multiple; bf16's LEN_OUT 23486 (tail 3006, keep 62) was the first
  violation ever sent. **Resolution: honor the contract, don't patch the
  certified stack** — the CU zero-fills its final 4 B write lane and the
  driver submits `len = ceil4(LEN_OUT)` (pad never crosses the lane since the
  write granule is 4 B); `CODEC_LEN_OUT` stays exact. Goes to the manual fault
  table + the CX-5 interop checklist (PadCount handling for odd lengths).
- **Mine #6 (D5 REVISION, multi-block only): RTL kernel output is a
  different-but-valid gzip vs csim for MULTI-block inputs** (+16 B on bf16
  32 KB, +1 B on e5m2 32 KB; first diffs inside block 1's coded region;
  single-block 4 KB stays byte-identical). The 8 concurrent cores +
  shared-treegen arrival order make inter-block packing timing-dependent in
  RTL, while csim is sequential. **Verified: `gzip.decompress(RTL bytes)` ==
  transformed input bit-exact in both cases** — content-correct, stock-
  decodable, α within 0.1 % of csim. D5 golden discipline is therefore
  two-tier: byte-identity-to-csim for single-block inputs; decode-bit-
  exactness + CU-out ≡ placement ≡ wire identity + α-report for multi-block
  (`check_codec.py` implements exactly this). Consequence for the board:
  wire-side compressed bytes may vary run-to-run (arrival timing), so board
  goldens must also be decode-based, never byte-based, for >16 KB payloads.
- **Mine #4 (fixed by D1 revision): 1-core kernel RTL deadlock on
  multi-block input.** `c_codec` (32 KB = 2×16 KB blocks) fed all input, kernel
  emitted 48 bytes, then wedged with no backpressure anywhere (probe: kin r1/v0,
  kout v0, fed=32768). Root cause = NUM_BLOCKS-scaled internal FIFO depths
  (see D1). Materializes exactly the "NUM_CORES=1 untested by AMD" risk —
  csim green ≠ RTL green for dataflow kernels. Final config 8-core/16 KB =
  AMD's shipped-and-tested `gzipc_16KB`; goldens regenerated, 1-core-vs-8-core
  output byte-identity re-verified per input.
- `c_codec_raw` (4 KB raw × 2 back-to-back jobs): **PASS** — LEN_OUT=3484
  both jobs (== csim golden), CYCLES=23511 identical (deterministic re-arm,
  review lens-3 closed), and `check_codec.py` all four identities PASS
  (decode roundtrip / CU-out ≡ golden / placement ≡ golden / wire ≡ golden×2
  incl. the non-64B tail segment).

## RESULT (P4-RTL sim gate, 2026-07-19)

**All three codec tests + all byte-level checks PASS** (final config
8-core/16 KB/gzip, IBTA-pad drain, F_IDLE fix):

| test | flow | LEN_OUT | wire | segs | α (csim) | verdict |
|---|---|---|---|---|---|---|
| c_codec_raw ×2 jobs | 4 KB raw | 3484 / 3484 | 3484 | 1+1 | 0.8506 (=) | **csim byte-identical**, CYCLES=23511 both |
| c_codec | 32 KB bf16 chan_bt | 23486 | 23488 (+2 pad) | 6 | 0.7167 (0.7162) | alt-encoding, decode bit-exact |
| c_codec_e5m2 | 32 KB e5m2 chan | 24136 | 24136 | 6 | 0.7366 (0.7365) | alt-encoding, decode bit-exact |

Identity chain held in every case: CU output ≡ placement ≡ on-wire WRITE
payload (per-segment framing + non-64B tail + pad), `CNT_RETRANS==0`, CQE
accounting exact, mid-run host staging poke only stalled the CU. The **HW
transform address generator is proven equivalent to E0's python transform**
(bf16 chan_bt AND e5m2 chan: kernel output over the HW-transformed stream
decodes bit-exact to the python-transformed input; for the byte-identical raw
case the equality is direct). Dual-length surface demonstrated end-to-end:
WQE len = ceil4(LEN_OUT) ≠ original length, RETH/DMALen in wire units,
responder placed compressed bytes content-agnostically.

Full-platform regression gate (`run_gate_p4.sh`): Stage C 4 tests +
byte-invariance vs certified goldens, Stage D 10 tests + per-flow goldens +
both B9 retrans DATA checks, then the 3 codec tests — see gate log
(myDevbox `/tmp/gate_p4.log`, archived with the run outputs).

## Risks / watch items

- **NUM_CORES=1 untested upstream** → Gate 1 control run at 8-core; fallback 2.
- **xsim health of generated kernel RTL** (Stage B X-init precedent) → Gate 2 cosim
  isolates; SIM_ZERO_INIT treatment if needed.
- **Port-A read-replay window**: the 2-cycle discard-and-replay must be exact or a host
  poke mid-run corrupts one byte — covered by the deliberate mid-run poke in `c_codec`
  (and harmless-by-discipline on the board).
- **`if constexpr` / C++17 under 2025.2 csim** → add `-std=c++17` on first error.
- **Kernel latency between input TLAST and output TLAST is unbounded by contract** —
  CODEC_CYCLES + tb watchdog bound it empirically; no hardware timeout in P4 (host can
  re-START; a wedged kernel needs reset — recorded as a bench-ops note).
- **No hardware interlock stops a doorbell strike whose pusher reads DST while the CU
  is still writing it** (review MINOR, lens 1) — an L0-style software constraint, same
  class as "poll STATUS.busy before doorbell": **poll CODEC_STATUS.done before
  submitting a WQE whose laddr overlaps DST**. A hardware gate (0x70 rejected while
  codec busy) was considered and rejected: it would also forbid *legitimate* concurrent
  WRs from non-overlapping staging regions (the research phase pipelines exactly that),
  and true overlap detection needs laddr-vs-DST range compare against in-flight
  segments — cost out of proportion to a driver-ordering bug that produces a visibly
  torn payload and cannot wedge. Recorded in the doorbell header; all tests obey it.
- **α ≠ E0 numbers by construction** (D6) — the design doc and any report must quote
  Gate-1-measured α, never 0.708/0.721, for the hardware path.
- **250 MHz timing of the kernel** is a build#4 (post-sim) risk; documented 300 MHz on
  the same die is encouraging but not evidence.
