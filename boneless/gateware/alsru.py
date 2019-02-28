from nmigen import *


__all__ = ["ALSRU", "ALSRU_4LUT"]


class ALSRU:
    """Arithmetical, logical, shift, and rotate unit."""

    # defined by subclasses
    CTRL_BITS = None

    CTRL_A    = None
    CTRL_B    = None
    CTRL_nB   = None
    CTRL_AaB  = None
    CTRL_AoB  = None
    CTRL_AxB  = None
    CTRL_ApB  = None
    CTRL_AmB  = None
    CTRL_SL   = None
    CTRL_SR   = None

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

        self.ctrl = None  # defined by subclasses

    @classmethod
    def ctrl_decoder(cls, word):
        if word == cls.CTRL_A._as_const():
            return "A"
        if word == cls.CTRL_B._as_const():
            return "B"
        if word == cls.CTRL_nB._as_const():
            return "~B"
        if word == cls.CTRL_AaB._as_const():
            return "A&B"
        if word == cls.CTRL_AoB._as_const():
            return "A|B"
        if word == cls.CTRL_AxB._as_const():
            return "A^B"
        if word == cls.CTRL_ApB._as_const():
            return "A+B"
        if word == cls.CTRL_AmB._as_const():
            return "A-B"
        if word == cls.CTRL_SL._as_const():
            return "R<<1"
        if word == cls.CTRL_SR._as_const():
            return "R>>1"
        return "? {:0{}b}".format(word, cls.CTRL_BITS)


class ALSRU_4LUT(ALSRU):
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

    MUX_S_x   = 0
    MUX_S_L   = 0b0
    MUX_S_R   = 0b1

    MUX_X_x   =  0
    MUX_X_AaB =  0b00
    MUX_X_AoB =  0b01
    MUX_X_AxB =  0b10
    MUX_X_A   =  0b11

    MUX_Y_0   =    0b00
    MUX_Y_S   =    0b01
    MUX_Y_B   =    0b10
    MUX_Y_nB  =    0b11

    MUX_O_XpY =      0b0
    MUX_O_Y   =      0b1

    CTRL_BITS = 6

    CTRL_A    = Cat(C(MUX_S_x, 1), C(MUX_X_A,   2), C(MUX_Y_0,  2), C(MUX_O_XpY, 1))
    CTRL_B    = Cat(C(MUX_S_x, 1), C(MUX_X_x,   2), C(MUX_Y_B,  2), C(MUX_O_Y,   1))
    CTRL_nB   = Cat(C(MUX_S_x, 1), C(MUX_X_x,   2), C(MUX_Y_nB, 2), C(MUX_O_Y,   1))
    CTRL_AaB  = Cat(C(MUX_S_x, 1), C(MUX_X_AaB, 2), C(MUX_Y_0,  2), C(MUX_O_XpY, 1))
    CTRL_AoB  = Cat(C(MUX_S_x, 1), C(MUX_X_AoB, 2), C(MUX_Y_0,  2), C(MUX_O_XpY, 1))
    CTRL_AxB  = Cat(C(MUX_S_x, 1), C(MUX_X_AxB, 2), C(MUX_Y_0,  2), C(MUX_O_XpY, 1))
    CTRL_ApB  = Cat(C(MUX_S_x, 1), C(MUX_X_A,   2), C(MUX_Y_B,  2), C(MUX_O_XpY, 1))
    CTRL_AmB  = Cat(C(MUX_S_x, 1), C(MUX_X_A,   2), C(MUX_Y_nB, 2), C(MUX_O_XpY, 1))
    CTRL_SL   = Cat(C(MUX_S_L, 1), C(MUX_X_x,   2), C(MUX_Y_S,  2), C(MUX_O_Y,   1))
    CTRL_SR   = Cat(C(MUX_S_R, 1), C(MUX_X_x,   2), C(MUX_Y_S,  2), C(MUX_O_Y,   1))

    def __init__(self, width):
        super().__init__(width)

        self.s = Signal(width)
        self.x = Signal(width)
        self.y = Signal(width)

        self.ctrl = Record([
            ("s", 1),
            ("x", 2),
            ("y", 2),
            ("o", 1),
        ])

    def elaborate(self, platform):
        m = Module()

        with m.Switch(self.ctrl.s):
            with m.Case(self.MUX_S_L):
                m.d.comb += self.s.eq(Cat(self.si, self.r[:-1]))
                m.d.comb += self.so.eq(self.r[-1])
            with m.Case(self.MUX_S_R):
                m.d.comb += self.s.eq(Cat(self.r[ 1:], self.si))
                m.d.comb += self.so.eq(self.r[ 0])

        with m.Switch(self.ctrl.x):
            with m.Case(self.MUX_X_AaB):
                m.d.comb += self.x.eq(self.a & self.b)
            with m.Case(self.MUX_X_AoB):
                m.d.comb += self.x.eq(self.a | self.b)
            with m.Case(self.MUX_X_AxB):
                m.d.comb += self.x.eq(self.a ^ self.b)
            with m.Case(self.MUX_X_A):
                m.d.comb += self.x.eq(self.a)

        with m.Switch(self.ctrl.y):
            with m.Case(self.MUX_Y_0):
                m.d.comb += self.y.eq(0)
            with m.Case(self.MUX_Y_S):
                m.d.comb += self.y.eq(self.s)
            with m.Case(self.MUX_Y_B):
                m.d.comb += self.y.eq(self.b)
            with m.Case(self.MUX_Y_nB):
                m.d.comb += self.y.eq(~self.b)

        p = Signal.like(self.o)
        m.d.comb += Cat(p, self.co).eq(self.x + self.y + self.ci)

        with m.Switch(self.ctrl.o):
            with m.Case(self.MUX_O_XpY):
                m.d.comb += self.o.eq(p)
            with m.Case(self.MUX_O_Y):
                m.d.comb += self.o.eq(self.y)

        # http://teaching.idallen.com/cst8214/08w/notes/overflow.txt
        with m.Switch(Cat(self.x[-1], self.y[-1], self.o[-1])):
            with m.Case(0b100):
                m.d.comb += self.vo.eq(1)
            with m.Case(0b011):
                m.d.comb += self.vo.eq(1)

        m.d.sync += self.r.eq(self.o)

        return m.lower(platform)

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
