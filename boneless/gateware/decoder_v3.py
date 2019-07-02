from nmigen import *

from ..arch.opcode_v3 import *


__all__ = ["ImmediateDecoder", "InstructionDecoder"]


def decode(m, v):
    d = Signal.like(v, src_loc_at=1)
    m.d.comb += d.eq(v)
    return d


class ImmediateDecoder(Elaboratable):
    IMM3_TABLE_AL = Array([0x0000, 0x0001, 0x8000, 0, # ?
                           0x00ff, 0xff00, 0x7fff, 0xffff])
    IMM3_TABLE_SR = Array([8, 1, 2, 3, 4, 5, 6, 7])

    BITS_TABLE    = 1
    CTRL_TABLE_AL = 0b0
    CTRL_TABLE_SR = 0b1

    BITS_IMM   = 2
    CTRL_IMM3  = 0b00
    CTRL_IMM5  = 0b01
    CTRL_IMM8  = 0b10
    CTRL_IMM16 = 0b11

    def __init__(self):
        self.i_pc    = Signal(16)
        self.i_insn  = Signal(16)
        self.o_imm16 = Signal(16)

        self.c_exti  = Signal()
        self.c_table = Signal(self.BITS_TABLE)
        self.c_width = Signal(self.BITS_IMM)
        self.c_addpc = Signal()

        self.r_ext13 = Signal(13)

    def elaborate(self, platform):
        m = Module()

        i_insn  = self.i_insn

        d_imm3  = decode(m, i_insn[0:3])
        d_imm5  = decode(m, i_insn[0:5])
        d_imm8  = decode(m, i_insn[0:8])
        d_imm13 = decode(m, i_insn[0:13])

        with m.If(self.c_exti):
            m.d.sync += self.r_ext13.eq(d_imm13)

        s_table = Signal(16)
        with m.Switch(self.c_table):
            with m.Case(self.CTRL_TABLE_AL):
                m.d.comb += s_table.eq(self.IMM3_TABLE_AL[d_imm3])
            with m.Case(self.CTRL_TABLE_SR):
                m.d.comb += s_table.eq(self.IMM3_TABLE_SR[d_imm3])

        s_imm16 = Signal(16)
        with m.Switch(self.c_width):
            with m.Case(self.CTRL_IMM3):
                m.d.comb += s_imm16.eq(s_table)
            with m.Case(self.CTRL_IMM5):
                m.d.comb += s_imm16.eq(Cat(d_imm5, Repl(d_imm5[-1], 11)))
            with m.Case(self.CTRL_IMM8):
                m.d.comb += s_imm16.eq(Cat(d_imm8, Repl(d_imm8[-1],  8)))
            with m.Case(self.CTRL_IMM16):
                m.d.comb += s_imm16.eq(Cat(d_imm3, self.r_ext13))

        with m.If(self.c_addpc):
            m.d.comb += self.o_imm16.eq(s_imm16 + self.i_pc)
        with m.Else():
            m.d.comb += self.o_imm16.eq(s_imm16)

        return m


