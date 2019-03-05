.alloc bork 10
.alloc stack 16
.macro HEADER name label
    .label $label
    .string $name
    .equ $name 100
.endm

.macro NEXT
    JAL R1 0
.endm


.def STP R4
.def TOS R3
.def RTN R7
.def WRK R2

MOVL STP #stack 
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
