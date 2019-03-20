; The serial monitor a simple monitor program
; for teathering the CPU
;
; Needs to provide the following commands
;
; READ : read a specific word from memory -> R , ADDR , VAL
; WRITE : write a specific word to memory -> W , ADDR , VAL
; CALL : jump the execution to a memory position -> J ADDR
;
; extras
; 
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

J init

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

.macro jump_target, char,target
    .int $char
    .@ $target
.endm

jump_table:
    jump_target 82 , read ; R 
    jump_target 87 , write ; W
    jump_target 67 , call ; C
    jump_target 68, dump ; D
    jump_target 73, bulk_write; I
    jump_target 79, bulk_read; O
    jump_target 0 ,  halt ;
jump_table_end:
    NOP
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


init:
    MOVL R0,0       ; reset the working register
    MOVL STP,9      ; set the stack pointer
loop:
    MOVA MAX,jump_table_end ; set max to the end of the jump table
    MOVL COM,0 ; reset command
    MOVL W,0 ; reset the working register 
    MOVH W,0 ; high byte
    in      ; grab a word from input
    MOVA ADDR,jump_table ; locate the jump tables in ADDR
    MOVL COUNT,0 ; reset the count
scan:
    LD COM,ADDR,0   ; load the values at ADDR into COM
    CMP W,COM       ; check COM against the current value
    JE go           ;  if they are equal , move to go
    ADDI ADDR,2     ; add 2 to the address, jump tables is (val,jump address)
    CMP MAX,ADDR    ; are we at the end of the jump table
    JE loop         ; start again
    J scan          ; keep scanning 
go:
    ADDI ADDR,1     ;add 1 to the current address to get the target
    LD ADDR,ADDR,0  ;load the address of the target back into ADDR
    JR ADDR,0       ; jump there
J loop

halt:               ; stop the simulator and get a line
    HALT
    return 

; READ A VALUE FROM MEMORY
; needs an ADDRESS
read:
    in ; Get the address off the input, goes into W
    LD W,W,0 ; load it
    out ; Send it out
read_out:
    return

; WRITE A VALUE TO MEMORY
; needs an address and a value
write:
    in ; Get the address off the input, goes into W
    MOV W,ADDR  ; move the value into the address register
    ST W,ADDR,0 ; copy the data into place
    return

; CALL AN ADDRESS
; needs an address
call:
    in ; get the address off the input
    JR W,0
    return

; DUMP the entire memory space
; set to 1024 words for now
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

; BULK READ 
; needs an Address and a count
bulk_read:
    return

; BULK WRITE
; needs an address and a count
bulk_write:
    return

; end of the monitor
