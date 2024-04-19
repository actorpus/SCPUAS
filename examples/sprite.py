from scp_instruction import (
    Instruction,
    REQUIRED,
    REFERENCE,
    REGISTER,
    VALUE,
    UNCHECKED,
)
import logging
import sys

instructions = {}


# instructions not inside the standard_instructions.py file will need to specify the instructions dictionary
# as the first argument to the instruction decorator, this should be a local dictionary for each file
@Instruction.create(instructions)
# double underscore for .sprite as the final instruction name
class __sprite:
    image = UNCHECKED | REQUIRED

    @staticmethod
    def compile(image):
        image = image.strip('"').strip().split("\n")

        if len(image) != 5:
            logging.critical("Invalid image size, must be 3x5")
            raise SystemExit

        image = [i.replace(' ', '').replace('\t', '') for i in image]

        if any(len(row) != 3 for row in image):
            logging.critical("Invalid image size, must be 3x5")
            raise SystemExit

        image = [
            [i == "#" for i in row] for row in image
        ]

        image = [
            i[0] << 2 | i[1] << 1 | i[2]
            for i in image
        ]

        return [f'{i:04X}' for i in image]
