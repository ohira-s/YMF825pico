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
#############################################################################

from ymf825pico import ymf825pico_class
from machine import Pin, I2C, SPI, UART
import ssd1306
import time
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

# YMF825 parameters mapping and order (ABBR, REAL KEY NAME, VALUE RANGE)
PARM_TEXT_OFF_ON = ["OFF", "ON"]
PARM_TEXT_ALGO = ["Ab", "A+b", "AbCd+", "A+bc", "Abcd", "Ab+Cd", "A+bcd", "A+bc+d"]
PARM_TEXT_WAVE = [
    "SIN",   "SIN/2", "SINSN", "SAILs",
    "SIN*2", "S*2/2", "SQUAR", "RIBBN",
    "SINcp", "Scp/2", "ScpSc", "SAILc",
    "Scp*2", "Sc2/2", "SQR/2", "-----",
    "TRIAN", "TRI/2", "TRITR", "SAILt",
    "TRI*2", "TR2/2", "SQR*2", "-----",
    "RAMP",  "RMP/2", "RMPRP", "SAILr",
    "RMP*2", "RRM/2", "SQ2/2", "-----"
]
YMF825_PARM = [
    # GENERAL
    ("Basic OCT", "Basic Octave", 4, None),
    ("Algorithm", "Algorithm", 8, PARM_TEXT_ALGO),
    ("LFO", "LFO", 8, None),
    # OP1
    ("Wave Shp A", "Wave Shape1", 32, PARM_TEXT_WAVE),
    ("Total LV A", "Total Operator Level1", 64, None),
    ("Feedback A", "FM Feedback Level1", 8, None),
    ("Detune   A", "Detune1", 8, None),
    ("MCM Freq A", "Multi Control Magnification Frequency1", 16, None),
    ("Atack RT A", "Attack Rate1", 16, None),
    ("Decay RT A", "Decay Rate1", 16, None),
    ("Sustn LV A", "Sustain Level1", 16, None),
    ("Sustn RT A", "Sustain Rate1", 16, None),
    ("Reles RT A", "Release Rate1", 16, None),
    ("Vibrt EN A", "Enable Vibrate1", 2, PARM_TEXT_OFF_ON),
    ("Vibrt DP A", "Depth Of Vibrate1", 4, None),
    ("Amp M EN A", "Enable Amp Modulation1", 2, PARM_TEXT_OFF_ON),
    ("Amp M DP A", "Depth Of Amp Modulation1", 4, None),
    ("Key S EN A", "Key Scale Sensitivity1", 2, PARM_TEXT_OFF_ON),
    ("Key S LV A", "Key Scale Level Sensivitiy1", 4, None),
    ("IgnKy OF A", "Ignore Key Off1", 2, PARM_TEXT_OFF_ON),
    # OP2
    ("Wave Shp B", "Wave Shape2", 32, PARM_TEXT_WAVE),
    ("Total LV B", "Total Operator Level2", 64, None),
    ("Feedback B", "FM Feedback Level2", 8, None),
    ("Detune   B", "Detune2", 8, None),
    ("MCM Freq B", "Multi Control Magnification Frequency2", 16, None),
    ("Atack RT B", "Attack Rate2", 16, None),
    ("Decay RT B", "Decay Rate2", 16, None),
    ("Sustn LV B", "Sustain Level2", 16, None),
    ("Sustn RT B", "Sustain Rate2", 16, None),
    ("Reles RT B", "Release Rate2", 16, None),
    ("Vibrt EN B", "Enable Vibrate2", 2, PARM_TEXT_OFF_ON),
    ("Vibrt DP B", "Depth Of Vibrate2", 4, None),
    ("Amp M EN B", "Enable Amp Modulation2", 2, PARM_TEXT_OFF_ON),
    ("Amp M DP B", "Depth Of Amp Modulation2", 4, None),
    ("Key S EN B", "Key Scale Sensitivity2", 2, PARM_TEXT_OFF_ON),
    ("Key S LV B", "Key Scale Level Sensivitiy2", 4, None),
    ("IgnKy OF B", "Ignore Key Off2", 2, PARM_TEXT_OFF_ON),
    # OP3
    ("Wave Shp C", "Wave Shape3", 32, PARM_TEXT_WAVE),
    ("Total LV C", "Total Operator Level3", 64, None),
    ("Feedback C", "FM Feedback Level3", 8, None),
    ("Detune   C", "Detune3", 8, None),
    ("MCM Freq C", "Multi Control Magnification Frequency3", 16, None),
    ("Atack RT C", "Attack Rate3", 16, None),
    ("Decay RT C", "Decay Rate3", 16, None),
    ("Sustn LV C", "Sustain Level3", 16, None),
    ("Sustn RT C", "Sustain Rate3", 16, None),
    ("Reles RT C", "Release Rate3", 16, None),
    ("Vibrt EN C", "Enable Vibrate3", 2, PARM_TEXT_OFF_ON),
    ("Vibrt DP C", "Depth Of Vibrate3", 4, None),
    ("Amp M EN C", "Enable Amp Modulation3", 2, PARM_TEXT_OFF_ON),
    ("Amp M DP C", "Depth Of Amp Modulation3", 4, None),
    ("Key S EN C", "Key Scale Sensitivity3", 2, PARM_TEXT_OFF_ON),
    ("Key S LV C", "Key Scale Level Sensivitiy3", 4, None),
    ("IgnKy OF C", "Ignore Key Off3", 2, PARM_TEXT_OFF_ON),
    # OP4
    ("Wave Shp D", "Wave Shape4", 32, PARM_TEXT_WAVE),
    ("Total LV D", "Total Operator Level4", 64, None),
    ("Feedback D", "FM Feedback Level4", 8, None),
    ("Detune   D", "Detune4", 8, None),
    ("MCM Freq D", "Multi Control Magnification Frequency4", 16, None),
    ("Atack RT D", "Attack Rate4", 16, None),
    ("Decay RT D", "Decay Rate4", 16, None),
    ("Sustn LV D", "Sustain Level4", 16, None),
    ("Sustn RT D", "Sustain Rate4", 16, None),
    ("Reles RT D", "Release Rate4", 16, None),
    ("Vibrt EN D", "Enable Vibrate4", 2, PARM_TEXT_OFF_ON),
    ("Vibrt DP D", "Depth Of Vibrate4", 4, None),
    ("Amp M EN D", "Enable Amp Modulation4", 2, PARM_TEXT_OFF_ON),
    ("Amp M DP D", "Depth Of Amp Modulation4", 4, None),
    ("Key S EN D", "Key Scale Sensitivity4", 2, PARM_TEXT_OFF_ON),
    ("Key S LV D", "Key Scale Level Sensivitiy4", 4, None),
    ("IgnKy OF D", "Ignore Key Off4", 2, PARM_TEXT_OFF_ON),
]

