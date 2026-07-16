// Stage B sim stubs: behavioral stand-ins for two Vivado-generated AXIS FIFO IPs.
// Classic pointer-based FIFO (NOT SV queues: xsim does not re-evaluate continuous
// assigns that reference queue methods mutated inside always_ff — data gets
// swallowed silently; found the hard way in Stage B bring-up).
`timescale 1ns/1ps

module axis_fifo_beh #(
    parameter int DEPTH_LOG = 9   // 512 deep
) (
    input  logic         s_axis_aresetn,
    input  logic         s_axis_aclk,
    input  logic         s_axis_tvalid,
    output logic         s_axis_tready,
    input  logic [511:0] s_axis_tdata,
    input  logic [63:0]  s_axis_tkeep,
    input  logic         s_axis_tlast,
    output logic         m_axis_tvalid,
    input  logic         m_axis_tready,
    output logic [511:0] m_axis_tdata,
    output logic [63:0]  m_axis_tkeep,
    output logic         m_axis_tlast
);
    localparam int DEPTH = 1 << DEPTH_LOG;
    logic [576:0] mem [DEPTH];              // {last, keep, data}
    logic [DEPTH_LOG:0] wptr, rptr;

    wire full  = (wptr - rptr) == DEPTH[DEPTH_LOG:0];
    wire empty = (wptr == rptr);

    assign s_axis_tready = !full;
    assign m_axis_tvalid = !empty;
    assign {m_axis_tlast, m_axis_tkeep, m_axis_tdata} = mem[rptr[DEPTH_LOG-1:0]];

    always_ff @(posedge s_axis_aclk) begin
        if (!s_axis_aresetn) begin
            wptr <= '0;
            rptr <= '0;
        end else begin
            if (s_axis_tvalid && s_axis_tready) begin
                mem[wptr[DEPTH_LOG-1:0]] <= {s_axis_tlast, s_axis_tkeep, s_axis_tdata};
                wptr <= wptr + 1;
            end
            if (m_axis_tvalid && m_axis_tready)
                rptr <= rptr + 1;
        end
    end
endmodule

// Used inside rdma_mux_retrans (data to HLS / data to retrans buffer)
module axis_data_fifo_512 (
    input  logic         s_axis_aresetn,
    input  logic         s_axis_aclk,
    input  logic         s_axis_tvalid,
    output logic         s_axis_tready,
    input  logic [511:0] s_axis_tdata,
    input  logic [63:0]  s_axis_tkeep,
    input  logic         s_axis_tlast,
    output logic         m_axis_tvalid,
    input  logic         m_axis_tready,
    output logic [511:0] m_axis_tdata,
    output logic [63:0]  m_axis_tkeep,
    output logic         m_axis_tlast
);
    axis_fifo_beh #(.DEPTH_LOG(9)) i (.*);
endmodule

// Used in roce_stack RX path before the ack-gap enforcer
module axis_data_fifo_512_cc_tx (
    input  logic         s_axis_aresetn,
    input  logic         s_axis_aclk,
    input  logic         s_axis_tvalid,
    output logic         s_axis_tready,
    input  logic [511:0] s_axis_tdata,
    input  logic [63:0]  s_axis_tkeep,
    input  logic         s_axis_tlast,
    output logic         m_axis_tvalid,
    input  logic         m_axis_tready,
    output logic [511:0] m_axis_tdata,
    output logic [63:0]  m_axis_tkeep,
    output logic         m_axis_tlast
);
    axis_fifo_beh #(.DEPTH_LOG(9)) i (.*);
endmodule
