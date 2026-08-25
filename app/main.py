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

try:
    from version import VERSION            # stamped by CI from the git tag
except ImportError:
    VERSION = "0.0.0-dev"

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    # packaged app: bundled read-only data lives in _internal (sys._MEIPASS);
    # everything the user writes goes to %LOCALAPPDATA%\LOK Studio.
    import os
    _BUNDLE = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    ROOT = _BUNDLE
    UI = _BUNDLE / "ui" / "lok_sketcher.html"
    GEN = _BUNDLE / "generator"
    WORKSPACE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LOK Studio"
    STYLES = WORKSPACE / "styles"                  # writable; seeded from the bundle
else:
    ROOT = Path(__file__).resolve().parent.parent  # repo root
    UI = ROOT / "app" / "ui" / "lok_sketcher.html"
    GEN = ROOT / "generator"
    WORKSPACE = ROOT / "workspace"                 # user data — gitignored
    STYLES = GEN / "styles"
# Defaults. settings.json ALWAYS lives at the default workspace — it is what records a
# custom one, so it can't live inside the folder it points at.
DEFAULT_WORKSPACE, DEFAULT_STYLES = WORKSPACE, STYLES
SETTINGS = DEFAULT_WORKSPACE / "settings.json"


def _dir(key, default):
    """Settings can repoint a folder (Settings dialog). Repoint only — files already
    written stay where they are; nothing is moved."""
    try:
        v = _settings().get(key)
    except Exception:
        v = None
    return Path(v) if v else default


def ws():         return _dir("workspace_dir", DEFAULT_WORKSPACE)
def styles_dir(): return _dir("styles_dir", DEFAULT_STYLES)
def imports():    return ws() / "Imports"
def exports():    return ws() / "Exports"
def snapshots():  return ws() / "Snapshots"

# Frozen re-exec: the packaged exe has no separate python, so generator scripts run
# as "<exe> --script <name> <args...>" — this branch executes them and exits.
if "--script" in sys.argv:
    _i = sys.argv.index("--script")
    _script, _args = sys.argv[_i + 1], sys.argv[_i + 2:]
    sys.argv = [_script] + _args
    sys.path.insert(0, str(GEN))
    import runpy
    runpy.run_path(str(GEN / _script), run_name="__main__")
    sys.exit(0)


def _settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_settings(st):
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)   # always the DEFAULT workspace
    SETTINGS.write_text(json.dumps(st, indent=1), encoding="utf-8")


