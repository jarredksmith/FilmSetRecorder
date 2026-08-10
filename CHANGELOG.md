# Changelog

## 0.7.0

- Added centered, uniform left-rail navigation buttons.
- Added visual waveform review with playback playhead in the desktop Takes workspace.
- Added post-recording note editing with JSON metadata and sound-report updates.
- Added phone waveform display and completed-take note editing.
- Added explicit per-ISO physical input routing, including stereo L/R labeling.
- Added live post-A/D digital record trim (-24 dB to +24 dB) and phone remote trim control.
- Saved track source and trim metadata with each take.
- Added routing/trim, waveform, and remote API regression tests.


## 0.6.6

- Closed another round of visual parity gaps against the approved mockup.
- Hidden the always-visible desktop menu bar; commands remain available from the header gear menu.
- Removed duplicate waveform branding from the content header.
- Added restrained blue Audio Ready state styling and neutral Ready recorder status.
- Increased navigation and circular transport proportions.
- Fixed the primary Record transport glyph to render as a high-contrast white center dot.
- Added safe meter-scale insets so -60 dBFS is not clipped.
- Added an Add Note affordance in the production strip.

## 0.6.5
- Replaced file-dependent desktop UI icons with runtime-rendered vector-style Qt icons.
- Fixed packaged builds where sidebar/transport/status icons disappeared.
- Made the application window icon independent of packaged PNG lookup.
- Added explicit Windows shortcut icon staging and shell refresh hint.
- Regenerated Windows ICO with BMP frames for shell compatibility.
- Replaced ambiguous ARM styling with clear red REC / gray OFF states.
- Added explanatory record-enable tooltip.
- Added always-visible device-selector chevrons.

## 0.6.3

- Added a packaged 27-icon FilmSet UI icon set used throughout desktop navigation, section headers, status cards, transport, take tools, remote controls, and system actions.
- Replaced text/glyph navigation placeholders with real graphical icons.
- Added an explicit Input Device selector to the System & Audio Setup workspace in addition to the Record workspace selector.
- Synchronized both input-device selectors and made UMC404HD auto-selection visible in either workspace.
- Added Start / Apply Audio to the System workspace so audio routing can be configured even on compact window layouts.
- Updated Windows packaging to include the full UI icon asset directory.


## 0.6.2
- Rebuilt app icon assets with a visible electric-blue waveform at small sizes.
- Unified Windows, macOS, desktop-window, and web-remote product graphics.
- Added icon regression tests.
- Desktop header now uses the real product mark.


## 0.6.1

- Fixed v0.6 startup crash (`QFrame` missing from the QtWidgets import list).
- Added a static UI import regression test.
- Automatic post-finalization take advancement remains enabled.

## 0.6.0

- Rebuilt the desktop interface as a restrained production-sound console.
- Kept slate, meters, clock and transport visible as the primary operating surface.
- Moved setup, notes, takes, remote and technical diagnostics into a compact inspector.
- Added a dBFS reference scale and refined track-strip presentation.
- Replaced dashboard-style cards/pills with flatter instrument-like surfaces and status indicators.
- Restyled the phone/tablet remote to the same professional design language.
- Preserved take playlist, phone audition, QR pairing, recovery and cross-platform packaging.

## 0.6.0

- Added first-class macOS packaging for both Apple Silicon (`arm64`) and Intel (`x86_64`) Macs.
- Added macOS microphone and local-network privacy descriptions to the application bundle.
- Added ad-hoc code signing and DMG packaging with an Applications shortcut.
- Added `MAC_INSTALL.md` with build, first-launch, permission, and architecture instructions.
- macOS and Windows continue to use the same project/session and web-remote format.

## 0.6.0
- Added desktop take playlist/browser with selected-take playback.
- Added authenticated `/api/takes` endpoint for remote take browsing.
- Added authenticated browser-audio endpoint that streams a stereo PCM16 downmix of a selected multichannel production WAV.
- Added phone/tablet take playlist with separate **Play on Recorder** and **Listen on This Phone** actions.
- Added secure project-relative take resolution to prevent path traversal.
- Added tests for playlist discovery, take resolution, and browser audio streaming.
- Circle control now explains its preferred/print-take purpose.


## 0.6.0
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

## 0.6.0
- Redesigned desktop layout for 1366x768 and other laptop-sized displays.
- Audio, Notes, Remote, and System panels now live in scrollable tabs instead of a tall fixed sidebar.
- Transport controls remain visible at the bottom of the window.
- Main workspace automatically stacks vertically on narrow windows.
- Reduced minimum window size from 1080x700 to 820x620.
- More compact track rows and spacing without reducing meter functionality.
