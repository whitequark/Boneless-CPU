from amaranth import *
from amaranth.lib import enum, data, wiring
from amaranth.lib.wiring import In, Out

from ..arch import instr as instr, opcode as opcode
from .alsru import ALSRU


__all__ = ["ImmediateDecoder", "InstructionDecoder"]


class ImmediateDecoder(wiring.Component):
    IMM3_TABLE_AL = Array(instr.Imm3AL.lut_to_imm)
    IMM3_TABLE_SR = Array(instr.Imm3SR.lut_to_imm)

    class Table(enum.Enum, shape=1):
        AL    = 0b1
        SR    = 0b0

    class Width(enum.Enum, shape=2):
        IMM3  = 0b00
        IMM5  = 0b01
        IMM8  = 0b10
        IMM16 = 0b11

    def __init__(self):
        super().__init__({
            "i_pc":     In(16),
            "i_insn":   In(16),
            "o_imm16":  Out(16),

            "c_exti":   In(1),
            "c_table":  In(self.Table),
            "c_width":  In(self.Width),
            "c_pcrel":  In(1),

            "r_ext13":  Out(13),
        })

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
                m.d.comb += s_imm16.eq(Cat(d_imm5, d_imm5[-1].replicate(11)))
            with m.Case(self.Width.IMM8):
                m.d.comb += s_imm16.eq(Cat(d_imm8, d_imm8[-1].replicate(8)))
            with m.Case(self.Width.IMM16):
                m.d.comb += s_imm16.eq(Cat(d_imm3, self.r_ext13))

        with m.If(self.c_pcrel):
            m.d.comb += self.o_imm16.eq(s_imm16 + self.i_pc)
        with m.Else():
            m.d.comb += self.o_imm16.eq(s_imm16)

        return m


class _Addr(enum.Enum, shape=2):
    IND   = 0b00
    RSD   = 0b01
    RB    = 0b10
    RA    = 0b11
    x     = 0b00


class _OpAMux(enum.Enum, shape=2):
    ZERO  = 0b00
    PCp1  = 0b01
    W     = 0b10
    PTR   = 0b11


class _OpBMux(enum.Enum, shape=1):
    IMM   = 0b0
    PTR   = 0b1


class _OpRMux(enum.Enum, shape=1):
    ZERO  = 0b0
    PTR   = 0b1


