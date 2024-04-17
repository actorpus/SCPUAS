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

    token = ""

    while True:
        try:
            c = stream.read(1)

        except EOFError:
            raise EOFError("End of file reached during token read.")

        if not c and not token:
            return None

        if not c:
            break

        if c in expected:
            break

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


InstructionStrut = dict[str, Union[str, list[Union[int, str]]]]
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

        elif token in InstructionSet:
            if not roots:
                logging.warning(
                    "Instruction found without a label. inserting 'start' label."
                )
                roots.append({"start": []})
                current_root = "start"

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
    """

    roots = []

    for instruction in stream:
        if "ref" in instruction:
            roots.append(instruction["ref"])

    # verify that all references are valid roots
    for instruction in stream:
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

    return stream


AssembledStreamStruct = list[list[int]]


def assemble(stream: list[InstructionStrut]) -> AssembledStreamStruct:
    """
    Assembles the stream.
    """

    # 'write start address to file'
    # hex in chunks of 4
    output = []
    roots = {
        inst["ref"]: address for address, inst in enumerate(stream) if "ref" in inst
    }

    for instruction in stream:
        opcode: int = InstructionSet[instruction["name"]]["instruction"]
        operands = instruction["arguments"]

        operands: list[int] = [
            roots[operand] if operand in roots else operand for operand in operands
        ]

        output.append([opcode, *operands])

    return output


cast_hex_2_big = lambda x: f"{min(max(x, 0x00), 0xff):<02x}"
cast_hex_2_small = lambda x: f"{min(max(x, 0x00), 0xff):>02x}"

"""
Generator functions to convert the stream into the 500 formats that are apparently required.
"""


def generate_asc(stream: AssembledStreamStruct) -> str:
    output = "0000 "

    for inst in stream:
        output += cast_hex_2_big(inst[0])
        output += " ".join([cast_hex_2_small(i) for i in inst[1:]])
        output += " "

    return output.upper()


def generate_high_asc(stream: AssembledStreamStruct) -> str:
    asc = generate_asc(stream)
    asc = asc.split(" ")[1:]
    return "0000 " + " ".join([i[:2] for i in asc])


def generate_low_asc(stream: AssembledStreamStruct) -> str:
    asc = generate_asc(stream)
    asc = asc.split(" ")[1:]
    return "0000 " + " ".join([i[2:] for i in asc])


def generate_dat(stream: AssembledStreamStruct) -> str:
    output = ""

    for i, inst in enumerate(stream):
        output += f"{i:04} {inst[0]:08b}{inst[1]:08b}\n"

    return output


def generate_mem(stream: AssembledStreamStruct) -> str:
    output = ""

    for i, inst in enumerate(stream):
        normal = cast_hex_2_small(inst[0]) + cast_hex_2_small(inst[1])

        output += f"@{2 * i:04x} {normal[::-1]}\n"

    return output.upper()


def generate_mif(stream: AssembledStreamStruct) -> str:
    output = """
DEPTH = 32;           -- The size of memory in words
WIDTH = 16;           -- The size of data in bits
ADDRESS_RADIX = HEX;  -- The radix for address values
DATA_RADIX = BIN;     -- The radix for data values
CONTENT               -- start of (address : data pairs)
BEGIN
""".strip()

    cheat = generate_dat(stream).split("\n")
    cheat = [a + " : " + b + ";" for a, b in [i.split(" ") for i in cheat if i]]
    output += "\n"
    output += "\n".join(cheat)

    output += "\nEND;\n"

    return output


def generate_cli(steam, asc, dat, mem, mif):
    tokens = tokenize(steam)
    positioned = root_afermer(tokens)
    linked = linker(positioned)
    assembled = assemble(linked)

    if asc is not None:
        gen_asc = generate_asc(assembled)
        path = pathlib.Path(asc + '.asc').resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_asc)
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
        gen_dat = generate_dat(assembled)
        path = pathlib.Path(dat + '.dat').resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_dat)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .dat file at {path}")

    if mem is not None:
        gen_mem = generate_mem(assembled)
        path = pathlib.Path(mem + '.mem').resolve()

        try:
            with open(path, "w") as f:
                f.write(gen_mem)
        except FileNotFoundError:
            logging.critical(f"Could not write to {path}. Exiting.")
            sys.exit(-1)

        logging.info(f"Generated .mem file at {path}")

    if mif is not None:
        gen_mif = generate_mif(assembled)
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
    assembled = assemble(linked)

    asc = generate_asc(assembled)
    high_asc = generate_high_asc(assembled)
    low_asc = generate_low_asc(assembled)
    dat = generate_dat(assembled)
    mem = generate_mem(assembled)
    mif = generate_mif(assembled)

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

        options = "hi:A:a:d:m:f:"
        long_options = ["help", "input", "Address_offset", "asc_output", "dat_output", "mem_output", "mif_output"]

        args, _ = getopt.getopt(args, options, long_options)

        asc, dat, mem, mif = None, None, None, None
        stream = None

        for arg, val in args:
            if arg in ("-h", "--help"):
                print("Usage: simpleCPUv1a_as.py -i <input assembly file>")
                print("                          -A <address_offset>")
                print("                          -a <output asc files (includes high and low)>")
                print("                          -d <output dat file>")
                print("                          -m <output mem file>")
                print("                          -f <output mif file>")
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
                raise NotImplementedError("Address offset not implemented yet. :(")

        if not stream:
            logging.critical("No input file found. Exiting.")
            sys.exit(-1)

        generate_cli(stream, asc, dat, mem, mif)


if __name__ == "__main__":
    main()
