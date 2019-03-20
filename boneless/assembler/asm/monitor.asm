; The serial monitor a simple monitor program
; for teathering the CPU
;
; Needs to provide the following commands
; READ : read a specific word from memory -> R , ADDR , VAL
; WRITE : write a specific word to memory memory -> W , ADDR , VAL
; CALL : jump the execution to a memory position -> J ADDR
;
; extras
; bulk read
; bulk write
; running checksum

; name some registers
.def W, R0          ; incoming data
.def ADDR , R1      ; src/desitination address
.def COUNT , R2     ; counter for bulk
.def LEN , R3       ; length for bulk
.def MAX , R4       ; max address pos 
.def COM, R5        ; command
.def STP, R7       ; stack pointer

.alloc stack ,16

.macro popr , reg
    LD $reg,STP,0
    ST R6,STP,0
    SUBI STP,1
.endm

.macro pushr , reg
    ST $reg,STP,0
    ADDI STP,1
.endm

.macro pop
    LD W,STP,0
    ST R6,STP,0
    SUBI STP,1
.endm

.macro push
    ST W,STP,0
    ADDI STP,1
.endm

.macro command , val , target
    MOVL COM, $val
    CMP W,COM
    JE $target
.endm
; macro to send an external halt to the simulator
.macro HALT
    XOR R6,R6,R6
    XOR R6,R6,R6
    STX R6,R6,1
.endm

.macro return
    J loop
.endm

.macro out
    STX W,R6,0
.endm

.macro in 
    LDX W,R6,0
.endm

J init

init:
    MOVL R0,0
    MOVL STP,9
loop:
    in
    command 82 , read ; R 
    command 87 , write ; W
    command 67 , call ; C
    command 0 ,  halt ; 
    command 68, dump ; D
    MOVL COM,0
J loop

halt:
    HALT
    return 

read:
    in
    CMP W,R6
    JE read_out
    push
    J read
read_out:
    return

write:
    return

call:
    return

dump:
    MOVL COUNT,0
    MOVL MAX,0x00
    MOVH MAX,0x04
dump_loop:
    LD W,COUNT,0
    out
    ADDI COUNT,1
    CMP COUNT,MAX
    JE dump_exit
    J dump_loop
dump_exit:
    return

