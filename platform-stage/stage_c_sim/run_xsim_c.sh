#!/usr/bin/env bash
# Stage C RTL sim: compile + elaborate + run under xsim (Vivado 2025.2).
# Usage: ./run_xsim_c.sh [c_write64|c_write8k|c_write12k|c_magic]
set -o pipefail
TEST="${1:-c_write64}"
cd "$(dirname "$0")"
source ~/xlnx_env.sh
export LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LIBRARY_PATH:-}
mkdir -p out

echo "== xvlog: packages + interfaces =="
xvlog --sv -d VITIS_HLS -i rtl/pkg \
    rtl/pkg/lynx_pkg.sv rtl/pkg/axi_intf.sv rtl/pkg/lynx_intf.sv \
    > out/xvlog_pkg.log 2>&1 || { tail -20 out/xvlog_pkg.log; exit 1; }

echo "== xvlog: HLS verilog =="
xvlog rtl/hls/*.v > out/xvlog_hls.log 2>&1 || { grep -iE "error" out/xvlog_hls.log | head; exit 1; }

echo "== xvlog: coyote wrapper + stubs + L0 + tb =="
xvlog --sv -d VITIS_HLS -i rtl/pkg \
    rtl/coyote/*.sv rtl/stubs/*.sv rtl/l0/*.sv tb/tb_stage_c.sv \
    > out/xvlog_c.log 2>&1 || { grep -iE "error" out/xvlog_c.log | head -20; exit 1; }

echo "== xelab =="
xelab -debug typical -timescale 1ns/1ps tb_stage_c -s tb_stage_c_sim \
    > out/xelab_c.log 2>&1 || { grep -iE "error" out/xelab_c.log | head -30; exit 1; }

echo "== xsim (+TEST=$TEST) =="
xsim tb_stage_c_sim -testplusarg "TEST=$TEST" -runall \
    > "out/xsim_$TEST.log" 2>&1
grep -E "CHECK|RESULT|ERROR|WARN|RBUF_RD" "out/xsim_$TEST.log" | tail -40
