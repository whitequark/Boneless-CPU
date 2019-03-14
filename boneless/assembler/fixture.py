from boneless.arch.disasm import disassemble


class Register:
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return "<register R" + str(self.val) + ">"

    def __call__(self):
        return int(self.val)


class TokenLine:
    " Wrap the token lines for debug"

    def __init__(self, source, line, val):
        self.source = source
        self.line = line
        self.val = val
        self.comment = False
        if val.startswith(";"):
            self.comment = True
            return
        comment_pos = val.find(";")
        if comment_pos != -1:
            val = val[:comment_pos]
            print(val)
        # self.items = val.split()
        part = val.strip().partition(" ")
        self.command = part[0]
        self.params = []  # comma seperated values
        p = part[2].split(",")
        for i in p:
            if i != "":
                self.params.append(i.strip())

    def copy(self, postfix):
        c = TokenLine(self.source + "-" + postfix, self.line, "")
        c.command = self.command
        c.params = self.params.copy()  # must be copy not ref.
        return c

    def __repr__(self):
        return (
            "<"
            + self.source
            + ","
            + str(self.line)
            + ","
            + str(self.command)
            + "|"
            + str(self.params)
            + ">"
        )


class CodeSection:
    " Code is broken into sections and linked after "

    def __init__(self, name):
        self.name = name
        self.labels = {}
        self.code = []
        self.counter = 0
        self.offset = 0
        self.rev_labels = {}

    def add_label(self, label):
        assert label not in self.labels
        self.labels[label] = self.counter

    def set_label(self, label, pos):
        #        assert label not in self.labels
        self.labels[label] = pos

    def add_code(self, code):
        " insert a code item"
        self.code += code
        self.counter += len(code)

    @property
    def length(self):
        return len(self.code)

    # shift the labels down
    def offset_labels(self, offset):
        offset_labels = {}
        for i in self.labels:
            offset_labels[i] = self.labels[i] + offset
        return offset_labels

    # insert an item and shift trailing labels down
    # for calculations of longer jumps
    def insert(self, pos, val):
        print("INSERT FAIL")
        raise

    def display(self):
        # reverse labels for disasm listing
        for i, j in self.labels.items():
            self.rev_labels[j] = i
        for offset, code in enumerate(self.code):
            l = ""
            if offset in self.rev_labels:
                l = self.rev_labels[offset]
            o = "{:05d} | ".format(offset)
            if isinstance(code, int):
                if (code < 31) or code == 128:
                    b = " | _ ," + str(int(code))
                else:
                    b = " | " + chr(code) + "," + str(int(code))
            else:
                b = 0
                code = 0
            print(o, l.ljust(10), " | ", disassemble(code).ljust(16), b)

    def __repr__(self):
        return str({"name": self.name, "labels": self.labels, "length": self.length})


class resolver:
    def __init__(self, name):
        self.name = name

    def __call__(self):
        return self.name
