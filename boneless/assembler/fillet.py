#!/usr/bin/python3
import sys
from boneless_sim import *
from boneless.arch.instr import *
from boneless.assembler.asm import Assembler
from boneless.arch.disasm import disassemble

exit = False
strin = ""


def io(addr, data=None):
    global strin, exit
    if data == None:
        if addr == 0:
            if len(strin) > 0:
                c = strin[0]
                strin = strin[1:]
                return ord(c)
            else:
                return 0  # return null char on read
        return 0
    else:
        if addr == 0:
            print(chr(data), end="")
        if addr == 1:
            print("")
            exit = True


#        elif addr == 1:
#            print("counter : ",data)
#        elif addr == 2:
#            print("maximum : ",data)
#        elif addr == 3:
#            print("length : ",data)
#        elif addr == 4:
#            print("spin")

cpu = BonelessSimulator(start_pc=0, memsize=1024)
if len(sys.argv) > 1:
    file_name = sys.argv[1]
else:
    file_name = "asm/forth.asm"
asmblr = Assembler(debug=False, file_name=file_name)
asmblr.assemble()
asmblr.display()
cpu.load_program(asmblr.code)
cpu.register_io(io)


def get_line():
    global strin
    strin = input(">")


def line(asmblr):
    pc = str(cpu.pc).ljust(10)
    code = disassemble(cpu.mem[cpu.pc]).ljust(20)
    reg = cpu.regs()[0:8].tolist()
    stack = cpu.regs()[9:16].tolist()
    if cpu.pc in asmblr.rev_labels:
        label = asmblr.rev_labels[cpu.pc]
    else:
        label = ""
    print(pc, "|", code, "|", reg, "|", stack, "->", label)


while 1:
    while 1:
        cpu.stepi()
        line(asmblr)
        if exit:
            exit = False
            break
