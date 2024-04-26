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

from scp_instruction import Instruction, REQUIRED, REGISTER, VALUE, UNCHECKED

_log = logging.getLogger("DefaultInstructions")
instructions: dict[str, Instruction] = {}


# add the following class as an instruction
@Instruction.create(instructions)
# the name of the class is the name of the instruction
# (the first _ is removed to avoid conflicts with python keywords,
#  if there is a second underscore it will be replaced with a '.')
class _move:
    __doc__ = """Move:
    Example            :    move RA 1
    Addressing mode    :    immediate
    Opcode             :    0000
    RTL                :    RX <- ( (K7)8 || KK )
    Flags set          :    None
    """

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
    __doc__ = """Add:
    Example            :    add RB 2
    Addressing mode    :    immediate
    Opcode             :    0001
    RTL                :    RX <- RX + ( (K7)8 || KK )
    Flags set          :    Z,C,O,P,N
    """

    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"1{reg:1x}{kk:02x}"


@Instruction.create(instructions)
class _sub:
    __doc__ = """Sub:
    Example            :    sub RC 33
    Addressing mode    :    immediate
    Opcode             :    0010
    RTL                :    RX <- RX - ( (K7)8 || KK )
    Flags set          :    Z,C,O,P,N
    """

    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"2{reg:1x}{kk:02x}"


@Instruction.create(instructions)
class _and:
    __doc__ = """And:
    Example            :    and RD 4
    Addressing mode    :    immediate
    Opcode             :    0011
    RTL                :    RX <- RX & ( (0)8 || KK )
    Flags set          :    Z,C,O,P,N
    """

    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"3{reg:1x}{kk:02x}"


@Instruction.create(instructions)
class _load:
    __doc__ = """Load:
    Example            :    load 123
    Addressing mode    :    absolute
    Opcode             :    0100
    RTL                :    RA <- M[AAA]
    Flags set          :    None
    """
    aaa = VALUE

    @staticmethod
    def compile(aaa=0):
        return f"4{aaa:03x}"


@Instruction.create(instructions)
class _store:
    __doc__ = """Store:
    Example            :    store 234
    Addressing mode    :    absolute
    Opcode             :    0101
    RTL                :    M[AAA] <- RA
    Flags set          :    None
    """
    aaa = VALUE

    @staticmethod
    def compile(aaa=0):
        return f"5{aaa:03x}"


@Instruction.create(instructions)
class _addm:
    __doc__ = """Add Memory:
    Example            :    addm 345
    Addressing mode    :    absolute
    Opcode             :    0110
    RTL                :    RA <- RA + M[AAA]
    Flags set          :    Z,C,O,P,N
    """
    aaa = VALUE

    @staticmethod
    def compile(aaa=0):
        return f"6{aaa:03x}"


@Instruction.create(instructions)
class _subm:
    __doc__ = """Sub Memory:
    Example            :    subm RA 456
    Addressing mode    :    absolute
    Opcode             :    0111
    RTL                :    RA <- RA - M[AAA]
    Flags set          :    Z,C,O,P,N
    """
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"7{aa:03x}"


@Instruction.create(instructions)
class _jump:
    __doc__ = """Jump:
    Example            :    jump 200
    Addressing mode    :    direct
    Opcode             :    1000
    RTL                :    PC <- AAA
    Flags set          :    None
    """
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"8{aa:03x}"


@Instruction.create(instructions)
class _jumpz:
    __doc__ = """Jump Zero:
    Example            :    jumpz 201
    Addressing mode    :    direct
    Opcode             :    1001
    RTL                :    IF Z=1 THEN PC <- AAA ELSE PC <- PC + 1
    Flags set          :    None
    """
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        logging.debug(f"Jump Zero compiling 9 {aa}")

        return f"9{aa:03x}"


@Instruction.create(instructions)
class _jumpnz:
    __doc__ = """Jump Not Zero:
    Example            :    jumpnz 202
    Addressing mode    :    direct
    Opcode             :    1010
    RTL                :    IF Z=0 THEN PC <- AAA ELSE PC <- PC + 1
    Flags set          :    None
    """
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"A{aa:03x}"


@Instruction.create(instructions)
class _jumpc:
    __doc__ = """Jump Carry:
    Example            :    jumpc 203
    Addressing mode    :    direct
    Opcode             :    1011
    RTL                :    IF C=1 THEN PC <- AAA ELSE PC <- PC + 1
    Flags set          :    None
    """
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"B{aa:03x}"


@Instruction.create(instructions)
class _call:
    __doc__ = """Call:
    Example            :    call 300
    Addressing mode    :    direct
    Opcode             :    1100
    RTL                :    STACK[SP]<- PC + 1
                       :    SP <- SP + 1
                       :    PC <- AAA
    Flags set          :    None
    """
    aa = VALUE

    @staticmethod
    def compile(aa=0):
        return f"C{aa:03x}"


@Instruction.create(instructions)
class _or:
    __doc__ = """Or:
    Example            :    or ra 10
    Addressing mode    :    immediate
    Opcode             :    1101
    RTL                :    RX <- RX | ( (0)8 || KK )
    Flags set          :    Z,C,O,P,N
    """

    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"D{reg:1x}{kk:02x}"


# XOP1 f'Exxx'


