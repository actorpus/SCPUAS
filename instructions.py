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

import logging
import sys
from typing import *
from collections import OrderedDict
import inspect


REQUIRED = 1
REFERENCE = 2
REGISTER = 4
VALUE = 8
UNCHECKED = 16


class Instruction:
    # These are set up by the wrapper
    arguments: OrderedDict
    required_arguments: int
    total_arguments: int

    @staticmethod
    def asm_compile(*args) -> List[str]:
        pass


instructions: dict[str, Instruction] = {}


def instruction(insts_ref: Optional[dict[str, Instruction]] = None):
    if insts_ref is None:
        insts_ref = instructions

    def wrapper(_class):
        args = set(_class.__dict__.keys())
        args = args - {"__doc__", "compile", "__module__"}
        args_by_func = inspect.getfullargspec(_class.compile).args

        if set(args) != set(args_by_func):
            logging.critical(
                f"Error parsing arguments for '{_class.__name__}', expected '{', '.join(args_by_func)}', got '{', '.join(args)}'"
            )
            sys.exit(-1)

        args = list(args)
        args.sort(key=lambda x: args_by_func.index(x))

        _class.arguments = OrderedDict()

        for instruction in args:
            _class.arguments[instruction] = _class.__dict__[instruction]

        name = _class.__name__[1:]
        if name.startswith("_"):
            name = "." + name[1:]

        if name in insts_ref:
            logging.critical(
                f"Error parsing instruction '{name}', instruction already exists"
            )
            sys.exit(-1)

        insts_ref[name] = _class

        # wrap the compile method to add the asm_compile method, checking for errors
        def _compile(*args) -> List[str]:
            value: Union[str, List[str]] = _class.compile(*args)

            if type(value) == str:
                if len(value) != 4:
                    logging.critical(
                        f"Error parsing compilation of '{_class.__name__}', expected 4 characters, got '{value}'"
                    )
                    sys.exit(-1)

                value = value.upper()

                return [value]

            elif type(value) == list:
                for v in value:
                    if len(v) != 4:
                        logging.critical(
                            f"Error parsing compilation of '{_class.__name__}', expected 4 characters, got '{v}' in '{', '.join(value)}'"
                        )
                        sys.exit(-1)

                return [v.upper() for v in value]

        _class.asm_compile = _compile

        _class.total_arguments = len(_class.arguments)
        _class.required_arguments = len(
            [arg for arg in _class.arguments if _class.arguments[arg] & REQUIRED]
        )

        return _class

    return wrapper


# add the folowing class as a instruction
@instruction()

# the name of the class is the name of the instruction
# (the _ is removed to avoid conflicts with python keywords)
class _move(Instruction):
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


@instruction()
class _add(Instruction):
    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"1{reg:1x}{kk:02x}"


@instruction()
class _sub(Instruction):
    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"2{reg:1x}{kk:02x}"


@instruction()
class _and(Instruction):
    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"3{reg:1x}{kk:02x}"


@instruction()
class _load(Instruction):
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"4{aa:03x}"


@instruction()
class _store(Instruction):
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"5{aa:03x}"


@instruction()
class _addm(Instruction):
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"6{aa:03x}"


@instruction()
class _subm(Instruction):
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"7{aa:03x}"


@instruction()
class _jump(Instruction):
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"8{aa:03x}"


@instruction()
class _jumpz(Instruction):
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"9{aa:03x}"


@instruction()
class _jumpnz(Instruction):
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"A{aa:03x}"


@instruction()
class _jumpc(Instruction):
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"B{aa:03x}"


@instruction()
class _call(Instruction):
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"C{aa:03x}"


@instruction()
class _or(Instruction):
    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"D{reg:1x}{kk:02x}"


# XOP1 f'Exxx'


@instruction()
class _ret(Instruction):
    @staticmethod
    def compile():
        # first in type FxxN
        return "F000"


@instruction()
class _mover(Instruction):
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}01"


@instruction()
class _loadr(Instruction):
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}02"


@instruction()
class _storer(Instruction):
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}03"


@instruction()
class _rol(Instruction):
    rsd = REGISTER | REQUIRED

    @staticmethod
    def compile(rsd):
        value = rsd << 2

        return f"F{value:1x}04"


@instruction()
class _ror(Instruction):
    rsd = REGISTER | REQUIRED

    @staticmethod
    def compile(rsd):
        value = rsd << 2

        return f"F{value:1x}05"


@instruction()
class _addr(Instruction):
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}06"


@instruction()
class _subr(Instruction):
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}07"


@instruction()
class _andr(Instruction):
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}08"


@instruction()
class _orr(Instruction):
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}09"


@instruction()
class _xorr(Instruction):
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}0A"


@instruction()
class _aslr(Instruction):
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


@instruction()
# __ will be replaced with '.'
class __data(Instruction):
    data = UNCHECKED

    @staticmethod
    def compile(data: int = 0):
        return f"{data:04x}"


@instruction()
class __chr(Instruction):
    data = UNCHECKED | REQUIRED

    @staticmethod
    def compile(data: str):
        if type(data) != str or len(data) != 1:
            logging.critical(
                f"Error compiling '.chr', only one character is allowed, got '{data}'"
            )
            sys.exit(-1)

        value = ord(data)

        return f"{value:04x}"


@instruction()
class __str(Instruction):
    data = UNCHECKED | REQUIRED

    @staticmethod
    def compile(data: str):
        if type(data) != str:
            logging.critical(
                f"Error compiling '.str', only strings are allowed, got '{data}'"
            )
            sys.exit(-1)

        if data.startswith('"'):
            data = data[1:]
        if data.endswith('"'):
            data = data[:-1]

        return [f"{ord(char):04x}" for char in data]


@instruction()
class __strn(Instruction):
    data = UNCHECKED | REQUIRED

    @staticmethod
    def compile(data: str):
        if type(data) != str:
            logging.critical(
                f"Error compiling '.strn', only strings are allowed, got '{data}'"
            )
            sys.exit(-1)

        if data.startswith('"'):
            data = data[1:]
        if data.endswith('"'):
            data = data[:-1]

        return [f"{ord(char):04x}" for char in data] + ["0000"]


# sets up the default aliases
aliases = {".randomname": '__import__("random").randbytes(16).hex()'}


if __name__ == "__main__":
    from pprint import pprint

    pprint(instructions)
    print(instructions["move"].arguments)
    print(instructions["rol"].asm_compile(3))
    print(instructions[".chr"].asm_compile("A"))
    print(instructions[".strn"].asm_compile('"Hello, World! " "'))
