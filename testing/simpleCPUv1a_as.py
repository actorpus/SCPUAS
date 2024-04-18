#!/usr/bin/python
import getopt
import sys
import re


###################
# INSTRUCTION-SET #
###################

# INSTR   IR15 IR14 IR13 IR12 IR11 IR10 IR09 IR08 IR07 IR06 IR05 IR04 IR03 IR02 IR01 IR00
# MOVE    0    0    0    0    X    X    X    X    K    K    K    K    K    K    K    K
# ADD     0    0    0    1    X    X    X    X    K    K    K    K    K    K    K    K
# SUB     0    0    1    0    X    X    X    X    K    K    K    K    K    K    K    K
# AND     0    0    1    1    X    X    X    X    K    K    K    K    K    K    K    K

# LOAD    0    1    0    0    X    X    X    X    A    A    A    A    A    A    A    A
# STORE   0    1    0    1    X    X    X    X    A    A    A    A    A    A    A    A
# ADDM    0    1    1    0    X    X    X    X    A    A    A    A    A    A    A    A
# SUBM    0    1    1    1    X    X    X    X    A    A    A    A    A    A    A    A

# JUMPU   1    0    0    0    X    X    X    X    A    A    A    A    A    A    A    A
# JUMPZ   1    0    0    1    X    X    X    X    A    A    A    A    A    A    A    A
# JUMPNZ  1    0    1    0    X    X    X    X    A    A    A    A    A    A    A    A
# JUMPC   1    0    1    1    X    X    X    X    A    A    A    A    A    A    A    A

#############
# FUNCTIONS #
#############


def convertData(data):
    try:
        if "0x" not in data:
            return int(data)
        else:
            return int(data, 16)
    except:
        print("Error: invalid operand (hex)")
        sys.exit(1)


################
# MAIN PROGRAM #
################


