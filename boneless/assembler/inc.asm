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

MOVL STP #stack 
.macro .call name
    JAL RTN $name 
.endm

.macro RET 
    JR RTN 0
.endm

.label push
    ST TOS STP 0
    ADDI STP 1
    RET
 
.label pop
    LD STP TOS 0
    SUBI STP 1 
    RET
