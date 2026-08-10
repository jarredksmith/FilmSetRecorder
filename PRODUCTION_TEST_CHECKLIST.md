# Production readiness test checklist

Do not treat a passing GUI launch as proof that a field recorder is safe for production. Validate the exact hardware chain you will use.

## Audio-device validation

- UMC404HD is visible after cold boot
- Correct input device is selected after reboot
- Correct output device is selected after reboot
- Four input channels meter independently
- 48 kHz / 24-bit files verify correctly
- 96 kHz / 24-bit files verify correctly if that mode will be used
- Hardware Direct Monitor works as expected
- Phantom power behavior is verified on the interface

## Recording integrity

Run each test at 48 kHz and the intended buffer size.

- 10-second take
- 10-minute take
- 60-minute continuous take
- 2-hour continuous take
- 100 consecutive short takes
- rapid record/stop cycles
- record with all four channels at high level
- record while moving/resizing the UI
- record while ESP32 polls the remote API
- record while the display turns off
- verify zero dropped blocks
- investigate every XRUN

## Recovery tests

Use expendable test audio only.

- force-close the app during recording
- reboot Windows during a test recording
- disconnect external recording drive during a test take
- fill the drive until the low-disk interlock activates
- verify `.partial.wav` recovery after restart
- verify recovered audio duration and channel count

## Playback

- play a 10-second take
- play a long take without excessive memory growth
- stop playback repeatedly
- start recording after playback
- verify output routing on the intended headphone/speaker path

## Remote

- record from ESP32
- stop from ESP32
- next take from ESP32
- circle from ESP32
- walk to the expected maximum Wi-Fi distance
- temporarily lose Wi-Fi and verify the desktop recorder continues unaffected
- reconnect remote without restarting the recorder

## Power

- screen turns off without stopping recording
- idle sleep is prevented when enabled
- AC adapter removal behavior is understood
- battery runtime is measured
- Windows/macOS lid-close behavior is explicitly tested

## File handoff

- import poly WAV into the intended NLE/DAW
- verify channel order
- verify sample rate and bit depth
- verify JSON metadata
- verify sound_report.csv
- verify backups before deleting camera/sound media
