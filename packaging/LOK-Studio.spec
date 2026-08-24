# PyInstaller spec — builds the packaged LOK Studio (one folder, zipped by CI).
# Bundled data (ui + generator) lands in _internal; main.py's FROZEN branch finds it
# via sys._MEIPASS and puts all user-written files in %LOCALAPPDATA%\LOK Studio.
# Build:  pyinstaller packaging/LOK-Studio.spec   (from the repo root)

a = Analysis(
    ['../app/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../app/ui', 'ui'),
        ('../generator', 'generator'),
    ],
    hiddenimports=[],
    hookspath=[],
    excludes=['tkinter'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LOK-Studio',
    debug=False,
    strip=False,
    upx=False,
    console=False,          # windowed app — no console flash
    icon='lok.ico',         # multi-res 16-256 (source: crystal-icon-1024.png + icon.svg)
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='LOK-Studio',
)
