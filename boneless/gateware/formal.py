from nmigen import *


__all__ = ["BonelessFormalInterface"]


class BonelessFormalInterface:
    def __init__(self):
        # Active when an instruction is retired.
        self.stb        = Signal(    name="fi_stb")
        # Retired instruction and its PC.
        self.pc         = Signal(16, name="fi_pc")
        self.insn       = Signal(16, name="fi_insn")
        # Flags after the instruction is retired.
        self.flags      = Signal(4,  name="fi_flags")
        # Memory write that happened when the instruction was retired, if any.
        self.mem_w_addr = Signal(16, name="fi_mem_w_addr")
        self.mem_w_data = Signal(16, name="fi_mem_w_data")
        self.mem_w_en   = Signal(    name="fi_mem_w_en")
        # External bus reads and writes. Unlike the previous signals, these can be active
        # at any time during the cycle.
        self.ext_addr   = Signal(16, name="fi_ext_addr")
        self.ext_r_data = Signal(16, name="fi_ext_r_data")
        self.ext_r_en   = Signal(    name="fi_ext_r_en")
        self.ext_w_data = Signal(16, name="fi_ext_w_data")
        self.ext_w_en   = Signal(    name="fi_ext_w_en")

        self._all = [
            self.stb,
            self.pc, self.insn,
            self.flags,
            self.mem_w_en, self.mem_w_addr, self.mem_w_data,
            self.ext_addr, self.ext_r_data, self.ext_r_en, self.ext_w_data, self.ext_w_en
        ]
