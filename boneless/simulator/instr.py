
from boneless.arch.disasm import disassemble
BITS = 16

CLASS_A = {"op": 4, "c": 1, "Rd": 3, "Ra": 3, "Rb": 3, "type": 2}
CLASS_S = {"op": 4, "c": 1, "Rd": 3, "Ra": 3, "amount": 4, "t": 1}
CLASS_M = {"op": 3, "code": 2, "Rd": 3, "Ra": 3, "offset": 5}
CLASS_I = {"op": 2, "opcode": 3, "Rd": 3, "immediate": 8}
CLASS_C = {"op": 1, "condition": 3, "F": 1, "offset": 11}

SET = {'A':CLASS_A,'S':CLASS_S,'M':CLASS_M,"I":CLASS_I,"C":CLASS_C}

for i,j in SET.items():
    print(i,j)

class opcode(type):
    op = 0b1111
    def __new__(cls,name,bases,classdict):
        op  = super().__new__(cls,name,bases,classdict)
        op.val = 0
        return op

class class_a(metaclass=opcode):
    op = 0b0000
    pass
       
class class_s(metaclass=opcode):
    op = 0b0000
    pass
       
class class_m(metaclass=opcode):
    op = 0b0010
    pass
       
class class_i(metaclass=opcode):
    op = 0b0100
    pass
       
class class_c(metaclass=opcode):
    op = 0b1000
    pass
       

print(class_a())

for i in range(2**BITS):
    print(i,disassemble(i))
