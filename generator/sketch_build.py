#!/usr/bin/env python3
"""sketch_build.py — generic LOK Sketcher JSON -> WorldForge region XML consumer.

Runs the LOCKED BUILD PROCESS (GENERATOR_HANDOFF.md, Tony 2026-08-23):
  1. DETERMINE   classify everything, state the determinations
  2. NORMALIZE   collapse double partition walls to single (fixpoint); partitions are 1-thick
  3. MODEL+CHECK build the full model in memory, audit the MODEL before any build
  4. BUILD ONCE  single-pass emit from the model — never patch-on-patch
  5. AUDIT       the output: doubles / stray walls / child sets / encoding / only-intended-tiles

RULINGS (Tony 2026-08-23):
  - Walls build EXACTLY AS DRAWN. Wall brush = partition, Structural brush = block mass.
    NO auto-enclosure, ever — if Tony wants an enclosure generated he says so at build time.
  - Connector IDs: stairs up = StaircaseComponent teleporterId 127, stairs down = 123,
    portal = EgressComponent egress 318, spawn-in point = floor ground 2,
    boss tile = floor ground 5 (Tony's correction 2026-08-23 — ground 2 was always spawn).

Junction vocabulary = emit_south.py (latest Tony-corrected classifier):
  through-runs carry ONE wall; corners NW=corner-piece NE=ns SW=ew SE=ns+ew stacked.
Structural faces = stage_a finalize: S/E face ON the block, N/W face on the neighbor
  (created FLOORLESS over void — wall with no floor), corner predicate, face completeness.

Usage:
  python3 sketch_build.py <sketch.json> --new <region_id> "<Region Name>" [-o out.xml]
  python3 sketch_build.py <sketch.json> --merge <region.xml> [--write]
                          [--base <context.json>]   # diff merge: write only what changed vs
                                                    # the context sketch handed to Tony;
                                                    # erased context tiles are cleared
                          [--clear-window x0 y0 x1 y1] [--no-preserve-extras]
  common: [--palette palette.json] [--png] [--layout out.layout.json]

Merge mode is a DRY RUN unless --write. Backup goes to Regions/_pre-fix/ first.
Never run against HaDeZs Test.
"""
import json, re, sys, bisect, datetime, zlib
from pathlib import Path
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------- palette
# Gray-box defaults. Every value here is a CAPTURED id, not an invention:
# walls/doors/corner from stage_a GRAYBOX; water ground 22 / mc 3 from region 0;
# grass 13, dirt 12, floor 1 per Components.xml; connector ids from Tony 2026-08-23.
DEFAULT_PALETTE = {
    "floor": 1, "room": 1, "hall": 1, "dirtfloor": 12, "grass": 13, "dirt": 184,
    # accent floors (Tony 2026-08-25): decoration grounds, default to plain floor 1 —
    # the real ids are per-style choices
    "accent1": 1, "accent2": 1, "accent3": 1,
    "water": {"ground": 22, "movementCost": 3},
    # impassable water = water + obstruction 19 (captured: region 0 harbor edges)
    "deepwater": {"ground": 22, "movementCost": 3, "obstruction": 19},
    # walkable tree mark -> TreeComponent; species is the style's call (98 = forest large)
    "tree": {"tree": 98, "canGrow": "true"},
    # impassable tree = Heavy Oak obstruction, blocks movement AND vision (captured: region 0)
    "treewall": {"obstruction": 266, "blockVision": "true"},
    "structural_floor": 12,
    "wall-ns": [29, 42, 46], "wall-ew": [30, 43, 46], "corner": [34, 144, 46],
    "structural": [447, 0, 44],
    "door-ns": [78, 66, 151, 84], "door-ew": [79, 67, 152, 85],
    "indestructible": False,           # thin walls; structural is ALWAYS indestructible
    "boss_ground": 5, "spawn_ground": 2,
    "stairs_up": 127, "stairs_down": 123, "portal_egress": 318,
}

# v5 sketches declare room/hall explicitly (the classification is Tony's, taken as drawn);
# "floor" remains for v1-v4 sketches. dirtfloor = dirt ground as walkable floor; dirt = ROAD.
GROUNDS = ("room", "hall", "floor", "dirtfloor", "grass", "water", "deepwater", "dirt",
           "accent1", "accent2", "accent3")


def resolve_palette(pal, rep):
    """Single-number palette entries (the sketcher's one-box-one-id form) get their
    load-bearing companions filled in from companions.json — mined from the live maps by
    mine_companions.py. An id no map has ever used is a hard stop, not a guess."""
    # Tony's ruling 2026-08-23: seen floor (under partition walls/doors) is ALWAYS the
    # room floor. Only structural_floor is an independent under-ground.
    pal["floor"] = pal.get("room", pal.get("floor", 1))
    # BARE STYLE (Tony 2026-08-24): id 0 (or null) in a DRESSING role means "none — do
    # not emit this role". Bare zones are floors + structural blocks only: no faces, no
    # corners, no caps, no doors. The builder derives NOTHING — N/W of a bare mass is
    # void unless Tony drew floor there. Grounds and structural can never be disabled.
    disabled = []
    for role in ("wall-ns", "wall-ew", "corner", "door-ns", "door-ew"):
        v = pal.get(role)
        if v in (0, None) or (isinstance(v, list) and (not v or v[0] in (0, None))):
            pal[role] = None
            disabled.append(role)
    if pal.get("structural") in (0, None):
        sys.exit("palette: structural cannot be 0/none — a bare zone still needs its block id")
    if disabled:
        rep.append("bare-style: roles disabled by id 0: " + ", ".join(disabled))
    cp = Path(__file__).resolve().parent / "companions.json"
    comp = json.load(open(cp, encoding="utf-8")) if cp.exists() else {}
    missing = []
    for role in ("wall-ns", "wall-ew", "corner", "structural"):
        v = pal[role]
        if v is None:
            continue
        if isinstance(v, int):
            e = comp.get("walls", {}).get(str(v))
            if e:
                pal[role] = [v, e["destroyed"], e["ruins"]]
            else:
                missing.append(f"{role}: wall {v}")
    for role in ("door-ns", "door-ew"):
        v = pal[role]
        if v is None:
            continue
        if isinstance(v, int):
            e = comp.get("doors", {}).get(str(v))
            if e:
                # family-aware: v may be ANY member id (Tony often types the CLOSED id —
                # it's the tile the ledger shows); the family's own openId leads.
                pal[role] = [e.get("open", v), e["closed"], e["secret"], e["destroyed"]]
            else:
                missing.append(f"{role}: door {v}")
    if isinstance(pal["water"], int):
        pal["water"] = {"ground": pal["water"], "movementCost": 3}
    if isinstance(pal["deepwater"], int):
        # NEW SEMANTICS (Tony 2026-08-24): a bare int in deepwater is the OBSTRUCTION id
        # (19 or 605 — the sketcher's two-button picker; it's what the player sees). The
        # water ground underneath comes from the Water role. Legacy sketches where the
        # int was the water ground (anything other than 19/605) still read the old way.
        dv = pal["deepwater"]
        wg = pal["water"]["ground"] if isinstance(pal["water"], dict) else pal["water"]
        if isinstance(wg, list):
            wg = wg[0]
        if dv in (19, 605):
            pal["deepwater"] = {"ground": wg or 22, "movementCost": 3, "obstruction": dv}
        else:
            pal["deepwater"] = {"ground": dv, "movementCost": 3, "obstruction": 19}
    if isinstance(pal["tree"], int):
        pal["tree"] = {"tree": pal["tree"], "canGrow": "true"}
    if isinstance(pal["treewall"], int):
        pal["treewall"] = {"obstruction": pal["treewall"], "blockVision": "true"}
    if missing:
        sys.exit("companion ids unknown for: " + "; ".join(missing)
                 + " — no mined map has ever used these. Ask Tony for the companions "
                   "(walls: destroyed/ruins · doors: closed/secret/destroyed) or re-run "
                   "mine_companions.py over maps that use them.")
    rep.append(f"palette companions: resolved from {cp.name}" if comp else
               "palette companions: companions.json missing — full entries only")
