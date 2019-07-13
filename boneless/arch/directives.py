" system commands for the assembler"

__all__ = []

directives = {}
directives_params  = {}


def register(cls, count):
    def func_wrapper(name):
        directives[cls] = name
        directives_params[cls] = count

    return func_wrapper


@register(".section", 1)
def section(m):
    print("section",m)

@register(".word",1)
def word(m):
    return int(m["args"], 0)

@register(".window",0)
def window(m):
    return [0 for i in range(8)]

@register(".alloc",1)
def alloc(m):
    return [0 for i in range(int(m['args'],0))]


# other commands 
# .include <filename>
# .macro <name>
# .endm
# .equ  /  define a constant , will need mc.Constant and tracking
