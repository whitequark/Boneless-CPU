from inspect import getmembers, isfunction, signature
from ast import literal_eval
from boneless.arch import instr
from boneless.arch.disasm import disassemble
import types

import commands
import macro
from macro import Macro


class UnknownInstruction(Exception):
    pass

class BadParameterCount(Exception):
    pass

class Register:
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return "<register R" + str(self.val) + ">"

    def __call__(self):
        return int(self.val)

class Assembler:
    def __init__(self, debug=False):
        self.debug = debug
        self.labels = {}
        self.rev_labels = {}

        self.instr_set = {}
        self.instr_count = {}
        self.instr_param = {}

        self.commands = {}

        self.variables = {}

        # current  code pos
        self.pos = 0
        # blank out the registers
        self.code = [0 for i in range(8)]

        # add the registers
        for i in range(8):
            self.instr_set["R" + str(i)] = Register(i)
        # build instruction set map
        ins = getmembers(instr, isfunction)
        # get all the instructions
        for i in ins:
            if i[0] in instr.__all__:
                self.instr_set[i[0]] = i[1]
        # get parameter sets
        for i, j in self.instr_set.items():
            s = signature(j).parameters
            self.instr_count[i] = len(s.keys())
            self.instr_param[i] = []
            for j in s.keys():
                self.instr_param[i].append(j)

        # set up commands system
        commands.bind(self)
        for i,j in commands.commands.items():
            self.commands[i] = j

        macro.bind(self)

    def load_file(self,file_name):
        f = open(file_name)
        li = f.readlines()
        f.close()
        tokl = []
        for i in li:
            tokl.append(i.split())
        return tokl

    def parse(self, lines):
        # line based assembler , break into lines and then tokens
        token_lines = []
        counter = 0
        in_macro = False
        current_macro = None

        for i in lines:
            t = i.split()
            token_lines.append(t)

        #use while loop so more instructions can be prepended inside
        while len(token_lines) > 0:
            i = token_lines.pop(0)
            # empty line
            if len(i) <1:
                continue
            if self.debug:
                print(i)
            command  = i[0]
            # include files
            if command == ".include":
                lines = self.load_file(i[1])
                # prepend the data
                token_lines = lines + token_lines
            # macros
            elif command  == ".macro":
                in_macro = True
                the_macro = Macro(i[1], i[2:])
                current_macro = the_macro
                self.commands[i[1]] = the_macro
                if self.debug:
                    print("STARTING MACRO")
            elif command == ".endm":
                in_macro = False
                if self.debug:
                    print("END MACRO")
            elif in_macro:
                current_macro.token_lines.append(i)
            # commands
            elif command in self.commands:
                print("RUN", str(command))
                mc = self.commands[command]
                lines = mc(i[1:])
                if isinstance(lines,list):
                    print("add macro stuff")
                    print(lines)
                    token_lines = lines + token_lines
            # check if it is an instruction
            elif command in self.instr_set:
                if self.debug:
                    print("command " + command)
                    print(
                        "param " + str(self.instr_count[command]) + "," + str(len(i) - 1)
                    )
                    print("params" + str(self.instr_param[command]))
                comm = self.instr_set[command]
                params = self.instr_count[command]
                if len(i) != params + 1:
                    print("for " + command + " params should be " + str(params))
                    raise BadParameterCount(command)
                pval = {}
                for j, k in enumerate(self.instr_param[command]):
                    par = i[1 + j]
                    # registers
                    if par in self.instr_set:
                        val = self.instr_set[par]()
                    else:
                        try:
                            val = literal_eval(par)
                        except:
                            val = par
                    pval[k] = val
                if self.debug:
                    print(pval)
                self.code += comm(**pval)
                self.pos = len(self.code)
            # labels
            elif i[0].endswith(":"):
                if self.debug:
                    print("adding label : "+command)
                self.labels[command[:-1]] = self.pos
            else:
                raise UnknownInstruction(command)

        # reverse labels for disasm listing
        for i, j in self.labels.items():
            self.rev_labels[j] = i

    def resolve(self):
        for offset, code in enumerate(self.code):
            if self.debug:
                print(offset, code)
            if isinstance(code, types.LambdaType):
                self.code[offset] = code(lambda label: self.labels[label] - offset - 1)

    def display(self):
        for offset, code in enumerate(self.code):
            l = ""
            if offset in self.rev_labels:
                l = self.rev_labels[offset]
            print(l.ljust(10),offset, disassemble(code))

    def assemble(self, code):
        self.parse(code)
        self.resolve()

    def info(self):
        print(self.labels)
        print(self.instr_count)
        print(self.instr_param)
        print(self.instr_set)
        print(self.commands)


if __name__ == "__main__":
    f = open("test.asm")
    li = f.readlines()
    f.close()

    code = Assembler(debug=False)
    code.assemble(li)
    code.display()
    #code.info()

