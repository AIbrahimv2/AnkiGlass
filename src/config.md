# AnkiGlass configuration

Changes apply on the next Anki restart.

- **glass_screens** — which main-window screens get the glass effect. Any of
  `"deckBrowser"` (deck list), `"overview"` (a deck's overview), `"review"`
  (the reviewer). Remove one to leave that screen stock.
- **glass_card** — `true` makes the card area itself glass; `false` keeps the
  card opaque and glasses only the top and bottom bars.
- **tint_dark** / **tint_light** — the tint painted over the glass in dark and
  light mode, as any CSS colour. Raise the alpha (e.g. `rgba(0,0,0,0.4)`) for
  more contrast behind text; use `"transparent"` for raw, untinted glass.
- **debug_log** — `true` writes a log to `user_files/anki_glass.log` and adds a
  "show log" item under Tools → AnkiGlass. Leave `false` for normal use.

macOS only. On macOS 26 (Tahoe) you get real Liquid Glass; older macOS falls
back to a vibrancy (frosted) effect. On Windows/Linux the add-on does nothing.
