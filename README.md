# FilmSet Recorder 0.1

A first working scaffold for a Windows/macOS multichannel production-dialogue recorder, plus a Wi-Fi remote-control API intended for an ESP32 Cheap Yellow Display (CYD).

## What this prototype does

- Lists PortAudio/Core Audio/WASAPI/ASIO-visible devices through `sounddevice`.
- Auto-selects a device whose name contains `UMC404` when possible.
- Records up to the selected number of input channels into one polyphonic 24-bit WAV file.
- Defaults to 48 kHz, with 96 kHz selectable.
- Displays live per-channel peak meters.
- Uses an audio callback + queue + dedicated writer thread so disk I/O does not happen directly in the audio callback.
- Scene, take, roll and four track-name fields.
- Record, stop, play-last, next-take and circle-take controls.
- Creates a JSON sidecar with take metadata. (True BWF/iXML embedding is planned for the next stage.)
- Runs a small HTTP remote-control server on port 8765 for the ESP32 controller.

## Install and run

Python 3.11 or 3.12 is recommended for the prototype.

### Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

For the UMC404HD, install Behringer's current Windows driver first. In the application's device list, prefer the UMC404HD entry exposed through the best low-latency host API available on your machine. The prototype uses PortAudio via `sounddevice`; dedicated ASIO-path validation is an important next test on Windows.

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

On first use, macOS may ask for microphone permission for Terminal/Python or the packaged app.

## Recording layout

If project folder is `/MyFilm`, roll is `A001`, scene is `24B`, and take is 3:

```text
/MyFilm/
  A001/
    A001_24B_T003.wav
    A001_24B_T003.json
```

The WAV is a polyphonic file: each interface input is stored as its own channel.

## Remote API

The desktop program displays its local address near the bottom of the window.

Default port: `8765`

Default prototype token: `filmset`

Every protected request sends this header:

```text
X-FilmRec-Token: filmset
```

Endpoints:

- `GET /health`
- `GET /status`
- `POST /command`

Example command body:

```json
{"command":"record"}
```

Supported commands are `record`, `stop`, `play`, `next_take`, `circle`, `set_scene`, and `set_take`.

## Important on-set limitations of 0.1

This is an engineering prototype, not yet a replacement for a certified field recorder. Before using it for an irreplaceable take, we should add and test BWF/iXML, file-recovery behavior, device-disconnect recovery, long-duration recording, storage-space alarms, sample-drop detection, duplicate/backup recording, and automated stress tests.

The UMC404HD's hardware Direct Monitor path is still the best choice for latency-free headphone monitoring. Software monitoring is deliberately not enabled in this first prototype.

Closing a laptop lid can put the computer to sleep. The ESP32 remote can control the application while the display is off or the computer is otherwise awake, but it cannot keep recording after the operating system suspends the laptop. Configure the computer's power behavior appropriately and test it before a shoot.

## Next milestone

1. Embed proper BWF + iXML metadata.
2. Add pre-record buffer (5-10 seconds).
3. Add per-track arm/mute and ISO naming.
4. Add a mix track and safety-track options.
5. Add LTC timecode input/reader and frame-rate aware display.
6. Add dual-drive/background backup.
7. Add sound-report CSV/PDF export.
8. Package `.exe` and `.app` installers.

## ESP32 Cheap Yellow Display remote

The `esp32_controller` folder contains a first-pass Arduino sketch for the common **ESP32-2432S028R 2.8-inch CYD** (ILI9341 + XPT2046). CYD boards are sold in several revisions and sizes, so confirm the exact model printed on your PCB before relying on the included pin map.

Libraries used by the sketch:

- Arduino ESP32 core
- TFT_eSPI
- XPT2046_Touchscreen
- ArduinoJson

Before flashing:

1. Configure TFT_eSPI using the included `User_Setup_CYD.h` values, adjusted if your board revision differs.
2. Put your Wi-Fi SSID/password into `CYD_FilmSet_Remote.ino`.
3. Run FilmSet Recorder and copy the IP address displayed at the bottom of the desktop app into `RECORDER_IP`.
4. Keep the prototype token as `filmset` on both ends, or change it in both places.
5. Calibrate the touch panel; clone boards vary enough that the example raw min/max values may need adjustment.

The remote currently provides Record, Stop, Play Last, Next Take and Circle Take, while displaying roll, scene, take, elapsed recording time and an XRUN counter.

### Recommended controller direction

For the next revision, the CYD should gain a setup page so Wi-Fi, recorder IP and pairing token can be entered on the touchscreen instead of compiled into firmware. We can also add scene/take +/- controls, battery status, a physical REC button input, lock screen, haptic/buzzer feedback and automatic recorder discovery via mDNS.

## Windows installer build

This package now includes a Windows packaging setup. On a Windows 10/11 development machine with Python 3.12 and Inno Setup 6 installed, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

The finished installer is written to:

`release\FilmSetRecorder_Setup_0.1.0.exe`

See `BUILD_WINDOWS.md` for details. A GitHub Actions workflow is also included so the installer can be built on a Windows runner without maintaining a dedicated build PC.
