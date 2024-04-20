# SCPUAS (scoopus, skuːpʌs)
# A assembler for the simplecpu project.
# SCPUAS © 2024 by actorpus is licensed under CC BY-NC-SA 4.0
# https://github.com/actorpus/SCPUAS
# http://simplecpudesign.com/
import logging
import pathlib
from collections import OrderedDict
from typing import *

from scp_instruction import (
    Instruction,
)

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


# def parse_dynamic_token(token: str) -> Union[int, str, RegisterRef]:
#     if token.startswith("0x"):
#         return int(token[2:], 16)
#
#     if token.startswith("0b"):
#         return int(token[2:], 2)
#
#     if token.startswith("0o"):
#         return int(token[2:], 8)
#
#     if token.isdigit():
#         return int(token)
#
#     if len(token) == 2 and token[0] == "R" and token[1] in "ABCDEFGHIJKLMNOP":
#         return RegisterRef("ABCDEFGHIJKLMNOP".index(token[1]))
#
#     return token


InstructionStrut = dict[str, Union[str, int, list[Union[int, str, RegisterRef]]]]
TokensStruct = list[dict[str, list[InstructionStrut]]]


def create_char_stream(frm) -> iter:
    return iter(str(frm))


def char_stream_ascii_only(stream: iter) -> iter:
    _log = logging.getLogger("AsciiOnly")

    while True:
        try:
            char = next(stream)
        except StopIteration:
            _log.debug("End of stream")
            break

        if char == "\t":
            _log.warning("Found tab character, replacing with 4 spaces.")

            for _ in range(4):
                yield " "

        if ord(char) not in range(32, 127) and char not in ["\n"]:
            _log.warning(f"Found non-ascii character '{char}', ignoring.")
            continue

        yield char


def token_stream_alias_replacer(stream: iter) -> iter:
    _log = logging.getLogger("AliasReplace")

    while True:
        try:
            token = next(stream)
        except StopIteration:
            _log.debug("End of stream")
            break

        for alias in aliases:
            nt = token.replace(f"${alias}$", aliases[alias])

            if nt != token:
                _log.debug(f"Found and replaced alias {alias} in {token}")

            token = nt

        yield token


class TokenizeError(Exception):
    def __init__(self, message, token, memory, char, stream):
        self.message = message
        self.token = token
        self.memory = memory
        self.char = char
        self.stream = stream
        super().__init__(memory)

    def __str__(self):
        nc = []
        for _ in range(10):
            try:
                nc.append(next(self.stream))
            except StopIteration:
                break

        pre = "".join([_ if _ != "\n" else "\\n" for _ in self.memory[:-1] if _ != "\x00"])
        post = "".join([_ if _ != "\n" else "\\n" for _ in nc])

        print(pre)
        print(post)

        return f"""{self.message} during {self.token}
{pre} {self.char} {post}
{' ' * len(pre)} ^ {' ' * len(post)}
"""


