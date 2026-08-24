# LOK Sketcher

The drawing surface inside LOK Studio. You sketch the map, and the built-in generator
turns it into a real region file — IMPORT REGION and ▶ BUILD R# in the sidebar run the
whole loop, no Claude session needed. (The same HTML still opens in a plain browser as
a fallback, with reduced saving features.)

## The basics

Draw with the left mouse button. The tools run down the right side, and each one has a
hotkey (shown on the button). Right-drag or hold SPACE to pan around, scroll wheel to
zoom. Ctrl+Z undoes, Ctrl+Y redoes.

Your work saves itself to disk as you go — close the app, come back tomorrow,
it's still there.

The dark canvas is blank space. You only paint the parts you want built; everything you
don't touch stays empty. The Dead space brush is for carving blank back INTO something
you painted, not for outlining around your map.

## The grid and the center

The sidebar's grid controls are size (W×H) and a **center X/Y**. The canvas is a window
onto the map's coordinate plane, and the center fields say which coordinate sits in the
middle of it — (0,0) by default. Type a different center and Apply: your drawing does NOT
move — every tile keeps its exact x/y — the window slides so your chosen spot is
mid-canvas. **Center on 0,0** slides it back. If sliding or shrinking would push drawn
tiles off the canvas, the canvas grows by itself (symmetrically around your center, with
25 tiles of clearance past everything drawn) and tells you — it never clips your work.

## The two views

**M** flips between Edit view (fast, for working) and Blueprint view (the pretty one —
cream walls on black, glowing doors, the map title drawn in the corner). Same map, two
looks. The BLUEPRINT VIEW button does the same as M.

## The brushes, in plain terms

- **Wall** — a thin interior wall, always one tile thick.
- **Structural** — thick solid mass: the outer shell of a dungeon, big block walls.
  The generator builds walls exactly where you draw them and nowhere else — it never
  wraps a wall around your map for you. Want an enclosure generated? Say so at build time.
- **Door** — a door in a wall. The generator figures out which way it faces.
- **Room floor / Hall floor** — interior floor, and YOU declare which is which. What you
  draw is what the generator believes.
- **Dirt floor** — walkable dirt ground, its own thing (not the same as Road).
- **Grass / Water / Road** — outdoor ground. Road is the walking path through grass.
- **Deep water** — water you can NOT walk through.
- **Dead space** — never built, stays void.
- **Boss** — marks the boss tile (the cyan diamond).
- **Path** — a green dot trail for planning your intended route. Not built, just notes.
- **Tree** — a walkable tree on top of whatever ground is there.
- **Tree wall** — a Heavy Oak you can't walk through or see past. A living wall.
- **Label** — text on the map. Click empty ground for a new one, click a label to edit
  it, drag it to move it.
- **Select** — drag a box, then Ctrl+C copy, Ctrl+X cut, Ctrl+V paste. The copy floats
  under your mouse and every click stamps it down. Del clears the box. Esc gets you out.
- **Erase** — first pass lifts marks and labels off a tile, second pass takes the ground.

Brush sizes 1/2/3/5 are in the sidebar, and a ghost outline previews where your brush
will land before you click.

## Connectors — how levels link up

Under CONNECTORS: **Spawn** (where players appear), **Portal**, **Stairs Up**, **Stairs
Down**. Place one with a click. Click it again to give it a link tag — put the same tag
on a connector in another map and those two spots are linked. That's how stairs on level
3 know they come out on level 4.

## The palette screen

The PALETTE / STYLES button opens a full screen (Esc to get back). This is where the
sketch's roles become real game tile numbers: every brush has a box with ONE tile id in
it, and next to each box you see the actual game tile that number is. Type a different
number, the picture changes. Every box starts with a sensible default, and the ↺ button
beside each one puts that row back to its default.

**Doors: type the CLOSED door's number — that's all a door is in the palette.** The
defaults are the closed ids (66 NS, 67 EW). A placed door automatically carries its
whole family into the map (open, closed, secret, destroyed ids all filled in from how
that door is used in the live maps). The ledger only lists closed door sprites — the
open and destroyed variants are hidden since you never pick them directly. Secret-door
sprites still appear because they double as real wall tiles.

**Deep water is a two-button pick: 19 or 605.** That number is the obstruction — the
thing you actually see. The water tile underneath comes from your Water row
automatically.

**Floor boxes take comma lists for a random mix.** Type `176,178` in a floor box and
the builder scatters those per tile; repeat a number to weight it (`176,176,176,178` =
75/25). The little picture shows the first id. The scatter is tied to tile coordinates,
so the same map builds the same way every time — an approved look never reshuffles.
Floors only (Room/Hall/Dirt/Grass/Road/Wall floor); walls and doors stay one id.

**0 means "none."** Typing 0 in a wall, corner, or door box turns that piece off — the
generator won't emit it at all. That's how you make a BARE zone: floors and structural
blocks only, no wall dressing, no doors (openings are just gaps in the mass). Note the
difference: 0 = none, but an *emptied* box = "use the default." Floors and the
structural block can't be zeroed. A `bare` style template ships in `Generator/styles/`.

You only ever type the main number — walls and doors need extra ids under the hood
(destroyed walls, closed doors, and so on), and the generator fills those in
automatically from how that id is actually used in the live maps (`companions.json`,
mined by `Generator/mine_companions.py`). If you use an id no map has ever used, the
build stops and asks rather than guessing.

