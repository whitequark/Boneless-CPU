import array

__all__ = ["BonelessSimulator", "BonelessError"]


# Flag functions
# Used to calculate sign bit and also
# overflow.
def sign(val):
    return int((val & 0x08000) != 0)

def zero(val):
    return int(to_unsigned16b(val) == 0)

# Carry and V use 65xx semantics:
# http://www.righto.com/2012/12/the-6502-overflow-flag-explained.html
# http://teaching.idallen.com/dat2343/10f/notes/040_overflow.txt
def carry(val):
    return int(val > 65535)

def overflow(a, b, out):
    s_a = sign(a)
    s_b = sign(b)
    s_o = sign(out)

    return int((s_a and s_b and not s_o) or (s_a and s_b and s_o))

def overflow_sub(a, b, out):
    s_a = sign(a)
    s_b = sign(b)
    s_o = sign(out)

    return int((s_a and not s_b and not s_o) or (not s_a and s_b and s_o))

# Works with signed _or_ unsigned math.
def to_unsigned16b(val):
    if val < 0:
        return val + 65536
    elif val >= 65536:
        return val - 65536
    else:
        return val


class BonelessSimulator:
    """The Boneless CPU instruction-level simulator object.

    Instantiating this object will create a simulator context in
    which Boneless CPU code runs, one instruction at a time. A
    sample simulation session looks similar to the following:
    ::
        from boneless.simulator import *
        from boneless.instr import *

        cpu = BonelessSimulator(start_pc=0x10, memsize=65536)
        program = assemble([MOVL(R0, 0xFF)])
        cpu.load_program(program)

        with cpu:
            cpu.stepi()

        print(cpu.regs())

    Parameters
    ----------
    start_pc: int, optional
        The Program Counter register is set to this value when instantiating
        an object of this class.
    mem_size: int, optional
        Number of 16-bit words that the simulated CPU can access, starting
        from address zero. Accessing out-of-bounds memory will cause an
        exception.
    io_callback: function
        Initial I/O callback to use. See
        :func:`~boneless_sim.BonelessSimulator.register_io` for usage.

    Attributes
    ----------
    sim_active: bool
        ``True`` if a simulation is in progress, ``False`` otherwise.
    window: int
        Offset of the register window into memory (Boneless CPU registers
        are just memory locations.)
    pc: int
        Current program counter pointer.
    z: int
        Current value of the Zero flag, ``1`` for ``True``, or ``0`` for
        ``False``.
    s: int
        Current value of the Sign flag, ``1`` for ``True``, or ``0`` for
        ``False``.
    c: int
        Current value of the Carry flag, ``1`` for ``True``, or ``0`` for
        ``False``.
    v: int
        Current value of the OVerflow flag, ``1`` for ``True``, or ``0`` for
        ``False``.
    mem: array
        Contents of the primary address space seen by the simulated CPU. On
        object construction this is initialized to all zeroes.
    io_callback: function
        Reference to the current I/O callback function.
    """
    def __init__(self, start_pc=0x10, mem_size=1024, io_callback=None):
        def memset():
            for i in range(mem_size):
                yield 0

        self.sim_active = False
        self.window = 0
        self.pc = start_pc
        self.z = 0
        self.s = 0
        self.c = 0
        self.v = 0
        self.mem = array.array("H", memset())
        self.io_callback = io_callback

    def __enter__(self):
        self.sim_active = True
        return self

    def __exit__(self, type, value, traceback):
        self.sim_active = False

    def regs(self):
        """Return the 8 registers within the current register window.

        Returns
        -------
        array
            Array of 16-bit ints representing registers.
        """
        return self.mem[self.window:self.window+8]

    def read_reg(self, reg):
        """Read the value of a single 16-bit register.

        Parameters
        ----------
        reg: int
            Register number to read. ``R[0-8]`` from :mod:`boneless.instr`
            is also acceptable.

        Returns
        -------
        int
            Current value of the queried register.
        """
        return self.mem[self.reg_loc(reg)]

    def reg_loc(self, offs):
        """Convenience function to return the address of a register in memory.

        A register's location changes when the CPU's :attr:`window` is updated.

        Parameters
        ----------
        offs: int
            Register number to read. ``R[0-8]`` from :mod:`boneless.instr`
            is also acceptable.

        Returns
        -------
        int
            16-bit memory address of the queried register.
        """
        return self.window + offs

    def set_pc(self, new_pc):
        """Set the program counter to a new value.

        The program counter can only be updated using this function when
        a simulation is inactive.

        Parameters
        ----------
        new_pc: int
            16-bit (`treated as unsigned`) to write to the PC register. If the
            value is out of range, a read to :attr:`mem` will throw an
            exception.
        """
        if not self.sim_active:
            self.pc = new_pc

    def write_reg(self, reg, val):
        """Write the value of a single 16-bit register.

        Registers can only be updated using this function when a simulation
        is inactive.

        Parameters
        ----------
        reg: int
            Register number to write. ``R[0-8]`` from :mod:`boneless.instr`
            is also acceptable.
        val: int
            16-bit (`treated as unsigned`) to write to a register. If the
            value is out of range, the write to :attr:`mem` will throw an
            exception.
        """
        if not self.sim_active:
            self.mem[self.reg_loc(reg)] = val

    def load_program(self, contents, start=0x10):
        """Inject program code into the memory space of the simulated CPU.

        This function does not distinguish between loading program code and
        raw data. Program code can only be loaded using this function when a
        simulation is inactive.

        Parameters
        ----------
        contents: list of ints
            Integer representation of opcodes to load into the memory space of
            the simulated CPU. The function :func:`boneless.instr.assemble`
            produces a list compatible with this input parameter.
        start: int
            16-bit int offset representing the starting location in memory
            in which to load ``contents``.
        """
        if not self.sim_active:
            for i, c in enumerate(contents):
                self.mem[i + start] = c

    def register_io(self, callback):
        """Replace the currently-defined I/O callback with a new one.

        The Simulated Boneless CPU needs a way to contact the outside world.
        The architecture itself defines a secondary address space for I/O,
        similar in idea to x86 port-mapped I/O. When the ``STX`` and ``LDX``
        instructions are encountered, the provided callback will execute to
        simulate I/O. It is up to the user to decode the I/O address passed
        into the callback accordingly.

        The I/O callback can only be replaced when a simulation is inactive.

        Parameters
        ----------
        callback: function
            The callback function, using the following signature:
            ``fn(addr, data=None)``

            * ``addr``: 16-bit int
                Virtual I/O address to read/write
            * ``data``: 16-bit int` or ``None``
                If this I/O access is a read, ``data`` is ``None``. Otherwise,
                ``data`` contains a value to write to a virtual I/O device.

            The callback should return a 16-bit int if the I/O access was a
            read and ``None`` if the I/O access was a write (ignored by the
            simulator).
        """
        if not self.sim_active:
            self.io_callback = callback

    def stepi(self):
        """Run a single instruction of the simulated CPU.

        The state of the CPU will be available through the attributes of
        :obj:`~boneless_sim.BonelessSimulator`.
        """
        opcode = self.mem[self.pc]
        op_class = (0xF800 & opcode) >> 11

        if op_class in [0x00, 0x01]:
            self._do_a_class(opcode)
            self.pc = to_unsigned16b(self.pc + 1)
        elif op_class in [0x02, 0x03]:
            self._do_s_class(opcode)
            self.pc = to_unsigned16b(self.pc + 1)
        elif op_class in [0x04, 0x05, 0x06, 0x07]:
            self._do_m_class(opcode)
            self.pc = to_unsigned16b(self.pc + 1)
        elif op_class in [0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F]:
            pc_incr = self._do_i_class(opcode)
            self.pc = to_unsigned16b(self.pc + pc_incr)
        else:
            pc_incr = self._do_c_class(opcode)
            self.pc = to_unsigned16b(self.pc + pc_incr)

    # Utility Functions- Do not call directly
    def _write_reg(self, reg, val):
        self.mem[self.reg_loc(reg)] = val

    # Handle Opcode Clases- Do not call directly
    def _do_a_class(self, opcode):
        dst = (0x0700 & opcode) >> 8
        opa = (0x00E0 & opcode) >> 5
        opb = (0x001C & opcode) >> 2
        typ = (0x0003 & opcode)
        code = (0x0800 & opcode) >> 11

        val_a = self.read_reg(opa)
        val_b = self.read_reg(opb)

        if code and (typ in range(3)):
            # ADD
            if typ == 0x00:
                raw = val_a + val_b
                self.v = overflow(val_a, val_b, raw)
                self._write_reg(dst, to_unsigned16b(raw))
            # SUB
            elif typ == 0x01:
                raw = val_a + to_unsigned16b(~val_b) + 1
                self.v = overflow_sub(val_a, val_b, raw)
                self._write_reg(dst, to_unsigned16b(raw))
            # CMP
            else:
                raw = val_a + to_unsigned16b(~val_b) + 1
                self.v = overflow_sub(val_a, val_b, raw)

            self.c = carry(raw)
        elif not code and typ in range(3):
            # AND
            if typ == 0x00:
                raw = val_a & val_b
            # OR
            elif typ == 0x01:
                raw = val_a | val_b
            # XOR
            else:
                raw = val_a ^ val_b
            self._write_reg(dst, raw)
        else:
            raise BonelessError("A-class opcode with typ == 0x03 is a reserved instruction.")

        self.z = zero(raw)
        self.s = sign(raw)

    def _do_s_class(self, opcode):
        dst = (0x0700 & opcode) >> 8
        opa = (0x00E0 & opcode) >> 5
        amt = (0x001E & opcode) >> 1
        typ = (0x0001 & opcode)
        code = (0x0800 & opcode) >> 11

        if not code:
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
                raw_hi = (hi_mask & val) >> (15 - amt + 1)
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
                    sign_mask = ((1 << amt) - 1) << (15 - amt + 1)
                    raw = sign_mask | u_shift
                else:
                    raw = u_shift

        self._write_reg(dst, raw & 0x0FFFF)
        self.z = zero(raw)
        self.s = sign(raw)

    def _do_m_class(self, opcode):
        def to_signed5b(val):
            if val > 16:
                return val - 32
            else:
                return val

        code = (0x1800 & opcode) >> 11
        srcdst = (0x0700 & opcode) >> 8
        adr = (0x00E0 & opcode) >> 5
        imm = (0x001F & opcode)

        # LD
        if code == 0x00:
            self._write_reg(srcdst, self.mem[self.read_reg(adr) + to_signed5b(imm)])
        # ST
        elif code == 0x01:
            self.mem[self.read_reg(adr) + to_signed5b(imm)] = self.read_reg(srcdst)
        # LDX
        elif code == 0x02:
            if self.io_callback:
                val = self.io_callback(self.read_reg(adr) + to_signed5b(imm), None)
                self._write_reg(srcdst, val)
            else:
                raise BonelessError("LDX instruction encountered but io_callback not set.")
        # STX
        else:
            if self.io_callback:
                val = self.read_reg(srcdst)
                self.io_callback(self.read_reg(adr) + to_signed5b(imm), val)
            else:
                raise BonelessError("STX instruction encountered but io_callback not set.")

    def _do_i_class(self, opcode):
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
            op_a = self.read_reg(srcdst)
            op_b = to_signed8b(imm)
            # Flags will not be set correctly unless we convert
            # op_b to unsigned to force a carry when op_a > op_b.
            raw = op_a + to_unsigned16b(op_b)

            val = to_unsigned16b(raw)

            self.z = zero(raw)
            self.s = sign(raw)
            self.c = carry(raw)
            self.v = overflow(op_a, op_b, raw)
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
        else:
            raw_pc = self.read_reg(srcdst) + to_signed8b(imm)
            pc_incr = to_unsigned16b(raw_pc - self.pc)

        if opc not in [0x05, 0x07]:
            self._write_reg(srcdst, val)
        return pc_incr

    def _do_c_class(self, opcode):
        def to_signed11b(val):
            if val > 1023:
                return val - 2048
            else:
                return val

        cond = (0x7000 & opcode) >> 12
        flag = (0x0800 & opcode) >> 11
        offs = (0x7FF & opcode)

        # J
        if cond == 0x00:
            if flag:
                raise BonelessError("Unconditional J with flag==1 is a reserved instruction.")
            else:
                cond_met = True

        # JNZ/JNE, JZ/JE
        elif cond == 0x01:
            cond_met = (self.z  == flag)
        # JNS, JS
        elif cond == 0x02:
            cond_met = (self.s  == flag)
        # JNC/JULT, JC/JUGE
        elif cond == 0x03:
            cond_met = (self.c  == flag)
        # JNO, JO
        elif cond == 0x04:
            cond_met = (self.v  == flag)
        # JULE, JUGT
        elif cond == 0x05:
            cond_met = ((not self.c or self.z)  == flag)
        # JSGE, JSLT
        elif cond == 0x06:
            cond_met = ((self.s ^ self.v)  == flag)
        # JSGT, JSLE
        elif cond == 0x07:
            cond_met = (((self.s ^ self.v) or self.z)  == flag)

        if cond_met:
            pc_incr = to_signed11b(offs) + 1
        else:
            pc_incr = 1

        return pc_incr


class BonelessError(Exception):
    """Exception raised when the CPU simulator doesn't know what to do."""
    pass
