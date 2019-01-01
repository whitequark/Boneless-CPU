from nmigen import *


class Arbiter:
    MUX_PTR_REG = 0b0
    MUX_PTR_PTR = 0b1

    MUX_REG_A   =  0b00
    MUX_REG_B   =  0b01
    MUX_REG_SD  =  0b10

    def __init__(self, rdport, wrport):
        self.rdport = rdport
        self.wrport = wrport

        self.i_win  = Signal(13)
        self.i_ra   = Signal(3)
        self.i_rb   = Signal(3)
        self.i_rsd  = Signal(3)
        self.i_ptr  = Signal(16)

        self.i_data = Signal(16)
        self.o_data = Signal(16)

        self.s_addr = Signal(16)

        self.ctrl   = Record([
            ("ptr", 1),
            ("reg", 2),
            ("we",  1),
        ])

    def get_fragment(self, platform):
        m = Module()

        m.submodules.rdport = self.rdport
        m.submodules.wrport = self.wrport

        with m.Switch(self.ctrl.ptr):
            with m.Case(self.MUX_PTR_REG):
                with m.Switch(self.ctrl.reg):
                    with m.Case(self.MUX_REG_A):
                        m.d.comb += self.s_addr.eq(Cat(self.i_ra,  self.i_win))
                    with m.Case(self.MUX_REG_B):
                        m.d.comb += self.s_addr.eq(Cat(self.i_rb,  self.i_win))
                    with m.Case(self.MUX_REG_SD):
                        m.d.comb += self.s_addr.eq(Cat(self.i_rsd, self.i_win))
            with m.Case(self.MUX_PTR_PTR):
                m.d.comb += self.s_addr.eq(self.i_ptr)

        m.d.comb += [
            self.rdport.addr.eq(self.s_addr),
            self.wrport.addr.eq(self.s_addr),
            self.o_data.eq(self.rdport.data),
            self.wrport.data.eq(self.i_data),
            self.rdport.en.eq(1),
            self.wrport.en.eq(self.ctrl.we),
        ]

        return m.lower(platform)

# -------------------------------------------------------------------------------------------------

import argparse
from nmigen import cli


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("type", choices=["arbiter"])
    cli.main_parser(parser)

    args = parser.parse_args()
    if args.type == "arbiter":
        mem = Memory(width=16, depth=256)
        dut = Arbiter(rdport=mem.read_port(transparent=False),
                      wrport=mem.write_port())
        ports = (
            dut.i_win, dut.i_ra, dut.i_rb, dut.i_rsd, dut.i_ptr, dut.i_data,
            dut.o_data,
            dut.ctrl.ptr, dut.ctrl.reg, dut.ctrl.we,
        )

    cli.main_runner(parser, args, dut, ports=ports)
