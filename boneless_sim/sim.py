import array

__all__ = ["BonelessSimulator"]


# Used to calculate sign bit and also
# overflow.
def sign(val):
    return int((val & 0x08000) != 0)

# Works with signed _or_ unsigned math.
def to_unsigned16b(val):
    if val < 0:
        return val + 65536
    elif val >= 65536:
        return val - 65536
    else:
        return val


class BonelessSimulator:
    def __init__(self, start_pc=0x10, memsize=1024, io_callback=None):
        def memset():
            for i in range(memsize):
                yield 0

        self.sim_active = False
        self.window = 0
        self.pc = start_pc
        self.flags = { "Z" : 0, "S" : 0, "C" : 0, "V" : 0}
        self.mem = array.array("H", memset())
        self.io_callback = io_callback

    def __enter__(self):
        self.sim_active = True
        return self

    def __exit__(self, type, value, traceback):
        self.sim_active = False

    def regs(self):
        return self.mem[self.window:self.window+16]

    def read_reg(self, reg):
        return self.mem[self.reg_loc(reg)]

    def reg_loc(self, offs):
        return self.window + offs

    def set_pc(self, new_pc):
        if not self.sim_active:
            self.pc = new_pc

    def write_reg(self, reg, val):
        if not self.sim_active:
            self.mem[self.reg_loc(reg)] = val

    def load_program(self, contents, start=0x10):
        if not self.sim_active:
            for i, c in enumerate(contents):
                self.mem[i + start] = c

    # Replace the currently-defined I/O callback with a new one.
    # I/O callback has the following signature:
    # fn(addr, write=False). Reads return read value.
    # Writes return anything (including None), return value ignored.
    def register_io(self, callback):
        """Replace the currently-defined I/O callback with a new one.

        The I/O callback has the following signature:
        ``fn(addr, data=None)``, where `addr` is the I/O address to read/write,
        and `data` is the data to write, `None` is this I/O access is a read.
        Reads return value read from I/O device. Writes return None, return
        value ignored.
        """
        if not self.sim_active:
            self.io_callback = callback

    def stepi(self):
        opcode = self.mem[self.pc]
        op_class = (0xF800 & opcode) >> 11

        if op_class in [0x00, 0x01]:
            self.do_a_class(opcode)
            self.pc = to_unsigned16b(self.pc + 1)
        elif op_class in [0x03, 0x04]:
            self.do_s_class(opcode)
            self.pc = to_unsigned16b(self.pc + 1)
        elif op_class in [0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F]:
            pc_incr = self.do_i_class(opcode)
            self.pc = to_unsigned16b(self.pc + pc_incr)
        else:
            raise NotImplementedError("Step Instruction")

    # Utility Functions- Do not call directly
    def _write_reg(self, reg, val):
        self.mem[self.reg_loc(reg)] = val

    # Handle Opcode Clases- Do not call directly
    def do_a_class(self, opcode):
        dst = (0x0700 & opcode) >> 8
        opa = (0x00E0 & opcode) >> 5
        opb = (0x001C & opcode) >> 2
        typ = (0x0003 & opcode)
        code = (0x0800 & opcode) >> 11

        val_a = self.read_reg(opa)
        val_b = self.read_reg(opb)
        s_a = sign(val_a)
        s_b = sign(val_b)

        if code and (typ in range(3)):
            # ADD
            if typ == 0x00:
                raw = val_a + val_b
                self._write_reg(dst, to_unsigned16b(raw))
            # SUB/CMP
            else:
                raw = val_a + ~val_b + 1

                # CMP skips writing results
                if typ == 0x01:
                    self._write_reg(dst, to_unsigned16b(raw))

            # Carry and V use 65xx semantics:
            # http://www.righto.com/2012/12/the-6502-overflow-flag-explained.html
            # http://teaching.idallen.com/dat2343/10f/notes/040_overflow.txt
            s_r = sign(raw)
            self.flags["C"] = int(raw > 65535)
            self.flags["V"] = int((s_a and not s_b and not s_r) or (not s_a and s_b and s_r))
        elif not code and typ in range(3):
            if typ == 0x00:
                raw = val_a & val_b
            elif typ == 0x01:
                raw = val_a | val_b
            else:
                raw = val_a ^ val_b
            self._write_reg(dst, raw)
        else:
            raise NotImplementedError("Do A Class")

        self.flags["Z"] = (raw == 0)
        self.flags["S"] = sign(raw)


    def do_s_class(self, opcode):
        dst = (0x0700 & opcode) >> 8
        opa = (0x00E0 & opcode) >> 5
        amt = (0x001E & opcode) >> 1
        typ = (0x0001 & opcode)
        code = (0x0800 & opcode) >> 11

        if code:
            # SLL/MOV
            if typ == 0:
                raw = self.read_reg(opa) << amt
            # ROT
            else:
                # Don't actually rotate, but implement
                # in terms of bitshifts.
                val = self.read_reg(opa)
                hi_mask = ((1 << amt) - 1) << (15 - amt + 1)
                lo_mask = (1 << (15 - amt + 1)) - 1
                raw_hi = (hi_mask & val) >> (15 - amt)
                raw_lo = (lo_mask & val) << amt
                raw = raw_hi | raw_lo
        else:
            # SRL
            if typ == 0:
                raw = self.read_reg(opa) >> amt
            # SRA
            else:
                val = self.read_reg(opa)
                sign_bit = sign(val)
                u_shift = self.read_reg(opa) >> amt
                if sign_bit:
                    sign_mask = ((1 << amt) - 1) << (15 - amt)
                    raw = sign_mask | u_shift
                else:
                    raw = u_shift

        self._write_reg(dst, raw & 0x0FFFF)
        self.flags["Z"] = (raw == 0)
        self.flags["S"] = sign(raw)

    def do_i_class(self, opcode):
        def to_signed8b(val):
            if val > 127:
                return val - 256
            else:
                return val

        opc = (0x3800 & opcode) >> 11
        srcdst = (0x0700 & opcode) >> 8
        imm = (0x00FF & opcode)

        pc_incr = 1
        # MOVL
        if opc == 0x00:
            val = imm
        # MOVH
        elif opc == 0x01:
            val = (imm << 8)
        # MOVA
        elif opc == 0x02:
            val = to_unsigned16b(self.pc + 1 + to_signed8b(imm))
        # ADDI/SUBI
        elif opc == 0x03:
            val = to_unsigned16b(self.read_reg(srcdst) + to_signed8b(imm))
        # LDI
        elif opc == 0x04:
            val = self.mem[to_unsigned16b(self.pc + to_signed8b(imm))]
        # STI
        elif opc == 0x05:
            self.mem[to_unsigned16b(self.pc + to_signed8b(imm))] = self.read_reg(srcdst)
        # JAL
        elif opc == 0x06:
            val = to_unsigned16b(self.pc + 1)
            pc_incr = 1 + to_signed8b(imm)
        # JR
        elif opc == 0x07:
            raw_pc = self.read_reg(srcdst) + to_signed8b(imm)
            pc_incr = to_unsigned16b(raw_pc - self.pc)
        else:
            raise NotImplementedError("Do I Class")

        if opc not in [0x05, 0x07]:
            self._write_reg(srcdst, val)
        return pc_incr
