from nmigen import *

from ..arch.opcode import *
from ..arch.instr import *
from .formal import *


__all__ = ["BonelessCore"]


def AddSignedImm(v, i):
    i_nbits, i_sign = i.shape()
    if i_nbits > v.nbits:
        return v + i
    else:
        return v + Cat(i, Repl(i[i_nbits - 1], v.nbits - i_nbits))


class _MemoryPort(Elaboratable):
    def __init__(self, name):
        self.addr = Signal(16, name=name + "_addr")
        self.en   = Signal(1,  name=name + "_en")
        self.data = Signal(16, name=name + "_data")

    def elaborate(self, platform):
        return Fragment()


class _ExternalPort(Elaboratable):
    def __init__(self):
        self.addr   = Signal(16, name="ext_addr")
        self.r_en   = Signal(1,  name="ext_r_en")
        self.r_data = Signal(16, name="ext_r_data")
        self.w_en   = Signal(1,  name="ext_w_en")
        self.w_data = Signal(16, name="ext_w_data")

    def elaborate(self, platform):
        return Fragment()


class _ALU(Elaboratable):
    SEL_AND = 0b1000
    SEL_OR  = 0b1001
    SEL_XOR = 0b1010
    SEL_ADD = 0b0011
    SEL_SUB = 0b0111

    def __init__(self, width):
        self.width = width

        self.s_a   = Signal(width)
        self.s_b   = Signal(width)
        self.s_o   = Signal(width + 1)

        self.c_sel = Signal(4)

    def elaborate(self, platform):
        # The following mux tree is optimized for 4-LUTs, and fits into the optimal 49 4-LUTs
        # on iCE40 using synth_ice40 with -relut:
        #  * 16 LUTs for A / A*B / A+B / A⊕B selector
        #  * 16 LUTs for B / ~B selector
        #  * 17 LUTs for adder / passthrough selector
        # The mux tree is 3 levels deep.
        s_m3n0 = Signal(self.width)
        s_m3n1 = Signal(self.width)
        s_m2n0 = Signal(self.width)
        s_m2n1 = Signal(self.width)
        s_m1n0 = Signal(self.width + 1)
        m = Module()
        m.d.comb += [
            s_m3n0.eq(Mux(self.c_sel[0], self.s_a | self.s_b, self.s_a & self.s_b)),
            s_m3n1.eq(Mux(self.c_sel[0], self.s_a,            self.s_a ^ self.s_b)),
            s_m2n0.eq(Mux(self.c_sel[1], s_m3n1, s_m3n0)),
            s_m2n1.eq(Mux(self.c_sel[2], ~self.s_b, self.s_b)),
            s_m1n0.eq(Mux(self.c_sel[3], s_m2n0, s_m2n0 + s_m2n1 + self.c_sel[2])),
            self.s_o.eq(s_m1n0),
        ]
        return m


class _SRU(Elaboratable):
    DIR_L = 0b0
    DIR_R = 0b1

    def __init__(self, width):
        self.width = width

        self.s_i   = Signal(width)
        self.s_c   = Signal()
        self.r_o   = Signal(width)

        self.c_ld  = Signal()
        self.c_dir = Signal()

    def elaborate(self, platform):
        # The following mux tree is optimized for 4-LUTs, and fits into the optimal 32 4-LUTs
        # and 16 DFFs on iCE40 using synth_ice40.
        # The mux tree is 2 levels deep.
        s_l    = Signal(self.width)
        s_r    = Signal(self.width)
        s_m2n0 = Signal(self.width)
        s_m1n0 = Signal(self.width)
        m = Module()
        m.d.comb += [
            s_l.eq(Cat(self.s_c,     self.r_o[:-1])),
            s_r.eq(Cat(self.r_o[1:], self.s_c     )),
            s_m2n0.eq(Mux(self.c_dir, s_r, s_l)),
            s_m1n0.eq(Mux(self.c_ld, self.s_i, s_m2n0)),
        ]
        m.d.sync += self.r_o.eq(s_m1n0)
        return m


