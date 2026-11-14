# Notes for agents

AnkiGlass is one of AIbrahimv2's Anki add-ons (AnkiWeb ID 1866406123).

To release it, publish it, or edit its AnkiWeb listing, follow the
`anki-addon-release` skill. It covers all of the user's add-ons: the
changelog, building and checking the package, the GitHub release, AnkiWeb, the
listing and AnkiWeb search.

- **On the user's Mac** it loads by itself, from
  `~/.claude/skills/anki-addon-release`.
- **Anywhere else**, such as a cloud session, read it first:
  https://github.com/AIbrahimv2/AnkiStepwise/tree/main/.claude/skills/anki-addon-release
  (`SKILL.md`, and `scripts/` for the package and search checks).

This repo: `./build.sh` builds `dist/anki-glass.ankiaddon` from `src/`. The
listing text is in `docs/ankiweb-listing.md`.

Its Settings are the shared kit's window, described by `src/settings_schema.py`
(keep it in step with `config.json`). `src/kit/` is a copy of `../anki-addon-kit` (the
theme, the controls, the Settings / What's new / About dialog and the
notice after updates). Don't edit it here: change the kit and run its
`sync.py`; `build.sh` warns when it's behind. `build.sh` puts
`CHANGELOG.md` in the package, where What's new shows it to users, so
write it in their terms.
