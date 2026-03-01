"""
SCons build script for WCH CH55x platform using SDCC compiler.
Based on ch55xduino Arduino core.

Part of JQB_CH55XPlatform:
  https://github.com/JAQUBA/JQB_CH55XPlatform
"""

import os
import sys
from os.path import isdir, isfile, join

from SCons.Script import (
    ARGUMENTS,
    COMMAND_LINE_TARGETS,
    AlwaysBuild,
    Builder,
    Default,
    DefaultEnvironment,
)

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

# ---------------------------------------------------------------------------
# Resolve package directories
# Packages are installed by setup.ps1 into ~/.platformio/packages/
# ---------------------------------------------------------------------------

PLATFORMIO_PACKAGES = join(os.path.expanduser("~"), ".platformio", "packages")

toolchain_dir = join(PLATFORMIO_PACKAGES, "toolchain-sdcc-ch55x")
framework_dir = join(PLATFORMIO_PACKAGES, "framework-ch55xduino")
tools_dir = join(PLATFORMIO_PACKAGES, "tool-ch55xtools")

assert isdir(toolchain_dir), (
    "SDCC toolchain not found at: %s\n"
    "Run the setup script first.\n"
    "See: https://github.com/JAQUBA/JQB_CH55XPlatform#installation"
    % toolchain_dir
)

sdcc_bin = join(toolchain_dir, "bin")

# SDCC library path — ch55xduino's custom SDCC uses large_int_calc_stack_auto
sdcc_lib_path = None
for candidate in [
    join(toolchain_dir, "lib", "large_int_calc_stack_auto"),
    join(toolchain_dir, "share", "sdcc", "lib", "large_int_calc_stack_auto"),
]:
    if isdir(candidate):
        sdcc_lib_path = candidate
        break

if sdcc_lib_path is None:
    # Fallback to standard large model
    for candidate in [
        join(toolchain_dir, "lib", "large"),
        join(toolchain_dir, "share", "sdcc", "lib", "large"),
    ]:
        if isdir(candidate):
            sdcc_lib_path = candidate
            break

# SDCC include path
sdcc_include_path = None
for candidate in [
    join(toolchain_dir, "include"),
    join(toolchain_dir, "share", "sdcc", "include"),
]:
    if isdir(candidate):
        sdcc_include_path = candidate
        break

# ---------------------------------------------------------------------------
# Configure build environment
# ---------------------------------------------------------------------------

env.Replace(
    AR=join(sdcc_bin, "sdar"),
    AS=join(sdcc_bin, "sdas8051"),
    CC=join(sdcc_bin, "sdcc"),
    CXX=join(sdcc_bin, "sdcc"),
    LINK=join(sdcc_bin, "sdcc"),
    OBJCOPY="",
    RANLIB="",
    SIZETOOL="",

    ARFLAGS=["rcs"],

    ASFLAGS=["-x", "assembler-with-cpp"],

    CFLAGS=[],

    CCFLAGS=[
        "-c",
        "-Ddouble=float",
        "-DUSE_STDINT",
        "-D__PROG_TYPES_COMPAT__",
        "--model-large",
        "--int-long-reent",
        "-mmcs51",
    ],

    CXXFLAGS=[],

    CPPDEFINES=[
        board.get("build.mcu"),
        ("F_CPU", board.get("build.f_cpu")),
        ("F_EXT_OSC", board.get("build.f_osc_external", "0L")),
        ("ARDUINO", 10819),
        "ARDUINO_%s" % board.get("build.board"),
        "ARDUINO_ARCH_mcs51",
    ],

    LINKFLAGS=[
        "--nostdlib",
        "--code-size", str(board.get("upload.maximum_size")),
        "--xram-size", str(board.get("upload.maximum_ram_size")),
        "--xram-loc", str(board.get("upload.xdata_location")),
        "-mmcs51",
        "--out-fmt-ihx",
    ],

    LIBS=["mcs51", "libsdcc", "liblong", "liblonglong", "libint", "libfloat"],
    LIBPATH=[sdcc_lib_path] if sdcc_lib_path else [],

    # SDCC-specific file extensions
    OBJSUFFIX=".rel",
    LIBSUFFIX=".lib",
    PROGSUFFIX=".ihx",

    LIBPREFIX="",
    LIBLINKPREFIX="-l",
    LIBLINKSUFFIX="",

    # Build commands for SDCC
    ARCOM="$AR $ARFLAGS $TARGET $SOURCES",
    CCCOM="$CC $CCFLAGS $CFLAGS $CPPFLAGS $_CPPDEFFLAGS $_CPPINCFLAGS -o $TARGET $SOURCES",
    CXXCOM="$CXX $CCFLAGS $CXXFLAGS $CPPFLAGS $_CPPDEFFLAGS $_CPPINCFLAGS -o $TARGET $SOURCES",
    LINKCOM="$LINK $LINKFLAGS $_LIBDIRFLAGS -o $TARGET $SOURCES $_LIBFLAGS",

    # Size tool patterns (for .mem file parsing)
    SIZEPROGREGEXP=r"^(?:\s+ROM\/EPROM\/FLASH)\s+0x[A-Fa-f0-9]+\s+0x[A-Fa-f0-9]+\s+(\d+)",
    SIZEDATAREGEXP=r"^(?:\s+EXTERNAL RAM)\s+0x[A-Fa-f0-9]+\s+0x[A-Fa-f0-9]+\s+(\d+)",
)

