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
#     SPI1 CLK  18(24)    SPI CLK    (4)
#     SPI1 CS   17(22)    SS         (1)
#     RESET     22(29)    RESET      (7)
#n/a  LED       28(34)                      Anode---1K--->|---Cathode---GND
#
#   PICO GPIO(pin)      SSD1306 name(pin)    LED(n/a)
#     I2C0 SDA  20(24)    SDA        (4)
#     I2C0 SCL  21(25)    SCL        (3)
#                         GND        (2)
#                         VCC(3.3V)  (1)
#
# Copyright (c) by Shunsuke Ohira
#   00.100 2023/08/05: Play Do-Re-Mi
#   01.000 2023/08/31: UI Editor and MIDI Keyboard are available.
#   01.001 2023/09/04: Databank available
#   01.100 2023/09/06: Sequencer available
#   01.200 2023/09/08: Equalizer available
#   01.210 2023/09/12: GUI for operator volumes and ADSSR
#   01.211 2023/09/13: GUI for Algorithm
#   01.212 2023/09/19: Reduce global variable memory
#   01.300 2023/09/19: Tones in the timbre can be selected from the other databank
#   01.400 2023/09/21: Bi quad filter parameters calculation (LPF, HPF, BPFskt, BPF0db, NOTCH, APF, PEAK)
#   01.500 2023/09/21: MIDI channel can be assigned to each timbre portion
#   01.501 2023/09/22: Ignore Realtime Clock (0xF8) and Active Sensing (0xFE) in MIDI message (too much!!)
#   01.502 2023/09/23: Waiting for receiving parfect MIDI messages via UART to never lost MIDI message
#############################################################################

from ymf825pico import ymf825pico_class
from machine import Pin, I2C, SPI, UART
import ssd1306
import time, os, json, math
import gc

# UART test
UART_CH = 0
UART_TX = 0   # GPIO No.
UART_RX = 1   # GPIO No.
#UART_BAUDRATE = 9600
UART_BAUDRATE = 31250      # MIDI speed

# I2C for SSD1306 OLED Display
I2C_SSD1306_CH = 0
I2C_SSD1306_SDA = 20    # Pin24
I2C_SSD1306_SCL = 21    # Pin25

# SSD1306 OLED Display
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAT_HALF_WIDTH = int(DISPLAY_WIDTH / 2)
DISPLAT_QUOT_WIDTH = int(DISPLAY_WIDTH / 4)
DISPLAY_DIVIDE = 83
DISPLAY_LINE_HEIGHT = 10
DISPLAY_MENU_LINES= 4
display = None

# I2C for SSD1306 OLED Display
i2c_ssd1306 = I2C(I2C_SSD1306_CH, sda=Pin(I2C_SSD1306_SDA), scl=Pin(I2C_SSD1306_SCL))

# Rotary encoders
ROTARY_ENCODERS = [
    # No.     GPIO No.                Pin objects                 Previous pin values       Pjn values             Pin No.
    {"NO": 0, "A_PIN": 2, "B_PIN": 3, "A_SW": None, "B_SW": None, "A_PREV": 2, "B_PREV": 2, "VALUES": [0,0,0,0]},  # Pin 4,  5
    {"NO": 1, "A_PIN": 4, "B_PIN": 5, "A_SW": None, "B_SW": None, "A_PREV": 2, "B_PREV": 2, "VALUES": [0,0,0,0]},  # Pin 6,  7
    {"NO": 2, "A_PIN": 6, "B_PIN": 7, "A_SW": None, "B_SW": None, "A_PREV": 2, "B_PREV": 2, "VALUES": [0,0,0,0]},  # Pin 9, 10
    {"NO": 3, "A_PIN": 8, "B_PIN": 9, "A_SW": None, "B_SW": None, "A_PREV": 2, "B_PREV": 2, "VALUES": [0,0,0,0]}   # Pin11, 12
]

# Timbre portion's volumes10/2go,10/3event,10/4back
timbre_volumes = [1.0] * 4

# YMF825 parameters mapping and order (ABBR, REAL KEY NAME, VALUE RANGE)
PARM_TEXT_OFF_ON = ["OFF", "ON"]
PARM_TEXT_ALGO = ["Ab", "A+b", "A+b+C+d", "(A+bc)d", "Abcd", "Ab+Cd", "A+bcd", "A+bc+d"]
PARM_TEXT_WAVE = [
    "SIN",     "plusSIN", "asbSIN",  "SAIL*2",
    "SIN2x",   "absSN2x", "SQUARE",  "RIBBON",
    "SINcomp", "plusScp", "absScmp", "SAILcmp",
    "SIN2xCp", "plsS2cp", "plusSQR", "-------",
    "TRIANGL", "plusTRI", "absTRIA", "absTRIh",
    "TRIAN2x", "plsTR2x", "plsSQR2", "-----",
    "SAW",     "plusSAW", "absSAW",  "absSAWc",
    "SAW2x",   "absSAW2", "SQUAR/4", "-------"
]
YMF825_PARM = [
    # GENERAL
    ("Basic OCT", "Basic Oct", 4, None),
    ("Algorithm", "Algorithm", 8, PARM_TEXT_ALGO),
    ("LFO", "LFO", 8, None),
    # OP1
    ("Wave Shp A", "Wave Shape1", 32, PARM_TEXT_WAVE),
    ("Total LV A", "Operator Lv1", 32, None),
    ("MCM Freq A", "MCMFreq1", 16, None),
    ("Feedback A", "Feedback Lv1", 8, None),
    ("Detune   A", "Detune1", 8, None),
    ("Atack RT A", "Attack R1", 16, None),
    ("Decay RT A", "Decay R1", 16, None),
    ("Sustn LV A", "Sus Level1", 16, None),
    ("Sustn RT A", "Sus R1", 16, None),
    ("Reles RT A", "Release R1", 16, None),
    ("Vibrt EN A", "Enable Vib1", 2, PARM_TEXT_OFF_ON),
    ("Vibrt DP A", "Depth Vib1", 4, None),
    ("Amp M EN A", "Enable Amp Mod1", 2, PARM_TEXT_OFF_ON),
    ("Amp M DP A", "Depth Amp Mod1", 4, None),
    ("Key S EN A", "KeySc Sens1", 2, PARM_TEXT_OFF_ON),
    ("Key S LV A", "KSL Sens1", 4, None),
    ("IgnKy OF A", "Ign Key Off1", 2, PARM_TEXT_OFF_ON),
    # OP2
    ("Wave Shp B", "Wave Shape2", 32, PARM_TEXT_WAVE),
    ("Total LV B", "Operator Lv2", 32, None),
    ("MCM Freq B", "MCMFreq2", 16, None),
    ("Feedback B", "Feedback Lv2", 8, None),
    ("Detune   B", "Detune2", 8, None),
    ("Atack RT B", "Attack R2", 16, None),
    ("Decay RT B", "Decay R2", 16, None),
    ("Sustn LV B", "Sus Level2", 16, None),
    ("Sustn RT B", "Sus R2", 16, None),
    ("Reles RT B", "Release R2", 16, None),
    ("Vibrt EN B", "Enable Vib2", 2, PARM_TEXT_OFF_ON),
    ("Vibrt DP B", "Depth Vib2", 4, None),
    ("Amp M EN B", "Enable Amp Mod2", 2, PARM_TEXT_OFF_ON),
    ("Amp M DP B", "Depth Amp Mod2", 4, None),
    ("Key S EN B", "KeySc Sens2", 2, PARM_TEXT_OFF_ON),
    ("Key S LV B", "KSL Sens2", 4, None),
    ("IgnKy OF B", "Ign Key Off2", 2, PARM_TEXT_OFF_ON),
    # OP3
    ("Wave Shp C", "Wave Shape3", 32, PARM_TEXT_WAVE),
    ("Total LV C", "Operator Lv3", 32, None),
    ("MCM Freq C", "MCMFreq3", 16, None),
    ("Feedback C", "Feedback Lv3", 8, None),
    ("Detune   C", "Detune3", 8, None),
    ("Atack RT C", "Attack R3", 16, None),
    ("Decay RT C", "Decay R3", 16, None),
    ("Sustn LV C", "Sus Level3", 16, None),
    ("Sustn RT C", "Sus R3", 16, None),
    ("Reles RT C", "Release R3", 16, None),
    ("Vibrt EN C", "Enable Vib3", 2, PARM_TEXT_OFF_ON),
    ("Vibrt DP C", "Depth Vib3", 4, None),
    ("Amp M EN C", "Enable Amp Mod3", 2, PARM_TEXT_OFF_ON),
    ("Amp M DP C", "Depth Amp Mod3", 4, None),
    ("Key S EN C", "KeySc Sens3", 2, PARM_TEXT_OFF_ON),
    ("Key S LV C", "KSL Sens3", 4, None),
    ("IgnKy OF C", "Ign Key Off3", 2, PARM_TEXT_OFF_ON),
    # OP4
    ("Wave Shp D", "Wave Shape4", 32, PARM_TEXT_WAVE),
    ("Total LV D", "Operator Lv4", 32, None),
    ("MCM Freq D", "MCMFreq4", 16, None),
    ("Feedback D", "Feedback Lv4", 8, None),
    ("Detune   D", "Detune4", 8, None),
    ("Atack RT D", "Attack R4", 16, None),
    ("Decay RT D", "Decay R4", 16, None),
    ("Sustn LV D", "Sus Level4", 16, None),
    ("Sustn RT D", "Sus R4", 16, None),
    ("Reles RT D", "Release R4", 16, None),
    ("Vibrt EN D", "Enable Vib4", 2, PARM_TEXT_OFF_ON),
    ("Vibrt DP D", "Depth Vib4", 4, None),
    ("Amp M EN D", "Enable Amp Mod4", 2, PARM_TEXT_OFF_ON),
    ("Amp M DP D", "Depth Amp Mod4", 4, None),
    ("Key S EN D", "KeySc Sens4", 2, PARM_TEXT_OFF_ON),
    ("Key S LV D", "KSL Sens4", 4, None),
    ("IgnKy OF D", "Ign Key Off4", 2, PARM_TEXT_OFF_ON),
]

# Character list
CHARS_LIST= ["="]   # No change
CHARS_LIST += [chr(ch) for ch in list(range(0x41,0x5b))]
#CHARS_LIST += [chr(ch) for ch in list(range(0x61,0x7b))]
CHARS_LIST += [chr(ch) for ch in list(range(0x30,0x3a))]
CHARS_LIST += [" "]

