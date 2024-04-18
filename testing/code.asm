################
# THE BUG GAME #
################
# MEMORY MAP
# 0xFFF - WR - UART tx
# 0xFFF - RD - UART rx

-alias RXCHAR 0xFFF

# 0xFFE - WR - UART tx

-alias TXCHAR 0xFFE

# 0xFFE - RD - UART status
# UART REGISTERS
# TX : B7 - B0 data
# RX : B7 - B0 data 
# STATUS REGISTER
# B7 : NU
# B6 : NU
# B5 : NU
# B4 : NU
# B3 : NU
# B2 : TX Idle
# B1 : RX Idle
# B0 : RX Valid
# Main
# ----
start:
    call init           # initialise system
    call clear          # clear screen
    call net            # draw net
    call scores         # draw scores
    call ball           # draw ball
    call bat1           # draw user bat
    call bat2           # draw ai bat
loop:
    load mode        # serve or play
    and RA 0xFF
    jumpnz play
serve:
    call move_player    # move player 
    jump loop
play:
    call move_player    # move player
    call move_ai        # move ai
    call move_ball      # move ball
    call check          # check edges
    call delay          # wait
    jump loop           # repeat
stop:
    jump stop            # trap code for testing
# Game Variables
# --------------
mode:
    .data 0
score_1:
    .data 0
score_2:
    .data 0
ball_x:
    .data 9
ball_y:
    .data 15
dir_x:
    .data 0
dir_y:
    .data 0
bat1_x:
    .data 7
bat1_y:
    .data 15
bat2_x:
    .data 73
bat2_y:
    .data 15 
# Draw Variables
# --------------
colour:
    .data 0x00
graphics:
    .data 0x00
row:
    .data 0x00
column:
    .data 0x00
line:
    .data 0x00
pixelCnt:
    .data 0x00
lineCnt:
    .data 0x00
colActive:
    .data 0x00
bufIndex:
    .data 0x00
count:
    .data 0x00
# Convert to Decimal Variables
# ----------------------------
decValue:
    .data 0x00
# String Copy Variables
# ---------------------
srcAddr:
    .data 0x00
destAddr:
    .data 0x00
# Check Variables
# ---------------
temp:
    .data 0x00
# Serial RX Variables
# -------------------
keyPressed:
    .data 0x00
# Hello World Test
# ----------------
message:
    load b_green         
    store srcAddr   
    load string_buf        # set buffer
    store destAddr
    call strcpy  
    load f_black         
    store srcAddr   
    move RA RC
    store destAddr
    call strcpy 
    load mes_1_hello         
    store srcAddr         
    move RA RC
    store destAddr
    call strcpy 
    load b_black         
    store srcAddr   
    move RA RC
    store destAddr
    call strcpy 
    call txString
    ret
# RX TX Test
# ----------
rx_tx_test:
    load STATUS           # has ASCII char been RX?
    and RA 0x01
    jumpz rx_tx_test         # no check again
    load RXCHAR
    store TXCHAR
rx_tx_waitTX:
    load STATUS           # test TX status wait till 1
    and RA 0x04          
    jumpz rx_tx_waitTX    
    jump rx_tx_test          # repeat
# Software Delay
# --------------
delay:
    move RB 5 
delay_start:
    load 0xFFF  
delay_loop:
    sub RA 1
    jumpnz delay_loop
    sub RB 1
    jumpnz delay_start
    ret
# Move AI player
# --------------
move_ai:
    load dir_x            # if (dir_x == 1)
    and RA 0x01
    jumpz move_ai_track
    load bat2_y           # if (bat2_y = WINDOWHEIGHT/2)  
    sub RA 15                #   exit
    jumpz move_ai_exit       
    and RA 0x80              # if (bat2_y > WINDOWHEIGHT/2)
    jumpz move_ai_up         #   decrement
move_ai_down:  
    load bat2_y           # bat2_y = bat2_y + 1 
    add RA 1
    store bat2_y
    jump move_ai_exit
move_ai_up:                  
    load bat2_y           # bat2_y = bat2_y - 1
    sub RA 1
    store bat2_y
    jump move_ai_exit
 
move_ai_track:
    load bat2_y           # if (bat2_y > ball_y)
    subm ball_y           #   decrement
    and RA 0x80
    jumpz move_ai_up
    jump move_ai_down
move_ai_exit:
    call bat2               # update pat position
    ret
