# JQB CH55x Platform

**PlatformIO platform for WCH CH55x (CH551, CH552, CH554, CH559) MCS51 USB microcontrollers.**

Uses the [ch55xduino](https://github.com/DeqingSun/ch55xduino) Arduino-like framework and a custom SDCC compiler build optimized for CH55x. **All toolchain packages are auto-downloaded on first build** — no manual setup required.

## Features

- **Zero setup** — SDCC toolchain, ch55xduino framework and upload tools are auto-downloaded on first `pio run`
- **USB auto-configuration** — `USER_USB_RAM`, endpoint addresses, XRAM size/location derived from board defaults
- **Library auto-detection** — `#include <WS2812.h>` → library auto-compiled and linked (no manual `build_src_filter`)
- **Include path auto-scan** — all `src/` subdirectories with `.h` files added automatically
- **VS Code IntelliSense** — auto-generated `c_cpp_properties.json` with SDCC keyword stubs (`__xdata`, `__sfr`, `__at`, etc.)
- **SDCC compiler** — custom MCS51 build with `large_int_calc_stack_auto` model
- **vnproch55x uploader** — flash firmware over USB bootloader with automatic verify-error handling
- **IHX → BIN conversion** — built-in Python converter (no external `makebin` dependency)
- **Cross-platform** — auto-download works on Windows, macOS and Linux

## Supported MCUs

| MCU | Flash | XRAM | EEPROM | USB | Board |
|-----|-------|------|--------|-----|-------|
| **CH551** | 10 KB | 512 B | — | Full-speed Device | `ch551` |
| **CH552** | 14 KB | 1 KB | 128 B | Full-speed Device | `ch552` |
| **CH554** | 14 KB | 1 KB | 128 B | Full-speed Host/Device | `ch554` |
| **CH559** | 60 KB | 6 KB | 1 KB | Full-speed Host + Low-speed Hub | `ch559` |

## Installation

### 1. Install PlatformIO

Follow the [PlatformIO installation guide](https://docs.platformio.org/en/latest/core/installation/index.html) or install the VS Code extension.

### 2. Reference the platform in your project

In your `platformio.ini`:

```ini
[env:firmware]
platform = https://github.com/JAQUBA/JQB_CH55XPlatform.git
board = ch552g
framework = arduino
```

That's it. On first `pio run`, the platform automatically downloads and installs:

| Package | Description |
|---------|-------------|
| `toolchain-sdcc-ch55x` | SDCC compiler (custom MCS51 build) |
| `framework-ch55xduino` | ch55xduino Arduino core |
| `tool-ch55xtools` | vnproch55x upload tool |

## Quick Start

### Minimal `platformio.ini`

```ini
[env:firmware]
platform = https://github.com/JAQUBA/JQB_CH55XPlatform.git
board = ch552g
framework = arduino
```

USB is auto-configured from board defaults (`usb_ram=148`). Override if needed:

```ini
; Disable USB (full XRAM available)
board_build.usb_ram = 0

; Custom USB RAM reservation
board_build.usb_ram = 200
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

### Board-level options (auto-configured)

These values are set in the board JSON and auto-applied by the builder:

| Option | CH551 | CH552G | CH554 | CH559 | Description |
|--------|-------|--------|-------|-------|-------------|
| `build.usb_ram` | `0` | `148` | `148` | `148` | USB XRAM reservation (bytes) |
| `build.total_xram` | `512` | `1024` | `1024` | `6144` | Total XRAM |
| `build.ep0_addr` | `0` | `0` | `0` | `0` | EP0 address in USB RAM |
| `build.ep1_addr` | `10` | `10` | `10` | `10` | EP1 address in USB RAM |
| `build.ep2_addr` | `20` | `20` | `20` | `20` | EP2 address in USB RAM |

The builder automatically derives from `usb_ram`:
- `-DUSER_USB_RAM=<usb_ram>` (compiler define)
- `-DEP0_ADDR`, `-DEP1_ADDR`, `-DEP2_ADDR` (endpoint addresses)
- `--xram-loc <usb_ram>` (linker: XRAM start after USB region)
- `--xram-size <total_xram - usb_ram>` (linker: available XRAM)

### Project-level overrides (`platformio.ini`)

Override any board option:

```ini
board_build.usb_ram = 200
board_build.ep2_addr = 80
```

## Project Structure

```
JQB_CH55XPlatform/
├── platform.json          — PlatformIO platform manifest
├── platform.py            — Platform class (auto-download packages)
├── sdcc_compat.h          — SDCC keyword stubs for IntelliSense
├── boards/
│   ├── ch551.json         — WCH CH551
│   ├── ch552g.json        — WCH CH552G
│   ├── ch554.json         — WCH CH554
│   └── ch559.json         — WCH CH559
└── builder/
    ├── main.py            — SCons build script (auto-config + IHX→BIN + upload)
    └── frameworks/
        └── arduino.py     — ch55xduino framework + library auto-detection
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

### Auto-configuration

On every `pio run`, the builder automatically:

1. **USB/XRAM** — reads `board_build.usb_ram` and derives all USB defines and linker flags
2. **Include paths** — scans all `src/` subdirectories for `.h` files and adds them to CPPPATH
3. **Libraries** — scans source files for `#include <Lib.h>` and auto-compiles matching ch55xduino libraries (WS2812, SPI, SoftI2C, etc.)
4. **IntelliSense** — generates `.vscode/c_cpp_properties.json` with all paths, defines and `sdcc_compat.h`

### Upload

The uploader wraps `vnproch55x` with smart error handling:
- Streams output in real-time
- Detects `"Write complete!!!"` as success indicator
- Ignores verify errors that occur on some bootloader versions ("Packet N doesn't match")

### Entering Bootloader Mode

- **Hardware:** Hold the boot button while plugging in USB
- **Software:** Send a bootloader command from your application (implementation-specific)

## Important Notes for CH55x Development

| Constraint | Details |
|------------|---------|
| **C only** | SDCC for MCS51 does not support C++. Use `.c` files. |
| **No printf/sprintf** | Too large for 8051. Use manual conversion. |
| **8-bit multiply overflow** | SDCC promotes to `int` (16-bit signed) — cast to `(uint16_t)` |
| **USB Serial unavailable** | When using custom USB (`usb_ram > 0`), CDC is disabled |
| **P3.6/P3.7 reserved** | USB D+/D− lines — never use as GPIO |
| **256 B IRAM** | Use `__data` for time-critical variables only |
| **EEPROM** | 128 B on CH552/CH554, 1 KB on CH559 — `eeprom_read_byte()` / `eeprom_write_byte()` |

## Credits

This platform is built upon:
- [ch55xduino](https://github.com/DeqingSun/ch55xduino) by Deqing Sun — Arduino core and custom SDCC build
- [SDCC](https://sdcc.sourceforge.net/) — Small Device C Compiler
- [vnproch55x](https://github.com/DeqingSun/ch55xduino) — USB bootloader flash tool

## License

[MIT](LICENSE) — Copyright (c) 2025 JAQUBA