# YMF825pico menu
menu_main = 0
menu_category = 0
menu_item = 0
menu_value = 0
gui_item_menu = None
gui_item_menu_exit = None

#--- YMF825pico menu definitions
# MAIN:PLAY
MAIN_MENU_PLAY = 0

# PLAY>CATEGORY
MAIN_MENU_PLAY_MANUAL = 0
MAIN_MENU_PLAY_EQUALIZER = 1
MAIN_MENU_PLAY_DEMO = 2
MAIN_MENU_PLAY_DATABANK = 3

# MAIN:TIMBRE NAME
MAIN_MENU_TIMBRE_NAME = 1
TIMBRE_NAME_LENGTH = 10

# MAIN:TIMBRE EDIT
MAIN_MENU_TIMBRE_EDIT = 2

# MAIN:TONE NAME
MAIN_MENU_TONE_NAME = 3
TONE_NAME_LENGTH = 10

# MAIN:TONE EDIT
MAIN_MENU_TONE_EDIT = 4

# MAIN:TONE COPY
MAIN_MENU_TONE_COPY = 5

# MAIN:EQUALIZER NAME
MAIN_MENU_EQUALIZER_NAME = 6
EQUALIZER_NAME_LENGTH = 10

# MAIN:EQUALIZER EDIT
MAIN_MENU_EQUALIZER_EDIT = 7


# Edit the tone volume related parameters with GUI
def gui_tone_edit_volumes(gui):
    global menu_main, menu_category, menu_item, menu_value
    global gui_item_menu
    
#    print("GUI EDITOR: TONE VOLUMES:", menu_item, gui)
    gui_item_menu = gui["items"]
    for ui in list(range(len(gui_item_menu))):  
        # Show the current editing VALUE
        i = gui["items"][ui]
        if i == menu_item:
