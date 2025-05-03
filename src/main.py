from sys import implementation, exit

major, minor, *_ = implementation.version

if major < 1 or major == 1 and minor < 25:
    print(
        f"Hey! You are running MicroPython {major}.{minor} "
        "but the minimum supported version is 1.25, "
        "upgrade your MicroPython and come back!"
    )
    exit()


from sys import print_exception
from asm import Machine
from logging import log, active_log
import time
import micropython
import machine as mpy_machine

micropython.alloc_emergency_exception_buf(100)

machine = Machine()

log("Starting to do useful work!")

while True:
    try:
        machine.execute()
    except Exception as e:
        machine.display.fill(0)
        machine.display.text("Error occurred:", 0, 0)
        machine.display.text(str(e)[:16], 0, 10)
        machine.display.show()
        time.sleep(2)
        log("Critical Failure!", e)
        raise
