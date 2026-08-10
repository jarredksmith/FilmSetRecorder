# FilmSet Recorder 0.6.4

This maintenance release fixes two UI problems exposed by the packaged Windows build.

## Icons
- Desktop UI icons are now rendered as Qt vector-style graphics at runtime instead of depending on PNG resource lookup.
- The header brand mark and window icon use the same runtime-drawn identity, so PyInstaller folder layout cannot make them disappear.
- The Windows build also stages the full `assets` directory beside the executable.
- The installer ships a dedicated `FilmSetRecorder.ico` and explicitly assigns it to Start Menu and Desktop shortcuts.
- The Windows ICO has been regenerated using BMP icon frames for maximum shell compatibility.

## Track record-enable control
- `ARM` has been replaced by an explicit two-state control:
  - **REC** with a red record indicator: the input is record-enabled.
  - **OFF** in neutral gray: the input remains visible on the meter but its channel is silent in the recorded poly WAV.
- A tooltip explains the behavior.
- Track record-enable cannot be changed while a take is rolling.

## Audio device selector
- Input/output device selectors now draw their own visible disclosure chevron, independent of the OS theme.
- Both Record and System workspaces continue to expose synchronized input-device selectors.