def char_stream_tokenize(stream: iter) -> iter:
    _log = logging.getLogger("tokenize")

    memory = ["\x00" for _ in range(10)]
    token = ""
    delimiters = [" ", "\n"]

    inside_block_comment = False
    inside_line_comment = False
    inside_block_code = False
    inside_line_code = False
    inside_string = False

    while True:
        try:
            char = next(stream)
        except StopIteration:
            _log.debug("End of stream")
            break

        if not char or char is None:
            break

        if memory[-1:] == ["\\"]:
            token += char
            memory = memory[1:] + [char]
            continue

        memory = memory[1:] + [char]

        if memory[-2:] == ["#", "/"] and not inside_block_comment:
            inside_block_comment = True
            inside_line_comment = False

        elif memory[-2:] == ["/", "#"] and inside_block_comment:
            inside_block_comment = False
            inside_line_comment = False
            continue

        elif memory[-1:] == ["#"] and not inside_line_code:
            inside_line_comment = True

        elif memory[-1:] == ["\n"] and inside_line_comment:
            inside_line_comment = False
            continue

        elif memory[-2:] == ["{", "!"] and not inside_block_code:
            if inside_line_code:
                _log.critical("Block code start symbol found inside line code")
                # passes out everything for nice error messages later
                raise TokenizeError("Block code start symbol found inside line code", token, memory, char, stream)

            inside_block_code = True

        elif memory[-2:] == ["!", "}"] and inside_block_code:
            inside_block_code = False
            token += "}"
            continue

        elif memory[-2:] == ["{", "{"] and not inside_line_code:
            if inside_block_code:
                _log.critical("Line code start symbol found inside block code")
                raise TokenizeError("Line code start symbol found inside block code", token, memory, char, stream)

            inside_line_code = True

        elif memory[-2:] == ["}", "}"] and inside_line_code:
            inside_line_code = False
            token += "}"
            continue

        elif memory[-1:] == ["\""] and not inside_string:
            inside_string = True

        elif memory[-1:] == ["\""] and inside_string:
            inside_string = False

        if char in delimiters and not (
                inside_block_comment
                or inside_line_comment
                or inside_block_code
                or inside_line_code
                or inside_string
        ):
            if token:
                _log.debug("Token: %s", token)
                yield token

            token = ""
            continue

        if not (
                inside_block_comment
                or inside_line_comment
        ):
            token += char

    if token:
        yield token


# store different scope for each file loaded and executed
# when loading multiple files other scopes can be accessed by
# like {name}.variable where name is relative to the root file
python_in_scp_scopes: dict[pathlib.Path, dict] = {}


def execute_cic_in_scope(code: str, scopes: dict, use_exec=False):
    _log = logging.getLogger("CICExecutor")

    project_root = pathlib.Path(r".").resolve()
    executing_from = pathlib.Path(r".\main").resolve()

    _log.debug("Generating scopes, executing from " + executing_from.__repr__())

    to_resolve = [(k.relative_to(project_root).parts, v) for k, v in scopes.items() if k.relative_to(project_root) != executing_from.relative_to(project_root)]
    to_resolve.sort(key=lambda x: len(x[0]))

    args: dict = {}

    if not executing_from in scopes:
        scopes[executing_from] = {}

    args.update(scopes[executing_from])

    for parts, scope in to_resolve:
        current = args
        for part in parts:
            current = current.setdefault(part, {})
        current.update(scope)

    def compile_r(scope: dict):
        localse = {}

        for k, v in scope.items():
            if isinstance(v, dict):
                localse[k] = compile_r(v)
            else:
                localse[k] = v.__repr__()

        r_code = "type('', (), {"

        for k, v in localse.items():
            r_code += f'"{k}": {v}, '

        r_code = r_code[:-2] + "})"

        return r_code

    init_setup = ""

    for k, v in args.items():
        if isinstance(v, dict):
            init_setup += f"{k} = {compile_r(v)}\n"
        else:
            init_setup += f"{k} = {v.__repr__()}\n"

    def run_and_extract_scope(__code__: str, __initial__: str, __args__: dict, __use__exec__):
        __log__ = logging.getLogger("CICExecutor.Run")
        exec(__initial__)

        if __use__exec__:
            __log__.debug("created scope, overwriting print and using exec")

            __output__ = ""

            def print(*args, end="\n", sep=" "):
                nonlocal __output__
                __output__ += sep.join(map(str, args)) + end

            exec(__code__)

        else:
            __log__.debug("created scope, using eval")

            __output__ = eval(__code__)

        __log__.debug("output = " + __output__.__repr__())

        locale = locals()
        locale = {k: v for k, v in locale.items() if not k.startswith("__") and not k.endswith("__")}

        if "print" in locale:
            del locale["print"]

        def decompose(value):
            if isinstance(value, type):
                locale = value.__dict__
                locale = {k: v for k, v in locale.items() if not k.startswith("__") and not k.endswith("__")}

                return {k: decompose(v) for k, v in locale.items()}
            else:
                return value

        for k, v in locale.items():
            locale[k] = decompose(v)

        __log__.debug("locale = " + locale.__repr__())

        return __output__, locale

    _log.debug("Built local objects, Running")

    output, locale = run_and_extract_scope(code, init_setup, args, use_exec)

    _log.debug("Code executed, reversing output locale into scopes")

    current_scope = {k: v for k, v in locale.items() if k not in {_[0][0] for _ in to_resolve}}
    extra_scopes = {k: v for k, v in locale.items() if k in {_[0][0] for _ in to_resolve}}

    scopes[executing_from] = current_scope

    for scope in scopes:
        if scope == executing_from:
            continue

        scope_t = scope.relative_to(project_root).parts
        looking = extra_scopes.copy()

        for part in scope_t:
            looking = looking[part]

        scopes[scope] = looking

    _log.debug("Reversed scopes")

    return output, scopes


