#!/usr/bin/env python3
"""xml_to_sketch.py — WorldForge region XML (whole or a window) -> LOK Sketcher JSON (v4).

The reverse leg of the pipeline: pull an existing map or a section of it back into the
sketcher so Tony can modify it, then push it through sketch_build.py again.

Mapping (lossy BY DESIGN — the sketch is a logical drawing, not the file):
  WallComponent 446/447 (or --structural-ids)  -> structural
  any other WallComponent / corner             -> wall
  DoorComponent                                -> door
  StaircaseComponent teleporterId 127 / 123    -> stairs_up / stairs_down
    (any other teleporterId -> stairs_up with the id as the link tag, and a report line)
  EgressComponent                              -> portal (egress != 318 kept as the tag)
  WaterComponent                               -> water
  FloorComponent ground 13 -> grass · 12 -> dirt · 2 -> floor + SPAWN connector ·
    5 -> floor + boss mark · else -> floor
    (Tony 2026-08-23: ground 2 has always been his spawn-in marker; 5 is the boss tile)
  empty tiles / tiles outside the window       -> blank canvas

EVERYTHING ELSE (statics, trees, obstructions, lockers, ruins…) CANNOT ride in a sketch.
The report lists how many tiles carry such components. sketch_build.py --merge preserves
them by default when it replaces a tile, so a round trip does NOT wipe decoration.

Usage:
  python3 xml_to_sketch.py <region.xml> [--window x0 y0 x1 y1] [--title "..."] [-o out.json]
"""
import json, sys
from pathlib import Path
from xml.etree import ElementTree as ET

