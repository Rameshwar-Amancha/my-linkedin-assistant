# build.ps1 — Package the extension for Chrome/Edge and Firefox
#
# Usage:
#   .\build.ps1                # Build all targets
#   .\build.ps1 -Target chrome # Build Chrome/Edge only
#   .\build.ps1 -Target firefox # Build Firefox only
#
# Output: dist\lea-chrome-<version>.zip and dist\lea-firefox-<version>.zip

param(
    [ValidateSet('all', 'chrome', 'firefox')]
    [string]$Target = 'all'
)

$ErrorActionPreference = 'Stop'

# Read version from manifest
$manifest = Get-Content -Raw "$PSScriptRoot\extension\manifest.json" | ConvertFrom-Json
$version = $manifest.version

$distDir = "$PSScriptRoot\dist"
if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
}

# Files to include in both builds (relative to extension/)
$extensionRoot = "$PSScriptRoot\extension"

function Build-Chrome {
    $zipName = "lea-chrome-edge-v$version.zip"
    $zipPath = "$distDir\$zipName"

    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

    Write-Host "Building Chrome/Edge package: $zipName" -ForegroundColor Cyan

    # Compress the extension folder (uses the default manifest.json)
    Compress-Archive -Path "$extensionRoot\*" -DestinationPath $zipPath `
        -CompressionLevel Optimal

    # Remove Firefox-specific files from the archive by re-creating without them
    $tmpDir = "$distDir\_chrome_tmp"
    if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }
    New-Item -ItemType Directory -Path $tmpDir | Out-Null

    Copy-Item -Recurse "$extensionRoot\*" -Destination $tmpDir

    # Remove Firefox-only manifest from Chrome build
    Remove-Item "$tmpDir\manifest.firefox.json" -ErrorAction SilentlyContinue

    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    Compress-Archive -Path "$tmpDir\*" -DestinationPath $zipPath -CompressionLevel Optimal

    Remove-Item $tmpDir -Recurse -Force
    Write-Host "  -> $zipPath" -ForegroundColor Green
}

function Build-Firefox {
    $zipName = "lea-firefox-v$version.zip"
    $zipPath = "$distDir\$zipName"

    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

    Write-Host "Building Firefox package: $zipName" -ForegroundColor Cyan

    $tmpDir = "$distDir\_firefox_tmp"
    if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }
    New-Item -ItemType Directory -Path $tmpDir | Out-Null

    Copy-Item -Recurse "$extensionRoot\*" -Destination $tmpDir

    # Swap manifest: replace manifest.json with manifest.firefox.json
    Remove-Item "$tmpDir\manifest.json"
    Rename-Item "$tmpDir\manifest.firefox.json" "manifest.json"

    Compress-Archive -Path "$tmpDir\*" -DestinationPath $zipPath -CompressionLevel Optimal

    Remove-Item $tmpDir -Recurse -Force
    Write-Host "  -> $zipPath" -ForegroundColor Green
}

switch ($Target) {
    'chrome'  { Build-Chrome }
    'firefox' { Build-Firefox }
    'all'     { Build-Chrome; Build-Firefox }
}

Write-Host ""
Write-Host "Done. Packages saved to: $distDir" -ForegroundColor Yellow
Write-Host ""
Write-Host "Load in Chrome/Edge:" -ForegroundColor White
Write-Host "  1. Extract lea-chrome-edge-v$version.zip"
Write-Host "  2. chrome://extensions -> Developer mode ON -> Load unpacked -> select extracted folder"
Write-Host ""
Write-Host "Load in Firefox:" -ForegroundColor White
Write-Host "  1. about:debugging -> This Firefox -> Load Temporary Add-on -> select lea-firefox-v$version.zip"
Write-Host "  OR for permanent install: Submit to https://addons.mozilla.org"
