## Comments
Comments can be added to the code using `#` for single line comments 
and `#/` ... `/#` for multi-line comments.

```
# this is a single line comment

#/
This is a multi-line comment
It can span multiple lines
/#
```

the assembler will ignore ALL comments. technically block comments can be placed
in the middle of instructions but this is not advised for readability.

## Language inclusion
Python files containing new instructions can be included into the assembly using 
the `-language` system command. See `examples/extra_languages.scp` for an example.
```
-language ./new_instructions.py
```
NOTE: The standard instructions are not loaded by default, load them with 
```
-language standard
```
Language files are one of the primary replacements for M4, custom instructions can
take any arguments, included references, and can compile to any number of instructions.
A good example of this is the .sprite instruction in `examples/sprite.py`, much easier
read and write than the M4 equivalent.

New instructions can be added in a form like. Note how the inputs to the compile function
are in the correct order and have the correct names, this is important.
```python
@Instruction.create(instructions)
class _sub:
    __doc__ = "Documentation on the instruction"

    rd = REGISTER | REQUIRED
    kk = VALUE

    @staticmethod
    def compile(rd, kk=0):
        reg = rd << 2

        return f"2{reg:1x}{kk:02x}"
```
They can also be created like
```python
@Instruction.create(instructions)
@Instruction.precompute
class __halt:
    @staticmethod
    def compile(_root, *args):
        return f"""
~insert:
    jump -HALT {_root}.HALT
"""
```
The `@Instruction.precompute` decorator is used to create instructions that are not
directly mapped to a cpu instruction. These are expanded and reassembled at assembly.
precompiled instructions can either create there own roots or use the `~insert` root
to add instructions to the current root. _root is the only current passed argument
but add *args incase more are added in the future.


## Subroots / OO style references
Subroots can be created by passing a `-name` as the __first__ argument of an instruction.
These subroots can be referenced by the main root's name followed by a `.` and the subroot name.
e.g.
```
.bird:
    .data -x 0
    .data -y 0
```
These can then be used as oo style references like `load bird.x` or `store bird.y`. These can
be used for normal instructions if you need to jump to a specific instruction in a root but dont
want to clutter with to many roots.


## Static vs Dynamic roots
(Roots are normally called 'Labels' but roots works better due to there use with OO
style references)

Roots can be static or dynamic. Static roots are created normally like `name:`. Dynamic roots
are created by adding a `.` to the start of the name. Dynamic roots are __position independent__.
This means the assembler will move them around to optimize the code. This is good for roots that
only contain variables (see subroots example) as the cpu will never access them as instructions.

Is is also good practice to allow functions that are only jumped to and from to be dynamic.
e.g.
```
start:
    load 0xFC
    and RA 0b00000001
    jumpz fire
# reset is naturally accessed if the jumpz does not execute thus start and reset should be static.
reset:
    move RA 0xFC
    store 0b11111100
    jump start
# As fire will never be naturally accessed it can be made dynamic
.fire:
    move RA 0xFC
    store 0b11111100
    jump start
```
NOTE: the first root of all scp files should be `start:` (unless they are only going to be included
or imported)

NOTE: this should probably be written using subroots but this example is used in class.

NOTE: no root can contain the symbol `~`, this is reserved for the subroot system.

## File inclusions
Other .scp files can be imported into the current file using the `-include` command. This will
include all the roots from said imported file into the current file.
See `examples/importing.scp` for an example.

NOTE: A limitation on included file's are they cannot contain static roots.

## Aliases
the `-alias` system command will create a swap-at-assemble aliases. this allows for you to 
define constants  that will get replaced at assembly time. This can be done at any time.
e.g.
```
-alias PortA 0xFC

load $PortA$
and RA 0b11111110
store $PortA$
``` 
will be preprocessed into
```
load 0xFC
and RA 0b11111110
store 0xFC
```
As this happens first this can be used for code substitution snippets,
one of the default aliases is $.randomname$, this will be replaced with
the code necessary to generate a 32 char random string. see example below.

## CIC Execution (block)
Python code can be written into your assembly files, anything between
'{!' and '!}' will be executed with a python interpreter. anything printed
to stdout will be inserted into the code. Each file is given its own scope
for CIC code, this means you can create a __python__ variable at the start
of your assembly and change and use it later. 

like python CIC is executed  top to bottom. The scopes of other files are 
shared with the current scope, if you wanted to acces the variable `x` from 
an included file (`-include ./folder/module/file.scp`) you can use the 
variable `folder.module.file.x`.

NOTE: all the CIC of included files is executed at the inclusion point.

