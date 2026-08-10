# FilmSet Recorder design system — v0.5

The interface is designed as a production instrument, not a dashboard.

## Principles

1. **Recording surface first.** Roll, scene, take, file name, meters, clock and transport remain visible while operating.
2. **Secondary controls stay secondary.** Audio setup, notes, take history, remote pairing and diagnostics live in the inspector.
3. **Low chrome.** Flat graphite surfaces, subtle one-pixel separators, restrained corner radii and no decorative gradients.
4. **Semantic color only.** Red means record/critical. Green means healthy. Amber means caution. Neutral blue-gray is selection/navigation.
5. **Instrument typography.** Metadata and labels use compact UI text; clocks, filenames, addresses and dB values use monospaced numerals.
6. **No ambiguous states.** Recording, playback, audio readiness and errors must be visually distinct without relying on animation.
7. **No hidden critical transport.** Record and Stop remain accessible at all supported window sizes.

## Desktop hierarchy

- Top bar: project, format, health.
- Slate strip: roll, scene, take, frame rate, next filename.
- Console: ISO tracks and dBFS meters.
- Inspector: Audio / Notes / Takes / Remote / System.
- Bottom transport: clock, state message, Record / Stop / Play / Next / Circle.

## Remote hierarchy

- Slate and timer.
- Live meters.
- Large transport.
- Take history and audition.
- Health summary.

## Visual tokens

- App background: `#090B0D`
- Surface: `#0D1014` / `#101318`
- Divider: `#242A31`
- Primary text: `#E7EAEE`
- Muted text: `#737D88`
- Record: `#A9262B`
- Healthy: `#48A779`
- Warning: `#C7923E`
- Selection: `#25313B`

## Interaction rules

- Configuration that could invalidate a take is locked while recording.
- Meter peak/clip memory must remain readable without excessive motion.
- Destructive or recovery actions require explicit confirmation.
- Technical counters belong in System; the main surface should communicate simple health states.
