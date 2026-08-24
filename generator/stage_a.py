#!/usr/bin/env python3
"""Stage A — WorldForge dungeon layout generator (typed grid -> sketch PNG / layout.json / gray-box XML).

Rules source: GENERATOR_HANDOFF.md + eldrathor-maps skill, verified tile-by-tile against
Regions/1.xml ("Wall with structural") and Regions/2.xml ("Wall as room divider").

Roles only — no real terrain IDs. Gray-box palette (Stage A placeholder) at bottom.
Known canon deviations (intentional):
  - region 1 (11,8): duplicate wall 29 in canon is a defect; generator emits one.
  - region 1 (14,4): canon carries an extra 30 (order 30,447,29). Confirmed a hand-editing
    artifact 2026-08-22 — Tony removed the same pattern from the assembly build — so the
    generator emits 447,29 there (no face-col wall on north block-row crossings).
"""
from __future__ import annotations
import json
from xml.etree import ElementTree as ET

FLOOR_V, FLOOR_H, FLOOR_E = "V", "H", "E"  # visible / hidden / exterior-face
EMIT_ORDER = ["door-ns", "door-ew", "structural", "wall-ns", "wall-ew", "corner"]

GRAYBOX = {
    "floor": {"V": 1, "H": 12, "E": 12},
    "wall-ns": (29, 42, 46),
    "wall-ew": (30, 43, 46),
    "corner": (34, 144, 46),
    "structural": (447, 0, 44),          # + indestructible
    "door-ns": (78, 66, 151, 84),        # openId, closedId, secretId, destroyedId
    "door-ew": (79, 67, 152, 85),        # E/W door family (Tony, region 5) — one higher each
}


class Layout:
    def __init__(self, name):
        self.name = name
        self.cells = {}  # (x,y) -> {"floor": F, "stack": [role,...]}
        self.pending = []  # (x, y, role) ends-rule extensions, applied late in finalize
                           # so they append AFTER face walls (canon junction order)

    def cell(self, x, y, floor=None):
        c = self.cells.get((x, y))
        if c is None:
            c = {"floor": floor or FLOOR_H, "stack": []}
            self.cells[(x, y)] = c
        elif floor is not None:
            c["floor"] = floor
        return c

    def add(self, x, y, role, floor_default=FLOOR_H):
        c = self.cells.get((x, y))
        if c is None:
            c = self.cell(x, y, floor_default)
        if role not in c["stack"]:
            c["stack"].append(role)

    def put(self, x, y, floor, stack):
        c = self.cell(x, y, floor)
        c["stack"] = list(stack)

    def bbox(self):
        xs = [x for x, _ in self.cells]
        ys = [y for _, y in self.cells]
        return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- primitives

def structural_room(L, ix0, iy0, ix1, iy1, north_doors=()):
    """Thick style, region-1 canon. Interior WxH -> (W+4)x(H+4) footprint."""
    fx0, fy0, fx1, fy1 = ix0 - 2, iy0 - 2, ix1 + 2, iy1 + 2
    # exterior NW corner + exterior face strips (floors belong to surrounding terrain)
    L.put(fx0, fy0, FLOOR_E, ["corner"])
    for y in range(fy0 + 1, fy1 + 1):
        L.put(fx0, y, FLOOR_E, ["wall-ew"])
    for x in range(fx0 + 1, fx1 + 1):
        L.put(x, fy0, FLOOR_E, ["wall-ns"])
    # block ring
    ring = set()
    for x in range(fx0 + 1, fx1 + 1):
        ring.add((x, fy0 + 1)); ring.add((x, fy1))
    for y in range(fy0 + 1, fy1 + 1):
        ring.add((fx0 + 1, y)); ring.add((fx1, y))
    for (x, y) in ring:
        L.put(x, y, FLOOR_H, ["structural"])
    # interior face row (north faces of south block row) — spans fx0+2..fx1-1
    # (stamped BEFORE the face col so crossings emit ns,ew like canon (14,8))
    for x in range(fx0 + 2, fx1):
        L.add(x, fy1 - 1, "wall-ns")
    # interior face col (west faces of east block col) — spans fy0+2..fy1-1. It does NOT
    # put its EW wall on the north block-row crossing: canon region 1 (14,4)'s extra 30
    # is a hand-editing artifact — Tony removed the same pattern in the assembly (2026-08-22).
    for y in range(fy0 + 2, fy1):
        L.add(fx1 - 1, y, "wall-ew")
    # interior
    for x in range(ix0, ix1 + 1):
        for y in range(iy0, iy1 + 1):
            L.put(x, y, FLOOR_V, [])
    # recessed doors on the north face row
    for dx in north_doors:
        L.put(dx, fy0, FLOOR_V, ["door-ns", "corner"])       # door + corner cap, seen floor
        L.put(dx, fy0 + 1, FLOOR_V, [])                       # open entry
        L.put(dx + 1, fy0 + 1, FLOOR_V, ["wall-ew"])          # entry's east wall (sanctioned exception)


