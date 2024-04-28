import time
import standard_instructions
import pathlib


watching = [
    pathlib.Path(r".\examples\emulator_test.scp").resolve()
]

old = [
    ""
]

while True:
    time.sleep(0.1)

    for watch_i in range(len(watching)):
        with open(watching[watch_i], "r") as file:
            new = file.read()

        if new == old:
            continue
        old = new

        print("\033[2J\033[H")

        if "!!" in new:
            lines = new.split("\n")
            line = list(filter(lambda x: "!!" in x, lines))[0]
            line_i = lines.index(line)
            line = line[:line.index("!!")]

            if not line:
                continue

            command = line.strip().split(" ")[0]
            indent = len(line) - len(line.lstrip())

            if command not in standard_instructions.instructions:
                print(f"Instruction '{command}' not found")
                continue

            instruction = standard_instructions.instructions[command]

            if not instruction.__doc__:
                print(f"Instruction '{command}' has no docstring")
                continue

            print(f"{instruction.__doc__}\n\n")

            lines = lines[line_i - 4:line_i + 5]

            for i, part_line in enumerate(lines):
                args = list(filter(lambda x: x and x[0] != '-' and x != '!!', part_line.split(" ")))
                inst = ""
                rtl = ""

                if part_line.strip() and part_line.strip()[0] == "#":
                    args = []

                if args:
                    inst, *args = args

                if inst in standard_instructions.instructions:
                    rtl = standard_instructions.instructions[inst].__rtl__

                for _i, arg in enumerate(args):
                    rtl = rtl.replace(f"{{{_i}}}", f"\033[32m{arg}\033[0m")

                rtl = rtl.split("\n")

                print_line = part_line

                for _i, arg in enumerate(args):
                    print_line = print_line.replace(arg, f"\033[32m{arg}\033[0m")

                if i == 4:
                    print("    |                                          | ")
                    print(f"\033[1;31m{i + line_i - 3:03} \033[0;31m| \033[97m{print_line.replace('!!', '')}\033[0m{' ' * (42 - len(part_line))} \033[31m|\033[0m {rtl[0]}")

                    for rtl_line in rtl[1:]:
                        print("    \033[31m|                                          \033[31m|\033[0m " + rtl_line)

                    print("    |                                          | ")

                    continue

                print(f"{i + line_i - 3:03} | {print_line.rstrip()}{' ' * (40 - len(part_line))} | {rtl[0]}")

                for rtl_line in rtl[1:]:
                    print("    |                                          | " + rtl_line)

        else:
            print("No instruction found, add '!!' to a line to get documentation")
