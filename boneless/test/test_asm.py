from contextlib import contextmanager
import unittest

from ..arch.opcode import Instr
from ..arch.opcode import *
from ..arch.asm import TranslationError


class AssemblerTestCase(unittest.TestCase):
    def assertAssembles(self, input, output):
        self.assertEqual(Instr.assemble(input), output)

    def assertTranslationError(self, input, regex):
        with self.assertRaisesRegex(TranslationError, regex):
            Instr.assemble(input)

    def test_data(self):
        self.assertAssembles(
            [1,2,[3,[4]]],
            [1,2,3,4])

    def test_instr_simple(self):
        self.assertAssembles(
            [ADDI(R1, R2, 1),
             OR  (R4, R5, R6)],
            [int(ADDI(R1, R2, 1)),
             int(OR  (R4, R5, R6))])

    def test_instr_ext_imm(self):
        self.assertAssembles(
            [ADDI(R1, R2, 3)],
            [int(EXTI(0)),
             int(ADDI(R1, R2, 3))])

    def test_instr_rel_back(self):
        self.assertAssembles(
            [0,
             L("foo"),
             0,
             J("foo")],
            [0,
             0,
             int(J(-2))])

    def test_instr_rel_fwd(self):
        self.assertAssembles(
            [0,
             J("foo"),
             0,
             L("foo")],
            [0,
             int(J(1)),
             0])

    def test_instr_rel_back_ext_imm(self):
        self.assertAssembles(
            [L("foo"),
             [0] * 126,
             J("foo")],
            [*[0] * 126,
             int(J(-127))])
        self.assertAssembles(
            [L("foo"),
             [0] * 127,
             J("foo")],
            [*[0] * 127,
             int(EXTI(-129>>3)),
             int(J(-129))])

    def test_instr_rel_fwd_ext_imm(self):
        self.assertAssembles(
            [J("foo"),
             [0] * 127,
             L("foo")],
            [int(J(127)),
             *[0] * 127])
        self.assertAssembles(
            [J("foo"),
             [0] * 128,
             L("foo")],
            [int(EXTI(128>>3)),
             int(J(128)),
             *[0] * 128])

    def test_instr_rel_pathological(self):
        j_count = 16
        self.assertAssembles(
            [[J(f"l{n}") for n in range(j_count)],
             [0] * (127 - j_count),
             [[0, L(f"l{n}")] for n in range(j_count)]],
            [*[int(J(127)) for n in range(j_count)],
             *[0] * (127)])

    def test_instr_rel_custom(self):
        def jump_table(*args):
            def relocate(resolver):
                return [resolver(arg) for arg in args]
            return relocate
        self.assertAssembles(
            [J("end"),
             jump_table("foo", "bar", "baz"),
             J("end2"),
             L("end"), 0,
             L("foo"), 0,
             L("bar"), 0,
             L("baz"), 0,
             L("end2")],
            [int(J(4)),
             5, 6, 7,
             int(J(4)),
             0,
             0, 0, 0])

    def test_text(self):
        self.assertAssembles("""
                ADD  R1, R1, R0
                ORI  R2, R3, 123
            loop:
                J    loop
                .word 5678
            """,
            [int(ADD(R1, R1, R0)),
             int(EXTI(123>>3)),
             int(ORI(R2,R3,123)),
             int(J(-1)),
             5678])

    def test_wrong_dup_label(self):
        self.assertTranslationError(
            [L("foo"), L("foo")],
            r"Label 'foo' at indexes \[1\] has the same name as the label at indexes \[0\]")

    def test_wrong_unrecognized(self):
        self.assertTranslationError(
            ["xxx"],
            r"Unrecognized value 'xxx' of type builtins\.str at indexes \[0\]")

    def test_wrong_unrecognized_none(self):
        self.assertTranslationError(
            [None],
            r"Unrecognized value None of type builtins\.NoneType at indexes \[0\]")

    def test_wrong_unresolved(self):
        self.assertTranslationError(
            [ADDI(R0, R0, "foo")],
            r"Unresolved reference 'foo' in operand at indexes \[0\]")

    def test_wrong_text_bad_mnemonic(self):
        self.assertTranslationError(
            "ill 0x123",
            r"Unknown mnemonic 'ill' at line 1")

    def test_wrong_text_bad_format(self):
        self.assertTranslationError(
            "add r0",
            r"Illegal operands 'r0' for instruction ADD; expected "
            r"'{rsd:R}, {ra:R}, {rb:R}' at line 1")

    def test_wrong_text_bad_operand(self):
        self.assertTranslationError(
            "add r0, r0, 123",
            r"Illegal operand '123'; expected 'R{:d}' at line 1")


class DisassemblerTestCase(unittest.TestCase):
    def assertDisassembles(self, input, output, **kwargs):
        if kwargs.get("as_text"):
            output = output[1:].rstrip() + "\n"
        self.assertEqual(Instr.disassemble(input, **kwargs), output)

    def test_instr_simple(self):
        self.assertDisassembles(
            [int(ADDI(R1, R2, 0))],
            [ADDI(R1, R2, 0)])

    def test_instr_ext_imm(self):
        self.assertDisassembles(
            [int(EXTI(0)),
             int(ADDI(R1, R2, 3))],
            [ADDI(R1, R2, 3)])

    def test_instr_noncanonical(self):
        self.assertDisassembles(
            [int(EXTI(-1)),
             int(ADDI(R1, R2, -1))],
            [EXTI(8191),
             ADDI(R1, R2, 65535)])

    def test_instr_illegal(self):
        self.assertDisassembles(
            [0xffff],
            [0xffff])

    def test_labels(self):
        self.assertDisassembles(
            [int(J(-1)),
             int(J(4)),
             int(J(3)),
             int(J(2)),
             0, 0, 0, 0,
             int(J(10)),
             int(ANDI(R0, R0, -1))],
            [L("L0"),
             J("L0"),
             J("L6"),
             J("L6"),
             J("L6"),
             *[AND(R0, R0, R0)] * 2,
             L("L6"),
             *[AND(R0, R0, R0)] * 2,
             J(10),
             ANDI(R0, R0, 65535)],
            labels=True)

    def test_text(self):
        code = [0x1234, 0xc123, 0x5678, 0xc123, 0x00b0, 0xb0ff, 0xffff]
        self.assertDisassembles(
            code, """
\tSUB\tR2, R1, R4\t\t; 1234
\tST\tR6, R3, 0x918\t\t; C123 5678
\tEXTI\t0x123\t\t\t; C123
\tXOR\tR0, R5, R0\t\t; 00B0
\tJNZ\t-0x1\t\t\t; B0FF
\t.word\t0xffff
            """,
            as_text=True)
        self.assertDisassembles(
            code, """
\tSUB\tR2, R1, R4\t\t; 1234
\tST\tR6, R3, 0x918\t\t; C123 5678
\tEXTI\t0x123\t\t\t; C123
\tXOR\tR0, R5, R0\t\t; 00B0
L5:
\tJNZ\tL5\t\t\t; <reloc>
\t.word\t0xffff
            """,
            as_text=True, labels=True)
