import unittest
from collections import defaultdict

from boneless_sim import *

from glasgow.arch.boneless.instr import *


# TODO: Simulate Undefined Regs and Memory? Fail if write to
# undefined location occurs.
class BonelessTestCase(unittest.TestCase):
    def setUp(self):
        self.cpu = BonelessSimulator(start_pc=0x10, memsize=1024, io_callback=None)
        self.init_regs = defaultdict(lambda : 0)
        self.payload = None

    def flatten(self):
        init_code = []
        for k,v in self.init_regs.items():
            self.cpu.write_reg(k, v)

        return assemble(self.payload)

    def run_cpu(self, count):
        with self.cpu:
            for i in range(count):
                self.cpu.stepi()

    def run_cpu_until_pc(self, final_pc, fail_count=100):
        with self.cpu:
            for i in range(fail_count):
                self.cpu.stepi()
                if self.cpu.pc >= final_pc:
                    break
            else:
                self.fail("Emergency stop of CPU after {} insns.".format(fail_count))


class TestMovI(BonelessTestCase):
    def test_movl(self):
        self.init_regs[R1] = 0xFF00
        self.init_regs[R2] = 0x00FF

        self.payload = [
            MOVL(R0, 0xFF),
            MOVL(R1, 0x80),
            MOVL(R2, 0x0),
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu_until_pc(0x13)
        self.assertEqual(self.cpu.regs()[:3].tolist(), [0x00FF, 0xFF80, 0])


class TestClassA(BonelessTestCase):
    def test_add(self):
        self.init_regs[R0] = 1
        self.init_regs[R1] = 2
        self.init_regs[R3] = 0xFFFE
        self.init_regs[R4] = 2

        self.payload = [
            ADD(R2, R0, R1),
            ADD(R5, R3, R4),
        ]

        self.cpu.load_program(self.flatten())
        # self.run(10) # Doesn't work if I define run() in parent object
        self.run_cpu(2)
        self.assertEqual(self.cpu.regs()[:3].tolist(), [1, 2, 3])
        self.assertEqual(self.cpu.regs()[3:6].tolist(), [0xFFFE, 2, 0])

    def test_sub(self):
        self.init_regs[R0] = 0x8000
        self.init_regs[R1] = 0x0001

        self.payload = [
            SUB(R2, R0, R1),
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[2], 0x7fff)
        self.assertEqual(self.cpu.flags, { "Z" : 0, "S" : 0, "C" : 0, "V" : 1})

    def test_logical(self):
        op_and = lambda x, y : x & y
        op_or = lambda x, y : x | y
        op_xor = lambda x, y : x ^ y

        self.init_regs[R1] = 0xDEAD
        self.init_regs[R2] = 0xFFFF

        self.payload = [
            AND(R3, R1, R0),
            OR(R4, R1, R0),
            XOR(R5, R1, R2)
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[3], 0)

        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[4], 0xDEAD)

        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[5], 0b0010000101010010)
