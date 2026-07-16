#!/usr/bin/env python3
"""Stage B checks B-4 + B-5.

B-4: RTL frame[0] vs csim golden — byte-exact over the csim-valid bytes (120),
     RTL must carry exactly 4 extra keep-valid bytes (materialized ICRC).
B-5: independent Python ICRC reference (RoCE v2, IBTA A17.9.5 style) vs the
     RTL ICRC bytes. Masked fields: IPv4 {DSCP/ECN, TTL, header-checksum},
     UDP {checksum}, BTH {resv8a}; 64 bits of 1s prepended (dummy LRH).
     CRC32 poly 0x04C11DB7 reflected (== zlib.crc32), final XOR 0xFFFFFFFF,
     transmitted little-endian (LSB first) per InfiniBand invariant-CRC rule.
"""
import re
import sys
import zlib

RTL_TX = sys.argv[1] if len(sys.argv) > 1 else "out/rtl_tx_write64.txt"
CSIM_TX = sys.argv[2] if len(sys.argv) > 2 else "/home/wanli.99/fpga-network-stack-csim/tx_frame.txt"


def parse_rtl(path):
    """Return list of frames; each frame = (bytes, keep_count_list)."""
    frames = {}
    for line in open(path):
        m = re.match(r"F(\d+) B(\d+) DATA=([0-9a-fA-F]+) KEEP=([0-9a-fA-F]+) LAST=(\d)", line)
        if not m:
            continue
        f, b, data, keep, last = int(m[1]), int(m[2]), m[3], int(m[4], 16), int(m[5])
        raw = bytes.fromhex(data)[::-1]          # %h prints MSB-first; wire = LSB byte first
        valid = bytes(raw[i] for i in range(64) if keep >> i & 1)
        frames.setdefault(f, []).append(valid)
    return ["".encode().join(bs) if False else b"".join(bs) for _, bs in sorted(frames.items())]


def parse_csim(path):
    frames, cur = [], []
    keep = 0
    for line in open(path):
        m = re.match(r"\[TXWORD \d+\] keep=0x([0-9a-fA-F]+) last=(\d)", line)
        if m:
            keep, last = int(m[1], 16), int(m[2])
            continue
        b = re.findall(r"\b([0-9a-f]{2})\b", line)
        if b:
            raw = bytes(int(x, 16) for x in b)
            cur.append(bytes(raw[i] for i in range(len(raw)) if keep >> i & 1))
            if last:
                frames.append(b"".join(cur))
                cur = []
                last = 0
    return frames


def icrc_ref(frame_no_icrc: bytes) -> bytes:
    p = bytearray(frame_no_icrc)
    assert p[0] >> 4 == 4, "IPv4 expected"
    p[1] = 0xFF                # DSCP/ECN
    p[8] = 0xFF                # TTL
    p[10] = p[11] = 0xFF       # IP header checksum
    p[26] = p[27] = 0xFF       # UDP checksum
    p[20 + 8 + 4] = 0xFF       # BTH resv8a (BTH byte 4: opcode,flags,pkey[2],resv8a)
    pseudo = b"\xff" * 8 + bytes(p)
    crc = zlib.crc32(pseudo) & 0xFFFFFFFF
    return crc.to_bytes(4, "little")


rtl = parse_rtl(RTL_TX)
csim = parse_csim(CSIM_TX)
print(f"RTL frames: {len(rtl)}  (len={[len(f) for f in rtl]})")
print(f"csim frames: {len(csim)} (len={[len(f) for f in csim[:3]]}...)")

r, c = rtl[0], csim[0]
n = len(c)                                   # csim-valid byte count (120)
ok_b4 = r[:n] == c and len(r) == n + 4
print(f"\n[B-4] byte-exact over first {n} bytes: {r[:n] == c}")
if r[:n] != c:
    for i, (a, b) in enumerate(zip(r[:n], c)):
        if a != b:
            print(f"  first diff @byte{i}: rtl={a:02x} csim={b:02x}")
            break
print(f"[B-4] RTL carries exactly 4 extra bytes: {len(r) == n + 4} (rtl={len(r)}, csim={n})")

got = r[n:n + 4]
want = icrc_ref(r[:n])
print(f"\n[B-5] RTL ICRC bytes : {got.hex()}")
print(f"[B-5] Python ref ICRC: {want.hex()}")
ok_b5 = got == want
if not ok_b5:
    # diagnostic variants
    crc = zlib.crc32(b"\xff" * 8 + bytes(bytearray(r[:n]))) & 0xFFFFFFFF
    print(f"      (no-mask variant: {crc.to_bytes(4,'little').hex()})")
print(f"[B-5] ICRC match: {ok_b5}")

# all retransmitted frames identical?
same = all(f == r for f in rtl)
print(f"\n[extra] all {len(rtl)} RTL frames identical: {same}")
sys.exit(0 if (ok_b4 and ok_b5) else 1)
