# L1 doorbell (SQ ring) + retransmission re-housing — 平台可用期工作项 ③

> 旧名 `PLATFORM_USABLE_P3_DESIGN.md`（"P3" = 平台可用期第 ③ 项，2026-07-19 改为描述名）。

Design document for platform-usable item **③**. Grounds two RTL changes in verified
recon of the `fns`/`fpga-network-stack` `coyote-TCP-RDMA` @20633d03 stack: the SQ /
completion path (`rdma_flow.sv`) and the retransmission-buffer memory contract
(`rdma_mux_retrans.sv` + HLS `retransmitter`/`transport_timer`). It supersedes the two
open items the platform inherited from Stage E:

- **Single outstanding WR.** The L0 doorbell (`rdma_doorbell_l0.sv`) pushes one WR's
  segments then idles (`DB_IDLE→DB_CMD→DB_PAY→DB_IDLE`). Any throughput / rate-limiter
  experiment needs many WRs in flight — the standard verbs SQ-ring model.
- **Retrans tie-off = wedge + B9 blind.** `stage_d_core.sv` ties the six retransmission-
  buffer ports off. Loopback ACKs return instantly so retrans never fires *in the happy
  path*, but any real frame loss ⇒ `CNT_RETRANS!=0` + permanent TX stall (reflash-only
  recovery), and the requester timer retransmission (Stage B finding **B9**) can never be
  observed because there is nowhere to read the retransmitted payload from.

Both are prerequisites for the codec / dual-length-verbs research phase.

---

## Part A — L1 doorbell: SQ ring for multiple outstanding WRs

### A.1 What the stack already gives us (recon-verified)

| Fact | Evidence | Consequence for L1 |
|---|---|---|
| Multiple outstanding is the **intended** mode; per-QP `head`/`tail`/`issued` window | `rdma_flow.sv:64-74,147,151,158,173` | No serialization between WRs is required beyond payload order. |
| Outstanding window = **16 SEGMENTS** (`RDMA_N_WR_OUTSTANDING=16`), counts dreq beats not WRs | `lynx_pkg.sv:218`; gate `rdma_flow.sv:169 if(!issued\|\|(head!=tail))` | ≈16 single-seg WRs, or ≈5 three-seg (12K) WRs, in flight before `s_rdma_sq.ready` drops. Sliding window: push all beats, ready throttles. |
| Second, tighter limit: payload-sequencing queue **depth 8** (`N_OUTSTANDING`) | `rdma_mux_retrans.sv:147-149`, `lynx_pkg.sv:289` | ≤8 outstanding payload/read commands. Design budget = **8 outstanding segments** to stay under both. |
| Payload consumed **strictly in SQ-command order**; must push exactly `len` bytes/segment, **no interleave** across WRs | `ib_transport_protocol.cpp:1074,1130-1138`; `rdma_mux_retrans.sv:237-238` back-pressures the pusher | L1 may pipeline WR#2's SQ cmd + payload behind WR#1, but must emit payload beats in enqueue order. |
| `dreq.req_1.offs` is **overwritten** by `rdma_flow` with the retrans slot (`= head`) | `rdma_flow.sv:130` | L1 must NOT use `offs` for its own bookkeeping. |
| PSN allocated **inside HLS**, not by us | `generate_ibh` per-QP state table | Fast enqueue cannot race PSN. |
| Completion = **one last-gated `m_rdma_ack` beat per WR, in order** | `rdma_flow.sv:145 ack_que_in.valid=s_ack.data.last`; `ibtp.cpp:748-754` | Track completions by **counting last-gated ACKs and advancing a consumer index** — this is the CQE-to-WR match. |
| `ack_t.pid` = **QPN low bits, not a per-WR tag** | `roce_stack.sv:119`; every WR on QP shares pid=17 | Cannot disambiguate WRs by pid; must count in order. |
| CQ write in `rdma_flow` is **unguarded / lossy** (valid asserted without checking ready, depth 16) | `rdma_flow.sv:143-145` | **L1 must keep `m_rdma_ack` continuously drained** or it silently drops completions and desyncs its consumer index. L0 hides this with `s_ack_if.ready=1'b1`. |
| Retransmitted last packet does **not** normally double-CQE (dup ACKs PSN-filtered before `rx_exh_fsm`) | `ibtp.cpp:~404-419` | Residual double-count risk only at PSN window edges — design the consumer index to be idempotent-tolerant / bounded, and flag it as a watch item. |
| `ack_gap_enforcer.sv` forces ~90 ns between processed ACKs (HLS ingest-rate workaround) | `ack_gap_enforcer.sv:44,52-68` | Rate-limits how fast completions are absorbed; L1 completion FSM must tolerate bursty-but-gapped ACKs. |
| Coalescing (Mellanox) peer hazard: requester pops **one** retrans entry per `RC_ACK` | `retransmitter.hpp:419` | Out of scope here (loopback peer acks per-segment), but a CX-5 interop watch item. |

