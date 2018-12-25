from boneless_sim.test.common import *

class TestClassA(BonelessTestCase):
    def test_add(self):
        self.init_regs[R0] = 1
        self.init_regs[R1] = 2
        self.init_regs[R3] = 0xFFFE
        self.init_regs[R4] = 2
        self.init_regs[R6] = 0x8000

        self.payload = [
            ADD(R2, R0, R1),
            ADD(R5, R3, R4),
            ADD(R7, R6, R6)
        ]

        self.cpu.load_program(self.flatten())
        # self.run(10) # Doesn't work if I define run() in parent object
        self.run_cpu(2)
        self.assertEqual(self.cpu.regs()[:3].tolist(), [1, 2, 3])
        self.assertEqual(self.cpu.regs()[3:6].tolist(), [0xFFFE, 2, 0])
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[7], 0)
        # Only possible calculation where this can occur?
        self.assertEqual(self.cpu.flags, { "Z" : 1, "S" : 0, "C" : 1, "V" : 1})

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
        self.assertEqual(self.cpu.flags, { "Z" : 0, "S" : 0, "C" : 1, "V" : 1})

        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[2], 0)
        self.assertEqual(self.cpu.flags, { "Z" : 1, "S" : 0, "C" : 1, "V" : 0})

    def test_cmp(self):
        self.init_regs[R1] = 0x0001
        self.init_regs[R2] = 0xFFFF
        self.init_regs[R3] = 0xFFFE
        self.init_regs[R4] = 0x8001
        self.init_regs[R5] = 0x8000
        self.init_regs[R6] = 0x7FFF
        self.init_regs[R7] = 0x0002

        # Test all valid combinations of flags
        # (Sign and Zero are mutually exclusive in twos comp, so we only need
        # to test twelve possble combinations). Commented-out combinations
        # are not possible with subtraction or at all.
        for ra, rb, f in [
            # (_, _, { "Z" : 0, "S" : 0, "C" : 0, "V" : 0}), # S=0, C=0 impossible
            # (_, _, { "Z" : 0, "S" : 0, "C" : 0, "V" : 1}),
            (R7, R1, { "Z" : 0, "S" : 0, "C" : 1, "V" : 0}),
            (R5, R1, { "Z" : 0, "S" : 0, "C" : 1, "V" : 1}),

            (R1, R7, { "Z" : 0, "S" : 1, "C" : 0, "V" : 0}),
            (R6, R2, { "Z" : 0, "S" : 1, "C" : 0, "V" : 1}),
            (R2, R0, { "Z" : 0, "S" : 1, "C" : 1, "V" : 0}),
            # (_, _, { "Z" : 0, "S" : 1, "C" : 1, "V" : 1}),
            # (_, _, { "Z" : 1, "S" : 0, "C" : 0, "V" : 0}), # Z=1, C=0 impossible
            # (_, _, { "Z" : 1, "S" : 0, "C" : 0, "V" : 1}),
            (R1, R1, { "Z" : 1, "S" : 0, "C" : 1, "V" : 0}),
            # (_, _, { "Z" : 1, "S" : 0, "C" : 1, "V" : 1}) # Only possible w/ ADD
        ]:
            with self.subTest(rb=rb, ra=ra, f=f):
                self.payload = [
                    CMP(ra, rb),
                ]
                self.cpu.pc = 16
                self.cpu.load_program(self.flatten())
                self.run_cpu(1)
                self.assertEqual(self.cpu.flags, f)

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


class TestClassS(BonelessTestCase):
    def test_sll(self):
        self.init_regs[R0] = 0x1

        self.payload = [
            SLL(R0, R0, 4)
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[0], 0x10)

    def test_mov(self):
        self.init_regs[R0] = 0x55AA

        self.payload = [
            MOV(R1, R0)
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[1], 0x55AA)

    def test_srl(self):
        self.init_regs[R0] = 0x8000

        self.payload = [
            SRL(R0, R0, 4)
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[0], 0x0800)

    def test_sra(self):
        self.init_regs[R0] = 0x8000

        self.payload = [
            SRA(R0, R0, 4)
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[0], 0xF800)

    def test_rot(self):
        self.init_regs[R0] = 0xDEAD

        self.payload = [
            ROT(R0, R0, 12),
            ROR(R0, R0, 12),
            ROR(R0, R0, 3),
            ROL(R0, R0, 3),
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[0], 0xDDEA)
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[0], 0xDEAD)
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[0], 0xBBD5)
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[0], 0xDEAD)

    def test_flags(self):
        self.init_regs[R0] = 0x1
        self.init_regs[R1] = 0x8000
        self.init_regs[R2] = 0x4000

        self.payload = [
            SLL(R2, R2, 1),
            SRL(R2, R2, 1),
            SRA(R2, R2, 15),
            SRA(R1, R1, 15)
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.flags, { "Z" : 0, "S" : 1, "C" : 0, "V" : 0})
        self.run_cpu(1)
        self.assertEqual(self.cpu.flags, { "Z" : 0, "S" : 0, "C" : 0, "V" : 0})
        self.run_cpu(1)
        self.assertEqual(self.cpu.flags, { "Z" : 1, "S" : 0, "C" : 0, "V" : 0})
        self.run_cpu(1)
        self.assertEqual(self.cpu.regs()[1], 0xFFFF)
        self.assertEqual(self.cpu.flags, { "Z" : 0, "S" : 1, "C" : 0, "V" : 0})


