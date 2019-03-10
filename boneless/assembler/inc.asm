.equ stack_size, 8
.alloc stack, stack_size 

.def STP, R4
.def TOS, R3
.def RTN, R7
.def WRK, R2

.section .text

reset:
    MOVL STP,8 
    J init

abort:
    J init

.macro _call, name
    JAL RTN, $name
.endm

.macro long, a, b, c, d
    MOV $a, $b
    MOV $b, $c
    MOV $d, $a
.endm

.macro RET
    JR RTN, 0
.endm

.macro pop
    _call POP
.endm

.macro push
    _call PUSH
.endm

.label PUSH
    ST TOS, STP, 0
    ADDI STP, 1
    MOV WRK, TOS
    RET

.label POP
    MOV WRK, TOS
    LD STP, TOS, 0
    SUBI STP, 1
    RET

.section .data

.string welcome, "Boneless 0.1"
.string overflow, "Stack Overflow"
.string underflow, "Stack Underflow"

.section .text

