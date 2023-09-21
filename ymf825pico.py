# -*- coding: utf-8 -*-
##################################################################################
# YMF825 synthesizer with Raspberry Pi PICO Class.
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
# Synthesizer Structure
#             ---PORTION0:VOICEa..b---TONEp---
#            |                                |
#            |---PORTION1:VOICEc..d---TONEq---|
#   TIMBREx--|                                |---SOUND--->YMF825
#            |---PORTION2:VOICEe..f---TONEr---|
#            |                                |
#             ---PORTION3:VOICEg..h---TONEs---
#
#     This synthesizer has TIMBRES timbres.
#     Each timbre has 4 portions.
#     Each portion is able to have some voices (from 0 to 16).
#     A voice is one of voice chanel in YMF825.  YMF825 has voices from 0 to 15. 
#     Each voice use a tone data.  Tone is a set of YMF825 sound parameters.
#
# Copyright (c) by Shunsuke Ohira
#   00.600 2022/05/09: For Pi400 (original)
#   00.100 2023/08/05: For PICO W
#   01.000 2023/08/31: MIDI Keyboard available.
#   01.001 2023/09/04: Databank available
#   01.002 2023/09/19: Reduce global variable memory
#   01.300 2023/09/19: Tones in the timbre can be selected from the other databank
#   01.500 2023/09/21: MIDI channel can be assigned to each timbre portion
##################################################################################

from machine import Pin, SPI
import time
import json
import re
#from decimal import Decimal
import math


