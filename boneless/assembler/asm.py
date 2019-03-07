from inspect import getmembers, isfunction, signature
from ast import literal_eval
from boneless.arch import instr
from boneless.arch.disasm import disassemble
import types

import commands
import macro
from macro import Macro
from linker import Linker
from fixture import Register , TokenLine , CodeSection

class UnknownInstruction(Exception):

    def __init__(self,tk):
        self.source = tk.source
        self.line = tk.line
        self.items = tk.items


class BadParameterCount(Exception):

    def __init__(self,tk,params):
        self.source = tk.source
        self.line = tk.line
        self.items = tk.items
        self.params = params


class Assembler:
    def __init__(self, debug=False,data="",file_name=""):
        self.debug = debug
        self.labels = {}
        self.rev_labels = {}

        # instruction set data
        self.instr_set = {}
        self.instr_count = {}
        self.instr_param = {}

        # inbuilt commands
        self.commands = {}
        # asm variables
        self.variables = {}
        # stored token lines
        self.token_lines = []
        # section data
        self.sections = {}
        # current  code pos
        self.pos = 8
        # blank out the registers
        self.code = [0 for i in range(8)]

        # add the register functions
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
        for i, j in commands.commands.items():
            self.commands[i] = j

        macro.bind(self)

        # put the code into place
        if data != "":
            li = data.splitlines()
            tokl = []
            for i,j in enumerate(li):
                items = j.split()
                tokl.append(TokenLine('string',i,items))
            self.token_lines = tokl
        elif file_name != "":
            self.token_lines = self.load_file(file_name)

        # default to .text section
        self.set_section(".text")
        # ref to the linker
        self.linker = Linker(self)

    def set_section(self,name):
        if name not in self.sections:
            self.sections[name] = CodeSection(name)
        self.current_section = self.sections[name]

    def load_file(self, file_name):
        f = open(file_name)
        li = f.readlines()
        f.close()
        tokl = []
        for i,j in enumerate(li):
            items = j.split()
            tokl.append(TokenLine(file_name,i,items))
        return tokl

    def resolve_symbol(self,symbol):
        # resolves literals, variables , registers
        # instructions
        if self.debug:
            print("find :"+symbol)
        if symbol in self.instr_set:
            val = self.instr_set[symbol]()
        # labels , deferenced by hash
        elif symbol.startswith("$"):
            print("referenced symbol")
            if symbol[1:] in self.labels:
                val = self.labels[symbol[1:]]
        # symbols
        elif symbol in self.variables:
            val = self.variables[symbol]
        # try a literal , or just hand back the string
        else:
            try:
                val = literal_eval(symbol)
            except:
                val = symbol
        return val

    def parse(self):
        # line based assembler , break into lines and then tokens
        in_macro = False
        current_macro = None

        # use while loop so more instructions can be prepended inside
        while len(self.token_lines) > 0:
            i = self.token_lines.pop(0)
            # empty line
            if len(i) < 1:
                continue
            if self.debug:
                print(i)
            command = i[0]

            # include files
            if command == ".include":
                lines = self.load_file(i[1])
                # prepend the data
                self.token_lines = lines + self.token_lines

            # macros
            elif command == ".macro":
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
                if self.debug:
                    print("RUN", str(command))
                mc = self.commands[command]
                lines = mc(i)
                if isinstance(lines, list):
                    if self.debug:
                        print("\t"+str(lines))
                    self.token_lines = lines + self.token_lines

            # labels
            elif i[0].endswith(":"):
                if self.debug:
                    print("adding label : " + command)
                self.labels[command[:-1]] = self.pos

            # check if it is an instruction
            elif command in self.instr_set:
                if self.debug:
                    print(str(i) + "--> " + str(self.instr_param[command]))
                comm = self.instr_set[command]
                params = self.instr_count[command]
                if len(i) != params + 1:
                    print("for " + command + " params should be " + str(params))
                    raise BadParameterCount(i,params)
                pval = {}
                for j, k in enumerate(self.instr_param[command]):
                    par = i[1 + j]
                    val = self.resolve_symbol(par)
                    pval[k] = val
                if self.debug:
                    print(pval)
                self.code += comm(**pval)
                self.pos = len(self.code)
            else:
                raise UnknownInstruction(i)

        # reverse labels for disasm listing
        for i, j in self.labels.items():
            self.rev_labels[j] = i

    def resolve(self):
        " simple resolver "
        #TODO move resolver into the linker
        #TODO need to deal with larger offsets
        #TODO need to integrate into the linker
        for offset, code in enumerate(self.code):
            if self.debug:
                print(offset, code)
            if isinstance(code, types.LambdaType):
                #TODO if label - offset > +-127 , an extended code needs to be inserted.
                self.code[offset] = code(lambda label: self.labels[label] - offset - 1)

    def display(self):
        for offset, code in enumerate(self.code):
            l = ""
            if offset in self.rev_labels:
                l = self.rev_labels[offset]
            o = "{:04X} | ".format(offset)
            b = "| {:05b}".format(code>>11)
            lb  = "{0:016b}".format(code)
            print(o,l.ljust(10)," | ", disassemble(code).ljust(16),b,lb)

    def assemble(self):
        self.parse()
        self.linker.link()
        self.resolve()

    def info(self):
        print("Labels")
        print(self.labels)
        print("Variables")
        print(self.variables)
        print("Instructions")
        for i in self.instr_set:
            print(i)
        print(self.instr_set)
        print("")
        print(self.instr_count)
        print("Labels")
        print(self.instr_param)
        print("Labels")
        print(self.commands)


if __name__ == "__main__":
    code = Assembler(debug=True,file_name="test.asm")
    code.assemble()
    #code.info()
    code.display()
