<img src="packaging/crystal-icon-1024.png" width="120" align="right" alt="LOK Studio">

# LOK Studio

**Draw a map. Get a working game region.**

LOK Studio is a map-making tool for [Stormhalter](https://stormhalter.com), the Legends
of Kesmai revival. You sketch a layout on a grid — rooms, corridors, walls, doors,
water, forest — pick which real game tiles it should be built from, and the app writes
the WorldForge region file for you.

The part that usually eats the day is the part it takes off your hands: isometric maps
have fussy rules about where wall faces render, which tile carries a corner piece, how a
door in a thick wall gets framed. You draw the shape you want. The builder handles the
rest, the same way every time.

---

## Download

### ➜ [**Download LOK Studio for Windows**](https://github.com/HaDeZs530/LOK-Studio/releases/latest/download/LOK-Studio-win64.zip)

Nothing to install. No Python, no accounts.

1. Download the zip.
2. **Unzip the whole folder** somewhere you'll keep it.
3. Run **`LOK-Studio.exe`** from inside it.

Windows will warn you the first time — *"Windows protected your PC"* — because the app
isn't code-signed. Click **More info → Run anyway**. Keep the exe inside its folder;
the `_internal` folder next to it is the app.

---

## How it works

**Draw.** Sixteen brushes: room and hall floors, thin walls, thick structural masses,
doors, grass, water, roads, trees, stairs and portals. Pan, zoom, copy-paste, undo.
Everything autosaves.

**Choose your tiles.** The palette screen shows every terrain tile in the game — over
1,400 of them, with pictures — and lets you say which one plays each role. Type `176`
next to Room floor and you see the tile you just picked. Save a set as a named style
and reuse it on any map.

**Build.** Press build and the app shows you what it's about to do before it does it:
which region, how many tiles, which tiles it's using. Building into an existing map is
always a dry run first — it tells you exactly what would change, and nothing is written
until you click confirm. Your file is backed up before every write.

**Come back later.** Pull an existing region back onto the canvas, move a wall, add a
room, and rebuild — only what you actually changed gets rewritten. Decorations you
placed by hand in WorldForge survive untouched.

**Restyle without redrawing.** Paint areas of a finished map and assign each one a
style — one wing in dungeon stone, another in marble — and the app repaints just those
tiles.

---

## Run from source

Clone the repo and double-click **`run.bat`**. Needs [Python](https://python.org) with
"Add to PATH" ticked; the first run installs one dependency and opens the app.

Working on two machines? Clone on both. Your saved tile styles live in the repo and
travel with it; your maps-in-progress stay local.

---

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

The full loop works and is in daily use: import a region, edit it, build it back,
restyle areas, all inside the app. Procedural layout generation is the next big piece.

Built by HaDeZs for the Stormhalter dev community. Issues and ideas welcome.
