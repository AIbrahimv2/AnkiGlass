# Changelog

## Unreleased

### Changed
- About lists Skim with an Install button, now that it's on AnkiWeb.
- **Settings, What's new and About are one surface** from top to bottom: the
  header, the tabs and the Save and Close bar no longer sit on bands of their
  own. Only what's between them scrolls, and it fades out at its edges.

### Fixed
- **Again, Hard, Good and Easy are glass too**, like the other buttons in
  review, instead of Anki's solid grey. Buttons another add-on colours keep
  their colours.

## 1.4.0 - 2026-11-17

### Added
- **⌘S saves Settings** (Ctrl+S on Windows and Linux).

### Fixed
- Save and Close in Settings sit in a bar across the bottom of the window,
  like the tabs across its top, instead of a narrower panel partway down it.

## 1.3.0 - 2026-11-17

### Added
- **Tools → AnkiGlass Options...** opens Settings, so you no longer have to
  find it under Tools → Add-ons → Config.
- **Glass on your other add-ons' windows.** Stepwise's, Skim's and Exam
  Timeline's windows, and this Settings, What's new and About window, get
  the same glass as Anki's main window, with the same tint. Headers turn
  solid while a list scrolls under them, so it doesn't show through. Skim's
  card is glass too, as in review, while **Glass behind the card** is on. **Glass on add-on
  windows** in Settings turns it all off.

### Changed
- **A wider Settings, What's new and About window**, with its tabs along the
  top: each version's changes sit beside its number, and the other add-ons
  are laid out as cards.
- **The signature at the end of About signs itself**, stroke by stroke, as
  if written by hand when you scroll to it.
- Add-on emoji stand on their own now, without a box around them.
- About ends with links to AIbrahimv2's LinkedIn and Instagram, under the
  signature, and the signature opens AIbrahimv2's website.
- **A colour picker for the tints** in Settings, with an opacity slider,
  instead of typing rgba() by hand. You can still type any colour.
- **⌘, opens Settings** on a Mac while AnkiGlass's window (Settings, What's
  new or About) is in front, instead of Anki's Preferences. Anywhere else
  it still opens Anki's.

## 1.2.0 - 2026-11-17

### Added
- **Settings in a window of their own**, instead of Anki's raw config text:
  which screens get glass, glass behind the card, the tints and the log. Open
  it from the Config button in Tools → Add-ons.
- The same window has What's new (this list of changes) and About (links,
  whether AnkiWeb has an update, and AIbrahimv2's other Anki add-ons, with an
  Install button).
- When any of AIbrahimv2's add-ons is updated, a card at the bottom of Anki's
  main window says so once, with a link to what's new.

### Changed
- AnkiGlass no longer adds anything to the Tools menu. Its settings and the
  log are in Settings, and the two items that turned it off are gone: to
  switch it off, turn it off in Tools → Add-ons, like any add-on. If you used
  "disable until re-enabled", the glass comes back with this version.

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
