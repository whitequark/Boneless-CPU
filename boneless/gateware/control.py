import enum
from nmigen import *


__all__ = ["ControlEnum", "MultiControlEnum"]


# We have to do an annoying metaclass dance because there's no @classproperty.
class ControlEnumMeta(enum.EnumMeta):
    @property
    def width(cls):
        return max(cls).bit_length()


@enum.unique
class ControlEnum(enum.IntEnum, metaclass=ControlEnumMeta):
    @classmethod
    def decoder(cls, value):
        try:
            return cls(value).name.replace("_", "-")
        except ValueError:
            return str(value)

    @classmethod
    def signal(cls, **kwargs):
        return Signal(cls.width, decoder=cls.decoder, src_loc_at=1, **kwargs)

    def __repr__(self):
        return "<{}: {:0{}b}>".format(self.name, self.value, self.width)


# We have to do an annoying metaclass dance because we want to do something like:
#
#   class MuxA(ControlEnum): ...
#   class MuxB(ControlEnum): ...
#   class Mode(MultiControlEnum):
#       FOO = (MuxA.X, MuxB.Y)
#
# but by the time we're inside the body of `Mode` it is no longer possible to access the names from
# the outer scope, so we can't easily name `MuxA` for example, so we rewrite it as:
#
#   class Mode(MultiControlEnum, layout=[MuxA, MuxB]):
#       FOO = ("X", "Y")
class MultiControlEnumMeta(ControlEnumMeta):
    @classmethod
    def __prepare__(metacls, name, bases, **kwargs):
        return super().__prepare__(name, bases)

    def __new__(cls, name, bases, classdict, layout=None):
        if layout is not None:
            classdict, old_classdict = type(classdict)(), classdict

            offsets = []
            offset  = 0
            for enum in layout.values():
                offsets.append(offset)
                offset += enum.width

            for key in old_classdict:
                if key.startswith("_"):
                    classdict[key] = old_classdict[key]
                else:
                    value = 0
                    for item, enum, offset in zip(old_classdict[key], layout.values(), offsets):
                        value |= enum[item] << offset
                    classdict[key] = value

            @classmethod
            def expand(cls, m, signal):
                rec = Record([(name, enum.width)   for (name, enum) in layout.items()],
                             src_loc_at=1)
                for name, enum in layout.items():
                    rec[name].decoder = enum.decoder
                m.d.comb += rec.eq(signal)
                return rec
            classdict["expand"] = expand

        return super().__new__(cls, name, bases, classdict)


class MultiControlEnum(ControlEnum, metaclass=MultiControlEnumMeta):
    def foo(self):
        pass
