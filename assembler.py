# SCPUAS (scoopus, skuːpʌs)
# A assembler for the simplecpu project.
# SCPUAS © 2024 by actorpus is licensed under CC BY-NC-SA 4.0
# https://github.com/actorpus/SCPUAS
# http://simplecpudesign.com/

import getopt
import random
from io import StringIO
from typing import *
import logging
import sys
import pathlib
from scp_instruction import (
    REQUIRED,
    REGISTER,
    REFERENCE,
    VALUE,
    UNCHECKED,
    Instruction,
)
from pprint import pprint


__doc__ = """
Usage:

standard use case 
assembler.py -i <input scp file>
             -A <address offset>
             -a <output asc files (includes high and low) (no ext)>
             -d <output dat file (no ext)>
             -m <output mem file (no ext)>
             -f <output mif file (no ext)>

'compile' into asm file
assembler.py -i <input scp file>
             -D <output asm file (no ext)>
"""


Instructions: dict[str, Instruction] = {}

logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger("SCPUAS")


# sets up the default aliases
aliases = {".randomname": '__import__("random").randbytes(16).hex()'}


class RegisterRef:
    def __init__(self, value: int):
        self.value = value

    def __str__(self):
        return f"Register({self.value})"

    def __repr__(self):
        return f"Register({self.value})"

    def as_arg(self):
        return f"R{chr(self.value + 65)}"


def read_token(
        stream, expected: list[str] = None, comment: Union[None, str] = "#"
) -> Union[str, None]:
    """
    Read a token from the stream until the expected character is found.
    """

    if expected is None:
        expected = [" ", "\n", ",", "\t"]

    token = ""
    memory = ""

    in_code = 0
    out_code_targets = []
    in_string = False
    escape = False

    while True:
        try:
            c = stream.read(1)

        except EOFError:
            raise EOFError("End of file reached during token read.")

        if len(memory) == len(max(expected, key=len)):
            memory = memory[1:] + c

        else:
            memory += c

        if not c and not token:
            return None

        if not c:
            break

        if c == "\\" and not escape:
            escape = True
            continue

        if escape:
            escape = False
            token += c
            continue

        if c == "{" and in_code == 0:
            in_code = 1
            token += c
            continue

        if c == "{" and in_code == 1:
            in_code = 2
            token += c

            out_code_targets = expected.copy()
            expected = ["}}"]

            continue

        if in_code == 1:
            in_code = 0

        if in_code == 0:
            if c == '"':
                in_string = not in_string

            if in_string:
                token += c
                continue

        if any(memory[: i + 1] in expected for i in range(len(max(expected, key=len)))):
            if in_code == 2:
                expected = out_code_targets
                in_code = 0
                token += c
                memory = memory[-len(max(expected, key=len)):]
                continue
            else:
                break

        if in_code == 0:
            if comment is not None and c == comment:
                control = stream.read(1)

                if control == "\n":
                    continue

                if control == "/":
                    read_token(stream, [f"/{comment}"], comment=None)
                    continue

                read_token(stream, ["\n"], comment=None)

                continue

        token += c

    return token.strip()


def parse_dynamic_token(token: str) -> Union[int, str, RegisterRef]:
    if token.startswith("0x"):
        return int(token[2:], 16)

    if token.startswith("0b"):
        return int(token[2:], 2)

    if token.startswith("0o"):
        return int(token[2:], 8)

    if token.isdigit():
        return int(token)

    if len(token) == 2 and token[0] == "R" and token[1] in "ABCDEFGHIJKLMNOP":
        return RegisterRef("ABCDEFGHIJKLMNOP".index(token[1]))

    return token


InstructionStrut = dict[str, Union[str, int, list[Union[int, str, RegisterRef]]]]
TokensStruct = list[dict[str, list[InstructionStrut]]]


def replace_alias(token: str) -> str:
    for alias in aliases:
        token = token.replace(f"${alias}$", aliases[alias])

    return token


user_scope_vars = {}


