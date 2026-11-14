# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""AnkiGlass's settings, as the shared add-on kit's page shows them (Tools →
Add-ons → AnkiGlass → Config). The values are the keys of config.json; see
config.md for what each does. schema() adds the buttons that turn it off or
back on, and show the log. Plain Python, so the kit's preview can read it.
"""

NOTE = "Changes apply after Anki restarts."

SCHEMA = [
    {
        "section": "Where",
        "fields": [
            {
                "key": "glass_screens",
                "type": "multi",
                "label": "Glass on these screens",
                "hint": "The others keep Anki's normal background.",
                "options": [
                    {"value": "deckBrowser", "label": "Deck list"},
                    {"value": "overview", "label": "Deck overview"},
                    {"value": "review", "label": "Review"},
                ],
            },
            {
                "key": "glass_card",
                "type": "switch",
                "label": "Glass behind the card",
                "hint": "Off keeps the card solid and puts glass only on the bars above and below it.",
            },
        ],
    },
    {
        "section": "Tint",
        "fields": [
            {
                "key": "tint_dark",
                "type": "text",
                "mono": True,
                "label": "In dark mode",
                "hint": "Painted over the glass, as any CSS colour. A higher alpha gives text more contrast; \"transparent\" shows the raw glass.",
                "placeholder": "rgba(0,0,0,0.38)",
            },
            {
                "key": "tint_light",
                "type": "text",
                "mono": True,
                "label": "In light mode",
                "hint": "The same, for light mode.",
                "placeholder": "rgba(255,255,255,0.35)",
            },
        ],
    },
    {
        "section": "Troubleshooting",
        "fields": [
            {
                "key": "debug_log",
                "type": "switch",
                "label": "Keep a log",
                "hint": "Writes what AnkiGlass does to user_files/anki_glass.log. After a restart, a button here shows it.",
            },
        ],
    },
]


def schema(on_now: bool, kept_off: bool, logging: bool) -> list:
    """SCHEMA with the rows that turn AnkiGlass off or back on (the buttons
    run __init__.py's turn_off_now, keep_off and turn_back_on), and, while it
    keeps a log, one that shows it."""
    if kept_off:
        rows = [{
            "key": "turn_back_on", "type": "action", "label": "Turned off",
            "hint": "AnkiGlass stays off, every time Anki starts, until you turn it back on.",
            "button": "Turn back on",
        }]
    else:
        now = {"key": "off_now", "type": "action", "label": "For now"}
        if on_now:
            now.update(hint="Anki gets its normal window back until you restart it.", button="Turn off")
        else:
            now.update(hint="Off until you restart Anki.")
        rows = [now, {
            "key": "keep_off", "type": "action", "label": "Until you turn it back on",
            "hint": "Off now and every time Anki starts, until you come back here.",
            "button": "Turn off",
        }]
    sections = [dict(s, fields=list(s["fields"])) for s in SCHEMA]
    sections.insert(len(sections) - 1, {"section": "Turn off", "fields": rows})  # before Troubleshooting
    if logging:
        sections[-1]["fields"].append({
            "key": "show_log", "type": "action", "label": "The log",
            "hint": "What AnkiGlass has done since Anki started.", "button": "Show log",
        })
    return sections


# What the kit's preview (anki-addon-kit/tools/preview.py) starts from.
PREVIEW_CONFIG = {
    "glass_screens": ["deckBrowser", "overview", "review"],
    "glass_card": True,
    "tint_dark": "rgba(0,0,0,0.38)",
    "tint_light": "rgba(255,255,255,0.35)",
    "debug_log": False,
}
