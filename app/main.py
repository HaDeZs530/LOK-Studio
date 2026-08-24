#!/usr/bin/env python3
"""LOK Studio — desktop shell for the LOK Sketcher + generator.

Opens the sketcher UI in a native window (pywebview / Edge WebView2 on Windows) and
exposes the generator to the page through a small Python API (window.pywebview.api).

Phase 1: the UI is the existing sketcher, unchanged. The API below is the bridge the
UI will grow into (build / import / styles on disk instead of browser storage).
Merges and mask applies stay dry-run-first: nothing writes without an explicit
confirm=True from a human click.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent      # repo root
UI = ROOT / "app" / "ui" / "lok_sketcher.html"
GEN = ROOT / "generator"
WORKSPACE = ROOT / "workspace"                     # user data — gitignored
IMPORTS = WORKSPACE / "Imports"
EXPORTS = WORKSPACE / "Exports"
STYLES = GEN / "styles"


def _run(script, *args):
    """Run a generator script, capture its report."""
    cmd = [sys.executable, str(GEN / script), *[str(a) for a in args]]
    p = subprocess.run(cmd, capture_output=True, text=True)
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
