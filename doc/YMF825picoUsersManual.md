# **YMF825pico User's Manual**
## Sound
- FM synthesizer with 7 algorithms and 4 operators (A, B, C, D).
- 29 wave forms each operator.
- 16 voices.  Each voice can have different tone.
- Multi Timbre. A timbre consists of 4 portions (0..3) with each tone.
- Each portion in a timbre has a MIDI channel to play with both note on and off.
- 3 layers biquad filters are placed following the sound output. 
- You can save 10 databanks each bank contains 20 Timbre sets, 20 Tones and 10 Equalizers in PICO.

    MIDI CHa ---> TIMBREx-PORTION0 ---> DATABANK0..9:TONE0..19 ---> VOICES0..15 / VOLUME0..31

    MIDI CHb ---> TIMBREx-PORTION1 ---> DATABANK0..9:TONE0..19 ---> VOICES0..15 / VOLUME0..31

    MIDI CHc ---> TIMBREx-PORTION2 ---> DATABANK0..9:TONE0..19 ---> VOICES0..15 / VOLUME0..31

    MIDI CHd ---> TIMBREx-PORTION3 ---> DATABANK0..9:TONE0..19 ---> VOICES0..15 / VOLUME0..31


| BLOCK:     | DATABANK  | TIMBRE  | PORTION  | MIDI CH   | VOICE        | DATABANK:TONE  | EQUALIZER  |
|----------- | --------- | ------- | -------- | --------- | ------------ | ----- | ---------- |
| QTY:       | 0..9      | 0..19   | 0..3     | 1..16     | 0..15        | 0..19 | 0..9       |
| STRUCTURE: | DATABANKi | TIMBREj | PORTION0 | a  | V0from..V0to | DATABANKt:TONEp | EQUALIZERx |
|            |           |         | PORTION1 | b | V1from..V1to | DATABANKu:TONEq |            |
|            |           |         | PORTION2 | c | V2from..V2to | DATABANKv:TONEr |            |
|            |           |         | PORTION3 | d | V3from..V3to | DATABANKw:TONEs |            |

- You can assign same MIDI channel to any timbre potion.  In this case, all tones with the same MIDI channel will be played at the same time.


## MIDI Controles
- Note on event with MIDI channel and verosity.
- Note off event with MIDI channel.
- Sustain event pedal.
- Pitch+ event increments the Base Tone Number (BTN).
- Pitch- event decrements the Base Tone Number (BTN).
- Modulation event resets the BTN to zero (default).

  Therefore (MIDI Channel + BTN + 1) % 4 corresponds to a portion number to play. YMF825 chip does not support both pitch bend and modulation, so YMF825pico assigns the original functions to these events.

## Interfaces
- An OLED display and 4 rotary encoders for UI to control the synthesizer.
- MIDI IN (DIN5) available (NOT support USB MIDI).
- Audio output for a stereo passive speaker (but output is monoral).
## Softwares
- Interpreter: micropython for Raspberry Pi PICO.
- Application: main.py and ymf825pico.py
## Hardwares
- YMF825 breakout board
- Raspberry Pi PICO or PICO W
- MIDI/UART (3.3v) conversion circuit
- USB MIDI/MIDI interface (if you need)

# **System Block Diagram**
| Hardwares                       | Pins  | Dir  | PICO Pins   |
| ------------------------------- | ----- | ---- | ----------- |
| MIDI IN(DIN5)--->UART I/F       | Tx    | ---> | UART.Rx     |
| YMF825 breakout board           | RST_N | <--- | GPIO        |
|                                 | SS    | <--- | GPIO        |
|                                 | CLK   | <--- | SPI.CLK     |
|                                 | MOSI  | <--- | SPI.MOSI    |
|                                 | MISO  | ---> | SPI.MISO    |
| OLED Display SSD1306            | SCL   | <--- | I2C.SCL     |
|                                 | SDA   | <--- | I2C.SDA     |
| Rotary Encoder 1 (RT1:Main)     | A     | ---> | GPIO.pullup |
|                                 | B     | ---> | GPIO.pullup |
| Rotary Encoder 2 (RT2:Category) | A     | ---> | GPIO.pullup |
|                                 | B     | ---> | GPIO.pullup |
| Rotary Encoder 3 (RT3:Item)     | A     | ---> | GPIO.pullup |
|                                 | B     | ---> | GPIO.pullup |
| Rotary Encoder 4 (RT4:Value)    | A     | ---> | GPIO.pullup |
|                                 | B     | ---> | GPIO.pullup |
| LED (sending data to YMF825)    | anode | <--- | GPIO        |
| - built-in LED in RT4           |       |      |             |


