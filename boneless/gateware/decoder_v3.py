from nmigen import *

from ..arch.opcode_v3 import *


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
            m.d.comb += self.o_imm16.eq(s_imm16 + self.i_pc + 1)
        with m.Else():
            m.d.comb += self.o_imm16.eq(s_imm16)

        return m

# -------------------------------------------------------------------------------------------------

import argparse
from nmigen import cli


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("type", choices=["immediate"])
    cli.main_parser(parser)

    args = parser.parse_args()

    if args.type == "immediate":
        dut = ImmediateDecoder()
        ports = (
            dut.i_pc, dut.i_insn,
            dut.o_imm16,
            dut.c_exti, dut.c_table, dut.c_width, dut.c_addpc,
        )

    cli.main_runner(parser, args, dut, ports=ports)
