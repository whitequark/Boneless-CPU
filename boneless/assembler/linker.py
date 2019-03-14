" section linker"
"""
    registers - 1..8
    .stacks
    .heap
    .data
    .text
    end of memory
"""

from boneless.assembler.fixture import CodeSection, resolver
import types


class Linker:
    order = [".header", ".text", ".data"]

    def __init__(self, assem):
        self.assem = assem
        self.sections = assem.sections
        self.counter = 0
        self.section_labels = {}
        self.built = assem.final

    def resolve(self):
        " simple resolver "
        # TODO need to deal with larger offsets
        for offset, code in enumerate(self.built.code):
            if self.assem.debug:
                print(offset, code)
            if isinstance(code, resolver):
                self.built.code[offset] = self.built.labels[code()]
            if isinstance(code, types.LambdaType):
                # TODO if label - offset > +-127 , an extended code needs to be inserted.
                self.built.code[offset] = code(
                    lambda label: self.built.labels[label] - offset - 1
                )

    def link(self):
        print("Activate the LINK-O-TRON")
        for i, j in self.sections.items():
            print(i, " : ", j)
            labels = j.offset_labels(self.counter)
            for name, pos in labels.items():
                self.built.set_label(name, pos)
            for k in j.code:
                self.built.add_code([k])
            self.counter += j.length
            self.section_labels[i] = self.counter

        self.resolve()
        if self.assem.debug:
            print(self.built)
            self.built.display()
            print(self.built.labels)
            print(self.section_labels)
        return self.built.code
