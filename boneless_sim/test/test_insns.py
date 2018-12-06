from boneless_sim.test.common import *

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
            SUB(R2, R2, R2),
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[2], 0x7fff)
        self.assertEqual(self.cpu.flags, { "Z" : 0, "S" : 0, "C" : 0, "V" : 1})

        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[2], 0)
        self.assertEqual(self.cpu.flags, { "Z" : 1, "S" : 0, "C" : 0, "V" : 0})

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
        self.assertEqual(self.cpu.flags, { "Z" : 1, "S" : 0, "C" : 0, "V" : 0})

        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[4], 0xDEAD)

        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[5], 0b0010000101010010)


class TestClassI(BonelessTestCase):
    def test_movl(self):
        self.init_regs[R1] = 0xFF00
        self.init_regs[R2] = 0x00FF

        self.payload = [
            MOVL(R0, 0xFF),
            MOVL(R1, 0x80),
            MOVL(R2, 0x0),
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(3)
        self.assertEqual(self.cpu.regs()[:3].tolist(), [0x00FF, 0x80, 0])

    def test_movh(self):
        self.init_regs[R1] = 0xFF00
        self.init_regs[R2] = 0x00FF

        self.payload = [
            MOVH(R0, 0xFF),
            MOVH(R1, 0x80),
            MOVH(R2, 0x0),
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(3)
        self.assertEqual(self.cpu.regs()[:3].tolist(), [0xFF00, 0x8000, 0])

    def test_mova(self):
        self.payload = [
            MOVA(R0, -1),
            MOVA(R1, -128),
            MOVA(R2, 127),
            MOVA(R3, 0),
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(4)
        self.assertEqual(self.cpu.regs()[0], 16)
        self.assertEqual(self.cpu.regs()[1], 17 + 65536 - 128 + 1)
        self.assertEqual(self.cpu.regs()[2], 18 + 127 + 1)
        self.assertEqual(self.cpu.regs()[3], 20)

    def test_addsubi(self):
        self.init_regs[R0] = 0xFF00
        self.init_regs[R1] = 0x00FF

        self.payload = [
            ADDI(R0, -1),
            SUBI(R0, -1),
            ADDI(R1, 127),
            SUBI(R1, 128)
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[0], 0xFEFF)
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[0], 0xFF00)
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[1], 0x017E)
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[1], 0x00FE)

    def test_addldisti(self):
        self.init_regs[R0] = 0xBEEF

        self.payload = [
            STI(R0, -15),
            LDI(R2, -16)
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(2)
        self.assertEqual(self.cpu.regs()[:3].tolist(), [0xBEEF, 0xBEEF, 0xBEEF])

    def test_jaljr(self):
        self.payload = [
            L("entry"),
            ADDI(R0, 1),
            JAL(R0, "my_fun"),
            NOP(),
            L("my_fun"),
            ADDI(R1, 1),
            JR(R0, -2)
        ]

        # Original test... save for later.
        # *[NOP() for _ in range(16)],
        # L("entry"),
        # JR(R0, "jump_table"),
        # L("jump_table"),
        # ADDI(R0, 4),
        # JR(R0, "entry"),
        # ADDI(R0, 4),
        # JR(R0, "entry"),
        # SUBI(R0, 2),
        # JR(R0, "entry"),
        # ADDI(R0, 0)

        self.cpu.load_program(self.flatten())
        self.run_cpu(2)
        self.assertEqual(self.cpu.pc, 19)
        self.run_cpu(2)
        self.assertEqual(self.cpu.pc, 16)
        self.run_cpu(4)
        self.assertEqual(self.cpu.pc, 16)
