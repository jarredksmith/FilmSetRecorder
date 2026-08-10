# FilmSet Recorder Design System — v0.6

## Product character

FilmSet Recorder should read as an instrument first and an application second: calm, legible, technically credible and visually quiet while recording.

## Identity

The product mark is a compact vertical waveform in electric blue on a deep blue-black field. It is used for the application icon, navigation identity, Windows installer, macOS bundle and web remote.

## Palette

- Canvas: `#06101A`
- Raised surface: `#0C1B2A`
- Hairline / structure: `#1B344B`
- Primary text: `#F5FAFF`
- Secondary text: `#7F91A5`
- Interaction blue: `#1E91FF`
- Record red: `#E62232`
- Healthy green: `#73E6A7`
- Meter cyan/green/yellow/red: functional signal-state colors only

## Layout rules

1. Record view always prioritizes slate, meters, clock and transport.
2. Administrative functions live in dedicated workspaces, not permanent dashboard cards.
3. The left rail is navigation, not decoration.
4. Use large empty areas deliberately; do not fill space with status cards.
5. Recording status must be obvious without flashing or animation.

## Typography

- UI: Inter / SF Pro Text / Segoe UI fallbacks.
- Time, filenames and diagnostics: SF Mono / Cascadia Mono / Consolas.
- Uppercase section labels are compact and tracked; values are larger and more immediate.

## Controls

- Record is the only strong red control.
- Blue is reserved for selection, navigation and primary configuration actions.
- Buttons use short verbs and stable positions.
- Track arm state uses green because it communicates readiness, not branding.

## Metering

Meters are segmented and calibrated from -60 to 0 dBFS with peak hold and clip latch. Signal colors move from cyan/green to yellow and red only as level approaches clipping.

## Iconography (0.6.3+)

FilmSet uses a dedicated product icon set in `assets/icons/`. Icons are functional, not decorative: navigation, transport, recorder health, audio routing, file actions, remote pairing and diagnostics all use the same restrained line language. Avoid replacing these with emoji, Unicode glyphs, or platform-dependent symbol fonts.

The icon set is rasterized with transparency so it packages consistently on both Windows and macOS through PyInstaller.

## v0.6.5 mockup-parity rules

The approved `assets/DESIGN_REFERENCE_v0_6.png` is the visual reference for the Record workspace. New UI work should preserve these priorities:

- circular transport controls, never five equal rectangular dashboard buttons
- slate values are visually dominant, not generic small form fields
- ISO tracks read as audio instrumentation with calibrated dBFS scale, peak hold, and RMS context
- recorder clock is `HH:MM:SS:FF` and visually anchors the right-side recorder module
- status cards use a concise title plus one secondary detail line
- the Record workspace always exposes last take, recent history, and current notes without opening another page
- hardware channel capacity is discoverable through an inline Add Input control when unused inputs exist
- settings remain secondary to recording state and metering


## v0.6.6 parity refinements

- The Record workspace hides the traditional menu bar and moves application commands into the header gear menu, matching the approved console reference.
- The header uses a single brand mark in the navigation rail; the content header carries only the FILMSET / RECORDER wordmark and project identity.
- Audio-ready status uses the restrained blue instrumentation treatment; green is reserved for live remote connectivity and other explicit healthy states.
- The primary Record transport uses a white center-dot glyph on the red transport button.
- Meter scale labels include safe horizontal inset so the -60 and 0 dBFS endpoints remain legible.
- The production strip includes an Add Note affordance beside the current-take notes field.
