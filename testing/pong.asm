################
# THE BUG GAME #
################

# MEMORY MAP
# 0xFFF - WR - UART tx
# 0xFFF - RD - UART rx
# 0xFFE - WR - UART tx
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
    load RA mode        # serve or play
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
	jump stop			# trap code for testing

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
    movea( RA, b_green )       
    store RA srcAddr   
    movea( RA, string_buf )      # set buffer
    store RA destAddr
    call strcpy  

    movea( RA, f_black )       
    store RA srcAddr   
    move RA RC
    store RA destAddr
    call strcpy 

    movea( RA, mes_1_hello )       
    store RA srcAddr         
    move RA RC
    store RA destAddr
    call strcpy 

    movea( RA, b_black )       
    store RA srcAddr   
    move RA RC
    store RA destAddr
    call strcpy 
    call txString
    ret

# RX TX Test
# ----------

rx_tx_test:
    load RA STATUS           # has ASCII char been RX?
    and RA 0x01
    jumpz rx_tx_test         # no check again

    load RA RXCHAR
    store RA TXCHAR

rx_tx_waitTX:
    load RA STATUS           # test TX status wait till 1
    and RA 0x04          
    jumpz rx_tx_waitTX    

    jump rx_tx_test          # repeat


# Software Delay
# --------------

delay:
    move RB 5 

delay_start:
    movea( RA, 0xFFF )

delay_loop:
    sub RA 1
    jumpnz delay_loop
    sub RB 1
    jumpnz delay_start

    ret

# Move AI player
# --------------

move_ai:
    load RA dir_x            # if (dir_x == 1)
    and RA 0x01
    jumpz move_ai_track

    load RA bat2_y           # if (bat2_y = WINDOWHEIGHT/2)  
    sub RA 15                #   exit
    jumpz move_ai_exit       
    and RA 0x80              # if (bat2_y > WINDOWHEIGHT/2)
    jumpz move_ai_up         #   decrement

move_ai_down:  
    load RA bat2_y           # bat2_y = bat2_y + 1 
    add RA 1
    store RA bat2_y
    jump move_ai_exit

move_ai_up:                  
    load RA bat2_y           # bat2_y = bat2_y - 1
    sub RA 1
    store RA bat2_y
    jump move_ai_exit
 
move_ai_track:
    load RA bat2_y           # if (bat2_y > ball_y)
    subm RA ball_y           #   decrement
    and RA 0x80
    jumpz move_ai_up
    jump move_ai_down

move_ai_exit:
    call bat2               # update pat position
    ret

# Move human player
# -----------------

move_player:
    load RA STATUS           # has ASCII char been RX?
    and RA 0x01
    jumpz move_player_exit   # no exit

    load RA RXCHAR
    store RA keyPressed

    sub RA 0x77              # w?
    jumpz move_player_up

    load RA keyPressed
    sub RA 0x73              # s?
    jumpz move_player_down

    load RA keyPressed
    sub RA 0x64              # d?
    jumpz move_player_fire

move_player_exit:
    ret

move_player_up:
    load RA bat1_y           # check y pos
    sub RA 5
    and RA 0x80
    jumpnz move_player_exit

    load RA bat1_y  
    sub RA 1
    store RA bat1_y      

move_player_update:
    call bat1               

    load RA mode
    and RA 0xFF
    jumpnz move_player_exit

    load RA bat1_y 
    store RA ball_y  
    call ball                # move ball if in serve mode
    ret
    
move_player_down:
    load RA bat1_y           # check y pos
    sub RA 23                
    and RA 0x80
    jumpz move_player_exit

    load RA bat1_y 
    add RA 1
    store RA bat1_y    

    jump move_player_update

move_player_fire:
    move RA 1                # fire button pressed change mode to play
    store RA mode
    jump move_player_exit

# Move Ball
# ---------

move_ball:
    load RA ball_x           # if ball_x < 10 (update direction)
    sub RA 10                 #   dir_x =0
    and RA 0x80
    jumpz move_ballNext0 

    move RA 0
    store RA dir_x
    jump move_ballNext1   

