#!/usr/bin/python
import getopt
import sys
import re

###################
# INSTRUCTION-SET #
###################

# INSTR   IR15 IR14 IR13 IR12 IR11 IR10 IR09 IR08 IR07 IR06 IR05 IR04 IR03 IR02 IR01 IR00  
# MOVE    0    0    0    0    RD   RD   X    X    K    K    K    K    K    K    K    K
# ADD     0    0    0    1    RD   RD   X    X    K    K    K    K    K    K    K    K
# SUB     0    0    1    0    RD   RD   X    X    K    K    K    K    K    K    K    K
# AND     0    0    1    1    RD   RD   X    X    K    K    K    K    K    K    K    K

# LOAD    0    1    0    0    A    A    A    A    A    A    A    A    A    A    A    A
# STORE   0    1    0    1    A    A    A    A    A    A    A    A    A    A    A    A
# ADDM    0    1    1    0    A    A    A    A    A    A    A    A    A    A    A    A
# SUBM    0    1    1    1    A    A    A    A    A    A    A    A    A    A    A    A

# JUMPU   1    0    0    0    A    A    A    A    A    A    A    A    A    A    A    A
# JUMPZ   1    0    0    1    A    A    A    A    A    A    A    A    A    A    A    A
# JUMPNZ  1    0    1    0    A    A    A    A    A    A    A    A    A    A    A    A
# JUMPC   1    0    1    1    A    A    A    A    A    A    A    A    A    A    A    A 

# CALL    1    1    0    0    A    A    A    A    A    A    A    A    A    A    A    A

# OR      1    1    0    1    RD   RD   X    X    K    K    K    K    K    K    K    K  -- Version 1.2
# XOP1    1    1    1    0    U    U    U    U    U    U    U    U    U    U    U    U  -- NOT IMPLEMENTED

# RET     1    1    1    1    X    X    X    X    X    X    X    X    0    0    0    0
# MOVE    1    1    1    1    RD   RD   RS   RS   X    X    X    X    0    0    0    1
# LOAD    1    1    1    1    RD   RD   RS   RS   X    X    X    X    0    0    1    0  -- REG INDIRECT
# STORE   1    1    1    1    RD   RD   RS   RS   X    X    X    X    0    0    1    1  -- REG INDIRECT   
# ROL     1    1    1    1    RSD  RSD  X    X    X    X    X    X    0    1    0    0  -- Version 1.1

# ROR     1    1    1    1    RSD  RSD  X    X    X    X    X    X    0    1    0    1  -- NOT IMPLEMENTED
# ADD     1    1    1    1    RD   RD   RS   RS   X    X    X    X    0    1    1    0  -- NOT IMPLEMENTED
# SUB     1    1    1    1    RD   RD   RS   RS   X    X    X    X    0    1    1    1  -- NOT IMPLEMENTED
# AND     1    1    1    1    RD   RD   RS   RS   X    X    X    X    1    0    0    0  -- NOT IMPLEMENTED
# OR      1    1    1    1    RD   RD   RS   RS   X    X    X    X    1    0    0    1  -- NOT IMPLEMENTED
# XOR     1    1    1    1    RD   RD   RS   RS   X    X    X    X    1    0    1    0  -- Version 1.1
# ASL     1    1    1    1    RD   RD   RS   RS   X    X    X    X    1    0    1    1  -- Version 1.2

# XOP2    1    1    1    1    RD   RD   RS   RS   X    X    X    X    1    1    0    0  -- NOT IMPLEMENTED REG INDIRECT
# XOP3    1    1    1    1    RD   RD   RS   RS   X    X    X    X    1    1    0    1  -- NOT IMPLEMENTED
# XOP4    1    1    1    1    RD   RD   RS   RS   X    X    X    X    1    1    1    0  -- NOT IMPLEMENTED REG INDIRECT
# XOP5    1    1    1    1    RD   RD   RS   RS   X    X    X    X    1    1    1    1  -- NOT IMPLEMENTED

#############
# FUNCTIONS #
#############

def convertData(data):
  try:
    if '0x' not in data:
      return int(data) 
    else:
      return int(data, 16) 
  except:
    print("Error: invalid operand (hex)")
    print(data) 
    sys.exit(1)

################
# MAIN PROGRAM #
################

