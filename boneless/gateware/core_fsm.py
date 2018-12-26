from nmigen.compat import *

from ..arch.opcode import *
from ..arch.instr import *
from .formal import *


__all__ = ["BonelessCore"]


def AddSignedImm(v, i):
    i_nbits, i_sign = value_bits_sign(i)
    if i_nbits > v.nbits:
        return v + i
    else:
        return v + Cat(i, Replicate(i[i_nbits - 1], v.nbits - i_nbits))


class _StubMemoryPort(Module):
    def __init__(self, name):
        self.adr   = Signal(16, name=name + "_adr")
        self.re    = Signal(1,  name=name + "_re")
        self.dat_r = Signal(16, name=name + "_dat_r")
        self.we    = Signal(1,  name=name + "_we")
        self.dat_w = Signal(16, name=name + "_dat_w")


class _ALU(Module):
    SEL_AND = 0b1000
    SEL_OR  = 0b1001
    SEL_XOR = 0b1010
    SEL_ADD = 0b0011
    SEL_SUB = 0b0111

    def __init__(self, width):
        self.s_a   = Signal(width)
        self.s_b   = Signal(width)
        self.s_o   = Signal(width + 1)

        self.c_sel = Signal(4)

        ###

        # The following mux tree is optimized for 4-LUTs, and fits into the optimal 49 4-LUTs
        # on iCE40 using synth_ice40 with -relut:
        #  * 16 LUTs for A / A*B / A+B / A⊕B selector
        #  * 16 LUTs for B / ~B selector
        #  * 17 LUTs for adder / passthrough selector
        # The mux tree is 3 levels deep.
        s_m3n0 = Signal(width)
        s_m3n1 = Signal(width)
        s_m2n0 = Signal(width)
        s_m2n1 = Signal(width)
        s_m1n0 = Signal(width + 1)
        self.comb += [
            s_m3n0.eq(Mux(self.c_sel[0], self.s_a | self.s_b, self.s_a & self.s_b)),
            s_m3n1.eq(Mux(self.c_sel[0], self.s_a,            self.s_a ^ self.s_b)),
            s_m2n0.eq(Mux(self.c_sel[1], s_m3n1, s_m3n0)),
            s_m2n1.eq(Mux(self.c_sel[2], ~self.s_b, self.s_b)),
            s_m1n0.eq(Mux(self.c_sel[3], s_m2n0, s_m2n0 + s_m2n1 + self.c_sel[2])),
            self.s_o.eq(s_m1n0),
        ]


class _SRU(Module):
    DIR_L = 0b0
    DIR_R = 0b1

    def __init__(self, width):
        self.s_i   = Signal(width)
        self.s_c   = Signal()
        self.r_o   = Signal(width)

        self.c_ld  = Signal()
        self.c_dir = Signal()

        ###

        # The following mux tree is optimized for 4-LUTs, and fits into the optimal 32 4-LUTs
        # and 16 DFFs on iCE40 using synth_ice40.
        # The mux tree is 2 levels deep.
        s_l    = Signal(width)
        s_r    = Signal(width)
        s_m2n0 = Signal(width)
        s_m1n0 = Signal(width)
        self.comb += [
            s_l.eq(Cat(self.s_c,     self.r_o[:-1])),
            s_r.eq(Cat(self.r_o[1:], self.s_c     )),
            s_m2n0.eq(Mux(self.c_dir, s_r, s_l)),
            s_m1n0.eq(Mux(self.c_ld, self.s_i, s_m2n0)),
        ]
        self.sync += self.r_o.eq(s_m1n0)