move_ballNext0:
    load RA ball_x           # if ball_x > 70 
    sub RA 70                #   dir_x =1
    and RA 0x80
    jumpnz move_ballNext1 

    move RA 1
    store RA dir_x

move_ballNext1:  
    load RA ball_y           # if ball_y < 8
    sub RA 8                 #   dir_y = 0
    and RA 0x80
    jumpz move_ballNext2 

    move RA 0
    store RA dir_y
    jump move_ballNext3   

move_ballNext2:
    load RA ball_y           # if ball_y > 23
    sub RA 23                #   dir_y = 1
    and RA 0x80
    jumpnz move_ballNext3 

    move RA 1
    store RA dir_y

move_ballNext3:                
    load RA dir_x            # if dir_x == 0
    and RA 0xFF              #   ball_x = ball_x + 1
    jumpnz move_ballNext4

    load RA ball_x           #
    add RA 1
    store RA ball_x
    jump move_ballNext5

move_ballNext4:                
    load RA ball_x           # else  
    sub RA 1                 #   ball_x = ball_x - 1 
    store RA ball_x

move_ballNext5:               
    load RA dir_y            # if dir_y == 0
    and RA 0xFF              #   ball_y = ball_y + 1
    jumpnz move_ballNext6

    load RA ball_y           # 
    add RA 1
    store RA ball_y
    jump move_ballNext7

move_ballNext6:                
    load RA ball_y           # else
    sub RA 1                 #    ball_y = ball_y - 1
    store RA ball_y

move_ballNext7:
    call ball                # update ball position

    ret

# Check Edges and Miss
# --------------------

check:
    load RA ball_x           # if ball_x > 37 and  ball_x < 41
    sub RA 37
    and RA 0x80
    jumpnz check_next0

    load RA ball_x
    sub RA 41
    and RA 0x80
    jumpz check_next0

    call net                 # redraw net

check_next0:
    load RA ball_x           # if (ball_x < 10)
    sub RA 10
    and RA 0x80
    jumpz check_next2

    load RA bat1_y           # if (ball_y = bat1_y)
    subm RA ball_y           #    ok - exit
    jumpz check_next2

    load RA bat1_y           # if (ball_y = bat1_y-1)
    sub RA 1                 #    ok - exit
    subm RA ball_y           
    jumpz check_next2

    load RA bat1_y           # if (ball_y = bat1_y+1)
    add RA 1                 #    ok - exit
    subm RA ball_y           
    jumpz check_next2

check_update1:
    load RA score_2          # score2+= 1
    add RA 1
    store RA score_2
    
    move RA 15
    store RA bat1_y
    store RA ball_y

    call clear
    call net
    call scores
    call ball
    call bat1
    call bat2

    move RA 0                # mode = 0, serve
    store RA mode

check_next2:
    ret

# Init 
# ----

init:
    movea( RA, cursor_off )  # set colour
    store RA srcAddr         
    movea( RA, string_buf )
    store RA destAddr

    call strcpy              # call strcpy
    call txString            # display string
    ret

# Clear screen
# ------------

clear:
    move RA 0
    store RA count
    move RA 1
    store RA row
    move RA 1
    store RA column 

clear_next:
    movea( RA, string_buf )
    store RA bufIndex        # set buffer index to start

    move RB RA
    move RA 0x1B             # ESC
    store RA (RB)
    add RB 1

    move RA 0x5B             # [
    store RA (RB)
    add RB 1
    move RA RB
    store RA bufIndex

    load RA row              # <ROW>
    store RA decValue
    call convDecBuf

    load RA bufIndex
    move RB RA
    move RA 0x3B             # ;
    store RA (RB)
    add RB 1
    move RA RB
    store RA bufIndex

    load RA column           # <COLUMN>
    store RA decValue
    call convDecBuf

    load RA bufIndex
    move RB RA
    move RA 0x48             # H
    store RA (RB)
    add RB 1
    move RA RB
    store RA bufIndex

    movea( RA, b_black )     # set colour
    store RA srcAddr         

    load RA bufIndex         # set buffer
    store RA destAddr
    call strcpy              # call strcpy