# **Menu Structures**

YMF825pico has 4 layers menu structures as below.

	⁃ Main
	⁃ Category
	⁃ Item
	⁃ Value


| Main           | Category         | Item             | Value        |
| -------------- | ---------------- | ---------------- | ------------ |
| PLAY           | MANUAL           | *timbre list*    | NO/SET       |
|                | EQIALIZER        | *equalizer list* | NO/PLAY      |
|                | DEMO             | DEMO1..3         | NO/PLAY      |
|                | DATABANK         | 0..9             | NO/PLAY      |
| TIMBRE NAME    | *timbre list*    | A..z0..9         | =A..z0..9    |
| TIMBRE EDIT    | *timbre list*    | *parameters*     | *values*     |
| TONE NAME      | *tone list*      | A..z0..9         | =A..z0..9    |
| TONE EDIT      | *tone list*      | *parameters*     | *values*     |
| TONE COPY      | *tone list*      | *tone list*      | NO/SURE?/YES |
| EQUALIZER NAME | *equalizer list* | A..z0..9         | =A..z0..9    |
| EQUALIZER EDIT | *equalizer list* | *parameters*     | *values*     |

*italic*: variable list

There are 4 rotary encoders to change each layer's value.  For example, rotary encode 1 (RT1) is for the Main menu.  Rotate RT1, the Main menu will change the value as below.

    PLAY <--> TIMBRE NAME <--> TIMBRE EDIT <--> TONE NAME <-->
    TONE EDIT <--> TONE COPY <--> PLAY.

Turning a rotary encoder right, the menu scrolls down or the value is up. Turning it left, the menu scrolls up or the value is down.

- Rotary Encode and Menu

    | RT1  | RT2      | RT3  | RT4  |
    | ---- | -------- | ---- | ---- |
    | Main | Category | Item | Value|

An OLED display shows you the menus and the values.  THe layout is as below.

- OLED Display Layout

    | Main     |       |
    | -------- | ----- |
    | Category |       |
    | Item     | Value |
    | :        | :     |

- Example: TIMBRE EDIT

    | TIMBRE EDIT |        |
    | ----------- | ------ |
    | ROCK BAND   |        |
    | DATABANK0   | 0      |
    | TONE0       | GUITAR |
    | VOICE L0    | 0      |
    | VOICE H0    | 5      |
    | VOLUME0     | 31     |
    | DATABANK1   | 0      |
    | TONE1       | BASS   |
    | VOICE L1    | 6      |
    | VOICE H1    | 8      |
    | VOLUME1     | 31     |
    | DATABANK2   | 3      |
    | TONE2       | DRUM   |
    | VOICE L2    | 9      |
    | VOICE H2    | 11     |
    | VOLUME2     | 20     |
    | DATABANK3   | 1      |
    | TONE3       | SYNTH  |
    | VOICE L3    | 12     |
    | VOICE H3    | 15     |
    | VOLUME3     | 25     |


# **Main: PLAY**
- ## **Category: MANUAL (PLAY > MANUAL)**
  Play YMF825 by the current timbre, receive MIDI data via MIDI interface (DIN5).

    - ### **Item:** ***timbre list***
        The timbre names are listed in the Item area.

    - #### **Items and Values**
        | Items             | Values | Descriptions |
        | ----------------- | ------ | ------------ |
        | NOTES OFF         | NO     | Nothing happends. |
        |                   | SURE?  | Nothing happends. |
        |                   | YES    | All notes off. |
        | ***timbre name*** | NO     | Nothing happens. |
        |                   | SET    | Play with this timbre. |


- ## **Category: EQUALIZER (PLAY > EQUALIZER)**
  Apply an equalizer to playing sound.

    - ### **Item:** ***timbre list***
        The equalizer names are listed in the Item area.

    - #### **Items and Values**
        | Items                | Values | Descriptions |
        | -------------------- | ------ | ------------ |
        | ***equalizer name*** | NO     | Nothing happends. |
        |                      | SET    | Apply this equalizer. |


