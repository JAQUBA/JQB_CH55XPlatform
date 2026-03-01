"""
Arduino framework integration for CH55x (ch55xduino).

This script configures the build environment with ch55xduino core sources,
variant-specific includes, and any built-in libraries.

Part of JQB_CH55XPlatform:
  https://github.com/JAQUBA/JQB_CH55XPlatform
"""

import os
from os.path import isdir, join

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

# --- Add built-in libraries if user includes them ---

BUILTIN_LIBS_DIR = join(CH55X_DIR, "libraries")
if isdir(BUILTIN_LIBS_DIR):
    # Scan for built-in libraries that are used by the project
    for lib_name in os.listdir(BUILTIN_LIBS_DIR):
        lib_dir = join(BUILTIN_LIBS_DIR, lib_name)
        if not isdir(lib_dir):
            continue
        # Check for src/ subdirectory (standard Arduino library layout)
        lib_src = join(lib_dir, "src")
        if not isdir(lib_src):
            lib_src = lib_dir
        # Add to include path so headers can be found
        env.Append(CPPPATH=[lib_src])

env.Prepend(LIBS=libs)
