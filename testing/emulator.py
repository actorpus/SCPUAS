# An emulator for the simplecpu project.
# This emulator is part of the SCPUAS project.
# SCPUAS © 2024 by actorpus is licensed under CC BY-NC-SA 4.0


import os
import numpy as np


class CPU:
    def __init__(self):
        self.__memory = np.zeros(4096, dtype=np.uint16)
        self.__registers = np.zeros(16, dtype=np.uint16)
        self.__stack = np.zeros(4, dtype=np.uint16)
        self.__stack_pointer = 0
        self.__pc = 0
        self.__ir = 0
        self.__flag_carry = False

        self._current_instruction_rel_func = None

    def _wipe_flags(self):
        self.__flag_carry = False

    def load_memory(self, at, memory):
        for i, c in enumerate(memory):
            self.__memory[i + at] = int(c, 16)

    def _get_mem(self, at):
        if at == 0xFFF:
            print("Trying to access memory at 0xFFF")

        if at == 0xFFE:
            print("Trying to access memory at 0xFFE")

        return self.__memory[at]

    def _set_mem(self, at, value):
        if at == 0xFFF:
            print("Trying to write memory at 0xFFF", value)

        if at == 0xFFE:
            print("Trying to write memory at 0xFFE", value)

        self.__memory[at] = value

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
        self.__registers[0] = self.__memory[value]

    def _STORE(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
            ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        self.__memory[value] = self.__registers[0]

    def _ADDM(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
            ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

        self._wipe_flags()
        self.__flag_carry = self.__registers[0] + value > 0xFFFF

        self.__registers[0] += value

    def _SUBM(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00):
        value = (
            ir11 << 11 | ir10 << 10 | ir09 << 9 | ir08 << 8 | ir07ir04 << 4 | ir03ir00
        )

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

        if self.__registers != 0:
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

    # def _MOVER(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
    # def _LOADR(self, ir11, ir10, ir09, ir08, ir07ir04, ir03ir00): ...
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
                # 0b0001: self._MOVER,
                # 0b0010: self._LOADR,
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
        print(f"Fetched: {self.__ir} at {self.__pc - 1}")

    def _decode(self):
        self._current_instruction_rel_func = self._decode_instruction_rel_func(
            self.__ir
        )

        print(f"Decoded: {self._current_instruction_rel_func.__name__}")

    def _execute(self):
        ir11 = (self.__ir >> 11) & 1
        ir10 = (self.__ir >> 10) & 1
        ir09 = (self.__ir >> 9) & 1
        ir08 = (self.__ir >> 8) & 1
        ir07ir04 = (self.__ir >> 4) & 0xF
        ir03ir00 = self.__ir & 0xF

        self._current_instruction_rel_func(ir11, ir10, ir09, ir08, ir07ir04, ir03ir00)

        print(f"Executed: {self._current_instruction_rel_func.__name__}")

    def run(self):
        import time

        print(f"Registers: {self.__registers}")
        # print(f"Memory: {self.__memory}")
        # print(f"PC: {self.__pc}")
        # print(f"IR: {self.__ir}")

        i, t = 0, time.time()

        while True:
            self._fetch()
            self._decode()
            self._execute()

            i += 1
            if i == 100000:
                c = time.time()
                r = c - t
                s = r / 100000
                print(f"Running at {1 / s / 1000:.2f} kHz")
                i, t = 0, c

            print(f"Registers: {self.__registers}")
            print(f"Memory: {self.__memory[4]}")
            print(f"PC: {self.__pc}")
            print(f"IR: {self.__ir}")

            time.sleep(1)


if __name__ == "__main__":
    # os.system(r".\.venv\Scripts\python.exe .\assembler.py -i .\test2.asm -a .\tmp")
    # os.remove(r".\tmp_high_byte.asc")
    # os.remove(r".\tmp_low_byte.asc")

    with open(r"tmp.asc", "r") as f:
        code = f.read().strip().split(" ")

    memory_start, *code = code
    memory_start = int(memory_start, 16)

    cpu = CPU()
    cpu.load_memory(memory_start, code)
    cpu.run()
