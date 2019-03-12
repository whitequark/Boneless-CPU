; basic string interaction
; testing comment
.def MAX, R2 ; redfine a register 
.def ADDR, R3
.def VAL,R1
.def RTN, R7
J init

.macro _call, name
    JAL RTN, $name
.endm

.macro RET
    JR RTN, 0
.endm

.macro _print, string
    MOVA ADDR, $string 
    _call PRINT
.endm

PRINT:
    LD MAX, ADDR,0 
    ADDI ADDR,1
    SUBI MAX, 1
    ADD MAX, ADDR,MAX
_next_char:
    LD VAL,ADDR,0
    STX VAL,R0,0
    CMP ADDR, MAX
    JE _out_print
    ADDI ADDR,1
    J _next_char 
_out_print:
    RET

init:
    _print hello 
    _print cr
    _print bl0
    _print cr
    MOVL VAL, 0x00
    MOVH VAL, 0x00
spin:
    J spin
;    STX VAL,R0,0
;    ADDI VAL,1

.string hello,"hello i am a program"
.string cr, " \n"
.string bl0, "╔═╦═╗╓─╥─╖╒═╤═╕┌─┬─┐"
.string red,"\u001b[31m"
.string clear,"\u001b[2J"
.string home,"\u001b[f"