### A.2 Design

**Keep L0 intact underneath.** The L1 doorbell is a *producer* in front of the existing
`rdma_doorbell_l0` splitter+pusher — it does not replace the FIRST/MIDDLE/LAST split, the
proactive payload push, or the completion counters. The current single-WR register path
stays valid (a 1-deep ring), so every Stage C/D/E golden and the board `write64/8k/12k`
STEPs remain byte-for-byte reproducible.

```
 host (jtag_axi / DMA)            L1 doorbell (new)                 L0 (unchanged)
 ┌───────────────┐   WQE writes  ┌──────────────────────┐  one WR   ┌─────────────────┐
 │ SQ ring in    │──────────────▶│ producer_idx (host)  │  at a     │ splitter FSM    │
 │ BRAM (N=16    │               │ consumer_idx (fetch) │  time     │ FIRST/MID/LAST  │
 │ WQEs × 32B)   │   ring DOORBELL│ fetch FSM: read WQE, │──────────▶│ + payload pusher│
 │ + payload in  │──────────────▶│ drive L0 regs+strike │           │ (rdma_uram_stg) │
 │ URAM staging  │               │ when L0 !busy &&     │           └─────────────────┘
 └───────────────┘               │ outstanding<BUDGET   │                   │ m_rdma_ack
                                  │ compl_idx (count ACK)│◀──────────────────┘ (last-gated)
                                  └──────────────────────┘
```

- **WQE ring**: `N_SQ=16` entries × 32 B in a simple dual-port BRAM (host write port via
  AXI-Lite window; fetch read port). Fields per WQE: opcode[4:0], last, pid[5:0]/vfid[3:0],
  laddr[47:0], raddr[47:0], len[27:0]. (Payload continues to live in the existing URAM
  staging window, addressed by `laddr` — unchanged.)