class BonelessCoreFSM(Elaboratable):
    def __init__(self, reset_addr, mem_rdport, mem_wrport, ext_port=None):
        self.reset_addr = reset_addr

        self.mem_rdport = mem_rdport
        self.mem_wrport = mem_wrport
        self.ext_port   = ext_port or _ExternalPort()

        self.formal     = BonelessFormalInterface(self.mem_wrport, self.ext_port)

        self.halted     = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules.formal = self.formal

        def decode(v):
            d = Signal.like(v, src_loc_at=1)
            m.d.comb += d.eq(v)
            return d

        fi      = self.formal
        mem_r   = self.mem_rdport
        mem_w   = self.mem_wrport
        ext     = self.ext_port

        pc_bits = max(mem_r.addr.nbits, mem_w.addr.nbits)

        r_insn  = Signal(16)
        r_pc    = Signal(pc_bits, reset=self.reset_addr)
        r_win   = Signal(max(pc_bits - 3, 1))
        r_z     = Signal()
        r_s     = Signal()
        r_c     = Signal()
        r_v     = Signal()

        r_opA   = Signal(16)
        s_opB   = Signal(16)
        r_shift = Signal(5)
        s_res   = Signal(17)

        s_addr  = Signal(16)
        r_addr  = Signal(16)

        s_insn  = Signal(16)
        m.d.comb += [
            self.halted.eq(s_insn == J(-1)[0]),
            fi.insn.eq(s_insn),
        ]

        i_type1 = decode(s_insn[0:1])
        i_type2 = decode(s_insn[0:2])
        i_shift = decode(s_insn[1:5])
        i_imm5  = decode(s_insn[0:5])
        i_imm8  = decode(s_insn[0:8])
        i_imm11 = decode(s_insn[0:11])
        i_regX  = decode(s_insn[2:5])
        i_regY  = decode(s_insn[5:8])
        i_regZ  = decode(s_insn[8:11])
        i_code1 = decode(s_insn[11:12])
        i_code2 = decode(s_insn[11:13])
        i_code3 = decode(s_insn[11:14])
        i_code5 = decode(s_insn[11:16])
        i_store = decode(s_insn[11])
        i_ext   = decode(s_insn[12])
        i_flag  = decode(s_insn[11])
        i_cond  = decode(s_insn[12:15])

        i_clsA  = decode(i_code5[1:5] == OPCLASS_A)
        i_clsS  = decode(i_code5[1:5] == OPCLASS_S)
        i_clsM  = decode(i_code5[2:5] == OPCLASS_M)
        i_clsI  = decode(i_code5[3:5] == OPCLASS_I)
        i_clsC  = decode(i_code5[4:5] == OPCLASS_C)

        s_cond  = Signal()
        with m.Switch(Cat(i_cond, C(1, 1))):
            with m.Case(OPCODE_F_0):     m.d.comb += s_cond.eq(0)
            with m.Case(OPCODE_F_Z):     m.d.comb += s_cond.eq(r_z)
            with m.Case(OPCODE_F_S):     m.d.comb += s_cond.eq(r_s)
            with m.Case(OPCODE_F_V):     m.d.comb += s_cond.eq(r_v)
            with m.Case(OPCODE_F_C):     m.d.comb += s_cond.eq(r_c)
            with m.Case(OPCODE_F_NCoZ):  m.d.comb += s_cond.eq(~r_c | r_z)
            with m.Case(OPCODE_F_SxV):   m.d.comb += s_cond.eq(r_s ^ r_v)
            with m.Case(OPCODE_F_SxVoZ): m.d.comb += s_cond.eq((r_s ^ r_v) | r_z)

        s_z     = Signal()
        s_s     = Signal()
        s_c     = Signal()
        s_v     = Signal()
        s_sub   = Signal()
        s_cmp   = Signal()
        c_flags = Signal()
        m.d.comb += [
            s_z.eq(s_res[0:16] == 0),
            s_s.eq(s_res[15]),
            s_c.eq(s_res[16]),
        ]
        # http://teaching.idallen.com/cst8214/08w/notes/overflow.txt
        with m.Switch(Cat(s_sub | s_cmp, r_opA[15], s_opB[15], s_res[15])):
            with m.Case(0b1000): m.d.comb += s_v.eq(1)
            with m.Case(0b0110): m.d.comb += s_v.eq(1)
            with m.Case(0b1101): m.d.comb += s_v.eq(1)
            with m.Case(0b0011): m.d.comb += s_v.eq(1)

        m.d.comb += fi.flags.eq(Cat(r_z, r_s, r_c, r_v))
        with m.If(c_flags):
            m.d.sync += Cat(r_z, r_s, r_c, r_v).eq(Cat(s_z, s_s, s_c, s_v))
            m.d.comb += fi.flags.eq(Cat(s_z, s_s, s_c, s_v))

        m.submodules.alu = alu = _ALU(width=16)
        m.d.comb += [
            alu.s_a.eq(r_opA),
            alu.s_b.eq(s_opB),
        ]
        with m.Switch(i_code5):
            with m.Case(OPCODE_LOGIC):
                with m.Switch(i_type2):
                    with m.Case(OPTYPE_AND):  m.d.comb +=  alu.c_sel.eq(alu.SEL_AND)
                    with m.Case(OPTYPE_OR):   m.d.comb +=  alu.c_sel.eq(alu.SEL_OR)
                    with m.Case(OPTYPE_XOR):  m.d.comb +=  alu.c_sel.eq(alu.SEL_XOR)
            with m.Case(OPCODE_ARITH):
                with m.Switch(i_type2):
                    with m.Case(OPTYPE_ADD):  m.d.comb +=  alu.c_sel.eq(alu.SEL_ADD)
                    with m.Case(OPTYPE_SUB):  m.d.comb += [alu.c_sel.eq(alu.SEL_SUB), s_sub.eq(1)]
                    with m.Case(OPTYPE_CMP):  m.d.comb += [alu.c_sel.eq(alu.SEL_SUB), s_cmp.eq(1)]
            with m.Case(OPCODE_ADDI):
                m.d.comb += alu.c_sel.eq(alu.SEL_ADD)

        m.submodules.sru = sru = _SRU(width=16)
        m.d.comb += [
            sru.s_i.eq(mem_r.data)
        ]

        with m.FSM(reset="FETCH") as fsm:
            with m.State("FETCH"):
                m.d.comb += [
                    mem_r.addr.eq(r_pc),
                    mem_r.en.eq(1),
                ]
                m.d.sync += [
                    fi.pc.eq(r_pc),
                    r_pc.eq(r_pc + 1),
                ]
                m.next = "DECODE/LOAD/JUMP"

            m.d.comb += s_insn.eq(Mux(fsm.ongoing("DECODE/LOAD/JUMP"), mem_r.data, r_insn))
            with m.State("DECODE/LOAD/JUMP"):
                m.d.sync += r_insn.eq(mem_r.data)
                with m.If(i_clsA):
                    m.d.comb += [
                        mem_r.addr.eq(Cat(i_regY, r_win)),
                        mem_r.en.eq(1),
                    ]
                    m.next = "A-READ"

                with m.Elif(i_clsS):
                    m.d.comb += [
                        mem_r.addr.eq(Cat(i_regY, r_win)),
                        mem_r.en.eq(1),
                    ]
                    m.next = "S-READ"

                with m.Elif(i_clsM):
                    m.d.comb += [
                        mem_r.addr.eq(Cat(i_regY, r_win)),
                        mem_r.en.eq(1),
                    ]
                    with m.If(i_store):
                        m.next = "M/I-STORE-1"
                    with m.Else():
                        m.next = "M/I-LOAD-1"

                with m.Elif(i_clsI):
                    m.d.comb += [
                        mem_r.addr.eq(Cat(i_regZ, r_win)),
                        mem_r.en.eq(1),
                    ]
                    with m.Switch(Cat(i_code3, C(OPCLASS_I, 2))):
                        with m.Case(OPCODE_MOVL): m.next = "I-EXECUTE-MOVx"
                        with m.Case(OPCODE_MOVH): m.next = "I-EXECUTE-MOVx"
                        with m.Case(OPCODE_MOVA): m.next = "I-EXECUTE-MOVx"
                        with m.Case(OPCODE_ADDI): m.next = "I-EXECUTE-ADDI-1"
                        with m.Case(OPCODE_LDI):  m.next = "M/I-LOAD-1"
                        with m.Case(OPCODE_STI):  m.next = "M/I-STORE-1"
                        with m.Case(OPCODE_JAL):  m.next = "I-EXECUTE-JAL"
                        with m.Case(OPCODE_JR):   m.next = "I-EXECUTE-JR"

                with m.Elif(i_clsC):
                    with m.If(s_cond == i_flag):
                        m.d.sync += r_pc.eq(AddSignedImm(r_pc, i_imm11))
                    m.d.comb += fi.stb.eq(1)
                    m.next = "FETCH"

            with m.State("A-READ"):
                m.d.comb += [
                    mem_r.addr.eq(Cat(i_regX, r_win)),
                    mem_r.en.eq(1),
                ]
                m.d.sync += [
                    r_opA.eq(mem_r.data),
                ]
                m.next = "A-EXECUTE"
            with m.State("A-EXECUTE"):
                m.d.comb += [
                    s_opB.eq(mem_r.data),
                    s_res.eq(alu.s_o),
                    mem_w.addr.eq(Cat(i_regZ, r_win)),
                    mem_w.data.eq(s_res),
                    mem_w.en.eq(~s_cmp),
                    c_flags.eq(1),
                    fi.stb.eq(1),
                ]
                m.next = "FETCH"

            with m.State("S-READ"):
                m.d.comb += sru.c_ld.eq(1)
                m.d.sync += r_shift.eq(i_shift)
                m.next = "S-EXECUTE"
            with m.State("S-EXECUTE"):
                with m.Switch(Cat(i_code1, C(OPCLASS_S, 4))):
                    with m.Case(OPCODE_SHIFT_L):
                        with m.Switch(i_type1):
                            with m.Case(OPTYPE_SLL):
                                m.d.comb += [sru.c_dir.eq(sru.DIR_L), sru.s_c.eq(0)]
                            with m.Case(OPTYPE_ROT):
                                m.d.comb += [sru.c_dir.eq(sru.DIR_L), sru.s_c.eq(sru.r_o[-1])]
                    with m.Case(OPCODE_SHIFT_R):
                        with m.Switch(i_type1):
                            with m.Case(OPTYPE_SRL):
                                m.d.comb += [sru.c_dir.eq(sru.DIR_R), sru.s_c.eq(0)]
                            with m.Case(OPTYPE_SRA):
                                m.d.comb += [sru.c_dir.eq(sru.DIR_R), sru.s_c.eq(sru.r_o[-1])]
                m.d.comb += [
                    s_res.eq(sru.r_o),
                    mem_w.addr.eq(Cat(i_regZ, r_win)),
                    mem_w.data.eq(s_res),
                    c_flags.eq(1),
                ]
                m.d.sync += r_shift.eq(r_shift - 1)
                with m.If(r_shift == 0):
                    m.d.comb += [
                        mem_w.en.eq(1),
                        fi.stb.eq(1),
                    ]
                    m.next = "FETCH"

            with m.State("M/I-LOAD-1"):
                with m.If(i_clsI):
                    m.d.comb += s_addr.eq(AddSignedImm(r_pc, i_imm8))
                with m.Else():
                    m.d.comb += s_addr.eq(AddSignedImm(mem_r.data, i_imm5))
                m.d.comb += [
                    mem_r.addr.eq(s_addr),
                    mem_r.en.eq(~i_ext),
                    ext.addr.eq(s_addr),
                    ext.r_en.eq(i_ext),
                ]
                m.next = "M/I-LOAD-2"
            with m.State("M/I-LOAD-2"):
                m.d.comb += [
                    mem_w.addr.eq(Cat(i_regZ, r_win)),
                    mem_w.data.eq(Mux(i_ext, ext.r_data, mem_r.data)),
                    mem_w.en.eq(1),
                    fi.stb.eq(1),
                ]
                m.next = "FETCH"

            with m.State("M/I-STORE-1"):
                with m.If(i_clsI):
                    m.d.sync += r_addr.eq(AddSignedImm(r_pc, i_imm8))
                with m.Else():
                    m.d.sync += r_addr.eq(AddSignedImm(mem_r.data, i_imm5))
                m.d.comb += [
                    mem_r.addr.eq(Cat(i_regZ, r_win)),
                    mem_r.en.eq(1),
                ]
                m.next = "M/I-STORE-2"
            with m.State("M/I-STORE-2"):
                m.d.comb += [
                    mem_w.addr.eq(r_addr),
                    mem_w.data.eq(mem_r.data),
                    mem_w.en.eq(~i_ext),
                    ext.addr.eq(r_addr),
                    ext.w_data.eq(mem_r.data),
                    ext.w_en.eq(i_ext),
                    fi.stb.eq(1),
                ]
                m.next ="FETCH"

            with m.State("I-EXECUTE-MOVx"):
                with m.Switch(Cat(i_code2, C(0b0, 1), C(OPCLASS_I, 2))):
                    with m.Case(OPCODE_MOVL): m.d.comb += mem_w.data.eq(Cat(i_imm8, C(0, 8)))
                    with m.Case(OPCODE_MOVH): m.d.comb += mem_w.data.eq(Cat(C(0, 8), i_imm8))
                    with m.Case(OPCODE_MOVA): m.d.comb += mem_w.data.eq(AddSignedImm(r_pc, i_imm8))
                m.d.comb += [
                    mem_w.addr.eq(Cat(i_regZ, r_win)),
                    mem_w.en.eq(1),
                    fi.stb.eq(1),
                ]
                m.next = "FETCH"

            with m.State("I-EXECUTE-ADDI-1"):
                m.d.sync += r_opA.eq(mem_r.data)
                m.next = "I-EXECUTE-ADDI-2"
            with m.State("I-EXECUTE-ADDI-2"):
                m.d.comb += [
                    s_opB.eq(Cat(i_imm8, Repl(i_imm8[7], 8))),
                    s_res.eq(alu.s_o),
                    mem_w.addr.eq(Cat(i_regZ, r_win)),
                    mem_w.data.eq(s_res),
                    mem_w.en.eq(1),
                    c_flags.eq(1),
                    fi.stb.eq(1),
                ]
                m.next = "FETCH"

            with m.State("I-EXECUTE-JAL"):
                m.d.comb += [
                    mem_w.addr.eq(Cat(i_regZ, r_win)),
                    mem_w.data.eq(r_pc),
                    mem_w.en.eq(1),
                    fi.stb.eq(1),
                ]
                m.d.sync += r_pc.eq(AddSignedImm(r_pc, i_imm8))
                m.next = "FETCH"

            with m.State("I-EXECUTE-JR"):
                m.d.comb += [
                    fi.stb.eq(1),
                ]
                m.d.sync += r_pc.eq(AddSignedImm(mem_r.data, i_imm8))
                m.next = "FETCH"

        return m

