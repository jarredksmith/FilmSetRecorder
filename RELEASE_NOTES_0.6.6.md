# FilmSet Recorder 0.6.6

This release is a mockup-parity refinement pass.

## Visual changes

- Hidden traditional menu chrome; the header gear now exposes project, audio, diagnostics, report, About, and Exit actions.
- Removed duplicate header waveform branding so the hierarchy matches the reference more closely.
- Enlarged the navigation rail and transport controls.
- Record transport now uses the reference-style white center dot.
- Audio Ready uses a restrained blue instrument state instead of a full green success card.
- Ready recorder state stays visually neutral; recording still becomes unmistakably red.
- Meter endpoints are inset so the -60 dBFS label is never clipped.
- Added an Add Note control to the persistent production strip.

## Existing production behavior retained

- Dynamic Add Input control based on available hardware channels.
- REC/OFF per-track record-enable state.
- Automatic take-number advance after successful finalization.
- QR web remote, take browser, crash recovery, peak/RMS metering, and Windows/macOS build workflows.
