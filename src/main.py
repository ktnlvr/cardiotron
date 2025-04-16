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
