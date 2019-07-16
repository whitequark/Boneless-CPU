" system commands for the assembler"

from .mc import * 
__all__ = []

directives = {}
directives_params  = {}
assembler = None

# expose the entire assembler to this module
def bind(asm):
    global assembler
    assembler = asm

def register_directive(cls, count):
    def func_wrapper(name):
        directives[cls] = name
        directives_params[cls] = count

    return func_wrapper


@register_directive(".def", 2)
def define(m):
    return [Constant('test',5)]

@register_directive(".macro",0)
def macro(m):
    assembler._in_macro = True
    assembler._current_macro = Macro(m['args'])

@register_directive(".endm",0)
def end_macro(m):
    assembler._in_macro = False
    return assembler._current_macro

@register_directive(".section", 1)
def section(m):
    print("section",m)

@register_directive(".word",1)
def word(m):
    return int(m["args"], 0)

@register_directive(".window",0)
def window(m):
    return [0 for i in range(8)]

@register_directive(".alloc",1)
def alloc(m):
    return [0 for i in range(int(m['args'],0))]


# other commands 
# .include <filename>
# .macro <name>
# .endm
# .equ  /  define a constant , will need mc.Constant and tracking
