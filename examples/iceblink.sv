module top(...);
    input clk;
    output [3:0] led;

    boneless cpu(
        .clk(clk),
        .rst(0),
        .pins(led),
    );
endmodule
