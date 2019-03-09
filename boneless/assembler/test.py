from boneless.arch.instr import *
from boneless.arch.disasm import disassemble
from asm import Assembler

as_string = """
    NOP
    NOP
init:
    MOVL R1, 1
loop:
    ROT R1, R1, 1
    MOVL R7, 0b10000
    CMP R1, R7
    JE  init
    MOVH R2, 255
breathe:
    SRL R3, R2, 8
    MOVL R7, 0xff
    AND R4, R2, R7
    MOVH R7, 0x80
    AND R7, R7, R2
    JNZ pwm
    XCHG R3, R4
pwm:
    CMP R3, R4
    JULT pwmon
pwmoff:
    STX R0, R0, 0
    J pwmdone
pwmon:
    STX R1, R0, 0
pwmdone:
    SUBI R2, 1
    JNZ breathe
    J loop
"""

code = Assembler(debug=True, data=as_string)
code.assemble()
print("---------- display ---------")
code.display()
print("---------- display end  ---------")
print()
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
            MOVL(R7, 0xFF),
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
print("---------------------- compare ----------------")
for i, j in enumerate(original):
    if original[i] != assembled[i]:
        print("----------------- error ----------------")
    print(
        str(i).ljust(5),
        "|",
        disassemble(original[i]).ljust(30),
        "|",
        disassemble(assembled[i]).ljust(30),
        "|",
    )


def test_circular():
    circular = ""
    for i in original:
        circular += disassemble(i) + "\n"

    print(circular)
    code2 = Assembler(data=circular)
    code2.assemble()
    code2.display()
