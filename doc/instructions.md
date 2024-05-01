
# Instructions loaded from standard_instructions.py
## RTL table
| Instruction | RTL |
| --- | --- |
| [move](#move) | rd <- kk |
| [add](#add) | rd <- rd + kk |
| [sub](#sub) | rd <- rd - kk |
| [and](#and) | rd <- rd & kk |
| [load](#load) | RA <- M[aaa] |
| [store](#store) | M[aaa] <- RA |
| [addm](#addm) | RA <- RA + M[aaa] |
| [subm](#subm) | RA <- RA - M[aa] |
| [jump](#jump) | PC <- aa |
| [jumpz](#jumpz) | if Zero:<br>    PC <- aa<br>else:<br>    PC <- PC + 1 |
| [jumpnz](#jumpnz) | if not Zero:<br>    PC <- aa<br>else:<br>    PC <- PC + 1 |
| [jumpc](#jumpc) | if Carry:<br>    PC <- aa<br>else:<br>    PC <- PC + 1 |
| [call](#call) | STACK[SP]<- PC + 1<br>SP <- SP + 1<br>PC <- aa |
| [or](#or) | rd <- rd │ kk |
| [ret](#ret) | SP <- SP - 1<br>PC <- STACK[SP] |
| [mover](#mover) | rd <- rs |
| [loadr](#loadr) | rd <- M[rs] |
| [storer](#storer) | M[rs] <- rd |
| [rol](#rol) | rsd <- ( rsd(14:0) ││ rsd(15) ) |
| [ror](#ror) | rsd <- ( rsd(0) ││ rsd(15:1) ) |
| [addr](#addr) | rd <- rd + rs |
| [subr](#subr) | rd <- rd - rs |
| [andr](#andr) | rd <- rd & rs |
| [orr](#orr) | rd <- rd │ rs |
| [xorr](#xorr) | rd <- rd ^ rs |
| [asl](#asl) | rd <- ( rd(14:0) ││ 0 ) |
| [.data](#.data) | Unknown |
| [.chr](#.chr) | Unknown |
| [.str](#.str) | Unknown |
| [.strn](#.strn) | Unknown |
| [.halt](#.halt) | PC <- PC |      
## Instructions
### move
 ```
Move:
    Example            :    move RA 1
    Addressing mode    :    immediate
    Opcode             :    0000
    RTL                :    RX <- ( (K7)8 || KK )
    Flags set          :    None
    
```
### add
 ```
Add:
    Example            :    add RB 2
    Addressing mode    :    immediate
    Opcode             :    0001
    RTL                :    RX <- RX + ( (K7)8 || KK )
    Flags set          :    Z,C,O,P,N
    
```
### sub
 ```
Sub:
    Example            :    sub RC 33
    Addressing mode    :    immediate
    Opcode             :    0010
    RTL                :    RX <- RX - ( (K7)8 || KK )
    Flags set          :    Z,C,O,P,N
    
```
### and
 ```
And:
    Example            :    and RD 4
    Addressing mode    :    immediate
    Opcode             :    0011
    RTL                :    RX <- RX & ( (0)8 || KK )
    Flags set          :    Z,C,O,P,N
    
```
### load
 ```
Load:
    Example            :    load 123
    Addressing mode    :    absolute
    Opcode             :    0100
    RTL                :    RA <- M[AAA]
    Flags set          :    None
    
```
### store
 ```
Store:
    Example            :    store 234
    Addressing mode    :    absolute
    Opcode             :    0101
    RTL                :    M[AAA] <- RA
    Flags set          :    None
    
```
### addm
 ```
Add Memory:
    Example            :    addm 345
    Addressing mode    :    absolute
    Opcode             :    0110
    RTL                :    RA <- RA + M[AAA]
    Flags set          :    Z,C,O,P,N
    
```
### subm
 ```
Sub Memory:
    Example            :    subm RA 456
    Addressing mode    :    absolute
    Opcode             :    0111
    RTL                :    RA <- RA - M[AAA]
    Flags set          :    Z,C,O,P,N
    
```
### jump
 ```
Jump:
    Example            :    jump 200
    Addressing mode    :    direct
    Opcode             :    1000
    RTL                :    PC <- AAA
    Flags set          :    None
    
```
### jumpz
 ```
Jump Zero:
    Example            :    jumpz 201
    Addressing mode    :    direct
    Opcode             :    1001
    RTL                :    IF Z=1 THEN PC <- AAA ELSE PC <- PC + 1
    Flags set          :    None
    
```
### jumpnz
 ```
Jump Not Zero:
    Example            :    jumpnz 202
    Addressing mode    :    direct
    Opcode             :    1010
    RTL                :    IF Z=0 THEN PC <- AAA ELSE PC <- PC + 1
    Flags set          :    None
    
```
### jumpc
 ```
Jump Carry:
    Example            :    jumpc 203
    Addressing mode    :    direct
    Opcode             :    1011
    RTL                :    IF C=1 THEN PC <- AAA ELSE PC <- PC + 1
    Flags set          :    None
    
```
### call
 ```
Call:
    Example            :    call 300
    Addressing mode    :    direct
    Opcode             :    1100
    RTL                :    STACK[SP]<- PC + 1
                       :    SP <- SP + 1
                       :    PC <- AAA
    Flags set          :    None
    
```
### or
 ```
Or:
    Example            :    or ra 10
    Addressing mode    :    immediate
    Opcode             :    1101
    RTL                :    RX <- RX | ( (0)8 || KK )
    Flags set          :    Z,C,O,P,N
    
```
### ret
 ```
Return:
    Example            :    ret
    Addressing mode    :    direct
    Opcode             :    1111 + 0000
    RTL                :    SP <- SP - 1    
                       :    PC <- STACK[SP]
    Flags set          :    None
    
```
### mover
 ```
Move (Register):
    Example            :    move ra rb
    Addressing mode    :    register
    Opcode             :    1111 + 0001
    RTL                :    RX <- RY
    Flags set          :    None
    
```
### loadr
 ```
Load (Register):
    Example            :    load ra (rb)
    Addressing mode    :    register indirect
    Opcode             :    1111 + 0010
    RTL                :    RX <- M[RY]
    Flags set          :    None
    
```
### storer
 ```
Store (Register):
    Example            :    store rb (rc)
    Addressing mode    :    register indirect
    Opcode             :    1111 + 0011
    RTL                :    M[RY] <- RX
    Flags set          :    None
    
```
### rol
 ```
Rotate Left:
    Example            :    rol rb
    Addressing mode    :    register
    Opcode             :    1111 + 0100
    RTL                :    RX <- ( RX(14:0) || RX(15) )
    Flags set          :    Z,C,O,P,N
    
```
### ror
 ```
Rotate Right:
    Example            :    ror RB
    Addressing mode    :    register
    Opcode             :    1111 + 0101
    RTL                :    RX <- ( RX(0) || RX(15:1) )
    Flags set          :    Z,C,O,P,N
    
```
### addr
 ```
Add (Register):
    Example            :    add RA RB
    Addressing mode    :    register
    Opcode             :    1111 + 0110
    RTL                :    RX <- RX + RY
    Flags set          :    Z,C,O,P,N
    
```
### subr
 ```
Sub (Register):
    Example            :    sub RA RB
    Addressing mode    :    register
    Opcode             :    1111 + 0111
    RTL                :    RX <- RX - RY
    Flags set          :    Z,C,O,P,N
    
```
### andr
 ```
And (Register):
    Example            :    and ra rb
    Addressing mode    :    register
    Opcode             :    1111 + 1000
    RTL                :    RX <- RX & RY
    Flags set          :    Z,C,O,P,N
    
```
### orr
 ```
Or (Register):
    Example            :    or ra rb
    Addressing mode    :    register
    Opcode             :    1111 + 1001
    RTL                :    RX <- RX | RY
    Flags set          :    Z,C,O,P,N
    
```
### xorr
 ```
Xor (Register):
    Example            :    xor ra rb
    Addressing mode    :    register
    Opcode             :    1111 + 1010
    RTL                :    RX <- RX ^ RY    
    Flags set          :    Z,C,O,P,N
    
```
### asl
 ```
Arithmetic Shift Left:  
    Example            :    asl rb
    Addressing mode    :    register
    Opcode             :    1111 + 1011
    RTL                :    RX <- ( RX(14:0) || 0 )
    Flags set          :    Z,C,O,P,N
    
```
### .data
 ```
Unknown
```
### .chr
 ```
Unknown
```
### .str
 ```
Unknown
```
### .strn
 ```
Unknown
```
### .halt
 ```
Unknown
```
