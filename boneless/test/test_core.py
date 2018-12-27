import unittest
import functools
from nmigen import *
from nmigen.back.pysim import *

from ..arch.instr import *
from ..gateware.core_fsm import BonelessCoreFSM, _ExternalPort


def simulation_test(**kwargs):
    def configure_wrapper(case):
        @functools.wraps(case)
        def wrapper(self):
            self.configure(self.tb, **kwargs)
            with Simulator(self.tb) as sim:
                sim.add_clock(1e-6)
                sim.add_sync_process(case(self, self.tb))
                sim.run()
        return wrapper
    return configure_wrapper


class BonelessSimulationTestbench(Module):
    def __init__(self):
        self.mem_init = []
        self.ext_init = []

    def get_fragment(self, platform):
        m = Module()

        mem = self.mem = Memory(width=16, depth=len(self.mem_init), init=self.mem_init)
        m.submodules.mem_rdport = mem_rdport = mem.read_port(transparent=False)
        m.submodules.mem_wrport = mem_wrport = mem.write_port()

        if self.ext_init:
            ext = self.ext = Memory(width=16, depth=len(self.ext_init), init=self.ext_init)
            m.submodules.ext_rdport = ext_rdport = ext.read_port(transparent=False)
            m.submodules.ext_wrport = ext_wrport = ext.write_port()

            ext_port = _ExternalPort()
            m.d.comb += [
                ext_rdport.addr.eq(ext_port.addr),
                ext_port.r_data.eq(ext_rdport.data),
                ext_rdport.en.eq(ext_port.r_en),
                ext_wrport.addr.eq(ext_port.addr),
                ext_wrport.data.eq(ext_port.w_data),
                ext_wrport.en.eq(ext_port.w_en),
            ]
        else:
            ext_port = None

        m.submodules.dut = self.dut = BonelessCoreFSM(reset_addr=8,
            mem_rdport=mem_rdport,
            mem_wrport=mem_wrport,
            ext_port  =ext_port)

        return m.lower(platform)


