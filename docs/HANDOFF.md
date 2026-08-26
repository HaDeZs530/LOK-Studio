# LOK STUDIO — the app era (2026-08-24 on)

## ⭐ STANDING LAW (Tony, 2026-08-25): CONFIRM EVERYTHING AGAINST A WORLDFORGE FILE

Nothing this project writes into a region is ever inferred, pattern-matched, or taken
from a UI label. Every element name, value format and default is CAPTURED from a real
WorldForge-saved file — that is how the isometric rules, junctions, doors, companions,
colours and component options were all settled, and it is the reason the generator has
never silently corrupted a map.

The procedure when something new is needed: Tony sets the property in WorldForge on a
throwaway region, saves, names the region; Claude reads the XML and encodes exactly
what is there. If no file has ever used a property, its serialization is UNKNOWN —
say so and ask for a calibration tile. Never guess it.

`Claude Worldforge Testing\Regions\1.xml` is the CALIBRATION REFERENCE (2026-08-25):
doors with isOpen / isSecret / isDestroyed / indestructible, a decayed tree, walls with
and without indestructible, obstructions. Keep it.

WHY IT MATTERS — the labels lie. WorldForge's property panel says "IsDecayed" but the
file says `<decayed>`; "IsIndestructible" writes `<indestructible>`; yet "IsOpen",
"IsSecret" and "IsDestroyed" keep their prefix. There is no derivable rule. Two of
those four would have been wrong on a confident guess.

Colour serialization (same law, captured from region 9):
`<color r=".." g=".." b=".." a=".." />` as the component's FIRST child, 255 = untouched.


## RULING (Tony, 2026-08-24): the 1-wide-hall coverage question is CLOSED — no fix

