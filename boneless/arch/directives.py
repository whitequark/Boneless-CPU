" system commands for the assembler"

from .mc import * 

__all__ = []

directives = {}
directives_params  = {}
assembler = None
stuff = {} 

# expose the entire assembler to this module
def bind(asm):
    global assembler
    assembler = asm

def register_directive(n, count):
    def func_wrapper(func):
        directives[n] = func 
        directives_params[n] = count
        stuff[n] = (func,n,count)
    return func_wrapper


def args(m):
    ar = m['args'].split(',')
    return ar

@register_directive(".equ", 2)
def equate(m):
    return [Constant(args(m)[0],int(args(m)[1]))]

@register_directive(".macro",0)
def macro(m):
    assembler._in_macro = True
    assembler._current_macro = Macro(m['args'])

@register_directive(".endm",0)
def end_macro(m):
    assembler._in_macro = False
    cm = assembler._current_macro
    assembler.macros[cm.name] = cm

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
