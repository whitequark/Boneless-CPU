from amaranth import *
from amaranth.lib import enum, data, wiring
from amaranth.lib.wiring import In, Out


__all__ = ["ALSRU"]


class _XMux(enum.Enum, shape=2):
    A   = 0b00
    AaB = 0b01
    AoB = 0b10
    AxB = 0b11
    x   = 0


class _YMux(enum.Enum, shape=2):
    Z   = 0b00
    S   = 0b01
    B   = 0b10
    nB  = 0b11


class _OMux(enum.Enum, shape=1):
    XpY = 0b0
    Y   = 0b1


class _OpWord(data.Struct):
    x: _XMux
    y: _YMux
    o: _OMux


class ALSRU(wiring.Component):
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

    class Op(enum.IntEnum, shape=5):
        A   = Cat(_XMux.A,   _YMux.Z,  _OMux.XpY,)
        B   = Cat(_XMux.x,   _YMux.B,  _OMux.Y,  )
        nB  = Cat(_XMux.x,   _YMux.nB, _OMux.Y,  )
        AaB = Cat(_XMux.AaB, _YMux.Z,  _OMux.XpY,)
        AoB = Cat(_XMux.AoB, _YMux.Z,  _OMux.XpY,)
        AxB = Cat(_XMux.AxB, _YMux.Z,  _OMux.XpY,)
        ApB = Cat(_XMux.A,   _YMux.B,  _OMux.XpY,)
        AmB = Cat(_XMux.A,   _YMux.nB, _OMux.XpY,)
        SLR = Cat(_XMux.x,   _YMux.S,  _OMux.Y,  )

    class Dir(enum.Enum, shape=1):
        L   = 0b0
        R   = 0b1

    def __init__(self, width):
        self.width = width

        super().__init__({
            "i_a":   In(width),
            "i_b":   In(width),
            "i_c":   In(1),
            "o_o":   Out(width),

            "o_z":   Out(1), # zero out
            "o_s":   Out(1), # sign out
            "o_c":   Out(1), # carry out
            "o_v":   Out(1), # overflow out

            "c_op":  In(self.Op),

            "i_h":   In(1), # shift in
            "o_h":   Out(1), # shift out

            "c_dir": In(self.Dir),
        })

        self.r_o = Signal(width)

    def elaborate(self, platform):
        m = Module()

        dec_op = Signal(_OpWord)
        m.d.comb += dec_op.eq(self.c_op)

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
            with m.Case(_XMux.AaB):
                m.d.comb += s_x.eq(self.i_a & self.i_b)
            with m.Case(_XMux.AoB):
                m.d.comb += s_x.eq(self.i_a | self.i_b)
            with m.Case(_XMux.AxB):
                m.d.comb += s_x.eq(self.i_a ^ self.i_b)
            with m.Case(_XMux.A):
                m.d.comb += s_x.eq(self.i_a)

        s_y = Signal(self.width)
        with m.Switch(dec_op.y):
            with m.Case(_YMux.Z):
                m.d.comb += s_y.eq(0)
            with m.Case(_YMux.S):
                m.d.comb += s_y.eq(s_s)
            with m.Case(_YMux.B):
                m.d.comb += s_y.eq(self.i_b)
            with m.Case(_YMux.nB):
                m.d.comb += s_y.eq(~self.i_b)

        s_p = Signal(self.width)
        m.d.comb += Cat(s_p, self.o_c).eq(s_x + s_y + self.i_c)

        with m.Switch(dec_op.o):
            with m.Case(_OMux.XpY):
                m.d.comb += self.o_o.eq(s_p)
            with m.Case(_OMux.Y):
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
    parser.add_argument("-w", "--width", type=int, default=16)
    cli.main_parser(parser)

    args  = parser.parse_args()
    alsru = ALSRU(args.width)
    cli.main_runner(parser, args, alsru, name="alsru")
