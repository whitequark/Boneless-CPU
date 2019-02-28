.include inc.asm
fnord:
    .string blah
    .equ TIME 0xffff
    HEADER bob bob
init:

    HEADER RPOP RPOP
    POP
    NEXT

    HEADER test bob
    NOP
    NEXT

    HEADER DUP DUP
    NOP
    NOP
    NEXT

    HEADER < <
    NOP
    NEXT

    HEADER DOCOL DOCOL
    NOP
    NEXT

    HEADER ; col
    NOP
    NOP
    NEXT

    .int DOCOL
    .int DUP
