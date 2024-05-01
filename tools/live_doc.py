import sys
import time

sys.path.append(".")

import standard_instructions
import pathlib

REQUIRED = 1
REFERENCE = 2
REGISTER = 4
VALUE = 8
UNCHECKED = 16

overwrite_right = ("@c▀   \n"
                   "@n┌───")

overwrite_left = ("@c▀   \n"
                  "@n┐   ")

passthrough = ("@c│   \n"
               "@n────")

split_right = ("@c│..@s  \n"
               "@g╠@n─.──")

split_left = ("@c│ .  \n"
              "@g╣@s  ")

standard = ("@c│   \n"
            "@c│   ")


def render_template(
        template,

        # three color options
        color, new="", generated="",

        # symbol for splitting / combining
        symbol=" "
):
    if not new:
        new = color

    if not generated:
        generated = color

    if symbol == ' ':
        template = template.replace("╣", "┤").replace("╠", "├")

    template = template.replace(".", "")
    template = template.replace("@c", color)
    template = template.replace("@n", new)
    template = template.replace("@g", generated)
    template = template.replace("@s", f"{generated}{symbol}")

    return template.split("\n")


def render(swaps, padding):
    output = ""

    colors = {
        "PC": "\033[34m",
        "RA": "\033[31m",
        "RB": "\033[32m",
        "RC": "\033[33m",
        "RD": "\033[36m",
        "MEM": "\033[35m",
    }

    lcv = list(colors.keys())

    unused_colors = [
        "\033[37m",
    ]

    all_colors = list(colors.values()) + unused_colors

    output += ''.join(f"{c}{k:4}" for k, c in colors.items() if k != "MEM") + "\033[0m\n"
    output += "   ".join([f"{v}│\033[0m" for k, v in colors.items() if k != "MEM"]) + "\n"

    for frm, to, gen, sym, ext, extra in swaps:
        ren = []

        for sel in list(colors.keys())[:-1]:
            left_ = split_left if gen else overwrite_left
            right_ = split_right if gen else overwrite_right
            color_ = colors[sel]
            new_ = colors[frm]
            generated_ = unused_colors[0] if gen else new_

            if frm == sel:
                if lcv.index(to) < lcv.index(sel):
                    ren.append(render_template(split_left, color_, color_))
                else:
                    ren.append(render_template(split_right, color_, color_))

            elif to == sel:
                if lcv.index(frm) < lcv.index(sel):
                    ren.append(render_template(left_, color_, new_, generated_, sym))
                else:
                    ren.append(render_template(right_, color_, new_, generated_, sym))

            elif lcv.index(to) < lcv.index(sel) < lcv.index(frm) or lcv.index(to) > lcv.index(sel) > lcv.index(frm):
                ren.append(render_template(passthrough, color_, new_))

            else:
                ren.append(render_template(standard, color_))

        for _ in range(extra):
            output += "   ".join([f"{v}│\033[0m" for k, v in colors.items() if k != "MEM"]) + "\n"

        if gen:
            colors[to] = unused_colors.pop(0)

        else:
            colors[to] = new_

        unused_colors = list(set(all_colors) - set(colors.values()))

        colors["MEM"] = unused_colors[0]

        unused_colors = list(set(all_colors) - set(colors.values()))

        output += '\n'.join(map(lambda x: ''.join(x), zip(*ren))) + ext + '\033[0m\n'
        # output += ("  ".join([f"{v}{k}\033[0m" for k, v in colors.items()]) +
        #            "   " +
        #            " ".join([f"{v}#\033[0m" for v in unused_colors]) + "\n")

    for _ in range(padding):
        output += "   ".join([f"{v}│\033[0m" for k, v in colors.items() if k != "MEM"]) + "\n"

    return output


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


def ansii_length(string):
    reading = True
    count = 0

    for char in string:
        if char == "\033":
            reading = False
            continue

        if not reading:
            if char == "m":
                reading = True
            continue

        count += 1

    return count


