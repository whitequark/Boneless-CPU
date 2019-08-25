from nmigen import *

from .control import *
from .decoder import InstructionDecoder


__all__ = ["ProgramCounter", "CondSelector", "ShiftSequencer", "BusArbiter", "CoreFSM"]


class ProgramCounter(Elaboratable):
    def __init__(self, reset):
        self.i_addr = Signal(16)
        self.r_addr = Signal(16, reset=reset)

        self.c_set  = Signal()
        self.c_inc  = Signal()

    def elaborate(self, platform):
        m = Module()

        with m.If(self.c_set):
            m.d.sync += self.r_addr.eq(self.i_addr)
        with m.Elif(self.c_inc):
            m.d.sync += self.r_addr.eq(self.r_addr + 1)

        return m


class CondSelector(Elaboratable):
    Cond = InstructionDecoder.Cond

    def __init__(self):
        self.i_f    = Record([("z", 1), ("s", 1), ("c", 1), ("v", 1)])
        self.c_cond = self.Cond.signal()
        self.o_flag = Signal()

    def elaborate(self, platform):
        m = Module()

        with m.Switch(self.c_cond):
            with m.Case(self.Cond.Z):
                m.d.comb += self.o_flag.eq(self.i_f.z)
            with m.Case(self.Cond.S):
                m.d.comb += self.o_flag.eq(self.i_f.s)
            with m.Case(self.Cond.C):
                m.d.comb += self.o_flag.eq(self.i_f.c)
            with m.Case(self.Cond.V):
                m.d.comb += self.o_flag.eq(self.i_f.v)
            with m.Case(self.Cond.nCoZ):
                m.d.comb += self.o_flag.eq(~self.i_f.c | self.i_f.z)
            with m.Case(self.Cond.SxV):
                m.d.comb += self.o_flag.eq( self.i_f.s ^ self.i_f.v)
            with m.Case(self.Cond.SxVoZ):
                m.d.comb += self.o_flag.eq((self.i_f.s ^ self.i_f.v) | self.i_f.z)
            with m.Case(self.Cond.A):
                m.d.comb += self.o_flag.eq(1)

        return m


class ShiftSequencer(Elaboratable):
    def __init__(self, width=4):
        self.i_shamt = Signal(width)
        self.o_done  = Signal()

        self.c_en    = Signal()
        self.c_load  = Signal()

        self.r_shamt = Signal(width)

    def elaborate(self, platform):
        m = Module()

        s_next = Signal.like(self.r_shamt)
        with m.If(self.c_load):
            m.d.comb += s_next.eq(self.i_shamt)
        with m.Else():
            m.d.comb += s_next.eq(self.r_shamt - 1)

        with m.If(self.c_en):
            m.d.comb += self.o_done.eq(s_next == 0)
            m.d.sync += self.r_shamt.eq(s_next)

        return m


class BusArbiter(Elaboratable):
    class Dir(ControlEnum):
        LD  = 0b0
        ST  = 0b1

    Addr = InstructionDecoder.Addr

    def __init__(self):
        self.i_pc   = Signal(16)
        self.i_w    = Signal(13)
        self.i_ra   = Signal(3)
        self.i_rb   = Signal(3)
        self.i_rsd  = Signal(3)
        self.i_ptr  = Signal(16)
        self.i_data = Signal(16)
        self.o_data = Signal(16)

        self.c_en   = Signal()
        self.c_dir  = self.Dir.signal()
        self.c_addr = self.Addr.signal()
        self.c_pc   = Signal()
        self.c_xbus = Signal()

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

        with m.Switch(self.c_addr):
            with m.Case(self.Addr.IND):
                m.d.comb += self.o_bus_addr.eq(self.i_ptr)
            with m.Case(self.Addr.RA):
                m.d.comb += self.o_bus_addr.eq(Cat(self.i_ra,  self.i_w))
            with m.Case(self.Addr.RB):
                m.d.comb += self.o_bus_addr.eq(Cat(self.i_rb,  self.i_w))
            with m.Case(self.Addr.RSD):
                m.d.comb += self.o_bus_addr.eq(Cat(self.i_rsd, self.i_w))
        with m.If(self.c_pc):
            m.d.comb += self.o_bus_addr.eq(self.i_pc)

        r_xbus = Signal()
        with m.Switch(self.c_dir):
            with m.Case(self.Dir.LD):
                with m.If(self.c_en):
                    m.d.sync += r_xbus.eq(self.c_xbus)
                with m.If(self.c_xbus):
                    m.d.comb += self.o_ext_re.eq(self.c_en)
                with m.Else():
                    m.d.comb += self.o_mem_re.eq(self.c_en)
            with m.Case(self.Dir.ST):
                with m.If(self.c_xbus):
                    m.d.comb += self.o_ext_we.eq(self.c_en)
                with m.Else():
                    m.d.comb += self.o_mem_we.eq(self.c_en)

        m.d.comb += self.o_mem_data.eq(self.i_data)
        m.d.comb += self.o_ext_data.eq(self.i_data)
        m.d.comb += self.o_data.eq(Mux(r_xbus, self.i_ext_data, self.i_mem_data))

        return m


