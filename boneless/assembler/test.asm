.include inc.asm

.def CTR, R5
.def MAX, R1 
.def ADDR, R2
.def LEN, R3
.def VAL, R4

init:
    MOVL CTR, 0
    MOVH MAX, 0x00
    MOVL MAX, 0x0f
middle:
    CMP CTR, MAX
    JE next
    STX CTR ,0, 0
    ADDI CTR, -1 
    J middle 
next:
    MOVH CTR, 0
    MOVL CTR, 0
    J middle 

.macro _print string
    LD ADDR, $string,0
    LD LEN, $string,1
    ADD MAX, ADDR,LEN
    MOVL CTR, 0
    _call PRINT
.endm

PRINT:
    LD VAL,ADDR,0
    STX 0,VAL,0
    CMP ADDR, MAX
    JE _out_print
    ADDI ADDR,1
    J PRINT
_out_print:
    NOP

.section .data
    .string hello,"hello"
    .string another,"More texty bits"
    .string bl0, "╔═╦═╗╓─╥─╖╒═╤═╕┌─┬─┐"
    .string bl1, "║ ║ ║║ ║ ║│ │ ││ │ │"
    .string bl2, "╠═╬═╣╟─╫─╢╞═╪═╡├─┼─┤"
    .string bl3, "║ ║ ║║ ║ ║│ │ ││ │ │"
    .string bl4, "╚═╩═╝╙─╨─╜╘═╧═╛└─┴─┘"
    .string braille, "⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿"
