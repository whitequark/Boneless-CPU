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
    def assertComputes(self, ctrl, ci=None, si=None):
        asserts = []
        yield(self.dut, asserts)

        random.seed(0)
        for _ in range(self.checks):
            rand_a  = random.randint(0, (1 << self.width) - 1)
            rand_b  = random.randint(0, (1 << self.width) - 1)
            rand_r  = random.randint(0, (1 << self.width) - 1)
            rand_ci = random.randint(0, 1) if ci is None else ci
            rand_si = random.randint(0, 1) if si is None else si

            with Simulator(self.dut) as sim:
                def process():
                    yield self.dut.ctrl.eq(ctrl)
                    yield self.dut.a.eq(rand_a)
                    yield self.dut.b.eq(rand_b)
                    yield self.dut.r.eq(rand_r)
                    yield self.dut.ci.eq(rand_ci)
                    yield self.dut.si.eq(rand_si)
                    yield Delay()

                    fail = False
                    msg  = "for a={:0{}x} b={:0{}x} ci={} si={}:" \
                        .format(rand_a, self.width // 4,
                                rand_b, self.width // 4,
                                rand_ci,
                                rand_si)
                    for signal, expr in asserts:
                        actual = (yield signal)
                        expect = (yield expr)
                        if expect != actual:
                            fail = True
                            msg += " {}={:0{}x} (expected {:0{}x})"\
                                .format(signal.name,
                                        actual, signal.nbits // 4,
                                        expect, signal.nbits // 4)
                    if fail:
                        self.fail(msg)

                sim.add_process(process)
                sim.run()

    def test_A(self):
        with self.assertComputes(self.dut_cls.CTRL_A, ci=0) as (dut, asserts):
            asserts += [(dut.o, dut.a)]

    def test_B(self):
        with self.assertComputes(self.dut_cls.CTRL_B, ci=0) as (dut, asserts):
            asserts += [(dut.o, dut.b)]

    def test_nB(self):
        with self.assertComputes(self.dut_cls.CTRL_nB, ci=0) as (dut, asserts):
            asserts += [(dut.o, ~dut.b)]

    def test_AaB(self):
        with self.assertComputes(self.dut_cls.CTRL_AaB, ci=0) as (dut, asserts):
            asserts += [(dut.o, dut.a & dut.b)]

    def test_AoB(self):
        with self.assertComputes(self.dut_cls.CTRL_AoB, ci=0) as (dut, asserts):
            asserts += [(dut.o, dut.a | dut.b)]

    def test_AxB(self):
        with self.assertComputes(self.dut_cls.CTRL_AxB, ci=0) as (dut, asserts):
            asserts += [(dut.o, dut.a ^ dut.b)]

    def test_ApB(self):
        with self.assertComputes(self.dut_cls.CTRL_ApB) as (dut, asserts):
            result   = dut.a + dut.b + dut.ci
            asserts += [(dut.o,   result[:self.width]),
                        (dut.co,  result[self.width]),
                        (dut.vo,  (dut.a[-1] == dut.b[-1]) &
                                  (dut.a[-1] != result[self.width - 1]))]

    def test_AmB(self):
        with self.assertComputes(self.dut_cls.CTRL_AmB) as (dut, asserts):
            result   = dut.a - dut.b - ~dut.ci
            asserts += [(dut.o,   result[:self.width]),
                        (dut.co, ~result[self.width]),
                        (dut.vo,  (dut.a[-1] == ~dut.b[-1]) &
                                  (dut.a[-1] != result[self.width - 1]))]

    def test_SL(self):
        with self.assertComputes(self.dut_cls.CTRL_SL) as (dut, asserts):
            result   = (dut.r << 1) | dut.si
            asserts += [(dut.o,   result[:self.width]),
                        (dut.so,  dut.r[-1])]

    def test_SR(self):
        with self.assertComputes(self.dut_cls.CTRL_SR) as (dut, asserts):
            result   = (dut.r >> 1) | (dut.si << (self.width - 1))
            asserts += [(dut.o,   result[:self.width]),
                        (dut.so,  dut.r[0])]


class ALSRU_4LUT_TestCase(ALSRUTestCase, unittest.TestCase):
    dut_cls = ALSRU_4LUT