#            print("main, category, item, value=", menu_main, menu_category, i, menu_value)
            value_name = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["VALUE"][menu_value]["name"]
        # Show the selected VALUE
        else:
            selected = int(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"])
#            print("MENU:", menu_main, menu_category, i, selected)
            value_name = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["VALUE"][selected]["name"]

#        print("SHOW=", value_name)
        disp = gui["disp"][ui]
        display.text(disp[0], disp[1], disp[2], True)
        display.text(value_name[:6], disp[1] + 16, disp[2], True)
        if i == menu_item:
            display.hline(disp[1], disp[2] + DISPLAY_LINE_HEIGHT - 2, DISPLAT_QUOT_WIDTH, True)

    display.vline(DISPLAT_HALF_WIDTH, DISPLAY_LINE_HEIGHT * 2 - 2, DISPLAY_HEIGHT - (DISPLAY_LINE_HEIGHT * 2 - 2), True)
    display.hline(0, DISPLAY_LINE_HEIGHT * 4 + 1, DISPLAY_WIDTH, True)


# Edit the tone ADSSL parameters with GUI
def gui_tone_edit_adssls(gui):
    global menu_main, menu_category, menu_item, menu_value
    global gui_item_menu
    
#    print("GUI EDITOR: TONE ADSSLs:", menu_item, gui)
    gui_item_menu = gui["items"]
    parmstr = ["AT", "DC", "SL", "SR", "RR"]
    px = [0, 0, 0, 0, 0]
    py = [0, 0, 0, 0, 0]
    for ui in list(range(len(gui_item_menu))):  
        base = int(ui / 5)
        offset = ui % 5

        # Show the current editing VALUE
        i = gui["items"][ui]
        if i == menu_item:
#            print("main, category, item, value=", menu_main, menu_category, i, menu_value)
            value_parm = menu_value
        # Show the selected VALUE
        else:
            value_parm = int(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"])
#            print("MENU:", menu_main, menu_category, i, value_parm)

#        print("SHOW=", value_parm, "OP=", base)
        base_x = (0 if base % 2 == 0 else DISPLAT_HALF_WIDTH + 2) + 25
        base_y = DISPLAY_LINE_HEIGHT * (4 + (2 if base >= 2 else 0)) + (1 if base >= 2 else -1)

        # Attack
        if offset == 0:
#            print("AT=", value_parm)
            px[1] = (15 - value_parm) / 15.0
            py[1] = 1.0
        # Decay
        elif offset == 1:
#            print("DC=", value_parm)
            px[2] = (15 - value_parm) / 15.0
        # Sustine level
        elif offset == 2:
#            print("SL=", value_parm)
            py[2] = py[1] - value_parm / 15.0
        # Sustain rate
        elif offset == 3:
#            print("SR=", value_parm)
            px[3] = 1.0
            py[3] = py[2] * (15 - value_parm) / 30.0
        elif offset == 4:
#            print("RR=", value_parm)
            px[4] = (15 - value_parm) / 15.0
            py[4] = py[3] if value_parm == 0 else 0
            x0 = 0
            y0 = 0
            for p in list(range(1,5)):
                x1 = x0 + px[p]
                y1 = py[p]
#                print("LINE:",x0, y0, x1, y1)
                display.line(int(x0 * 8) + base_x, base_y - int(y0 * (DISPLAY_LINE_HEIGHT-1)*2), int(x1 * 8) + base_x, base_y - int(y1 * (DISPLAY_LINE_HEIGHT-1)*2), True)
                x0 = x1
                y0 = y1

        disp = [chr(0x41+base)+parmstr[offset], 0 if base % 2 == 0 else DISPLAT_HALF_WIDTH+2, DISPLAY_LINE_HEIGHT*2 if base <= 1 else DISPLAY_LINE_HEIGHT*4+4]
        if i == menu_item:
            display.text(disp[0], disp[1], disp[2], True)
            display.text(str(value_parm), disp[1], disp[2] + DISPLAY_LINE_HEIGHT, True)
            display.hline(disp[1], disp[2] + DISPLAY_LINE_HEIGHT * 2 - 2, int(DISPLAT_QUOT_WIDTH / 2), True)

    display.vline(DISPLAT_HALF_WIDTH, DISPLAY_LINE_HEIGHT * 2 - 2, DISPLAY_HEIGHT - (DISPLAY_LINE_HEIGHT * 2 - 2), True)
    display.hline(0, DISPLAY_LINE_HEIGHT * 4 + 1, DISPLAY_WIDTH, True)


# Edit the tone Algorithm parameters with GUI
def gui_tone_edit_algorithm(gui):
    global menu_main, menu_category, menu_item, menu_value
    global gui_item_menu

    if menu_item == 1:
        value_parm = menu_value
    # Show the selected VALUE
    else:
        value_parm = int(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"])

    display.text("Algorithm:{}".format(value_parm), 0, DISPLAY_LINE_HEIGHT * 2, True)
    if value_parm == 0:
        display.text("A--b-->", 20, DISPLAY_LINE_HEIGHT * 4, True)
    elif value_parm == 1:
        display.text("A--", 20, DISPLAY_LINE_HEIGHT * 3, True)
        display.text("   +-->", 20, DISPLAY_LINE_HEIGHT * 4, True)
        display.text("b--", 20, DISPLAY_LINE_HEIGHT * 5, True)
    elif value_parm == 2:
        display.text("A--+-->", 20, DISPLAY_LINE_HEIGHT * 3, True)
        display.text("b--|", 20, DISPLAY_LINE_HEIGHT * 4 - 1, True)
        display.text("C--|", 20, DISPLAY_LINE_HEIGHT * 5 - 2, True)
        display.text("d--", 20, DISPLAY_LINE_HEIGHT * 6 - 3, True)
    elif value_parm == 3:
        display.text("A-----", 20, DISPLAY_LINE_HEIGHT * 3, True)
        display.text("      +--d-->", 20, DISPLAY_LINE_HEIGHT * 4, True)
        display.text("b--c--", 20, DISPLAY_LINE_HEIGHT * 5, True)
    elif value_parm == 4:
        display.text("A--b--c--d-->", 20, DISPLAY_LINE_HEIGHT * 4, True)
    elif value_parm == 5:
        display.text("A--b--", 20, DISPLAY_LINE_HEIGHT * 3, True)
        display.text("      +-->", 20, DISPLAY_LINE_HEIGHT * 4, True)
        display.text("C--d--", 20, DISPLAY_LINE_HEIGHT * 5, True)
    elif value_parm == 6:
        display.text("A--------", 20, DISPLAY_LINE_HEIGHT * 3, True)
        display.text("         +-->", 20, DISPLAY_LINE_HEIGHT * 4, True)
        display.text("b--c--d--", 20, DISPLAY_LINE_HEIGHT * 5, True)
    elif value_parm == 7:
        display.text("   A--", 20, DISPLAY_LINE_HEIGHT * 3, True)
        display.text("b--c--+-->", 20, DISPLAY_LINE_HEIGHT * 4, True)
        display.text("   d--", 20, DISPLAY_LINE_HEIGHT * 5, True)


# GUI editor definitions
GUI_EDITOR = [
    # Algorithm
    {"items": [1],
     "func": gui_tone_edit_algorithm,
     "disp": None
    },
    # Wave Shape, Total Volume, Multi Control Magnification Frequency
    {"items": [3, 4, 5, 20, 21, 22, 37, 38, 39, 54, 55, 56],
     "func": gui_tone_edit_volumes,
     "disp": [
         ("A:", 0, DISPLAY_LINE_HEIGHT*2), ("V:", 0, DISPLAY_LINE_HEIGHT*3), ("M:", DISPLAT_QUOT_WIDTH, DISPLAY_LINE_HEIGHT*3),
         ("B:", DISPLAT_HALF_WIDTH+2, DISPLAY_LINE_HEIGHT*2), ("V:", DISPLAT_HALF_WIDTH+2, DISPLAY_LINE_HEIGHT*3), ("M:", DISPLAT_HALF_WIDTH+DISPLAT_QUOT_WIDTH+2, DISPLAY_LINE_HEIGHT*3),
         ("C:", 0, DISPLAY_LINE_HEIGHT*4+4), ("V:", 0, DISPLAY_LINE_HEIGHT*5+4), ("M:", DISPLAT_QUOT_WIDTH, DISPLAY_LINE_HEIGHT*5+4),
         ("D:", DISPLAT_HALF_WIDTH+2, DISPLAY_LINE_HEIGHT*4+4), ("V:", DISPLAT_HALF_WIDTH+2, DISPLAY_LINE_HEIGHT*5+4), ("M:", DISPLAT_HALF_WIDTH+DISPLAT_QUOT_WIDTH+2, DISPLAY_LINE_HEIGHT*5+4)
              ]
    },
    # ADSSL
    {"items": [8, 9, 10, 11, 12, 25, 26, 27, 28, 29, 42, 43, 44, 45, 46, 59, 60, 61, 62, 63],
     "func": gui_tone_edit_adssls,
     "disp": None
    }
]


# Show menu
# item_move_dir: 1=item list down, -1=item list up
# slide: Number of characters to slide the vertical line diveding the item and value regions
# str_head: True = Get the item string from head / Faluse = from tail
item_menu_display_start = 0
def show_menu(item_move_dir, slide=0, str_head=True):
    global item_menu_display_start
    global menu_main, menu_category, menu_item, menu_value
    global gui_item_menu, gui_item_menu_exit

    # Get the next menu number of menu_item in gui_items list
    def get_next_to_gui_editor(gui_items, menu_item):
        find_next = menu_item
        for i in list(range(len(gui_items))):
            if gui_items[i] == find_next:
                find_next += 1
                
        find_prev = menu_item
        for i in reversed(range(len(gui_items))):
            if gui_items[i] == find_prev:
                find_prev -= 1
                
        return (find_prev, find_next)

#    print(SYNTH_MENU)
#    print(menu_main, menu_category, menu_item, menu_value)

    # Vertical divide point
    v_divide = DISPLAY_DIVIDE - slide * 8

    # Show MAIN and CATEGORY
    main_name = SYNTH_MENU[menu_main]["name"]
    category_name = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["name"]
    if main_name == "PLAY":
        main_name = main_name + ":BANK=" + str(YMF825pico.get_databank())

    elif main_name == "TONE EDIT":
        selected = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][1]["selected"]
        algo = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][1]["VALUE"][selected]["name"]
#        print("ALGO=", menu_main, menu_category, selected, algo)
        main_name = main_name + ":" + algo

    display.fill(0)
    display.text(main_name, 0, 0, True)
    display.hline(0, DISPLAY_LINE_HEIGHT - 2, DISPLAY_WIDTH, True)
    display.text(category_name, 0, DISPLAY_LINE_HEIGHT, True)
    display.hline(0, DISPLAY_LINE_HEIGHT * 2 - 2, DISPLAY_WIDTH, True)
    
    # Use GUI Editor
    if menu_main == MAIN_MENU_TONE_EDIT:
        for gui in GUI_EDITOR:
#            print("GUI CHECK:", menu_item, gui)
            if menu_item in gui["items"]:
                if gui_item_menu_exit is None:
                    gui_item_menu_exit = get_next_to_gui_editor(gui["items"], menu_item)
#                    print("NEXT ITEM MENU=", gui_item_menu_exit)

                gui["func"](gui)
                display.show()
                return

    # Text Editor Menu
    gui_item_menu = None
    gui_item_menu_exit = None

    # Show ITEM and VALUE
    display.vline(v_divide, DISPLAY_LINE_HEIGHT * 2 - 2, DISPLAY_HEIGHT - (DISPLAY_LINE_HEIGHT * 2 - 2), True)
    items = len(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"])
    if menu_item < DISPLAY_MENU_LINES:
        menu_s = 0
    elif menu_item >= items - DISPLAY_MENU_LINES:
        menu_s = items - DISPLAY_MENU_LINES
    elif item_move_dir == 1 and menu_item >= item_menu_display_start + DISPLAY_MENU_LINES:
        menu_s = item_menu_display_start + 1
    elif item_move_dir == -1 and menu_item < item_menu_display_start:
        menu_s = item_menu_display_start - 1
    else:
        menu_s = item_menu_display_start

#    print("MOVE DIR, s, e=", item_move_dir, menu_s, menu_s + DISPLAY_MENU_LINES)
    item_menu_display_start = menu_s
    y = DISPLAY_LINE_HEIGHT * 2
    for i in list(range(menu_s, min(items, menu_s + DISPLAY_MENU_LINES))):
        # Show ITEM
        item_name = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["name"]
        display.text(item_name if slide == 0 else item_name[0:10-slide] if str_head else item_name[slide-10:], 0, y, True)
        
        # Show the current editing VALUE
        if i == menu_item:
#            print("main, category, item, value=", menu_main, menu_category, i, menu_value)
            value_name = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["VALUE"][menu_value]["name"]
            display.hline(0, y + DISPLAY_LINE_HEIGHT - 2, DISPLAY_WIDTH, True)
        # Show the selected VALUE
        else:
            selected = int(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"])
#            print("MENU:", menu_main, menu_category, i, selected)
            value_name = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["VALUE"][selected]["name"]

#        print("SHOW=", value_name)
        display.text(value_name, v_divide + 2, y, True)
        y += DISPLAY_LINE_HEIGHT

    display.show()


# Clear list memory for SYNTH_MENU
def clear_menu_memory(prev, clear_category, clear_item, clear_value):
    global menu_main, menu_category, menu_item, menu_value

    if prev < 0:
        return

    target_main = menu_main
    target_category = menu_category
    target_item = menu_item

    if clear_category:
        target_main = prev
        menu_category = 0
        menu_item = 0
        menu_value = 0

    elif clear_item:
        target_category = prev
        menu_item = 0
        menu_value = 0

    elif clear_value:
        target_item = prev
        menu_value = 0
        
#    print("CLEAR:", clear_category, clear_item, clear_value)
#    print("TARGET: MAIN={} CATEGORY={} ITEM={}".format(target_main, target_category, target_item))
#    print("LENGTH: CATEGORY={} ITEM={} VALUE={}".format(len(SYNTH_MENU[target_main]["CATEGORY"]), len(SYNTH_MENU[target_main]["CATEGORY"][target_category]["ITEM"]), len(SYNTH_MENU[target_main]["CATEGORY"][target_category]["ITEM"][target_item]["VALUE"])))
    if clear_value:
        del SYNTH_MENU[target_main]["CATEGORY"][target_category]["ITEM"][target_item]["VALUE"]
        SYNTH_MENU[target_main]["CATEGORY"][target_category]["ITEM"][target_item]["VALUE"] = []

    if clear_item:
        del SYNTH_MENU[target_main]["CATEGORY"][target_category]["ITEM"]
        SYNTH_MENU[target_main]["CATEGORY"][target_category]["ITEM"] = []

    if clear_category:
        del SYNTH_MENU[target_main]["CATEGORY"]
        SYNTH_MENU[target_main]["CATEGORY"] = []

    gc.collect()


#--- MAIN MENU: PLAY
# Make select play menu (PLAY)
def make_select_play_menu(menu, prev_menu):
    clear_menu_memory(prev_menu, True, True, True)

    SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"] = [
        {   # MAIN_MENU_PLAY_MANUAL
            "name": "MANUAL",
            "on_select": make_select_manual_menu,
            "on_selected": None,
            "ITEM": []
        },
        {   # MAIN_MENU_PLAY_EQUALIZER
            "name": "EQUALIZER",
            "on_select": make_select_equalizer_menu,
            "on_selected": None,
            "ITEM": []
        },
        {   # MAIN_MENU_PLAY_DEMO
            "name": "DEMO",
            "on_select": make_select_demo_menu,
            "on_selected": None,
            "ITEM": []
        },
        {   # MAIN_MENU_PLAY_DATABANK
            "name": "DATABANK",
            "on_select": make_select_databank_menu,
            "on_selected": None,
            "ITEM": []
        }
    ]

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_select"](0, -1)

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_select"](0, -1)

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"]()


#--- CATEGORY MENU: MANUAL
# Make select timbre menu (PLAY>MANUAL>timbre list>selelct)
def make_select_manual_menu(menu, prev_menu):
    clear_menu_memory(prev_menu, False, True, True)

    tmb_list = YMF825pico.get_synth_timbre_names()
    SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_MANUAL]["ITEM"] = []
    SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_MANUAL]["ITEM"].append({"name": "NOTES OFF", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_select_timbre, "on_selected": None}, {"name": None}]})
    timbre_value =[{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SET", "on_select": on_select_timbre, "on_selected": None}, {"name": None}]
    for tmb in tmb_list:
        # VALUES.name is None means this is a straight forward item menu (not rotary menu)
        SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_MANUAL]["ITEM"].append({"name": tmb, "on_select": None, "on_selected": None, "selected": 0, "VALUE": timbre_value})


#--- CATEGORY MENU: EQUALIZER
# Make select demo menu (PLAY>MANUAL>equalizer list>selelct)
def make_select_equalizer_menu(menu, prev_menun):
    eq_list = YMF825pico.get_synth_equalizer_names()
    SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_EQUALIZER]["ITEM"] = []
    for eq in eq_list:
        SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_EQUALIZER]["ITEM"].append({"name": eq, "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SET", "on_select": None, "on_selected": on_set_equalizer}, {"name": None}]})


#--- CATEGORY MENU: DEMO
# Make select demo menu (PLAY>MANUAL>demo list>selelct)
def make_select_demo_menu(menu, prev_menu):
    clear_menu_memory(prev_menu, False, True, True)

#    demo_list = ["demo1", "demo2", "demo3"]
    score_path = "./scores/"
