"""
SCPUAS Editor

will probably fuck up any files you open with it, use with caution (and backups)

Originally was going to implement by parsing a custom buffer into the console via
the Windows API, to be platform independent left it to good old print statement
"""

import os
import sys
import pathlib
import msvcrt

try:
    os.get_terminal_size()
except OSError:
    print("Unable to detect terminal size, try changing terminals.")
    sys.exit(1)

UI_BACKGROUND = 94, 94, 94
CODE_BACKGROUND = 48, 48, 48

SELECTED_COLOR = 236, 249, 50
TEXT_COLOR = 255, 255, 255

DARK_TEXT_COLOR = 88, 88, 88


def ansii_length(string):
    reading = False
    length = 0

    for char in string:
        if char == "\033":
            reading = True
        elif reading and char in "JHmf":
            reading = False
        elif not reading:
            length += 1

    return length


def ansii_color_background(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"


def ansii_color_foreground(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


class File:
    def __init__(self, path):
        self.path = pathlib.Path(path).resolve().__str__()
        self.contents = ""

        if os.path.exists(path):
            with open(path, 'r') as f:
                self.contents = f.read()

        self.write_count = 0

        self.pointer = [0, 0]
        self.render_pointer = 0

    def read(self):
        return self.contents

    def write(self, contents):
        self.contents = contents

        self.write_count += 1

        if self.write_count % 5 == 0:
            self.save()

    def save(self):
        with open(self.path, 'w') as f:
            f.write(self.contents)


class Editor:
    def __init__(self, file):
        self._running = True
        self._file = File(file)
        self._last_input = b''

        self._command_mode = False
        self._current_command = ""
        self._command_cursor = 0

    def render_partial_file(self, width, height):
        contents = self._file.read()
        lines = contents.split("\n")

        # TODO: this start variable controls a lot of the UX with
        #       navigating the file, it should be more dynamic to
        #       not constantly be jumping around.

        start = max(0, self._file.pointer[0] - height // 4)

        end = min(len(lines), start + (height // 2))

        lines = lines[start:end]
        olines = []

        for i, l in enumerate(lines):
            olines.append(
                f"{ansii_color_background(*CODE_BACKGROUND)}{ansii_color_foreground(*DARK_TEXT_COLOR)}{i + start + 1:4} │ "
                f"{ansii_color_foreground(*TEXT_COLOR)}{l[:width - 7]}"
            )
            olines.append(
                f"{ansii_color_background(*CODE_BACKGROUND)}{ansii_color_foreground(*DARK_TEXT_COLOR)}     │ "
            )

        for _ in range(height - len(olines)):
            olines.append(f"{ansii_color_background(*CODE_BACKGROUND)}{ansii_color_foreground(*DARK_TEXT_COLOR)}     │ ")

        cursor = (self._file.pointer[0] - start) * 2, self._file.pointer[1] + 7

        return olines, cursor

    def file_navigate(self, *, left=0, right=0, up=0, down=0):
        lines = self._file.read().split("\n")

        if left:
            self._file.pointer[1] -= left
            if self._file.pointer[1] < 0:
                self.file_navigate(up=1)
                self._file.pointer[1] = len(lines[self._file.pointer[0]])

        elif right:
            self._file.pointer[1] += right
            if self._file.pointer[1] > len(lines[self._file.pointer[0]]):
                self._file.pointer[1] = 0
                self.file_navigate(down=1)

        elif up:
            self._file.pointer[0] -= up

            if self._file.pointer[0] < 0:
                self._file.pointer[0] = 0
                self._file.pointer[1] = 0

            if self._file.pointer[1] >= len(lines[self._file.pointer[0]]):
                self._file.pointer[1] = len(lines[self._file.pointer[0]])

        elif down:
            self._file.pointer[0] += down

            if self._file.pointer[0] >= len(lines):
                self._file.pointer[0] = len(lines) - 1
                self._file.pointer[1] = len(lines[self._file.pointer[0]])

            if self._file.pointer[1] >= len(lines[self._file.pointer[0]]):
                self._file.pointer[1] = len(lines[self._file.pointer[0]])

    def file_insert(self, char):
        lines = self._file.read().split("\n")

        lines[self._file.pointer[0]] = lines[self._file.pointer[0]][:self._file.pointer[1]] + char + lines[self._file.pointer[0]][self._file.pointer[1]:]
        self._file.pointer[1] += 1

        self._file.write("\n".join(lines))

    def file_delete(self):
        lines = self._file.read().split("\n")

        if self._file.pointer[1] == 0:
            if self._file.pointer[0] == 0:
                return

            self._file.pointer[0] -= 1
            self._file.pointer[1] = len(lines[self._file.pointer[0]])
            lines[self._file.pointer[0]] += lines.pop(self._file.pointer[0] + 1)

        else:
            lines[self._file.pointer[0]] = lines[self._file.pointer[0]][:self._file.pointer[1] - 1] + lines[self._file.pointer[0]][self._file.pointer[1]:]
            self._file.pointer[1] -= 1

        self._file.write("\n".join(lines))

    def file_newline(self):
        lines = self._file.read().split("\n")

        lines.insert(self._file.pointer[0] + 1, lines[self._file.pointer[0]][self._file.pointer[1]:])
        lines[self._file.pointer[0]] = lines[self._file.pointer[0]][:self._file.pointer[1]]

        self._file.pointer[0] += 1
        self._file.pointer[1] = 0

        self._file.write("\n".join(lines))

    def render(self):
        width, height = os.get_terminal_size()

        if width < 100 or height < 24:
            print("Terminal too small, please resize.")
            print("Minimum size: 100x24")
            return 

        final_lines = []

        line = "SCPUAS Editor   " + self._file.path + "   LI:" + f"{self._last_input.__repr__()[2:-1]:6}"
        line = (ansii_color_background(*UI_BACKGROUND) +
                ansii_color_foreground(*TEXT_COLOR) +
                line + " " * (width - len(line) - 5) + "I001 \033[0m")
        final_lines.append(line)

        partial_file_width = width - 40

        pfile, pcursor = self.render_partial_file(partial_file_width, height - len(final_lines) - (1 if self._command_mode else 0))
        pfile = [_ + " " * (partial_file_width - ansii_length(_)) for _ in pfile]

        final_lines += [_ + "\033[0m║" for _ in pfile]

        if self._command_mode:
            line = (ansii_color_background(*UI_BACKGROUND) +
                    ansii_color_foreground(*TEXT_COLOR) +
                    ":" + self._current_command)
            final_lines.append(line)

        final_output = "\033[J\033[H"
        for line in final_lines:
            final_output += line + " " * (width - ansii_length(line))

        final_output += "\033[0m"

        if self._command_mode:
            final_output += f"\033[{height};{self._command_cursor + 2}f"
        else:
            final_output += f"\033[{pcursor[0] + 2};{pcursor[1] + 1}f"

        print(final_output, end="", flush=True)

    def handle_command(self):
        if self._current_command == "wq" or self._current_command == "q":
            self._running = False

        if self._current_command == "w":
            self._file.save()

        if self._current_command == ":":
            self.file_insert(":")

        self._command_mode = False
        self._current_command = ""
        self._command_cursor = 0

    def handle_input(self):
        char = msvcrt.getch()
        self._last_input = char

        if char == b'\x1b':
            self._running = False

        elif char == b'\x08':
            if self._command_mode:
                self._current_command = self._current_command[:self._command_cursor - 1] + self._current_command[self._command_cursor:]
                self._command_cursor = max(0, self._command_cursor - 1)
            else:
                self.file_delete()

        elif char == b'\xe0':
            # special key
            char = msvcrt.getch()
            self._last_input += char

            if char == b'H':
                if not self._command_mode:
                    self.file_navigate(up=1)

            elif char == b'P':
                if not self._command_mode:
                    self.file_navigate(down=1)

            elif char == b'K':
                if self._command_mode:
                    self._command_cursor = max(0, self._command_cursor - 1)
                else:
                    self.file_navigate(left=1)

            elif char == b'M':
                if self._command_mode:
                    self._command_cursor = min(len(self._current_command), self._command_cursor + 1)
                else:
                    self.file_navigate(right=1)

            elif char == b'S':
                self.file_navigate(right=1)
                self.file_delete()

            elif char == b'I':
                _, height = os.get_terminal_size()
                self.file_navigate(up=height - 2)

            elif char == b'Q':
                _, height = os.get_terminal_size()
                self.file_navigate(down=height - 2)

        elif char == b'\r':
            if self._command_mode:
                self.handle_command()
            else:
                self.file_newline()

        # handle differently bc 4 spaces rule
        elif char == b'\t':
            if self._command_mode:
                self._current_command = self._current_command[:self._command_cursor] + "    " + self._current_command[self._command_cursor:]
                self._command_cursor += 4

            else:
                self.file_insert(" ")
                self.file_insert(" ")
                self.file_insert(" ")
                self.file_insert(" ")

        elif char == b':':
            if self._command_mode:
                self._current_command = self._current_command[:self._command_cursor] + ":" + self._current_command[self._command_cursor:]
                self._command_cursor += 1
            else:
                self._command_mode = True

        elif char[0] in range(32, 127):
            if self._command_mode:
                self._current_command = self._current_command[:self._command_cursor] + char.decode() + self._current_command[self._command_cursor:]
                self._command_cursor += 1

            else:
                self.file_insert(char.decode())

        else:
            ...

    def run(self):
        self.render()

        while self._running:
            self.handle_input()
            self.render()

        self._file.save()

        if sys.platform == "win32":
            os.system("cls")

        else:
            print("Unknown platform, please fix :)")

        print()
        print("File saved")
        print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python editor.py <file>")
        sys.exit(1)

    file = sys.argv[1]

    editor = Editor(file)
    editor.run()