Fill in a set of numbers you like? Hit **Save** and name it — it lands in
`generator\styles\` as a file, appears in the dropdown on any machine after a push,
and **Delete** removes it (with a confirmation). **Export** saves a copy wherever you
like, and **Defaults** resets the whole board. Each wall, corner, and door row also
has an **×** button — one click sets it to 0 (none) for bare styles.

Below all that is the **tile ledger**: every terrain tile in the game, with its picture —
1,432 of them. Type in the filter box to narrow it down by number or name, click any tile
to copy its number. (Tiles from the game's older core file have no names — the game data
itself doesn't name them — so they show as picture + number only.)

The numbers you set travel INSIDE the exported sketch, so a map always carries its own
look with it.

## The MASKS tab — restyling areas of existing maps

The SKETCH/MASKS tabs at the top of the sidebar switch between two views of the same
map. MASKS is not for drawing — it's for telling the generator which style goes where.
Whatever is in the sketch area IS the mask base: switch to MASKS and the current sketch
appears dimmed and read-only, ready to mask. So the flow is simple — import any map into
the sketch (your own export, or a section Claude prepped), then flip to MASKS. The
IMPORT BASE MAP button does the same thing from inside the masks tab: it loads the file
into BOTH areas. Then add masks: each
mask is a named colored area bound to one of your saved styles. Paint the mask over the
part of the map that should use that style (a tile can only belong to one mask; painting
one mask over another takes the tile). EXPORT MASKS produces a file you hand back to
Claude, and the generator restyles exactly those areas — nothing else on the map is
touched. Your sketch on the other tab is completely unaffected by any of this.

## Getting maps in and out

**IMPORT REGION…** (sidebar) is the way in: browse to a region XML, see its id, name
and bounds, optionally give a window (`x0 y0 x1 y1`), and it lands on the canvas with
the R# box stamped. The app silently keeps a full-region backup and the untouched
context it will diff your changes against.

**▶ BUILD R#** is the way out: pre-flight first (target, mode, tile count, palette
line — read that line first whenever a build looks wrong), then only explicit
buttons. Merges are dry-run → CONFIRM & WRITE, a missing file restores from the
import backup before merging, and an unused number is a plain CREATE NEW. Backups go
to `Regions\_pre-fix\` before every write; HaDeZs Test is refused.

## Saving and where things live

Your work autosaves to disk as you draw (`workspace\` in the LOK Studio folder) and
comes back when you reopen the app. EXPORT JSON opens a real save dialog (defaults to
`workspace\Exports`); IMPORT JSON opens in `workspace\Imports`. Styles save straight
into `generator\styles\` — no folder linking, no browser storage — and travel to
your other machine with every git push.

## When Claude is still involved

Routine builds and merges don't need a Claude session anymore. Claude sessions are
for: applying MASKS to a region (paint and export works in-app; the applier isn't a
button yet), new rule corrections after you fix something in WorldForge, and changes
to the tools themselves.

## Applying masks — the full sequence

1. **Get the area on canvas** — IMPORT REGION with a window covering the part to
   restyle.
2. **Mask it** — flip to MASKS, add a mask per area, bind each to a saved style,
   paint. EXPORT MASKS (the export carries the style numbers, so it's self-contained).
3. **Claude applies** — the masks applier isn't a button yet, so hand the export to a
   Claude session. Only masked tiles whose look actually changes get rewritten;
   unmasked tiles and decorations aren't touched; masks recolor what exists, never
   create tiles. Dry-run report first, nothing written until you say so.
4. **Check it in WorldForge** — seams where two styles meet are the part still being
   learned; corrections there get captured as rules, same as the door and junction
   rules were.

---

## Technical notes (for Claude and the generator — safe to ignore)

Export format v5. Layers: `wall, structural, door, room, hall, dirtfloor, grass, water,
deepwater, dirt (= ROAD, name kept for compatibility), dead, boss, path, tree, treewall`,
connector layers `spawn / portal / stairs_up / stairs_down` as `[x, y, "tag"]`, plus
`labels` and `palette` (role → id map). Coordinates are absolute region coordinates.
Older files (v1–v4) import fine; legacy `floor` loads as `room`.

Generator: `generator/sketch_build.py` (sketch → region XML,
locked build process, `--new` or `--merge`, dry-run by default) and `xml_to_sketch.py`
(region → sketch). Palette precedence, later wins: gray-box defaults < sketch palette <
`--style <name>` < `--palette <file>`. Style files live in `generator/styles/`;
`graybox.json` is the template.

Captured ids (2026-08-23): stairs up 127, stairs down 123, portal egress 318, spawn-in =
floor ground 2, boss tile = floor ground 5, deep water = water + obstruction 19, tree
wall = obstruction 266 blockVision, tree default 98.

Ledger: `app/ui/tiles_ledger.js`, baked by `generator/bake_ledger.py <worldforge_dir> <this
folder>` from Data.bin + Kesmai.bin/Stormhalter.bin. Re-bake after a WorldForge update.

Companions: single-number palette entries expand via `generator/companions.json`
(mined from the live maps by `mine_companions.py`); unknown ids are a hard stop.

Diff merge: `sketch_build.py <export> --merge <region> --base <context>` writes only
tiles whose built result differs from the context; erased context tiles are cleared.

Masks: export is `{kind:"masks", source:{…}, styles:{name:values}, masks:[{name, style,
tiles:[[x,y],…]}]}`. Applied by `generator/apply_masks.py <masks> <context> --merge
<region> [--write]` — per-mask resolved palettes, only actually-changed tiles written.
PREP NOTE (Claude): set the context sketch's `palette` from the region's real ids (the
xml_to_sketch histograms) so the base render reproduces the file — otherwise lossy
ground recovery can make a restyle "change" tiles it shouldn't.
