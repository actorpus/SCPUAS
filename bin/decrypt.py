#!/usr/bin/python
import getopt
import sys
import re

def convert_to_bin( value ):
  n = ['0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0']

  if value >= 2**15:
    n[0] = '1'
    value = value - (2**15)
  if value >= 2**14:
    n[1] = '1'
    value = value - (2**14)
  if value >= 2**13:
    n[2] = '1'
    value = value - (2**13)
  if value >= 2**12:
    n[3] = '1'
    value = value - (2**12)
  if value >= 2**11:
    n[4] = '1'
    value = value - (2**11)
  if value >= 2**10:
    n[5] = '1'
    value = value - (2**10)
  if value >= 2**9:
    n[6] = '1'
    value = value - (2**9)
  if value >= 2**8:
    n[7] = '1'
    value = value - (2**8)
  if value >= 2**7:
    n[8] = '1'
    value = value - (2**7)
  if value >= 2**6:
    n[9] = '1'
    value = value - (2**6)
  if value >= 2**5:
    n[10] = '1'
    value = value - (2**5)
  if value >= 2**4:
    n[11] = '1'
    value = value - (2**4)
  if value >= 2**3:
    n[12] = '1'
    value = value - (2**3)
  if value >= 2**2:
    n[13] = '1'
    value = value - (2**2)
  if value >= 2**1:
    n[14] = '1'
    value = value - (2**1)
  if value >= 2**0:
    n[15] = '1'
    value = value - (2**0)

  return str(''.join(n))

def convert_to_int( value ):
  n = 0
  if value[0] == '1':
    n = n + (2**7)
  if value[1] == '1':
    n = n + (2**6)    
  if value[2] == '1':
    n = n + (2**5)
  if value[3] == '1':
    n = n + (2**4)  
  if value[4] == '1':
    n = n + (2**3)
  if value[5] == '1':
    n = n + (2**2)    
  if value[6] == '1':
    n = n + (2**1)
  if value[7] == '1':
    n = n + (2**0)  
  return n

if len(sys.argv) == 1:
  print( "Usage: decrypt.py -i <input_file> -o <output_file>" )
  exit()

version = '1.0'
source_filename = 'output.ppm'
destination_filename = 'new.ppm'

address = 0
byte_count = 0

invert = { "0000": "1111",
           "0001": "1110",
           "0010": "1101",
           "0011": "1100",
           "0100": "1011",
           "0101": "1010",
           "0110": "1001",
           "0111": "1000",
           "1000": "0111",
           "1001": "0110",
           "1010": "0101",
           "1011": "0100",
           "1100": "0011",
           "1101": "0010",
           "1110": "0001",
           "1111": "0000"}

dencrypt = { "1010": "0000",
             "0110": "0001",
             "1110": "0010",
             "0001": "0011",
             "1001": "0100",
             "0101": "0101",
             "1101": "0110",
             "0011": "0111",
             "1011": "1000",
             "0111": "1001",
             "1111": "1010",
             "0000": "1011",
             "1000": "1100",
             "0100": "1101",
             "1100": "1110",
             "0010": "1111" }

try:
  options, remainder = getopt.getopt(sys.argv[1:], 'i:o:', [ 'input=', 
                                                             'output=' ])
except getopt.GetoptError as m:
  print( "Error: ", m )
  exit()

for opt, arg in options:
  if opt in ('-o', '--output'):
    if ".ppm" in arg:
      destination_filename = arg
    else:
      destination_filename = arg + ".ppm"
  elif opt in ('-i', '--input'):
    if ".ppm" in arg:
      source_filename = arg
    else:
      source_filename = arg + ".ppm"

try:
  source_file = open(source_filename, "r")
except IOError: 
  print( "Error: Input file does not exist." )
  exit() 

try:
  destination_file = open(destination_filename, "w")
except IOError: 
  print( "Error: Could not open output file" )
  exit() 
  
line = source_file.readline()
if "P3" in line:
  pass
else:
  print( "Error: Not PPM image - missing id" )
  exit()  

line = source_file.readline()
if "#" in line:
  pass
else:
  print( "Error: Not PPM image - missing description " )
  exit() 

line = source_file.readline()
w,h = line.split(" ")

print( "Image size = " + str(w) + " " + str(h) )

image_R = [[0 for x in range(int(w))] for y in range(int(h))] 
image_G = [[0 for x in range(int(w))] for y in range(int(h))] 
image_B = [[0 for x in range(int(w))] for y in range(int(h))] 

new = [[0 for x in range(int(w))] for y in range(int(h))] 

line = source_file.readline()
maximum = line

column = 0
row    = 0
while True:
  line = source_file.readline()
  if line == '':
    break 

  if column < int(w):
    tmp = line.split()
    image_R[row][column] = int(tmp[0])
    image_G[row][column] = int(tmp[1])
    image_B[row][column] = int(tmp[2])

  column += 1
  if column == int(w):
    column = 0
    row += 1

for y in range(int(h)):
  for x in range(int(w)):
    data = ((image_R[y][x] & 0xF8) << 8) + ((image_G[y][x] & 0xFC) << 3) + (image_B[y][x] >> 3)
    key = convert_to_bin(data)

    #print( key + " " + key[0:4] + " " + key[4:8] + " " + key[8:12] + " " + key[12:16] )
    #print( key + " " + invert[key[0:4]] + " " + invert[key[4:8]] + " " + invert[key[8:12]] + " " + invert[key[12:16]] )
    #print( key + " " + encrypt[invert[key[0:4]]] + " " + encrypt[invert[key[4:8]]] + " " + encrypt[invert[key[8:12]]] + " " + encrypt[invert[key[12:16]]] )

    new[y][x] =  dencrypt[invert[key[0:4]]] + dencrypt[invert[key[4:8]]] + dencrypt[invert[key[8:12]]] + dencrypt[invert[key[12:16]]]

destination_file.write( "P3" + "\n" )
destination_file.write( "# new image"  + "\n" )
destination_file.write( str(int(w)) + " " + str(int(h)) + "\n" )
destination_file.write( "255 \n" )

for y in range(int(h)):
  for x in range(int(w)):
    tmp = new[y][x]

    red = tmp[0:5]+"000"
    green = tmp[5:11]+"00"
    blue = tmp[11:16]+"000"

    #print( "red = " + red + " " + str(convert_to_int(red)) )
    #print( "green = " + green + " " + str(convert_to_int(green)) )
    #print( "blue = " + blue + " " + str(convert_to_int(blue)) )

    destination_file.write( str(convert_to_int(red)) + " " + str(convert_to_int(green)) + " " + str(convert_to_int(blue)) + "\n" )

source_file.close() 
destination_file.close()



