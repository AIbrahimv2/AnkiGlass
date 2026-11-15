# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 AIbrahimv2
"""AnkiGlass's settings, as the shared add-on kit's page shows them (Tools →
Add-ons → AnkiGlass → Config). The values are the keys of config.json; see
config.md for what each does. schema() adds the button that shows the log,
while there is one. Plain Python, so the kit's preview can read it.
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


def schema(logging: bool) -> list:
    """SCHEMA, with a button that shows the log while AnkiGlass keeps one
    (it runs __init__.py's show_log)."""
    sections = [dict(s, fields=list(s["fields"])) for s in SCHEMA]
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