def _run(script, *args):
    """Run a generator script, capture its report. UTF-8 forced end to end —
    Windows pipes default to cp1252, which chokes on the reports' ⚠/× glyphs."""
    import os
    if FROZEN:
        cmd = [sys.executable, "--script", script, *[str(a) for a in args]]
    else:
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
        for f in sorted(styles_dir().glob("*.json")):
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
        (styles_dir() / f"{fn}.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")
        return True

    def style_delete(self, name):
        fn = "".join(ch if ch.isalnum() else "_" for ch in name.lower()).strip("_")
        p = styles_dir() / f"{fn}.json"
        if p.exists():
            p.unlink()
        return True

    # ---- sketch autosave to disk (replaces localStorage)
    def autosave_write(self, kind, data):
        (ws() / f"autosave_{kind}.json").write_text(data, encoding="utf-8")
        return True

    def autosave_read(self, kind):
        p = ws() / f"autosave_{kind}.json"
        return p.read_text(encoding="utf-8") if p.exists() else None

    # ---- interface scale (per machine: a 4K panel wants a bigger UI than a laptop)
    def ui_scale_get(self):
        try:
            return float(_settings().get("ui_scale", 1))
        except Exception:
            return 1

    def ui_scale_set(self, scale):
        st = _settings()
        st["ui_scale"] = max(0.5, min(3.0, float(scale)))
        _save_settings(st)
        return st["ui_scale"]

    # ---- settings dialog (☰ menu). Folders are REPOINT ONLY: nothing is moved,
    # files already written stay where they are.
    FOLDER_KEYS = {"regions_dir": "Regions", "workspace_dir": "Workspace",
                   "styles_dir": "Styles"}

    def settings_get(self):
        st = _settings()
        return {
            "regions_dir": st.get("regions_dir") or "",
            "workspace_dir": str(ws()), "workspace_custom": bool(st.get("workspace_dir")),
            "styles_dir": str(styles_dir()), "styles_custom": bool(st.get("styles_dir")),
            "defaults": {"workspace_dir": str(DEFAULT_WORKSPACE),
                         "styles_dir": str(DEFAULT_STYLES)},
            "ui_scale": self.ui_scale_get(),
            "frozen": FROZEN, "version": self.version(),
            "settings_file": str(SETTINGS),
        }

    def pick_folder(self, key):
        """Folder dialog for one settings key; returns the chosen path or an error."""
        if key not in self.FOLDER_KEYS:
            return {"error": f"unknown setting: {key}"}
        import webview
        st = _settings()
        start = st.get(key) or (str(ws()) if key != "regions_dir" else "")
        res = webview.windows[0].create_file_dialog(
            webview.FOLDER_DIALOG, directory=start or "")
        if not res:
            return None
        p = str(res[0] if isinstance(res, (list, tuple)) else res)
        if key == "regions_dir" and "HaDeZs Test" in p:
            return {"error": "That is HaDeZs Test — the tools never write there. "
                             "Point at your sandbox Regions folder instead."}
        st[key] = p
        _save_settings(st)
        if key in ("workspace_dir", "styles_dir"):       # make it usable immediately
            try:
                Path(p).mkdir(parents=True, exist_ok=True)
                if key == "workspace_dir":
                    for d in (imports(), exports(), snapshots()):
                        d.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return {"error": f"could not use that folder: {e}"}
        return {"path": p}

    def reset_folder(self, key):
        """Back to the default location (Workspace / Styles only)."""
        st = _settings()
        st.pop(key, None)
        _save_settings(st)
        return {"path": str(ws() if key == "workspace_dir" else styles_dir())}

    def open_folder(self, path):
        import os
        p = Path(path)
        if not p.exists():
            return {"error": "that folder does not exist yet"}
        try:
            os.startfile(str(p))                          # Windows
        except AttributeError:
            subprocess.Popen(["xdg-open", str(p)])
        return True

    # ---- generator
    def import_region(self, region_xml, window=None):
        """Region XML -> sketch JSON in workspace/Imports (layout only, no palette)."""
        out = imports() / (Path(region_xml).stem + "_import.json")
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
        res = w.create_file_dialog(webview.SAVE_DIALOG, directory=str(exports()),
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
        d = exports() if start == "exports" else imports()
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
        start = st.get("regions_dir") or str(imports())
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
        out = imports() / f"{src.stem}_{ts}_context.json"
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
        snapshots().mkdir(parents=True, exist_ok=True)
        snap = snapshots() / f"{src.stem}_{ts}.xml"
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
        tmp = ws() / "_build_sketch.json"
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

    def apply_masks_run(self, rid, masks_json, write=False):
        """Restyle the masked areas of region <rid>. Needs the region imported through
        IMPORT REGION first — that kept context is the restyle base. Dry run unless
        write; apply_masks backs up to _pre-fix before writing."""
        target = self._target(rid)
        if target is None:
            return {"ok": False, "report": "Regions folder not set."}
        if not target.exists():
            return {"ok": False, "report": f"{target.name} not found — masks restyle an "
                                           f"EXISTING region."}
        origins = _settings().get("origins", {}).get(str(rid), {})
        base = origins.get("base")
        if not (base and Path(base).exists()):
            return {"ok": False, "report": f"No import context for region {rid} — use "
                                           f"IMPORT REGION on it first (that kept copy "
                                           f"is the restyle base)."}
        mf = ws() / "_apply_masks.json"
        mf.write_text(masks_json, encoding="utf-8")
        args = [str(mf), base, "--merge", str(target)]
        if write:
            args += ["--write"]
        return _run("apply_masks.py", *args)

    def version(self):
        return f"LOK Studio {VERSION}"

    # ---- updates: checked only on request (☰ menu), never automatically.
    REPO_API = "https://api.github.com/repos/HaDeZs530/LOK-Studio/releases/latest"

    @staticmethod
    def _vtuple(s):
        s = str(s or "").strip().lstrip("vV").split("-")[0]
        parts = []
        for chunk in s.split("."):
            parts.append(int(chunk) if chunk.isdigit() else 0)
        return tuple(parts + [0, 0, 0])[:3]

    def check_update(self):
        """Ask GitHub for the newest release. Returns what's there — never downloads."""
        import urllib.request
        try:
            req = urllib.request.Request(
                self.REPO_API, headers={"User-Agent": "LOK-Studio",
                                        "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=12) as r:
                d = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"error": f"Could not reach GitHub: {e}"}
        latest = d.get("tag_name") or ""
        setup = next((a.get("browser_download_url") for a in (d.get("assets") or [])
                      if str(a.get("name", "")).lower().endswith("setup.exe")), None)
        # a build living under Program Files came from the installer; a portable copy
        # should be pointed at the page rather than handed a second installation
        installed = "program files" in str(Path(sys.executable).parent).lower()
        return {"current": VERSION, "latest": latest.lstrip("vV"),
                "newer": self._vtuple(latest) > self._vtuple(VERSION),
                "dev": VERSION.endswith("-dev"),
                "notes": (d.get("body") or "").strip()[:1200],
                "page": d.get("html_url"), "setup": setup,
                "installed": installed and bool(setup)}

    def run_update(self, url):
        """Download the release installer and launch it, then close the app so the
        installer can replace the files. Only ever called after an explicit confirm."""
        import urllib.request, tempfile, os
        if not str(url).startswith("https://github.com/HaDeZs530/LOK-Studio/releases/"):
            return {"error": "refused: that download is not from this project's releases"}
        try:
            dest = Path(tempfile.gettempdir()) / "LOK-Studio-Setup.exe"
            req = urllib.request.Request(url, headers={"User-Agent": "LOK-Studio"})
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
                shutil.copyfileobj(r, f)
            if dest.stat().st_size < 1_000_000:
                return {"error": "the download looks truncated — try again"}
            os.startfile(str(dest))
        except Exception as e:
            return {"error": f"Update failed: {e}"}
        import threading, webview
        threading.Timer(1.5, lambda: webview.windows[0].destroy()).start()
        return {"ok": True, "path": str(dest)}


def main():
    try:
        import webview
    except ImportError:
        sys.exit("pywebview is not installed — run run.bat (it installs it), or:\n"
                 "  python -m pip install pywebview")
    for d in (ws(), imports(), exports(), snapshots()):
        d.mkdir(parents=True, exist_ok=True)
    if FROZEN:
        # first run: seed the writable styles folder from the bundled defaults
        styles_dir().mkdir(parents=True, exist_ok=True)
        for f in (GEN / "styles").glob("*.json"):
            if not (styles_dir() / f.name).exists():
                shutil.copy2(f, styles_dir() / f.name)
    # size to the screen it opens on — 1500x950 is a postage stamp on a 4K panel
    w, h = 1500, 950
    try:
        scr = webview.screens[0]
        w, h = int(scr.width * 0.8), int(scr.height * 0.85)
        w, h = max(1200, min(w, 2600)), max(800, min(h, 1600))
    except Exception:
        pass
    window = webview.create_window(
        "LOK Studio", UI.as_uri(), js_api=Api(),
        width=w, height=h, background_color="#0a1014")
    webview.start(debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
