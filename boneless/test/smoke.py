from abc import ABCMeta, abstractmethod
import functools
import traceback
import sys

from ..arch.opcode import *


def simulation_test(case):
    @functools.wraps(case)
    def wrapper(self):
        try:
            self.run_simulator(case)
        except AssertionError as error:
            error.__traceback__ = None
            raise error
    return wrapper


class SmokeTestCase(metaclass=ABCMeta):
    @abstractmethod
    def run_simulator(self, case):
        pass

    @abstractmethod
    def execute(self, code, regs=[], data=[], extr=[], flag="", cycles=None):
        pass

    @abstractmethod
    def assertF(self, flags):
        pass

    @abstractmethod
    def assertW(self, win):
        pass

    @abstractmethod
    def assertPC(self, addr):
        pass

    @abstractmethod
    def assertMemory(self, addr, value):
        pass

    @abstractmethod
    def assertExternal(self, addr, value):
        pass

    def do_ALU_R(self, op, a, b, r):
        yield from self.execute(
            regs=[a, b],
            code=[op(R2, R0, R1)])
        yield from self.assertMemory(2, r)

    def do_ALU_R_2(self, op1, a1, b1, r1, op2, a2, b2, r2):
        yield from self.execute(
            regs=[a1, a2, b1, b2],
            code=[op1(R4, R0, R2),
                  op2(R5, R1, R3)])
        yield from self.assertMemory(4, r1)
        yield from self.assertMemory(5, r2)

    def do_ALU_I(self, op, a, b, r):
        yield from self.execute(
            regs=[a],
            code=[op(R1, R0, b)])
        yield from self.assertMemory(1, r)

    def do_ALU_I_2(self, op1, a1, b1, r1, op2, a2, b2, r2):
        yield from self.execute(
            regs=[a1, a2],
            code=[op1(R2, R0, b1),
                  op2(R3, R1, b2)])
        yield from self.assertMemory(2, r1)
        yield from self.assertMemory(3, r2)

    @simulation_test
    def test_AND(self):
        yield from self.do_ALU_R(AND,  0xFA50, 0xA0F5, 0xA050)

    @simulation_test
    def test_ANDI(self):
        yield from self.do_ALU_I(ANDI, 0xFA50, 0xA0F5, 0xA050)

    @simulation_test
    def test_OR(self):
        yield from self.do_ALU_R(OR,   0xFA50, 0xA0F5, 0xFAF5)

    @simulation_test
    def test_ORI(self):
        yield from self.do_ALU_I(ORI,  0xFA50, 0xA0F5, 0xFAF5)

    @simulation_test
    def test_XOR(self):
        yield from self.do_ALU_R(XOR,  0xFA50, 0xA0F5, 0x5AA5)

    @simulation_test
    def test_XORI(self):
        yield from self.do_ALU_I(XORI, 0xFA50, 0xA0F5, 0x5AA5)

    @simulation_test
    def test_ADD(self):
        yield from self.do_ALU_R(ADD,  0x1234, 0x5678, 0x68ac)

    @simulation_test
    def test_ADDI(self):
        yield from self.do_ALU_I(ADDI, 0x1234, 0x5678, 0x68ac)

    @simulation_test
    def test_ADC(self):
        yield from self.do_ALU_R(ADC,  0x1234, 0x5678, 0x68ac)

    @simulation_test
    def test_ADCI(self):
        yield from self.do_ALU_I(ADCI, 0x1234, 0x5678, 0x68ac)

    @simulation_test
    def test_ADD_ADC(self):
        yield from self.do_ALU_R_2(ADD,  0xaaaa, 0xbbbb, 0x6665,
                                   ADC,  0x0002, 0x0003, 0x0006)

    @simulation_test
    def test_ADDI_ADCI(self):
        yield from self.do_ALU_I_2(ADDI, 0xaaaa, 0xbbbb, 0x6665,
                                   ADCI, 0x0002, 0x0003, 0x0006)

    @simulation_test
    def test_SUB(self):
        yield from self.do_ALU_R(SUB,  0x1234, 0x5678, 0xbbbc)

    @simulation_test
    def test_SUBI(self):
        yield from self.do_ALU_I(SUBI, 0x1234, 0x5678, 0xbbbc)

    @simulation_test
    def test_SBC(self):
        yield from self.do_ALU_R(SBC,  0x1234, 0x5678, 0xbbbb)

    @simulation_test
    def test_SBCI(self):
        yield from self.do_ALU_I(SBCI, 0x1234, 0x5678, 0xbbbb)

    @simulation_test
    def test_SUB_SBC(self):
        yield from self.do_ALU_R_2(SUB,  0xaaaa, 0xbbbb, 0xeeef,
                                   SBC,  0x0002, 0x0003, 0xfffe)

    @simulation_test
    def test_SUBI_SBCI(self):
        yield from self.do_ALU_I_2(SUBI, 0xaaaa, 0xbbbb, 0xeeef,
                                   SBCI, 0x0002, 0x0003, 0xfffe)

    @simulation_test
    def test_SLL(self):
        yield from self.do_ALU_R(SLL,  0xFA50, 3, 0xD280)

    @simulation_test
    def test_SLL_0(self):
        yield from self.do_ALU_R(SLL,  0xFA50, 0, 0xFA50)

    @simulation_test
    def test_SLLI(self):
        yield from self.do_ALU_I(SLLI, 0xFA50, 3, 0xD280)

    @simulation_test
    def test_ROL(self):
        yield from self.do_ALU_R(ROL,  0xFA50, 3, 0xD287)

    @simulation_test
    def test_ROLI(self):
        yield from self.do_ALU_I(ROLI, 0xFA50, 3, 0xD287)

    @simulation_test
    def test_SRL(self):
        yield from self.do_ALU_R(SRL,  0xFA50, 3, 0x1F4A)

    @simulation_test
    def test_SRLI(self):
        yield from self.do_ALU_I(SRLI, 0xFA50, 3, 0x1F4A)

    @simulation_test
    def test_SRA(self):
        yield from self.do_ALU_R(SRA,  0xFA50, 3, 0xFF4A)

    @simulation_test
    def test_SRAI(self):
        yield from self.do_ALU_I(SRAI, 0xFA50, 3, 0xFF4A)

    @simulation_test
    def test_CMP(self):
        yield from self.execute(
            regs=[0xabcd, 0x1234],
            code=[CMP (R0, R1)])
        yield from self.assertMemory(0, 0xabcd)
        yield from self.assertF("sc")

    @simulation_test
    def test_CMPI(self):
        yield from self.execute(
            regs=[0xabcd],
            code=[CMPI(R0, 0x1234)])
        yield from self.assertMemory(0, 0xabcd)
        yield from self.assertF("sc")

    @simulation_test
    def test_LD(self):
        yield from self.execute(
            regs=[0, 0, 0, 0x0005, 0x1234, 0x5678, 0x9abc],
            code=[LD  (R0, R3, -1),
                  LD  (R1, R3,  0),
                  LD  (R2, R3,  1)])
        yield from self.assertMemory(0,  0x1234)
        yield from self.assertMemory(1,  0x5678)
        yield from self.assertMemory(2,  0x9abc)

    @simulation_test
    def test_ST(self):
        yield from self.execute(
            regs=[0x1234, 0x5678, 0x9abc, 0x0005, 0, 0, 0],
            code=[ST  (R0, R3, -1),
                  ST  (R1, R3,  0),
                  ST  (R2, R3,  1)])
        yield from self.assertMemory(4,  0x1234)
        yield from self.assertMemory(5,  0x5678)
        yield from self.assertMemory(6,  0x9abc)

    @simulation_test
    def test_LDR(self):
        yield from self.execute(
            regs=[0, 0, 0, 0xffff, 0, 0, 0, 0x1234],
            code=[LDR (R0, R3, -1),
                  LDR (R1, R3,  3),
                  LDR (R2, R3,  1)],
            data=[0x9abc, 0x5678])
        yield from self.assertMemory(0,  0x1234)
        yield from self.assertMemory(1,  0x5678)
        yield from self.assertMemory(2,  0x9abc)

    @simulation_test
    def test_STR(self):
        yield from self.execute(
            regs=[0x1234, 0x5678, 0x9abc, 0xffff],
            code=[STR (R0, R3, -1),
                  STR (R1, R3,  3),
                  STR (R2, R3,  1)])
        yield from self.assertMemory(7,  0x1234)
        yield from self.assertMemory(12, 0x5678)
        yield from self.assertMemory(11, 0x9abc)


    @simulation_test
    def test_LDX(self):
        yield from self.execute(
            regs=[0, 0, 0, 0x0005],
            code=[LDX (R0, R3, -1),
                  LDX (R1, R3,  0),
                  LDX (R2, R3,  1)],
            extr=[0, 0, 0, 0, 0x1234, 0x5678, 0x9abc])
        yield from self.assertMemory(0, 0x1234)
        yield from self.assertMemory(1, 0x5678)
        yield from self.assertMemory(2, 0x9abc)

    @simulation_test
    def test_STX(self):
        yield from self.execute(
            regs=[0x1234, 0x5678, 0x9abc, 0x0005, 0, 0, 0],
            code=[STX (R0, R3, -1),
                  STX (R1, R3,  0),
                  STX (R2, R3,  1)])
        yield from self.assertExternal(4, 0x1234)
        yield from self.assertExternal(5, 0x5678)
        yield from self.assertExternal(6, 0x9abc)

    @simulation_test
    def test_LDXA(self):
        yield from self.execute(
            code=[LDXA(R0, 1)],
            extr=[0, 0x1234])
        yield from self.assertMemory(0, 0x1234)

    @simulation_test
    def test_STXA(self):
        yield from self.execute(
            regs=[0x1234],
            code=[STXA(R0, 1)])
        yield from self.assertExternal(1, 0x1234)

    @simulation_test
    def test_MOVI(self):
        yield from self.execute(
            code=[MOVI(R0, 0x0011),
                  MOVI(R1, 0xffee),
                  MOVI(R2, 0x1234)])
        yield from self.assertMemory(0, 0x0011)
        yield from self.assertMemory(1, 0xffee)
        yield from self.assertMemory(2, 0x1234)

    @simulation_test
    def test_MOVR(self):
        yield from self.execute(
            code=[MOVR(R0, 0x0011),
                  MOVR(R1, 0xffee),
                  MOVR(R2, 0x1234)])
        yield from self.assertMemory(0, 9  + 0x0011)
        yield from self.assertMemory(1, 10 + 0xffee)
        yield from self.assertMemory(2, 12 + 0x1234)

    @simulation_test
    def test_STW(self):
        yield from self.execute(
            regs=[0x1234],
            code=[STW (R0)])
        yield from self.assertW(0x1230)

    @simulation_test
    def test_XCHW(self):
        yield from self.execute(
            regs=[0x0010],
            code=[STW (R0),
                  XCHW(R0, R0)],
            data=[0, 0, 0, 0, 0, 0,
                  0x0018, 0, 0, 0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0, 0, 0, 0])
        yield from self.assertW(0x0018)
        yield from self.assertMemory(24, 0x0010)

    @simulation_test
    def test_ADJW(self):
        yield from self.execute(
            code=[ADJW(0x20),
                  ADJW(-0x8)])
        yield from self.assertW(0x0018)

    @simulation_test
    def test_LDW(self):
        yield from self.execute(
            regs=[0x0010],
            code=[STW (R0),
                  LDW (R0, 0x8)],
            data=[0, 0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0, 0, 0, 0])
        yield from self.assertW(0x0018)
        yield from self.assertMemory(24, 0x0010)

    @simulation_test
    def test_JR(self):
        yield from self.execute(
            regs=[0x1234],
            code=[JR  (R0, 2)])
        yield from self.assertPC(0x1234 + 2)

    @simulation_test
    def test_JRAL(self):
        yield from self.execute(
            regs=[0x1234, 0],
            code=[JRAL(R1, R0)])
        yield from self.assertPC(0x1234)
        yield from self.assertMemory(1, 9)

    @simulation_test
    def test_JVT(self):
        yield from self.execute(
            regs=[0x0009],
            code=[JVT (R0, 1)],
            data=[0x1234, 0x5678])
        yield from self.assertPC(0x0009 + 0x5678)

    @simulation_test
    def test_JST(self):
        yield from self.execute(
            regs=[0x0001],
            code=[JST (R0, 2)],
            data=[0, 0, 0x1234, 0x5678])
        yield from self.assertPC(9 + 2 + 0x5678)

    @simulation_test
    def test_JAL(self):
        yield from self.execute(
            regs=[0],
            code=[JAL (R0, 12)])
        yield from self.assertPC(9 + 12)
        yield from self.assertMemory(0, 9)

    @simulation_test
    def test_J(self):
        yield from self.execute(code=[J   (7)])
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_NOP(self):
        yield from self.execute(code=[NOP (7)])
        yield from self.assertPC(9)

    @simulation_test
    def test_BZ1(self): # includes aliases BZ, BEQ
        yield from self.execute(code=[BZ1 (7)], flags="z")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BZ0(self): # includes aliases BNZ, BNE
        yield from self.execute(code=[BZ0 (7)], flags="")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BS1(self): # includes alias BS
        yield from self.execute(code=[BS1 (7)], flags="s")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BS0(self): # includes alias BNS
        yield from self.execute(code=[BS0 (7)], flags="")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BC1(self): # includes aliases BC, BGEU
        yield from self.execute(code=[BC1 (7)], flags="c")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BC0(self): # includes aliases BNC, BLTU
        yield from self.execute(code=[BC0 (7)], flags="")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BV1(self): # includes alias BV
        yield from self.execute(code=[BV1 (7)], flags="v")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BV0(self): # includes alias BNV
        yield from self.execute(code=[BV0 (7)], flags="")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BGTU(self):
        yield from self.execute(code=[BGTU(7)], flags="c")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BLEU(self):
        yield from self.execute(code=[BLEU(7)], flags="z")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BGES(self):
        yield from self.execute(code=[BGES(7)], flags="sv")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BLTS(self):
        yield from self.execute(code=[BLTS(7)], flags="v")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BGTS(self):
        yield from self.execute(code=[BGTS(7)], flags="sv")
        yield from self.assertPC(9 + 7)

    @simulation_test
    def test_BLES(self):
        yield from self.execute(code=[BLES(7)], flags="z")
        yield from self.assertPC(9 + 7)
