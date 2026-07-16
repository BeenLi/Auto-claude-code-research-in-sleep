// ============================================================================
// Stage C testbench: roce_l0_top (doorbell L0 + URAM staging + roce_stack).
// The TB plays exactly the role of `run_hw_axi` over jtag_axi on the board:
// every stimulus and every observation goes through AXI-Lite. TX is wired
// straight back into RX (single-stack self-talk — the QSFP0=DAC=QSFP1
// rehearsal); the only non-AXI-Lite TB fixtures are the retransmission-buffer
// behavioral model (external port at this stage) and a TX tap that records
// frames for offline golden comparison vs Stage B.
//
// Tests (+TEST=<name>, default c_write64):
//   c_write64  : full loop — QP cfg, 64B payload preload, WQE, doorbell,
//                poll CQE, read back placement bytes, check counters.
//                Signatures identical to Stage B => frames must be identical.
//   c_write8k  : 8 KiB WR -> doorbell pre-splits FIRST/LAST (golden vs B).
//   c_write12k : 12 KiB WR -> FIRST/MIDDLE/LAST (MIDDLE = new coverage).
//   c_magic    : qp vaddr = 0xDEADBEEF -> sticky STATUS warn bit + W1C.
//
// Signature set (Stage A/B lineage): QPN=0x11(pid 17) PSN0=0x80ce4e
// RKEY=0x1234abcd RADDR48=0x334455667788 UDP=0xc000 src IP 0x0b01d4d1.
// Placement lands at RADDR48 mod 256KiB = 0x27788 (unaligned: 0x27788 mod 64
// = 8, so each 64B beat splits 56/8 across two staging words).
// ============================================================================
`timescale 1ns/1ps

import lynxTypes::*;

module tb_stage_c;

    logic clk = 0;
    logic rstn = 0;
    always #2ns clk = ~clk;           // 250 MHz

    // ------------------------------------------------------------------ ifs
    AXI4L #(.AXI4L_ADDR_BITS(24), .AXI4L_DATA_BITS(32)) axil (.aclk(clk), .aresetn(rstn));
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_rx (.aclk(clk), .aresetn(rstn));
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_tx (.aclk(clk), .aresetn(rstn));

    metaIntf #(.STYPE(logic[95:0])) mem_rd_cmd (.aclk(clk), .aresetn(rstn));
    metaIntf #(.STYPE(logic[95:0])) mem_wr_cmd (.aclk(clk), .aresetn(rstn));
    metaIntf #(.STYPE(logic[31:0])) mem_rd_sts (.aclk(clk), .aresetn(rstn));
    metaIntf #(.STYPE(logic[31:0])) mem_wr_sts (.aclk(clk), .aresetn(rstn));
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_mem_rd (.aclk(clk), .aresetn(rstn));
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_mem_wr (.aclk(clk), .aresetn(rstn));

    roce_l0_top #(.STG_ADDR_BITS(18)) dut (
        .nclk(clk), .nresetn(rstn),
        .s_axil(axil),
        .s_axis_rx(axis_rx), .m_axis_tx(axis_tx),
        .local_ip_address(32'hd1d4010b),
        .m_rdma_mem_rd_cmd(mem_rd_cmd), .m_rdma_mem_wr_cmd(mem_wr_cmd),
        .s_rdma_mem_rd_sts(mem_rd_sts), .s_rdma_mem_wr_sts(mem_wr_sts),
        .s_axis_rdma_mem_rd(axis_mem_rd), .m_axis_rdma_mem_wr(axis_mem_wr)
    );

    // ------------------------------------------------------- register map
    localparam logic [23:0] A_ID        = 24'h000000;
    localparam logic [23:0] A_STATUS    = 24'h000004;
    localparam logic [23:0] A_QP_STATE  = 24'h000010;
    localparam logic [23:0] A_QP_QPN    = 24'h000014;
    localparam logic [23:0] A_QP_RPSN   = 24'h000018;
    localparam logic [23:0] A_QP_LPSN   = 24'h00001C;
    localparam logic [23:0] A_QP_RKEY   = 24'h000020;
    localparam logic [23:0] A_QP_VA_LO  = 24'h000024;
    localparam logic [23:0] A_QP_VA_HI  = 24'h000028;
    localparam logic [23:0] A_QP_SUBMIT = 24'h00002C;
    localparam logic [23:0] A_CN_QPN    = 24'h000030;
    localparam logic [23:0] A_CN_RQPN   = 24'h000034;
    localparam logic [23:0] A_CN_RIP0   = 24'h000038;
    localparam logic [23:0] A_CN_RIP1   = 24'h00003C;
    localparam logic [23:0] A_CN_RIP2   = 24'h000040;
    localparam logic [23:0] A_CN_RIP3   = 24'h000044;
    localparam logic [23:0] A_CN_UDPP   = 24'h000048;
    localparam logic [23:0] A_CN_SUBMIT = 24'h00004C;
    localparam logic [23:0] A_WQ_OP     = 24'h000050;
    localparam logic [23:0] A_WQ_QPN    = 24'h000054;
    localparam logic [23:0] A_WQ_LA_LO  = 24'h000058;
    localparam logic [23:0] A_WQ_LA_HI  = 24'h00005C;
    localparam logic [23:0] A_WQ_RA_LO  = 24'h000060;
    localparam logic [23:0] A_WQ_RA_HI  = 24'h000064;
    localparam logic [23:0] A_WQ_LEN    = 24'h000068;
    localparam logic [23:0] A_WQ_CTRL   = 24'h00006C;
    localparam logic [23:0] A_DOORBELL  = 24'h000070;
    localparam logic [23:0] A_C_IBV_TX  = 24'h000080;
    localparam logic [23:0] A_C_IBV_RX  = 24'h000084;
    localparam logic [23:0] A_C_CRC     = 24'h000088;
    localparam logic [23:0] A_C_PSN     = 24'h00008C;
    localparam logic [23:0] A_C_RET     = 24'h000090;
    localparam logic [23:0] A_C_SQ      = 24'h000094;
    localparam logic [23:0] A_C_CQE     = 24'h000098;
    localparam logic [23:0] A_LAST_ACK  = 24'h00009C;
    localparam logic [23:0] A_C_WRREQ   = 24'h0000A0;
    localparam logic [23:0] A_C_RDREQ   = 24'h0000A4;
    localparam logic [23:0] A_C_TXFRM   = 24'h0000A8;
    localparam logic [23:0] A_C_RXFRM   = 24'h0000AC;
    localparam logic [23:0] STG_BASE    = 24'h800000;

    // ------------------------------------------------------- signature set
    localparam logic [23:0]  QPN     = 24'h000011;    // pid=17, vfid=0
    localparam logic [23:0]  PSN0    = 24'h80ce4e;
    localparam logic [31:0]  RKEY    = 32'h1234abcd;
    localparam logic [47:0]  RADDR48 = 48'h334455667788;
    localparam logic [127:0] REM_IP  = 128'hd2d4010b_ff530f02_00000000_000080fe;
    localparam logic [15:0]  UDPP    = 16'hc000;
    localparam logic [17:0]  DST_OFF = RADDR48[17:0]; // 0x27788 in the window

    string testname = "c_write64";
    int    test_len = 64;
    int    n_seg    = 1;
    int    errors   = 0;

    // ------------------------------------------------- TX -> RX loopback
    assign axis_rx.tvalid = axis_tx.tvalid;
    assign axis_rx.tdata  = axis_tx.tdata;
    assign axis_rx.tkeep  = axis_tx.tkeep;
    assign axis_rx.tlast  = axis_tx.tlast;
    assign axis_tx.tready = axis_rx.tready;

    // ------------------------------------------------------------ TX tap
    int tx_fd;
    int tx_frame_cnt = 0;
    int tx_beat_cnt  = 0;
    always_ff @(posedge clk) begin
        if (rstn && axis_tx.tvalid && axis_tx.tready) begin
            $fdisplay(tx_fd, "F%0d B%0d DATA=%0128h KEEP=%016h LAST=%0d",
                      tx_frame_cnt, tx_beat_cnt, axis_tx.tdata, axis_tx.tkeep, axis_tx.tlast);
            tx_beat_cnt <= tx_beat_cnt + 1;
            if (axis_tx.tlast) begin
                tx_frame_cnt <= tx_frame_cnt + 1;
                tx_beat_cnt  <= 0;
            end
        end
    end

    // -------------------------------------------- placement log (forensics)
    int pl_fd;
    always_ff @(posedge clk) begin
        if (rstn && dut.wr_req_if.valid && dut.wr_req_if.ready)
            $fdisplay(pl_fd, "WR_REQ vaddr=%0h len=%0d last=%0b",
                      dut.wr_req_if.data.vaddr, dut.wr_req_if.data.len,
                      dut.wr_req_if.data.last);
        if (rstn && dut.axis_wr.tvalid && dut.axis_wr.tready)
            $fdisplay(pl_fd, "WR_DATA DATA=%0128h KEEP=%016h LAST=%0d",
                      dut.axis_wr.tdata, dut.axis_wr.tkeep, dut.axis_wr.tlast);
    end

    // ------------------------------------------------- retrans buffer model
    localparam int MEM_BYTES = 1<<20;
    byte unsigned rbuf[MEM_BYTES];
    typedef struct { longint unsigned addr; int unsigned len; } memcmd_s;
    memcmd_s wrq[$], rrq[$];
    assign mem_wr_cmd.ready = 1'b1;
    assign mem_rd_cmd.ready = 1'b1;
    assign axis_mem_wr.tready = 1'b1;
    // one process: cmd push textually before the data store, so a same-edge
    // cmd + first beat is ordered; wr_off tracks the beat offset within a
    // multi-beat store (review finding C-R2 — was missing in Stage B/C TBs)
    int wr_off = 0;
    always_ff @(posedge clk) begin
        if (rstn && mem_wr_cmd.valid)
            wrq.push_back('{longint'(mem_wr_cmd.data[63:0]), int'(mem_wr_cmd.data[95:64])});
        if (rstn && mem_rd_cmd.valid) begin
            rrq.push_back('{longint'(mem_rd_cmd.data[63:0]), int'(mem_rd_cmd.data[95:64])});
            $display("[%0t] RBUF_RD_CMD: addr=%0h len=%0d", $time,
                     mem_rd_cmd.data[63:0], mem_rd_cmd.data[95:64]);
        end
        if (rstn && axis_mem_wr.tvalid && wrq.size() > 0) begin
            for (int i = 0; i < 64; i++)
                if (axis_mem_wr.tkeep[i])
                    rbuf[((wrq[0].addr & (MEM_BYTES-1)) + wr_off*64 + i) & (MEM_BYTES-1)]
                        <= axis_mem_wr.tdata[i*8 +: 8];
            if (axis_mem_wr.tlast) begin
                void'(wrq.pop_front());
                wr_off <= 0;
            end else
                wr_off <= wr_off + 1;
        end
    end
    task automatic serve_rbuf_rd();
        memcmd_s r;
        int nbeats, off;
        r = rrq.pop_front();
        nbeats = (r.len + 63) / 64;
        for (int b = 0; b < nbeats; b++) begin
            axis_mem_rd.tvalid <= 1;
            for (int i = 0; i < 64; i++) begin
                off = b*64 + i;
                axis_mem_rd.tdata[i*8 +: 8] <= (off < r.len) ? rbuf[((r.addr & (MEM_BYTES-1)) + off) & (MEM_BYTES-1)] : 8'h00;
                axis_mem_rd.tkeep[i]        <= (off < r.len);
            end
            axis_mem_rd.tlast <= (b == nbeats-1);
            do @(posedge clk); while (!(axis_mem_rd.tvalid && axis_mem_rd.tready));
            axis_mem_rd.tvalid <= 0;
        end
        axis_mem_rd.tlast <= 0;
    endtask
    initial begin : rbuf_server
        axis_mem_rd.tvalid = 0; axis_mem_rd.tdata = '0;
        axis_mem_rd.tkeep = '0; axis_mem_rd.tlast = 0;
        forever begin
            @(posedge clk);
            if (rrq.size() > 0) serve_rbuf_rd();
        end
    end
    assign mem_rd_sts.valid = 1'b0;
    assign mem_wr_sts.valid = 1'b0;
    assign mem_rd_sts.data  = '0;
    assign mem_wr_sts.data  = '0;

    // ------------------------------------------------- AXI-Lite master tasks
    task automatic axil_wr(input logic [23:0] addr, input logic [31:0] data);
        logic aw_done, w_done;
        aw_done = 0; w_done = 0;
        axil.awaddr <= addr; axil.awvalid <= 1;
        axil.wdata  <= data; axil.wstrb <= 4'hF; axil.wvalid <= 1;
        while (!(aw_done && w_done)) begin
            @(posedge clk);
            if (axil.awvalid && axil.awready) begin axil.awvalid <= 0; aw_done = 1; end
            if (axil.wvalid  && axil.wready)  begin axil.wvalid  <= 0; w_done  = 1; end
        end
        axil.bready <= 1;
        do @(posedge clk); while (!axil.bvalid);
        axil.bready <= 0;
    endtask

    task automatic axil_rd(input logic [23:0] addr, output logic [31:0] data);
        axil.araddr <= addr; axil.arvalid <= 1;
        do @(posedge clk); while (!(axil.arvalid && axil.arready));
        axil.arvalid <= 0;
        axil.rready <= 1;
        do @(posedge clk); while (!axil.rvalid);
        data = axil.rdata;
        axil.rready <= 0;
        @(posedge clk);
    endtask

    // expected payload byte (Stage B convention: 0xA0+i for 64B, i%256 else)
    function automatic byte unsigned exp_byte(int i);
        return (test_len == 64) ? byte'(8'hA0 + i) : byte'(i % 256);
    endfunction

    task automatic preload_payload();
        logic [31:0] w;
        for (int i = 0; i < test_len; i += 4) begin
            w = {exp_byte(i+3), exp_byte(i+2), exp_byte(i+1), exp_byte(i)};
            axil_wr(STG_BASE + 24'(i), w);
        end
        $display("[%0t] payload preloaded (%0d bytes over AXI-Lite)", $time, test_len);
    endtask

    task automatic check_placement();
        logic [31:0] w;
        int bad;
        bad = 0;
        for (int i = 0; i < test_len; i += 4) begin
            axil_rd(STG_BASE + 24'(DST_OFF) + 24'(i), w);
            for (int b = 0; b < 4; b++)
                if (w[b*8 +: 8] !== exp_byte(i+b)) begin
                    if (bad < 8)
                        $display("  PLACEMENT MISMATCH @+%0d: got %02h want %02h",
                                 i+b, w[b*8 +: 8], exp_byte(i+b));
                    bad++;
                end
        end
        if (bad == 0)
            $display("[%0t] CHECK placement: %0d bytes at 0x%0h bit-exact PASS",
                     $time, test_len, DST_OFF);
        else begin
            $display("[%0t] CHECK placement: %0d/%0d bytes WRONG FAIL", $time, bad, test_len);
            errors++;
        end
    endtask

    task automatic check_eq(string what, logic [31:0] got, logic [31:0] want);
        if (got !== want) begin
            $display("[%0t] CHECK %s: got 0x%0h want 0x%0h FAIL", $time, what, got, want);
            errors++;
        end else
            $display("[%0t] CHECK %s: 0x%0h PASS", $time, what, got);
    endtask

    // ------------------------------------------------------------ sequences
    task automatic cfg_qp_conn();
        axil_wr(A_QP_STATE, 32'd3);            // READY_SEND
        axil_wr(A_QP_QPN,  {8'b0, QPN});
        axil_wr(A_QP_RPSN, {8'b0, PSN0});
        axil_wr(A_QP_LPSN, {8'b0, PSN0});
        axil_wr(A_QP_RKEY, RKEY);
        axil_wr(A_QP_VA_LO, 32'h0);
        axil_wr(A_QP_VA_HI, 32'h0);
        axil_wr(A_QP_SUBMIT, 32'h1);
        axil_wr(A_CN_QPN,  {16'b0, QPN[15:0]});
        axil_wr(A_CN_RQPN, {8'b0, QPN});
        axil_wr(A_CN_RIP0, REM_IP[31:0]);
        axil_wr(A_CN_RIP1, REM_IP[63:32]);
        axil_wr(A_CN_RIP2, REM_IP[95:64]);
        axil_wr(A_CN_RIP3, REM_IP[127:96]);
        axil_wr(A_CN_UDPP, {16'b0, UDPP});
        axil_wr(A_CN_SUBMIT, 32'h1);
        $display("[%0t] QP + conn programmed over AXI-Lite", $time);
    endtask

    task automatic submit_wqe();
        axil_wr(A_WQ_OP,    32'h0A);           // WRITE (splitter may override)
        axil_wr(A_WQ_QPN,   32'd17);           // pid=17, vfid=0
        axil_wr(A_WQ_LA_LO, 32'h0);
        axil_wr(A_WQ_LA_HI, 32'h0);
        axil_wr(A_WQ_RA_LO, RADDR48[31:0]);
        axil_wr(A_WQ_RA_HI, {16'b0, RADDR48[47:32]});
        axil_wr(A_WQ_LEN,   32'(test_len));
        axil_wr(A_WQ_CTRL,  32'h1);            // last=1
        axil_wr(A_DOORBELL, 32'h1);
        $display("[%0t] WQE submitted + doorbell struck (len=%0d)", $time, test_len);
    endtask

    task automatic poll_cqe(input int want);
        logic [31:0] v;
        int polls;
        polls = 0;
        forever begin
            axil_rd(A_C_CQE, v);
            polls++;
            if (int'(v) >= want) break;
            if (polls > 5000) begin
                $display("[%0t] CHECK cqe: TIMEOUT after %0d polls (cqe=%0d) FAIL", $time, polls, v);
                errors++;
                return;
            end
        end
        $display("[%0t] CHECK cqe: reached %0d after %0d AXI-Lite polls PASS", $time, v, polls);
    endtask

    task automatic dump_counters();
        logic [31:0] v;
        axil_rd(A_C_IBV_TX, v); $display("  CNT ibv_tx  = %0d", v);
        axil_rd(A_C_IBV_RX, v); $display("  CNT ibv_rx  = %0d", v);
        axil_rd(A_C_CRC, v);    $display("  CNT crc_drop= %0d", v);
        axil_rd(A_C_PSN, v);    $display("  CNT psn_drop= %0d", v);
        axil_rd(A_C_RET, v);    $display("  CNT retrans = %0d", v);
        axil_rd(A_C_SQ, v);     $display("  CNT sq      = %0d", v);
        axil_rd(A_C_CQE, v);    $display("  CNT cqe     = %0d", v);
        axil_rd(A_C_WRREQ, v);  $display("  CNT wr_req  = %0d", v);
        axil_rd(A_C_RDREQ, v);  $display("  CNT rd_req  = %0d", v);
        axil_rd(A_C_TXFRM, v);  $display("  CNT tx_frm  = %0d", v);
        axil_rd(A_C_RXFRM, v);  $display("  CNT rx_frm  = %0d", v);
    endtask

    // ------------------------------------------------------------ main
    logic [31:0] rv, rv2;
    ack_t ack_v;
    initial begin
        void'($value$plusargs("TEST=%s", testname));
        if (testname == "c_write8k")  begin test_len = 8192;  n_seg = 2; end
        if (testname == "c_write12k") begin test_len = 12288; n_seg = 3; end

        tx_fd = $fopen($sformatf("out/rtl_tx_%s.txt", testname), "w");
        pl_fd = $fopen($sformatf("out/rtl_placement_%s.txt", testname), "w");

        axil.tie_off_m();

        repeat (20) @(posedge clk);
        rstn = 1;
        repeat (50) @(posedge clk);

        axil_rd(A_ID, rv);
        check_eq("id", rv, 32'h0C1A_0001);

        if (testname == "c_magic") begin
            // magic vaddr -> sticky warn; W1C; clean vaddr -> no warn
            axil_wr(A_QP_QPN, 32'h22);
            axil_wr(A_QP_VA_LO, 32'hDEADBEEF);
            axil_wr(A_QP_VA_HI, 32'h0);
            axil_wr(A_QP_SUBMIT, 32'h1);
            repeat (10) @(posedge clk);
            axil_rd(A_STATUS, rv);
            check_eq("magic warn set", rv[1], 1'b1);
            axil_wr(A_STATUS, 32'h2);          // W1C
            axil_rd(A_STATUS, rv);
            check_eq("magic warn cleared", rv[1], 1'b0);
            axil_wr(A_QP_VA_LO, 32'h0);
            axil_wr(A_QP_SUBMIT, 32'h1);
            repeat (10) @(posedge clk);
            axil_rd(A_STATUS, rv);
            check_eq("clean vaddr no warn", rv[1], 1'b0);
        end else begin
            cfg_qp_conn();
            repeat (50) @(posedge clk);
            preload_payload();
            submit_wqe();

            if (testname == "c_write12k") begin
                // mid-WR mutation probe (review C-R1): rewrite WQE registers
                // while the splitter is busy — the doorbell snapshot must keep
                // segments 2/3 on pid=17 / last=1 (checked via CQE + ack pid)
                axil_wr(A_WQ_QPN,  32'd63);
                axil_wr(A_WQ_CTRL, 32'h0);
                $display("[%0t] WQE regs mutated mid-WR (pid=63, last=0)", $time);
            end

            poll_cqe(1);
            repeat (500) @(posedge clk);       // let trailing ACK frames settle

            check_placement();
            axil_rd(A_C_SQ, rv);    check_eq("sq segments", rv, 32'(n_seg));
            axil_rd(A_C_WRREQ, rv); check_eq("placement cmds", rv, 32'(n_seg));
            axil_rd(A_C_CQE, rv);   check_eq("cqe count", rv, 32'h1);
            axil_rd(A_LAST_ACK, rv);
            ack_v = ack_t'(rv);
            check_eq("ack opcode", 32'(ack_v.opcode), 32'h11);
            check_eq("ack pid",    32'(ack_v.pid),    32'd17);
            axil_rd(A_C_TXFRM, rv);
            if (testname == "c_write64") check_eq("tx frames", rv, 32'd2);
            else if (int'(rv) < n_seg + 1) begin
                $display("CHECK tx frames: %0d < %0d FAIL", rv, n_seg + 1);
                errors++;
            end
            axil_rd(A_C_TXFRM, rv);
            axil_rd(A_C_RXFRM, rv2);           // loopback: rx == tx
            check_eq("rx==tx frames", rv2, rv);
            dump_counters();
        end

        $display("RESULT %s: %s (%0d errors, %0d tx frames)",
                 testname, (errors == 0) ? "PASS" : "FAIL", errors, tx_frame_cnt);
        $fclose(tx_fd); $fclose(pl_fd);
        $finish;
    end

    // watchdog
    initial begin
        #2ms;
        $display("WATCHDOG timeout");
        $display("RESULT %s: FAIL (watchdog)", testname);
        $fclose(tx_fd); $fclose(pl_fd);
        $finish;
    end

    // waveform dump (+VCD)
    initial begin
        if ($test$plusargs("VCD")) begin
            $dumpfile("out/dbg_c.vcd");
            $dumpvars(4, dut);
            #3us $dumpoff;
        end
    end

    // debug probe
    initial begin
        forever begin
            #10us;
            $display("[dbg %0t] db_state=%0d sq(v%b r%b) tx(v%b) pu=%0d pl(act%b n%0d) cqe=%0d frames=%0d",
                     $time, dut.inst_doorbell.db_state,
                     dut.sq_if.valid, dut.sq_if.ready, axis_tx.tvalid,
                     dut.inst_staging.pu_state, dut.inst_staging.pl_active,
                     dut.inst_staging.plq_n, dut.inst_doorbell.c_cqe, tx_frame_cnt);
        end
    end

endmodule
