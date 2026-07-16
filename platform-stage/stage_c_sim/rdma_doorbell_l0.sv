// ============================================================================
// Stage C: L0 doorbell shim — the AXI-Lite front-end for roce_stack.
// One RTL for both drivers: simulation TB (this stage) and jtag_axi on the
// board (Stage D/E). Implements the three Stage B hard specs:
//   (1) SQ packing via dreq_t field names (the 248b HLS repack lives in the
//       STAGE-B-FIXED roce_stack.sv: raddr before laddr, struct order);
//   (2) WRITE payload is pushed proactively after each SQ command (pusher
//       command handshake to rdma_uram_staging);
//   (3) >PMTU WRs are pre-split here into FIRST/MIDDLE/LAST, len per command.
//
// Register map (byte addr; addr[23]=0 regs, addr[23]=1 staging window):
//   0x000 ID          RO  32'h0C1A_0001
//   0x004 STATUS      RO  {30'b0, warn_magic, db_busy}; write bit1=1 clears warn
//   0x008 SCRATCH     RW
//   0x010 QP_STATE    RW  (READY_SEND = 3)
//   0x014 QP_QPN      RW  [23:0]
//   0x018 QP_RPSN     RW  [23:0]
//   0x01C QP_LPSN     RW  [23:0]
//   0x020 QP_RKEY     RW
//   0x024 QP_VADDR_LO RW
//   0x028 QP_VADDR_HI RW  [15:0]
//   0x02C QP_SUBMIT   W1  -> s_rdma_qp_interface beat {vaddr,rkey,lpsn,rpsn,qpn,state}
//   0x030 CONN_QPN    RW  [15:0] (local)
//   0x034 CONN_RQPN   RW  [23:0]
//   0x038 CONN_RIP0   RW  remote IP [31:0]   (128b, RIP0 = LSW)
//   0x03C CONN_RIP1   RW  remote IP [63:32]
//   0x040 CONN_RIP2   RW  remote IP [95:64]
//   0x044 CONN_RIP3   RW  remote IP [127:96]
//   0x048 CONN_UDPP   RW  [15:0]
//   0x04C CONN_SUBMIT W1  -> s_rdma_conn_interface beat {udp,rip,rqpn,qpn}
//   0x050 WQE_OPCODE  RW  [4:0]  (0x0A WRITE; splitter overrides for >PMTU)
//   0x054 WQE_QPN     RW  {[9:6] vfid, [5:0] pid}
//   0x058 WQE_LADDR_LO RW
//   0x05C WQE_LADDR_HI RW [15:0]
//   0x060 WQE_RADDR_LO RW
//   0x064 WQE_RADDR_HI RW [15:0]
//   0x068 WQE_LEN     RW  [27:0]
//   0x06C WQE_CTRL    RW  bit0 = last (reset 1)
//   0x070 DOORBELL    W1  submit (ignored while busy — poll STATUS.busy first)
//   0x080 CNT_IBV_TX  RO  (stack counter, latched)   0x084 CNT_IBV_RX
//   0x088 CNT_CRC_DROP    0x08C CNT_PSN_DROP         0x090 CNT_RETRANS
//   0x094 CNT_SQ      RO  dreq beats emitted
//   0x098 CNT_CQE     RO  m_rdma_ack beats           0x09C LAST_ACK (raw ack_t)
//   0x0A0 CNT_WR_REQ  RO  placement commands         0x0A4 CNT_RD_REQ
//   0x0A8 CNT_TX_FRM  RO  tlast on m_axis_tx         0x0AC CNT_RX_FRM
//   0x0B0 DBG_DB      RO  {db_rem[15:0], 13'b0, db_first, db_state}
//
// Magic-vaddr guard (guide Stage C fault table): qpContext.virtual_address ==
// 0xDEADBEEF / 0xFEEDBEEF are in-band partial-update opcodes in this branch
// (ib_transport_protocol.cpp:2120-2131). Submitting such a vaddr silently
// degrades to a partial update — we still submit (it IS the legit mechanism)
// but latch a sticky STATUS warn bit so an accidental hit is visible.
// ============================================================================
`timescale 1ns/1ps

import lynxTypes::*;

module rdma_doorbell_l0 #(
    parameter int STG_ADDR_BITS = 18       // staging window = 2**N bytes
) (
    input  logic aclk,
    input  logic aresetn,

    AXI4L.s s_axil,

    // control plane -> roce_stack
    metaIntf.m m_qp_if,                    // logic[183:0]
    metaIntf.m m_conn_if,                  // logic[183:0]
    metaIntf.m m_sq_if,                    // dreq_t

    // completions
    metaIntf.s s_ack_if,                   // ack_t (32b, last-gated: B8)

    // stack counter taps (valid/data pulse pairs, latched here)
    input  logic        ibv_tx_v,
    input  logic [31:0] ibv_tx_d,
    input  logic        ibv_rx_v,
    input  logic [31:0] ibv_rx_d,
    input  logic        crc_v,
    input  logic [31:0] crc_d,
    input  logic        psn_v,
    input  logic [31:0] psn_d,
    input  logic        ret_v,
    input  logic [31:0] ret_d,

    // event ticks (from top)
    input  logic tick_wr_req,
    input  logic tick_rd_req,
    input  logic tick_tx_frm,
    input  logic tick_rx_frm,

    // payload pusher command (to rdma_uram_staging)
    output logic                     pusher_go,
    output logic [STG_ADDR_BITS-1:0] pusher_addr,
    output logic [27:0]              pusher_len,
    input  logic                     pusher_done,

    // staging port A window (read data stable 2 cycles after the strobe)
    output logic                     stg_en,
    output logic                     stg_we,
    output logic [STG_ADDR_BITS-1:0] stg_addr,
    output logic [31:0]              stg_wdata,
    output logic [3:0]               stg_wstrb,
    input  logic [31:0]              stg_rdata
);

    localparam int PMTU = 4096;
    // RC opcodes (dreq encoding == BTH opcode low bits, Stage B verified)
    localparam logic [4:0] OP_WRITE_FIRST  = 5'h06;
    localparam logic [4:0] OP_WRITE_MIDDLE = 5'h07;
    localparam logic [4:0] OP_WRITE_LAST   = 5'h08;
    localparam logic [4:0] OP_WRITE_ONLY   = 5'h0A;
    localparam logic [47:0] MAGIC_RKEY_UPD = 48'h0000DEADBEEF;
    localparam logic [47:0] MAGIC_PSN_UPD  = 48'h0000FEEDBEEF;

    // ------------------------------------------------------------- registers
    logic [31:0]  r_scratch;
    logic [31:0]  r_qp_state;
    logic [23:0]  r_qp_qpn, r_qp_rpsn, r_qp_lpsn;
    logic [31:0]  r_qp_rkey;
    logic [47:0]  r_qp_vaddr;
    logic [15:0]  r_conn_qpn;
    logic [23:0]  r_conn_rqpn;
    logic [127:0] r_conn_rip;
    logic [15:0]  r_conn_udpp;
    logic [4:0]   r_wqe_opcode;
    logic [5:0]   r_wqe_pid;
    logic [3:0]   r_wqe_vfid;
    logic [47:0]  r_wqe_laddr, r_wqe_raddr;
    logic [27:0]  r_wqe_len;
    logic         r_wqe_last;
    logic         warn_magic;

    logic [31:0] c_ibv_tx, c_ibv_rx, c_crc, c_psn, c_ret;
    logic [31:0] c_sq, c_cqe, c_wr_req, c_rd_req, c_tx_frm, c_rx_frm;
    logic [31:0] r_last_ack;

    logic qp_pend, conn_pend, db_go;

    // ------------------------------------------------------- AXI-Lite: write
    logic        aw_got, w_got, bvalid;
    logic [23:0] wr_addr;
    logic [31:0] wr_data;
    logic [3:0]  wr_strb;

    assign s_axil.awready = ~aw_got;
    assign s_axil.wready  = ~w_got;
    assign s_axil.bvalid  = bvalid;
    assign s_axil.bresp   = 2'b00;

    wire wr_fire   = aw_got & w_got & ~bvalid;
    wire wr_is_stg = wr_addr[23];

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            aw_got <= 0; w_got <= 0; bvalid <= 0;
        end else begin
            if (s_axil.awvalid && s_axil.awready) begin
                aw_got  <= 1;
                wr_addr <= s_axil.awaddr[23:0];
            end
            if (s_axil.wvalid && s_axil.wready) begin
                w_got   <= 1;
                wr_data <= s_axil.wdata;
                wr_strb <= s_axil.wstrb;
            end
            if (wr_fire) bvalid <= 1;
            if (bvalid && s_axil.bready) begin
                bvalid <= 0; aw_got <= 0; w_got <= 0;
            end
        end
    end

    // -------------------------------------------------------- AXI-Lite: read
    logic        ar_got, rvalid;
    logic [23:0] rd_addr;
    logic [31:0] rdata;
    logic [2:0]  rd_cnt;

    assign s_axil.arready = ~ar_got;
    assign s_axil.rvalid  = rvalid;
    assign s_axil.rdata   = rdata;
    assign s_axil.rresp   = 2'b00;

    wire rd_is_stg = rd_addr[23];
    // issue the port-A read strobe once, with write priority on the port
    wire rd_issue = ar_got & ~rvalid & rd_is_stg & (rd_cnt == 0)
                  & ~(wr_fire & wr_is_stg);

    // ------------------------------------------------- staging port A strobes
    always_comb begin
        stg_en    = 1'b0;
        stg_we    = 1'b0;
        stg_addr  = wr_addr[STG_ADDR_BITS-1:0];
        stg_wdata = wr_data;
        stg_wstrb = wr_strb;
        if (wr_fire && wr_is_stg) begin
            stg_en = 1'b1;
            stg_we = 1'b1;
        end else if (rd_issue) begin
            stg_en   = 1'b1;
            stg_addr = rd_addr[STG_ADDR_BITS-1:0];
        end
    end

    // ------------------------------------------------------------- doorbell FSM
    typedef enum logic [1:0] {DB_IDLE, DB_CMD, DB_PAY} db_t;
    db_t         db_state;
    logic [27:0] db_rem;
    logic [47:0] db_l, db_r;
    logic        db_first;
    // WQE snapshot at doorbell strike: register writes while the splitter is
    // busy must not mutate in-flight segments (review finding C-R1)
    logic [5:0]  db_pid;
    logic [3:0]  db_vfid;
    logic        db_last;

    wire        db_busy  = (db_state != DB_IDLE);
    wire [27:0] seg_len  = (db_rem > PMTU) ? 28'(PMTU) : db_rem;
    wire        seg_tail = (db_rem <= PMTU);
    wire [4:0]  seg_op   = db_first ? (seg_tail ? OP_WRITE_ONLY : OP_WRITE_FIRST)
                                    : (seg_tail ? OP_WRITE_LAST : OP_WRITE_MIDDLE);

    dreq_t sq_data;
    always_comb begin
        sq_data = '0;
        sq_data.req_1.opcode = seg_op;
        sq_data.req_1.strm   = '0;
        sq_data.req_1.mode   = 1'b0;
        sq_data.req_1.rdma   = 1'b1;
        sq_data.req_1.remote = 1'b1;
        sq_data.req_1.vfid   = db_vfid;
        sq_data.req_1.pid    = db_pid;
        sq_data.req_1.dest   = '0;
        sq_data.req_1.last   = seg_tail ? db_last : 1'b0;
        sq_data.req_1.vaddr  = db_l;            // local (staging) addr
        sq_data.req_1.len    = seg_len;         // per-command len (B4)
        sq_data.req_1.actv   = 1'b1;
        sq_data.req_1.host   = 1'b1;
        sq_data.req_1.offs   = '0;
        sq_data.req_2        = sq_data.req_1;
        sq_data.req_2.vaddr  = db_r;            // remote vaddr -> RETH VA
    end
    assign m_sq_if.data  = sq_data;
    assign m_sq_if.valid = (db_state == DB_CMD);

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            db_state  <= DB_IDLE;
            pusher_go <= 1'b0;
            c_sq      <= '0;
        end else begin
            pusher_go <= 1'b0;
            case (db_state)
                DB_IDLE: if (db_go) begin
                    db_rem   <= r_wqe_len;
                    db_l     <= r_wqe_laddr;
                    db_r     <= r_wqe_raddr;
                    db_pid   <= r_wqe_pid;
                    db_vfid  <= r_wqe_vfid;
                    db_last  <= r_wqe_last;
                    db_first <= 1'b1;
                    db_state <= DB_CMD;
                end
                DB_CMD: if (m_sq_if.ready) begin
                    c_sq        <= c_sq + 1;
                    pusher_go   <= 1'b1;
                    pusher_addr <= db_l[STG_ADDR_BITS-1:0];
                    pusher_len  <= seg_len;
                    db_rem      <= db_rem - seg_len;
                    db_l        <= db_l + 48'(seg_len);
                    db_r        <= db_r + 48'(seg_len);
                    db_first    <= 1'b0;
                    db_state    <= DB_PAY;
                end
                DB_PAY: if (pusher_done)
                    db_state <= (db_rem == 0) ? DB_IDLE : DB_CMD;
                default: db_state <= DB_IDLE;
            endcase
        end
    end

    // --------------------------------------------------- QP / conn submitters
    // beats are snapshot at submit time: metaIntf data must stay stable while
    // valid is asserted, even if the host rewrites config registers meanwhile
    logic [183:0] qp_shadow, conn_shadow;
    assign m_qp_if.valid   = qp_pend;
    assign m_qp_if.data    = qp_shadow;
    assign m_conn_if.valid = conn_pend;
    assign m_conn_if.data  = conn_shadow;

    // ------------------------------------------------------------ completions
    assign s_ack_if.ready = 1'b1;

    // ------------------------------------------------------- register writes
    wire reg_wr = wr_fire && !wr_is_stg;

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            r_scratch <= '0;   r_qp_state <= '0;  r_qp_qpn <= '0;
            r_qp_rpsn <= '0;   r_qp_lpsn <= '0;   r_qp_rkey <= '0;
            r_qp_vaddr <= '0;  r_conn_qpn <= '0;  r_conn_rqpn <= '0;
            r_conn_rip <= '0;  r_conn_udpp <= '0; r_wqe_opcode <= OP_WRITE_ONLY;
            r_wqe_pid <= '0;   r_wqe_vfid <= '0;  r_wqe_laddr <= '0;
            r_wqe_raddr <= '0; r_wqe_len <= '0;   r_wqe_last <= 1'b1;
            warn_magic <= 1'b0; qp_pend <= 1'b0;  conn_pend <= 1'b0;
            db_go <= 1'b0;      qp_shadow <= '0;  conn_shadow <= '0;
        end else begin
            db_go <= 1'b0;
            if (qp_pend   && m_qp_if.ready)   qp_pend   <= 1'b0;
            if (conn_pend && m_conn_if.ready) conn_pend <= 1'b0;
            if (reg_wr) begin
                case (wr_addr[7:0])
                    8'h04: if (wr_data[1]) warn_magic <= 1'b0;   // W1C
                    8'h08: r_scratch     <= wr_data;
                    8'h10: r_qp_state    <= wr_data;
                    8'h14: r_qp_qpn      <= wr_data[23:0];
                    8'h18: r_qp_rpsn     <= wr_data[23:0];
                    8'h1C: r_qp_lpsn     <= wr_data[23:0];
                    8'h20: r_qp_rkey     <= wr_data;
                    8'h24: r_qp_vaddr[31:0]  <= wr_data;
                    8'h28: r_qp_vaddr[47:32] <= wr_data[15:0];
                    8'h2C: begin
                        qp_pend   <= 1'b1;
                        qp_shadow <= {r_qp_vaddr, r_qp_rkey, r_qp_lpsn,
                                      r_qp_rpsn, r_qp_qpn, r_qp_state};
                        if (r_qp_vaddr == MAGIC_RKEY_UPD ||
                            r_qp_vaddr == MAGIC_PSN_UPD)
                            warn_magic <= 1'b1;
                    end
                    8'h30: r_conn_qpn    <= wr_data[15:0];
                    8'h34: r_conn_rqpn   <= wr_data[23:0];
                    8'h38: r_conn_rip[31:0]   <= wr_data;
                    8'h3C: r_conn_rip[63:32]  <= wr_data;
                    8'h40: r_conn_rip[95:64]  <= wr_data;
                    8'h44: r_conn_rip[127:96] <= wr_data;
                    8'h48: r_conn_udpp   <= wr_data[15:0];
                    8'h4C: begin
                        conn_pend   <= 1'b1;
                        conn_shadow <= {r_conn_udpp, r_conn_rip,
                                        r_conn_rqpn, r_conn_qpn};
                    end
                    8'h50: r_wqe_opcode  <= wr_data[4:0];
                    8'h54: begin
                        r_wqe_pid  <= wr_data[5:0];
                        r_wqe_vfid <= wr_data[9:6];
                    end
                    8'h58: r_wqe_laddr[31:0]  <= wr_data;
                    8'h5C: r_wqe_laddr[47:32] <= wr_data[15:0];
                    8'h60: r_wqe_raddr[31:0]  <= wr_data;
                    8'h64: r_wqe_raddr[47:32] <= wr_data[15:0];
                    8'h68: r_wqe_len     <= wr_data[27:0];
                    8'h6C: r_wqe_last    <= wr_data[0];
                    8'h70: if (db_state == DB_IDLE && r_wqe_len != 0)
                        db_go <= 1'b1;
                    default: ;
                endcase
            end
        end
    end

    // ------------------------------------------------------------- counters
    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            c_ibv_tx <= '0; c_ibv_rx <= '0; c_crc <= '0; c_psn <= '0;
            c_ret <= '0;    c_cqe <= '0;    c_wr_req <= '0; c_rd_req <= '0;
            c_tx_frm <= '0; c_rx_frm <= '0; r_last_ack <= '0;
        end else begin
            if (ibv_tx_v) c_ibv_tx <= ibv_tx_d;
            if (ibv_rx_v) c_ibv_rx <= ibv_rx_d;
            if (crc_v)    c_crc    <= crc_d;
            if (psn_v)    c_psn    <= psn_d;
            if (ret_v)    c_ret    <= ret_d;
            if (s_ack_if.valid && s_ack_if.ready) begin
                c_cqe      <= c_cqe + 1;
                r_last_ack <= s_ack_if.data;
            end
            if (tick_wr_req) c_wr_req <= c_wr_req + 1;
            if (tick_rd_req) c_rd_req <= c_rd_req + 1;
            if (tick_tx_frm) c_tx_frm <= c_tx_frm + 1;
            if (tick_rx_frm) c_rx_frm <= c_rx_frm + 1;
        end
    end

    // -------------------------------------------------------- register reads
    logic [31:0] reg_rd_mux;
    always_comb begin
        case (rd_addr[7:0])
            8'h00: reg_rd_mux = 32'h0C1A_0001;
            8'h04: reg_rd_mux = {30'b0, warn_magic, db_busy};
            8'h08: reg_rd_mux = r_scratch;
            8'h10: reg_rd_mux = r_qp_state;
            8'h14: reg_rd_mux = {8'b0, r_qp_qpn};
            8'h18: reg_rd_mux = {8'b0, r_qp_rpsn};
            8'h1C: reg_rd_mux = {8'b0, r_qp_lpsn};
            8'h20: reg_rd_mux = r_qp_rkey;
            8'h24: reg_rd_mux = r_qp_vaddr[31:0];
            8'h28: reg_rd_mux = {16'b0, r_qp_vaddr[47:32]};
            8'h50: reg_rd_mux = {27'b0, r_wqe_opcode};
            8'h54: reg_rd_mux = {22'b0, r_wqe_vfid, r_wqe_pid};
            8'h58: reg_rd_mux = r_wqe_laddr[31:0];
            8'h68: reg_rd_mux = {4'b0, r_wqe_len};
            8'h6C: reg_rd_mux = {31'b0, r_wqe_last};
            8'h80: reg_rd_mux = c_ibv_tx;
            8'h84: reg_rd_mux = c_ibv_rx;
            8'h88: reg_rd_mux = c_crc;
            8'h8C: reg_rd_mux = c_psn;
            8'h90: reg_rd_mux = c_ret;
            8'h94: reg_rd_mux = c_sq;
            8'h98: reg_rd_mux = c_cqe;
            8'h9C: reg_rd_mux = r_last_ack;
            8'hA0: reg_rd_mux = c_wr_req;
            8'hA4: reg_rd_mux = c_rd_req;
            8'hA8: reg_rd_mux = c_tx_frm;
            8'hAC: reg_rd_mux = c_rx_frm;
            8'hB0: reg_rd_mux = {db_rem[15:0], 13'b0, db_first, db_state};
            default: reg_rd_mux = 32'h0;
        endcase
    end

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            ar_got <= 0; rvalid <= 0; rd_cnt <= '0; rdata <= '0;
        end else begin
            if (s_axil.arvalid && s_axil.arready) begin
                ar_got  <= 1;
                rd_addr <= s_axil.araddr[23:0];
                rd_cnt  <= '0;
            end
            if (ar_got && !rvalid) begin
                if (!rd_is_stg) begin
                    rdata  <= reg_rd_mux;
                    rvalid <= 1;
                end else begin
                    // strobe issued via rd_issue; data stable after 3 cycles
                    if (rd_issue || rd_cnt != 0) rd_cnt <= rd_cnt + 1;
                    if (rd_cnt == 3'd4) begin
                        rdata  <= stg_rdata;
                        rvalid <= 1;
                    end
                end
            end
            if (rvalid && s_axil.rready) begin
                rvalid <= 0; ar_got <= 0; rd_cnt <= '0;
            end
        end
    end

endmodule
