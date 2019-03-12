.include inc.asm
init:
    _print welcome
loop:
    LDX R0, R0,0
    MOVL R2, 0
    CMP R2,R0
    JNZ char
    J loop
char:
    STX R0,R3,0
    J loop

