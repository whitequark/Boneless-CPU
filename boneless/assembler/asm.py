from inspect import getmembers, isfunction, signature
from ast import literal_eval
from boneless.arch import instr
from boneless.arch.disasm import disassemble
import types, array, base64

from boneless.assembler import commands
from boneless.assembler import macro
from boneless.assembler.macro import Macro
from boneless.assembler.linker import Linker
from boneless.assembler.fixture import Register, TokenLine, CodeSection


class UnknownInstruction(Exception):
    def __init__(self, tk):
        self.source = tk.source
        self.line = tk.line
        self.command = tk.command
        self.params = tk.params


class BadParameterCount(Exception):
    def __init__(self, tk, params):
        self.source = tk.source
        self.line = tk.line
        self.params = params


class Assembler:
    def __init__(self, debug=False, data="", file_name=""):
        self.debug = debug
        self.labels = {}
        self.rev_labels = {}

        # instruction set data
        self.instr_set = {}
        self.instr_count = {}
        self.instr_param = {}

        # inbuilt commands
        self.commands = {}
        self.commands_params = {}
        # asm variables
        self.variables = {}
        # stored token lines
        self.token_lines = []
        # the code
        self.final = CodeSection("final")
        # section data
        self.sections = {}
        # default to .header section
        self.current_section = None
        self.set_section(".header")
        self.pos = 8
        # add the register functions
        for i in range(8):
            self.current_section.add_label("r_R" + str(i))
            self.current_section.add_code([0])
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
            self.commands_params[i] = commands.commands_params[i]

        macro.bind(self)

        # put the code into place
        if data != "":
            li = data.splitlines()
            tokl = []
            for i, j in enumerate(li):
                if len(j) > 1:
                    tokl.append(TokenLine("string", i, j))
            self.token_lines = tokl
        elif file_name != "":
            self.token_lines = self.load_file(file_name)

        # ref to the linker
        self.linker = Linker(self)

    def set_section(self, name):
        if name not in self.sections:
            self.sections[name] = CodeSection(name)
        self.current_section = self.sections[name]

    def load_file(self, file_name):
        f = open(file_name)
        li = f.readlines()
        f.close()
        tokl = []
        for i, j in enumerate(li):
            if len(j) > 1:
                tokl.append(TokenLine(file_name, i, j))
        return tokl

    def add_label(self):
        pass

    def resolve_symbol(self, symbol):
        # resolves literals, variables , registers
        # instructions
        if self.debug:
            print("find :" + symbol)
        if symbol in self.instr_set:
            if self.debug:
                print("is symbol")
            val = self.instr_set[symbol]()
        # labels , deferenced by at
        elif symbol.startswith("@"):
            if self.debug:
                print("reference :" + symbol)
            print(self.current_section.labels)
            if symbol[1:] in self.current_section.labels:
                val = -self.current_section.labels[symbol[1:]]
        # symbols
        elif symbol in self.variables:
            if self.debug:
                print("variable" + symbol)
            val = self.variables[symbol]
        # try a literal , or just hand back the string
        else:
            try:
                val = literal_eval(symbol)
            except:
                val = symbol
        return val

    def prepend(self, lines):
        self.token_lines = lines + self.token_lines

    def parse(self):
        # line based assembler , break into lines and then tokens
        in_macro = False
        current_macro = None

        # use while loop so more instructions can be prepended inside
        while len(self.token_lines) > 0:
            i = self.token_lines.pop(0)
            # comments line
            if i.comment:
                continue
            if self.debug:
                print(" ", i)
            command = i.command
            params = i.params

            # include files
            if command == ".include":
                lines = self.load_file(params[0])
                # prepend the data
                self.prepend(lines)

            # macros
            elif command == ".macro":
                in_macro = True
                the_macro = Macro(i)
                current_macro = the_macro
                self.commands[params[0]] = the_macro
                self.commands_params[params[0]] = len(params) - 1
                if self.debug:
                    print("start macro create")
            elif command == ".endm":
                in_macro = False
                if self.debug:
                    print("end macro create")
            elif in_macro:
                current_macro.token_lines.append(i)

            # commands and macros
            elif command in self.commands:
                if len(params) != self.commands_params[command]:
                    raise BadParameterCount(i)
                if self.debug:
                    print("RUN", str(command))
                mc = self.commands[command]
                lines = mc(i)
                if isinstance(lines, list):
                    self.prepend(lines)
                elif lines == None:
                    pass
                else:
                    print("bad return" + str(i))

            # labels
            elif command.endswith(":"):
                if self.debug:
                    print("adding label : " + command)
                self.labels[command[:-1]] = self.pos
                self.current_section.add_label(command[:-1])

            # check if it is an instruction
            elif command in self.instr_set:
                if self.debug:
                    print(str(i) + "--> " + str(self.instr_param[command]))
                comm = self.instr_set[command]
                i_params = self.instr_count[command]
                if len(params) != i_params:
                    print("for " + command + " params should be " + str(i_params))
                    raise BadParameterCount(i, params)
                pval = {}
                for j, k in enumerate(self.instr_param[command]):
                    par = params[j]
                    val = self.resolve_symbol(par)
                    pval[k] = val
                if self.debug:
                    print(pval)
                self.current_section.add_code(comm(**pval))
            else:
                self.info()
                raise UnknownInstruction(i)

    def packer(self):
        data = array.array("H", self.code)
        print(data.tobytes())
        s = base64.b16encode(data.tobytes())
        print(s)
        f = open("code.hex", "wb")
        f.write(s)
        f.close()
        return s

    def unpacker(self, data):
        packed_array = base64.b16decode(data)
        data = array.array("H", packed_array)
        print(data)

    def assemble(self):
        self.parse()
        self.code = self.linker.link()

    def show_instruction_set(self):
        for i in self.instr_set:
            l = i.ljust(4) + " - "
            for j in self.instr_param[i]:
                l += j + " "
            print(l)

    def display(self):
        self.final.display()

    def info(self):
        print("Labels")
        print(self.current_section.labels)
        print("Variables")
        print(self.variables)
        print("Instructions")
        print(self.instr_set)
        print("Parameters")
        print(self.instr_param)
        print("Commands")
        print(self.commands)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()

    action = p.add_subparsers(dest="action")

    action.add_parser("info")
    action.add_parser("compile")

    args = p.parse_args()

    code = Assembler(debug=False, file_name="base.asm")
    if args.action == "info":
        code.show_instruction_set()
    if args.action == None:
        code.assemble()
        code.display()
        # c = code.packer()
        # code.unpacker(c)