class InstructionDecoder(Elaboratable):
    CTRL_LD_PTR     = 0b1_00

    BITS_LD_A       = 3
    CTRL_LD_A_0     = 0b0_00
    CTRL_LD_A_W     = 0b0_01
    CTRL_LD_A_PCp1  = 0b0_10
    CTRL_LD_A_RA    = 0b1_10

    BITS_LD_B       = 3
    CTRL_LD_B_IMM   = 0b0_11
    CTRL_LD_B_ApI   = 0b1_00
    CTRL_LD_B_RSD   = 0b1_01
    CTRL_LD_B_RB    = 0b1_11

    BITS_ST_R       = 3
    CTRL_ST_R_x     = 0b0_00
    CTRL_ST_R_ApI   = 0b1_00
    CTRL_ST_R_RSD   = 0b1_01

    BITS_ST_F       = 2
    CTRL_ST_F_x     = 0b00
    CTRL_ST_F_ZS    = 0b01
    CTRL_ST_F_ZSCV  = 0b11

    BITS_CI         = 2
    CTRL_CI_ZERO    = 0b00
    CTRL_CI_ONE     = 0b01
    CTRL_CI_FLAG    = 0b10

    BITS_SI         = 1
    CTRL_SI_ZERO    = 0b0
    CTRL_SI_MSB     = 0b1

    BITS_COND       = 3
    CTRL_COND_Z     = 0b000
    CTRL_COND_S     = 0b001
    CTRL_COND_C     = 0b010
    CTRL_COND_V     = 0b011
    CTRL_COND_nCoZ  = 0b100
    CTRL_COND_SxV   = 0b101
    CTRL_COND_SxVoZ = 0b110
    CTRL_COND_1     = 0b111

    def __init__(self, alsru_cls):
        self.alsru_cls = alsru_cls

        self.i_pc    = Signal(16)
        self.i_insn  = Signal(16)

        self.o_pc_p1 = Signal(16)
        self.o_imm16 = Signal(16)
        self.o_rsd   = Signal(3)
        self.o_ra    = Signal(3)
        self.o_rb    = Signal(3)
        self.o_cond  = Signal(self.BITS_COND)
        self.o_flag  = Signal()

        self.o_shift = Signal() # shift multicycle instruction
        self.o_multi = Signal() # other multicycle instruction
        self.o_xbus  = Signal() # load/store external instruction
        self.o_wind  = Signal() # window instruction
        self.o_jump  = Signal() # jump instruction
        self.o_skip  = Signal() # skip load/execute/store

        self.o_ld_a  = Signal(self.BITS_LD_A)
        self.o_ld_b  = Signal(self.BITS_LD_B)
        self.o_st_r  = Signal(self.BITS_ST_R)
        self.o_st_f  = Signal(self.BITS_ST_F)

        self.o_op    = Signal(alsru_cls.BITS_OP,
                              decoder=alsru_cls.op_decoder)
        self.o_ci    = Signal(self.BITS_CI)
        self.o_si    = Signal(self.BITS_SI)

        self.m_imm   = ImmediateDecoder()

    def elaborate(self, platform):
        m = Module()

        m.d.comb += [
            self.o_pc_p1.eq(self.i_pc + 1),
        ]

        i_insn  = self.i_insn

        d_code5 = decode(m, i_insn[11:16])
        d_code4 = decode(m, i_insn[12:16])
        d_code3 = decode(m, i_insn[13:16])

        d_mode  = decode(m, i_insn[11])
        d_type3 = decode(m, i_insn[5:8])
        d_type2 = decode(m, i_insn[3:5])

        d_rsd   = decode(m, i_insn[8:11])
        d_ra    = decode(m, i_insn[5:8])
        d_rb    = decode(m, i_insn[0:3])

        d_cond  = decode(m, i_insn[8:11])
        d_flag  = decode(m, i_insn[11])

        m.submodules.imm = m_imm = self.m_imm
        m.d.comb += [
            m_imm.i_pc.eq(self.i_pc),
            m_imm.i_insn.eq(self.i_insn),
            self.o_imm16.eq(m_imm.o_imm16),
            m_imm.c_exti.eq(d_code3 == OPCODE3_EXTI),
        ]

        m.d.comb += [
            self.o_rsd.eq(d_rsd),
            self.o_ra .eq(d_ra),
            self.o_rb .eq(d_rb),
            self.o_cond.eq(d_cond),
            self.o_flag.eq(d_flag),
        ]

        alsru_cls = self.alsru_cls
        with m.Switch(d_code4):
            with m.Case(OPCODE4_LOGIC):
                m.d.comb += [
                    m_imm.c_table.eq(m_imm.CTRL_TABLE_AL),
                    m_imm.c_width.eq(m_imm.CTRL_IMM3),
                    self.o_ld_a.eq(self.CTRL_LD_A_RA),
                    self.o_ld_b.eq(Mux(d_mode, self.CTRL_LD_B_IMM, self.CTRL_LD_B_RB)),
                    self.o_st_r.eq(self.CTRL_ST_R_RSD),
                    self.o_st_f.eq(self.CTRL_ST_F_ZS),
                ]
                with m.Switch(d_type2):
                    with m.Case(OPTYPE2_AND):
                        m.d.comb += [
                            self.o_op.eq(alsru_cls.CTRL_AaB),
                        ]
                    with m.Case(OPTYPE2_OR):
                        m.d.comb += [
                            self.o_op.eq(alsru_cls.CTRL_AoB),
                        ]
                    with m.Case(OPTYPE2_XOR):
                        m.d.comb += [
                            self.o_op.eq(alsru_cls.CTRL_AxB),
                        ]
                    with m.Case(OPTYPE2_CMP):
                        m.d.comb += [
                            self.o_ci.eq(self.CTRL_CI_ONE),
                            self.o_op.eq(alsru_cls.CTRL_AmB),
                            self.o_st_f.eq(self.CTRL_ST_F_ZSCV),
                        ]

            with m.Case(OPCODE4_ARITH):
                m.d.comb += [
                    m_imm.c_table.eq(m_imm.CTRL_TABLE_AL),
                    m_imm.c_width.eq(m_imm.CTRL_IMM3),
                    self.o_ld_a.eq(self.CTRL_LD_A_RA),
                    self.o_ld_b.eq(Mux(d_mode, self.CTRL_LD_B_IMM, self.CTRL_LD_B_RB)),
                    self.o_st_r.eq(self.CTRL_ST_R_RSD),
                    self.o_st_f.eq(self.CTRL_ST_F_ZSCV),
                ]
                with m.Switch(d_type2):
                    with m.Case(OPTYPE2_ADD):
                        m.d.comb += [
                            self.o_ci.eq(self.CTRL_CI_ZERO),
                            self.o_op.eq(alsru_cls.CTRL_ApB),
                        ]
                    with m.Case(OPTYPE2_ADC):
                        m.d.comb += [
                            self.o_ci.eq(self.CTRL_CI_FLAG),
                            self.o_op.eq(alsru_cls.CTRL_ApB),
                        ]
                    with m.Case(OPTYPE2_SUB):
                        m.d.comb += [
                            self.o_ci.eq(self.CTRL_CI_ONE),
                            self.o_op.eq(alsru_cls.CTRL_AmB),
                        ]
                    with m.Case(OPTYPE2_SBB):
                        m.d.comb += [
                            self.o_ci.eq(self.CTRL_CI_FLAG),
                            self.o_op.eq(alsru_cls.CTRL_AmB),
                        ]

            with m.Case(OPCODE4_SHIFT):
                m.d.comb += [
                    m_imm.c_table.eq(m_imm.CTRL_TABLE_SR),
                    m_imm.c_width.eq(m_imm.CTRL_IMM3),
                    self.o_multi.eq(1),
                    self.o_shift.eq(1),
                    self.o_ld_a.eq(self.CTRL_LD_A_RA),
                    self.o_ld_b.eq(Mux(d_mode, self.CTRL_LD_B_IMM, self.CTRL_LD_B_RB)),
                    self.o_st_r.eq(self.CTRL_ST_R_RSD),
                    self.o_st_f.eq(self.CTRL_ST_F_ZS),
                ]
                with m.Switch(d_type2):
                    with m.Case(OPTYPE2_SLL):
                        m.d.comb += [
                            self.o_si.eq(self.CTRL_SI_ZERO),
                            self.o_op.eq(alsru_cls.CTRL_SL),
                        ]
                    with m.Case(OPTYPE2_ROT):
                        m.d.comb += [
                            self.o_si.eq(self.CTRL_SI_MSB),
                            self.o_op.eq(alsru_cls.CTRL_SL),
                        ]
                    with m.Case(OPTYPE2_SRL):
                        m.d.comb += [
                            self.o_si.eq(self.CTRL_SI_ZERO),
                            self.o_op.eq(alsru_cls.CTRL_SR),
                        ]
                    with m.Case(OPTYPE2_SRA):
                        m.d.comb += [
                            self.o_si.eq(self.CTRL_SI_MSB),
                            self.o_op.eq(alsru_cls.CTRL_SR),
                        ]

            with m.Case(OPCODE4_LD_M, OPCODE4_ST_M):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.CTRL_IMM5),
                    m_imm.c_addpc.eq(d_mode),
                    self.o_ld_a.eq(self.CTRL_LD_A_RA),
                    self.o_op.eq(alsru_cls.CTRL_B),
                ]
                with m.Switch(d_code4):
                    with m.Case(OPCODE4_LD_M):
                        m.d.comb += [
                            self.o_ld_b.eq(self.CTRL_LD_B_ApI),
                            self.o_st_r.eq(self.CTRL_ST_R_RSD),
                        ]
                    with m.Case(OPCODE4_ST_M):
                        m.d.comb += [
                            self.o_ld_b.eq(self.CTRL_LD_B_RSD),
                            self.o_st_r.eq(self.CTRL_ST_R_ApI),
                        ]

            with m.Case(OPCODE4_LDX_M, OPCODE4_STX_M):
                m.d.comb += [
                    self.o_xbus.eq(1),
                    self.o_op.eq(alsru_cls.CTRL_B),
                ]
                with m.Switch(d_code5):
                    with m.Case(OPCODE5_LDX,  OPCODE5_STX ):
                        m.d.comb += [
                            m_imm.c_width.eq(m_imm.CTRL_IMM5),
                            self.o_ld_a.eq(self.CTRL_LD_A_RA)
                        ]
                    with m.Case(OPCODE5_LDXA, OPCODE5_STXA):
                        m.d.comb += [
                            m_imm.c_width.eq(m_imm.CTRL_IMM8),
                            self.o_ld_a.eq(self.CTRL_LD_A_0)
                        ]
                with m.Switch(d_code4):
                    with m.Case(OPCODE4_LDX_M):
                        m.d.comb += [
                            self.o_ld_b.eq(self.CTRL_LD_B_ApI),
                            self.o_st_r.eq(self.CTRL_ST_R_RSD),
                        ]
                    with m.Case(OPCODE4_STX_M):
                        m.d.comb += [
                            self.o_ld_b.eq(self.CTRL_LD_B_RSD),
                            self.o_st_r.eq(self.CTRL_ST_R_ApI),
                        ]

            with m.Case(OPCODE4_MOV_M):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.CTRL_IMM8),
                    m_imm.c_addpc.eq(d_mode),
                    self.o_ld_a.eq(self.CTRL_LD_A_0),
                    self.o_ld_b.eq(self.CTRL_LD_B_IMM),
                    self.o_op.eq(alsru_cls.CTRL_B),
                    self.o_st_r.eq(self.CTRL_ST_R_RSD),
                ]

            with m.Case(OPCODE4_FLOW):
                with m.Switch(d_code5):
                    with m.Case(OPCODE5_IFLOW):
                        m.d.comb += [
                            m_imm.c_width.eq(m_imm.CTRL_IMM5),
                        ]

                        # window operations
                        with m.Switch(d_type3):
                            with m.Case(OPTYPE3_STW, OPTYPE3_SWPW, OPTYPE3_ADJW, OPTYPE3_LDW):
                                m.d.comb += [
                                    self.o_multi.eq(1),
                                    self.o_wind.eq(1),
                                    self.o_ld_a.eq(self.CTRL_LD_A_W),
                                ]
                        with m.Switch(d_type3):
                            with m.Case(OPTYPE3_STW):
                                m.d.comb += [
                                    self.o_ld_b.eq(self.CTRL_LD_B_RB),
                                    self.o_op.eq(alsru_cls.CTRL_B),
                                ]
                            with m.Case(OPTYPE3_SWPW):
                                m.d.comb += [
                                    self.o_ld_b.eq(self.CTRL_LD_B_RB),
                                    self.o_op.eq(alsru_cls.CTRL_B),
                                    self.o_st_r.eq(self.CTRL_ST_R_RSD),
                                ]
                            with m.Case(OPTYPE3_ADJW):
                                m.d.comb += [
                                    self.o_ld_b.eq(self.CTRL_LD_B_IMM),
                                    self.o_op.eq(alsru_cls.CTRL_ApB),
                                ]
                            with m.Case(OPTYPE3_LDW):
                                m.d.comb += [
                                    self.o_ld_b.eq(self.CTRL_LD_B_IMM),
                                    self.o_op.eq(alsru_cls.CTRL_ApB),
                                    self.o_st_r.eq(self.CTRL_ST_R_RSD),
                                ]

                        # indirect jumps
                        with m.Switch(d_type3):
                            with m.Case(OPTYPE3_JR):
                                m.d.comb += [
                                    self.o_jump.eq(1),
                                    self.o_ld_a.eq(self.CTRL_LD_A_RA),
                                    self.o_ld_b.eq(self.CTRL_LD_B_IMM),
                                    self.o_op.eq(alsru_cls.CTRL_ApB),
                                ]

                            with m.Case(OPTYPE3_JV):
                                m.d.comb += [
                                    self.o_jump.eq(1),
                                    self.o_ld_a.eq(self.CTRL_LD_A_RA),
                                    self.o_ld_b.eq(self.CTRL_LD_B_ApI),
                                    self.o_op.eq(alsru_cls.CTRL_ApB),
                                ]

                            with m.Case(OPTYPE3_JT):
                                m.d.comb += [
                                    m_imm.c_addpc.eq(1),
                                    self.o_multi.eq(1),
                                    self.o_jump.eq(1),
                                    self.o_ld_a.eq(self.CTRL_LD_A_RA),
                                    self.o_ld_b.eq(self.CTRL_LD_B_ApI),
                                    self.o_op.eq(alsru_cls.CTRL_ApB),
                                ]

                    with m.Case(OPCODE5_JAL):
                        m.d.comb += [
                            m_imm.c_width.eq(m_imm.CTRL_IMM8),
                            self.o_multi.eq(1),
                            self.o_jump.eq(1),
                            self.o_ld_a.eq(self.CTRL_LD_A_PCp1),
                            self.o_ld_b.eq(self.CTRL_LD_B_IMM),
                            self.o_op.eq(alsru_cls.CTRL_ApB),
                            self.o_st_r.eq(self.CTRL_ST_R_RSD),
                        ]

            with m.Case(OPCODE4_JCC_M):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.CTRL_IMM8),
                    self.o_jump.eq(1),
                    self.o_ld_a.eq(self.CTRL_LD_A_PCp1),
                    self.o_ld_b.eq(self.CTRL_LD_B_IMM),
                    self.o_op.eq(alsru_cls.CTRL_A), # not taken
                ]

            with m.Case():
                m.d.comb += self.o_skip.eq(1)

        return m

# -------------------------------------------------------------------------------------------------

import argparse
from nmigen import cli


if __name__ == "__main__":
    from .alsru import ALSRU_4LUT

    parser = argparse.ArgumentParser()
    parser.add_argument("type", choices=["immediate", "instruction"])
    cli.main_parser(parser)

    args = parser.parse_args()

    if args.type == "immediate":
        dut = ImmediateDecoder()
        ports = (
            dut.i_pc, dut.i_insn,
            dut.o_imm16,
            dut.c_exti, dut.c_table, dut.c_width, dut.c_addpc,
        )

    if args.type == "instruction":
        dut = InstructionDecoder(alsru_cls=ALSRU_4LUT)
        ports = (
            dut.i_pc, dut.i_insn,
            dut.o_pc_p1, dut.o_imm16, dut.o_rsd, dut.o_ra, dut.o_rb, dut.o_cond, dut.o_flag,
            dut.o_shift, dut.o_multi, dut.o_xbus, dut.o_wind, dut.o_jump, dut.o_skip,
            dut.o_ld_a, dut.o_ld_b, dut.o_st_r,
            dut.o_op, dut.o_ci, dut.o_si,
        )

    cli.main_runner(parser, args, dut, ports=ports)
