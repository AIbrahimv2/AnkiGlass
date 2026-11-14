# Changelog

## Unreleased

### Added
- **Settings in a window of their own**, instead of Anki's raw config text:
  which screens get glass, glass behind the card, the tints and the log. Open
  it from the Config button in Tools → Add-ons.
- Turning it off is in Settings too, for now or until you turn it back on
  there (which you can now do without deleting a file).
- The same window has What's new (this list of changes) and About (links,
  whether AnkiWeb has an update, and AIbrahimv2's other Anki add-ons, with an
  Install button).
- When any of AIbrahimv2's add-ons is updated, a card at the bottom of Anki's
  main window says so once, with a link to what's new.

### Changed
- AnkiGlass no longer adds anything to the Tools menu: its settings, turning
  it off and the log are all in Settings.

### Fixed
- Turned off for the session, the glass stays off on every screen, instead
  of its styling coming back on the next screen.

## 1.1.0 - 2026-11-09

### Changed
- The deck list's card is the same glass as the toolbar, instead of Anki's own
  darker fill, and its header line and the hovered or selected row match it.

### Fixed
- Full screen no longer blurs the whole window. In full screen macOS put the
  glass in front of Anki instead of behind it, so AnkiGlass now gives Anki its
  normal solid window there, and brings the glass back once you leave full
  screen.

## 1.0.0
- Initial release.
- Native macOS Liquid Glass (`NSGlassEffectView`, macOS 26 Tahoe) behind Anki's
  deck list, deck overview, and reviewer, with a vibrancy fallback on older
  macOS.
- Frosted toolbar pill and bottom-bar buttons; theme-aware tint shared across
  the toolbar, card, and bottom bar.
- Glass runs in a separate child window behind a transparent main window, so
  mouse hover (e.g. AMBOSS pop-ups) keeps working.
- Configurable screens, card glass, and tint; runtime toggle under Tools.