# Move human player
# -----------------
move_player:
    load STATUS           # has ASCII char been RX?
    and RA 0x01
    jumpz move_player_exit   # no exit
    load RXCHAR
    store keyPressed
    sub RA 0x77              # w?
    jumpz move_player_up
    load keyPressed
    sub RA 0x73              # s?
    jumpz move_player_down
    load keyPressed
    sub RA 0x64              # d?
    jumpz move_player_fire
move_player_exit:
    ret
move_player_up:
    load bat1_y           # check y pos
    sub RA 5
    and RA 0x80
    jumpnz move_player_exit
    load bat1_y  
    sub RA 1
    store bat1_y      
move_player_update:
    call bat1               
    load mode
    and RA 0xFF
    jumpnz move_player_exit
    load bat1_y 
    store ball_y  
    call ball                # move ball if in serve mode
    ret
    
move_player_down:
    load bat1_y           # check y pos
    sub RA 23                
    and RA 0x80
    jumpz move_player_exit
    load bat1_y 
    add RA 1
    store bat1_y    
    jump move_player_update
move_player_fire:
    move RA 1                # fire button pressed change mode to play
    store mode
    jump move_player_exit
# Move Ball
# ---------
move_ball:
    load ball_x           # if ball_x < 10 (update direction)
    sub RA 10                 #   dir_x =0
    and RA 0x80
    jumpz move_ballNext0 
    move RA 0
    store dir_x
    jump move_ballNext1   
move_ballNext0:
    load ball_x           # if ball_x > 70 
    sub RA 70                #   dir_x =1
    and RA 0x80
    jumpnz move_ballNext1 
    move RA 1
    store dir_x
move_ballNext1:  
    load ball_y           # if ball_y < 8
    sub RA 8                 #   dir_y = 0
    and RA 0x80
    jumpz move_ballNext2 
    move RA 0
    store dir_y
    jump move_ballNext3   
move_ballNext2:
    load ball_y           # if ball_y > 23
    sub RA 23                #   dir_y = 1
    and RA 0x80
    jumpnz move_ballNext3 
    move RA 1
    store dir_y
move_ballNext3:                
    load dir_x            # if dir_x == 0
    and RA 0xFF              #   ball_x = ball_x + 1
    jumpnz move_ballNext4
    load ball_x           #
    add RA 1
    store ball_x
    jump move_ballNext5
move_ballNext4:                
    load ball_x           # else  
    sub RA 1                 #   ball_x = ball_x - 1 
    store ball_x
move_ballNext5:               
    load dir_y            # if dir_y == 0
    and RA 0xFF              #   ball_y = ball_y + 1
    jumpnz move_ballNext6
    load ball_y           # 
    add RA 1
    store ball_y
    jump move_ballNext7
move_ballNext6:                
    load ball_y           # else
    sub RA 1                 #    ball_y = ball_y - 1
    store ball_y
move_ballNext7:
    call ball                # update ball position
    ret
# Check Edges and Miss
# --------------------
check:
    load ball_x           # if ball_x > 37 and  ball_x < 41
    sub RA 37
    and RA 0x80
    jumpnz check_next0
    load ball_x
    sub RA 41
    and RA 0x80
    jumpz check_next0
    call net                 # redraw net
check_next0:
    load ball_x           # if (ball_x < 10)
    sub RA 10
    and RA 0x80
    jumpz check_next2
    load bat1_y           # if (ball_y = bat1_y)
    subm ball_y           #    ok - exit
    jumpz check_next2
    load bat1_y           # if (ball_y = bat1_y-1)
    sub RA 1                 #    ok - exit
    subm ball_y           
    jumpz check_next2
    load bat1_y           # if (ball_y = bat1_y+1)
    add RA 1                 #    ok - exit
    subm ball_y           
    jumpz check_next2
check_update1:
    load score_2          # score2+= 1
    add RA 1
    store score_2
    
    move RA 15
    store bat1_y
    store ball_y
    call clear
    call net
    call scores
    call ball
    call bat1
    call bat2
    move RA 0                # mode = 0, serve
    store mode
check_next2:
    ret
# Init 
# ----
init:
    load cursor_off    # set colour
    store srcAddr         
    load string_buf  
    store destAddr
    call strcpy              # call strcpy
    call txString            # display string
    ret
# Clear screen
# ------------
clear:
    move RA 0
    store count
    move RA 1
    store row
    move RA 1
    store column 