class BonelessCoreFSM(Module):
    def __init__(self, reset_addr, mem_rdport, mem_wrport, ext_port=None):
        self.formal = fi = BonelessFormalInterface()

        if ext_port is None:
            ext_port = _StubMemoryPort("ext")

        def decode(v):
            d = Signal.like(v, src_loc_at=1)
            self.comb += d.eq(v)
            return d

        mem_r_a = mem_rdport.adr
        mem_r_d = mem_rdport.dat_r
        mem_re  = mem_rdport.re
        mem_w_a = mem_wrport.adr
        mem_w_d = mem_wrport.dat_w
        mem_we  = mem_wrport.we
        self.comb += [
            fi.mem_w_addr.eq(mem_wrport.adr),
            fi.mem_w_data.eq(mem_wrport.dat_w),
            fi.mem_w_en.eq(mem_wrport.we),
        ]

        ext_r_a = ext_port.adr
        ext_r_d = ext_port.dat_r
        ext_re  = ext_port.re
        ext_w_a = ext_port.adr
        ext_w_d = ext_port.dat_w
        ext_we  = ext_port.we
        self.comb += [
            fi.ext_addr.eq(ext_port.adr),
            fi.ext_r_data.eq(ext_port.dat_r),
            fi.ext_r_en.eq(ext_port.re),
            fi.ext_w_data.eq(ext_port.dat_w),
            fi.ext_w_en.eq(ext_port.we),
        ]

        pc_bits = max(mem_r_a.nbits, mem_w_a.nbits)

        r_insn  = Signal(16)
        r_pc    = Signal(pc_bits, reset=reset_addr)
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

        s_insn  = self.s_insn = Signal(16)
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
        self.comb += [
            Case(Cat(i_cond, C(1, 1)), {
                OPCODE_F_0:     s_cond.eq(0),
                OPCODE_F_Z:     s_cond.eq(r_z),
                OPCODE_F_S:     s_cond.eq(r_s),
                OPCODE_F_V:     s_cond.eq(r_v),
                OPCODE_F_C:     s_cond.eq(r_c),
                OPCODE_F_NCoZ:  s_cond.eq(~r_c | r_z),
                OPCODE_F_SxV:   s_cond.eq(r_s ^ r_v),
                OPCODE_F_SxVoZ: s_cond.eq((r_s ^ r_v) | r_z),
            })
        ]

        s_z     = Signal()
        s_s     = Signal()
        s_c     = Signal()
        s_v     = Signal()
        s_sub   = Signal()
        s_cmp   = Signal()
        c_flags = Signal()
        self.comb += [
            s_z.eq(s_res[0:16] == 0),
            s_s.eq(s_res[15]),
            s_c.eq(s_res[16]),
            # http://teaching.idallen.com/cst8214/08w/notes/overflow.txt
            Case(Cat(s_sub | s_cmp, r_opA[15], s_opB[15], s_res[15]), {
                0b1000: s_v.eq(1),
                0b0110: s_v.eq(1),
                0b1101: s_v.eq(1),
                0b0011: s_v.eq(1),
                "default": s_v.eq(0),
            }),
        ]
        self.sync += [
            If(c_flags,
                Cat(r_z, r_s, r_c, r_v).eq(Cat(s_z, s_s, s_c, s_v)),
            )
        ]
        self.comb += [
            If(c_flags,
                fi.flags.eq(Cat(s_z, s_s, s_c, s_v)),
            ).Else(
                fi.flags.eq(Cat(r_z, r_s, r_c, r_v)),
            )
        ]

        self.submodules.alu = alu = _ALU(width=16)
        self.comb += [
            alu.s_a.eq(r_opA),
            alu.s_b.eq(s_opB),
            Case(Cat(i_code5), {
                OPCODE_LOGIC: Case(i_type2, {
                    OPTYPE_AND:  alu.c_sel.eq(alu.SEL_AND),
                    OPTYPE_OR:   alu.c_sel.eq(alu.SEL_OR),
                    OPTYPE_XOR:  alu.c_sel.eq(alu.SEL_XOR),
                }),
                OPCODE_ARITH: Case(i_type2, {
                    OPTYPE_ADD:  alu.c_sel.eq(alu.SEL_ADD),
                    OPTYPE_SUB: [alu.c_sel.eq(alu.SEL_SUB), s_sub.eq(1)],
                    OPTYPE_CMP: [alu.c_sel.eq(alu.SEL_SUB), s_cmp.eq(1)],
                }),
                OPCODE_ADDI:     alu.c_sel.eq(alu.SEL_ADD),
            }),
        ]

        self.submodules.sru = sru = _SRU(width=16)
        self.comb += [
            sru.s_i.eq(mem_r_d),
        ]

        self.comb += [
            mem_re.eq(1),
        ]

        self.submodules.fsm = FSM(reset_state="FETCH")
        self.fsm.act("FETCH",
            mem_r_a.eq(r_pc),
            NextValue(fi.pc, r_pc),
            NextValue(r_pc, r_pc + 1),
            NextState("DECODE/LOAD/JUMP")
        )
        self.comb += [
            s_insn.eq(Mux(self.fsm.ongoing("DECODE/LOAD/JUMP"), mem_r_d, r_insn)),
            fi.insn.eq(s_insn),
        ]
        self.fsm.act("DECODE/LOAD/JUMP",
            NextValue(r_insn, mem_r_d),
            If(i_clsA,
                mem_r_a.eq(Cat(i_regY, r_win)),
                NextState("A-READ")
            ).Elif(i_clsS,
                mem_r_a.eq(Cat(i_regY, r_win)),
                NextState("S-READ")
            ).Elif(i_clsM,
                mem_r_a.eq(Cat(i_regY, r_win)),
                If(~i_store,
                    NextState("M/I-LOAD-1")
                ).Else(
                    NextState("M/I-STORE-1")
                )
            ).Elif(i_clsI,
                mem_r_a.eq(Cat(i_regZ, r_win)),
                Case(Cat(i_code3, C(OPCLASS_I, 2)), {
                    OPCODE_MOVL: NextState("I-EXECUTE-MOVx"),
                    OPCODE_MOVH: NextState("I-EXECUTE-MOVx"),
                    OPCODE_MOVA: NextState("I-EXECUTE-MOVx"),
                    OPCODE_ADDI: NextState("I-EXECUTE-ADDI-1"),
                    OPCODE_LDI:  NextState("M/I-LOAD-1"),
                    OPCODE_STI:  NextState("M/I-STORE-1"),
                    OPCODE_JAL:  NextState("I-EXECUTE-JAL"),
                    OPCODE_JR:   NextState("I-EXECUTE-JR"),
                })
            ).Elif(i_clsC,
                If(s_cond == i_flag,
                    NextValue(r_pc, AddSignedImm(r_pc, i_imm11))
                ),
                fi.stb.eq(1),
                NextState("FETCH")
            )
        )
        self.fsm.act("A-READ",
            mem_r_a.eq(Cat(i_regX, r_win)),
            NextValue(r_opA, mem_r_d),
            NextState("A-EXECUTE")
        )
        self.fsm.act("A-EXECUTE",
            s_opB.eq(mem_r_d),
            s_res.eq(alu.s_o),
            mem_w_a.eq(Cat(i_regZ, r_win)),
            mem_w_d.eq(s_res),
            mem_we.eq(~s_cmp),
            c_flags.eq(1),
            fi.stb.eq(1),
            NextState("FETCH")
        )
        self.fsm.act("S-READ",
            sru.c_ld.eq(1),
            NextValue(r_shift, i_shift),
            NextState("S-EXECUTE")
        )
        self.fsm.act("S-EXECUTE",
            Case(Cat(i_code1, C(OPCLASS_S, 4)), {
                OPCODE_SHIFT_L: Case(i_type1, {
                    OPTYPE_SLL: [sru.c_dir.eq(sru.DIR_L), sru.s_c.eq(0)],
                    OPTYPE_ROT: [sru.c_dir.eq(sru.DIR_L), sru.s_c.eq(sru.r_o[-1])],
                }),
                OPCODE_SHIFT_R: Case(i_type1, {
                    OPTYPE_SRL: [sru.c_dir.eq(sru.DIR_R), sru.s_c.eq(0)],
                    OPTYPE_SRA: [sru.c_dir.eq(sru.DIR_R), sru.s_c.eq(sru.r_o[-1])],
                })
            }),
            s_res.eq(sru.r_o),
            mem_w_a.eq(Cat(i_regZ, r_win)),
            mem_w_d.eq(s_res),
            c_flags.eq(1),
            NextValue(r_shift, r_shift - 1),
            If(r_shift == 0,
                mem_we.eq(1),
                fi.stb.eq(1),
                NextState("FETCH")
            )
        )
        self.fsm.act("M/I-LOAD-1",
            If(i_clsI,
                s_addr.eq(AddSignedImm(r_pc, i_imm8))
            ).Else(
                s_addr.eq(AddSignedImm(mem_r_d, i_imm5))
            ),
            mem_r_a.eq(s_addr),
            ext_r_a.eq(s_addr),
            ext_re.eq(i_ext),
            NextState("M/I-LOAD-2")
        )
        self.fsm.act("M/I-LOAD-2",
            mem_w_a.eq(Cat(i_regZ, r_win)),
            mem_w_d.eq(Mux(i_ext, ext_r_d, mem_r_d)),
            mem_we.eq(1),
            fi.stb.eq(1),
            NextState("FETCH")
        )
        self.fsm.act("M/I-STORE-1",
            If(i_clsI,
                NextValue(r_addr, AddSignedImm(r_pc, i_imm8))
            ).Else(
                NextValue(r_addr, AddSignedImm(mem_r_d, i_imm5))
            ),
            mem_r_a.eq(Cat(i_regZ, r_win)),
            NextState("M/I-STORE-2")
        )
        self.fsm.act("M/I-STORE-2",
            mem_w_a.eq(r_addr),
            mem_w_d.eq(mem_r_d),
            mem_we.eq(~i_ext),
            ext_w_a.eq(r_addr),
            ext_w_d.eq(mem_r_d),
            ext_we.eq(i_ext),
            fi.stb.eq(1),
            NextState("FETCH")
        )
        self.fsm.act("I-EXECUTE-MOVx",
            mem_w_a.eq(Cat(i_regZ, r_win)),
            Case(Cat(i_code2, C(0b0, 1), C(OPCLASS_I, 2)), {
                OPCODE_MOVL:  mem_w_d.eq(Cat(i_imm8, C(0, 8))),
                OPCODE_MOVH:  mem_w_d.eq(Cat(C(0, 8), i_imm8)),
                OPCODE_MOVA:  mem_w_d.eq(AddSignedImm(r_pc, i_imm8)),
            }),
            mem_we.eq(1),
            fi.stb.eq(1),
            NextState("FETCH")
        )
        self.fsm.act("I-EXECUTE-ADDI-1",
            NextValue(r_opA, mem_r_d),
            NextState("I-EXECUTE-ADDI-2")
        )
        self.fsm.act("I-EXECUTE-ADDI-2",
            s_opB.eq(Cat(i_imm8, Replicate(i_imm8[7], 8))),
            s_res.eq(alu.s_o),
            mem_w_a.eq(Cat(i_regZ, r_win)),
            mem_w_d.eq(s_res),
            mem_we.eq(1),
            c_flags.eq(1),
            fi.stb.eq(1),
            NextState("FETCH")
        )
        self.fsm.act("I-EXECUTE-JAL",
            mem_w_a.eq(Cat(i_regZ, r_win)),
            mem_w_d.eq(r_pc),
            mem_we.eq(1),
            NextValue(r_pc, AddSignedImm(r_pc, i_imm8)),
            fi.stb.eq(1),
            NextState("FETCH")
        )
        self.fsm.act("I-EXECUTE-JR",
            NextValue(r_pc, AddSignedImm(mem_r_d, i_imm8)),
            fi.stb.eq(1),
            NextState("FETCH")
        )

