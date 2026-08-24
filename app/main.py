#!/usr/bin/env python3
"""LOK Studio — desktop shell for the LOK Sketcher + generator.

Opens the sketcher UI in a native window (pywebview / Edge WebView2 on Windows) and
exposes the generator to the page through a small Python API (window.pywebview.api).

Phase 1: the UI is the existing sketcher, unchanged. The API below is the bridge the
UI will grow into (build / import / styles on disk instead of browser storage).
Merges and mask applies stay dry-run-first: nothing writes without an explicit
confirm=True from a human click.
"""
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent      # repo root
UI = ROOT / "app" / "ui" / "lok_sketcher.html"
GEN = ROOT / "generator"
WORKSPACE = ROOT / "workspace"                     # user data — gitignored
IMPORTS = WORKSPACE / "Imports"
EXPORTS = WORKSPACE / "Exports"
SNAPSHOTS = WORKSPACE / "Snapshots"
STYLES = GEN / "styles"
SETTINGS = WORKSPACE / "settings.json"


def _settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_settings(st):
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(st, indent=1), encoding="utf-8")


def _run(script, *args):
    """Run a generator script, capture its report. UTF-8 forced end to end —
    Windows pipes default to cp1252, which chokes on the reports' ⚠/× glyphs."""
    import os
    cmd = [sys.executable, "-X", "utf8", str(GEN / script), *[str(a) for a in args]]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    return {"ok": p.returncode == 0, "report": (p.stdout + p.stderr).strip(),
            "cmd": " ".join(cmd)}


