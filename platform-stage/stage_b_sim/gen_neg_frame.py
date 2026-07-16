#!/usr/bin/env python3
"""Build the NEG-3 PSN-skip injection frame for tb_stage_b (+TEST=rx_neg).

Takes the captured golden WRITE frame (124B incl. ICRC), bumps BTH.PSN by +2
(bytes 37..39, big-endian), recomputes the ICRC with the same reference
implementation as check_golden_icrc.py, and prints the two 512b beats in
xsim plusarg form (%h, MSB-first hex).
"""
import re
import sys
import zlib

RTL_TX = sys.argv[1] if len(sys.argv) > 1 else "out/rtl_tx_write64.txt"


def parse_first_frame(path):
    beats = []
    for line in open(path):
        m = re.match(r"F0 B(\d+) DATA=([0-9a-fA-F]+) KEEP=([0-9a-fA-F]+) LAST=(\d)", line)
        if m:
            raw = bytes.fromhex(m[2])[::-1]
            keep = int(m[3], 16)
            beats.append(bytes(raw[i] for i in range(64) if keep >> i & 1))
    return b"".join(beats)


def icrc_ref(p120: bytes) -> bytes:
    p = bytearray(p120)
    p[1] = 0xFF
    p[8] = 0xFF
    p[10] = p[11] = 0xFF
    p[26] = p[27] = 0xFF
    p[32] = 0xFF
    crc = zlib.crc32(b"\xff" * 8 + bytes(p)) & 0xFFFFFFFF
    return crc.to_bytes(4, "little")


frame = bytearray(parse_first_frame(RTL_TX))
assert len(frame) == 124, f"expected 124B frame, got {len(frame)}"
psn = int.from_bytes(frame[37:40], "big")
frame[37:40] = ((psn + 2) & 0xFFFFFF).to_bytes(3, "big")
frame[120:124] = icrc_ref(bytes(frame[:120]))

b0 = frame[0:64]
b1 = frame[64:124] + b"\x00" * 4
print(f"INJ_B0={b0[::-1].hex()}")
print(f"INJ_B1={b1[::-1].hex()}")
print(f"# psn {psn:#x} -> {(psn+2) & 0xFFFFFF:#x}, icrc {frame[120:124].hex()}", file=sys.stderr)
