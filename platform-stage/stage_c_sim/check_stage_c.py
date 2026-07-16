#!/usr/bin/env python3
"""Stage C offline frame checker.

Golden rule (guide Stage C pass bar): same signature inputs => the doorbell-
driven datapath must emit frames byte-identical to the Stage B goldens.

  c_write64 : data frame F0 == Stage B rtl_tx_write64 F0 (124B incl ICRC);
              ACK frame  == Stage B rtl_tx_rx_loop F1.
  c_write8k : the two data frames == Stage B rtl_tx_write8k F0/F1.
  c_write12k: no Stage B golden (MIDDLE is new coverage) -> structural check:
              opcodes 0x06/0x07/0x08, consecutive PSN, RETH only in FIRST
              (VA + DMALen=4096 per command), payload bytes == offset%256,
              ICRC valid on every frame.

Frames on m_axis_tx start at the IPv4 header (no Ethernet framing yet).
ACK frame = 48B (IP20+UDP8+BTH12+AETH4+ICRC4); anything >= 100B is data.

Usage: check_stage_c.py <test> <stage_c_out_dir> <stage_b_out_dir>
"""
import re
import sys
import zlib

TEST, C_DIR, B_DIR = sys.argv[1], sys.argv[2], sys.argv[3]
PSN0 = 0x80CE4E
RADDR = 0x334455667788


def parse_frames(path):
    frames = {}
    for line in open(path):
        m = re.match(r"F(\d+) B(\d+) DATA=([0-9a-fA-F]+) KEEP=([0-9a-fA-F]+) LAST=(\d)", line)
        if m:
            raw = bytes.fromhex(m[3])[::-1]
            keep = int(m[4], 16)
            frames.setdefault(int(m[1]), []).append(
                bytes(raw[i] for i in range(64) if keep >> i & 1))
    return [b"".join(frames[k]) for k in sorted(frames)]


def icrc_ref(p):
    p = bytearray(p)
    p[1] = 0xFF
    p[8] = 0xFF
    p[10] = p[11] = 0xFF
    p[26] = p[27] = 0xFF
    p[32] = 0xFF
    return (zlib.crc32(b"\xff" * 8 + bytes(p)) & 0xFFFFFFFF).to_bytes(4, "little")


fails = 0


def check(name, ok, detail=""):
    global fails
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  {detail}" if detail else ""))
    if not ok:
        fails += 1


cf = parse_frames(f"{C_DIR}/rtl_tx_{TEST}.txt")
data = [f for f in cf if len(f) >= 100]
acks = [f for f in cf if len(f) < 100]
print(f"{TEST}: {len(cf)} frames captured ({len(data)} data, {len(acks)} ack)")

for i, f in enumerate(cf):
    check(f"icrc frame{i} ({len(f)}B)", f[-4:] == icrc_ref(f[:-4]),
          f"{f[-4:].hex()} vs {icrc_ref(f[:-4]).hex()}")

if TEST == "c_write64":
    gb = parse_frames(f"{B_DIR}/rtl_tx_write64.txt")
    check("data==StageB write64 F0", len(data) == 1 and data[0] == gb[0],
          f"{len(data[0])}B vs {len(gb[0])}B" if data else "no data frame")
    ga = parse_frames(f"{B_DIR}/rtl_tx_rx_loop.txt")
    check("ack==StageB rx_loop F1", len(acks) == 1 and acks[0] == ga[1],
          f"{len(acks[0])}B vs {len(ga[1])}B" if acks else "no ack frame")
elif TEST == "c_write8k":
    gb = parse_frames(f"{B_DIR}/rtl_tx_write8k.txt")
    check("2 data frames", len(data) == 2)
    for i in range(min(2, len(data))):
        check(f"data{i}==StageB write8k F{i}", data[i] == gb[i],
              f"{len(data[i])}B vs {len(gb[i])}B")
    check(">=1 ack", len(acks) >= 1)
elif TEST == "c_write12k":
    check("3 data frames", len(data) == 3)
    exp_ops = [0x06, 0x07, 0x08]           # FIRST / MIDDLE / LAST
    off = 0
    for i, f in enumerate(data[:3]):
        op, psn = f[28], int.from_bytes(f[37:40], "big")
        check(f"F{i} opcode", op == exp_ops[i], f"{op:#04x} want {exp_ops[i]:#04x}")
        check(f"F{i} psn", psn == ((PSN0 + i) & 0xFFFFFF), f"{psn:#08x}")
        if i == 0:
            va = int.from_bytes(f[40:48], "big")
            dmalen = int.from_bytes(f[52:56], "big")
            check("F0 RETH VA", va == RADDR, f"{va:#x}")
            check("F0 RETH DMALen per-command (B4)", dmalen == 4096, f"{dmalen}")
            pay = f[56:-4]
        else:
            pay = f[40:-4]
        check(f"F{i} payload {len(pay)}B", len(pay) == 4096 and
              pay == bytes((off + j) % 256 for j in range(4096)))
        off += 4096
    check(">=1 ack", len(acks) >= 1)

print(f"{'ALL PASS' if fails == 0 else f'{fails} FAILURES'}")
sys.exit(1 if fails else 0)
