#!/usr/bin/env python3
"""Round-trip regression for the wall placement engine.

Every fixture is a real WorldForge region: the game developers' own maps (tests/fixtures/dev)
and Tony's hand-corrected teaching regions (tests/fixtures/tony). Each one is imported with
xml_to_sketch, rebuilt with sketch_build using the region's own ids, and the rebuild is
compared tile by tile on ROLE CLASSES (H / V / C wall pieces, door H/V, mass), never on ids.
Agreement is printed per fixture and compared with tests/baseline.json.

  python3 tests/run_regression.py            # run, compare with baseline, exit 1 on a drop
  python3 tests/run_regression.py --update   # run and rewrite the baseline (after Tony approves)
  python3 tests/run_regression.py --only r9  # fixtures whose name contains "r9"
  python3 tests/run_regression.py --dump     # also write diff.json (one entry per differing tile)

A fixture's score is the share of tiles (that carry a wall, door or mass in either file) whose
role set is identical. Tiles that only differ on floors or decoration are not counted here;
the importer is lossy on those by design.
"""
import json, re, subprocess, sys, collections
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
import os
GEN = Path(os.environ.get("LOK_GEN", HERE.parent / "generator"))
OUT = HERE / "_out"
_WO = json.load(open(GEN / "wall_orient.json", encoding="utf-8"))
ORIENT = {int(k): v for k, v in _WO["orient"].items()}
DOOR_ORIENT = {int(k): v for k, v in _WO.get("doors", {}).items()}
COMP = json.load(open(GEN / "companions.json", encoding="utf-8"))

# fixture -> mass ids, wall ids (H, V, C), door closed ids (H, V), mass style, floor ground
FIXTURES = {
    # developers' regions: Solid Rock / Granite is bare fill, every wall is drawn
    "dev/prae1_temple":        dict(mass=[31, 447], walls=(258, 259, 262),   doors=(311, 312), style="bare", floor=265),
    "dev/prae3_hellsgate":     dict(mass=[31, 447], walls=(346, 347, 359),   doors=(62, 63),   style="bare", floor=265),
    "dev/prae251_lowerUW":     dict(mass=[31, 447], walls=(346, 347, 359),   doors=(62, 63),   style="bare", floor=12),
    "dev/bb1_mineentrance":    dict(mass=[31, 447], walls=(29, 30, 34),      doors=(62, 63),   style="bare", floor=12),
    "dev/bb6_thieflair":       dict(mass=[31, 447], walls=(29, 30, 34),      doors=(62, 63),   style="bare", floor=179),
    "dev/uk2_lowerkobold":     dict(mass=[31, 447], walls=(29, 30, 34),      doors=(62, 63),   style="bare", floor=12),
    "dev/uk11_lightningcaves": dict(mass=[31, 447], walls=(29, 30, 34),      doors=(62, 63),   style="bare", floor=12),
    "dev/uk16_yasnaki":        dict(mass=[31, 447], walls=(29, 30, 34),      doors=(62, 63),   style="bare", floor=12),
    "dev/ag18_chaostown":      dict(mass=[31, 447], walls=(29, 30, 34),      doors=(62, 63),   style="bare", floor=12),
    # Tony's canon: Solid Granite 447 with faces ON the block (the default style)
    "tony/r3_cross_five_rooms": dict(mass=[447], walls=(29, 30, 34),       doors=(66, 67),   style="faces", floor=1),
    "tony/r4_lblock":           dict(mass=[447], walls=(29, 30, 34),       doors=(66, 67),   style="faces", floor=1),
    "tony/r5_bossway":          dict(mass=[447], walls=(29, 30, 34),       doors=(66, 67),   style="faces", floor=1),
    "tony/r6_shell_partitions": dict(mass=[447], walls=(29, 30, 34),       doors=(66, 67),   style="faces", floor=1),
    "tony/test2_two_masses":    dict(mass=[447], walls=(1225, 1227, 1231), doors=(66, 67),   style="faces", floor=1),
    "tony/r9_castle_spire":     dict(mass=[447], walls=(1225, 1227, 1231), doors=(62, 63),   style="faces", floor=14),
    # Forge L6: Solid Dirt 446 is bare fill under hand-drawn Dirty Marble runs
    "tony/r7_forge_south_corrections": dict(mass=[446], walls=(139, 140, 143), doors=(66, 67), style="faces", floor=176),
}


def wall_triple(i):
    e = COMP["walls"].get(str(i))
    return [i, e["destroyed"], e["ruins"]] if e else [i, 0, 0]


def door_quad(closed):
    for e in COMP["doors"].values():
        if e.get("closed") == closed:
            return [e.get("open", closed), closed, e.get("secret", 0), e.get("destroyed", 0)]
    return [closed, closed, 0, 0]


