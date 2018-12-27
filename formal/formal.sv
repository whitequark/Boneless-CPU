`define sign(x) ($signed(x) < 0)

module boneless_formal(
    input clk,
);
    reg  [15:0] mem [65535:0];
    wire [15:0] mem_r_addr;
    reg  [15:0] mem_r_data;
    wire        mem_r_en;
    wire [15:0] mem_w_addr;
    wire [15:0] mem_w_data;
    wire        mem_w_en;
    always @(posedge clk) begin
      if (mem_r_en) mem_r_data <= mem[mem_r_addr];
      if (mem_w_en) mem[mem_w_addr] <= mem_w_data;
    end

    reg  [15:0] ext [65535:0];
    wire [15:0] ext_addr;
    reg  [15:0] ext_r_data;
    wire        ext_r_en;
    wire [15:0] ext_w_data;
    wire        ext_w_en;
    always @(posedge clk) begin
      if (ext_r_en) ext_r_data <= ext[ext_addr];
      if (ext_w_en) ext[ext_addr] <= ext_w_data;
    end

    wire        fi_stb;
    wire [15:0] fi_pc;
    wire  [3:0] fi_flags;
    wire        fi_z, fi_s, fi_c, fi_v;
    wire [15:0] fi_insn;
    wire [15:0] fi_mem_w_addr;
    wire [15:0] fi_mem_w_data;
    wire        fi_mem_w_en;
    wire [15:0] fi_ext_addr;
    wire [15:0] fi_ext_r_data;
    wire        fi_ext_r_en;
    wire [15:0] fi_ext_w_data;
    wire        fi_ext_w_en;
    assign {fi_v, fi_c, fi_s, fi_z} = fi_flags;

    reg [12:0] r_win = 0;
    boneless cpu(
        .rst(0),
        .clk(clk),
        .r_win(r_win),
        .mem_r_addr(mem_r_addr),
        .mem_r_data(mem_r_data),
        .mem_r_en(mem_r_en),
        .mem_w_addr(mem_w_addr),
        .mem_w_data(mem_w_data),
        .mem_w_en(mem_w_en),
        .ext_addr(ext_addr),
        .ext_r_data(ext_r_data),
        .ext_r_en(ext_r_en),
        .ext_w_data(ext_w_data),
        .ext_w_en(ext_w_en),
        .fi_stb(fi_stb),
        .fi_pc(fi_pc),
        .fi_flags(fi_flags),
        .fi_insn(fi_insn),
        .fi_mem_w_addr(fi_mem_w_addr),
        .fi_mem_w_data(fi_mem_w_data),
        .fi_mem_w_en(fi_mem_w_en),
        .fi_ext_addr(fi_ext_addr),
        .fi_ext_r_data(fi_ext_r_data),
        .fi_ext_r_en(fi_ext_r_en),
        .fi_ext_w_data(fi_ext_w_data),
        .fi_ext_w_en(fi_ext_w_en),
    );

    wire [2:0]  i_regX   = fi_insn[4:2];
    wire [2:0]  i_regY   = fi_insn[7:5];
    wire [2:0]  i_regZ   = fi_insn[10:8];
    wire [4:0]  i_imm5   = fi_insn[4:0];
    wire [7:0]  i_imm8   = fi_insn[7:0];
    wire [10:0] i_imm11  = fi_insn[10:0];
    wire [3:0]  i_shift  = fi_insn[4:1];
    wire [0:0]  i_code1  = fi_insn[11];
    wire [1:0]  i_code2  = fi_insn[12:11];
    wire [2:0]  i_code3  = fi_insn[13:11];
    wire [3:0]  i_code4  = fi_insn[14:11];
    wire [4:0]  i_code5  = fi_insn[15:11];
    wire [0:0]  i_type1  = fi_insn[0];
    wire [1:0]  i_type2  = fi_insn[1:0];
    wire        i_flag   = fi_insn[11];
    wire [2:0]  i_cond   = fi_insn[14:12];

    localparam OPCLASS_A      = 4'b0000;
    localparam OPCLASS_S      = 4'b0001;
    localparam OPCLASS_M      = 3'b001;
    localparam OPCLASS_I      = 2'b01;
    localparam OPCLASS_C      = 1'b1;

    wire        i_clsA   = (i_code5[4:1] == OPCLASS_A);
    wire        i_clsS   = (i_code5[4:1] == OPCLASS_S);
    wire        i_clsM   = (i_code5[4:2] == OPCLASS_M);
    wire        i_clsI   = (i_code5[4:3] == OPCLASS_I);
    wire        i_clsC   = (i_code5[4:4] == OPCLASS_C);

    localparam OPCODE_LOGIC   = 5'b00000;
    localparam OPTYPE_AND     = 2'b00;
    localparam OPTYPE_OR      = 2'b01;
    localparam OPTYPE_XOR     = 2'b10;

    localparam OPCODE_ARITH   = 5'b00001;
    localparam OPTYPE_ADD     = 2'b00;
    localparam OPTYPE_SUB     = 2'b01;
    localparam OPTYPE_CMP     = 2'b10;

    localparam OPCODE_SHIFT_L = 5'b00010;
    localparam OPTYPE_SLL     = 1'b0;
    localparam OPTYPE_ROT     = 1'b1;

    localparam OPCODE_SHIFT_R = 5'b00011;
    localparam OPTYPE_SRL     = 1'b0;
    localparam OPTYPE_SRA     = 1'b1;

    localparam OPCODE_LD      = 5'b00100;
    localparam OPCODE_ST      = 5'b00101;
    localparam OPCODE_LDX     = 5'b00110;
    localparam OPCODE_STX     = 5'b00111;

    localparam OPCODE_MOVL    = 5'b01000;
    localparam OPCODE_MOVH    = 5'b01001;
    localparam OPCODE_MOVA    = 5'b01010;
    localparam OPCODE_ADDI    = 5'b01011;
    localparam OPCODE_LDI     = 5'b01100;
    localparam OPCODE_STI     = 5'b01101;
    localparam OPCODE_JAL     = 5'b01110;
    localparam OPCODE_JR      = 5'b01111;

    localparam COND_F_0       = 3'b000;
    localparam COND_F_Z       = 3'b001;
    localparam COND_F_S       = 3'b010;
    localparam COND_F_C       = 3'b011;
    localparam COND_F_V       = 3'b100;
    localparam COND_F_NCoZ    = 3'b101;
    localparam COND_F_SxV     = 3'b110;
    localparam COND_F_SxVoZ   = 3'b111;

    localparam OPCODE_J       = (OPCODE_F_0<<1)|0;

    wire [15:0] a_regX = {r_win, i_regX};
    wire [15:0] a_regY = {r_win, i_regY};
    wire [15:0] a_regZ = {r_win, i_regZ};

    reg  [15:0] fs_next_pc;
    reg         fs_jumped = 0;
    reg         fs_past_ext_r_en = 0;
    reg         fs_past_ext_w_en = 0;
    reg         fs_past_ext_adr  = 0;
    always @(posedge clk) begin
        // TODO: assert that no instruction takes more than <n> clock cycles
        // TODO: below, instead of $past(fi_flags), what should be used is something like
        // $prev(fi_stb, fi_flags).

        if (fi_ext_r_en || fi_ext_w_en) begin
            assert (!fs_past_ext_r_en && !fs_past_ext_w_en);
            fs_past_ext_r_en <= fi_ext_r_en;
            fs_past_ext_w_en <= fi_ext_w_en;
            fs_past_ext_adr  <= fi_ext_addr;
        end

        if (fi_stb) begin :stb
            if (fi_ext_r_en || fs_past_ext_r_en) begin
                assert (i_code5 == OPCODE_LDX);
                fs_past_ext_r_en <= 0;
            end
            if (fi_ext_w_en || fs_past_ext_w_en) begin
                assert (i_code5 == OPCODE_STX);
                fs_past_ext_w_en <= 0;
            end

            if (fs_jumped) begin
                fs_jumped <= 0;
                assert (fi_pc == fs_next_pc);
            end

            if (i_code5 == OPCODE_LOGIC) begin
                if (i_type2 != 2'b11) begin
                    assert (fi_mem_w_en);
                    assert (fi_mem_w_addr == a_regZ);
                    case (i_type2)
                        OPTYPE_AND:
                            assert (fi_mem_w_data == (mem[a_regY] & mem[a_regX]));
                        OPTYPE_OR:
                            assert (fi_mem_w_data == (mem[a_regY] | mem[a_regX]));
                        OPTYPE_XOR:
                            assert (fi_mem_w_data == (mem[a_regY] ^ mem[a_regX]));
                    endcase
                    assert (fi_z == (fi_mem_w_data == 0));
                    assert (fi_s == fi_mem_w_data[15]);
                    // fi_c is undefined
                    // fi_v is undefined
                end else begin
                    // opcode=logic optype=11 is undefined
                end
            end
            if (i_code5 == OPCODE_ARITH) begin :arith
                reg [16:0] res;
                reg c, v;
                case (i_type2)
                    OPTYPE_ADD: begin
                        res = mem[a_regY] + mem[a_regX];
                        c   = res[16];
                        v   = (`sign(mem[a_regY]) == `sign(mem[a_regX])) &&
                              (`sign(mem[a_regY]) != res[15]);
                    end
                    OPTYPE_SUB: begin
                        res = mem[a_regY] - mem[a_regX];
                        c   = ~res[16];
                        v   = (`sign(mem[a_regY]) == !`sign(mem[a_regX])) &&
                              (`sign(mem[a_regY]) != res[15]);
                    end
                    OPTYPE_CMP: begin
                        res = mem[a_regY] - mem[a_regX];
                        c   = ~res[16];
                        v   = (`sign(mem[a_regY]) == !`sign(mem[a_regX])) &&
                              (`sign(mem[a_regY]) != res[15]);
                    end
                endcase
                if (i_type2 != 2'b11) begin
                    if (i_type2 == OPTYPE_CMP) begin
                        assert (!fi_mem_w_en);
                    end else begin
                        assert (fi_mem_w_en);
                        assert (fi_mem_w_addr == a_regZ);
                        assert (fi_mem_w_data == res[15:0]);
                    end
                    assert (fi_z == (res[15:0] == 0));
                    assert (fi_s == res[15]);
                    assert (fi_c == c);
                    assert (fi_v == v);
                end else begin
                    // opcode=arith optype=11 is undefined
                end
            end
            if (i_code5 == OPCODE_SHIFT_L || i_code5 == OPCODE_SHIFT_R) begin
                assert (fi_mem_w_en);
                assert (fi_mem_w_addr == a_regZ);
                case ({ i_code5, i_type1 })
                    OPCODE_SHIFT_L, OPTYPE_SLL:
                        assert (fi_mem_w_data == (mem[a_regY] << i_shift));
                    OPCODE_SHIFT_L, OPTYPE_ROT:
                        assert (fi_mem_w_data == (mem[a_regY] << i_shift) |
                                             (mem[a_regY] >> (16 - i_shift)));
                    OPCODE_SHIFT_R, OPTYPE_SRL:
                        assert (fi_mem_w_data == (mem[a_regY] >> i_shift));
                    OPCODE_SHIFT_R, OPTYPE_SRA:
                        assert (fi_mem_w_data == {$signed(mem[a_regY]) >>> i_shift});
                endcase
                assert (fi_z == (fi_mem_w_data == 0));
                assert (fi_s == fi_mem_w_data[15]);
                // fi_c is undefined
                // fi_v is undefined
            end
            if (i_code5 == OPCODE_LD) begin
                assert (fi_mem_w_en);
                assert (fi_mem_w_addr == a_regZ);
                // FIXME: $past is a workaround for a false logic loop detected by Yosys
                // because of the way multiport memories are represented by $mem cells.
                assert (fi_mem_w_data == mem[$signed($past(mem[a_regY])) + $signed(i_imm5)]);
                assert (fi_flags == $past(fi_flags));
            end
            if (i_code5 == OPCODE_ST) begin
                assert (fi_mem_w_en);
                assert (fi_mem_w_addr == {$signed(mem[a_regY]) + $signed(i_imm5)});
                assert (fi_mem_w_data == mem[a_regZ]);
                assert (fi_flags == $past(fi_flags));
            end
            if (i_code5 == OPCODE_LDX) begin
                assert (fi_mem_w_en);
                assert (fi_ext_r_en || fs_past_ext_r_en);
                assert (fi_mem_w_addr == a_regZ);
                assert (fi_mem_w_data == ext[$signed(mem[a_regY]) + $signed(i_imm5)]);
                assert (fi_flags == $past(fi_flags));
            end
            if (i_code5 == OPCODE_STX) begin
                assert (!fi_mem_w_en);
                assert (fi_ext_w_en || fs_past_ext_w_en);
                if (fi_ext_w_en) begin
                    assert (fi_ext_addr == {$signed(mem[a_regY]) + $signed(i_imm5)});
                    assert (fi_ext_w_data == mem[a_regZ]);
                end
                if (fs_past_ext_w_en)
                    assert (ext[$signed(mem[a_regY]) + $signed(i_imm5)] == mem[a_regZ]);
                assert (fi_flags == $past(fi_flags));
            end
            if (i_code5 == OPCODE_MOVL || i_code5 == OPCODE_MOVH || i_code5 == OPCODE_MOVA) begin
                assert (fi_mem_w_en);
                assert (fi_mem_w_addr == a_regZ);
                if (i_code5 == OPCODE_MOVL)
                    assert (fi_mem_w_data == i_imm8);
                if (i_code5 == OPCODE_MOVH)
                    assert (fi_mem_w_data == i_imm8 << 8);
                if (i_code5 == OPCODE_MOVA)
                    assert (fi_mem_w_data == {$signed(fi_pc) + 16'sd1 + $signed(i_imm8)});
                assert (fi_flags == $past(fi_flags));
            end
            if (i_code5 == OPCODE_ADDI) begin :addi
                reg [15:0] tmp;
                reg [16:0] res;
                reg v;
                tmp = $signed(i_imm8);
                res = mem[a_regZ] + tmp;
                v   = (`sign(mem[a_regZ]) == tmp[15]) &&
                      (`sign(mem[a_regZ]) != res[15]);
                assert (fi_mem_w_en);
                assert (fi_mem_w_addr == a_regZ);
                assert (fi_mem_w_data == res[15:0]);
                assert (fi_z == (res[15:0] == 0));
                assert (fi_s == res[15]);
                assert (fi_c == res[16]);
                assert (fi_v == v);
            end
            if (i_code5 == OPCODE_LDI) begin
                assert (fi_mem_w_en);
                assert (fi_mem_w_addr == a_regZ);
                assert (fi_mem_w_data == mem[$signed(fi_pc) + 16'sd1 + $signed(i_imm8)]);
                assert (fi_flags == $past(fi_flags));
            end
            if (i_code5 == OPCODE_STI) begin
                assert (fi_mem_w_en);
                assert (fi_mem_w_addr == {$signed(fi_pc) + 16'sd1 + $signed(i_imm8)});
                assert (fi_mem_w_data == mem[a_regZ]);
                assert (fi_flags == $past(fi_flags));
            end
            if (i_code5 == OPCODE_JAL) begin
                assert (fi_mem_w_en);
                assert (fi_mem_w_addr == a_regZ);
                assert (fi_mem_w_data == {$signed(fi_pc) + 16'sd1});
                assert (fi_flags == $past(fi_flags));
                fs_next_pc <= $signed($signed(fi_pc) + 16'sd1 + $signed(i_imm8));
                fs_jumped  <= 1;
            end
            if (i_code5 == OPCODE_JR) begin
                assert (!fi_mem_w_en);
                assert (fi_flags == $past(fi_flags));
                fs_next_pc <= $signed($signed(mem[a_regZ]) + $signed(i_imm8));
                fs_jumped  <= 1;
            end
            if (i_clsC) begin
                assert (!fi_mem_w_en);
                assert (fi_flags == $past(fi_flags));
                fs_next_pc <= {$signed(fi_pc) + 16'sd1 + $signed(i_imm11)};
                case (i_cond)
                    COND_F_0:     fs_jumped <= i_flag == (0);
                    COND_F_Z:     fs_jumped <= i_flag == (fi_z);
                    COND_F_S:     fs_jumped <= i_flag == (fi_s);
                    COND_F_C:     fs_jumped <= i_flag == (fi_c);
                    COND_F_V:     fs_jumped <= i_flag == (fi_v);
                    COND_F_NCoZ:  fs_jumped <= i_flag == (!fi_c | fi_z);
                    COND_F_SxV:   fs_jumped <= i_flag == (fi_s ^ fi_v);
                    COND_F_SxVoZ: fs_jumped <= i_flag == ((fi_s ^ fi_v) | fi_z);
                endcase
            end
        end
    end

endmodule



