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
from instructions import instructions, REQUIRED, REGISTER, REFERENCE, VALUE, UNCHECKED, aliases


logging.basicConfig(level=logging.DEBUG)


class RegisterRef:
    def __init__(self, value: int):
        self.value = value

    def __str__(self):
        return f"Register({self.value})"

    def __repr__(self):
        return f"Register({self.value})"


def read_token(stream, expected: list[str] = None, comment: Union[None, str] = "#") -> Union[str, None]:
    """
    Read a token from the stream until the expected character is found.
    """

    if expected is None:
        expected = [" ", "\n", ",", "\t"]

    remember_length = len(max(expected, key=len))

    token = ""
    memory = ""

    in_string = False
    escape = False

    while True:
        try:
            c = stream.read(1)

        except EOFError:
            raise EOFError("End of file reached during token read.")

        if len(memory) == remember_length:
            memory = memory[1:] + c

        else:
            memory += c

        if not c and not token:
            return None

        if not c:
            break

        if c == '\\' and not escape:
            escape = True
            continue

        if escape:
            escape = False
            token += c
            continue

        if c == '"':
            in_string = not in_string

        if in_string:
            token += c
            continue

        if any(memory[:i + 1] in expected for i in range(remember_length)):
            break

        if comment is not None and c == comment:
            control = stream.read(1)

            if control == "\n":
                continue

            if control == "/":
                read_token(stream, ["/#"], comment = None)
                continue

            read_token(stream, ["\n"], comment = None)

            continue

        token += c

    return token


def parse_dynamic_token(token: str) -> Union[int, str, RegisterRef]:
    if token.startswith("0x"):
        return int(token[2:], 16)

    if token.startswith("0b"):
        return int(token[2:], 2)

    if token.startswith("0o"):
        return int(token[2:], 8)

    if token.isdigit():
        return int(token)

    if len(token) == 2 and \
        token[0] == "R" and \
        token[1] in "ABCDEFGHIJKLMNOP":
        return RegisterRef("ABCDEFGHIJKLMNOP".index(token[1]))

    return token


InstructionStrut = dict[str, Union[str, int, list[Union[int, str, RegisterRef]]]]
TokensStruct = list[dict[str, list[InstructionStrut]]]


