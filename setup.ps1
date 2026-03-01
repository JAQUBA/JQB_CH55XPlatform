<#
.SYNOPSIS
    Setup script for JQB CH55x PlatformIO Platform.
    Downloads and installs ch55xduino toolchain, framework, and upload tools.

.DESCRIPTION
    This script downloads the following packages from ch55xduino releases:
    - SDCC compiler (custom build with MCS51 support and proper libraries)
    - ch55xduino Arduino core framework
    - MCS51Tools (vnproch55x upload tool)

    Packages are installed into PlatformIO's packages directory (~/.platformio/packages/).

.LINK
    https://github.com/JAQUBA/JQB_CH55XPlatform

.NOTES
    Run: powershell -ExecutionPolicy Bypass -File setup.ps1
#>

$ErrorActionPreference = "Stop"

# --- Configuration ---

$PLATFORMIO_PACKAGES_DIR = Join-Path (Join-Path $env:USERPROFILE ".platformio") "packages"

$PACKAGES = @(
    @{
        Name        = "toolchain-sdcc-ch55x"
        Version     = "0.0.1"
        Description = "SDCC compiler for CH55x (MCS51)"
        Url         = "https://github.com/DeqingSun/ch55xduino/releases/download/0.0.20/sdcc-mcs51-i586-mingw32msvc-20220422-13407_4.tar.bz2"
        ArchiveFile = "sdcc-mcs51-i586-mingw32msvc-20220422-13407_4.tar.bz2"
        StripRoot   = "sdcc"
    },
    @{
        Name        = "framework-ch55xduino"
        Version     = "0.0.25"
        Description = "ch55xduino Arduino-like framework for CH55x MCUs"
        Url         = "https://github.com/DeqingSun/ch55xduino/releases/download/0.0.25/ch55xduino-core-0.0.25.tar.bz2"
        ArchiveFile = "ch55xduino-core-0.0.25.tar.bz2"
        StripRoot   = ""
    },
    @{
        Name        = "tool-ch55xtools"
        Version     = "0.0.1"
        Description = "CH55x upload tools (vnproch55x)"
        Url         = "https://github.com/DeqingSun/ch55xduino/releases/download/0.0.20/ch55xduino-tools_mingw32-2023.10.10.tar.bz2"
        ArchiveFile = "ch55xduino-tools_mingw32-2023.10.10.tar.bz2"
        StripRoot   = "ch55xduino"
    }
)

# --- Helper Functions ---

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Download-File {
    param([string]$Url, [string]$OutFile)
    Write-Host "  Downloading: $Url" -ForegroundColor Cyan
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
    $ProgressPreference = 'Continue'
}

function Extract-TarBz2 {
    param([string]$Archive, [string]$Destination)
    Write-Host "  Extracting to: $Destination" -ForegroundColor Cyan

    # Use tar (available on Windows 10+)
    if (Get-Command "tar" -ErrorAction SilentlyContinue) {
        & tar -xjf $Archive -C $Destination
    } else {
        # Fallback: use 7-Zip if available
        $sevenZip = "C:\Program Files\7-Zip\7z.exe"
        if (Test-Path $sevenZip) {
            $tarFile = $Archive -replace '\.bz2$', ''
            & $sevenZip x $Archive -o"$(Split-Path $Archive)" -y | Out-Null
            & $sevenZip x $tarFile -o"$Destination" -y | Out-Null
            Remove-Item $tarFile -Force -ErrorAction SilentlyContinue
        } else {
            throw "Cannot extract .tar.bz2: neither 'tar' nor '7-Zip' found. Install one of them."
        }
    }
}

function Create-PackageJson {
    param(
        [string]$Directory,
        [string]$Name,
        [string]$Version,
        [string]$Description
    )
    $packageJson = @{
        name        = $Name
        version     = $Version
        description = $Description
    } | ConvertTo-Json -Depth 2

    $packageJsonPath = Join-Path $Directory "package.json"
    $packageJson | Out-File -FilePath $packageJsonPath -Encoding utf8 -Force
}

# --- Main ---

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " JQB CH55x Platform — Toolchain Setup" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

Ensure-Directory $PLATFORMIO_PACKAGES_DIR

$tempDir = Join-Path $env:TEMP "ch55x_setup"
Ensure-Directory $tempDir

