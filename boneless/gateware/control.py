from enum import Enum, EnumMeta
from amaranth import *


__all__ = ["EnumGroup"]


# We have to do an annoying metaclass dance because we want to do something like:
#
#   class MuxA(Enum): ...
#   class MuxB(Enum): ...
#   class Mode(EnumGroup):
#       FOO = (MuxA.X, MuxB.Y)
#
# but by the time we're inside the body of `Mode` it is no longer possible to access the names from
# the outer scope, so we can't easily name `MuxA` for example, so we rewrite it as:
#
#   class Mode(EnumGroup, layout=[MuxA, MuxB]):
#       FOO = ("X", "Y")
class EnumGroupMeta(EnumMeta):
    @classmethod
    def __prepare__(metacls, name, bases, **kwargs):
        return super().__prepare__(name, bases)

    def __new__(cls, name, bases, classdict, layout=None):
        if layout is not None:
            classdict, old_classdict = type(classdict)(), classdict
            classdict._cls_name = cls

            offsets = []
            offset  = 0
            for enum in layout.values():
                offsets.append(offset)
                offset += Shape.cast(enum).width

            for key in old_classdict:
                if key.startswith("_"):
                    classdict[key] = old_classdict[key]
                else:
                    value = 0
                    for item, enum, offset in zip(old_classdict[key], layout.values(), offsets):
                        value |= enum[item].value << offset
                    classdict[key] = value

            @classmethod
            def expand(cls, m, signal):
                rec = Record([*layout.items()], src_loc_at=1)
                m.d.comb += rec.eq(signal)
                return rec
            classdict["expand"] = expand

        return super().__new__(cls, name, bases, classdict)


class EnumGroup(Enum, metaclass=EnumGroupMeta):
    def foo(self):
        pass
