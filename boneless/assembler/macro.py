" macros for the assembler"

assembler = None

# give commands access to the assembler object
def bind(assembler_object):
    global assembler
    assembler = assembler_object


class Macro:
    " macros would be cool "
    " need to pass variables through to macro"

    def __init__(self, name, params):
        self.name = name
        self.code = []
        self.token_lines = []
        self.params = params

    def __call__(self, params):
        print("parse with params")
        print(params)
        if len(params) != len(self.params):
            raise BaseException
        pmap = {}
        for i, j in enumerate(self.params):
            pmap[j] = params[i]
        parsed_lines = []
        for i in self.token_lines:
            line = []
            for j in i:
                if j.startswith("$"):
                    if j[1:] in pmap:
                        print("has " + j)
                        j = pmap[j[1:]]
                line.append(j)
            parsed_lines.append(line)

        print("from ", str(self.token_lines))
        print("becomes ", str(parsed_lines))
        return parsed_lines

    def __repr__(self):
        return (
            "<macro "
            + self.name
            + " - "
            + str(self.params)
            + "-"
            + str(self.token_lines)
            + ">"
        )
