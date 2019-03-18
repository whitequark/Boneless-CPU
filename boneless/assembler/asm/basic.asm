
HEADER COLD
    MOVL PSP,8 
    MOVL RSP,16
NEXT

HEADER set_10
    MOVL W, 10
    push
NEXT

HEADER set_20
    MOVL W, 20
    push
NEXT

HEADER +
    pop
    ADD W,TOS,W
    MOV TOS,W 
NEXT 

HEADER DROP
    pop
NEXT

HEADER sub
    DOCOL
    set_20
    DROP
    EXIT
NEXT

HEADER gorf
    DOCOL
    set_10
    set_10
    set_10
    +
    +
    DROP
    sub
    EXIT
NEXT 


HEADER pad
.alloc pad_alloc,10
NEXT

HEADER dup 
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


HEADER BRANCH
NEXT

HEADER SWAP
    pop
    XCHG W,TOS
    push
NEXT