STRUCTURAL_IDS = {446, 447}
GROUND_MAP = {13: "grass", 12: "dirt"}   # 2 (spawn) and 5 (boss) handled specially


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    src = Path(a[0])
    win = None
    if "--window" in a:
        i = a.index("--window")
        win = tuple(int(v) for v in a[i+1:i+5])
    sids = set(STRUCTURAL_IDS)
    if "--structural-ids" in a:
        sids |= {int(v) for v in a[a.index("--structural-ids")+1].split(",")}
    root = ET.fromstring(src.read_bytes())
    rname = (root.findtext("name") or src.stem).strip()
    # first pass: where the structural masses are (to recognize DERIVED face walls)
    struct_at = set()
    for t in root.iter("tile"):
        for c in t.findall("component"):
            if c.get("type") == "WallComponent":
                w = c.findtext("wall")
                if w and int(w) in sids:
                    struct_at.add((int(t.get("x")), int(t.get("y"))))
    title = a[a.index("--title")+1] if "--title" in a else (
        rname + (f" {win[0]},{win[1]} to {win[2]},{win[3]}" if win else ""))

    layers = {k: [] for k in ("wall", "structural", "door", "floor", "grass",
                              "water", "deepwater", "dirt", "dead", "boss", "path",
                              "tree", "treewall",
                              "spawn", "portal", "stairs_up", "stairs_down")}
    ground_hist, wall_hist, odd_stairs, extras_tiles = {}, {}, [], 0
    tree_hist, spec_obst = {}, {}
    n_tiles = 0
    dropped_faces = [0]
    for t in root.iter("tile"):
        x, y = int(t.get("x")), int(t.get("y"))
        if win and not (win[0] <= x <= win[2] and win[1] <= y <= win[3]):
            continue
        n_tiles += 1
        ground, is_water, walls, door = None, False, [], False
        stair, egress, extra = None, None, False
        t_ids, obst = [], []
        for c in t.findall("component"):
            ty = c.get("type")
            if ty == "FloorComponent":
                g = c.findtext("ground")
                ground = int(g) if g else None
            elif ty == "WaterComponent":
                is_water = True
            elif ty == "WallComponent":
                w = c.findtext("wall")
                if w:
                    walls.append(int(w))
            elif ty == "DoorComponent":
                door = True
            elif ty == "StaircaseComponent":
                tid = c.findtext("teleporterId")
                stair = int(tid) if tid else None
            elif ty == "EgressComponent":
                e = c.findtext("egress")
                egress = int(e) if e else None
            elif ty == "TreeComponent":
                tid = c.findtext("tree")
                t_ids.append(int(tid) if tid else 0)
            elif ty == "ObstructionComponent":
                o = c.findtext("obstruction")
                obst.append(int(o) if o else 0)
            else:
                extra = True
        spec = [o for o in obst if o not in (19, 266)]
        for o in spec:
            spec_obst[o] = spec_obst.get(o, 0) + 1
        if extra or spec:
            extras_tiles += 1
        # terrain layer
        if walls:
            for w in walls:
                wall_hist[w] = wall_hist.get(w, 0) + 1
            layer = "structural" if any(w in sids for w in walls) else "wall"
            # DERIVED face walls: a non-structural walled tile whose S or E neighbor is a
            # structural mass is a face sketch_build regenerates — recover the GROUND, not
            # a drawn wall (the inverse of face completeness). Floorless faces vanish.
            # The SE-diagonal check covers the NW exterior corner cap (derived 2026-08-23).
            adj = ((x, y+1) in struct_at) + ((x+1, y) in struct_at) \
                + ((x+1, y+1) in struct_at)
            if layer == "wall" and adj and len(walls) <= adj:
                dropped_faces[0] += 1
                if ground is None and not is_water:
                    continue
                layer = None
            if layer:
                layers[layer].append([x, y])
                if door:                  # door stacked with walls: door wins the tile
                    layers[layer].pop()
                    layers["door"].append([x, y])
                ground = None             # ground under a drawn wall isn't representable
                is_water = False
        elif door:
            layers["door"].append([x, y])
            ground, is_water = None, False
        if 266 in obst:                   # Heavy Oak blocker -> tree wall mark (overlay)
            layers["treewall"].append([x, y])
        if t_ids:                         # walkable tree(s) -> tree mark (overlay)
            layers["tree"].append([x, y])
            for tid in t_ids:
                tree_hist[tid] = tree_hist.get(tid, 0) + 1
        if is_water:
            layers["deepwater" if 19 in obst else "water"].append([x, y])
        elif ground is not None:
            ground_hist[ground] = ground_hist.get(ground, 0) + 1
            if ground == 2:
                layers["floor"].append([x, y])
                layers["spawn"].append([x, y, ""])
            elif ground == 5:
                layers["floor"].append([x, y])
                layers["boss"].append([x, y])
            else:
                layers[GROUND_MAP.get(ground, "floor")].append([x, y])
        # connectors ride on top of whatever terrain
        if stair is not None:
            if stair == 127:
                layers["stairs_up"].append([x, y, ""])
            elif stair == 123:
                layers["stairs_down"].append([x, y, ""])
            else:
                layers["stairs_up"].append([x, y, str(stair)])
                odd_stairs.append((x, y, stair))
        if egress is not None:
            layers["portal"].append([x, y, "" if egress == 318 else str(egress)])

    layers = {k: v for k, v in layers.items() if v}
    all_pts = [p[:2] for v in layers.values() for p in v]
    if not all_pts:
        sys.exit("nothing representable found in that window")
    xs = [p[0] for p in all_pts]; ys = [p[1] for p in all_pts]
    x0, y0 = (win[0], win[1]) if win else (min(xs) - 2, min(ys) - 2)
    x1, y1 = (win[2], win[3]) if win else (max(xs) + 2, max(ys) + 2)
    rid = root.findtext("id")
    out = {"app": "lok-sketcher", "version": 4, "title": title,
           "region": (int(rid) if rid and rid.strip().lstrip("-").isdigit() else None),
           "width": x1 - x0 + 1, "height": y1 - y0 + 1, "x0": x0, "y0": y0,
           "layers": layers, "labels": []}
    dest = Path(a[a.index("-o")+1]) if "-o" in a else src.with_name(
        src.stem + ("_win" if win else "") + "_sketch.json")
    json.dump(out, open(dest, "w", encoding="utf-8"))
    print(f"read {n_tiles} tiles from {src.name}" + (f" window {win}" if win else ""))
    print("layers:", {k: len(v) for k, v in layers.items()})
    print("ground histogram:", dict(sorted(ground_hist.items())))
    print("wall histogram:", dict(sorted(wall_hist.items())),
          f"(structural ids: {sorted(sids)})")
    if dropped_faces[0]:
        print(f"derived face walls dropped (regenerated on rebuild): {dropped_faces[0]}")
    if tree_hist:
        print("tree id histogram (all become the generic tree mark; the style set picks the species):",
              dict(sorted(tree_hist.items())))
    if spec_obst:
        print("⚠ specialty obstructions (not sketch-representable, preserved only if the tile isn't rebuilt):",
              dict(sorted(spec_obst.items())))
    if odd_stairs:
        print("⚠ staircases with non-captured teleporterIds (kept as link tags):", odd_stairs)
    if extras_tiles:
        print(f"⚠ {extras_tiles} tiles carry components a sketch can't hold (statics/trees/etc.).")
        print("  sketch_build.py --merge preserves them by default when those tiles are replaced.")
    print("written:", dest)


if __name__ == "__main__":
    main()
