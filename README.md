# :anatomical_heart: Cardiotron

Embedded heart sensor with supporting cloud infrastructure. Now with support for multiple hearts!

## What makes it cool?

- Not a single `sleep_ms` in the entire codebase. Interrupts all the way down.

## Setup 

### Running the Pico

1. Follow the library setup instructions at [Metropolia's Pico Setup Guide](https://gitlab.metropolia.fi/lansk/pico-test).
2. Close all the apps that might use the COM port (VSCode, Thonny).
3. Open Thonny, navigate to "View" > "Files" and check that the "lib" folder is non-empty.
4. Clone the project `git clone https://github.com/ktnlvr/cardiotron.git`
5. Open the entire project in VSCode.
6. Install the [MicroPico extension](https://marketplace.visualstudio.com/items?itemName=paulober.pico-w-go)
7. Navigate to the command palette (Ctrl + Shift + P) and find "Initialize Project"
8. Delete the `.micropico` file in the project's root, **NOT IN THE `src/`**.
9. Reload VSCode
11. Connect the Pico
12. In the command palette and run "MicroPico: Upload project to Pico"
13. Open the [`src/main.py`](src/main.py).
14. Again in the comand palette run "MicroPico: Run this file"
15. Repeat steps 10 and 14 for development.

Sometimes the pico gets stuck, you need to stop the Python program to reupload the files again. If it gets stuck and non-responsive, disconnect the pico, reload VSCode and connect the Pico back again.

### Running the Server

Unai San, pls :з