class Api:
    """Called from the page as window.pywebview.api.<method>(...) — returns Promises."""

    # ---- styles on disk (replaces browser storage + folder-permission dance)
    def styles_list(self):
        out = {}
        for f in sorted(STYLES.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                name = d.pop("_name", None) or f.stem
                d.pop("_comment", None)
                out[name] = d
            except Exception:
                pass
        return out

    def style_save(self, name, obj):
        fn = "".join(ch if ch.isalnum() else "_" for ch in name.lower()).strip("_")
        obj = dict(obj); obj["_name"] = name
        (STYLES / f"{fn}.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")
        return True

    def style_delete(self, name):
        fn = "".join(ch if ch.isalnum() else "_" for ch in name.lower()).strip("_")
        p = STYLES / f"{fn}.json"
        if p.exists():
            p.unlink()
        return True

    # ---- sketch autosave to disk (replaces localStorage)
    def autosave_write(self, kind, data):
        (WORKSPACE / f"autosave_{kind}.json").write_text(data, encoding="utf-8")
        return True

    def autosave_read(self, kind):
        p = WORKSPACE / f"autosave_{kind}.json"
        return p.read_text(encoding="utf-8") if p.exists() else None

    # ---- generator
    def import_region(self, region_xml, window=None):
        """Region XML -> sketch JSON in workspace/Imports (layout only, no palette)."""
        out = IMPORTS / (Path(region_xml).stem + "_import.json")
        args = [region_xml]
        if window:
            args += ["--window", *window]
        args += ["-o", str(out)]
        r = _run("xml_to_sketch.py", *args)
        r["out"] = str(out)
        return r

    def build_new(self, sketch_json, region_id, region_name, style=None):
        """Sketch JSON -> fresh region XML beside the sketch. Safe: new file only."""
        args = [sketch_json, "--new", str(region_id), region_name, "--png"]
        if style:
            args += ["--style", style]
        return _run("sketch_build.py", *args)

    def merge_dry_run(self, sketch_json, region_xml, base_json=None, style=None):
        """Diff-merge preview — never writes."""
        args = [sketch_json, "--merge", region_xml]
        if base_json:
            args += ["--base", base_json]
        if style:
            args += ["--style", style]
        return _run("sketch_build.py", *args)

    def merge_write(self, sketch_json, region_xml, base_json=None, style=None,
                    confirm=False):
        """The ONLY writing merge — requires the explicit confirm from a human click."""
        if not confirm:
            return {"ok": False, "report": "refused: confirm not given"}
        args = [sketch_json, "--merge", region_xml, "--write"]
        if base_json:
            args += ["--base", base_json]
        if style:
            args += ["--style", style]
        return _run("sketch_build.py", *args)

    # ---- real file dialogs (replace the browser download/upload dance)
    def export_json(self, suggested, data):
        """Save dialog defaulting to workspace/Exports; returns the written path or None."""
        import webview
        w = webview.windows[0]
        res = w.create_file_dialog(webview.SAVE_DIALOG, directory=str(EXPORTS),
                                   save_filename=suggested)
        if not res:
            return None
        p = Path(res if isinstance(res, str) else res[0])
        p.write_text(data, encoding="utf-8")
        return str(p)

    def import_json(self, start="imports"):
        """Open dialog defaulting to workspace/Imports (or Exports); returns
        {name, text} or None."""
        import webview
        w = webview.windows[0]
        d = EXPORTS if start == "exports" else IMPORTS
        res = w.create_file_dialog(webview.OPEN_DIALOG, directory=str(d),
                                   file_types=("JSON files (*.json)", "All files (*.*)"))
        if not res:
            return None
        p = Path(res[0])
        return {"name": p.name, "text": p.read_text(encoding="utf-8")}

    # ================= BUILD (Tony's three-path design, 2026-08-24) =================
    # Import keeps two silent copies: the full region XML (snapshot) and the untouched
    # window context (diff base). Build never guesses: exists -> merge dry-run;
    # missing + snapshot -> restore then merge, with notice; missing + no origin ->
    # plain new build. Explicit buttons only; merges write nothing without confirm.

    def get_regions_dir(self):
        return _settings().get("regions_dir")

    def pick_regions_dir(self):
        import webview
        res = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        if not res:
            return None
        p = str(res[0] if isinstance(res, (list, tuple)) else res)
        if "HaDeZs Test" in p:
            return {"error": "That is HaDeZs Test — the tools never write there. "
                             "Point at your sandbox Regions folder instead."}
        st = _settings(); st["regions_dir"] = p; _save_settings(st)
        return {"path": p}

    def pick_region_file(self):
        """Step 1: choose the region XML; returns its identity so the window prompt
        can say what was picked (id, name, bounds)."""
        import webview
        st = _settings()
        start = st.get("regions_dir") or str(IMPORTS)
        res = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG, directory=start,
            file_types=("Region XML (*.xml)", "All files (*.*)"))
        if not res:
            return None
        src = Path(res[0])
        info = {"path": str(src), "name": src.name}
        try:
            head = src.read_bytes()[:2000].decode("utf-8-sig", errors="replace")
            for tag in ("id", "name"):
                m = re.search(rf"<{tag}>([^<]*)</{tag}>", head)
                if m:
                    info["region_" + tag] = m.group(1).strip()
            m = re.search(r'<bounds left="(-?\d+)" top="(-?\d+)" '
                          r'right="(-?\d+)" bottom="(-?\d+)"', head)
            if m:
                l, t, rr, b = map(int, m.groups())
                info["bounds"] = f"({l},{t}) to ({rr-1},{b-1})"
        except Exception:
            pass
        return info

    def import_region(self, src_path, window_text=""):
        """Step 2: convert the chosen file, keeping snapshot + diff base."""
        st = _settings()
        src = Path(src_path)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        out = IMPORTS / f"{src.stem}_{ts}_context.json"
        args = [src]
        wt = (window_text or "").split()
        if wt:
            if len(wt) != 4:
                return {"error": "Window needs exactly four numbers: x0 y0 x1 y1 "
                                 "(or leave it blank for the whole region)."}
            args += ["--window", *wt]
        args += ["-o", str(out)]
        r = _run("xml_to_sketch.py", *args)
        if not r["ok"]:
            return {"error": r["report"]}
        SNAPSHOTS.mkdir(parents=True, exist_ok=True)
        snap = SNAPSHOTS / f"{src.stem}_{ts}.xml"
        shutil.copy2(src, snap)
        text = out.read_text(encoding="utf-8")
        d = json.loads(text)
        rid = d.get("region")
        if rid is not None:
            st.setdefault("origins", {})[str(rid)] = {
                "source": str(src), "base": str(out), "snapshot": str(snap)}
            _save_settings(st)
        return {"json": text, "name": src.name, "region": rid, "report": r["report"]}

    def _target(self, rid):
        rd = _settings().get("regions_dir")
        return (Path(rd) / f"{rid}.xml") if rd else None

    def build_preflight(self, sketch_json):
        s = json.loads(sketch_json)
        rid = s.get("region")
        if rid in (None, ""):
            return {"error": "Set the R# box first — the region number is Build's target."}
        if not _settings().get("regions_dir"):
            return {"need_dir": True}
        target = self._target(rid)
        origins = _settings().get("origins", {}).get(str(rid), {})
        snap = origins.get("snapshot")
        snap_ok = bool(snap and Path(snap).exists())
        exists = target.exists()
        mode = "merge" if exists else ("restore_merge" if snap_ok else "new")
        pal = s.get("palette") or {}
        g = lambda k, d: pal.get(k, d)
        pal_line = (f"room {g('room',1)} · hall {g('hall',1)} · NS {g('wall-ns',29)} · "
                    f"EW {g('wall-ew',30)} · corner {g('corner',34)} · "
                    f"struct {g('structural',447)} · doors {g('door-ns',66)}/{g('door-ew',67)}")
        if (g('room',1), g('hall',1), g('wall-ns',29), g('wall-ew',30),
                g('corner',34), g('structural',447)) == (1, 1, 29, 30, 34, 447):
            pal_line += "   (gray-box values)"
        tiles = sum(len(v) for v in (s.get("layers") or {}).values())
        notes = []
        if mode == "restore_merge":
            notes.append(f"TARGET MISSING — {target.name} will be RESTORED from the "
                         f"backup taken at import, then your changes merged on top.")
        if mode == "new" and origins:
            notes.append(f"WARNING: this sketch traces to region {rid} but neither the "
                         f"file nor an import backup exists — a new build will contain "
                         f"ONLY what is sketched.")
        return {"mode": mode, "region": rid, "target": str(target),
                "title": s.get("title") or "", "tiles": tiles,
                "palette": pal_line, "notes": notes,
                "base": origins.get("base") if origins.get("base")
                        and Path(origins["base"]).exists() else None}

    def build_run(self, sketch_json, mode, write=False):
        s = json.loads(sketch_json)
        rid = s.get("region")
        target = self._target(rid)
        if target is None:
            return {"ok": False, "report": "Regions folder not set."}
        tmp = WORKSPACE / "_build_sketch.json"
        tmp.write_text(sketch_json, encoding="utf-8")
        origins = _settings().get("origins", {}).get(str(rid), {})
        notice = ""
        if mode == "restore_merge":
            snap = origins.get("snapshot")
            if not (snap and Path(snap).exists()):
                return {"ok": False, "report": "Import backup not found — cannot restore."}
            if not target.exists():
                shutil.copy2(snap, target)
                notice = (f"NOTICE: {target.name} was missing and has been RESTORED "
                          f"from the import backup.\n\n")
            mode = "merge"
        if mode == "merge":
            args = [str(tmp), "--merge", str(target)]
            base = origins.get("base")
            if base and Path(base).exists():
                args += ["--base", base]
            if write:
                args += ["--write"]
            r = _run("sketch_build.py", *args)
        elif mode == "new":
            if target.exists():
                return {"ok": False, "report": f"{target.name} appeared since pre-flight "
                                               f"— re-run Build to merge instead."}
            r = _run("sketch_build.py", str(tmp), "--new", str(rid),
                     s.get("title") or f"Region {rid}", "-o", str(target))
        else:
            return {"ok": False, "report": f"unknown mode {mode}"}
        r["report"] = notice + r["report"]
        return r

    def version(self):
        return "LOK Studio 0.1.0"


def main():
    try:
        import webview
    except ImportError:
        sys.exit("pywebview is not installed — run run.bat (it installs it), or:\n"
                 "  python -m pip install pywebview")
    for d in (WORKSPACE, IMPORTS, EXPORTS):
        d.mkdir(parents=True, exist_ok=True)
    window = webview.create_window(
        "LOK Studio", UI.as_uri(), js_api=Api(),
        width=1500, height=950, background_color="#0a1014")
    webview.start(debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