def divider_room(L, ix0, iy0, ix1, iy1, north_doors=()):
    """Thin style, region-2 canon. Interior WxH -> (W+2)x(H+2) footprint."""
    fx0, fy0, fx1, fy1 = ix0 - 1, iy0 - 1, ix1 + 1, iy1 + 1
    L.put(fx0, fy0, FLOOR_H, ["corner"])                      # NW
    for x in range(fx0 + 1, fx1 + 1):                          # north run incl NE
        L.put(x, fy0, FLOOR_H, ["wall-ns"])
    for y in range(fy0 + 1, fy1):                              # west + east runs
        L.put(fx0, y, FLOOR_H, ["wall-ew"])
        L.put(fx1, y, FLOOR_H, ["wall-ew"])
    L.put(fx0, fy1, FLOOR_H, ["wall-ew"])                      # SW: west run claims it (canon (10,7)=30)
    for x in range(fx0 + 1, fx1 + 1):                          # south run; SE stacks both
        L.put(x, fy1, FLOOR_H, ["wall-ns"])
    L.add(fx1, fy1, "wall-ew")                                 # SE stack (canon (14,7)=29+30)
    for x in range(ix0, ix1 + 1):
        for y in range(iy0, iy1 + 1):
            L.put(x, y, FLOOR_V, [])
    for dx in north_doors:
        L.put(dx, fy0, FLOOR_V, ["door-ns"])                   # door replaces wall, no cap


# -------------------------------------------------- general shell engine

