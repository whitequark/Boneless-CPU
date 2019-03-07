.equ stack_size 8 
.alloc stack stack_size 

.def STP R4
.def TOS R3
.def RTN R7
.def WRK R2

.section .text

MOVL STP $stack 

.macro _call name
    JAL RTN $name 
.endm

.macro RET 
    JR RTN 0
.endm

.macro pop
    _call POP 
.endm

.macro push
    _call PUSH
.endm

.label PUSH 
    ST TOS STP 0
    ADDI STP 1
    MOV WRK TOS
    RET
 
.label POP 
    MOV WRK TOS
    LD STP TOS 0
    SUBI STP 1 
    RET

.section .data 

.string welcome Boneless 0.1
.string stack_overflow Stack Overflow
.string stack_underflow Stack Underflow

.section .text