class InstructionDecoder(wiring.Component):
    Addr = _Addr
    OpAMux = _OpAMux
    OpBMux = _OpBMux
    OpRMux = _OpRMux

    LdAStruct = data.StructLayout({"mux":_OpAMux, "addr":_Addr})
    class LdA(enum.Enum, shape=LdAStruct):
        ZERO  = Cat(_OpAMux.ZERO, _Addr.x  )
        PCp1  = Cat(_OpAMux.PCp1, _Addr.x  )
        W     = Cat(_OpAMux.W,    _Addr.x  )
        RA    = Cat(_OpAMux.PTR,  _Addr.RA )
        RSD   = Cat(_OpAMux.PTR,  _Addr.RSD)

    LdBStruct = data.StructLayout({"mux":_OpBMux, "addr":_Addr})
    class LdB(enum.Enum, shape=LdBStruct):
        IMM   = Cat(_OpBMux.IMM,  _Addr.x  )
        IND   = Cat(_OpBMux.PTR,  _Addr.IND)
        RB    = Cat(_OpBMux.PTR,  _Addr.RB )
        RSD   = Cat(_OpBMux.PTR,  _Addr.RSD)

    StRStruct = data.StructLayout({"mux":_OpRMux, "addr":_Addr})
    class StR(enum.Enum, shape=StRStruct):
        x     = Cat(_OpRMux.ZERO, _Addr.x  )
        IND   = Cat(_OpRMux.PTR,  _Addr.IND)
        RSD   = Cat(_OpRMux.PTR,  _Addr.RSD)

    class CI(enum.Enum, shape=2):
        ZERO  = 0b00
        ONE   = 0b01
        FLAG  = 0b10

    class SI(enum.Enum, shape=1):
        ZERO  = 0b0
        MSB   = 0b1

    class Cond(enum.Enum, shape=3):
        Z     = 0b000
        S     = 0b001
        C     = 0b010
        V     = 0b011
        nCoZ  = 0b100
        SxV   = 0b101
        SxVoZ = 0b110
        A     = 0b111

    def __init__(self):
        super().__init__({
            "i_pc":    In(16),
            "i_insn":  In(16),

            "c_fetch": In(1),
            "c_cycle": In(1),

            "o_imm16": Out(16),
            "o_rsd":   Out(3),
            "o_ra":    Out(3),
            "o_rb":    Out(3),
            "o_cond":  Out(self.Cond),
            "o_flag":  Out(1),

            "o_shift": Out(1), # shift multicycle instruction
            "o_multi": Out(1), # other multicycle instruction
            "o_xbus":  Out(1), # use external bus for load/store
            "o_jcc":   Out(1), # select ALU operation based on cond/flag
            "o_skip":  Out(1), # skip load/execute/store

            "o_ld_a":  Out(self.LdA),
            "o_ld_b":  Out(self.LdB),
            "o_st_r":  Out(self.StR),
            "o_st_f":  Out(data.StructLayout({"zs": 1, "cv": 1})),
            "o_st_w":  Out(1),
            "o_st_pc": Out(1),

            "o_op":    Out(ALSRU.Op),
            "o_dir":   Out(ALSRU.Dir),
            "o_ci":    Out(self.CI),
            "o_si":    Out(self.SI),

            "r_exti":  Out(1),
        })

        def insn_decoder(encoding):
            try:
                insn = opcode.Instr.from_int(encoding)
                return str(insn).expandtabs(1)
            except ValueError:
                return "{:04x}".format(encoding)
        self.i_insn = Signal.like(self.i_insn, decoder=insn_decoder)

        self.m_imm  = ImmediateDecoder()

    def elaborate(self, platform):
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
                m.d.comb += self.o_dir.eq(ALSRU.Dir.L)
            with m.Case(opcode.S_RIGHT.coding):
                m.d.comb += self.o_dir.eq(ALSRU.Dir.R)
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
                            self.o_op.eq(ALSRU.Op.AaB),
                        ]
                    with m.Case(opcode.T_OR.coding):
                        m.d.comb += [
                            self.o_op.eq(ALSRU.Op.AoB),
                        ]
                    with m.Case(opcode.T_XOR.coding):
                        m.d.comb += [
                            self.o_op.eq(ALSRU.Op.AxB),
                        ]
                    with m.Case(opcode.T_CMP.coding):
                        m.d.comb += [
                            self.o_ci.eq(self.CI.ONE),
                            self.o_op.eq(ALSRU.Op.AmB),
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
                            self.o_op.eq(ALSRU.Op.ApB),
                        ]
                    with m.Case(opcode.T_ADC.coding):
                        m.d.comb += [
                            self.o_ci.eq(self.CI.FLAG),
                            self.o_op.eq(ALSRU.Op.ApB),
                        ]
                    with m.Case(opcode.T_SUB.coding):
                        m.d.comb += [
                            self.o_ci.eq(self.CI.ONE),
                            self.o_op.eq(ALSRU.Op.AmB),
                        ]
                    with m.Case(opcode.T_SBC.coding):
                        m.d.comb += [
                            self.o_ci.eq(self.CI.FLAG),
                            self.o_op.eq(ALSRU.Op.AmB),
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
                    m.d.comb += self.o_op.eq(ALSRU.Op.A)
                with m.Else():
                    m.d.comb += self.o_op.eq(ALSRU.Op.SLR)

            with m.Case(opcode.C_LD.coding, opcode.C_ST.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM5),
                    self.o_ld_a.eq(self.LdA.RA),
                    self.o_op.eq(ALSRU.Op.B),
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
                    self.o_op.eq(ALSRU.Op.B),
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
                    self.o_op.eq(ALSRU.Op.B),
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
                            self.o_op.eq(ALSRU.Op.B),
                        ]
                    with m.Case(opcode.C_XCHW.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.RB),
                            self.o_op.eq(ALSRU.Op.B),
                            self.o_st_r.eq(self.StR.RSD),
                        ]
                    with m.Case(opcode.C_ADJW.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.IMM),
                            self.o_op.eq(ALSRU.Op.ApB),
                        ]
                    with m.Case(opcode.C_LDW.coding):
                        m.d.comb += [
                            self.o_ld_b.eq(self.LdB.IMM),
                            self.o_op.eq(ALSRU.Op.ApB),
                            self.o_st_r.eq(self.StR.RSD),
                        ]
                with m.If(self.c_cycle == 0):
                    m.d.comb += self.o_st_w.eq(1)
                    m.d.comb += self.o_st_r.eq(self.StR.x)      # overrides above
                with m.If(self.c_cycle == 1):
                    m.d.comb += self.o_op.eq(ALSRU.Op.A)    # overrides above

            with m.Case(opcode.C_JR.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM5),
                    self.o_ld_a.eq(self.LdA.RSD),
                    self.o_ld_b.eq(self.LdB.IMM),
                    self.o_op.eq(ALSRU.Op.ApB),
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
                    m.d.comb += self.o_op.eq(ALSRU.Op.A)
                    m.d.comb += self.o_st_r.eq(self.StR.RSD)
                with m.If(self.c_cycle == 1):
                    m.d.comb += self.o_op.eq(ALSRU.Op.B)

            with m.Case(opcode.C_JVT.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM5),
                    self.o_ld_a.eq(self.LdA.RSD),
                    self.o_ld_b.eq(self.LdB.IND),
                    self.o_op.eq(ALSRU.Op.ApB),
                    self.o_st_pc.eq(1),
                ]

            with m.Case(opcode.C_JST.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM5),
                    m_imm.c_pcrel.eq(1),
                    self.o_multi.eq(1),
                    self.o_ld_a.eq(self.LdA.RSD),   # latches [M] on 2nd cycle
                    self.o_op.eq(ALSRU.Op.ApB),
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
                    m.d.comb += self.o_op.eq(ALSRU.Op.A)
                    m.d.comb += self.o_st_r.eq(self.StR.RSD)
                with m.If(self.c_cycle == 1):
                    m.d.comb += self.o_op.eq(ALSRU.Op.ApB)

            with m.Case(opcode.C_JCOND.coding):
                m.d.comb += [
                    m_imm.c_width.eq(m_imm.Width.IMM8),
                    self.o_jcc.eq(1),
                    self.o_ld_a.eq(self.LdA.PCp1),
                    self.o_ld_b.eq(self.LdB.IMM),
                    self.o_op.eq(ALSRU.Op.A), # overridden in core if taken
                    self.o_st_pc.eq(1),
                ]

            with m.Case(opcode.C_EXT.coding):
                m.d.comb += [
                    m_imm.c_exti.eq(1),
                    self.o_skip.eq(1),
                ]

            with m.Default():
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
from amaranth import cli


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("type", choices=["immediate", "instruction"])
    cli.main_parser(parser)

    args = parser.parse_args()
    if args.type == "immediate":
        dut = ImmediateDecoder()
    if args.type == "instruction":
        dut = InstructionDecoder()
    cli.main_runner(parser, args, dut)