def simpleCPUv1a_as(argv):
    if len(sys.argv) <= 1:
        print("Usage: simpleCPUv1a_as.py -i <input_file.asm>")
        print("                          -o <output_file>")
        print("                          -a <address_offset>")
        print("                          -p <number_of_passes>")
        print("                          -b <byte addressable>")
        print("                          -d <debug level>")
        return

    # init variables #
    version = "2.0"
    debug = 0

    source_filename = "default.asm"
    tmp_filename = "tmp.asm"

    word_filename = "default.asc"
    high_byte_filename = "default_high.asc"
    low_byte_filename = "default_low.asc"

    mem_filename = "default.mem"
    mif_filename = "default.mif"
    data_filename = "default.dat"

    address = 0
    byte_count = 0
    byte_addressable = False

    s_config = "a:i:o:p:bd:"
    l_config = ["address", "input", "output", "pass", "byte", "debug"]

    input_file_present = False

    instruction_address = 0
    instruction_count = 0

    label_dictionary = {}

    instr_names = [
        "move",
        "add",
        "sub",
        "and",
        "load",
        "store",
        "addm",
        "subm",
        "jump",
        "jumpu",
        "jumpz",
        "jumpnz",
        "jumpc",
        ".data",
        ".addr",
    ]

    self_mod_opcodes = [
        "0000",
        "0001",
        "0010",
        "0011",
        "0100",
        "0101",
        "0110",
        "0111",
        "1000",
        "1001",
        "1010",
        "1011",
        "1100",
        "1101",
        "1110",
        "1111",
    ]

    # Assembler Mode
    # Mode = 0 : full function, normal two pass
    # Mode = 1 : first pass only, generate tmp.asm file
    # Mode = 2 : second pass only, process "tmp.asm" file

    mode = 0

    # capture commandline options #
    try:
        options, remainder = getopt.getopt(sys.argv[1:], s_config, l_config)
    except getopt.GetoptError as m:
        print("Error: ", m)
        sys.exit(1)

    # extract options #
    for opt, arg in options:
        if opt in ("-o", "--output"):
            if ".asc" in arg:
                name = arg.split(".")
                word_filename = arg
                high_byte_filename = name[0] + "_high_byte.asc"
                low_byte_filename = name[0] + "_low_byte.asc"
            elif ".dat" in arg:
                data_filename = arg
            elif ".mem" in arg:
                mem_filename = arg
            else:
                word_filename = arg + ".asc"
                high_byte_filename = arg + "_high_byte.asc"
                low_byte_filename = arg + "_low_byte.asc"
                data_filename = arg + ".dat"
                mem_filename = arg + ".mem"
                mif_filename = arg + ".mif"
        elif opt in ("-i", "--input"):
            input_file_present = True
            if ".asm" in arg:
                source_filename = arg
            else:
                source_filename = arg + ".asm"
        elif opt in ("-a", "--address"):
            address = int(arg)
        elif opt in ("-p", "--pass"):
            mode = int(arg)
        elif opt in ("-b", "--byte"):
            byte_addressable = True
        elif opt in ("-d", "--debug"):
            debug = int(arg)

    # exit if no input file present #
    if input_file_present:

        # open files #
        try:
            source_file = open(source_filename, "r")
        except IOError:
            print("Error: Input file does not exist.")
            sys.exit(1)

        try:
            word_file = open(word_filename, "w")
            high_byte_file = open(high_byte_filename, "w")
            low_byte_file = open(low_byte_filename, "w")
            mem_file = open(mem_filename, "w")
            data_file = open(data_filename, "w")
            mif_file = open(mif_filename, "w")
            tmp_file = open(tmp_filename, "w")
        except IOError:
            print("Error: Could not open output files")
            sys.exit(1)

        # scan through code, count instruction, check opcodes
        # and identify labels and assign addresses.

        if mode != 2:
            instruction_address = address

            while True:
                line = source_file.readline()
                line = re.sub("#", "# ", line.lower())
                line = re.sub("\s+", " ", line)

                if line == "":
                    break

                if len(line) > 1 and line[0] == " ":
                    line = line[1:]

                if line[0] == "#" or line[0] == " ":
                    continue

                if ".addr" in line:
                    instruction_address = convertData(line.split()[1])
                    continue

                if ":" in line:
                    key = re.sub(":.$", "", line)
                    if key in label_dictionary:
                        print("Error: duplicate labels")
                        sys.exit(1)
                    else:
                        label_dictionary[key] = instruction_address
                else:
                    words = line.split(" ")
                    if words[0] in instr_names:
                        if byte_addressable:
                            instruction_address += 2
                        else:
                            instruction_address += 1
                    else:
                        print("Error: invalid instruction")
                        sys.exit(1)

            if debug > 0:
                divider = "|"
                print(" ")
                print("LABEL            |      ADDR    ")
                print("-----------------|--------------")
                for name in label_dictionary:
                    print(f"{str(name):<12}{divider:^12}{str(label_dictionary[name])}")
                print(" ")

            # replace lables with addresses, write code to tmp_file

            source_file.seek(0)
            instruction_address = address

            while True:
                line = source_file.readline()
                line = re.sub("#", "# ", line.lower())
                line = re.sub("\s+", " ", line)

                if line == "":
                    break

                if len(line) > 1 and line[0] == " ":
                    line = line[1:]

                if line[0] == "#" or line[0] == " ":
                    continue

                if ":" in line:
                    continue

                if ".addr" in line:
                    instruction_address = convertData(line.split()[1])
                    continue

                words = line.split(" ")
                outputString = str.format("{:03}", instruction_address) + " "

                for i in range(0, len(words)):
                    if words[i] in label_dictionary:
                        key = words[i]
                        outputString = outputString + " " + str(label_dictionary[key])
                    else:
                        if words[i] != "":
                            outputString = outputString + " " + words[i]

                outputString = outputString + "\n"
                tmp_file.write(outputString)
                if byte_addressable:
                    instruction_address += 2
                else:
                    instruction_address += 1

            source_file.close()
            tmp_file.close()

            # limit test #

            if byte_addressable:
                if instruction_address > 128:
                    print(
                        "Error: program bigger than memory limit: ("
                        + str(instruction_address)
                        + ")"
                    )
                    sys.exit(1)
            else:
                if instruction_address > 256:
                    print(
                        "Error: program bigger than memory limit: ("
                        + str(instruction_address)
                        + ")"
                    )
                    sys.exit(1)

        if mode == 1:
            print("Exit: first pass complete")
            sys.exit(0)

        # open TMP file #

        if mode == 2:
            try:
                tmp_file = open(source_filename, "r")
            except IOError:
                print("Error: could not output temp file")
                sys.exit(1)
        else:
            try:
                tmp_file = open(tmp_filename, "r")
            except IOError:
                print("Error: could not output temp file")
                sys.exit(1)

        instruction_count = 0
        byte_count = 0

        # write mif header to file #

        mif_file.write("DEPTH = 32;           -- The size of memory in words\n")
        mif_file.write("WIDTH = 16;           -- The size of data in bits\n")
        mif_file.write("ADDRESS_RADIX = HEX;  -- The radix for address values\n")
        mif_file.write("DATA_RADIX = BIN;     -- The radix for data values\n")
        mif_file.write("CONTENT               -- start of (address : data pairs)\n")
        mif_file.write("BEGIN\n")

        if debug > 1:
            print(
                "  ADDR   OP   RD/ADDR  RS/IMM                       |                 MACHINE CODE      "
            )
            print(
                "----------------------------------------------------|-----------------------------------"
            )

        while True:
            line = tmp_file.readline()
            line = re.sub("\s+", " ", line)

            if line == "":
                break

            words = line.split(" ")

            instr = 0
            imm = False
            abs = False
            dat = False

            # print words
            if words[0].isdigit():

                # match opcode #
                if words[1] == "move":
                    imm = True
                    instr = instr | int("0000000000000000", 2)
                elif words[1] == "add":
                    imm = True
                    instr = int("0001000000000000", 2)
                elif words[1] == "sub":
                    imm = True
                    instr = int("0010000000000000", 2)
                elif words[1] == "and":
                    imm = True
                    instr = int("0011000000000000", 2)
                elif words[1] == "load":
                    abs = True
                    instr = int("0100000000000000", 2)
                elif words[1] == "store":
                    abs = True
                    if words[3] == "" or words[3] == "#":
                        instr = int("0101000000000000", 2)
                    else:
                        print(words[3])
                        if int(words[3]) < 16 and int(words[3]) >= 0:
                            instr = int(
                                "0101"
                                + self_mod_opcodes[int(words[3])]
                                + "000000000000",
                                2,
                            )
                        else:
                            print("Error: invalid opcode")
                            print(words)
                            sys.exit(1)
                elif words[1] == "addm":
                    abs = True
                    instr = int("0110000000000000", 2)
                elif words[1] == "subm":
                    abs = True
                    instr = int("0111000000000000", 2)
                elif words[1] == "jump":
                    abs = True
                    instr = int("1000000000000000", 2)
                elif words[1] == "jumpu":
                    abs = True
                    instr = int("1000000000000000", 2)
                elif words[1] == "jumpz":
                    abs = True
                    instr = int("1001000000000000", 2)
                elif words[1] == "jumpnz":
                    abs = True
                    instr = int("1010000000000000", 2)
                elif words[1] == "jumpc":
                    abs = True
                    instr = int("1011000000000000", 2)
                elif words[1] == ".data":
                    dat = True
                    instr = int("0000000000000000", 2)
                else:
                    print("Error: invalid opcode")
                    print(words)
                    sys.exit(1)

                length = 0
                for i in range(len(words)):
                    length = length + 1
                    if words[i] == "#":
                        break

                if length < 2:
                    print("Error: invalid operand (len<2)")
                    print(words)
                    sys.exit(1)

                else:
                    data = 0
                    if (length == 4) and imm:
                        data = words[2].rstrip()
                    elif (length == 4) and abs:
                        data = words[2].rstrip()
                    elif (length == 4) and dat:
                        data = words[2].rstrip()
                    else:
                        print("Error: invalid operand (len)")
                        print(words)
                        print(length)
                        sys.exit(1)

                    operand = convertData(data)

                    if imm and (operand > 255):
                        print("Error: invalid immediate operand (>MAX)")
                        print(words)
                        sys.exit(1)

                    if abs and (operand > 255):
                        print("Error: invalid absolute operand (>MAX)")
                        print(words)
                        sys.exit(1)

                    if dat and (operand > 255):
                        print("Error: invalid data operand (>MAX)")
                        print(words)
                        sys.exit(1)

                    instr = instr | operand

                    if debug > 1:
                        divider = "|"
                        print(
                            f"{str(words):<35}{divider:^35}{str.format('{:016b}', instr)}"
                        )

                    instruction_address = int(words[0])

                    if instruction_count == 0:
                        # write start address to file #
                        word_file.write(str.format("{:04X}", instruction_address) + " ")
                        high_byte_file.write(
                            str.format("{:04X}", instruction_address) + " "
                        )
                        low_byte_file.write(
                            str.format("{:04X}", instruction_address) + " "
                        )

                    if byte_count == 16:
                        byte_count = 0
                        word_file.write("\n")
                        high_byte_file.write("\n")
                        low_byte_file.write("\n")

                        addressString = str.format("{:04X}", instruction_address) + " "
                        word_file.write(addressString)
                        high_byte_file.write(addressString)
                        low_byte_file.write(addressString)

                    data_file.write(str.format("{:04}", instruction_address) + " ")
                    bin_value = str.format("{:016b}", instr)
                    data_file.write(bin_value)
                    data_file.write("\n")

                    # update EPROM files #
                    word_file.write(str.format("{:04X}", instr) + " ")
                    high_byte_file.write(
                        str.format("{:02X}", (instr & 0xFF00) >> 8) + " "
                    )
                    low_byte_file.write(str.format("{:02X}", (instr & 0xFF)) + " ")

                    # update mem file
                    data_string = str.format("{:04X}", instr) + " "
                    mem_file.write(
                        "@" + str.format("{:04X}", (instruction_address * 2)) + " "
                    )
                    mem_file.write(
                        data_string[3]
                        + data_string[2]
                        + data_string[1]
                        + data_string[0]
                        + "\n"
                    )

                    # update mif file
                    mif_file.write(str.format("{:04X}", instruction_address) + " : ")
                    mif_file.write(str.format("{:016b}", instr) + ";\n")

                    instruction_count += 1
                    byte_count += 1

        mif_file.write("END;\n")

        # close files #
        source_file.close()
        word_file.close()
        high_byte_file.close()
        low_byte_file.close()
        mem_file.close()
        mif_file.close()
        data_file.close()
        tmp_file.close()

        if debug > 0:
            print(" ")

        # display info #
        outputString = (
            "Number of instructions: "
            + str(instruction_count)
            + ", Max address: "
            + str(instruction_address)
        )
        print(outputString)
        sys.exit(0)

    else:
        print("Error: Input file not specified")
        sys.exit(1)


if __name__ == "__main__":
    simpleCPUv1a_as(sys.argv)
