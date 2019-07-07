import unittest
from collections import defaultdict

from .. import *
from ...instr import *

# TODO: Simulate Undefined Regs and Memory? Fail if write to
# undefined location occurs.
class BonelessTestCase(unittest.TestCase):
    def setUp(self):
        self.cpu = BonelessSimulator(start_pc=0x10, mem_size=1024, io_callback=None)
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

    def assertFlagsEqual(self, z=0, s=0, c=0, v=0):
        self.assertEqual([self.cpu.z, self.cpu.s, self.cpu.c, self.cpu.v], [z, s, c, v])
