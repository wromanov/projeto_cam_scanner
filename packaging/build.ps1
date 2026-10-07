$ErrorActionPreference = 'Stop'

# Build scaffold for the future portable Windows ONEDIR distribution.
# This script does not publish or release artifacts.
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    pyinstaller --noconfirm --clean packaging/cam_scanner.spec
}
finally {
    Pop-Location
}
