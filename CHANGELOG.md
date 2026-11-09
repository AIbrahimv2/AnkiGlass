# Changelog

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
