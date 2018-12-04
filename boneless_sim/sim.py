import array

class BonelessSimulator:
    def __init__(self, start_pc=0x10, memsize=1024, io_callback=None):
        def memset():
            for i in range(memsize):
                yield 0

        self.sim_active = False
        self.window = 0
        self.pc = start_pc
        self.mem = array.array("H", memset())
        self.io_callback = io_callback

    def __enter__(self):
        self.sim_active = True
        return self

    def __exit__(self, type, value, traceback):
        self.sim_active = False

    def regs(self):
        return self.mem[self.window:self.window+16]

    def set_pc(self, new_pc):
        if not self.sim_active:
            self.pc = new_pc

    # Use regs() in place of read_reg
    def write_reg(self, reg, val):
        if not self.sim_active:
            self.mem[self.window + reg] = val

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
        # Utility Functions
        def write_reg(offs, val):
            self.mem[reg_loc(offs)] = val

        def read_reg(offs):
            return self.mem[reg_loc(offs)]

        def reg_loc(offs):
            return self.window + offs

        # Handle Opcode Clases
        def do_a_class():
            dst = (0x0700 & opcode) >> 8
            opa = (0x00E0 & opcode) >> 5
            opb = (0x001C & opcode) >> 2
            typ = (0x0003 & opcode)

            # print(self.pc, opcode, dst, opa, opb, typ)
            if typ == 0x00:
                val = read_reg(opa) + read_reg(opb)
            elif typ == 0x01:
                val = read_reg(opa) - read_reg(opb)
            else:
                raise NotImplementedError("Do A Class")

            write_reg(dst, val)

        def do_i_class():
            opc = (0x3800 & opcode) >> 11
            srcdst = (0x0700 & opcode) >> 8
            imm = (0x00FF & opcode)

            if opc == 0x00:
                val = (read_reg(srcdst) & 0xFF00) | imm
            elif opc == 0x01:
                val = (read_reg(srcdst) & 0x00FF) | imm
            else:
                raise NotImplementedError("Do I Class")

            write_reg(srcdst, val)

        opcode = self.mem[self.pc]
        op_class = (0xF800 & opcode) >> 11

        if op_class in [0x00, 0x01]:
            do_a_class()
            self.pc = self.pc + 1
        elif op_class in [0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F]:
            do_i_class()
            self.pc = self.pc + 1
        else:
            raise NotImplementedError("Step Instruction")
