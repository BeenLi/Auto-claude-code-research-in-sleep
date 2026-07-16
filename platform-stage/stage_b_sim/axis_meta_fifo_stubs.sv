// AUTO-STYLE Stage B: behavioral stand-ins for axis_data_fifo_meta_* Vivado IPs.
// Pointer-based (no SV queues: xsim does not re-evaluate continuous assigns
// that reference queue methods mutated in always_ff).
`timescale 1ns/1ps

module axis_meta_fifo_beh #(
    parameter int W = 32
) (
    input  logic         s_axis_aresetn,
    input  logic         s_axis_aclk,
    input  logic         s_axis_tvalid,
    output logic         s_axis_tready,
    input  logic [W-1:0] s_axis_tdata,
    output logic         m_axis_tvalid,
    input  logic         m_axis_tready,
    output logic [W-1:0] m_axis_tdata
);
    logic [W-1:0] mem [64];
    logic [6:0] wptr, rptr;
    wire full  = (wptr - rptr) == 7'd64;
    wire empty = (wptr == rptr);
    assign s_axis_tready = !full;
    assign m_axis_tvalid = !empty;
    assign m_axis_tdata  = mem[rptr[5:0]];
    always_ff @(posedge s_axis_aclk) begin
        if (!s_axis_aresetn) begin
            wptr <= '0; rptr <= '0;
        end else begin
            if (s_axis_tvalid && s_axis_tready) begin
                mem[wptr[5:0]] <= s_axis_tdata;
                wptr <= wptr + 7'd1;
            end
            if (m_axis_tvalid && m_axis_tready) rptr <= rptr + 7'd1;
        end
    end
endmodule

module axis_data_fifo_meta_8   (input logic s_axis_aresetn, input logic s_axis_aclk, input logic s_axis_tvalid, output logic s_axis_tready, input logic [7:0] s_axis_tdata, output logic m_axis_tvalid, input logic m_axis_tready, output logic [7:0] m_axis_tdata);
    axis_meta_fifo_beh #(.W(8)) i (.*);
endmodule
module axis_data_fifo_meta_16  (input logic s_axis_aresetn, input logic s_axis_aclk, input logic s_axis_tvalid, output logic s_axis_tready, input logic [15:0] s_axis_tdata, output logic m_axis_tvalid, input logic m_axis_tready, output logic [15:0] m_axis_tdata);
    axis_meta_fifo_beh #(.W(16)) i (.*);
endmodule
module axis_data_fifo_meta_32  (input logic s_axis_aresetn, input logic s_axis_aclk, input logic s_axis_tvalid, output logic s_axis_tready, input logic [31:0] s_axis_tdata, output logic m_axis_tvalid, input logic m_axis_tready, output logic [31:0] m_axis_tdata);
    axis_meta_fifo_beh #(.W(32)) i (.*);
endmodule
module axis_data_fifo_meta_64  (input logic s_axis_aresetn, input logic s_axis_aclk, input logic s_axis_tvalid, output logic s_axis_tready, input logic [63:0] s_axis_tdata, output logic m_axis_tvalid, input logic m_axis_tready, output logic [63:0] m_axis_tdata);
    axis_meta_fifo_beh #(.W(64)) i (.*);
endmodule
module axis_data_fifo_meta_96  (input logic s_axis_aresetn, input logic s_axis_aclk, input logic s_axis_tvalid, output logic s_axis_tready, input logic [95:0] s_axis_tdata, output logic m_axis_tvalid, input logic m_axis_tready, output logic [95:0] m_axis_tdata);
    axis_meta_fifo_beh #(.W(96)) i (.*);
endmodule
module axis_data_fifo_meta_128 (input logic s_axis_aresetn, input logic s_axis_aclk, input logic s_axis_tvalid, output logic s_axis_tready, input logic [127:0] s_axis_tdata, output logic m_axis_tvalid, input logic m_axis_tready, output logic [127:0] m_axis_tdata);
    axis_meta_fifo_beh #(.W(128)) i (.*);
endmodule
module axis_data_fifo_meta_256 (input logic s_axis_aresetn, input logic s_axis_aclk, input logic s_axis_tvalid, output logic s_axis_tready, input logic [255:0] s_axis_tdata, output logic m_axis_tvalid, input logic m_axis_tready, output logic [255:0] m_axis_tdata);
    axis_meta_fifo_beh #(.W(256)) i (.*);
endmodule
module axis_data_fifo_meta_512 (input logic s_axis_aresetn, input logic s_axis_aclk, input logic s_axis_tvalid, output logic s_axis_tready, input logic [511:0] s_axis_tdata, output logic m_axis_tvalid, input logic m_axis_tready, output logic [511:0] m_axis_tdata);
    axis_meta_fifo_beh #(.W(512)) i (.*);
endmodule
