
HEADER COLD
    MOVL PSP,8 
    MOVL RSP,16
NEXT

HEADER set_10
    MOVL W, 10
    push
NEXT

HEADER test
    DOCOL 
    .@ xt_set_10
    .@ xt_dup 
    .@ xt_+
    .@ xt_DROP
    .@ xt_sub
    .@ xt_EXIT
NEXT

HEADER sub
    DOCOL
    .@ xt_EXIT
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

