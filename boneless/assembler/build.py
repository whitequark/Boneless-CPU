from boneless.arch.instr import *
from boneless.gateware.core_fsm import BonelessCoreFSM, _ExternalPort
from asm import Assembler
from nmigen import *
from nmigen.back import pysim
from nmigen.cli import main


class Boneless:
    def __init__(self, has_pins=False, asmfile="base.asm"):
        self.memory = Memory(width=16, depth=4096)
        self.ext_port = _ExternalPort()
        self.pins = Signal(16, name="pins") if has_pins else None

        code = Assembler(file_name=asmfile)
        code.assemble()
        self.memory.init = code.code

    def elaborate(self, platform):
        m = Module()

        if self.pins is not None:
            with m.If(self.ext_port.addr == 0):
                with m.If(self.ext_port.r_en):
                    m.d.sync += self.ext_port.r_data.eq(self.pins)
                with m.If(self.ext_port.w_en):
                    m.d.sync += self.pins.eq(self.ext_port.w_data)

        m.submodules.mem_rdport = mem_rdport = self.memory.read_port(transparent=False)
        m.submodules.mem_wdport = mem_wrport = self.memory.write_port()
        m.submodules.core = BonelessCoreFSM(
            reset_addr=8,
            mem_rdport=mem_rdport,
            mem_wrport=mem_wrport,
            ext_port=self.ext_port,
        )
        return m.lower(platform)


def simulate(cpu):
    ecpu = cpu.elaborate(None)

    print(dir(cpu.pins))

    def testbench(sim):
        def read():
            return (yield cpu.pins)

        sim._traces.decoder = lambda n: "{}".format(n)
        for i in range(5):
            d = ecpu.ports.items()
            print(i, d)
            yield

    print(dir(ecpu))
    with pysim.Simulator(ecpu, vcd_file=None, traces=ecpu.pins) as sim:
        sim.add_clock(1, domain="sync")
        sim.add_sync_process(testbench(sim), domain="sync")
        sim.run()


if __name__ == "__main__":
    tm = Boneless(has_pins=True)
    # for i in dir(tm.ext_port): print(i)
    print(dir(tm.pins))
    simulate(tm)
    # main(tm)
