### Notes from the original assembler:
- ~~The instruction jumpu was removed~~ ~~ITS BACK BABY~~ it was removed again
- register operating instructions are now named with an 'r' at the end, e.g. 'add RA RB' -> 'addr RA RB'
- This assembler does not support the assembly language for the v1 processor, it is designed for v1d, it still works but instructions like 'move 0x01' will need to be replaced with 'move RA 0x01'
- -a flag was replaces with -A flag

## Todo:
- [ ] Add file importing (diferent to including importing is like a fat alias)
- [ ] Add an emulator ~
- [x] Fix the fukin -A command to take hex aswell
- [x] ~~Add in a disassembler~~ ~~it broke lol~~ its back!
- [ ] Add support for [1d's frame buffer and sprites](http://simplecpudesign.com/simple_cpu_v1d_pong/index.html)

## Notes to self:
- import should take the selected file and insert it into the current file at
the location of the import statement.
