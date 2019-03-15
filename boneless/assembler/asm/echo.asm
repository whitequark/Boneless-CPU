reset:
    MOVL R2, 0
loop:
    LDX R0, R2,0
    CMP R2,R0
    JNZ char
    STX R4,R4,1
    J loop
char:
    STX R0,R3,0
    J loop