def simpleCPUv1d_as(argv):

  if len(sys.argv) <= 1:
    print ("Usage: simpleCPUv1d_as.py -i <input_file.asm>")
    print ("                          -o <output_file>") 
    print ("                          -a <address_offset>")
    print ("                          -p <number_of_passes>")
    print ("                          -d <debug level>")
    return

  # init variables #
  version = '2.0'
  debug = 0
  
  source_filename = 'default.asm'
  tmp_filename = 'tmp.asm'
  word_filename = 'default.asc'
  mem_filename = 'default.mem'
  data_filename = 'default.dat' 
  mif_filename = 'default.mif' 

  address = 0
  byte_count = 0

  s_config = 'a:i:o:p:d:'
  l_config = ['address', 'input', 'output', 'pass', 'debug']

  input_file_present = False

  instruction_address = 0
  instruction_count   = 0

  label_dictionary = {}

  reg_names = ['ra', 'rb', 'rc', 'rd'];
  
  instr_names = ['move', 'add', 'sub', 'and', 'load', 'store', 'addm', 'subm',
                 'jump', 'jumpu', 'jumpz', 'jumpnz', 'jumpc', 'call', 'jr', 'ret',
				 'or', 'xor', 'rol', 'ror', 'asl', 'xop1', 'xop2', 'xop3', 'xop4', 'xop5', 
                 '.data', '.addr' ]

  # Assembler Mode
  # Mode = 0 : full function, normal two pass
  # Mode = 1 : first pass only, generate tmp.asm file
  # Mode = 2 : second pass only, process "tmp.asm" file

  mode = 0

  # capture commandline options #
  try:
    options, remainder = getopt.getopt(sys.argv[1:], s_config, l_config)
  except getopt.GetoptError as m:
    print("Error: ", m)
    return

  # extract options #
  for opt, arg in options:
    if opt in ('-o', '--output'):
      if ".asc" in arg:
        word_filename = arg
      elif ".dat" in arg:
        data_filename = arg
      elif ".mem" in arg:
        mem_filename = arg
      else:
        word_filename = arg + ".asc"
        data_filename = arg + ".dat"
        mem_filename = arg + ".mem"
        mif_filename = arg + ".mif"
    elif opt in ('-i', '--input'):
      input_file_present = True
      if ".asm" in arg:
        source_filename = arg
      else:
        source_filename = arg + ".asm"
    elif opt in ('-a', '--address'):
      address = int(arg)
    elif opt in ('-p', '--pass'):
      mode = int(arg)
    elif opt in ('-d', '--debug'):
      debug = int(arg)
	  
  # exit if no input file present # 
  if input_file_present:

    # open files #
    try:
      source_file = open(source_filename, "r")
    except IOError: 
      print("Error: Input file does not exist.")
      sys.exit(1) 

    try:
      word_file = open(word_filename, "w")
      mem_file = open(mem_filename, "w")
      data_file = open(data_filename, "w")
      mif_file = open(mif_filename, "w")
      tmp_file = open(tmp_filename, "w")
    except IOError: 
      print("Error: Could not open output files")
      sys.exit(1) 

    # scan through code, count instruction, check opcodes
	# and identify labels and link to addresses.

    if mode != 2:
      instruction_address = address
    
      while True:
        line = source_file.readline() 
        line = re.sub('#', '# ', line.lower()) 
        line = re.sub('\s+', ' ', line)

        if line == '': 
          break

        if len(line) > 1 and line[0] == ' ':
          line = line[1:]
		  
        if line[0] =='#' or line[0] ==' ':
          continue
		  
        if ".addr" in line:
          instruction_address = convertData(line.split()[1])
          continue
		  
        if ":" in line:
          key = re.sub(':.$', '', line)
          if key in label_dictionary:
            print("Error: duplicate labels")
            sys.exit(1)
          else:
            label_dictionary[key] = instruction_address
        else:
          words = line.split(' ')
          if words[0] in instr_names:	
            instruction_address += 1 		
          else:
            print("Error: invalid instruction") 
            sys.exit(1)

      if debug > 0:
        divider='|'
        print(" ")
        print("LABEL            |      ADDR    ")
        print("-----------------|--------------")
        for name in label_dictionary:
          print( f"{str(name):<12}{divider:^12}{str(label_dictionary[name])}" )
        print(" ")
		
      # replace lables with addresses, write code to tmp_file
	  
      source_file.seek(0) 
      instruction_address = address

      while True:
        line = source_file.readline() 
        line = re.sub('#', '# ', line.lower()) 
        line = re.sub('\s+', ' ', line)

        if line == '': 
          break
		
        if len(line) > 1 and line[0] == ' ':
          line = line[1:]
		  
        if line[0] =='#' or line[0] ==' ':
          continue

        if ":" in line:
          continue
		  
        if ".addr" in line:
          instruction_address = convertData(line.split()[1]) 
          continue
		  
        words = line.split(' ')	
        outputString = str.format('{:03}', instruction_address) + " "

        for i in range(0, len(words)):
          if words[i] in label_dictionary:
            key = words[i]
            outputString = outputString + " " + str(label_dictionary[key])
          else:
            if words[i] != '':
              outputString = outputString + " " + words[i]

        outputString = outputString + "\n"
        tmp_file.write( outputString )			
        instruction_address += 1 
  
      source_file.close() 
      tmp_file.close()  

      # limit test #
      if instruction_address >  4096:
        print("Error: program bigger than 4096 instruction limit")
        sys.exit(1)
		
    if mode == 1:
      print("Exit: first pass complete")
      sys.exit(0)
      
    # open TMP file #

    if mode == 2:
      try:
        tmp_file = open(source_filename, "r")
      except IOError: 
        print("Error: could not output temp file")
        sys.exit(1) 
    else:
      try:
        tmp_file = open(tmp_filename, "r")
      except IOError: 
        print("Error: could not output temp file")
        sys.exit(1) 

    instruction_count = 0
    byte_count = 0

    # write mif header to file #

    mif_file.write("DEPTH = 32;           -- The size of memory in words\n")
    mif_file.write("WIDTH = 16;           -- The size of data in bits\n")
    mif_file.write("ADDRESS_RADIX = HEX;  -- The radix for address values\n")
    mif_file.write("DATA_RADIX = BIN;     -- The radix for data values\n")
    mif_file.write("CONTENT               -- start of (address : data pairs)\n")
    mif_file.write("BEGIN\n")

    if debug > 1:
      print("  ADDR   OP   RD/ADDR  RS/IMM                       |                 MACHINE CODE      ")
      print("----------------------------------------------------|-----------------------------------")
	  
    while True:
      line = tmp_file.readline()
      line = re.sub('\s+', ' ', line)

      if line == '':
        break 

      words = line.split(' ')

      instr = 0
      imm   = False
      reg   = False
      abs   = False
      dat   = False

      #print words
      if words[0].isdigit():

        # match opcode #
        if words[1]   == "move":
          if (words[2] in reg_names) and (words[3] in reg_names):
            reg = True
            instr = int('1111000000000001', 2)

            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)
          else:
            imm = True
            if (words[2] == "ra"): 
              instr = int('0000000000000000', 2)
            elif (words[2] == "rb"):
              instr = int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words)
              sys.exit(1)
              
        elif words[1] == "add":
          if (words[2] in reg_names) and  (words[3] in reg_names):
            reg = True
            instr = int('1111000000000110', 2)

            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)
          else:
            imm = True
            if (words[2] == "ra"): 
              instr = int('0001000000000000', 2)
            elif (words[2] == "rb"):
              instr = int('0001010000000000', 2)
            elif (words[2] == "rc"):
              instr = int('0001100000000000', 2)
            elif (words[2] == "rd"):
              instr = int('0001110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

        elif words[1] == "sub":
          if (words[2] in reg_names) and  (words[3] in reg_names):
            reg = True
            instr = int('1111000000000111', 2)

            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words)
              sys.exit(1)
          else:
            imm = True
            if (words[2] == "ra"): 
              instr = int('0010000000000000', 2)
            elif (words[2] == "rb"):
              instr = int('0010010000000000', 2)
            elif (words[2] == "rc"):
              instr = int('0010100000000000', 2)
            elif (words[2] == "rd"):
              instr = int('0010110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

        elif words[1] == "and":
          if (words[2] in reg_names) and  (words[3] in reg_names):
            reg = True
            instr = int('1111000000001000', 2)

            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register")
              print(words)
              sys.exit(1)
          else:
            imm = True
            if (words[2] == "ra"): 
              instr = int('0011000000000000', 2)
            elif (words[2] == "rb"):
              instr = int('0011010000000000', 2)
            elif (words[2] == "rc"):
              instr = int('0011100000000000', 2)
            elif (words[2] == "rd"):
              instr = int('0011110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

        elif words[1] == "or":
          if (words[2] in reg_names) and  (words[3] in reg_names):
            reg = True
            instr = int('1111000000001001', 2)

            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)
          else:
            imm = True
            if (words[2] == "ra"): 
              instr = int('1101000000000000', 2)
            elif (words[2] == "rb"):
              instr = int('1101010000000000', 2)
            elif (words[2] == "rc"):
              instr = int('1101100000000000', 2)
            elif (words[2] == "rd"):
              instr = int('1101110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

        elif words[1] == "xor":
          if (words[2] in reg_names) and  (words[3] in reg_names):
            reg = True
            instr = int('1111000000001010', 2)

            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)
          else:
            print("Error: invalid instruction")
            print(words)
            sys.exit(1)

        elif words[1] == "load":
          if (words[2] in reg_names) and  (words[3][1:3] in reg_names):
            reg = True
            instr = int('1111000000000010', 2)    

            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3][1:3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3][1:3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3][1:3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3][1:3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

          elif (words[2] == "ra"): 
            abs = True
            instr = int('0100000000000000', 2)
          else:
            print("Error: invalid register") 
            print(words) 
            sys.exit(1)

        elif words[1] == "store":
          if (words[2] in reg_names) and (words[3][1:3] in reg_names):
            reg = True
            instr = int('1111000000000011', 2)
            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2) 
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3][1:3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3][1:3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3][1:3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3][1:3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

          elif (words[2] == "ra"): 
            abs = True
            instr = int('0101000000000000', 2)
          else:
            print("Error: invalid register") 
            print(words) 
            sys.exit(1)

        elif words[1] == "addm":
          abs = True
          if (words[2] == "ra"): 
            instr = int('0110000000000000', 2)
          else:
            print("Error: invalid register") 
            print(words) 
            sys.exit(1)

        elif words[1] == "subm":
          abs = True
          if (words[2] == "ra"): 
            instr = int('0111000000000000', 2)
          else:
            print("Error: invalid register") 
            print(words) 
            sys.exit(1)

        elif words[1] == "jump":
          abs = True 
          instr = int('1000000000000000', 2)
        elif words[1] == "jumpu":
          abs = True
          instr = int('1000000000000000', 2)
        elif words[1] == "jumpz":
          abs = True
          instr = int('1001000000000000', 2)
        elif words[1] == "jumpnz":
          abs = True
          instr = int('1010000000000000', 2)
        elif words[1] == "jumpc":
          abs = True
          instr = int('1011000000000000', 2)
        elif words[1] == "call":
          abs = True
          instr = int('1100000000000000', 2)
        elif words[1] == "ret":
          reg = True
          instr = int('1111000000000000', 2)

        elif words[1] == "rol":
          reg = True
          if (words[2] == "ra"): 
            instr = int('1111000000000100', 2)
          elif (words[2] == "rb"):
            instr = int('1111010000000100', 2)
          elif (words[2] == "rc"):
            instr = int('1111100000000100', 2)
          elif (words[2] == "rd"):
            instr = int('1111110000000100', 2)
          else:
            print("Error: invalid register") 
            print(words) 
            sys.exit(1)

        elif words[1] == "ror":
          reg = True
          if (words[2] == "ra"): 
            instr = int('1111000000000101', 2)
          elif (words[2] == "rb"):
            instr = int('1111010000000101', 2)
          elif (words[2] == "rc"):
            instr = int('1111100000000101', 2)
          elif (words[2] == "rd"):
            instr = int('1111110000000101', 2)
          else:
            print("Error: invalid register") 
            print(words)
            sys.exit(1)

        elif words[1] == "asl":
          reg = True
          if (words[2] == "ra"): 
            instr = int('1111000000001011', 2)
          elif (words[2] == "rb"):
            instr = int('1111010000001011', 2)
          elif (words[2] == "rc"):
            instr = int('1111100000001011', 2)
          elif (words[2] == "rd"):
            instr = int('1111110000001011', 2)
          else:
            print("Error: invalid register") 
            print(words) 
            sys.exit(1)

        elif words[1] == "xop1":
          imm = True
          if (words[2] == "ra"): 
            instr = int('1110000000000000', 2)
          elif (words[2] == "rb"):
            instr = int('1110010000000000', 2)
          elif (words[2] == "rc"):
            instr = int('1110100000000000', 2)
          elif (words[2] == "rd"):
            instr = int('1110110000000000', 2)
          else:
            print("Error: invalid register") 
            print(words) 
            sys.exit(1)

        elif words[1] == "xop2":
          if (words[2] in reg_names) and  (words[3][1:3] in reg_names):
            reg = True
            instr = int('1111000000001100', 2)    

            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3][1:3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3][1:3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3][1:3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3][1:3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

          else:
            print("Error: invalid register") 
            print(words) 
            sys.exit(1)

        elif words[1] == "xop3":
          if (words[2] in reg_names) and (words[3] in reg_names):
              
            reg = True
            instr = int('1111000000001101', 2)
            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2) 
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)
          else:
            print("Error: invalid instruction") 
            print(words) 
            sys.exit(1)    

        elif words[1] == "xop4":
          if (words[2] in reg_names) and  (words[3][1:3] in reg_names):
            reg = True
            instr = int('1111000000001110', 2)    

            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3][1:3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3][1:3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3][1:3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3][1:3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

          else:
            print("Error: invalid register") 
            print(words) 
            sys.exit(1)

        elif words[1] == "xop5":
          if (words[2] in reg_names) and (words[3] in reg_names):
              
            reg = True
            instr = int('1111000000001111', 2)
            if (words[2] == "ra"):
              instr = instr | int('0000000000000000', 2) 
            elif (words[2] == "rb"):
              instr = instr | int('0000010000000000', 2)
            elif (words[2] == "rc"):
              instr = instr | int('0000100000000000', 2)
            elif (words[2] == "rd"):
              instr = instr | int('0000110000000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)

            if (words[3] == "ra"):
              instr = instr | int('0000000000000000', 2)
            elif (words[3] == "rb"):
              instr = instr | int('0000000100000000', 2)
            elif (words[3] == "rc"):
              instr = instr | int('0000001000000000', 2)
            elif (words[3] == "rd"):
              instr = instr | int('0000001100000000', 2)
            else:
              print("Error: invalid register") 
              print(words) 
              sys.exit(1)
          else:
            print("Error: invalid instruction") 
            print(words) 
            sys.exit(1)            

        elif words[1] == ".data":
          dat = True
          instr = int('0000000000000000', 2)
        else:
          print("Error: invalid opcode") 
          print(words) 
          sys.exit(1)

        length = 0 
        for i in range(len(words)):
          length = length + 1
          if words[i] == "#":
            break

        if (length < 2):
          print("Error: invalid operand (len<2)")
          print(words) 
          sys.exit(1)

        else:
          if (length == 5) and imm:   
            data = words[3].rstrip()     
          elif (length == 5) and abs:
            data = words[3].rstrip()
          elif (length == 4) and abs:
            data = words[2].rstrip()
          elif (length == 4) and dat:
            data = words[2].rstrip()
          elif reg:
            data = "0"
          else:
            print("Error: invalid operand (len)")
            print(words) 
            sys.exit(1)

          operand = convertData(data) 
			
          if imm and (operand > 255):
            print("Error: invalid 8bit operand (>MAX)")
            print(words) 
            sys.exit(1)
			
          if abs and (operand > 4095):
            print("Error: invalid 12bit operand (>MAX)")
            print(words) 
            sys.exit(1)
			
          if data and (operand > 65535):
            print("Error: invalid 16bit operand (>MAX)")
            print(words) 
            sys.exit(1)
			
          instr = instr | operand
		  
          if debug > 1:
            divider='|'
            print( f"{str(words):<35}{divider:^35}{str.format('{:016b}', instr)}" )

          instruction_address = int(words[0])
		  
          if instruction_count == 0:
            # write start address to file #
            word_file.write(str.format('{:04X}', instruction_address) + ' ')
			
          if byte_count == 16:
            byte_count = 0
            word_file.write("\n")

            addressString = str.format('{:04X}', instruction_address) + ' '
            word_file.write(addressString)

          data_file.write(str.format('{:04}', instruction_address) + ' ')
          bin_value = str.format('{:016b}', instr) 
          data_file.write( bin_value )
          data_file.write("\n")

          # update EPROM files #
          data_string = str.format('{:04X}', instr ) + ' '
          word_file.write(data_string)

          # update mem file
          mem_file.write('@' + str.format('{:04X}', (instruction_address * 2)) + ' ')
          mem_file.write(data_string[3] + data_string[2] + data_string[1] + data_string[0] + "\n")
          
          #update mif file
          mif_file.write(str.format('{:04X}', instruction_address) + " : ")
          mif_file.write( str.format('{:016b}', instr) + ";\n"  )

          instruction_count += 1
          byte_count += 1

    mif_file.write( "END;\n" )

    # close files #
    source_file.close() 
    word_file.close()
    mem_file.close()
    mif_file.close()
    data_file.close()
    tmp_file.close()
	
    if debug > 0:
      print(" ")

    # display info #
    outputString = "Number of instructions : " + str(instruction_count)
    print( outputString )
    sys.exit(0) 

  else:
    print("Error: Input file not specified")
    sys.exit(1) 

if __name__ == '__main__':
  simpleCPUv1d_as(sys.argv)