- ## **Category: DEMO (PLAY > DEMO)**
  Play demo music by the current timbre.

    - ### **Item:** ***demo list***
        The demo music names are listed in the Item area.
        Demo music must be written in YMF825pico sequencer format.

    - #### **Items and Values**
        | Items           | Values | Descriptions |
        | --------------- | ------ | ------------ |
        | ***demo name*** | NO     | Nothing happens. |
        |                 | PLAY   | Play this demo. |


- ## **Category: DATABANK (PLAY > DATABANK)**
  Load a dataset from a databank.

    - ### **Item:** ***demo list***
        Numbers of the databank (0..9) are listed in the Item area.

    - #### **Items and Values**
        | Items           | Values | Descriptions |
        | --------------- | ------ | ------------ |
        | ***0..9***      | NO     | Nothing happens. |
        |                 | LOAD   | Load this dataset. |


# **Main: TIMBRE NAME**
- ## **Category:** ***timbre list*** (TIMBRE NAME > ***timbre list***)
  Choose a timbre name to edit it.

    - ### **Item:** ***name characters***
        Characters of the timbre name are listed in the Item area.

    - #### **Items and Values**
        | Items           | Values     | Descriptions |
        | --------------- | ---------- | ------------ |
        | ***character*** | =          | Not change. |
        |                 | A..z0..9   | Change the character to this. |
        | SAVE            | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Save as new name. |
        | CANCEL          | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Cancel the changes. |


# **Main: TIMBRE EDIT**
- ## **Category:** ***timbre list*** (TIMBRE EDIT > ***timbre list***)
  Choose a timbre name to edit the parameters.

    - ### **Item:** ***timbre parameters***
        Timbre parameters are listed in the Item area.  A timbre has 4 tones (0..3).

    - #### **Items and Values**
        | Items           | Values          | Descriptions |
        | --------------- | --------------- | ------------ |
        | DATABANK0       | 0..9            | Select a databank number of the tone0. |
        | TONE0           | ***tone list*** | Select a tone for MIDI channel 1. |
        | VOICE L0        | 0..15           | Lower scale to play with this tone. |
        | VOICE H0        | 0..15           | Upper scale to play with this tone. |
        | VOLUME0         | 0..31           | Tone volume. |
        | MIDI CH0        | 1..16           | MIDI channel. |
        | DATABANK1       | 0..9            | Select a databank number of the tone1. |
        | TONE1           | ***tone list*** | Select a tone for MIDI channel 2. |
        | VOICE L1        | 0..15           | Lower voice number to assign this tone. |
        | VOICE H1        | 0..15           | Upper voice number to assign this tone. |
        | VOLUME1         | 0..31           | Tone volume. |
        | MIDI CH1        | 1..16           | MIDI channel. |
        | DATABANK2       | 0..9            | Select a databank number of the tone2. |
        | TONE2           | ***tone list*** | Select a tone for MIDI channel 3. |
        | VOICE L2        | 0..15           | Lower scale to play with this tone. |
        | VOICE H2        | 0..15           | Upper scale to play with this tone. |
        | VOLUME2         | 0..31           | Tone volume. |
        | MIDI CH2        | 1..16           | MIDI channel. |
        | DATABANK3       | 0..9            | Select a databank number of the tone3. |
        | TONE3           | ***tone list*** | Select a tone for MIDI channel 4. |
        | VOICE L3        | 0..15           | Lower scale to play with this tone. |
        | VOICE H3        | 0..15           | Upper scale to play with this tone. |
        | VOLUME3         | 0..31           | Tone volume. |
        | MIDI CH3        | 1..16           | MIDI channel. |
        | SAVE            | NO              | Nothing happens. |
        |                 | SURE?           | Nothing happens. |
        |                 | YES             | Save as new name. |
        | CANCEL          | NO              | Nothing happens. |
        |                 | SURE?           | Nothing happens. |
        |                 | YES             | Cancel the changes. |
        - Never overlap each tone's ranges of the voice number.
        - VOLUME? value is from 0 to 31.  The value is mapped from 0% to 100% to control master volume of the timbre?.

              The tone volume corresponds to MIDI velosity.


