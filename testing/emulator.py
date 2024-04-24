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

import os
import numpy as np
import socket
import threading
import time


class CPU:
    class memwrap:
        def __init__(self):
            self.__memory = np.zeros(4096, dtype=np.uint16)
            self.mem_change_hook = None

        def __getitem__(self, key):
            return self.__memory[key]

        def __setitem__(self, key, value):
            if self.mem_change_hook:
                self.mem_change_hook(key, value)

            self.__memory[key] = value


    def __init__(self):
        self._memory = self.memwrap()
        self.__registers = np.zeros(16, dtype=np.uint16)
        self.__stack = np.zeros(4, dtype=np.uint16)
        self.__stack_pointer = 0
        self.__pc = 0
        self.__ir = 0
        self.__flag_carry = False

        self._current_instruction_rel_func = None
        self._running_at = "~ KHz"

        self.enabled = False
        self.running = True

    def _wipe_flags(self):
        self.__flag_carry = False

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

        self.__registers[dest] = value

    def _ADD(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        value = ir07ir04 << 4 | ir03ir00

        self._wipe_flags()
        self.__flag_carry = self.__registers[dest] + value > 0xFFFF

        self.__registers[dest] += value

    def _SUB(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        value = ir07ir04 << 4 | ir03ir00

        self._wipe_flags()
        self.__flag_carry = self.__registers[dest] < value

        self.__registers[dest] -= value

    def _AND(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        value = ir07ir04 << 4 | ir03ir00

        self._wipe_flags()

        self.__registers[dest] &= value

    def _LOAD(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )
        self.__registers[0] = self._memory[value]

    def _STORE(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        # if value == 0xfff:
        #     print(f"Attempted to write to 0xfff, {self.__registers[0]}")

        self._memory[value] = self.__registers[0]

    def _ADDM(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        value = self._memory[value]

        self._wipe_flags()
        self.__flag_carry = self.__registers[0] + value > 0xFFFF

        self.__registers[0] += value

    def _SUBM(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        value = self._memory[value]

        self._wipe_flags()
        self.__flag_carry = self.__registers[0] < value

        self.__registers[0] -= value

    def _JUMPU(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        self.__pc = value

    def _JUMPZ(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        if self.__registers[0] == 0:
            self.__pc = value

    def _JUMPNZ(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        if self.__registers[0] != 0:
            self.__pc = value

    def _JUMPC(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        if self.__flag_carry:
            self.__pc = value

    def _CALL(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        self.__stack[self.__stack_pointer] = self.__pc
        self.__stack_pointer += 1

        value = (
                ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        self.__pc = value

    # def _OR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    # def _XOP1(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    def _RET(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        self.__stack_pointer -= 1
        self.__pc = self.__stack[self.__stack_pointer]

    def _MOVER(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        src = ir09 << 1 | ir08

        self.__registers[dest] = self.__registers[src]
    def _LOADR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        dest = ir11 << 1 | ir10
        src = ir09 << 1 | ir08

        self.__registers[dest] = self._memory[self.__registers[src]]

    # def _STORER(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    # def _ROL(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    # def _ROR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    # def _ADDR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    # def _SUBR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    # def _ANDR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    # def _ORR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    # def _XORR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    # def _ASLR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...

    def _decode_instruction_rel_func(self, ir):
        ir15ir12 = ir >> 12
        ir04ir00 = ir & 0x0F

        if ir15ir12 == 0b1111:
            return {
                0b0000: self._RET,
                0b0001: self._MOVER,
                0b0010: self._LOADR,
                # 0b0011: self._STORER,
                # 0b0100: self._ROL,
                # 0b0101: self._ROR,
                # 0b0110: self._ADDR,
                # 0b0111: self._SUBR,
                # 0b1000: self._ANDR,
                # 0b1001: self._ORR,
                # 0b1010: self._XORR,
                # 0b1011: self._ASLR,
                # 0b1100: self._XOP2,
                # 0b1101: self._XOP3,
                # 0b1110: self._XOP4,
                # 0b1111: self._XOP5,
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
            # 0b1101: self._OR,
            # 0b1110: self._XOP1,
        }[ir15ir12]

    def _fetch(self):
        self.__ir = self._get_mem(self.__pc)
        self.__pc += 1
        # print(f"Fetched: {self.__ir} at {self.__pc - 1}")

    def _decode(self):
        self._current_instruction_rel_func = self._decode_instruction_rel_func(
            self.__ir
        )

        # print(f"Decoded: {self._current_instruction_rel_func.__name__}")

    def _execute(self):
        ir11 = (self.__ir >> 11) & 1
        ir10 = (self.__ir >> 10) & 1
        ir09 = (self.__ir >> 9) & 1
        ir08 = (self.__ir >> 8) & 1
        ir07ir04 = (self.__ir >> 4) & 0xF
        ir03ir00 = self.__ir & 0xF

        self._current_instruction_rel_func(ir11, ir10, ir09, ir08, ir07ir04, ir03ir00)

        # print(f"Executed: {self._current_instruction_rel_func.__name__}")

    def run(self):
        i, t = 0, time.time()

        while self.running:
            if not self.enabled:
                time.sleep(1)
                self.running_at = "~ KHz"
                continue

            self._fetch()
            self._decode()
            self._execute()

            i += 1
            if i == 100000:
                c = time.time()
                r = c - t
                s = r / 100000
                self._running_at = f"{1 / s / 1000:.2f} kHz"
                i, t = 0, c

class RemoteControl(threading.Thread):
    class _NonBlocked(threading.Thread):
        def __init__(self, client, rc):
            super().__init__()
            self._client = client
            self._rc = rc

            self._old_data = {}
            self._rc._cpu._memory.mem_change_hook = lambda key, value: self._check_changes(key, value)

        def bind(self, client):
            self._client = client

        def _check_changes(self, key, value):
            if key in self._rc._watching:
                w = ""
                if value in range(32, 127):
                    w = f" '{chr(value)}'"

                self._rc._lines.append(f"\033[31mMemory\033[0m {key:03x}: {self._old_data.get(key, 0):04x} -> {value:04x}{w}")
                self._old_data[key] = value

        def run(self):
            print(f"[RC.NB] Started")

            while True:
                try:
                    self._client.send(self._rc.render())
                except ConnectionAbortedError:
                    print(f"[RC.NB] Connection closed")
                    self._rc._cpu.enabled = False
                    self._rc._cpu.running = False
                    break

                time.sleep(0.1)

    def __init__(self, cpu_ref: CPU):
        super().__init__()

        self._screen_size = (80, 24)
        self._cpu: CPU = cpu_ref
        self._stop_blocking = True

        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind(('localhost', 4003))
        self._server.listen(1)

        self._lines = []
        self._cur_command = ''
        self._watching = []
        self._last_command = ''

        self.start()

        self._nonblocked = self._NonBlocked(self._server, self)

        print(f"[RC] Waiting for connection")
        while self._stop_blocking: time.sleep(0.1)

    def render(self):
        # Clear screen, reset cursor, reset colors, underline
        out = '\033[2J\033[H\033[0m\033[4m Remote Control \033[0m' + ' ' * (self._screen_size[0] - 16 - 4) + 'I001\r\n'

        lines = self._lines[-(self._screen_size[1] - 3):]

        for line in lines:
            out += line + '\r\n'

        out += f'\033[{self._screen_size[1] - 1};0f'
        out += '-' * self._screen_size[0]
        out += '\r\n:'
        out += self._cur_command
        out += ' ' * (self._screen_size[0] - len(self._cur_command) - len(self._cpu._running_at) - 1)
        out += self._cpu._running_at
        # move cursor back to input
        out += f'\033[{self._screen_size[1]};{len(self._cur_command) + 2}f'

        return out.encode('utf-8')

    def handle_command(self):
        if self._cur_command == '!exit':
            raise SystemExit

        if self._cur_command.startswith('ss'):
            if not self._cur_command[2:].strip():
                self._lines.append("Reset screen size to 80x24")
                self._screen_size = (80, 24)
                self._last_command = self._cur_command
                self._cur_command = ''
                return

            x, y = self._cur_command[2:].strip().split(' ')
            self._lines.append(f"Screen size set to {x}x{y}")
            self._screen_size = (int(x), int(y))
            self._last_command = self._cur_command
            self._cur_command = ''
            return

        if self._cur_command == 'start':
            self._cpu.enabled = True
            self._lines.append("CPU started")
            self._last_command = self._cur_command
            self._cur_command = ''
            return

        if self._cur_command == 'stop':
            self._cpu.enabled = False
            self._lines.append("CPU stopped")
            self._last_command = self._cur_command
            self._cur_command = ''
            return

        if self._cur_command.startswith("watch"):
            address = eval(self._cur_command[6:])
            self._watching.append(address)
            self._lines.append(f"Watching memory at {address:03x}")
            self._last_command = self._cur_command
            self._cur_command = ''
            return

        if self._cur_command.startswith("unwatch"):
            address = eval(self._cur_command[8:])
            self._watching.remove(address)
            self._lines.append(f"Stopped watching memory at {address:03x}")
            self._last_command = self._cur_command
            self._cur_command = ''

        if self._cur_command.startswith("getmem"):
            address = eval(self._cur_command[6:])
            self._lines.append(f"Memory at {address:03x}: {self._cpu._get_mem(address):03x}")
            self._last_command = self._cur_command
            self._cur_command = ''
            return

        if self._cur_command.startswith("setmem"):
            address, value = self._cur_command[6:].strip().split(" ")
            address = eval(address)
            value = eval(value)

            self._cpu._set_mem(address, value)
            self._lines.append(f"Memory at {address:03x} set to {value:03x}")
            self._last_command = self._cur_command
            self._cur_command = ''
            return

        self._lines.append(f"Unknown command: {self._cur_command}")
        self._last_command = self._cur_command
        self._cur_command = ''


    def handle_x1b(self, data):
        if data == b'[A':
            self._cur_command, self._last_command = self._last_command, self._cur_command
            return

        print(f"[RC] Got escape sequence: {data}")

    def run(self):
        client, addr = self._server.accept()
        print(f"[RC] Connected to {addr}")
        client.send(
            b'Connected successfully\r\n'
            b'Assuming screen size of 80x24\r\n'
            b'Commands:\r\n'
            b'exit - Exit the emulator\r\n'
            b'ss {X} {Y} - Set the screen size to X by Y\r\n'
            b'watch {X} - Watch memory at address X\r\n'
            b'unwatch {X} - Stop watching memory at address X\r\n'
            b'start - Start the CPU\r\n'
            b'stop - Stop the CPU\r\n'
            b'getmem {X} - Get the value at memory address X\r\n'
            b'setmem {X} {Y} - Set the value at memory address X to Y\r\n'
            b'\r\n'
            b'Press any key to continue\r\n'
        )
        print(f"[RC] Waiting on client input")
        _ = client.recv(1)
        self._nonblocked.bind(client)
        self._nonblocked.start()
        self._stop_blocking = False

        while True:
            try:
                data = client.recv(1)
            except ConnectionAbortedError:
                print(f"[RC] Connection closed")
                break

            if not data:
                continue

            if data == b'\x1b':
                self.handle_x1b(client.recv(2))
                continue

            if data[0] in range(32, 127):
                self._cur_command += data.decode('utf-8')

            if data == b'\x7f':
                self._cur_command = self._cur_command[:-1]

            if data == b'\r':
                self.handle_command()


if __name__ == "__main__":
    os.system(r".\..\.venv\Scripts\python.exe .\..\assembler.py -i .\emulator_test.scp -a .\tmp -V")
    os.remove(r".\tmp_high_byte.asc")
    os.remove(r".\tmp_low_byte.asc")

    with open(r"tmp.asc", "r") as f:
        code = f.read().strip().split(" ")

    memory_start, *code = code
    memory_start = int(memory_start, 16)

    cpu = CPU()
    cpu.load_memory(memory_start, code)

    RemoteControl(cpu)

    cpu.run()
