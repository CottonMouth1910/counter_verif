module counter (
    input  logic clk,
    input  logic rst_n,
    input  logic en,
    input  logic up_down,      // 1 = count up, 0 = count down
    output logic [3:0] count
);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 4'b0000;
        else if (en) begin
            if (up_down)
                count <= count + 1'b1;
            else
                count <= count - 1'b1;
        end
    end
endmodule