- **Producer index** `sq_prod`: host writes WQE fields to `SQ_WQE_*` shadow regs, then
  writes `SQ_PUSH` (W1) → the shadow snapshots into ring[`sq_prod`], `sq_prod++`. (Mirrors
  L0's submit-time snapshot discipline, review finding C-R1.)
- **Fetch FSM** `sq_cons`: when `sq_cons != sq_prod` AND L0 is `DB_IDLE` (`STATUS.busy==0`)
  AND `outstanding < BUDGET`, read ring[`sq_cons`], drive the L0 WQE registers, strike the
  L0 doorbell, `sq_cons++`, `outstanding++`. **BUDGET=8** (min of the 16-segment window and
  the 8-deep payload queue; conservatively counted in WRs for the ≤PMTU common case, or in
  segments when we later pipeline multi-seg WRs — start WR-granular).
- **Completion** `sq_compl`: count last-gated `m_rdma_ack` beats (exactly L0's `c_cqe`),
  each one `sq_compl++`, `outstanding--`. `m_rdma_ack.ready` stays `1'b1` (drain always).
- **Serialization within a WR is still L0's job** (payload push completes before its next
  segment). L1 only gates *WR-to-WR* on `outstanding<BUDGET` and L0-idle, which guarantees
  payload is pushed in SQ order (no cross-WR interleave — the A.1 hard requirement).

### A.3 Register-map extension — AS BUILT (simpler than first sketched)

The implementation **unifies** the ring producer with the existing doorbell instead
of adding a separate SQ_WQE shadow block: `0x70 DOORBELL` **is** the ring push. The
host writes the existing WQE shadow (0x50–0x6C) then strikes `0x70` per WR; each strike
snapshots the shadow into `sq_ring[sq_prod]` and advances `sq_prod` (ignored if the ring
is full or `len==0`). The only new register is a status word:

| Addr | Name | Acc | Meaning |
|---|---|---|---|
| 0x70 | DOORBELL | W1 | **push** WQE shadow → `sq_ring[sq_prod]`, `sq_prod++` (was: direct issue) |
| 0xE4 | SQ_STATUS | RO | `{ring_full, 3'b0, outstanding[3:0], sq_compl[7:0], sq_cons[7:0], sq_prod[7:0]}` |

Why simpler is better here: it reuses the proven 0x50–0x70 decode and the C-R1 snapshot
discipline (the snapshot now happens at push, even earlier than the old doorbell-time
capture, so a mid-WR shadow rewrite provably cannot corrupt an in-flight segment — the
`c_write12k` mutation probe confirms it). Legacy single-WR use is literally a 1-deep ring,
so the frame content is issue-timing-invariant and every Stage C/D golden is byte-identical
(verified). ID bumps to **0x0C1A0003** for build#2.

Single-driver discipline: `sq_prod` in the register-write process, `sq_cons` in the
doorbell FSM (fetch), `sq_compl` in the counter process (one per last-gated `m_rdma_ack`).
`outstanding = sq_cons − sq_compl` (no separate up/down counter, no underflow); the fetch
gate is `(sq_prod≠sq_cons) && outstanding<SQ_BUDGET`.

### A.4 Why not deeper / fancier
The stack caps us at 16 segments; a ring deeper than that only queues host-side latency
hiding, which JTAG (100 ms/txn) makes irrelevant until a DMA WQE-fetch front-end exists.
Ship N=16 ring / BUDGET=8; DMA fetch and >16 windows are future work.

---

## Part B — retransmission-buffer re-housing (tie-off → on-chip URAM)

### B.1 The memory contract (recon-verified)

- **Command**: 96-bit `{len[31:0], addr[63:0]}` on `m_rdma_mem_wr_cmd` / `m_rdma_mem_rd_cmd`
  (`rdma_mux_retrans.sv:83-84,129-134`). **Data**: 512-bit AXIS (`m_axis_rdma_mem_wr` out,
  `s_axis_rdma_mem_rd` in), `len/64` beats, `tlast` on last.
- **No status handshake**: the stack never consumes `mem_*_sts` (`roce_stack.sv:261-262`
  only tie `.ready=1`). Re-house may leave `sts.valid` low forever.
- **Address is RTL-computed, NOT the vaddr**: `addr = {vfid, pid, offs, 12'b0} << 27`
  (`rdma_mux_retrans.sv:129-141`). **Low 39 bits are always zero.** For our single QP
  (vfid=0, pid=17) the distinguishing field is `offs` (0..15, the outstanding slot).
  → **Index the URAM by `addr >> 27`**, i.e. `{pid, offs}` — *not* `addr & mask` (which
  collapses every slot onto byte 0). Slot pitch after the `>>27` un-shift = `offs<<12` =
  4 KiB; size each slot **≥ 16 KiB** so a multi-PMTU segment burst cannot overrun the next.
- **Write side**: every outgoing WRITE segment mirrors its payload into its slot
  (`ibtp.cpp:1137`, `PKG_NR`→`actv=1`; mux forks host-read payload into both stack and
  buffer, `rdma_mux_retrans.sv:326-331,359`). 1 cmd per segment, data strictly after cmd,
  `len/64` back-to-back 64 B beats.
- **Read side (retransmission)**: on timer fire, `process_retransmissions` walks the
  unACKed list head→tail emitting **one read per stored segment** at the same `offs`
  (`retransmitter.hpp:508-526`; `ibtp.cpp:1112`, `PKG_R`→`actv=0`→`req_ddr_rd`). Reads are
  serialized (single-transaction FSM, `rdma_mux_retrans.sv:232-295`), each command's full
  data returns in order, never interleaved mid-burst with a write.
- **Timer (why B9 saw nothing in 240 µs)**: round-robin, one QP/cycle; first timeout ≈
  `TIME_1ms(611) × MAX_QPS(256) ≈ 156k cycles` (`transport_timer.hpp:56,161-179`;
  `rocev2_config.hpp:8`). At 250 MHz that's **≈ 626 µs**, and only if the ACK is dropped
  (a valid ACK resets `time`/`retries`, `transport_timer.hpp:120-133`). Retry escalation
  1/5/12/64 ms (`RETRANS_S*=3`), final give-up at `RETRANS_RETRY_CNT=12` (goes quiet, no
  explicit QP-error state). **RETRANS_EN=1** on this branch (`rocev2_config.hpp:4`).

### B.2 Design

A synthesizable dual-port URAM buffer `rdma_retrans_uram` — AS BUILT sized to the real
working set: each `offs` slot holds exactly ONE PMTU segment (the doorbell pre-splits
>PMTU WRs, one `offs` per segment), so 16 slots × 4 KiB = **64 KiB** (recon-confirmed max,
not the 256 KiB first sketched — a segment is never >PMTU). ~2 URAM288, trivially inside
the >88 % headroom. slot = `addr[42:39]` (offs), word = `{slot, beat}`:

```
 roce_stack mem_wr_cmd (96b) ─▶ decode addr>>27 = {pid,offs} ─▶ base = offs*16KiB
 roce_stack m_axis_rdma_mem_wr (512b, len/64 beats) ─▶ URAM write port (byte-en, seq addr)
 roce_stack mem_rd_cmd (96b) ─▶ same decode ─▶ URAM read port ─▶ s_axis_rdma_mem_rd (512b)
 mem_*_sts: valid tied low (unused by stack)
```

- **Write path (cmd-FIFO paced — adversarial-review BLOCKER fix)**: the upstream mux
  decouples command acceptance from its data FSM (provisions `N_OUTSTANDING=8`), so under
  multi-WR it can emit segment k+1's write command while segment k's payload is still
  streaming. A directly-latched write slot would be hijacked mid-frame and silently corrupt
  the URAM. Fix: a 16-deep command-slot FIFO; the active write slot is the FIFO **front**
  (oldest un-drained command, whose data streams now), popped on that frame's `tlast`. Data
  arrives in command order (mux seq FIFO), so front == current data. Depth 16 > 8 ⇒
  `cmd.ready` is effectively always 1, preserving the tie-off's zero-backpressure timing.
- **Read FSM**: latch `{offs,len}` on `mem_rd_cmd`, read `len/64` beats out to
  `s_axis_rdma_mem_rd` with `tkeep`/`tlast` matching `len` (mirror the TB `serve_rbuf_rd`).
- **Arbitration**: writes (happy path, every segment) vs reads (rare, on timer). Single
  shared port with write-priority is fine — the stack serializes reads anyway; a read only
  happens after a timeout when writes for that WR have long completed.
- **URAM inference**: same XPM path Stage D proved (`xpm_memory_*`, byte-enable, no async
  read). Avoids the `8-12186` BWE+TDP inference trap by using an XPM instance, not inferred
  TDP.

This **removes the wedge** (a lost frame now retransmits from the buffer instead of
stalling forever) and **makes B9 testable** (a TB that drops one ACK and runs ≥ ~160k
cycles will observe the timer retransmission reading the buffer).

### B.3 TB fix required (latent bug found in recon)
`tb_stage_c.sv:170,188` models the rbuf with `& (MEM_BYTES-1)` on the raw 64-bit address —
which, given the low-39-zero layout, **collapses all `offs` onto offset 0**. It has been
harmless only because retrans never fires in the loopback goldens (write-into-void). The
new `rdma_retrans_uram` and any B9 test must index by `addr >> 27`; the TB behavioral model
(and the new URAM RTL) must both adopt `{pid,offs}`-based addressing or a multi-segment
retransmission read will return the wrong segment. **This does not affect existing goldens**
(they never read the buffer), but it is a correctness gate for the B9 test.

---

## Test plan (P3-RTL / task 16)

1. **Regression**: full Stage B/C/D suite byte-identical (goldens untouched — L1 is a
   1-deep ring in the legacy path; retrans URAM is write-into-void on the happy loopback,
   so `CNT_RETRANS==0` still holds).
2. **`d_multiwr`** (new): enqueue K WRs via the SQ ring (mix 64B/8K/12K), assert
   `sq_compl` reaches K, per-WR placement bit-exact, `outstanding` never exceeds BUDGET,
   `m_rdma_ack` drained (no dropped CQE), tx/rx frame accounting = Σ segments+ACKs.
3. **`d_retrans_b9`** (new): single WR, **drop the responder ACK** on the TB DAC path; the
   transport timer fires (~156k cyc ≈ 626 µs at 250 MHz — matches the recon prediction),
   the WR retransmits reading the URAM, CQE=1, `CNT_RETRANS>=1`. **First observation of B9.**
4. **`d_retrans_b9_multi`** (new — closes review blockers): TWO WRs pushed via the SQ ring so
   their retrans-write mirrors pipeline into the URAM command FIFO, then **drop WR1's ACK** so
   the timer retransmits WR1 by reading its slot. Exercises the write-race fix + the read path.
5. **Retransmitted-frame DATA check** (`check_b9_retrans.py` — closes review blocker #2):
   `check_placement()` alone cannot see URAM read corruption (the responder places correct
   data on the first attempt and DROPS the duplicate-PSN retransmission, so destination memory
   stays stale-correct). Instead the post-process asserts the **retransmitted WRITE frame on
   the wire** is byte-for-byte identical to its original — the only way it can differ is if
   `rdma_retrans_uram` replayed wrong bytes. Applied to both b9 tests.
6. Adversarial pre-synthesis review (done): 4 lenses + 2 skeptics. Found **two blockers** in
   Feature B — the write-slot race (fixed by the command FIFO above) and the insufficient
   `check_placement()` data coverage (fixed by items 4–5). SQ ring (Feature A) clean.

## Build / board (P3-SYN / task 17)
- Synth build#2 (ID 0x0C1A0003): expect the URAM count to rise from 8 → ~16 (staging 8 +
  retrans 8) and a small LUT/FF bump for the SQ ring + FSMs; 250 MHz must still close.
- **build#2 RESULT (2026-07-17 night): functionally complete but WNS −0.209 ns / 935
  failing endpoints — all on the reset tree** (single sync FF → LUT2 fanout 9454 R pins
  across SLRs, 97 % routing). Fix: `rstn_core` two-stage pipeline + `max_fanout=256`
  (quasi-static, 2-cycle-late deassert harmless).
- **build#3 RESULT (2026-07-18 09:11): ✅ TIMING CLOSED — WNS +0.169 ns, TNS = 0,
  0 failing endpoints (408,952), hold +0.010, pulse +0.455.** The reset fix recovered
  −0.209 → +0.169, better margin than Stage D's +0.029. Util: LUT 89,986 = 7.61 %,
  FF 146,515 = 6.20 %. `fpga_stage_d.bit` produced (syn/out/), ID 0x0C1A0003 —
  **the board-session flash candidate.** Preceded by GATE2 all-green (10/10 sims incl
  both b9 retrans DATA checks, per-flow goldens).
- Board: L1 multi-WR submit over JTAG; and — the payoff — a real frame-loss scenario that
  previously wedged now recovers via retransmission (drive with a deliberate single-frame
  drop if a mechanism exists, else document that loopback cannot inject loss and B9 stays
  sim-only on the bench).

## Risks / watch items
- **PSN-window-edge double-CQE** (A.1): low probability in single-QP loopback; add a bounded
  `outstanding` underflow guard and log if `sq_compl` overtakes `sq_prod`.
- **Coalescing peer** (A.1): out of scope for loopback; CX-5 interop checklist item.
- **URAM arbitration under simultaneous read+write**: stack serializes reads, but assert it
  in sim rather than assume it.
- **B9 sim wall-clock**: ~200k cycles ≈ 0.8 ms sim time — longer than current TBs (watchdog
  must be raised; the existing `#4ms` in tb_stage_d is already enough).
