class Register:
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return "<register R" + str(self.val) + ">"

    def __call__(self):
        return int(self.val)


class TokenLine:
    " Wrap the token lines for debug"
    def __init__(self,source,line,items):
        self.source = source 
        self.line = line 
        self.items = items 

    def __repr__(self):
        return "<"+self.source+","+str(self.line)+","+str(self.items)+">"

    def __len__(self):
        return len(self.items)

    def __getitem__(self,i):
        return self.items[i]

    def parse(self):
        pass

class CodeSection:
    " Code is broken into sections and linked after "
    def __init__(self,name):
        self.name = name
        self.labels = {} 
        self.code = []
        self.counter = 0 
        self.offset = 0
        self.length = 0

    def add_label(self,label):
        assert label not in self.labels
        self.labels[label] = self.counter

    # shift the labels down
    def offset(self,n):
        for i in self.labels:
            self.labels[i] = self.labels[i] + offset

    # insert an item and shift trailing labels down
    # for calculations of longer jumps
    def insert(self,pos,val):
        print("INSERT FAIL")
        raise
