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
- FM synthesizer with 7 algorithms and 4 operators (A, B, C, D).
- 29 wave forms each operator.
- 16 voices.  Each voice can have different tone.
- Multi Timbre. A timbre consists of 4 portions (0..3) with each tone.
- Each portion in a timbre has a MIDI channel to play with both note on and off.
- 3 layers biquad filters are placed following the sound output. 
- You can save 10 databanks each bank contains 20 Timbre sets, 20 Tones and 10 Equalizers in PICO.

## MIDI Events
- Note on event with verosity.
- Sustain pedal event.
- Pitch+ event increments the Base Tone Number (BTN).
- Pitch- event decrements the Base Tone Number (BTN).
- Modulation event resets the BTN to zero (default).
    Therefore ((MIDI CH - 1 + BTN) % 4) corresponds to a portion number to play.
    YMF825 chip does not support both pitch bend and modulation,
    so YMF825pico assigns the original functions to these events.

## Interfaces
- An OLED display and 4 rotary encoders for UI to control the synthesizer. 
- MIDI IN (DIN5) available (NOT support USB MIDI).
- Audio output for a stereo passive speaker (but output is monoral).
    
## YMF825 Sound Editor:
- [User's Manual](https://github.com/ohira-s/YMF825pico/blob/master/doc/YMF825picoUsersManual.md)
- [Web Site（日本語）](https://www.thymes-square.net/?p=41)

  The web site is written in Japanese, and access to the site might be limited from Japan for security problems.  Sorry for inconvenience.