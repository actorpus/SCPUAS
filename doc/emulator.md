# Emulator I003

## Installation
Pygame is required to run the emulator. You can install it using pip

Putty is required to connect to the emulator, [here](https://putty.org/).

## Usage
The emulator is run as a standard python file.

### Putty
- Open putty
  - Host Name: localhost
  - Port: 4003
  - Connection Type: Raw
- Swap tab to `Terminal`
  - Local echo: Force off
  - Local line editing: Force off
- Swap back to `Session`
  - Save the session as `rawtoscpu`

## Controls
- exit - Exit the emulator
- ss {X} {Y} - Set the screen size to X by Y
- watch {X} - Watch memory at address X
- unwatch {X} - Stop watching memory at address X
- start - Start the CPU
- stop - Stop the CPU
- getmem {X} - Get the value at memory address X
- setmem {X} {Y} - Set the value at memory address X to Y
- loadscp {X} - Load the SCP file at X
- loadimg {X} {Y} - Load the image at X into memory at Y
- watchimg {X} {Y} {Z} - Watch the image at X of size YxZ
- unwatchimg {X} - Stop watching the image at X 
- clearmem - Clear the memory
- setreg {X} {Y} - Set register X to Y
- getreg {X} - Get the value of register X
- setpc {X} - Set the PC to X
- getpc - Get the value of the P