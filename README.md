# JQB CH55x Platform

**PlatformIO platform for WCH CH55x (CH551, CH552, CH554, CH559) MCS51 USB microcontrollers.**

Uses the [ch55xduino](https://github.com/DeqingSun/ch55xduino) Arduino-like framework and a custom SDCC compiler build optimized for CH55x. Includes auto-generated VS Code IntelliSense configuration with full SDCC keyword support.

## Features

- **SDCC compiler** — custom MCS51 build with `large_int_calc_stack_auto` model
- **ch55xduino framework** — Arduino-like API (`pinMode`, `digitalRead`, `analogRead`, `delay`, `millis`, USB HID, EEPROM, etc.)
- **vnproch55x uploader** — flash firmware over USB bootloader with automatic verify-error handling
- **VS Code IntelliSense** — auto-generated `c_cpp_properties.json` with SDCC keyword stubs (`__xdata`, `__sfr`, `__at`, etc.)
- **IHX → BIN conversion** — built-in Python converter (no external `makebin` dependency)

## Supported MCUs

| MCU | Flash | XRAM | IRAM | USB | Board file |
|-----|-------|------|------|-----|------------|
| **CH552G** | 14 KB (16 KB − 2 KB bootloader) | 1 KB | 256 B | Full-speed Device | `ch552g` |

> More board definitions can be added — see [Adding a new board](#adding-a-new-board).

## Installation

### 1. Install PlatformIO

Follow the [PlatformIO installation guide](https://docs.platformio.org/en/latest/core/installation/index.html) or install the VS Code extension.

### 2. Run the setup script

The setup script downloads and installs the SDCC toolchain, ch55xduino framework, and upload tools into `~/.platformio/packages/`:

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

This installs:

| Package | Description |
|---------|-------------|
| `toolchain-sdcc-ch55x` | SDCC compiler (custom MCS51 build) |
| `framework-ch55xduino` | ch55xduino Arduino core |
| `tool-ch55xtools` | vnproch55x upload tool |

### 3. Reference the platform in your project

In your `platformio.ini`:

```ini
[env:firmware]
platform = https://github.com/JAQUBA/JQB_CH55XPlatform.git
board = ch552g
framework = arduino
```

Or use a local path during development:

```ini
[env:firmware]
platform = /path/to/JQB_CH55XPlatform
board = ch552g
framework = arduino
```

## Quick Start

### Minimal `platformio.ini`

```ini
[env:firmware]
platform = https://github.com/JAQUBA/JQB_CH55XPlatform.git
board = ch552g
framework = arduino
build_flags =
    -DUSER_USB_RAM=0
```

### Minimal `src/main.c`

```c
#include <Arduino.h>

#define LED_PIN 34  // P3.4

void setup() {
    pinMode(LED_PIN, OUTPUT);
}

void loop() {
    digitalWrite(LED_PIN, HIGH);
    delay(500);
    digitalWrite(LED_PIN, LOW);
    delay(500);
}
```

### Build & Upload

```bash
# Build
pio run

# Upload (CH552 must be in bootloader mode)
pio run -t upload
```

## Configuration

### Board-level options (`boards/ch552g.json`)

| Option | Default | Description |
|--------|---------|-------------|
| `build.f_cpu` | `24000000L` | CPU clock frequency |
| `build.mcu` | `CH552` | MCU type (used as `-D` define) |
| `build.variant` | `ch552` | ch55xduino variant directory |
| `upload.maximum_size` | `14336` | Flash size in bytes |
| `upload.maximum_ram_size` | `1024` | XRAM size in bytes |
| `upload.xdata_location` | `0` | XRAM start address |
| `upload.boot_config` | `3` | Bootloader config byte |

### Project-level overrides (`platformio.ini`)

Override any board option:

```ini
[env:firmware]
platform = https://github.com/JAQUBA/JQB_CH55XPlatform.git
board = ch552g
framework = arduino

; Custom USB endpoint allocation — reduce available XRAM
board_upload.maximum_ram_size = 876
board_upload.xdata_location = 148

build_flags =
    -DUSER_USB_RAM=148
    -DEP0_ADDR=0
    -DEP1_ADDR=10
    -DEP2_ADDR=20
```

## Project Structure

```
JQB_CH55XPlatform/
├── platform.json          — PlatformIO platform manifest
├── platform.py            — Platform class
├── sdcc_compat.h          — SDCC keyword stubs for IntelliSense
├── setup.ps1              — Toolchain installer (Windows)
├── boards/
│   └── ch552g.json        — WCH CH552G board definition
└── builder/
    ├── main.py            — SCons build script (SDCC + IHX→BIN + upload)
    └── frameworks/
        └── arduino.py     — ch55xduino framework integration
```

## How It Works

### Build Pipeline

```
Source (.c) → SDCC → Object (.rel) → SDCC Linker → Intel HEX (.ihx) → BIN → vnproch55x → CH55x
```

1. **SDCC** compiles `.c` files with `--model-large --int-long-reent -mmcs51`
2. **SDCC linker** produces `.ihx` (Intel HEX)
3. **Built-in IHX→BIN converter** creates raw binary
4. **vnproch55x** flashes via USB bootloader

### IntelliSense

On every `pio run`, the builder auto-generates `.vscode/c_cpp_properties.json` with:
- All include paths (SDCC stdlib, ch55xduino core, variant, libraries, project `src/`)
- All `-D` defines from board config, CCFLAGS, and `build_flags`
- Force-include of `sdcc_compat.h` — maps SDCC keywords to standard C equivalents

This means **zero manual VS Code configuration** for CH55x projects.

### Upload

The uploader wraps `vnproch55x` with smart error handling:
- Streams output in real-time
- Detects `"Write complete!!!"` as success indicator
- Ignores verify errors that occur on some bootloader versions ("Packet N doesn't match")

### Entering Bootloader Mode

- **Hardware:** Hold the boot button while plugging in USB
- **Software:** Send a bootloader command from your application (implementation-specific)

## Adding a New Board

Create a JSON file in `boards/`, e.g. `boards/ch551g.json`:

```json
{
    "build": {
        "f_cpu": "24000000L",
        "f_osc_external": "0L",
        "mcu": "CH551",
        "variant": "ch551",
        "core": "ch55xduino",
        "board": "ch55x"
    },
    "frameworks": ["arduino"],
    "name": "WCH CH551G",
    "upload": {
        "maximum_ram_size": 512,
        "maximum_size": 10240,
        "protocol": "ch55x",
        "xdata_location": 0,
        "boot_config": 3
    },
    "url": "https://www.wch-ic.com/products/CH551.html",
    "vendor": "WCH"
}
```

## Important Notes for CH55x Development

| Constraint | Details |
|------------|---------|
| **C only** | SDCC for MCS51 does not support C++. Use `.c` files. |
| **No printf/sprintf** | Too large for 8051. Use manual conversion. |
| **8-bit multiply overflow** | SDCC promotes to `int` (16-bit signed) — cast to `(uint16_t)` |
| **USB Serial unavailable** | When using custom USB (`-DUSER_USB_RAM=N`), CDC is disabled |
| **P3.6/P3.7 reserved** | USB D+/D− lines — never use as GPIO |
| **256 B IRAM** | Use `__data` for time-critical variables only |
| **EEPROM = 128 B** | DataFlash — use `eeprom_read_byte()` / `eeprom_write_byte()` |

## Credits

This platform is built upon:
- [ch55xduino](https://github.com/DeqingSun/ch55xduino) by Deqing Sun — Arduino core and custom SDCC build
- [SDCC](https://sdcc.sourceforge.net/) — Small Device C Compiler
- [vnproch55x](https://github.com/DeqingSun/ch55xduino) — USB bootloader flash tool

## License

[MIT](LICENSE) — Copyright (c) 2025 JAQUBA
