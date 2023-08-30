#############################################################################
# YMF825 synthesizer with Raspberry Pi PICO W.
#
# Hardware Information:
#   YMF825 bottom view
#     1 2 3 4 5 6 7 8 9
#    -+-+-+-+-+-+-+-+-+-
#   | S M M C G V R     |
#   | S O I L N C S     |
#   |   S S K D C T     |
#   |   I O             |
#   |             Audio Jack
#    ---------------+---
#                   |
#                    ---Amp
#
#   PICO GPIO(pin)      YMF825 name(pin)    LED(n/a)
#     5V          (40)    VCC        (6)
#     GND         (38)    GND        (5)
#     SPI1 MOSI 19(25)    SPI MOSI   (2)
#     SPI1 MISO 16(21)    SPI MISO   (3)
#     SPI1 CLK  18( 24)    SPI CLK    (4)
#     SPI1 CS   17(22)    SS         (1)
#     RESET     22(29)    RESET      (7)
#n/a  LED       28(34)                      Anode---1K--->|---Cathode---GND
#
# Copyright (c) by Shunsuke Ohira
#   00.100 2023/08/05: Play Do-Re-Mi
#############################################################################

from machine import Pin, SPI
import time

# SPI
SPI_CH = 0
SPI_MAX_SPEED_HZ = 1000000

#GPIO assignment     # Pin No.
SPIPORT_MOSI = 19    # pin25
SPIPORT_MISO = 16    # pin21
SPIPORT_CLK  = 18    # pin24
SPIPORT_CE   = 17    # pin22
YMF825_RESET = 22    # pin29
GPIO_LED     = 28    # pin34    # N/A

# SPI
spi_cs = Pin(SPIPORT_CE, Pin.OUT)
spi = SPI(SPI_CH, sck=Pin(SPIPORT_CLK), mosi=Pin(SPIPORT_MOSI), miso=Pin(SPIPORT_MISO), baudrate=SPI_MAX_SPEED_HZ, firstbit=SPI.MSB, polarity=0, phase=0)

# YMF825 RESET pin
YMF825_reset = Pin(YMF825_RESET, Pin.OUT)

# LED (CURRENTLY NOT AVAILABLE)
led_indicator = Pin(GPIO_LED, Pin.OUT)

#Tone parameter [address(1byte)|data(35byte)]
#sound_param = [0]*36
sound_param = bytearray(36)

#Tone data HI
notenum_hi = (0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x18,0x18,0x18,0x18,0x18,0x20,0x20,0x20,0x20,0x28,0x11,0x11,0x19,0x19,0x19,0x19,0x19,0x21,0x21,0x21,0x21,0x29,0x12,0x12,0x1A,0x1A,0x1A,0x1A,0x1A,0x22,0x22,0x22,0x22,0x2A,0x13,0x13,0x1B,0x1B,0x1B,0x1B,0x1B,0x23,0x23,0x23,0x23,0x2B,0x14,0x14,0x1C,0x1C,0x1C,0x1C,0x1C,0x24,0x24,0x24,0x24,0x2C,0x15,0x15,0x1D,0x1D,0x1D,0x1D,0x1D,0x25,0x25,0x25,0x25,0x2D,0x16,0x16,0x1E,0x1E,0x1E,0x1E,0x1E,0x26,0x26,0x26,0x26,0x2E,0x17,0x17,0x1F,0x1F,0x1F,0x1F,0x1F,0x27,0x27,0x27,0x27,0x2F,0x10,0x10,0x18,0x18,0x18,0x18,0x18,0x20,0x20,0x20,0x20,0x28,0x11,0x11,0x19,0x19,0x19,0x19,0x10,0x1E)
#Tone data LO
notenum_lo = (0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x65,0x5D)


#LED indicator
#  onoff:: True:turn on, False: turn off
def led_turn(onoff):
    led_indicator.value(1 if onoff else 0)


#Wait timer
#  msec:: Waite time in milli-seconds
def delay(msec):
    time.sleep(msec/1000)


#Set SPI Slave Select Pin (CE0)
#  pinv:: GPIO.HIGH: not-select, GPIO.LOW: select
def chip_select(sel):
    spi_cs.value(0 if sel else 1)


#Write byte array data to SPI
#  addr:: SPI register address
#  data_array: byte data in array
def spi_write(addr, data_array):
    chip_select(True)
    data_array[0] = addr
    spi.write(data_array)
    chip_select(False)


#Write one byte data to SPI
#  addr:: SPI register address
#  byte_data: one byte data
def spi_write_byte(addr, byte_data):
    spi_byte_data = bytearray([addr, byte_data])
    chip_select(True)
    spi.write(spi_byte_data)
    chip_select(False)


#Set Chanel
def set_chanel():
    spi_write_byte(0x0F,0x30)
    spi_write_byte(0x10,0x71)
    spi_write_byte(0x11,0x00)
    spi_write_byte(0x12,0x08)
    spi_write_byte(0x13,0x00)


