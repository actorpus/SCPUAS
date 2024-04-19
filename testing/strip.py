"""
Hours crying: 5
"""

with open("code.asm") as file:
    code = file.read()

new_code = ""

for char in code:
    if char.isascii() and ord(char) not in [255, 254, 0]:
        new_code += char

for _ in range(10):
    new_code = new_code.replace("\n\n", "\n")

new_code = new_code.replace("\t", "    ")
new_code = new_code.replace("load RA", "load")
new_code = new_code.replace("store RA", "store")
new_code = new_code.replace("addm RA", "addm")
new_code = new_code.replace("subm RA", "subm")
new_code = new_code.replace("jump RA", "jump")
new_code = new_code.replace("jumpz RA", "jumpz")
new_code = new_code.replace("jumpnz RA", "jumpnz")
new_code = new_code.replace("call RA", "call")

with open("code.asm", "w") as file:
    file.write(new_code)
