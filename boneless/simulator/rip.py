#!/usr/bin/python
from boneless.arch import opcode
from inspect import getmembers

def showb(val):
    return "{0:04b}".format(val)
    
class instr:
    def __init__(self):
        self.opclass  = {}
        self.opcode = {}
        l = getmembers(opcode)
        for i in l:
            if i[0].startswith("OPCL"):
                self.opclass[i[0]] = i[1]
            if i[0].startswith("OPCO"):
                self.opcode[i[0]] = i[1]

    def show(self):
        print("---- class ----")
        for i in self.opclass:
            print(i,showb(self.opclass[i]))
        print("---- opcode ----")
        for i in self.opcode:
            print(i,showb(self.opcode[i]))
        
    def __repr__(self):
        return str(self.opclass)+"\n"+str(self.opcode)

i = instr()
i.show()
