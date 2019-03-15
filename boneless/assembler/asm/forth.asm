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
    JR IP,0     ; jump to the address
.endm

.macro ENTER, h 
    MOVA W, $h  ; store this spot in the working register 
    .label $h   ; that's right here
    ADDI W ,4   ; offset past these instructions
    MOV IP, W   ; copy into the interpter pointer
    LD W,W,0    ; load the value of the working pointer 
    JR W,0      ; jump to the XT
.endm


.macro EXIT
    rpop        ;
    MOV IP,W
    NEXT
.endm

; MAIN LOOP
init:
    MOVL W, 100
    push
    MOVL W, 50
    push
    MOVL W, 25
    push
    ENTER start ; start the inner intepreter
    .@ xt_+ ; to run words in assembly , use .@ 
    .@ xt_+
    HALT
    J init

.macro EXECUTE
.endm

HEADER COLD
    MOVL PSP,8 
    MOVL RSP,16
NEXT

HEADER DOCOL ; run the do colon code
NEXT

HEADER DUP
    MOV W,TOS
    push 
NEXT

HEADER QUIT
    LDX W,SP,0
NEXT

HEADER &
NEXT

HEADER @
NEXT

HEADER !
NEXT

HEADER +
    pop
    ADD W,TOS,W
    MOV TOS,W 
NEXT 

HEADER BRANCH
NEXT

HEADER SWAP
    pop
    XCHG W,TOS
    push
NEXT

HEADER DROP
    pop
NEXT

