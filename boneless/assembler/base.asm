    NOP
    NOP
init:
    MOVL R1 1
loop:
    ROT R1 R1 1
    MOVL R7 0b10000
    CMP R1 R7
    JE  init
    MOVH R2 255
breathe:
    SRL R3 R2 8
    MOVL R7 0xff
    AND R4 R2 R7
    MOVH R7 0x80
    AND R7 R7 R2
    JNZ pwmoff
    XCHG R3 R4
pwm:
    CMP R3 R4
    JULT pwmon
pwmoff:
    STX R0 R0 0
    J pwmdone
pwmon:
    STX R1 R0 0
pwmdone:
    SUBI R2 1
    JNZ breathe
    J loop
