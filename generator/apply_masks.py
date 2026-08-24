#!/usr/bin/env python3
"""apply_masks.py — restyle areas of an existing region from a LOK Sketcher masks file.

The masks workflow (Tony, 2026-08-23):
  1. Claude preps a coordinate section:  xml_to_sketch.py region.xml --window …  -> context JSON
     (Claude KEEPS this exact file — it is the base for both diff merges and restyles.)
  2. Tony imports it into the sketcher, flips to MASKS, paints named areas, binds each to
     a saved style, EXPORT MASKS. The export carries the style VALUES (self-contained).
  3. This script re-emits ONLY the masked tiles with their mask's style; every unmasked
     tile is untouched. Dry run by default; --write commits with a _pre-fix backup.

Usage:
  python3 apply_masks.py <masks.json> <context.json> --merge <region.xml> [--write]
                         [--palette <base_palette.json>]   # base ids for unstyled roles

Style lookup per mask, first hit wins: the masks file's embedded "styles" block, then
Generator/styles/<name>.json. A mask bound to no findable style is a hard stop.
Only tiles whose emitted result actually differs from the base-palette form are written.
"""
import json, sys
from pathlib import Path
import sketch_build as sb


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    masks_d = json.load(open(a[0], encoding="utf-8"))
    if masks_d.get("kind") != "masks":
        sys.exit(f"{a[0]} is not a masks file")
    rep = []
    d, L = sb.load_sketch(a[1])
    rep.append(f"context: {a[1]}  title '{d.get('title','')}'")
    rep.append(f"masks: {a[0]}  ({len(masks_d.get('masks', []))} masks)")

    # base palette: defaults < context sketch palette < --palette
    base = dict(sb.DEFAULT_PALETTE)
    if isinstance(d.get("palette"), dict):
        base.update(d["palette"])
    if "--palette" in a:
        base.update(json.load(open(a[a.index("--palette")+1], encoding="utf-8")))
    base.pop("_comment", None)
    sb.resolve_palette(base, rep)

    # one resolved palette per mask
    embedded = masks_d.get("styles", {})
    styles_dir = Path(__file__).resolve().parent / "styles"
    mask_pal, tile_mask = {}, {}
    for m in masks_d.get("masks", []):
        name, style = m.get("name", "?"), m.get("style", "")
        vals = embedded.get(style)
        if vals is None and style:
            sp = styles_dir / f"{style}.json"
            if sp.exists():
                vals = json.load(open(sp, encoding="utf-8"))
        if vals is None:
            sys.exit(f"mask '{name}': style '{style or '(none)'}' not found in the masks "
                     f"file or {styles_dir} — bind a style in the sketcher and re-export")
        p = dict(base); p.update(vals); p.pop("_comment", None)
        sb.resolve_palette(p, rep)
        mask_pal[name] = p
        for x, y in m.get("tiles", []):
            tile_mask[(x, y)] = name
    if not tile_mask:
        sys.exit("no masked tiles — nothing to do")

    # model the context in full (orientation/faces need the whole neighborhood)
    S = sb.determine(d, L, rep)
    sb.normalize(S, rep)
    M, _ = sb.build_model(S, rep)

    # CARRIER EXPANSION (Tony's bug report 2026-08-23): structural blocks push their N/W
    # face walls, the NW cap, and shifted N/W doors onto tiles one OUTSIDE the mask.
    # Those carrier tiles restyle their wall/door components with the mask's style while
    # keeping their own (exterior) ground from the base palette.
    WALLISH = ("wall-ns", "wall-ew", "corner", "structural",
               "door-ns", "door-ew", "indestructible")

    def hybrid(name):
        p = dict(base)
        for k in WALLISH:
            p[k] = mask_pal[name][k]
        return p

    def expand(tiles):
        """carrier tiles for a {tile: mask_name} set — sources are blocks and door gaps"""
        out = {}
        for c, name in tiles.items():
            if c not in S["structural"] and c not in S["door"]:
                continue
            x, y = c
            for nb in ((x, y-1), (x-1, y), (x-1, y-1)):
                if nb in tiles or nb in out:
                    continue
                mnb = M.get(nb)
                if mnb and any(r in WALLISH for r in mnb["stack"]):
                    out[nb] = name
        return out

    carriers = expand(tile_mask)
    carrier_pal = {c: hybrid(n) for c, n in carriers.items()}
    if carriers:
        rep.append(f"carriers: {len(carriers)} tiles outside the mask hold masked faces/"
                   f"doors/caps — walls restyled, exterior ground kept")

    # restyle set: masked + carrier tiles that exist in the model and actually change
    off_model = [c for c in tile_mask if c not in M]
    changed, pal_of, same = {}, {}, 0
    for c, name in list(tile_mask.items()) + list(carriers.items()):
        if c not in M:
            continue
        p = carrier_pal.get(c) or mask_pal[name]
        if sb.tile_lines(c, M[c], p) != sb.tile_lines(c, M[c], base):
            changed[c] = name
            pal_of[c] = p
        else:
            same += 1
    per = {}
    for c, name in changed.items():
        per[name] = per.get(name, 0) + 1
    rep.append(f"RESTYLE: {len(tile_mask)} masked tiles -> {len(changed)} change, "
               f"{same} already match the style, {len(off_model)} not in the context model (skipped)")
    for name, n in sorted(per.items()):
        rep.append(f"  mask '{name}': {n} tiles restyled")
    if off_model:
        rep.append(f"  ⚠ masked outside the context content, e.g. {sorted(off_model)[:6]} "
                   "— masks recolor what exists; they don't create tiles")
    if not changed:
        rep.append("nothing differs — no merge needed")
        print("\n".join(rep)); return

    if "--merge" not in a:
        rep.append("no --merge target given: analysis only")
        print("\n".join(rep)); return
    src = a[a.index("--merge")+1]
    # tiles the LAST applied mask covered but this one doesn't get REVERTED to base
    applied = Path(__file__).resolve().parent / "last_applied_masks" / (Path(src).stem + ".json")
    revert = set()
    if applied.exists():
        prev = json.load(open(applied, encoding="utf-8"))
        prev_tiles = {tuple(t): (m.get("name") or "?")
                      for m in prev.get("masks", []) for t in m.get("tiles", [])}
        prev_all = set(prev_tiles) | set(expand(prev_tiles))
        cur_all = set(tile_mask) | set(carriers)
        revert = {c for c in prev_all - cur_all if c in M}
        if revert:
            rep.append(f"REVERT: {len(revert)} tiles (incl. carriers) left the mask since "
                       "last apply -> back to base")
    M_write = {c: M[c] for c in changed}
    M_write.update({c: M[c] for c in revert})
    if not M_write:
        rep.append("nothing to write"); print("\n".join(rep)); return
    pal_fn = lambda c: pal_of[c] if c in pal_of else base
    txt, intended = sb.merge(M_write, pal_fn, src, rep, write="--write" in a,
                             preserve_extras=True)
    sb.audit(txt, M_write, base, rep, intended)
    if "--write" in a:
        applied.parent.mkdir(exist_ok=True)
        applied.write_text(json.dumps(masks_d), encoding="utf-8")
        rep.append(f"applied-state saved: {applied.name}")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
