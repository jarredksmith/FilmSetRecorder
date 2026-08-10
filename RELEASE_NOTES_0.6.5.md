# FilmSet Recorder 0.6.5

## Visual parity pass

This release moves the Record workspace substantially closer to the approved FilmSet Recorder mockup while preserving the existing recording engine and remote APIs.

### New Record workspace

- two-line FilmSet brand lockup with active-project title
- two-line status cards for audio, remote, disk, and recorder state
- larger production slate fields and dedicated next-file field
- production-style recorder clock using `HH:MM:SS:FF`
- recorder state badge and compact health cells
- circular transport controls with adjacent labels and shortcut badges
- persistent Last Take, Take History, and current Notes strip
- global footer for operator messages and project/device status

### ISO tracks

- calibrated -60 to 0 dBFS scale
- separate peak and RMS metering
- peak-hold marker and clip latch
- clearer per-track REC/OFF record-enable state
- track identity layout now matches the approved mockup more closely

### Add Input

When the selected hardware interface exposes more inputs than are currently shown, an **ADD INPUT** button appears directly below the ISO tracks. Adding an input expands the track layout and, if audio is already ready, safely reconfigures monitoring to the new channel count.

Example: a two-input interface with one active track shows `ADD INPUT 2 OF 2`; a UMC404HD can grow from one through four tracks.

### Reliability

- existing auto-advance take behavior remains intact
- recording controls are locked while a take is rolling
- input-count changes remain bounded by the hardware-reported channel count
- RMS calculation is performed in the existing audio callback and does not add disk I/O to the callback