foreach ($pkg in $PACKAGES) {
    $pkgDir = Join-Path $PLATFORMIO_PACKAGES_DIR $pkg.Name

    # Check if already installed
    if ((Test-Path $pkgDir) -and (Test-Path (Join-Path $pkgDir "package.json"))) {
        Write-Host "[SKIP] $($pkg.Name) already installed at $pkgDir" -ForegroundColor Yellow
        continue
    }

    Write-Host "[INSTALL] $($pkg.Name) v$($pkg.Version)" -ForegroundColor Green

    # Download
    $archivePath = Join-Path $tempDir $pkg.ArchiveFile
    if (-not (Test-Path $archivePath)) {
        Download-File -Url $pkg.Url -OutFile $archivePath
    } else {
        Write-Host "  Using cached archive: $archivePath" -ForegroundColor DarkGray
    }

    # Extract to temp directory first
    $extractDir = Join-Path $tempDir ($pkg.Name + "_extract")
    if (Test-Path $extractDir) {
        Remove-Item $extractDir -Recurse -Force
    }
    Ensure-Directory $extractDir
    Extract-TarBz2 -Archive $archivePath -Destination $extractDir

    # Move to final location, stripping root directory if needed
    if (Test-Path $pkgDir) {
        Remove-Item $pkgDir -Recurse -Force
    }

    if ($pkg.StripRoot -and $pkg.StripRoot -ne "") {
        $sourceDir = Join-Path $extractDir $pkg.StripRoot
        if (Test-Path $sourceDir) {
            Move-Item -Path $sourceDir -Destination $pkgDir -Force
        } else {
            Write-Host "  Warning: Expected subdirectory '$($pkg.StripRoot)' not found, using root" -ForegroundColor Yellow
            Move-Item -Path $extractDir -Destination $pkgDir -Force
        }
    } else {
        Move-Item -Path $extractDir -Destination $pkgDir -Force
    }

    # Create package.json for PlatformIO
    Create-PackageJson -Directory $pkgDir `
                       -Name $pkg.Name `
                       -Version $pkg.Version `
                       -Description $pkg.Description

    Write-Host "  Installed to: $pkgDir" -ForegroundColor Green

    # Cleanup extract temp
    if (Test-Path $extractDir) {
        Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Cleanup temp downloads
Write-Host ""
Write-Host "Cleaning up temporary files..." -ForegroundColor DarkGray
Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue

# --- Verification ---

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " Verification" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

$allOk = $true
foreach ($pkg in $PACKAGES) {
    $pkgDir = Join-Path $PLATFORMIO_PACKAGES_DIR $pkg.Name
    if (Test-Path $pkgDir) {
        Write-Host "[OK] $($pkg.Name)" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $($pkg.Name) - not found" -ForegroundColor Red
        $allOk = $false
    }
}

# Verify SDCC binary
$sdccExe = Join-Path (Join-Path (Join-Path $PLATFORMIO_PACKAGES_DIR "toolchain-sdcc-ch55x") "bin") "sdcc.exe"
if (Test-Path $sdccExe) {
    Write-Host "[OK] SDCC compiler found" -ForegroundColor Green
} else {
    Write-Host "[FAIL] SDCC compiler not found at $sdccExe" -ForegroundColor Red
    $allOk = $false
}

# Verify vnproch55x
$vnprochExe = Join-Path (Join-Path (Join-Path $PLATFORMIO_PACKAGES_DIR "tool-ch55xtools") "win") "vnproch55x.exe"
if (-not (Test-Path $vnprochExe)) {
    # Try tools/win/vnproch55x.exe (some tarball layouts)
    $vnprochExe = Join-Path $PLATFORMIO_PACKAGES_DIR "tool-ch55xtools" "tools" "win" "vnproch55x.exe"
}
if (Test-Path $vnprochExe) {
    Write-Host "[OK] Upload tool (vnproch55x) found" -ForegroundColor Green
} else {
    Write-Host "[WARN] Upload tool (vnproch55x) not found" -ForegroundColor Yellow
}

# Verify framework core
$coreDir = Join-Path $PLATFORMIO_PACKAGES_DIR "framework-ch55xduino" "ch55x" "cores" "ch55xduino"
if (Test-Path $coreDir) {
    Write-Host "[OK] ch55xduino core found" -ForegroundColor Green
} else {
    Write-Host "[FAIL] ch55xduino core not found at $coreDir" -ForegroundColor Red
    $allOk = $false
}

Write-Host ""
if ($allOk) {
    Write-Host "Setup complete! You can now build with: pio run" -ForegroundColor Green
} else {
    Write-Host "Setup completed with errors. Please check the messages above." -ForegroundColor Red
}
Write-Host ""
