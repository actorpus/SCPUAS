#/
Assembler test script
Note: this will not assemble with the old assembler
/#

.data 0
# this should add it to the start of the 'start' scope.

-alias portA 0xFC
# Aliases are basic macros that are replaced at assembly
# They cannot be modified (they can be redefined) so are
# useful for constants you dont want to take memory

start:
    load portA
    # 0xFC is the memory location for port A
    and RA 0b00000001 # mask the bit for the button
    jumpz fire
reset:
    move RA portA
    store 0b11111100
    jumpu start
fire:
    move RA portA
    store 0b11111100
    jump start

.data 0x3333 1
# the 1 will be ignored

.data reset
# should be a pointer to the reset root

.chr a
# should use the ASCII value of 'a' (97) (0x61)

.str "ABC abc \" "
# 0x41 0x42 0x43 0x20 0x61 0x62 0x63 0x20 0x22 0x20
.strn "a"

se\ lf:
    # Funny property caused in the tokeniser
    # you can escape the space in the root with a backslash

    .data se\ lf

# current location

#/
_: .data _
would do the same thing
/#