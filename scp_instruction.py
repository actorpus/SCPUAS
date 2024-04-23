"""
This file contains the wrapping class for new instructions.
see /examples/sprite.py for an example of how to use this

A caution to other devs, this is fucked beyond imagining
it is only set up this way so people who have not used python
can easily create new instructions.
"""

import logging
import sys
from typing import *
from collections import OrderedDict
import inspect

_log = logging.getLogger("InstructionConfigurator")

REQUIRED = 1
REFERENCE = 2
REGISTER = 4
VALUE = 8
UNCHECKED = 16


class Instruction(type):
    __rep__: Callable
    arguments: OrderedDict
    required_arguments: int
    total_arguments: int
    name: str

    def __repr__(cls):
        return cls.__rep__(cls)

    @staticmethod
    def compile(*args) -> List[str]:
        raise NotImplementedError

    @staticmethod
    def create(insts_ref: dict[str,]):
        if type(insts_ref) != dict:
            _log.critical(f"Error parsing instructions reference, expected dict, got '{type(insts_ref)}'")

        _log.debug(f"Creating new instruction wrapper")

        def class_wrapper(_class):
            _log.debug(f"Wrapping class '{_class.__name__}'")

            args = set(_class.__dict__.keys())
            args = args - {
                "compile",
                "__module__",
                "__doc__",
                "__weakref__",
                "__dict__",
            }
            args_by_func = inspect.getfullargspec(_class.compile).args

            if set(args) != set(args_by_func):
                _log.critical(
                    f"Error parsing arguments for '{_class.__name__}', expected '{', '.join(args_by_func)}', got '{', '.join(args)}'"
                )
                raise SystemExit

            args = list(args)
            args.sort(key=lambda x: args_by_func.index(x))

            _log.debug("Arguments parsed and ordered, '" + ", ".join(args) + ",'")

            name = _class.__name__[1:]
            if name.startswith("_"):
                name = "." + name[1:]

            if name in insts_ref:
                _log.critical(
                    f"Error parsing instruction '{name}', instruction already exists"
                )
                raise SystemExit

            # wrap the compile method to add the asm_compile method, checking for errors
            def compile_wrapper(*args) -> List[str]:
                value: Union[str, List[str]] = _class.compile(*args)

                if type(value) == str:
                    if len(value) != 4:
                        _log.critical(
                            f"Error parsing compilation of '{_class.__name__}', expected 4 characters, got '{value}'"
                        )
                        raise SystemExit

                    value = value.upper()

                    return [value]

                elif type(value) == list:
                    for v in value:
                        if len(v) != 4:
                            _log.critical(
                                f"Error parsing compilation of '{_class.__name__}', expected 4 characters, got '{v}' in '{', '.join(value)}'"
                            )
                            raise SystemExit

                    return [v.upper() for v in value]

            def ref(cls):
                return f"<Instruction '{cls.instruction}' wrapping '{cls.__orig_class__.__name__}'>"

            if name.startswith("_"):
                name = '.' + name[1:]

            arguments = OrderedDict()

            for instruction in args:
                arguments[instruction] = _class.__dict__[instruction]

            n_args = {
                'instruction': name,
                'compile': compile_wrapper,
                'arguments': arguments,
                'total_arguments': len(arguments),
                'required_arguments': len(
                    [arg for arg in arguments if arguments[arg] & REQUIRED]
                ),
                '__doc__': _class.__doc__,
                '__rep__': ref,
                '__orig_class__': _class,
            }

            new_class = Instruction(
                "GeneratedInstruction",
                (Instruction, object),
                n_args
            )


            _log.debug(f"Instruction '{name}' wrapped to '{new_class.__name__}', adding to reference")

            insts_ref[name] = new_class

            return new_class

        return class_wrapper


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    i = {}
    print("TESTING")

    @Instruction.create(i)
    class __str:
        data = UNCHECKED | REQUIRED

        @staticmethod
        def compile(data: str):
            return "00a0"


    @Instruction.create(i)
    class _add:
        rd = REGISTER | REQUIRED
        kk = VALUE

        @staticmethod
        def compile(rd, kk=0):
            reg = rd << 2

            return f"1{reg:1x}{kk:02x}"

    for inst in i:
        print(inst, i[inst])

    assert i['.str'].compile("a") == ['00A0']
    assert i['add'].compile(1, 2) == ['1402']

    print("TESTING PASSED")

    # no way anything could slip through this absolute unit of a test setup
