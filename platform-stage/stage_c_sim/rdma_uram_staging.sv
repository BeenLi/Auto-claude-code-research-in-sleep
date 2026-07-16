// ============================================================================
// Stage C: URAM staging + memory glue for roce_stack.
//   port A: host window (32b via doorbell AXI-Lite decode) — payload preload
//           and placement read-back, exactly what jtag_axi reaches on board.
//   port B: datapath — placement writes (priority) + payload pusher reads.
//
// Placement (stack -> mem): m_rdma_wr_req gives (vaddr,len); the m_axis_rdma_wr
// byte stream is dense (lane i = payload byte i, contiguous-low tkeep). The
// destination byte address = vaddr mod window (RETH VA is protocol-fixed, so
// unaligned targets are handled: each beat becomes 1-2 word writes with byte
// enables and a byte-rotate).
//
// Pusher (mem -> stack): streams len bytes from a 64B-ALIGNED source address
// onto s_axis_rdma_rd_req right after each SQ command (Stage B hard spec #2 —
// WRITE payload is proactive; m_rdma_rd_req fires only for READ responses).
// Source alignment is software-controlled, so alignment is an L0 constraint,
// asserted in sim.
// ============================================================================
`timescale 1ns/1ps

import lynxTypes::*;

module rdma_uram_staging #(
    parameter int STG_ADDR_BITS = 18       // 2**18 = 256 KiB
) (
    input  logic aclk,
    input  logic aresetn,

    // port A window (from doorbell)
    input  logic                     stg_en,
    input  logic                     stg_we,
    input  logic [STG_ADDR_BITS-1:0] stg_addr,
    input  logic [31:0]              stg_wdata,
    input  logic [3:0]               stg_wstrb,
    output logic [31:0]              stg_rdata,

    // pusher command (from doorbell)
    input  logic                     pusher_go,
    input  logic [STG_ADDR_BITS-1:0] pusher_addr,
    input  logic [27:0]              pusher_len,
    output logic                     pusher_done,

    // payload out -> stack s_axis_rdma_rd_req
    AXI4S.m m_axis_payload,

    // placement in <- stack
    metaIntf.s s_wr_req,                   // req_t
    AXI4S.s s_axis_wr,
    output logic tick_wr_req
);

    localparam int WBITS = STG_ADDR_BITS - 6;
    localparam int WORDS = 1 << WBITS;

    (* ram_style = "ultra" *) logic [511:0] mem [WORDS-1:0];

    // synthesis translate_off
    // SIM_ZERO_INIT: xsim leaves RAM X-initialized (no bitstream zeroing) and
    // X-compare deadlocks downstream logic — Stage B finding B6.
    initial for (int i = 0; i < WORDS; i++) mem[i] = '0;
    // synthesis translate_on

    // ------------------------------------------------------------- port A
    logic [511:0] a_q;
    logic [3:0]   a_lane_q;
    always_ff @(posedge aclk) begin
        if (stg_en) begin
            if (stg_we) begin
                for (int i = 0; i < 4; i++)
                    if (stg_wstrb[i])
                        mem[stg_addr[STG_ADDR_BITS-1:6]]
                           [(32*stg_addr[5:2] + 8*i) +: 8] <= stg_wdata[8*i +: 8];
            end else begin
                a_q      <= mem[stg_addr[STG_ADDR_BITS-1:6]];
                a_lane_q <= stg_addr[5:2];
            end
        end
        stg_rdata <= a_q[32*a_lane_q +: 32];
    end

    // ----------------------------------------------------- placement engine
    // command FIFO (depth 4)
    req_t       plq [4];
    logic [1:0] plq_wp, plq_rp;
    logic [2:0] plq_n;
    assign s_wr_req.ready = (plq_n != 3'd4);
    wire plq_push = s_wr_req.valid && s_wr_req.ready;
    assign tick_wr_req = plq_push;

    logic                     pl_active;
    logic [STG_ADDR_BITS-1:0] pl_ptr;
    logic [27:0]              pl_rem;

    // per-beat write ops (phase 1 always, phase 2 on word spill)
    logic         pb_w1v, pb_w2v;
    logic [511:0] pb_d1, pb_d2;
    logic [63:0]  pb_be1, pb_be2;
    logic [WBITS-1:0] pb_a1, pb_a2;

    assign s_axis_wr.tready = pl_active && !pb_w1v && !pb_w2v;
    wire pl_beat = s_axis_wr.tvalid && s_axis_wr.tready;

    // contiguous-low tkeep -> byte count
    logic [6:0] pl_nbytes;
    always_comb begin
        pl_nbytes = '0;
        for (int i = 0; i < 64; i++)
            if (s_axis_wr.tkeep[i]) pl_nbytes = 7'(i + 1);
    end

    wire [5:0]  pl_off   = pl_ptr[5:0];
    wire        pl_spill = ({1'b0, pl_off} + pl_nbytes) > 7'd64;
    // phase 1: mem byte (off+j) <= beat byte j        (data <<  off bytes)
    // phase 2: mem byte  k      <= beat byte k+64-off (data >> (64-off) bytes)
    wire [511:0] pl_sh1 = s_axis_wr.tdata << (32'(pl_off) * 8);
    wire [511:0] pl_sh2 = s_axis_wr.tdata >> ((64 - 32'(pl_off)) * 8);

    logic [63:0] pl_be1, pl_be2;
    always_comb begin
        for (int k = 0; k < 64; k++) begin
            pl_be1[k] = (k >= pl_off) && ((7'(k) - {1'b0, pl_off}) < pl_nbytes);
            pl_be2[k] = ({1'b0, pl_off} + pl_nbytes > 7'd64)
                        && (7'(k) < ({1'b0, pl_off} + pl_nbytes - 7'd64));
        end
    end

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            plq_wp <= '0; plq_rp <= '0; plq_n <= '0;
            pl_active <= 1'b0; pb_w1v <= 1'b0; pb_w2v <= 1'b0;
        end else begin
            if (plq_push) begin
                plq[plq_wp] <= s_wr_req.data;
                plq_wp      <= plq_wp + 1;
            end

            if (!pl_active && plq_n != 0 && !plq_push) begin
                pl_ptr    <= plq[plq_rp].vaddr[STG_ADDR_BITS-1:0];
                pl_rem    <= plq[plq_rp].len;
                pl_active <= 1'b1;
                plq_rp    <= plq_rp + 1;
                plq_n     <= plq_n - 1;
            end else begin
                plq_n <= plq_n + 3'(plq_push);
            end

            // consume write-op strobes (port B process executes them)
            if (!pl_beat) begin
                if (pb_w1v)      pb_w1v <= 1'b0;
                else if (pb_w2v) pb_w2v <= 1'b0;
            end

            if (pl_beat) begin
                pb_w1v <= 1'b1;
                pb_d1  <= pl_sh1;
                pb_be1 <= pl_be1;
                pb_a1  <= pl_ptr[STG_ADDR_BITS-1:6];
                pb_w2v <= pl_spill;
                pb_d2  <= pl_sh2;
                pb_be2 <= pl_be2;
                pb_a2  <= pl_ptr[STG_ADDR_BITS-1:6] + 1;
                pl_ptr <= pl_ptr + STG_ADDR_BITS'(pl_nbytes);
                pl_rem <= pl_rem - 28'(pl_nbytes);
                if (28'(pl_nbytes) >= pl_rem) begin
                    pl_active <= 1'b0;
                    // synthesis translate_off
                    if (!s_axis_wr.tlast)
                        $display("[%0t] STAGING WARN: placement len done w/o tlast", $time);
                    // synthesis translate_on
                end
            end
        end
    end

    // ------------------------------------------------------------- pusher
    typedef enum logic [1:0] {PU_IDLE, PU_ISSUE, PU_CAPT, PU_SEND} pu_t;
    pu_t pu_state;
    logic [STG_ADDR_BITS-1:0] pu_base;
    logic [27:0]              pu_len, pu_off;
    logic [511:0]             pu_q;

    // port B is placement-priority: read only when no write op pending
    wire pu_rd   = (pu_state == PU_ISSUE) && !pb_w1v && !pb_w2v;
    wire [WBITS-1:0] pu_word = WBITS'((pu_base + pu_off[STG_ADDR_BITS-1:0]) >> 6);

    wire [27:0] pu_nrem = pu_len - pu_off;

    assign m_axis_payload.tvalid = (pu_state == PU_SEND);
    assign m_axis_payload.tdata  = pu_q;
    assign m_axis_payload.tlast  = (pu_nrem <= 28'd64);
    always_comb
        for (int i = 0; i < 64; i++)
            m_axis_payload.tkeep[i] = (28'(i) < pu_nrem);

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            pu_state <= PU_IDLE;
            pusher_done <= 1'b0;
        end else begin
            pusher_done <= 1'b0;
            case (pu_state)
                PU_IDLE: if (pusher_go) begin
                    pu_base <= pusher_addr;
                    pu_len  <= pusher_len;
                    pu_off  <= '0;
                    pu_state <= PU_ISSUE;
                    // synthesis translate_off
                    if (pusher_addr[5:0] != 0)
                        $display("[%0t] STAGING ERROR: pusher addr not 64B-aligned (L0 constraint)", $time);
                    // synthesis translate_on
                end
                PU_ISSUE: if (pu_rd) pu_state <= PU_CAPT;   // pu_q loads this edge
                PU_CAPT:  pu_state <= PU_SEND;
                PU_SEND: if (m_axis_payload.tready) begin
                    if (pu_nrem <= 28'd64) begin
                        pusher_done <= 1'b1;
                        pu_state    <= PU_IDLE;
                    end else begin
                        pu_off   <= pu_off + 28'd64;
                        pu_state <= PU_ISSUE;
                    end
                end
                default: pu_state <= PU_IDLE;
            endcase
        end
    end

    // ------------------------------------------------------------- port B
    always_ff @(posedge aclk) begin
        if (pb_w1v) begin
            for (int i = 0; i < 64; i++)
                if (pb_be1[i]) mem[pb_a1][8*i +: 8] <= pb_d1[8*i +: 8];
        end else if (pb_w2v) begin
            for (int i = 0; i < 64; i++)
                if (pb_be2[i]) mem[pb_a2][8*i +: 8] <= pb_d2[8*i +: 8];
        end else if (pu_rd) begin
            pu_q <= mem[pu_word];
        end
    end

endmodule
