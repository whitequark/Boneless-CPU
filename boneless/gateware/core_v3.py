from nmigen import *

from .decoder_v3 import InstructionDecoder


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
            ("op",   3),
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


class CoreFSM(Elaboratable):
    def __init__(self, alsru_cls, memory=None):
        self.r_pc    = Signal(16)
        self.r_w     = Signal(13)
        self.r_f     = Record([("z", 1), ("s", 1), ("c", 1), ("v", 1)])

        self.r_insn  = Signal(16)
        self.r_a     = Signal(16)
        self.s_b     = Signal(16)
        self.s_f     = Record(self.r_f.layout)

        self.m_dec   = InstructionDecoder(alsru_cls)
        self.m_arb   = BusArbiter()
        self.m_alsru = alsru_cls(width=16)

        self.o_bus_addr = self.m_arb.o_bus_addr

        self.i_mem_data = self.m_arb.i_mem_data
        self.o_mem_re   = self.m_arb.o_mem_re
        self.o_mem_data = self.m_arb.o_mem_data
        self.o_mem_we   = self.m_arb.o_mem_we

        self.i_ext_data = self.m_arb.i_ext_data
        self.o_ext_re   = self.m_arb.o_ext_re
        self.o_ext_data = self.m_arb.o_ext_data
        self.o_ext_we   = self.m_arb.o_ext_we

        self.memory  = memory

    def elaborate(self, platform):
        m = Module()

        if self.memory is not None:
            m.submodules.memrd = m_memrd = self.memory.read_port(transparent=False)
            m.submodules.memwr = m_memwr = self.memory.write_port()
            m.d.comb += [
                m_memrd.addr.eq(self.o_bus_addr),
                self.i_mem_data.eq(m_memrd.data),
                m_memrd.en.eq(self.o_mem_re),
                m_memwr.addr.eq(self.o_bus_addr),
                m_memwr.data.eq(self.o_mem_data),
                m_memwr.en.eq(self.o_mem_we),
            ]

        m.submodules.dec = m_dec = self.m_dec
        m.d.comb += [
            m_dec.i_pc.eq(self.r_pc),
        ]

        m.submodules.arb = m_arb = self.m_arb
        m.d.comb += [
            m_arb.i_pc.eq(self.r_pc),
            m_arb.i_w .eq(self.r_w),
            m_arb.i_rsd.eq(m_dec.o_rsd),
            m_arb.i_ra .eq(m_dec.o_ra),
            m_arb.i_rb .eq(m_dec.o_rb),
            m_arb.i_ptr.eq(m_dec.o_imm16 + self.r_a),
        ]

        m.submodules.alsru = m_alsru = self.m_alsru
        m.d.comb += [
            m_alsru.a.eq(self.r_a),
            m_alsru.b.eq(self.s_b),
            m_alsru.op.eq(m_dec.o_op),
            m_arb.i_data.eq(m_alsru.o),
            self.s_f.z.eq(m_alsru.o == 0),
            self.s_f.s.eq(m_alsru.o[-1]),
            self.s_f.c.eq(m_alsru.co),
            self.s_f.v.eq(m_alsru.vo),
        ]
        with m.Switch(m_dec.o_ci):
            with m.Case(m_dec.CTRL_CI_ZERO):
                m.d.comb += m_alsru.ci.eq(0)
            with m.Case(m_dec.CTRL_CI_ONE):
                m.d.comb += m_alsru.ci.eq(1)
            with m.Case(m_dec.CTRL_CI_FLAG):
                m.d.comb += m_alsru.ci.eq(self.r_f.c)
        with m.Switch(m_dec.o_si):
            with m.Case(m_dec.CTRL_SI_ZERO):
                m.d.comb += m_alsru.si.eq(0)
            with m.Case(m_dec.CTRL_SI_MSB):
                m.d.comb += m_alsru.si.eq(m_alsru.r[-1])

        with m.FSM():
            m.d.comb += m_dec.i_insn.eq(self.r_insn)

            with m.State("FETCH"):
                m.d.sync += self.r_pc.eq(m_dec.o_pc_p1)
                m.d.comb += m_arb.c_mode.eq(m_arb.CTRL_LD_PC)
                m.next = "LOAD-A"

            with m.State("LOAD-A"):
                m.d.sync += self.r_insn.eq(m_arb.o_data)
                m.d.comb += m_dec.i_insn.eq(m_arb.o_data)
                with m.Switch(m_dec.o_ld_a):
                    with m.Case(m_dec.CTRL_LD_A_RA):
                        m.d.comb += m_arb.c_mode.eq(m_arb.CTRL_LD_RA)
                m.next = "LOAD-B"

            with m.State("LOAD-B"):
                with m.Switch(m_dec.o_ld_a):
                    with m.Case(m_dec.CTRL_LD_A_0):
                        m.d.sync += self.r_a.eq(0)
                    with m.Case(m_dec.CTRL_LD_A_W):
                        m.d.sync += self.r_a.eq(self.r_w << 3)
                    with m.Case(m_dec.CTRL_LD_A_PCp1):
                        m.d.sync += self.r_a.eq(self.r_pc)
                    with m.Case(m_dec.CTRL_LD_A_RA):
                        m.d.sync += self.r_a.eq(m_arb.o_data)
                with m.Switch(m_dec.o_ld_b):
                    with m.Case(m_dec.CTRL_LD_B_ApI):
                        m.d.comb += m_arb.c_mode.eq(
                            Mux(m_dec.o_xbus, m_arb.CTRL_LD_EXT, m_arb.CTRL_LD_MEM))
                    with m.Case(m_dec.CTRL_LD_B_RSD):
                        m.d.comb += m_arb.c_mode.eq(m_arb.CTRL_LD_RSD)
                    with m.Case(m_dec.CTRL_LD_B_RB):
                        m.d.comb += m_arb.c_mode.eq(m_arb.CTRL_LD_RB)
                m.next = "EXECUTE"

            with m.State("EXECUTE"):
                with m.Switch(m_dec.o_ld_b):
                    with m.Case(m_dec.CTRL_LD_B_IMM):
                        m.d.comb += self.s_b.eq(m_dec.o_imm16)
                    with m.Case(m_dec.CTRL_LD_B_ApI, m_dec.CTRL_LD_B_RSD, m_dec.CTRL_LD_B_RB):
                        m.d.comb += self.s_b.eq(m_arb.o_data)
                with m.Switch(m_dec.o_st_r):
                    with m.Case(m_dec.CTRL_ST_R_ApI):
                        m.d.comb += m_arb.c_mode.eq(
                            Mux(m_dec.o_xbus, m_arb.CTRL_ST_EXT, m_arb.CTRL_ST_MEM))
                    with m.Case(m_dec.CTRL_ST_R_RSD):
                        m.d.comb += m_arb.c_mode.eq(m_arb.CTRL_ST_RSD)
                with m.Switch(m_dec.o_st_f):
                    with m.Case(m_dec.CTRL_ST_F_ZS):
                        m.d.sync += self.r_f["z","s"]        .eq(self.s_f["z","s"])
                    with m.Case(m_dec.CTRL_ST_F_ZSCV):
                        m.d.sync += self.r_f["z","s","c","v"].eq(self.s_f["z","s","c","v"])
                with m.If(m_dec.o_wind):
                    m.d.sync += self.r_w .eq(m_alsru.o >> 3)
                with m.If(m_dec.o_jump):
                    m.d.sync += self.r_pc.eq(m_alsru.o)
                m.next = "FETCH"

        return m

# -------------------------------------------------------------------------------------------------

import argparse
from nmigen import cli


if __name__ == "__main__":
    from .alsru import ALSRU_4LUT

    parser = argparse.ArgumentParser()
    parser.add_argument("type", choices=["bus-arbiter", "core-fsm", "core-fsm+memory"])
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

    if args.type == "core-fsm":
        dut = CoreFSM(alsru_cls=ALSRU_4LUT)
        ports = (
            dut.o_bus_addr,
            dut.i_mem_data, dut.o_mem_re, dut.o_mem_data, dut.o_mem_we,
            dut.i_ext_data, dut.o_ext_re, dut.o_ext_data, dut.o_ext_we,
        )

    if args.type == "core-fsm+memory":
        memory = Memory(width=16, depth=256)
        memory.init = [0b10000_111_10101010] # MOVI R7, 0xAA
        dut = CoreFSM(alsru_cls=ALSRU_4LUT, memory=memory)
        ports = (
            dut.o_bus_addr,
            dut.i_ext_data, dut.o_ext_re, dut.o_ext_data, dut.o_ext_we,
        )

    cli.main_runner(parser, args, dut, ports=ports)
