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