def replace_code_snippet_eval(token: str, start_c="{{", end_c="}}", _exec=False) -> str:
    global user_scope_vars

    def contained_eval(__code__: str):
        # All names with __ are removed from the scope after the eval,
        # leaving only the variables that are defined in the code snippet.
        # these then are loaded into any future snippets
        for __name__, __value__ in user_scope_vars.items():
            exec(f"{__name__} = {__value__.__repr__()}")

        __var__ = eval(__code__)

        return __var__, locals()

    def contained_exec(__code__: str):
        for __name__, __value__ in user_scope_vars.items():
            exec(f"{__name__} = {__value__.__repr__()}")
        __var__ = ""

        def print(*args, end="\n", sep=" "):
            nonlocal __var__
            __var__ += sep.join(map(str, args)) + end

        exec(__code__)

        return __var__, locals()

    while start_c in token:
        start = token.index(start_c)
        end = token.index(end_c)

        code = token[start + len(start_c): end]

        if _exec:
            value, scope = contained_exec(code)
        else:
            value, scope = contained_eval(code)

        user_scope_vars = {
            k: v
            for k, v in scope.items()
            if not k.startswith("__") and not k.endswith("__") and k != "print"
        }

        token = token[:start] + str(value) + token[end + len(end_c):]

    return token


def tokenize(stream, project_path: pathlib.Path) -> tuple[TokensStruct, list[pathlib.Path]]:
    roots: TokensStruct = []
    imported = []

    current_root = None
    current_root_index = -1

    # Just for logging purposes
    _last_instruction = None

    while True:
        token = read_token(stream)

        if token is None:
            break
        if not token.strip():
            continue

        token = replace_alias(token)

        # system commands
        if token == "-alias":
            alias = read_token(stream)
            value = read_token(stream)

            aliases[alias] = value

            continue

        if token == "-language":
            location = read_token(stream)

            if location == "standard":
                _log.info("Loading standard language file.")

                from standard_instructions import instructions as default_instructions

                Instructions.update(default_instructions)
                imported.append(pathlib.Path("standard_instructions.py"))

            else:
                _log.info(f"Loading language file at {location}.")

                path = pathlib.Path(location)
                if not path.is_absolute():
                    path = project_path / path

                if not path.exists():
                    _log.critical(
                        f"Could not find language file at {path}. Exiting."
                    )
                    raise SystemExit

                path = path.resolve().__str__()

                # Hacky way to load specific file as we only need one variable from it
                def _():
                    with open(path, "r") as f:
                        code = f.read()
                    __name__ = "instructions"
                    exec(code)
                    return locals()["instructions"]

                extra_instructions = _()

                Instructions.update(extra_instructions)
                imported.append(pathlib.Path(path))

            continue

        # Handle code injection
        token = replace_code_snippet_eval(token)

        # Handle .*: as roots
        if token.endswith(":"):
            # roots cannot be named the same as instructions
            if token[:-1] in Instructions:
                _log.critical(f"Found instruction '{token[:-1]}' as root. Exiting.")
                raise SystemExit

            if token[:-1] in [list(root.keys())[0] for root in roots]:
                _log.error(
                    f"Root '{token[:-1]}' already exists. Instructions will be amended to previous root."
                )
                current_root = token[:-1]
                current_root_index = [list(root.keys())[0] for root in roots].index(
                    token[:-1]
                )
                continue

            # Root
            roots.append({token[:-1]: []})
            current_root = token[:-1]
            current_root_index = -1

            continue

        # Insert 'start' root if no roots are found
        if not roots:
            _log.warning("Instruction found without a root. inserting 'start' root.")
            roots.append({"start": []})
            current_root = "start"

        # Handle instructions
        if token in Instructions:
            # If the last instruction does not have at-least the required number of arguments
            if (
                    roots[current_root_index][current_root]
                    and len(roots[current_root_index][current_root][-1]["arguments"])
                    < Instructions[token].required_arguments
            ):
                _log.critical(
                    f"Found token '{token}' before instruction '{_last_instruction}' was fulfilled."
                )
                raise SystemExit

            roots[current_root_index][current_root].append(
                {"type": "instruction", "name": token, "arguments": []}
            )
            _last_instruction = token

        elif len(roots[current_root_index][current_root]) == 0:
            _log.error(f"Found token '{token}' that cannot be handled. Ignoring.")
            raise SystemExit

        # if the last instruction has unfulfilled arguments
        elif (
                len(roots[current_root_index][current_root][-1]["arguments"])
                < Instructions[
                    roots[current_root_index][current_root][-1]["name"]
                ].total_arguments
        ):

            value = parse_dynamic_token(token)

            roots[current_root_index][current_root][-1]["arguments"].append(value)

        else:
            _log.error(f"Found token '{token}' that cannot be handled. Ignoring.")

    return roots, imported


