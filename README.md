# LOK Studio

Map-making studio for Stormhalter (Legends of Kesmai revival): sketch dungeon and
outdoor layouts, style them with real game tiles, and build WorldForge region XML —
one desktop app, no browser, no Claude session needed at runtime.

## Download (Windows)

### ➜ [**Download LOK Studio**](https://github.com/HaDeZs530/LOK-Studio/releases/latest/download/LOK-Studio-win64.zip)

No install, no Python, no account needed.

1. Download the zip above (or grab it from [Releases](https://github.com/HaDeZs530/LOK-Studio/releases/latest)).
2. **Unzip the whole folder** somewhere you'll keep it — Documents is fine.
3. Run **`LOK-Studio.exe`** from inside that folder.

Windows will say *"Windows protected your PC"* the first time, because the app isn't
code-signed: click **More info → Run anyway**. Keep the exe inside its folder — the
`_internal` folder beside it holds everything the app needs.

First launch: press **▶ BUILD R#** once and point it at the Regions folder of the
segment you build into — use a sandbox copy, never your live game data.

## Run from source instead

Double-click **`run.bat`**. Needs Python installed (python.org, "Add to PATH" ticked).
First run installs one small dependency, then the LOK Studio window opens with the
sketcher inside.

First time on a machine: press **▶ BUILD R#** once and point it at the Regions
folder of the segment you build into (a sandbox copy, never your live game data) —
remembered per machine in `workspace\settings.json`.

## The loop

**IMPORT REGION…** pulls a region XML (or a coordinate window of it) onto the canvas,
stamps the **R#** box, and silently keeps a full-region backup plus the untouched
context that later merges diff against. Draw and style as usual — the palette screen's
numbers travel inside the sketch. **▶ BUILD R#** opens the pre-flight: target, mode,
tile count, and the palette line (read that line first when a build looks wrong).
Then only explicit buttons: merge dry-run → CONFIRM & WRITE, restore-from-backup +
merge if the file went missing, or CREATE NEW for an unused number. Blueprint view
(M) also renders the face walls the builder will add along structural masses, so
joins read the way they build.

## Second machine

GitHub Desktop → clone this repo → `run.bat` → point BUILD at that machine's Regions
folder once. Styles live in `generator/styles/`, so they travel with pushes;
`workspace/` (autosaves, imports, settings) stays per-machine.

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

## Packaged version (no Python needed)

The Actions tab builds a double-clickable Windows package: run the **Build Windows
package** workflow (or push a `v*` tag to also cut a Release), download
`LOK-Studio-win64.zip`, unzip anywhere, run `LOK-Studio.exe`. User files live in
`%LOCALAPPDATA%\LOK Studio`. Needs Microsoft's WebView2 runtime, which Windows 11
and updated Windows 10 machines already have.

## Status

Phase 1 complete (2026-08-24): the full loop — import region, edit, pre-flight,
dry-run merge, confirmed write — runs in-app with no Claude session, verified against
live maps. Open: masks apply as a button, packaged .exe via GitHub Actions, procedural
layout generation. `docs/HANDOFF.md` is the living state and rules history.
