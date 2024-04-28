import sys
import time
import standard_instructions
import pathlib

REQUIRED = 1
REFERENCE = 2
REGISTER = 4
VALUE = 8
UNCHECKED = 16


def colored_args(args, instruction):
    new_args = []

    if instruction is None:
        return [(f"\033[32m{arg}\033[0m", arg) for arg in args]

    defined_args = list(instruction.arguments.values())

    for i, arg in enumerate(args):
        if i >= len(defined_args):
            new_args.append(f"\033[32m{arg}\033[0m")
            continue

        arg_type = defined_args[i]
        a, b = 0, 32

        if arg_type & REQUIRED:
            a = 4  # Underline

        if arg_type & REFERENCE:
            b = 33  # Yellow

        if arg_type & REGISTER:
            b = 35  # Magenta

        if arg_type & VALUE:
            b = 36  # Cyan

        if a == 0:
            new_args.append(f"\033[0;{b}m{arg}\033[0m")
            continue

        new_args.append(f"\033[{a};{b}m{arg}\033[0m")

    return list(zip(new_args, args))


def main(watching):
    old = [
        "" for _ in watching
    ]

    while True:
        time.sleep(0.1)

        for watch_i in range(len(watching)):
            with open(watching[watch_i], "r") as file:
                new = file.read()

            if new == old[watch_i]:
                continue

            old[watch_i] = new

            print("\033[2J\033[HLiveDoc: \033[4;37mRequired\033[0;33m Reference\033[0;35m Register\033[0;36m Value\033[0m\n")

            if "!!" in new:
                lines = new.split("\n")
                line = list(filter(lambda x: "!!" in x, lines))[0]
                line_i = lines.index(line)
                line = line[:line.index("!!")]

                if not line:
                    continue

                command = line.strip().split(" ")[0]

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
                    p_inst = None

                    if part_line.strip() and part_line.strip()[0] == "#":
                        args = []

                    if args:
                        inst, *args = args

                        if '#' in args:
                            args = args[:args.index('#')]

                    if inst in standard_instructions.instructions:
                        p_inst = standard_instructions.instructions[inst]
                        rtl = p_inst.__rtl__

                    args = colored_args(args, p_inst)

                    for _i, arg in enumerate(args):
                        rtl = rtl.replace(f"{{{_i}}}", arg[0])

                    rtl = rtl.split("\n")

                    print_line = part_line.replace("!!", "")[:40]

                    for _i, arg in enumerate(reversed(args)):
                        print_line = print_line.replace(arg[1], arg[0], 1)

                    if i == 4:
                        print("    │                                          │ ")
                        print(f"\033[1;31m{i + line_i - 3:03} \033[0;31m│ \033[97m{print_line}{' ' * (42 - len(part_line))} \033[31m│\033[0m {rtl[0]}")

                        for rtl_line in rtl[1:]:
                            print("    \033[31m│                                          \033[31m│\033[0m " + rtl_line)

                        print("    │                                          │ ")

                        continue

                    print(f"{i + line_i - 3:03} │ {print_line.rstrip()}{' ' * (40 - len(part_line))} │ {rtl[0]}")

                    for rtl_line in rtl[1:]:
                        print("    │                                          │ " + rtl_line)

            else:
                print("\033[2J\033[H")
                print("No instruction found, add '!!' to a line to get documentation")

            break


if __name__ == '__main__':
    if not sys.argv[1:]:
        print("Usage: python livedoc.py <file1> <file2> ...")
        raise SystemExit

    watching = [
        pathlib.Path(_) for _ in sys.argv[1:]
    ]

    print("Watching files:", watching)
    time.sleep(1)

    main(watching)