def role_map(root, mass):
    """(x,y) -> frozenset of role classes present on that tile."""
    T = {}
    for t in root.findall("tile"):
        s = set()
        for c in t.findall("component"):
            ty = c.get("type")
            if ty == "WallComponent":
                i = int(c.findtext("wall") or 0)
                s.add("M" if i in mass else (ORIENT.get(i) or "P"))      # P = post/pillar/unknown
            elif ty == "DoorComponent":
                i = int(c.findtext("closedId") or 0)
                s.add("d" + (DOOR_ORIENT.get(i) or "?"))
        if s:
            T[(int(t.get("x")), int(t.get("y")))] = frozenset(s)
    return T


def run_one(name, cfg, dump=False):
    src = HERE / "fixtures" / f"{name}.xml"
    out = OUT / name.replace("/", "_")
    out.mkdir(parents=True, exist_ok=True)
    sketch = out / "sketch.json"
    r = subprocess.run([sys.executable, str(GEN / "xml_to_sketch.py"), str(src), "--structural-ids",
                        ",".join(map(str, cfg["mass"])), "--mass-style", cfg["style"], "-o", str(sketch)],
                       capture_output=True, text=True)
    if r.returncode:
        return None, "import failed: " + r.stderr.strip()[-300:]
    h, v, c = cfg["walls"]
    dh, dv = cfg["doors"]
    pal = {"room": cfg["floor"], "hall": cfg["floor"], "floor": cfg["floor"], "structural_floor": cfg["floor"],
           "wall-ns": wall_triple(h), "wall-ew": wall_triple(v), "corner": wall_triple(c),
           "structural": wall_triple(cfg["mass"][0]), "door-ns": door_quad(dh), "door-ew": door_quad(dv),
           "mass_style": cfg["style"]}
    (out / "pal.json").write_text(json.dumps(pal, indent=1), encoding="utf-8")
    r = subprocess.run([sys.executable, str(GEN / "sketch_build.py"), str(sketch), "--new", "99", name,
                        "--palette", str(out / "pal.json"), "--no-normalize", "-o", str(out / "rebuilt.xml")],
                       capture_output=True, text=True)
    if r.returncode:
        return None, "build failed: " + (r.stderr or r.stdout).strip()[-300:]
    mass = set(cfg["mass"])
    A = role_map(ET.parse(src).getroot(), mass)
    B = role_map(ET.parse(out / "rebuilt.xml").getroot(), mass)
    keys = set(A) | set(B)
    same = sum(1 for k in keys if A.get(k) == B.get(k))
    diffs = collections.Counter(("".join(sorted(A.get(k, ()))) or "-", "".join(sorted(B.get(k, ()))) or "-")
                                for k in keys if A.get(k) != B.get(k))
    if dump:
        (out / "diff.json").write_text(json.dumps(
            [{"x": k[0], "y": k[1], "file": sorted(A.get(k, ())), "rebuilt": sorted(B.get(k, ()))}
             for k in sorted(keys, key=lambda p: (p[1], p[0])) if A.get(k) != B.get(k)], indent=0), encoding="utf-8")
    return {"tiles": len(keys), "same": same, "pct": round(100.0 * same / max(1, len(keys)), 2),
            "top": diffs.most_common(4)}, None


def main():
    a = sys.argv[1:]
    only = a[a.index("--only") + 1] if "--only" in a else None
    update, dump = "--update" in a, "--dump" in a
    base_path = HERE / "baseline.json"
    baseline = json.load(open(base_path)) if base_path.exists() else {}
    results, failed = {}, []
    print(f"{'fixture':34} {'tiles':>6} {'same':>6} {'score':>7}  {'base':>7}  top differences (file -> rebuilt)")
    for name, cfg in FIXTURES.items():
        if only and only not in name:
            continue
        res, err = run_one(name, cfg, dump)
        if err:
            print(f"{name:34} ERROR {err}")
            failed.append(name)
            continue
        results[name] = res["pct"]
        base = baseline.get(name)
        flag = ""
        if base is not None and res["pct"] < base - 0.05:
            flag = "  <-- DROPPED"
            failed.append(name)
        print(f"{name:34} {res['tiles']:6} {res['same']:6} {res['pct']:6.2f}%  {('%6.2f%%' % base) if base is not None else '   new '}  "
              + ", ".join(f"{x}->{y} x{n}" for (x, y), n in res["top"]) + flag)
    if update:
        baseline.update(results)
        base_path.write_text(json.dumps(baseline, indent=1, sort_keys=True), encoding="utf-8")
        print("baseline updated:", base_path)
    if failed:
        print("FAILED:", ", ".join(failed))
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