# **Main: TONE NAME**
- ## **Category:** ***tone list*** (TONE NAME > ***tone list***)
  Choose a tone name to edit it.

    - ### **Item:** ***name characters***
        Characters of the tone name are listed in the Item area.

    - #### **Items and Values**
        | Items           | Values     | Descriptions |
        | --------------- | ---------- | ------------ |
        | ***character*** | =          | Not change. |
        |                 | A..z0..9   | Change the character to this. |
        | SAVE            | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Save as new name. |
        | CANCEL          | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Cancel the changes. |


# **Main: TONE EDIT**
- ## **Category:** ***tone list*** (TONE EDIT > ***tone list***)
  Choose a tone name to edit the tone parameters.

    - ### **Item:** ***name characters***
        Tone parameters are listed in the Item area.
        A demo scores will sound automatically when target item editing is changed and the parameter value was changed.

    - #### **Items and Values**
        | Items           | Values     | Descriptions |
        | --------------- | ---------- | ------------ |
        | Basic OCT       | 0..3       | Basic octave. |
        | Algorithm       | 0..7       | Algorithm. |
        | LFO             | 0..7       | LFO frequency. |
        | Wave Shp A      | 0..31      | Operator-A wave shape. |
        | Total LV A      | 0..31      | Operator-A output level. |
        | MCM Freq A      | 0..15      | Operator-A multi control magnification frequency. |
        | Feedback A      | 0..7       | Operator-A feedback level. |
        | Detune   A      | 0..7       | Operator-A detune. |
        | Atack RT A      | 0..15      | Operator-A attack rate. |
        | Decay RT A      | 0..15      | Operator-A decay rate. |
        | Sustn LV A      | 0..15      | Operator-A sustain level. |
        | Sustn RT A      | 0..15      | Operator-A sustain rate. |
        | Reles RT A      | 0..15      | Operator-A release rate. |
        | Vibrt EN A      | OFF / ON   | Operator-A enable vibrate. |
        | Vibrt DP A      | 0..3       | Operator-A depth of vibrate. |
        | Amp M EN A      | OFF/ ON    | Operator-A enable amp modulation. |
        | Amp M DP A      | 0..3       | Operator-A depth of amp modulation. |
        | Key S EN A      | OFF / ON   | Operator-A key scale sensitivity. |
        | Key S LV A      | 0..3       | Operator-A key scale level sensivitiy. |
        | IgnKy OF A      | OFF / ON   | Operator-A ignore key off. |
        | Wave Shp B      | 0..31      | Operator-B wave shape. |
        | Total LV B      | 0..31      | Operator-B output level. |
        | MCM Freq B      | 0..15      | Operator-B multi control magnification frequency. |
        | Feedback B      | 0..7       | Operator-B feedback level. |
        | Detune   B      | 0..7       | Operator-B detune. |
        | Atack RT B      | 0..15      | Operator-B attack rate. |
        | Decay RT B      | 0..15      | Operator-B decay rate. |
        | Sustn LV B      | 0..15      | Operator-B sustain level. |
        | Sustn RT B      | 0..15      | Operator-B sustain rate. |
        | Reles RT B      | 0..15      | Operator-B release rate. |
        | Vibrt EN B      | OFF / ON   | Operator-B enable vibrate. |
        | Vibrt DP B      | 0..3       | Operator-B depth of vibrate. |
        | Amp M EN B      | OFF/ ON    | Operator-B enable amp modulation. |
        | Amp M DP B      | 0..3       | Operator-B depth of amp modulation. |
        | Key S EN B      | OFF / ON   | Operator-B key scale sensitivity. |
        | Key S LV B      | 0..3       | Operator-B key scale level sensivitiy. |
        | IgnKy OF B      | OFF / ON   | Operator-B ignore key off. |
        | Wave Shp C      | 0..31      | Operator-C wave shape. |
        | Total LV C      | 0..31      | Operator-C output level. |
        | MCM Freq C      | 0..15      | Operator-C multi control magnification frequency. |
        | Feedback C      | 0..7       | Operator-C feedback level. |
        | Detune   C      | 0..7       | Operator-C detune. |
        | Atack RT C      | 0..15      | Operator-C attack rate. |
        | Decay RT C      | 0..15      | Operator-C decay rate. |
        | Sustn LV C      | 0..15      | Operator-C sustain level. |
        | Sustn RT C      | 0..15      | Operator-C sustain rate. |
        | Reles RT C      | 0..15      | Operator-C release rate. |
        | Vibrt EN C      | OFF / ON   | Operator-C enable vibrate. |
        | Vibrt DP C      | 0..3       | Operator-C depth of vibrate. |
        | Amp M EN C      | OFF/ ON    | Operator-C enable amp modulation. |
        | Amp M DP C      | 0..3       | Operator-C depth of amp modulation. |
        | Key S EN C      | OFF / ON   | Operator-C key scale sensitivity. |
        | Key S LV C      | 0..3       | Operator-C key scale level sensivitiy. |
        | IgnKy OF C      | OFF / ON   | Operator-C ignore key off. |
        | Wave Shp D      | 0..31      | Operator-D wave shape. |
        | Total LV D      | 0..31      | Operator-D output level. |
        | MCM Freq D      | 0..15      | Operator-D multi control magnification frequency. |
        | Feedback D      | 0..7       | Operator-D feedback level. |
        | Detune   D      | 0..7       | Operator-D detune. |
        | Atack RT D      | 0..15      | Operator-D attack rate. |
        | Decay RT D      | 0..15      | Operator-D decay rate. |
        | Sustn LV D      | 0..15      | Operator-D sustain level. |
        | Sustn RT D      | 0..15      | Operator-D sustain rate. |
        | Reles RT D      | 0..15      | Operator-D release rate. |
        | Vibrt EN D      | OFF / ON   | Operator-D enable vibrate. |
        | Vibrt DP D      | 0..3       | Operator-D depth of vibrate. |
        | Amp M EN D      | OFF/ ON    | Operator-D enable amp modulation. |
        | Amp M DP D      | 0..3       | Operator-D depth of amp modulation. |
        | Key S EN D      | OFF / ON   | Operator-D key scale sensitivity. |
        | Key S LV D      | 0..3       | Operator-D key scale level sensivitiy. |
        | IgnKy OF D      | OFF / ON   | Operator-D ignore key off. |
        | CPadsl A>B      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-A to B. |
        | CPadsl A>C      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-A to C. |
        | CPadsl A>D      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-A to D. |
        | CPadsl B>A      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-B to A. |
        | CPadsl B>C      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-B to C. |
        | CPadsl B>D      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-B to D. |
        | CPadsl C>A      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-C to A. |
        | CPadsl C>B      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-C to B. |
        | CPadsl C>D      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-C to D. |
        | CPadsl D>A      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-D to A. |
        | CPadsl D>B      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-D to B. |
        | CPadsl D>C      | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Copy ADSSL-D to C. |
        | SAVE            | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Save the changes to PICO. |
        | CANCEL          | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Cancel the changes. |
        - You will see an expression like "Ab+cd" as the algorithm parameter.

          - a, b, c, d mean an operator in YMF825.
          - A capital letter like 'A' means an operator with self-feedback.
          - A small letter like 'a' means an operator without self-feedback.
          - '+' means a mixer.
          - Ab means the operator-A modulates the operator-b. 

        - If you choose Wave Shape, Total Level and MCM Frequency, you will see a 4 sub panes editor.  You can change these parameters in the same display.
        - If you choose ADSSL, you will see a 4 sub panes editor.  You can change these parameters in the same display.


