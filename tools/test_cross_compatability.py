import sys
assert sys.path[1].split("\\")[-1] == "SCPUAS", "Please run this script in the SCPUAS directory"
import os

SCP = r".\examples\emulator_test.scp"

os.system("mkdir tmp")
os.system(rf".venv\Scripts\python.exe assembler.py -i {SCP} -D tmp\tmp -V -P tmp\debug -o tmp\compiler_test")
print("decompiled into asm")
print("generated compiled versions (from scp)")


os.system(rf".venv\Scripts\python.exe bin\simpleCPUv1d_as.py -i tmp\tmp.dec -o tmp\assembler_test")
print("generated assembled versions (from decompiled asm)")


for file in [
    "tmp\&_test.asc",
    "tmp\&_test.dat",
    "tmp\&_test.mem",
    "tmp\&_test.mif",
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