def root_afermer(tokens: TokensStruct) -> list[InstructionStrut]:
    """
    Converts TokensStruct to a list of InstructionStruct moving
    root information into respective instructions.
    """

    if "start" not in tokens[0]:
        _log.critical("No 'start' root found. Exiting.")
        raise SystemExit

    stream: list[InstructionStrut] = []

    for root in tokens:
        root, insts = list(root.keys())[0], list(root.values())[0]

        for i, instruction in enumerate(insts):
            stream.append(instruction)

            if i == 0:
                stream[-1]["ref"] = root

    return stream


def linker(stream: list[InstructionStrut]) -> list[InstructionStrut]:
    """
    Will eventually interpret link's to other files, recursively assembling where necessarily.
    """

    return stream


def type_verifier(stream: list[InstructionStrut], *, ret_roots=False) -> list[InstructionStrut]:
    """
    Verify that all references are valid.
    Verify all arguments are correct types (converting where necessary).
    """

    # flag for decompiling to leave in unconverted types
    if ret_roots:
        for instruction in stream:
            instruction['original'] = instruction['arguments']

    roots = []

    # find all roots
    for instruction in stream:
        if "ref" in instruction:
            roots.append(instruction["ref"])

    # verify that all references are valid roots
    for instruction in stream:
        if instruction["type"] == "instruction":
            name = instruction["name"]
            arguments = instruction["arguments"]

            instruction = Instructions[name]

            for i in range(instruction.total_arguments):
                instruction_flags = list(instruction.arguments.values())[i]

                if instruction_flags & REQUIRED and i >= len(arguments):
                    _log.critical(
                        f"Instruction '{name}' requires at least {instruction.required_arguments} arguments. Exiting."
                    )
                    raise SystemExit

                if i >= len(arguments):
                    continue

                if instruction_flags & REGISTER and not isinstance(
                        arguments[i], RegisterRef
                ):
                    _log.critical(
                        f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a register reference. Exiting."
                    )
                    raise SystemExit

                if (
                        instruction_flags & REFERENCE
                        and isinstance(arguments[i], str)
                        and arguments[i] not in roots
                ):
                    _log.critical(
                        f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a valid reference. Exiting."
                    )
                    raise SystemExit

                if (
                        instruction_flags & VALUE
                        and isinstance(arguments[i], str)
                        and arguments[i] not in roots
                ):
                    _log.critical(
                        f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a valid token. Exiting."
                    )
                    raise SystemExit

    return stream


def compiler(stream: list[InstructionStrut], memory_offset: int, *, ret_roots=False) -> Union[list[str], tuple[list[str], dict[str, int], list[InstructionStrut]]]:
    roots = [inst["ref"] for inst in stream if "ref" in inst]

    # final check on input types and convert registers to values
    for instruction in stream:
        if instruction["type"] == "instruction":
            args = instruction["arguments"]

            for i in range(len(args)):
                if isinstance(args[i], str) and args[i] in roots: continue
                if list(Instructions[instruction["name"]].arguments.values())[i] & UNCHECKED: continue
                if isinstance(args[i], RegisterRef):
                    args[i] = args[i].value
                    continue
                if isinstance(args[i], int): continue
                _log.critical(f"Unknown argument type '{args[i]}'. Exiting.")
                raise SystemExit

    for instruction in stream:
        temp_args = instruction["arguments"]

        # all reference args set to 0
        temp_args = [
            0 if
            isinstance(arg, str) and arg in roots
            else arg

            for i, arg in enumerate(temp_args)
        ]

        instruction["dummy"] = Instructions[instruction["name"]].compile(*temp_args)

    pointer = memory_offset
    roots = {}

    for instruction in stream:
        if "ref" in instruction:
            roots[instruction["ref"]] = pointer

        pointer += len(instruction["dummy"])

    pointer = memory_offset
    output = []

    for instruction in stream:
        temp_args = instruction["arguments"]

        temp_args = [
            arg if not
            (isinstance(arg, str) and arg in roots)
            else roots[arg]

            for i, arg in enumerate(temp_args)
        ]

        instruction['compiled'] = Instructions[instruction['name']].compile(*temp_args)

        if len(instruction['compiled']) != len(instruction['dummy']):
            _log.critical(f"Instruction '{instruction['name']}' compiled to incorrect length. Exiting.")
            raise SystemExit

        pointer += len(instruction['compiled'])
        output += instruction['compiled']

    if ret_roots:
        return output, roots, stream

    return output


