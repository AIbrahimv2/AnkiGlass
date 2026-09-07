# AnkiWeb listing copy

**Title:** AnkiGlass

**Support page / more info URL:** https://github.com/AIbrahimv2/AnkiGlass

**Tags:** macos, appearance, theme, liquid-glass, ui

---

## Description

AnkiGlass gives Anki's main window Apple's **Liquid Glass** material on macOS —
a real AppKit `NSGlassEffectView` behind the deck list, deck overview, and
reviewer, with a frosted toolbar pill, frosted bottom-bar buttons, and a
theme-aware tint that reads consistently in light and dark mode.

Unlike a CSS-only "glass look", this uses the genuine system material, so it
refracts and blurs your desktop and other windows behind Anki.

**Requirements**

- macOS only. On Windows and Linux the add-on loads and does nothing.
- macOS 26 (Tahoe) for true Liquid Glass. Older macOS falls back automatically
  to a vibrancy (frosted) effect.

**Configurable** (Tools → Add-ons → AnkiGlass → Config): which screens get
glass, whether the card area itself is glass or stays opaque, and the tint
colour for light and dark mode. A runtime on/off toggle lives under
Tools → AnkiGlass.

**Notes**

- The glass renders in a separate window pinned behind a transparent main
  window, so mouse hover (for example AMBOSS pop-ups) keeps working normally.
- If you use a tiling window manager, it may try to manage the glass window;
  if the glass ever detaches on a move or resize, that is the window manager.
- A few heavily customised note types paint their own full-card background.
  AnkiGlass clears canvas-sized backgrounds automatically, but for unusual
  templates you can set "glass_card" to false to glass only the bars.

Source, issues, and updates: https://github.com/AIbrahimv2/AnkiGlass
