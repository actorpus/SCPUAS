r"""
A simple script that attempts to convert standard simplecpu .asm files
to .scp files.

If not on windows you will need to compile your own m4 binary.

Usage:
    python .\asm_to_scp.py *<files> > file.scp

    e.g.
    python .\asm_to_scp.py .\pong.m4 .\pong.asm > .\converted_pong.scp

Hours crying: 7
"""

import os
import sys
import subprocess


def swap(name):
    with open(name) as file:
        code = file.read()

    new_code = ""

    for char in code:
        if char.isascii() and ord(char) not in [255, 254, 0]:
            new_code += char

    new_code = new_code.replace("\r", "")

    for _ in range(10):
        new_code = new_code.replace("\n\n\n", "\n\n")

    # help deal with the crap that m4 causes
    while new_code.startswith("\n"):
        new_code = new_code[1:]

    new_code = new_code.replace("\t", "    ")

    # swap all register commands for the new versions
    for _ in "ABCD":
        for __ in "ABCD":
            new_code = new_code.replace(f"move R{_} R{__}", f"mover R{_} R{__}")
            new_code = new_code.replace(f"load R{_} (R{__})", f"loadr R{_} R{__}")
            new_code = new_code.replace(f"store R{_} (R{__})", f"storer R{_} R{__}")
            new_code = new_code.replace(f"add R{_} R{__}", f"addr R{_} R{__}")
            new_code = new_code.replace(f"sub R{_} R{__}", f"subr R{_} R{__}")
            new_code = new_code.replace(f"and R{_} R{__}", f"andr R{_} R{__}")
            new_code = new_code.replace(f"or R{_} R{__}", f"orr R{_} R{__}")
            new_code = new_code.replace(f"xor R{_} R{__}", f"xorr R{_} R{__}")

    # replace dead RA calls
    new_code = new_code.replace("load RA", "load")
    new_code = new_code.replace("store RA", "store")
    new_code = new_code.replace("addm RA", "addm")
    new_code = new_code.replace("subm RA", "subm")
    new_code = new_code.replace("jump RA", "jump")
    new_code = new_code.replace("jumpz RA", "jumpz")
    new_code = new_code.replace("jumpnz RA", "jumpnz")
    new_code = new_code.replace("call RA", "call")

    # new_code = new_code.replace(f"asl R{_} R{__}", f"aslr R{_} R{__}")

    # search for runs of .data commands
    runs = []
    in_run = False

    new_code = new_code.split("\n")

    for i, line in enumerate(new_code):
        line = line.strip()

        if line.startswith(".data") and int(
            line.split(" ")[1].replace("0x", ""), 16
        ) in range(32, 128):
            if not in_run:
                in_run = True
                runs.append([(i, chr(int(line.split(" ")[1].replace("0x", ""), 16)))])
            else:
                runs[-1].append((i, chr(int(line.split(" ")[1].replace("0x", ""), 16))))

        elif (
            in_run
            and line.startswith(".data")
            and int(line.split(" ")[1].replace("0x", ""), 16) == 0
        ):
            in_run = False
            runs[-1].append((i, "\x00"))

        else:
            in_run = False

    runs = [run for run in runs if len(run) > 1]

    for run in runs:
        index = run[0][0]
        spacing = new_code[index].split(".data")[0]
        word = "".join([char for _, char in run])

        if run[-1][1] == "\x00":
            inst = ".strn"
            word = word[:-1]
        else:
            inst = ".str"

        new_code[index] = f'{spacing}{inst} "{word}"'

        for i, _ in run[1:]:
            # flag, remove line
            new_code[i] = "\x00\x00"

    # force one space after comments
    # and empty line above coments
    # and swap to block comments for runs >= 3
    runs = []
    in_run = False

    for i, line in enumerate(new_code):
        if line.startswith("#"):
            if len(line) == 1:
                new_code[i] = "# "
                line = "# "

            if not line[1] == " ":
                new_code[i] = "# " + line[1:]
                line = "# " + line[1:]

            if not in_run:
                in_run = True
                runs.append([(i, line)])
            else:
                runs[-1].append((i, line))

        elif line.strip(" ") == "":
            ...

        else:
            in_run = False

    comments, blocks = [run for run in runs if not len(run) > 2], [
        run for run in runs if len(run) > 2
    ]

    for run in comments:
        index = run[0][0]

        if index == 0:
            continue

        if new_code[index - 1].strip(" ") != "":
            new_code[index] = new_code[index] + "\x00\x01"

    for run in blocks:
        index = run[0][0]
        end_index = run[-1][0]

        if index == 0:
            new_code[index] = new_code[index][2:].replace("#", "-") + "\x00\x02"
        elif new_code[index - 1].strip(" ") != "\n":
            new_code[index] = new_code[index][2:].replace("#", "-") + "\x00\x04"
        else:
            new_code[index] = new_code[index][2:].replace("#", "-") + "\x00\x02"

        for i, _ in run[1:-1]:
            new_code[i] = new_code[i][2:].replace("#", "-")

        new_code[end_index] = new_code[end_index][2:].replace("#", "-") + "\x00\x03"

    code = new_code.copy()
    new_code = []

    for line in code:
        if line == "\x00\x00":
            continue

        if line.endswith("\x00\x01"):
            new_code.append("\n")
            new_code.append(line[:-2])
            continue

        if line.endswith("\x00\x02"):
            new_code.append("#/")
            new_code.append(line[:-2])
            continue

        if line.endswith("\x00\x03"):
            new_code.append(line[:-2])
            new_code.append("/#")
            continue

        if line.endswith("\x00\x04"):
            new_code.append("\n")
            new_code.append("#/")
            new_code.append(line[:-2])
            continue

        new_code.append(line)

    new_code = "\n".join(new_code)

    new_code = (
        """# Converted from .asm to .scp
-language: standard
"""
        + new_code
    )

    return new_code


if __name__ == "__main__":
    if not len(sys.argv) > 1:
        print("Usage: python asm_to_scp.py *<file> <output>.scp")
        raise SystemExit

    # call m4
    f = open(".tmp.m4.asm", "w")
    subprocess.run(["./bin/m4"] + sys.argv[1:-1], stdout=f)
    f.close()

    code = swap(".tmp.m4.asm")
    os.remove(".tmp.m4.asm")

    with open(sys.argv[-1], "w") as f:
        f.write(code)
