<img width="1800" height="1169" alt="Screenshot 2026-09-06 at 10 06 39" src="https://github.com/user-attachments/assets/79d091a3-07e7-493b-b6ef-8847524203f0" />
# AnkiGlass

Native macOS **Liquid Glass** for [Anki](https://apps.ankiweb.net/). AnkiGlass
gives Anki's main window a real AppKit `NSGlassEffectView` — the macOS 26
"Tahoe" glass material — behind the deck list, deck overview, and reviewer,
with frosted toolbar and bottom-bar controls and a theme-aware tint.

> macOS only. Best on macOS 26 (Tahoe) for true Liquid Glass; older macOS gets
> a vibrancy (frosted) fallback. On Windows and Linux the add-on does nothing.

## Screenshots

<img width="1800" height="1169" alt="Screenshot 2026-09-06 at 10 04 10" src="https://github.com/user-attachments/assets/678ff45c-b262-49bd-a36d-943fbe8a74e9" />
<img width="1800" height="1169" alt="Screenshot 2026-09-06 at 10 07 04" src="https://github.com/user-attachments/assets/69c2b21c-4a2a-456e-b90c-b475f38c6885" />
<img width="1800" height="1169" alt="Screenshot 2026-09-06 at 10 06 39" src="https://github.com/user-attachments/assets/c82c5078-d561-4fa1-bf7e-1bb67de85388" />


## Install

- **From AnkiWeb:** search for “AnkiGlass” in Tools → Add-ons → Get Add-ons.
- **From a build:** run `./build.sh` and double-click `dist/anki-glass.ankiaddon`,
  or in Anki use Tools → Add-ons → Install from file.

Restart Anki after installing.

## Configuration

Tools → Add-ons → AnkiGlass → Config. See [`src/config.md`](src/config.md) for
each option. In short: choose which screens get glass, whether the card area
itself is glass, and the tint colour for light and dark mode. A runtime toggle
lives under Tools → AnkiGlass.

## How it works

Anki's UI is Qt/Chromium web views, not native AppKit controls, so AnkiGlass
does not replace the widget engine. Instead it:

1. Makes the main `NSWindow` transparent and requests an alpha surface format so
   Chromium clears its transparent regions cleanly (no ghosting).
2. Hosts a real `NSGlassEffectView` in a **borderless child window pinned behind**
   the main window. The main window is never re-parented, so Qt keeps ownership
   of its own view and mouse hover (e.g. AMBOSS pop-ups) keeps working.
3. Injects small, scoped CSS into Anki's toolbar, bottom bar, and card pages to
   make their backgrounds transparent and style the controls as frosted glass.

It talks to the Objective-C runtime through `ctypes` (see `objc_bridge.py`) —
the same technique Anki itself uses for its bundled macOS helper — because Anki
does not ship PyObjC.

## Caveats

- macOS 26 (Tahoe) is required for genuine Liquid Glass; earlier macOS shows a
  vibrancy fallback.
- Tiling window managers may try to manage the child glass window; if the glass
  detaches on move/resize, that is the window manager, not Anki.
- Some heavily customised note types paint their own full-card background;
  AnkiGlass neutralises canvas-sized backgrounds automatically, but very unusual
  templates may need `glass_card` set to `false`.

## Development

- Source lives in `src/`. Symlink or copy it into your Anki add-ons folder as
  `anki_glass` to test, then restart Anki.
- `./build.sh` packages `src/` into `dist/anki-glass.ankiaddon`.

## License

[AGPL-3.0](LICENSE).
