#!/usr/bin/env python3
"""mine_companions.py — build the companion-id lookup from existing region files.

Tony types ONE number per palette role in the sketcher; the generator fills in the
load-bearing companions (wall destroyed/ruins, door closed/secret/destroyed) from how
that id actually appears in the live maps. This script mines every region XML it is
given (READ ONLY — HaDeZs Test is safe to read, never to write) and majority-votes:

  companions.json = {
    "walls": {"29": {"destroyed": 42, "ruins": 46, "indestructible": false, "seen": 812}, …},
    "doors": {"78": {"closed": 66, "secret": 151, "destroyed": 84, "seen": 40}, …}
  }

Ties/variants are reported. Re-run whenever new maps introduce new wall/door families.

The WorldForge component catalog (.storage/WorldForge/Components.xml) is ingested first
when given via --components: authoritative child sets for every wall/door family, doors
stored under EVERY member id (open/closed/secret/destroyed) so Tony can type whichever
number the ledger showed him. Live-map mining overrides the catalog on conflict.

Usage: python3 mine_companions.py <dir-or-xml> [<dir-or-xml> …]
       [--components <Components.xml>] -o companions.json
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET


def catalog(path):
    """WorldForge Components.xml -> authoritative wall/door child sets."""
    W, D = {}, {}
    root = ET.fromstring(Path(path).read_bytes())
    for c in root.iter("component"):
        ty = c.get("type")
        if ty == "WallComponent" and c.findtext("wall"):
            W[str(int(c.findtext("wall")))] = {
                "destroyed": int(c.findtext("destroyed") or 0),
                "ruins": int(c.findtext("ruins") or 0),
                "indestructible": (c.findtext("indestructible") or "").strip().lower() == "true",
                "seen": 0, "name": c.get("name", "")}
        elif ty == "DoorComponent" and c.findtext("openId"):
            fam = {"open": int(c.findtext("openId")),
                   "closed": int(c.findtext("closedId") or 0),
                   "secret": int(c.findtext("secretId") or 0),
                   "destroyed": int(c.findtext("destroyedId") or 0),
                   "seen": 0, "name": c.get("name", "")}
            for member in (fam["open"], fam["closed"], fam["secret"], fam["destroyed"]):
                if member:
                    D[str(member)] = fam
    return W, D


def main():
    a = sys.argv[1:]
    out = Path(a[a.index("-o") + 1]) if "-o" in a else Path(__file__).parent / "companions.json"
    cat_w, cat_d = {}, {}
    if "--components" in a:
        cpath = a[a.index("--components") + 1]
        cat_w, cat_d = catalog(cpath)
        skip = {a[a.index("--components") + 1], "--components"}
    else:
        skip = set()
    roots = [Path(p) for p in a if p != "-o" and Path(p) != out and p not in skip]
    files = []
    for r in roots:
        files += sorted(r.rglob("*.xml")) if r.is_dir() else [r]
    walls = defaultdict(Counter)      # wall id -> Counter[(destroyed, ruins, indestructible)]
    doors = defaultdict(Counter)      # openId  -> Counter[(closed, secret, destroyed)]
    n_regions = 0
    unreadable = []
    for f in files:
        try:
            root = ET.fromstring(f.read_bytes())
        except ET.ParseError:
            continue
        except OSError:
            unreadable.append(str(f))     # cloud-only (OneDrive) or locked — skipped
            continue
        if root.tag != "region" and root.find(".//tile") is None:
            continue
        n_regions += 1
        for c in root.iter("component"):
            ty = c.get("type")
            if ty == "WallComponent":
                w = c.findtext("wall")
                if not w:
                    continue
                walls[int(w)][(int(c.findtext("destroyed") or 0),
                               int(c.findtext("ruins") or 0),
                               (c.findtext("indestructible") or "").strip().lower() == "true")] += 1
            elif ty == "DoorComponent":
                o = c.findtext("openId")
                if not o:
                    continue
                doors[int(o)][(int(c.findtext("closedId") or 0),
                               int(c.findtext("secretId") or 0),
                               int(c.findtext("destroyedId") or 0))] += 1
    W, D, variants = dict(cat_w), dict(cat_d), []
    for wid, cnt in sorted(walls.items()):
        (d, r, ind), n = cnt.most_common(1)[0]
        W[str(wid)] = {"destroyed": d, "ruins": r, "indestructible": ind,
                       "seen": sum(cnt.values()),
                       "name": cat_w.get(str(wid), {}).get("name", "")}
        if len(cnt) > 1:
            variants.append(f"wall {wid}: majority {(d, r, ind)} x{n}, variants {dict(cnt)}")
    for oid, cnt in sorted(doors.items()):
        (cl, se, de), n = cnt.most_common(1)[0]
        fam = {"open": oid, "closed": cl, "secret": se, "destroyed": de,
               "seen": sum(cnt.values()),
               "name": cat_d.get(str(oid), {}).get("name", "")}
        for member in (oid, cl, se, de):
            if member:
                D[str(member)] = fam
        if len(cnt) > 1:
            variants.append(f"door {oid}: majority {(cl, se, de)} x{n}, variants {dict(cnt)}")
    out.write_text(json.dumps({"walls": W, "doors": D}, indent=1), encoding="utf-8")
    print(f"catalog: {len(cat_w)} walls, {len(cat_d)} door member ids · "
          f"mined {n_regions} region files -> {len(W)} wall ids, {len(D)} door ids -> {out}")
    if unreadable:
        print(f"  ! {len(unreadable)} files unreadable (cloud-only?): {unreadable[:5]}")
    for v in variants:
        print("  ~", v)


if __name__ == "__main__":
    main()
