start:
    load 0xFC
    and  0b00000001
    jumpz fire
reset:
    move  0xFC
    store 0b11111100
    jump start
fire:
    move  0xFC
    store 0b11111100
    jump start