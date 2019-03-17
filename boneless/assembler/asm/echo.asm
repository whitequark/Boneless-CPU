reset:
    NOP
loop:
    LDX R0, R2,0 ; load a word from 0
    CMP R2,R0    ; compare with R0 (0)
    JNZ char    ; is it not neto , go to cher
    STX R4,R4,1 ; send a break to the simulatore
    J loop ; do it again
char:
    STX R0,R3,0  ;output the char back out
    J loop ; lump back to loop