def tokenize(stream):
    roots: TokensStruct = []

    current_root = None
    current_root_index = -1

    # Just for logging purposes
    _last_instruction = None

    while True:
        token = read_token(stream)

        if token in aliases:
            token = str(aliases[token])

        if token is None: break
        if not token.strip(): continue

        # system commands
        if token == '-alias':
            alias = read_token(stream)
            value = read_token(stream)

            aliases[alias] = value

            continue

        # Handle .*: as roots
        if token.endswith(":"):
            # roots cannot be named the same as instructions
            if token[:-1] in instructions:
                logging.critical(f"Found instruction '{token[:-1]}' as root. Exiting.")
                sys.exit(-1)

            if token[:-1] in [list(root.keys())[0] for root in roots]:
                logging.error(f"Root '{token[:-1]}' already exists. Instructions will be amended to previous root.")
                current_root = token[:-1]
                current_root_index = [list(root.keys())[0] for root in roots].index(token[:-1])
                continue

            # Root
            roots.append({token[:-1]: []})
            current_root = token[:-1]
            current_root_index = -1

            continue

        # Insert 'start' root if no roots are found
        if not roots:
            logging.warning("Instruction found without a root. inserting 'start' root.")
            logging.debug(f"{token=} {current_root=} {current_root_index=} {roots=}")
            roots.append({"start": []})
            current_root = "start"

        # Handle instructions
        if token in instructions:
            # If the last instruction does not have at-least the required number of arguments
            if roots[current_root_index][current_root] and len(roots[current_root_index][current_root][-1]['arguments']) < instructions[token].required_arguments:
                logging.critical(f"Found token '{token}' before instruction '{_last_instruction}' was fulfilled.")
                sys.exit(-1)

            roots[current_root_index][current_root].append(
                {"type": "instruction", "name": token, "arguments": []}
            )
            _last_instruction = token


        elif len(roots[current_root_index][current_root]) == 0:
            logging.error(f"Found token '{token}' that cannot be handled. Ignoring.")
            logging.debug(f"{_last_instruction=} {current_root=} {roots[current_root_index][current_root][-10:]}")
            sys.exit()

        # if the last instruction has unfulfilled arguments
        elif len(roots[current_root_index][current_root][-1]['arguments']) < \
            instructions[roots[current_root_index][current_root][-1]['name']].total_arguments:

            value = parse_dynamic_token(token)

            roots[current_root_index][current_root][-1]["arguments"].append(value)

        else:
            logging.error(f"Found token '{token}' that cannot be handled. Ignoring.")
            logging.debug(f"{_last_instruction=} {current_root=} {roots[current_root_index][current_root][-10:]}")

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
        if instruction['type'] == 'instruction':
            name = instruction["name"]
            arguments = instruction["arguments"]

            instruction = instructions[name]

            for i in range(instruction.total_arguments):
                instruction_flags = list(instruction.arguments.values())[i]

                if instruction_flags & REQUIRED and i >= len(arguments):
                    logging.critical(f"Instruction '{name}' requires at least {instruction.required_arguments} arguments. Exiting.")
                    sys.exit(-1)

                if i >= len(arguments):
                    continue

                if instruction_flags & REGISTER and not isinstance(arguments[i], RegisterRef):
                    logging.critical(f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a register reference. Exiting.")
                    sys.exit(-1)

                if instruction_flags & REFERENCE and isinstance(arguments[i], str) and arguments[i] not in roots:
                    logging.critical(f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a valid reference. Exiting.")
                    sys.exit(-1)

                if instruction_flags & VALUE and isinstance(arguments[i], str) and arguments[i] not in roots:
                    logging.critical(f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a valid token. Exiting.")
                    sys.exit(-1)

    return stream


def assemble_asc(stream: list[InstructionStrut], memory_offset: int) -> str:
    """
    Assembles the stream.
    """

    # 'write start address to file'
    # hex in chunks of 4
    output = [f'{memory_offset:>04x}']
    roots = {
        inst["ref"]: address + memory_offset for address, inst in enumerate(stream) if "ref" in inst
    }

    for instruction in stream:
        if instruction["type"] == "instruction":
            args = instruction["arguments"]

            for i in range(len(args)):
                if isinstance(args[i], str) and args[i] in roots:
                    args[i] = roots[args[i]]
                    continue

                if list(instructions[instruction['name']].arguments.values())[i] & UNCHECKED:
                    continue

                if isinstance(args[i], RegisterRef):
                    args[i] = args[i].value
                    continue

                if isinstance(args[i], int):
                    continue

                logging.critical(f"Unknown argument type '{args[i]}'. Exiting.")
                sys.exit(-1)

            output.extend(instructions[instruction['name']].asm_compile(*args))

    return ' '.join(output)


cast_hex_2_big = lambda x: f"{min(max(x, 0x00), 0xff):<02x}"
cast_hex_2_small = lambda x: f"{min(max(x, 0x00), 0xff):>02x}"

"""
Generator functions to convert the stream into the 500 formats that are apparently required.
"""



def generate_high_asc(assembled: str) -> str:
    asc = assembled.split(" ")[1:]

    return assembled[:5] + " ".join([i[:2] for i in asc])

def generate_low_asc(assembled: str) -> str:
    asc = assembled.split(" ")[1:]

    return assembled[:5] + " ".join([i[2:] for i in asc])

def generate_dat(assembled: str, memory_offset: int) -> str:
    output = ""

    for i, inst in enumerate(assembled.split(" ")[1:]):
        output += f"{i + memory_offset:04} {int(inst[:2], 16):08b}{int(inst[2:], 16):08b}\n"

    return output

def generate_mem(assembled: str, memory_offset: int) -> str:
    output = ""

    for i, inst in enumerate(assembled.split(" ")[1:]):
        normal = cast_hex_2_small(int(inst[:2], 16)) + cast_hex_2_small(int(inst[2:], 16))

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
    cheat = [f'{int(a):>04x}' + " : " + b + ";" for a, b in [i.split(" ") for i in cheat if i]]
    output += "\n"
    output += "\n".join(cheat)

    output += "\nEND;\n"

    return output


def generate_cli(steam, asc, dat, mem, mif, address_offset: int = 0):
    # tokens = tokenize(steam)
    # positioned = root_afermer(tokens)
    # linked = linker(positioned)
    #
    # assembled = assemble(linked, address_offset)

    assembled = assemble_asc(
        type_verifier(
            linker(
                root_afermer(
                    tokenize(steam)
                )
            ),
        ),
        address_offset
    )

    if asc is not None:
        path = pathlib.Path(asc + '.asc').resolve()

        try:
            with open(path, "w") as f:
                f.write(assembled)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .asc file at {path}")

        gen_high_asc = generate_high_asc(assembled)
        path = pathlib.Path(asc + '_high_byte.asc').resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_high_asc)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .asc file at {path}")

        gen_low_asc = generate_low_asc(assembled)
        path = pathlib.Path(asc + '_low_byte.asc').resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_low_asc)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .asc file at {path}")

    if dat is not None:
        gen_dat = generate_dat(assembled, address_offset)
        path = pathlib.Path(dat + '.dat').resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_dat)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .dat file at {path}")

    if mem is not None:
        gen_mem = generate_mem(assembled, address_offset)
        path = pathlib.Path(mem + '.mem').resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_mem)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .mem file at {path}")

    if mif is not None:
        gen_mif = generate_mif(assembled, address_offset)
        path = pathlib.Path(mif + '.mif').resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_mif)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .mif file at {path}")


