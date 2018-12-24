import unittest

from .disasm import disassemble
from .instr import *


class DisassemblerTestCase(unittest.TestCase):
    def test_exhaustive(self):
        for insn in range(0, 0x10000):
            text_insn = disassemble(insn, python=False)
            code_insn = disassemble(insn, python=True)
            try:
                roundtrip_insn = eval(code_insn)[0]
                code_insn_2 = disassemble(roundtrip_insn, python=True)
                roundtrip_insn_2 = eval(code_insn_2)[0]
            except Exception as e:
                msg = "(instruction {}, encoding {:04x}) {}".format(code_insn, insn, str(e))
                raise self.failureException(msg).with_traceback(e.__traceback__) from None
            if roundtrip_insn != roundtrip_insn_2:
                self.fail("instruction {}: encoding {:04x}, roundtrip {:04x}"
                          .format(code_insn, insn, roundtrip_insn))
