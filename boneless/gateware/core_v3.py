from nmigen import *

from .alsru import *


class BusArbiter(Elaboratable):
    MUX_ADDR_x   = 0
    MUX_ADDR_REG = 0b0
    MUX_ADDR_PTR = 0b1

    MUX_REG_x    =  0
    MUX_REG_PC   =  0b00
    MUX_REG_A    =  0b01
    MUX_REG_B    =  0b10
    MUX_REG_SD   =  0b11

    MUX_OP_x     =    0b0_00
    MUX_OP_RD    =    0b1_00
    MUX_OP_RDX   =    0b1_10
    MUX_OP_WR    =    0b1_01
    MUX_OP_WRX   =    0b1_11

    BITS_MODE    = 5
    CTRL_x       = Cat(C(MUX_ADDR_x,   1), C(MUX_REG_x,  2), C(MUX_OP_x,   3))
    CTRL_LD_PC   = Cat(C(MUX_ADDR_REG, 1), C(MUX_REG_PC, 2), C(MUX_OP_RD,  3))
    CTRL_LD_RA   = Cat(C(MUX_ADDR_REG, 1), C(MUX_REG_A,  2), C(MUX_OP_RD,  3))
    CTRL_LD_RB   = Cat(C(MUX_ADDR_REG, 1), C(MUX_REG_B,  2), C(MUX_OP_RD,  3))
    CTRL_LD_RSD  = Cat(C(MUX_ADDR_REG, 1), C(MUX_REG_SD, 2), C(MUX_OP_RD,  3))
    CTRL_ST_RSD  = Cat(C(MUX_ADDR_REG, 1), C(MUX_REG_SD, 2), C(MUX_OP_WR,  3))
    CTRL_LD_MEM  = Cat(C(MUX_ADDR_PTR, 1), C(MUX_REG_x,  2), C(MUX_OP_RD,  3))
    CTRL_ST_MEM  = Cat(C(MUX_ADDR_PTR, 1), C(MUX_REG_x,  2), C(MUX_OP_WR,  3))
    CTRL_LD_EXT  = Cat(C(MUX_ADDR_PTR, 1), C(MUX_REG_x,  2), C(MUX_OP_RDX, 3))
    CTRL_ST_EXT  = Cat(C(MUX_ADDR_PTR, 1), C(MUX_REG_x,  2), C(MUX_OP_WRX, 3))

    def __init__(self):
        self.i_pc   = Signal(16)
        self.i_w    = Signal(13)
        self.i_ra   = Signal(3)
        self.i_rb   = Signal(3)
        self.i_rsd  = Signal(3)
        self.i_ptr  = Signal(16)
        self.i_data = Signal(16)
        self.o_data = Signal(16)

        self.c_mode = Record([
            ("addr", 1),
            ("reg",  2),
            ("op",   2),
        ])

        self.o_bus_addr = Signal(16)

        self.i_mem_data = Signal(16)
        self.o_mem_re   = Signal()
        self.o_mem_data = Signal(16)
        self.o_mem_we   = Signal()

        self.i_ext_data = Signal(16)
        self.o_ext_re   = Signal()
        self.o_ext_data = Signal(16)
        self.o_ext_we   = Signal()

    def elaborate(self, platform):
        m = Module()

        with m.Switch(self.c_mode.addr):
            with m.Case(self.MUX_ADDR_REG):
                with m.Switch(self.c_mode.reg):
                    with m.Case(self.MUX_REG_PC):
                        m.d.comb += self.o_bus_addr.eq(self.i_pc)
                    with m.Case(self.MUX_REG_A):
                        m.d.comb += self.o_bus_addr.eq(Cat(self.i_ra,  self.i_w))
                    with m.Case(self.MUX_REG_B):
                        m.d.comb += self.o_bus_addr.eq(Cat(self.i_rb,  self.i_w))
                    with m.Case(self.MUX_REG_SD):
                        m.d.comb += self.o_bus_addr.eq(Cat(self.i_rsd, self.i_w))
            with m.Case(self.MUX_ADDR_PTR):
                m.d.comb += self.o_bus_addr.eq(self.i_ptr)

        with m.Switch(self.c_mode.op):
            with m.Case(self.MUX_OP_RD):
                m.d.comb += self.o_mem_re.eq(1)
            with m.Case(self.MUX_OP_RDX):
                m.d.comb += self.o_ext_re.eq(1)
            with m.Case(self.MUX_OP_WR):
                m.d.comb += self.o_mem_we.eq(1)
            with m.Case(self.MUX_OP_WRX):
                m.d.comb += self.o_ext_we.eq(1)

        r_mem_re = Signal()
        r_ext_re = Signal()
        m.d.sync += [
            r_mem_re.eq(self.o_mem_re),
            r_ext_re.eq(self.o_ext_re),
        ]

        m.d.comb += self.o_mem_data.eq(self.i_data)
        m.d.comb += self.o_ext_data.eq(self.i_data)
        with m.If(r_mem_re):
            m.d.comb += self.o_data.eq(self.i_mem_data)
        with m.If(r_ext_re):
            m.d.comb += self.o_data.eq(self.i_ext_data)

        return m

# -------------------------------------------------------------------------------------------------

import argparse
from nmigen import cli


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("type", choices=["bus-arbiter", "core-fsm"])
    cli.main_parser(parser)

    args = parser.parse_args()

    if args.type == "bus-arbiter":
        dut = BusArbiter()
        ports = (
            dut.i_pc, dut.i_w, dut.i_ra, dut.i_rb, dut.i_rsd, dut.i_ptr,
            dut.i_data, dut.o_data,
            dut.c_mode.addr, dut.c_mode.reg, dut.c_mode.op,
            dut.o_bus_addr,
            dut.i_mem_data, dut.o_mem_re, dut.o_mem_data, dut.o_mem_we,
            dut.i_ext_data, dut.o_ext_re, dut.o_ext_data, dut.o_ext_we,
        )

    cli.main_runner(parser, args, dut, ports=ports)