## YMF825 hardware control class for Raspberry Pi PICO W ##
class ymf825pico_class:

    # Initializer
    def __init__( self, file_tone_name = "YMF825ToneName.txt", file_tone_param = "YMF825ToneParm.txt", file_timbre_name = "YMF825TimbreName.txt", file_timbre_param = "YMF825TimbreParm.txt", file_equalizer_name = "YMF825EQName.txt", file_equalizer_param = "YMF825EQParm.txt", file_encode = "utf-8" ):
        # PICO GPIO and pin no.
        self.SPI_CH = 0
        self.SPIPORT_MOSI = 19    # pin25
        self.SPIPORT_MISO = 16    # pin21
        self.SPIPORT_CLK  = 18    # pin24
        self.SPIPORT_CE   = 17    # pin22
        self.YMF825_RESET = 22    # pin29
        self.GPIO_LED     = 28    # pin34    # N/A

        # SPI mode0
        self.SPI_MAX_SPEED_HZ = 1000000
        self.spi_cs = Pin(self.SPIPORT_CE, Pin.OUT)
        self.spi = SPI(self.SPI_CH, sck=Pin(self.SPIPORT_CLK), mosi=Pin(self.SPIPORT_MOSI), miso=Pin(self.SPIPORT_MISO), baudrate=self.SPI_MAX_SPEED_HZ, firstbit=SPI.MSB, polarity=0, phase=0)

        # YMF825 RESET pin
        self.YMF825_reset = Pin(self.YMF825_RESET, Pin.OUT)

        # LED (CURRENTLY NOT AVAILABLE)
        self.led_indicator = Pin(self.GPIO_LED, Pin.OUT)

        #Tone parameter [address(1byte)|data(35byte)].
        self.sound_param = bytearray(36)

        # Note number and Note name
        self.note_str = ["C_","C_#","D_","D_#","E_","F_","F_#","G_","G_#","A_","A_#","B_"]
        
        #Tone data HI.
        self.notenum_hi = (0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x10,0x18,0x18,0x18,0x18,0x18,0x20,0x20,0x20,0x20,0x28,0x11,0x11,0x19,0x19,0x19,0x19,0x19,0x21,0x21,0x21,0x21,0x29,0x12,0x12,0x1A,0x1A,0x1A,0x1A,0x1A,0x22,0x22,0x22,0x22,0x2A,0x13,0x13,0x1B,0x1B,0x1B,0x1B,0x1B,0x23,0x23,0x23,0x23,0x2B,0x14,0x14,0x1C,0x1C,0x1C,0x1C,0x1C,0x24,0x24,0x24,0x24,0x2C,0x15,0x15,0x1D,0x1D,0x1D,0x1D,0x1D,0x25,0x25,0x25,0x25,0x2D,0x16,0x16,0x1E,0x1E,0x1E,0x1E,0x1E,0x26,0x26,0x26,0x26,0x2E,0x17,0x17,0x1F,0x1F,0x1F,0x1F,0x1F,0x27,0x27,0x27,0x27,0x2F,0x10,0x10,0x18,0x18,0x18,0x18,0x18,0x20,0x20,0x20,0x20,0x28,0x11,0x11,0x19,0x19,0x19,0x19,0x10,0x1E)
        #Tone data LO.
        self.notenum_lo = (0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x79,0x17,0x37,0x59,0x7D,0x22,0x65,0x7A,0x11,0x29,0x42,0x5D,0x65,0x5D)

        #Tone parameter byte order and how to make a byte data
        self.synth_data_map = {
            ##COMMON
            # [ 2]: NOP 000000 | Basic Octave 11
            "Basic Oct":                           {"BYTE":  2, "SELF_MASK": 0x03, "SHFT_LEFT": 0, "DATA_MASK": 0x00},

            # [ 3]:LFO 11 | NOP 000 | Algorithm 111
            "LFO":                                    {"BYTE":  3, "SELF_MASK": 0x03, "SHFT_LEFT": 6, "DATA_MASK": 0x07},
            "Algorithm":                              {"BYTE":  3, "SELF_MASK": 0x07, "SHFT_LEFT": 0, "DATA_MASK": 0xf8},

            ##OP1
            # [ 4]: OP1:Sustain Rate 1111 | Ignore Key Off 0 | Key Scale Sensitivity 111
            "Sus R1":                          {"BYTE":  4, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Ign Key Off1":                        {"BYTE":  4, "SELF_MASK": 0x01, "SHFT_LEFT": 3, "DATA_MASK": 0xf7},
            "KeySc Sens1":                 {"BYTE":  4, "SELF_MASK": 0x07, "SHFT_LEFT": 0, "DATA_MASK": 0xf8},

            # [ 5]: OP1:Release Rate 1111 | Decay Rate 0000
            "Release R1":                          {"BYTE":  5, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Decay R1":                            {"BYTE":  5, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [ 6]: OP1:Attack Rate 1111 | Sustain Level 0000
            "Attack R1":                           {"BYTE":  6, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Sus Level1":                         {"BYTE":  6, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [ 7]: OP1:Total Operator Level 111111 | Key Scale Level Sensivitiy 00
            "Operator Lv1":                  {"BYTE":  7, "SELF_MASK": 0x3f, "SHFT_LEFT": 2, "DATA_MASK": 0x03},
            "KSL Sens1":            {"BYTE":  7, "SELF_MASK": 0x03, "SHFT_LEFT": 0, "DATA_MASK": 0xfc},

            # [ 8]: OP1:Depth Of Amp Modulation 111 | Enable Amp Modulation 0 | Depth Of Vibrate 111 | Enable Vibrate 0
            "Depth Amp Mod1":               {"BYTE":  8, "SELF_MASK": 0x07, "SHFT_LEFT": 5, "DATA_MASK": 0x1f},
            "Enable Amp Mod1":                 {"BYTE":  8, "SELF_MASK": 0x01, "SHFT_LEFT": 4, "DATA_MASK": 0xef},
            "Depth Vib1":                      {"BYTE":  8, "SELF_MASK": 0x07, "SHFT_LEFT": 1, "DATA_MASK": 0xf1},
            "Enable Vib1":                        {"BYTE":  8, "SELF_MASK": 0x01, "SHFT_LEFT": 0, "DATA_MASK": 0xfe},

                # [ 9]: OP1:Multi Control Magnification Frequency 1111 | Detune 0000
            "MCMFreq1": {"BYTE":  9, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Detune1":                                {"BYTE":  9, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [10]: OP1:Wave Shape 11111 | FM Feedback Level 000
            "Wave Shape1":                            {"BYTE": 10, "SELF_MASK": 0x1f, "SHFT_LEFT": 3, "DATA_MASK": 0x07},
            "Feedback Lv1":                     {"BYTE": 10, "SELF_MASK": 0x07, "SHFT_LEFT": 0, "DATA_MASK": 0xf8},

            ##OP2
            # [11]: OP2:Sustain Rate 1111 | Ignore Key Off 0 | Key Scale Sensitivity 111
            "Sus R2":                          {"BYTE": 11, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Ign Key Off2":                        {"BYTE": 11, "SELF_MASK": 0x01, "SHFT_LEFT": 3, "DATA_MASK": 0xf7},
            "KeySc Sens2":                 {"BYTE": 11, "SELF_MASK": 0x07, "SHFT_LEFT": 0, "DATA_MASK": 0xf8},

            # [12]: OP2:Release Rate 1111 | Decay Rate 0000
            "Release R2":                          {"BYTE": 12, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Decay R2":                            {"BYTE": 12, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [13]: OP2:Attack Rate 1111 | Sustain Level 0000
            "Attack R2":                           {"BYTE": 13, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Sus Level2":                         {"BYTE": 13, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [14]: OP2:Total Operator Level 111111 | Key Scale Level Sensivitiy 00
            "Operator Lv2":                  {"BYTE": 14, "SELF_MASK": 0x3f, "SHFT_LEFT": 2, "DATA_MASK": 0x03},
            "KSL Sens2":            {"BYTE": 14, "SELF_MASK": 0x03, "SHFT_LEFT": 0, "DATA_MASK": 0xfc},

            # [15]: OP2:Depth Of Amp Modulation 111 | Enable Amp Modulation 0 | Depth Of Vibrate 111 | Enable Vibrate 0
            "Depth Amp Mod2":               {"BYTE": 15, "SELF_MASK": 0x07, "SHFT_LEFT": 5, "DATA_MASK": 0x1f},
            "Enable Amp Mod2":                 {"BYTE": 15, "SELF_MASK": 0x01, "SHFT_LEFT": 4, "DATA_MASK": 0xef},
            "Depth Vib2":                      {"BYTE": 15, "SELF_MASK": 0x07, "SHFT_LEFT": 1, "DATA_MASK": 0xf1},
            "Enable Vib2":                        {"BYTE": 15, "SELF_MASK": 0x01, "SHFT_LEFT": 0, "DATA_MASK": 0xfe},

            # [16]: OP2:Multi Control Magnification Frequency 1111 | Detune 0000
            "MCMFreq2": {"BYTE": 16, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Detune2":                                {"BYTE": 16, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [17]: OP2:Wave Shape 11111 | FM Feedback Level 000
            "Wave Shape2":                            {"BYTE": 17, "SELF_MASK": 0x1f, "SHFT_LEFT": 3, "DATA_MASK": 0x07},
            "Feedback Lv2":                     {"BYTE": 17, "SELF_MASK": 0x07, "SHFT_LEFT": 0, "DATA_MASK": 0xf8},

            ##OP3
            # [18]: OP3:Sustain Rate 1111 | Ignore Key Off 0 | Key Scale Sensitivity 111
            "Sus R3":                          {"BYTE": 18, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Ign Key Off3":                        {"BYTE": 18, "SELF_MASK": 0x01, "SHFT_LEFT": 3, "DATA_MASK": 0xf7},
            "KeySc Sens3":                 {"BYTE": 18, "SELF_MASK": 0x07, "SHFT_LEFT": 0, "DATA_MASK": 0xf8},

            # [19]: OP3:Release Rate 1111 | Decay Rate 0000
            "Release R3":                          {"BYTE": 19, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Decay R3":                            {"BYTE": 19, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [20]: OP3:Attack Rate 1111 | Sustain Level 0000
            "Attack R3":                           {"BYTE": 20, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Sus Level3":                         {"BYTE": 20, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [21]: OP3:Total Operator Level 111111 | Key Scale Level Sensivitiy 00
            "Operator Lv3":                  {"BYTE": 21, "SELF_MASK": 0x3f, "SHFT_LEFT": 2, "DATA_MASK": 0x03},
            "KSL Sens3":            {"BYTE": 21, "SELF_MASK": 0x03, "SHFT_LEFT": 0, "DATA_MASK": 0xfc},

            # [22]: OP3:Depth Of Amp Modulation 111 | Enable Amp Modulation 0 | Depth Of Vibrate 111 | Enable Vibrate 0
            "Depth Amp Mod3":               {"BYTE": 22, "SELF_MASK": 0x07, "SHFT_LEFT": 5, "DATA_MASK": 0x1f},
            "Enable Amp Mod3":                 {"BYTE": 22, "SELF_MASK": 0x01, "SHFT_LEFT": 4, "DATA_MASK": 0xef},
            "Depth Vib3":                      {"BYTE": 22, "SELF_MASK": 0x07, "SHFT_LEFT": 1, "DATA_MASK": 0xf1},
            "Enable Vib3":                        {"BYTE": 22, "SELF_MASK": 0x01, "SHFT_LEFT": 0, "DATA_MASK": 0xfe},

            # [23]: OP3:Multi Control Magnification Frequency 1111 | Detune 0000
            "MCMFreq3": {"BYTE": 23, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Detune3":                                {"BYTE": 23, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [24]: OP3:Wave Shape 11111 | FM Feedback Level 000
            "Wave Shape3":                            {"BYTE": 24, "SELF_MASK": 0x1f, "SHFT_LEFT": 3, "DATA_MASK": 0x07},
            "Feedback Lv3":                     {"BYTE": 24, "SELF_MASK": 0x07, "SHFT_LEFT": 0, "DATA_MASK": 0xf8},

            ##OP4
            # [25]: OP4:Sustain Rate 1111 | Ignore Key Off 0 | Key Scale Sensitivity 111
            "Sus R4":                          {"BYTE": 25, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Ign Key Off4":                        {"BYTE": 25, "SELF_MASK": 0x01, "SHFT_LEFT": 3, "DATA_MASK": 0xf7},
            "KeySc Sens4":                 {"BYTE": 25, "SELF_MASK": 0x07, "SHFT_LEFT": 0, "DATA_MASK": 0xf8},

            # [26]: OP4:Release Rate 1111 | Decay Rate 0000
            "Release R4":                          {"BYTE": 26, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Decay R4":                            {"BYTE": 26, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [27]: OP4:Attack Rate 1111 | Sustain Level 0000
            "Attack R4":                           {"BYTE": 27, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Sus Level4":                         {"BYTE": 27, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [28]: OP4:Total Operator Level 111111 | Key Scale Level Sensivitiy 00
            "Operator Lv4":                  {"BYTE": 28, "SELF_MASK": 0x3f, "SHFT_LEFT": 2, "DATA_MASK": 0x03},
            "KSL Sens4":            {"BYTE": 28, "SELF_MASK": 0x03, "SHFT_LEFT": 0, "DATA_MASK": 0xfc},

            # [29]: OP4:Depth Of Amp Modulation 111 | Enable Amp Modulation 0 | Depth Of Vibrate 111 | Enable Vibrate 0
            "Depth Amp Mod4":               {"BYTE": 29, "SELF_MASK": 0x07, "SHFT_LEFT": 5, "DATA_MASK": 0x1f},
            "Enable Amp Mod4":                 {"BYTE": 29, "SELF_MASK": 0x01, "SHFT_LEFT": 4, "DATA_MASK": 0xef},
            "Depth Vib4":                      {"BYTE": 29, "SELF_MASK": 0x07, "SHFT_LEFT": 1, "DATA_MASK": 0xf1},
            "Enable Vib4":                        {"BYTE": 29, "SELF_MASK": 0x01, "SHFT_LEFT": 0, "DATA_MASK": 0xfe},

            # [30]: OP4:Multi Control Magnification Frequency 1111 | Detune 0000
            "MCMFreq4": {"BYTE": 30, "SELF_MASK": 0x0f, "SHFT_LEFT": 4, "DATA_MASK": 0x0f},
            "Detune4":                                {"BYTE": 30, "SELF_MASK": 0x0f, "SHFT_LEFT": 0, "DATA_MASK": 0xf0},

            # [31]: OP4:Wave Shape 11111 | FM Feedback Level 000
            "Wave Shape4":                            {"BYTE": 31, "SELF_MASK": 0x1f, "SHFT_LEFT": 3, "DATA_MASK": 0x07},
            "Feedback Lv4":                     {"BYTE": 31, "SELF_MASK": 0x07, "SHFT_LEFT": 0, "DATA_MASK": 0xf8}
        }
        
        # Sustain pedal control
        self.NO_SUSTAIN      = 0                              # Sustain pedal is released
        self.WILL_BE_SUSTAIN = 1                              # Sustain pedal was pressed while note on
        self.IN_SUSTAIN      = 2                              # Note off but sustain pedal is pressed
        self.sustain_pressed = -1;                            # True while sustain pedal is pressed, otherwise False

        # YMF825 Voices.
        self.VOICES = 16                                      # Maximum voices
        self.synth_voices  = [""] * self.VOICES               # Playing note like "C4" or "C4#" each voice, voices are spearated 4-timbres.
        self.synth_volumes = [0] * self.VOICES                # Playing note volume (0..31) each voice
        self.synth_sustain = [self.NO_SUSTAIN] * self.VOICES  # Sustain pedal status for each voice
#        self.synth_sounds = [[[0]*36]] * self.VOICES          # Sound parameters each voice
        self.synth_sounds = [bytearray(36)] * self.VOICES       # Sound parameters each voice
        self.synth_sel_voices = list(range(0,self.VOICES+1))  # Number of voices to assign each timbre portion
        self.synth_sel_volume = list(range(0,32))             # Voice volume (0..31)

        # Databank number (0..9)
        self.DATABANK_MAX = 10                                # Databank is a set of TIMBREs, TONEs and EQs
        self.DATABANK = 0                                     # Databank is a set of TIMBREs, TONEs and EQs

        # Sounds (YMF825 sound parameter).
        self.TONES = 20                                  # Maximum tones
        self.PRESET_TONES = 2                            # TONE 0 and 1 is preset tones, can NOT edit
        self.synth_edit_tone = 0
        self.synth_tone_names = ["NoName"] * self.TONES
        self.synth_tones = [[0,0x80 + self.VOICES]+[0]*30+[0x80,0x03,0x81,0x80]] * self.TONES

        # Multi-Timbre.
        self.TIMBRES = 20                                   # Maximum timbres
        self.TIMBRE_PORTIONS = 4                            # Maximum portions in timbre
        self.synth_play_timbre = 0                          # Playing timbre index
        self.synth_timbre_names = ["NoName"] * self.TIMBRES # Timbre names list
        self.synth_timbres = [[                             # YMF825 voice number (from-to) and its tone index for each timbre [Timber List][Timber Postion][from to]
                                {"voice_from":  0, "voice_to": 15, "databank": 0, "tone": 0, "volume": 31, "midi_ch": 1},
                                {"voice_from": -1, "voice_to": -1, "databank": 0, "tone": 0, "volume":  0, "midi_ch": 2},
                                {"voice_from": -1, "voice_to": -1, "databank": 0, "tone": 0, "volume":  0, "midi_ch": 3},
                                {"voice_from": -1, "voice_to": -1, "databank": 0, "tone": 0, "volume":  0, "midi_ch": 4}
                             ]] * self.TIMBRES

        # Equalizer settings
        self.EQUALIZERS = 10
        self.synth_selected_equalizer = 1
        self.synth_equalizer_names = ["NoName"] * self.EQUALIZERS
        self.synth_equalizer_settings = [[
                                            {"ceq0": 1, "ceq1": 0, "ceq2": 0, "ceq3": 0, "ceq4": 0},
                                            {"ceq0": 1, "ceq1": 0, "ceq2": 0, "ceq3": 0, "ceq4": 0},
                                            {"ceq0": 1, "ceq1": 0, "ceq2": 0, "ceq3": 0, "ceq4": 0}
                                        ]] * self.EQUALIZERS

        # Files
        self.tone_name_file = file_tone_name
        self.tone_param_file= file_tone_param
        self.timbre_name_file = file_timbre_name
        self.timbre_param_file = file_timbre_param
        self.equalizer_name_file = file_equalizer_name
        self.equalizer_param_file = file_equalizer_param
        self.file_encode = file_encode
        
        # Equalizer parameters buffer (address + 15bytes)
        self.equalizer_ceq = bytearray(16)


    # LED indicator.
    #   onoff:: True:turn on, False: turn off
    def led_turn( self, onoff ):
        self.led_indicator.value(1 if onoff else 0)


    # Wait timer.
    #   msec:: Waite time in milli-seconds
    def delay( self, msec ):
        time.sleep( msec/1000 )


    # Set SPI Slave Select Pin (CE0).
    #   pinv:: GPIO.HIGH: not-select, GPIO.LOW: select
    def chip_select( self, sel ):
        self.spi_cs.value(0 if sel else 1)


    # Write byte array data to SPI.
    #   addr:: SPI register address
    #   data_array: byte data in array
    def spi_write( self, addr, data_array ):
        self.chip_select(True)
        data_array[0] = addr
        self.spi.write(data_array)
        self.chip_select(False)


    # Write one byte data to SPI.
    #   addr:: SPI register address
    #   byte_data: one byte data
    def spi_write_byte( self, addr, byte_data ):
        spi_byte_data = bytearray([addr, byte_data])
        self.chip_select(True)
        self.spi.write(spi_byte_data)
        self.chip_select(False)


    # Set YMF825 Chanel.
    def set_chanel( self ):
        self.spi_write_byte( 0x0F, 0x30 )       # Note on
        self.spi_write_byte( 0x10, 0x71 )       # Chanel volume
        self.spi_write_byte( 0x11, 0x00 )       # XVB
        self.spi_write_byte( 0x12, 0x08 )       # FRAC
        self.spi_write_byte( 0x13, 0x00 )       # FRAc


    # Note on (play a note).
    # NOTICE:: Never call this directory, use play_by_scale() or play_by_timbre_scale().
    #   fnumh, fnuml:: 2byte data to play, byte data for a note is in notenum_hi[note] and notenum_lo[note].
    def note_on( self, voice, notenum_h, notenum_l, volume = 0x7c ):
#        print("NOTE ON VOLUME =", str(volume))
        # Send note on to YMF825
        self.spi_write_byte( 0x0B, voice & 0x0f )
        self.spi_write_byte( 0x0C, volume & 0x7c )
        self.spi_write_byte( 0x0D, notenum_h )
        self.spi_write_byte( 0x0E, notenum_l )
        self.spi_write_byte( 0x0F, 0x40 | (voice&0x0f) )

        # LED
        self.led_turn( True )


    # Note off.
    #   Turn off the note playing.
    def note_off( self, voice, volume = 0x54 ):
        s = self.get_scale_number(self.synth_voices[voice])
        if 0 <= s and s <= 127:
#            print("STOP VOICE, SCALE:", voice,s)
            self.spi_write_byte( 0x0B, voice & 0x0f )
            self.spi_write_byte( 0x0C, volume & 0x7c )
            self.spi_write_byte( 0x0D, self.notenum_hi[s] )
            self.spi_write_byte( 0x0E, self.notenum_lo[s] )
            self.spi_write_byte( 0x0F, 0x00 | (voice&0x0f) )
        else:
            print("UNKNOWN STOP VOICE:[", voice, "]")
            
        # LED
        self.led_turn(False)


    # All notes off
    def all_notes_off( self ):
        for voice in list(range(self.VOICES)):
            self.note_off( voice )


    # Get scale number in fnum_hi nd lo.
    #   scale:: "C4", "D5#", "F2", "E3b" and so on. From "C0" to "G9".
    #
    #   RETURN:: scale number(index) in fnum_hi nd lo.
    def get_scale_number( self, scale ):
        octave = scale[1:2]
#        print("SCALE, OCTAVE=", scale, octave)
        if octave == "":
            return -1

        octv = 0 if not octave.isdigit() else (int(octave) + 1)
        sc = scale[0:1] + "_" + scale[2:]
#        print("SCALE BASE, OCTV, INDEX=", sc, octv, self.note_str.index(sc))
        if sc in self.note_str:
            try:
                return self.note_str.index(sc) + octv * 12
            except:
                return -1
        else:
            return -1


    # Play by a scale name, play time and rest time.
    # Use 0-voice only.
    #   scale:: "C4", "D5#", "F2", and so on. From "C0" to "G9".
    #   play:: note on time(msec).
    #   rest:: note off time(msec) after playing the note.
    def play_by_scale( self, scale, play, rest ):
        s = self.get_scale_number(scale)
        if 0 <= s and s <= 127:
            print("PLAY:", scale, "=", s, " ", play, "_", rest, "//")
            self.synth_voices[0] = scale
            self.note_on( 0, self.notenum_hi[s], self.notenum_lo[s] )
            self.delay( play )
            self.note_off( 0 )
            self.delay( rest )
        else:
            print("Unknown scale:", scale)


    # Get voice number playing new note in timbre.
    #   timbre_portion:: Multi-Timbre index (0..3).
    #   scale:: "C4", "D5#", "F2", and so on. From "C0" to "G9".
    #   play:: True: find a voice not playing, False: find the scale only.
    #
    #   RETURN:: voice number
    def get_voice_in_timbre( self, timbre_portion, scale, play=True ):
        v = -1
        if timbre_portion >= 0 and timbre_portion < self.TIMBRE_PORTIONS and self.synth_timbres[self.synth_play_timbre][timbre_portion]["voice_from"] >= 0:
            for i in range(self.synth_timbres[self.synth_play_timbre][timbre_portion]["voice_from"], self.synth_timbres[self.synth_play_timbre][timbre_portion]["voice_to"]+1):
                if self.synth_voices[i] == scale:
                    return i
                if play and self.synth_voices[i] == "":
                    v = i

        #There is no voice not playing, use "first-voice" in the tmbre
        if v == -1 and play:
            v = self.synth_timbres[self.synth_play_timbre][timbre_portion]["voice_to"]
            self.note_off(v)

        return v


    #Get a note string ("C4", "D#3", ...) of note number (60-->"C4")
    # scale:: note number
    #
    # String of the note
    def get_note_scale(self, scale):
        octave = int(scale / 12) - 1
        note = scale % 12
        return self.note_str[note] if octave < 0 else self.note_str[note].replace("_", str(octave))


    # Play by a scale name, call stop_by_timbre_scale() to turn off the scale.
    #   timbre_portion:: Multi-Timbre portion index (0..TIMBRE_PORTIONS)
    #   scale:: "C4", "D5#", "F2", and so on. From "C0" to "G9".
    #
    #   RETURN:: voice number
    def play_by_timbre_scale( self, timbre_portion, scale ):
        v = self.get_voice_in_timbre( timbre_portion, scale, True )
        if v >= 0 and self.synth_voices[v] != scale:
            s = self.get_scale_number(scale)
    
            if 0 <= s and s <= 127:
                volume = self.synth_timbres[self.synth_play_timbre][timbre_portion]["volume"]
                print("PLAY:", self.synth_play_timbre, self.synth_timbre_names[self.synth_play_timbre], timbre_portion, self.synth_tone_names[self.synth_timbres[self.synth_play_timbre][timbre_portion]["tone"]], ":", scale, "=", s, v, "vol =", volume)
                self.note_on( v, self.notenum_hi[s], self.notenum_lo[s], volume << 2 )
                self.synth_voices[v] = scale
                self.synth_volumes[v] = volume
                        
                # Sustain pedal
                if self.sustain_pressed == timbre_portion:
                    self.synth_sustain[v] = self.WILL_BE_SUSTAIN

#            print("VOICES=",synth_voices)
            else:
                print("Unknown play scale:", scale)
        else:
            print("No start voice:", self.synth_play_timbre, timbre_portion, scale)

        return v


    # Play by a scale name, call stop_by_timbre_scale() to turn off the scale.
    #   timbre_portion:: Multi-Timbre portion index (0..TIMBRE_PORTIONS)
    #   scale:: "C4", "D5#", "F2", and so on. From "C0" to "G9".
    #
    #   RETURN:: voice number
    def play_by_timbre_scale_velocity( self, timbre_portion, scale, velocity ):
        v = self.get_voice_in_timbre( timbre_portion, scale, True )
#        print("PLAY: portion, scale, v=", timbre_portion, scale, v)
        if v >= 0 and self.synth_voices[v] != scale:
            s = self.get_scale_number(scale)
    
            if 0 <= s and s <= 127:
                # Inerite sustain pedal if the timbre portion is changed
                if self.sustain_pressed != -1:
                    self.sustain_pressed = timbre_portion
                
                # Note on
                volume = self.synth_timbres[self.synth_play_timbre][timbre_portion]["volume"]
                volume = math.floor(volume * velocity / 127)
#                print("PLAY:", self.synth_play_timbre, self.synth_timbre_names[self.synth_play_timbre], timbre_portion, self.synth_tone_names[self.synth_timbres[self.synth_play_timbre][timbre_portion]["tone"]], ":", scale, "=", s, v, "vol =", volume)
                print("PLAY: T,TN, P, B, T=", self.synth_play_timbre, self.synth_timbre_names[self.synth_play_timbre], timbre_portion, self.synth_timbres[self.synth_play_timbre][timbre_portion]["databank"], self.synth_timbres[self.synth_play_timbre][timbre_portion]["tone"], ":", scale, "=", s, v, "vol =", volume)
                self.note_on( v, self.notenum_hi[s], self.notenum_lo[s], volume << 2 )
                self.synth_voices[v] = scale
                self.synth_volumes[v] = volume
                        
                # Sustain pedal
                if self.sustain_pressed == timbre_portion:
                    self.synth_sustain[v] = self.WILL_BE_SUSTAIN

#            print("VOICES=",synth_voices)
            else:
                print("Unknown play scale:", scale)
        else:
            print("No start voice:", self.synth_play_timbre, timbre_portion, scale)

        return v


    #  timbre_portion:: Multi-Timbre portion index (0..TIMBRE_PORTIONS)
    #  scale:: 60 = "C4", "From "C0" to "G9".
    #
    #  RETURN:: voice number
    def play_by_timbre_note(self, timbre_portion, scale, velocity):
        return self.play_by_timbre_scale_velocity(timbre_portion, self.get_note_scale(scale), velocity)
    

    # Stop a scale in the timbre.
    #   timbre_portion: Multi-Timbre portion index (0..TIMBRE_PORTIONS)
    #   scale:: "C4", "D5#", "F2", and so on. From "C0" to "G9".
    def stop_by_timbre_scale( self, timbre_portion, scale ):
        v = self.get_voice_in_timbre( timbre_portion, scale, False )
    
        if v >= 0:
            volume = self.synth_timbres[self.synth_play_timbre][timbre_portion]["volume"]
            volume = self.synth_volumes[v]
            
            # Sustail pedal
            if self.synth_sustain[v] == self.WILL_BE_SUSTAIN:
                print("SUSTAIN:", timbre_portion, scale, "=", v, "vol =", volume)
                self.synth_sustain[v] = self.IN_SUSTAIN

            # Sustail pedal is released
            else:
                print("STOP:", timbre_portion, scale, "=", v, "vol =", volume)
                self.note_off( v, volume << 2 )
                self.synth_voices[v] = ""
                
#        print("VOICES=", synth_voices)
        else:
            print("Unknown stop voice:", self.synth_play_timbre, timbre_portion, scale)


    #Stop a scale in the timbre.
    #  timbre_portion: Multi-Timbre portion index (0..TIMBRE_PORTIONS)
    #  scale:: 60 = "C4", "From "C0" to "G9".
    def stop_by_timbre_note(self, timbre_portion, scale):
        self.stop_by_timbre_scale(timbre_portion, self.get_note_scale(scale))


    #Set sutain pedal status
    #  timbre_portion: Multi-Timbre portion index (0..TIMBRE_PORTIONS)
    #  status:: True=Sutain pedal pressed, False=released.
    def sustain_pedal(self, timbre_portion, status):
        self.sustain_pressed = timbre_portion if status else -1;

        # Sustain pedal was pressed --> set sustain to playing voice in the timbre portion
        if status:
            for v in list(range(self.synth_timbres[self.synth_play_timbre][timbre_portion]["voice_from"], self.synth_timbres[self.synth_play_timbre][timbre_portion]["voice_to"]+1)):
                if self.synth_voices[v] != "":
                    self.synth_sustain[v] = self.WILL_BE_SUSTAIN
                    print("WILL_BE_SUSTAIN:", self.synth_voices[v])
        
        # Sustain pedal was released --> note off the notes in sustain mode (all timbres)
        else:
            for tp in list(range(0, self.TIMBRE_PORTIONS)):
                for v in list(range(self.synth_timbres[self.synth_play_timbre][tp]["voice_from"], self.synth_timbres[self.synth_play_timbre][tp]["voice_to"]+1)):
                    if self.synth_voices[v] != "":
                        if self.synth_sustain[v] == self.IN_SUSTAIN:
                            self.stop_by_timbre_scale(tp, self.synth_voices[v])
                            print("STOP SUSTAIN:", self.synth_voices[v])
                    
                        self.synth_sustain[v] = self.NO_SUSTAIN
        

    # Send sound data to YMF825.
    #   timbre_portion: Multi-Timbre portion index (0..TIMBRE_PORTIONS)
    def send_sound_to_YMF825( self, timbre ):
        all_sound_param = bytearray(self.synth_sounds[0][0:32])         # address + voices + prams
        for v in range(1,self.VOICES):                       # params * VOICES
            all_sound_param += bytearray(self.synth_sounds[v][2:32])
        all_sound_param += bytearray(self.synth_sounds[0][32:])         # trailer

        #Burst write mode
        print("YMF825 Burst write mode: ", timbre)
        self.spi_write_byte( 0x08, 0xF6 )
        self.delay(20)
        self.spi_write_byte( 0x08, 0x00 )

        #Write tone data to YMF825 FIFO.
        print("Write timbre tone data to YMF825:", timbre)
#    print("YMF825 PARAM:", all_sound_param)
        self.spi_write( 0x07, all_sound_param )


    # Get Synthesizer data map
    def get_synth_data_map( self ):
        return self.synth_data_map


    # Get Synthesizer tone names list
    def get_synth_tone_names( self ):
        return self.synth_tone_names


    # Get Synthesizer timbre names list
    def get_synth_timbre_names( self ):
        return self.synth_timbre_names


    # Get selected equalizer
    def get_selected_equalizer( self ):
        return self.synth_selected_equalizer


    # Get Synthesizer equalizer names list
    def get_synth_equalizer_names( self ):
        return self.synth_equalizer_names


    # Get synthesizer voices list
    def get_synth_sel_voices( self ):
        return self.synth_sel_voices


    # Get synthesizer volume list
    def get_synth_sel_volume( self ):
        return self.synth_sel_volume


    # Get playing timbre index
    def get_synth_play_timbre( self ):
        return self.synth_play_timbre


    # Set playing timbre index
    def set_synth_play_timbre( self, timbre ):
        self.synth_play_timbre = timbre


    # Get timbre voice from
    def get_timbre_voice_from( self, timbre, portion ):
        return self.synth_timbres[timbre][portion]["voice_from"]


    # Get timbre voice to
    def get_timbre_voice_to( self, timbre, portion ):
        return self.synth_timbres[timbre][portion]["voice_to"]


    # Get timbre voice from
    def get_playing_timbre_voice_from( self, portion ):
        return self.synth_timbres[self.synth_play_timbre][portion]["voice_from"]


    # Get timbre voice to
    def get_playing_timbre_voice_to( self, portion ):
        return self.synth_timbres[self.synth_play_timbre][portion]["voice_to"]


    # Get databank of the timbre voice tone
    def get_timbre_databank( self, timbre, portion ):
        return self.synth_timbres[timbre][portion]["databank"]


    # Get timbre voice tone
    def get_timbre_tone( self, timbre, portion ):
        return self.synth_timbres[timbre][portion]["tone"]


    # Get editing tone index
    def get_synth_edit_tone( self ):
        return self.synth_edit_tone


    # Get editing tone index
    def set_synth_edit_tone( self, tone ):
        self.synth_edit_tone = tone


    # Get
    def get_playing_timbre_tone( self, portion ):
        return self.synth_timbres[self.synth_play_timbre][portion]["tone"]


    # Set databank of the timbre portion tone
    def set_timbre_portion_databank( self, timbre, portion, bank ):
        self.synth_timbres[timbre][portion]["databank"] = bank


    # Set timbre portion tone
    def set_timbre_portion_tone( self, timbre, portion, tone ):
        self.synth_timbres[timbre][portion]["tone"] = tone


    # Set timbre portion volume
    def set_timbre_portion_volume( self, timbre, portion, volume ):
        self.synth_timbres[timbre][portion]["volume"] = volume


    # Get timbre portion volume
    def get_timbre_volume( self, timbre, portion ):
        return self.synth_timbres[timbre][portion]["volume"]


    # Set timbre portion midi channel
    def set_timbre_portion_midich( self, timbre, portion, midich ):
        self.synth_timbres[timbre][portion]["midi_ch"] = midich


    # Get timbre portion midi channel
    def get_timbre_portion_midich( self, timbre, portion ):
        return self.synth_timbres[timbre][portion]["midi_ch"]


    # Get timbre portion volume
    def get_playing_timbre_volume( self, portion ):
        return self.synth_timbres[self.synth_play_timbre][portion]["volume"]


    # Set timbre portion volume
    def set_playing_timbre_volume( self, portion, volume ):
        self.synth_timbres[self.synth_play_timbre][portion]["volume"] = volume


    # Get timbre portion midi channel
    def get_playing_timbre_midich( self, portion ):
        return self.synth_timbres[self.synth_play_timbre][portion]["midi_ch"]


    # Set equalizer
    #   eql:: Equalizer number (0..2)
    #   ceq#:: ceq-eql-#
    def set_equalizer( self, eql, ceq0 = 1.0, ceq1 = 0.0, ceq2 = 0.0, ceq3 = 0.0, ceq4 = 0.0 ):

        def dec2bin_frac( dec, sign = False, digits=54 ):
#            dec=Decimal(str(dec))
            dec=float(str(dec))
            mantissa=''
            nth=0
            first=0
            rb=False
            while dec:
                if dec  >= 1:
#                    mantissa += '1'
                    mantissa += '1' if not sign else '0'
                    dec = dec -1
                    if first==0:
                        first=nth
                else:
                    if nth!=0:
#                        mantissa += '0'
                        mantissa += '0' if not sign else '1'
                    else:
                        mantissa += '0.'
                dec*=2
                nth+=1
                if nth-first==digits:
                    if dec != 0:
                        rb=True
                    break

            carry = False
            if sign:
                print("SIGN BFR:", mantissa)
                revs = ""
                lman = len(mantissa)
                for b in range(1,lman-1):
                    if mantissa[-b] == "0":
                        revs = "1" + revs
                        if b != lman-2:
                            revs = mantissa[2:lman-b] + revs

                        break
                    else:
                        revs = "0" + revs
                        if b == lman-2:
                            carry = True

                mantissa = "0." + revs
                print("SIGN AFT:", mantissa, carry)

            return mantissa,carry,rb

        # Make CEQ# bytes data
        def make_ceq_bytes( ceq_num, ceq ):
            ceq_num = ceq_num * 3 + 1

            if ceq < 0.0:
                sign = True
                self.equalizer_ceq[ceq_num] = 0x80
                ceq = -ceq
                ceq_int = ( ~int(ceq) ) & 0x07
                ceq_frc = ceq - int(ceq)
            else:
                sign = False
                self.equalizer_ceq[ceq_num+1] = 0x00
                ceq_int = int(ceq) & 0x07
                ceq_frc = ceq - int(ceq)

            if ceq_frc != 0.0:
                mantissa,carry,rb = dec2bin_frac( ceq_frc, sign, 23 )
                if carry:
                    ceq_int += 1

                print("EQUALIZER BITS and CARRY = INT:", mantissa, carry, "=", ceq_int)
                self.equalizer_ceq[ceq_num] = self.equalizer_ceq[ceq_num] | ( ceq_int << 4 )
                print("FRC:: CEQ INT SHIFT ARRAY FRAC=", ceq, ceq_int, ( ceq_int << 4 ), self.equalizer_ceq[ceq_num], ceq_frc)
                for b in range(2,len( mantissa )):
                    print("BIT:", b, "=", mantissa[b])
                    if mantissa[b] == "1":
                        if   b <=  5:       #  2.. 5
                            self.equalizer_ceq[ceq_num  ] = self.equalizer_ceq[ceq_num  ] | ( 0x01 << ( 5-b) )
                        elif b <= 13:       #  6..13
                            self.equalizer_ceq[ceq_num+1] = self.equalizer_ceq[ceq_num+1] | ( 0x01 << (13-b) )
                        elif b <= 21:       # 14..21
                            self.equalizer_ceq[ceq_num+2] = self.equalizer_ceq[ceq_num+2] | ( 0x01 << (21-b) )

            else:
                if sign:
                    ceq_int += 1

                self.equalizer_ceq[ceq_num] = self.equalizer_ceq[ceq_num] | ( ceq_int << 4 )
                print("INT:: CEQ INT SHIFT ARRAY FRAC=", ceq, ceq_int, ( ceq_int << 4 ), self.equalizer_ceq[ceq_num], ceq_frc)

            print("EQL::", self.equalizer_ceq[ceq_num], self.equalizer_ceq[ceq_num+1], self.equalizer_ceq[ceq_num+2])

        # Clear CEQ bytes data
        for b in range(15):
            self.equalizer_ceq[b] = 0

        # Make CEQ0 bytes data
        make_ceq_bytes( 0, ceq0 )
        make_ceq_bytes( 1, ceq1 )
        make_ceq_bytes( 2, ceq2 )
        make_ceq_bytes( 3, ceq3 )
        make_ceq_bytes( 4, ceq4 )

        #Burst write mode and all key notes off
#    print("EDITOR: YMF825 Burst write mode.")
        self.spi_write_byte( 0x08, 0xF6 )
        self.delay(20)
        self.spi_write_byte( 0x08, 0x00 )

        #Write tone data to YMF825 FIFO.
#    print("EDITOR: Write sound data to YMF825.")
        print("EQUALIZER", eql, ":", list(self.equalizer_ceq))
        self.spi_write( 32 + eql, bytearray(list(self.equalizer_ceq)) )


    # Set timbre voice range.
    #   timbre:: Timbre index (0..TIMBRES-1)
    #   timbre_portion:: Timbre portion index(0..TIMBRE_PORTIONS-1) in the timbre
    #   vfrom:: vioce from
    #   vto  :: voice to
    def set_timbre_voice_range( self, timbre, timbre_portion, vfrom, vto ):
        if vfrom < 0 or vto < 0 or vfrom >= self.VOICES or vto >= self.VOICES:
            vfrom = -1
            vto = -1

        if vfrom <= vto:
            self.synth_timbres[timbre][timbre_portion]["voice_from"] = vfrom
            self.synth_timbres[timbre][timbre_portion]["voice_to"] = vto


    # Set timbre portion sound (but not send it to YMF825).
    #   timbre:: Timbre index (0..TIMBRES-1)
    #   timbre_portion:: timbre index (0..TIMBRE_PORTIONS)
    def set_timbre_tone( self, timbre, timbre_portion ):
        def load_tone_in(databank):
            try:
                file = open( self.tone_param_file.replace(".txt", str(databank) + ".txt"), encoding = self.file_encode )
            except OSError as e:
                print(e)
            else:
                tones_parm = json.load( file )
                file.close()

            file = None
            return tones_parm

        vs = self.synth_timbres[timbre][timbre_portion]["voice_from"];
        vt = self.synth_timbres[timbre][timbre_portion]["voice_to"];
        db = self.synth_timbres[timbre][timbre_portion]["databank"];
        del_flg = False
        if db != self.DATABANK:
            print("LOAD TONES in db, DATABANK=", db, self.DATABANK)
            tones_parm = load_tone_in(db)
            del_flg = True
        else:
            tones_parm = self.synth_tones

        if vs >=0 and vs <= vt:
#            print("SET TIMBER PORTION TONE", timbre, timbre_portion, self.synth_timbres[self.synth_play_timbre][timbre_portion]["tone"], ":", vs, vt )
            print("SET TIMBER PORTION TONE: T, P, B, T=", timbre, timbre_portion, db, self.synth_timbres[timbre][timbre_portion]["tone"], ":", vs, vt )
            for v in range(vs,vt+1):
                self.synth_sounds[v] = tones_parm[self.synth_timbres[timbre][timbre_portion]["tone"]].copy()

        if del_flg:
            del tones_parm


    # Set timber sound and send it to YMF825.
    #   timbre:: Timbre index (0..TIMBRES-1)
    def set_timbre_tones( self, timbre ):
        for p in range(self.TIMBRE_PORTIONS):
            self.set_timbre_tone( timbre, p )
#        print("TIMBRE TONE:", "tmbtone_T" + str(p))
#        gui_timbre_pane["tmbtone_T" + str(p)]["object"].set( synth_tone_names[synth_timbres[synth_play_timbre][p]["tone"]] )

        self.send_sound_to_YMF825( timbre )


    # Rename tone name
    #   tone:: Tone index (0..TONES-1)
    #   name:: name to rename
    #
    #   RETURN:: ("INFO|ERROR","TONE","message-string")
    def rename_tone( self, tone, name ):
        if tone == 0:
            self.synth_tone_names[tone] = "EDITING"
            return ("","TONE","")

        name = re.sub( '^ {1,}', "", name )
        name = re.sub( ' {1,}$', "", name )
        print("RENAME TONE", self.synth_tone_names[tone], "-->", name, ":", self.synth_tone_names.count( name ))

        if   name == "":
            return ( "ERROR", "TONE", "Illegal tone name." )
    
        elif self.synth_tone_names.count( name ) == 0:
            self.synth_tone_names[tone] = name
#        set_playing_timbre( synth_play_timbre )
            return ( "INFO", "TONE", "Tone name was renamed." )

        elif self.synth_tone_names.index( name ) != tone:
            return ( "ERROR", "TONE", "Same tone name already exists." )

        else:
            self.synth_tone_names[tone] = name

        return ("","TONE","")


    # Rename timbre name
    #   timbre:: Timbre index (0..TIMBRES-1)
    #   name:: name to rename
    #
    #   RETURN:: ("INFO|ERROR","TIMBRE","message-string")
    def rename_timbre( self, timbre, name ):
        name = re.sub( '^ {1,}', "", name )
        name = re.sub( ' {1,}$', "", name )
        print("RENAME TIMBER", self.synth_timbre_names[timbre], "-->", name, ":", self.synth_timbre_names.count( name ))

        if   timbre == 0:
            return ( "ERROR", "TIMBER", "Can't rename EDITING timbre." )

        elif name == "":
            return ( "ERROR", "TIMBER", "Illegal timbre name." )

        elif self.synth_timbre_names.count( name ) == 0:
            self.synth_timbre_names[timbre] = name
            return ( "INFO", "TIMBER", "Timbre name was renamed." )

        elif self.synth_timbre_names.index( name ) != timbre:
            return ( "ERROR", "TIMBER", "Same timbre name already exists." )

        return ("","TIMBRE","")


    # Rename euqalizer name
    def rename_equalizer( self, eql, name ):
        name = re.sub( '^ {1,}', "", name )
        name = re.sub( ' {1,}$', "", name )
        print("RENAME EQUALIZER", self.synth_equalizer_names[eql], "-->", name, ":", self.synth_equalizer_names.count( name ))

        if   ( eql == 0 or eql == 1 ) and self.synth_equalizer_names[eql] != name:
            return ( "ERROR", "EQUALIZER", "Can't rename EDITING or ALL PATH equalizer." )

        elif name == "":
            return ( "ERROR", "EQUALIZER", "Illegal equalizer name." )

        elif self.synth_equalizer_names.count( name ) == 0:
            self.synth_equalizer_names[eql] = name
            return ( "INFO", "EQUALIZER", "Equalizer name was renamed." )

        elif eql >= 2 and self.synth_equalizer_names.index( name ) != eql:
            return ( "ERROR", "EQUALIZER", "Same equalizer name already exists." )

        return ("","EQUALIZER","")


    # Get a editing tone parameters as hash
    #   sound_prm:: byte array of YMF825 sound parameter
    #   RETURN:: One sound parameter as hash
    def get_editing_tone( self, sound_prm ):
        paramHash = {"Address": 0, "Voices": sound_prm[ 1] - 0x80}
    
        for (param,proc) in self.synth_data_map.items():
            byte_order = proc["BYTE"]
            self_mask  = proc["SELF_MASK"]
            shift_left = proc["SHFT_LEFT"]
#        data_mask  = proc["DATA_MASK"]
            paramHash[param] = (sound_prm[byte_order] >> shift_left ) & self_mask

        return paramHash


    # make one sound parameters to all voices.
    # This function is for sound editor.
    #   paramHash:: Tone parameter to edit as a hash
    def make_sound_param( self, paramHash ):
        #HED: 0,0x81,
        ## [ 0]: Register Address (constant)
        self.sound_param[0] = 0

        ## [ 1]: Header 0x80 + voices(=16 constant)
        self.sound_param[1] = 0x80 + self.VOICES

        for (param,val) in paramHash.items():
            if param in self.synth_data_map:
#                print("Edit:", param, "=", val)
                byte_order = self.synth_data_map[param]["BYTE"]
                self_mask  = self.synth_data_map[param]["SELF_MASK"]
                shift_left = self.synth_data_map[param]["SHFT_LEFT"]
                data_mask  = self.synth_data_map[param]["DATA_MASK"]
                self.sound_param[byte_order] = (self.sound_param[byte_order] & data_mask) | ((val & self_mask) << shift_left)

            else:
                print("UNKNOWN PARAMETER NAME:", param, "=", val)

        # TRAILER CODES: 0x80,0x03,0x81,0x80
        self.sound_param[32]=0x80
        self.sound_param[33]=0x03
        self.sound_param[34]=0x81
        self.sound_param[35]=0x80
        return self.sound_param


    # Set one sound parameters to all voices.
    # This function is for sound editor.
    #   paramHash:: Tone parameter to edit as a hash
    def set_editing_tone( self, paramHash ):
        # Make the sound parameter bytearray (sound_param)
        self.make_sound_param(paramHash)

        #Burst write mode and all key notes off
#    print("EDITOR: YMF825 Burst write mode.")
        self.spi_write_byte( 0x08, 0xF6 )
        self.delay(20)
        self.spi_write_byte( 0x08, 0x00 )

        #Write tone data to YMF825 FIFO.
#    print("EDITOR: Write sound data to YMF825.")
#    print("Set end:", sound_param)
        self.spi_write( 0x07, bytearray(self.sound_param) )
#    print("Write end:", sound_param)


    # Save edited sound parameters to a tone data
    # The sound parameters in self.sound_param is set by self.set_editing_tone()
    #   tone: Tone index.
    def save_edited_data_to_tone( self, tone ):
        self.synth_tones[tone] = self.sound_param.copy()
    #    print("Save:", sound_param)


    # Copy a tone to the sound parameters to edit
    #   tone: Tone index.
    def copy_tone_data_for_edit( self, tone ):
        self.sound_param = self.synth_tones[tone].copy()
    #    print("Edit:", sound_param)
        return self.get_editing_tone( self.sound_param )


    # Set equalizer
    #   eql:: Equalizer setting number (0..EQUALIZERS-1)
    def set_synth_equalizer( self, eql ):
        if eql >= 0 and eql < self.EQUALIZERS:
            self.synth_selected_equalizer = eql
            for e in range(3):
                self.set_equalizer( e, self.synth_equalizer_settings[eql][e]["ceq0"], self.synth_equalizer_settings[eql][e]["ceq1"], self.synth_equalizer_settings[eql][e]["ceq2"], self.synth_equalizer_settings[eql][e]["ceq3"], self.synth_equalizer_settings[eql][e]["ceq4"] )


    # Save edited equalizer parameters to an equalizer
    #   eql:: Equalizer setting number (0..EQUALIZERS-1)
    #   eq#:: Three equalizers parameter hash {"ceq0".."ceq4"}
    def save_edited_data_to_equalizer( self, eql, eq0, eq1, eq2 ):
        if eql >= 0 and eql < self.EQUALIZERS:
            for c in range(5):
                self.synth_equalizer_settings[eql][0]["ceq"+str(c)] = eq0["ceq"+str(c)]

            for c in range(5):
                self.synth_equalizer_settings[eql][1]["ceq"+str(c)] = eq1["ceq"+str(c)]

            for c in range(5):
                self.synth_equalizer_settings[eql][2]["ceq"+str(c)] = eq2["ceq"+str(c)]


    # Get equalizer parameters
    #   eql:: Equalizer setting number (0..EQUALIZERS-1)
    #   RETURN:: Equalizer three parameters [0..2]{"ceq0".."ceq4"}
    def get_equalizer_parameters( self, eql ):
        if eql >= 0 and eql < self.EQUALIZERS:
            return( self.synth_equalizer_settings[eql] )

        return( None )


    # Get the current databak number
    def get_databank( self ):
        return self.DATABANK


    # Set databak number
    def set_databank( self, databank ):
        if 0 <= databank and databank < self.DATABANK_MAX:
            self.DATABANK = databank


    # Load tone data.
    def load_tone_data( self ):
        try:
            file = open( self.tone_name_file.replace(".txt", str(self.DATABANK) + ".txt"), encoding = self.file_encode )
        except OSError as e:
            print(e)
        else:
            self.synth_tone_names = json.load( file )
            file.close()

        file = None

        try:
            file = open( self.tone_param_file.replace(".txt", str(self.DATABANK) + ".txt"), encoding = self.file_encode )
        except OSError as e:
            print(e)
        else:
            self.synth_tones = json.load( file )
            file.close()

        file = None


    # Load timbre data.
    def load_timbre_data( self ):
        try:
            file = open( self.timbre_name_file.replace(".txt", str(self.DATABANK) + ".txt"), encoding = self.file_encode )
        except OSError as e:
            print(e)
        else:
            self.synth_timbre_names = json.load( file )
            file.close()

        file = None

        try:
            file = open( self.timbre_param_file.replace(".txt", str(self.DATABANK) + ".txt"), encoding = self.file_encode )
        except OSError as e:
            print(e)
        else:
            self.synth_timbres = json.load( file )
            file.close()

        file = None


    # Load equalizer data.
    def load_equalizer_data( self ):
        try:
            file = open( self.equalizer_name_file.replace(".txt", str(self.DATABANK) + ".txt"), encoding = self.file_encode )
        except OSError as e:
            print(e)
        else:
            self.synth_equalizer_names = json.load( file )
            file.close()

        file = None

        try:
            file = open( self.equalizer_param_file.replace(".txt", str(self.DATABANK) + ".txt") , encoding = self.file_encode )
        except OSError as e:
            print(e)
        else:
            self.synth_equalizer_settings = json.load( file )
            file.close()

        file = None


    # Save tone data.
    def save_tone_data( self, name_file = "YMF825ToneName.txt", tone_file = "YMF825ToneParm.txt", encode = "utf-8" ):
        try:
            file = open( name_file.replace(".txt", str(self.DATABANK) + ".txt"), "w", encoding = encode )
        except OSError as e:
            print(e)
        else:
            json.dump( self.synth_tone_names, file )
            file.close()

        file = None

        try:
            file = open( tone_file.replace(".txt", str(self.DATABANK) + ".txt"), "w", encoding = encode )
        except OSError as e:
            print(e)
        else:
            json.dump( self.synth_tones, file )
            file.close()

        file = None


    # Save timbre data.
    def save_timbre_data( self, name_file = "YMF825TimbreName.txt", timbre_file = "YMF825TimbreParm.txt", encode = "utf-8" ):
        try:
            file = open( name_file.replace(".txt", str(self.DATABANK) + ".txt"), "w", encoding = encode )
        except OSError as e:
            print(e)
        else:
            json.dump( self.synth_timbre_names, file )
            file.close()

        file = None

        try:
            file = open( timbre_file.replace(".txt", str(self.DATABANK) + ".txt"), "w", encoding = encode )
        except OSError as e:
            print(e)
        else:
            json.dump( self.synth_timbres, file )
            file.close()

        file = None


    # Save equalizer data.
    def save_equalizer_data( self, name_file = "YMF825EQName.txt", equalizer_file = "YMF825EQParm.txt", encode = "utf-8" ):
        try:
            file = open( name_file.replace(".txt", str(self.DATABANK) + ".txt"), "w", encoding = encode )
        except OSError as e:
            print(e)
        else:
            json.dump( self.synth_equalizer_names, file )
            file.close()

        file = None

        try:
            file = open( equalizer_file.replace(".txt", str(self.DATABANK) + ".txt"), "w", encoding = encode )
        except OSError as e:
            print(e)
        else:
            json.dump( self.synth_equalizer_settings, file )
            file.close()

        file = None


    # Reset and Initialize YMF825.
    def init_YMF825( self ):
        self.YMF825_reset.high()
        print("RESET HIGH")
        self.delay(1000)
        self.YMF825_reset.low()
        print("RESET LOW")
        self.delay(1000)
        self.YMF825_reset.high()
        self.delay(1000)
        print("Reset YMF825.")
      
        self.spi_write_byte( 0x1D, 0x00 )
        self.spi_write_byte( 0x02, 0x0E )
        self.delay(20)
      
        self.spi_write_byte( 0x00, 0x01 )
        self.spi_write_byte( 0x01, 0x00 )
        self.spi_write_byte( 0x1A, 0xA3 )
        self.delay(20)
      
        self.spi_write_byte( 0x1A, 0x00 )
        self.delay( 40 )
      
        self.spi_write_byte( 0x02, 0x04 )
        self.delay( 20 )
    
        self.spi_write_byte( 0x02, 0x00 )
    
        # add
        self.spi_write_byte( 0x19, 0xFF )
        self.spi_write_byte( 0x1B, 0x3F )
        self.spi_write_byte( 0x14, 0x00 )
        self.spi_write_byte( 0x03, 0x01 )
    
        self.spi_write_byte( 0x08, 0xF6 )
        self.delay( 40 )
        self.spi_write_byte( 0x08, 0x00 )
        self.spi_write_byte( 0x09, 0xF8 )
        self.spi_write_byte( 0x0A, 0x00 )
    
        self.spi_write_byte( 0x17, 0x40 )
        self.spi_write_byte( 0x18, 0x00 )
    
        print("YMF825 initialized.")


    # Set up hardware.
    def setup_hardware( self ):
        print("SPI uses CE0(pin24/port8)")
        self.led_turn( True )
        self.chip_select( False )

        print("spi object=", self.spi)
        print("Set up YMF825")
        self.init_YMF825()


    # Set up software
    def setup_synth( self ):
        # Clear tone data
        for t in range(1,self.TONES):
            self.synth_tones[t] = [0,0x80 + self.VOICES]+[0]*30+[0x80,0x03,0x81,0x80]

        # Clear timbre data
        for t in range(1,self.TIMBRES):
            self.synth_timbres[t] = [
                                        {"voice_from":  0, "voice_to":  7, "tone": 1},
                                        {"voice_from":  8, "voice_to": 11, "tone": 2},
                                        {"voice_from": 12, "voice_to": 13, "tone": 1},
                                        {"voice_from": 14, "voice_to": 15, "tone": 2}
                                    ]

        # Initialize EDITING tone (to be overwritten by load_tone_data)
        self.synth_tone_names[0] = "EDITING"

        # Load tone data
        self.load_tone_data()

        # load timbre data
        self.load_timbre_data()

        # load equalizer data
        self.load_equalizer_data()

        # Timbre0 is EDITING timbre (not to be overwritten by load_timbre_data)
        self.synth_timbre_names[0] = "EDITING"
        self.synth_timbres[0][0]["voice_from"] = 0
        self.synth_timbres[0][0]["voice_to"]   = self.VOICES-1
        self.synth_timbres[0][1]["voice_from"] = -1
        self.synth_timbres[0][1]["voice_to"]   = -1
        self.synth_timbres[0][2]["voice_from"] = -1
        self.synth_timbres[0][2]["voice_to"]   = -1
        self.synth_timbres[0][3]["voice_from"] = -1
        self.synth_timbres[0][3]["voice_to"]   = -1
        self.set_timbre_portion_tone( 0, 0, 0 )
        self.set_timbre_portion_tone( 0, 1, 0 )
        self.set_timbre_portion_tone( 0, 2, 0 )
        self.set_timbre_portion_tone( 0, 3, 0 )

#        self.set_playing_timbre( self.synth_play_timbre )
        self.set_synth_play_timbre( self.synth_play_timbre )
        self.set_timbre_tones( self.synth_play_timbre )
        self.set_chanel()

        # Equalizer1 must be path-through filter
        self.synth_equalizer_names[0] = "EDITING"
        self.synth_equalizer_names[1] = "ALL PATH"
        print("EQ PARAMS:", self.synth_equalizer_settings[1])
        for eq in range(3):
            self.synth_equalizer_settings[1][eq]["ceq0"] = 1.0
            self.synth_equalizer_settings[1][eq]["ceq1"] = 0.0
            self.synth_equalizer_settings[1][eq]["ceq2"] = 0.0
            self.synth_equalizer_settings[1][eq]["ceq3"] = 0.0
            self.synth_equalizer_settings[1][eq]["ceq4"] = 0.0

        self.set_synth_equalizer(0)

        print("Finished setting up.")
        self.led_turn(False)


    # Turn the Synthsize on
    def turn_on_synthesizer( self ):
#        self.init()
        self.setup_hardware()
