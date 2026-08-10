# FilmSet Recorder 0.6.3 — Icon & Audio Routing Pass

This release closes two gaps in the 0.6 visual redesign.

## UI iconography
- Real graphical icons now appear in the left navigation rail.
- Record/Stop/Play/Next/Circle use dedicated transport icons.
- Slate, ISO tracks, recorder, Takes, Notes, Remote and System headings now carry matching icons.
- Top audio/remote/disk/state indicators now include icons.
- Remote, take-browser and system action buttons use consistent FilmSet line icons.

## Input-device selection
- The Record workspace retains its prominent Input Device selector.
- System & Audio Setup now contains a second synchronized Input Device selector next to Output Device.
- Selecting an interface in either place updates the other selector immediately.
- Refresh Devices populates both selectors from the same hardware inventory.
- Start / Apply Audio is available in both workspaces.

## Packaging
The Windows PyInstaller spec now bundles `assets/icons/`, and macOS already bundles the complete assets directory.