#    demo_list = [f for f in os.listdir(score_path) if os.path.isfile(os.path.join(score_path, f))]
    demo_list = [f.replace(".txt", "") for f in os.listdir(score_path)]
    demo_list.sort()
    SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_DEMO]["ITEM"] = []
    for demo in demo_list:
        SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_DEMO]["ITEM"].append({"name": demo, "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "PLAY", "on_select": None, "on_selected": on_play_demo}, {"name": None}]})


#--- CATEGORY MENU: DATABANK
# Make select databank menu (PLAY>DATABANK>0..9>selelct)
def make_select_databank_menu(menu, prev_menu):
    clear_menu_memory(prev_menu, False, True, True)

    SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_DATABANK]["ITEM"] = []
    for databank in list(range(YMF825pico.DATABANK_MAX)):
        SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_DATABANK]["ITEM"].append({"name": str(databank), "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "LOAD", "on_select": None, "on_selected": on_change_databank}, {"name": None}]})


# Select a timbre on the menu
def on_select_timbre():
    global timbre_volumes

    # All notes off
    if menu_item == 0:
        YMF825pico.all_notes_off()

    # Set new timbre to YMF825pico class, then send a change timbre command to YMF825
    else:
#        print("CHANGE TIMBRE TO ", SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["name"])
        timbre = menu_item - 1
        YMF825pico.set_synth_play_timbre(timbre)
        YMF825pico.set_timbre_tones(timbre)
        for prt in list(range(YMF825pico.TIMBRE_PORTIONS)):
            timbre_volumes[prt] = YMF825pico.get_timbre_volume(timbre, prt) / 31.0


# Set an equalizer
def on_set_equalizer():
    YMF825pico.set_synth_equalizer(menu_item)


# Play a demo score
def on_play_demo(demo=None, clear_menu_value=True):
    global menu_main, menu_category, menu_item, menu_value

    # Play a demo
    if demo is None:
        demo = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["name"]

#    print("PLAY DEMO=", demo)
    piano_role_player(score_file=demo + ".txt")
#    print("DEMO END:", menu_category, menu_item, SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"])
    if clear_menu_value:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = 0
        menu_value = 0
        show_menu(0)


current_databank = 0
def load_current_databank():
    global databank_copy_to, current_databank

    # Load databak
    YMF825pico.set_databank(current_databank)
    # Load tone data
    YMF825pico.load_tone_data()
    # load timbre data
    YMF825pico.load_timbre_data()
    # load equalizer data
    YMF825pico.load_equalizer_data()


def on_change_databank():
    global databank_copy_to, current_databank

    databank = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["name"]
    current_databank = menu_item
    databank_copy_to = menu_item
#    print("LOAD DATABANK=", YMF825pico.get_databank(), "/", databank)
    load_current_databank()

    menu_value = 0
    make_select_databank_menu(menu_category, menu_category)
    show_menu(0)


#--- MAIN MENU: TIMBRE NAME
# Make edit timbre name menu (TIMBRE>timbre list>timbre name>selelct)
def make_edit_timbre_name_menu(menu, prev_menu):
    clear_menu_memory(prev_menu, True, True, True)

    values = []
    for ch in CHARS_LIST:
        values.append({"name": ch, "on_select": on_change_char, "on_selected": None})

    timbre_list = YMF825pico.get_synth_timbre_names()
    SYNTH_MENU[MAIN_MENU_TIMBRE_NAME]["CATEGORY"] = []
    for timbre in timbre_list:
#        values = []
#        for ch in CHARS_LIST:
#            values.append({"name": ch, "on_select": on_change_char, "on_selected": None})

        # Current timbre name as ITEM menu
        item = []
        for i in list(range(TIMBRE_NAME_LENGTH)):
            ch = timbre[i:i+1]
            if ch == "":
                ch = " "
            item.append({"name": ch, "on_select": None, "on_selected": None, "selected": 0, "VALUE": values})

        item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_timbre_name, "on_selected": None}, {"name": None}]})
        item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_timbre_name, "on_selected": None}, {"name": None}]})

        SYNTH_MENU[MAIN_MENU_TIMBRE_NAME]["CATEGORY"].append({"name": timbre, "on_select": None, "on_selected": None, "ITEM": item})


# Cancel the changes to timbre name
def on_cancel_timbre_name():
    global menu_main, menu_category, menu_item, menu_value

    # Clear selected data and initialize the TIMBRE NAME menu
    menu_item = 0
    for itm in SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"]:
        itm["selected"] = 0

    menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
    show_menu(0)


# Change a timbre name and save all timbre data
def on_save_timbre_name():
    global menu_main, menu_category, menu_item, menu_value

    # Change the current tone name
    name = ""
    for i in list(range(TIMBRE_NAME_LENGTH)):
        ch = CHARS_LIST[SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"]]
        name += ch if ch != CHARS_LIST[0] else SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["name"]

#    print("CHANGE TIMBRE NAME[{}]={}".format(menu_category, name))
    YMF825pico.rename_timbre(menu_category, name)

    # Save tone data
    YMF825pico.save_timbre_data()
    gc.collect()

    # Initialize the TONE NAME menu
    make_edit_timbre_name_menu(menu_main, menu_main)
    on_cancel_timbre_name()


#--- MAIN MENU: TIMBRE EDIT
# Make timbre edit menu
db_values_tone = None
def make_edit_timbre_edit_menu(menu, prev_menu):
    global db_values_tone

    clear_menu_memory(prev_menu, True, True, True)

    '''
    tone_list = YMF825pico.get_synth_tone_names()
    values_tone = []
    for tone in tone_list:
        values_tone.append({"name": tone, "on_select": on_change_timbre_edit, "on_selected": None})
    '''
    
    values_databank = []
    for voice in list(range(10)):
        values_databank.append({"name": str(voice), "on_select": on_change_timbre_databank, "on_selected": None})

    values_voice = []
    for voice in list(range(16)):
        values_voice.append({"name": str(voice), "on_select": on_change_timbre_edit, "on_selected": None})

    values_volume = []
    for volume in list(range(32)):
        values_volume.append({"name": str(volume), "on_select": on_change_timbre_edit, "on_selected": None})

    values_midich = values_volume[1:17]

    if db_values_tone is not None:
        del db_values_tone
    db_values_tone = [None] * YMF825pico.DATABANK_MAX

    timbre_list = YMF825pico.get_synth_timbre_names()
#    print("TIMBER LIST:", timbre_list)
    SYNTH_MENU[MAIN_MENU_TIMBRE_EDIT]["CATEGORY"] = []
    timbre_id = 0
    for timbre in timbre_list:

        # TIMBER SET ITEM menu
        item = []
        for portion in list(range(YMF825pico.TIMBRE_PORTIONS)):
            db = YMF825pico.get_timbre_databank(timbre_id, portion)
            item.append({"name": "DATABANK{}".format(portion), "on_select": None, "on_selected": None, "selected": db, "VALUE": values_databank})

#            print("DATABANK IS ", timbre_id, portion, db)
            if db_values_tone[db] is None:
                db_values_tone[db] = values_tone_names_in_databank(db)
            item.append({"name": "TONE{}".format(portion), "on_select": None, "on_selected": None, "selected": YMF825pico.get_timbre_tone(timbre_id, portion), "VALUE": db_values_tone[db]})
#            item.append({"name": "TONE{}".format(portion), "on_select": None, "on_selected": None, "selected": YMF825pico.get_timbre_tone(timbre_id, portion), "VALUE": values_tone})

            item.append({"name": "VOICE L{}".format(portion), "on_select": None, "on_selected": None, "selected": YMF825pico.get_timbre_voice_from(timbre_id, portion), "VALUE": values_voice})
            item.append({"name": "VOICE H{}".format(portion), "on_select": None, "on_selected": None, "selected": YMF825pico.get_timbre_voice_to(timbre_id, portion), "VALUE": values_voice})
            item.append({"name": "VOLUME{}".format(portion), "on_select": None, "on_selected": None, "selected": YMF825pico.get_timbre_volume(timbre_id, portion), "VALUE": values_volume})
            item.append({"name": "MIDI CH{}".format(portion), "on_select": None, "on_selected": None, "selected": YMF825pico.get_timbre_portion_midich(timbre_id, portion) - 1, "VALUE": values_midich})

        item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_timbre_edit, "on_selected": None}, {"name": None}]})
        item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_timbre_edit, "on_selected": None}, {"name": None}]})

        SYNTH_MENU[MAIN_MENU_TIMBRE_EDIT]["CATEGORY"].append({"name": timbre, "on_select": None, "on_selected": None, "ITEM": item})
        timbre_id += 1

    gc.collect()


def on_change_timbre_edit():
    global menu_main, menu_category, menu_item, menu_value
    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = menu_value


def values_tone_names_in_databank(databank):
    global menu_main, menu_category, menu_item, menu_value

    #  SOS: Load tone name list in the databank
#    print("DATABANK = ", databank)
    try:
        file = open( "YMF825ToneName" + str(databank) + ".txt", encoding = YMF825pico.file_encode )
    except OSError as e:
#        print(e)
        tone_list = []
    else:
        tone_list = json.load(file)
        file.close()
        
    file = None
    gc.collect()

    # Set value list for the timbre portion
    values_tone = []
    for tone in tone_list:
        values_tone.append({"name": tone, "on_select": on_change_timbre_edit, "on_selected": None})

    return values_tone


def on_change_timbre_databank():
    global db_values_tone
    global menu_main, menu_category, menu_item, menu_value
#    print("TIMBRE PORTION, DATABANK=", menu_item, menu_value)
    
    # Selected databank
    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = menu_value

    # New tone list
    if db_values_tone[menu_value] is None:
        db_values_tone[menu_value] = values_tone_names_in_databank(menu_value)

    # Clear the current tone list
    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item + 1]["VALUE"] = db_values_tone[menu_value]
    show_menu(0)


def on_cancel_timbre_edit():
    global menu_main, menu_category, menu_item, menu_value

    # Clear selected data and initialize the TIMBRE NAME menu
    menu_item = 0
    make_edit_timbre_edit_menu(menu_main, menu_main)
    menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
    show_menu(0)


def on_save_timbre_edit():
    global menu_main, menu_category, menu_item, menu_value

    # Change the current timbre settings
#    print("CHANGE TIMBRE SETTINGS[{}]".format(menu_category))
    for portion in list(range(YMF825pico.TIMBRE_PORTIONS)):
        i = portion * 6
        databank = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"]
        YMF825pico.set_timbre_portion_databank(menu_category, portion, databank)

        tone = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i+1]["selected"]
        YMF825pico.set_timbre_portion_tone(menu_category, portion, tone)

        vfrom = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i+2]["selected"]
        vto   = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i+3]["selected"]
        YMF825pico.set_timbre_voice_range(menu_category, portion, vfrom, vto)

        volume = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i+4]["selected"]
        YMF825pico.set_timbre_portion_volume(menu_category, portion, volume)

#        midich = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i+5]["selected"]
#        YMF825pico.set_timbre_portion_midich(menu_category, portion, midich)
        YMF825pico.set_timbre_portion_midich(menu_category, portion, SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i+5]["selected"] + 1)

    # Save timbre data
    YMF825pico.save_timbre_data()
    gc.collect()
    on_cancel_timbre_edit()


#--- MAIN MENU: TONE NAME
# Make edit tone name menu (TONE>tone list>tone name>selelct)
def make_edit_tone_name_menu(menu, prev_menu):
    clear_menu_memory(prev_menu, True, True, True)

    values = []
    for ch in CHARS_LIST:
        values.append({"name": ch, "on_select": on_change_char, "on_selected": None})

    tone_list = YMF825pico.get_synth_tone_names()
    SYNTH_MENU[MAIN_MENU_TONE_NAME]["CATEGORY"] = []
    for tone in tone_list:
