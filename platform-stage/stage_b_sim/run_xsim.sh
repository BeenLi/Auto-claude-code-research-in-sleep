#!/usr/bin/env bash
# Stage B RTL sim: compile + elaborate + run under xsim (Vivado 2025.2).
# Usage: ./run_xsim.sh [write64|rx_loop|write8k]
set -o pipefail
TEST="${1:-write64}"
cd "$(dirname "$0")"
source ~/xlnx_env.sh
export LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LIBRARY_PATH:-}
mkdir -p out

echo "== xvlog: packages + interfaces =="
xvlog --sv -d VITIS_HLS -i rtl/pkg \
    rtl/pkg/lynx_pkg.sv rtl/pkg/axi_intf.sv rtl/pkg/lynx_intf.sv \
    > out/xvlog_pkg.log 2>&1 || { tail -20 out/xvlog_pkg.log; exit 1; }

echo "== xvlog: HLS verilog (139 files) =="
xvlog rtl/hls/*.v > out/xvlog_hls.log 2>&1 || { grep -iE "error" out/xvlog_hls.log | head; exit 1; }

echo "== xvlog: coyote wrapper + stubs + tb =="
xvlog --sv -d VITIS_HLS -i rtl/pkg \
    rtl/coyote/*.sv rtl/stubs/*.sv tb/tb_stage_b.sv \
    > out/xvlog_top.log 2>&1 || { grep -iE "error" out/xvlog_top.log | head -20; exit 1; }

echo "== xelab =="
xelab -debug typical tb_stage_b -s tb_stage_b_sim \
    > out/xelab.log 2>&1 || { grep -iE "error" out/xelab.log | head -30; exit 1; }

echo "== xsim (+TEST=$TEST) =="
xsim tb_stage_b_sim -testplusarg "TEST=$TEST" -runall \
    > "out/xsim_$TEST.log" 2>&1
tail -15 "out/xsim_$TEST.log"
