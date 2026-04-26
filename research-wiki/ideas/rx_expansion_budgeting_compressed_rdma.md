---
type: idea
node_id: idea:rx_expansion_budgeting_compressed_rdma
title: "Rx Expansion Budgeting for Compressed RDMA"
stage: selected
outcome: active
added: 2026-04-26T10:26:45+08:00
---

# Rx Expansion Budgeting for Compressed RDMA

## Thesis

Compressed RDMA should be admitted and scheduled by decompressed output-byte pressure, not only compressed wire bytes.

## Problem

NIC-side compression reduces network bytes, but the receiver must materialize the original bytes into host/GPU memory. Variable LLM tensor compressibility can make Rx decompression engines, PCIe, host-memory writes, or Rx SRAM buffers the true bottleneck.

## Mechanism

Expansion-Aware RDMA Rx Budgeter (EARB):

- per-flow expansion-ratio estimator
- decompressed-output-byte credit allocator
- Rx decompression-engine scheduler
- feedback hook into RDMA congestion/credit control

## Validation

Start with analytical break-even modeling, then htsim or standalone flow simulation, then gem5/htsim window-level co-simulation.

## Connections

- addresses_gap: G1, G2, G8
- inspired_by: NetZIP, RoCE BALBOA, Ecco, ZipServ, DECA, Quad Length Codes, Toasty