class CoreFSM(Elaboratable):
    def __init__(self, alsru_cls, reset_pc=0, reset_w=0xffff, memory=None):
        self.m_pc    = ProgramCounter(reset_pc)
        self.m_dec   = InstructionDecoder(alsru_cls)
        self.m_csel  = CondSelector()
        self.m_arb   = BusArbiter()
        self.m_alsru = alsru_cls(width=16)
        self.m_shift = ShiftSequencer()

        self.o_pc    = Signal(16)
        self.r_w     = Signal(13, reset=reset_w >> 3)
        self.r_f     = Record([("z", 1), ("s", 1), ("c", 1), ("v", 1)])

        self.r_insn  = Signal(16)
        self.s_base  = Signal(16)
        self.s_a     = Signal(16)
        self.r_a     = Signal(16)
        self.s_b     = Signal(16)

        self.r_cycle = Signal(1)
        self.o_done  = Signal()

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

        m.submodules.pc = m_pc = self.m_pc
        m.d.comb += [
            self.o_pc.eq(m_pc.r_addr),
        ]

        m.submodules.dec = m_dec = self.m_dec
        m.d.comb += [
            m_dec.i_pc.eq(m_pc.r_addr),
            m_dec.c_cycle.eq(self.r_cycle),
        ]

        m.submodules.csel = m_csel = self.m_csel
        m.d.comb += [
            m_csel.i_f.eq(self.r_f),
            m_csel.c_cond.eq(m_dec.o_cond),
        ]

        m.submodules.arb = m_arb = self.m_arb
        m.d.comb += [
            m_arb.i_pc .eq(m_pc.r_addr),
            m_arb.i_w  .eq(self.r_w),
            m_arb.i_ra .eq(m_dec.o_ra),
            m_arb.i_rb .eq(m_dec.o_rb),
            m_arb.i_rsd.eq(m_dec.o_rsd),
            m_arb.i_ptr.eq(self.s_base + m_dec.o_imm16),
        ]

        m.submodules.alsru = m_alsru = self.m_alsru
        m.d.comb += [
            m_alsru.c_op.eq(m_dec.o_op),
            m_alsru.c_dir.eq(m_dec.o_dir),
            m_alsru.i_a.eq(self.r_a),
            m_alsru.i_b.eq(self.s_b),
            m_pc.i_addr.eq(m_alsru.o_o),
            m_arb.i_data.eq(m_alsru.o_o),
        ]
        with m.If(m_dec.o_jcc):
            assert (m_alsru.Op.A | m_alsru.Op.ApB) == m_alsru.Op.ApB
            with m.If(m_dec.o_flag == m_csel.o_flag):
                m.d.comb += m_alsru.c_op.eq(m_dec.o_op | m_alsru.Op.ApB)
        with m.Switch(m_dec.o_ci):
            with m.Case(m_dec.CI.ZERO):
                m.d.comb += m_alsru.i_c.eq(0)
            with m.Case(m_dec.CI.ONE):
                m.d.comb += m_alsru.i_c.eq(1)
            with m.Case(m_dec.CI.FLAG):
                m.d.comb += m_alsru.i_c.eq(self.r_f.c)
        with m.Switch(m_dec.o_si):
            with m.Case(m_dec.SI.ZERO):
                m.d.comb += m_alsru.i_h.eq(0)
            with m.Case(m_dec.SI.MSB):
                m.d.comb += m_alsru.i_h.eq(m_alsru.r_o[-1])

        m.submodules.shift = m_shift = self.m_shift
        m.d.comb += [
            m_shift.i_shamt.eq(self.s_b),
        ]

        dec_ld_a = m_dec.LdA.expand(m, m_dec.o_ld_a)
        with m.Switch(dec_ld_a.mux):
            with m.Case(m_dec.OpAMux.ZERO):
                m.d.comb += self.s_a.eq(0)
            with m.Case(m_dec.OpAMux.PCp1):
                m.d.comb += self.s_a.eq(m_pc.r_addr)
            with m.Case(m_dec.OpAMux.W):
                m.d.comb += self.s_a.eq(self.r_w << 3)
            with m.Case(m_dec.OpAMux.PTR):
                m.d.comb += self.s_a.eq(m_arb.o_data)
        m.d.sync += self.r_a.eq(self.s_a)

        dec_ld_b = m_dec.LdB.expand(m, m_dec.o_ld_b)
        with m.Switch(dec_ld_b.mux):
            with m.Case(m_dec.OpBMux.IMM):
                m.d.comb += self.s_b.eq(m_dec.o_imm16)
            with m.Case(m_dec.OpBMux.PTR):
                m.d.comb += self.s_b.eq(m_arb.o_data)

        dec_st_r = m_dec.StR.expand(m, m_dec.o_st_r)

        with m.FSM():
            m.d.comb += m_dec.i_insn.eq(self.r_insn)
            m.d.comb += self.s_base.eq(self.r_a)

            with m.State("FETCH"):
                m.d.comb += m_pc.c_inc.eq(1)
                m.d.comb += m_dec.c_fetch.eq(1)
                m.d.comb += m_arb.c_pc.eq(1)
                m.d.comb += m_arb.c_en.eq(1)
                m.next = "LOAD-A"

            with m.State("LOAD-A"):
                m.d.sync += self.r_insn.eq(m_arb.o_data)
                m.d.comb += m_dec.i_insn.eq(m_arb.o_data)
                m.d.comb += m_arb.c_addr.eq(dec_ld_a.addr)
                with m.Switch(dec_ld_a.mux):
                    with m.Case(m_dec.OpAMux.PTR):
                        m.d.comb += m_arb.c_en.eq(1)
                m.next = "LOAD-B"

            with m.State("LOAD-B"):
                m.d.comb += self.s_base.eq(self.s_a)
                m.d.comb += m_arb.c_addr.eq(dec_ld_b.addr)
                with m.Switch(dec_ld_b.addr):
                    with m.Case(m_arb.Addr.IND):
                        m.d.comb += m_arb.c_xbus.eq(m_dec.o_xbus)
                with m.Switch(dec_ld_b.mux):
                    with m.Case(m_dec.OpBMux.PTR):
                        m.d.comb += m_arb.c_en.eq(1)
                m.next = "EXECUTE"

            with m.State("EXECUTE"):
                m.d.comb += m_arb.c_dir.eq(m_arb.Dir.ST)
                m.d.comb += m_arb.c_addr.eq(dec_st_r.addr)
                with m.Switch(dec_st_r.addr):
                    with m.Case(m_arb.Addr.IND):
                        m.d.comb += m_arb.c_xbus.eq(m_dec.o_xbus)
                with m.Switch(dec_st_r.mux):
                    with m.Case(m_dec.OpRMux.PTR):
                        m.d.comb += m_arb.c_en.eq(1)
                with m.If(m_dec.o_st_f.zs):
                    m.d.sync += self.r_f.z.eq(m_alsru.o_z)
                    m.d.sync += self.r_f.s.eq(m_alsru.o_s)
                with m.If(m_dec.o_st_f.cv):
                    m.d.sync += self.r_f.c.eq(m_alsru.o_c)
                    m.d.sync += self.r_f.v.eq(m_alsru.o_v)
                with m.If(m_dec.o_st_w):
                    m.d.sync += self.r_w.eq(m_alsru.o_o >> 3)
                with m.If(m_dec.o_shift):
                    m.d.comb += m_shift.c_en.eq(1)
                    m.d.comb += m_shift.c_load.eq(self.r_cycle == 0)
                    m.d.comb += self.o_done.eq(m_shift.o_done)
                with m.Elif(m_dec.o_multi):
                    m.d.comb += self.o_done.eq(self.r_cycle == 1)
                with m.Else():
                    m.d.comb += self.o_done.eq(1)
                with m.If(self.o_done):
                    m.d.comb += m_pc.c_set.eq(m_dec.o_st_pc)
                    m.d.sync += self.r_cycle.eq(0)
                    m.next = "FETCH"
                with m.Else():
                    m.d.sync += self.r_cycle.eq(1)

        return m

# -------------------------------------------------------------------------------------------------

import argparse
from nmigen import cli


if __name__ == "__main__":
    from .alsru import ALSRU_4LUT

    parser = argparse.ArgumentParser()
    parser.add_argument("type", choices=[
        "cond-selector", "bus-arbiter",
        "core-fsm", "core-fsm+memory"
    ])
    cli.main_parser(parser)

    args = parser.parse_args()

    if args.type == "cond-selector":
        dut = CondSelector()
        ports = (
            dut.i_f.z, dut.i_f.s, dut.i_f.c, dut.i_f.v,
            dut.c_cond,
            dut.o_flag
        )

    if args.type == "bus-arbiter":
        dut = BusArbiter()
        ports = (
            dut.i_pc, dut.i_w, dut.i_ra, dut.i_rb, dut.i_rsd, dut.i_ptr,
            dut.i_data, dut.o_data,
            dut.c_op.addr, dut.c_op.reg, dut.c_op.op,
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
        dut = CoreFSM(alsru_cls=ALSRU_4LUT, memory=memory)
        ports = (
            dut.o_bus_addr,
            dut.i_ext_data, dut.o_ext_re, dut.o_ext_data, dut.o_ext_we,
        )

    cli.main_runner(parser, args, dut, ports=ports)
