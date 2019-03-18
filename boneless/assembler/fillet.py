#!/usr/bin/python3
import sys
from boneless.simulator import *
from boneless.arch.instr import *
from boneless.assembler.asm import Assembler
from boneless.arch.disasm import disassemble

end = False
exit = False
strin = ""
debug = True


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

cpu = BonelessSimulator(start_pc=0,mem_size=1024)
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
    global strin,debug
    strin = input(">")
    if strin.startswith("\\"):
        if strin[1:] == 'd':
            debug= not debug
        strin = ""



def line(asmblr):
    pc = str(cpu.pc).ljust(10)
    code = disassemble(cpu.mem[cpu.pc]).ljust(20)
    reg = cpu.regs()[0:8].tolist()
    stack = cpu.mem[9:15].tolist()
    rstack = cpu.mem[16:24].tolist()
    if cpu.mem[cpu.pc] in asmblr.rev_labels:
        ref = asmblr.rev_labels[cpu.mem[cpu.pc]]
    else:
        ref = ""
    if cpu.pc in asmblr.rev_labels:
        label = asmblr.rev_labels[cpu.pc]
    else:
        label = ""
    print(pc, "|", code, "|", reg, "|", stack,"|",rstack, "->", label,"|",ref)


while not end:
    while 1:
        cpu.stepi()
        if debug:
            line(asmblr)
        if exit:
            exit = False
            break
    get_line()
