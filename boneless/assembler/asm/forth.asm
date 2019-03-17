; \Build a forth in Assembly
; Simon Kirkby
; obetgiantrobot@gmail.com
; 20190319

.alloc stack, 8 ; .alloc will label and zero X cells;
.alloc rstack, 8

; redefine the registers

.def W, R0 ; working register
.def IP, R1 ; interpreter pointer
.def PSP, R2 ; parameter stack pointer 
.def TOS, R7 ; top of parameter stack
.def RSP, R4 ; return stack pointer 
.def JUMP, R5 ; jump saver , no direct access to PC
.def SP, R6 ; spare register 2
.def RTN, R3 ; cpu jump store

; macro to send an external halt to the simulator
.macro HALT 
    STX SP,SP,1
.endm

reset:
    MOVL PSP,15 
    MOVL RSP,16
    J init

abort:
    J init

; short form 
.macro _call, name
    JAL RTN, $name
.endm

.macro RET
    JR RTN, 0
.endm

; stack structures
.macro pop
;_call POP
    MOV W, TOS
    ADDI PSP, 1
    LD TOS,PSP, 0
.endm

.macro push
;_call PUSH
    ST TOS, PSP, 0
    SUBI PSP, 1
    MOV TOS, W
.endm

.macro rpop
;    _call RPOP
    LD W, RSP, 0
    SUBI RSP, 1
.endm

.macro rpush
;    _call RPUSH
    ST W, RSP, 0
    ADDI RSP, 1
.endm

; unprotected stack functions

.label PUSH
    ST TOS, PSP, 0
    SUBI PSP, 1
    MOV TOS, W
    RET

.label POP
    MOV W, TOS
    ADDI PSP, 1
    LD TOS,PSP, 0
    MOVI PSP, 0 
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
    .label $name        ; push a header label
    .pos latest         ; add current pos to code
    .set latest, $name  ; copy this ref for next header
    .ulstring $name     ; unlabeled string length then characters
    .plabel $name , xt  ; the execution token , direct pointer
.endm

; the inner interpreter

; --8<--  SNIP

.macro NEXT
    ADDI IP,1   ; jump to the next xt in the list
    MOV W,IP    ; copy the IP into the working register
    LD W,W,0    ; load the data at the address in W
    JR IP,0     ; jump to the data reference 
.endm

.macro ENTER, h 
    MOVA W, $h  ; store this spot in the working register 
    .label $h   ; that's right here
    ADDI W ,4   ; offset past these instructions
    MOV IP, W   ; copy into the interpter pointer
    LD W,W,0    ; load the value of the working pointer 
    JR W,0      ; jump to the XT
.endm


HEADER EXIT
    rpop        ;
    NEXT

; MAIN LOOP
init:
    ENTER start ; start the inner intepreter
    .@ xt_+
    HALT
    J init

.macro EXECUTE name
    MOVA W, $name
    rpush
.endm
.include asm/basic.asm
