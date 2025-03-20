# :anatomical_heart: Cardiotron

Embedded heart sensor with supporting cloud infrastructure. Now with support for multiple hearts!

## What makes it cool?

- Not a single `sleep_ms` in the entire codebase. Interrupts all the way down.

## Setup 

### Running the Pico

0. Before proceeding, save all the sensetive data on another drive and wipe the pico clean.
1. Follow the library setup instructions at [Metropolia's Pico Setup Guide](https://gitlab.metropolia.fi/lansk/pico-test).
2. Close all the apps that might use the COM port (VSCode, Thonny).
3. Open Thonny, navigate to "View" > "Files" and check that the "lib" folder is non-empty.
4. Clone the project `git clone https://github.com/ktnlvr/cardiotron.git`.
5. Install `mpremote` with `pip install mpremote`.
6. Run the build command for your system: `.\build.cmd` for Windows or `./build.sh` for linux.
7. Done! The Pico should be in order.

### Running the Server

Unai San, pls :з

## Usage

## File Formats

To see how the Pico stores its data investigate the files in [`examples/`](examples/). On the pico itself, the information is stored in the `data/` folder.