def generate_shell(L, vis, exterior_floor=FLOOR_E):
    """Deterministic structural shell around an ARBITRARY visible footprint (polyomino).
    Partition-first principle: structural only on the exterior. Classification derived
    from regions 1-6 canon (reproduces Tony's region-3 continuity fixes exactly):
      F     face tile: non-visible cell with visible directly N, directly W, or NW-diagonal.
            An F "crossing" (NW-diag visible, N and W not) carries both walls (canon (14,8)).
      BLOCK any other cell reachable from a visible cell at offset dx,dy both in [-1..+2].
      TRIM  remaining cells within chebyshev-2 (exterior face strips on the N/W sides).
    All face walls arrive via the finalize() completeness passes."""
    V = set(vis)
    for (x, y) in V:
        L.put(x, y, FLOOR_V, [])
    cand = {}
    for (x, y) in V:
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                c = (x + dx, y + dy)
                if c not in V:
                    cand.setdefault(c, set()).add((dx, dy))
    for (cx, cy), offs in sorted(cand.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        n, w, nw = (cx, cy - 1) in V, (cx - 1, cy) in V, (cx - 1, cy - 1) in V
        if n or w or nw:
            stack = []
            if nw and not n and not w:          # face crossing: both runs continue through
                stack = ["wall-ns", "wall-ew"]
            L.put(cx, cy, FLOOR_H, stack)
        elif any(-1 <= dx <= 2 and -1 <= dy <= 2 for dx, dy in offs):
            L.put(cx, cy, FLOOR_H, ["structural"])
        else:
            L.put(cx, cy, exterior_floor, [])


def partition_h(L, x0, x1, y, doors=()):
    """Horizontal partition wall x0..x1 at row y (inside visible floor). ENDS RULE:
    east end extends one tile (stacking after whatever wall is there); west end clean."""
    for x in range(x0, x1 + 1):
        if x in doors:
            L.put(x, y, FLOOR_V, ["door-ns"])
        else:
            L.put(x, y, FLOOR_H, ["wall-ns"])
    L.pending.append((x1 + 1, y, "wall-ns"))


def partition_v(L, x, y0, y1, doors=()):
    """Vertical partition wall y0..y1 at col x. ENDS RULE: south end extends; north clean."""
    for y in range(y0, y1 + 1):
        if y in doors:
            L.put(x, y, FLOOR_V, ["door-ew"])
        else:
            L.put(x, y, FLOOR_H, ["wall-ew"])
    L.pending.append((x, y1 + 1, "wall-ew"))


# shell door patterns as captured from Tony's corrections (region 1 north; region 5 S/E/W)
def shell_door_north(L, x, y):
    """y = the trim/face row two above the interior. Door + cap; recess gaps below."""
    L.put(x, y, FLOOR_V, ["door-ns", "corner"])
    L.put(x, y + 1, FLOOR_V, [])
    L.put(x + 1, y + 1, FLOOR_V, ["wall-ew"])
    L.add(x + 1, y, "wall-ns")   # face row continues over the gap column (canon (13,3))


def shell_door_south(L, x, y):
    """y = the face row one below the interior; door goes in the block row below it."""
    L.put(x, y, FLOOR_V, [])
    L.put(x, y + 1, FLOOR_V, ["door-ns"])
    L.put(x + 1, y, FLOOR_H, ["corner"])
    L.put(x + 1, y + 1, FLOOR_V, ["wall-ew", "wall-ns"])


def shell_door_east(L, x, y):
    """x = the face col one east of the interior; door goes in the block col east of it."""
    L.put(x, y, FLOOR_V, [])
    L.put(x + 1, y, FLOOR_V, ["door-ew"])
    L.put(x, y + 1, FLOOR_H, ["corner"])
    L.put(x + 1, y + 1, FLOOR_V, ["wall-ns", "wall-ew"])


def shell_door_west(L, x, y):
    """x = the trim col two west of the interior. Door replaces the west-face wall."""
    L.put(x, y, FLOOR_V, ["door-ew"])
    L.put(x + 1, y, FLOOR_V, [])
    L.put(x + 1, y + 1, FLOOR_V, ["wall-ns"])
    # the pierced face-col run continues below the door (Tony's region-5 fix at (0,18))
    L.pending.append((x, y + 1, "wall-ew"))


# ---------------------------------------------------------------- finalize

def finalize(L):
    """Block face walls + corners by adjacency, then corner demotion. Run once, after all stamps."""
    blocks = {p for p, c in L.cells.items() if "structural" in c["stack"]}
    for (x, y) in blocks:
        if (x, y + 1) not in blocks:      # south face on same tile (ns before ew, canon (15,9))
            L.add(x, y, "wall-ns")
        if (x + 1, y) not in blocks:      # east face on same tile
            L.add(x, y, "wall-ew")
    # face completeness (Tony, regions 4/5): every block's north neighbor (if not a block)
    # carries the block's north face (NS wall); every west neighbor carries its west face
    # (EW wall). If the neighbor tile doesn't exist, create it FLOORLESS — wall over void
    # (canon: Tony's (8,10) in region 4: WallComponent only, no FloorComponent).
    for (x, y) in blocks:
        if (x, y - 1) not in blocks:
            n = L.cells.get((x, y - 1))
            if n is None:
                L.cells[(x, y - 1)] = {"floor": None, "stack": ["wall-ns"]}
            elif "wall-ns" not in n["stack"] and not any(r.startswith("door") for r in n["stack"]):
                n["stack"].append("wall-ns")
        if (x - 1, y) not in blocks:
            w = L.cells.get((x - 1, y))
            if w is None:
                L.cells[(x - 1, y)] = {"floor": None, "stack": ["wall-ew"]}
            elif "wall-ew" not in w["stack"] and not any(r.startswith("door") for r in w["stack"]):
                w["stack"].append("wall-ew")
    for (x, y) in blocks:                 # corner predicate (canon (10,4))
        s = L.cells.get((x, y + 1))
        e = L.cells.get((x + 1, y))
        if s and "wall-ew" in s["stack"] and e and "wall-ns" in e["stack"]:
            L.add(x, y, "corner")
    # exterior-trim NW corner: an empty non-visible cell whose S neighbor carries an EW
    # wall and E neighbor an NS wall gets the corner piece (canon region 1 (9,3))
    for (x, y), c in L.cells.items():
        if c["stack"] or c["floor"] in (FLOOR_V, None):
            continue
        s = L.cells.get((x, y + 1))
        e = L.cells.get((x + 1, y))
        if s and "wall-ew" in s["stack"] and e and "wall-ns" in e["stack"]:
            c["stack"].append("corner")
    # ends-rule extensions, applied AFTER completeness so they stack behind existing walls
    for (x, y, role) in L.pending:
        L.add(x, y, role)
    # vertical face-run continuity (Tony, region 3 fix at (14,2)): a face-row tile with an
    # EW wall on the non-block tile directly north and a block directly south carries the
    # EW wall too, so the vertical run doesn't visually break at the crossing
    for (x, y), c in list(L.cells.items()):
        if "wall-ns" in c["stack"] and "structural" not in c["stack"]:
            n = L.cells.get((x, y - 1))
            s = L.cells.get((x, y + 1))
            nw = L.cells.get((x - 1, y - 1))
            # the EW wall above must be a room/corridor's east wall — plain open floor
            # sits directly WEST of it (true for canon (14,2); false for Tony's (12,7)
            # region-5 removal, where it was just the side facade of an unrelated mass)
            east_wall_of_open = (nw is not None and nw["floor"] == FLOOR_V and not nw["stack"])
            if (n and "wall-ew" in n["stack"] and "structural" not in n["stack"]
                    and east_wall_of_open and s and "structural" in s["stack"]):
                if "wall-ew" not in c["stack"]:
                    c["stack"].append("wall-ew")
    # demote a non-block corner whose column continues north (strip extended past it)
    for (x, y), c in L.cells.items():
        if "corner" in c["stack"] and "structural" not in c["stack"]:
            n = L.cells.get((x, y - 1))
            if n and "wall-ew" in n["stack"]:
                c["stack"].remove("corner")
                if "wall-ew" not in c["stack"]:
                    c["stack"].append("wall-ew")
    # seen floor under walls beside open floor (Tony, regions 4/5): walls lean up-left, so
    # a NS-walled face tile shows its floor beside PLAIN open floor to its EAST, and an
    # EW-walled face tile beside plain open floor to its SOUTH. Those floors are SEEN floor.
    def _plain(p):
        n = L.cells.get(p)
        return n is not None and n["floor"] == FLOOR_V and not n["stack"]
    for (x, y), c in L.cells.items():
        if c["floor"] is None or "structural" in c["stack"] or "corner" in c["stack"]:
            continue
        if not c["stack"] or any(r.startswith("door") for r in c["stack"]):
            continue
        if ("wall-ns" in c["stack"] and _plain((x + 1, y))) or \
           ("wall-ew" in c["stack"] and _plain((x, y + 1))):
            c["floor"] = FLOOR_V


# ---------------------------------------------------------------- validation

def validate(L, recess_exceptions=()):
    """Coverage rules from the handoff. Returns list of warnings."""
    warns = []
    blocks = {p for p, c in L.cells.items() if "structural" in c["stack"]}
    # "visible" for coverage purposes = plain walkable floor; seen floor UNDER a wall
    # (exposure rule) is part of the wall band, not open floor
    vis = {p for p, c in L.cells.items()
           if c["floor"] == FLOOR_V
           and not any(r.startswith("wall") or r in ("structural", "corner") for r in c["stack"])}
    for (x, y) in blocks:
        for (nx, ny), tag in (((x - 1, y), "W"), ((x - 1, y - 1), "NW")):
            if (nx, ny) in vis and (nx, ny) not in recess_exceptions:
                warns.append(f"coverage-1: visible floor at ({nx},{ny}) is {tag} of block ({x},{y})")
    doors = {p for p, c in L.cells.items() if any(r.startswith("door") for r in c["stack"])}
    for (x, y) in vis:
        if (x, y) in doors or (x, y) in recess_exceptions:
            continue
        for (nx, ny), tag in (((x, y + 1), "S"), ((x + 1, y), "E")):
            n = L.cells.get((nx, ny))
            if n and "structural" in n["stack"]:
                warns.append(f"coverage-2: visible ({x},{y}) directly {tag}-adjacent to block ({nx},{ny})")
    # duplicates can't happen via add(); assert anyway
    for p, c in L.cells.items():
        if len(c["stack"]) != len(set(c["stack"])):
            warns.append(f"duplicate component at {p}")
    return warns


# ---------------------------------------------------------------- emitters

def emit_xml(L, region_id, region_name):
    x0, y0, x1, y1 = L.bbox()
    ln = []
    ln.append('<?xml version="1.0" encoding="utf-8"?>')
    ln.append('<region>')
    ln.append(f'  <id>{region_id}</id>')
    ln.append(f'  <name>{region_name}</name>')
    ln.append('  <height>0</height>')
    ln.append(f'  <bounds left="{x0}" top="{y0}" right="{x1 + 1}" bottom="{y1 + 1}" />')
    for (x, y) in sorted(L.cells, key=lambda p: (p[1], p[0])):
        c = L.cells[(x, y)]
        ln.append(f'  <tile x="{x}" y="{y}">')
        if c["floor"] is not None:      # floorless tiles: wall over void (Tony, region 4 (8,10))
            ln.append('    <component type="FloorComponent">')
            ln.append(f'      <ground>{GRAYBOX["floor"][c["floor"]]}</ground>')
            ln.append('    </component>')
        # insertion order, NOT sorted: canon keeps the pre-existing wall first and appends
        # extensions/stacks after it (Tony's junction fixes (6,-2)=29,30 vs (13,5)=30,29)
        for role in c["stack"]:
            if role.startswith("door"):
                o, cl, se, de = GRAYBOX[role]
                ln.append('    <component type="DoorComponent">')
                ln.append(f'      <openId>{o}</openId>')
                ln.append(f'      <closedId>{cl}</closedId>')
                ln.append(f'      <secretId>{se}</secretId>')
                ln.append(f'      <destroyedId>{de}</destroyedId>')
                ln.append('    </component>')
            elif role == "structural":
                w, d, r = GRAYBOX["structural"]
                ln.append('    <component type="WallComponent">')
                ln.append(f'      <wall>{w}</wall>')
                ln.append(f'      <destroyed>{d}</destroyed>')
                ln.append(f'      <ruins>{r}</ruins>')
                ln.append('      <indestructible>true</indestructible>')
                ln.append('    </component>')
            else:
                w, d, r = GRAYBOX[role]
                ln.append('    <component type="WallComponent">')
                ln.append(f'      <wall>{w}</wall>')
                ln.append(f'      <destroyed>{d}</destroyed>')
                ln.append(f'      <ruins>{r}</ruins>')
                ln.append('    </component>')
        ln.append('  </tile>')
    ln.append('</region>')
    return '\ufeff' + '\r\n'.join(ln)


def emit_layout_json(L, note=""):
    cells = []
    for (x, y) in sorted(L.cells, key=lambda p: (p[1], p[0])):
        c = L.cells[(x, y)]
        cells.append({"x": x, "y": y, "floor": c["floor"],
                      "stack": list(c["stack"]), "set": "main"})
    return json.dumps({
        "name": L.name, "schema": 1, "note": note,
        "roles": {"floor": {"V": "floor-visible", "H": "floor-hidden", "E": "floor-exterior"},
                  "stack": ["door-ns", "door-ew", "structural", "wall-ns", "wall-ew", "corner"]},
        "wall_sets": ["main"],
        "cells": cells,
    }, indent=2)


def render_sketch(L, path, title, doors_red=True):
    from PIL import Image, ImageDraw, ImageFont
    x0, y0, x1, y1 = L.bbox()
    cs = 42
    mx, my = 64, 76
    W = mx + (x1 - x0 + 1) * cs + 20
    H = my + (y1 - y0 + 1) * cs + 20
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
        ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    except OSError:
        f = ft = ImageFont.load_default()
    C_V, C_H, C_D, C_LINE = (233, 229, 216), (104, 90, 74), (200, 32, 32), (58, 50, 41)
    for (x, y), c in L.cells.items():
        px = mx + (x - x0) * cs
        py = my + (y - y0) * cs
        col = C_H
        if any(r.startswith("door") for r in c["stack"]) and doors_red:
            col = C_D
        elif c["floor"] == FLOOR_V and not c["stack"]:
            col = C_V
        elif c["floor"] == FLOOR_V:
            col = C_V   # seen floor carrying a wall still renders light (legend: light = seen floor)
        d.rectangle([px, py, px + cs, py + cs], fill=col, outline=C_LINE)
    for x in range(x0, x1 + 1):
        d.text((mx + (x - x0) * cs + cs // 2, my - 24), str(x), fill=(255, 255, 255), font=f, anchor="mm")
    for y in range(y0, y1 + 1):
        d.text((mx - 30, my + (y - y0) * cs + cs // 2), str(y), fill=(255, 255, 255), font=f, anchor="mm")
    d.text((mx, 12), title, fill=(255, 255, 255), font=ft)
    img.save(path)


# ---------------------------------------------------------------- selftest

def _signature(xml_bytes):
    root = ET.fromstring(xml_bytes)
    tiles = {}
    for t in root.iter("tile"):
        key = (int(t.get("x")), int(t.get("y")))
        comps = []
        for comp in t.findall("component"):
            comps.append((comp.get("type"), tuple((ch.tag, (ch.text or "").strip()) for ch in comp)))
        tiles[key] = comps
    return tiles


def selftest(regions_dir):
    from pathlib import Path
    results = []

    L1 = Layout("region1-repro")
    structural_room(L1, 11, 5, 13, 7, north_doors=[12])
    finalize(L1)
    mine = _signature(emit_xml(L1, 1, "Wall with structural").encode("utf-8"))
    canon = _signature(Path(regions_dir, "1.xml").read_bytes())
    diffs = _diff(canon, mine)
    results.append(("region 1 (structural)", diffs))

    L2 = Layout("region2-repro")
    divider_room(L2, 11, 4, 13, 6, north_doors=[12])
    finalize(L2)
    mine2 = _signature(emit_xml(L2, 2, "Wall as room divider").encode("utf-8"))
    canon2 = _signature(Path(regions_dir, "2.xml").read_bytes())
    results.append(("region 2 (divider)", _diff(canon2, mine2)))
    return results


def _diff(canon, mine):
    diffs = []
    for k in sorted(set(canon) | set(mine), key=lambda p: (p[1], p[0])):
        a, b = canon.get(k), mine.get(k)
        if a != b:
            diffs.append((k, a, b))
    return diffs


if __name__ == "__main__":
    import sys
    for label, diffs in selftest(sys.argv[1] if len(sys.argv) > 1 else "../Regions"):
        print(f"== {label}: {len(diffs)} differing tiles")
        for k, a, b in diffs:
            print(f"  {k}:")
            fmt = lambda comps: [c[0] + ':' + dict(c[1]).get('wall', dict(c[1]).get('ground', dict(c[1]).get('openId', '?'))) for c in comps] if comps else None
            print(f"    canon: {fmt(a)}")
            print(f"    mine : {fmt(b)}")
