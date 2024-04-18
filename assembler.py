# SCPUAS (scoopus, skuːpʌs)
# A assembler for the simplecpu project.
# SCPUAS © 2024 by actorpus is licensed under CC BY-NC-SA 4.0
# https://github.com/actorpus/SCPUAS
# http://simplecpudesign.com/

import getopt
from io import StringIO
from typing import *
import logging
import sys
import pathlib
from instructions import (
    REQUIRED,
    REGISTER,
    REFERENCE,
    VALUE,
    UNCHECKED,
    Instruction,
    aliases,
)

Instructions: dict[str, Instruction] = {}

logging.basicConfig(level=logging.DEBUG)


class RegisterRef:
    def __init__(self, value: int):
        self.value = value

    def __str__(self):
        return f"Register({self.value})"

    def __repr__(self):
        return f"Register({self.value})"


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


def tokenize(stream, project_path: pathlib.Path):
    roots: TokensStruct = []

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
                logging.info("Loading standard language file.")

                from instructions import instructions as default_instructions

                Instructions.update(default_instructions)

            else:
                logging.info(f"Loading language file at {location}.")

                path = pathlib.Path(location)
                if not path.is_absolute():
                    path = project_path / path

                if not path.exists():
                    logging.critical(
                        f"Could not find language file at {path}. Exiting."
                    )
                    sys.exit(-1)

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

            continue

        # Handle code injection
        token = replace_code_snippet_eval(token)

        # Handle .*: as roots
        if token.endswith(":"):
            # roots cannot be named the same as instructions
            if token[:-1] in Instructions:
                logging.critical(f"Found instruction '{token[:-1]}' as root. Exiting.")
                sys.exit(-1)

            if token[:-1] in [list(root.keys())[0] for root in roots]:
                logging.error(
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
            logging.warning("Instruction found without a root. inserting 'start' root.")
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
                logging.critical(
                    f"Found token '{token}' before instruction '{_last_instruction}' was fulfilled."
                )
                sys.exit(-1)

            roots[current_root_index][current_root].append(
                {"type": "instruction", "name": token, "arguments": []}
            )
            _last_instruction = token

        elif len(roots[current_root_index][current_root]) == 0:
            logging.error(f"Found token '{token}' that cannot be handled. Ignoring.")
            sys.exit()

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
            logging.error(f"Found token '{token}' that cannot be handled. Ignoring.")

    return roots


def root_afermer(tokens: TokensStruct) -> list[InstructionStrut]:
    """
    Converts TokensStruct to a list of InstructionStruct moving
    root information into respective instructions.
    """

    if "start" not in tokens[0]:
        logging.critical("No 'start' root found. Exiting.")
        sys.exit(-1)

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


def type_verifier(stream: list[InstructionStrut]) -> list[InstructionStrut]:
    """
    Verify that all references are valid.
    Verify all arguments are correct types (converting where necessary).
    """

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
                    logging.critical(
                        f"Instruction '{name}' requires at least {instruction.required_arguments} arguments. Exiting."
                    )
                    sys.exit(-1)

                if i >= len(arguments):
                    continue

                if instruction_flags & REGISTER and not isinstance(
                        arguments[i], RegisterRef
                ):
                    logging.critical(
                        f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a register reference. Exiting."
                    )
                    sys.exit(-1)

                if (
                        instruction_flags & REFERENCE
                        and isinstance(arguments[i], str)
                        and arguments[i] not in roots
                ):
                    logging.critical(
                        f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a valid reference. Exiting."
                    )
                    sys.exit(-1)

                if (
                        instruction_flags & VALUE
                        and isinstance(arguments[i], str)
                        and arguments[i] not in roots
                ):
                    logging.critical(
                        f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a valid token. Exiting."
                    )
                    sys.exit(-1)

    return stream


def compiler(stream: list[InstructionStrut], memory_offset: int) -> list[str]:
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
                logging.critical(f"Unknown argument type '{args[i]}'. Exiting.")
                sys.exit(-1)

    for instruction in stream:
        temp_args = instruction["arguments"]

        # all reference args set to 0
        temp_args = [
            0 if
            isinstance(arg, str) and arg in roots
            else arg

            for i, arg in enumerate(temp_args)
        ]

        instruction["dummy"] = Instructions[instruction["name"]].asm_compile(*temp_args)

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

        instruction['compiled'] = Instructions[instruction['name']].asm_compile(*temp_args)

        if len(instruction['compiled']) != len(instruction['dummy']):
            logging.critical(f"Instruction '{instruction['name']}' compiled to incorrect length. Exiting.")
            sys.exit(-1)

        pointer += len(instruction['compiled'])
        output += instruction['compiled']

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

    tokens = tokenize(steam, pathlib.Path(ppath).parent)
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
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .asc file at {path}")

        gen_high_asc = generate_high_asc(assembled)
        path = pathlib.Path(asc + "_high_byte.asc").resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_high_asc)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .asc file at {path}")

        gen_low_asc = generate_low_asc(assembled)
        path = pathlib.Path(asc + "_low_byte.asc").resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_low_asc)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .asc file at {path}")

    if dat is not None:
        gen_dat = generate_dat(assembled, address_offset)
        path = pathlib.Path(dat + ".dat").resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_dat)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .dat file at {path}")

    if mem is not None:
        gen_mem = generate_mem(assembled, address_offset)
        path = pathlib.Path(mem + ".mem").resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_mem)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .mem file at {path}")

    if mif is not None:
        gen_mif = generate_mif(assembled, address_offset)
        path = pathlib.Path(mif + ".mif").resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_mif)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .mif file at {path}")


def main():
    if not sys.argv[1:]:
        sys.argv.append("-h")

    else:
        args = sys.argv[1:]

        options = "hi:A:a:d:m:f:o:"
        long_options = [
            "help",
            "input",
            "Address_offset",
            "asc_output",
            "dat_output",
            "mem_output",
            "mif_output",
            "output",
        ]

        args, _ = getopt.getopt(args, options, long_options)

        asc, dat, mem, mif = None, None, None, None
        address_offset = 0
        ppath = None

        for arg, val in args:
            if arg in ("-h", "--help"):
                print("Usage: assembler.py -i <input assembly file>")
                print("                    -A <address_offset>")
                print(
                    "                    -a <output asc files (includes high and low)>"
                )
                print("                    -d <output dat file>")
                print("                    -m <output mem file>")
                print("                    -f <output mif file>")
                sys.exit(0)

            if arg in ("-i", "--input"):
                ppath = pathlib.Path(val).resolve()
                if not ppath.exists():
                    logging.critical(f"Could not find input file at {ppath}. Exiting.")
                    sys.exit(-1)

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
                    logging.critical("Address offset must be an integer. Exiting.")
                    sys.exit(-1)

            if arg in ("-o", "--output"):
                asc = val
                dat = val
                mem = val
                mif = val

        if not ppath:
            logging.critical("No input file found. Exiting.")
            sys.exit(-1)

        generate_cli(ppath, asc, dat, mem, mif, address_offset)


if __name__ == "__main__":
    main()