A 1-tile hall drawn against structural mass on its SOUTH or EAST reads half-covered in
game: the mass's face renders ON the hall tile and the tall sprite spills W/NW. That is
the game's isometric art, not a generator bug. Tony's answer is drawing discipline —
mass on the south/east of a corridor means draw the extra strip (exactly the canon
"visible floor row → hidden face row → block row" from his hand-built regions).
DO NOT re-propose: auto-expansion / logical-mode building (breaks exactly-as-drawn,
coordinates, diff merges, masks, round trip — considered and rejected), or a
coverage-dimming overlay in blueprint (proposed, declined — blueprint's existing
implied-face rendering is enough). Nothing to build here.
WHAT WAS BUILT INSTEAD (Tony's design, mocked up and approved): blueprint's implied
face strips are trimmed so a QUARTER of the carrier tile shows as floor — north faces
keep the top quarter, west faces the left quarter (TRIM=0.25 in drawBlueprint;
measured ~1/5-1/4 surviving sliver from an in-game close-up, Tony chose 1/4 over 1/3).
The two orientations now read differently, and a 1-wide hall against mass shows its
true sliver instead of a solid cream band. Drawn walls/structural tiles unchanged.
BOTH-FACES TILES (mass south AND east): the two strips stack and only the top-left
quarter-corner shows floor — reviewed with Tony, ACCEPTED AS-IS (a cleaner combined
shape was mocked up and declined as indistinguishable). Don't "fix" the overlap.
EVOLVED SAME NIGHT (Tony's design, mocked and approved): (1) the NW DIAGONAL of every
block is a third carrier — an L-piece, floor on its top-left quarter edges, cream in
the SE bulk (the sprite spill blueprint previously ignored); (2) strip ENDS get a 45°
corner cut back to the tile's own ground color — NE end of north strips, SW end of
west strips, cut spans CUT=0.75 — imitating the isometric lean while the view stays
flat. Cuts appear ONLY where a run truly ends (next tile isn't a block or another
N/W carrier), so runs and N-meets-W junctions stay solid — Tony's tileability rule.
Carrier sets are collected with a 1-tile pad past the viewport so edge cuts stay
honest. Cuts paint in a FINAL pass with ~1px bleed (a later strip on a both-strips
tile was repainting over an earlier cut; AA left hairlines) and any cream-rendered
neighbor (block/wall/door/strip/NW piece) counts as solid so no cut strands a floor
notch. The full-iso cube render was first rejected as a blueprint REPLACEMENT, then
adopted as a THIRD VIEW MODE (Tony: "edit, blueprint, iso"):
**ISO MODE — M now cycles EDIT → BLUEPRINT → ISO.** `viewMode` string replaced the
`blueprint` bool everywhere (sketchKeep, mask enter/exit, badge, title redraw).
drawIso = blueprint styling, but structural masses render as merged isometric cubes:
top faces shifted up-left S=0.75, east shoulder "#8c7e5e", south shoulder "#a39470",
tops "#e8dcc0", block list padded past the viewport so offscreen tops still show.
Partition walls/doors/marks/labels stay blueprint-style. Verified against Test 3 in
a three-mode test render matching Tony's WorldForge screenshots.
**PACKAGED-APP UNICODE CRASH (Tony's masked build, 2026-08-24):** the frozen
interpreter IGNORES PYTHONUTF8/PYTHONIOENCODING, so _run's UTF-8 env only protects
dev mode — the packaged re-exec fell back to cp1252 and died printing the report's
⚠ glyph. Fixed in the --script branch: sys.stdout/stderr .reconfigure(utf-8,
errors=replace) before running the generator script. Reproduced and verified.
Lesson: any encoding guarantee via env vars must be re-checked under PyInstaller.
**SECOND PACKAGED-APP CRASH, same family (Tony 2026-08-26):** apply_masks saved its
applied-state (reapply/revert memory) beside the script — inside Program Files in the
installed app → PermissionError on a masked WRITE (after the region was already
written; only the state save died). Fix: `--state-dir` flag on apply_masks; main.py
passes `ws()/last_applied_masks` when FROZEN. Dev/standalone keep the old beside-the-
script default. Verified both paths headlessly. AUDIT NOTE for future sessions: grep
generator scripts for writes derived from `Path(__file__)` before packaging features —
anything the generator WRITES must live in the workspace, only reads may live in the
bundle. One consequence: an installed app's reapply memory starts empty (the old
location could never have been written), so the first reapply after this fix won't
revert tiles from before it — harmless for fresh work, worth knowing.
**REPO SHIPS CLEAN (Tony 2026-08-26):** personal styles and the masks applied-state
never go to GitHub. .gitignore now excludes generator/last_applied_masks/ and all of
generator/styles/*.json EXCEPT the two templates (graybox.json = build fallback,
bare.json = bare-style template). This REVERSES the earlier "styles travel with
pushes" two-machine design — styles are per-machine now; moving one means copying its
JSON or exporting from the palette screen. Already-tracked personal files (test1.json,
24.json) need a manual delete+commit by Tony — gitignore alone can't untrack them.
CI bundles the styles dir into the package, so a clean repo = a clean installer.

## 2026-08-24 (night) — UI SCALE · APP ICON · INSTALLER · RELEASE FIX · README

- **INTERFACE SCALE (Tony moved to a 3840x2160 panel; the fixed-px UI read small).**
  CSS `zoom` on the document root, stepped Ctrl+= / Ctrl+− / Ctrl+0 through
  75/90/100/110/125/150/175/200/250%, brief toast readout, persisted PER MACHINE via
  new `ui_scale_get` / `ui_scale_set` (settings.json) with a localStorage fallback in
  browser mode. Shortcuts bound in CAPTURE phase so they work on the palette screen
  and while a text box has focus. **`resize()` now measures `getBoundingClientRect()`
  instead of clientWidth** — the canvas bitmap must match painted pixels or the map
  goes soft above 100%; `tileAt()` was already zoom-safe. Window opens at 80% of the
  screen it lands on (clamped 1200-2600 x 800-1600) instead of a fixed 1500x950.
  Commit `0e0c906`.
- **APP ICON.** Tony's crystal-island design (Claude Design) → `packaging/lok.ico`,
  seven resolutions 16-256 downscaled LANCZOS from the 1024 render, wired as
  `icon='lok.ico'` in the spec (paths there are relative to the spec file). Sources
  kept: `crystal-icon-1024.png` (the richer render — shading/glow) and `icon.svg`
  (flat vector fallback; compared both at 16px, PNG downscale won). First PNG export
  from Claude Design arrived FULLY TRANSPARENT — if that recurs, ask for the SVG
  source instead, it can't arrive blank.
- **RELEASE FIX.** v0.2.0 built clean (17.9 MB artifact) but the Release step failed:
  *"Resource not accessible by integration"* — the workflow token was read-only.
  Added `permissions: contents: write` at workflow level (better than the repo
  setting: travels with the repo). A failed tag build can't be fixed by re-running —
  the run uses that commit's workflow file, so cut a NEW tag.
- **INSTALLER.** `packaging/installer.iss` (Inno Setup) + workflow step: each Release
  now ships `LOK-Studio-Setup.exe` beside the zip. Program Files, Start Menu entry,
  optional desktop shortcut, clean uninstall; user data stays in
  `%LOCALAPPDATA%\LOK Studio` so reinstalls never touch maps or styles. Step falls
  back to `choco install innosetup` if the runner image lacks ISCC. Version comes
  from the tag (`/DAppVersion`), defaults 0.0.0 on manual runs.
  **Onefile exe was considered and REJECTED:** the app re-launches itself as a
  subprocess for every generator call, so a onefile build would re-extract the whole
  bundle on every build/import/mask — installer gives the same one-click share
  without that cost.
- **README REWRITTEN** for a stranger, on Tony's direction (it read like a system
  document, then like a sales pitch — both rejected). Now: the isometric offset
  problem stated plainly, what the tool does, his own scoping line ("not a
  start-to-finish map creator"), then Sketch / Styles / Build R# / Import. Download
  section offers installer and zip via `releases/latest/download/...` permalinks —
  those 404 until a Release exists.
- **PROCESS NOTE FOR FUTURE COWORK SESSIONS: do NOT run git in this repo.** The
  sandbox mount can't delete inside `.git`, so every `git add`/`commit` leaves a
  stale `index.lock` that blocks GitHub Desktop ("A lock file already exists").
  Claude edits files; TONY commits and pushes. If a lock appears, delete
  `.git\index.lock` (hidden — reach it by pasting the path in Explorer's address bar).
  Also: the repo stores LF but the working tree is CRLF, so a Linux-side `git status`
  flags all 20 files as modified — that's an artifact, not a change. Normalize any
  file you edit to LF so Tony's diff shows only real edits.

## 2026-08-24 (evening) — PHASE 2 DONE: MASKS APPLY + PACKAGED APP

- **▶ APPLY MASKS** button on the MASKS tab: needs R# + the region imported via
  IMPORT REGION (kept context = restyle base); dry-run report → CONFIRM & WRITE.
  Verified headlessly (56-tile restyle, carriers correct, audit clean). Mask style
  dropdowns now read the disk style list (was empty in-app — browser-storage leftover).
- **PACKAGED APP WORKS — first CI run, green in 58s.** GitHub Actions (Build Windows
  package workflow, manual or v* tag → Release) → PyInstaller onedir → 
  LOK-Studio-win64.zip. Tony ran the exe cold: drew, made a palette, BUILT a map —
  the frozen paths (bundled ui/generator via _MEIPASS, exe --script re-exec for
  generator subprocesses, %LOCALAPPDATA%\LOK Studio workspace, styles seeded from
  bundle) all proven. Anyone can now run LOK Studio from a zip: no Python, no repo.
- Remaining light: in-app masks APPLY not yet user-tested in WorldForge · action
  version bumps uncommitted at time of writing · tag v0.2.0 when a shareable Release
  is wanted. Procedural generation parked deliberately (Tony's call — later).


The pipeline is now a desktop app: this repo (GitHub tosie/LOK-Studio) is the live
line; the OneDrive sketcher/generator copies are frozen fallbacks. pywebview shell
(app/main.py) hosts the sketcher UI with the generator behind a Python bridge.

PROVEN END TO END BY TONY (2026-08-24): import region (panel: browse -> id/name/
bounds -> window) -> edit -> BUILD pre-flight (3-path: merge dry-run/confirm-write ·
restore-from-import-backup+merge · create-new) -> correct region verified in
WorldForge. Storage on disk (autosave, styles in generator/styles, real file
dialogs), centered app dialogs, mode badge, R# region field (imports auto-stamp it),
blueprint view renders implied N/W face walls (preview approximation — corner caps,
T-join stacks, door carve-outs remain build-only). Fixed along the way: UTF-8 forced
on subprocesses (cp1252 pipes), zero-change merges exit clean, consumed action
buttons remove themselves, unhandled promise rejections surface as dialogs.

Lesson enshrined: when a build looks wrong, READ THE PRE-FLIGHT PALETTE LINE FIRST
(a leftover wall-ns=0 from x-button testing silently stripped 148 walls; the line
had named it all along).

STILL OPEN: masks apply not yet behind a button (paint/export works in-app; applying
goes through Claude) · restore path untested by Tony · home-machine clone ritual ·
packaged .exe via GitHub Actions (Phase 2) · procedural layout generation (Phase 2).

---

# Dungeon Generator — session handoff (updated 2026-08-24)

## 2026-08-24 — REGION 9 CONTEXT PREPPED · IMPORTS/EXPORTS FOLDERS · Make Import.bat

- **Region 9 ("Castle Spire", Regions\9.xml saved by Tony 2026-08-24 11:20) window
  (-33,-75)-(35,-37) pulled to `LOK Sketcher\Imports\region9_-33_-75_to_35_-37.json`**:
  1786 tiles, 30 walls, 50 structural, 7 doors, 8 derived faces dropped, 5 decor-tile
  carriers (preserved on merge). **Palette embedded then STRIPPED on Tony's ruling
  (2026-08-24): edit-imports carry LAYOUT ONLY, no palette — the look comes from his
  saved styles via the palette screen.** This is safe for diff merges because export
  and base are modeled with ONE palette at build time (untouched tiles diff equal and
  get zero writes). The masks PREP RULE (embed real ids in RESTYLE contexts so base
  render == file) is a DIFFERENT flow and still stands. For reference, region 9's real
  ids: room 14, hall 179, road 184, structural_floor 1, walls 1225/1227/1231, 447,
  doors 62/63 closed — a "region9" saved style is Tony's to make.
  **The Imports file is the diff base — merge his export with `--base` against it;
  never let it be overwritten.**
- **LOK Sketcher now has `Imports\` and `Exports\`**: contexts in, Tony's edited maps
  out. Old `Maps\` folder still holds the test_1..3 era files.
- **`Make Import.bat`** beside the sketcher: drag a region .xml on → optional window
  prompt → xml_to_sketch runs → JSON into Imports\, NO Claude session needed (needs
  Python on the machine; falls back to `py` launcher). Limitation stated in README:
  bat-made imports embed no palette (gray-box for new paint) — Claude-prepped imports
  carry real ids. The parked Build Map.bat (sketch→XML side) is still parked.

## 2026-08-24 — FOLDER REORGANIZED (Tony-approved)

`Generator\` now holds ONLY live tooling: sketch_build.py, xml_to_sketch.py,
apply_masks.py, stage_a.py, bake_ledger.py, mine_companions.py + companions.json,
styles\, last_applied_masks\ (those three must stay beside the scripts). Everything
historical moved to `Archive\` at the testing-folder root: region7\ (emitters, markups,
finals, decor plans), region9\ (r9_* plans, reach debug), stage-a-tests\ (old build_*
drivers + canon test layouts), analysis\ (all dated PNGs), markup-tools\ (the three
pre-sketcher HTML tools, superseded by LOK Sketcher). WorldForge project files and the
three .md references stay at root. Verified sketch_build still resolves companions and
builds clean post-move. (__pycache__ left in place — delete blocked by permissions,
harmless.) Sketcher-era outputs continue to live in LOK Sketcher\Maps\.

## 2026-08-24 (latest) — DOORS SHOWN/TYPED AS CLOSED · LEDGER DE-DUPED

Tony's ruling: the palette speaks in CLOSED door ids. Sketcher door defaults are now
66/67 (was 78/79 open). Generator needed NO change — resolve_palette was already
family-aware (any member id → full [open,closed,secret,destroyed]); verified 66→
78/66/151/84 and 67→79/67/152/85 in emitted XML, placement rules are role-based and
untouched. The tile LEDGER hides door OPEN and DESTROYED variants (87 ids, LEDGER_HIDE
set in lok_sketcher.html, derived from companions.json as (opens∪destroyeds)−closeds−
secrets−walls — REGENERATE the list when the miner finds new door families). SECRET
ids are deliberately KEPT: they double as real wall tiles (151 Dragon, 139/140 Dirty
Marble, etc.). Note for future sessions: windows and gates are DoorComponents too and
follow the same closed-id convention.

## 2026-08-24 (latest) — DEEP WATER PICKER

Deep water's palette entry now means the OBSTRUCTION — what the player actually sees;
the water ground underneath is invisible and comes from the Water role. Sketcher row is
a two-button picker (19 | 605), no free-typing; exports the chosen int. resolve_palette:
int 19/605 → {ground: water-role ground, mc 3, obstruction: int}; any OTHER int is a
legacy export where the int was the water ground (old semantics, obstruction 19).
Verified all three paths. Ledger note: 19 and 605 both render from the terrain sheets.

## 2026-08-24 (latest) — RANDOM-MIX FLOORS + palette row order

- **Floor roles accept comma lists** (room/hall/dirtfloor/grass/dirt/structural_floor;
  sketcher shape "nl"): per-tile pick weighted by repetition ("176,176,176,178" = 75/25),
  **seeded by tile coordinate (crc32)** in sketch_build's `_gid` so builds are byte-
  deterministic — rebuilds and diff merges never reshuffle an approved scatter. Verified:
  75/25 distribution, two builds identical. Walls/doors stay single-id (Tony's rule).
  Boss/spawn grounds stay single. Flat scatter only — clumping was offered, deferred.
- Palette grid reordered per Tony: Structural moved up beside Wall floor; Wall NS / Wall
  EW / Corner now share one row. Ghost × placeholders keep all rows column-aligned; ×
  only on the five dressing roles (his confirmation: that's correct).
- ("Random floor" began as Tony misreading the "Room floor" label while tired — but he
  ruled to keep the feature the misreading suggested.)

## 2026-08-24 (later) — SHARED STYLES FOLDER + × NONE BUTTONS in the sketcher

- Palette rows for wall-ns/ew, corner, door-ns/ew got an **× button** = set to 0 (none)
  in one click, for bare styles.
- **Styles now sync through a folder** (Tony works from two machines): Save writes the
  style JSON (with `_name`) into a linked folder via the File System Access API — first
  Save per machine prompts a ONE-TIME directory pick (point it at `Generator/styles` so
  builds see saved styles immediately); dropdown lists the folder (loaded silently at
  boot/palette-open when permission persists, or on first dropdown click). Handle kept
  in IndexedDB; localStorage remains the fallback; folder wins name clashes.
  **CHROMIUM ONLY — Firefox has no FS Access API**; Tony was told to use Chrome/Edge
  for the sketcher (Firefox falls back to browser-local + Export). Offered but not
  built: a baked styles.js read-only fallback for Firefox.
- Also confirmed to Tony: bare-style stripping is SAFE for the build pipeline — it runs
  after the model is complete (orientation/gaps/reachability decided), audits run after,
  and --base contexts are stripped identically so diffs stay fair.

## 2026-08-24 — BARE STRUCTURAL STYLE (Tony's rulings, same day)

A zone of floors + structural blocks with NO dressing: no faces, corners, caps, or
doors. Expressed in the palette, not the sketch: **id 0 in a dressing role
(wall-ns / wall-ew / corner / door-ns / door-ew) = "none — don't emit"** (0 = none;
an EMPTIED sketcher box = default; grounds and structural can't be zeroed).
Template: `Generator/styles/bare.json`. Rulings:
- **Bare zones have NO doors** — connectivity is open gaps in the mass. A drawn door
  in a bare build is a HARD STOP.
- **The builder derives NOTHING**: N/W of a bare mass is VOID unless Tony drew floor
  there (adjoining room floor runs right up to the block; the block's overhang is the
  look). No offset strips, no floorless face tiles. Isometric offsets are Tony's
  drawing discipline in bare zones, not generator output.
- Blocks still emit floor-first on structural_floor, indestructible.
Implementation: resolve_palette normalizes 0→disabled (companions skipped);
`strip_disabled()` removes disabled roles from the MODEL after build (render/layout/
emit/audit all agree) and deletes derived tiles left empty; applied to --base context
models too so diff merges stay fair; tile_lines also guards per-tile (per-mask bare
palettes emit nothing for disabled roles — but masks never delete derived tiles, so
true bare-via-mask needs the seam design pass). Sketcher: palette box showing 0
displays "none — not emitted". Verified: synthetic bare build (mass + N/W adjoining
rooms + gap path) → 96 tiles, zero Wall/Door components besides 38 blocks, 5 derived
face tiles removed, audit clean; door hard stop fires; dressed Test 1 rebuild matches
current rules (only the documented 2026-08-23-late door-fix deltas vs its stale
layout file).

## 2026-08-24 — CENTER-BASED GRID CONTROL in the sketcher

The sidebar's X0/Y0 origin boxes are REPLACED by center X/Y fields (Tony's design):
the canvas is a window over the region plane; the center fields say which absolute
coordinate is mid-canvas (default 0,0; "Center on 0,0" button resets). Re-centering
NEVER re-addresses tiles — drawn content keeps its absolute x/y (stored rel keys are
shifted by the origin delta; undo/redo stacks shifted too; exports byte-identical
before/after). If a re-center or shrink would drop drawn tiles, the canvas AUTO-GROWS
symmetrically around the chosen center to 25 tiles clearance past the drawn extent,
with an alert — never clips, never refuses. Resize keeps the center, not the top-left.
Grid changes are blocked on the MASKS tab. JSON format untouched (x0/y0 still in the
file; import computes and shows the center). Verified by simulation: abs-coord
preservation, growth clearance, old −100/−100 default reproduced. Backup:
`lok_sketcher_backup_2026-08-24.html`. Diff-merge note: re-centering is SAFE mid
context-edit under these semantics.

## ⭐ LATE SESSION (2026-08-23 night) — v5, PALETTE SCREEN, TILE LEDGER

- **Sketch JSON is v5.** Floor split into ROOM (F) and HALL (R) — Tony's drawn classification
  is authoritative, the generator no longer infers room-vs-corridor for declared tiles. New
  DIRT FLOOR ground (I). Legacy `floor` imports as room; `dirt` layer stays ROAD. Sketcher
  UX same session: cursor box + map title moved to the top bar, blank canvas renders as
  dead-space black (unplaced = blank, no more painting dead around a build), Road above
  Water in the tool list.
- **PALETTE / STYLES is a full screen** (button in sidebar, Esc closes): every role → id box
  with per-row ↺ reset, style save/recall (browser), style Export (drops a ready file for
  `Generator/styles/`), Defaults. The palette EXPORTS INSIDE the sketch JSON; sketch_build
  precedence is defaults < sketch palette < --style < --palette (verified end to end).
- **TILE LEDGER baked**: `Generator/bake_ledger.py` reads the WorldForge install
  (Data.bin Terrain.xml 550 ids 1–1007 + Terrain-External.xml 882 ids 622–1599, no id
  collisions; XNB textures LZ4-decoded from Kesmai.bin/Stormhalter.bin) →
  `LOK Sketcher/tiles_ledger.js` (1,432 tiles, 6 MB). Palette boxes show the live game
  tile for the typed id; browsable/filterable ledger on the palette screen. Internal-file
  ids carry no names (game data has none). Known cosmetic miss: ids 209/210 reference a
  nonexistent `Bitmaps\004` base sheet (render from overlay only).
- **ONE NUMBER PER PALETTE ROLE (Tony 2026-08-23 night):** the sketcher's palette boxes
  take a single id; no comma lists. `Generator/mine_companions.py` mined 47 live region
  files (HaDeZs Test 8.23.26 + testing Regions) → `Generator/companions.json`: 36 wall
  ids with their destroyed/ruins, 12 door ids with closed/secret/destroyed.
  `sketch_build.resolve_palette` expands single numbers from that table (water gets
  cost 3, deep water obstruction 19, tree canGrow, treewall blockVision); an id no map
  ever used is a HARD STOP asking Tony — never guessed. Full-entry palettes (graybox.json,
  old exports) still accepted. Mined `indestructible` variants are ignored: role decides
  (structural always true). Re-run the miner when new maps introduce new families.
  Ledger/palette icons doubled (80px cards / 60px rows) same session.
- **DIFF MERGE (`--base`, Tony's workflow ruling 2026-08-23 night):** the context-edit loop.
  Flow: xml_to_sketch a window → Tony imports, edits over/around it → export →
  `sketch_build.py export.json --merge region.xml --base context.json`. Both sketches are
  modeled IN FULL (orientation/faces see the whole neighborhood), then only tiles whose
  BUILT RESULT differs are written; tiles erased from the context are actively cleared;
  untouched context tiles get ZERO writes and stay byte-original (decor safe by
  construction, not just by preserve-extras). Verified: moved a structural wall row south
  one tile — 44 untouched, 19 changed incl. face ripples, 1 derived tile cleared, audit
  clean. ALWAYS keep the exact context JSON handed to Tony; it is the diff base.
  Provenance tracking stays OUT of the sketcher (his ruling — generator's job).
- **THREE GENERATOR FIXES from Tony's WorldForge review of the Test 1 build (2026-08-23):**
  1. **Divider NE/SW corner floors inherit the OUTWARD ground.** On an exterior building,
     those corner tiles lean away from the wall sprite and visibly show floor — they now
     take the exterior neighbor's ground (NE: east then north; SW: south then west; never
     water) instead of interior seen floor. Strict corner match only — through-runs and
     T-junctions unaffected.
  2. **Structural NW exterior cap.** The tile diagonally NW of a mass corner (S neighbor
     carries the W face, E neighbor the N face) now gets the corner piece — canon
     structural_room's exterior NW, was missing from sketch_build. **GUARDED (Tony's
     artifact report, same night): never on drawn room/hall floor** — a lone block
     embedded in a partition building put the cap INSIDE a room, rendering as a wall stub
     floating in the floor (5 such tiles in Test 1). Exterior grounds still cap. xml_to_sketch's
     derived-face drop extended to the SE diagonal so round trips stay clean.
  3. **Unified door rule wired into sketch_build** (was naive door-on-drawn-tile): doors
     piercing a structural run follow canon — N/W doors move OUT to the face strip (N gets
     the corner cap; recess east-wall/south-wall exceptions only when Tony left the second
     gap open), S/E doors stay in the gap with passage cleared, flank corner replacing the
     face wall, and both walls stacked on an open second gap tile. Interior side detected
     by room/hall/floor ground; ambiguous doors warn and default. Divider doors unchanged.
  Round trip re-verified: structure zero-diff; only palette ids (not carried by recovery)
  and the room/hall distinction (recovery maps generic floor->room) differ — pass the
  palette when rebuilding a recovery.
  **T-JUNCTION ENDS RULE wired into the wall classifier (Tony-reported "disconnected
  walls" on Test 2, CONFIRMED FIXED by him in WorldForge):** a run terminating into a
  through-run from the west/north (its east/south end) stacks its wall on the junction
  tile after the through-wall; ends arriving from east/south stop clean; 4-way crossings
  carry both walls; run ends against a structural FACE strip extend onto it (bare-block
  ends still stop clean — that stacking prediction remains untested). 18 junction tiles
  changed on Test 2; canon-shaped regression tests unchanged. Also ruled same night:
  **seen floor is ALWAYS the room floor** — the palette's separate Seen-floor box is
  gone, resolve_palette enforces floor=room; structural_floor stays independent.
  **CARVE CLEANUP (Tony's second artifact report, same night — "wall on both sides of
  the tile past the door flank"):** a carved flank's OLD pushed faces are now removed
  from its N/W neighbors (`_carve` cleanup; drawn walls/blocks/door tiles untouched —
  face sources are unique so this is safe). The N-door face-row continuation is added
  AFTER the carve so canon (13,3) survives. Effect: room/hall tiles beyond a solid-run
  door flank are clean; faces from STANDING blocks remain (face completeness intact).
  The fourdoor synthetic's S/E flank-face tiles went from straight-wall to clean —
  matching Tony's ruling; region-5 recess canon (open flanks, corner caps) unaffected.
  **FLANK CORNER — SUPERSEDED then RESOLVED (same night):** a "mid-run keeps straight
  wall" exception was briefly added, then REVERTED — it was a misread of Tony's report.
  Final state: S/E door flank faces ALWAYS get the corner (region-5 canon, `_drop` the
  face wall + corner, other roles kept). The real rule behind his report: **the block
  corner predicate must NOT fire off drawn partition walls** — an h-partition run
  touching a vertical structural wall was capping the block (e.g. (-15,-31) Test 1).
  Predicate now skips when the S or E neighbor is a drawn wall tile; partition-meets-mass
  is ends-rule territory, never corner-predicate territory.
  **SHARED-WALL DOORS (Test 3, CONFIRMED CLEAN by Tony in WorldForge):** doors in a
  structural run with rooms on BOTH sides take the gap-door pattern (S-form for
  horizontal runs, E-form for vertical — door stays in its drawn tile, passage cleared,
  flank carved, corner on the flank face). The outside-shift N/W forms need an outside.
  Ruled via Test 3: 219-block all-structural room complex, 21 shared-wall doors, zero
  corrections. Mask pipeline also confirmed on a second map same night: Test 3 restyled
  into a fresh region 53 (base kept at 52) — 545 tiles + 10 carriers, "no issues at all,
  perfect" per Tony. Regions 50–53 are the night's test builds. Also that night:
  apply_masks CARRIER EXPANSION — masked blocks/doors pull their N/W face tiles, NW caps,
  and shifted doors (one tile outside the mask) into the restyle with a hybrid palette
  (mask walls, base ground); reverts track carriers too, and the applier keeps a
  last-applied state per region (Generator/last_applied_masks/) so reapplying a moved
  mask reverts what it left.
- **MASKS TAB (Tony's design, 2026-08-23 night):** the sketcher now has SKETCH/MASKS tabs —
  separate work areas. MASKS is for restyling existing maps: Claude preps a coordinate
  section (xml_to_sketch context JSON), Tony imports it as a dimmed read-only base and
  paints named masks over it, each bound to a saved style. One mask per tile (painting
  steals from other masks — no overlap rule needed). Export format:
  `{app:"lok-sketcher", kind:"masks", version:1, source:{title,width,height,x0,y0},
    masks:[{name, style, tiles:[[absx,absy],…]}]}`.
  **This LARGELY SUPERSEDES the multi-wall-set chat topic below** — a mask's style carries
  its wall family, so per-area styles fall out of the same mechanism. Still to design when
  first used: the SEAM rules (which style owns a boundary/junction tile where two masked
  areas' wall families meet — the role model allows stacking two sets on one tile), and
  the seam rules when his first real corrections arrive. **APPLIER BUILT (same night):**
  `Generator/apply_masks.py <masks.json> <context.json> --merge <region> [--write]` —
  models the context in full, resolves one palette per mask (embedded style values in the
  export win, then styles/<name>.json; companions resolved; unfindable style = hard stop),
  writes ONLY masked tiles whose emitted result differs from the base-palette form,
  preserve-extras on, dry run default. Mask export now embeds referenced style VALUES and
  warns on unbound masks. sketch_build's emit/merge accept a per-tile palette callable.
  Verified on a Test 1 window: 44 building tiles restyled to the maze family, ground-only
  style correctly wrote zero, audit clean. PREP RULE: when prepping a restyle context, set
  its sketch `palette` from the region's real ids (histograms) so base render == file.
- **CHAT TOPIC, not built (Tony's ruling):** MULTIPLE WALL SETS on one map. The sketch has
  one wall vocabulary; a map using several wall families per area needs a design pass
  (how a sketch declares "this run is set A"). Work it through in a chat first — do NOT
  bolt a mechanism into the sketcher before that design exists.

---


## ⭐ NEW THIS SESSION (2026-08-23 evening) — THE PIPELINE IS WIRED END TO END

**Sketcher → generator → region XML now exists in both directions.** Two new scripts in
`Generator\`, both verified (see verification below):

- **`sketch_build.py`** — the GENERIC consumer. Takes ANY lok-sketcher JSON and runs the
  locked build process (determine → normalize → model+check → build once → audit battery).
  `--new <id> "<name>"` emits a fresh region; `--merge <region.xml>` merges a section into
  an existing file (dry run by default, `--write` to commit, backup to `_pre-fix\` first,
  refuses HaDeZs Test outright). `--palette <file.json>` overrides the gray-box defaults.
  `--png` renders a preview. Junction vocabulary = the emit_south classifier (through-runs
  carry ONE wall); structural faces/corners = the stage_a finalize rules, including
  floorless walls over void and faces landing on neighboring floor tiles.
  **When merging, components a sketch can't hold (statics, trees, obstructions…) are
  PRESERVED by default** on replaced tiles — a round trip does not wipe decoration.
- **`xml_to_sketch.py`** — the reverse leg. Existing region (or `--window x0 y0 x1 y1`
  section) → sketcher v4 JSON so Tony can pull a built map into the sketcher, modify it,
  and push it back through sketch_build for that section. DERIVED face walls (the ones the
  builder regenerates from structural masses) are dropped on recovery instead of becoming
  drawn walls. Reports ground/wall histograms (for palette reconstruction) and counts the
  decor tiles a rebuild would touch.

**RULINGS (Tony, 2026-08-23):**
- **The sketcher got a STRUCTURAL brush (key X).** Wall = partition, Structural = block
  mass/enclosure. **Walls build EXACTLY AS DRAWN — the generator NEVER auto-encloses a
  map.** No toggle; if Tony wants an enclosure generated he says so at build time. The old
  "outer outline becomes the structural surround" README language is gone. Sketch JSON is
  now v4 (adds the structural layer); v1–v3 import fine.
- **Connector IDs captured (Tony's corrected set, 2026-08-23 late):**
  stairs up = StaircaseComponent teleporterId **127** · stairs down = **123** ·
  portal = EgressComponent egress **318** · **spawn-in point = floor ground 2** ·
  **boss tile = floor ground 5**. Ground 2 has ALWAYS been Tony's spawn marker in the
  maps — an earlier reading of it as the boss tile was wrong and is fixed everywhere.
  Water gray-box default: WaterComponent ground 22 / mc 3 (region 0's form).
  Link tags are design-side only for now — teleporterId is the same fixed id per
  direction in the file, so tags don't survive an XML round trip. Cross-level wiring
  stays a Tony/dev step.

**VERIFICATION (all green):** synthetic map (structural shell + partition rooms + both
door families + all connectors + water/dirt/grass/dead space) built clean, audits zero;
converted back to sketch and REBUILT TO A ZERO-TILE DIFF; merge test changed only intended
tiles and preserved an injected TreeComponent; v3 import builds; HaDeZs guard refuses;
BOM/CRLF intact everywhere. Real-data check: xml_to_sketch read all 2303 tiles of region 9
cleanly (found its two odd staircases, teleporterIds 124/125, kept as link tags).

**⚠ FOUND, NOT FIXED: the canon teaching regions are missing.** `Regions\1.xml` ("Wall
with structural") and `2.xml` ("Wall as room divider") are no longer in `Regions\` — the
fresh-slate cleanup seems to have taken them, so `stage_a.py`'s selftest has nothing to
run against (`Regions\OLD\1.xml`/`2.xml` are contact sheets, `_pre-fix\1.xml` is a Town
Ruins backup). The rules they taught are encoded and verified, but restoring copies would
re-arm the regression. Tony's call where from.

**LATE ADDITIONS (same session) — whole-map vocabulary + style sets:**
- Sketcher UX: grid-snapped GHOST preview of every brush footprint (incl. sizes 2/3/5) ·
  REDO (Ctrl+Y) · SELECT tool (C) with copy/cut/paste-stamp and Del · top toolbar
  (undo/redo, select, copy/paste, zoom, "Go to 0,0" which PANS to the origin — the sidebar
  "Origin to center" is the old origin-setting action) · Dirt brush relabeled ROAD (still
  the `dirt` layer, ground 12 gray-box).
- **Three whole-map brushes, ids captured from the live regions, all round-trip verified:**
  · TREE (Y, overlay mark) → TreeComponent, style picks species (gray-box 98 forest large)
  · TREE WALL (H, overlay) → ObstructionComponent **266 blockVision true** (Heavy Oak — the
    living wall; region 0 has 876 of them). IMPASSABLE; excluded from reachability.
  · DEEP WATER (Q, terrain) → WaterComponent + ObstructionComponent **19** (region 0's
    harbor-edge pattern). IMPASSABLE.
  Specialty obstructions (168, 605, 883, 449…) stay out of the sketch on Tony's word —
  placed by hand, preserved on merge like statics.
- **STYLE SETS (Tony's direction):** the sketch stays logical; a named palette file in
  `Generator\styles\<name>.json` (template: `graybox.json`) maps roles → real ids per area
  style. `sketch_build.py --style <name>`. Future iteration once proven: per-area style
  tags inside one sketch.
- Merge ownership rule: Tree/Obstruction components are now SKETCH-OWNED on replaced tiles
  (regenerated from marks, so recovered sections keep their trees); only truly
  unrepresentable components (statics, lockers, ruins…) are carried over verbatim.

**PARKED, Tony wants it later:** a standalone runner so sketch→XML needs no Claude session
— a `Build Map.bat` beside the sketcher (drag a JSON on, builds via sketch_build.py with
the embedded palette, preview + audit shown). Needs Python on his machine. Safe scope:
`--new` builds; merges/masks keep the reviewed dry-run flow.

**Next:** Tony draws a real map in the sketcher and we shake the pipeline out in practice
— structural-vs-partition placement rules get refined from what that surfaces. Skill fold
(locked process + region-9 lessons + this pipeline into eldrathor-maps) still pending
Tony's go-ahead.

---


## ⭐ THE PIPELINE GOING FORWARD (Tony, 2026-08-23)

**Sketch program → JSON → generator populates.** The sketch tool is
`OneDrive\Stormhalter Worlds\LOK Sketcher\lok_sketcher.html` (self-contained browser app:
200×200+ grid, zoom/pan, brush sizes, terrain brushes incl. grass/water/dirt for OUTDOOR
work, dead-space, boss/path overlay marks, settable coordinate origin, export/import JSON —
format documented in the README beside it). Tony sketches, exports JSON into that folder,
and the generator builds it under the locked process (below). This replaces per-region
ad-hoc markup tools.

## ⭐ THE LOCKED BUILD PROCESS (Tony, 2026-08-23 — after the region 9 regression)

Region 9 regressed because fixes were layered as patches, each recomputing wall
orientations against a different snapshot. NEVER patch-on-patch. Always:
1. **DETERMINE** — classify everything first: what is a room, hallway/corridor, boss room,
   outline, dead space. State the determinations.
2. **NORMALIZE** — collapse input defects in the MODEL (double walls to single — partitions
   are ALWAYS 1-thick; run collapse to fixpoint), enforce declared symmetry on
   partitions/doors but derive rings/enclosure LOCALLY from geometry (never mirror them —
   region 9's top-center chamber is genuinely half-a-tile off-center).
3. **MODEL + CHECK** — build the full model in memory; audit the MODEL before any build:
   0 double walls, symmetry as intended, full enclosure (all existing content counted as
   occupied!), every open cell classified.
4. **BUILD ONCE** — single-pass emit from the model. Wall ids assigned once, from the final
   network: partitions never bleed orientation into structural runs; ring lining is by the
   ring run's own direction only.
5. **AUDIT the output** — doubles / ring cross-orientation walls / stray walls / void leaks
   / reachability / symmetry / ordering(floor→structural→rest) / no dupes / encoding.

## Region 9 (2026-08-23): rebuilt clean under that process — all audits zero. Palette:
walls 1225 h (1229/1228), 1227 v (1229/1230), 1231 NE corner (1229/1232) — NOT
indestructible; 447 ring on ground 1 (lining stacked, by run direction); doors 74/62/25/80
h + 75/63/26/81 v; halls 179, rooms 14. Doors: only the sketch's 1-wide gaps + Tony's
existing — HE places the rest ("we can add doors so they make sense"). Awaiting his door
pass. Regions 0 and 7 cleanup passes done earlier (ordering, dedupe, floors-under-walls
with neighbor-matched grounds).

Continuation point for the WorldForge procedural dungeon generator Tony and Claude are building.
Read this whole file before doing any work. The `eldrathor-maps` skill still applies, EXCEPT where
this file overrides it (see "Rule corrections" below — the old doubled-south/east room rules are
superseded for rooms).

## What this project is

A two-stage pipeline that turns chat-sketched dungeon layouts into WorldForge region XML:

- **Stage A — layout generator.** Tony and Claude sketch in chat on an x/y grid with all isometric
  expansion ALREADY APPLIED, iterate until approved, then emit (a) a typed-grid layout file
  (`<name>.layout.json`) and (b) a gray-box region XML (`<name>.stageA.xml`, placeholder palette:
  floor 1, wall 30-family) that Tony loads in WorldForge to check the red structure view.
- **Stage B — walls builder.** Takes the approved typed grid + a palette block and emits final XML
  (`<name>.xml`) with real floor/wall/door IDs, stacking order, colors. No sketch at this stage.
- The typed-grid file is the single source of truth. Never hand-edit emitted XML; fix the grid and
  re-emit. Both stages write ONLY into `Claude Worldforge Testing` — never HaDeZs Test.
- Sketches shown in chat for approval BEFORE any XML. Approval gate: sketch = geometry,
  WorldForge red view = structure, Stage B = palette.

## Status (2026-08-22)

- Rules **folded into the `eldrathor-maps` skill** with Tony's approval (2026-08-22). The skill
  now carries the wall styles, coverage, doors, emission, palette/role model, sketch legend.
- **Stage A BUILT**: `Generator\stage_a.py` (primitives, finalize, validator, sketch renderer,
  layout.json + gray-box XML emitters) + `Generator\build_tworooms.py` (driver). Selftest:
  reproduces `Regions\2.xml` with 0 differing tiles and `Regions\1.xml` with only the two known
  canon deviations — the (11,8) duplicate 29 and the (14,4) order 30→447→29 (we emit
  floor→block→faces per the locked rule; Tony was told, no objection yet).
- **Hallway rows: v3 pattern CONFIRMED CORRECT by Tony in WorldForge (2026-08-22 pm).**
  A buffer-row variant (v4/v5, hallway at y0 with a covered row at y1) was tried and
  **REJECTED after in-game review** — the visible corridor row sits directly north of the
  face/door row, same as room interiors. Do not resurrect the buffer row.
- **JUNCTION RULE CAPTURED (2026-08-22).** Tony corrected the emitted test region in
  WorldForge; diff against the pristine emit was exactly 3 tiles
  (`Regions\_pre-fix\3.tony-junction-fixes-2026-08-22.xml` is his teaching save):
  1. **A divider wall terminating against a structural mass EXTENDS onto the adjacent FACE
     tile, stacking after the face wall already there** (his (6,-2): 29 then +30; his (13,5):
     30 then +29). **Against a BLOCK it stops clean** — he left every stub-meets-block end
     untouched.
  2. **Vertical face-wall runs stay continuous through face-row crossings**: a face-row tile
     with an EW wall on the non-block tile directly north and a block directly south also
     carries the EW wall (his (14,2): 29 then +30).
  3. Component order on stacked tiles: **pre-existing wall first, extension appended.**
     Generator now emits per-tile insertion order (still reproduces regions 1/2; the only
     shift is iface-col crossings like (5,3)/(13,3) now 447,30,29 instead of 447,29,30 —
     same components).
  All three rules are encoded in `stage_a.py` (`finalize` continuity pass) and the driver.
- **HALLWAY WALL-BAND CONTINUITY (2026-08-22 pm, Tony's second WorldForge pass, 7 tiles —
  teaching save `Regions\_pre-fix\3.tony-hallway-band-fixes-2026-08-22.xml`):**
  1. **A hallway must be fully enclosed by structural or partition walls — no open seams
     between the masses of rooms fronting it.** Between rooms A and B the block row joins
     across the seam ((7,3) = block), the face row's NS run continues (no per-room corner
     pieces at interior seams — (7,2) = 29 not 34), and the corner predicate then correctly
     produces 34 on (6,3).
  2. **Boundary block cols run THROUGH interior face rows at hallway ends** ((1,2) = block+30;
     (1,1) then loses its south face). Exterior face strips + NW corner pieces belong only to
     TRUE exterior boundaries of the merged mass, not to each room separately.
  3. **The interior face col does NOT put its EW wall on the north block-row crossing** —
     Tony stripped it at (5,3) and (13,3). This also settles canon region 1 (14,4): its extra
     30 was a hand-editing artifact, now an expected selftest deviation.
- **EMITTED v7 (2026-08-22, current):** `Generator\tworooms_tjunctions.layout.json` +
  `Regions\3.xml` — junction rule + wall-band continuity folded in. 169 tiles, 36 visible,
  64 blocks, 3 doors, validator clean, BOM+CRLF verified. Pristine copy in
  `Regions\_pre-fix\3.xml`. **The generator now reproduces Tony's corrected region with ZERO
  differing tiles.**
- **Process direction from Tony (2026-08-22):** stay on Stage A — more iterations on simple
  setups to shake out bugs BEFORE Stage B. Then build the drawn-sketch intake: Tony draws a
  layout (his preferred process), Claude recovers it and generates. Use the markup-loop
  technique from the eldrathor-maps skill: labelled grid template → he paints → DIFF his image
  against the blank render to recover cells, never classify by colour.

## Reference regions (Tony hand-built these as teaching examples — they are canon)

`Regions/1.xml` "Wall with structural" and `Regions/2.xml` "Wall as room divider" in this folder.
3×3 room with a door, one per style. IDs in them are PLACEHOLDERS — Tony supplies real IDs per
build. Known defect: region 1 tile (11,8) has wall 29 twice — a mistake, ignore it.

## Confirmed rules (verified tile-by-tile against those regions)

### Two wall styles

**Divider (thin):** single ring on perimeter tiles. 3×3 interior → 5×5 footprint.
N/S runs = NS-wall (e.g. 29), W/E runs = EW-wall (e.g. 30). Corners: NW = corner piece (34),
NE = NS run continues, SW = NS run claims it, SE = NS + EW stacked on one tile.
Door replaces the wall on its tile, seen floor under it.

**Structural (thick):** ring of full-tile structural blocks (e.g. 447) with face walls.
3×3 interior → 7×7 footprint. Per block:
- East face: EW-wall on the SAME tile, sequenced floor → block → wall
- West face: EW-wall on the tile WEST of the block (floor → wall)
- South face: NS-wall on the SAME tile
- North face: NS-wall on the tile NORTH of the block
- Corner piece on any tile whose south neighbor has an EW-wall and east neighbor an NS-wall
Exterior-face tiles sit outside the mass; their floors belong to the surrounding terrain
(parameterized "exterior floor").

### Isometric coverage (Tony, 2026-08-21 — drives layout validation)

A tall sprite at (x,y) spills onto its **west** (x−1,y) and **northwest** (x−1,y−1) neighbors.
Therefore:
1. **No visible floor may sit W or NW of a structural block**, except the designated recess
   illusion tile (below).
2. **Visible floor needs a hidden buffer row/col between it and any block mass on its south and
   east sides** (the face row/col — where the NS/EW faces render). North and west masses may sit
   directly adjacent because they lean away.
So a hallway is: visible floor row → hidden face row (south) → block row. Same for east side.

### Doors

- Two door roles: one ID for a north/south entrance, a different ID for east/west. Generator
  infers orientation from which wall run the door sits in — Tony only gives location.
- **Seen floor under every door, never a wall floor.** Both styles.
- Doors sit **in the face row**, not on open floor. In structural style the door tile also
  carries the corner piece (34) as a cap.
- **Recessed door (structural style):** door on the face row; block row below it omits TWO
  blocks — directly south of the door (open entry, visible floor) and east of that (visible
  floor carrying an EW-wall = the entry's east wall). This is the "single-tile hallway"
  illusion; that second tile is the ONE sanctioned exception to coverage rule 1.
  Canonical example: region 1 door (12,3), gaps (12,4),(13,4).

### Component emission

- Sequence: floor first, then block, then faces, in that order. One wall per face per tile —
  duplicates are defects (generator never emits; audit flags).
- Full child sets always (a WallComponent missing destroyed/ruins crashes WorldForge).
  As captured: walls 29/30/34 → destroyed 42/43/144, ruins 46; block 447 → destroyed=0,
  ruins=44, indestructible=true; door → openId=78, closedId=66, secretId=151, destroyedId=84.
  These specific values follow the palette — re-capture per build.
- Encoding: UTF-8 with BOM, CRLF, 2-space indent, bounds half-open.

### Palette / role model

Layout file stores ROLES, never IDs: floor-visible, floor-hidden, floor-exterior, wall-NS,
wall-EW, corner-NW, structural, door-NS, door-EW. Per build Tony supplies a palette block
mapping roles → IDs (there are many wall families; he names which set for what purpose).
A layout may carry SEVERAL named wall sets; each room/hall references one. Junction tiles may
stack components from two sets.

### Sketch legend (locked)

Three colors + grid, nothing else: visible floor = light, hidden floor = mid-tone (clearly not
the black background), door = red (both orientations). NO structural color, NO wall line
segments — hidden-floor band width carries the wall info (1-thick = divider, 2-thick =
structural). Coordinate labels on both axes; wall-set names as small text labels only when a
layout uses more than one set.

## Next steps (in order)

1. **Regions 4 and 5 corrected by Tony and RE-CAPTURED (2026-08-22 pm). New rules, all
   encoded in `stage_a.py` and verified (r1/r2 selftests unchanged, r3 zero-diff intact):**
   - **DOOR PLACEMENT — unified rule: the door sits where its wall face renders.** N and W
     faces render on the tile OUTSIDE the block → N doors sit in the face row, W doors in
     the face col (both as originally guessed). S and E faces render ON the block → S doors
     sit in the BLOCK ROW gap, E doors in the BLOCK COL gap. The face-strip tile the player
     passes through becomes plain seen floor; the far-side flank face tile becomes corner 34
     (S door: east flank; E door: south flank); the second gap tile carries both walls
     (S door: 30 then 29; E door: 29 then 30). W door: no corner anywhere; second gap tile
     south of exit carries 29 only. Captured in `build_ringroom.py`.
   - **E/W DOORS ARE A DIFFERENT ID FAMILY:** gray-box N/S door = 78/66/151/84; E/W door =
     79/67/152/85 (one higher each). `GRAYBOX` now has door-ns and door-ew entries.
   - **SEEN FLOOR UNDER WALLS BESIDE OPEN FLOOR (exposure rule):** walls lean up-left, so a
     NS-walled face tile with PLAIN open visible floor directly EAST, or an EW-walled face
     tile with plain open floor directly SOUTH, gets seen floor (1) instead of wall floor
     (12). "Plain" = visible floor with an empty stack — doors and walled gap tiles don't
     count. Verified against every canon region with zero false positives.
   - **FACE COMPLETENESS:** every block's north neighbor (if not a block) must carry the
     block's NS north face, and every west neighbor its EW west face. If the tile doesn't
     exist, CREATE IT FLOORLESS — WallComponent with no FloorComponent, wall over void
     (Tony's (8,10) in region 4). This subsumes his (11,9)r4 and (12,12)r5 fixes.
   - Remaining intentional deltas vs his saves: (16,3)r4 stray floor tile (asked Tony —
     assumed accidental, left out); 4 tiles in r5 where his save lists the wall before the
     floor (WorldForge edit artifact — canon everywhere else is floor-first, we emit
     floor-first). Teaching saves: `_pre-fix\4.tony-fixes-2026-08-22.xml`,
     `_pre-fix\5.tony-fixes-2026-08-22.xml`.
2. **PARTITION-FIRST PRINCIPLE (Tony, 2026-08-22): use partition (divider) walls wherever
   possible; structural walls ALWAYS and ONLY on the exteriors of the shape. Must be
   deterministic** — in the drawn-sketch flow, the outer boundary becomes the structural
   shell and every interior line becomes a partition.
3. **Region 6 built and corrected (2026-08-22 pm): structural shell, all-partition interior**
   (4 rooms, 4 doors incl. the first door in a VERTICAL partition — E/W door family works
   in divider runs). Tony's single fix (removed my stacked wall at (8,10), kept (8,8))
   collapsed the junction rule into the **ENDS RULE**:
   - **A divider run extends one tile at its EAST or SOUTH end**, stacking AFTER the wall
     already on that tile (works onto face strips and onto perpendicular partition tiles).
   - **Its WEST or NORTH end stops CLEAN** — the run's first sprite leans up-left and
     already dresses that joint.
   - This subsumes the earlier "extends onto face tiles, stops at blocks" reading — that
     was a coincidence of which ends got tested first. All junction data across regions
     3 and 6 fits the ends rule. UNTESTED EDGE: an east/south end abutting a block
     directly (rule predicts stacking onto the block tile).
   Teaching save: `_pre-fix\6.tony-fixes-2026-08-22.xml`. Generator re-emits region 6 at
   zero diff. Also confirmed: (16,3) in region 4 was a stray click — permanently excluded.
4. **COMPLEX-SHAPE ROUND (2026-08-22 evening) — GENERAL SHELL ENGINE built and validated.**
   Old test regions deleted (fresh slate; teaching saves kept). `stage_a.generate_shell(V)`
   derives the full structural shell around ANY footprint polyomino: F face tiles (cell with
   visible N / W / NW-diag; NW-diag-only = crossing carrying both walls), BLOCK (offsets
   dx,dy ∈ [-1..2] from visible), TRIM beyond (chebyshev-2). Reproduces region 1 from its
   bare floor plan and derives every one of Tony's old region-3 continuity fixes on its own.
   Partition helpers with the ends rule; shell-door helpers for all four sides.
   Three regions built, corrected by Tony, re-captured to ZERO diff:
   - **Region 3 cross** (5 rooms, 4 concave shell corners): **ZERO corrections** — the
     concave shell math is right.
   - **Region 4 L-block** (L-shaped room, 2 shell doors): 1 fix → **partition ELBOWS use
     the ring-corner vocabulary**: two runs joining around a room's NW corner get corner 34
     on the elbow tile, sitting on seen floor.
   - **Region 5 bossway** (8-space winding path to a clipped-corner boss room): 3 fixes →
     (a) vertical face-run continuity fires ONLY when the wall above is a room/corridor's
     east wall (plain open floor directly west of it) — not a mass facade; (b+c) **a pierced
     wall run continues on the door's far flank** (east flank for NS runs, south flank for
     EW cols) — this unifies the old gap-tile wall stacks on S/E doors too. Door-in-1-thick-
     wall gates ((10,17) ew, (12,12) ns) worked as guessed.
   Teaching saves: `_pre-fix\{3,4,5}.tony-complex-fixes-2026-08-22.xml`.
5. **Stage A looks converged.** Remaining untested oddments: two hallways crossing,
   east/south partition end abutting a block directly. Next milestone is Tony's choice:
   **drawn-sketch intake** (blank labelled grid template → he draws → diff-recover →
   generate via the shell engine) or **Stage B** (real palette walls builder).

## FIRST REAL BUILD — region 7 NORTH dungeon (2026-08-22 evening, MERGED into 7.xml)

- Tony directed via the NEW MARKUP TOOL (`Claude Worldforge Testing\north_markup_tool.html`):
  an HTML page with the canvas baked in; he paints walls/doors/boss/path/dead-space per
  tile, exports `Generator\north_markup.json`. This REPLACES screenshot markup recovery —
  his preferred process. (Tool had a click-vs-zoom offset bug, now fixed; door clicks that
  land beside walls are snapped with flank-aware logic — in-line gap doors stay put.)
- Layout: corridor-first per Tony ("corridors mostly; rooms only as transfer nodes or odd
  shapes"). North dungeon: entrance = existing masked-room door (-17,-7); 814 open tiles,
  17 doors; boss = big top-left chamber, south door (-47,-14), 116 steps deep, seals
  completely without its door; dead-space cells honored (not built). Claude's 3 patches
  (approved on render): door (-45,0) — the missing west passage per his red path — and
  walls (-40,-14),(-40,-13) closing a 1-tile slit into the boss chamber beside his void
  block. VOID CELLS RENDER DARK AND READ AS "CLOSED" — always pathfind, never eyeball.
- Emitted with `Generator\emit_north.py` (raw-text merge, row-major insert/replace):
  1032 tiles written (178 replaced — trails/empties, 854 inserted), ZERO tiles outside
  the intended set, zero removed, BOM/CRLF intact, full wall child sets, doors 78/66/151/84
  in h-runs + 79/67/152/85 in v-runs, floor 176 under everything incl. thin walls.
  Pre-merge copy: `Regions\_pre-fix\7_before_north_dungeon_2026-08-22.xml` (Tony's testing
  folder is itself a copy of his game folder — backups are for diffing, not safety).
- NORTH reviewed + corrected by Tony (teaching save `_pre-fix\7.tony-north-corrections-*.xml`).
  Lessons folded: boundary walls at map edges go STRUCTURAL (446 stacked into the wall
  tiles, floorless 446 over void beyond the window, face cols beside); divider T-junctions
  follow the ENDS RULE (through-run wall + terminating run's wall ONLY at its east/south
  end); TIE-INS = masked mass tiles adjacent to new floor get their face walls, seams
  closed with divider runs + corners; face completeness applies onto FLOOR tiles too
  (north/west faces of 446 lines land on neighboring floors, which keep seen floor);
  WorldForge prunes empty <tile/> elements on ITS saves. Structural perimeter rule:
  dungeon edges facing border/void get a 446 line on the dirt bed (the 12-border exists
  to CARRY 446 — the old floor-under-wall rule was about this).
- SOUTH dungeon built same day via `south_markup_tool.html` → `emit_south.py` with all
  north lessons (single-wall junctions, perimeter+faces, AUTO TIE-INS — 23 mass tiles).
  Tony's corrections captured (`_pre-fix\7.tony-south-corrections-*.xml`): confirmed
  neighbor-spill faces everywhere + the ends-rule junction refinement (he ADDED stacks at
  terminating-run east/south ends, REMOVED them at west/north ends — one rule, both cases).
  His later design tweaks are NOT teaching material (his instruction).
- DECORATIVE PASS applied then FULLY REVERTED (2026-08-22 night): my centroid-based motif
  placement landed OFF-CENTER in irregular rooms — Tony pulled the pass ("things are off
  center"), all 144 tiles restored to plain 176. He will hand-place decoration and show it
  as reference; STUDY HIS PLACEMENTS before attempting another decorative pass — visual
  centering in isometric rooms is not the geometric centroid. Also: no 607 in these
  dungeons ("remove lava"). Plan file kept at `Generator\decor_plan.json` for comparison
  against his eventual placements.
- REGION 7 WEST IS COMPLETE: two dungeons, built from Tony's tool markups, corrected,
  tied in, decorated. Next candidates: the markup-tool flow for other regions/areas,
  Stage B (real-palette builds elsewhere), folding the day's late rules into the skill.

## DESIGN LANGUAGE (learned from Tony's region-7 mazes, 2026-08-22 — HIS reference standard)

Tony pointed at two hand-built maze sections in `Regions\7.xml` as the model for how real
content should be laid out ("main importance is a path to the end boss, but if there is a
space, this is how things should be built"). Studied windows: (-8,3)-(53,27) [lower maze,
solved: west door (-1,11) → 115 steps → Fireal walkway behind door (20,5)] and
(4,-27)-(51,1) [upper maze, south hall → lava-moat sanctum]. Analysis PNGs with solved
routes are in the testing folder root (2026-08-22 region7 *.png). Principles:

1. **One true path, wound tight.** The goal sits physically CLOSE to the entrance but far
   by travel — the lower maze ends almost directly above where it starts, after a full
   clockwise sweep of the map. Switchbacks, not straight lines, to the boss.
2. **Depth gradient = progression.** The goal is behind the DEEPEST door; door depth from
   the entrance increases along the main path (a door roughly every 10-15 steps).
3. **Distraction rooms.** About half the doors (9 of 18 in the lower maze) lead to side
   rooms and dead ends hanging off the main path, so players keep making choices. Extra
   rooms exist to fill space and mislead — that is their job.
4. **Fill the footprint.** No large voids inside the shell: leftover space becomes side
   rooms; even fully sealed pockets are acceptable as dead-space filler for the shape
   (bottom-left of the lower maze — confirmed intentional).
5. **Rooms have identity.** Floor inlays (606 blue-cobble motifs: diamonds, spirals, bars)
   give rooms individual character; special floors mark special places (607 Fireal walkway
   at the goal; 178 spaced accent tiles as corridor rhythm; 177 pool surrounds).
6. **Set pieces as landmarks.** Pool alcoves with portal pillars (104 — DECORATIVE, not
   functional, confirmed), dragon walls (151/152), water features — memorable
   non-functional anchors that help players navigate.
7. **Not every gate is a door.** The upper maze's NE sanctum has NO dry path: it is gated
   by wading minimum 2-4 LAVA tiles (floor 10) — an HP-cost gate to the inner platform
   (floor 6, ringed by the lava moat). Terrain as lock.
8. **Scale/rhythm:** rooms ~3×3 up to ~7×9, corridors 1-2 wide and short, wall bands thin
   (partition-first) with the 446 structural fill only in the mass between spaces.

Region-7 maze palette (a real instance of the role model): 139 = wall-NS, 140 = wall-EW,
143 = corner, 446 = structural fill; floors: 176 main (Worn Marble), 606 inlay, 607
Fireal, 177/178 accents, 12 wall-floor, 10 lava, 22 pool floor, 6 sanctum platform;
doors 78/66/151/84 + 79/67/152/85 families in the wild, matching capture.
3. **Drawn-sketch intake** (Tony's preferred end process): he draws the layout, Claude
   replicates. Planned mechanics: Claude renders a blank labelled grid template PNG; Tony
   draws rooms/halls/doors over it in a paint tool; Claude recovers tiles by DIFFING against
   the blank template (markup-loop rule — never classify colours); Claude applies the
   isometric expansion (Tony draws LOGICAL layout, generator does the footprint math),
   renders the expanded sketch back for approval, then emits. Agree the drawing vocabulary
   with Tony before building this.
4. Stage B (real-palette walls builder) only after Stage A survives the above.

## Corrections to the 2026-08-21 rule text (verified against canon 2026-08-22)

- Divider corners: canon region 2 (10,7) carries wall 30 — the WEST (EW) run claims the SW
  corner, not the NS run as the older text said. SE stacks 29+30 as stated. Encoded in
  `stage_a.py` `divider_room` and selftested.

## Working style (unchanged)

Sketch → approval → XML. Never edit region files in place; copies + `_pre-fix\` backups. Preview
first, write second. Survey with real counts before acting. One or two questions at a time.
Concrete next steps, not option lists. Check the date with a tool before writing it anywhere.

---

## SESSION 2026-08-23 (PM) — LOK SKETCHER FINISHED OUT · HANDOFF FOR NEXT CHAT

### What happened this session
Built out `LOK Sketcher/lok_sketcher.html` (the connected "LOK Sketcher" OneDrive folder) into the
full drafting tool. Read `LOK Sketcher/README.md` for the complete feature/JSON reference. Summary:

- **Two views, toggled with M.** Edit view = fast planning canvas. Blueprint view = Tony's chosen
  presentation style (from his Leafhall reference image): cream wall slabs on near-black, ember door
  glow, blue water glow, cyan boss diamonds, letterspaced serif labels, title block from the MAP
  TITLE field. Tony approved this direction; blueprint face stays cream-on-black even though the
  editor UI moved blue (see next).
- **UI restyle (Tony-directed):** editor chrome is now blueish EQ-style — navy panels, teal borders,
  gold text/rulers. Grid BED is neutral charcoal `#161719` (Tony explicitly did not want a blue bed;
  blue grid LINES are wanted). Wall brush light steel, floor slate.
- **Marks:** boss renders as a cyan diamond in BOTH views; path is a green dot. Sidebar swatches show
  the shapes (diamond/dot).
- **Erase peels:** first pass over a tile removes marks/labels/connectors only, second pass takes the
  ground. One layer per stroke.
- **Labels (L):** click empty = new, click = edit, drag = move. Exported as `labels: [[x,y,"text"]]`.
- **Connectors (new, dropdown group in sidebar):** Spawn (S, gold circled dot), Portal (O, violet
  double ring), Stairs Up (U, ▲), Stairs Down (N, ▼). Single-click placement (no drag-paint).
  Clicking a placed connector of the same type again prompts for a **link tag**; two connectors
  sharing a tag are LINKED — the cross-level join key. Tags render beside the glyph and export as
  `[[x,y,"tag"]]` per connector layer. JSON is now **version 3**; v1/v2 import fine.
- **Origin:** (0,0) at grid center by default, Center 0,0 button, pinned top/left rulers, red axes.
  NOTE: a browser autosave from an older version can restore an old origin — one click of Center 0,0 fixes.

### Open items (in priority order)
1. **Generic JSON→XML consumer.** The sketcher exports v3 JSON; per-region emitters exist in
   `Claude Worldforge Testing/Generator/` (emit_north/south/perimeter etc.) but there is NO generic
   script yet that takes any lok-sketcher JSON + target region and runs the LOCKED BUILD PROCESS
   (determine → normalize → model+check → build once → audit battery). That is the next build.
   Connector semantics for it: spawn/portal/stairs are placement intents; matching link tags across
   two sketches/levels mean those tiles connect. Tony's levels are all linked — treat connector
   wiring as a first-class output, and ask Tony for the game-side IDs (portal/stair tile IDs)
   before emitting them; we have NOT captured those yet.
2. **Region 9 doors:** Tony places them himself, then we verify/capture the pattern.
3. **Region 7 west boss rooms:** decoration still pending (Tony held them back).
4. **Skill fold:** the locked build process + region-9 lessons + sketcher pipeline are in THIS file
   but not yet folded into the eldrathor-maps skill. Get Tony's go-ahead, then fold.

### Standing constraints (unchanged)
Never touch HaDeZs Test. Raw-text edits only on region XML, BOM+CRLF preserved. _pre-fix backups
before region edits. Partitions always 1-thick. Always run the locked process + audit battery.
Tony's post-correction design tweaks are NOT teaching material. No 607 in region 7 west dungeons.
Write to Tony in plain language, column-first coordinates.

---

## BUG — FIXED (2026-08-23 late Cowork): sketch_build drops the shell-door flank dividers

**Fixed per the spec below.** The door post-pass now carves flank tiles out of the mass
UNCONDITIONALLY (`_carve`: structural role removed, seen floor, exactly the canon divider
stack; blocks that lose the neighbor grow their own-tile faces back), and door/entry/
passage tiles are stripped of the spurious faces the flank mass pushed onto them during
the faces pass. Verified against a canon-shaped four-door structural room — all four
patterns match stage_a's shell_door_* exactly (N: face-row door+corner, plain entry,
carved e2 wall-ew, face row continues over the gap col · S: door in gap, corner flank,
carved [wall-ew, wall-ns] · E: mirrored · W: face-col door, carved wall-ns, pierced run
continues) — and against Tony's live case: Test 1 door (-13,-22), flank (-12,-22) now
[wall-ew, wall-ns]. Audit battery clean. Same session: sketch↔mask flow fixed (the sketch
auto-snapshots as the mask base on tab switch; IMPORT BASE MAP loads into both areas —
the old reload path that clobbered the saved sketch state is gone).

## Original report (kept for the record): sketch_build drops the shell-door flank dividers

**Symptom:** doors pierced through STRUCTURAL runs come out with no companion divider —
canon requires divider wall(s) to the EAST of a N/S door and to the SOUTH of an E/W door.

**Root cause:** the unified door rule in `Generator/sketch_build.py` (post-pass, ~lines
370–407) made the flank additions CONDITIONAL: `if e2/g2/s2 not in B and
S["ground"].get(...)` — i.e. only when the sketch already left the flank tile out of the
structural mass. That guard was modeled on the region-1 recessed door (blocks deliberately
omitted). On a normally drawn solid run with a 1-wide door gap the flank tile IS in B, the
guard is false, and nothing is emitted. The canon source — stage_a.py's shell_door_north/
south/east/west helpers — created those flank tiles UNCONDITIONALLY as part of the door
pattern (L.put replacing the mass cell with a seen-floor tile carrying the dividers).

**Fix spec (per stage_a canon, door gap at c):**
- side S: flank (x+1, y): remove from mass rendering, seen floor, stack = wall-ew then
  wall-ns. (The corner-replaces-face at (x+1, y-1) already fires — keep it.)
- side E: flank (x, y+1): same conversion, stack = wall-ns then wall-ew. (South-flank
  corner at (x-1, y+1) already fires — keep it.)
- side N: entry tile's east neighbor (x+1, y): convert, wall-ew. Face row continues over
  the gap column (shell_door_north also adds wall-ns at (x+1, y-1) — verify present).
- side W: (x, y+1): convert, wall-ns; pierced face-col run continues below the door.
- When converting a tile out of B: clear its structural role AND any on-block faces it
  carried, then re-audit — its former faces onto neighbors (e.g. spurious wall-ew pushed
  onto the door tile by the flank mass during the faces pass) must be cleaned up too.
- Re-verify against the teaching saves: region 1 north door (12,3) and region 5 S/E/W
  shell doors. Run the full audit battery after.
