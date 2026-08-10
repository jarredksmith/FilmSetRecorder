# Changelog

## 0.3.2
- Fixed packaged Web Remote returning `{"error":"not found"}` at the recorder URL.
- Web Remote assets are now compiled into the application as a fallback while still using external web files during development.
- Added an automated regression test that starts the remote server with no web directory and verifies the UI and JavaScript are still served.

## 0.3.0

- Added a responsive phone/tablet web remote served directly by FilmSet Recorder.
- Added one-scan QR pairing from the desktop GUI, with manual six-digit PIN fallback.
- Added browser session cookies so paired devices do not need the PIN on every refresh.
- Added live mobile meters, recording clock, roll/scene/take slate, transport, circle, scene/take editing, disk status, XRUNs, and drop counters.
- Preserved backward compatibility with the ESP32 `/status` and `/command` API.
- Added web-asset packaging to Windows/macOS builds.
- Added automated tests for static web serving and browser pairing.
- Changed Windows installer artifact upload to a wildcard path so version filename changes do not silently lose the artifact.

## 0.2.0

- New modern PySide6 user interface
- Custom production-audio meters and track strips
- Crash-safe partial WAV workflow and recovery
- Configurable pre-roll
- Track arm state
- Disk-space safety checks
- Streaming playback
- Persistent settings
- Automatic sound report CSV
- Rotating logs and exportable diagnostics
- Sleep inhibition option
- Six-digit ESP32 remote PIN and richer remote status
- Automated tests
- Updated Windows installer builder
- Added macOS DMG workflow

## 0.1.0

- Initial multichannel recorder prototype
- Device selection
- Polyphonic 24-bit WAV recording
- Basic meters and slate metadata
- Basic HTTP ESP32 remote

## 0.3.2
- Redesigned desktop layout for 1366x768 and other laptop-sized displays.
- Audio, Notes, Remote, and System panels now live in scrollable tabs instead of a tall fixed sidebar.
- Transport controls remain visible at the bottom of the window.
- Main workspace automatically stacks vertically on narrow windows.
- Reduced minimum window size from 1080x700 to 820x620.
- More compact track rows and spacing without reducing meter functionality.