# Character list
CHARS_LIST= ["="]   # No change
CHARS_LIST += [chr(ch) for ch in list(range(0x41,0x5b))]
CHARS_LIST += [chr(ch) for ch in list(range(0x30,0x3a))]
CHARS_LIST += [" "]

# YMF825pico menu
menu_main = 0
menu_category = 0
menu_item = 0
menu_value = 0

#--- YMF825pico menu definitions
# PLAY
MAIN_MENU_PLAY_MANUAL = 0
MAIN_MENU_PLAY = 0
MAIN_MENU_PLAY_DEMO = 1

# TIMBRE NAME
MAIN_MENU_TIMBRE_NAME = 1
TIMBRE_NAME_LENGTH = 10

# TIMBRE EDIT
MAIN_MENU_TIMBRE_EDIT = 2

# TONE NAME
MAIN_MENU_TONE_NAME = 3
TONE_NAME_LENGTH = 10

# TONE EDIT
MAIN_MENU_TONE_EDIT = 4

# TONE COPY
MAIN_MENU_TONE_COPY = 5


# Show menu
# move_dir: 1=down, -1=up
def show_menu(move_dir):
    global menu_main, menu_category, menu_item, menu_value

#    print(SYNTH_MENU)
#    print(menu_main, menu_category, menu_item, menu_value)

    # Show MAIN and CATEGORY
    main_name = SYNTH_MENU[menu_main]["name"]
    category_name = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["name"]
    if main_name == "TONE EDIT":
        selected = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][1]["selected"]
        algo = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][1]["VALUE"][selected]["name"]
        print("ALGO=", menu_main, menu_category, selected, algo)
        main_name = main_name + ":" + algo

    display.fill(0)
    display.text(main_name, 0, 0, True)
    display.hline(0, DISPLAY_LINE_HEIGHT - 2, DISPLAY_WIDTH, True)
    display.text(category_name, 0, DISPLAY_LINE_HEIGHT, True)
    display.hline(0, DISPLAY_LINE_HEIGHT * 2 - 2, DISPLAY_WIDTH, True)
    display.vline(DISPLAY_DIVIDE, DISPLAY_LINE_HEIGHT * 2 - 2, DISPLAY_HEIGHT - (DISPLAY_LINE_HEIGHT * 2 - 2), True)

    # Show ITEM and VALUE
    items = len(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"])
    if menu_item < DISPLAY_MENU_LINES:
        menu_s = 0
    elif menu_item >= items - DISPLAY_MENU_LINES:
        menu_s = items - DISPLAY_MENU_LINES
    elif move_dir == 1:
        menu_s = menu_item - DISPLAY_MENU_LINES + 1
    else:
        menu_s = menu_item

#    print("MOVE DIR, s, e=", move_dir, menu_s, menu_s + DISPLAY_MENU_LINES)
    y = DISPLAY_LINE_HEIGHT * 2
    for i in list(range(menu_s, min(items, menu_s + DISPLAY_MENU_LINES))):
        # Show ITEM
        item_name = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["name"]
        display.text(item_name, 0, y, True)
        
        # Show the current editing VALUE
        if i == menu_item:
            value_name = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["VALUE"][menu_value]["name"]
            display.hline(0, y + DISPLAY_LINE_HEIGHT - 2, DISPLAY_WIDTH, True)
        # Show the selected VALUE
        else:
            selected = int(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"])
#            print("MENU:", menu_main, menu_category, i, selected)
            value_name = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["VALUE"][selected]["name"]

#        print("SHOW=", value_name)
        display.text(value_name, DISPLAY_DIVIDE + 2, y, True)
        y += DISPLAY_LINE_HEIGHT

    display.show()


# Clear list memory for SYNTH_MENU
def clear_menu_memory(prev, clear_category, clear_item, clear_value):
    if prev < 0:
        return

    target_main = menu_main
    target_category = menu_category
    target_item = menu_item
    if clear_category:
        target_main = prev
    elif clear_item:
        target_category = prev
    elif clear_value:
        target_item = prev
        
    print("CLEAR:", clear_category, clear_item, clear_value)
    print("TARGET: MAIN={} CATEGORY={} ITEM={}".format(target_main, target_category, target_item))
    print("LENGTH: CATEGORY={} ITEM={} VALUE={}".format(len(SYNTH_MENU[target_main]["CATEGORY"]), len(SYNTH_MENU[target_main]["CATEGORY"][target_category]["ITEM"]), len(SYNTH_MENU[target_main]["CATEGORY"][target_category]["ITEM"][target_item]["VALUE"])))
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


#--- MAIN MENE: PLAY
# Make select play menu (PLAY)
def make_select_play_menu(menu, prev_menu):
    global YMF825pico

    clear_menu_memory(prev_menu, True, True, True)

    SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"] = [
        {   # MAIN_MENU_PLAY_MANUAL
            "name": "MANUAL",
            "on_select": make_select_timbre_menu,
            "on_selected": None,
            "ITEM": []
        },
        {   # MAIN_MENU_PLAY_DEMO
            "name": "DEMO",
            "on_select": make_select_demo_menu,
            "on_selected": None,
            "ITEM": []
        }
    ]
    
    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_select"](0, -1)

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_select"](0, -1)

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"](0, -1)


# Make select timbre menu (PLAY>MANUAL>timbre list>selelct)
def make_select_timbre_menu(menu, prev_menu):
    global YMF825pico

    clear_menu_memory(prev_menu, False, True, True)

    tmb_list = YMF825pico.get_synth_timbre_names()
    SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_MANUAL]["ITEM"] = []
    for tmb in tmb_list:
        SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_MANUAL]["ITEM"].append({"name": tmb, "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SET", "on_select": on_select_timbre, "on_selected": None}]})


