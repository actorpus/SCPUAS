# SCPUAS
(scoopus, skuːpʌs)

A linker/assembler/emulator primarily designed for the [simple cpu](http://simplecpudesign.com/), although it can easily be configured

Made primarily to allow for easier modification than the original provided assembler.
All instructions are now stored in one central place allowing for easy expansion and 
actually assembling the assembly into a token stream allows for adding extra file formats with one function.

check instructions.py for the instruction set!


# Order of operations / Features examples
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

## Language inclusion
Files can be included in the assembly using the `-language` command. This will
include all instructions in the file into the current assembly. This can be used
to add new commands without changing the main instructions file. files are loaded
relative to the current working directory.

```
-language new_instructions.py
```

see /examples/extra_languages.scp for an example.
The standard instructions are not loaded by default, load them with `-language standard`

## Code substitution (block)
Python code can be written into your assembly files, anything between
'{{!' and '!}}' will be EVALUATED and replaced with the result. The scope
between multiple code substitutions is shared, so variables can be set
using pythons `(name := value)` syntax. the variable `name` can then be
used in later code snippets. As the block substitutions are done before
tokenization this can be used for programmatically generating instructions
e.g.
```
block:
{{!
for _ in range(5):
    print(f"jump {_}")
!}}
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
## Aliases
This assembler supports swap-at-assemble aliases. this allows for the user to define constants
that will get replaced at assembly time. This can be done at any time using the `-alias` assembler
command.
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
## Code Substitution (inline)
These work the exact same as the block substitutions, with 2 diferences.
1. they are defined with `{{` and `}}` rather than `{{!` and `!}}`
2. they are executed after tokenization, this means that they can only return one token.

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
and
```
{{ (_:=$.randomname$) }}: .data {{_}}
```
will be preprocessed into (remember that `$.randomname$` is a default alias)
```
778797A: .data 778797A
```

# Usage
Standard usage is as follows, -i is mandatory.
at least one of -a, -d, -m, -f must be set.
-A is optional (default to 0)
```commandline
assembler.py -i <input scp file>
             -A <address offset>
             -a <output asc files (includes high and low) (no ext)>
             -d <output dat file (no ext)>
             -m <output mem file (no ext)>
             -f <output mif file (no ext)>
```

The assembler can also be called with a -D flag,
this will assemble then re-render the code into a
standard .asm file (for the non SCPUAS users)
```commandline
assembler.py -i <input scp file>
             -D <output asm file (no ext)>
```


-----
Feel free to contribute, all pr's are appreciated.
This project is fully approved by [mike](mailto:mike@simplecpudesign.com) (the creator of the simple cpu)

[SCPUAS](https://github.com/actorpus/SCPUAS) by [Alex](https://github.com/actorpus) is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0)
