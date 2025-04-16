from sys import implementation, exit

major, minor, *_ = implementation.version

if major < 1 or major == 1 and minor < 25:
    print(
        f"Hey! You are running MicroPython {major}.{minor} "
        "but the minimum supported version is 1.25, "
        "upgrade your MicroPython and come back!"
    )
    exit()


from asm import Machine
from logging import log
from wifi import connect_ap

import micropython

micropython.alloc_emergency_exception_buf(100)

connect_ap()

machine = Machine()
log("Starting to do useful work!")

while True:
    machine.execute()