#--- MAIN MENE: DEMO
# Make select demo menu (PLAY>MANUAL>demo list>selelct)
def make_select_demo_menu(menu, prev_menu):
    clear_menu_memory(prev_menu, False, True, True)

    demo_list = ["DEMO1", "DEMO2", "DEMO3"]
    SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_DEMO]["ITEM"] = []
    for demo in demo_list:
        SYNTH_MENU[MAIN_MENU_PLAY]["CATEGORY"][MAIN_MENU_PLAY_DEMO]["ITEM"].append({"name": demo, "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "PLAY", "on_select": None, "on_selected": on_play_demo}]})


# Select a timbre on the menu
def on_select_timbre():
    global YMF825pico

    # Set new timbre to YMF825pico class, then send a change timbre command to YMF825
    print("CHANGE TIMBRE TO ", SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["name"])
    YMF825pico.set_synth_play_timbre(menu_item)
    YMF825pico.set_timbre_tones(menu_item)


# Play a demo score
def on_play_demo(demo = None):
    global YMF825pico

    # Play a demo
    if demo is None:
        demo = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["name"]

    print("PLAY DEMO=", demo)
    if demo == "DEMO1":
        YMF825pico.play_by_timbre_scale(0,"C4")
        YMF825pico.delay(500)
        YMF825pico.stop_by_timbre_scale(0,"C4")
        
        YMF825pico.play_by_timbre_scale(0,"E4")
        YMF825pico.delay(500)
        YMF825pico.stop_by_timbre_scale(0,"E4")
        
        YMF825pico.play_by_timbre_scale(0,"G4")
        YMF825pico.delay(500)
        YMF825pico.stop_by_timbre_scale(0,"G4")

        YMF825pico.play_by_timbre_scale(0,"C5")
        YMF825pico.delay(500)
        YMF825pico.stop_by_timbre_scale(0,"C5")

    elif demo == "DEMO2":
        YMF825pico.play_by_timbre_scale(0,"C4")
        YMF825pico.delay(500)
        YMF825pico.play_by_timbre_scale(0,"E4")
        YMF825pico.delay(500)
        YMF825pico.play_by_timbre_scale(0,"G4")
        YMF825pico.delay(500)
        YMF825pico.play_by_timbre_scale(0,"C5")
        YMF825pico.delay(500)
        YMF825pico.stop_by_timbre_scale(0,"C4")
        YMF825pico.stop_by_timbre_scale(0,"E4")
        YMF825pico.stop_by_timbre_scale(0,"G4")
        YMF825pico.stop_by_timbre_scale(0,"C5")

    elif demo == "DEMO3":
        YMF825pico.play_by_timbre_scale(0,"C4")
        YMF825pico.play_by_timbre_scale(1,"C4")
        YMF825pico.delay(500)
        YMF825pico.stop_by_timbre_scale(0,"C4")
        YMF825pico.stop_by_timbre_scale(1,"C4")
        
        YMF825pico.play_by_timbre_scale(0,"E4")
        YMF825pico.play_by_timbre_scale(1,"E4")
        YMF825pico.delay(500)
        YMF825pico.stop_by_timbre_scale(0,"E4")
        YMF825pico.stop_by_timbre_scale(1,"E4")

        YMF825pico.play_by_timbre_scale(0,"G4")
        YMF825pico.play_by_timbre_scale(1,"G4")
        YMF825pico.delay(500)
        YMF825pico.stop_by_timbre_scale(0,"G4")
        YMF825pico.stop_by_timbre_scale(1,"G4")

        YMF825pico.play_by_timbre_scale(0,"C5")
        YMF825pico.play_by_timbre_scale(1,"C5")
        YMF825pico.delay(500)
        YMF825pico.stop_by_timbre_scale(0,"C5")
        YMF825pico.stop_by_timbre_scale(1,"C5")


#--- MAIN MENE: TIMBRE NAME
# Make edit timbre name menu (TIMBRE>timbre list>timbre name>selelct)
def make_edit_timbre_name_menu(menu, prev_menu):
    global YMF825pico

    clear_menu_memory(prev_menu, True, True, True)

    timbre_list = YMF825pico.get_synth_timbre_names()
    SYNTH_MENU[MAIN_MENU_TIMBRE_NAME]["CATEGORY"] = []
    for timbre in timbre_list:
        values = []
        for ch in CHARS_LIST:
            values.append({"name": ch, "on_select": on_change_char, "on_selected": None})

        # Current timbre name as ITEM menu
        item = []
        for i in list(range(TIMBRE_NAME_LENGTH)):
            ch = timbre[i:i+1]
            if ch == "":
                ch = " "
            item.append({"name": ch, "on_select": None, "on_selected": None, "selected": 0, "VALUE": values})

        item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_timbre_name, "on_selected": None}]})
        item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_timbre_name, "on_selected": None}]})

        SYNTH_MENU[MAIN_MENU_TIMBRE_NAME]["CATEGORY"].append({"name": timbre, "on_select": None, "on_selected": None, "ITEM": item})


