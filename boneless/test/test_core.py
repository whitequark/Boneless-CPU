import unittest
from amaranth import *
from amaranth.lib import memory
from amaranth.sim import *

from ..arch.opcode import Instr
from ..gateware.core import CoreFSM
from .smoke import SmokeTestCase


class CoreTestbench(Elaboratable):
    def __init__(self):
        self.sync = ClockDomain("sync")
        self.mem = memory.MemoryData(shape=16, depth=32, init=[])
        self.ext = memory.MemoryData(shape=16, depth=32, init=[])
        self.dut = CoreFSM(mem_data=self.mem, reset_w=0, reset_pc=8)
        self.rst = Signal(init=1)

    def elaborate(self, platform):
        m = Module()
        m.domains.sync = self.sync
        m.submodules.dut = self.dut
        m.submodules.mem = mem = memory.Memory(self.mem)
        m.submodules.ext = ext = memory.Memory(self.ext)
        m_extrd = ext.read_port()
        m_extwr = ext.write_port()
        m.d.comb += [
            m_extrd.addr.eq(self.dut.o_bus_addr),
            self.dut.i_ext_data.eq(m_extrd.data),
            m_extrd.en.eq(self.dut.o_ext_re),
            m_extwr.addr.eq(self.dut.o_bus_addr),
            m_extwr.data.eq(self.dut.o_ext_data),
            m_extwr.en.eq(self.dut.o_ext_we),
        ]
        return m


class CoreSmokeTestCase(SmokeTestCase, unittest.TestCase):
    def setUp(self):
        self.tb = CoreTestbench()

    def run_simulator(self, case):
        dut = self.tb.dut
        frag = Fragment.get(self.tb, platform=None)
        sim = Simulator(frag)
        sim.add_clock(1e-6)
        sim.add_sync_process(lambda: (yield from case(self)))
        traces = (
            dut.o_pc, dut.r_w, dut.m_dec.i_insn, frag.find_generated("dut", "fsm").state,
            dut.r_cycle, dut.o_done,
        )
        with sim.write_vcd(f"{case.__name__}.vcd", f"{case.__name__}.gtkw", traces=traces):
            sim.run()

    def execute(self, code, regs=[], data=[], extr=[], flags="", limit=None):
        code = Instr.assemble(code)
        if limit is None:
            limit = len(code)
        yield self.tb.sync.rst.eq(1)
        yield
        yield self.tb.sync.rst.eq(0)
        yield Settle()
        for addr, word in enumerate([*regs, *[0] * (8 - len(regs)), *code, *data]):
            yield self.tb.mem[addr].eq(word)
        for addr, word in enumerate(extr):
            yield self.tb.ext[addr].eq(word)
        for flag in flags:
            yield self.tb.dut.r_f[flag].eq(1)
        for cycle in range(limit):
            while not (yield self.tb.dut.o_done):
                yield
            yield

    def assertF(self, flags):
        for flag in "zscv":
            self.assertEqual((yield self.tb.dut.r_f[flag]), flag in flags, msg=f"F.{flag}")

    def assertW(self, win):
        self.assertEqual((yield self.tb.dut.r_w) << 3, win, msg=f"W")

    def assertPC(self, addr):
        self.assertEqual((yield self.tb.dut.o_pc), addr, msg=f"PC")

    def assertMemory(self, addr, value):
        self.assertEqual((yield self.tb.mem[addr]), value, msg=f"M[{addr}]")

    def assertExternal(self, addr, value):
        self.assertEqual((yield self.tb.ext[addr]), value, msg=f"X[{addr}]")
