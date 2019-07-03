from nmigen import *

from .control import *


__all__ = ["ALSRU", "ALSRU_4LUT"]


class ALSRU:
    """Arithmetical, logical, shift, and rotate unit."""

    # redefined by subclasses
    class Op(MultiControlEnum):
        A    = ()
        B    = ()
        nB   = ()
        AaB  = ()
        AoB  = ()
        AxB  = ()
        ApB  = ()
        AmB  = ()
        SL   = ()
        SR   = ()

    def __init__(self, width):
        self.a  = Signal(width)
        self.b  = Signal(width)
        self.o  = Signal(width)
        self.r  = Signal(width)

        self.ci = Signal() # carry in
        self.co = Signal() # carry out
        self.vo = Signal() # overflow out

        self.si = Signal() # shift in
        self.so = Signal() # shift out

        self.op = self.Op.signal() # redefined by subclasses


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

    class MuxS(ControlEnum):
        L   = 0b0
        R   = 0b1
        x   = 0

    class MuxX(ControlEnum):
        A   = 0b00
        AaB = 0b01
        AoB = 0b10
        AxB = 0b11
        x   = 0

    class MuxY(ControlEnum):
        Z   = 0b00
        S   = 0b01
        B   = 0b10
        nB  = 0b11

    class MuxO(ControlEnum):
        XpY = 0b0
        Y   = 0b1

    class Op(MultiControlEnum, layout={"s":MuxS, "x":MuxX, "y":MuxY, "o":MuxO}):
        A    = ("x", "A",   "Z",  "XpY",)
        B    = ("x", "x",   "B",  "Y",  )
        nB   = ("x", "x",   "nB", "Y",  )
        AaB  = ("x", "AaB", "Z",  "XpY",)
        AoB  = ("x", "AoB", "Z",  "XpY",)
        AxB  = ("x", "AxB", "Z",  "XpY",)
        ApB  = ("x", "A",   "B",  "XpY",)
        AmB  = ("x", "A",   "nB", "XpY",)
        SL   = ("L", "x",   "S",  "Y",  )
        SR   = ("R", "x",   "S",  "Y",  )

    def elaborate(self, platform):
        m = Module()

        op = self.Op.expand(m, self.op)

        s = Signal.like(self.o)
        with m.Switch(op.s):
            with m.Case(self.MuxS.L):
                m.d.comb += s.eq(Cat(self.si, self.r[:-1]))
                m.d.comb += self.so.eq(self.r[-1])
            with m.Case(self.MuxS.R):
                m.d.comb += s.eq(Cat(self.r[ 1:], self.si))
                m.d.comb += self.so.eq(self.r[ 0])

        x = Signal.like(self.o)
        with m.Switch(op.x):
            with m.Case(self.MuxX.AaB):
                m.d.comb += x.eq(self.a & self.b)
            with m.Case(self.MuxX.AoB):
                m.d.comb += x.eq(self.a | self.b)
            with m.Case(self.MuxX.AxB):
                m.d.comb += x.eq(self.a ^ self.b)
            with m.Case(self.MuxX.A):
                m.d.comb += x.eq(self.a)

        y = Signal.like(self.o)
        with m.Switch(op.y):
            with m.Case(self.MuxY.Z):
                m.d.comb += y.eq(0)
            with m.Case(self.MuxY.S):
                m.d.comb += y.eq(s)
            with m.Case(self.MuxY.B):
                m.d.comb += y.eq(self.b)
            with m.Case(self.MuxY.nB):
                m.d.comb += y.eq(~self.b)

        p = Signal.like(self.o)
        m.d.comb += Cat(p, self.co).eq(x + y + self.ci)

        with m.Switch(op.o):
            with m.Case(self.MuxO.XpY):
                m.d.comb += self.o.eq(p)
            with m.Case(self.MuxO.Y):
                m.d.comb += self.o.eq(y)

        # http://teaching.idallen.com/cst8214/08w/notes/overflow.txt
        with m.Switch(Cat(x[-1], y[-1], self.o[-1])):
            with m.Case(0b100):
                m.d.comb += self.vo.eq(1)
            with m.Case(0b011):
                m.d.comb += self.vo.eq(1)

        m.d.sync += self.r.eq(self.o)

        return m

# -------------------------------------------------------------------------------------------------

import argparse
from nmigen import cli


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--type",  choices=["4lut"], default="4lut")
    parser.add_argument("-w", "--width", type=int, default=16)
    cli.main_parser(parser)

    args = parser.parse_args()
    if args.type == "4lut":
        alsru = ALSRU_4LUT(args.width)
        ctrl  = (alsru.ctrl.s, alsru.ctrl.x, alsru.ctrl.y, alsru.ctrl.o)

    ports = (
        alsru.a,  alsru.b,  alsru.o,  alsru.r,
        alsru.ci, alsru.co, alsru.vo,
        alsru.si, alsru.so,
        *ctrl
    )
    cli.main_runner(parser, args, alsru, name="alsru", ports=ports)
