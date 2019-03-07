" macros for the assembler"
from fixture import TokenLine

assembler = None

# give commands access to the assembler object
def bind(assembler_object):
    global assembler
    assembler = assembler_object


class BadParameterCount(Exception):

    def __init__(self,tk,params):
        self.source = tk.source
        self.line = tk.line
        self.items = tk.items
        self.params = params

class Macro:
    "Simple substitution macro processor"

    def __init__(self, tk):
        self.name = tk.params[0]
        self.source = tk.source+"-macro"
        self.line = tk.line
        self.token_lines = []
        self.params = tk.params[1:]

    def __call__(self,tok):
        if assembler.debug:
            print("parse with params")
            print(tok.params)
        if len(tok.params) != len(self.params):
            raise BadParameterCount(tok,params)
        # map parameters to passed values
        pmap = {}
        for i, j in enumerate(self.params):
            pmap[j] = tok.params[i]
        parsed_lines = []
        # find $ vaules and replace with passed string
        print("macro_line:",tok)
        for i in self.token_lines:
            line = []
            for j in i.params:
                if j.startswith("$"):
                    if j[1:] in pmap:
                        print("has " + j)
                        j = pmap[j[1:]]
                line.append(j)
            #parsed_lines.append(TokenLine(self.source,self.line,line))
        if assembler.debug:
            print("from ", str(self.token_lines))
            print("becomes ", str(parsed_lines))
        # return token lines back to the parser
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