# Add SDCC include path
if sdcc_include_path:
    env.Append(CPPPATH=[sdcc_include_path])

# Board-specific extra flags (e.g., USB endpoint defines)
extra_flags = board.get("build.extra_flags", "")
if extra_flags:
    env.Append(CCFLAGS=extra_flags.split())

# ---------------------------------------------------------------------------
# Process framework
# Load framework manually before BuildProgram to avoid PlatformIO's
# path resolution issues with local/remote platforms.
# ---------------------------------------------------------------------------

_platform_dir = os.path.abspath(platform.get_dir())
_framework_script = join(_platform_dir, "builder", "frameworks", "arduino.py")

if "PIOFRAMEWORK" in env and isfile(_framework_script):
    env.SConscript(_framework_script, exports="env")

# Remove PIOFRAMEWORK so BuildProgram doesn't try to load it again
# (it would fail due to path doubling with local platforms)
_saved_framework = env.get("PIOFRAMEWORK", [])
env["PIOFRAMEWORK"] = []

# ---------------------------------------------------------------------------
# Auto-generate VS Code IntelliSense configuration
# Produces .vscode/c_cpp_properties.json with correct include paths,
# defines and a forcedInclude of sdcc_compat.h so IntelliSense understands
# SDCC-specific keywords (__xdata, __sfr, __at, etc.).
# ---------------------------------------------------------------------------

import json as _json


def _generate_ide_config(env):
    project_dir = env.subst("$PROJECT_DIR")
    vscode_dir = join(project_dir, ".vscode")

    # --- Collect include paths from build environment ---
    includes = []
    seen = set()
    for p in env.get("CPPPATH", []):
        path = os.path.abspath(str(p)).replace("\\", "/")
        if path not in seen:
            seen.add(path)
            includes.append(path)
    # Source directory (recursive) for user headers
    src_dir = join(project_dir, "src").replace("\\", "/")
    includes.append(src_dir + "/**")

    # --- Collect defines ---
    defines = []

    # 1) CPPDEFINES set by the builder and framework
    for d in env.get("CPPDEFINES", []):
        if isinstance(d, (list, tuple)) and len(d) == 2:
            defines.append("%s=%s" % (d[0], d[1]))
        elif isinstance(d, (list, tuple)):
            for item in d:
                s = str(item)
                if s:
                    defines.append(s)
        else:
            s = str(d)
            if s:
                defines.append(s)

    # 2) -D flags embedded in CCFLAGS (e.g. -Ddouble=float, -DUSE_STDINT)
    for flag in env.Flatten(env.get("CCFLAGS", [])):
        fs = str(flag)
        if fs.startswith("-D"):
            d = fs[2:]
            if d and d not in defines:
                defines.append(d)

    # 3) User build_flags from platformio.ini (e.g. -DUSER_USB_RAM=148)
    try:
        raw = env.GetProjectOption("build_flags", "")
        parts = raw.split() if isinstance(raw, str) else env.Flatten(raw)
        for flag in parts:
            fs = str(flag).strip()
            if fs.startswith("-D"):
                d = fs[2:]
                if d and d not in defines:
                    defines.append(d)
    except Exception:
        pass

    # --- SDCC compatibility header (forced include) ---
    # Resolved relative to the platform directory (works for both local
    # and remote/git-installed platforms).
    compat_header = join(_platform_dir, "sdcc_compat.h").replace("\\", "/")

    config = {
        "configurations": [{
            "name": "CH55x",
            "includePath": includes,
            "defines": defines,
            "forcedInclude": [compat_header],
            "compilerPath": "",
            "cStandard": "c11",
            "intelliSenseMode": "gcc-x86"
        }],
        "version": 4
    }

    config_json = _json.dumps(config, indent=4)
    config_path = join(vscode_dir, "c_cpp_properties.json")

    # Write only when content actually changed (avoids IntelliSense churn)
    try:
        with open(config_path, "r") as f:
            if f.read() == config_json:
                return
    except (IOError, OSError):
        pass

    if not isdir(vscode_dir):
        os.makedirs(vscode_dir)
    with open(config_path, "w") as f:
        f.write(config_json)
    print("Generated IntelliSense config: %s" % config_path)


