
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
- `\n` ` ` and `,` are used as delimiters, they can be escaped with `\ ` for naming. (automatically escaped in comments)
- `\n` ` ` and `,` are used as delimiters, they can be escaped with `\ ` for naming. (automatically escaped in comments)

## Todo:
- [x] Add support for comments (# and #/ ... /#)
- [x] Reimplement entire original assembler
- [x] ^ Add in option to use start address location (-A)
- [x] ^ Patch in -o option to use all outputs (backwards compatibility)
- [x] ^ Add in .data (will probably include .int .char .str ...)
- [x] ^ add registers to the instruction set
- [x] Add assembler instructions (alias)
- [ ] Add file linking / importing ~
- [ ] Add an emulator ~
- [ ] Add in a disassembler
- [x] Add support for [1d's frame buffer and sprites](http://simplecpudesign.com/simple_cpu_v1d_pong/index.html)

## Notes to self:
- import should take the selected file and insert it into the current file at
the location of the import statement.
- Future backwards compatibility issue: during assembly of complex data types
 if ret_roots, each complex data reference needs to be assigned its own temporary root
 so the old assembler can still assemble the code after rendering.
- write how to for using -name
- write how to for -include

## -name temp howto
`<instruction> -name <arguments>`
the -name has to be the first argument of an instruction it wont get added to the
instructction but will create a subroot for it reference by root.name

```
-language standard

start:
    load bird.x
    add RA 1
    store bird.x

.bird:
    .data -x 0
    .data -y 0
```

## -include temp howto
- any file imported with -include can only have non static roots (.name not name)
- -include can be anywhere but the roots will be added to the end
- -any CIC inside a included file will be ran at include time


## other shit
in CIC forbidden names inclide anything 
```
__something__
_log
```
in CIC relative paths are still calculated from project root
local paths are realtive to execition root obviously
roots cannot contain the symbol '~'








