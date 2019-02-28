from nmigen import *


__all__ = ["BonelessFormalInterface"]


class BonelessFormalInterface:
    def __init__(self, mem_wrport=None, ext_port=None):
        self.mem_wrport = mem_wrport
        self.ext_port   = ext_port

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

    def elaborate(self, platform):
        m = Module()
        if self.mem_wrport:
            m.d.comb += [
                self.mem_w_addr.eq(self.mem_wrport.addr),
                self.mem_w_data.eq(self.mem_wrport.data),
                self.mem_w_en  .eq(self.mem_wrport.en),
            ]
        if self.ext_port:
            m.d.comb += [
                self.ext_addr  .eq(self.ext_port.addr),
                self.ext_r_data.eq(self.ext_port.r_data),
                self.ext_r_en  .eq(self.ext_port.r_en),
                self.ext_w_data.eq(self.ext_port.w_data),
                self.ext_w_en  .eq(self.ext_port.w_en),
            ]
        return m.lower(platform)
