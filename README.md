# LOK Studio

Map-making studio for Stormhalter (Legends of Kesmai revival): sketch dungeon and
outdoor layouts, style them with real game tiles, and build WorldForge region XML —
one desktop app, no browser, no Claude session needed at runtime.

## Run it

Double-click **`run.bat`**. Needs Python installed (python.org, "Add to PATH" ticked).
First run installs one small dependency, then the LOK Studio window opens with the
sketcher inside.

## What's in here

| Folder | What it is |
|---|---|
| `app/` | The desktop shell (`main.py`) and the sketcher UI (`ui/lok_sketcher.html` + `ui/tiles_ledger.js`, the baked game-tile catalog) |
| `generator/` | The build engine: `sketch_build.py` (sketch → region XML, new builds and diff merges, full audit battery), `xml_to_sketch.py` (region → sketch), `apply_masks.py` (area restyles), `stage_a.py` (canon isometric rules engine), `mine_companions.py` + `companions.json` (wall/door family ids mined from live maps), `bake_ledger.py` (rebuilds the tile catalog from a WorldForge install), `styles/` (named tile-id sets) |
| `docs/` | `HANDOFF.md` — the full rules history and project state. `SKETCHER_GUIDE.md` — how to use the sketcher. |
| `workspace/` | Your working files (Imports / Exports / autosaves). Local only, never committed. |

## Ground rules (enforced by the tools)

- Merges into existing regions are **dry-run first, explicit confirm to write**,
  backup before every write. HaDeZs Test is refused outright.
- The sketch is the source of truth — never hand-edit generated XML.
- Region XML stays UTF-8 BOM + CRLF, floor-first component order, full wall child
  sets. The audit battery runs on every build.

## Status

Phase 1 — productionizing. The browser-era sketcher runs inside the shell; the
storage and build buttons are moving from browser workarounds onto the Python bridge.
See `docs/HANDOFF.md` for the living state.