def token_stream_cic_executor(stream: iter) -> iter:
    _log = logging.getLogger("CICExecutor")
    global python_in_scp_scopes

    while True:
        try:
            token = next(stream)
        except StopIteration:
            _log.debug("End of stream")
            break

        insert = []

        while "{!" in token:
            start = token.index("{!")
            end = token.index("!}")

            code = token[start + 2:end]

            result, python_in_scp_scopes = execute_cic_in_scope(code, python_in_scp_scopes, use_exec=True)

            # catch up result to where we are now
            temp_char_stream = create_char_stream(result)
            temp_char_stream = char_stream_ascii_only(temp_char_stream)
            temp_token_stream = char_stream_tokenize(temp_char_stream)
            temp_token_stream = token_stream_alias_replacer(temp_token_stream)

            if start != 0:
                insert.append(token[:start])

            # At no point should an entire stream be loaded into memory, store a reference to an iter
            # and yield individual tokens after processing
            insert.append(temp_token_stream)

            token = token[end + 2:]

        while "{{" in token:
            start = token.index("{{")
            end = token.index("}}")

            code = token[start + 2:end]

            result, python_in_scp_scopes = execute_cic_in_scope(code, python_in_scp_scopes, use_exec=False)

            # catch up result to where we are now
            temp_char_stream = create_char_stream(result)
            temp_char_stream = char_stream_ascii_only(temp_char_stream)
            temp_token_stream = char_stream_tokenize(temp_char_stream)
            temp_token_stream = token_stream_alias_replacer(temp_token_stream)

            if start != 0:
                insert.append(token[:start])

            # At no point should an entire stream be loaded into memory, store a reference to an iter
            # and yield individual tokens after processing
            insert.append(temp_token_stream)

            token = token[end + 2:]

        if token:
            insert.append(token)

        # decompress the insert list into a single stream
        for i in insert:
            if isinstance(i, str):
                yield i
            else:
                for j in i:
                    yield j


def instruction_press(stream: iter, project_path: pathlib.Path) -> tuple[OrderedDict[str, list[InstructionStrut]], list[pathlib.Path]]:
    _log = logging.getLogger("InstructionPress")

    roots: OrderedDict[str, list[InstructionStrut]] = OrderedDict()
    imported = []

    current_root = None

    while True:
        try:
            token = next(stream)
        except StopIteration:
            _log.debug("End of stream")
            break

        if token is None:
            break

        # system commands
        if token == "-alias":
            alias = next(stream, None)
            value = next(stream, None)

            _log.info(f"Found alias '{alias}' with value '{value}'.")
            aliases[alias] = value

            continue

        if token == "-language":
            location = next(stream, None)

            _log.debug(f"Requesting language file at '{location}'.")

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

        _log.debug(f"Read non system token: {token}")

        # Handle .*: as roots
        if token.endswith(":"):
            # roots cannot be named the same as instructions
            if token[:-1] in Instructions:
                _log.critical(f"Found instruction '{token[:-1]}' as root. Exiting.")
                raise SystemExit

            # if root already exists in table jump back to it
            if token[:-1] in roots:
                _log.error(f"Root '{token[:-1]}' already exists. Instructions will be amended "
                           f"to previous instance of root.")
                current_root = token[:-1]
                continue

            # If the last instruction does not have at-least the required number of arguments
            if current_root is not None and roots[current_root] and len(roots[current_root][-1]["arguments"]) < Instructions[roots[current_root][-1]["name"]].required_arguments:
                _log.critical(f"Found root '{token[:-1]}' before the required arguments of the previous instruction were filled. Exiting.")
                raise SystemExit

            # Root
            roots[token[:-1]] = []
            current_root = token[:-1]
            continue

        # Insert 'start' root if no roots are defined yet
        if not roots:
            _log.warning("Instruction found without a root. inserting 'start' root.")
            roots["start"] = []
            current_root = "start"

        # Handle instructions
        if token in Instructions:
            _log.debug(f"Read as instruction: {token}")
            # If the last instruction does not have at-least the required number of arguments
            if roots[current_root] and len(roots[current_root][-1]["arguments"]) < Instructions[roots[current_root][-1]["name"]].required_arguments:
                _log.critical(f"Found instruction '{token}' before the required arguments of the previous instruction were filled. Exiting.")
                raise SystemExit

            roots[current_root].append({"type": "instruction", "name": token, "arguments": []})
            continue


        # Everything else will be a generic token, treat all as arguments
        elif not roots[current_root]:
            _log.error(f"Found token '{token}' before any applicable instruction. Ignoring.")
            continue

        # if the last instruction is full
        if len(roots[current_root][-1]["arguments"]) == Instructions[roots[current_root][-1]["name"]].total_arguments:
            _log.error(f"Found token '{token}' before new applicable instruction. Ignoring.")
            continue

        roots[current_root][-1]["arguments"].append(
            token
        )

    return roots, imported



