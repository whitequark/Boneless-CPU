#!/usr/bin/python3
import sys
from boneless_sim import *
from boneless.arch.instr import *
from boneless.assembler.asm import Assembler
from boneless.arch.disasm import disassemble


def io(addr, data=None):
    if data == None:
        print("Read-", addr, "{0:016b}".format(data))
    else:
        if addr == 0:
            print(chr(data), end="")


#        elif addr == 1:
#            print("counter : ",data)
#        elif addr == 2:
#            print("maximum : ",data)
#        elif addr == 3:
#            print("length : ",data)
#        elif addr == 4:
#            print("spin")

cpu = BonelessSimulator(start_pc=0, memsize=1024)
code = Assembler(debug=False, file_name="strings.asm")
code.assemble()
cpu.load_program(code.code)
cpu.register_io(io)


def line():
    pc = str(cpu.pc).ljust(10)
    code = disassemble(cpu.mem[cpu.pc]).ljust(20)
    reg = cpu.regs()
    print(pc, "|", code, "|", reg)


for i in range(30000):
    cpu.stepi()
    #line()
