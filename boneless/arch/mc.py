import abc
import re
import textwrap
from parse import parse
from string import Formatter


__all__ = ["UnresolvedRef", "Operand", "Instr"]


class UnresolvedRef(Exception):
    pass


class OperandMeta(abc.ABCMeta):
    def __new__(metacls, name, bases, namespace):
        if "__slots__" not in namespace:
            namespace["__slots__"] = []

        return super().__new__(metacls, name, bases, namespace)


class Operand(metaclass=OperandMeta):
    __slots__ = ["value"]

    format  = abc.abstractproperty()
    prepare = abc.abstractproperty()

    def __init__(self, value):
        if isinstance(value, type(self)):
            self.value = value.value
        else:
            self.value = self.prepare(value)

    def __repr__(self):
        return repr(self.value)

    @classmethod
    def from_str(cls, input):
        parsed = parse(cls.format, input)
        if parsed is None:
            raise ValueError(f"Illegal operand {repr(input)}; expected {repr(cls.format)}")
        return cls(*parsed.fixed, **parsed.named)

    def __str__(self):
        return self.format.format(self.value)

    @classmethod
    def from_int(cls, input):
        return cls(cls.value_from_bits(input))

    def __int__(self):
        if hasattr(self.value, "__int__"):
            return int(self.bits_from_value(self.value))
        else:
            raise UnresolvedRef(f"Unresolved reference '{self.value}' in operand")

    @classmethod
    def value_from_bits(cls, input):
        return input

    @classmethod
    def bits_from_value(cls, value):
        return value

    def __call__(self, resolver):
        return self

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.value == other.value or self.value == other

    def __bool__(self):
        return bool(self.value)


class InstrMeta(abc.ABCMeta):
    def __new__(metacls, instr_name, bases, namespace):
        # Merge the instruction coding (if any) and codings from base classes.
        coding = namespace.get("coding")
        alias  = False
        for base in bases:
            if not hasattr(base, "coding"):
                pass
            elif coding is None:
                coding = base.coding
                if "-" not in coding:
                    alias = True
            else:
                assert len(coding) == len(base.coding)
                for idx, (new_bit, base_bit) in enumerate(zip(coding, base.coding)):
                    assert "-" in (new_bit, base_bit)
                    if new_bit == "-":
                        coding = coding[:idx] + base_bit + coding[idx+1:]
        if coding is not None:
            namespace["coding"] = coding
            if "-" not in coding:
                namespace["alias"] = alias

        # If the coding is complete, create the constructor and accessors for fields.
        if coding is not None and "-" not in coding:
            for base in bases:
                if issubclass(base, Instr):
                    instr_base = base
                if hasattr(base, "operands"):
                    operands = base.operands
            assert None not in (instr_base.abbrevs, instr_base.mnemonics, instr_base.decodings)

            field_formats = list(Formatter().parse(operands))
            namespace["_field_types"] = {field: instr_base.formats[format]
                                         for (_, field, format, _) in field_formats}
            namespace["_field_format"] = "".join("{}{{{}}}".format(literal, field)
                                                 for (literal, field, _, _) in field_formats)

            code = ""

            instr_code   = int(re.sub(r"[^01]", "0", coding), 2)
            instr_mask   = int(re.sub(r"[^01]", "0", coding.replace("0", "1")), 2)
            operand_mask = int(re.sub(r"[^01]", "1", coding.replace("1", "0")), 2)

            fields = {}
            for match in re.finditer(r"([A-Za-z])\1*", coding):
                field_name   = instr_base.abbrevs[match[1]]
                field_mask   = (1 << (match.end() - match.start())) - 1
                field_offset = len(coding) - match.end()

                fields[field_name] = (field_mask, field_offset)

                code += textwrap.dedent(f"""
                @property
                def {field_name}(self):
                    return self._{field_name}

                @{field_name}.setter
                def {field_name}(self, value):
                    self._{field_name} = self._field_types[{repr(field_name)}](value)
                """)

            namespace["__slots__"] = [f"_{field}" for field in fields]

            code += textwrap.dedent(f"""
            def __init__(self, {", ".join(fields)}):
                '''Unpack an instruction from Python code.'''
                {"; ".join(f"self.{field} = {field}"
                           for field in fields)}

            def __repr__(self):
                '''Pack an instruction into Python code.'''
                return f"{instr_name}({", ".join(f"{{repr(self._{field})}}"
                                                 for field in fields)})"

            def __str__(self):
                '''Pack an instruction into text code.'''
                return f"{instr_name}\t{{self._field_format.format({
                    ", ".join(f"{field}=self._{field}"
                              for field in fields)})}}"

            @classmethod
            def _from_int(cls, input):
                return cls({", ".join(f"{field}=cls._field_types[{repr(field_name)}]"
                                      f".from_int((input >> {offset}) & {mask})"
                                      for field, (mask, offset) in fields.items())})

            def __int__(self):
                '''Pack an instruction into machine code.'''
                return {instr_code} | {
                    " | ".join(f"((int(self._{field}) & {mask}) << {offset})"
                               for field, (mask, offset) in fields.items())}

            __index__ = __int__

            def __call__(self, resolver):
                return type(self)({", ".join(f"{field}=self._{field}(resolver)"
                                             for field in fields)})

            def __eq__(self, other):
                # Make sure aliased instructions compare equal no matter the direction.
                return ((isinstance(self, type(other)) or isinstance(other, type(self))) and
                        {" and ".join(f"self._{field} == other._{field}"
                                      for field in fields)})
            """)

            # It's somewhat unfortunate that we have to resort to `eval` here, but there are good
            # (if I say so myself) reasons for it:
            #  1. Python's argument parsing is complex, and there is no especially good way to
            #     say "parse this args tuple and kwargs dict into a linear sequence of arguments".
            #  2. Other than __init__, writing the same thing with a bunch of lambdas and dicts
            #     and `getattr()` is definitely possible, but way too slow on CPython.
            #  3. It would also be harder to read and understand. (Not that this approach is very
            #     easy to understand either, but it is -easier-. Relatively speaking.)
            exec(code, globals(), namespace)

            # Create the instruction class and register mnemonics as well as opcodes in global
            # lookup tables, to speed up assembly/disassembly.
            cls = super().__new__(metacls, instr_name, bases, namespace)
            instr_base.mnemonics[instr_name.upper()] = cls
            if not alias:
                operand_code = 0
                while True:
                    instr_opcode = instr_code | operand_code
                    if instr_opcode in instr_base.decodings:
                        raise ValueError(
                            "Encoding {:0{}b} of instruction {} conflicts with instruction {}"
                            .format(instr_opcode, len(coding), instr_name,
                                    instr_base.decodings[instr_opcode].__name__))
                    instr_base.decodings[instr_code | operand_code] = cls
                    if operand_code == operand_mask:
                        break
                    # The following line cleverly uses carries to make a counter only from the bits
                    # that are set in `operand_mask`. To understand it, consider that `instr_mask`
                    # is the inverse of `operand_mask`, and adding 1 to a 011...1 chunk changes it
                    # into a 100...0 chunk.
                    operand_code = ((operand_code | instr_mask) + 1) & operand_mask
            return cls

        else:
            if "__slots__" not in namespace:
                namespace["__slots__"] = []

            return super().__new__(metacls, instr_name, bases, namespace)


