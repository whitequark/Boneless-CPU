.macro TEST name ref
    .label $name
    .global $ref
.endm

.macro HELLO
    NOP
    J init
    J init
    MOVL R1 4
.endm

.macro FNORD one two
    NOP
    test one two 
    bord asdf $fasdfasdf
    norq rr
.endm

.macro HEADER name label
    .label $label
    .string $name
    .equ STUFF
.endm

.macro NEXT
    JAL R1 0
.endm

.macro POP
.endm