# Cancel the changes to timbre name
def on_cancel_timbre_name():
    global menu_main, menu_category, menu_item, menu_value

    # Clear selected data and initialize the TIMBRE NAME menu
    menu_item = 0
    for itm in SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"]:
        itm["selected"] = 0

    menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
    show_menu(1)


# Change a timbre name and save all timbre data
def on_save_timbre_name():
    global YMF825pico
    global menu_main, menu_category, menu_item, menu_value

    # Change the current tone name
    name = ""
    for i in list(range(TIMBRE_NAME_LENGTH)):
        ch = CHARS_LIST[SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"]]
        name += ch if ch != CHARS_LIST[0] else SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["name"]

    print("CHANGE TIMBRE NAME[{}]={}".format(menu_category, name))
    YMF825pico.rename_timbre(menu_category, name)

    # Save tone data
    YMF825pico.save_timbre_data()

    # Initialize the TONE NAME menu
    make_edit_timbre_name_menu(menu_main, menu_main)
    on_cancel_timbre_name()


#--- MAIN MENE: TIMBRE EDIT
# Make timbre edit menu
def make_edit_timbre_edit_menu(menu, prev_menu):
    global YMF825pico

    clear_menu_memory(prev_menu, True, True, True)

    tone_list = YMF825pico.get_synth_tone_names()
    values_tone = []
    for tone in tone_list:
        values_tone.append({"name": tone, "on_select": on_change_timbre_edit, "on_selected": None})

    values_voice = []
    for voice in list(range(16)):
        values_voice.append({"name": str(voice), "on_select": on_change_timbre_edit, "on_selected": None})

    values_volume = []
    for volume in list(range(32)):
        values_volume.append({"name": str(volume), "on_select": on_change_timbre_edit, "on_selected": None})

    timbre_list = YMF825pico.get_synth_timbre_names()
    print("TIMBER LIST:", timbre_list)
    SYNTH_MENU[MAIN_MENU_TIMBRE_EDIT]["CATEGORY"] = []
    timbre_id = 0
    for timbre in timbre_list:

        # TIMBER SET ITEM menu
        item = []
        for portion in list(range(YMF825pico.TIMBRE_PORTIONS)):
            item.append({"name": "TONE{}".format(portion), "on_select": None, "on_selected": None, "selected": YMF825pico.get_timbre_tone(timbre_id, portion), "VALUE": values_tone})
            item.append({"name": "VOICE L{}".format(portion), "on_select": None, "on_selected": None, "selected": YMF825pico.get_timbre_voice_from(timbre_id, portion), "VALUE": values_voice})
            item.append({"name": "VOICE H{}".format(portion), "on_select": None, "on_selected": None, "selected": YMF825pico.get_timbre_voice_to(timbre_id, portion), "VALUE": values_voice})
            item.append({"name": "VOLUME{}".format(portion), "on_select": None, "on_selected": None, "selected": YMF825pico.get_timbre_volume(timbre_id, portion), "VALUE": values_volume})

        item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_timbre_edit, "on_selected": None}]})
        item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_timbre_edit, "on_selected": None}]})

        SYNTH_MENU[MAIN_MENU_TIMBRE_EDIT]["CATEGORY"].append({"name": timbre, "on_select": None, "on_selected": None, "ITEM": item})
        timbre_id += 1


