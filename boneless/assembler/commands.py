" system commands for the assembler"

__all__ = []

commands = {}

assembler = None

# give commands access to the assembler object
def bind(assembler_object):
    global assembler
    assembler = assembler_object


def register(cls):
    def func_wrapper(name):
        commands[cls] = name

    return func_wrapper


@register(".int")
def pos(s):
    v = assembler.labels[s[0]]
    print(v)


@register(".label")
def label(name):
    return [[name[0] + ":"]]


@register(".string")
def stringer(s):
    print(s)
    print("|")
    for i in s[0]:
        print(ord(i))
    print("|")
    print(assembler)
    return [[]]


@register(".equ")
def equ(s):
    pass


@register(".global")
def glob(s):
    pass


@register(".multi")
def multi(a, b, c, d):
    print(a, b, c, d)