clear_next:
    load string_buf  
    store bufIndex        # set buffer index to start
    move RB RA
    move RA 0x1B             # ESC
    storer RA RB
    add RB 1
    move RA 0x5B             # [
    storer RA RB
    add RB 1
    move RA RB
    store bufIndex
    load row              # <ROW>
    store decValue
    call convDecBuf
    load bufIndex
    move RB RA
    move RA 0x3B             # ;
    storer RA RB
    add RB 1
    move RA RB
    store bufIndex
    load column           # <COLUMN>
    store decValue
    call convDecBuf
    load bufIndex
    move RB RA
    move RA 0x48             # H
    storer RA RB
    add RB 1
    move RA RB
    store bufIndex
    load b_black       # set colour
    store srcAddr         
    load bufIndex         # set buffer
    store destAddr
    call strcpy              # call strcpy
clear_loop:
    move RA 0x20             # add space to buffer
    storer RA RC
    add RC 1
    load count            # inc count
    add RA 1
    store count
    sub RA 80
    jumpnz clear_loop
    move RA 0x00             # insert NULL
    storer RA RC
    store count
    call txString            # display string
    load row              # inc row
    add RA 1
    store row             # if row > 30 exit
    sub RA 30
    jumpz clear_exit
    jump clear_next
 clear_exit:   
    ret
# Draw net
# --------
net:
    move RA 0                # zero repeat count
    store count
    move RA 39               # set position
    store column
    move RA 2
    store row
    load b_blue        # set colour
    store colour
    
    load net_1         # set graphics
    store graphics
net_loop:
    call draw                # draw sprite
    load count            # inc count
    add RA 1
    store count
    sub RA 5                 # all segments printed?
    jumpnz net_loop
    
    ret
# Draw Scores
# -----------
scores: 
    move RA 20               # set position
    store column
    move RA 2
    store row
    load b_yellow      # set colour
    store colour
    
    load score_1          # calc offset score x 5
    aslr RA
    aslr RA
    addm score_1
    store count
    load num_0         # set graphics
    addm count
    store graphics
    call draw
    move RA 60               # set position
    store column
    move RA 2
    store row
    
    load score_2          # calc offset score x 5
    rol RA
    rol RA
    addm score_2
    store count
 
    load num_0         # set graphics
    addm count
    store graphics
    
    call draw
    ret
# Draw Ball
# ---------
ball:
    load ball_x           # set position
    store column
    load ball_y   
    store row
    load b_green       # set colour
    store colour
    
    load ball_1        # set graphics
    store graphics
    call draw                # draw sprite
   
    ret
# Draw Bat1
# ---------
bat1:
    load bat1_x           # set position
    store column
    load bat1_y   
    store row
    load b_cyan        # set colour
    store colour
    
    load bat_1         # set graphics
    store graphics
    call draw                # draw sprite
   
    ret
# Draw Bat2
# ---------
bat2:
    load bat2_x           # set position
    store column
    load bat2_y   
    store row
    load b_cyan        # set colour
    store colour
    
    load bat_2         # set graphics
    store graphics
    call draw                # draw sprite
   
    ret
# Draw sprite
# -----------
draw:
    move RA 0            
    store lineCnt         # set sprite line to first 
    store pixelCnt        # set sprite pixel to first 
    store colActive       # set colour active to false
    load string_buf  
    store bufIndex        # set buffer index to start
    load b_black       # get colour string address
    store srcAddr         # call strcpy
    load bufIndex
    store destAddr
    call strcpy
    move RA RC
    store bufIndex
draw_next:
    load bufIndex
    move RB RA
    move RA 0x1B             # ESC
    storer RA RB
    add RB 1
    move RA 0x5B             # [
    storer RA RB
    add RB 1
    move RA RB
    store bufIndex
    load row              # <ROW>
    store decValue
    call convDecBuf
    load bufIndex
    move RB RA
    move RA 0x3B             # ;
    storer RA RB
    add RB 1
    move RA RB
    store bufIndex
    load column           # <COLUMN>
    store decValue
    call convDecBuf
    load bufIndex
    move RB RA
    move RA 0x48             # H
    storer RA RB
    add RB 1
    move RA RB
    store bufIndex
    load graphics         # load sprite address
    addm lineCnt
    move RB RA
    loadr RB             # load pixel data
    store line            # buffer line
draw_loop:
    load line
    and RA 0x04              # test bit position
    jumpz draw_black
    