#        values = []
#        for ch in CHARS_LIST:
#            values.append({"name": ch, "on_select": on_change_char, "on_selected": None})

        # Current tone name as ITEM menu
        item = []
        for i in list(range(TONE_NAME_LENGTH)):
            ch = tone[i:i+1]
            if ch == "":
                ch = " "
            item.append({"name": ch, "on_select": None, "on_selected": None, "selected": 0, "VALUE": values})

        item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_tone_name, "on_selected": None}, {"name": None}]})
        item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_tone_name, "on_selected": None}, {"name": None}]})

        SYNTH_MENU[MAIN_MENU_TONE_NAME]["CATEGORY"].append({"name": tone, "on_select": None, "on_selected": None, "ITEM": item})


# Change a character data
def on_change_char():
    global menu_main, menu_category, menu_item, menu_value
    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = menu_value


# Cancel the changes to tone name
def on_cancel_tone_name():
    global menu_main, menu_category, menu_item, menu_value

    # Clear selected data and initialize the TONE NAME menu
    menu_item = 0
    for itm in SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"]:
        itm["selected"] = 0

    menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
    show_menu(0)


# Change a tone name and save all tone data
def on_save_tone_name():
    global menu_main, menu_category, menu_item, menu_value

    # Change the current tone name
    name = ""
    for i in list(range(TONE_NAME_LENGTH)):
        ch = CHARS_LIST[SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"]]
        name += ch if ch != CHARS_LIST[0] else SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["name"]

#    print("CHANGE TONE NAME[{}]={}".format(menu_category, name))
    YMF825pico.rename_tone(menu_category, name)

    # Save tone data
    YMF825pico.save_tone_data()
    gc.collect()

    # Initialize the TONE NAME menu
    make_edit_tone_name_menu(menu_main, menu_main)
    on_cancel_tone_name()


#--- MAIN MENU: TONE EDIT
# Make edit tone edit menu (TONE EDIT>tone list>parameter name>selelct)
def make_edit_tone_edit_menu(menu, prev_menu):
    clear_menu_memory(prev_menu, True, True, True)

    tone_list = YMF825pico.get_synth_tone_names()
    SYNTH_MENU[MAIN_MENU_TONE_EDIT]["CATEGORY"] = []
    for tone in tone_list:
        SYNTH_MENU[MAIN_MENU_TONE_EDIT]["CATEGORY"].append({"name": tone, "on_select": on_select_tone_edit_tone, "on_selected": None, "ITEM": None})

    SYNTH_MENU[MAIN_MENU_TONE_EDIT]["CATEGORY"][menu_category]["on_select"](menu_item, -1)


# Make tone editor menu
def on_select_tone_edit_tone(menu, prev_menu):
    # Remake ITEM>VALUE menu
#    print("MENU={} CLEAR PREV={}".format(menu, prev_menu))
    clear_menu_memory(prev_menu, False, True, True)

    # Get tone data for editing
    tone_hash = YMF825pico.copy_tone_data_for_edit(menu_category)
#    print("TONE HASH[{}]:".format(menu_category))

    values_parm = []
    for num in list(range(32)):
        values_parm.append({"name": str(num), "on_select": on_change_tone_parm, "on_selected": None})
        
    item = []
    for parm_def in YMF825_PARM:
        parm = parm_def[0]        
#        print("PARM[{}/{}] = {}".format(parm, parm_def[1], tone_hash[parm_def[1]]))
        if parm_def[3] is None:
            item.append({"name": parm, "on_select": on_select_tone_parm, "on_selected": None, "selected": tone_hash[parm_def[1]], "VALUE": values_parm[0:parm_def[2]]})
        else:
            item.append({"name": parm, "on_select": on_select_tone_parm, "on_selected": None, "selected": tone_hash[parm_def[1]], "VALUE": [{"name": nm, "on_select": on_change_tone_parm, "on_selected": None} for nm in parm_def[3]]})

    adssl_values = [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_copy_adssl, "on_selected": None}, {"name": None}]
    item.append({"name": "CPadsl A>B", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl A>C", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl A>D", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl B>A", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl B>C", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl B>D", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl C>A", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl C>B", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl C>D", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl D>A", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl D>B", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})
    item.append({"name": "CPadsl D>C", "on_select": None, "on_selected": None, "selected": 0, "VALUE": adssl_values})

    item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_tone_edit, "on_selected": None}, {"name": None}]})
    item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_tone_edit, "on_selected": None}, {"name": None}]})
    SYNTH_MENU[MAIN_MENU_TONE_EDIT]["CATEGORY"][menu_category]["ITEM"] = item

    # Set EDITING Timbre
    YMF825pico.save_edited_data_to_tone(0)
    YMF825pico.set_synth_play_timbre(0)
    YMF825pico.set_timbre_tones(0)
    for prt in list(range(YMF825pico.TIMBRE_PORTIONS)):
        timbre_volumes[prt] = YMF825pico.get_timbre_volume(0, prt) / 31.0


def on_select_tone_parm(menu, prev_menu):
    if reflect_tone_edit():
        on_play_demo("demo1", False)


def on_change_tone_parm():
    global menu_main, menu_category, menu_item, menu_value
    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = menu_value


def on_cancel_tone_edit():
    global menu_main, menu_category, menu_item, menu_value

    # Clear selected data and initialize the TONE NAME menu
    menu_item = 0
    on_select_tone_edit_tone(menu_category, menu_category)
    menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
    show_menu(0)


prev_parm_hash = {}
def reflect_tone_edit(force_save = False):
    global menu_main, menu_category, menu_item, menu_value, prev_parm_hash

    # Make edited tone parameters' hash
    parm_hash = {}
    for parm_def in YMF825_PARM:
        abbr = parm_def[0]
        pkey = parm_def[1]
        for item in SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"]:
            if item["name"] == abbr:
                parm_hash[pkey] = item["selected"]

    # Save tone parameters' data
    if force_save or parm_hash != prev_parm_hash:
#        for parm in parm_hash.keys():
#            print("PARM[{}] = {}".format(parm, parm_hash[parm]))

        YMF825pico.set_editing_tone(parm_hash)
        YMF825pico.save_edited_data_to_tone(0)
        YMF825pico.set_synth_play_timbre(0)
        YMF825pico.set_timbre_tones(0)
        prev_parm_hash = parm_hash.copy()
        return True
    else:
#        print("PARM NOT CHANGED.")
        return False


# Save the all tone data to the current databank
def on_save_tone_edit():
    if reflect_tone_edit(True):
        YMF825pico.save_edited_data_to_tone(menu_category)
        YMF825pico.save_tone_data()
        gc.collect()

    on_play_demo("demo1", False)
    on_cancel_tone_edit()


# Copy ADSL 71..82 (A>B=71 adssl=8..12)
def on_copy_adssl():
    base = menu_item - 71
    copy_from = int(base / 3)
    copy_to = base % 3
    if copy_to >= copy_from:
        copy_to += 1

#    print("COPY ADSSL:", copy_from, copy_to)
    copy_from = 3 + copy_from * 17 + 5
    copy_to = 3 + copy_to * 17 + 5
#    print("COPY ADSSL:", copy_from, copy_to)
    adssl = 0
    while adssl <= 4:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][copy_to + adssl]["selected"] = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][copy_from + adssl]["selected"]
        adssl += 1

    if reflect_tone_edit():
        on_play_demo("demo1", False)


#--- MAIN MENU: TONE COPY
# Make edit tone copy menu (TONE COPY>tone list>tone list>selelct)
databank_copy_to = 0
def make_edit_tone_copy_menu(menu, prev_menu):
    clear_menu_memory(prev_menu, True, True, True)

    tone_list = YMF825pico.get_synth_tone_names()
    SYNTH_MENU[MAIN_MENU_TONE_COPY]["CATEGORY"] = []
    for tone in tone_list:
        SYNTH_MENU[MAIN_MENU_TONE_COPY]["CATEGORY"].append({"name": tone, "on_select": on_select_tone_copy_tone, "on_selected": None, "ITEM": None})

    SYNTH_MENU[MAIN_MENU_TONE_COPY]["CATEGORY"][menu_category]["on_select"](menu_item, -1)
    

# Make copy target tone list as the item list
def on_select_tone_copy_tone(menu, prev_menu):
    global databank_copy_to
    global menu_main, menu_category, menu_item, menu_value, prev_parm_hash

    clear_menu_memory(prev_menu, False, True, True)

    item = []
    values_parm = []
    for bank in list(range(10)):
        values_parm.append({"name": str(bank), "on_select": None, "on_selected": on_change_databank_copy_to})
    menu_value = databank_copy_to
#    print("ITEM DATABANK=", databank_copy_to, menu_item)
    item.append({"name": "DATABANK", "on_select": None, "on_selected": None, "selected": databank_copy_to, "VALUE": values_parm})

    values_parm = [
        {"name": "NO", "on_select": None, "on_selected": None},
        {"name": "SURE?", "on_select": None, "on_selected": None},
        {"name": "YES", "on_select": on_change_copy_parm, "on_selected": None}
    ]

    try:
        file = open( "YMF825ToneName" + str(databank_copy_to) + ".txt", encoding = YMF825pico.file_encode )
    except OSError as e:
#        print(e)
        tone_list = []
    else:
        tone_list = json.load(file)
        file.close()
        
    file = None

#    tone_list = YMF825pico.get_synth_tone_names()
    for tone in tone_list:
        item.append({"name": tone, "on_select": None, "on_selected": None, "selected": 0, "VALUE": values_parm})

#    item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_tone_edit, "on_selected": None}, {"name": None}]})
#    item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_tone_edit, "on_selected": None}, {"name": None}]})
    SYNTH_MENU[MAIN_MENU_TONE_COPY]["CATEGORY"][menu_category]["ITEM"] = item
    show_menu(0)


# Change databank to copy to
def on_change_databank_copy_to():
    global databank_copy_to
    global menu_main, menu_category, menu_item, menu_value, prev_parm_hash
    
    databank_copy_to = menu_value
    on_select_tone_copy_tone(menu_item, -1)


# Copy a tone to another one in the selected databank
def on_change_copy_parm():
    global databank_copy_to
    global menu_main, menu_category, menu_item, menu_value, prev_parm_hash

    tone_copy_to = menu_item - 1
#    print("Copy tone {} to DATABANK{}:{}.".format(menu_category, databank_copy_to, tone_copy_to))

    # Load the databank tones to copy to
    try:
        file = open("YMF825ToneParm" + str(databank_copy_to) + ".txt", encoding = YMF825pico.file_encode)
    except OSError as e:
