; \Build a forth in Assembly
; Simon Kirkby
; obetgiantrobot@gmail.com
; 20190319

.alloc stack, 8
.alloc rstack, 8
; redifine the registers

.def W, R0 ; working register
.def IP, R1 ; interpreter pointer
.def PSP, R2 ; parameter stack pointer 
.def TOS, R7 ; top of parameter stack
.def RSP, R4 ; return stack pointer 
.def JUMP, R5 ; jump saver , no direct access to PC
.def SP, R6 ; spare register 2
.def RTN, R3 ; cpu jump store

reset:
    MOVL PSP,8 
    MOVL RSP,16
    J init

abort:
    J init

.macro _call, name
    JAL RTN, $name
.endm

.macro RET
    JR RTN, 0
.endm

; stack structures
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
    MOV TOS, W
    ADDI PSP, 1
    RET

.label POP
    MOV W, TOS
    SUBI PSP, 1
    LD TOS,PSP, 0
    RET

.label RPUSH
    ST W, RSP, 0
    ADDI RSP, 1
    RET

.label RPOP
    LD W, RSP, 0
    SUBI RSP, 1
    RET

; start of low level forth words

.equ latest, r_R0 

.macro HEADER, name
    .plabel $name , _ 
    .pos latest ; add current pos to code
    .pset latest, $name, _ ; copy this ref for next header
    .ulstring $name ; unlabeled string length then characters
    .label $name
.endm

; the inner interpreter

.macro NEXT
    ADDI IP,1
    LD W,IP,0
    JR W,0
.endm

.macro ENTER, h 
    MOVA W, $h ; store this spot in the working register 
    .label $h ; that's right here
    ADDI W ,5 ; offset past these instructions
    MOV IP, W ; copy into the interpter pointer
    rpush ; put it in the return stack
    LD W,W,0
    JR W,0
.endm

.macro EXECUTE
    NOP
.endm

.macro EXIT
    NOP
.endm

HEADER DUP
    MOV W,TOS
    push 
NEXT

HEADER +
    pop
    ADD W,TOS,W
    MOV TOS,W 
NEXT 

; MAIN LOOP
init:
    MOVI R0, 100
    push
    MOVI R0, 150
    push
    MOVI R0, 175
    push
    ENTER here
    .@ +
    .@ +
    .@ DUP
    .@ +
    EXIT
spin:
    J spin
