from boneless.arch.instr import *
from boneless.arch.disasm import disassemble
from asm import Assembler

f = open("base.asm")
li = f.readlines()
f.close()

code = Assembler(debug=False)
code.assemble(li)
code.display()

assembled = code.code

original = [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    *assemble(
        [
            NOP(),
            NOP(),
            "init",
            MOVL(R1, 1),
            "loop",
            ROT(R1, R1, 1),
            MOVL(R7, 0b10000),
            CMP(R1, R7),
            JE("init"),
            MOVH(R2, 255),
            "breathe",
            SRL(R3, R2, 8),
            MOVL(R7, 0xff),
            AND(R4, R2, R7),
            MOVH(R7, 0x80),
            AND(R7, R7, R2),
            JNZ("pwm"),
            XCHG(R3, R4),
            "pwm",
            CMP(R3, R4),
            JULT("pwmon"),
            "pwmoff",
            STX(R0, R0, 0),
            J("pwmdone"),
            "pwmon",
            STX(R1, R0, 0),
            "pwmdone",
            SUBI(R2, 1),
            JNZ("breathe"),
            J("loop"),
        ]
    ),
]

for i,j in enumerate(original):
    if original[i] != assembled[i]:
        print("----------------- error ----------------")
    print(disassemble(original[i]).ljust(30),'-',disassemble(assembled[i]).ljust(30))
