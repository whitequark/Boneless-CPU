import unittest

from ..arch import mc, opcode_v3 as op


class InstructionTestCase(unittest.TestCase):
    def iter_each_code(self):
        for instr_code in range(0, 1<<16):
            try:
                yield instr_code, op.Instr.from_int(instr_code)
            except ValueError as e:
                self.assertIn("Unknown encoding", str(e))

    def test_roundtrip_int(self):
        for instr_code, instr_obj in self.iter_each_code():
            instr_obj_2  = op.Instr.from_int(instr_code)
            self.assertEqual(instr_obj_2, instr_obj)

    def test_roundtrip_str(self):
        for instr_code, instr_obj in self.iter_each_code():
            instr_str    = str(instr_obj)
            instr_obj_2  = op.Instr.from_str(instr_str)
            self.assertEqual(instr_obj_2, instr_obj)

    def test_roundtrip_repr(self):
        for instr_code, instr_obj in self.iter_each_code():
            instr_repr   = repr(instr_obj)
            instr_obj_2  = eval(instr_repr, op.__dict__)
            self.assertEqual(instr_obj_2, instr_obj)

    def test_encode_decode(self):
        stream, instr = [], op.ADDI(op.R2, op.R1, 0)
        self.assertEqual(instr.encode(stream), 1)
        self.assertEqual(len(stream), 1)
        self.assertEqual(op.Instr.decode(stream), (instr, 1))

        stream, instr = [], op.ADDI(op.R2, op.R1, 2)
        self.assertEqual(instr.encode(stream), 2)
        self.assertEqual(len(stream), 2)
        self.assertEqual(op.Instr.decode(stream), (instr, 2))
        self.assertEqual(op.Instr.decode(stream[:1]), (op.EXTI(0), 1))

        stream, instr = [], op.ROTI(op.R2, op.R1, 8)
        self.assertEqual(instr.encode(stream), 1)
        self.assertEqual(len(stream), 1)
        self.assertEqual(op.Instr.decode(stream), (instr, 1))

        stream, instr = [], op.ROTI(op.R2, op.R1, 11)
        self.assertEqual(instr.encode(stream), 2)
        self.assertEqual(len(stream), 2)
        self.assertEqual(op.Instr.decode(stream), (instr, 2))
        self.assertEqual(op.Instr.decode(stream[:1]), (op.EXTI(1), 1))

    def test_alias(self):
        self.assertEqual(int(op.JZ(0)), int(op.JE(0)))
        self.assertEqual(op.JZ(0), op.JE(0))
        self.assertFalse(op.JZ.alias)
        self.assertTrue(op.JE.alias)

    def test_max_length(self):
        self.assertEqual(op.ADD(op.R1, op.R1, op.R1).max_length, 1)
        self.assertEqual(op.ADDI(op.R1, op.R1, 0).max_length, 2)

    def test_imm_conversion(self):
        instr_1 = op.ANDI(op.R1, op.R1, 0)
        instr_2 = op.ANDI(op.R1, op.R1, 123)
        self.assertEqual(instr_1.imm, 0)
        self.assertFalse(instr_1.imm)
        self.assertEqual(instr_2.imm, 123)
        self.assertTrue(instr_2.imm)

    def test_negative_imm(self):
        stream_1 = []
        instr_1  = op.ANDI(op.R1, op.R1, -10)
        instr_1.encode(stream_1)
        stream_2 = []
        instr_2  = op.ANDI(op.R1, op.R1, 65526)
        instr_2.encode(stream_2)
        self.assertEqual(stream_1, stream_2)
        self.assertNotEqual(instr_1, instr_2)

    def test_negative_imm_lut(self):
        stream_1 = []
        instr_1  = op.ANDI(op.R1, op.R1, -1)
        instr_1.encode(stream_1)
        stream_2 = []
        instr_2  = op.ANDI(op.R1, op.R1, 0xffff)
        instr_2.encode(stream_2)
        self.assertEqual(stream_1, stream_2)
        self.assertNotEqual(instr_1, instr_2)

    def test_roundtrip_negative_imm(self):
        instr = op.LD(op.R1, op.R0, -10)
        self.assertEqual(op.Instr.from_int(int(instr)), instr)

    def test_roundtrip_negative_ext_imm(self):
        stream = []
        instr  = op.LD(op.R1, op.R0, -100)
        instr.encode(stream)
        self.assertEqual(op.Instr.decode(stream), (instr, 2))

    def test_odd_whitespace(self):
        self.assertEqual(op.ANDI(op.R0, op.R0, 1),
                         op.Instr.from_str(" ANDI \t R0 , R0, 1 "))

    def test_relocate(self):
        instr = op.MOVR(op.R1, "foo")
        self.assertEqual(op.Instr.from_str(str(instr)), instr)
        self.assertEqual(eval(repr(instr), op.__dict__), instr)
        with self.assertRaisesRegex(mc.UnresolvedRef,
                r"Unresolved reference 'foo' in operand"):
            int(instr)

        def relocate(symbol):
            self.assertEqual(symbol, "foo")
            return 42
        instr_2 = instr(relocate)
        self.assertEqual(instr_2, op.MOVR(op.R1, 42))

        def dont_relocate(symbol):
            return None
        instr_3 = instr(dont_relocate)
        self.assertEqual(instr_3, op.MOVR(op.R1, "foo"))

        def fail_relocate(symbol):
            self.fail()
        instr_4 = instr_2(fail_relocate)

    def test_from_str_wrong_mnemonic(self):
        with self.assertRaisesRegex(ValueError,
                r"Unknown mnemonic 'FAIL'"):
            op.Instr.from_str("FAIL 0x10")

    def test_from_str_wrong_operands(self):
        with self.assertRaisesRegex(ValueError,
                r"Illegal operands 'R0, R0' for instruction ADD; "
                r"expected '{rsd:R}, {ra:R}, {rb:R}'"):
            op.Instr.from_str("ADD R0, R0")
        with self.assertRaisesRegex(ValueError,
                r"Illegal operands 'R0, R0, 0' for instruction ADD; "
                r"expected '{rsd:R}, {ra:R}, {rb:R}'") as e:
            op.Instr.from_str("ADD R0, R0, 0")
        with self.assertRaisesRegex(ValueError,
                r"Illegal operand '0'; expected 'R{:d}'"):
            raise e.exception.__cause__
        with self.assertRaisesRegex(ValueError,
                r"Illegal operands 'R10, R0, R0' for instruction ADD; "
                r"expected '{rsd:R}, {ra:R}, {rb:R}'") as e:
            op.Instr.from_str("ADD R10, R0, R0")
        with self.assertRaisesRegex(ValueError,
                r"Register operand must be one of R0 to R7"):
            raise e.exception.__cause__
        with self.assertRaisesRegex(ValueError,
                r"Illegal operands 'R0, R0, 65536' for instruction ADDI; "
                r"expected '{rsd:R}, {ra:R}, {imm:I3AL}'") as e:
            op.Instr.from_str("ADDI R0, R0, 65536")
        with self.assertRaisesRegex(ValueError,
                r"Immediate operand 65536 must be in range -32768..65536"):
            raise e.exception.__cause__

    def test_from_int_wrong(self):
        with self.assertRaisesRegex(ValueError,
                r"Unknown encoding 0b1111111111111111"):
            op.Instr.from_int(0xffff)

    def test_imm_wrong_range(self):
        with self.assertRaisesRegex(ValueError,
                r"Immediate operand 65536 must be in range -32768\.\.65536"):
            op.ADDI(op.R0, op.R0, 0x10000)

    def test_shift_wrong_range(self):
        with self.assertRaisesRegex(ValueError,
                r"Immediate operand 18 must be in range 0\.\.16"):
            op.ROTI(op.R0, op.R0, 18)
