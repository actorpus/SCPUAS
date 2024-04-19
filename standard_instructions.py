"""
This file contains the instructions for the assembly language
jump to line 100 to see the instructions, the instructions are
defined as classes with the name of the instruction, the
arguments are defined as class variables.

A class decorator '@instruction()' wraps the compile method for
error handling and sets up a few other variables the assembler
needs.

IMPORTANT:
The length of an instructions compilation may not change depending
on any reference arguments. other arguments can change the length
but as the final reference is not known until the length is calculated
it is not possible to change the length of the instruction('s output)
based on reference arguments.
"""

from scp_instruction import Instruction, REQUIRED, REGISTER, VALUE, UNCHECKED, REFERENCE
import logging
import sys


_log = logging.getLogger("DefaultInstructions")
instructions: dict[str, Instruction] = {}


# add the following class as an instruction
@Instruction.create(instructions)

# the name of the class is the name of the instruction
# (the first _ is removed to avoid conflicts with python keywords,
#  if there is a second underscore it will be replaced with a '.')
class _move:
    # All local variables will be counted as arguments for
    # the instruction, in this case the move instruction
    # can take one or two arguments, the first is a register
    # second is a value, e.g. 'move R1 0x10'
    rd = REGISTER | REQUIRED
    kk = VALUE

    # The compile method is used to convert the arguments
    # to a string that can be used in the assembly code
    # any code can go here but the only arguments are the
    # ones defined in the class above, see '__str' for an
    # example of how to use the UNCHECKED argument
    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"0{reg:1x}{kk:02x}"

    # 'move RB 0x33' would get tokenized into:
    # '_move(1, 51)' then compiled into
    # '0433'


@Instruction.create(instructions)
class _add:
    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"1{reg:1x}{kk:02x}"


@Instruction.create(instructions)
class _sub:
    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"2{reg:1x}{kk:02x}"


@Instruction.create(instructions)
class _and:
    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"3{reg:1x}{kk:02x}"


@Instruction.create(instructions)
class _load:
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"4{aa:03x}"


@Instruction.create(instructions)
class _store:
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"5{aa:03x}"


@Instruction.create(instructions)
class _addm:
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"6{aa:03x}"


@Instruction.create(instructions)
class _subm:
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"7{aa:03x}"


@Instruction.create(instructions)
class _jump:
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"8{aa:03x}"


@Instruction.create(instructions)
class _jumpz:
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"9{aa:03x}"


@Instruction.create(instructions)
class _jumpnz:
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"A{aa:03x}"


@Instruction.create(instructions)
class _jumpc:
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"B{aa:03x}"


@Instruction.create(instructions)
class _call:
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"C{aa:03x}"


@Instruction.create(instructions)
class _or:
    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"D{reg:1x}{kk:02x}"


# XOP1 f'Exxx'


@Instruction.create(instructions)
class _ret:
    @staticmethod
    def compile():
        # first in type FxxN
        return "F000"


@Instruction.create(instructions)
class _mover:
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}01"


@Instruction.create(instructions)
class _loadr:
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}02"


@Instruction.create(instructions)
class _storer:
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}03"


@Instruction.create(instructions)
class _rol:
    rsd = REGISTER | REQUIRED

    @staticmethod
    def compile(rsd):
        value = rsd << 2

        return f"F{value:1x}04"


@Instruction.create(instructions)
class _ror:
    rsd = REGISTER | REQUIRED

    @staticmethod
    def compile(rsd):
        value = rsd << 2

        return f"F{value:1x}05"


@Instruction.create(instructions)
class _addr:
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}06"


@Instruction.create(instructions)
class _subr:
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}07"


@Instruction.create(instructions)
class _andr:
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}08"


@Instruction.create(instructions)
class _orr:
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}09"


@Instruction.create(instructions)
class _xorr:
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}0A"


@Instruction.create(instructions)
class _aslr:
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}0B"


# XOP2 f'FxxC'
# XOP3 f'FxxD'
# XOP4 f'FxxE'
# XOP5 f'FxxF'


# ASSEMBLER INSTRUCTIONS


@Instruction.create(instructions)
# __ will be replaced with '.'
class __data:
    data = UNCHECKED

    @staticmethod
    def compile(data: int = 0):
        return f"{data:04x}"


@Instruction.create(instructions)
class __chr:
    data = UNCHECKED | REQUIRED

    @staticmethod
    def compile(data: str):
        if type(data) != str or len(data) != 1:
            _log.critical(
                f"Error compiling '.chr', only one character is allowed, got '{data}'"
            )
            raise SystemExit

        value = ord(data)

        return f"{value:04x}"


@Instruction.create(instructions)
class __str:
    data = UNCHECKED | REQUIRED

    @staticmethod
    def compile(data: str):
        if type(data) != str:
            _log.critical(
                f"Error compiling '.str', only strings are allowed, got '{data}'"
            )
            raise SystemExit

        if data.startswith('"'):
            data = data[1:]
        if data.endswith('"'):
            data = data[:-1]

        return [f"{ord(char):04x}" for char in data]


@Instruction.create(instructions)
class __strn:
    data = UNCHECKED | REQUIRED

    @staticmethod
    def compile(data: str):
        if type(data) != str:
            _log.critical(
                f"Error compiling '.strn', only strings are allowed, got '{data}'"
            )
            raise SystemExit

        if data.startswith('"'):
            data = data[1:]
        if data.endswith('"'):
            data = data[:-1]

        return [f"{ord(char):04x}" for char in data] + ["0000"]


if __name__ == "__main__":
    from pprint import pprint

    pprint(instructions)
    print(instructions["move"].arguments)
    print(instructions["rol"].compile(3))
    print(instructions[".chr"].compile("A"))
    print(instructions[".strn"].compile('"Hello, World! " "'))
