// ============================================================================
// Stage B testbench: roce_stack (SV wrapper incl. icrc) standalone RTL sim.
// Same signature-value method as Stage A csim TB (my_write_tb.cpp), driven
// through the REAL Coyote-facing interfaces (dreq_t SQ, 184b qp/conn ctx).
//
// Phases (select by +TEST=<name>, default "write64"):
//   write64  : program QP -> one 64B RDMA WRITE -> capture N TX frames
//              (frame[0] = golden vs csim; frames[1..] = retransmissions)
//   rx_loop  : write64 then inject frame[0] back into s_axis_rx ->
//              expect m_rdma_wr_req placement + payload + ACK TX frame
//   write8k  : 8KiB WRITE -> FIRST/MIDDLE/LAST split (PMTU 4096)
//
// Signature values (Stage A lineage, RADDR re-registered to 48b):
//   QPN=0x11 (pid=17,vfid=0) PSN=0x80ce4e RKEY=0x1234abcd
//   RADDR48=0x334455667788 -> wire VA 0x0000334455667788, LEN=64
//   payload byte i = 0xA0+i ; src IP 0x0b01d4d1 ; dst IP 0x0b01d4d2
// ============================================================================
`timescale 1ns/1ps

import lynxTypes::*;

module tb_stage_b;

    // ------------------------------------------------------------------ clk/rst
    logic clk = 0;
    logic rstn = 0;
    always #2ns clk = ~clk;           // 250 MHz

    // ------------------------------------------------------------------ DUT ifs
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_rx (.aclk(clk), .aresetn(rstn));
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_tx (.aclk(clk), .aresetn(rstn));

    metaIntf #(.STYPE(logic[183:0])) qp_if   (.aclk(clk), .aresetn(rstn));
    metaIntf #(.STYPE(logic[183:0])) conn_if (.aclk(clk), .aresetn(rstn));
    metaIntf #(.STYPE(dreq_t))       sq_if   (.aclk(clk), .aresetn(rstn));
    // rdma_flow CQ queue carries plain ack_t (32b, last-gated), NOT dack_t
    metaIntf #(.STYPE(ack_t))        ack_if  (.aclk(clk), .aresetn(rstn));

    metaIntf #(.STYPE(req_t)) rd_req_if (.aclk(clk), .aresetn(rstn));
    metaIntf #(.STYPE(req_t)) wr_req_if (.aclk(clk), .aresetn(rstn));
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_rd_req (.aclk(clk), .aresetn(rstn)); // user data -> stack (WRITE payload)
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_rd_rsp (.aclk(clk), .aresetn(rstn)); // user data -> stack (READ resp)
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_wr     (.aclk(clk), .aresetn(rstn)); // stack -> user (placement)

    metaIntf #(.STYPE(logic[95:0])) mem_rd_cmd (.aclk(clk), .aresetn(rstn));
    metaIntf #(.STYPE(logic[95:0])) mem_wr_cmd (.aclk(clk), .aresetn(rstn));
    metaIntf #(.STYPE(logic[31:0])) mem_rd_sts (.aclk(clk), .aresetn(rstn));
    metaIntf #(.STYPE(logic[31:0])) mem_wr_sts (.aclk(clk), .aresetn(rstn));
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_mem_rd (.aclk(clk), .aresetn(rstn)); // retrans buf -> stack
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_mem_wr (.aclk(clk), .aresetn(rstn)); // stack -> retrans buf

    logic        cnt_rx_v, cnt_tx_v, cnt_crc_v, cnt_psn_v, cnt_ret_v;
    logic [31:0] cnt_rx, cnt_tx, cnt_crc, cnt_psn, cnt_ret;
    logic [31:0] r_cnt_rx, r_cnt_tx, r_cnt_crc, r_cnt_psn, r_cnt_ret;
    always_ff @(posedge clk) begin
        if (cnt_rx_v)  r_cnt_rx  <= cnt_rx;
        if (cnt_tx_v)  r_cnt_tx  <= cnt_tx;
        if (cnt_crc_v) r_cnt_crc <= cnt_crc;
        if (cnt_psn_v) r_cnt_psn <= cnt_psn;
        if (cnt_ret_v) r_cnt_ret <= cnt_ret;
    end

    roce_stack dut (
        .nclk(clk), .nresetn(rstn),
        .s_axis_rx(axis_rx), .m_axis_tx(axis_tx),
        .s_rdma_qp_interface(qp_if), .s_rdma_conn_interface(conn_if),
        .s_rdma_sq(sq_if), .m_rdma_ack(ack_if),
        .m_rdma_rd_req(rd_req_if), .m_rdma_wr_req(wr_req_if),
        .s_axis_rdma_rd_req(axis_rd_req), .s_axis_rdma_rd_rsp(axis_rd_rsp),
        .m_axis_rdma_wr(axis_wr),
        .local_ip_address(32'hd1d4010b),      // csim TB rev_ip low lane
        .m_rdma_mem_rd_cmd(mem_rd_cmd), .m_rdma_mem_wr_cmd(mem_wr_cmd),
        .s_rdma_mem_rd_sts(mem_rd_sts), .s_rdma_mem_wr_sts(mem_wr_sts),
        .s_axis_rdma_mem_rd(axis_mem_rd), .m_axis_rdma_mem_wr(axis_mem_wr),
        .ibv_rx_pkg_count_valid(cnt_rx_v),  .ibv_rx_pkg_count_data(cnt_rx),
        .ibv_tx_pkg_count_valid(cnt_tx_v),  .ibv_tx_pkg_count_data(cnt_tx),
        .crc_drop_pkg_count_valid(cnt_crc_v), .crc_drop_pkg_count_data(cnt_crc),
        .psn_drop_pkg_count_valid(cnt_psn_v), .psn_drop_pkg_count_data(cnt_psn),
        .retrans_count_valid(cnt_ret_v),      .retrans_count_data(cnt_ret)
    );

    // ------------------------------------------------------------ signature set
    localparam logic [23:0] QPN      = 24'h000011;   // pid=17, vfid=0
    localparam logic [23:0] PSN0     = 24'h80ce4e;
    localparam logic [31:0] RKEY     = 32'h1234abcd;
    localparam logic [47:0] RADDR48  = 48'h334455667788;
    localparam logic [127:0] REM_IP  = 128'hd2d4010b_ff530f02_00000000_000080fe; // csim rev_remote_ip
    localparam logic [15:0] UDPP     = 16'hc000;
    localparam int STAGE_LEN_DEFAULT = 64;

    int test_len = STAGE_LEN_DEFAULT;
    string testname = "write64";
    logic [511:0] inj_b0, inj_b1;   // python-built injection beats (rx_neg NEG-3)

    // ------------------------------------------------------------ staging memory
    // user-side memory (URAM-staging stand-in), byte addressed
    localparam int MEM_BYTES = 1<<20;
    byte unsigned staging[MEM_BYTES];
    // retransmission buffer (DDR/HBM stand-in), keyed by beat address
    byte unsigned rbuf[MEM_BYTES];

    // ------------------------------------------------------------ TX capture
    int tx_fd;
    int tx_frame_cnt = 0;
    int tx_beat_cnt  = 0;
    assign axis_tx.tready = 1'b1;
    always_ff @(posedge clk) begin
        if (rstn && axis_tx.tvalid) begin
            $fdisplay(tx_fd, "F%0d B%0d DATA=%0128h KEEP=%016h LAST=%0d",
                      tx_frame_cnt, tx_beat_cnt, axis_tx.tdata, axis_tx.tkeep, axis_tx.tlast);
            tx_beat_cnt <= tx_beat_cnt + 1;
            if (axis_tx.tlast) begin
                tx_frame_cnt <= tx_frame_cnt + 1;
                tx_beat_cnt  <= 0;
            end
        end
    end
    // keep copies of frame[0] (WRITE) and frame[1] (responder ACK) for RX injection
    logic [511:0] cap_data[$],  cap2_data[$];
    logic [63:0]  cap_keep[$],  cap2_keep[$];
    logic         cap_last[$],  cap2_last[$];
    always_ff @(posedge clk) begin
        if (rstn && axis_tx.tvalid && tx_frame_cnt == 0) begin
            cap_data.push_back(axis_tx.tdata);
            cap_keep.push_back(axis_tx.tkeep);
            cap_last.push_back(axis_tx.tlast);
        end
        if (rstn && axis_tx.tvalid && tx_frame_cnt == 1) begin
            cap2_data.push_back(axis_tx.tdata);
            cap2_keep.push_back(axis_tx.tkeep);
            cap2_last.push_back(axis_tx.tlast);
        end
    end

    // ------------------------------------------------------------ ACK capture
    assign ack_if.ready = 1'b1;
    always_ff @(posedge clk) begin
        if (rstn && ack_if.valid)
            $display("[%0t] ACK: opcode=%0h pid=%0d vfid=%0d", $time,
                     ack_if.data.opcode, ack_if.data.pid, ack_if.data.vfid);
    end

    // ------------------------------------------------- user payload fetch model
    // m_rdma_rd_req -> stream staging bytes on s_axis_rdma_rd_req
    typedef struct { longint unsigned vaddr; int unsigned len; } memreq_s;
    memreq_s rdq[$];
    assign rd_req_if.ready = 1'b1;
    always_ff @(posedge clk) begin
        if (rstn && rd_req_if.valid) begin
            rdq.push_back('{longint'(rd_req_if.data.vaddr), int'(rd_req_if.data.len)});
            $display("[%0t] RD_REQ: vaddr=%0h len=%0d last=%0b",
                     $time, rd_req_if.data.vaddr, rd_req_if.data.len, rd_req_if.data.last);
        end
    end

    // serve one payload fetch from staging memory
    task automatic serve_payload();
        memreq_s r;
        int nbeats, off;
        r = rdq.pop_front();
        nbeats = (r.len + 63) / 64;
        for (int b = 0; b < nbeats; b++) begin
            axis_rd_req.tvalid <= 1;
            for (int i = 0; i < 64; i++) begin
                off = b*64 + i;
                axis_rd_req.tdata[i*8 +: 8] <= (off < r.len) ? staging[(r.vaddr + off) & (MEM_BYTES-1)] : 8'h00;
                axis_rd_req.tkeep[i]        <= (off < r.len);
            end
            axis_rd_req.tlast <= (b == nbeats-1);
            do @(posedge clk); while (!(axis_rd_req.tvalid && axis_rd_req.tready));
            axis_rd_req.tvalid <= 0;
        end
        axis_rd_req.tlast <= 0;
    endtask

    // Coyote contract (rdma_mux_retrans): WRITE payload is NOT requested via
    // m_rdma_rd_req — the user side pushes it spontaneously on s_axis_rdma_rd_req
    // right after the SQ command ("Shouldn't it be automatically delivered to
    // the stack?" — Coyote source comment). m_rdma_rd_req fires only for READ
    // responses. So the TB pushes payload proactively via push_payload().
    task automatic push_payload(logic [47:0] vaddr, int len);
        int nbeats, off;
        nbeats = (len + 63) / 64;
        for (int b = 0; b < nbeats; b++) begin
            axis_rd_req.tvalid <= 1;
            for (int i = 0; i < 64; i++) begin
                off = b*64 + i;
                axis_rd_req.tdata[i*8 +: 8] <= (off < len) ? staging[(vaddr + off) & (MEM_BYTES-1)] : 8'h00;
                axis_rd_req.tkeep[i]        <= (off < len);
            end
            axis_rd_req.tlast <= (b == nbeats-1);
            do @(posedge clk); while (!(axis_rd_req.tvalid && axis_rd_req.tready));
            axis_rd_req.tvalid <= 0;
        end
        axis_rd_req.tlast <= 0;
    endtask

    initial begin : payload_server
        axis_rd_req.tvalid = 0; axis_rd_req.tdata = '0;
        axis_rd_req.tkeep = '0; axis_rd_req.tlast = 0;
        axis_rd_rsp.tvalid = 0; axis_rd_rsp.tdata = '0;
        axis_rd_rsp.tkeep = '0; axis_rd_rsp.tlast = 0;
        forever begin
            @(posedge clk);
            if (rdq.size() > 0) serve_payload();   // READ-response fetches only
        end
    end

    // ------------------------------------------------- retrans buffer model
    // wr cmd + data -> store ; rd cmd -> replay
    typedef struct { longint unsigned addr; int unsigned len; } memcmd_s;
    memcmd_s wrq[$], rrq[$];
    assign mem_wr_cmd.ready = 1'b1;
    assign mem_rd_cmd.ready = 1'b1;
    always_ff @(posedge clk) begin
        if (rstn && mem_wr_cmd.valid) begin
            wrq.push_back('{longint'(mem_wr_cmd.data[63:0]), int'(mem_wr_cmd.data[95:64])});
            $display("[%0t] RBUF_WR_CMD: addr=%0h len=%0d", $time,
                     mem_wr_cmd.data[63:0], mem_wr_cmd.data[95:64]);
        end
        if (rstn && mem_rd_cmd.valid) begin
            rrq.push_back('{longint'(mem_rd_cmd.data[63:0]), int'(mem_rd_cmd.data[95:64])});
            $display("[%0t] RBUF_RD_CMD: addr=%0h len=%0d", $time,
                     mem_rd_cmd.data[63:0], mem_rd_cmd.data[95:64]);
        end
    end
    // sink retrans-buffer writes; wr_off tracks the beat offset within a
    // multi-beat store (Stage C review C-R2: was missing, so >64B stores
    // collapsed onto one 64B window — never exercised in Stage B passes)
    assign axis_mem_wr.tready = 1'b1;
    int wr_off = 0;
    always_ff @(posedge clk) begin
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
    // serve one retrans-buffer read
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

    // ------------------------------------------------- placement capture (RX)
    int pl_fd;
    assign wr_req_if.ready = 1'b1;
    assign axis_wr.tready  = 1'b1;
    always_ff @(posedge clk) begin
        if (rstn && wr_req_if.valid)
            $fdisplay(pl_fd, "WR_REQ vaddr=%0h len=%0d last=%0b",
                      wr_req_if.data.vaddr, wr_req_if.data.len, wr_req_if.data.last);
        if (rstn && axis_wr.tvalid)
            $fdisplay(pl_fd, "WR_DATA DATA=%0128h KEEP=%016h LAST=%0d",
                      axis_wr.tdata, axis_wr.tkeep, axis_wr.tlast);
    end

    // sts never driven
    assign mem_rd_sts.valid = 1'b0;
    assign mem_wr_sts.valid = 1'b0;
    assign mem_rd_sts.data  = '0;
    assign mem_wr_sts.data  = '0;

    // ------------------------------------------------------------ helpers
    task automatic push_qp_ctx(logic [31:0] state, logic [23:0] qpn,
                               logic [23:0] rpsn, logic [23:0] lpsn,
                               logic [31:0] rkey, logic [47:0] vaddr);
        qp_if.data  <= {vaddr, rkey, lpsn, rpsn, qpn, state};
        qp_if.valid <= 1;
        do @(posedge clk); while (!(qp_if.valid && qp_if.ready));
        qp_if.valid <= 0;
    endtask

    task automatic push_conn(logic [15:0] qpn, logic [23:0] rqpn,
                             logic [127:0] rip, logic [15:0] udp);
        conn_if.data  <= {udp, rip, rqpn, qpn};
        conn_if.valid <= 1;
        do @(posedge clk); while (!(conn_if.valid && conn_if.ready));
        conn_if.valid <= 0;
    endtask

    task automatic push_cmd(logic [4:0] opcode, logic [5:0] pid, logic [47:0] laddr,
                            logic [47:0] raddr, logic [27:0] len, logic lst);
        dreq_t d;
        d = '0;
        d.req_1.opcode = opcode;
        d.req_1.strm   = 0;
        d.req_1.mode   = 0;
        d.req_1.rdma   = 1;
        d.req_1.remote = 1;
        d.req_1.vfid   = 0;
        d.req_1.pid    = pid;
        d.req_1.dest   = 0;
        d.req_1.last   = lst;
        d.req_1.vaddr  = laddr;      // local (staging) addr
        d.req_1.len    = len;
        d.req_1.actv   = 1;
        d.req_1.host   = 1;
        d.req_1.offs   = 0;
        d.req_2 = d.req_1;
        d.req_2.vaddr  = raddr;      // remote vaddr -> RETH VA[47:0]
        sq_if.data  <= d;
        sq_if.valid <= 1;
        do @(posedge clk); while (!(sq_if.valid && sq_if.ready));
        sq_if.valid <= 0;
    endtask

    task automatic inject_rx_frame(int which);
        for (int b = 0; b < (which == 0 ? cap_data.size() : cap2_data.size()); b++) begin
            axis_rx.tvalid <= 1;
            axis_rx.tdata  <= (which == 0) ? cap_data[b] : cap2_data[b];
            axis_rx.tkeep  <= (which == 0) ? cap_keep[b] : cap2_keep[b];
            axis_rx.tlast  <= (which == 0) ? cap_last[b] : cap2_last[b];
            do @(posedge clk); while (!(axis_rx.tvalid && axis_rx.tready));
            axis_rx.tvalid <= 0;
        end
        axis_rx.tlast <= 0;
    endtask

    // ------------------------------------------------------------ main
    initial begin
        void'($value$plusargs("TEST=%s", testname));
        tx_fd = $fopen($sformatf("out/rtl_tx_%s.txt", testname), "w");
        pl_fd = $fopen($sformatf("out/rtl_placement_%s.txt", testname), "w");

        if (testname == "write8k") test_len = 8192;

        // staging payload signature: byte i = 0xA0 + (i mod 64) for 64B case,
        // for 8k: byte i = i mod 256 (distinguishable across beats)
        for (int i = 0; i < MEM_BYTES; i++) staging[i] = 0;
        if (test_len == 64)
            for (int i = 0; i < 64; i++) staging[i] = 8'hA0 + i;
        else
            for (int i = 0; i < test_len; i++) staging[i] = i % 256;

        qp_if.valid = 0; conn_if.valid = 0; sq_if.valid = 0;
        axis_rx.tvalid = 0; axis_rx.tdata = '0; axis_rx.tkeep = '0; axis_rx.tlast = 0;

        repeat (20) @(posedge clk);
        rstn = 1;
        repeat (50) @(posedge clk);

        // ---- program QP + conn (READY_SEND = 3)
        push_qp_ctx(32'd3, QPN, PSN0, PSN0, RKEY, 48'h0);
        push_conn(QPN[15:0], QPN, REM_IP, UDPP);
        repeat (50) @(posedge clk);

        if (testname == "write8k") begin
            // roce_stack does NOT split >PMTU requests — the SQ producer must
            // deliver pre-split FIRST/…/LAST commands (Coyote does this in
            // dreq_rdma_parser_wr, outside roce_stack). Two commands here:
            push_cmd(5'h06, 6'd17, 48'h0,    RADDR48,           28'd4096, 1'b0); // WRITE_FIRST
            $display("[%0t] SQ pushed: WRITE_FIRST 4096", $time);
            push_payload(48'h0, 4096);
            push_cmd(5'h08, 6'd17, 48'd4096, RADDR48 + 48'd4096, 28'd4096, 1'b1); // WRITE_LAST
            $display("[%0t] SQ pushed: WRITE_LAST 4096", $time);
            push_payload(48'd4096, 4096);
            wait (tx_frame_cnt >= 2);
            $display("[%0t] both split frames complete", $time);
            repeat (2000) @(posedge clk);
        end else begin
            // ---- one WRITE + proactive payload push (Coyote WRITE contract)
            push_cmd(5'h0A, 6'd17, 48'h0, RADDR48, test_len[27:0], 1'b1);
            $display("[%0t] SQ pushed: %s len=%0d", $time, testname, test_len);
            push_payload(48'h0, test_len);
            $display("[%0t] payload pushed (%0d bytes)", $time, test_len);
            wait (tx_frame_cnt >= 1);
            $display("[%0t] first TX frame complete", $time);
        end

        if (testname == "rx_loop") begin
            // inject frame[0] (the WRITE) into RX: expect placement + responder ACK on TX
            repeat (2000) @(posedge clk);
            $display("[%0t] injecting WRITE frame into RX", $time);
            inject_rx_frame(0);
            wait (tx_frame_cnt >= 2);   // responder ACK emitted
            repeat (200) @(posedge clk);
            // inject frame[1] (the ACK) back: expect m_rdma_ack (requester CQE analog)
            $display("[%0t] injecting ACK frame into RX", $time);
            inject_rx_frame(1);
            repeat (4000) @(posedge clk);
        end else if (testname == "rx_neg") begin
            // NEG-1: corrupt one payload byte (ICRC untouched) -> expect crc_drop++, no placement
            repeat (2000) @(posedge clk);
            $display("[%0t] NEG-1: injecting payload-corrupted frame", $time);
            cap_data[1][7:0] = cap_data[1][7:0] ^ 8'hFF;   // flip byte 64 (payload)
            inject_rx_frame(0);
            repeat (2000) @(posedge clk);
            $display("[%0t] after NEG-1: crc_drop=%0d rx=%0d frames=%0d", $time, r_cnt_crc, r_cnt_rx, tx_frame_cnt);
            cap_data[1][7:0] = cap_data[1][7:0] ^ 8'hFF;   // restore
            // NEG-2: good frame -> placement + ACK (epsn advances to PSN0+1)
            $display("[%0t] NEG-2: injecting good frame", $time);
            inject_rx_frame(0);
            wait (tx_frame_cnt >= 2);
            repeat (500) @(posedge clk);
            $display("[%0t] after NEG-2: rx=%0d frames=%0d", $time, r_cnt_rx, tx_frame_cnt);
            // NEG-3: PSN-skip frame (PSN0+2, valid ICRC precomputed by python via plusargs)
            if ($value$plusargs("INJ_B0=%h", inj_b0) && $value$plusargs("INJ_B1=%h", inj_b1)) begin
                $display("[%0t] NEG-3: injecting PSN-skip frame", $time);
                cap_data[0] = inj_b0;
                cap_data[1] = inj_b1;
                inject_rx_frame(0);
                repeat (4000) @(posedge clk);
                $display("[%0t] after NEG-3: psn_drop=%0d crc_drop=%0d rx=%0d frames=%0d",
                         $time, r_cnt_psn, r_cnt_crc, r_cnt_rx, tx_frame_cnt);
            end else begin
                $display("NEG-3 skipped (no INJ_B0/INJ_B1 plusargs)");
            end
        end else begin
            // capture retransmissions for a bounded window
            repeat (60000) @(posedge clk);
        end

        $display("FINAL counters: tx=%0d rx=%0d crc_drop=%0d psn_drop=%0d retrans=%0d frames=%0d",
                 r_cnt_tx, r_cnt_rx, r_cnt_crc, r_cnt_psn, r_cnt_ret, tx_frame_cnt);
        $fclose(tx_fd); $fclose(pl_fd);
        $finish;
    end

    // watchdog
    initial begin
        #500us;
        $display("WATCHDOG timeout");
        $fclose(tx_fd); $fclose(pl_fd);
        $finish;
    end

    // waveform dump for pipeline forensics (+VCD)
    initial begin
        if ($test$plusargs("VCD")) begin
            $dumpfile("out/dbg.vcd");
            $dumpvars(4, dut);
            #3us $dumpoff;
        end
    end

    // debug probe
    initial begin
        forever begin
            #10us;
            $display("[dbg %0t] qp(v%b r%b) conn(v%b r%b) sq(v%b r%b) tx(v%b) rdreq(v%b) muxst=%0d cnt_tx=%0d",
                     $time, qp_if.valid, qp_if.ready, conn_if.valid, conn_if.ready,
                     sq_if.valid, sq_if.ready, axis_tx.tvalid, rd_req_if.valid,
                     dut.inst_mux_retrans.state_C, r_cnt_tx);
        end
    end

endmodule
