.include inc.asm

.equ BOB, 200 
.equ A, 1000
.equ TIME, 0xffff

.def CTR, R5
.def MAX, R1 

init:
    MOVL CTR, 0
    MOVH MAX, 0xff
    MOVL MAX, 0xff
middle:
    NOP
    push 
    NOP
    pop
    NOP
    ADDI CTR, 1 
    CMP CTR, MAX
    JE next
    J middle 
next:
    MOVH CTR, 0
    MOVL CTR, 0
    J middle 

.section .data
    .string hello,"hello"
    .string Wrapped, "This is a longer test"
    .string fnord,"What you talking about"
    .string another,"More texty bits"