class Instr(metaclass=InstrMeta):
    # ISA-wide properties
    abbrevs    = None
    formats    = None
    _parsers   = None
    mnemonics  = None
    decodings  = None
    # Per-instruction properties
    operands   = abc.abstractproperty()
    alias      = abc.abstractproperty()
    max_length = 1

    @classmethod
    def from_str(cls, input):
        """Unpack an instruction from text code."""
        # First, canonicalize the whitespace.
        input = re.sub(r"\s*(,)\s*|\s+", r"\1 ", input)
        parts = input.split(maxsplit=1)
        if len(parts) == 1:
            mnemonic, = parts
            operands  = ""
        else:
            mnemonic, operands = parts
        instr_cls = cls.mnemonics.get(mnemonic.upper())
        if instr_cls is None:
            raise ValueError(f"Unknown mnemonic '{mnemonic}'")
        if cls._parsers is None:
            cls._parsers = {format: operand_cls.from_str
                            for format, operand_cls in cls.formats.items()}
        try:
            parsed = parse(instr_cls.operands, operands, cls._parsers)
            error  = None
        except ValueError as e:
            parsed = None
            error  = e
        if parsed is None:
            raise ValueError(f"Illegal operands {repr(operands)} for instruction "
                             f"{instr_cls.__name__}; "
                             f"expected {repr(instr_cls.operands)}") from error
        return instr_cls(*parsed.fixed, **parsed.named)

    @classmethod
    def from_int(cls, input):
        """Unpack an instruction from machine code."""
        opcode = int(input)
        instr_cls = cls.decodings.get(opcode)
        if instr_cls is None:
            raise ValueError(f"Unknown encoding {bin(opcode)}")
        return instr_cls._from_int(opcode)

    @property
    def length(self):
        """Determine length of a variable instruction, in units."""
        return 1

    def encode(self, stream):
        """Encode instruction, append to the stream of units, and return the encoded length."""
        stream.append(int(self))
        return 1

    @classmethod
    def decode(cls, stream, index=0):
        """Decode instruction from the stream of units at given index, and return the instruction
        as well as its length."""
        return cls.from_int(stream[index]), 1