"""
Generator functions to convert the stream into the 500 formats that are apparently required.
"""


def assemble_asc(stream: list[str], memory_offset: int) -> str:
    # 'write start address to file'
    output = [f"{memory_offset:04x}"] + stream
    return " ".join(output)


cast_hex_2_big = lambda x: f"{min(max(x, 0x00), 0xff):<02x}"
cast_hex_2_small = lambda x: f"{min(max(x, 0x00), 0xff):>02x}"


def generate_high_asc(assembled: str) -> str:
    asc = assembled.split(" ")[1:]

    return assembled[:5] + " ".join([i[:2] for i in asc])


def generate_low_asc(assembled: str) -> str:
    asc = assembled.split(" ")[1:]

    return assembled[:5] + " ".join([i[2:] for i in asc])


def generate_dat(assembled: str, memory_offset: int) -> str:
    output = ""

    for i, inst in enumerate(assembled.split(" ")[1:]):
        output += (
            f"{i + memory_offset:04} {int(inst[:2], 16):08b}{int(inst[2:], 16):08b}\n"
        )

    return output


def generate_mem(assembled: str, memory_offset: int) -> str:
    output = ""

    for i, inst in enumerate(assembled.split(" ")[1:]):
        normal = cast_hex_2_small(int(inst[:2], 16)) + cast_hex_2_small(
            int(inst[2:], 16)
        )

        output += f"@{2 * (i + memory_offset):04x} {normal[::-1]}\n"

    return output.upper()


def generate_mif(assembled: str, memory_offset: int) -> str:
    output = """
DEPTH = 32;           -- The size of memory in words
WIDTH = 16;           -- The size of data in bits
ADDRESS_RADIX = HEX;  -- The radix for address values
DATA_RADIX = BIN;     -- The radix for data values
CONTENT               -- start of (address : data pairs)
BEGIN
""".strip()

    cheat = generate_dat(assembled, memory_offset).split("\n")
    cheat = [
        f"{int(a):>04x}" + " : " + b + ";"
        for a, b in [i.split(" ") for i in cheat if i]
    ]
    output += "\n"
    output += "\n".join(cheat)

    output += "\nEND;\n"

    return output


