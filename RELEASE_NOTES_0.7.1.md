# FilmSet Recorder 0.7.1

## Take playback and front-panel routing

- Take waveforms are now interactive: click or drag anywhere on the waveform to scrub playback to that point.
- Clicking a waveform starts the selected take from that location if it is not already playing.
- The phone waveform can also scrub the phone-local take player.
- Every ISO row on the Record screen now has a compact physical-input selector directly beside the REC/OFF control.
- The front-panel source selector and System > Audio Setup routing matrix remain synchronized.
- Source selectors are locked during recording to prevent accidental mid-take rerouting.

## Recording file format

FilmSet Recorder continues to write one 24-bit polyphonic WAV per take. Each enabled microphone/ISO is stored as its own channel inside that WAV. This is intentional for production-sound/post workflows; separate mono-ISO file export can be added as an optional mode without changing the default poly-WAV workflow.
