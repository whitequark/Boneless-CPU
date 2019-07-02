import enum
from nmigen import *
from nmigen.tools import bits_for


__all__ = []


@enum.unique
class ControlEnum(enum.IntEnum):
    @property
    def pretty_name(self):
        return self.name.replace("_", "-")

    @classmethod
    def signal(cls, **kwargs):
        width = max(cls).bit_length()
        def decoder(value):
            try:
                # return "{}/{:0{}b}".format(cls(value).pretty_name, value, width)
                return cls(value).pretty_name
            except ValueError:
                return str(value)
        return Signal(width, decoder=decoder, src_loc_at=1, **kwargs)
