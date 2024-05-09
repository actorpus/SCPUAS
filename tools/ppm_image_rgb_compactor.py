import pathlib
import sys

if __name__ == "__main__":
    # Ensure that the user passes in a file first, before starting anything else
    if not sys.argv[1:]:
        print("Usage: python emulator.py <input .ppm image> <output .ppm image>")
        raise SystemExit

    input_file = pathlib.Path(sys.argv[1]).resolve()
    output_file = pathlib.Path(sys.argv[2]).resolve()

    with open(input_file, "r", encoding="utf-8") as file:
        data = file.readlines()
        data = [x.strip() for x in data]

    compacted: str = ""
    values: list[str] = data[4:]

    # compact every three values on one line separated by a space
    for i in range(0, len(values), 3):
        r, g, b = values[i], values[i + 1], values[i + 2]

        r = str(int(r) >> 3 << 3)
        g = str(int(g) >> 2 << 2)
        b = str(int(b) >> 3 << 3)

        compacted += f"{r} {g} {b}\n"

    final_string = "\n".join(data[:4]) + "\n" + compacted

    with open(output_file, "w", encoding="utf=8") as file:
        file.write(final_string)
