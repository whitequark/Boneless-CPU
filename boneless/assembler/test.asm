.include inc.asm
.equ BOB 200 
.equ A 1000

fnord:
    .string blah
    .equ TIME 0xffff
init:
    NOP
middle:
    NOP
    .call pop
    .call push
    J middle 
borf:
    JR TOS 0 
gorf:
    NOP
    NOP
    NOP

.alloc hello 10