draw_colour:
    load colActive        # is colour active
    and RA 0xFF
    jumpnz draw_colourSet
    move RA 1                # set colour is active flag
    store colActive
    load colour           # get colour string address
    store srcAddr         # call strcpy
    load bufIndex
    store destAddr
    call strcpy
    move RA RC
    store bufIndex
draw_colourSet:
    load bufIndex         # draw block (space)
    move RB RA
    move RA 0x20
    storer RA RB
    add RB 1
    move RA RB
    store bufIndex
    jump draw_nextPixel
 
draw_black:
    load colActive
    and RA 0xFF
    jumpz draw_blackSet
    move RA 0                # set colour is not active flag
    store colActive
    load b_black       # get colour string address
    store srcAddr         # call strcpy
    load bufIndex
    store destAddr
    call strcpy
    move RA RC
    store bufIndex
draw_blackSet: 
    load bufIndex         # draw block (space)
    move RB RA
    move RA 0x20
    storer RA RB
    add RB 1
    move RA RB
    store bufIndex
draw_nextPixel:
    load line             # move to next pixel
    aslr RA
    store line
    load pixelCnt         # inc pixel count
    add RA 1
    store pixelCnt
    sub RA 3
    jumpnz draw_loop
 
    move RA 0                # zero pixel count
    store pixelCnt
    load row              # move to next row
    add RA 1
    store row
    load lineCnt          # inc line count
    add RA 1
    store lineCnt
    sub RA 5                 # have all 5 rows been processed?
    jumpnz draw_next
    load bufIndex         # yes, insert NULL
    move RB RA
    move RA 0x0
    storer RA RB
    call txString            # display string
    ret
# Convert variable DECVALUE into decimal characters and TX
# --------------------------------------------------------
# Used in cursor movement commands RANGE limited to 99 - 0
convDecBuf:
    load bufIndex
    move RD RA
    load decValue
    move RB 0
convDecBuf_H:
    sub RA 10                # sub 10
    move RC RA               # copy for compare
    and RC 0x80              # neg?
    jumpnz convDecBuf_HTx    # yes, exit
    add RB 1                 # inc count 
    jump convDecBuf_H        # repeat
convDecBuf_HTx:
    add RA 10                # undo last sub
    move RC RA               # buffer for units
    and RB 0xFF              # skip if 10s count 0
    jumpz convDecBuf_LTx  
 
    move RA RB               # copy count
    add RA 0x30              # convert to ASCII
    storer RA RD
    add RD 1
    
convDecBuf_LTx:
    move RA RC               # copy count
    add RA 0x30              # convert to ASCII
    storer RA RD
    add RD 1
    move RA RD
    store bufIndex
    ret
# Copy string (must terminate with a \0)
# --------------------------------------
# Source / destination addresses passed in SRCADDR / DESTADDR
strcpy:
    load srcAddr          # get source address
    move RB RA
    load destAddr         # get destination address
    move RC RA 
strcpy_loop:              
    loadr RB             # load  char
    and RA 0xFF
    jumpz strcpy_exit        # exit if 0
    storer RA RC            # copy
    add RB 1
    add RC 1
    jump strcpy_loop         # repeat
strcpy_exit:
    ret
# TX String (must terminate with a \0)
# ------------------------------------
# Base address passed in variable STRING
txString:
    load string_buf    # get string address
tx_loop:              
    loadr RB             # load  char
    and RA 0xFF
    jumpz tx_exit            # exit if 0
    store TXCHAR          # tx
waitTX:
    load STATUS           # test TX status wait till 1
    and RA 0x04          
    jumpz waitTX    
    add RB 1                 # inc address
    jump tx_loop             # repeat
tx_exit:
    ret
# Test String
# ----------------------------------
mes_0_hello:
    .data 0x48
    .data 0x69
    .data 0x0A
    .data 0x0D
    .data 0x00
mes_1_hello:
    .data 0x48
    .data 0x65
    .data 0x6C
    .data 0x6C
    .data 0x6F
    .data 0x20
    .data 0x57
    .data 0x6F
    .data 0x72
    .data 0x6C
    .data 0x64
    .data 0x0A
    .data 0x0D
    .data 0x00
# Constants, ASCII strings, Graphics
# ----------------------------------
# Cursor Blink OFF
# ----------------
cursor_off:
    .data 0x1B
    .data 0x5B
    .data 0x3F
    .data 0x32
    .data 0x35
    .data 0x6C
    .data 0x00