def example():
    code = """
start:
    load 0xFC
    and 0x01
    jumpz fire
reset:
    move 0x02
    store 0xFC
    jump start
fire:
    move 0x01
    store 0xFC
    jump start
    """.strip()

    stream = StringIO(code)
    stream.seek(0)

    tokens = tokenize(stream)
    positioned = root_afermer(tokens)
    linked = linker(positioned)
    verified = type_verifier(linked)
    assembled = assemble_asc(verified, 0)

    high_asc = generate_high_asc(assembled)
    low_asc = generate_low_asc(assembled)
    dat = generate_dat(assembled, 0)
    mem = generate_mem(assembled, 0)
    mif = generate_mif(assembled, 0)

    print("No arguments where found so showing this example.")
    print("Use -h to list the arguments.")
    print()
    print("Code:")
    print(code)
    print()
    print(".asc file:")
    print(assembled)
    print()
    print(".high.asc file:")
    print(high_asc)
    print()
    print(".low.asc file:")
    print(low_asc)
    print()
    print(".dat file:")
    print(dat)
    print()
    print(".mem file:")
    print(mem)
    print()
    print(".mif file:")
    print(mif)


def main():
    if not sys.argv[1:]:
        example()

    else:
        args = sys.argv[1:]

        options = "hi:A:a:d:m:f:o:"
        long_options = ["help", "input", "Address_offset", "asc_output", "dat_output", "mem_output", "mif_output", "output"]

        args, _ = getopt.getopt(args, options, long_options)

        asc, dat, mem, mif = None, None, None, None
        address_offset = 0
        stream = None

        for arg, val in args:
            if arg in ("-h", "--help"):
                print("Usage: assembler.py -i <input assembly file>")
                print("                    -A <address_offset>")
                print("                    -a <output asc files (includes high and low)>")
                print("                    -d <output dat file>")
                print("                    -m <output mem file>")
                print("                    -f <output mif file>")
                sys.exit(0)

            if arg in ("-i", "--input"):
                with open(val, "r") as f:
                    code = f.read()
                    stream = StringIO(code)
                    stream.seek(0)

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

        if not stream:
            logging.critical("No input file found. Exiting.")
            sys.exit(-1)

        generate_cli(stream, asc, dat, mem, mif, address_offset)


if __name__ == "__main__":
    main()
