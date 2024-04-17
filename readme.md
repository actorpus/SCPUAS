# SCPUAS
(scoopus, skuːpʌs)

A linker/assembler primarily designed for the [simple cpu](http://simplecpudesign.com/), although it can easily be configured

Made primarily to allow for easier modification than the original provided assembler.
All instructions are now stored in one central place allowing for easy expansion and 
actually assembling the assembly into a token stream allows for adding extra file formats with one function.

### Notes from the original assembler:
- The instruction jumpu was removed
- Numbers can now be represented in decimal, binary, hexadecimal or octal (why not (: )

## Todo:
- [ ] Add support for comments (# and #/ ... /#)
- [ ] Reimplement entire original assembler
- [ ] ^ Add in option to use start address location (-A)
- [ ] ^ Patch in -o option to use all outputs (backwards compatibility)
- [ ] ^ Add in .data (will probably include .int .char .string ...)

- [ ] Add file linking / importing
- [ ] Add an emulator 
- [ ] Add in a disassembler
- [ ] Add support for [1d's frame buffer and sprites](http://simplecpudesign.com/simple_cpu_v1d_pong/index.html)


-----
Feel free to contribute, all pr's are appreciated.
This project is fully approved by [mike](mailto:mike@simplecpudesign.com) (the creator of the simple cpu)

[SCPUAS](https://github.com/actorpus/SCPUAS) by [Alex](https://github.com/actorpus) is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0)