# **Main: TONE COPY**
- ## **Category:** ***tone list*** (TONE COPY > ***tone list***)
  Choose a tone name to copy to another tone.

    - ### **Item:** DATABANK
        Choose a databank number (0..9) to copy a tone data to.  The tone list will be re-loaded just after the databank is changed.

    - ### **Item:** ***tone list***
        Tone names are listed in the Item area.  The tone data of category tone name will be copied to an item tone name.

    - #### **Items and Values**
        | Items           | Values| Descriptions |
        | --------------- | ----- | ------------ |
        | DATABANK        | 0..9  | Choose a databank to copy to |
        | ***tone list*** | NO    | Nothing happens. |
        |                 | SURE? | Nothing happens. |
        |                 | YES   | Copy to this tone. |


# **Main: EQUALIZER NAME**
- ## **Category:** ***equalizer list*** (EQUALIZER NAME > ***timbre list***)
  Choose a timbre name to edit it.

    - ### **Item:** ***name characters***
        Characters of the equalizer name are listed in the Item area.

    - #### **Items and Values**
        | Items           | Values     | Descriptions |
        | --------------- | ---------- | ------------ |
        | ***character*** | =          | Not change. |
        |                 | A..z0..9   | Change the character to this. |
        | SAVE            | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Save as new name. |
        | CANCEL          | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Cancel the changes. |


