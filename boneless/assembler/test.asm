.include inc.asm
.equ BOB 200 
.equ A 1000
.equ TIME 0xffff

init:
    NOP
middle:
    NOP
    pop
    push 
    J middle 
borf:
    JR TOS 0 
gorf:
    NOP
    NOP
    NOP

.section .data
    .string hello hello
    .string Wrapped, "This is a longer  test"