def on_change_timbre_edit():
    global menu_main, menu_category, menu_item, menu_value
    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = menu_value


def on_cancel_timbre_edit():
    global menu_main, menu_category, menu_item, menu_value

    # Clear selected data and initialize the TIMBRE NAME menu
    menu_item = 0
    make_edit_timbre_edit_menu(menu_main, menu_main)
    menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
    show_menu(1)


def on_save_timbre_edit():
    global YMF825pico
    global menu_main, menu_category, menu_item, menu_value

    # Change the current timbre settings
    print("CHANGE TIMBRE SETTINGS[{}]".format(menu_category))
    for portion in list(range(YMF825pico.TIMBRE_PORTIONS)):
        i = portion * 4
        tone = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"]
        YMF825pico.set_timbre_portion_tone(menu_category, portion, tone)

        vfrom = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i+1]["selected"]
        vto   = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i+2]["selected"]
        YMF825pico.set_timbre_voice_range(menu_category, portion, vfrom, vto)

        volume = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i+3]["selected"]
        YMF825pico.set_timbre_portion_volume(menu_category, portion, volume)

    # Save timbre data
    YMF825pico.save_timbre_data()
    on_cancel_timbre_edit()


#--- MAIN MENE: TONE NAME
# Make edit tone name menu (TONE>tone list>tone name>selelct)
def make_edit_tone_name_menu(menu, prev_menu):
    global YMF825pico

    clear_menu_memory(prev_menu, True, True, True)

    tone_list = YMF825pico.get_synth_tone_names()
    SYNTH_MENU[MAIN_MENU_TONE_NAME]["CATEGORY"] = []
    for tone in tone_list:
        values = []
        for ch in CHARS_LIST:
            values.append({"name": ch, "on_select": on_change_char, "on_selected": None})

        # Current tone name as ITEM menu
        item = []
        for i in list(range(TONE_NAME_LENGTH)):
            ch = tone[i:i+1]
            if ch == "":
                ch = " "
            item.append({"name": ch, "on_select": None, "on_selected": None, "selected": 0, "VALUE": values})

        item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_tone_name, "on_selected": None}]})
        item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_tone_name, "on_selected": None}]})

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
    show_menu(1)


