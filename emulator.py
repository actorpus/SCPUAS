# An emulator for the simplecpu project.
# This emulator is part of the SCPUAS project.
# SCPUAS © 2024 by actorpus is licensed under CC BY-NC-SA 4.0


"""
# Putty config

Connection type: Raw
Host Name: localhost
Port: 4003

Under terminal
Local echo: Force off
Local line editing: Force off

(save config)
"""

import json
import os
import pathlib
import socket
import sys
import threading
import time
import traceback

try:
    import numpy as np
except ImportError:
    print("Numpy is not installed, please install it to use the emulator")
    sys.exit(1)

try:
    import pygame
except ImportError:
    print("Pygame is not installed, please install it to use the screen")
    sys.exit(1)

class CPU(threading.Thread):
    class memwrap:
        def __init__(self, root):
            self._memory = np.zeros(4096, dtype=np.uint16)
            self.mem_change_hook = None
            self.__root = root

        def __getitem__(self, key):
            if key == self.__root.debug_port:
                print(
                    f"Attempted to read from {self.__root.debug_port:x}, enabling debug mode"
                )
                self.__root.debug = True

            return self._memory[key]

        def __setitem__(self, key, value):
            if key == self.__root.debug_port:
                print(
                    f"Attempted to write to {self.__root.debug_port:x}, enabling debug mode"
                )
                self.__root.debug = True

            if self.mem_change_hook:
                self.mem_change_hook(key, value)

            self._memory[key] = value

        def clear(self):
            self._memory = np.zeros(4096, dtype=np.uint16)

    def __init__(self):
        super().__init__()

        self._memory = self.memwrap(self)
        self._registers = np.zeros(4, dtype=np.uint16)
        self.__stack = np.zeros(4, dtype=np.uint16)
        self.__stack_pointer = 0
        self._pc = 0
        self.__ir = 0

        self.__flags_zero = False
        self.__flags_carry = False
        self.__flags_overflow = False
        self.__flags_positive = False
        self.__flags_negative = False

        self._current_instruction_rel_func = None
        self._running_at = "~ KHz"

        self._total_instructions = 0

        self.enabled = False
        self.running = True
        self.debug = False
        self.debug_port = -1

        self.__rc = None

    def bind(self, remote_control):
        self.__rc = remote_control

    def self_loop(self):
        self.enabled = False

        self.__rc._lines.append(f"\033[31mWarn\033[0m Processor entered self loop, disabling.")
        self.__rc._lines.append(f"     Total instructions executed: {self._total_instructions}")

    def load_memory(self, at, memory):
        for i, c in enumerate(memory):
            self._memory[i + at] = int(c, 16)

    def _get_mem(self, at):
        return self._memory[at]

    def _set_mem(self, at, value):
        self._memory[at] = value

    def _MOVE(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        value = ir07ir04 << 4 | ir03ir00

        self._registers[dest] = value

    def _ADD(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        value = ir07ir04 << 4 | ir03ir00

        self.__flags_carry = self._registers[dest] + value > 0xFFFF

        v = self._registers[dest] + value

        self.__flags_zero = v == 0
        self.__flags_overflow = v > 0xFFFF
        self.__flags_negative = v & 0x8000
        self.__flags_positive = not self.__flags_negative

        self._registers[dest] = v

    def _SUB(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        value = ir07ir04 << 4 | ir03ir00

        self.__flags_carry = self._registers[dest] < value

        v = self._registers[dest] - value

        self.__flags_zero = v == 0
        self.__flags_overflow = v > 0xFFFF
        self.__flags_negative = v & 0x8000
        self.__flags_positive = not self.__flags_negative

        self._registers[dest] = v

    def _AND(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        value = ir07ir04 << 4 | ir03ir00

        self.__flags_carry = False

        v = self._registers[dest] & value

        self.__flags_zero = v == 0
        self.__flags_overflow = False
        self.__flags_negative = v & 0x8000
        self.__flags_positive = not self.__flags_negative

        self._registers[dest] = v

    def _LOAD(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )
        self._registers[0] = self._memory[value]

    def _STORE(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        self._memory[value] = self._registers[0]

    def _ADDM(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        value = self._memory[value]

        self.__flags_carry = self._registers[0] + value > 0xFFFF

        v = self._registers[0] + value

        self.__flags_zero = v == 0
        self.__flags_overflow = v > 0xFFFF
        self.__flags_negative = v & 0x8000
        self.__flags_positive = not self.__flags_negative

        self._registers[0] = v

    def _SUBM(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        value = self._memory[value]

        self.__flags_carry = self._registers[0] < value

        v = self._registers[0] - value

        self.__flags_zero = v == 0
        self.__flags_overflow = v > 0xFFFF
        self.__flags_negative = v & 0x8000
        self.__flags_positive = not self.__flags_negative

        self._registers[0] = v

    def _JUMPU(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        if self._pc - 1 == value:
            self.self_loop()

        self._pc = value

    def _JUMPZ(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        if self._pc - 1 == value:
            self.self_loop()

        if self.__flags_zero:
            self._pc = value

    def _JUMPNZ(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        if self._pc - 1 == value:
            self.self_loop()

        if not self.__flags_zero:
            self._pc = value

    def _JUMPC(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        if self._pc - 1 == value:
            self.self_loop()

        if self.__flags_carry:
            self._pc = value

    def _CALL(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        self.__stack[self.__stack_pointer] = self._pc
        self.__stack_pointer += 1

        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        self._pc = value

    def _OR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        raise NotImplementedError

    def _XOP1(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        raise NotImplementedError

    def _RET(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        self.__stack_pointer -= 1
        self._pc = self.__stack[self.__stack_pointer]

    def _MOVER(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        src = ir09 << 1 | ir08

        self._registers[dest] = self._registers[src]

    def _LOADR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        src = ir09 << 1 | ir08

        self._registers[dest] = self._memory[self._registers[src]]

    def _STORER(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        src = ir11 << 1 | ir10
        dest = ir09 << 1 | ir08

        self._memory[self._registers[dest]] = self._registers[src]

    def _ROL(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        src = ir09 << 1 | ir08

        self.__flags_overflow = self._registers[dest] & 0x8000

        self._registers[dest] = (self._registers[dest] << 1) | (
                self._registers[src] >> 15
        )

        self.__flags_zero = self._registers[dest] == 0
        self.__flags_carry = False
        self.__flags_negative = self._registers[dest] & 0x8000
        self.__flags_positive = not self.__flags_negative

    def _ROR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        raise NotImplementedError
        # dest = ir11 << 1 | ir10
        # src = ir09 << 1 | ir08
        #
        # self.__flags_overflow = self._registers[dest] & 0x0001
        #
        # self._registers[dest] = (self._registers[dest] >> 1) | (
        #         self._registers[src] << 15
        # )
        #
        # self.__flags_zero = self._registers[dest] == 0
        # self.__flags_carry = False
        # self.__flags_negative = self._registers[dest] & 0x8000
        # self.__flags_positive = not self.__flags_negative

    def _ADDR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        src = ir09 << 1 | ir08

        self.__flags_carry = self._registers[dest] + self._registers[src] > 0xFFFF

        v = int(self._registers[dest]) + int(self._registers[src])

        self.__flags_zero = v == 0
        self.__flags_overflow = v > 0xFFFF
        self.__flags_negative = v & 0x8000
        self.__flags_positive = not self.__flags_negative

        self._registers[dest] = v & 0xFFFF

    def _SUBR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        src = ir09 << 1 | ir08

        self.__flags_carry = self._registers[dest] < self._registers[src]

        v = int(self._registers[dest]) - int(self._registers[src])

        self.__flags_zero = v == 0
        self.__flags_overflow = v > 0xFFFF
        self.__flags_negative = v & 0x8000
        self.__flags_positive = not self.__flags_negative

        self._registers[dest] = v & 0xFFFF

    def _ANDR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        raise NotImplementedError

    def _ORR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        raise NotImplementedError

    def _XORR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        src = ir09 << 1 | ir08

        v = int(self._registers[dest]) ^ int(self._registers[src])

        self.__flags_carry = False
        self.__flags_zero = v == 0
        self.__flags_overflow = v > 0xFFFF
        self.__flags_negative = v & 0x8000
        self.__flags_positive = not self.__flags_negative

        self._registers[dest] = v & 0xFFFF

    def _ASLR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        raise NotImplementedError

    def _XOP2(self, ir11, ir10, ir09, ir08, ir08ir04, ir03ir00):
        raise NotImplementedError

    def _XOP3(self, ir11, ir10, ir09, ir08, ir08ir04, ir03ir00):
        raise NotImplementedError

    def _XOP4(self, ir11, ir10, ir09, ir08, ir08ir04, ir03ir00):
        raise NotImplementedError

    def _XOP5(self, ir11, ir10, ir09, ir08, ir08ir04, ir03ir00):
        raise NotImplementedError

    def _decode_instruction_rel_func(self, ir):
        ir15ir12 = ir >> 12
        ir04ir00 = ir & 0x0F

        if ir15ir12 == 0b1111:
            return {
                0b0000: self._RET,
                0b0001: self._MOVER,
                0b0010: self._LOADR,
                0b0011: self._STORER,
                0b0100: self._ROL,
                0b0101: self._ROR,
                0b0110: self._ADDR,
                0b0111: self._SUBR,
                0b1000: self._ANDR,
                0b1001: self._ORR,
                0b1010: self._XORR,
                0b1011: self._ASLR,
                0b1100: self._XOP2,
                0b1101: self._XOP3,
                0b1110: self._XOP4,
                0b1111: self._XOP5,
            }[ir04ir00]

        return {
            0b0000: self._MOVE,
            0b0001: self._ADD,
            0b0010: self._SUB,
            0b0011: self._AND,
            0b0100: self._LOAD,
            0b0101: self._STORE,
            0b0110: self._ADDM,
            0b0111: self._SUBM,
            0b1000: self._JUMPU,
            0b1001: self._JUMPZ,
            0b1010: self._JUMPNZ,
            0b1011: self._JUMPC,
            0b1100: self._CALL,
            0b1101: self._OR,
            0b1110: self._XOP1,
        }[ir15ir12]

    def _fetch(self):
        self.__ir = self._get_mem(self._pc)
        self._pc += 1

        if self.debug:
            print(f"Fetched: {self.__ir} at {self._pc - 1}")

    def _decode(self):
        self._current_instruction_rel_func = self._decode_instruction_rel_func(
            self.__ir
        )

        if self.debug:
            print(f"Decoded: {self._current_instruction_rel_func.__name__}")

    def _execute(self):
        ir11 = (self.__ir >> 11) & 1
        ir10 = (self.__ir >> 10) & 1
        ir09 = (self.__ir >> 9) & 1
        ir08 = (self.__ir >> 8) & 1
        ir07ir04 = (self.__ir >> 4) & 0xF
        ir03ir00 = self.__ir & 0xF

        self._current_instruction_rel_func(ir11, ir10, ir09, ir08, ir07ir04, ir03ir00)

        if self.debug:
            print(f"Executed: {self._current_instruction_rel_func.__name__}")

    def run(self):
        self._run()

    def _run(self):
        i, t = 0, time.time()

        while self.running:
            if not self.enabled:
                time.sleep(1)
                self.running_at = "~ KHz"
                continue

            self._fetch()
            self._decode()
            self._execute()

            self._total_instructions += 1

            if self.debug:
                print(f"Registers: {self._registers}")
                print(f"Stack: {self.__stack}")
                print(f"Stack Pointer: {self.__stack_pointer}")
                print(f"PC: {self._pc}")
                print(f"IR: {self.__ir}")
                print(f"Carry: {self.__flags_carry}")
                print(f"Zero: {self.__flags_zero}")
                print(f"Overflow: {self.__flags_overflow}")
                print(f"Negative: {self.__flags_negative}")
                print(f"Positive: {self.__flags_positive}")
                print()
                time.sleep(1)

            i += 1
            if i == 100000:
                c = time.time()
                r = c - t
                s = r / 100000
                self._running_at = f"{1 / s / 1000:.2f} kHz"
                i, t = 0, c

        print(f"[CPU] Stopped")


class PygameScreen:
    def __init__(self, cpu_ref: CPU):
        pygame.font.init()

        self._display = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
        self._clock = pygame.time.Clock()
        self._running = True

        self._font = pygame.font.Font(None, 24)

        self._cpu = cpu_ref
        self._watching = []

    def watch(self, address, size: tuple[int, int]):
        self._watching.append((address, size))
        print(f"[PS] Watching {size[0]}x{size[1]} image at {address}")

    def unwatch(self, address):
        self._watching = [w for w in self._watching if w[0] != address]
        print(f"[PS] Stopped watching image at {address}")

    def load_image(
            self, address, size: tuple[int, int], fsize: tuple[int, int]
    ) -> pygame.surface:
        surf = pygame.Surface(size)

        for y in range(size[1]):
            for x in range(size[0]):
                # horrible but avoids trigering the debug mode
                value = self._cpu._memory._memory[address + y * size[0] + x]
                r = (value >> 11) << 3
                g = ((value >> 5) & 0x3F) << 2
                b = (value & 0x1F) << 3

                surf.set_at((x, y), (r, g, b))

        surf = pygame.transform.scale(surf, fsize)

        return surf

    def run(self):
        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False

            self._display.fill((0, 0, 0))

            for i, (address, size) in enumerate(self._watching):
                # leave a 2x gap
                pygame.draw.rect(
                    self._display,
                    (255, 255, 255),
                    ((i * (128 + 8)) + 13, 13, 134, 134),
                    1,
                )
                self._display.blit(
                    self.load_image(address, size, (128, 128)), ((i * (128 + 8)) + 16, 16)
                )
                sur = self._font.render(f"0x{address:03x}", True, (255, 255, 255))
                self._display.blit(
                    sur,
                    ((i * (128 + 8)) + 16 + 64 - (sur.get_width() // 2), 128 + 20),
                )

            pygame.display.flip()
            self._clock.tick(30)

        print(f"[PS] Stopped")


class RemoteControl(threading.Thread):
    class _NonBlocked(threading.Thread):
        def __init__(self, client, rc):
            super().__init__()
            self._client = client
            self._rc = rc

            self._running = True

            self._old_data = {}
            self._rc._cpu._memory.mem_change_hook = (
                lambda key, value: self._check_changes(key, value)
            )

        def bind(self, client):
            self._client = client

        def _check_changes(self, key, value):
            if key in self._rc._watching:
                w = ""
                if value in range(32, 127):
                    w = f" '{chr(value)}'"

                self._rc._lines.append(
                    f"\033[31mMemory\033[0m {key:03x}: {self._old_data.get(key, 0):04x} -> {value:04x}{w}"
                )
                self._old_data[key] = value

        def run(self):
            print(f"[RC.NB] Started")

            while self._running:
                try:
                    self._client.send(self._rc.render())
                except ConnectionAbortedError:
                    print(f"[RC.NB] Connection closed")
                    self._rc._cpu.enabled = False
                    self._rc._cpu.running = False
                    self._rc._screen._running = False
                    self._running = False
                    self._rc._running = False
                    break
                except ConnectionResetError:
                    print(f"[RC.NB] Connection closed")
                    self._rc._cpu.enabled = False
                    self._rc._cpu.running = False
                    self._rc._screen._running = False
                    self._running = False
                    self._rc._running = False
                    break

                time.sleep(0.1)

            print(f"[RC.NB] Stopped")

    def __init__(self, cpu_ref: CPU, screen_ref: PygameScreen):
        super().__init__()

        self._screen_size = (80, 24)
        self._cpu: CPU = cpu_ref
        self._screen: PygameScreen = screen_ref
        self._stop_blocking = True

        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind(("localhost", 4003))
        self._server.listen(1)

        self._lines = []
        self._cur_command = ""
        self._watching = []
        self._last_command = ""

        self._running = True

        self.start()

        self._nonblocked = self._NonBlocked(self._server, self)

        print(f"[RC] Waiting for connection")
        while self._stop_blocking:
            time.sleep(0.1)

    def render(self):
        # Clear screen, reset cursor, reset colors, underline
        out = (
                "\033[2J\033[H\033[0m\033[4m Remote Control \033[0m"
                + " " * (self._screen_size[0] - 16 - 4)
                + "I003\r\n"
        )

        lines = self._lines[-(self._screen_size[1] - 3):]

        for line in lines:
            out += line + "\r\n"

        out += f"\033[{self._screen_size[1] - 1};0f"
        out += "-" * self._screen_size[0]
        out += "\r\n:"
        out += self._cur_command
        out += " " * (
                self._screen_size[0]
                - len(self._cur_command)
                - len(self._cpu._running_at)
                - 1
        )
        out += self._cpu._running_at
        # move cursor back to input
        out += f"\033[{self._screen_size[1]};{len(self._cur_command) + 2}f"

        return out.encode("utf-8")

    def run_command_ext(self, command):
        try:
            self._cur_command = command
            self._lines.append(f"\033[34mCommand\033[0m {self._cur_command}")
            print(f"[RC] Running external command: {self._cur_command}")
            self.handle_command()
        except Exception as e:
            print(f"[RC] Exception while executing command: {e}")
            traceback.print_exc()

            self._lines.append(f"\033[31mError\033[0m {e}")

    def handle_command(self):
        if self._cur_command == "!exit":
            raise SystemExit

        if self._cur_command.startswith("ss"):
            if not self._cur_command[2:].strip():
                self._lines.append("Reset screen size to 80x24")
                self._screen_size = (80, 24)
                self._last_command = self._cur_command
                self._cur_command = ""
                return

            x, y = self._cur_command[2:].strip().split(" ")
            self._lines.append(f"Screen size set to {x}x{y}")
            self._screen_size = (int(x), int(y))
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command == "gettotalinst":
            self._lines.append(f"Total instructions executed: {self._cpu._total_instructions}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command == "start":
            self._cpu.enabled = True
            self._lines.append("CPU started")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command == "stop":
            self._cpu.enabled = False
            self._lines.append("CPU stopped")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("loadimg"):
            img_path, address = self._cur_command[7:].strip().split(" ")
            address = eval(address)
            print(f"[RC] Loading image {img_path} at {address}")

            with open(img_path, "r") as f:
                code = f.read()

            type_id, size, max, *code = [
                *[
                    _.split(" ")
                    for _ in code.strip().split("\n")
                    if not _.startswith("#")
                ]
            ]
            # also not an error ignore ide
            type_id, max = type_id[0], max[0]
            size = size[:2]

            if type_id != "P3":
                self._lines.append(f"Invalid image type: {type_id}")
                return

            if max != "255":
                self._lines.append(f"Invalid max value: {max}")
                return

            og_size = size
            size = int(size[0]) * int(size[1])

            for _ in range(size):
                r = int(code.pop(0)[0])
                g = int(code.pop(0)[0])
                b = int(code.pop(0)[0])

                value = (r >> 3) << 11 | (g >> 2) << 5 | (b >> 3)

                self._cpu._set_mem(address + _, value)

            self._lines.append(
                f"Loaded image at {address}, ({og_size[0]}x{og_size[1]})"
            )
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("dumpimg"):
            address, width, height, path = self._cur_command[7:].strip().split(" ")
            path = pathlib.Path(path).resolve()
            address, width, height = eval(address), eval(width), eval(height)

            out = f"P3\n# CREATOR: SCPUAS image dump\n{width} {height}\n255\n"

            for y in range(height):
                for x in range(width):
                    value = self._cpu._memory._memory[address + (y * width) + x]
                    r = (value >> 11) << 3
                    g = ((value >> 5) & 0x3F) << 2
                    b = (value & 0x1F) << 3

                    out += f"{r}\n{g}\n{b}\n"

            with open(path, "w") as f:
                f.write(out)

            self._lines.append(f"Dumped image at {address} {width}x{height} to {path}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("watchimg"):
            address, x, y = self._cur_command[8:].strip().split(" ")

            self._screen.watch(eval(address), (eval(x), eval(y)))
            self._lines.append(f"Watching image at {address} {x}x{y}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("unwatchimg"):
            address, x, y = self._cur_command[8:].strip().split(" ")

            self._screen.unwatch(eval(address))
            self._lines.append(f"Watching image at {address} {x}x{y}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("loadasc"):
            asc_path = self._cur_command[7:].strip()
            asc_path = pathlib.Path(asc_path).resolve()

            if asc_path.exists() is False:
                self._lines.append(f"File at {asc_path} does not exist")
                return

            with open(asc_path, "r") as f:
                code = f.read().strip()

            code = code.split("\n")

            memory_start = int(code[0].split(" ")[0], 16)

            for i, line in enumerate(code):
                code[i] = line.strip().split(" ")[1:]

            code = [item for sublist in code for item in sublist]

            self._cpu.load_memory(memory_start, code)

            self._lines.append(f"Loaded ASC at {memory_start:03x}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("loadscp"):
            asm_path = self._cur_command[7:].strip()
            asm_path = pathlib.Path(asm_path).resolve()
            python_executable_path = pathlib.Path(sys.executable).resolve()
            output_path = pathlib.Path("tmp/output").resolve()

            if asm_path.exists() is False:
                self._lines.append(f"File at {asm_path} does not exist")
                return

            if not os.path.exists("tmp"):
                os.mkdir("tmp")

            if os.path.exists("tmp/output.asc"):
                os.remove("tmp/output.asc")

            os.system(
                rf"{python_executable_path} assembler.py -i {asm_path} -P debug -a {output_path} -V"
            )

            # load the assembled code
            self._cur_command = f"loadasc tmp/output.asc"
            self._lines.append(f"        {self._cur_command}")
            self.handle_command()

            return

        if self._cur_command.startswith("loadasm"):
            asm_path = self._cur_command[7:].strip()
            asm_path = pathlib.Path(asm_path).resolve()
            python_executable_path = pathlib.Path(sys.executable).resolve()
            output_path = pathlib.Path("tmp/output").resolve()

            if asm_path.exists() is False:
                self._lines.append(f"File at {asm_path} does not exist")
                return

            if not os.path.exists("tmp"):
                os.mkdir("tmp")

            if os.path.exists("tmp/output.asc"):
                os.remove("tmp/output.asc")

            os.system(
                rf"{python_executable_path} bin\simpleCPUv1d_as.py -i {asm_path} -o {output_path}"
            )

            if not os.path.exists("tmp/output.asc"):
                self._lines.append(f"Error while assembling")
                return

            # load the assembled code
            self._cur_command = f"loadasc tmp/output.asc"
            self._lines.append(f"        {self._cur_command}")
            self.handle_command()



        if self._cur_command.startswith("watch"):
            address = eval(self._cur_command[6:])
            self._watching.append(address)
            self._lines.append(f"Watching memory at {address:03x}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("unwatch"):
            address = eval(self._cur_command[8:])
            self._watching.remove(address)
            self._lines.append(f"Stopped watching memory at {address:03x}")
            self._last_command = self._cur_command
            self._cur_command = ""

        if self._cur_command.startswith("getmem"):
            address = eval(self._cur_command[6:])
            self._lines.append(
                f"Memory at {address:03x}: {self._cpu._get_mem(address):03x}"
            )
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("setmem"):
            address, value = self._cur_command[6:].strip().split(" ")
            address = eval(address)
            value = eval(value)

            self._cpu._set_mem(address, value)
            self._lines.append(f"Memory at {address:03x} set to {value:03x}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("exit"):
            self._cpu.enabled = False
            self._cpu.running = False
            self._screen._running = False
            self._running = False
            self._nonblocked._running = False
            return

        if self._cur_command.startswith("clearmem"):
            self._cpu._memory.clear()
            self._lines.append(f"Cleared memory")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("setreg"):
            reg, value = self._cur_command[6:].strip().split(" ")
            reg = eval(reg)
            value = eval(value)

            self._cpu._registers[reg] = value

            self._lines.append(f"Register {reg} set to {value}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("getreg"):
            reg = eval(self._cur_command[6:])

            self._lines.append(f"Register {reg}: {self._cpu._registers[reg]}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("setpc"):
            pc = eval(self._cur_command[5:])

            self._cpu._pc = pc

            self._lines.append(f"PC set to {pc}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("getpc"):
            self._lines.append(f"PC: {self._cpu._pc}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("enabledebug"):
            self._cpu.debug = True
            self._lines.append(f"Debug enabled")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("disabledebug"):
            self._cpu.debug = False
            self._lines.append(f"Debug disabled")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        if self._cur_command.startswith("setdebugtrigger"):
            trigger = eval(self._cur_command[15:])
            self._cpu.debug_port = trigger
            self._lines.append(f"Debug trigger set to {trigger:x}")
            self._last_command = self._cur_command
            self._cur_command = ""
            return

        self._lines.append(f"Unknown command: {self._cur_command}")
        self._last_command = self._cur_command
        self._cur_command = ""

    def handle_x1b(self, data):
        if data == b"[A":
            self._cur_command, self._last_command = (
                self._last_command,
                self._cur_command,
            )
            return

        print(f"[RC] Got escape sequence: {data}")

    def run(self):
        client, addr = self._server.accept()
        print(f"[RC] Connected to {addr}")
        client.send(
            b"Connected successfully\r\n"
            b"Assuming screen size of 80x24\r\n"
            b"Commands:\r\n"
            b"exit - Exit the emulator\r\n"
            b"ss {X} {Y} - Set the screen size to X by Y\r\n"
            b"watch {X} - Watch memory at address X\r\n"
            b"unwatch {X} - Stop watching memory at address X\r\n"
            b"start - Start the CPU\r\n"
            b"stop - Stop the CPU\r\n"
            b"getmem {X} - Get the value at memory address X\r\n"
            b"setmem {X} {Y} - Set the value at memory address X to Y\r\n"
            b"loadscp {X} - Load the SCP file at X\r\n"
            b"loadasm {X} - Load the ASM file at X\r\n"
            b"loadasc {X} - Load the ASC file at X\r\n"
            b"loadimg {X} {Y} - Load the image at X into memory at Y\r\n"
            b"dumpimg {X} {Y} {Z} {W} - Dump the image at X of size YxZ to W\r\n"
            b"watchimg {X} {Y} {Z} - Watch the image at X of size YxZ\r\n"
            b"unwatchimg {X} - Stop watching the image at X\r\n"
            b"clearmem - Clear the memory\r\n"
            b"setreg {X} {Y} - Set register X to Y\r\n"
            b"getreg {X} - Get the value of register X\r\n"
            b"setpc {X} - Set the PC to X\r\n"
            b"getpc - Get the value of the PC\r\n"
            b"enabledebug - Enable debug mode\r\n"
            b"disabledebug - Disable debug mode\r\n"
            b"setdebugtrigger {X} - Set the debug trigger to X\r\n"
            b"gettotalinst - Get the total number of instructions executed\r\n"
            b"\r\n"
            b"Press any key to continue\r\n"
        )
        print(f"[RC] Waiting on client input")
        _ = client.recv(1)
        self._nonblocked.bind(client)
        self._nonblocked.start()
        self._stop_blocking = False

        while self._running:
            try:
                data = client.recv(1)
            except ConnectionAbortedError:
                print(f"[RC] Connection closed")
                break
            except ConnectionResetError:
                print(f"[RC] Connection closed")
                break

            if not data:
                continue

            if data == b"\x1b":
                self.handle_x1b(client.recv(2))
                continue

            if data[0] in range(32, 127):
                self._cur_command += data.decode("utf-8")

            if data == b"\x7f":
                self._cur_command = self._cur_command[:-1]

            if data == b"\r":
                self._lines.append(f"\033[32mCommand\033[0m {self._cur_command}")

                try:
                    self.handle_command()
                except Exception as e:
                    print(f"[RC] Exception while executing command: {e}")
                    traceback.print_exc()

                    self._lines.append(f"\033[31mError\033[0m {e}")

        print("[RC] Stopped")


if __name__ == "__main__":
    # Ensure that the user passes in a file first, before starting anything else
    if not sys.argv[1:]:
        print("Usage: python emulator.py <json file>")
        raise SystemExit

    # Parse file to make sure that the user does not connect, for there to be an error
    command_file = pathlib.Path(sys.argv[1])

    with open(command_file, encoding="utf-8") as file:
        data = file.read()
        json_data = json.loads(data)
        if "defaults" in json_data:
            commands = json_data["defaults"]
        else:
            print("JSON file needs a 'default' key with the instuctions there")
            raise SystemExit

    # Start everything else
    cpu = CPU()
    screen = PygameScreen(cpu)

    os.system(r"start putty -load rawtoscpu")
    rc = RemoteControl(cpu, screen)
    # starts itself

    # Executes commands from the .json file
    for command in commands:
        rc.run_command_ext(command)

    cpu.bind(rc)

    cpu.start()
    screen.run()
