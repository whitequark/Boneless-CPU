from boneless.simulator.test.common import *

class TestSimActive(BonelessTestCase):
    def test_set_pc(self):
        with self.cpu:
            self.cpu.set_pc(0)

        self.assertEqual(self.cpu.pc, 0x10)

    def test_write_reg(self):
        with self.cpu:
            self.cpu.write_reg(R0, 0xFFFF)

        self.assertEqual(self.cpu.regs()[0], 0x0000)

    def test_load_program(self):
        self.payload = [
            ADDI(R0, 1)
        ]

        self.cpu.load_program(self.flatten())

        with self.cpu:
            self.payload = [
                NOP()
            ]
            self.cpu.load_program(self.flatten())

        self.assertEqual(self.cpu.mem[self.cpu.pc], ADDI(R0, 1)[0])

    def test_register_io(self):
        def callback0(addr, data):
            return 0xFFFF

        def callback1(addr, data):
            return 0x0001

        self.payload = [
            LDX(R0, R1, 0),
        ]

        self.cpu.register_io(callback0)
        self.cpu.load_program(self.flatten())

        with self.cpu:
            self.cpu.register_io(callback1)
            self.cpu.stepi()

        self.assertEqual(self.cpu.regs()[0], 0xFFFF)


class TestException(BonelessTestCase):
    def test_reserved(self):
        for opc in [0x0003, 0x8800]:
            with self.subTest(opc=opc):
                self.cpu.load_program([opc])
                with self.assertRaisesRegex(BonelessError, "reserved instruction"):
                    self.run_cpu(1)

    def test_no_callback(self):
        for opc in [LDX(R0, R1, 0), STX(R0, R1, 0)]:
            with self.subTest(opc=opc):
                self.cpu.load_program(opc)
                with self.assertRaisesRegex(BonelessError, "io_callback not set"):
                    self.run_cpu(1)
