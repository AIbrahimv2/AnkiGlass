#!/usr/bin/env python3
"""Make the screenshots for the README and the AnkiWeb listing.

    python3 tools/screenshots.py [--collection PATH] [--note ID] [--capture-wallpaper | --wallpaper PATH]

Writes docs/screenshot.png: the deck list on Liquid Glass beside a card
under review with the answer buttons in glass, as one image, unlabelled
since they speak for themselves. Each is Anki's main window with this
add-on's own CSS (src/__init__.py) and its glass drawn as the wallpaper
behind the window, blurred, under its tint.

The card is a real one from the AnKing Step Deck ("The large intestine is
characterized histologically by abundant goblet cells"), rendered by Anki
with AnKing's note type from a copy of your collection (--collection, the
Default profile's unless named). Its image is CC0 (Berkshire Community
College Bioscience Image Library, via Wikimedia Commons), and it was chosen
from the cards with openly licensed images for showing whole, credit and
all, in the window. AnKing notes keep their IDs, so --note finds it in
anyone's copy of the deck. Without a collection it falls back to a made-up
card. The decks are made up.

The window is a little taller than the kit's usual main window, so the
card's image and credit show whole, and both windows share that size.

They're made with the add-ons' shared screenshot tools, in the kit's
checkout next to this one (../anki-addon-kit/screenshots/shots.py, or set
ANKI_ADDON_KIT), which describe how they look and what they need.
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
KIT = os.environ.get("ANKI_ADDON_KIT", os.path.join(os.path.dirname(ROOT), "anki-addon-kit"))
sys.path.insert(0, os.path.join(KIT, "screenshots"))
import shots  # noqa: E402


NOTE = 1486608813182  # AnKing: "...abundant {{c1::goblet}} cells", a CC0 image
SIZE = (760, 690)  # the main window: taller than shots.MAIN_SIZE, so the card shows whole


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--collection", default=shots.DEFAULT_COLLECTION)
    ap.add_argument("--note", type=int, default=NOTE, help="the note whose first card is under review")
    shots.add_wallpaper_args(ap)
    args = ap.parse_args()
    glass = shots.load_glass(os.path.join(ROOT, "src"))
    with shots.Session() as s:
        if os.path.isfile(args.collection):
            card = shots.reviewer(glass, card=shots.export_card(args.collection, args.note, s.work), css="")
        else:
            print(f"no collection at {args.collection}: the review shows a made-up card")
            card = shots.reviewer(glass)
        deck = s.main_window("deck", shots.toolbar(glass), shots.deck_browser(glass),
                             shots.deck_browser_bar(glass), glass)
        review = s.main_window("review", shots.toolbar(glass), card, shots.reviewer_bar(glass), glass)
        size = SIZE
        s.capture([{"url": url, "width": size[0], "height": size[1], "setup": "window.shotReady",
                    "transparent": True, "wait": 1200, "out": f"{name}.png"}  # the card's image loads
                   for name, url in (("deck", deck), ("review", review))])
        out = s.side_by_side([
            {"image": "deck.png", "size": size, "title": "User 1 - Anki", "tint": glass["tint"]},
            {"image": "review.png", "size": size, "title": "User 1 - Anki", "tint": glass["tint"]},
        ], None, shots.wallpaper_for(args, s), os.path.join(DOCS, "screenshot.png"))
    print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
