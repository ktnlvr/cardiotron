# :anatomical_heart: Cardiotron

Embedded heart sensor with supporting cloud infrastructure. Now with support for multiple hearts!

## What makes it cool?

- Not a single `sleep_ms` in the entire codebase. Interrupts all the way down.

## Abbreviations/Notation

- Some stuff is prefixed with `_`, that largely means "internal" and you shouldn't be touching those for writing "business logic."
- Some stuff ends in a `_b`, `_ns` or `_ms`. That specifies that units, for instance `_ns` is nanoseconds and `_b` is byte. That is useful for conversions and understanding what range a variable can be in (i.e. bytes are `0..255`).

## Setup 

### Running the Pico

0. Before proceeding, save all the sensitive data on another drive and wipe the pico clean.
1. Follow the library setup instructions at [Metropolia's Pico Setup Guide](https://gitlab.metropolia.fi/lansk/pico-test).
2. Close all the apps that might use the COM port (VSCode, Thonny).
3. Open Thonny, navigate to "View" > "Files" and check that the "lib" folder is non-empty.
4. Clone the project `git clone https://github.com/ktnlvr/cardiotron.git`.
5. Install `mpremote` with `pip install mpremote`.
6. Input your network credentials in the `src/secrets.py` file filling the SSID and password fields.
7. Run the build command for your system: `.\build.cmd` for Windows or `./build.sh` for linux.
8. Done! The Pico should be in order.

### Running the Server

In a linux environment you can run the following one liner to setup the server:
```
curl -fsSL https://raw.githubusercontent.com/ktnlvr/cardiotron/refs/heads/main/server/server-setup.sh | sudo bash
```

In any other OS:

0. First, make sure you have [Docker](https://www.docker.com) installed.
1. Clone the project if you haven't already `git clone https://github.com/ktnlvr/cardiotron.git`.
2. Enter the `server` folder inside the new clonned cardiotron folder
3. In your terminal of preference run `docker compose -f compose.yaml up -d`

To manage the server simply run the same command again in the server folder to start the containers or run
`docker compose -f compose.yaml down`
to stop them.

## Usage

## File Formats

To see how the Pico stores its data investigate the files in [`examples/`](examples/). On the pico itself, the information is stored in the `data/` folder.
