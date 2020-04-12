from enum import Enum
from nmigen import *

from ..arch import instr as instr, opcode as opcode
from .control import *


__all__ = ["ImmediateDecoder", "InstructionDecoder"]


class ImmediateDecoder(Elaboratable):
    IMM3_TABLE_AL = Array(instr.Imm3AL.lut_to_imm)
    IMM3_TABLE_SR = Array(instr.Imm3SR.lut_to_imm)

    class Table(Enum):
        AL    = 0b1
        SR    = 0b0

    class Width(Enum):
        IMM3  = 0b00
        IMM5  = 0b01
        IMM8  = 0b10
        IMM16 = 0b11

    def __init__(self):
        self.i_pc    = Signal(16)
        self.i_insn  = Signal(16)
        self.o_imm16 = Signal(16)

        self.c_exti  = Signal()
        self.c_table = Signal(self.Table)
        self.c_width = Signal(self.Width)
        self.c_pcrel = Signal()

        self.r_ext13 = Signal(13)

    def elaborate(self, platform):
        m = Module()

        d_imm3  = self.i_insn[0:3]
        d_imm5  = self.i_insn[0:5]
        d_imm8  = self.i_insn[0:8]
        d_imm13 = self.i_insn[0:13]

        with m.If(self.c_exti):
            m.d.sync += self.r_ext13.eq(d_imm13)

        s_table = Signal(16)
        with m.Switch(self.c_table):
            with m.Case(self.Table.AL):
                m.d.comb += s_table.eq(self.IMM3_TABLE_AL[d_imm3])
            with m.Case(self.Table.SR):
                m.d.comb += s_table.eq(self.IMM3_TABLE_SR[d_imm3])

        s_imm16 = Signal(16)
        with m.Switch(self.c_width):
            with m.Case(self.Width.IMM3):
                m.d.comb += s_imm16.eq(s_table)
            with m.Case(self.Width.IMM5):
                m.d.comb += s_imm16.eq(Cat(d_imm5, Repl(d_imm5[-1], 11)))
            with m.Case(self.Width.IMM8):
                m.d.comb += s_imm16.eq(Cat(d_imm8, Repl(d_imm8[-1],  8)))
            with m.Case(self.Width.IMM16):
                m.d.comb += s_imm16.eq(Cat(d_imm3, self.r_ext13))

        with m.If(self.c_pcrel):
            m.d.comb += self.o_imm16.eq(s_imm16 + self.i_pc)
        with m.Else():
            m.d.comb += self.o_imm16.eq(s_imm16)

        return m