#        print(e)
        return
    else:
        tone_parm = json.load(file)
        file.close()
        
    # Get tone data for editing
    tone_hash = YMF825pico.copy_tone_data_for_edit(menu_category)
    sound_param = YMF825pico.make_sound_param(tone_hash)
#    print("DATABANK TONES=", tone_parm)
#    print("TONE TO COPY  =", tone_hash)
#    print("PARM TO COPY  =", sound_param)
    tone_parm[tone_copy_to] = sound_param
#    print("COPY PARAMS   =", tone_parm)

    try:
        file = open("YMF825ToneParm" + str(databank_copy_to) + ".txt", "w", encoding = YMF825pico.file_encode)
    except OSError as e:
        pass
#        print(e)
    else:
        json.dump(tone_parm, file)
        file.close()

    # Reload tone data
    if current_databank == databank_copy_to:
        load_current_databank()

#        print("TONE HASH[{}]:".format(menu_category))
#        YMF825pico.set_editing_tone(tone_hash)
#        YMF825pico.save_edited_data_to_tone(menu_item)


#--- MAIN MENU: EQUALIZER NAME
# Make edit equalizer name menu (TONE>tone list>equalizer name>selelct)
def make_edit_equalizer_name_menu(menu, prev_menu):
    clear_menu_memory(prev_menu, True, True, True)

    values = []
    for ch in CHARS_LIST:
        values.append({"name": ch, "on_select": on_change_char, "on_selected": None})

    eq_list = YMF825pico.get_synth_equalizer_names()
    SYNTH_MENU[MAIN_MENU_EQUALIZER_NAME]["CATEGORY"] = []
    for equalizer in eq_list:
#        values = []
#        for ch in CHARS_LIST:
#            values.append({"name": ch, "on_select": on_change_char, "on_selected": None})

        # Current tone name as ITEM menu
        item = []
        for i in list(range(EQUALIZER_NAME_LENGTH)):
            ch = equalizer[i:i+1]
            if ch == "":
                ch = " "
            item.append({"name": ch, "on_select": None, "on_selected": None, "selected": 0, "VALUE": values})

        item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_equalizer_name, "on_selected": None}, {"name": None}]})
        item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_equalizer_name, "on_selected": None}, {"name": None}]})

        SYNTH_MENU[MAIN_MENU_EQUALIZER_NAME]["CATEGORY"].append({"name": equalizer, "on_select": None, "on_selected": None, "ITEM": item})


def on_save_equalizer_name():
    global menu_main, menu_category, menu_item, menu_value

    # Change the current tone name
    name = ""
    for i in list(range(TIMBRE_NAME_LENGTH)):
        ch = CHARS_LIST[SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"]]
        name += ch if ch != CHARS_LIST[0] else SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["name"]

#    print("CHANGE EQUALIZER NAME[{}]={}".format(menu_category, name))
    YMF825pico.rename_equalizer(menu_category, name)

    # Save equalizer data
    YMF825pico.save_equalizer_data()
    gc.collect()

    # Initialize the TONE NAME menu
    make_edit_equalizer_name_menu(menu_main, menu_main)
    on_cancel_equalizer_name()


def on_cancel_equalizer_name():
#    print("CANCEl EQ NAME")
    on_cancel_timbre_name()


#--- MAIN MENU: EQUALIZER EDIT
# Make edit equalizer edit menu (TONE>tone list>equalizer eit>selelct)
equalizer_value_index = 0
def make_edit_equalizer_edit_menu(menu, prev_menu):
    global equalizer_value_index

    clear_menu_memory(prev_menu, True, True, True)

    # Values for dicimal places
    values = []
    for i in list(range(10)):
        values.append({"name": str(i), "on_select": None, "on_selected": on_change_decimal_places})

    # For the biquad filter equation
    bqeq_types = {"name": "FLT Type", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "DIRECT", "on_select": None, "on_selected": on_change_filter_type}, {"name": "LPF:FcQ", "on_select": None, "on_selected": on_change_filter_type}, {"name": "HPF:FcQ", "on_select": None, "on_selected": on_change_filter_type}, {"name": "BPFskt:FcQ", "on_select": None, "on_selected": on_change_filter_type}, {"name": "BPF0db:FcQ", "on_select": None, "on_selected": on_change_filter_type}, {"name": "NOTCH:FcQ", "on_select": None, "on_selected": on_change_filter_type}, {"name": "APF:FcQ", "on_select": None, "on_selected": on_change_filter_type}]}
    bqeq_calc  = {"name": "Calc FLT", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "CALC", "on_select": None, "on_selected": on_calc_biquad_filter}, {"name": None}]}

    equalizer_value_index = 0
    eq_list = YMF825pico.get_synth_equalizer_names()
    SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"] = []
    eq_id = 0
    for equalizer in eq_list:

        eq_parm = YMF825pico.get_equalizer_parameters(eq_id)
#        print("EQ PARM[", eq_id, "]=", eq_parm)

        # Current tone name as ITEM menu
        item = [{"name": "DECIMAL PL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": values}]
        for i in list(range(3)):
            item.append(bqeq_types)
            item.append(bqeq_calc)

            eqname = "EQ" + str(i) + " "
            val = str(eq_parm[i]["ceq0"])
#            print("STR=", val)
            item.append({"name": eqname + "B0/Fc", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": val, "on_select": on_change_eq_param, "on_selected": None}, {"name": val, "on_select": on_change_eq_param, "on_selected": None}, {"name": val, "on_select": on_change_eq_param, "on_selected": None}]})

            val = str(eq_parm[i]["ceq1"])
            item.append({"name": eqname + "B1/Qv", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": val, "on_select": on_change_eq_param, "on_selected": None}, {"name": val, "on_select": on_change_eq_param, "on_selected": None}, {"name": val, "on_select": on_change_eq_param, "on_selected": None}]})

            val = str(eq_parm[i]["ceq2"])
            item.append({"name": eqname + "B2", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": val, "on_select": on_change_eq_param, "on_selected": None}, {"name": val, "on_select": on_change_eq_param, "on_selected": None}, {"name": val, "on_select": on_change_eq_param, "on_selected": None}]})

            val = str(eq_parm[i]["ceq3"])
            item.append({"name": eqname + "A1", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": val, "on_select": on_change_eq_param, "on_selected": None}, {"name": val, "on_select": on_change_eq_param, "on_selected": None}, {"name": val, "on_select": on_change_eq_param, "on_selected": None}]})

            val = str(eq_parm[i]["ceq4"])
            item.append({"name": eqname + "A2", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": val, "on_select": on_change_eq_param, "on_selected": None}, {"name": val, "on_select": on_change_eq_param, "on_selected": None}, {"name": val, "on_select": on_change_eq_param, "on_selected": None}]})

        item.append({"name": "LISTEN",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "PLAY", "on_select": None, "on_selected": on_change_equalizer_parameter}, {"name": None}]})
        item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_equalizer_edit, "on_selected": None}, {"name": None}]})
        item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_equalizer_edit, "on_selected": None}, {"name": None}]})
        item.append({"name": "RESET", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_reset_equalizer_edit, "on_selected": None}, {"name": None}]})

        SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"].append({"name": equalizer, "on_select": None, "on_selected": None, "ITEM": item})
        eq_id += 1


# Change the filter type to calculate
def on_change_filter_type():
    SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = menu_value


# Calculate the biquad filter parameters
def on_calc_biquad_filter():
    flt_id = SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item-1]["selected"]
    flt_type = SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item-1]["VALUE"][flt_id]["name"]

    # Cut off frequency and Q value (fc kHz, YMF825 sampling frequency is always 48.000 kHz)
    fc = float(SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item+1]["VALUE"][0]["name"])
    qv = float(SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item+2]["VALUE"][0]["name"])

    # Zero clear the Fc and Qv
    if fc < 0.0 or qv < 0.0:
        for i in list(range(3)):
            SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item+1]["VALUE"][i]["name"] = "0.0"
            SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item+2]["VALUE"][i]["name"] = "0.0"
        SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = 0
        show_menu(0)
        return

    # Calculate the filter parameters
    if qv < 0.01:
        qv = 0.01

#    print("BIQUAD FILTER:{}, Fc={}, Q={}".format(flt_type, fc, qv))
    w0 = math.pi * 2 * fc / 48.000
    alpha = math.sin(w0) / (qv + qv)
    cosw0 = math.cos(w0)
    a0 = 1.0 + alpha
    a1 = cosw0 * 2 / a0
    a2 = (alpha - 1.0) / a0

    if flt_type == "LPF:FcQ":
        b0 = (1.0 - cosw0) / (a0 + a0)
        b1 = (1.0 - cosw0) / a0
        b2 = b0
    elif flt_type == "HPF:FcQ":
        b0 = (1.0 + cosw0) / (a0 + a0)
        b1 = -(1.0 + cosw0) / a0
        b2 = b0
    elif flt_type == "BPFskt:FcQ":
        b0 = qv * alpha / a0
        b1 = 0
        b2 = -b0
    elif flt_type == "BPF0db:FcQ":
        b0 = alpha / a0
        b1 = 0
        b2 = -b0
    elif flt_type == "NOTCH:FcQ":
        b0 = 1 / a0
        b1 = -2 * cosw0 / a0
        b2 = b0
    elif flt_type == "APF:FcQ":
        b0 = (1 - alpha) / a0
        b1 = -2 * cosw0 / a0
        b2 = (1 + alpha) / a0
    else:
#        print("UNKNOWN FILTER TYPE.")
        return

    # Set parameters
#    print("PARMS=", b0, b1, b2, a1, a2)
    for i in list(range(3)):
        SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item+1]["VALUE"][i]["name"] = str(b0)
        SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item+2]["VALUE"][i]["name"] = str(b1)
        SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item+3]["VALUE"][i]["name"] = str(b2)
        SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item+4]["VALUE"][i]["name"] = str(a1)
        SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item+5]["VALUE"][i]["name"] = str(a2)

    SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = 0
    show_menu(0)


# Change equalizer parameter
def on_change_equalizer_parameter():
    # Set equalizer and play demo
    save_equalizer_edit()
    YMF825pico.set_synth_equalizer(menu_category)
    on_play_demo("demo1", False)


# Change the decimal places
def on_change_decimal_places():
    SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = menu_value


# Change an equalizer parameter
def on_change_eq_param():
    global equalizer_value_index

    # Value move direction
    sign = 0
    if menu_value == 0 and equalizer_value_index == 2:
#        print("plus")
        sign = 1
    elif menu_value == 2 and equalizer_value_index == 0:
#        print("minus")
        sign = -1
    elif menu_value > equalizer_value_index:
#        print("PLUS")
        sign = 1
    elif menu_value < equalizer_value_index:
#        print("MINUS")
        sign = -1
        
    equalizer_value_index = menu_value
    if sign == 0:
        return

    decimal = SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][0]["selected"]
    val = float(SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][0]["name"])
    if decimal >= 1:
        sign = float(("-" if sign == -1 else "") + "." + ("0" * (decimal - 1)) + "1")

    val += sign
    s = str(val)
    SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][0]["name"] = s
    SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][1]["name"] = s
    SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][2]["name"] = s


# Save the edited equalize parameters
def save_equalizer_edit():
#    print("on_save_equalizer_edit")
    eq0 = {}
    eq1 = {}
    eq2 = {}
    for parm in list(range(5)):
        ceq = "ceq" + str(parm)
        eq0[ceq] = float(SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][parm +  3]["VALUE"][0]["name"])
        eq1[ceq] = float(SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][parm + 10]["VALUE"][0]["name"])
        eq2[ceq] = float(SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][parm + 17]["VALUE"][0]["name"])

#    print("SAVE EQ0[", menu_category, "]=", eq0)
#    print("SAVE EQ1[", menu_category, "]=", eq1)
#    print("SAVE EQ2[", menu_category, "]=", eq2)
    YMF825pico.save_edited_data_to_equalizer( menu_category, eq0, eq1, eq2 )


# Save the edited equalize parameters
def on_save_equalizer_edit():
    save_equalizer_edit()
    YMF825pico.save_equalizer_data()
    gc.collect()
    YMF825pico.set_synth_equalizer(menu_category)


# Cancel equalizer parameters edited
def on_cancel_equalizer_edit():
#    print("on_cancel_equalizer_edit")
    global menu_main, menu_category, menu_item, menu_value

    # Clear selected data and initialize the TIMBRE NAME menu
    menu_item = 0
    make_edit_equalizer_edit_menu(menu_main, menu_main)
    menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
    show_menu(0)


# Reset equalizer parameter to the all path filter
def on_reset_equalizer_edit():
#    print("on_reset_equalizer_edit")
    for e in list(range(3,17,7)):
        for i in list(range(5)):
            val = "1.0" if i == 0 else "0.0"
            SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][e+i]["VALUE"][0]["name"] = val
            SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][e+i]["VALUE"][1]["name"] = val
            SYNTH_MENU[MAIN_MENU_EQUALIZER_EDIT]["CATEGORY"][menu_category]["ITEM"][e+i]["VALUE"][2]["name"] = val

    menu_item = 0
    equalizer_value_index = 0
    show_menu(0)


# YMF825pico 4 layers' menu structures: MAIN>CATEGORY>ITEM>VALUE
SYNTH_MENU = [
    {   # MAIN_MENU_PLAY
        "name": "PLAY",
        "on_select": make_select_play_menu,
        "on_selected": None,
        "CATEGORY": [
            '''
            {   # MAIN_MENU_PLAY_MANUAL
                "name": "MANUAL",
                "on_select": make_select_manual_menu,
                "on_selected": None,
                "ITEM": []
            },
            {   # MAIN_MENU_PLAY_DEMO
                "name": "DEMO",
                "on_select": make_select_demo_menu,
                "on_selected": None,
                "ITEM": []
            }
            '''
        ]
    },
    {   # MAIN_MENU_TIMBRE_NAME
        "name": "TIMBRE NAME",
        "on_select": make_edit_timbre_name_menu,
        "on_selected": None,
        "CATEGORY": []
    },
    {   # MAIN_MENU_TIMBRE_EDIT
        "name": "TIMBRE EDIT",
        "on_select": make_edit_timbre_edit_menu,
        "on_selected": None,
        "CATEGORY": []
    },
    {   # MAIN_MENU_TONE_NAME
        "name": "TONE NAME",
        "on_select": make_edit_tone_name_menu,
        "on_selected": None,
        "CATEGORY": []
    },
    {   # MAIN_MENU_TONE_EDIT
        "name": "TONE EDIT",
        "on_select": make_edit_tone_edit_menu,
        "on_selected": None,
        "CATEGORY": []
    },
    {   # MAIN_MENU_TONE_COPY
        "name": "TONE COPY",
        "on_select": make_edit_tone_copy_menu,
        "on_selected": None,
        "CATEGORY": []
    },
    {   # MAIN_MENU_EQUALIZER_NAME
        "name": "EQUALIZER NAME",
        "on_select": make_edit_equalizer_name_menu,
        "on_selected": None,
        "CATEGORY": []
    },
    {   # MAIN_MENU_EQUALIZER_EDIT
        "name": "EQUALIZER EDIT",
        "on_select": make_edit_equalizer_edit_menu,
        "on_selected": None,
        "CATEGORY": []
    }
]


# Get a rotary encoder status
# rte: {"NO": ?, "A_PIN": gpio, "B_PIN": gpio, "A_SW": pin object, "B_SW": pin object, "A_PREV": ?, "B_PREV": ?, "VALUES": [0,0,0,0]}
# RETURN:
#   1=count up
#  -1=count down
#   0=stay
def get_a_rotary_encoder(rte):
    a = rte["A_SW"].value()
    b = rte["B_SW"].value()
    time.sleep(0.001)
    if rte["A_PREV"] != a or rte["B_PREV"] != b:
        del rte["VALUES"][0]
        rte["VALUES"].append(rte["A_PREV"] * 8 + rte["B_PREV"] * 4 + a * 2 + b)
        rte["A_PREV"] = a
        rte["B_PREV"] = b
#        print("A, B=", a, b)
#        print("BUF[{}]={},{},{},{}".format(rte["NO"], bin(rte["VALUES"][0]), bin(rte["VALUES"][1]), bin(rte["VALUES"][2]), bin(rte["VALUES"][3])))

        if rte["VALUES"] == [0b1101, 0b0100, 0b0010, 0b1011]:
            return 1
        
        if rte["VALUES"] == [0b1110, 0b1000, 0b0001, 0b0111]:
            return -1

    return 0


# Get rotary encoders' status
def get_rotary_encoders():
    global menu_main, menu_category, menu_item, menu_value
    global gui_item_menu, gui_item_menu_exit
    global item_menu_display_start
    global db_values_tone

    # Rotary encoder pins
    for rte in ROTARY_ENCODERS:
        count = get_a_rotary_encoder(rte)
        if count != 0:
#            print("ROTARY ENCODER[{}] = {}".format(rte["NO"], count))
            
            # MAIN
            if rte["NO"] == 0:
                prev_menu = menu_main
                menu_main += count
                if menu_main < 0:
                    menu_main = len(SYNTH_MENU) - 1
                elif menu_main >= len(SYNTH_MENU):
                    menu_main = 0

                if db_values_tone is not None:
                    del db_values_tone
                    db_values_tone = None

                # on select event
                if SYNTH_MENU[menu_main]["on_select"] is not None:
                    SYNTH_MENU[menu_main]["on_select"](menu_main, prev_menu)