clear_loop:
    move RA 0x20             # add space to buffer
    store RA (RC)
    add RC 1

    load RA count            # inc count
    add RA 1
    store RA count
    sub RA 80
    jumpnz clear_loop

    move RA 0x00             # insert NULL
    store RA (RC)
    store RA count

    call txString            # display string

    load RA row              # inc row
    add RA 1
    store RA row             # if row > 30 exit
    sub RA 30
    jumpz clear_exit
    jump clear_next

 clear_exit:   
    ret

# Draw net
# --------

net:
    move RA 0                # zero repeat count
    store RA count
    move RA 39               # set position
    store RA column
    move RA 2
    store RA row

    movea( RA, b_blue )      # set colour
    store RA colour
    
    movea( RA, net_1 )       # set graphics
    store RA graphics

net_loop:
    call draw                # draw sprite

    load RA count            # inc count
    add RA 1
    store RA count
    sub RA 5                 # all segments printed?
    jumpnz net_loop
    
    ret

# Draw Scores
# -----------

scores: 
    move RA 20               # set position
    store RA column
    move RA 2
    store RA row

    movea( RA, b_yellow )    # set colour
    store RA colour
    
    load RA score_1          # calc offset score x 5
    asl RA
    asl RA
    addm RA score_1
    store RA count

    movea( RA, num_0 )       # set graphics
    addm RA count
    store RA graphics

    call draw

    move RA 60               # set position
    store RA column
    move RA 2
    store RA row
    
    load RA score_2          # calc offset score x 5
    rol RA
    rol RA
    addm RA score_2
    store RA count
 
    movea( RA, num_0 )       # set graphics
    addm RA count
    store RA graphics
    
    call draw
    ret

# Draw Ball
# ---------

ball:
    load RA ball_x           # set position
    store RA column
    load RA ball_y   
    store RA row

    movea( RA, b_green )     # set colour
    store RA colour
    
    movea( RA, ball_1 )      # set graphics
    store RA graphics

    call draw                # draw sprite
   
    ret

# Draw Bat1
# ---------

bat1:
    load RA bat1_x           # set position
    store RA column
    load RA bat1_y   
    store RA row

    movea( RA, b_cyan )      # set colour
    store RA colour
    
    movea( RA, bat_1 )       # set graphics
    store RA graphics

    call draw                # draw sprite
   
    ret

# Draw Bat2
# ---------

bat2:
    load RA bat2_x           # set position
    store RA column
    load RA bat2_y   
    store RA row

    movea( RA, b_cyan )      # set colour
    store RA colour
    
    movea( RA, bat_2 )       # set graphics
    store RA graphics

    call draw                # draw sprite
   
    ret

# Draw sprite
# -----------

draw:
    move RA 0            
    store RA lineCnt         # set sprite line to first 
    store RA pixelCnt        # set sprite pixel to first 
    store RA colActive       # set colour active to false

    movea( RA, string_buf )
    store RA bufIndex        # set buffer index to start

    movea( RA, b_black )     # get colour string address
    store RA srcAddr         # call strcpy

    load RA bufIndex
    store RA destAddr
    call strcpy
    move RA RC
    store RA bufIndex

draw_next:
    load RA bufIndex
    move RB RA
    move RA 0x1B             # ESC
    store RA (RB)
    add RB 1

    move RA 0x5B             # [
    store RA (RB)
    add RB 1
    move RA RB
    store RA bufIndex

    load RA row              # <ROW>
    store RA decValue
    call convDecBuf

    load RA bufIndex
    move RB RA
    move RA 0x3B             # ;
    store RA (RB)
    add RB 1
    move RA RB
    store RA bufIndex

    load RA column           # <COLUMN>
    store RA decValue
    call convDecBuf

    load RA bufIndex
    move RB RA
    move RA 0x48             # H
    store RA (RB)
    add RB 1
    move RA RB
    store RA bufIndex

    load RA graphics         # load sprite address
    addm RA lineCnt
    move RB RA
    load RA (RB)             # load pixel data
    store RA line            # buffer line

draw_loop:
    load RA line
    and RA 0x04              # test bit position
    jumpz draw_black
    