# -------------------------------------------------------------------------------------------------

import argparse
from nmigen import cli


class BonelessFSMTestbench(Module):
    def __init__(self, has_pins=False):
        self.submodules.ext_port = _StubMemoryPort("ext")

        if has_pins:
            self.pins = Signal(16)
            self.sync += [
                If(self.ext_port.adr == 0,
                    If(self.ext_port.re,
                        self.ext_port.dat_r.eq(self.pins)
                    ),
                    If(self.ext_port.we,
                        self.pins.eq(self.ext_port.dat_w)
                    )
                )
            ]

        self.specials.mem = Memory(width=16, depth=256)
        self.mem.init = [
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

        self.specials.mem_rdport = self.mem.get_port(has_re=True, mode=READ_FIRST)
        self.specials.mem_wrport = self.mem.get_port(write_capable=True)
        self.submodules.core = BonelessCoreFSM(reset_addr=8,
            mem_rdport=self.mem_rdport,
            mem_wrport=self.mem_wrport,
            ext_port  =self.ext_port)


class BonelessFSMFormal(Module):
    def __init__(self):
        self.submodules.ext_port   = _StubMemoryPort("ext")
        self.submodules.mem_rdport = _StubMemoryPort("mem_r")
        self.submodules.mem_wrport = _StubMemoryPort("mem_w")
        self.submodules.core = BonelessCoreFSM(reset_addr=8,
            mem_rdport=self.mem_rdport,
            mem_wrport=self.mem_wrport,
            ext_port  =self.ext_port)


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
        ios = (tb.ext_port.adr,
               tb.ext_port.re, tb.ext_port.dat_r,
               tb.ext_port.we, tb.ext_port.dat_w)

    if args.type == "pins":
        tb  = BonelessFSMTestbench(has_pins=True)
        ios = (tb.pins,)

    if args.type == "formal":
        tb  = BonelessFSMFormal()
        ios = tb.core.formal._all + [
            tb.mem_rdport.adr, tb.mem_rdport.dat_r, tb.mem_rdport.re,
            tb.mem_wrport.adr, tb.mem_wrport.dat_w, tb.mem_wrport.we,
            tb.ext_port.adr,   tb.ext_port.dat_r, tb.ext_port.re,
                               tb.ext_port.dat_w, tb.ext_port.we,
        ]

    cli.main_runner(parser, args, tb.get_fragment(), name="boneless", ports=ios)
