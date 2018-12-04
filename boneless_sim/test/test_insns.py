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

        self.payload = [
            ADD(R2, R0, R1),
        ]

        self.cpu.load_program(self.flatten())
        # self.run(10) # Doesn't work if I define run() in parent object
        self.run_cpu_until_pc(17)
        self.assertEqual(self.cpu.regs()[:3].tolist(), [1, 2, 3])