draw_colour:
    load RA colActive        # is colour active
    and RA 0xFF
    jumpnz draw_colourSet

    move RA 1                # set colour is active flag
    store RA colActive
    load RA colour           # get colour string address
    store RA srcAddr         # call strcpy
    load RA bufIndex
    store RA destAddr
    call strcpy
    move RA RC
    store RA bufIndex

draw_colourSet:
    load RA bufIndex         # draw block (space)
    move RB RA
    move RA 0x20
    store RA (RB)
    add RB 1
    move RA RB
    store RA bufIndex
    jump draw_nextPixel
 
draw_black:
    load RA colActive
    and RA 0xFF
    jumpz draw_blackSet

    move RA 0                # set colour is not active flag
    store RA colActive

    movea( RA, b_black )     # get colour string address

    store RA srcAddr         # call strcpy
    load RA bufIndex
    store RA destAddr
    call strcpy
    move RA RC
    store RA bufIndex

draw_blackSet: 
    load RA bufIndex         # draw block (space)
    move RB RA
    move RA 0x20
    store RA (RB)
    add RB 1
    move RA RB
    store RA bufIndex

draw_nextPixel:
    load RA line             # move to next pixel
    asl RA
    store RA line
    load RA pixelCnt         # inc pixel count
    add RA 1
    store RA pixelCnt
    sub RA 3
    jumpnz draw_loop
 
    move RA 0                # zero pixel count
    store RA pixelCnt
    load RA row              # move to next row
    add RA 1
    store RA row
    load RA lineCnt          # inc line count
    add RA 1
    store RA lineCnt
    sub RA 5                 # have all 5 rows been processed?
    jumpnz draw_next

    load RA bufIndex         # yes, insert NULL
    move RB RA
    move RA 0x0
    store RA (RB)

    call txString            # display string

    ret

# Convert variable DECVALUE into decimal characters and TX
# --------------------------------------------------------
# Used in cursor movement commands RANGE limited to 99 - 0

convDecBuf:
    load RA bufIndex
    move RD RA
    load RA decValue
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
    store RA (RD)           
    add RD 1
    
convDecBuf_LTx:
    move RA RC               # copy count
    add RA 0x30              # convert to ASCII
    store RA (RD) 
    add RD 1
    move RA RD
    store RA bufIndex

    ret

# Copy string (must terminate with a \0)
# --------------------------------------
# Source / destination addresses passed in SRCADDR / DESTADDR

strcpy:
    load RA srcAddr          # get source address
    move RB RA
    load RA destAddr         # get destination address
    move RC RA 

strcpy_loop:              
    load RA (RB)             # load  char
    and RA 0xFF
    jumpz strcpy_exit        # exit if 0
    store RA (RC)            # copy
    add RB 1
    add RC 1
    jump strcpy_loop         # repeat

strcpy_exit:
    ret

# TX String (must terminate with a \0)
# ------------------------------------
# Base address passed in variable STRING

txString:
    movea( RB, string_buf )  # get string address

tx_loop:              
    load RA (RB)             # load  char
    and RA 0xFF
    jumpz tx_exit            # exit if 0
    store RA TXCHAR          # tx

waitTX:
    load RA STATUS           # test TX status wait till 1
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
    sprite( 1,1,1 ) 
    sprite( 1,0,1 ) 
    sprite( 1,0,1 ) 
    sprite( 1,0,1 )
    sprite( 1,1,1 ) 

num_1:
    sprite( 0,1,0 ) 
    sprite( 1,1,0 ) 
    sprite( 0,1,0 ) 
    sprite( 0,1,0 )
    sprite( 1,1,1 ) 

num_2:
    sprite( 1,1,1 ) 
    sprite( 0,0,1 )
    sprite( 1,1,1 ) 
    sprite( 1,0,0 )
    sprite( 1,1,1 ) 

num_3:
    sprite( 1,1,1 ) 
    sprite( 0,0,1 )
    sprite( 1,1,1 ) 
    sprite( 0,0,1 )
    sprite( 1,1,1 ) 

num_4:
    sprite( 1,0,1 )
    sprite( 1,0,1 )
    sprite( 1,1,1 )
    sprite( 0,0,1 )
    sprite( 0,0,1 )