def to_swap(padding, instruction, args, *, rtl=None):
    if rtl is None:
        rtl = standard_instructions.instructions[instruction].__rtl__

    for _ in range(len(args)):
        rtl = rtl.replace(f"{{{_}}}", args[_])

    if rtl.count("\n") > 0:
        rtls = rtl.split("\n")
        outs = []
        push = -1

        for _ in rtls:
            print(_)
            if "<-" not in _:
                push += 1
                continue

            _ = to_swap(padding, instruction, args, rtl=_.strip())

            if type(_) == int:
                push += _
                continue

            outs.append(_)
            push += 1

        return outs[0][0], outs[0][1], outs[0][2], outs[0][3], ', '.join(_[4] if _[3] == " " else f'\'{_[4]} ({_[3]})\'' for _ in outs), push

        # return out[0], out[1], out[2], out[3], out[4], push

    left, right = rtl.split(" <- ")
    sym = ""

    if '+' in right:
        extra, right = right.split(" + ")
        if extra != left:
            return rtl.count("\n") + 1
        sym = "+"

    if '-' in right:
        extra, right = right.split(" - ")
        if extra != left:
            return rtl.count("\n") + 1
        sym = "-"

    if '&' in right:
        extra, right = right.split(" & ")
        if extra != left:
            return rtl.count("\n") + 1
        sym = "&"

    if '|' in right:
        extra, right = right.split(" | ")
        if extra != left:
            return rtl.count("\n") + 1
        sym = "|"

    if '^' in right:
        extra, right = right.split(" ^ ")
        if extra != left:
            return rtl.count("\n") + 1
        sym = "^"

    mem = ""

    if left.startswith("M["):
        mem = left
        left = "MEM"

    if right.startswith("M["):
        mem = right
        right = "MEM"

    if left not in ["PC", "RA", "RB", "RC", "RD", "MEM"]:
        return rtl.count("\n") + 1

    if right not in ["PC", "RA", "RB", "RC", "RD", "MEM"] and mem:
        return rtl.count("\n") + 1

    if right not in ["PC", "RA", "RB", "RC", "RD", "MEM"]:
        mem = right
        right = "MEM"

    if right == "MEM":
        mem = f"< {mem}"

    if left == "MEM":
        mem = f"> {mem}"

    return (right, left, bool(sym), sym.rjust(1, ' '), mem, padding)


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

                print(f"{instruction.__doc__}")

                lines = lines[line_i - 4:line_i + 5]
                output = "\n\n\n"

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
                        output += f"\033[1;31m{i + line_i - 3:03} \033[0;31m│ \033[97m{print_line}{' ' * (42 - len(part_line))} \033[31m│\033[0m {rtl[0]}\n"

                        for rtl_line in rtl[1:]:
                            output += "    \033[31m│                                          \033[31m│\033[0m " + rtl_line + "\n"

                        output += "    │                                          │ \n"

                        continue

                    output += f"{i + line_i - 3:03} │ {print_line.rstrip()}{' ' * (40 - len(part_line))} │ {rtl[0]}\n"

                    output += "    │                                          │ \n"

                    for rtl_line in rtl[1:]:
                        output += "    │                                          │ " + rtl_line + "\n"

                output = "\n".join([f"{_}{' ' * (70 - ansii_length(_))} ║ " for _ in output.split("\n")])

                try:
                    swaps = []

                    padding = 0

                    for line in lines:
                        line = line.strip()

                        if ':' in line:
                            padding += 2
                            continue

                        if not line:
                            padding += 2
                            continue

                        inst, *args = line.split("#")[0].split(" ")
                        args = list(filter(lambda x: x and x[0] != '-', args))

                        if inst not in standard_instructions.instructions:
                            padding += 2
                            continue

                        if '__rtl__' not in standard_instructions.instructions[inst].__dict__:
                            padding += 2
                            continue

                        # if standard_instructions.instructions[inst].__rtl__.count("\n") != 0:
                        #     padding += standard_instructions.instructions[inst].__rtl__.count("\n") + 2
                        #     continue

                        if "!!" in args:
                            args.remove("!!")
                            padding += 1

                        ret = to_swap(padding, inst, args)

                        if type(ret) == int:
                            padding += ret
                            continue

                        else:
                            padding = 0

                        swaps.append(ret)

                    swaps = render(swaps, padding + 1)
                except Exception as e:
                    swaps = f"Unable to compute line graph\nError: {e}"

                if output.count("\n") > swaps.count("\n"):
                    swaps += "\n" * (output.count("\n") - swaps.count("\n"))
                else:
                    output += "\n" * (swaps.count("\n") - output.count("\n"))

                print('\n'.join(map(lambda x: '\033[0m  '.join(x) + '\033[0m', zip(output.split("\n"), swaps.split("\n")))))


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
    time.sleep(0.2)

    main(watching)
