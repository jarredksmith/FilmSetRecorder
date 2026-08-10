# FilmSet Recorder 0.2.0

FilmSet Recorder is a cross-platform multitrack production-dialogue recorder built for film sets. The desktop application is written in Python/PySide6 and is designed around a field-recorder workflow rather than a general-purpose DAW.

> **Engineering build:** 0.2.0 is intended for development and hardware validation. Do not use it as the only recorder for irreplaceable production audio until the stress-test checklist has been completed on the exact computer, interface, storage device, and sample-rate configuration you will use on set.

## What is new in 0.2

- Completely redesigned modern dark GUI
- Large production slate and transport controls
- Up to 16 visible ISO track strips with editable names and record-arm state
- Purpose-built peak meters with peak hold and clipping indication
- 24-bit polyphonic WAV recording
- 48 kHz and 96 kHz operation
- Configurable 256 / 512 / 1024 frame input buffers
- 0-10 second pre-roll buffer
- Dedicated disk-writer thread so the PortAudio callback never writes to disk
- Bounded write queue with dropped-block accounting
- XRUN counter and recorder-health display
- Crash-resilient `.partial.wav` recording with periodic WAV-header refresh followed by atomic final rename
- Startup recovery of interrupted partial recordings
- No-overwrite file allocation; duplicate slate/take combinations receive a safe suffix
- Persistent project, audio, slate, track-name, window, and remote settings
- Automatic JSON take metadata
- Automatic CSV sound report generation
- Streaming playback of the last take as a dialog mix instead of loading the whole file into RAM
- Disk-space and estimated remaining-record-time display
- Low-disk recording interlock below 512 MB plus automatic safety stop below 256 MB
- Automatic safety stop if the disk-writer queue reaches a critical backlog before silent data loss
- Keep-awake mode for Windows and macOS idle sleep
- Local Wi-Fi ESP32 remote-control server
- Per-install six-digit remote pairing PIN
- Remote status now includes track names, arm states, meters, XRUNs, and dropped blocks
- Rotating application logs
- Saveable audio/system diagnostics report
- Automated unit tests in GitHub Actions
- Windows installer workflow and macOS DMG workflow

## Desktop workflow

1. Connect and power the audio interface before launching FilmSet Recorder.
2. Choose the film project folder.
3. Select the input and output device.
4. Choose 48 kHz or 96 kHz, input channel count, buffer size, and pre-roll.
5. Click **Apply / Start Audio**.
6. Verify meters on every required input.
7. Name and arm the ISO tracks.
8. Enter roll, scene, take, and frame-rate metadata.
9. Record. FilmSet Recorder writes to a recoverable `.partial.wav` while the take is active.
10. Stop. A clean take is atomically renamed to its final `.wav`, its `.json` metadata is written, and `sound_report.csv` is rebuilt.
11. Use **PLAY LAST**, **CIRCLE**, and **NEXT TAKE** as needed.

## File layout

Example:

```text
My Movie/
|-- .filmset/
|-- sound_report.csv
|-- A001/
|   |-- A001_24B_T001.wav
|   |-- A001_24B_T001.json
|   |-- A001_24B_T002.wav
|   `-- A001_24B_T002.json
`-- A002/
```

During recording you may temporarily see:

```text
A001_24B_T003.partial.wav
```

That file is deliberate. It is renamed only after a clean stop. If the application or computer is interrupted, FilmSet Recorder detects the partial recording the next time the project opens and offers to recover it.

## UMC404HD notes

The Behringer UMC404HD is a primary development target for this project. On Windows, install the current Behringer driver first. FilmSet Recorder displays whichever PortAudio host APIs and channel arrangements are actually available on the machine. Do not assume ASIO is present merely because the Behringer driver is installed; use **Save Diagnostics** to see exactly what the packaged PortAudio build exposes.

For headphones during recording, use the UMC404HD hardware **Direct Monitor** path. Software input monitoring is intentionally disabled in 0.2 because dependable zero/low-latency monitoring requires more platform-specific validation.

## Windows installer with GitHub Actions

The repository includes:

```text
.github/workflows/build-windows.yml
```

Open **Actions -> Build Windows Installer -> Run workflow**. After the workflow succeeds, download the artifact:

```text
FilmSetRecorder-Windows-Installer-v0.2.0
```

Inside it is:

```text
FilmSetRecorder_Setup_0.2.0.exe
```

The target recording PC does not need Python installed. It still needs the appropriate audio-interface driver.

## macOS DMG with GitHub Actions

The repository also includes:

```text
.github/workflows/build-macos.yml
```

Run **Build macOS App** and download the `FilmSetRecorder-macOS-v0.2.0` artifact. The generated app is not Apple-notarized or Developer-ID signed yet, so Gatekeeper warnings are expected on development builds.

## ESP32 Cheap Yellow Display remote

The desktop application starts a small HTTP controller service on port `8765`. The SYSTEM card shows both the recorder IP address and a six-digit PIN.

Edit these values in:

```text
esp32_controller/CYD_FilmSet_Remote.ino
```

```cpp
const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* RECORDER_IP = "192.168.1.100";
const uint16_t RECORDER_PORT = 8765;
const char* RECORDER_TOKEN = "000000";
```

Replace `RECORDER_TOKEN` with the six-digit PIN displayed by FilmSet Recorder.

Current remote controls:

- Record
- Stop
- Play last take
- Next take
- Circle take
- Set scene through the API
- Set take through the API

Current remote status includes recording state, elapsed time, roll, scene, take, circle state, XRUNs, dropped blocks, track names, arm states, and meter values.

## Keyboard shortcuts

- `F9` - record / stop current take
- `Esc` - stop recording or playback
- `F8` - play last take
- `Ctrl+N` - next take
- `Ctrl+Shift+C` - toggle circle

## Current metadata behavior

Version 0.2 stores production metadata in a JSON sidecar and a project-level CSV sound report. Proper embedded Broadcast Wave (BWF `bext`) and iXML metadata are planned for a later milestone after the core recording path is validated.

## Reliability design

The recorder has several deliberate safety choices:

- Audio callback does not write to disk.
- Disk writes happen on a dedicated thread.
- The writer queue is bounded instead of growing without limit.
- Queue overruns are counted as dropped blocks.
- PortAudio status events increment the XRUN counter.
- Active takes are written to a partial file and the WAV header is refreshed periodically so interrupted files remain readable near the last sync point.
- Clean completion uses an atomic filesystem rename.
- Existing take files are never overwritten automatically.
- Take metadata is written atomically through a temporary JSON file.
- Sound reports are rebuilt atomically.
- Low disk space can block recording.
- Interrupted partial WAV files can be recovered at next project open.
- Application logs rotate instead of growing indefinitely.

## Sleep / lid behavior

**Keep computer awake** prevents normal idle system sleep on supported Windows and macOS systems without intentionally forcing the display to remain on. It cannot override every hardware lid-close rule. In particular, a Mac can still sleep when the lid closes unless it is in a supported clamshell configuration. Test the exact laptop behavior before relying on a closed-lid workflow.

## What is intentionally not in 0.2 yet

- BWF `bext` metadata
- iXML metadata
- LTC decoding / timecode jam
- true time-of-day BWF time reference
- software headphone monitoring and monitor routing
- mix track in addition to ISO tracks
- safety-track channel generation
- waveform editor
- destructive editing
- plug-ins / effects
- cloud synchronization
- code signing / notarization

See `ROADMAP.md` for the planned progression.