# **Main: EQUALIZER EDIT**
- ## **Category:** ***equalizer list*** (EQUALIZER EDIT > ***equalizer list***)
  Choose a equalizer name to edit the parameters.

    - ### **Item:** ***equalizer parameters***
        Equalizer parameters are listed in the Item area.  An equalizer has 3 biquad filters (1..3).

    - #### **Items and Values**
        | Items           | Values          | Descriptions |
        | ------------ | --------------- | ------------ |
        | DECIMAL PLC  | 0..9            | Choose a decimal place to edit. 0 means the integer part. |
        | FLT Type     | DIRECT          | Use parameters directly. |
        |              | LPF:FcQ         | Calculate parameters for LPF. |
        |              | HPF:FcQ         | Calculate parameters for HPF. |
        |              | BPFskt:FcQ      | Calculate parameters for BPFskt. |
        |              | BPF0db:FcQ      | Calculate parameters for BPF0db. |
        |              | NOTCH:FcQ       | Calculate parameters for NOTCH. |
        |              | APF:FcQ         | Calculate parameters for APF. |
        | Calc FLT     | NO              | Nothing happens. |
        |              | SURE?           | Nothing happens. |
        |              | CALC            | Calculate filter parameters. |
        | EQ1 B0/Fc    | -2.0 .. 2.0     | 1st biquad filter parameter b0. |
        |              |  0.0 .. 48.0    | 1st cut off frequency Fc1(kHz). |
        | EQ1 B1/Qv    | -2.0 .. 2.0     | 1st biquad filter parameter b1. |
        |              |  0.0 .. 10.0    | 1st Q value Qv1. |
        | EQ1 B2       | -2.0 .. 2.0     | 1st biquad filter parameter b2. |
        | EQ1 A1       | -2.0 .. 2.0     | 1st biquad filter parameter a1. |
        | EQ1 A2       | -2.0 .. 2.0     | 1st biquad filter parameter a2. |
        | FLT Type     | DIRECT          | Use parameters directly. |
        |              | LPF:FcQ         | Calculate parameters for LPF. |
        |              | HPF:FcQ         | Calculate parameters for HPF. |
        |              | BPFskt:FcQ      | Calculate parameters for BPFskt. |
        |              | BPF0db:FcQ      | Calculate parameters for BPF0db. |
        |              | NOTCH:FcQ       | Calculate parameters for NOTCH. |
        |              | APF:FcQ         | Calculate parameters for APF. |
        | Calc FLT     | NO              | Nothing happens. |
        |              | SURE?           | Nothing happens. |
        |              | CALC            | Calculate filter parameters. |
        | EQ2 B0/Fc    | -2.0 .. 2.0     | 2nd biquad filter parameter b0. |
        |              |  0.0 .. 48.0    | 1st cut off frequency Fc2(kHz). |
        | EQ2 B1/Qv    | -2.0 .. 2.0     | 2nd biquad filter parameter b1. |
        |              |  0.0 .. 10.0    | 1st Q value Qv2. |
        | EQ2 B2       | -2.0 .. 2.0     | 2nd biquad filter parameter b2. |
        | EQ2 A1       | -2.0 .. 2.0     | 2nd biquad filter parameter a1. |
        | EQ2 A2       | -2.0 .. 2.0     | 2nd biquad filter parameter a2. |
        | FLT Type     | DIRECT          | Use parameters directly. |
        |              | LPF:FcQ         | Calculate parameters for LPF. |
        |              | HPF:FcQ         | Calculate parameters for HPF. |
        |              | BPFskt:FcQ      | Calculate parameters for BPFskt. |
        |              | BPF0db:FcQ      | Calculate parameters for BPF0db. |
        |              | NOTCH:FcQ       | Calculate parameters for NOTCH. |
        |              | APF:FcQ         | Calculate parameters for APF. |
        | Calc FLT     | NO              | Nothing happens. |
        |              | SURE?           | Nothing happens. |
        |              | CALC            | Calculate filter parameters. |
        | EQ3 B0/Fc    | -2.0 .. 2.0     | 3rd biquad filter parameter b0. |
        |              |  0.0 .. 48.0    | 1st cut off frequency Fc3(kHz). |
        | EQ3 B1/Qv    | -2.0 .. 2.0     | 3rd biquad filter parameter b1. |
        |              |  0.0 .. 10.0    | 1st Q value Qv3. |
        | EQ3 B2       | -2.0 .. 2.0     | 3rd biquad filter parameter b2. |
        | EQ3 A1       | -2.0 .. 2.0     | 3rd biquad filter parameter a1. |
        | EQ3 A2       | -2.0 .. 2.0     | 3rd biquad filter parameter a2. |
        | LISTEN       | NO              | Nothing happens. |
        |              | PLAY            | Play a sample sound with the current equalizer settings. |
        | SAVE         | NO              | Nothing happens. |
        |              | SURE?           | Nothing happens. |
        |              | YES             | Save as new name. |
        | CANCEL       | NO              | Nothing happenSs. |
        |              | SURE?           | Nothing happens. |
        |              | YES             | Cancel the changes. |
        | RESET        | NO              | Nothing happens. |
        |              | SURE?           | Nothing happens. |
        |              | YES             | Reset to the all pass filter. |
        - A biquad filter's equation is as below.

                  b0 + b1/z + b2/z/z

          H(z) = -----------------------

                  a0 + a1/z + a2/z/z        : a0-->0.0

        - If FLT Type is DIRECT, parameter values B0, B1, B2, A1, A2 are used as filter parameters directly.
        - If a filter name is selected as FLT Type, you should set a cut off frequency (kHz) into a B0/Fc, and a Q value into a B1/Qv.  Then selecting CALC in the Calc FLT, the filter parameters are calculated in the B0, B1, B2, A1, A2 rows.


