; \Build a forth in Assembly
; Simon Kirkby
; obetgiantrobot@gmail.com
; 20190319

.equ stack_size, 8
.alloc stack, stack_size 
.alloc rstack, stack_size
; redifine the registers

.def W, R0 ; working register
.def IP, R1 ; interpreter pointer
.def PSP, R2 ; parameter stack pointer 
.def TOS, R7 ; top of parameter stack
.def RSP, R4 ; return stack pointer 
.def JUMP, R5 ; jump saver , no direct access to PC
.def SP, R6 ; spare register 2
.def RTN, R3 ; cpu jump store

J reset
.section .text

reset:
    MOVL PSP,7 
    MOVL RSP,16
    J init

abort:
    J init

.macro _call, name
    JAL RTN, $name
.endm
; stack structures
.macro RET
    JR RTN, 0
.endm

.macro pop
    _call POP
.endm

.macro push
    _call PUSH
.endm

.macro rpop
    _call RPOP
.endm

.macro rpush
    _call RPUSH
.endm

; unprotected stack functions

.label PUSH
    ST TOS, PSP, 0
    ADDI PSP, 1
    MOV TOS, W
    RET

.label POP
    MOV W, TOS
    SUBI PSP, 1
    LD TOS,PSP, 0
    RET

.label RPUSH
    ST W , RSP, 0
    ADDI RSP, 1
    RET

.label RPOP
    LD W , RSP, 0
    SUBI RSP, 1
    RET

; start of low level forth words

.macro NEXT
    LD W,IP,0
    J W
.endm

.equ latest, r_R0 

.macro HEADER, name
    .label $name
    .pos latest ; add current pos to code
    .set latest, $name ; copy this ref for next header
    .ulstring $name ; string length then characters
.endm

; do colon 
HEADER DOCOL 
NEXT

; from address find the first code word
HEADER >CFA
    LD W,PSP,1 ; load the value after the current pointer
    ADD W,PSP,W ; add the offset
    MOV PSP,W    
NEXT

HEADER DUP
    MOV W,TOS
    push 
NEXT

HEADER [
NEXT

HEADER ]
NEXT

; MAIN LOOP
QUIT:

init:
    MOVA PSP, QUIT
    NOP
    MOVI W, 100
    push
    MOVI W, 101
    push
    MOVI W, 102
    push
    pop
    pop
    pop
J init

