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
    #                        CO         O       SLn+1
    #                        |   A-|‾\  |  ___    |
    #                     A-|‾\    |4 |-·-|D Q|-R-·
    #              B-|‾\    |3 |-Y-|_/    |>  |   |
    #   SRn+1-|‾\    |2 |-X-|_/            ‾‾‾  SRn-1
    #         |1 |-S-|_/     |
    #   SLn-1-|_/            CI
    #
    # LUT 1 computes: R<<1, R>>1
    # LUT 2 computes: 0, S, ~B, B
    # LUT 3 computes: A+X, X
    # LUT 4 computes: A&Y, A|Y, A^Y, Y
    #
    # To compute:
    #      A:          X=0    Y=A+X O=Y
    #      B:          X=B    Y=X   O=Y
    #     ~B:          X=~B   Y=X   O=Y
    #    A&B:          X=B    Y=X   O=A&Y
    #    A|B:          X=B    Y=X   O=A|Y
    #    A^B:          X=B    Y=X   O=A^Y
    #    A+B:          X=B    Y=A+X O=Y
    #    A-B:          X=~B   Y=A+X O=Y    (pre-invert CI)
    #   R<<1: S=SLn-1  X=S    Y=X   O=Y    (pre-load R)
    #   R>>1: S=SRn+1  X=S    Y=X   O=Y    (pre-load R)

    class MuxS(ControlEnum):
        L   = 0b0
        R   = 0b1
        x   = 0

    class MuxX(ControlEnum):
        Z   = 0b00
        S   = 0b01
        nB  = 0b11
        B   = 0b10

    class MuxY(ControlEnum):
        ApX = 0b0
        X   = 0b1

    class MuxO(ControlEnum):
        AaY = 0b00
        AoY = 0b01
        AxY = 0b10
        Y   = 0b11
        x   = 0

    class Op(MultiControlEnum, layout={"s":MuxS, "x":MuxX, "y":MuxY, "o":MuxO}):
        A    = ("x", "Z",   "ApX", "Y",  )
        B    = ("x", "B",   "X",   "Y",  )
        nB   = ("x", "nB",  "X",   "Y",  )
        AaB  = ("x", "B",   "X",   "AaY",)
        AoB  = ("x", "B",   "X",   "AoY",)
        AxB  = ("x", "B",   "X",   "AxY",)
        ApB  = ("x", "B",   "ApX", "Y",  )
        AmB  = ("x", "nB",  "ApX", "Y",  )
        SL   = ("L", "S",   "X",   "Y",  )
        SR   = ("R", "S",   "X",   "Y",  )

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
            with m.Case(self.MuxX.Z):
                m.d.comb += x.eq(0)
            with m.Case(self.MuxX.S):
                m.d.comb += x.eq(s)
            with m.Case(self.MuxX.nB):
                m.d.comb += x.eq(~self.b)
            with m.Case(self.MuxX.B):
                m.d.comb += x.eq(self.b)

        p = Signal.like(self.o)
        m.d.comb += Cat(p, self.co).eq(self.a + x + self.ci)

        # http://teaching.idallen.com/cst8214/08w/notes/overflow.txt
        with m.Switch(Cat(self.a[-1], x[-1], p[-1])):
            with m.Case(0b100):
                m.d.comb += self.vo.eq(1)
            with m.Case(0b011):
                m.d.comb += self.vo.eq(1)

        y = Signal.like(self.o)
        with m.Switch(op.y):
            with m.Case(self.MuxY.ApX):
                m.d.comb += y.eq(p)
            with m.Case(self.MuxY.X):
                m.d.comb += y.eq(x)

        with m.Switch(op.o):
            with m.Case(self.MuxO.AaY):
                m.d.comb += self.o.eq(self.a & y)
            with m.Case(self.MuxO.AoY):
                m.d.comb += self.o.eq(self.a | y)
            with m.Case(self.MuxO.AxY):
                m.d.comb += self.o.eq(self.a ^ y)
            with m.Case(self.MuxO.Y):
                m.d.comb += self.o.eq(y)

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
