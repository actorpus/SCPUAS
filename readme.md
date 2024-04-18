# SCPUAS
(scoopus, skuːpʌs)

A linker/assembler/emulator primarily designed for the [simple cpu](http://simplecpudesign.com/), although it can easily be configured

Made primarily to allow for easier modification than the original provided assembler.
All instructions are now stored in one central place allowing for easy expansion and 
actually assembling the assembly into a token stream allows for adding extra file formats with one function.

check instructions.py for the instruction set!

### Notes from the original assembler:
- ~~The instruction jumpu was removed~~ ITS BACK BABY
- register operating instructions are now named with an 'r' at the end, e.g. 'add RA RB' -> 'addr RA RB'
- This assembler does not support the assembly language for the v1 processor, it is designed for v1d, it still works but instructions like 'move 0x01' will need to be replaced with 'move RA 0x01'
- Labels are now called roots, this is because they will (eventually) also be used for OO style data classes
- Numbers can now be represented in decimal, binary, hexadecimal or octal (why not (: )
- data can be saved with .data, this accepts all forms of numbers and references to roots
- .chr saves the ascii value of a character
- .str saves the ascii values of a string (not terminated)
- .strn saves the ascii values of a string (null terminated)
- -a flag was replaces with -A flag
- -o flag still works or use -a:d:m:f: for specific output types
- `#` and `#/ ... /#` are used for comments
- `\n` ` ` and `,` are used as delimiters, they can be escaped with `\ ` for naming. (automatically escaped in comments)

## Todo:
- [x] Add support for comments (# and #/ ... /#)
- [x] Reimplement entire original assembler
- [x] ^ Add in option to use start address location (-A)
- [x] ^ Patch in -o option to use all outputs (backwards compatibility)
- [x] ^ Add in .data (will probably include .int .char .str ...)
- [x] ^ add registers to the instruction set
- [x] Add assembler instructions (alias)
- [ ] Add file linking / importing
- [ ] Add an emulator ~
- [ ] Add in a disassembler
- [ ] Add support for [1d's frame buffer and sprites](http://simplecpudesign.com/simple_cpu_v1d_pong/index.html)

## Notes to self:
-import and -include should be different.
-import should take the selected file and insert it into the current file at
the location of the import statement.
-include should take the selected file and insert it into the current file at
the end of the token stream.
Difference only important for files with code vs files with functions of code.
-import should only include the 'start' root


-----
Feel free to contribute, all pr's are appreciated.
This project is fully approved by [mike](mailto:mike@simplecpudesign.com) (the creator of the simple cpu)

[SCPUAS](https://github.com/actorpus/SCPUAS) by [Alex](https://github.com/actorpus) is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0)