# **Music Sequencer File Format**
YMF825pico can play music with sequencer file. The file format is the original for YMF825pico.

## Header
The header part declares a databank and a timbre for an instruments to play sequencer music. And also declares an interval time to play one sequence step. 
### Format
    
    #DATABANK=***databank number***
    #TIMBRE=***timbre number***
    #WAIT=***interval(sec)***

### Example
    
    #DATABANK=1
    #TIMBRE=5
    #WAIT=0.5

## Score
The score line defines scores for each timbre portion.
### Format

    |***portion number***:***start note name***:***any characters for score***|***portion number***:...|

### Example
    |0:C3:_*_*__*_*_*__*_*__*_*_*__|1:F2:_*_*__*_*_|2:C4:_*_*__*_*_*__|

The score for the portion 0 covers the notes from C3 to C5. '_' means a white key in piano and '*' means a black key. However you can use any character except '|' for '_' and '*'.

In this case, the portion 3 has no note to play.

## Notes
### Format
    
    volume(0..9)  
    note off(-)

### Example

    |0:C3:_*_*__*_*_*__*_*__*_*_*__|1:F2:_*_*_*__*_*_|2:C4:_*_*__*_*_*__|
          9                                6    6
          .                                .    .
          .   7                            - 6  -   6   
          -   .                              .      .
              .  5                         6 -  6   -
              -  .                         .    .
                 .                         .    .
                 -                         -    -
    |0:C3:_*_*__*_*_*__*_*__*_*_*__|1:F2:_*_*__*_*_|2:C4:_*_*__*_*_*__|
          9   9  9                                       8   8      7
          .   .  .                                       .   .      .
          9   9  9                                       -   -      -
          .   .  .                                       8   8      7
          -   -  -                                       -   -      -

In the portion 0, YMF825pico sequencer plays C3 at the step 1.  C3 cotinues 3 steps, then stop at step 4.

In the portion2, both G2 and C3 sound at the step 1.

You can write the score line anywhere for getting readable score.

'-' executes a note off.  It uses one step for note off, so no note plays in the step.  If you want to execute note off and note on in one step, write a volume number at the step. '-' executes note off only, but volume number executes note off and note on in a step.
