# **YMF825pico Speciffications**
## Sound
	- FM synthesizer with 7 algorithms and 4 operators (A, B, C, D).
	- 29 wave forms each operator.
	- 16 voices.  Each voice can have different tone.
	- Multi Timbre. A timbre consists of 4 tones (0..3).
        (MIDI Channel % 4) corresponds to a tone number to play.
	- You can save 10 Timbre sets and 20 tones in PICO.
## Controles
	- Note on event with MIDI channel and verosity.
	- Note off event with MIDI channel.
	- Sustain event pedal.
	- Pitch+ event increments the Base Tone Number (BTN).
	- Pitch- event decrements the Base Tone Number (BTN).
	- Modulation event resets the BTN to zero (default).
        Therefore (MIDI Channel + BTN) % 4 corresponds to a tone number to play. YMF825 chip does not support both pitch bend and modulation, so YMF825pico assigns original functions to these events.

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

# System Block Diagram

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


| Main        | Category      | Item          | Value        |
| ----------- | ------------- | ------------- | ------------ |
| PLAY        | MANUAL        | *timbre list* | NO/SET       |
|             | DEMO          | DEMO1..3      | NO/PLAY      |
| TIMBRE NAME | *timbre list* | A..Z0..9      | =A..Z0..9    |
| TIMBRE EDIT | *timbre list* | *parameters*  | *values*     |
| TONE NAME   | *tone list*   | A..Z0..9      | =A..Z0..9    |
| TONE EDIT   | *tone list*   | *parameters*  | *values*     |
| TONE COPY   | *tone list*   | *tone list*   | NO/SURE?/YES |

*italic*: variable list

There are 4 rotary encoders to change each layer's value.  For example, rotary encode 1 (RT1) is for the Main menu.  Rotate RT1, the Main menu will change the value as below.

    PLAY <--> TIMBRE NAME <--> TIMBRE EDIT <--> TONE NAME <--> TONE EDIT <--> TONE COPY <--> PLAY.

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


# **Main: PLAY**
- ## **Category: MANUAL (PLAY > MANUAL)**
  Play YMF825 by the current timbre, receive MIDI data via MIDI interface (DIN5).

    - ### **Item:** ***timbre list***
        The timbre names are listed in the Item area.

    - #### **Items and Values**
        | Items             | Values | Descriptions |
        | ----------------- | ------ | ------------ |
        | ***timbre name*** | NO     | Nothing happens. |
        |                   | SET    | Play with this timbre. |


- ## **Category: DEMO (PLAY > DEMO)**
  Play demo music by the current timbre.

    - ### **Item:** ***demo list***
        The demo music names are listed in the Item area.

    - #### **Items and Values**
        | Items           | Values | Descriptions |
        | --------------- | ------ | ------------ |
        | ***demo name*** | NO     | Nothing happens. |
        |                 | PLAY   | Play this demo. |


# **Main: TIMBRE NAME**
- ## **Category:** ***timbre list*** (TIMBRE NAME > ***timbre list***)
  Choose a timbre name to edit it.

    - ### **Item:** ***name characters***
        Characters of the timbre name are listed in the Item area.

    - #### **Items and Values**
        | Items           | Values     | Descriptions |
        | --------------- | ---------- | ------------ |
        | ***character*** | =          | Not change. |
        |                 | A..Z0..9   | Change the character to this. |
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
        | TONE0           | ***tone list*** | Select a tone for MIDI channel 0. |
        | VOICE L0        | 0..15           | Lower scale to play with this tone. |
        | VOICE H0        | 0..15           | Upper scale to play with this tone. |
        | VOLUME0         | 0..31           | Tone volume. |
        | TONE1           | ***tone list*** | Select a tone for MIDI channel 1. |
        | VOICE L1        | 0..15           | Lower voice number to assign this tone. |
        | VOICE H1        | 0..15           | Upper voice number to assign this tone. |
        | VOLUME1         | 0..31           | Tone volume. |
        | TONE2           | ***tone list*** | Select a tone for MIDI channel 2. |
        | VOICE L2        | 0..15           | Lower scale to play with this tone. |
        | VOICE H2        | 0..15           | Upper scale to play with this tone. |
        | VOLUME2         | 0..31           | Tone volume. |
        | TONE3           | ***tone list*** | Select a tone for MIDI channel 3. |
        | VOICE L3        | 0..15           | Lower scale to play with this tone. |
        | VOICE H3        | 0..15           | Upper scale to play with this tone. |
        | VOLUME3         | 0..31           | Tone volume. |
        | SAVE            | NO              | Nothing happens. |
        |                 | SURE?           | Nothing happens. |
        |                 | YES             | Save as new name. |
        | CANCEL          | NO              | Nothing happens. |
        |                 | SURE?           | Nothing happens. |
        |                 | YES             | Cancel the changes. |
        - Never overlap each tone's ranges of the voice number.
        - VOLUME? are obsolete.

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
        |                 | A..Z0..9   | Change the character to this. |
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
        | Feedback A      | 0..7       | Operator-A feedback level. |
        | Detune   A      | 0..7       | Operator-A detune. |
        | MCM Freq A      | 0..15      | Operator-A multi control magnification frequency. |
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
        | Feedback B      | 0..7       | Operator-B feedback level. |
        | Detune   B      | 0..7       | Operator-B detune. |
        | MCM Freq B      | 0..15      | Operator-B multi control magnification frequency. |
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
        | Feedback C      | 0..7       | Operator-C feedback level. |
        | Detune   C      | 0..7       | Operator-C detune. |
        | MCM Freq C      | 0..15      | Operator-C multi control magnification frequency. |
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
        | Feedback D      | 0..7       | Operator-D feedback level. |
        | Detune   D      | 0..7       | Operator-D detune. |
        | MCM Freq D      | 0..15      | Operator-D multi control magnification frequency. |
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
        | SAVE            | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Save the changes. |
        | CANCEL          | NO         | Nothing happens. |
        |                 | SURE?      | Nothing happens. |
        |                 | YES        | Cancel the changes. |
        - You will see an expression like "Ab+cd" as the algorithm parameter.

          - a, b, c, d mean an operator in YMF825.
          - A capital letter like A means an operator with self-feedback.
          - A small letter like a means an operator without self-feedback.
          - + means a mixer.
          - Ab means the operator-A modulates the operator-b. 


# **Main: TONE COPY**
- ## **Category:** ***tone list*** (TONE COPY > ***tone list***)
  Choose a tone name to copy to another tone.

    - ### **Item:** ***tone list***
        Tone names are listed in the Item area.  The tone data of category tone name will be copied to an item tone name.

    - #### **Items and Values**
        | Items           | Values| Descriptions |
        | --------------- | ----- | ------------ |
        | ***tone list*** | NO    | Nothing happens. |
        |                 | SURE? | Nothing happens. |
        |                 | YES   | Copy to this tone. |


