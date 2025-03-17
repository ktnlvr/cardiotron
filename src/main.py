from asm import Machine

if __name__ == '__main__':
    import micropython
    micropython.alloc_emergency_exception_buf(100)

    machine = Machine()
    while True:
        machine.execute()