NOTE: The scope for accessing is __not__ relative to the current file, the
CIC code in `/folder/code.scp` will still have to use `folder.module.file.x`
to access the variable `x` from `./folder/module/file.scp` despite the relative
path being just `module/file.scp`. accessing variables in the root scope is
done with the root name. (normally `main`)

e.g.
```
block:
{!
for _ in range(5):
    print(f"jump {_}")
!}
```
will be preprocessed into
```
block:
    jump 0
    jump 1
    jump 2
    jump 3
    jump 4
```

## CIC Execution (inline)
These work the exact same as the block substitutions, with 2 diferences.
1. they are defined with `{{` and `}}`
2. they are evaluated not executed. rather than printing to stdout they 
return the value of the expression. This can be used for inline code.

NOTE: these can still return multiple tokens (instructions).

These are more usefully for name or value manipulation (they share the same scope as the
block substitutions so variables can be pulled into tokens)

eg.
```
jump {{_ + 1}}
```
will be preprocessed into (assuming the block substitution is also in this example so _ is
defined)
```
jump 5
```
and using pythons `:=` operator to create a variable (name) inline
```
{{ ( name := $.randomname$ ) }}: .data {{ name }}
```
will be preprocessed into (remember that `$.randomname$` is a default alias)
```
778797A: .data 778797A
```

NOTE: for all CIC, variables can not be named surrounded by `__` (e.g. `__name__`), any variable
with this naming style will be ignored by the CIC executor. The variable name `_log` is also reserved.

## Naming schema for instructions
Instructions that have a direct mapping to a cpu instruction should be named normally,
instructions that have extra functionality, or dont have a direct mapping should start
with a `.`. e.g. `move` and `.strn`.

## Default extra stuff
The default instruction set contains:
- `.chr` takes one ascii char and represents it as a number (like .data)
- `.str` takes a string and represents it as a series of chars
- `.strn` takes a string and represents it as a series of chars with a null terminator (0x0000)

There is also the default alias `$.randomname$` which will be replaced with the code to generate
a 32 char random string.

## Disassembler
It's less of a disassembler and more of an advanced output type.
Using the option -D will output ONE .asm file that is functionally identical
to the input file but using the original simple cpu assembly language.
Important note: no information is technically lost during this process
as anything that isn't directly assembly is encoded in comments, as of current
the asm_to_scp.py script does NOT use this information.

## Debug assembler
One of the options (-P or --debug_output) will output a .debug file containing
the scp assembly, the compiled instructions, and a breakdown of the compiled
instructions. mostly useful for debugging the assembler. but could be useful
for checking how custom instructions are compiled.

## Error messages (WIP)
There is a mistake in examples/importing.scp, on line 9 the ADD instruction is
missing the register argument. The error message for this is:
```
Error in instruction 'add', at line 8, in file ...\SCPUAS\examples\importing.scp

   7 | load bird.x
   8 | add 0x01
       ^^^^^^^^
   9 | addr RA RB


Was interpreted as add( 0x01 )

Documentation for instruction:
Add:
    Example            :    add RB 2
    Addressing mode    :    immediate
    Opcode             :    0001
    RTL                :    RX <- RX + ( (K7)8 || KK )
    Flags set          :    Z,C,O,P,N
```
This works by referencing the `__doc__` property of a instruction class.
NOTE: not all errors have this yet so some will still just CRITICAL:... 
in the console

# Usage
Standard usage is as follows, -i is mandatory.
at least one of -a, -d, -m, -f must be set.
-A and -R are optional.
```commandline
assembler.py

  Options:
    -h, --help                             Display this help message and exit
 *  -i, --input          <file>            Input file (required)
    -A, --Address_offset <address offset>  Set address offset
    -a, --asc_output     <filename>        Generate asc files (includes high and low)
    -d, --dat_output     <filename>        Generate dat file
    -m, --mem_output     <filename>        Generate mem file
    -f, --mif_output     <filename>        Generate mif file
    -D, --dec_output     <filename>        Generate .asm file (disassembly for original format)
    -P, --debug_output   <filename>        Generate debug file
    -o, --output         <filename>        Output file (similar to the old assembler this will output ALL types)
    -R, --Root           <project root>    Set project root (if you're initial file is not compiling from the project root)
    -v, --verbose
    -V, --super_verbose

```
Example:
```commandline
assembler.py -i examples/pong.scp 
             -A 0x1000 
             -a examples/pong
```
Will create the files `examples/pong.asc`, `examples/pong_high_byte.asc`, `examples/pong_low_byte.asc`
