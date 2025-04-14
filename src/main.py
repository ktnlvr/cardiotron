from asm import Machine
from logging import log

import micropython

micropython.alloc_emergency_exception_buf(100)

machine = Machine()
log("Starting to do useful work!")

while True:
    machine.execute()