def generate_cli(ppath, asc, dat, mem, mif, address_offset: int = 0):
    with open(ppath, "r") as f:
        code = f.read()

    steam = StringIO(
        replace_code_snippet_eval(code, start_c="{{!", end_c="!}}", _exec=True)
    )
    steam.seek(0)

    tokens, imported_names = tokenize(steam, pathlib.Path(ppath).parent)
    affirmed = root_afermer(tokens)
    linked = linker(affirmed)
    typed = type_verifier(linked)
    placed = compiler(typed, address_offset)
    assembled = assemble_asc(placed, address_offset)

    if asc is not None:
        path = pathlib.Path(asc + ".asc").resolve()

        try:
            with open(path, "w") as f:
                f.write(assembled)
        except FileNotFoundError:
            _log.critical(f"Could not write to {path}. Exiting.")
            raise SystemExit

        _log.info(f"Generated .asc file at {path}")

        gen_high_asc = generate_high_asc(assembled)
        path = pathlib.Path(asc + "_high_byte.asc").resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_high_asc)
        except FileNotFoundError:
            _log.critical(f"Could not write to {path}. Exiting.")
            raise SystemExit

        _log.info(f"Generated .asc file at {path}")

        gen_low_asc = generate_low_asc(assembled)
        path = pathlib.Path(asc + "_low_byte.asc").resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_low_asc)
        except FileNotFoundError:
            _log.critical(f"Could not write to {path}. Exiting.")
            raise SystemExit

        _log.info(f"Generated .asc file at {path}")

    if dat is not None:
        gen_dat = generate_dat(assembled, address_offset)
        path = pathlib.Path(dat + ".dat").resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_dat)
        except FileNotFoundError:
            _log.critical(f"Could not write to {path}. Exiting.")
            raise SystemExit

        _log.info(f"Generated .dat file at {path}")

    if mem is not None:
        gen_mem = generate_mem(assembled, address_offset)
        path = pathlib.Path(mem + ".mem").resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_mem)
        except FileNotFoundError:
            _log.critical(f"Could not write to {path}. Exiting.")
            raise SystemExit

        _log.info(f"Generated .mem file at {path}")

    if mif is not None:
        gen_mif = generate_mif(assembled, address_offset)
        path = pathlib.Path(mif + ".mif").resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_mif)
        except FileNotFoundError:
            _log.critical(f"Could not write to {path}. Exiting.")
            raise SystemExit

        _log.info(f"Generated .mif file at {path}")



def deassemble_asc(assembled: str, root_dictionary: dict[str, int], insts: list[InstructionStrut], names:list[pathlib.Path]) -> str:
    # TODO: names is a list bc of the linking to other files

    accepted_instructions = [
        "move", "add", "sub", "and",
        "load", "store", "addm", "subm",
        "jump", "jumpz", "jumpnz", "jumpc",
        "call", "or", "ret", "mover",
        "loadr", "storer", "rol", "ror",
        "addr", "subr", "andr", "orr",
        "xorr", "alsr", ".data"
    ]

    output = ""
    address_offset, *assembled = assembled.split(" ")
    address_offset = int(address_offset, 16)
    root_dictionary = {v- address_offset: k for k, v in root_dictionary.items()}
    current_instruction = None
    current_instruction_remainder = []
    instructions_remainder = insts.copy()
    unsupported_roots = {}

    randname = lambda: ''.join(map(lambda x: x if not x.isdigit() else chr(int(x) + 97), f"UnsupportedOldRoot{random.randbytes(16).hex().upper()}"))

    for root, value in root_dictionary.items():
        if any(ord(_) not in range(97, 123) for _ in value.lower()):
            new = randname()

            _log.debug(f"Unsupported root name '{value}' -> '{new}'")

            if new in unsupported_roots:
                _log.critical(f"Duplicate root name '{new}'. Exiting.")
                raise SystemExit

            unsupported_roots[value] = new

    def interpret_final(value):
        if isinstance(value, RegisterRef):
            return value.as_arg()

        if isinstance(value, int):
            return f"0x{value:x}"

        if not isinstance(value, str):
            _log.critical(f"Unknown value type {value}. Exiting.")
            raise SystemExit

        if value in unsupported_roots:
            return unsupported_roots[value]

        return value

    for compiled_instruction_i, compiled_instruction in enumerate(assembled):
        ti = False

        if not current_instruction_remainder:
            current_instruction = instructions_remainder.pop(0)
            current_instruction_remainder = current_instruction['compiled'].copy()
            ti = True

        supposed = current_instruction_remainder.pop(0)
        if compiled_instruction != supposed:
            _log.critical(f"Instruction {current_instruction['name']} at {address_offset} is not correct, {compiled_instruction} != {supposed}. Exiting.")
            raise SystemExit

        if compiled_instruction_i in root_dictionary:
            root = root_dictionary[compiled_instruction_i]

            if root in unsupported_roots:
                root = unsupported_roots[root]

                output += "# root failed to decompile\n"
            output += f"{root}:\n"

        if ti and current_instruction['name'] not in accepted_instructions:
            output += f"    # Decompiled {current_instruction['name']} instruction\n"

        decomp = [current_instruction['name'], ]

        inst_args_flags = list(Instructions[current_instruction['name']].arguments.values())

        if current_instruction['name'] not in accepted_instructions:
            output += f"    .data 0x{int(compiled_instruction, 16):x}\n"
            continue

        for i, arg in enumerate(current_instruction['original']):
            flags = inst_args_flags[i]

            if flags & REFERENCE:
                decomp.append(root_dictionary[arg])
                continue

            if flags & REGISTER:
                decomp.append(RegisterRef(arg))
                continue

            decomp.append(arg)


        output += f"    {decomp[0]} {' '.join(map(interpret_final, decomp[1:]))}\n"

    final = """
# This code was originally written in the SCPUAS language.
# large chunks of .data instructions may be resultant of
# custom implemented commands within the language.
# 
# See https://github.com/actorpus/SCPUAS
#
# this assembly was rendered from:
"""
    final += "\n".join([f"# - {name.name}" for name in names])
    final += """
# 
# If present, check the .scp files for comments and code annotations.

"""
    final += output + "\n"
    final += "# End of rendered code\n# Failed root index:\n"
    final += "\n".join([f"# - '{k.encode().hex()}' -> '{v}'" for k, v in unsupported_roots.items()])
    # recompilation if necessary:
    # ''.join(chr(int(b[i:i+2], 16)) for i in range(0, len(b), 2))

    return final


