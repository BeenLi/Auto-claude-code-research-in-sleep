// ============================================================================
// Stage C top: doorbell L0 + URAM staging + roce_stack.
// This is the unit Stage D drops into the Corundum app_block (or bare-CMAC
// shell): one AXI-Lite slave in (jtag_axi on board), one 512b AXIS pair to
// the MAC, retransmission-buffer ports out (behavioral model in the Stage C
// TB; DDR4/URAM re-housing is post-platform work).
// L0 boundaries: RDMA WRITE only — READ responses unsupported (fetch commands
// are counted and sunk, s_axis_rdma_rd_rsp never driven).
// ============================================================================
`timescale 1ns/1ps

import lynxTypes::*;

module roce_l0_top #(
    parameter int STG_ADDR_BITS = 18
) (
    input  logic nclk,
    input  logic nresetn,

    AXI4L.s s_axil,

    AXI4S.s s_axis_rx,
    AXI4S.m m_axis_tx,
    input  logic [31:0] local_ip_address,

    // retransmission buffer (external at this stage)
    metaIntf.m m_rdma_mem_rd_cmd,
    metaIntf.m m_rdma_mem_wr_cmd,
    metaIntf.s s_rdma_mem_rd_sts,
    metaIntf.s s_rdma_mem_wr_sts,
    AXI4S.s s_axis_rdma_mem_rd,
    AXI4S.m m_axis_rdma_mem_wr
);

    // ------------------------------------------------------------ internals
    metaIntf #(.STYPE(logic[183:0])) qp_if   (.aclk(nclk), .aresetn(nresetn));
    metaIntf #(.STYPE(logic[183:0])) conn_if (.aclk(nclk), .aresetn(nresetn));
    metaIntf #(.STYPE(dreq_t))       sq_if   (.aclk(nclk), .aresetn(nresetn));
    metaIntf #(.STYPE(ack_t))        ack_if  (.aclk(nclk), .aresetn(nresetn));

    metaIntf #(.STYPE(req_t)) rd_req_if (.aclk(nclk), .aresetn(nresetn));
    metaIntf #(.STYPE(req_t)) wr_req_if (.aclk(nclk), .aresetn(nresetn));
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_rd_req (.aclk(nclk), .aresetn(nresetn));
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_rd_rsp (.aclk(nclk), .aresetn(nresetn));
    AXI4S #(.AXI4S_DATA_BITS(512)) axis_wr     (.aclk(nclk), .aresetn(nresetn));

    logic        cnt_rx_v, cnt_tx_v, cnt_crc_v, cnt_psn_v, cnt_ret_v;
    logic [31:0] cnt_rx, cnt_tx, cnt_crc, cnt_psn, cnt_ret;

    logic                     pusher_go, pusher_done;
    logic [STG_ADDR_BITS-1:0] pusher_addr;
    logic [27:0]              pusher_len;

    logic                     stg_en, stg_we;
    logic [STG_ADDR_BITS-1:0] stg_addr;
    logic [31:0]              stg_wdata, stg_rdata;
    logic [3:0]               stg_wstrb;

    logic tick_wr_req;

    // READ responses unsupported at L0: count + sink
    assign rd_req_if.ready    = 1'b1;
    assign axis_rd_rsp.tvalid = 1'b0;
    assign axis_rd_rsp.tdata  = '0;
    assign axis_rd_rsp.tkeep  = '0;
    assign axis_rd_rsp.tlast  = 1'b0;

    wire tick_rd_req = rd_req_if.valid & rd_req_if.ready;
    wire tick_tx_frm = m_axis_tx.tvalid & m_axis_tx.tready & m_axis_tx.tlast;
    wire tick_rx_frm = s_axis_rx.tvalid & s_axis_rx.tready & s_axis_rx.tlast;

    // ------------------------------------------------------------- doorbell
    rdma_doorbell_l0 #(.STG_ADDR_BITS(STG_ADDR_BITS)) inst_doorbell (
        .aclk(nclk), .aresetn(nresetn),
        .s_axil(s_axil),
        .m_qp_if(qp_if), .m_conn_if(conn_if), .m_sq_if(sq_if),
        .s_ack_if(ack_if),
        .ibv_tx_v(cnt_tx_v),  .ibv_tx_d(cnt_tx),
        .ibv_rx_v(cnt_rx_v),  .ibv_rx_d(cnt_rx),
        .crc_v(cnt_crc_v),    .crc_d(cnt_crc),
        .psn_v(cnt_psn_v),    .psn_d(cnt_psn),
        .ret_v(cnt_ret_v),    .ret_d(cnt_ret),
        .tick_wr_req(tick_wr_req), .tick_rd_req(tick_rd_req),
        .tick_tx_frm(tick_tx_frm), .tick_rx_frm(tick_rx_frm),
        .pusher_go(pusher_go), .pusher_addr(pusher_addr),
        .pusher_len(pusher_len), .pusher_done(pusher_done),
        .stg_en(stg_en), .stg_we(stg_we), .stg_addr(stg_addr),
        .stg_wdata(stg_wdata), .stg_wstrb(stg_wstrb), .stg_rdata(stg_rdata)
    );

    // -------------------------------------------------------------- staging
    rdma_uram_staging #(.STG_ADDR_BITS(STG_ADDR_BITS)) inst_staging (
        .aclk(nclk), .aresetn(nresetn),
        .stg_en(stg_en), .stg_we(stg_we), .stg_addr(stg_addr),
        .stg_wdata(stg_wdata), .stg_wstrb(stg_wstrb), .stg_rdata(stg_rdata),
        .pusher_go(pusher_go), .pusher_addr(pusher_addr),
        .pusher_len(pusher_len), .pusher_done(pusher_done),
        .m_axis_payload(axis_rd_req),
        .s_wr_req(wr_req_if),
        .s_axis_wr(axis_wr),
        .tick_wr_req(tick_wr_req)
    );

    // ---------------------------------------------------------------- stack
    roce_stack inst_stack (
        .nclk(nclk), .nresetn(nresetn),
        .s_axis_rx(s_axis_rx), .m_axis_tx(m_axis_tx),
        .s_rdma_qp_interface(qp_if), .s_rdma_conn_interface(conn_if),
        .s_rdma_sq(sq_if), .m_rdma_ack(ack_if),
        .m_rdma_rd_req(rd_req_if), .m_rdma_wr_req(wr_req_if),
        .s_axis_rdma_rd_req(axis_rd_req), .s_axis_rdma_rd_rsp(axis_rd_rsp),
        .m_axis_rdma_wr(axis_wr),
        .local_ip_address(local_ip_address),
        .m_rdma_mem_rd_cmd(m_rdma_mem_rd_cmd), .m_rdma_mem_wr_cmd(m_rdma_mem_wr_cmd),
        .s_rdma_mem_rd_sts(s_rdma_mem_rd_sts), .s_rdma_mem_wr_sts(s_rdma_mem_wr_sts),
        .s_axis_rdma_mem_rd(s_axis_rdma_mem_rd), .m_axis_rdma_mem_wr(m_axis_rdma_mem_wr),
        .ibv_rx_pkg_count_valid(cnt_rx_v),    .ibv_rx_pkg_count_data(cnt_rx),
        .ibv_tx_pkg_count_valid(cnt_tx_v),    .ibv_tx_pkg_count_data(cnt_tx),
        .crc_drop_pkg_count_valid(cnt_crc_v), .crc_drop_pkg_count_data(cnt_crc),
        .psn_drop_pkg_count_valid(cnt_psn_v), .psn_drop_pkg_count_data(cnt_psn),
        .retrans_count_valid(cnt_ret_v),      .retrans_count_data(cnt_ret)
    );

endmodule