# -------------------------------------------------------------------------------------------------

import argparse
from nmigen import cli


class BonelessFSMTestbench(Elaboratable):
    def __init__(self, has_pins=False):
        self.memory   = Memory(width=16, depth=256)
        self.ext_port = _ExternalPort()
        self.pins     = Signal(16, name="pins") if has_pins else None

        self.memory.init = [
            0, 0, 0, 0, 0, 0, 0, 0,
            *assemble([
                NOP (),
                NOP (),
            "init",
                MOVL(R1, 1),
            "loop",
                ROT (R1, R1, 1),
                MOVL(R7, 0b10000),
                CMP (R1, R7),
                JE  ("init"),
                MOVH(R2, 255),
            "breathe",
                SRL (R3, R2, 8),
                MOVL(R7, 0xff),
                AND (R4, R2, R7),
                MOVH(R7, 0x80),
                AND (R7, R7, R2),
                JNZ ("pwm"),
                XCHG(R3, R4),
            "pwm",
                CMP (R3, R4),
                JULT("pwmon"),
            "pwmoff",
                STX (R0, R0, 0),
                J   ("pwmdone"),
            "pwmon",
                STX (R1, R0, 0),
            "pwmdone",
                SUBI(R2, 1),
                JNZ ("breathe"),
                J   ("loop"),
            ])
        ]

    def elaborate(self, platform):
        m = Module()

        if self.pins is not None:
            with m.If(self.ext_port.addr == 0):
                with m.If(self.ext_port.r_en):
                    m.d.sync += self.ext_port.r_data.eq(self.pins)
                with m.If(self.ext_port.w_en):
                    m.d.sync += self.pins.eq(self.ext_port.w_data)

        m.submodules.mem_rdport = mem_rdport = self.memory.read_port(transparent=False)
        m.submodules.mem_rdport = mem_wrport = self.memory.write_port()
        m.submodules.core = BonelessCoreFSM(reset_addr=8,
            mem_rdport=mem_rdport,
            mem_wrport=mem_wrport,
            ext_port  =self.ext_port)
        return m


