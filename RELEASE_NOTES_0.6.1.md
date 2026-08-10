# FilmSet Recorder 0.6.1 — Startup Hotfix

## Fixed

- Fixed a Windows/macOS startup crash in the v0.6 Field Console UI caused by `QFrame` being used without being imported from `PySide6.QtWidgets`.
- Added a static Qt-symbol import regression test so this class of UI startup failure is caught in GitHub Actions before installers are published.
- Retains the v0.6 automatic take-number advancement: after a take is successfully finalized and metadata is written, the slate advances to the next take number. Failed/partial recordings do not advance the slate.

## Build

- Windows installer: `FilmSetRecorder_Setup_0.6.1.exe`
- macOS Apple Silicon: `FilmSetRecorder_0.6.1_arm64.dmg`
- macOS Intel: `FilmSetRecorder_0.6.1_x86_64.dmg`
