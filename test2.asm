#/
Designed to test the emulator
/#

start:
    load x
    add RA 1
    store x

    jump start

x:,.data 0