# Foreground Colour
# -----------------
f_black:
    .data 0x1B
    .data 0x5B
    .data 0x33
    .data 0x30
    .data 0x6D
    .data 0x00
# Background Colour
# -----------------
b_cyan:
    .data 0x1B
    .data 0x5B
    .data 0x34
    .data 0x36
    .data 0x6D
    .data 0x00
b_green:
    .data 0x1B
    .data 0x5B
    .data 0x34
    .data 0x32
    .data 0x6D
    .data 0x00
b_black:
    .data 0x1B
    .data 0x5B
    .data 0x34
    .data 0x30
    .data 0x6D
    .data 0x00
b_yellow:
    .data 0x1B
    .data 0x5B
    .data 0x34
    .data 0x33
    .data 0x6D
    .data 0x00
b_blue:
    .data 0x1B
    .data 0x5B
    .data 0x31
    .data 0x30
    .data 0x34
    .data 0x6D
    .data 0x00
b_white:
    .data 0x1B
    .data 0x5B
    .data 0x31
    .data 0x30
    .data 0x37
    .data 0x6D
    .data 0x00
num_0:
    .data 7  
    .data 5  
    .data 5  
    .data 5 
    .data 7  
num_1:
    .data 2  
    .data 6  
    .data 2  
    .data 2 
    .data 7  
num_2:
    .data 7  
    .data 1 
    .data 7  
    .data 4 
    .data 7  
num_3:
    .data 7  
    .data 1 
    .data 7  
    .data 1 
    .data 7  
num_4:
    .data 5 
    .data 5 
    .data 7 
    .data 1 
    .data 1 
num_5:
    .data 7 
    .data 4 
    .data 7 
    .data 1 
    .data 7 
num_6:
    .data 7 
    .data 4 
    .data 7 
    .data 5 
    .data 7 
num_7:
    .data 7 
    .data 1 
    .data 2 
    .data 4 
    .data 4 
num_8:
    .data 7 
    .data 5 
    .data 7 
    .data 5 
    .data 7 
num_9:
    .data 7 
    .data 5 
    .data 7 
    .data 1 
    .data 7 
bat_1:
    .data 0 
    .data 6 
    .data 6 
    .data 6 
    .data 0 
bat_2:
    .data 0 
    .data 3 
    .data 3 
    .data 3 
    .data 0 
ball_1:
    .data 0 
    .data 0 
    .data 2 
    .data 0 
    .data 0 
net_1:
    .data 0 
    .data 2 
    .data 2 
    .data 2 
    .data 0 
bug_0:
    .data 3 
    .data 7 
    .data 4 
    .data 6 
    .data 4 
bug_1:
    .data 7 
    .data 7 
    .data 3 
    .data 3 
    .data 3 
bug_2:
    .data 7 
    .data 7 
    .data 6 
    .data 6 
    .data 6 
bug_3:
    .data 6 
    .data 7 
    .data 1 
    .data 5 
    .data 1 
bug_4:
    .data 7 
    .data 7 
    .data 6 
    .data 7 
    .data 3 
bug_5:
    .data 7 
    .data 3 
    .data 0 
    .data 2 
    .data 7 
bug_6:
    .data 7 
    .data 6 
    .data 0 
    .data 2 
    .data 7 
bug_7:
    .data 7 
    .data 7 
    .data 3 
    .data 7 
    .data 6 
# Graphics 3 x 5 pixels
letter_0:
    .data 7 
    .data 2 
    .data 2 
    .data 2 
    .data 2 
letter_1:
    .data 5 
    .data 5 
    .data 7 
    .data 5 
    .data 5 
letter_2:
    .data 7 
    .data 4 
    .data 7 
    .data 4 
    .data 7 
letter_3:
    .data 4 
    .data 4 
    .data 7 
    .data 5 
    .data 7 
letter_4:
    .data 5 
    .data 5 
    .data 5 
    .data 5 
    .data 7 
letter_5:
    .data 7 
    .data 5 
    .data 7 
    .data 1 
    .data 7 
letter_6:
    .data 7 
    .data 5 
    .data 7 
    .data 5 
    .data 5 
letter_7:
    .data 7 
    .data 5 
    .data 5 
    .data 4 
    .data 4 
letter_8:
    .data 7 
    .data 5 
    .data 5 
    .data 1 
    .data 1 
STATUS:
    .data 0x00
string_buf:
    .data 0x00
