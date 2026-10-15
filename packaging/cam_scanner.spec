"""Offline ONEDIR collection manifest; validation/build is intentionally deferred to P12."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

PROJECT_ROOT = Path(SPECPATH).resolve().parent.parent
datas = collect_data_files("onvif", includes=["wsdl/**/*.wsdl"])
datas += collect_data_files("certifi")
datas.append((str(PROJECT_ROOT / "config" / "settings.example.toml"), "config"))

# These packages load native libraries dynamically; collect their declared runtime DLLs.
binaries = collect_dynamic_libs("av")
binaries += collect_dynamic_libs("lxml")
binaries += collect_dynamic_libs("PIL")

hiddenimports = [
    "onvif.client",
    "zeep.transports",
    "zeep.wsse.username",
    "requests",
    "lxml.etree",
    "av",
    "PIL.Image",
    "PIL.ImageOps",
    "openpyxl",
    "openpyxl.styles",
    "openpyxl.drawing.image",
    "rich.progress",
]

block_cipher = None
a = Analysis(
    [str(PROJECT_ROOT / "src" / "cam_scanner" / "__main__.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="cam-scanner", console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="cam-scanner")