_generate_ide_config(env)

# ---------------------------------------------------------------------------
# Build program
# ---------------------------------------------------------------------------

target_firm = env.BuildProgram()

# Restore (in case anything else needs it)
env["PIOFRAMEWORK"] = _saved_framework

# ---------------------------------------------------------------------------
# Convert .ihx to .bin
# vnproch55x expects a .bin file.  We convert using a Python-based ihx parser
# since makebin is not available in this SDCC build.
# ---------------------------------------------------------------------------

import struct


def ihx_to_bin(target, source, env):
    """Convert Intel HEX (.ihx) to raw binary (.bin)."""
    ihx_path = str(source[0])
    bin_path = str(target[0])
    data = {}
    min_addr = 0xFFFFFFFF
    max_addr = 0

    with open(ihx_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line[0] != ':':
                continue
            byte_count = int(line[1:3], 16)
            address = int(line[3:7], 16)
            record_type = int(line[7:9], 16)
            if record_type == 0:  # Data record
                for i in range(byte_count):
                    byte_val = int(line[9 + i*2:11 + i*2], 16)
                    data[address + i] = byte_val
                if address < min_addr:
                    min_addr = address
                addr_end = address + byte_count - 1
                if addr_end > max_addr:
                    max_addr = addr_end
            elif record_type == 1:  # EOF
                break

    if not data:
        print("Error: No data in IHX file")
        return 1

    size = max_addr - min_addr + 1
    bin_data = bytearray([0xFF] * size)
    for addr, val in data.items():
        bin_data[addr - min_addr] = val

    with open(bin_path, "wb") as f:
        f.write(bin_data)

    print("Converted %s -> %s (%d bytes)" % (ihx_path, bin_path, size))
    return 0


# Create .bin target from .ihx
target_bin = env.Command(
    join("$BUILD_DIR", "program.bin"),
    target_firm,
    env.Action(ihx_to_bin, "Converting IHX to BIN")
)

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

if "upload" in COMMAND_LINE_TARGETS:
    # The tools tarball extracts to tools/ subdirectory
    tools_subdir = join(tools_dir, "tools")
    if not isdir(tools_subdir):
        tools_subdir = tools_dir

    if sys.platform == "win32":
        uploader_path = join(tools_subdir, "win", "vnproch55x")
    elif sys.platform == "darwin":
        uploader_path = join(tools_subdir, "macosx", "vnproch55x")
    else:
        uploader_path = join(tools_subdir, "linux", "vnproch55x")

    env.Replace(
        UPLOADER=uploader_path,
        UPLOADERFLAGS=[
            "-r", "2",
            "-t", board.get("build.mcu"),
            "-c", str(board.get("upload.boot_config", 3)),
        ],
        UPLOADCMD='"$UPLOADER" $UPLOADERFLAGS "$SOURCE"'
    )

    # Custom upload action that ignores verify errors from vnproch55x.
    # The tool writes firmware correctly but verification may fail on some
    # bootloader versions ("Packet N doesn't match.").  We check the output
    # for "Write complete!!!" to confirm success.
    import subprocess

    def upload_ch55x(target, source, env):
        cmd = env.subst('"$UPLOADER" $UPLOADERFLAGS "%s"' % source[0])
        print("Uploading %s" % source[0])
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        output = b""
        while True:
            chunk = proc.stdout.read(1)
            if not chunk:
                break
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            output += chunk
        proc.wait()
        output_str = output.decode("utf-8", errors="replace")
        if "Write complete!!!" in output_str:
            if proc.returncode != 0:
                print(
                    "Warning: Verify failed but write was successful "
                    "— firmware is OK."
                )
            return 0
        return proc.returncode

    upload_actions = [
        env.Action(upload_ch55x, "Uploading $SOURCE")
    ]

    AlwaysBuild(env.Alias("upload", target_bin, upload_actions))

# ---------------------------------------------------------------------------
# Default target
# ---------------------------------------------------------------------------

Default([target_firm])
