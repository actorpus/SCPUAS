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

logging.basicConfig(level=logging.DEBUG)

InstructionSet = {
    "add": {"instruction": 0x10, "arguments": 1},
    "addm": {"instruction": 0x60, "arguments": 1},
    "and": {"instruction": 0x30, "arguments": 1},
    "jump": {"instruction": 0x80, "arguments": 1, "ref_arguments": [0]},
    "jumpc": {"instruction": 0xB0, "arguments": 1, "ref_arguments": [0]},
    "jumpnz": {"instruction": 0xA0, "arguments": 1, "ref_arguments": [0]},
    "jumpz": {"instruction": 0x90, "arguments": 1, "ref_arguments": [0]},
    "load": {"instruction": 0x40, "arguments": 1},
    "move": {"instruction": 0x00, "arguments": 1},
    "store": {"instruction": 0x50, "arguments": 1},
    "sub": {"instruction": 0x20, "arguments": 1},
    "subm": {"instruction": 0x60, "arguments": 1},
}


def read_token(stream, expected: list[str] = None) -> Union[str, None]:
    """
    Read a token from the stream until the expected character is found.
    """

    if expected is None:
        expected = [" ", "\n", ","]

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

        if c == "#":
            control = stream.read(1)

            if control == "\n":
                continue

            if control == "/":
                read_token(stream, ["/#"])

            read_token(stream, ["\n"])

            continue

        token += c

    return token


def parse_dynamic_token(token: str) -> Union[int, str]:
    if token.startswith("0x"):
        return int(token[2:], 16)

    if token.startswith("0b"):
        return int(token[2:], 2)

    if token.startswith("0o"):
        return int(token[2:], 8)

    if token.isdigit():
        return int(token)

    return token


InstructionStrut = dict[str, Union[str, int, list[Union[int, str]]]]
TokensStruct = list[dict[str, list[InstructionStrut]]]


def tokenize(stream):
    roots: TokensStruct = []

    current_root = None
    current_root_index = -1
    instruction_unfulfilled = False

    # Just for logging purposes
    _last_instruction = None

    while True:
        token = read_token(stream)

        if token is None:
            break

        if not token.strip():
            # logging.info("Empty token found.")
            continue

        if token.endswith(":"):
            if token[:-1] in InstructionSet:
                logging.critical(
                    f"Found instruction '{token[:-1]}' as label. Ignoring."
                )
                sys.exit(-1)

            if token[:-1] in [list(root.keys())[0] for root in roots]:
                logging.error(
                    f"Label '{token[:-1]}' already exists. Instructions will be amended to previous label."
                )
                current_root = token[:-1]
                current_root_index = [list(root.keys())[0] for root in roots].index(
                    token[:-1]
                )
                continue

            # Label
            roots.append({token[:-1]: []})
            current_root = token[:-1]
            current_root_index = -1

            continue

        if not roots:
            logging.warning(
                "Instruction found without a label. inserting 'start' label."
            )
            roots.append({"start": []})
            current_root = "start"

        if token in InstructionSet:
            if instruction_unfulfilled:
                logging.critical(
                    f"Found token '{token}' before instruction '{_last_instruction}' was fulfilled."
                )
                sys.exit(-1)

            roots[current_root_index][current_root].append(
                {"type": "instruction", "name": token, "arguments": []}
            )
            instruction_unfulfilled = True
            _last_instruction = token

        elif instruction_unfulfilled:
            dynam = parse_dynamic_token(token)

            roots[current_root_index][current_root][-1]["arguments"].append(dynam)

            if (
                    len(roots[current_root_index][current_root][-1]["arguments"])
                    == InstructionSet[_last_instruction]["arguments"]
            ):
                instruction_unfulfilled = False

        elif token.startswith('.'):
            # data instruction

            if token not in [".data", ".str", ".chr", ".strn"]:
                logging.error(
                    f"Found instruction '{token}' without a label or instruction. Ignoring."
                )
                continue

            if instruction_unfulfilled:
                # TODO: unless its the first extra .c* after a .data in which case it should be treated as a relname
                logging.critical(
                    f"Found token '{token}' before instruction '{_last_instruction}' was fulfilled."
                )
                sys.exit(-1)

            roots[current_root_index][current_root].append(
                {"type": "data", "value": None}
            )
            _last_instruction = token

        elif _last_instruction.startswith('.') and roots[current_root_index][current_root][-1]["value"] is None:
            roots[current_root_index][current_root][-1]["value"]: int

            # data for .data
            if _last_instruction == ".data":
                roots[current_root_index][current_root][-1]["value"] = parse_dynamic_token(token)

            elif _last_instruction == ".chr":
                if len(token) != 1:
                    logging.critical(
                        f"Found token '{token}' for .chr instruction. Must be a single character. Exiting."
                    )
                    sys.exit(-1)

                roots[current_root_index][current_root][-1]["value"] = ord(token)

            elif _last_instruction == ".str":
                if token[0] != '"' or token[-1] != '"':
                    logging.critical(
                        f"Found token '{token}' for .str instruction. Must be a string. Exiting."
                    )
                    sys.exit(-1)

                if len(token) == 3:
                    roots[current_root_index][current_root][-1]["value"] = ord(token[1])
                    continue

                for i in range(1, len(token) - 2):
                    roots[current_root_index][current_root][-1]["value"] = ord(token[i])

                    roots[current_root_index][current_root].append(
                        {"type": "data", "value": None}
                    )

                roots[current_root_index][current_root][-1]["value"] = ord(token[-2])

            elif _last_instruction == ".strn":
                if token[0] != '"' or token[-1] != '"':
                    logging.critical(
                        f"Found token '{token}' for .strn instruction. Must be a string. Exiting."
                    )
                    sys.exit(-1)

                if len(token) == 3:
                    roots[current_root_index][current_root][-1]["value"] = ord(token[1])
                    roots[current_root_index][current_root].append(
                        {"type": "data", "value": 0}
                    )

                    continue

                for i in range(1, len(token) - 2):
                    roots[current_root_index][current_root][-1]["value"] = ord(token[i])

                    roots[current_root_index][current_root].append(
                        {"type": "data", "value": None}
                    )

                roots[current_root_index][current_root][-1]["value"] = ord(token[-2])

                roots[current_root_index][current_root].append(
                    {"type": "data", "value": 0}
                )

        elif _last_instruction.startswith('.'):
            logging.error(
                f"Found token '{token}' for completed instruction '{_last_instruction}'. Ignoring."
            )

        else:
            logging.error(
                f"Found token '{token}' without a label or instruction. Ignoring."
            )

    return roots


