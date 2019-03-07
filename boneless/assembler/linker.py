" section linker"
"""
    registers - 1..8
    .stacks
    .heap
    .data 
    .text  
    end of memory
"""

from fixture import CodeSection


class Linker:
    order = [".header", ".text", ".data"]

    def __init__(self, assem):
        print("WHAAAAT! no linker")
        self.assem = assem
        self.sections = assem.sections
        self.built = CodeSection("complete")
        self.counter = 0

    def link(self):
        print("Activate the LINK-O-TRON")
        for i, j in self.sections.items():
            print(i, " : ", j)
            print(j.code)
            for k in j.code:
                self.built.add_code([k])
            print(self.built, self.built.code)