class BonelessFSMFormal(Elaboratable):
    def __init__(self):
        self.mem_rdport = _MemoryPort("mem_r")
        self.mem_wrport = _MemoryPort("mem_w")
        self.ext_port   = _ExternalPort()
        self.core = BonelessCoreFSM(reset_addr=8,
            mem_rdport=self.mem_rdport,
            mem_wrport=self.mem_wrport,
            ext_port  =self.ext_port)

    def elaborate(self, platform):
        m = Module()
        m.submodules += self.mem_rdport, self.mem_wrport, self.core
        return m.lower(platform)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "type", choices=["alu", "sru", "bus", "pins", "formal"], default="bus")
    cli.main_parser(parser)

    args = parser.parse_args()

    if args.type == "alu":
        tb  = _ALU(16)
        ios = (tb.s_a, tb.s_b, tb.s_o, tb.c_sel)

    if args.type == "sru":
        tb  = _SRU(16)
        ios = (tb.s_i, tb.s_c, tb.r_o, tb.c_ld, tb.c_dir)

    if args.type == "bus":
        tb  = BonelessFSMTestbench()
        ios = (tb.ext_port.addr,
               tb.ext_port.r_en, tb.ext_port.r_data,
               tb.ext_port.w_en, tb.ext_port.w_data)

    if args.type == "pins":
        tb  = BonelessFSMTestbench(has_pins=True)
        ios = (tb.pins)

    if args.type == "formal":
        tb  = BonelessFSMFormal()
        ios = tb.core.formal._all + [
            tb.mem_rdport.addr, tb.mem_rdport.data, tb.mem_rdport.en,
            tb.mem_wrport.addr, tb.mem_wrport.data, tb.mem_wrport.en,
            tb.ext_port.addr,   tb.ext_port.r_data, tb.ext_port.r_en,
                                tb.ext_port.w_data, tb.ext_port.w_en,
        ]

    cli.main_runner(parser, args, tb, name="boneless", ports=ios)