def root_afermer(tokens: TokensStruct) -> list[InstructionStrut]:
    """
    Converts TokensStruct to a list of InstructionStruct moving
    label information into respective instructions.
    """

    if "start" not in tokens[0]:
        logging.critical("No 'start' label found. Exiting.")
        sys.exit(-1)

    stream: list[InstructionStrut] = []

    for root in tokens:
        root, instructions = list(root.keys())[0], list(root.values())[0]

        for i, instruction in enumerate(instructions):
            stream.append(instruction)

            if i == 0:
                stream[-1]["ref"] = root

    return stream


def linker(stream: list[InstructionStrut]) -> list[InstructionStrut]:
    """
    Will eventually interpret link's to other files, recursively assembling where necessarily.
    Verify that all references are valid.
    Patch all None references to 0
    """

    roots = []

    # find all roots
    for instruction in stream:
        if "ref" in instruction:
            roots.append(instruction["ref"])

    # verify that all references are valid roots
    for instruction in stream:

        if instruction['type'] == 'instruction':
            if "ref_arguments" in InstructionSet[instruction["name"]]:
                InstructionSet[instruction["name"]]: list[int]

                check = [
                    instruction["arguments"][i]
                    for i in range(len(instruction["arguments"]))
                    if i in InstructionSet[instruction["name"]]["ref_arguments"]
                ]

                if not all(i in roots for i in check):
                    logging.critical(
                        f"Invalid reference found in instruction '{instruction}'. Exiting."
                    )
                    sys.exit(-1)

        elif instruction['type'] == 'data':
            if type(instruction['value']) != str:
                continue

            if instruction['value'] not in roots:
                logging.critical(
                    f"Invalid reference found in data '{instruction}'. Exiting."
                )
                sys.exit(-1)

    for i in range(len(stream)):
        if 'arguments' in stream[i] and not stream[i]['arguments']:
            logging.warning(f"Instruction '{stream[i]}' has no arguments. Patching to 0.")
            stream[i]['arguments'] = [0]

        if 'value' in stream[i] and stream[i]['value'] is None:
            logging.warning(f"Data '{stream[i]}' has no value. Patching to 0.")
            stream[i]['value'] = 0

    return stream


AssembledStreamStruct = list[list[int]]


