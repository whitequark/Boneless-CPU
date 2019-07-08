import abc
import parse

from . import mc


__all__ = ["Reg", "Imm3AL", "Imm3SR", "Imm5", "Imm8", "Imm13", "Instr"]


def _signed(value, bits):
    if value & (1 << (bits - 1)):
        return value | (-1 << bits)
    return value


class Reg(mc.Operand):
    format    = "R{:d}"

    @classmethod
    def prepare(cls, value):
        value = int(value)
        if value not in range(0, 8):
            raise ValueError("Register operand must be one of R0 to R7")
        return value

    def __repr__(self):
        return str(self)

    @parse.with_pattern(r"R\d+")
    @classmethod
    def from_str(cls, input):
        return super().from_str(input)


class Imm(mc.Operand):
    format     = "{:#x}"
    bits       = abc.abstractproperty()
    values     = abc.abstractproperty()

    @classmethod
    def prepare(cls, value):
        if hasattr(value, "__int__"):
            value = int(value)
        else:
            try:
                value = int(value, 0)
            except ValueError:
                return value # will be resolved later
        if value not in cls.values:
            raise ValueError(f"Immediate operand {value} must be in range "
                             f"{cls.values.start}..{cls.values.stop}")
        return value

    @property
    def is_legal(self):
        return self.value in range(-1 << self.bits - 1, 1 << self.bits - 1)

    @classmethod
    def from_str(cls, input):
        return cls(input)

    @classmethod
    def value_from_bits(cls, input):
        return _signed(input, cls.bits)

    def __str__(self):
        if hasattr(self.value, "__int__"):
            return self.format.format(self.value)
        return self.value

    def __call__(self, resolver):
        if hasattr(self.value, "__int__"):
            return self # never relocate literals
        rel_value = resolver(self.value)
        if rel_value is None:
            return self # undefined reference
        return type(self)(rel_value)


class ImmLUT(Imm):
    lut_to_imm = abc.abstractproperty()
    imm_to_lut = abc.abstractproperty()

    @property
    def is_legal(self):
        return (self.value & 0xffff) in self.imm_to_lut

    @classmethod
    def value_from_bits(cls, input):
        return cls.lut_to_imm[input]

    @classmethod
    def bits_from_value(cls, value):
        # For legal immediates, look up the values in the inverse LUT.
        # For illegal immediates, trim the value to the part that fits into the instruction;
        # the rest of the immediate will be handled in `Instr.encode()`.
        return cls.imm_to_lut.get(value & 0xffff, value & ((1 << cls.bits) - 1))


class Imm3AL(ImmLUT):
    bits       = 3
    values     = range(-1 << 15, 1 << 16)
    lut_to_imm = [0x0000, 0x0001, 0x8000, 0x1234, # FIXME
                  0x00ff, 0xff00, 0x7fff, 0xffff]
    imm_to_lut = {v: k for k, v in enumerate(lut_to_imm)}

class Imm3SR(ImmLUT):
    bits       = 3
    values     = range(0, 16)
    lut_to_imm = [8, 1, 2, 3, 4, 5, 6, 7]
    imm_to_lut = {v: k for k, v in enumerate(lut_to_imm)}

class Imm5 (Imm):
    bits       = 5
    values     = range(-1 << 15, 1 << 16)

class Imm8 (Imm):
    bits       = 8
    values     = range(-1 << 15, 1 << 16)

class Imm13(Imm):
    bits       = 13
    values     = range(-1 << bits, 1 << bits)

    @property
    def is_legal(self):
        return self.value in range(-1 << self.bits - 1, 1 << self.bits)

    @classmethod
    def value_from_bits(cls, input):
        return input


class Instr(mc.Instr):
    abbrevs    = {"D": "rsd", "A": "ra", "B": "rb", "i": "imm"}
    formats    = {"R": Reg, "I3AL": Imm3AL, "I3SR": Imm3SR, "I5": Imm5, "I8": Imm8, "I13": Imm13}
    mnemonics  = {}
    decodings  = {}

    _i3_mask   = 0b0000000000000_111
    _i13_mask  = 0b000_1111111111111
    _ext_code  = 0b110_0000000000000
    _ext_mask  = 0b111_0000000000000

    @property
    def max_length(self):
        if hasattr(self, "imm"):
            return 2
        return 1

    @property
    def length(self):
        if hasattr(self, "imm") and not self.imm.is_legal:
            return 2 # EXTI plus instruction
        return 1 # just the instruction

    def encode(self, stream, use_longest=False):
        # Translate the instruction first, so that we don't append anything to the stream if there
        # is an unresolved relocation.
        instr_encoding = int(self)
        length = 1
        # If the instruction has an immediate...
        if hasattr(self, "imm"):
            # ... which is too large to fit into the field in the encoding, or might participate
            # in relocation later...
            if use_longest or not self.imm.is_legal:
                # ... then encode an EXTI instruction first.
                stream.append(self._ext_code | ((self.imm.value >> 3) & self._i13_mask))
                length += 1
        # And encode the instruction in either case.
        stream.append(instr_encoding)
        return length

    @classmethod
    def decode(cls, stream, index=0):
        # If there's an EXTI prefix...
        if stream[index] & cls._ext_mask == cls._ext_code:
            ext_imm = stream[index] & cls._i13_mask
            # ... followed by a non-EXTI instruction...
            if len(stream) > index + 1 and (stream[index + 1] & cls._ext_mask != cls._ext_code):
                # ... then decode two opcodes as one instruction with a large immediate...
                instr   = cls.from_int(stream[index + 1])
                ext_imm = _signed((ext_imm << 3) | (stream[index + 1] & cls._i3_mask), 16)
                if hasattr(instr, "imm"):
                    # ... if it takes an immediate at all.
                    instr.imm.value = ext_imm
                    return instr, 2
        # Othrewise, decode one opcode as one instruction, as usual.
        return cls.from_int(stream[index]), 1