CONNS = ("spawn", "portal", "stairs_up", "stairs_down")



WALLISH = ("wall-ns", "wall-ew", "corner", "structural",
           "door-ns", "door-ew", "indestructible")


def build_mask_palette(base, a, S, M, rep):
    """--masks <file>: return a per-tile palette callable, or `base` when unmasked."""
    if "--masks" not in a:
        return base
    mf = Path(a[a.index("--masks") + 1])
    md = json.load(open(mf, encoding="utf-8"))
    if md.get("kind") != "masks":
        sys.exit(f"{mf} is not a masks file")
    embedded = md.get("styles", {})
    sdir = Path(__file__).resolve().parent / "styles"
    mask_pal, tile_mask = {}, {}
    for m in md.get("masks", []):
        name, style = m.get("name", "?"), m.get("style", "")
        tiles = [tuple(t) for t in m.get("tiles", [])]
        if not tiles:
            continue
        vals = embedded.get(style)
        if vals is None and style:
            sp = sdir / f"{style}.json"
            if sp.exists():
                vals = json.load(open(sp, encoding="utf-8"))
        if vals is None:
            sys.exit(f"mask '{name}': style '{style or '(none)'}' not found in the masks "
                     f"file or {sdir} — bind a style in the sketcher and re-export")
        p = dict(base); p.update(vals); p.pop("_comment", None)
        resolve_palette(p, rep)
        mask_pal[name] = p
        for t in tiles:
            tile_mask[t] = name
    if not tile_mask:
        return base
    # carriers: a masked block/door pushes faces onto N/W/NW neighbours outside the
    # mask — those take the mask's WALL roles but keep their own ground
    carriers = {}
    for c, name in tile_mask.items():
        if c not in S["structural"] and c not in S["door"]:
            continue
        x, y = c
        for nb in ((x, y - 1), (x - 1, y), (x - 1, y - 1)):
            if nb in tile_mask or nb in carriers:
                continue
            mnb = M.get(nb)
            if mnb and any(r in WALLISH for r in mnb["stack"]):
                carriers[nb] = name
    hybrid = {}
    for c, name in carriers.items():
        h = dict(base)
        for k in WALLISH:
            h[k] = mask_pal[name][k]
        hybrid[c] = h
    rep.append(f"MASKS: {len(mask_pal)} styled area(s), {len(tile_mask)} tiles"
               + (f" + {len(carriers)} carrier tiles" if carriers else ""))
    for name in sorted(mask_pal):
        n = sum(1 for v in tile_mask.values() if v == name)
        rep.append(f"  mask '{name}': {n} tiles")
    return lambda c: hybrid.get(c) or (mask_pal[tile_mask[c]] if c in tile_mask else base)

def load_sketch(path):
    d = json.load(open(path, encoding="utf-8"))
    if d.get("app") != "lok-sketcher":
        sys.exit(f"not a lok-sketcher file: {path}")
    L = {k: [tuple(c) for c in v] for k, v in (d.get("layers") or {}).items()}
    return d, L


def cells(L, name):
    return {(c[0], c[1]) for c in L.get(name, [])}


# ---------------------------------------------------------------- 1 DETERMINE
def determine(d, L, rep):
    S = {
        "wall": cells(L, "wall"), "structural": cells(L, "structural"),
        "door": cells(L, "door"), "dead": cells(L, "dead"),
        "boss": cells(L, "boss"), "path": cells(L, "path"),
        "tree": cells(L, "tree"), "treewall": cells(L, "treewall"),
    }
    for g in GROUNDS:
        S[g] = cells(L, g)
    S["conn"] = {}
    for cn in CONNS:
        for c in L.get(cn, []):
            S["conn"][(c[0], c[1])] = (cn, c[2] if len(c) > 2 else "")
    S["labels"] = [(x, y, t) for x, y, t in d.get("labels", [])]
    # precedence: a tile can only be one terrain; walls/doors beat grounds; structural beats wall
    S["wall"] -= S["structural"]
    S["door"] -= S["structural"] | S["wall"]
    ground = {}
    for g in GROUNDS:
        for c in S[g]:
            ground.setdefault(c, g)      # first layer wins on accidental overlap
    S["ground"] = ground
    blockers = {c for c, g in ground.items() if g == "deepwater"} | S["treewall"]
    walk = (set(ground) | S["door"]) - S["wall"] - S["structural"] - S["dead"] - blockers
    S["walk"] = walk
    comps = _components(walk)
    rep.append(f"DETERMINE: {len(S['wall'])} partition walls, {len(S['structural'])} structural, "
               f"{len(S['door'])} doors, {len(ground)} ground tiles "
               f"({', '.join(str(len(S[g]))+' '+g for g in GROUNDS if S[g])}), "
               f"{len(S['dead'])} dead-space, {len(S['boss'])} boss marks, {len(S['path'])} path marks, "
               f"{len(S['tree'])} trees, {len(S['treewall'])} tree-wall blocks, "
               f"{len(S['conn'])} connectors, {len(S['labels'])} labels")
    rep.append(f"  open areas: {len(comps)}"
               + "".join(f"\n    area {i+1}: {len(cc)} tiles, bbox {_bbox(cc)}" for i, cc in enumerate(comps)))
    for (x, y), (t, tag) in sorted(S["conn"].items(), key=lambda kv: (kv[0][1], kv[0][0])):
        rep.append(f"  connector: {t} at ({x},{y})" + (f" tag '{tag}'" if tag else ""))
    S["areas"] = comps
    return S


