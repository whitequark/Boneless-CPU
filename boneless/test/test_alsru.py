import unittest
import contextlib
import random
from nmigen import *
from nmigen.back.pysim import *

from ..gateware.alsru import *


class ALSRUTestCase:
    dut_cls = None

    def setUp(self):
        self.checks = 100
        self.width  = 16
        self.dut    = self.dut_cls(self.width)

    @contextlib.contextmanager
    def assertComputes(self, op, dir=None, *, ci=None, si=None):
        asserts = []
        yield(self.dut, asserts)

        random.seed(0)
        for _ in range(self.checks):
            rand_a = random.randint(0, (1 << self.width) - 1)
            rand_b = random.randint(0, (1 << self.width) - 1)
            rand_r = random.randint(0, (1 << self.width) - 1)
            rand_c = random.randint(0, 1) if ci is None else ci
            rand_h = random.randint(0, 1) if si is None else si

            def process():
                yield self.dut.c_op.eq(op)
                yield self.dut.c_dir.eq(self.dut_cls.Dir.L if dir is None else dir)
                yield self.dut.i_a.eq(rand_a)
                yield self.dut.i_b.eq(rand_b)
                yield self.dut.r_o.eq(rand_r)
                yield self.dut.i_c.eq(rand_c)
                yield self.dut.i_h.eq(rand_h)
                yield Delay()

                fail = False
                msg  = "for a={:0{}x} b={:0{}x} c={} h={}:" \
                    .format(rand_a, self.width // 4,
                            rand_b, self.width // 4,
                            rand_c,
                            rand_h)
                for signal, expr in asserts:
                    actual = (yield signal)
                    expect = (yield expr)
                    if expect != actual:
                        fail = True
                        msg += " {}={:0{}x} (expected {:0{}x})"\
                            .format(signal.name,
                                    actual, signal.width // 4,
                                    expect, signal.width // 4)
                if fail:
                    self.fail(msg)

            sim = Simulator(self.dut)
            sim.add_process(process)
            sim.run()

    def test_A(self):
        with self.assertComputes(self.dut_cls.Op.A, ci=0) as (dut, asserts):
            asserts += [(dut.o_o, dut.i_a)]

    def test_B(self):
        with self.assertComputes(self.dut_cls.Op.B, ci=0) as (dut, asserts):
            asserts += [(dut.o_o, dut.i_b)]

    def test_nB(self):
        with self.assertComputes(self.dut_cls.Op.nB, ci=0) as (dut, asserts):
            asserts += [(dut.o_o, ~dut.i_b)]

    def test_AaB(self):
        with self.assertComputes(self.dut_cls.Op.AaB, ci=0) as (dut, asserts):
            asserts += [(dut.o_o, dut.i_a & dut.i_b)]

    def test_AoB(self):
        with self.assertComputes(self.dut_cls.Op.AoB, ci=0) as (dut, asserts):
            asserts += [(dut.o_o, dut.i_a | dut.i_b)]

    def test_AxB(self):
        with self.assertComputes(self.dut_cls.Op.AxB, ci=0) as (dut, asserts):
            asserts += [(dut.o_o, dut.i_a ^ dut.i_b)]

    def test_ApB(self):
        with self.assertComputes(self.dut_cls.Op.ApB) as (dut, asserts):
            result   = dut.i_a + dut.i_b + dut.i_c
            asserts += [(dut.o_o, result[:self.width]),
                        (dut.o_z, result == 0),
                        (dut.o_s, result[self.width - 1]),
                        (dut.o_c, result[self.width]),
                        (dut.o_v, (dut.i_a[-1] == dut.i_b[-1]) &
                                  (dut.i_a[-1] != result[self.width - 1]))]

    def test_AmB(self):
        with self.assertComputes(self.dut_cls.Op.AmB) as (dut, asserts):
            result   = dut.i_a - dut.i_b - ~dut.i_c
            asserts += [(dut.o_o,  result[:self.width]),
                        (dut.o_z, result == 0),
                        (dut.o_s, result[self.width - 1]),
                        (dut.o_c, ~result[self.width]),
                        (dut.o_v,  (dut.i_a[-1] == ~dut.i_b[-1]) &
                                   (dut.i_a[-1] != result[self.width - 1]))]

    def test_SL(self):
        with self.assertComputes(self.dut_cls.Op.SLR, self.dut_cls.Dir.L) as (dut, asserts):
            result   = (dut.r_o << 1) | dut.i_h
            asserts += [(dut.o_o,  result[:self.width]),
                        (dut.o_h,  dut.r_o[-1])]

    def test_SR(self):
        with self.assertComputes(self.dut_cls.Op.SLR, self.dut_cls.Dir.R) as (dut, asserts):
            result   = (dut.r_o >> 1) | (dut.i_h << (self.width - 1))
            asserts += [(dut.o_o,  result[:self.width]),
                        (dut.o_h,  dut.r_o[0])]


class ALSRU_4LUT_TestCase(ALSRUTestCase, unittest.TestCase):
    dut_cls = ALSRU_4LUT
