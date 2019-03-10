" system commands for the assembler"
from ast import literal_eval
from boneless.assembler.fixture import TokenLine

__all__ = []

commands = {}
commands_params = {}

assembler = None

# give commands access to the assembler object
def bind(assembler_object):
    global assembler
    assembler = assembler_object


def register(cls, count):
    def func_wrapper(name):
        commands[cls] = name
        commands_params[cls] = count

    return func_wrapper


@register(".section", 1)
def section(l):
    assembler.set_section(l.params[0])


@register(".int", 1)
def pos(l):
    v = assembler.labels[l.params[0]]
    print(v)


@register(".label", 1)
def label(l):
    " create a label , useful inside macros"
    val = TokenLine(l.source, l.line, l.params[0] + ": ")
    return [val]


@register(".string", 2)
def stringer(l):
    assembler.current_section.add_label(l.params[0])
    txt = literal_eval(l.params[1])
    assembler.current_section.add_code([len(txt)])
    for i in txt:
        assembler.current_section.add_code([int(ord(i))])


@register(".equ", 2)
def equ(l):
    name = l.params[0]
    val = literal_eval(l.params[1])
    assembler.variables[name] = val


# rebind a exisiting command
@register(".def", 2)
def defn(l):
    dst = l.params[0]
    src = l.params[1]
    assembler.instr_set[dst] = assembler.instr_set[src]
    assembler.instr_param[dst] = assembler.instr_param[src]
    assembler.instr_count[dst] = assembler.instr_count[src]


@register(".alloc", 2)
def alloc(l):
    name = l.params[0]
    cmds = [TokenLine(l.source + "-comm", l.line, name + ":")]
    v = assembler.resolve_symbol(l.params[1])
    if isinstance(v, int):
        for i in range(v):
            cmds.append(TokenLine(l.source + "-comm", l.line, "NOP"))
    return cmds


@register(".global", 0)
def glob(l):
    pass
