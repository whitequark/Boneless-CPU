#!/usr/bin/python
# Simon Kirkby
# obeygiantrobot@gmail.com
# 20190321

# a boneless simulator attached to a pty
# preperations for having a gateway boneless

import os, pty,sys
from serial import Serial
import threading


from boneless.simulator import *
from boneless.assembler.asm import Assembler

def listener(port):
    while 1:
        v = os.read(port, 1)
        print(v)

if __name__=='__main__':
    master,slave = pty.openpty() #open the pseudoterminal
    s_name = os.ttyname(slave) #translate the slave fd to a filename
    print(s_name)
    #create a separate thread that listens on the master device for commands
    cpu = BonelessSimulator(mem_size=1024)
    asmblr = Assembler(file_name="mon.asm")
    asmblr.assemble()
    asmblr.display()
    cpu.load_program(asmblr.code)
    thread = threading.Thread(target=listener, args=[master])
    thread.start()
