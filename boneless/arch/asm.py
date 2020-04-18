import re

from . import mc
from . import opcode

__all__ = ["TranslationError", "Assembler", "assemble", "disassemble"]


class TranslationError(Exception):
    " Fail on no translation "
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
    """
    Assembler of Boneless code
    """

    def __init__(self,instr_cls=opcode.Instr):
        self.instr_cls = instr_cls

        # convert text or take asm objects
        self.input = []

        # array of encoded 16 bit integers
        self.output = []

        # mappings of assembly
        self.constants = {}
        self.const_locs = {}
        self.label_addrs  = {}
        self.label_locs = {}

    def parse(self,input_d):
        if isinstance(input_d,str):
            self.parse_text(input_d)
        else:
            self.input.append(input_d)

    def parse_text(self,input_d):
        for index, line in enumerate(str(input_d).splitlines()):
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
            line_output_d = []
            if m["label"]:
                line_output_d.append(mc.Label(m["label"]))
            if m["instr"]:
                try:
                    line_output_d.append(self.instr_cls.from_str(m["instr"]))
                except ValueError as error:
                    while error.__cause__ is not None:
                        error = error.__cause__
                    raise TranslationError(f"{{0}} at {{loc}}", error,
                                           loc=(index,), lines=True) from None
            if m["direct"]:
                if m["direct"] == ".word":
                    line_output_d.append(int(m["args"], 0))
                else:
                    raise TranslationError(f"Unknown directive {m['direct']} at {{loc}}",
                                           loc=(index,), lines=True)
            self.input.append(line_output_d)

    def emit_text(self,input_d):
        output = []
        for index, elem in enumerate(input_d):
            if isinstance(elem, mc.Label):
                output.append(f"{elem.name}:")
            elif isinstance(elem, int):
                output.append(f"\t.word\t{hex(elem)}")
            elif isinstance(elem,self.instr_cls):
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
                elem_type_name = f"{type(elem).__module__}.{type(elem).__qualname__}"
                raise TranslationError(f"Unrecognized value {repr(elem)} of type {elem_type_name} "
                                       f"at {{loc}}", loc=(index,))
        output.append("")
        return "\n".join(output)


    def assemble(self):

        label_locs  = {}
        label_addrs = {}
        instr_sizes = {}

        constants = {}
        const_locs = {}

        fwd_adjust = 0

        def resolve(obj_addr, symbol):
            # If the label isn't defined it could mean one of the two things:
            #   * We're in the first relaxation pass.
            #   * It's an external symbol.
            # In both cases we return `None`, as a request to downstream code to lower to largest
            # possible encoding.
            if symbol in label_addrs:
                result = label_addrs[symbol] - obj_addr
                if result > 0:
                    # Each time we shrink a chunk, we need to move all labels after this chunk lower,
                    # or else relative forward offsets after this point may increase.
                    result -= fwd_adjust
            elif symbol in constants:
                result = constants[symbol]
            else:
                result = None

            return result

        def translate(elem, output_d, n_pass, *, indexes=(), allow_unresolved=None):
            length = None
            elem_addr = len(output_d)
            # Process empty entries
            if elem is None and n_pass == 1:
                # `None` in input_d is OK during the first pass as a placeholder for a complex address
                # computation that relies on a symbol that isn't defined yet; but after that it must
                # be expanded, because we never return closures in the output_d.
                output_d.append(None)
            # Literal integer
            elif isinstance(elem, int):
                output_d.append(elem)
            # Expand lists
            elif isinstance(elem, list):
                for index, nested_elem in enumerate(elem):
                    translate(nested_elem, output_d, n_pass,
                              indexes=(*indexes, index), allow_unresolved=allow_unresolved)
            # Absolute references, insert for later
            elif isinstance(elem,mc.AbsRef):
                output_d.append(elem)
            # Relative references, later
            elif isinstance(elem,mc.RelRef):
                output_d.append(elem)
            # Constants, add to dict for translation
            elif isinstance(elem, mc.Constant):
                if n_pass == 1:
                    if elem.name in self.constants:
                        raise TranslationError(f"Const {repr(elem.name)} at {{new}} has the same name "
                                               f"as the const at {{old}}",
                                               new=indexes, old=str(const_locs[elem.name]))
                    const_locs[elem.name] = indexes
                constants[elem.name] = elem.value
            # Label, add to dict
            elif isinstance(elem, mc.Label):
                if n_pass == 1:
                    if elem.name in label_addrs:
                        raise TranslationError(f"Label {repr(elem.name)} at {{new}} has the same name "
                                               f"as the label at {{old}}",
                                               new=indexes, old=label_locs[elem.name])
                    label_locs[elem.name] = indexes
                label_addrs[elem.name] = elem_addr
            # It's an Instruction! , process
            elif isinstance(elem, self.instr_cls):
                try:
                    # First, try encoding without relocation. This usually succeeds, and is faster.
                    length = elem.encode(output_d)
                except mc.UnresolvedRef:
                    try:
                        # Compute the expected instruction size; necessary since offsets are computed
                        # from address of the next instruction.
                        length = instr_sizes.get(indexes, elem.max_length)
                        # Second, relocate and try encoding again. This will always succeed if
                        # the referenced label is defined, and will refine our size estimate.
                        length = elem(lambda sym: resolve(elem_addr + length, sym)).encode(output_d)
                    except mc.UnresolvedRef as error:
                        # If we still can't encode it...
                        length = elem.max_length
                        if allow_unresolved is None:
                            # ... add a placeholder sized for the worst case during initial passes;
                            for _ in range(length):
                                output_d.append(None)
                        elif allow_unresolved:
                            # ... use the longest encoding if we're emitting relocations;
                            rel_length = elem(lambda sym: 0).encode(output_d, use_longest=True)
                            assert length == rel_length, f"Illegal longest encoding at {indexes}"
                        else:
                            # ... raise an error otherwise.
                            raise TranslationError(f"{{0}} at {{loc}}", error,
                                                   loc=indexes) from None
            # can be Executed, call it and return the result
            elif hasattr(elem, "__call__"):
                translate(elem(lambda sym: resolve(elem_addr, sym)), output_d, n_pass,
                          indexes=indexes, allow_unresolved=allow_unresolved)
                length = len(output_d) - elem_addr
            # it's not code, error out
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
            return output_d

        # Iterate to fixed point. This does more work than strictly necessary (if there are both
        # forward and backward references, at least three iterations), but produces obviously correct
        # result: if the (n-1)th and (n)th pass converged, then (n-1)th pass has updated every label
        # to the same value as in (n)th pass, and (n)th pass has relocated every reference to
        # the address of the label in either of them.
        n_pass = 1
        output_d = translate(self.input, [], n_pass)
        while True:
            fwd_adjust = 0
            old_output_d = output_d
            n_pass += 1
            output_d = translate(self.input, [], n_pass)
            if output_d == old_output_d:
                break

        # Convert absolute and relative references
        for index, elem in enumerate(output_d):
            if isinstance(elem,mc.Reference):
                if elem.name not in label_addrs:
                    raise TranslationError(f"Label {repr(elem.name)} does not exist at {index}")
                if isinstance(elem, mc.RelRef):
                    output_d[index] = label_addrs[elem.name]-index
                if isinstance(elem, mc.AbsRef):
                    output_d[index] = label_addrs[elem.name]

        # If there are unresolved relocations, ensure they are either reported as an error or emitted
        # as the longest possible encoding, for future linking.
        if None in output_d:
            fwd_adjust = 0
            n_pass += 1
            output_d = translate(self.input, [], n_pass, allow_unresolved=False)

        # store the mapping
        # constants, const_locs, labels, label_locs
        self.constants = constants
        self.const_locs = const_locs
        self.label_addrs  = label_addrs
        self.label_locs = label_locs

        # store the output_d
        self.output_d = output_d

        return output_d

    def info(self):
        info_data = {
            'constants' : self.constants,
            'const_locs' : self.const_locs,
            'label_addrs' : self.label_addrs,
            'label_locs' : self.label_locs,
        }
        return info_data

    def disassemble(self,input_d, labels=False, as_text=False):
        index  = 0
        output_d = []
        addr_f = [0]
        addr_r = {0: 0}
        while index < len(input_d):
            try:
                instr, length = self.instr_cls.decode(input_d, index)
                while instr.length != length:
                    # This instruction is not well-behaved: it will not roundtrip to a sequence of
                    # the same length, probably because it uses a noncanonical prefix form. Truncate
                    # the instruction so that the prefix is decoded separately and try again.
                    instr, length = self.instr_cls.decode(input_d[index:index + length - 1])
                output_d.append(instr)
                index += length
            except ValueError:
                output_d.append(input_d[index])
                index += 1
            addr_f.append(index)
            addr_r[index] = len(output_d)

        if labels:
            labels_at = set()
            for index, instr in enumerate(output_d):
                if isinstance(instr, self.instr_cls):
                    for op_name in instr.pc_rel_ops:
                        label_at = addr_f[index + 1] + getattr(instr, op_name).value
                        if label_at in range(addr_f[-1]):
                            labels_at.add(label_at)
                            setattr(instr, op_name, f"L{label_at}")
            for label_at in reversed(sorted(labels_at)):
                output_d.insert(addr_r[label_at], mc.Label(f"L{label_at}"))

        if as_text:
            return self.emit_text(output_d)
        else:
            return output_d

# helper functions
def assemble(input_d,*,instr_cls):
    asm = Assembler(instr_cls=instr_cls)
    asm.parse(input_d)
    output = asm.assemble()
    return output

def disassemble(input_d,*,instr_cls,labels=None,as_text=False):
    asm = Assembler(instr_cls=instr_cls)
    output = asm.disassemble(input_d,labels=labels,as_text=as_text)
    return output