# Change a tone name and save all tone data
def on_save_tone_name():
    global YMF825pico
    global menu_main, menu_category, menu_item, menu_value

    # Change the current tone name
    name = ""
    for i in list(range(TONE_NAME_LENGTH)):
        ch = CHARS_LIST[SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["selected"]]
        name += ch if ch != CHARS_LIST[0] else SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][i]["name"]

    print("CHANGE TONE NAME[{}]={}".format(menu_category, name))
    YMF825pico.rename_tone(menu_category, name)

    # Save tone data
    YMF825pico.save_tone_data()

    # Initialize the TONE NAME menu
    make_edit_tone_name_menu(menu_main, menu_main)
    on_cancel_tone_name()


#--- MAIN MENE: TONE EDIT
# Make edit tone edit menu (TONE EDIT>tone list>parameter name>selelct)
def make_edit_tone_edit_menu(menu, prev_menu):
    global YMF825pico

    clear_menu_memory(prev_menu, True, True, True)

    tone_list = YMF825pico.get_synth_tone_names()
    SYNTH_MENU[MAIN_MENU_TONE_EDIT]["CATEGORY"] = []
#    tone_id = 0
    for tone in tone_list:
        item = []

        item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_tone_edit, "on_selected": None}]})
        item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_tone_edit, "on_selected": None}]})

        SYNTH_MENU[MAIN_MENU_TONE_EDIT]["CATEGORY"].append({"name": tone, "on_select": on_select_tone_edit_tone, "on_selected": None, "ITEM": item})
#        tone_id += 1


# Make tone editor menu
def on_select_tone_edit_tone(menu, prev_menu):
    global YMF825pico

    # Remake ITEM>VALUE menu
    print("MENU={} CLEAR PREV={}".format(menu, prev_menu))
    clear_menu_memory(prev_menu, False, True, True)

    # Get tone data for editing
    tone_hash = YMF825pico.copy_tone_data_for_edit(menu_category)
    print("TONE HASH[{}]:".format(menu_category))

    values_parm = []
    for num in list(range(64)):
        values_parm.append({"name": str(num), "on_select": on_change_tone_parm, "on_selected": None})
        
    item = []
    for parm_def in YMF825_PARM:
        parm = parm_def[0]        
        print("PARM[{}/{}] = {}".format(parm, parm_def[1], tone_hash[parm_def[1]]))
        if parm_def[3] is None:
            item.append({"name": parm, "on_select": on_select_tone_parm, "on_selected": None, "selected": tone_hash[parm_def[1]], "VALUE": values_parm[0:parm_def[2]]})
        else:
            item.append({"name": parm, "on_select": on_select_tone_parm, "on_selected": None, "selected": tone_hash[parm_def[1]], "VALUE": [{"name": nm, "on_select": on_change_tone_parm, "on_selected": None} for nm in parm_def[3]]})

    item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_tone_edit, "on_selected": None}]})
    item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_tone_edit, "on_selected": None}]})
    SYNTH_MENU[MAIN_MENU_TONE_EDIT]["CATEGORY"][menu_category]["ITEM"] = item

    # Set EDITING Timbre
    YMF825pico.save_edited_data_to_tone(0)
    YMF825pico.set_synth_play_timbre(0)
    YMF825pico.set_timbre_tones(0)


def on_select_tone_parm(menu, prev_menu):
    if reflect_tone_edit():
        on_play_demo("DEMO1")


def on_change_tone_parm():
    global menu_main, menu_category, menu_item, menu_value

    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"] = menu_value


def on_cancel_tone_edit():
    global menu_main, menu_category, menu_item, menu_value

    # Clear selected data and initialize the TONE NAME menu
    menu_item = 0
    on_select_tone_edit_tone(menu_category, menu_category)
    menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
    show_menu(1)


prev_parm_hash = {}
def reflect_tone_edit(force_save = False):
    global YMF825pico
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
        for parm in parm_hash.keys():
            print("PARM[{}] = {}".format(parm, parm_hash[parm]))

        YMF825pico.set_editing_tone(parm_hash)
        YMF825pico.save_edited_data_to_tone(0)
        YMF825pico.set_synth_play_timbre(0)
        YMF825pico.set_timbre_tones(0)
        prev_parm_hash = parm_hash.copy()
        return True
    else:
        print("PARM NOT CHANGED.")
        return False


def on_save_tone_edit():
    print("on_save_tone_edit: IN")
    if reflect_tone_edit(True):
        YMF825pico.save_edited_data_to_tone(menu_category)
        YMF825pico.save_tone_data()
        print("on_save_tone_edit: DONE")

    on_play_demo("DEMO1")
    on_cancel_tone_edit()


