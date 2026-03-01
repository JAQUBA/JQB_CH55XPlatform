"""
Arduino framework integration for CH55x (ch55xduino).

This script configures the build environment with ch55xduino core sources,
variant-specific includes, and **auto-detected** built-in libraries.

Library auto-detection:
  Source files under src/ are scanned for #include directives.
  When a header matches a built-in ch55xduino library (e.g. WS2812.h),
  that library is compiled and linked automatically — no manual
  build_src_filter entries needed.

Part of JQB_CH55XPlatform:
  https://github.com/JAQUBA/JQB_CH55XPlatform
"""

import os
import re
from os.path import isdir, isfile, join

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

PLATFORMIO_PACKAGES = join(os.path.expanduser("~"), ".platformio", "packages")
FRAMEWORK_DIR = join(PLATFORMIO_PACKAGES, "framework-ch55xduino")

# ch55xduino core structure (inside ch55x/ subdirectory):
#   ch55x/cores/ch55xduino/   — Arduino core sources (.c, .h)
#   ch55x/variants/<variant>/ — Variant-specific files
#   ch55x/variants/<variant>/include/ — Chip register headers
#   ch55x/libraries/          — Built-in libraries (SPI, SoftI2C, WS2812, etc.)

# The ch55xduino tarball extracts to a ch55x/ subdirectory
CH55X_DIR = join(FRAMEWORK_DIR, "ch55x")
if not isdir(CH55X_DIR):
    # Fallback: maybe files are directly in FRAMEWORK_DIR
    CH55X_DIR = FRAMEWORK_DIR

CORE_DIR = join(CH55X_DIR, "cores", "ch55xduino")
VARIANT = board.get("build.variant", "ch552")
VARIANT_DIR = join(CH55X_DIR, "variants", VARIANT)
VARIANT_INCLUDE_DIR = join(VARIANT_DIR, "include")
BUILTIN_LIBS_DIR = join(CH55X_DIR, "libraries")

assert isdir(FRAMEWORK_DIR), (
    "Could not find ch55xduino framework directory: %s\n"
    "Run the setup script first.\n"
    "See: https://github.com/JAQUBA/JQB_CH55XPlatform#installation"
    % FRAMEWORK_DIR
)
assert isdir(CORE_DIR), (
    "Could not find ch55xduino core directory: %s" % CORE_DIR
)

# --- Include paths ---

env.Append(
    CPPPATH=[
        CORE_DIR,
        VARIANT_DIR,
    ]
)

# Add variant include directory if it exists (chip-specific register headers)
if isdir(VARIANT_INCLUDE_DIR):
    env.Append(CPPPATH=[VARIANT_INCLUDE_DIR])

# --- Build the Arduino core as a library ---

libs = []

libs.append(
    env.BuildLibrary(
        join("$BUILD_DIR", "FrameworkArduino"),
        CORE_DIR,
    )
)

# ---------------------------------------------------------------------------
# Built-in library auto-detection
#
# 1. Index all built-in libraries: map header names to library directories
# 2. Scan project source files for #include <Header.h> directives
# 3. Build and link every matched library automatically
# ---------------------------------------------------------------------------

_INCLUDE_RE = re.compile(r'^\s*#include\s*[<"]([^>"]+)[>"]', re.MULTILINE)


def _index_builtin_libraries(libs_dir):
    """Build a map: header_filename -> library_src_directory."""
    header_map = {}
    if not isdir(libs_dir):
        return header_map
    for lib_name in os.listdir(libs_dir):
        lib_dir = join(libs_dir, lib_name)
        if not isdir(lib_dir):
            continue
        lib_src = join(lib_dir, "src")
        if not isdir(lib_src):
            lib_src = lib_dir
        # Register every .h file in the library root src dir
        for f in os.listdir(lib_src):
            if f.lower().endswith('.h'):
                header_map[f] = (lib_name, lib_src)
    return header_map


def _scan_project_includes(src_dir):
    """Collect all #include'd header names from project source files."""
    headers = set()
    if not isdir(src_dir):
        return headers
    for root, _dirs, files in os.walk(src_dir):
        for fname in files:
            if not fname.endswith(('.c', '.h')):
                continue
            fpath = join(root, fname)
            try:
                with open(fpath, 'r', errors='ignore') as fp:
                    content = fp.read()
                for match in _INCLUDE_RE.finditer(content):
                    inc = match.group(1)
                    # Normalize: take basename (handles "subdir/header.h")
                    headers.add(os.path.basename(inc))
            except (IOError, OSError):
                pass
    return headers


# --- Detect and build required libraries ---

_header_map = _index_builtin_libraries(BUILTIN_LIBS_DIR)
_project_src = env.subst("$PROJECT_SRC_DIR")
_used_headers = _scan_project_includes(_project_src)

_built_libs = set()

for header_name in _used_headers:
    if header_name not in _header_map:
        continue
    lib_name, lib_src = _header_map[header_name]
    if lib_name in _built_libs:
        continue
    _built_libs.add(lib_name)

    # Add library include path
    env.AppendUnique(CPPPATH=[lib_src])

    # Build library (compiles all .c files recursively, including templates)
    libs.append(
        env.BuildLibrary(
            join("$BUILD_DIR", "Lib_%s" % lib_name),
            lib_src,
        )
    )
    print("Auto-detected library: %s (from #include <%s>)" % (lib_name, header_name))

# Also add include paths for ALL built-in libraries so headers are always
# resolvable (even if the library itself isn't compiled — for IDE support).
if isdir(BUILTIN_LIBS_DIR):
    for lib_name in os.listdir(BUILTIN_LIBS_DIR):
        lib_dir = join(BUILTIN_LIBS_DIR, lib_name)
        if not isdir(lib_dir):
            continue
        lib_src = join(lib_dir, "src")
        if not isdir(lib_src):
            lib_src = lib_dir
        env.AppendUnique(CPPPATH=[lib_src])

env.Prepend(LIBS=libs)
