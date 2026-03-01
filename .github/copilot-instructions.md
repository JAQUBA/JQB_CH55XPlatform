# JQB_CH55XPlatform — Copilot Instructions

## Projekt

Platforma PlatformIO dla mikrokontrolerów **WCH CH55x** (CH551, CH552, CH554, CH559) — architektura MCS51 / 8051.  
Używa frameworka **ch55xduino** i kompilatora **SDCC**.

Repozytorium: `https://github.com/JAQUBA/JQB_CH55XPlatform`

---

## Struktura

```
JQB_CH55XPlatform/
├── platform.json          — Manifest platformy PlatformIO
├── platform.py            — Klasa platformy + auto-download pakietów (cross-platform)
├── sdcc_compat.h          — Stuby słów kluczowych SDCC dla IntelliSense
├── boards/
│   ├── ch551.json         — WCH CH551 (10KB Flash, 512B XRAM)
│   ├── ch552g.json        — WCH CH552G (14KB Flash, 1KB XRAM)
│   ├── ch554.json         — WCH CH554 (14KB Flash, 1KB XRAM)
│   └── ch559.json         — WCH CH559 (60KB Flash, 6KB XRAM)
└── builder/
    ├── main.py            — Skrypt budowania SCons (auto-config USB/XRAM, IHX→BIN, upload, IntelliSense)
    └── frameworks/
        └── arduino.py     — Integracja z ch55xduino + auto-detekcja bibliotek
```

---

## Architektura

### Przepływ budowania

```
.c → SDCC (.rel) → Linker (.ihx) → IHX→BIN (Python) → vnproch55x → CH55x
```

### Pakiety (auto-download przez platform.py)

Przy pierwszym `pio run` platforma automatycznie pobiera i instaluje do `~/.platformio/packages/`:

| Pakiet | Opis |
|--------|------|
| `toolchain-sdcc-ch55x` | Kompilator SDCC (custom build, per-platform: Win/Mac/Linux) |
| `framework-ch55xduino` | Arduino core dla CH55x |
| `tool-ch55xtools` | vnproch55x (upload, per-platform) |

Nie wymaga ręcznej instalacji ani skryptów setup.

### Auto-konfiguracja (builder)

Builder automatycznie konfiguruje projekt na podstawie opcji w `ch552g.json`:

| Funkcja | Źródło | Co robi |
|---------|--------|---------|
| **USB XRAM** | `board_build.usb_ram` (domyślnie `148`) | Ustawia `-DUSER_USB_RAM`, `--xram-loc`, `--xram-size`, `upload.maximum_ram_size` |
| **EP adresy** | `board_build.ep0_addr/ep1_addr/ep2_addr` | Dodaje `-DEP0_ADDR`, `-DEP1_ADDR`, `-DEP2_ADDR` |
| **Include paths** | `src/` subdirectory scan | Automatycznie dodaje wszystkie podkatalogi `src/` zawierające `.h` do `CPPPATH` |
| **Biblioteki** | `#include` scan w źródłach | Wykrywa `#include <WS2812.h>` itp. i automatycznie buduje odpowiednie biblioteki ch55xduino |
| **IntelliSense** | build environment | Auto-generuje `.vscode/c_cpp_properties.json` z poprawnymi ścieżkami, defines i `sdcc_compat.h` |

### IntelliSense

Builder auto-generuje `.vscode/c_cpp_properties.json` z:
- Include paths (SDCC, core, variant, biblioteki, src/ subdirs)
- Defines (-D z board, CCFLAGS, build_flags, auto-USB)
- Force-include `sdcc_compat.h` (ścieżka rozwiązywana dynamicznie z `platform.get_dir()`)

---

## Ograniczenia CH55x

| Parametr | CH551 | CH552G | CH554 | CH559 |
|---|---|---|---|---|
| Flash | 10 KB | 14 KB | 14 KB | 60 KB |
| XRAM | 512 B | 1 KB | 1 KB | 6 KB |
| IRAM | 256 B | 256 B | 256 B | 256 B |
| EEPROM | — | 128 B | 128 B | 1 KB |
| Język | Tylko C (SDCC) | Tylko C | Tylko C | Tylko C |
| Kompilator | SDCC `--model-large --int-long-reent` ||||

---

## Minimalny `platformio.ini` dla CH552G

```ini
[env:board]
platform = https://github.com/JAQUBA/JQB_CH55XPlatform.git
board = ch552g
framework = arduino
```

Wszystko inne jest auto-konfigurowane. Opcjonalne override'y:

```ini
; Zmień rezerwację USB RAM (domyślnie 148):
board_build.usb_ram = 200

; Zmień adresy EP (domyślnie 0/10/20):
board_build.ep1_addr = 16
board_build.ep2_addr = 80

; Wyłącz USB (pełne 1024 B XRAM):
board_build.usb_ram = 0
```

---

## Wskazówki

1. **Board JSON zawiera sensowne domyślne** — `usb_ram=148` (typowe composite HID), EP adresy `0/10/20`. Projekty nadpisują tylko gdy potrzebują innej konfiguracji.
2. **Ścieżka do `sdcc_compat.h`** jest rozwiązywana dynamicznie przez `platform.get_dir()` w `builder/main.py` — działa zarówno lokalnie jak i z git URL.
3. **Auto-download** pakietów (SDCC, ch55xduino, vnproch55x) jest w `platform.py` — cross-platform (Win/Mac/Linux). Nie ma skryptu setup.
4. **`platform.py`** zawiera logikę auto-download + deklarację pakietów. Cała logika budowania jest w `builder/main.py`.
5. **Upload** obsługuje błędy weryfikacji vnproch55x — sprawdza `"Write complete!!!"` zamiast kodu wyjścia.
6. **Biblioteki ch55xduino** (WS2812, SPI, SoftI2C itp.) są wykrywane automatycznie przez skan `#include` w źródłach — nie trzeba dodawać ich do `build_src_filter`.
7. **Include paths** — wszystkie podkatalogi `src/` z plikami `.h` są dodawane automatycznie do ścieżek include — nie trzeba ręcznie dodawać `-Isrc/shared` itp.
