from enum import Enum
from amaranth import *

from .control import *


__all__ = ["ALSRU", "ALSRU_4LUT"]


class ALSRU:
    """Arithmetical, logical, shift, and rotate unit."""

    # redefined by subclasses
    class Op(EnumGroup):
        A    = ()
        B    = ()
        nB   = ()
        AaB  = ()
        AoB  = ()
        AxB  = ()
        ApB  = ()
        AmB  = ()
        SLR  = ()

    class Dir(Enum):
        L    = ()
        R    = ()

    def __init__(self, width):
        self.width = width

        self.i_a = Signal(width)
        self.i_b = Signal(width)
        self.i_c = Signal()
        self.o_o = Signal(width)
        self.r_o = Signal(width)

        self.o_z = Signal() # zero out
        self.o_s = Signal() # sign out
        self.o_c = Signal() # carry out
        self.o_v = Signal() # overflow out

        self.c_op  = Signal(self.Op) # redefined by subclasses

        self.i_h = Signal() # shift in
        self.o_h = Signal() # shift out

        self.c_dir = Signal(self.Dir)


class ALSRU_4LUT(ALSRU, Elaboratable):
    """ALSRU optimized for 4-LUT architecture with no adder pre-inversion.

    On iCE40 with Yosys, ABC, and -relut this synthesizes to the optimal 4n+3 LUTs.
    """

    # The block diagram of an unit cell is as follows:
    #
    #              A-|‾\       CO
    #                |3 |-X-·  |   O       SLn+1
    #              B-|_/    |_|‾\  |  ___    |
    #                       ._|4 |-·-|D Q|-R-·
    #              B-|‾\    | |_/    |>  |   |
    #   SRn+1-|‾\    |2 |-Y-·  |      ‾‾‾  SRn-1
    #         |1 |-S-|_/       CI
    #   SLn-1-|_/
    #
    # LUT 1 computes: R<<1, R>>1
    # LUT 2 computes: B, ~B, 0, S
    # LUT 3 computes: A&B, A|B, A^B, A
    # LUT 4 computes: X+Y, Y
    #
    # To compute:
    #      A:          X=A    Y=0   O=X+Y
    #      B:                 Y=B   O=Y
    #     ~B:                 Y=~B  O=Y
    #    A&B:          X=A&B  Y=0   O=X+Y
    #    A|B:          X=A|B  Y=0   O=X+Y
    #    A^B:          X=A^B  Y=0   O=X+Y
    #    A+B:          X=A    Y=B   O=X+Y
    #    A-B:          X=A    Y=~B  O=X+Y  (pre-invert CI)
    #   R<<1: S=SLn-1         Y=S   O=Y    (pre-load R)
    #   R>>1: S=SRn+1         Y=S   O=Y    (pre-load R)

    class XMux(Enum):
        A   = 0b00
        AaB = 0b01
        AoB = 0b10
        AxB = 0b11
        x   = 0

    class YMux(Enum):
        Z   = 0b00
        S   = 0b01
        B   = 0b10
        nB  = 0b11

    class OMux(Enum):
        XpY = 0b0
        Y   = 0b1

    class Op(EnumGroup, layout={"x":XMux, "y":YMux, "o":OMux}):
        A    = ("A",   "Z",  "XpY",)
        B    = ("x",   "B",  "Y",  )
        nB   = ("x",   "nB", "Y",  )
        AaB  = ("AaB", "Z",  "XpY",)
        AoB  = ("AoB", "Z",  "XpY",)
        AxB  = ("AxB", "Z",  "XpY",)
        ApB  = ("A",   "B",  "XpY",)
        AmB  = ("A",   "nB", "XpY",)
        SLR  = ("x",   "S",  "Y",  )

    class Dir(Enum):
        L    = 0b0
        R    = 0b1

    def elaborate(self, platform):
        m = Module()

        dec_op = self.Op.expand(m, self.c_op)

        s_s = Signal(self.width)
        with m.Switch(self.c_dir):
            with m.Case(self.Dir.L):
                m.d.comb += s_s.eq(Cat(self.i_h, self.r_o[:-1]))
                m.d.comb += self.o_h.eq(self.r_o[-1])
            with m.Case(self.Dir.R):
                m.d.comb += s_s.eq(Cat(self.r_o[ 1:], self.i_h))
                m.d.comb += self.o_h.eq(self.r_o[ 0])

        s_x = Signal(self.width)
        with m.Switch(dec_op.x):
            with m.Case(self.XMux.AaB):
                m.d.comb += s_x.eq(self.i_a & self.i_b)
            with m.Case(self.XMux.AoB):
                m.d.comb += s_x.eq(self.i_a | self.i_b)
            with m.Case(self.XMux.AxB):
                m.d.comb += s_x.eq(self.i_a ^ self.i_b)
            with m.Case(self.XMux.A):
                m.d.comb += s_x.eq(self.i_a)

        s_y = Signal(self.width)
        with m.Switch(dec_op.y):
            with m.Case(self.YMux.Z):
                m.d.comb += s_y.eq(0)
            with m.Case(self.YMux.S):
                m.d.comb += s_y.eq(s_s)
            with m.Case(self.YMux.B):
                m.d.comb += s_y.eq(self.i_b)
            with m.Case(self.YMux.nB):
                m.d.comb += s_y.eq(~self.i_b)

        s_p = Signal(self.width)
        m.d.comb += Cat(s_p, self.o_c).eq(s_x + s_y + self.i_c)

        with m.Switch(dec_op.o):
            with m.Case(self.OMux.XpY):
                m.d.comb += self.o_o.eq(s_p)
            with m.Case(self.OMux.Y):
                m.d.comb += self.o_o.eq(s_y)

        # http://teaching.idallen.com/cst8214/08w/notes/overflow.txt
        with m.Switch(Cat(s_x[-1], s_y[-1], self.o_o[-1])):
            with m.Case(0b100):
                m.d.comb += self.o_v.eq(1)
            with m.Case(0b011):
                m.d.comb += self.o_v.eq(1)

        m.d.comb += self.o_z.eq(self.o_o == 0)
        m.d.comb += self.o_s.eq(self.o_o[-1])

        m.d.sync += self.r_o.eq(self.o_o)

        return m

# -------------------------------------------------------------------------------------------------

import argparse
from amaranth import cli


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--type",  choices=["4lut"], default="4lut")
    parser.add_argument("-w", "--width", type=int, default=16)
    cli.main_parser(parser)

    args = parser.parse_args()
    if args.type == "4lut":
        alsru = ALSRU_4LUT(args.width)
        ctrl  = (alsru.op, alsru.dir)

    ports = (
        alsru.a,  alsru.b,  alsru.o,  alsru.r,
        alsru.ci, alsru.co, alsru.vo,
        alsru.si, alsru.so,
        *ctrl
    )
    cli.main_runner(parser, args, alsru, name="alsru", ports=ports)