#--- MAIN MENU: TONE COPY
# Make edit tone copy menu (TONE COPY>tone list>tone list>selelct)
def make_edit_tone_copy_menu(menu, prev_menu):
    global YMF825pico

    clear_menu_memory(prev_menu, True, True, True)

    tone_list = YMF825pico.get_synth_tone_names()
    SYNTH_MENU[MAIN_MENU_TONE_COPY]["CATEGORY"] = []
    for tone in tone_list:
        item = []

        item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_tone_edit, "on_selected": None}]})
        item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_tone_edit, "on_selected": None}]})

        SYNTH_MENU[MAIN_MENU_TONE_COPY]["CATEGORY"].append({"name": tone, "on_select": on_select_tone_copy_tone, "on_selected": None, "ITEM": item})


# Make copy target tone list as the item list
def on_select_tone_copy_tone(menu, prev_menu):
    global YMF825pico

    clear_menu_memory(prev_menu, False, True, True)

    item = []
    values_parm = [
        {"name": "NO", "on_select": None, "on_selected": None},
        {"name": "SURE?", "on_select": None, "on_selected": None},
        {"name": "YES", "on_select": on_change_copy_parm, "on_selected": None}
    ]
    tone_list = YMF825pico.get_synth_tone_names()
    for tone in tone_list:
        item.append({"name": tone, "on_select": None, "on_selected": None, "selected": 0, "VALUE": values_parm})

    item.append({"name": "SAVE",   "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_save_tone_edit, "on_selected": None}]})
    item.append({"name": "CANCEL", "on_select": None, "on_selected": None, "selected": 0, "VALUE": [{"name": "NO", "on_select": None, "on_selected": None}, {"name": "SURE?", "on_select": None, "on_selected": None}, {"name": "YES", "on_select": on_cancel_tone_edit, "on_selected": None}]})
    SYNTH_MENU[MAIN_MENU_TONE_COPY]["CATEGORY"][menu_category]["ITEM"] = item


# Copy a tone to another one
def on_change_copy_parm():
    global YMF825pico
    global menu_main, menu_category, menu_item, menu_value, prev_parm_hash

    print("Copy tone {} to {}.".format(menu_category, menu_item))
    if menu_category != menu_item:
        # Get tone data for editing
        tone_hash = YMF825pico.copy_tone_data_for_edit(menu_category)
        print("TONE HASH[{}]:".format(menu_category))
        YMF825pico.set_editing_tone(tone_hash)
        YMF825pico.save_edited_data_to_tone(menu_item)


# YMF825pico 4 layers' menu structures: MAIN>CATEGORY>ITEM>VALUE
SYNTH_MENU = [
    {   # MAIN_MENU_PLAY
        "name": "PLAY",
        "on_select": make_select_play_menu,
        "on_selected": None,
        "CATEGORY": [
            {   # MAIN_MENU_PLAY_MANUAL
                "name": "MANUAL",
                "on_select": make_select_timbre_menu,
                "on_selected": None,
                "ITEM": []
            },
            {   # MAIN_MENU_PLAY_DEMO
                "name": "DEMO",
                "on_select": make_select_demo_menu,
                "on_selected": None,
                "ITEM": []
            }
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

                # on select event
                if SYNTH_MENU[menu_main]["on_select"] is not None:
                    SYNTH_MENU[menu_main]["on_select"](menu_main, prev_menu)
                        
                # Change menu
                menu_category = 0
                menu_item = 0
                print("MENU: MAIN={} CATEGORY={} ITEM={}".format(menu_main, menu_category, menu_item))
                print("LENG: MAIN={}".format(len(SYNTH_MENU)))
                print("LENG: CATEGORY={}".format(len(SYNTH_MENU[menu_main]["CATEGORY"])))
                print("LENG: ITEM={}".format(len(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"])))
                print("ITEM: SELECTED={}".format(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]))
                menu_value = SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["selected"]
                show_menu(count)

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
                show_menu(count)

                # on selected event
                if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_selected"] is not None:
                    SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_selected"](menu_category, prev_category)

            # ITEM
            elif rte["NO"] == 2:
                prev_item = menu_item
                menu_item += count
                if menu_item < 0:
                    menu_item = len(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"]) - 1
                elif menu_item >= len(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"]):
                    menu_item = 0

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
                menu_value += count
                if menu_value < 0:
                    menu_value = 0
                elif menu_value >= len(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"]):
                    menu_value = len(SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"]) - 1
                else:
                    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"] is not None:
                        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"]()

                    # Change menu
                    show_menu(count)

                    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_selected"] is not None:
                        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_selected"]()


#Receive MIDI (work in a thread)
timbre_offset = 0
def midi_interface(midi_events, length):
    global timbre_offset

    bt = 0
    while bt < length:
        # MIDI command
        midi_cmd  = midi_events[bt]
        bt += 1
        left = length - bt

        # note on: 0x9n (n=0..f: MIDI CH)
        if (midi_cmd & 0xf0) == 0x90:
            if left >= 2:
                # Chanel -> Timbre
                timbre = (midi_cmd - 0x90 + timbre_offset) % YMF825pico.TIMBRE_PORTIONS
                # MIDI note
                midi_note = midi_events[bt]
                # MIDI velocity
                midi_velo = midi_events[bt + 1]
                bt += 2
                YMF825pico.play_by_timbre_note(timbre, midi_note, midi_velo)

        # note off: 0x8n (n=0..f: MIDI CH)
        elif (midi_cmd & 0xf0) == 0x80:
            if left >= 2:
                # Chanel -> Timbre
                timbre = (midi_cmd - 0x80 + timbre_offset) % YMF825pico.TIMBRE_PORTIONS
                # MIDI note
                midi_note = midi_events[bt]
                # MIDI velocity
                midi_velo = midi_events[bt + 1]
                bt += 2
                YMF825pico.stop_by_timbre_note(timbre, midi_note)
    
        # Control
        elif (midi_cmd & 0xf0) == 0xb0:
            if left >= 2:
                # Chanel -> Timbre
                timbre = (midi_cmd - 0xb0 + timbre_offset) % YMF825pico.TIMBRE_PORTIONS
                # MIDI note
                midi_note = midi_events[bt]
                # MIDI velocity
                midi_velo = midi_events[bt + 1]
                bt += 2
                
                # sustain: pressed:[2]==0x7f / released [2]==0
                if midi_note == 0x40:
                    YMF825pico.sustain_pedal(timbre, midi_velo == 0x7f)

                # modulation --> reset timbre_offset
                elif midi_note == 0x01:
                    timbre_offset = 0
                    print("MIDI: Modulation")
    
        elif (midi_cmd & 0xf0) == 0xe0:
            if left >= 2:
                # MIDI note
                midi_note = midi_events[bt]
                # MIDI velocity
                midi_velo = midi_events[bt + 1]
                bt += 2

                # pitch+ --> timbre+
                if midi_note == 0x47:
                    timbre_offset = (timbre_offset + 1) % YMF825pico.TIMBRE_PORTIONS
            
                # pitch- --> timbre-
                elif midi_note == 0x39:
                    timbre_offset = (timbre_offset - 1) % YMF825pico.TIMBRE_PORTIONS


#Set up hardware
def setup():
    print("setup.")

    # Menu initialize
    if SYNTH_MENU[menu_main]["on_select"] is not None:
        SYNTH_MENU[menu_main]["on_select"](0, -1)

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["on_select"](0, -1)

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["on_select"](0, -1)

    if SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"] is not None:
        SYNTH_MENU[menu_main]["CATEGORY"][menu_category]["ITEM"][menu_item]["VALUE"][menu_value]["on_select"](0, -1)

    print("setup end.")


#Initialize application
def init():
    global display
    
    print("init.")

    # SSD1306 setup
    addr = i2c_ssd1306.scan()
    print("SSD1306 ADDRESS=" + hex(addr[0]))
    display = ssd1306.SSD1306_I2C(DISPLAY_WIDTH, DISPLAY_HEIGHT, i2c_ssd1306)
    print("SSD1306 display=", display)
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

    print("init() end.")


#Main
if __name__=='__main__':
    # CPU clock 240MHz
#    machine.freq(133000000)
    machine.freq(240000000)

    # UART
    uart = UART(UART_CH, baudrate=UART_BAUDRATE, tx=Pin(UART_TX), rx=Pin(UART_RX), bits=8, parity=None, stop=1)

    # YMF825
    YMF825pico = ymf825pico_class()
    init()
    setup()

    # YMF825 control class
    print("YMF825 PICO CLASS")
    YMF825pico.turn_on_synthesizer()
    YMF825pico.setup_synth()

    YMF825pico.play_demo()

    show_menu(1)

    # UART
    recv = 0
    uart_read = True

    while True:
        # Get rotary encoders
        get_rotary_encoders()

        # MIDI keyboard UART receive
        length = uart.any()
        if length > 0:
            read_bytes = uart.read(length)
#            print("UART:[", recv, ":", length, "]=", read_bytes)
#            for bt in read_bytes:
#                print("data=", hex(bt))
            uart_read = True

            if length == 3:
                midi_interface(read_bytes, length)

        elif uart_read:
            print("UART: waiting...")
            uart_read = False

    print("QUIT.")