#                print("MENU: MAIN={} CATEGORY={} ITEM={}".format(menu_main, menu_category, menu_item))
#                print("LENG: MAIN={}".format(len(SYNTH_MENU)))
#                print("LENG: CATEGORY={}".format(len(SYNTH_MENU[menu_main]["CATEGORY"])))
#                print("LENG: ITEM={}".format(len(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"])))
#                print("ITEM: SELECTED={}".format(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]))
                        
                # Change menu
                menu_category = 0
                menu_item = 0
                menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
                show_menu(0)

                # on selected event
                if SYNTH_MENU[menu_main]["on_selected"] is not None:
                    SYNTH_MENU[menu_main]["on_selected"](menu_main, prev_menu)

            # CATEGORY
            elif rte["NO"] == 1:
                prev_category = menu_category
                menu_category += count
                if menu_category < 0:
                    menu_category = len(SYNTH_MENU[menu_main]["CATEGORY"]) - 1
                elif menu_category >= len(SYNTH_MENU[menu_main]["CATEGORY"]):
                    menu_category = 0

                # on select event
                if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_select"] is not None:
                    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_select"](menu_category, prev_category)

                # Change menu
                menu_item = 0
                menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
                show_menu(0)

                # on selected event
                if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_selected"] is not None:
                    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_selected"](menu_category, prev_category)

            # ITEM
            elif rte["NO"] == 2:
                # Text editor mode
                if gui_item_menu is None:
                    menu_len = len(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"])
                    prev_item = menu_item
                    menu_item += count
                    if menu_item < 0:
                        menu_item = menu_len - 1
                    elif menu_item >= menu_len:
                        menu_item = 0

                # GUI editor mode
                else:
                    menu_len = len(gui_item_menu)
                    prev_item = menu_item
                    item_index = gui_item_menu.index(menu_item)
#                    print("GUI MODE prev=", prev_item, "item=", menu_item, "index=", item_index, "count=", count, "exit=", gui_item_menu_exit)
                    item_index += count
                    if item_index < 0:
                        menu_item = gui_item_menu_exit[0]
                        item_menu_display_start = menu_item
                        gui_item_menu = None
                        gui_item_menu_exit = None

                    elif item_index >= menu_len:
                        menu_item = gui_item_menu_exit[1]
                        item_menu_display_start = menu_item
                        gui_item_menu = None
                        gui_item_menu_exit = None
                    else:
                        menu_item = gui_item_menu[item_index]

                # on select event
                if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_select"] is not None:
                    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_select"](menu_item, prev_item)

                # Change menu
                menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
                show_menu(count)

                # on selected event
                if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_selected"] is not None:
                    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_selected"](menu_item, prev_item)

            # VALUE
            elif rte["NO"] == 3:
                menu_len = len(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"])
                val = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_len - 1]["name"]
                menu_value += count
                refresh_menu = False
                
                # Straight forward menu
                if val is None:
                    if menu_value < 0:
                        menu_value = 0
                    elif menu_value >= menu_len - 1:
                        menu_value = menu_len - 2
                    else:
                        refresh_menu = True
                # Rotary menu
                else:
                    refresh_menu = True
                    if menu_value < 0:
                        menu_value = menu_len - 1
                    elif menu_value >= menu_len:
                        menu_value = 0

                if refresh_menu:
                    # on select an item
                    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"] is not None:
                        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"]()

                    # Slide item region to left
                    if menu_main == MAIN_MENU_TONE_EDIT:
                        slide = 2
                        str_head = True
                    elif menu_main == MAIN_MENU_TIMBRE_EDIT:
                        slide = 5
                        str_head = True
                    elif menu_main == MAIN_MENU_EQUALIZER_EDIT:
                        slide = 5
                        str_head = False
                    else:
                        slide = 0
                        str_head = True

                    # Change menu
                    show_menu(0, slide, str_head)

                    # on selected an item
                    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_selected"] is not None:
                        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_selected"]()


# Piano role player
step_wait = 2.0
def piano_role_player(score_file="score1.txt", file_encode="utf-8"):
    global step_wait
    timbre = []
    for port in list(range(YMF825pico.TIMBRE_PORTIONS)):
        timbre.append({"base": -1, "from": 0, "to": 0}) 

    def split_by_str(line, str):
        pos = line.find(str)
        if pos >= 0:
            return (line[:pos], line[pos+1:])
        else:
            return None

    def parse_command(line):
        global step_wait

        while True:
            # Skip to "#"
            splt = split_by_str(line, "#")
            if splt is None:
                return
            (car, line) = splt
            
            # Read variable name
            splt = split_by_str(line, "=")
            if splt is None:
                return
            (var_name, line) = splt
            
            # Read value
            splt = split_by_str(line, ";")
            if splt is None:
                return
            (val_str, line) = splt
            try:
                val = float(val_str)
                if var_name == "WAIT":
                    step_wait = val
                    
                elif var_name == "DATABANK":
                    YMF825pico.set_databank(int(val))
                    YMF825pico.load_tone_data()
                    YMF825pico.load_timbre_data()
                    YMF825pico.load_equalizer_data()
                    
                elif var_name == "TIMBRE":
                    YMF825pico.set_synth_play_timbre(int(val))
                    YMF825pico.set_timbre_tones(val)
                    for prt in list(range(YMF825pico.TIMBRE_PORTIONS)):
                        timbre_volumes[prt] = YMF825pico.get_timbre_volume(val, prt) / 31.0

            except:
                return

    def parse_scale(line):
        pos = 0
        port = -1
        while True:
            # Skip to "|"
            splt = split_by_str(line, "|")
            if splt is None:
                return
            (car, line) = splt
            pos = pos + len(car) + 1
            if port >= 0:
                timbre[port]["to"] = pos - 2
            
            # Read timbre portion number
            splt = split_by_str(line, ":")
            if splt is None:
                return
            (car, line) = splt
            try:
                port = int(car)
                if port < 0 or port >= len(timbre):
                    return
            except:
                return
            pos = pos + len(car) + 1

            # Read scale
            splt = split_by_str(line, ":")
            if splt is None:
                return
            (car, line) = splt
            s = YMF825pico.get_scale_number(car)
            if s < 0 or s > 127:
                return
            timbre[port]["base"] = s
            pos = pos + len(car) + 1
            timbre[port]["from"] = pos

    def get_note_info(pos):
        for port in list(range(len(timbre))):
            if timbre[port]["base"] != -1:
                f = timbre[port]["from"]
                t = timbre[port]["to"]
                if f <= pos and pos <= t:
                    return (port, timbre[port]["base"] + pos - f)
        return (-1, 0)

    def parse_score(line):
        for pos in list(range(len(line))):
            note = line[pos]

            # note off
            if note == "-":
                (timbre, midi_note) = get_note_info(pos)
                if timbre >= 0:
                    YMF825pico.stop_by_timbre_note(timbre, midi_note)

            # note on
            elif note.isdigit():
                (timbre, midi_note) = get_note_info(pos)
                if timbre >= 0:
                    YMF825pico.stop_by_timbre_note(timbre, midi_note)
                    YMF825pico.play_by_timbre_note(timbre, midi_note, int(int(note) * 127 / 9))

    try:
        with open("./scores/" + score_file, "r", encoding = file_encode) as file:
            for a_line in file:
                line = repr(a_line)
                line = line[1:]
#                print("F" + line[0] + "=" + line)

                if line[0] == " ":
                    parse_score(line)
                    time.sleep(step_wait)
                
                elif line[0] == "#":
                    parse_command(line)

                elif line[0] == "|":
                    parse_scale(line)
#                    print("TIMBRE=", timbre)

        file.close()

    except OSError as e:
#        print(e)
        return


#Receive MIDI (work in a thread)
timbre_offset = 0
def midi_interface(midi_events, length):
    global timbre_offset

    midich = {}
    for p in list(range(YMF825pico.TIMBRE_PORTIONS)):
        ch = "CH" + str(YMF825pico.get_playing_timbre_midich(p))
        if ch in midich:
            midich[ch].append(p)
        else:
            midich[ch] = [p]
#    print("MIDI CH, length, events=", midich, length, midi_events)

    bt = 0
    while bt < length:
        # MIDI command
        midi_cmd  = midi_events[bt]
        bt += 1
        left = length - bt
#        print("MIDI CMD, left=", midi_cmd, left)
        if left >= 2:
            # MIDI note
            midi_note = midi_events[bt]
            # MIDI velocity
            midi_velo = midi_events[bt + 1]
            bt += 2

            # note on: 0x9n (n=0..f: MIDI CH)
            if (midi_cmd & 0xf0) == 0x90:
                ch = "CH" + str(midi_cmd - 0x90 + 1)
#                print("note on :", ch, midi_note, midi_velo)
                if ch in midich:
                    for portion in midich[ch]:
                        # note off
                        if midi_velo == 0:
                            YMF825pico.stop_by_timbre_note((portion + timbre_offset) % YMF825pico.TIMBRE_PORTIONS, midi_note)
                        # note on
                        else:
                            YMF825pico.play_by_timbre_note((portion + timbre_offset) % YMF825pico.TIMBRE_PORTIONS, midi_note, midi_velo)

            # note off: 0x8n (n=0..f: MIDI CH)
            elif (midi_cmd & 0xf0) == 0x80:
                ch = "CH" + str(midi_cmd - 0x80 + 1)
#                print("note off:", ch, midi_note, midi_velo)
                if ch in midich:
                    for portion in midich[ch]:
                        YMF825pico.stop_by_timbre_note((portion + timbre_offset) % YMF825pico.TIMBRE_PORTIONS, midi_note)
        
            # Control
            elif (midi_cmd & 0xf0) == 0xb0:
                # Chanel -> Timbre
                timbre = (midi_cmd - 0xb0 + timbre_offset) % YMF825pico.TIMBRE_PORTIONS
                
                # sustain: pressed:[2]==0x7f / released [2]==0
                if midi_note == 0x40:
                    YMF825pico.sustain_pedal(timbre, midi_velo == 0x7f)

                # modulation --> reset timbre_offset
                elif midi_note == 0x01:
                    timbre_offset = 0
#                    print("MIDI: Modulation")

            # Pitch --> Timbre shift
            elif (midi_cmd & 0xf0) == 0xe0:
                # pitch+ --> timbre+
                if midi_note == 0x47:
                    timbre_offset = (timbre_offset + 1) % YMF825pico.TIMBRE_PORTIONS
            
                # pitch- --> timbre-
                elif midi_note == 0x39:
                    timbre_offset = (timbre_offset - 1) % YMF825pico.TIMBRE_PORTIONS


#Set up this module
def setup_module():
    # Menu initialize
    if SYNTH_MENU[menu_main]["on_select"] is not None:
        SYNTH_MENU[menu_main]["on_select"](0, -1)

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_select"](0, -1)

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_select"](0, -1)

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"](0, -1)


#Initialize the application
def init():
    global display
    
    print("init.")

    # SSD1306 setup
    addr = i2c_ssd1306.scan()
#    print("SSD1306 ADDRESS=" + hex(addr[0]))
    display = ssd1306.SSD1306_I2C(DISPLAY_WIDTH, DISPLAY_HEIGHT, i2c_ssd1306)
#    print("SSD1306 display=", display)
    display.contrast(128)
    display.fill(0)
    display.text("YMF825pico", 25, 20, True)
    display.hline(0, 30, DISPLAY_WIDTH, True)
    display.text("(C)2023, S.Ohira", 0, 33, True)
    display.show()

    # Rotary encoder pins
    for rte in ROTARY_ENCODERS:
        rte["A_SW"] = Pin(rte["A_PIN"], Pin.IN, Pin.PULL_UP)
        rte["B_SW"] = Pin(rte["B_PIN"], Pin.IN, Pin.PULL_UP)

    print("init end.")


#Main
if __name__=='__main__':
    # CPU clock 240MHz
#    machine.freq(133000000)
    machine.freq(240000000)

    # UART
#    uart = UART(UART_CH, baudrate=UART_BAUDRATE, tx=Pin(UART_TX), rx=Pin(UART_RX), bits=8, parity=None, stop=1, rxbuf=512)
    uart = UART(UART_CH, baudrate=UART_BAUDRATE, tx=Pin(UART_TX), rx=Pin(UART_RX), bits=8, parity=None, stop=1)

    # YMF825
    YMF825pico = ymf825pico_class()
    init()

    # YMF825 control class
#    print("YMF825 PICO CLASS")
    YMF825pico.turn_on_synthesizer()
    YMF825pico.setup_synth()

    setup_module()
#    YMF825pico.play_demo()
    piano_role_player("demo1.txt")

    show_menu(0)

    # UART
#    uart_read = True
    cmd_data = 0
    read_bytes = []
    while True:
        # MIDI keyboard UART receive
        length = uart.any()
        if length > 0:
            read_byte = uart.read(1)
#            uart_read = True

            # MIDI envets for YMF825pico
            midi_cmd = read_byte[0] & 0xf0
            if midi_cmd == 0x90 or midi_cmd == 0x80 or midi_cmd == 0xb0 or midi_cmd == 0xe0:
                cmd_data = 2
                read_bytes.append(read_byte[0])
            elif cmd_data > 0:
                read_bytes.append(read_byte[0])
                cmd_data -= 1

        elif cmd_data == 0 and len(read_bytes) > 0:
#            print("UART:[", length, "]=", read_bytes)
#            for bt in read_bytes:
#                print("data=", hex(bt))

            # Ignore MIDI real time clock and active sensing (too many data!!)
#            uart_read = False
            midi_interface(read_bytes, len(read_bytes))
            del read_bytes
            read_bytes = []

#        elif cmd_data > 0:
#            print("WAITING FOR PARAMETERS:", cmd_data)

#        if not uart_read:
        if cmd_data == 0:
            # Get rotary encoders
            get_rotary_encoders()


#    print("QUIT.")


