### Notes from the original assembler:
- ~~The instruction jumpu was removed~~ ~~ITS BACK BABY~~ it was removed again
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
- `\n` and ` ` are used as delimiters, they can be escaped with `\ ` for naming. (automatically escaped in comments)

## Todo:
- [ ] Add file importing (diferent to including importing is like a fat alias)
- [ ] Add an emulator ~
- [ ] Fix the fukin -A command to take hex aswell
- [x] ~~Add in a disassembler~~ it broke lol
- [ ] Add in a disassembler
- [ ] Add support for [1d's frame buffer and sprites](http://simplecpudesign.com/simple_cpu_v1d_pong/index.html)

## Notes to self:
- import should take the selected file and insert it into the current file at
the location of the import statement.
- Future backwards compatibility issue: during assembly of complex data types
 if ret_roots, each complex data reference needs to be assigned its own temporary root
 so the old assembler can still assemble the code after rendering.