def assemble(stream: list[InstructionStrut], memory_offset: int) -> AssembledStreamStruct:
    """
    Assembles the stream.
    """

    # 'write start address to file'
    # hex in chunks of 4
    output = []
    roots = {
        inst["ref"]: address + memory_offset for address, inst in enumerate(stream) if "ref" in inst
    }

    for instruction in stream:
        if instruction["type"] == "instruction":
            opcode: int = InstructionSet[instruction["name"]]["instruction"]
            operands = instruction["arguments"]

            operands: list[int] = [
                roots[operand] if operand in roots else operand for operand in operands
            ]

            output.append([opcode, *operands])

        elif instruction["type"] == "data":
            final = roots[instruction["value"]] if instruction["value"] in roots else instruction["value"]


            # convert to 2 hex numbers to allow for the edge case where the user wants to store an entire word.
            final = f'{final:>04x}'
            if len(final) > 4:
                logging.critical(f"Data value '{final}' is too large. Exiting.")
                sys.exit(-1)
            final = final[:2], final[2:]

            output.append([
                int(final[0], 16), int(final[1], 16)
            ])

    return output


cast_hex_2_big = lambda x: f"{min(max(x, 0x00), 0xff):<02x}"
cast_hex_2_small = lambda x: f"{min(max(x, 0x00), 0xff):>02x}"

"""
Generator functions to convert the stream into the 500 formats that are apparently required.
"""


def generate_asc(stream: AssembledStreamStruct, memory_offset: int) -> str:
    output = f"{memory_offset:>04x} "

    for inst in stream:
        output += cast_hex_2_big(inst[0])
        output += " ".join([cast_hex_2_small(i) for i in inst[1:]])
        output += " "

    return output.upper()


def generate_high_asc(stream: AssembledStreamStruct, memory_offset: int) -> str:
    asc = generate_asc(stream, memory_offset)
    asc = asc.split(" ")[1:]
    return f"{memory_offset:>04x} " + " ".join([i[:2] for i in asc])


def generate_low_asc(stream: AssembledStreamStruct, memory_offset: int) -> str:
    asc = generate_asc(stream, memory_offset)
    asc = asc.split(" ")[1:]
    return f"{memory_offset:>04x} " + " ".join([i[2:] for i in asc])


def generate_dat(stream: AssembledStreamStruct, memory_offset: int) -> str:
    output = ""

    for i, inst in enumerate(stream):
        output += f"{i + memory_offset:04} {inst[0]:08b}{inst[1]:08b}\n"

    return output


def generate_mem(stream: AssembledStreamStruct, memory_offset: int) -> str:
    output = ""

    for i, inst in enumerate(stream):
        normal = cast_hex_2_small(inst[0]) + cast_hex_2_small(inst[1])

        output += f"@{2 * (i + memory_offset):04x} {normal[::-1]}\n"

    return output.upper()


def generate_mif(stream: AssembledStreamStruct, memory_offset: int) -> str:
    output = """
DEPTH = 32;           -- The size of memory in words
WIDTH = 16;           -- The size of data in bits
ADDRESS_RADIX = HEX;  -- The radix for address values
DATA_RADIX = BIN;     -- The radix for data values
CONTENT               -- start of (address : data pairs)
BEGIN
""".strip()

    cheat = generate_dat(stream, memory_offset).split("\n")
    cheat = [f'{int(a):>04x}' + " : " + b + ";" for a, b in [i.split(" ") for i in cheat if i]]
    output += "\n"
    output += "\n".join(cheat)

    output += "\nEND;\n"

    return output


def generate_cli(steam, asc, dat, mem, mif, address_offset: int = 0):
    tokens = tokenize(steam)
    positioned = root_afermer(tokens)
    linked = linker(positioned)
    assembled = assemble(linked, address_offset)

    if asc is not None:
        gen_asc = generate_asc(assembled, address_offset)
        path = pathlib.Path(asc + '.asc').resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_asc)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .asc file at {path}")

        gen_high_asc = generate_high_asc(assembled, address_offset)
        path = pathlib.Path(asc + '_high_byte.asc').resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_high_asc)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .asc file at {path}")

        gen_low_asc = generate_low_asc(assembled, address_offset)
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
    assembled = assemble(linked, 0)

    asc = generate_asc(assembled, 0)
    high_asc = generate_high_asc(assembled, 0)
    low_asc = generate_low_asc(assembled, 0)
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
    print(asc)
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
                    stream = StringIO(f.read())
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