class TestClassM(BonelessTestCase):
    def test_ldst(self):
        self.init_regs[R0] = 0xBEEF
        self.init_regs[R1] = 0xDEAD
        self.init_regs[R2] = 0x41

        self.payload = [
            ST(R0, R2, 0),
            ST(R1, R2, -1),
            LD(R3, R2, -1),
            LD(R4, R2, 0)
        ]

        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(self.cpu.mem[0x41], 0xBEEF)
        self.run_cpu(1)
        self.assertEqual(self.cpu.mem[0x40:0x42].tolist(), [0xDEAD, 0xBEEF])
        self.run_cpu(2)
        self.assertEqual(self.cpu.regs()[3:5].tolist(), [0xDEAD, 0xBEEF])

    def test_ldxstx(self):
        my_str = ["H", "e", "l", "l", "o"]
        def callback(addr, data):
            if data:
                if addr < 5:
                    my_str[addr] = chr(data & 0x00FF)
            else:
                if addr < 5:
                    return ord(my_str[addr])
            return None

        self.init_regs[R0] = ord("L")

        self.payload = [
            STX(R0, R1, 3),
            LDX(R2, R1, 3),
            ADDI(R1, 1),
            LDX(R3, R1, -1)
        ]

        self.cpu.register_io(callback)
        self.cpu.load_program(self.flatten())
        self.run_cpu(1)
        self.assertEqual(my_str, ["H", "e", "l", "L", "o"])
        self.run_cpu(3)
        self.assertEqual(self.cpu.regs()[2:4].tolist(), [ord("L"), ord("H")])


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

        self.cpu.load_program(self.flatten())
        self.run_cpu(2)
        self.assertEqual(self.cpu.pc, 19)
        self.run_cpu(2)
        self.assertEqual(self.cpu.pc, 16)
        self.run_cpu(4)
        self.assertEqual(self.cpu.pc, 16)


class TestClassC(BonelessTestCase):
    def mk_payload(self, Jcc, Ra=R5, Rb=R6):
        return [
            L("start"),
            CMP(Ra, Rb),
            Jcc("end_branch"),
            L("end_no_branch"),
            NOP(),
            L("end_branch"),
            NOP()
        ]

    def test_jmps(self):
        for val_a, val_b, jcc, taken in [
            (0, 0, J, True),

            (0x7FFF, 0x7FFF, JZ, True),
            (0x8000, 0x7FFF, JE, False),
            (0xFFFF, 2, JNZ, True),
            (0xFFFF, 0xFFFF, JNE, False),

            (2, 1, JS, False),
            (1, 2, JS, True),
            (1, 2, JNS, False),
            (2, 1, JNS, True),

            (1, 0x8001, JO, True),
            (1, 0x8002, JO, False),
            (0x8001, 1, JNO, True),
            (0x8000, 1, JNO, False),

            (0xC000, 0x8001, JNC, False),
            (0x8000, 0x8001, JULT, True),
            (0x8001, 0x8001, JULT, False),

            (0xC000, 0x8001, JULE, False),
            (0x8000, 0x8001, JULE, True),
            (0x8001, 0x8001, JULE, True),

            (0xFFFF, 0x7FFF, JUGT, True),
            (0x7FFF, 0xFFFF, JUGT, False),
            (0xFFFF, 0xFFFF, JUGT, False),

            (0xFFFF, 0x7FFF, JC, True),
            (0x7FFF, 0xFFFF, JUGE, False),
            (0xFFFF, 0xFFFF, JUGE, True),

            (0xC000, 0x8001, JSLT, False),
            (0x8000, 0x8001, JSLT, True),
            (0x8001, 0x8001, JSLT, False),

            (0xC000, 0x8001, JSLE, False),
            (0x8000, 0x8001, JSLE, True),
            (0x8001, 0x8001, JSLE, True),

            (0xFFFF, 0x7FFF, JSGT, False),
            (0x7FFF, 0xFFFF, JSGT, True),
            (0xFFFF, 0xFFFF, JSGT, False),

            (0xFFFF, 0x7FFF, JSGE, False),
            (0x7FFF, 0xFFFF, JSGE, True),
            (0xFFFF, 0xFFFF, JSGE, True),
        ]:
            with self.subTest(val_a=val_a, val_b=val_b, jcc=jcc, taken=taken):
                self.init_regs[R5] = val_a
                self.init_regs[R6] = val_b

                self.payload = self.mk_payload(jcc)
                self.cpu.pc = 16
                self.cpu.load_program(self.flatten())
                self.run_cpu(2)
                if taken:
                    self.assertEqual(self.cpu.pc, 19)
                else:
                    self.assertEqual(self.cpu.pc, 18)