@Instruction.create(instructions)
class _ret:
    __doc__ = """Return:
    Example            :    ret
    Addressing mode    :    direct
    Opcode             :    1111 + 0000
    RTL                :    SP <- SP - 1    
                       :    PC <- STACK[SP]
    Flags set          :    None
    """

    @staticmethod
    def compile():
        # first in type FxxN
        return "F000"


@Instruction.create(instructions)
class _mover:
    __doc__ = """Move (Register):
    Example            :    move ra rb
    Addressing mode    :    register
    Opcode             :    1111 + 0001
    RTL                :    RX <- RY
    Flags set          :    None
    """
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}01"


@Instruction.create(instructions)
class _loadr:
    __doc__ = """Load (Register):
    Example            :    load ra (rb)
    Addressing mode    :    register indirect
    Opcode             :    1111 + 0010
    RTL                :    RX <- M[RY]
    Flags set          :    None
    """
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}02"


@Instruction.create(instructions)
class _storer:
    __doc__ = """Store (Register):
    Example            :    store rb (rc)
    Addressing mode    :    register indirect
    Opcode             :    1111 + 0011
    RTL                :    M[RY] <- RX
    Flags set          :    None
    """
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}03"


@Instruction.create(instructions)
class _rol:
    __doc__ = """Rotate Left:
    Example            :    rol rb
    Addressing mode    :    register
    Opcode             :    1111 + 0100
    RTL                :    RX <- ( RX(14:0) || RX(15) )
    Flags set          :    Z,C,O,P,N
    """
    rsd = REGISTER | REQUIRED

    @staticmethod
    def compile(rsd):
        value = rsd << 2

        return f"F{value:1x}04"


@Instruction.create(instructions)
class _ror:
    __doc__ = """Rotate Right:
    Example            :    ror RB
    Addressing mode    :    register
    Opcode             :    1111 + 0101
    RTL                :    RX <- ( RX(0) || RX(15:1) )
    Flags set          :    Z,C,O,P,N
    """

    rsd = REGISTER | REQUIRED

    @staticmethod
    def compile(rsd):
        value = rsd << 2

        return f"F{value:1x}05"


@Instruction.create(instructions)
class _addr:
    __doc__ = """Add (Register):
    Example            :    add RA RB
    Addressing mode    :    register
    Opcode             :    1111 + 0110
    RTL                :    RX <- RX + RY
    Flags set          :    Z,C,O,P,N
    """
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}06"


@Instruction.create(instructions)
class _subr:
    __doc__ = """Sub (Register):
    Example            :    sub RA RB
    Addressing mode    :    register
    Opcode             :    1111 + 0111
    RTL                :    RX <- RX - RY
    Flags set          :    Z,C,O,P,N
    """
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}07"


@Instruction.create(instructions)
class _andr:
    __doc__ = """And (Register):
    Example            :    and ra rb
    Addressing mode    :    register
    Opcode             :    1111 + 1000
    RTL                :    RX <- RX & RY
    Flags set          :    Z,C,O,P,N
    """
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}08"


@Instruction.create(instructions)
class _orr:
    __doc__ = """Or (Register):
    Example            :    or ra rb
    Addressing mode    :    register
    Opcode             :    1111 + 1001
    RTL                :    RX <- RX | RY
    Flags set          :    Z,C,O,P,N
    """
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}09"


@Instruction.create(instructions)
class _xorr:
    __doc__ = """Xor (Register):
    Example            :    xor ra rb
    Addressing mode    :    register
    Opcode             :    1111 + 1010
    RTL                :    RX <- RX + RY    
    Flags set          :    Z,C,O,P,N
    """
    rd = REGISTER | REQUIRED
    rs = REGISTER

    @staticmethod
    def compile(rd, rs=0):
        value = rd << 2 | rs

        return f"F{value:1x}0A"


@Instruction.create(instructions)
class _asl:
    __doc__ = """Arithmetic Shift Left:  
    Example            :    asl rb
    Addressing mode    :    register
    Opcode             :    1111 + 1011
    RTL                :    RX <- ( RX(14:0) || 0 )
    Flags set          :    Z,C,O,P,N
    """
    rd = REGISTER | REQUIRED

    @staticmethod
    def compile(rd, ):
        value = rd << 2

        return f"F{value:1x}0B"


# XOP2 f'FxxC'
# XOP3 f'FxxD'
# XOP4 f'FxxE'
# XOP5 f'FxxF'


# ASSEMBLER INSTRUCTIONS


@Instruction.create(instructions)
# __ will be replaced with '.'
class __data:
    # UNCHECKED could be anything...
    data = UNCHECKED

    @staticmethod
    def compile(data: any = None):
        if data is None:
            data = "0"

        if type(data) == str:
            data = eval(data)

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


@Instruction.create(instructions)
# precompute instructs the assembler to compile the instruction at tokenization.
# used for instructions that return multiple generated instructions (prevents
# having to load and call the compiler for used instructions at compile time)
# Use the root '~insert:' to insert the new instructions to the current root.
@Instruction.precompute
class __halt:
    @staticmethod
    def compile(_root, *args):
        return f"""
~insert:
    jump -HALT {_root}.HALT
"""


if __name__ == "__main__":
    from pprint import pprint

    pprint(instructions)
    print(instructions["move"].arguments)
    print(instructions["rol"].compile(3))
    print(instructions[".chr"].compile("A"))
    print(instructions[".strn"].compile('"Hello, World! " "'))
