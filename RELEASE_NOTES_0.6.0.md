# FilmSet Recorder 0.6.0 — Field Console Redesign

This release replaces the settings-dashboard layout with a branded, production-focused recorder interface based on the visual references developed for the project.

## Visual redesign

- New FilmSet waveform identity and blue-black product palette.
- Dedicated left navigation rail for Record, Takes, Notes, Remote and System.
- Record workspace prioritizes slate, ISO meters, recorder state and transport.
- Large recorder clock and quick audio-status panel.
- Segmented professional-style level meters with peak hold and functional signal colors.
- Dedicated full-size Takes workspace instead of a small inspector tab.
- Dedicated Notes, Remote and System workspaces.
- Cleaner transport deck with stronger visual hierarchy.
- Matching logo assets for Windows, macOS and the web remote.

## Workflow fix

- Successfully finalized recordings now automatically advance the take number.
- Auto-advance happens only after the WAV and metadata are safely finalized; failed or partial recordings do not skip the slate number.
- Current-take notes clear after a successful take so they are not accidentally carried into the next recording.
- Manual Next Take remains available.

## Build / packaging

- Windows installer and portable artifacts updated to 0.6.0.
- macOS Apple Silicon and Intel DMG artifacts updated to 0.6.0.
- macOS workflow generates the ICNS icon from the shared high-resolution product mark.
