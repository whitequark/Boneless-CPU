from .opcode import *


__all__ = ["disassemble"]


def bits(word, start, end=None, sign=False):
    if end is None:
        end = start + 1
    value = (word >> start) & ((1 << (end - start)) - 1)
    if sign and value & (1 << (end - start - 1)):
        return -((1 << (end - start)) - value)
    else:
        return value


def disassemble(insn, python=False):
    if python:
        l, r = "()"
    else:
        l = r = ""

    i_class = bits(insn, 12, 16)
    i_code1 = bits(insn, 11, 12)
    i_code2 = bits(insn, 11, 13)
    i_code3 = bits(insn, 11, 14)
    i_code5 = bits(insn, 11, 16)
    i_type1 = bits(insn, 0, 1)
    i_type2 = bits(insn, 0, 2)
    i_shift = bits(insn, 1, 5)
    i_imm5  = bits(insn, 0, 5, sign=True)
    i_imm8  = bits(insn, 0, 8, sign=True)
    i_imm11 = bits(insn, 0, 11, sign=True)
    i_regX  = bits(insn, 2, 5)
    i_regY  = bits(insn, 5, 8)
    i_regZ  = bits(insn, 8, 11)
    i_store = bits(insn, 11)
    i_ext   = bits(insn, 12)
    i_flag  = bits(insn, 11)
    i_cond  = bits(insn, 12, 15)

    if insn == 0x0000:
        return "NOP  {}{}".format(l, r)

    if i_code5 == OPCODE_LOGIC:
        if i_type2 == OPTYPE_AND:
            return "AND  {}R{}, R{}, R{}{}".format(l, i_regZ, i_regY, i_regX, r)
        if i_type2 == OPTYPE_OR:
            return "OR   {}R{}, R{}, R{}{}".format(l, i_regZ, i_regY, i_regX, r)
        if i_type2 == OPTYPE_XOR:
            return "XOR  {}R{}, R{}, R{}{}".format(l, i_regZ, i_regY, i_regX, r)
    if i_code5 == OPCODE_ARITH:
        if i_type2 == OPTYPE_ADD:
            return "ADD  {}R{}, R{}, R{}{}".format(l, i_regZ, i_regY, i_regX, r)
        if i_type2 == OPTYPE_SUB:
            return "SUB  {}R{}, R{}, R{}{}".format(l, i_regZ, i_regY, i_regX, r)
        if i_type2 == OPTYPE_CMP:
            return "CMP  {}R{}, R{}{}".format(l, i_regY, i_regX, r)
    if i_code5 == OPCODE_SHIFT_L:
        if i_type1 == OPTYPE_SLL:
            return "SLL  {}R{}, R{}, {}{}".format(l, i_regZ, i_regY, i_shift, r)
        if i_type1 == OPTYPE_ROT:
            return "ROT  {}R{}, R{}, {}{}".format(l, i_regZ, i_regY, i_shift, r)
    if i_code5 == OPCODE_SHIFT_R:
        if i_type1 == OPTYPE_SRL:
            return "SRL  {}R{}, R{}, {}{}".format(l, i_regZ, i_regY, i_shift, r)
        if i_type1 == OPTYPE_SRA:
            return "SRA  {}R{}, R{}, {}{}".format(l, i_regZ, i_regY, i_shift, r)
    if i_code5 == OPCODE_LD:
        return "LD   {}R{}, R{}, {:+}{}".format(l, i_regZ, i_regY, i_imm5, r)
    if i_code5 == OPCODE_ST:
        return "ST   {}R{}, R{}, {:+}{}".format(l, i_regZ, i_regY, i_imm5, r)
    if i_code5 == OPCODE_LDX:
        return "LDX  {}R{}, R{}, {:+}{}".format(l, i_regZ, i_regY, i_imm5, r)
    if i_code5 == OPCODE_STX:
        return "STX  {}R{}, R{}, {:+}{}".format(l, i_regZ, i_regY, i_imm5, r)
    if i_code5 == OPCODE_MOVL:
        return "MOVL {}R{}, {}{}".format(l, i_regZ, i_imm8 & 0xff, r)
    if i_code5 == OPCODE_MOVH:
        return "MOVH {}R{}, {}{}".format(l, i_regZ, i_imm8 & 0xff, r)
    if i_code5 == OPCODE_MOVA:
        return "MOVA {}R{}, {:+}{}".format(l, i_regZ, i_imm8, r)
    if i_code5 == OPCODE_ADDI:
        return "ADDI {}R{}, {}{}".format(l, i_regZ, i_imm8, r)
    if i_code5 == OPCODE_LDI:
        return "LDI  {}R{}, {:+}{}".format(l, i_regZ, i_imm8, r)
    if i_code5 == OPCODE_STI:
        return "STI  {}R{}, {:+}{}".format(l, i_regZ, i_imm8, r)
    if i_code5 == OPCODE_JAL:
        return "JAL  {}R{}, {:+}{}".format(l, i_regZ, i_imm8, r)
    if i_code5 == OPCODE_JR:
        return "JR   {}R{}, {:+}{}".format(l, i_regZ, i_imm8, r)
    if i_code5 == OPCODE_J:
        return "J    {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JNZ:
        return "JNZ  {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JZ:
        return "JZ   {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JNS:
        return "JNS  {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JS:
        return "JS   {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JNO:
        return "JNO  {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JO:
        return "JO   {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JULT:
        return "JULT {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JUGE:
        return "JUGE {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JUGT:
        return "JUGT {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JULE:
        return "JULE {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JSGE:
        return "JSGE {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JSLT:
        return "JSLT {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JSGT:
        return "JSGT {}{:+}{}".format(l, i_imm11, r)
    if i_code5 == OPCODE_JSLE:
        return "JSLE {}{:+}{}".format(l, i_imm11, r)

    return "ILL  {}0x{:04x}{}".format(l, insn, r)


def main():
    import fileinput
    for line in fileinput.input():
        print(disassemble(int(line, 16)), flush=True)


if __name__ == "__main__":
    main()
