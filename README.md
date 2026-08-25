<img src="packaging/crystal-icon-1024.png" width="120" align="right" alt="LOK Studio">

# LOK Studio

A sketching front end for building WorldForge regions.

[Stormhalter](https://stormhalter.com)'s tiles are isometric, so a wall piece doesn't
render on the tile it sits on. It leans up and to the left, spilling onto neighbouring
tiles, and the piece that draws a corner or frames a doorway often belongs to a
different tile than the wall it closes. Placing walls by hand means tracking those
offsets for every run, corner and door in a region.

LOK Studio handles that placement. You sketch the layout — rooms, corridors, walls,
doors — and it writes the region XML with the wall pieces placed by those rules.

It is not a start-to-finish map creator. It gets a drawn area into WorldForge correctly
built; decoration, spawns and the rest are done in WorldForge afterwards.

---

## Download

### ➜ [**Installer**](https://github.com/HaDeZs530/LOK-Studio/releases/latest/download/LOK-Studio-Setup.exe) &nbsp;·&nbsp; [**Portable zip**](https://github.com/HaDeZs530/LOK-Studio/releases/latest/download/LOK-Studio-win64.zip)

No Python and no accounts either way. The installer puts it in the Start Menu; the zip
runs from wherever you unzip it — unzip the **whole folder** and run `LOK-Studio.exe`
from inside it, keeping the `_internal` folder beside it.

Windows will warn you the first time — *"Windows protected your PC"* — because the app
isn't code-signed. Click **More info → Run anyway**.

---

## How it works

### Sketch

The sketch screen is where you draw and plan — a whole region or just a piece of one.
Rooms, corridors, thin dividing walls, thick structural masses, doors, floors, water,
roads, trees, stairs and portals, on a coordinate grid that matches WorldForge.

The isometric rules are applied as you go, so what you draw is a layout that will
actually build. You lay out the shape of the space; you don't have to think about which
tile carries which wall face.

### Styles

A style is a saved set of tile ids — this floor, that wall family, these doors. Save as
many as you like: a dungeon set, a marble set, a ruined set. Every tile in the game is
browsable with its picture, so you pick by eye rather than by number.

Masking is the other half. Paint over sections of a map and assign each section its own
style, and those areas get rebuilt in their own tiles — one wing in dungeon stone,
another in marble — without redrawing a single wall.

### Build R#

**R#** is the region number you're building into. Press build and the sketch goes
through the generators, which convert it into WorldForge region XML following the
placement and isometric rules.

You see what it intends to do before it does it — which region, how many tiles, which
tile set. Building into an existing region is a dry run first: it reports exactly what
would change and writes nothing until you confirm. Every write is backed up.

### Import

Import a section of a region to work on one area without disturbing the rest, and when
you rebuild, only what you actually changed gets rewritten — decoration you placed by
hand in WorldForge stays untouched. Or import a whole map purely to mask it and apply
styles to specific areas.

---

## Run from source

Clone the repo and double-click **`run.bat`**. Needs [Python](https://python.org) with
"Add to PATH" ticked; the first run installs one dependency and opens the app.

Working on two machines? Clone on both. Your saved styles live in the repo and travel
with it; your maps-in-progress stay local.

## What's inside

| | |
|---|---|
| `app/` | The desktop app — a native window wrapped around the sketcher |
| `generator/` | The build engine: sketch to region XML, region back to sketch, area restyling, and the tile catalog baked from a WorldForge install |
| `docs/` | `SKETCHER_GUIDE.md` for using it, `HANDOFF.md` for the full design history |
| `packaging/` | Icon and build spec for the Windows package |

## How it protects your maps

- Writing into an existing region is dry-run first, explicit confirm second, backed up
  always.
- The sketch is the source of truth. Generated XML is never hand-edited — you change
  the drawing and rebuild.
- Every build is checked before it's saved: no duplicated components, no walls missing
  the pieces WorldForge needs, correct file encoding.
- The tool refuses to write to live game folders. Point it at a sandbox copy.

## Status

The full loop works and is in daily use: sketch, style, build, import a region, edit it,
build it back, restyle areas.