class InstructionDecoder(Elaboratable):
    class Addr(Enum):
        IND   = 0b00
        RSD   = 0b01
        RB    = 0b10
        RA    = 0b11
        x     = 0b00

    class OpAMux(Enum):
        ZERO  = 0b00
        PCp1  = 0b01
        W     = 0b10
        PTR   = 0b11

    class OpBMux(Enum):
        IMM   = 0b0
        PTR   = 0b1

    class OpRMux(Enum):
        ZERO  = 0b0
        PTR   = 0b1

    class LdA(EnumGroup, layout={"mux":OpAMux, "addr":Addr}):
        ZERO  = ("ZERO", "x"  )
        PCp1  = ("PCp1", "x"  )
        W     = ("W",    "x"  )
        RA    = ("PTR",  "RA" )
        RSD   = ("PTR",  "RSD")

    class LdB(EnumGroup, layout={"mux":OpBMux, "addr":Addr}):
        IMM   = ("IMM",  "x"  )
        IND   = ("PTR",  "IND")
        RB    = ("PTR",  "RB" )
        RSD   = ("PTR",  "RSD")

    class StR(EnumGroup, layout={"mux":OpRMux, "addr":Addr}):
        x     = ("ZERO", "x"  )
        IND   = ("PTR",  "IND")
        RSD   = ("PTR",  "RSD")

    class CI(Enum):
        ZERO  = 0b00
        ONE   = 0b01
        FLAG  = 0b10

    class SI(Enum):
        ZERO  = 0b0
        MSB   = 0b1

    class Cond(Enum):
        Z     = 0b000
        S     = 0b001
        C     = 0b010
        V     = 0b011
        nCoZ  = 0b100
        SxV   = 0b101
        SxVoZ = 0b110
        A     = 0b111

    @staticmethod
    def _insn_decoder(encoding):
        try:
            insn = opcode.Instr.from_int(encoding)
            return str(insn).expandtabs(1)
        except ValueError:
            return "{:04x}".format(encoding)

    def __init__(self, alsru_cls):
        self.alsru_cls = alsru_cls

        self.i_pc    = Signal(16)
        self.i_insn  = Signal(16, decoder=self._insn_decoder)

        self.c_fetch = Signal()
        self.c_cycle = Signal(1)

        self.o_imm16 = Signal(16)
        self.o_rsd   = Signal(3)
        self.o_ra    = Signal(3)
        self.o_rb    = Signal(3)
        self.o_cond  = Signal(self.Cond)
        self.o_flag  = Signal()

        self.o_shift = Signal() # shift multicycle instruction
        self.o_multi = Signal() # other multicycle instruction
        self.o_xbus  = Signal() # use external bus for load/store
        self.o_jcc   = Signal() # select ALU operation based on cond/flag
        self.o_skip  = Signal() # skip load/execute/store

        self.o_ld_a  = Signal(self.LdA)
        self.o_ld_b  = Signal(self.LdB)
        self.o_st_r  = Signal(self.StR)
        self.o_st_f  = Record([("zs", 1), ("cv", 1)])
        self.o_st_w  = Signal()
        self.o_st_pc = Signal()

        self.o_op    = Signal(alsru_cls.Op)
        self.o_dir   = Signal(alsru_cls.Dir)
        self.o_ci    = Signal(self.CI)
        self.o_si    = Signal(self.SI)

        self.r_exti  = Signal()

        self.m_imm   = ImmediateDecoder()

    def elaborate(self, platform):
        alsru_cls = self.alsru_cls

        m = Module()

        m.submodules.imm = m_imm = self.m_imm
        m.d.comb += [
            m_imm.i_pc.eq(self.i_pc),
            m_imm.i_insn.eq(self.i_insn),
            self.o_imm16.eq(m_imm.o_imm16),
        ]

        m.d.comb += [
            self.o_rsd.eq(self.i_insn[8:11]),
            self.o_ra .eq(self.i_insn[5:8]),
            self.o_rb .eq(self.i_insn[0:3]),
        ]

        with m.Switch(self.i_insn):
            with m.Case(opcode.M_FL0.coding):
                m.d.comb += self.o_flag.eq(0)
            with m.Case(opcode.M_FL1.coding):
                m.d.comb += self.o_flag.eq(1)
        with m.Switch(self.i_insn):
            with m.Case(opcode.T_Z.coding):
                m.d.comb += self.o_cond.eq(self.Cond.Z)
            with m.Case(opcode.T_S.coding):
                m.d.comb += self.o_cond.eq(self.Cond.S)
            with m.Case(opcode.T_C.coding):
                m.d.comb += self.o_cond.eq(self.Cond.C)
            with m.Case(opcode.T_V.coding):
                m.d.comb += self.o_cond.eq(self.Cond.V)
            with m.Case(opcode.T_nCoZ.coding):
                m.d.comb += self.o_cond.eq(self.Cond.nCoZ)
            with m.Case(opcode.T_SxV.coding):
                m.d.comb += self.o_cond.eq(self.Cond.SxV)
            with m.Case(opcode.T_SxVoZ.coding):
                m.d.comb += self.o_cond.eq(self.Cond.SxVoZ)
            with m.Case(opcode.T_A.coding):
                m.d.comb += self.o_cond.eq(self.Cond.A)

        with m.Switch(self.i_insn):
            with m.Case(opcode.C_LOGIC.coding, opcode.C_ARITH.coding):
                m.d.comb += m_imm.c_table.eq(m_imm.Table.AL)
            with m.Case(opcode.C_SHIFT.coding):
                m.d.comb += m_imm.c_table.eq(m_imm.Table.SR)

        with m.Switch(self.i_insn):
            with m.Case(opcode.S_LEFT.coding):
                m.d.comb += self.o_dir.eq(alsru_cls.Dir.L)
            with m.Case(opcode.S_RIGHT.coding):
                m.d.comb += self.o_dir.eq(alsru_cls.Dir.R)
        with m.Switch(self.i_insn):
            with m.Case(opcode.S_IZERO.coding):
                m.d.comb += self.o_si.eq(self.SI.ZERO)
            with m.Case(opcode.S_IMSB.coding):
                m.d.comb += self.o_si.eq(self.SI.MSB)

        with m.Switch(self.i_insn):
            with m.Case(opcode.C_LOGIC.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM3),
                    self.o_ld_a.eq(self.LdA.RA),
                    self.o_st_r.eq(self.StR.RSD),
                    self.o_st_f.zs.eq(1),
                ]
                with m.Switch(self.i_insn):
                    with m.Case(opcode.M_RRR.coding):
                        m.d.comb += self.o_ld_b.eq(self.LdB.RB)
                    with m.Case(opcode.M_RRI.coding):
                        m.d.comb += self.o_ld_b.eq(self.LdB.IMM)
                with m.Switch(self.i_insn):
                    with m.Case(opcode.T_AND.coding):
                        m.d.comb += [
                            self.o_op.eq(alsru_cls.Op.AaB),
                        ]
                    with m.Case(opcode.T_OR.coding):
                        m.d.comb += [
                            self.o_op.eq(alsru_cls.Op.AoB),
                        ]
                    with m.Case(opcode.T_XOR.coding):
                        m.d.comb += [
                            self.o_op.eq(alsru_cls.Op.AxB),
                        ]
                    with m.Case(opcode.T_CMP.coding):
                        m.d.comb += [
                            self.o_ci.eq(self.CI.ONE),
                            self.o_op.eq(alsru_cls.Op.AmB),
                            self.o_st_r.eq(self.StR.x),
                            self.o_st_f.cv.eq(1),
                        ]

            with m.Case(opcode.C_ARITH.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM3),
                    self.o_ld_a.eq(self.LdA.RA),
                    self.o_st_r.eq(self.StR.RSD),
                    self.o_st_f.zs.eq(1),
                    self.o_st_f.cv.eq(1),
                ]
                with m.Switch(self.i_insn):
                    with m.Case(opcode.M_RRR.coding):
                        m.d.comb += self.o_ld_b.eq(self.LdB.RB)
                    with m.Case(opcode.M_RRI.coding):
                        m.d.comb += self.o_ld_b.eq(self.LdB.IMM)
                with m.Switch(self.i_insn):
                    with m.Case(opcode.T_ADD.coding):
                        m.d.comb += [
                            self.o_ci.eq(self.CI.ZERO),
                            self.o_op.eq(alsru_cls.Op.ApB),
                        ]
                    with m.Case(opcode.T_ADC.coding):
                        m.d.comb += [
                            self.o_ci.eq(self.CI.FLAG),
                            self.o_op.eq(alsru_cls.Op.ApB),
                        ]
                    with m.Case(opcode.T_SUB.coding):
                        m.d.comb += [
                            self.o_ci.eq(self.CI.ONE),
                            self.o_op.eq(alsru_cls.Op.AmB),
                        ]
                    with m.Case(opcode.T_SBC.coding):
                        m.d.comb += [
                            self.o_ci.eq(self.CI.FLAG),
                            self.o_op.eq(alsru_cls.Op.AmB),
                        ]

            with m.Case(opcode.C_SHIFT.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM3),
                    self.o_shift.eq(1),
                    self.o_ld_a.eq(self.LdA.RA),
                    self.o_st_r.eq(self.StR.RSD),
                    self.o_st_f.zs.eq(1),
                ]
                with m.Switch(self.i_insn):
                    with m.Case(opcode.M_RRR.coding):
                        m.d.comb += self.o_ld_b.eq(self.LdB.RB)
                    with m.Case(opcode.M_RRI.coding):
                        m.d.comb += self.o_ld_b.eq(self.LdB.IMM)
                with m.If(self.c_cycle == 0):
                    m.d.comb += self.o_op.eq(alsru_cls.Op.A)
                with m.Else():
                    m.d.comb += self.o_op.eq(alsru_cls.Op.SLR)

            with m.Case(opcode.C_LD.coding, opcode.C_ST.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM5),
                    self.o_ld_a.eq(self.LdA.RA),
                    self.o_op.eq(alsru_cls.Op.B),
                ]
                with m.Switch(self.i_insn):
                    with m.Case(opcode.M_ABS.coding):
                        m.d.comb += m_imm.c_pcrel.eq(0)
                    with m.Case(opcode.M_REL.coding):
                        m.d.comb += m_imm.c_pcrel.eq(1)
                with m.Switch(self.i_insn):
                    with m.Case(opcode.C_LD.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.IND),
                            self.o_st_r.eq(self.StR.RSD),
                        ]
                    with m.Case(opcode.C_ST.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.RSD),
                            self.o_st_r.eq(self.StR.IND),
                        ]

            with m.Case(opcode.C_LDX.coding, opcode.C_STX.coding):
                m.d.comb += [
                    self.o_xbus.eq(1),
                    self.o_op.eq(alsru_cls.Op.B),
                ]
                with m.Switch(self.i_insn):
                    with m.Case(opcode.M_ABS.coding):
                        m.d.comb += [
                            m_imm.c_width.eq(m_imm.Width.IMM5),
                            self.o_ld_a.eq(self.LdA.RA),
                        ]
                    with m.Case(opcode.M_LIT.coding):
                        m.d.comb += [
                            m_imm.c_width.eq(m_imm.Width.IMM8),
                            self.o_ld_a.eq(self.LdA.ZERO),
                        ]
                with m.Switch(self.i_insn):
                    with m.Case(opcode.C_LDX.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.IND),
                            self.o_st_r.eq(self.StR.RSD),
                        ]
                    with m.Case(opcode.C_STX.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.RSD),
                            self.o_st_r.eq(self.StR.IND),
                        ]

            with m.Case(opcode.C_MOVE.coding):
                with m.Switch(self.i_insn):
                    with m.Case(opcode.M_ABS.coding):
                        m.d.comb += m_imm.c_pcrel.eq(0)
                    with m.Case(opcode.M_REL.coding):
                        m.d.comb += m_imm.c_pcrel.eq(1)
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM8),
                    self.o_ld_a.eq(self.LdA.ZERO),
                    self.o_ld_b.eq(self.LdB.IMM),
                    self.o_op.eq(alsru_cls.Op.B),
                    self.o_st_r.eq(self.StR.RSD),
                ]

            with m.Case(opcode.C_STW.coding,  opcode.C_XCHW.coding,
                        opcode.C_ADJW.coding, opcode.C_LDW.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM5),
                    self.o_multi.eq(1),
                    self.o_ld_a.eq(self.LdA.W),
                ]
                with m.Switch(self.i_insn):
                    with m.Case(opcode.C_STW.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.RB),
                            self.o_op.eq(alsru_cls.Op.B),
                        ]
                    with m.Case(opcode.C_XCHW.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.RB),
                            self.o_op.eq(alsru_cls.Op.B),
                            self.o_st_r.eq(self.StR.RSD),
                        ]
                    with m.Case(opcode.C_ADJW.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.IMM),
                            self.o_op.eq(alsru_cls.Op.ApB),
                        ]
                    with m.Case(opcode.C_LDW.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.IMM),
                            self.o_op.eq(alsru_cls.Op.ApB),
                            self.o_st_r.eq(self.StR.RSD),
                        ]
                with m.If(self.c_cycle == 0):
                    m.d.comb += self.o_st_w.eq(1)
                    m.d.comb += self.o_st_r.eq(self.StR.x)      # overrides above
                with m.If(self.c_cycle == 1):
                    m.d.comb += self.o_op.eq(alsru_cls.Op.A)    # overrides above

            with m.Case(opcode.C_JR.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM5),
                    self.o_ld_a.eq(self.LdA.RSD),
                    self.o_ld_b.eq(self.LdB.IMM),
                    self.o_op.eq(alsru_cls.Op.ApB),
                    self.o_st_pc.eq(1),
                ]

            with m.Case(opcode.C_JRAL.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM5), # unused, simplifies decoding
                    self.o_multi.eq(1),
                    self.o_ld_a.eq(self.LdA.PCp1),
                    self.o_ld_b.eq(self.LdB.RB),
                    self.o_st_pc.eq(1),
                ]
                with m.If(self.c_cycle == 0):
                    m.d.comb += self.o_op.eq(alsru_cls.Op.A)
                    m.d.comb += self.o_st_r.eq(self.StR.RSD)
                with m.If(self.c_cycle == 1):
                    m.d.comb += self.o_op.eq(alsru_cls.Op.B)

            with m.Case(opcode.C_JVT.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM5),
                    self.o_ld_a.eq(self.LdA.RSD),
                    self.o_ld_b.eq(self.LdB.IND),
                    self.o_op.eq(alsru_cls.Op.ApB),
                    self.o_st_pc.eq(1),
                ]

            with m.Case(opcode.C_JST.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM5),
                    m_imm.c_pcrel.eq(1),
                    self.o_multi.eq(1),
                    self.o_ld_a.eq(self.LdA.RSD),   # latches [M] on 2nd cycle
                    self.o_op.eq(alsru_cls.Op.ApB),
                    self.o_st_pc.eq(1),
                ]
                with m.If(self.c_cycle == 0):
                    m.d.comb += self.o_ld_b.eq(self.LdB.IND)
                with m.If(self.c_cycle == 1):
                    m.d.comb += self.o_ld_b.eq(self.LdB.IMM)

            with m.Case(opcode.C_JAL.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM8),
                    self.o_multi.eq(1),
                    self.o_ld_a.eq(self.LdA.PCp1),
                    self.o_ld_b.eq(self.LdB.IMM),
                    self.o_st_pc.eq(1),
                ]
                with m.If(self.c_cycle == 0):
                    m.d.comb += self.o_op.eq(alsru_cls.Op.A)
                    m.d.comb += self.o_st_r.eq(self.StR.RSD)
                with m.If(self.c_cycle == 1):
                    m.d.comb += self.o_op.eq(alsru_cls.Op.ApB)

            with m.Case(opcode.C_JCOND.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM8),
                    self.o_jcc.eq(1),
                    self.o_ld_a.eq(self.LdA.PCp1),
                    self.o_ld_b.eq(self.LdB.IMM),
                    self.o_op.eq(alsru_cls.Op.A), # overridden in core if taken
                    self.o_st_pc.eq(1),
                ]

            with m.Case(opcode.C_EXT.coding):
                m.d.comb += [
                    m_imm.c_exti.eq(1),
                    self.o_skip.eq(1),
                ]

            with m.Case():
                m.d.comb += [
                    self.o_skip.eq(1),
                ]

        with m.If(self.c_fetch):
            m.d.sync += self.r_exti.eq(m_imm.c_exti)

        with m.If(self.r_exti):
            m.d.comb += m_imm.c_width.eq(m_imm.Width.IMM16)

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
            dut.c_exti, dut.c_table, dut.c_width, dut.c_pcrel,
        )

    if args.type == "instruction":
        dut = InstructionDecoder(alsru_cls=ALSRU_4LUT)
        ports = (
            dut.i_pc, dut.i_insn,
            dut.o_imm16, dut.o_rsd, dut.o_ra, dut.o_rb, dut.o_cond, dut.o_flag,
            dut.o_shift, dut.o_multi, dut.o_xbus, dut.o_skip,
            dut.o_ld_a, dut.o_ld_b, dut.o_st_r, dut.o_st_w, dut.o_st_pc,
            dut.o_op, dut.o_ci, dut.o_si,
        )

    cli.main_runner(parser, args, dut, ports=ports)
