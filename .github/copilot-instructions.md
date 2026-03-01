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
├── platform.py            — Klasa platformy (Ch55xPlatform)
├── sdcc_compat.h          — Stuby słów kluczowych SDCC dla IntelliSense
├── setup.ps1              — Skrypt instalujący toolchain (Windows)
├── boards/
│   └── ch552g.json        — Definicja płytki CH552G
└── builder/
    ├── main.py            — Skrypt budowania SCons (SDCC + IHX→BIN + upload)
    └── frameworks/
        └── arduino.py     — Integracja z ch55xduino
```

---

## Architektura

### Przepływ budowania

```
.c → SDCC (.rel) → Linker (.ihx) → IHX→BIN (Python) → vnproch55x → CH55x
```

### Pakiety (instalowane przez setup.ps1)

| Pakiet | Ścieżka | Opis |
|--------|---------|------|
| `toolchain-sdcc-ch55x` | `~/.platformio/packages/` | Kompilator SDCC (custom build) |
| `framework-ch55xduino` | `~/.platformio/packages/` | Arduino core dla CH55x |
| `tool-ch55xtools` | `~/.platformio/packages/` | vnproch55x (upload) |

### IntelliSense

Builder auto-generuje `.vscode/c_cpp_properties.json` z:
- Include paths (SDCC, core, variant, biblioteki, src/)
- Defines (-D z board, CCFLAGS, build_flags)
- Force-include `sdcc_compat.h` (ścieżka rozwiązywana dynamicznie z `platform.get_dir()`)

---

## Ograniczenia CH55x

| Parametr | Wartość |
|---|---|
| Język | **Tylko C** — SDCC dla MCS51 nie obsługuje C++ |
| Flash | 14 KB (CH552G) |
| XRAM | 1 KB (876 B z USB endpoints) |
| IRAM | 256 B |
| EEPROM | 128 B |
| Kompilator | SDCC z `--model-large --int-long-reent` |

---

## Wskazówki

1. **Board JSON nie zawiera project-specific flags** — adresy USB endpoints (`-DEP0_ADDR`, `-DUSER_USB_RAM` itp.) definiuje użytkownik w `platformio.ini`.
2. **Ścieżka do `sdcc_compat.h`** jest rozwiązywana dynamicznie przez `platform.get_dir()` w `builder/main.py` — działa zarówno lokalnie jak i z git URL.
3. **`setup.ps1`** instaluje tylko pakiety CH55x — nie zawiera MinGW ani narzędzi niezwiązanych z platformą.
4. **Plik `platform.py`** jest minimalny — cała logika jest w `builder/main.py`.
5. **Upload** obsługuje błędy weryfikacji vnproch55x — sprawdza `"Write complete!!!"` zamiast kodu wyjścia.
6. **Board `ch552g.json`** ma generyczne wartości (`xdata_location: 0`, `maximum_ram_size: 1024`) — projekty nadpisują je w `platformio.ini` przez `board_upload.*`.
