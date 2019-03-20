import os, pty,sys
from serial import Serial
import threading

# lifted from
# http://allican.be/blog/2017/01/15/python-dummy-serial-port.html
b0 = "╔═╦═╗╓─╥─╖╒═╤═╕┌─┬─┐" .encode(sys.stdout.encoding)
b1 = "║ ║ ║║ ║ ║│ │ ││ │ │" .encode(sys.stdout.encoding)
b2 = "╠═╬═╣╟─╫─╢╞═╪═╡├─┼─┤" .encode(sys.stdout.encoding)
b3 = "║ ║ ║║ ║ ║│ │ ││ │ │" .encode(sys.stdout.encoding)
b4 = "╚═╩═╝╙─╨─╜╘═╧═╛└─┴─┘" .encode(sys.stdout.encoding)
print(b0)
def listener(port):
    #continuously listen to commands on the master device
    #os.write(port,b"\x1b[500;500f")
    #os.write(port,b"\x1b[6n")
    #os.write(port,b"\x1b[41m")
    #os.write(port,b"\x1b[39m")

    #os.write(port,b"\x1b[2j")
    ##os.write(port,b"\x1b[0;0")
    while 1:
        res = b""
        while not res.endswith(b"\r"):
            #keep reading one byte at a time until we have a full line
            v = os.read(port, 1)
            print(v)
            res += v
            os.write(port,v)
        print("command: %s" % res)

        #os.write(port,b"\x1b[500;500f")
        #os.write(port,b"\x1b[6n")
        #write back the response
        if res == b'QPGS\r\n':
            os.write(port, b"correct result\r\n")
        else:
            os.write(port,b"\x1b[48;5;171m")
            #os.write(port,b"\x1b[39m")
            os.write(port,b0)
            os.write(port,b'\r\n')
            os.write(port,b1)
            os.write(port,b'\r\n')
            os.write(port,b2)
            os.write(port,b'\r\n')
            os.write(port,b3)
            os.write(port,b'\r\n')
            os.write(port,b4)
            os.write(port,b'\r\n')

def test_serial():
    """Start the testing"""
    master,slave = pty.openpty() #open the pseudoterminal
    s_name = os.ttyname(slave) #translate the slave fd to a filename

    print(s_name)
    #create a separate thread that listens on the master device for commands
    thread = threading.Thread(target=listener, args=[master])
    thread.start()

    #open a pySerial connection to the slave
    ser = Serial(s_name, 2400, timeout=1)
    ser.write(b'test2\r\n') #write the first command
    res = b""
    while not res.endswith(b'\r\n'):
        #read the response
        res +=ser.read()
    print("result: %s" % res)
    ser.write(b'QPGS\r\n') #write a second command
    res = b""
    while not res.endswith(b'\r\n'):
        #read the response
        res +=ser.read()
    print("result: %s" % res)

if __name__=='__main__':
    master,slave = pty.openpty() #open the pseudoterminal
    s_name = os.ttyname(slave) #translate the slave fd to a filename
    print(s_name)
    #create a separate thread that listens on the master device for commands
    thread = threading.Thread(target=listener, args=[master])
    thread.start()
