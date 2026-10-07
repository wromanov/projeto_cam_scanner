# Scaffold PyInstaller ONEDIR. Datas and hidden imports will be defined after
# implementation and validation of the modules that need them.
block_cipher = None

a = Analysis(
    ["../src/cam_scanner/__main__.py"],
    pathex=["../src"],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="cam-scanner", console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="cam-scanner")