if __name__ == '__main__':
    with open("examples/instructions.scp") as file:
        code = file.read()

    char_stream = create_char_stream(code)
    char_stream = char_stream_ascii_only(char_stream)
    token_stream = char_stream_tokenize(char_stream)
    token_stream = token_stream_alias_replacer(token_stream)
    token_stream = token_stream_cic_executor(token_stream)

    print(
        instruction_press(token_stream, pathlib.Path("examples/instructions.scp"))
    )


def root_rerooter



# def linker(stream: list[InstructionStrut]) -> list[InstructionStrut]:
#     """
#     Will eventually interpret link's to other files, recursively assembling where necessarily.
#     """
#
#     return stream
#
#
# def root_afermer(tokens: TokensStruct) -> list[InstructionStrut]:
#     """
#     Converts TokensStruct to a list of InstructionStruct moving
#     root information into respective instructions.
#     """
#
#     if "start" not in tokens[0]:
#         _log.critical("No 'start' root found. Exiting.")
#         raise SystemExit
#
#     stream: list[InstructionStrut] = []
#
#     for root in tokens:
#         root, insts = list(root.keys())[0], list(root.values())[0]
#
#         for i, instruction in enumerate(insts):
#             stream.append(instruction)
#
#             if i == 0:
#                 stream[-1]["ref"] = root
#
#     return stream
#
#
#
#
# def type_verifier(stream: list[InstructionStrut], *, ret_roots=False) -> list[InstructionStrut]:
#     """
#     Verify that all references are valid.
#     Verify all arguments are correct types (converting where necessary).
#     """
#
#     # flag for decompiling to leave in unconverted types
#     if ret_roots:
#         for instruction in stream:
#             instruction['original'] = instruction['arguments']
#
#     roots = []
#
#     # find all roots
#     for instruction in stream:
#         if "ref" in instruction:
#             roots.append(instruction["ref"])
#
#     # verify that all references are valid roots
#     for instruction in stream:
#         if instruction["type"] == "instruction":
#             name = instruction["name"]
#             arguments = instruction["arguments"]
#
#             instruction = Instructions[name]
#
#             for i in range(instruction.total_arguments):
#                 instruction_flags = list(instruction.arguments.values())[i]
#
#                 if instruction_flags & REQUIRED and i >= len(arguments):
#                     _log.critical(
#                         f"Instruction '{name}' requires at least {instruction.required_arguments} arguments. Exiting."
#                     )
#                     raise SystemExit
#
#                 if i >= len(arguments):
#                     continue
#
#                 if instruction_flags & REGISTER and not isinstance(
#                         arguments[i], RegisterRef
#                 ):
#                     _log.critical(
#                         f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a register reference. Exiting."
#                     )
#                     raise SystemExit
#
#                 if (
#                         instruction_flags & REFERENCE
#                         and isinstance(arguments[i], str)
#                         and arguments[i] not in roots
#                 ):
#                     _log.critical(
#                         f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a valid reference. Exiting."
#                     )
#                     raise SystemExit
#
#                 if (
#                         instruction_flags & VALUE
#                         and isinstance(arguments[i], str)
#                         and arguments[i] not in roots
#                 ):
#                     _log.critical(
#                         f"Argument {i} ({arguments[i]}) of instruction '{name}' must be a valid token. Exiting."
#                     )
#                     raise SystemExit
#
#     return stream
#
#
# def compiler(stream: list[InstructionStrut], memory_offset: int, *, ret_roots=False) -> Union[list[str], tuple[list[str], dict[str, int], list[InstructionStrut]]]:
#     roots = [inst["ref"] for inst in stream if "ref" in inst]
#
#     # final check on input types and convert registers to values
#     for instruction in stream:
#         if instruction["type"] == "instruction":
#             args = instruction["arguments"]
#
#             for i in range(len(args)):
#                 if isinstance(args[i], str) and args[i] in roots: continue
#                 if list(Instructions[instruction["name"]].arguments.values())[i] & UNCHECKED: continue
#                 if isinstance(args[i], RegisterRef):
#                     args[i] = args[i].value
#                     continue
#                 if isinstance(args[i], int): continue
#                 _log.critical(f"Unknown argument type '{args[i]}'. Exiting.")
#                 raise SystemExit
#
#     for instruction in stream:
#         temp_args = instruction["arguments"]
#
#         # all reference args set to 0
#         temp_args = [
#             0 if
#             isinstance(arg, str) and arg in roots
#             else arg
#
#             for i, arg in enumerate(temp_args)
#         ]
#
#         instruction["dummy"] = Instructions[instruction["name"]].compile(*temp_args)
#
#     pointer = memory_offset
#     roots = {}
#
#     for instruction in stream:
#         if "ref" in instruction:
#             roots[instruction["ref"]] = pointer
#
#         pointer += len(instruction["dummy"])
#
#     pointer = memory_offset
#     output = []
#
#     for instruction in stream:
#         temp_args = instruction["arguments"]
#
#         temp_args = [
#             arg if not
#             (isinstance(arg, str) and arg in roots)
#             else roots[arg]
#
#             for i, arg in enumerate(temp_args)
#         ]
#
#         instruction['compiled'] = Instructions[instruction['name']].compile(*temp_args)
#
#         if len(instruction['compiled']) != len(instruction['dummy']):
#             _log.critical(f"Instruction '{instruction['name']}' compiled to incorrect length. Exiting.")
#             raise SystemExit
#
#         pointer += len(instruction['compiled'])
#         output += instruction['compiled']
#
#     if ret_roots:
#         return output, roots, stream
#
#     return output
#
#
# """
# Generator functions to convert the stream into the 500 formats that are apparently required.
# """
#
#
# def assemble_asc(stream: list[str], memory_offset: int) -> str:
#     # 'write start address to file'
#     output = [f"{memory_offset:04x}"] + stream
#     return " ".join(output)
#
#
# cast_hex_2_big = lambda x: f"{min(max(x, 0x00), 0xff):<02x}"
# cast_hex_2_small = lambda x: f"{min(max(x, 0x00), 0xff):>02x}"
#
#
# def generate_high_asc(assembled: str) -> str:
#     asc = assembled.split(" ")[1:]
#
#     return assembled[:5] + " ".join([i[:2] for i in asc])
#
#
# def generate_low_asc(assembled: str) -> str:
#     asc = assembled.split(" ")[1:]
#
#     return assembled[:5] + " ".join([i[2:] for i in asc])
#
#
# def generate_dat(assembled: str, memory_offset: int) -> str:
#     output = ""
#
#     for i, inst in enumerate(assembled.split(" ")[1:]):
#         output += (
#             f"{i + memory_offset:04} {int(inst[:2], 16):08b}{int(inst[2:], 16):08b}\n"
#         )
#
#     return output
#
#
# def generate_mem(assembled: str, memory_offset: int) -> str:
#     output = ""
#
#     for i, inst in enumerate(assembled.split(" ")[1:]):
#         normal = cast_hex_2_small(int(inst[:2], 16)) + cast_hex_2_small(
#             int(inst[2:], 16)
#         )
#
#         output += f"@{2 * (i + memory_offset):04x} {normal[::-1]}\n"
#
#     return output.upper()
#
#
# def generate_mif(assembled: str, memory_offset: int) -> str:
#     output = """
# DEPTH = 32;           -- The size of memory in words
# WIDTH = 16;           -- The size of data in bits
# ADDRESS_RADIX = HEX;  -- The radix for address values
# DATA_RADIX = BIN;     -- The radix for data values
# CONTENT               -- start of (address : data pairs)
# BEGIN
# """.strip()
#
#     cheat = generate_dat(assembled, memory_offset).split("\n")
#     cheat = [
#         f"{int(a):>04x}" + " : " + b + ";"
#         for a, b in [i.split(" ") for i in cheat if i]
#     ]
#     output += "\n"
#     output += "\n".join(cheat)
#
#     output += "\nEND;\n"
#
#     return output
#
#
# def generate_cli(ppath, asc, dat, mem, mif, address_offset: int = 0):
#     with open(ppath, "r") as f:
#         code = f.read()
#
#     steam = StringIO(
#         replace_code_snippet_eval(code, start_c="{{!", end_c="!}}", _exec=True)
#     )
#     steam.seek(0)
#
#     tokens, imported_names = tokenize(steam, pathlib.Path(ppath).parent)
#     affirmed = root_afermer(tokens)
#     linked = linker(affirmed)
#     typed = type_verifier(linked)
#     placed = compiler(typed, address_offset)
#     assembled = assemble_asc(placed, address_offset)
#
#     if asc is not None:
#         path = pathlib.Path(asc + ".asc").resolve()
#
#         try:
#             with open(path, "w") as f:
#                 f.write(assembled)
#         except FileNotFoundError:
#             _log.critical(f"Could not write to {path}. Exiting.")
#             raise SystemExit
#
#         _log.info(f"Generated .asc file at {path}")
#
#         gen_high_asc = generate_high_asc(assembled)
#         path = pathlib.Path(asc + "_high_byte.asc").resolve()
#
#         try:
#             with open(path, "w") as f:
#                 f.write(gen_high_asc)
#         except FileNotFoundError:
#             _log.critical(f"Could not write to {path}. Exiting.")
#             raise SystemExit
#
#         _log.info(f"Generated .asc file at {path}")
#
#         gen_low_asc = generate_low_asc(assembled)
#         path = pathlib.Path(asc + "_low_byte.asc").resolve()
#
#         try:
#             with open(path, "w") as f:
#                 f.write(gen_low_asc)
#         except FileNotFoundError:
#             _log.critical(f"Could not write to {path}. Exiting.")
#             raise SystemExit
#
#         _log.info(f"Generated .asc file at {path}")
#
#     if dat is not None:
#         gen_dat = generate_dat(assembled, address_offset)
#         path = pathlib.Path(dat + ".dat").resolve()
#
#         try:
#             with open(path, "w") as f:
#                 f.write(gen_dat)
#         except FileNotFoundError:
#             _log.critical(f"Could not write to {path}. Exiting.")
#             raise SystemExit
#
#         _log.info(f"Generated .dat file at {path}")
#
#     if mem is not None:
#         gen_mem = generate_mem(assembled, address_offset)
#         path = pathlib.Path(mem + ".mem").resolve()
#
#         try:
#             with open(path, "w") as f:
#                 f.write(gen_mem)
#         except FileNotFoundError:
#             _log.critical(f"Could not write to {path}. Exiting.")
#             raise SystemExit
#
#         _log.info(f"Generated .mem file at {path}")
#
#     if mif is not None:
#         gen_mif = generate_mif(assembled, address_offset)
#         path = pathlib.Path(mif + ".mif").resolve()
#
#         try:
#             with open(path, "w") as f:
#                 f.write(gen_mif)
#         except FileNotFoundError:
#             _log.critical(f"Could not write to {path}. Exiting.")
#             raise SystemExit
#
#         _log.info(f"Generated .mif file at {path}")
#
#
#
# def deassemble_asc(assembled: str, root_dictionary: dict[str, int], insts: list[InstructionStrut], names:list[pathlib.Path]) -> str:
#     # TODO: names is a list bc of the linking to other files
#
#     accepted_instructions = [
#         "move", "add", "sub", "and",
#         "load", "store", "addm", "subm",
#         "jump", "jumpz", "jumpnz", "jumpc",
#         "call", "or", "ret", "mover",
#         "loadr", "storer", "rol", "ror",
#         "addr", "subr", "andr", "orr",
#         "xorr", "alsr", ".data"
#     ]
#
#     output = ""
#     address_offset, *assembled = assembled.split(" ")
#     address_offset = int(address_offset, 16)
#     root_dictionary = {v- address_offset: k for k, v in root_dictionary.items()}
#     current_instruction = None
#     current_instruction_remainder = []
#     instructions_remainder = insts.copy()
#     unsupported_roots = {}
#
#     randname = lambda: ''.join(map(lambda x: x if not x.isdigit() else chr(int(x) + 97), f"UnsupportedOldRoot{random.randbytes(16).hex().upper()}"))
#
#     for root, value in root_dictionary.items():
#         if any(ord(_) not in range(97, 123) for _ in value.lower()):
#             new = randname()
#
#             _log.debug(f"Unsupported root name '{value}' -> '{new}'")
#
#             if new in unsupported_roots:
#                 _log.critical(f"Duplicate root name '{new}'. Exiting.")
#                 raise SystemExit
#
#             unsupported_roots[value] = new
#
#     def interpret_final(value):
#         if isinstance(value, RegisterRef):
#             return value.as_arg()
#
#         if isinstance(value, int):
#             return f"0x{value:x}"
#
#         if not isinstance(value, str):
#             _log.critical(f"Unknown value type {value}. Exiting.")
#             raise SystemExit
#
#         if value in unsupported_roots:
#             return unsupported_roots[value]
#
#         return value
#
#     for compiled_instruction_i, compiled_instruction in enumerate(assembled):
#         ti = False
#
#         if not current_instruction_remainder:
#             current_instruction = instructions_remainder.pop(0)
#             current_instruction_remainder = current_instruction['compiled'].copy()
#             ti = True
#
#         supposed = current_instruction_remainder.pop(0)
#         if compiled_instruction != supposed:
#             _log.critical(f"Instruction {current_instruction['name']} at {address_offset} is not correct, {compiled_instruction} != {supposed}. Exiting.")
#             raise SystemExit
#
#         if compiled_instruction_i in root_dictionary:
#             root = root_dictionary[compiled_instruction_i]
#
#             if root in unsupported_roots:
#                 root = unsupported_roots[root]
#
#                 output += "# root failed to decompile\n"
#             output += f"{root}:\n"
#
#         if ti and current_instruction['name'] not in accepted_instructions:
#             output += f"    # Decompiled {current_instruction['name']} instruction\n"
#
#         decomp = [current_instruction['name'], ]
#
#         inst_args_flags = list(Instructions[current_instruction['name']].arguments.values())
#
#         if current_instruction['name'] not in accepted_instructions:
#             output += f"    .data 0x{int(compiled_instruction, 16):x}\n"
#             continue
#
#         for i, arg in enumerate(current_instruction['original']):
#             flags = inst_args_flags[i]
#
#             if flags & REFERENCE:
#                 decomp.append(root_dictionary[arg])
#                 continue
#
#             if flags & REGISTER:
#                 decomp.append(RegisterRef(arg))
#                 continue
#
#             decomp.append(arg)
#
#
#         output += f"    {decomp[0]} {' '.join(map(interpret_final, decomp[1:]))}\n"
#
#     final = """
# # This code was originally written in the SCPUAS language.
# # large chunks of .data instructions may be resultant of
# # custom implemented commands within the language.
# #
# # See https://github.com/actorpus/SCPUAS
# #
# # this assembly was rendered from:
# """
#     final += "\n".join([f"# - {name.name}" for name in names])
#     final += """
# #
# # If present, check the .scp files for comments and code annotations.
#
# """
#     final += output + "\n"
#     final += "# End of rendered code\n# Failed root index:\n"
#     final += "\n".join([f"# - '{k.encode().hex()}' -> '{v}'" for k, v in unsupported_roots.items()])
#     # recompilation if necessary:
#     # ''.join(chr(int(b[i:i+2], 16)) for i in range(0, len(b), 2))
#
#     return final
#
#
# def generate_dec(ppath, final_path, asc, address_offset: int = 0):
#     with open(ppath, "r") as f:
#         code = f.read()
#
#     steam = StringIO(
#         replace_code_snippet_eval(code, start_c="{{!", end_c="!}}", _exec=True)
#     )
#     steam.seek(0)
#
#     tokens, imported_names = tokenize(steam, pathlib.Path(ppath).parent)
#     affirmed = root_afermer(tokens)
#     linked = linker(affirmed)
#     typed = type_verifier(linked, ret_roots=True)
#     placed, root_dictionary, insts = compiler(typed, address_offset, ret_roots=True)
#     assembled = assemble_asc(placed, address_offset)
#     rendered = deassemble_asc(assembled, root_dictionary, insts, names=imported_names + [ppath])
#
#     path = pathlib.Path(final_path + ".asm").resolve()
#
#     try:
#         with open(path, "w") as f:
#             f.write(rendered)
#     except FileNotFoundError:
#         _log.critical(f"Could not write to {path}. Exiting.")
#         raise SystemExit
#
#     _log.info(f"Generated .asm file at {path}")
#
#
# def main():
#     if not sys.argv[1:]:
#         sys.argv.append("-h")
#
#
#     args = sys.argv[1:]
#
#     options = "hi:A:a:d:m:f:o:D:"
#     long_options = [
#         "help",
#         "input",
#         "Address_offset",
#         "asc_output",
#         "dat_output",
#         "mem_output",
#         "mif_output",
#         "output",
#         "Decompile"
#     ]
#
#     args, _ = getopt.getopt(args, options, long_options)
#
#     asc, dat, mem, mif, dec = None, None, None, None, None
#     address_offset = 0
#     ppath = None
#
#     for arg, val in args:
#         if arg in ("-h", "--help"):
#             print(__doc__)
#
#             raise SystemExit
#
#         if arg in ("-i", "--input"):
#             ppath = pathlib.Path(val).resolve()
#             if not ppath.exists():
#                 _log.critical(f"Could not find input file at {ppath}. Exiting.")
#                 raise SystemExit
#
#         if arg in ("-a", "--asc_output"):
#             asc = val
#
#         if arg in ("-d", "--dat_output"):
#             dat = val
#
#         if arg in ("-m", "--mem_output"):
#             mem = val
#
#         if arg in ("-f", "--mif_output"):
#             mif = val
#
#         if arg in ("-A", "--Address_offset"):
#             try:
#                 address_offset = int(val)
#             except ValueError:
#                 _log.critical("Address offset must be an integer. Exiting.")
#                 raise SystemExit
#
#         if arg in ("-o", "--output"):
#             asc = val
#             dat = val
#             mem = val
#             mif = val
#
#         if arg in ("-D", "--Decompile"):
#             dec = val
#
#     if not ppath:
#         _log.critical("No input file found. Exiting.")
#         raise SystemExit
#
#     if dec is not None and any([asc, dat, mem, mif]):
#         _log.critical("Decompile flag cannot be used with output flags. Exiting.")
#         raise SystemExit
#
#     if dec is not None:
#         return generate_dec(ppath, dec, asc, address_offset)
#
#     return generate_cli(ppath, asc, dat, mem, mif, address_offset)
#
#
# if __name__ == "__main__":
#     main()
