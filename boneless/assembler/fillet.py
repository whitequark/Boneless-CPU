#!/usr/bin/python3
import sys
from boneless_sim import *
from boneless.arch.instr import *
from boneless.assembler.asm import Assembler
from boneless.arch.disasm import disassemble

exit = False
strin = ""

def io(addr, data=None):
    global strin,exit
    if data == None:
        if addr == 0:
            if len(strin) > 0:
                c = strin[0]
                strin = strin[1:]
                return ord(c)
            else:
                return 0 # return null char on read
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
if len(sys.argv) > 1 :
    file_name = sys.argv[1]
else:
    file_name = "strings.asm"
code = Assembler(debug=True, file_name=file_name)
code.assemble()
code.display()
cpu.load_program(code.code)
cpu.register_io(io)


def get_line():
    global strin
    strin = input(">")

def line():
    pc = str(cpu.pc).ljust(10)
    code = disassemble(cpu.mem[cpu.pc]).ljust(20)
    reg = cpu.regs()
    print(pc, "|", code, "|", reg)

while(1):
    get_line()
    while(1):
        cpu.stepi()
        #line()
        if exit:
            exit = False
            break