#Note on (play a note)
#  fnumh, fnuml:: 2byte data to play, byte data for a note is in notenum_hi[note] and notenum_lo[note]
def note_on(notenum_h, notenum_l):
    spi_write_byte(0x0B,0x00)
    spi_write_byte(0x0C,0x54)
    spi_write_byte(0x0D,notenum_h)
    spi_write_byte(0x0E,notenum_l)
    spi_write_byte(0x0F,0x40)
    led_turn(True)


#Note off
#  Turn off the note playing
def note_off():
    spi_write_byte(0x0F,0x00)
    led_turn(False)


#Play by a scale name, play time and rest time
#  scale:: "C4", "D5#", "F2", and so on. From "C0" to "G9".
#  play:: note on time(msec)
#  rest:: note off time(msec) after playing the note
def play_by_scale(scale, play, rest):
    t = 999
    c = ""
    
    if len(scale) >= 2:
        t = (int(scale[1])+1)*12
        c = scale[0]
        
        if c == "D":
            t = t+2
        elif c == "E":
            t = t+4
        elif c == "F":
            t = t+5
        elif c == "G":
            t = t+7
        elif c == "A":
            t = t+9
        elif c == "B":
            t = t+11

        if len(scale) == 3:
            if scale[2] == "#":
                t += 1

    if t <= 127:
        print("PLAY:", scale, "=", t, " ", play, "_", rest, "//")
        note_on(notenum_hi[t], notenum_lo[t])
        delay(play)
        note_off()
        delay(rest)
    else:
        print("Unknown scale:", scale)


#Set sound parameters to YMF825
#  sound_param[0]:: byte for register address (to be set it later)
#  sound_param[1..35]:: tone data
def set_sound():
    global sound_param

    #HED: 0,0x81,
    ##Address
    sound_param[ 0]=0
    ##Header
    sound_param[ 1]=0x81

    #BLS: 0x01,0x85,
    ##Basic octave
    sound_param[ 2]=1
    ##LFO*64 + Algolithm
    sound_param[ 3]=2*64+6

    #OP1: 0x00,0x7F,0xF4,0xBB,0x00,0x10,0x40,
    ##OP1:Sustin rate*16 + Ignore key off*8 + Key scale sensitivity
    sound_param[ 4]=0*16+0*8+0
    ##OP1:Release rate*16 + Decay rate
#    sound_param[ 5]=7*16+15
    sound_param[ 5]=15*16+15
    ##OP1:Atack rate*16 + Sustin level
    sound_param[ 6]=15*16+4
    ##OP1:Total operator level*16 + Key scaling level sensitivity
    sound_param[ 7]=11*16+11
    ##OP1:Depth of amp modulation*32 + Enable amp mod*16 + Depth of vibrato*2 + Enable vivlato
    sound_param[ 8]=0*32+0*16+0*2+0
    ##OP1:Multi contol magnification frequency*16 + Detune
    sound_param[ 9]=1*16+0
    ##OP1:Wave shape*8 + FM feedback level
    sound_param[10]=7*64+0

    #OP2: 0x00,0xAF,0xA0,0x0E,0x03,0x10,0x40,
    ##OP2:Sustin rate*16 + Ignore key off*8 + Key scale sensitivity
    sound_param[11]=0*16+0*8+0
    ##OP2:Release rate*16 + Decay rate
    sound_param[12]=10*16+15
    ##OP2:Atack rate*16 + Sustin level
    sound_param[13]=10*16+0
    ##OP2:Total operator level*16 + Key scaling level sensitivity
    sound_param[14]=0*16+14
    ##OP2:Depth of amp modulation*32 + Enable amp mod*16 + Depth of vibrato*2 + Enable vivlato
    sound_param[15]=0*32+0*16+0*2+3
    ##OP2:Multi contol magnification frequency*16 + Detune
    sound_param[16]=1*16+0
    ##OP2:Wave shape*8 + FM feedback level
    sound_param[17]=7*64+0

    #OP3: 0x00,0x2F,0xF3,0x9B,0x00,0x20,0x41,
    ##OP3:Sustin rate*16 + Ignore key off*8 + Key scale sensitivity
    sound_param[18]=0*16+0*8+0
    ##OP3:Release rate*16 + Decay rate
