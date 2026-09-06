# Changelog

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
