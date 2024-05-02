import os
assert os.getcwd().split("\\")[-1] == "SCPUAS", "Please run this script in the SCPUAS directory"
import sys


SCP = r".\examples\emulator_test.scp"

os.system("mkdir tmp")
files = os.listdir("tmp")

for file in files:
    os.remove(f"tmp\\{file}")
    print(f"Removed {file}")


os.system(rf".venv\Scripts\python.exe assembler.py -i {SCP} -D tmp\tmp -V -P tmp\debug -o tmp\compiler_test")
print("decompiled into asm")
print("generated compiled versions (from scp)")


os.system(rf".venv\Scripts\python.exe bin\simpleCPUv1d_as.py -i tmp\tmp.dec -o tmp\assembler_test")
print("generated assembled versions (from decompiled asm)")


for file in [
    r"tmp\&_test.asc",
    r"tmp\&_test.dat",
    r"tmp\&_test.mem",
    r"tmp\&_test.mif",
]:
    print(f"Checking {file.replace('&', 'compiler')} and {file.replace('&', 'assembler')}")

    with open(file.replace("&", "compiler"), "r") as f:
        compiler = f.read()

    with open(file.replace("&", "assembler"), "r") as f:
        assembler = f.read()

    if compiler != assembler:
        print(f"Files {file.replace('&', 'compiler')} and {file.replace('&', 'assembler')} are different")
        break

else:
    print("All files are equal! :D")