#   sound_param[19]=2*16+15
    sound_param[19]=15*16+15
    ##OP3:Atack rate*16 + Sustin level
    sound_param[20]=15*16+3
    ##OP3:Total operator level*16 + Key scaling level sensitivity
    sound_param[21]=9*16+11
    ##OP3:Depth of amp modulation*32 + Enable amp mod*16 + Depth of vibrato*2 + Enable vivlato
    sound_param[22]=0*32+0*16+0*2+0
    ##OP3:Multi contol magnification frequency*16 + Detune
    sound_param[23]=2*16+0
    ##OP3:Wave shape*8 + FM feedback level
    sound_param[24]=7*64+1

    #OP4: 0x00,0xAF,0xA0,0x0E,0x01,0x10,0x40,
    ##OP4:Sustin rate*16 + Ignore key off*8 + Key scale sensitivity
    sound_param[25]=0*16+0*8+0
    ##OP4:Release rate*16 + Decay rate
    sound_param[26]=10*16+15
    ##OP4:Atack rate*16 + Sustin level
    sound_param[27]=10*16+0
    ##OP4:Total operator level*16 + Key scaling level sensitivity
    sound_param[28]=0*16+14
    ##OP4:Depth of amp modulation*32 + Enable amp mod*16 + Depth of vibrato*2 + Enable vivlato
    sound_param[29]=0*32+0*16+0*2+1
    ##OP4:Multi contol magnification frequency*16 + Detune
    sound_param[30]=1*16+0
    ##OP4:Wave shape*8 + FM feedback level
    sound_param[31]=7*64+0

    #END: 0x80,0x03,0x81,0x80
    sound_param[32]=0x80
    sound_param[33]=0x03
    sound_param[34]=0x81
    sound_param[35]=0x80

    #Burst write mode
    print("YMF85 Burst write mode.")
    spi_write_byte(0x08, 0xF6)
    delay(20)
    spi_write_byte(0x08, 0x00)
  
    #Write tone data to YMF825 FIFO
    print("Write tone data to YMF85.")
    spi_write(0x07, sound_param)


#Set default sound parameters to YMF825
def set_default_sound():
    default_sound = bytearray([0,0x81,0x01,0x85,0x00,0x7F,0xF4,0xBB,0x00,0x10,0x40,0x00,0xAF,0xA0,0x0E,0x03,0x10,0x40,0x00,0x2F,0xF3,0x9B,0x00,0x20,0x41,0x00,0xAF,0xA0,0x0E,0x01,0x10,0x40,0x80,0x03,0x81,0x80])
    spi_write_byte(0x08,0xF6)
    delay(20)
    spi_write_byte(0x08,0x00)
    spi_write(0x07, default_sound)


#Reset and Initialize YMF825
def init_YMF825():
    YMF825_reset.high()
    print("RESET HIGH")
    delay(1000)
    YMF825_reset.low()
    print("RESET LOW")
    delay(1000)
    YMF825_reset.high()
    delay(1000)
    print("Reset YMF825.")
  
    spi_write_byte(0x1D,0x00)
    spi_write_byte(0x02,0x0E)
    delay(20)
  
    spi_write_byte(0x00,0x01)
    spi_write_byte(0x01,0x00)
    spi_write_byte(0x1A,0xA3)
    delay(20)
  
    spi_write_byte(0x1A,0x00)
    delay(40)
  
    spi_write_byte(0x02,0x04)
    delay(20)

    spi_write_byte(0x02,0x00)

    # add
    spi_write_byte(0x19,0xFF)
    spi_write_byte(0x1B,0x3F)
    spi_write_byte(0x14,0x00)
    spi_write_byte(0x03,0x01)

    spi_write_byte(0x08,0xF6)
    delay(40)
    spi_write_byte(0x08,0x00)
    spi_write_byte(0x09,0xF8)
    spi_write_byte(0x0A,0x00)

    spi_write_byte(0x17,0x40)
    spi_write_byte(0x18,0x00)

    print("YMF825 initialized.")


#Set up hardware
def setup():
    print("SPI uses CE0(pin24/port8)")
    led_turn(True)
    chip_select(False)

#    spi = SPI(SPI_CH, sck=Pin(SPIPORT_CLK), mosi=Pin(SPIPORT_MOSI), miso=Pin(SPIPORT_MISO), baudrate=SPI_MAX_SPEED_HZ)
    print("spi object=", spi)

    print("Set up YMF825")
    init_YMF825()
    set_default_sound()
    # set_sound()
    set_chanel()
    
    print("Finished setting up.")
    led_turn(False)


#Initialize application
def init():
    print("Initialize Application.")

    # SPI
#    spi = SPI(SPI_CH, sck=Pin(SPIPORT_CLK), mosi=Pin(SPIPORT_MOSI), miso=Pin(SPIPORT_MISO), baudrate=SPI_MAX_SPEED_HZ)
    spi_cs = Pin(SPIPORT_CE, Pin.OUT)
    
    # YMF825 RESET pin
    YMF825_reset = Pin(YMF825_RESET, Pin.OUT)

    # LED (CURRENTLY NOT AVAILABLE)
    led_indicator = Pin(GPIO_LED, Pin.OUT)


#Keyboard Player
def keyboardPlayer():
    print("NOT AVAILABLE.")


#Main
init()
setup()

print("DoReMi...")
note_on(0x14,0x65)
delay(1000)
note_off()

note_on(0x1C,0x11)
delay(1000)
note_off()

note_on(0x1C,0x42)
delay(1000)
note_off()

note_on(0x1C,0x5D)
delay(1000)
note_off()

note_on(0x24,0x17)
delay(1000)
note_off()

print("DoMiSoDo")
set_sound()
play_by_scale("C4",500,500)
play_by_scale("E4",500,500)
play_by_scale("G4",500,500)
play_by_scale("C5",500,500)

print("DoSoDo")
set_default_sound()
play_by_scale("C5",500,500)
play_by_scale("G4",500,500)
play_by_scale("C5",1000,500)

#print("Play with your keyboard! (Quit=!)")
#keyboardPlayer
print("QUIT.")

#SPISTOP