class BonelessTestCase(unittest.TestCase):
    def setUp(self):
        self.tb = BonelessSimulationTestbench()

    def configure(self, tb, code, regs=[], data=[], extr=[]):
        tb.mem_init = [*regs, *[0] * (8 - len(regs))] + assemble(code + [J(-1)] + data)
        tb.ext_init = extr

    def run_core(self, tb):
        while not (yield tb.dut.halted):
            yield

    def assertMemory(self, tb, addr, value):
        self.assertEqual((yield tb.mem[addr]), value)

    def assertExternal(self, tb, addr, value):
        self.assertEqual((yield tb.ext[addr]), value)

    @simulation_test(regs=[0xA5A5, 0xAA55],
                     code=[AND (R2, R1, R0)])
    def test_AND(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0xA5A5)
        yield from self.assertMemory(tb, 1, 0xAA55)
        yield from self.assertMemory(tb, 2, 0xA005)

    @simulation_test(regs=[0xA5A5, 0xAA55],
                     code=[OR  (R2, R1, R0)])
    def test_OR(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0xA5A5)
        yield from self.assertMemory(tb, 1, 0xAA55)
        yield from self.assertMemory(tb, 2, 0xAFF5)

    @simulation_test(regs=[0xA5A5, 0xAA55],
                     code=[XOR (R2, R1, R0)])
    def test_XOR(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0xA5A5)
        yield from self.assertMemory(tb, 1, 0xAA55)
        yield from self.assertMemory(tb, 2, 0x0FF0)

    @simulation_test(regs=[0x1234, 0x5678],
                     code=[ADD (R2, R0, R1)])
    def test_ADD(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x1234)
        yield from self.assertMemory(tb, 1, 0x5678)
        yield from self.assertMemory(tb, 2, 0x68AC)

    @simulation_test(regs=[0x1234, 0x5678],
                     code=[SUB (R2, R0, R1)])
    def test_SUB(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x1234)
        yield from self.assertMemory(tb, 1, 0x5678)
        yield from self.assertMemory(tb, 2, 0xBBBC)

    @simulation_test(regs=[0x1234, 0x5678],
                     code=[CMP (R0, R1)])
    def test_CMP(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x1234)
        yield from self.assertMemory(tb, 1, 0x5678)
        yield from self.assertMemory(tb, 2, 0)

    @simulation_test(regs=[0x1012],
                     code=[SLL (R1, R0, 1),
                           SLL (R2, R0, 8)])
    def test_SLL(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x1012)
        yield from self.assertMemory(tb, 1, 0x2024)
        yield from self.assertMemory(tb, 2, 0x1200)

    @simulation_test(regs=[0x1012],
                     code=[ROT (R1, R0, 1),
                           ROT (R2, R0, 8)])
    def test_ROT(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x1012)
        yield from self.assertMemory(tb, 1, 0x2024)
        yield from self.assertMemory(tb, 2, 0x1210)

    @simulation_test(regs=[0x1234],
                     code=[MOV (R1, R0)])
    def test_MOV(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x1234)
        yield from self.assertMemory(tb, 1, 0x1234)

    @simulation_test(regs=[0x1210, 0x9210],
                     code=[SRL (R2, R0, 1),
                           SRL (R3, R0, 8),
                           SRL (R4, R1, 1),
                           SRL (R5, R1, 8)])
    def test_SRL(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x1210)
        yield from self.assertMemory(tb, 2, 0x0908)
        yield from self.assertMemory(tb, 3, 0x0012)
        yield from self.assertMemory(tb, 1, 0x9210)
        yield from self.assertMemory(tb, 4, 0x4908)
        yield from self.assertMemory(tb, 5, 0x0092)

    @simulation_test(regs=[0x1210, 0x9210],
                     code=[SRA (R2, R0, 1),
                           SRA (R3, R0, 8),
                           SRA (R4, R1, 1),
                           SRA (R5, R1, 8)])
    def test_SRA(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x1210)
        yield from self.assertMemory(tb, 2, 0x0908)
        yield from self.assertMemory(tb, 3, 0x0012)
        yield from self.assertMemory(tb, 1, 0x9210)
        yield from self.assertMemory(tb, 4, 0xC908)
        yield from self.assertMemory(tb, 5, 0xFF92)

    @simulation_test(regs=[0x0005, 0x0000, 0x0000, 0x0000,
                           0x1234, 0x5678, 0xABCD, 0x0000],
                     code=[LD  (R1, R0,  0),
                           LD  (R2, R0,  1),
                           LD  (R3, R0, -1)])
    def test_LD(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x0005)
        yield from self.assertMemory(tb, 1, 0x5678)
        yield from self.assertMemory(tb, 2, 0xABCD)
        yield from self.assertMemory(tb, 3, 0x1234)

    @simulation_test(regs=[0x0001, 0x0000],
                     code=[LDX (R1, R0, 0)],
                     extr=[0x0000, 0x1234])
    def test_LDX(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x0001)
        yield from self.assertMemory(tb, 1, 0x1234)

    @simulation_test(regs=[0x0005, 0x5678, 0xABCD, 0x1234,
                           0x0000, 0x0000, 0x0000, 0x0000],
                     code=[ST  (R1, R0,  0),
                           ST  (R2, R0,  1),
                           ST  (R3, R0, -1)])
    def test_ST(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x0005)
        yield from self.assertMemory(tb, 1, 0x5678)
        yield from self.assertMemory(tb, 2, 0xABCD)
        yield from self.assertMemory(tb, 3, 0x1234)

    @simulation_test(regs=[0x0001, 0x1234],
                     code=[STX (R1, R0, 0)],
                     extr=[0x0000, 0x0000])
    def test_STX(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x0001)
        yield from self.assertExternal(tb, 1, 0x1234)

    @simulation_test(regs=[0xabcd],
                     code=[MOVL(R0, 0x12)])
    def test_MOVL(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x0012)

    @simulation_test(regs=[0xabcd],
                     code=[MOVH(R0, 0x12)])
    def test_MOVH(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x1200)

    @simulation_test(regs=[0xabcd],
                     code=[MOVA(R0, 1)])
    def test_MOVA(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x000a)

    @simulation_test(regs=[1234, 1234],
                     code=[ADDI(R0, +42),
                           ADDI(R1, -42)])
    def test_ADDI(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 1234+42)
        yield from self.assertMemory(tb, 1, 1234-42)

    @simulation_test(regs=[0xabcd, 0xabcd],
                     code=[MOVI(R0, 0x12),
                           MOVI(R1, 0x1234),
                           MOVI(R2, 0x89ab)])
    def test_MOVI(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x0012)
        yield from self.assertMemory(tb, 1, 0x1234)
        yield from self.assertMemory(tb, 2, 0x89ab)

    @simulation_test(regs=[0x0000, 0x0000, 0x0000, 0x0000,
                           0x0000, 0x0000, 0x1234, 0x0000],
                     code=[LDI (R0, -3)])
    def test_LDI(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x1234)

    @simulation_test(regs=[0x1234, 0x0000, 0x0000, 0x0000,
                           0x0000, 0x0000, 0x0000, 0x0000],
                     code=[STI (R0, -3)])
    def test_STI(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 6, 0x1234)

    @simulation_test(code=[JAL (R0, 1),
                           MOVL(R1, 1),
                           MOVL(R2, 1)])
    def test_JAL(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x0009)
        yield from self.assertMemory(tb, 1, 0x0000)
        yield from self.assertMemory(tb, 2, 0x0001)

    @simulation_test(regs=[0x0004],
                     code=[JR  (R0, 6),
                           MOVL(R1, 1),
                           MOVL(R2, 1)])
    def test_JR(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x0004)
        yield from self.assertMemory(tb, 1, 0x0000)
        yield from self.assertMemory(tb, 2, 0x0001)

    @simulation_test(code=[J   (1), MOVL(R0, 1), MOVL(R1, 1)])
    def test_J(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 0, 0x0000)
        yield from self.assertMemory(tb, 1, 0x0001)

    @simulation_test(regs=[0x1234, 0x1234,
                           0x5678, 0x5679],
                     code=[CMP (R0, R1), JNZ (1), MOVL(R4, 1), MOVL(R5, 1),
                           CMP (R2, R3), JNZ (1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JNZ(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 4, 0x0001)
        yield from self.assertMemory(tb, 5, 0x0001)
        yield from self.assertMemory(tb, 6, 0x0000)
        yield from self.assertMemory(tb, 7, 0x0001)

    @simulation_test(regs=[0x1234, 0x1234,
                           0x5678, 0x5679],
                     code=[CMP (R0, R1), JZ  (1), MOVL(R4, 1), MOVL(R5, 1),
                           CMP (R2, R3), JZ  (1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JZ(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 4, 0x0000)
        yield from self.assertMemory(tb, 5, 0x0001)
        yield from self.assertMemory(tb, 6, 0x0001)
        yield from self.assertMemory(tb, 7, 0x0001)

    @simulation_test(regs=[0x1234, 0x7777,
                           0x0000, 0x7777],
                     code=[ADD (R0, R0, R1), JNS (1), MOVL(R4, 1), MOVL(R5, 1),
                           ADD (R2, R2, R3), JNS (1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JNS(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 4, 0x0001)
        yield from self.assertMemory(tb, 5, 0x0001)
        yield from self.assertMemory(tb, 6, 0x0000)
        yield from self.assertMemory(tb, 7, 0x0001)

    @simulation_test(regs=[0x1234, 0x7777,
                           0x0000, 0x7777],
                     code=[ADD (R0, R0, R1), JS  (1), MOVL(R4, 1), MOVL(R5, 1),
                           ADD (R2, R2, R3), JS  (1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JS(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 4, 0x0000)
        yield from self.assertMemory(tb, 5, 0x0001)
        yield from self.assertMemory(tb, 6, 0x0001)
        yield from self.assertMemory(tb, 7, 0x0001)

    @simulation_test(regs=[0x8888, 0x7fff,
                           0x8888, 0x7777],
                     code=[ADD (R0, R0, R1), JNC (1), MOVL(R4, 1), MOVL(R5, 1),
                           ADD (R2, R2, R3), JNC (1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JNC(self, tb):
        yield from self.run_core(tb)
        yield from self.assertMemory(tb, 4, 0x0001)
        yield from self.assertMemory(tb, 5, 0x0001)
        yield from self.assertMemory(tb, 6, 0x0000)
        yield from self.assertMemory(tb, 7, 0x0001)

    def assertCMPBranch(self, tb, n, taken):
        r = 2 + n * 2
        if taken:
            yield from self.assertMemory(tb, r + 0, 0x0000)
            yield from self.assertMemory(tb, r + 1, 0x0001)
        else:
            yield from self.assertMemory(tb, r + 0, 0x0001)
            yield from self.assertMemory(tb, r + 1, 0x0001)

    def assertCMPBranchY(self, tb, n):
        yield from self.assertCMPBranch(tb, n, True)

    def assertCMPBranchN(self, tb, n):
        yield from self.assertCMPBranch(tb, n, False)

    @simulation_test(regs=[0x1234, 0x1235],
                     code=[CMP (R0, R0), JUGE(1), MOVL(R2, 1), MOVL(R3, 1),
                           CMP (R0, R1), JUGE(1), MOVL(R4, 1), MOVL(R5, 1),
                           CMP (R1, R0), JUGE(1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JUGE(self, tb):
        yield from self.run_core(tb)
        yield from self.assertCMPBranchY(tb, 0) # R0 u>= R0 → Y
        yield from self.assertCMPBranchN(tb, 1) # R0 u>= R1 → N
        yield from self.assertCMPBranchY(tb, 2) # R1 u>= R0 → Y

    @simulation_test(regs=[0x1234, 0x1235],
                     code=[CMP (R0, R0), JUGT(1), MOVL(R2, 1), MOVL(R3, 1),
                           CMP (R0, R1), JUGT(1), MOVL(R4, 1), MOVL(R5, 1),
                           CMP (R1, R0), JUGT(1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JUGT(self, tb):
        yield from self.run_core(tb)
        yield from self.assertCMPBranchN(tb, 0) # R0 u> R0 → N
        yield from self.assertCMPBranchN(tb, 1) # R0 u> R1 → N
        yield from self.assertCMPBranchY(tb, 2) # R1 u> R0 → Y

    @simulation_test(regs=[0x1234, 0x1235],
                     code=[CMP (R0, R0), JULT(1), MOVL(R2, 1), MOVL(R3, 1),
                           CMP (R0, R1), JULT(1), MOVL(R4, 1), MOVL(R5, 1),
                           CMP (R1, R0), JULT(1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JULT(self, tb):
        yield from self.run_core(tb)
        yield from self.assertCMPBranchN(tb, 0) # R0 u< R0 → N
        yield from self.assertCMPBranchY(tb, 1) # R0 u< R1 → Y
        yield from self.assertCMPBranchN(tb, 2) # R1 u< R0 → N

    @simulation_test(regs=[0x1234, 0x1235],
                     code=[CMP (R0, R0), JULE(1), MOVL(R2, 1), MOVL(R3, 1),
                           CMP (R0, R1), JULE(1), MOVL(R4, 1), MOVL(R5, 1),
                           CMP (R1, R0), JULE(1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JULE(self, tb):
        yield from self.run_core(tb)
        yield from self.assertCMPBranchY(tb, 0) # R0 u<= R0 → Y
        yield from self.assertCMPBranchY(tb, 1) # R0 u<= R1 → Y
        yield from self.assertCMPBranchN(tb, 2) # R1 u<= R0 → N

    @simulation_test(regs=[0x0123, 0x8123],
                     code=[CMP (R0, R0), JSGE(1), MOVL(R2, 1), MOVL(R3, 1),
                           CMP (R0, R1), JSGE(1), MOVL(R4, 1), MOVL(R5, 1),
                           CMP (R1, R0), JSGE(1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JSGE(self, tb):
        yield from self.run_core(tb)
        yield from self.assertCMPBranchY(tb, 0) # R0 s>= R0 → Y
        yield from self.assertCMPBranchY(tb, 1) # R0 s>= R1 → Y
        yield from self.assertCMPBranchN(tb, 2) # R1 s>= R0 → N

    @simulation_test(regs=[0x0123, 0x8123],
                     code=[CMP (R0, R0), JSGT(1), MOVL(R2, 1), MOVL(R3, 1),
                           CMP (R0, R1), JSGT(1), MOVL(R4, 1), MOVL(R5, 1),
                           CMP (R1, R0), JSGT(1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JSGT(self, tb):
        yield from self.run_core(tb)
        yield from self.assertCMPBranchN(tb, 0) # R0 s> R0 → N
        yield from self.assertCMPBranchY(tb, 1) # R0 s> R1 → Y
        yield from self.assertCMPBranchN(tb, 2) # R1 s> R0 → N

    @simulation_test(regs=[0x0123, 0x8123],
                     code=[CMP (R0, R0), JSLT(1), MOVL(R2, 1), MOVL(R3, 1),
                           CMP (R0, R1), JSLT(1), MOVL(R4, 1), MOVL(R5, 1),
                           CMP (R1, R0), JSLT(1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JSLT(self, tb):
        yield from self.run_core(tb)
        yield from self.assertCMPBranchN(tb, 0) # R0 s< R0 → N
        yield from self.assertCMPBranchN(tb, 1) # R0 s< R1 → N
        yield from self.assertCMPBranchY(tb, 2) # R1 s< R0 → Y

    @simulation_test(regs=[0x0123, 0x8123],
                     code=[CMP (R0, R0), JSLE(1), MOVL(R2, 1), MOVL(R3, 1),
                           CMP (R0, R1), JSLE(1), MOVL(R4, 1), MOVL(R5, 1),
                           CMP (R1, R0), JSLE(1), MOVL(R6, 1), MOVL(R7, 1)])
    def test_JSLE(self, tb):
        yield from self.run_core(tb)
        yield from self.assertCMPBranchY(tb, 0) # R0 s<= R0 → Y
        yield from self.assertCMPBranchN(tb, 1) # R0 s<= R1 → N
        yield from self.assertCMPBranchY(tb, 2) # R1 s<= R0 → Y
