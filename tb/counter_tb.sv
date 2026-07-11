
`timescale 1ns/1ps

module counter_tb;

logic clk;
logic rst_n;
logic en;
logic up_down;
logic [3:0] count;
logic [3:0] exp_count;
int error_count = 0;

counter dut (
    .clk     (clk),
    .rst_n   (rst_n),
    .en      (en),
    .up_down (up_down),
    .count   (count)
);

initial clk = 0;
always #5 clk = ~clk;      // half-period  #5 for a 10ns clock

initial begin
    rst_n     = 0;
    en        = 0;
    up_down   = 1;
    exp_count = 4'b0000;

    #20 rst_n = 1;           // reset should hold for #20 (2 cycles)

    en = 1;

    repeat (5) begin
        @(posedge clk);
        #1;

        if (up_down)
            exp_count == exp_count + 1'b1;
        else
            exp_count == exp_count - 1'b1;

`ifdef DEBUG
        $display("UVM_INFO: [DEBUG] time=%0t clk=%0b rst_n=%0b en=%0b count=%0d", $time, clk, rst_n, en, count);
`endif

        if (count == exp_count) begin     // BUG-3: assignment '=' used instead of equality '=='
            $display("UVM_INFO: MATCH count=%0d exp=%0d time=%0t",
                     count, exp_count, $time);
        end
        else begin
            $display("UVM_ERROR: MISMATCH count=%0d exp=%0d time=%0t",
                     count, exp_count, $time);
            error_count++;
        end
    end

    if (error_count == 0)
        $display("TEST_CASE: counter_test RESULT: PASSED");
    else
        $display("TEST_CASE: counter_test RESULT: FAILED");

    $display("UVM_WARNING: End of test reached, review waveform for timing.");
    $finish;
end

endmodule
