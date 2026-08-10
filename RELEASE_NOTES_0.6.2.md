# FilmSet Recorder 0.6.2

## Brand icon repair

- Rebuilt the Windows, macOS-source, desktop-window, and web-remote product mark from one high-contrast waveform design.
- Fixed the 0.6.x PNG/ICO assets that could render as a nearly solid black tile because the waveform layer was absent from the raster export.
- The desktop header now renders the actual product mark instead of a text placeholder.
- Added automated asset checks so a missing/dark waveform cannot silently ship again.
- Retains the 0.6.1 startup fix and automatic take advancement behavior.
