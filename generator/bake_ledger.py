#!/usr/bin/env python3
"""bake_ledger.py — bake the game's terrain tiles into a ledger the LOK Sketcher loads.

Reads the WorldForge install (Data.bin: Terrain.xml + Terrain-External.xml; Kesmai.bin /
Stormhalter.bin: XNB texture sheets, LZ4), crops every terrain's sprites, stacks composites
in order, and writes tiles_ledger.js next to the sketcher:

    window.TILE_LEDGER = { "<id>": {"n": "name-from-comment", "i": "data:image/png;base64,…"}, … }

Terrain.xml (internal, ids 1–1007) is loaded first; Terrain-External.xml overrides on
id collision (it is the live extension file). Icons are capped at ICON px on the long side.

Usage: python3 bake_ledger.py <worldforge_dir> <out_dir>
"""
import base64, io, re, struct, sys, zipfile
from pathlib import Path
import lz4.block
from PIL import Image

ICON = 64


def read_xnb_texture(raw):
    assert raw[:3] == b"XNB", "not an XNB"
    flags = raw[5]
    if flags & 0x40:
        dsize = struct.unpack("<I", raw[10:14])[0]
        payload = lz4.block.decompress(raw[14:], uncompressed_size=dsize)
    elif flags & 0x80:
        raise ValueError("LZX-compressed XNB (not supported)")
    else:
        payload = raw[10:]

    def r7(o):
        res = sh = 0
        while True:
            x = payload[o]; o += 1
            res |= (x & 0x7F) << sh
            if not x & 0x80:
                return res, o
            sh += 7

    o = 0
    n, o = r7(o)
    for _ in range(n):
        ln, o = r7(o)
        o += ln + 4                      # reader name + version
    _, o = r7(o)                          # shared resources
    _, o = r7(o)                          # type id
    fmt, w, h, mips = struct.unpack("<iIII", payload[o:o+16]); o += 16
    size = struct.unpack("<I", payload[o:o+4])[0]; o += 4
    if fmt != 0:
        raise ValueError(f"surface format {fmt} (only Color supported)")
    return Image.frombytes("RGBA", (w, h), payload[o:o+size])


class Sheets:
    def __init__(self, wf):
        self.zips = [zipfile.ZipFile(wf / "Kesmai.bin"), zipfile.ZipFile(wf / "Stormhalter.bin")]
        self.index = {}
        for z in self.zips:
            for n in z.namelist():
                if n.lower().endswith(".xnb"):
                    self.index[n[:-4].lower()] = (z, n)
        self.cache, self.misses = {}, set()

    def get(self, tex):
        key = tex.replace("\\", "/").lower()
        if key in self.cache:
            return self.cache[key]
        hit = self.index.get(key)
        if not hit:
            self.misses.add(tex)
            self.cache[key] = None
            return None
        try:
            img = read_xnb_texture(hit[0].read(hit[1]))
        except Exception as e:
            print(f"  ! {tex}: {e}")
            img = None
        self.cache[key] = img
        return img


TER_RE = re.compile(r"<terrain\s+id=\"(\d+)\"[^>]*>(.*?)</terrain>", re.S)
SPR_RE = re.compile(r"<sprite([^>]*)>(.*?)</sprite>", re.S)
COM_RE = re.compile(r"<!--\s*(.*?)\s*-->", re.S)


def parse_terrains(text):
    out = {}
    for m in TER_RE.finditer(text):
        tid, body = int(m.group(1)), m.group(2)
        cm = COM_RE.search(body)
        name = " ".join(cm.group(1).split()) if cm else ""
        sprites = []
        for sm in SPR_RE.finditer(body):
            attrs, sbody = sm.group(1), sm.group(2)
            om = re.search(r'order="(-?\d+)"', attrs)
            rm = re.search(r'resolution="(\d+)"', attrs)
            tm = re.search(r"<texture>(.*?)</texture>", sbody)
            srm = re.search(r"<source>\((\d+),(\d+),(\d+),(\d+)\)</source>", sbody)
            if not (tm and srm):
                continue
            sprites.append({
                "order": int(om.group(1)) if om else 0,
                "res": int(rm.group(1)) if rm else 1,
                "tex": tm.group(1).strip(),
                "src": tuple(int(v) for v in srm.groups()),
            })
        if sprites:
            out[tid] = {"name": name, "sprites": sorted(sprites, key=lambda s: s["order"])}
    return out


def render(entry, sheets):
    crops = []
    for s in entry["sprites"]:
        sheet = sheets.get(s["tex"])
        if sheet is None:
            continue
        x, y, w, h = s["src"]
        if x + w > sheet.width or y + h > sheet.height:
            continue
        img = sheet.crop((x, y, x + w, y + h))
        if s["res"] != 1:                          # normalize to logical pixels
            img = img.resize((w // s["res"], h // s["res"]), Image.LANCZOS)
        crops.append(img)
    if not crops:
        return None
    W = max(c.width for c in crops); H = max(c.height for c in crops)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for c in crops:                                # stack in order, bottom-anchored
        canvas.alpha_composite(c, ((W - c.width) // 2, H - c.height))
    canvas.thumbnail((ICON, ICON), Image.LANCZOS)
    buf = io.BytesIO()
    canvas.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    wf, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    data = zipfile.ZipFile(wf / "Data.bin")
    terrains = parse_terrains(data.read("Data/Terrain.xml").decode("utf-8-sig", "replace"))
    n_int = len(terrains)
    ext = parse_terrains(data.read("Data/Terrain-External.xml").decode("utf-8-sig", "replace"))
    overlap = sorted(set(terrains) & set(ext))
    terrains.update(ext)                           # external overrides on collision
    print(f"terrains: {n_int} internal + {len(ext)} external "
          f"({len(overlap)} overridden by external) = {len(terrains)}")
    sheets = Sheets(wf)
    ledger, skipped = {}, []
    for tid in sorted(terrains):
        b64 = render(terrains[tid], sheets)
        if b64 is None:
            skipped.append(tid)
            continue
        ledger[str(tid)] = {"n": terrains[tid]["name"], "i": "data:image/png;base64," + b64}
    js = ("// baked by bake_ledger.py from the WorldForge install — do not hand-edit\n"
          "window.TILE_LEDGER=")
    import json
    js += json.dumps(ledger, separators=(",", ":")) + ";\n"
    out = out_dir / "tiles_ledger.js"
    out.write_text(js, encoding="utf-8")
    print(f"baked {len(ledger)} tiles -> {out} ({out.stat().st_size/1e6:.1f} MB)")
    if skipped:
        print(f"skipped (no renderable sprite): {len(skipped)} e.g. {skipped[:12]}")
    if sheets.misses:
        print(f"missing sheets: {sorted(sheets.misses)[:10]}")


if __name__ == "__main__":
    main()
