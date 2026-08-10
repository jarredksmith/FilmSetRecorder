# FilmSet Recorder 0.7.0

This release turns take review and input routing into first-class production workflows.

## Take review

- Added a waveform inspector to the **Takes** workspace.
- The waveform is generated from the recorded WAV without modifying the source file.
- Playback shows a moving playhead and current / total time.
- Waveform generation runs off the UI thread so long takes do not freeze the recorder window.
- Added editable notes for completed takes. Saving a note updates the take JSON metadata and rebuilds the sound report.
- The phone remote now shows the waveform with a moving playhead during **Listen on Phone** and **Play on Recorder**, and can edit/save notes on completed takes.
- Live phone metering and remote trim/routing are included; low-latency live audio monitoring through the browser is not part of this release. Recorded takes can still be auditioned directly on the phone.

## Input routing and digital trim

- Added **ISO Routing & Digital Trim** in System & Audio Setup.
- Each ISO track can choose a physical interface source.
- Two-channel interfaces are labeled **Input 1 · L** and **Input 2 · R**, making stereo Left/Right splitting explicit.
- Source routing can be reordered without changing the project slate or track name.
- Added per-track digital record trim from -24 dB to +24 dB.
- Record trim is post-preamp / post-A-D and cannot repair clipping that already occurred in the audio interface.
- Digital trim can be adjusted while recording; routing changes remain locked during a take.
- The phone remote exposes the same source routing and trim controls alongside live meters.
- Source and trim settings are saved with the application and written into take metadata / the sound report.

## Interface refinement

- Record, Takes, Notes, Remote and System navigation buttons now use identical dimensions and are centered in the left rail.
- ISO rows show a compact physical-input badge such as `IN 1 L` or `IN 2 R` without cluttering the primary meter surface.

## Validation

The automated suite covers recording masks, routing, digital trim, waveform envelope generation, authenticated waveform delivery, take-note UI hooks, and existing recorder / remote / recovery behavior.