def generate_dec(ppath, final_path, asc, address_offset: int = 0):
    with open(ppath, "r") as f:
        code = f.read()

    steam = StringIO(
        replace_code_snippet_eval(code, start_c="{{!", end_c="!}}", _exec=True)
    )
    steam.seek(0)

    tokens, imported_names = tokenize(steam, pathlib.Path(ppath).parent)
    affirmed = root_afermer(tokens)
    linked = linker(affirmed)
    typed = type_verifier(linked, ret_roots=True)
    placed, root_dictionary, insts = compiler(typed, address_offset, ret_roots=True)
    assembled = assemble_asc(placed, address_offset)
    rendered = deassemble_asc(assembled, root_dictionary, insts, names=imported_names + [ppath])

    path = pathlib.Path(final_path + ".asm").resolve()

    try:
        with open(path, "w") as f:
            f.write(rendered)
    except FileNotFoundError:
        _log.critical(f"Could not write to {path}. Exiting.")
        raise SystemExit

    _log.info(f"Generated .asm file at {path}")


def main():
    if not sys.argv[1:]:
        sys.argv.append("-h")


    args = sys.argv[1:]

    options = "hi:A:a:d:m:f:o:D:"
    long_options = [
        "help",
        "input",
        "Address_offset",
        "asc_output",
        "dat_output",
        "mem_output",
        "mif_output",
        "output",
        "Decompile"
    ]

    args, _ = getopt.getopt(args, options, long_options)

    asc, dat, mem, mif, dec = None, None, None, None, None
    address_offset = 0
    ppath = None

    for arg, val in args:
        if arg in ("-h", "--help"):
            print(__doc__)

            raise SystemExit

        if arg in ("-i", "--input"):
            ppath = pathlib.Path(val).resolve()
            if not ppath.exists():
                _log.critical(f"Could not find input file at {ppath}. Exiting.")
                raise SystemExit

        if arg in ("-a", "--asc_output"):
            asc = val

        if arg in ("-d", "--dat_output"):
            dat = val

        if arg in ("-m", "--mem_output"):
            mem = val

        if arg in ("-f", "--mif_output"):
            mif = val

        if arg in ("-A", "--Address_offset"):
            try:
                address_offset = int(val)
            except ValueError:
                _log.critical("Address offset must be an integer. Exiting.")
                raise SystemExit

        if arg in ("-o", "--output"):
            asc = val
            dat = val
            mem = val
            mif = val

        if arg in ("-D", "--Decompile"):
            dec = val

    if not ppath:
        _log.critical("No input file found. Exiting.")
        raise SystemExit

    if dec is not None and any([asc, dat, mem, mif]):
        _log.critical("Decompile flag cannot be used with output flags. Exiting.")
        raise SystemExit

    if dec is not None:
        return generate_dec(ppath, dec, asc, address_offset)

    return generate_cli(ppath, asc, dat, mem, mif, address_offset)


if __name__ == "__main__":
    main()
