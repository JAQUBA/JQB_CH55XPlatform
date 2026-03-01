"""
JQB CH55x Platform — PlatformIO platform class.

Supports WCH CH551, CH552, CH554, CH559 MCS51 USB microcontrollers
using the ch55xduino Arduino-like framework and SDCC compiler.

Packages (SDCC toolchain, ch55xduino core, upload tools) are
auto-downloaded on first build — no manual setup required.
"""

import json
import os
import shutil
import sys
import tarfile
from os.path import isdir, isfile, join

from platformio.public import PlatformBase

# ---------------------------------------------------------------------------
# Package definitions with download URLs per OS
# ---------------------------------------------------------------------------

_PACKAGES = [
    {
        "name": "toolchain-sdcc-ch55x",
        "version": "0.0.1",
        "description": "SDCC compiler for CH55x (MCS51)",
        "strip_root": "sdcc",
        "urls": {
            "win32":  "https://github.com/DeqingSun/ch55xduino/releases/download/0.0.20/sdcc-mcs51-i586-mingw32msvc-20220422-13407_4.tar.bz2",
            "darwin": "https://github.com/DeqingSun/ch55xduino/releases/download/0.0.20/sdcc-mcs51-i386-apple-darwin14.0.0-20220422-13407_4.tar.bz2",
            "linux":  "https://github.com/DeqingSun/ch55xduino/releases/download/0.0.20/sdcc-mcs51-i386-unknown-linux2.5-20220422-13407_4.tar.bz2",
        },
    },
    {
        "name": "framework-ch55xduino",
        "version": "0.0.25",
        "description": "ch55xduino Arduino-like framework for CH55x MCUs",
        "strip_root": "",
        "urls": {
            "*": "https://github.com/DeqingSun/ch55xduino/releases/download/0.0.25/ch55xduino-core-0.0.25.tar.bz2",
        },
    },
    {
        "name": "tool-ch55xtools",
        "version": "0.0.1",
        "description": "CH55x upload tools (vnproch55x)",
        "strip_root": "",
        "urls": {
            "win32":  "https://github.com/DeqingSun/ch55xduino/releases/download/0.0.20/ch55xduino-tools_mingw32-2023.10.10.tar.bz2",
            "darwin": "https://github.com/DeqingSun/ch55xduino/releases/download/0.0.20/ch55xduino-tools_macOS-2023.10.10.tar.bz2",
            "linux":  "https://github.com/DeqingSun/ch55xduino/releases/download/0.0.20/ch55xduino-tools_linuxamd64-2023.10.10.tar.bz2",
        },
    },
]


def _get_packages_dir():
    """Return PlatformIO packages directory."""
    pio_home = os.environ.get(
        "PLATFORMIO_HOME_DIR",
        join(os.path.expanduser("~"), ".platformio")
    )
    return join(pio_home, "packages")


def _get_url(pkg):
    """Select the correct download URL for the current OS."""
    urls = pkg["urls"]
    if "*" in urls:
        return urls["*"]
    key = sys.platform
    if key in urls:
        return urls[key]
    if key.startswith("linux"):
        return urls.get("linux", "")
    raise RuntimeError(
        "No download URL for package '%s' on platform '%s'" % (pkg["name"], key)
    )


def _download(url, dest_path):
    """Download a file from URL with progress indication."""
    from urllib.request import urlretrieve

    def _progress(count, block_size, total_size):
        if total_size > 0:
            pct = min(100, count * block_size * 100 // total_size)
            sys.stdout.write("\r  Downloading: %d%%" % pct)
            sys.stdout.flush()

    urlretrieve(url, dest_path, _progress)
    sys.stdout.write("\r  Downloading: done   \n")
    sys.stdout.flush()


def _install_package(pkg, packages_dir):
    """Download, extract and install a single CH55x package."""
    pkg_dir = join(packages_dir, pkg["name"])

    # Already installed — skip
    if isdir(pkg_dir) and isfile(join(pkg_dir, "package.json")):
        return

    url = _get_url(pkg)
    print("[CH55x] Installing %s ..." % pkg["name"])

    # Use a temp directory next to the final location for atomic-ish install
    tmp_dir = join(packages_dir, "_ch55x_tmp_%s" % pkg["name"])
    try:
        if isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir)

        # Download
        archive_path = join(tmp_dir, "archive.tar.bz2")
        _download(url, archive_path)

        # Extract
        print("  Extracting...")
        extract_dir = join(tmp_dir, "extract")
        os.makedirs(extract_dir)
        with tarfile.open(archive_path, "r:bz2") as tar:
            try:
                tar.extractall(extract_dir, filter="data")
            except TypeError:
                tar.extractall(extract_dir)

        # Determine source (with optional root stripping)
        if pkg["strip_root"]:
            source_dir = join(extract_dir, pkg["strip_root"])
        else:
            source_dir = extract_dir

        if not isdir(source_dir):
            raise RuntimeError(
                "Expected directory '%s' not found after extraction" % source_dir
            )

        # Move to final location
        if isdir(pkg_dir):
            shutil.rmtree(pkg_dir)
        shutil.move(source_dir, pkg_dir)

        # Create package.json for PlatformIO
        pkg_json = {
            "name": pkg["name"],
            "version": pkg["version"],
            "description": pkg["description"],
        }
        with open(join(pkg_dir, "package.json"), "w") as f:
            json.dump(pkg_json, f, indent=2)

        print("[CH55x] %s installed successfully" % pkg["name"])

    except Exception as e:
        print("[CH55x] ERROR installing %s: %s" % (pkg["name"], e))
        raise
    finally:
        if isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass


class Ch55xPlatform(PlatformBase):

    def configure_default_packages(self, variables, targets):
        # Auto-install packages if any are missing
        packages_dir = _get_packages_dir()
        if not isdir(packages_dir):
            os.makedirs(packages_dir)

        for pkg in _PACKAGES:
            _install_package(pkg, packages_dir)

        # Declare packages for PlatformIO (all optional — we manage them)
        for pkg_name, pkg_meta in {
            "toolchain-sdcc-ch55x": {"type": "toolchain", "optional": True},
            "framework-ch55xduino": {"type": "framework", "optional": True},
            "tool-ch55xtools":      {"type": "uploader",  "optional": True},
        }.items():
            if pkg_name not in self.packages:
                self.packages[pkg_name] = dict(pkg_meta)

        return super().configure_default_packages(variables, targets)