num_5:
    sprite( 1,1,1 )
    sprite( 1,0,0 )
    sprite( 1,1,1 )
    sprite( 0,0,1 )
    sprite( 1,1,1 )

num_6:
    sprite( 1,1,1 )
    sprite( 1,0,0 )
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,1,1 )

num_7:
    sprite( 1,1,1 )
    sprite( 0,0,1 )
    sprite( 0,1,0 )
    sprite( 1,0,0 )
    sprite( 1,0,0 )

num_8:
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,1,1 )

num_9:
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,1,1 )
    sprite( 0,0,1 )
    sprite( 1,1,1 )

bat_1:
    sprite( 0,0,0 )
    sprite( 1,1,0 )
    sprite( 1,1,0 )
    sprite( 1,1,0 )
    sprite( 0,0,0 )

bat_2:
    sprite( 0,0,0 )
    sprite( 0,1,1 )
    sprite( 0,1,1 )
    sprite( 0,1,1 )
    sprite( 0,0,0 )

ball_1:
    sprite( 0,0,0 )
    sprite( 0,0,0 )
    sprite( 0,1,0 )
    sprite( 0,0,0 )
    sprite( 0,0,0 )

net_1:
    sprite( 0,0,0 )
    sprite( 0,1,0 )
    sprite( 0,1,0 )
    sprite( 0,1,0 )
    sprite( 0,0,0 )

bug_0:
    sprite( 0,1,1 )
    sprite( 1,1,1 )
    sprite( 1,0,0 )
    sprite( 1,1,0 )
    sprite( 1,0,0 )

bug_1:
    sprite( 1,1,1 )
    sprite( 1,1,1 )
    sprite( 0,1,1 )
    sprite( 0,1,1 )
    sprite( 0,1,1 )

bug_2:
    sprite( 1,1,1 )
    sprite( 1,1,1 )
    sprite( 1,1,0 )
    sprite( 1,1,0 )
    sprite( 1,1,0 )

bug_3:
    sprite( 1,1,0 )
    sprite( 1,1,1 )
    sprite( 0,0,1 )
    sprite( 1,0,1 )
    sprite( 0,0,1 )

bug_4:
    sprite( 1,1,1 )
    sprite( 1,1,1 )
    sprite( 1,1,0 )
    sprite( 1,1,1 )
    sprite( 0,1,1 )

bug_5:
    sprite( 1,1,1 )
    sprite( 0,1,1 )
    sprite( 0,0,0 )
    sprite( 0,1,0 )
    sprite( 1,1,1 )

bug_6:
    sprite( 1,1,1 )
    sprite( 1,1,0 )
    sprite( 0,0,0 )
    sprite( 0,1,0 )
    sprite( 1,1,1 )

bug_7:
    sprite( 1,1,1 )
    sprite( 1,1,1 )
    sprite( 0,1,1 )
    sprite( 1,1,1 )
    sprite( 1,1,0 )

# Graphics 3 x 5 pixels

letter_0:
    sprite( 1,1,1 )
    sprite( 0,1,0 )
    sprite( 0,1,0 )
    sprite( 0,1,0 )
    sprite( 0,1,0 )

letter_1:
    sprite( 1,0,1 )
    sprite( 1,0,1 )
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,0,1 )

letter_2:
    sprite( 1,1,1 )
    sprite( 1,0,0 )
    sprite( 1,1,1 )
    sprite( 1,0,0 )
    sprite( 1,1,1 )

letter_3:
    sprite( 1,0,0 )
    sprite( 1,0,0 )
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,1,1 )

letter_4:
    sprite( 1,0,1 )
    sprite( 1,0,1 )
    sprite( 1,0,1 )
    sprite( 1,0,1 )
    sprite( 1,1,1 )

letter_5:
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,1,1 )
    sprite( 0,0,1 )
    sprite( 1,1,1 )

letter_6:
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,0,1 )

letter_7:
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,0,1 )
    sprite( 1,0,0 )
    sprite( 1,0,0 )

letter_8:
    sprite( 1,1,1 )
    sprite( 1,0,1 )
    sprite( 1,0,1 )
    sprite( 0,0,1 )
    sprite( 0,0,1 )

string_buf:
    .data 0x00

