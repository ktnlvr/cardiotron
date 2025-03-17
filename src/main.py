from asm import Machine

import micropython
micropython.alloc_emergency_exception_buf(100)

machine = Machine()
while True:
    machine.execute()
