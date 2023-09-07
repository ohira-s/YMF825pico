# YMF825pico
YMF825 FM synthesizer controlled with Raspberry Pi PICO.

## Installations:
- Prepare Raspberry Pi PICO or PICO W with micropython.
- Copy all files in data folder into PICO / folder.
- Copy all files in scores folder into PICO /scores/ folder.
- Copy YMF825pico_synth_main.py into PICO as main.py.
- Copy YMF825pico.py into PICO.
- YMF825piBasic.py is a test program, so don't care this file.

## Quick start:
- Connect a MIDI OUT of your MIDI instrument to a MIDI DIN5 connector of YMF825pico.
- MIDI CH should be 1ch.
- Connect a passive speaker or amplifire to a audio output of YMF825 board.
- Turn on PICO.
- Play your MIDI instrument.

## Specifications:
- 7 algorithms and 4 operators FM synthesizer.
- 29 wave forms each operator.
- 16 voices.
- Multi Timbre.
    A timbre consists of 4 tones (0..3)
    ((MIDI CH - 1) % 4) corresponds to a tone number to play (MIDI CH=1..16).
- You can save 10 databank in PICO, each databank has 20 timbre sets and 20 tones.
- Note on event with verosity.
- Sustain event pedal.
- Pitch+ event increments the Base Tone Number (BTN).
- Pitch- event decrements the Base Tone Number (BTN).
- Modulation event resets the BTN to zero (default).
    Therefore ((MIDI CH - 1 + BTN) % 4) corresponds to a tone number to play.
    YMF825 chip does not support both pitch bend and modulation,
    so YMF825pico assigns original functions to these events.
- An OLED display and 4 rotary encoders for UI to control the synthesizer. 
- MIDI IN (DIN5) available (NOT support USB MIDI).
- Audio output for a stereo passive speaker (but output is monoral).
    
## Edit YMF825 sound:
- [User's Manual](https://github.com/ohira-s/YMF825pico/blob/master/doc/YMF825picoUsersManual.md)
