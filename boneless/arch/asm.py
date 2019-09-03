import re

from . import mc
from . import directives
from .opcode import Instr

__all__ = ["TranslationError", "assemble", "disassemble"]


class TranslationError(Exception):
    def __init__(self, message, *args, lines=False, **locs):
        super().__init__(message, *args)
        self.lines = lines
        self.locs  = locs

    def __str__(self):
        if self.lines:
            return self.args[0].format(*self.args[1:], **{
                loc: f"line {indexes[0] + 1}"
                for loc, indexes in self.locs.items()
            })
        else:
            return self.args[0].format(*self.args[1:], **{
                loc: f"indexes {''.join(f'[{index}]' for index in indexes)}"
                for loc, indexes in self.locs.items()
            })

class Assembler:
    def __init__(self,instr_cls=Instr):
        self.instr_cls = instr_cls
        self.output = []
        self.input = [] 

        directives.bind(self)
        self.directives = directives.directives

        self._in_macro = False
        self._current_macro = None
        self.macros = {}

        self.constants = {}
        self.label_locs  = {}
        self.label_addrs = {}

    def parse(self,input):
        if isinstance(input,str):
            self.parse_text(input)
        else:
            self.input.append(input)

    def parse_text(self,input):
        for index, line in enumerate(str(input).splitlines()):
            m = re.match(r"""
                ^\s*
                (?: (?P<label>[a-z][a-z0-9]*):\s*)?
                (?:
                |   (?P<instr>[a-z].*?)
                |   (?P<direct>\.[a-z][a-z0-9]*)\s*(?P<args>.*?)
                )\s*
                (?: ;.*)?
                \s*$
            """, line, re.I|re.X)
            line_output = []
            if m["label"]:
                line_output.append(mc.Label(m["label"]))
            if m["instr"]:
                try:
                    line_output.append(self.instr_cls.from_str(m["instr"]))
                except ValueError as error:
                    while error.__cause__ is not None:
                        error = error.__cause__
                    raise TranslationError(f"{{0}} at {{loc}}", error,
                                           loc=(index,), lines=True) from None
            if m["direct"]:
                if m["direct"] in self.directives:
                    val = self.directives[m['direct']](m)
                    if val != None:
                        line_output.append(val)
                else:
                    raise TranslationError(f"Unknown directive {m['direct']} at {{loc}}",
                                           loc=(index,), lines=True)
            if self._in_macro:
                self._current_macro.add(line_output)
            else:
                self.input.append(line_output)


    def emit_text(self):
        output = []
        for index, elem in enumerate(self.input):
            if isinstance(elem, mc.Label):
                output.append(f"{elem.name}:")
            elif isinstance(elem, int):
                output.append(f"\t.word\t{hex(elem)}")
            elif isinstance(elem, self.instr_cls):
                mnemonic = str(elem)
                padding  = "\t" * max(0, 4 - len(mnemonic.expandtabs()) // 8)
                try:
                    words = []
                    elem.encode(words)
                    encoding = " ".join("{:0{}X}".format(word, len(elem.coding) // 4)
                                        for word in words)
                except mc.UnresolvedRef:
                    encoding = "<reloc>"
                output.append(f"\t{mnemonic}{padding}; {encoding}")
            else:
                raise TranslationError(f"Unrecognized value {repr(elem)} of type {elem_type_name} "
                                       f"at {{loc}}", loc=(index,))
        output.append("")
        return "\n".join(output)


    def assemble(self):
        instr_sizes = {}
        fwd_adjust  = 0

        def resolve(obj_addr, symbol):
            # If the label isn't defined it could mean one of the two things:
            #   * We're in the first relaxation pass.
            #   * It's an external symbol.
            # In both cases we return `None`, as a request to downstream code to lower to largest
            # possible encoding.
            if symbol in self.label_addrs:
                result = self.label_addrs[symbol] - obj_addr
                if result > 0:
                    # Each time we shrink a chunk, we need to move all labels after this chunk lower,
                    # or else relative forward offsets after this point may increase.
                    result -= fwd_adjust
            elif symbol in self.constants:
                result = self.constants[symbol]
            else:
                result = None
            return result

        def translate(elem, output, n_pass, *, indexes=(), allow_unresolved=None):
            length = None
            elem_addr = len(output)
            if elem is None and n_pass == 1:
                # `None` in input is OK during the first pass as a placeholder for a complex address
                # computation that relies on a symbol that isn't defined yet; but after that it must
                # be expanded, because we never return closures in the output.
                output.append(None)
            elif isinstance(elem, int):
                output.append(elem)
            elif isinstance(elem, list):
                for index, nested_elem in enumerate(elem):
                    translate(nested_elem, output, n_pass,
                              indexes=(*indexes, index), allow_unresolved=allow_unresolved)
            elif isinstance(elem, mc.Macro):
                # TODO process macro and return
                pass
            elif isinstance(elem, mc.Constant):
                if n_pass == 1:
                    if elem.name in self.constants:
                        raise TranslationError(f"Const {repr(elem.name)} at {{new}} has the same name "
                                               f"as the const at {{old}}",
                                               new=indexes, old=str(const_locs[elem.name]))

                        label_locs[elem.name] = indexes
                self.constants[elem.name] = elem.value
            elif isinstance(elem, mc.Label):
                if n_pass == 1:
                    if elem.name in self.label_addrs:
                        raise TranslationError(f"Label {repr(elem.name)} at {{new}} has the same name "
                                               f"as the label at {{old}}",
                                               new=indexes, old=self.label_locs[elem.name])
                    self.label_locs[elem.name] = indexes
                self.label_addrs[elem.name] = elem_addr
            elif isinstance(elem, self.instr_cls):
                try:
                    # First, try encoding without relocation. This usually succeeds, and is faster.
                    length = elem.encode(output)
                except mc.UnresolvedRef:
                    try:
                        # Compute the expected instruction size; necessary since offsets are computed
                        # from address of the next instruction.
                        length = instr_sizes.get(indexes, elem.max_length)
                        # Second, relocate and try encoding again. This will always succeed if
                        # the referenced label is defined, and will refine our size estimate.
                        length = elem(lambda sym: resolve(elem_addr + length, sym)).encode(output)
                    except mc.UnresolvedRef as error:
                        # If we still can't encode it...
                        length = elem.max_length
                        if allow_unresolved is None:
                            # ... add a placeholder sized for the worst case during initial passes;
                            for _ in range(length):
                                output.append(None)
                        elif allow_unresolved:
                            # ... use the longest encoding if we're emitting relocations;
                            rel_length = elem(lambda sym: 0).encode(output, use_longest=True)
                            assert length == rel_length, f"Illegal longest encoding at {indexes}"
                        else:
                            # ... raise an error otherwise.
                            raise TranslationError(f"{{0}} at {{loc}}", error,
                                                   loc=indexes) from None
            elif hasattr(elem, "__call__"):
                translate(elem(lambda sym: resolve(elem_addr, sym)), output, n_pass,
                          indexes=indexes, allow_unresolved=allow_unresolved)
                length = len(output) - elem_addr
            else:
                elem_type_name = f"{type(elem).__module__}.{type(elem).__qualname__}"
                raise TranslationError(f"Unrecognized value {repr(elem)} of type {elem_type_name} "
                                       f"at {{loc}}", loc=indexes)
            # The assembler will terminate as long as two conditions are fulfilled:
            #  1. The size of relocatable chunks never gets higher as the relative offsets shrink, and
            #  2. The contents of relocatable chunks only depends on offsets.
            # In other words, each relocatable chunk is a linear function of offsets. We can't easily
            # check (2), but we can and do check (1) here as a precaution.
            if length is not None:
                old_length = instr_sizes.get(indexes, length)
                assert length <= old_length, f"Expansion at {indexes}: {old_length} to {length}"
                instr_sizes[indexes] = length
                # Correct the offset in future forward relocations by accounting for backwards shift
                # of labels caused by the instruction we may have just shrunk.
                nonlocal fwd_adjust
                fwd_adjust += old_length - length
            return output

        # Iterate to fixed point. This does more work than strictly necessary (if there are both
        # forward and backward references, at least three iterations), but produces obviously correct
        # result: if the (n-1)th and (n)th pass converged, then (n-1)th pass has updated every label
        # to the same value as in (n)th pass, and (n)th pass has relocated every reference to
        # the address of the label in either of them.
        n_pass = 1
        output = translate(self.input, [], n_pass)
        while True:
            fwd_adjust = 0
            old_output = output
            n_pass += 1
            output = translate(self.input, [], n_pass)
            if output == old_output:
                break

        # If there are unresolved relocations, ensure they are either reported as an error or emitted
        # as the longest possible encoding, for future linking.
        if None in output:
            fwd_adjust = 0
            n_pass += 1
            output = translate(self.input, [], n_pass, allow_unresolved=False)

        return output


    def disassemble(self,input,labels=False, as_text=False):
        index  = 0
        output = []
        addr_f = [0]
        addr_r = {0: 0}
        while index < len(input):
            try:
                instr, length = self.instr_cls.decode(input, index)
                while instr.length != length:
                    # This instruction is not well-behaved: it will not roundtrip to a sequence of
                    # the same length, probably because it uses a noncanonical prefix form. Truncate
                    # the instruction so that the prefix is decoded separately and try again.
                    instr, length = self.instr_cls.decode(input[index:index + length - 1])
                output.append(instr)
                index += length
            except ValueError:
                output.append(input[index])
                index += 1
            addr_f.append(index)
            addr_r[index] = len(output)

        if labels:
            labels_at = set()
            for index, instr in enumerate(output):
                if isinstance(instr, self.instr_cls):
                    for op_name in instr.pc_rel_ops:
                        label_at = addr_f[index + 1] + getattr(instr, op_name).value
                        if label_at in range(addr_f[-1]):
                            labels_at.add(label_at)
                            setattr(instr, op_name, f"L{label_at}")
            for label_at in reversed(sorted(labels_at)):
                output.insert(addr_r[label_at], mc.Label(f"L{label_at}"))

        if as_text:
            return emit_text(output)
        else:
            return output

# short cuts 

def assemble():
    pass

def disassemble():
    pass