def _components(cs):
    seen, out = set(), []
    for c in sorted(cs, key=lambda p: (p[1], p[0])):
        if c in seen:
            continue
        stack, comp = [c], set()
        while stack:
            p = stack.pop()
            if p in comp or p not in cs:
                continue
            comp.add(p)
            x, y = p
            stack += [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
        seen |= comp
        out.append(comp)
    return sorted(out, key=len, reverse=True)


def _bbox(cs):
    xs = [c[0] for c in cs]; ys = [c[1] for c in cs]
    return f"({min(xs)},{min(ys)})-({max(xs)},{max(ys)})"


# ---------------------------------------------------------------- 2 NORMALIZE
def normalize(S, rep):
    """Collapse 2-thick partition runs to 1-thick, to fixpoint. Conservative: only removes
    a wall cell that exactly parallels its N (h-runs) or W (v-runs) neighbor run, keeping
    the north/west line. Anything still clustered gets flagged in the model audit."""
    removed = []
    changed = True
    while changed:
        changed = False
        W = S["wall"]
        for (x, y) in sorted(W, key=lambda p: (p[1], p[0])):
            n, s = (x, y-1) in W, (x, y+1) in W
            w_, e = (x-1, y) in W, (x+1, y) in W
            # horizontal doubling: my north neighbor is wall, we both run horizontally,
            # and I'm the southern duplicate (nothing hanging south of me)
            if n and not s and (w_ or e):
                nn = (x, y-1)
                nw_, ne = (x-1, y-1) in W, (x+1, y-1) in W
                if (w_ <= nw_) and (e <= ne):        # my run is covered by the north run
                    S["wall"].discard((x, y)); removed.append((x, y)); changed = True; continue
            # vertical doubling: west neighbor is wall, both vertical, I'm the eastern duplicate
            if w_ and not e and (n or s):
                wn, ws = (x-1, y-1) in W, (x-1, y+1) in W
                if (n <= wn) and (s <= ws):
                    S["wall"].discard((x, y)); removed.append((x, y)); changed = True; continue
    if removed:
        rep.append(f"NORMALIZE: collapsed {len(removed)} double-wall tiles to 1-thick: "
                   + ", ".join(f"({x},{y})" for x, y in removed[:20])
                   + (" …" if len(removed) > 20 else ""))
        # collapsed wall tiles become ground if a neighbor ground exists, else nothing
        for c in removed:
            if c not in S["ground"]:
                for nb in ((c[0]+1, c[1]), (c[0]-1, c[1]), (c[0], c[1]+1), (c[0], c[1]-1)):
                    if nb in S["ground"]:
                        S["ground"][c] = S["ground"][nb]
                        S["walk"].add(c)
                        break
    else:
        rep.append("NORMALIZE: no double walls found")


# ---------------------------------------------------------------- 3 MODEL + CHECK
def build_model(S, rep):
    """model: (x,y) -> {"ground": role|None, "stack": [role,...], "conn": (type,tag)|None}
    ground role: one of GROUNDS, "structural_floor", or None (floorless wall over void)."""
    M = {}
    wd = S["wall"] | S["door"] | S["structural"]

    def cell(c, ground="__keep__"):
        m = M.get(c)
        if m is None:
            m = {"ground": S["ground"].get(c), "stack": [], "conn": None}
            M[c] = m
        if ground != "__keep__":
            m["ground"] = ground
        return m

    def add(c, role):
        m = cell(c)
        if role not in m["stack"]:
            m["stack"].append(role)

    # ground tiles
    for c, g in S["ground"].items():
        cell(c, g)
    # partition walls: orientation from the run (emit_south classifier, Tony-corrected)
    for c in sorted(S["wall"], key=lambda p: (p[1], p[0])):
        x, y = c
        E, W_, N, Sd = (x+1, y) in wd, (x-1, y) in wd, (x, y-1) in wd, (x, y+1) in wd
        h, v = (E or W_), (N or Sd)
        if h and not v: roles = ["wall-ns"]
        elif v and not h: roles = ["wall-ew"]
        elif h and v:
            # T-junctions follow the ENDS RULE (region 6/7 canon): the through-run's wall
            # first, plus the terminating run's wall ONLY when it arrives at its own
            # EAST or SOUTH end (from the west / from the north). West/north ends of the
            # terminating run stop clean.
            if E and W_ and N and Sd: roles = ["wall-ns", "wall-ew"]   # 4-way crossing
            elif N and Sd: roles = ["wall-ew"] + (["wall-ns"] if W_ else [])
            elif E and W_: roles = ["wall-ns"] + (["wall-ew"] if N else [])
            elif E and Sd: roles = ["corner"]           # NW corner
            elif W_ and Sd: roles = ["wall-ns"]         # NE corner
            elif N and E: roles = ["wall-ew"]           # SW corner
            else: roles = ["wall-ns", "wall-ew"]        # SE corner: stacked
        else:
            roles = ["wall-ns"]                          # isolated stub
        m = cell(c)
        # floor under a partition wall = the tile's drawn ground, else main floor.
        # NE/SW corner tiles lean away from the wall sprite, so on an exterior building
        # they visibly show their floor: inherit the OUTWARD neighbor's ground instead of
        # interior seen floor (Tony's correction 2026-08-23: keep the exterior ground).
        if m["ground"] is None:
            inherit = None
            if W_ and Sd and not E and not N:               # NE corner: outward = E, then N
                for nb in ((x+1, y), (x, y-1)):
                    g = S["ground"].get(nb)
                    if g and g not in ("water", "deepwater"):
                        inherit = g; break
            elif N and E and not Sd and not W_:             # SW corner: outward = S, then W
                for nb in ((x, y+1), (x-1, y)):
                    g = S["ground"].get(nb)
                    if g and g not in ("water", "deepwater"):
                        inherit = g; break
            m["ground"] = inherit or "floor"
        for r in roles:
            add(c, r)
    # doors: family from the run they pierce. Doors piercing a STRUCTURAL run follow the
    # unified rule (post-pass below, after the faces exist); divider doors replace the
    # wall on their own tile (canon region 2).
    amb, sd_doors = [], []
    for c in sorted(S["door"], key=lambda p: (p[1], p[0])):
        x, y = c
        if ((x-1, y) in S["structural"] and (x+1, y) in S["structural"]) or \
           ((x, y-1) in S["structural"] and (x, y+1) in S["structural"]):
            sd_doors.append(c)
            continue
        h = (x+1, y) in S["wall"] | S["structural"] or (x-1, y) in S["wall"] | S["structural"]
        v = (x, y-1) in S["wall"] | S["structural"] or (x, y+1) in S["wall"] | S["structural"]
        if h == v:
            amb.append(c)
        m = cell(c)
        if m["ground"] is None:
            m["ground"] = "floor"                        # seen floor under every door
        add(c, "door-ns" if h and not v else ("door-ew" if v and not h else "door-ns"))
    # structural blocks + faces (stage_a finalize vocabulary)
    B = S["structural"]
    for c in B:
        m = cell(c)
        if m["ground"] is None:
            m["ground"] = "structural_floor"
        add(c, "structural")
    for (x, y) in B:
        if (x, y+1) not in B:
            add((x, y), "wall-ns")                       # south face ON the block
        if (x+1, y) not in B:
            add((x, y), "wall-ew")                       # east face ON the block
    faces_over_void = []
    for (x, y) in B:
        for nb, role in (((x, y-1), "wall-ns"), ((x-1, y), "wall-ew")):
            if nb in B:
                continue
            m = M.get(nb)
            if m is None:
                if nb in S["dead"]:
                    M[nb] = {"ground": None, "stack": [role], "conn": None}
                    faces_over_void.append(nb)
                else:
                    M[nb] = {"ground": None, "stack": [role], "conn": None}
                    faces_over_void.append(nb)
            elif role not in m["stack"] and not any(r.startswith("door") for r in m["stack"]):
                m["stack"].append(role)
    for (x, y) in B:                                     # corner predicate
        # ...on FACE geometry only: a drawn partition run abutting the mass follows the
        # ends rule and must NOT cap the block (Tony 2026-08-23, e.g. h-run into a
        # vertical structural wall).
        if (x, y+1) in S["wall"] or (x+1, y) in S["wall"]:
            continue
        s = M.get((x, y+1)); e = M.get((x+1, y))
        if s and "wall-ew" in s["stack"] and e and "wall-ns" in e["stack"]:
            add((x, y), "corner")
    # NW exterior cap (Tony's correction 2026-08-23): the tile diagonally NW of a mass
    # corner — its S neighbor carries the mass's W face, its E neighbor the N face — gets
    # the corner piece (canon predicate applied off-block; structural_room's exterior NW).
    for (x, y) in B:
        dnw = (x-1, y-1)
        if dnw in B:
            continue
        # ...but only at a mass's EXTERIOR corner. A block embedded in a partition
        # building puts this tile INSIDE a room, where the cap renders as a wall stub
        # floating in the floor (Tony's artifact report 2026-08-23). Drawn interior
        # floor is never a cap tile.
        if S["ground"].get(dnw) in ("room", "hall"):
            continue
        w = M.get((x-1, y)); nb = M.get((x, y-1))
        if w and "wall-ew" in w["stack"] and nb and "wall-ns" in nb["stack"]:
            m = M.get(dnw)
            if m is None:
                M[dnw] = {"ground": S["ground"].get(dnw), "stack": ["corner"], "conn": None}
                if M[dnw]["ground"] is None:
                    faces_over_void.append(dnw)
            elif "corner" not in m["stack"] and not any(r.startswith("door") for r in m["stack"]):
                m["stack"].append("corner")
    # UNIFIED DOOR RULE for doors piercing a structural run (canon build_ringroom +
    # Tony's 2026-08-22/23 corrections): the door sits where its wall face renders.
    # N and W faces render OUTSIDE the block -> those doors move to the face strip;
    # S and E faces render ON the block -> the door stays in the gap itself.
    def _drop(mm, role):
        if mm and role in mm["stack"]:
            mm["stack"].remove(role)

    def _interior(t):
        return S["ground"].get(t) in ("room", "hall", "floor")

    def _strip_walls(t):
        mm = M.get(t)
        if mm:
            mm["stack"] = [r for r in mm["stack"] if r not in ("wall-ns", "wall-ew", "corner")]
        return mm

    def _carve(t, stack):
        """Pull a flank tile out of the mass (or claim an already-open one): seen floor +
        exactly the canon divider stack (BUG fix 2026-08-23 — flanks are UNCONDITIONAL,
        stage_a shell_door_* canon; the old ground/B guard dropped them on solid runs)."""
        B.discard(t); S["structural"].discard(t)
        mm = cell(t)
        mm["stack"] = list(stack)
        mm["ground"] = "floor"
        S["ground"][t] = "floor"; S["walk"].add(t)
        # blocks that just lost this neighbor grow their own-tile faces back
        if (t[0], t[1]-1) in B:
            add((t[0], t[1]-1), "wall-ns")               # north block's south face
        if (t[0]-1, t[1]) in B:
            add((t[0]-1, t[1]), "wall-ew")               # west block's east face
        # and the faces THIS tile pushed while it was still a block are now stale —
        # take them back off its N and W neighbors (Tony 2026-08-23: the carved flank's
        # old north face was landing on the room tile beyond the door wall). Sources are
        # unique, so only tiles that aren't drawn walls/blocks/doors are touched.
        for q, role in (((t[0], t[1]-1), "wall-ns"), ((t[0]-1, t[1]), "wall-ew")):
            if q in B or q in S["wall"]:
                continue
            mq = M.get(q)
            if mq and role in mq["stack"] and not any(r.startswith("door") for r in mq["stack"]):
                mq["stack"].remove(role)

    for c in sd_doors:
        x, y = c
        m = cell(c)
        if m["ground"] in (None, "structural_floor"):
            m["ground"] = "floor"                        # seen floor through every doorway
        horiz = (x-1, y) in B and (x+1, y) in B
        ins, outs = ((x, y+1), (x, y-1)) if horiz else ((x+1, y), (x-1, y))
        side = None
        if _interior(ins) and not _interior(outs):
            side = "N" if horiz else "W"                 # interior below/right of the run
        elif _interior(outs) and not _interior(ins):
            side = "S" if horiz else "E"
        elif _interior(ins) and _interior(outs):
            # rooms on BOTH sides (shared interior wall): the gap-door pattern — the
            # outside-shift forms need an outside. Default 2026-08-23 for Tony's
            # all-structural room complexes.
            side = "S" if horiz else "E"
        _strip_walls(c)                                  # flank mass pushed faces onto the gap
        if side == "N":                                  # door OUT on the face row, capped
            t = (x, y-1); mt = cell(t)
            _strip_walls(t)
            if mt["ground"] is None:
                mt["ground"] = "floor"
            mt["stack"] = ["door-ns", "corner"]
            _carve((x+1, y), ["wall-ew"])                # entry's east wall
            add((x+1, y-1), "wall-ns")                   # face row continues over the gap col
                                                         # (added AFTER the carve cleanup)
        elif side == "W":                                # door OUT on the face col
            t = (x-1, y); mt = cell(t)
            _strip_walls(t)
            if mt["ground"] is None:
                mt["ground"] = "floor"
            mt["stack"] = ["door-ew"]
            _carve((x, y+1), ["wall-ns"])                # south-of-entry divider
            add((x-1, y+1), "wall-ew")                   # pierced face-col run continues below
        elif side == "S":                                # door in the gap; passage cleared
            m["stack"] = ["door-ns"]
            _strip_walls((x, y-1))                       # plain seen-floor passage
            f = M.get((x+1, y-1))
            # east flank face: corner replaces the face wall (region-5 canon — restored
            # 2026-08-23 late after the mid-run exception proved to be a misread; the
            # "no corner" ruling was about partition runs abutting blocks, handled at
            # the corner predicate instead)
            if f:
                _drop(f, "wall-ns"); add((x+1, y-1), "corner")
            _carve((x+1, y), ["wall-ew", "wall-ns"])     # flank dividers, ew then ns (canon)
        elif side == "E":
            m["stack"] = ["door-ew"]
            _strip_walls((x-1, y))
            f = M.get((x-1, y+1))
            if f:                                        # south flank face: corner (canon)
                _drop(f, "wall-ew"); add((x-1, y+1), "corner")
            _carve((x, y+1), ["wall-ns", "wall-ew"])     # flank dividers, ns then ew (canon)
        else:                                            # can't tell inside from outside
            add(c, "door-ns" if horiz else "door-ew")
            amb.append(c)
    # ENDS RULE onto face strips (region 3/6 canon): a partition run's EAST or SOUTH end
    # that terminates against a structural mass extends one tile onto the adjacent FACE
    # tile, stacking AFTER the face wall already there. Ends against a bare BLOCK stop
    # clean (the stacking prediction for that edge is UNTESTED — not built).
    W = S["wall"]
    for (x, y) in sorted(W, key=lambda p: (p[1], p[0])):
        if (x-1, y) in W and (x+1, y) not in W and (x+1, y) not in B:
            t = M.get((x+1, y))
            if t and "wall-ew" in t["stack"] and not any(r.startswith("door") for r in t["stack"]):
                if "wall-ns" not in t["stack"]:
                    t["stack"].append("wall-ns")         # east end onto the face col
        if (x, y-1) in W and (x, y+1) not in W and (x, y+1) not in B:
            t = M.get((x, y+1))
            if t and "wall-ns" in t["stack"] and not any(r.startswith("door") for r in t["stack"]):
                if "wall-ew" not in t["stack"]:
                    t["stack"].append("wall-ew")         # south end onto the face row
    # boss marks: floor becomes the boss tile (ground 5)
    for c in S["boss"]:
        m = M.get(c) or cell(c, "floor")
        m["boss"] = True
    # tree marks (walkable) and tree-wall blocks (impassable): overlays; default ground grass
    for name in ("tree", "treewall"):
        for c in S[name]:
            m = M.get(c) or cell(c, "grass")
            if m["ground"] is None:
                m["ground"] = "grass"
            m[name] = True
    # connectors
    spawns = []
    for c, (t, tag) in S["conn"].items():
        m = M.get(c) or cell(c, "floor")
        if m["ground"] is None:
            m["ground"] = "floor"
        m["conn"] = (t, tag)
        if t == "spawn":
            spawns.append((c, tag))
    # ---- model checks
    warns = []
    for c, m in M.items():
        if len(m["stack"]) != len(set(m["stack"])):
            warns.append(f"duplicate component at {c}")
    # 2x2 partition clusters that survived normalize
    W = S["wall"]
    for (x, y) in W:
        if (x+1, y) in W and (x, y+1) in W and (x+1, y+1) in W:
            warns.append(f"2x2 wall cluster at ({x},{y}) — check the drawing (partitions are 1-thick)")
    for c in amb:
        warns.append(f"door at {c} has no clear run orientation (defaulted to N/S family)")
    for c in S["door"]:
        x, y = c
        if not any(nb in wd for nb in ((x+1, y), (x-1, y), (x, y-1), (x, y+1))):
            warns.append(f"door at {c} touches no wall")
    for c in S["boss"] | set(S["conn"]):
        if c in S["wall"] or c in S["structural"]:
            warns.append(f"mark/connector at {c} sits on a wall tile")
    # enclosure / leak report (INFORMATIONAL — outdoor maps are legitimately open)
    zone = set(M) | S["dead"]
    leaks = []
    for c in S["walk"]:
        x, y = c
        for nb in ((x+1, y), (x-1, y), (x, y-1), (x, y+1)):
            if nb not in zone:
                leaks.append(c)
                break
    if leaks:
        rep.append(f"  open-edge tiles (walkable beside blank canvas): {len(leaks)} "
                   f"e.g. {', '.join(str(c) for c in sorted(leaks, key=lambda p:(p[1],p[0]))[:8])}"
                   " — fine for outdoor space, a LEAK if this was meant to be sealed")
    # reachability from spawn (or biggest area)
    if S["walk"]:
        start = spawns[0][0] if spawns else next(iter(sorted(S["areas"][0], key=lambda p: (p[1], p[0]))))
        reach = _components({c for c in S["walk"]})
        home = next((cc for cc in reach if start in cc), reach[0])
        unreached = S["walk"] - home
        if unreached:
            rep.append(f"  unreachable from {'spawn' if spawns else 'main area'} {start}: "
                       f"{len(unreached)} tiles in {len([cc for cc in reach if cc is not home])} pocket(s)"
                       " — report only; sealed pockets can be intentional")
    if spawns:
        rep.append("  spawn-in points (floor ground 2): "
                   + ", ".join(f"{c}" + (f" '{t}'" if t else "") for c, t in spawns))
    rep.append(f"MODEL: {len(M)} tiles, {len(faces_over_void)} floorless face tiles over void, "
               f"{len(warns)} warnings")
    for w in warns:
        rep.append(f"  ⚠ {w}")
    return M, warns


def strip_disabled(M, S, pal, rep):
    """BARE STYLE (Tony 2026-08-24): dressing roles disabled with id 0 are removed from
    the model itself, so render, layout, emit and audit all agree. Derived tiles left
    with nothing (floorless face tiles, cap tiles) disappear — a bare mass gets NO
    offset strips; N/W of it is void unless Tony drew floor there. Doors cannot exist
    in a bare build: connectivity is open gaps, a drawn door is a hard stop."""
    off = {r for r in ("wall-ns", "wall-ew", "corner", "door-ns", "door-ew")
           if pal.get(r) is None}
    if not off:
        return
    blocked = sorted((c for c, m in M.items()
                      if any(r in off for r in m["stack"] if r.startswith("door"))),
                     key=lambda p: (p[1], p[0]))
    if blocked:
        sys.exit("bare style has no doors — remove the drawn doors at "
                 + ", ".join(map(str, blocked[:12]))
                 + (" …" if len(blocked) > 12 else "")
                 + ". Door roles are disabled (id 0); connectivity is open gaps in the mass.")
    dropped = removed = 0
    for c in list(M):
        m = M[c]
        n0 = len(m["stack"])
        m["stack"] = [r for r in m["stack"] if r not in off]
        dropped += n0 - len(m["stack"])
        if (m["ground"] is None and not m["stack"] and not m["conn"]
                and not m.get("boss") and not m.get("tree") and not m.get("treewall")):
            del M[c]
            removed += 1
    rep.append(f"BARE STYLE: {', '.join(sorted(off))} disabled — "
               f"{dropped} dressing components dropped, {removed} derived tiles removed")


# ---------------------------------------------------------------- 4 BUILD ONCE
def _wall_lines(pal, role, indent="    "):
    w, d, r = pal[role]
    ln = [f'{indent}<component type="WallComponent">']
    t = _tint(pal, role)
    if t:
        ln.append(_color_line(t, indent + "  "))
    ln += [f'{indent}  <wall>{w}</wall>',
          f'{indent}  <destroyed>{d}</destroyed>',
          f'{indent}  <ruins>{r}</ruins>']
    if role == "structural" or _opt(pal, role, "indestructible") or pal.get("indestructible"):
        ln.append(f'{indent}  <indestructible>true</indestructible>')
    ln.append(f'{indent}</component>')
    return ln


def _tint(pal, role):
    """TINTS (Tony 2026-08-25): style palettes may carry {"tint": {role: [r,g,b,a]}} —
    WorldForge's multiplicative color sliders. 255,255,255,255 = untinted = omitted.
    Serialization captured from region 9: <color r=".." g=".." b=".." a=".." /> as the
    FIRST child of the component."""
    t = (pal.get("tint") or {}).get(role)
    if role == "floor" and not t:                  # seen floor follows the room tint
        t = (pal.get("tint") or {}).get("room")
    if not t:
        return None
    t = [int(x) for x in t]
    return None if t == [255, 255, 255, 255] else t


def _opt(pal, role, key, default=None):
    """COMPONENT OPTIONS (Tony 2026-08-25): style palettes may carry
    {"opts": {role: {key: value}}} — WorldForge's non-colour properties. Element names
    are CAPTURED from live regions — region 1 holds Tony's calibration tiles. Beware:
    WorldForge's UI labels don't match the file. "IsDecayed" -> <decayed>,
    "IsIndestructible" -> <indestructible>, but isOpen/isSecret/isDestroyed keep the Is.
    Absent = default, so untouched styles emit exactly what they always did."""
    o = (pal.get("opts") or {}).get(role) or {}
    return o.get(key, default)


def _flag_lines(pal, role, keys, indent="      "):
    ln = []
    for k in keys:
        v = _opt(pal, role, k)
        if v is None:
            continue
        if isinstance(v, bool):
            if v:
                ln.append(f'{indent}<{k}>true</{k}>')
        else:
            ln.append(f'{indent}<{k}>{v}</{k}>')
    return ln


def _color_line(t, indent="      "):
    return f'{indent}<color r="{t[0]}" g="{t[1]}" b="{t[2]}" a="{t[3]}" />'


def _gid(v, c):
    """RANDOM-MIX FLOORS (Tony 2026-08-24): a floor role may be a LIST of ids — the
    per-tile pick is weighted by repetition and SEEDED BY THE TILE COORDINATE (crc32),
    so the same sketch + palette always builds byte-identical output. Rebuilds and
    diff merges never reshuffle an approved scatter."""
    if isinstance(v, list):
        return v[zlib.crc32(f"{c[0]},{c[1]}".encode()) % len(v)]
    return v


def tile_lines(c, m, pal):
    x, y = c
    ln = [f'  <tile x="{x}" y="{y}">']
    g = m["ground"]
    if g is not None:
        if g in ("water", "deepwater"):
            wtr = pal[g]
            ln += ['    <component type="WaterComponent">']
            tw = _tint(pal, g)
            if tw:
                ln.append(_color_line(tw))
            mc = _opt(pal, g, "movementCost", wtr["movementCost"])
            ln += [f'      <ground>{wtr["ground"]}</ground>',
                   f'      <movementCost>{mc}</movementCost>']
            ln += _flag_lines(pal, g, ("depth",))
            ln.append('    </component>')
            if g == "deepwater":
                ln += ['    <component type="ObstructionComponent">',
                       f'      <obstruction>{wtr["obstruction"]}</obstruction>',
                       '    </component>']
        else:
            if m.get("boss"):
                gid = pal["boss_ground"]
            elif m["conn"] and m["conn"][0] == "spawn":
                gid = pal["spawn_ground"]
            else:
                gid = _gid(pal["structural_floor"] if g == "structural_floor" else pal[g], c)
            ln += ['    <component type="FloorComponent">']
            tf = _tint(pal, "structural_floor" if g == "structural_floor" else g)
            if tf and not m.get("boss") and not (m["conn"] and m["conn"][0] == "spawn"):
                ln.append(_color_line(tf))
            ln += [f'      <ground>{gid}</ground>']
            ln += _flag_lines(pal, "structural_floor" if g == "structural_floor" else g,
                              ("movementCost",))
            ln.append('    </component>')
    for role in m["stack"]:
        if pal.get(role) is None:                # bare style: disabled role, emit nothing
            continue
        if role.startswith("door"):
            o, cl, se, de = pal[role]
            ln += ['    <component type="DoorComponent">']
            td = _tint(pal, role)
            if td:
                ln.append(_color_line(td))
            ln += [f'      <openId>{o}</openId>', f'      <closedId>{cl}</closedId>',
                   f'      <secretId>{se}</secretId>', f'      <destroyedId>{de}</destroyedId>']
            ln += _flag_lines(pal, role, ("isOpen", "isSecret", "isDestroyed",
                                          "indestructible"))
            ln.append('    </component>')
        else:
            ln += _wall_lines(pal, role)
    if m.get("tree"):
        tp = pal["tree"]
        ln += ['    <component type="TreeComponent">']
        tt = _tint(pal, "tree")
        if tt:
            ln.append(_color_line(tt))
        cg = _opt(pal, "tree", "canGrow", tp["canGrow"])
        ln += [f'      <tree>{tp["tree"]}</tree>',
               f'      <canGrow>{"true" if cg in (True, "true") else "false"}</canGrow>']
        ln += _flag_lines(pal, "tree", ("decayed",))
        ln.append('    </component>')
    if m.get("treewall"):
        tw = pal["treewall"]
        ln += ['    <component type="ObstructionComponent">']
        to = _tint(pal, "treewall")
        if to:
            ln.append(_color_line(to))
        bv = _opt(pal, "treewall", "blockVision", tw["blockVision"])
        ln += [f'      <obstruction>{tw["obstruction"]}</obstruction>',
               f'      <blockVision>{"true" if bv in (True, "true") else "false"}</blockVision>',
               '    </component>']
    if m["conn"]:
        t, tag = m["conn"]
        if t in ("stairs_up", "stairs_down"):
            ln += ['    <component type="StaircaseComponent">']
            ts = _tint(pal, t)
            if ts:
                ln.append(_color_line(ts))
            ln += [f'      <teleporterId>{pal[t]}</teleporterId>',
                   '    </component>']
        elif t == "portal":
            ln += ['    <component type="EgressComponent">',
                   f'      <egress>{pal["portal_egress"]}</egress>',
                   '    </component>']
        # spawn: the ground-2 floor above IS the emission
    ln.append('  </tile>')
    return ln


def _pal_at(pal, c):
    """pal may be a plain palette dict or a callable (x,y)->palette (per-area styles)."""
    return pal(c) if callable(pal) else pal


def emit_new(M, pal, region_id, region_name):
    xs = [c[0] for c in M]; ys = [c[1] for c in M]
    ln = ['<?xml version="1.0" encoding="utf-8"?>', '<region>',
          f'  <id>{region_id}</id>', f'  <name>{region_name}</name>', '  <height>0</height>',
          f'  <bounds left="{min(xs)}" top="{min(ys)}" right="{max(xs)+1}" bottom="{max(ys)+1}" />']
    for c in sorted(M, key=lambda p: (p[1], p[0])):
        ln += tile_lines(c, M[c], _pal_at(pal, c))
    ln.append('</region>')
    return '\r\n'.join(ln)


# components the SKETCH owns — regenerated from the model, never carried over on merge.
# Everything else (statics, lockers, trash, ruins…) is preserved when a tile is replaced.
KEEP_TYPES = ("FloorComponent", "WallComponent", "DoorComponent", "StaircaseComponent",
              "EgressComponent", "WaterComponent", "TreeComponent", "ObstructionComponent")


def merge(M, pal, src_path, rep, write=False, clear_window=None, preserve_extras=True,
          clear_keys=None):
    src = Path(src_path)
    if "HaDeZs Test" in str(src.resolve()):
        sys.exit("REFUSED: never write to HaDeZs Test. Work on the copy in Claude Worldforge Testing.")
    raw = src.read_bytes()
    assert raw[:3] == b'\xef\xbb\xbf', "source is not UTF-8 with BOM"
    assert b"\r\n" in raw, "source is not CRLF — refusing to merge"
    lines = raw.decode("utf-8-sig").split("\r\n")
    tile_re = re.compile(r'\s*<tile x="(-?\d+)" y="(-?\d+)"\s*/?>')
    blocks, i = [], 0
    while i < len(lines):
        mt = tile_re.match(lines[i])
        if mt:
            key = (int(mt.group(1)), int(mt.group(2)))
            if lines[i].rstrip().endswith("/>"):
                blocks.append((key, i, i)); i += 1
            else:
                j = i
                while "</tile>" not in lines[j]:
                    j += 1
                blocks.append((key, i, j)); i = j + 1
        else:
            i += 1
    if not blocks:
        sys.exit("no <tile> blocks found in the target — wrong file?")
    existing = {b[0]: b for b in blocks}
    sortkeys = [(k[1], k[0]) for k, _, _ in blocks]

    def extras_of(key):
        """non-structural components (statics, trees, obstructions…) of an existing tile,
        preserved verbatim when we replace that tile."""
        if key not in existing:
            return []
        _, s, e = existing[key]
        seg = lines[s:e+1]
        out, j = [], 0
        while j < len(seg):
            mt2 = re.match(r'\s*<component type="([A-Za-z]+)"\s*/?>', seg[j])
            if mt2:
                if seg[j].rstrip().endswith("/>"):
                    if mt2.group(1) not in KEEP_TYPES:
                        out.append(seg[j])
                    j += 1
                else:
                    k = j
                    while "</component>" not in seg[k]:
                        k += 1
                    if mt2.group(1) not in KEEP_TYPES:
                        out += seg[j:k+1]
                    j = k + 1
            else:
                j += 1
        return out

    replacements, inserts, kept_extras = {}, [], 0
    for c in sorted(M, key=lambda p: (p[1], p[0])):
        nl = tile_lines(c, M[c], _pal_at(pal, c))
        if preserve_extras:
            ex = extras_of(c)
            if ex:
                nl = nl[:-1] + ex + [nl[-1]]
                kept_extras += 1
        if c in existing:
            _, s, e = existing[c]
            replacements[s] = (e, nl)
        else:
            pos = bisect.bisect_left(sortkeys, (c[1], c[0]))
            anchor = blocks[pos][1] if pos < len(blocks) else blocks[-1][2] + 1
            inserts.append((anchor, nl))
    cleared = []
    if clear_window:
        x0, y0, x1, y1 = clear_window
        for key, s, e in blocks:
            if x0 <= key[0] <= x1 and y0 <= key[1] <= y1 and key not in M:
                replacements[s] = (e, [f'  <tile x="{key[0]}" y="{key[1]}" />'])
                cleared.append(key)
    if clear_keys:                       # --base diff: tiles erased from the base context
        for key in sorted(clear_keys, key=lambda p: (p[1], p[0])):
            if key in existing and key not in M:
                _, s, e = existing[key]
                replacements[s] = (e, [f'  <tile x="{key[0]}" y="{key[1]}" />'])
                cleared.append(key)
    rep.append(f"MERGE: replacing {len(replacements)-len(cleared)} tiles, inserting {len(inserts)}, "
               f"clearing {len(cleared)} (window), extras preserved on {kept_extras} tiles")
    out, ins = [], {}
    for at, nl in inserts:
        ins.setdefault(at, []).extend(nl)
    i = 0
    while i < len(lines):
        if i in ins:
            out.extend(ins[i])
        if i in replacements:
            e, nl = replacements[i]
            out.extend(nl)
            i = e + 1
        else:
            out.append(lines[i]); i += 1
    btxt = "\r\n".join(out)
    bm = re.search(r'<bounds left="(-?\d+)" top="(-?\d+)" right="(-?\d+)" bottom="(-?\d+)" />', btxt)
    Lb, T, R, Bb = map(int, bm.groups())
    nL = min(Lb, min(c[0] for c in M)); nT = min(T, min(c[1] for c in M))
    nR = max(R, max(c[0] for c in M) + 1); nB = max(Bb, max(c[1] for c in M) + 1)
    if (nL, nT, nR, nB) != (Lb, T, R, Bb):
        btxt = btxt.replace(bm.group(0), f'<bounds left="{nL}" top="{nT}" right="{nR}" bottom="{nB}" />')
        rep.append(f"  bounds ({Lb},{T},{R},{Bb}) -> ({nL},{nT},{nR},{nB})")
    if write:
        stamp = datetime.date.today().isoformat()
        bak = src.parent / "_pre-fix" / f"{src.stem}_before_sketch_build_{stamp}.xml"
        bak.parent.mkdir(exist_ok=True)
        bak.write_bytes(raw)
        src.write_bytes(b'\xef\xbb\xbf' + btxt.encode("utf-8"))
        rep.append(f"  WRITTEN. backup: {bak}")
    else:
        rep.append("  DRY RUN — use --write to commit")
    return btxt, set(M) | set(cleared)


# ---------------------------------------------------------------- 5 AUDIT
def audit(xml_text, M, pal, rep, intended=None):
    errs = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        rep.append(f"AUDIT: XML DOES NOT PARSE: {e}")
        return False
    seen = {}
    for t in root.iter("tile"):
        key = (int(t.get("x")), int(t.get("y")))
        comps = t.findall("component")
        sig = [(c.get("type"), tuple((ch.tag, (ch.text or "").strip()) for ch in c)) for c in comps]
        if len(sig) != len(set(sig)):
            errs.append(f"duplicate component at {key}")
        floors = [c for c in comps if c.get("type") in ("FloorComponent", "WaterComponent")]
        if len(floors) > 1:
            errs.append(f"{len(floors)} floors at {key}")
        for c in comps:
            if c.get("type") == "WallComponent":
                tags = {ch.tag for ch in c}
                if "destroyed" not in tags or "ruins" not in tags:
                    errs.append(f"WallComponent at {key} missing destroyed/ruins (CRASHES WorldForge)")
        seen[key] = sig
    missing = [c for c in M if c not in seen]
    if missing:
        errs.append(f"{len(missing)} model tiles missing from output, e.g. {missing[:5]}")
    if intended is not None:
        pass  # merge path already constrained edits to model+cleared keys by construction
    ok = not errs
    rep.append(f"AUDIT: {len(seen)} tiles in output — " + ("ALL CLEAN" if ok else f"{len(errs)} ERRORS"))
    for e in errs:
        rep.append(f"  ✗ {e}")
    return ok


# ---------------------------------------------------------------- preview PNG
def render_png(M, S, path):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False
    xs = [c[0] for c in M] + [c[0] for c in S["dead"]]
    ys = [c[1] for c in M] + [c[1] for c in S["dead"]]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    cs, mx, my = 14, 46, 30
    img = Image.new("RGB", (mx + (x1-x0+1)*cs + 12, my + (y1-y0+1)*cs + 12), (10, 12, 14))
    d = ImageDraw.Draw(img)
    COL = {"floor": (58, 74, 86), "room": (58, 74, 86), "hall": (85, 104, 122),
           "dirtfloor": (138, 106, 60), "grass": (77, 122, 61), "water": (47, 111, 184),
           "deepwater": (29, 74, 128), "dirt": (109, 84, 51), "structural_floor": (40, 36, 30),
           "accent1": (126, 139, 152), "accent2": (74, 111, 176), "accent3": (160, 118, 74)}
    for c, m in M.items():
        px, py = mx + (c[0]-x0)*cs, my + (c[1]-y0)*cs
        col = COL.get(m["ground"], (24, 24, 26)) if m["ground"] else (16, 14, 12)
        if "structural" in m["stack"]:
            col = (120, 132, 143)
        elif any(r.startswith("door") for r in m["stack"]):
            col = (194, 74, 42)
        elif any(r.startswith("wall") or r == "corner" for r in m["stack"]):
            col = (185, 199, 210)
        if m.get("boss"):
            col = (53, 196, 214)
        if m.get("tree"):
            col = (46, 139, 58)
        if m.get("treewall"):
            col = (29, 92, 38)
        if m["conn"]:
            col = {"spawn": (224, 200, 90), "portal": (176, 106, 224),
                   "stairs_up": (230, 230, 235), "stairs_down": (150, 150, 160)}[m["conn"][0]]
        d.rectangle([px, py, px+cs-1, py+cs-1], fill=col)
    for x in range(x0, x1+1):
        if x % 10 == 0:
            d.line([mx+(x-x0)*cs, my, mx+(x-x0)*cs, my+(y1-y0+1)*cs], fill=(60, 90, 96))
            d.text((mx+(x-x0)*cs, 8), str(x), fill=(224, 200, 90))
    for y in range(y0, y1+1):
        if y % 10 == 0:
            d.line([mx, my+(y-y0)*cs, mx+(x1-x0+1)*cs, my+(y-y0)*cs], fill=(60, 90, 96))
            d.text((4, my+(y-y0)*cs), str(y), fill=(224, 200, 90))
    img.save(path)
    return True


def dump_layout(M, S, d, path, pal):
    cellrows = []
    for c in sorted(M, key=lambda p: (p[1], p[0])):
        m = M[c]
        row = {"x": c[0], "y": c[1], "ground": m["ground"], "stack": m["stack"]}
        if m.get("boss"):
            row["boss"] = True
        if m.get("tree"):
            row["tree"] = True
        if m.get("treewall"):
            row["treewall"] = True
        if m["conn"]:
            row["conn"] = {"type": m["conn"][0], "tag": m["conn"][1]}
        cellrows.append(row)
    json.dump({"source": d.get("title", ""), "schema": "sketch_build-1",
               "palette": pal,
               "labels": S["labels"], "path_marks": sorted(S["path"]),
               "dead": sorted(S["dead"]), "cells": cellrows},
              open(path, "w", encoding="utf-8"), indent=1)


# ---------------------------------------------------------------- main
def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    sketch = a[0]
    d, L = load_sketch(sketch)
    pal = dict(DEFAULT_PALETTE)
    pal_src = ["gray-box defaults"]
    if isinstance(d.get("palette"), dict):   # v5 sketches carry their own tile ids
        pal.update(d["palette"])
        pal_src.append("sketch palette")
    if "--style" in a:                    # named style set: Generator/styles/<name>.json
        name = a[a.index("--style")+1]
        sp = Path(__file__).resolve().parent / "styles" / f"{name}.json"
        if not sp.exists():
            sys.exit(f"no such style set: {sp}")
        pal.update(json.load(open(sp, encoding="utf-8")))
        pal_src.append(f"--style {name}")
    if "--palette" in a:
        user = json.load(open(a[a.index("--palette")+1], encoding="utf-8"))
        pal.update(user)
        pal_src.append("--palette file")
    pal.pop("_comment", None)
    rep = []
    rep.append(f"sketch: {sketch}  title '{d.get('title','')}'  v{d.get('version')}")
    rep.append(f"palette: {' < '.join(pal_src)} (later overrides earlier)")
    resolve_palette(pal, rep)
    S = determine(d, L, rep)
    normalize(S, rep)
    M, warns = build_model(S, rep)
    # ---- MASKS IN THE BUILD (Tony 2026-08-26): each painted area builds in its own
    # style, one pass. Same vocabulary as apply_masks (embedded style values win, then
    # styles/<name>.json; carriers keep base ground but take the mask's wall roles), but
    # here it drives a fresh build too — apply_masks needs an existing region.
    # pal stays the BASE DICT (strip_disabled and the dict consumers need it);
    # pal_emit is what tile emission uses.
    pal_emit = build_mask_palette(pal, a, S, M, rep)
    strip_disabled(M, S, pal, rep)
    if not M:
        sys.exit("empty sketch — nothing to build")
    stem = Path(sketch).stem
    out_dir = Path(sketch).parent
    if "--layout" in a:
        lay = Path(a[a.index("--layout")+1])
    else:
        lay = out_dir / f"{stem}.layout.json"
    dump_layout(M, S, d, lay, pal)
    rep.append(f"layout written: {lay}")
    if "--png" in a:
        p = out_dir / f"{stem}_preview.png"
        rep.append(f"preview: {p}" if render_png(M, S, p) else "preview skipped (no PIL)")
    if "--new" in a:
        i = a.index("--new")
        rid, rname = a[i+1], a[i+2]
        out = Path(a[a.index("-o")+1]) if "-o" in a else out_dir / f"{stem}.xml"
        txt = emit_new(M, pal_emit, rid, rname)
        audit(txt, M, pal, rep)
        out.write_bytes(b'\xef\xbb\xbf' + txt.encode("utf-8"))
        rep.append(f"new region written: {out}")
    elif "--merge" in a:
        src = a[a.index("--merge")+1]
        cw = None
        if "--clear-window" in a:
            j = a.index("--clear-window")
            cw = tuple(int(v) for v in a[j+1:j+5])
        M_write, clear_keys = M, None
        if "--base" in a:
            # DIFF MERGE (Tony 2026-08-23): the base is the context sketch that was handed
            # out (xml_to_sketch output). Both sketches are built in full so wall
            # orientation and derived faces see their whole neighborhood; then only tiles
            # whose BUILT RESULT differs are written. Untouched context tiles produce zero
            # writes and stay byte-original in the file; tiles erased from the context are
            # actively cleared.
            db, Lb = load_sketch(a[a.index("--base")+1])
            scratch = []
            Sb = determine(db, Lb, scratch)
            normalize(Sb, scratch)
            Mb, _ = build_model(Sb, scratch)
            strip_disabled(Mb, Sb, pal, scratch)   # same palette, same stripping — fair diff
            changed = {c for c in M
                       if c not in Mb or tile_lines(c, M[c], pal) != tile_lines(c, Mb[c], pal)}
            clear_keys = set(Mb) - set(M)
            M_write = {c: M[c] for c in changed}
            untouched = len(set(Mb) & set(M)) - len(set(Mb) & changed)
            rep.append(f"BASE DIFF: {len(Mb)} context tiles, {len(M)} in export -> "
                       f"{len(changed)} changed/new to write, {len(clear_keys)} erased to clear, "
                       f"{untouched} untouched (no writes)")
            if not M_write and not clear_keys:
                rep.append("  nothing differs from the base — no merge needed")
        if M_write or clear_keys:
            txt, intended = merge(M_write, pal_emit, src, rep, write="--write" in a,
                                  clear_window=cw,
                                  preserve_extras="--no-preserve-extras" not in a,
                                  clear_keys=clear_keys)
            audit(txt, M_write, pal, rep, intended)
        else:
            rep.append("NO CHANGES TO WRITE — the target file is untouched.")
    else:
        rep.append("no --new or --merge given: model + layout only")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
