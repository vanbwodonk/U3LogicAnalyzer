# AGENTS.md

Guidance for coding agents working in this repository.

## What this project is

U3LogicAnalyzer is a Qt6 desktop application for WCH CH32H417 / CH569 USB
logic analyzers. It is a fork of PulseView 0.5.0 with a bundled sigrok stack
vendored in-tree:

- `main.cpp`, `pv/` — PulseView-derived GUI and application code.
- `libsigrok/` — upstream libsigrok `0.6.0-ch32h417` with the complete hardware
  driver set (FX2LAFW/Saleae, DreamSourceLab, Hantek, serial/SCPI instruments,
  etc.) plus the U3 `wch-ch32h417` driver.
- `libsigrokdecode/` — libsigrokdecode `0.6.0` with 130 Python decoders.
- `firmware/` — MounRiver Studio projects (CH32H417 APP/IAP, V3F/V5F) and
  prebuilt images; `firmware/dreamsourcelab/`, `firmware/fx2lafw/`,
  `firmware/asix-sigma/` and `firmware/sysclk-lwla/` contain bundled firmware
  installed by CMake.
- `build_macos.sh`, `build_linux.sh`, `build_windows.sh`, `package_app.sh` —
  supported build and packaging entry points. `build_linux.sh` is the
  Linux-only helper (release/debug, separate `build/linux` tree).
- `.github/workflows/build.yml` — macOS/Linux/Windows CI; `v*` tags create a
  GitHub Release.

Known USB IDs: CH32H417 `1a86:5537`, CH569 `1a86:8025`, CH32H417 HID/IAP mode
`1a86:fe17`.

## Build and run

macOS / Linux, from the repo root:

```bash
./build_macos.sh              # 4 stages; installs everything into build/install
./build_macos.sh --clean      # delete build/ and rebuild from scratch
./build_macos.sh --run        # build, then launch the app
```

- Main binary: `build/pulseview_build/LogicAnalyzer`.
- Linux-only helper: `./build_linux.sh` (release), `--debug`, `--clean`,
  `--run`; it uses a separate `build/linux` tree and install prefix.
- Headless sanity check:
  `QT_QPA_PLATFORM=offscreen ./build/pulseview_build/LogicAnalyzer -V`.
- Debug device detection with `-l 5`; a working CH32H417 logs
  `Scan found 1 device (wch-ch32h417)` and repeated `Read ... bytes from pipe`
  lines. Use `-d wch-ch32h417` to restrict the driver, `-D` to skip scanning.

Windows: run `./build_windows.sh` from an MSYS2 **MINGW64** shell. Output:
`build/windows/pulseview_build/LogicAnalyzer.exe` and
`build/LogicAnalyzer-win64.zip`.

macOS packaging (macOS only): `./package_app.sh` creates
`build/U3LogicAnalyzer.app`; `--dmg` also creates `build/U3LogicAnalyzer.dmg`.

Dependencies: CMake (≥3.21 for the app, ≥3.10 for the bundled libraries), a
C++17 compiler, Qt6 (Widgets, Gui, Svg, Network, LinguistTools), glib/glibmm-2.4, Boost
(filesystem, serialization), libusb, hidapi, libzip, and Python 3 development
files. For the full driver set also install libserialport, libftdi1, nettle,
libieee1284, and libbluetooth (BlueZ); CMake excludes drivers whose optional
dependency is unavailable. Boost.Test (`libboost-test-dev`) is needed only for
tests. FX2LAFW and DSLogic firmware are bundled in `firmware/` and installed
to `share/sigrok-firmware` (`SIGROK_FIRMWARE_DIR` overrides the search path).

### Manual CMake

The scripts wrap four independent builds. The app must resolve the libraries
installed in `build/install`, so point pkg-config and CMake at that prefix:

```bash
export PKG_CONFIG_PATH="$PWD/build/install/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
cmake -S . -B build/pv -DCMAKE_PREFIX_PATH="$PWD/build/install" \
      -DCMAKE_BUILD_TYPE=Release -DDISABLE_WERROR=ON
cmake --build build/pv -j"$(nproc)"
```

`DISABLE_WERROR` defaults to `ON` (warnings are not errors). The scripts set
`ENABLE_TESTS=OFF`, `ENABLE_FLOW=OFF`, and `ENABLE_SIGNALS=OFF` (Windows has no
signal support).

## Tests

The scripts do **not** build tests, and CI does not run them. Against an
existing `build/install` prefix:

```bash
export PKG_CONFIG_PATH="$PWD/build/install/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
cmake -S . -B build/test_build -DCMAKE_PREFIX_PATH="$PWD/build/install" \
      -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTS=ON -DDISABLE_WERROR=ON
cmake --build build/test_build -j"$(nproc)" --target pulseview-test
ctest --test-dir build/test_build --output-on-failure
```

The suite uses Boost.Test and is headless (segments, decoder stack,
device-presence logic, software-update parsing, ruler). Add new tests under
`test/` and register the source in `test/CMakeLists.txt`.

## Code map

- `main.cpp` — CLI parsing, decoder-directory discovery, bootstrap, Windows
  dark title bar.
- `pv/application.*` — app identity/version, language switching, decoder list,
  About/version info.
- `pv/mainwindow.*` — session/view lifecycle, USB hot-plug polling.
- `pv/session.*` — acquisition state machine, data feed, save/restore.
- `pv/data/` — signals, chunked logic/analog segments, decode stack.
- `pv/views/trace/` — waveform view; `pv/views/decoder_binary/` and
  `pv/views/tabular_decoder/` — decoder result views.
- `pv/binding/` — C++ wrappers around libsigrok(cxx).
- `pv/dialogs/iapdialog.*` — HID firmware upgrade (CH375 IAP is Windows-only);
  `pv/dialogs/decoder_channel_dialog.*` — decoder channel assignment.
- `pv/devicepresence.*` — pure USB identity/snapshot-diff helpers.
- `pv/dialogs/triggerdialog.*` — Device → Trigger Option. Simple mode is a
  per-channel match table; Advanced mode builds multi-stage libsigrok triggers
  (up to 16 stages). Serial trigger and per-channel invert/counter are not
  supported by the DSLogic driver.
- `pv/popups/channels.*` — the Device Options dialog (Settings/Channels
  tabs). Non-WCH devices get a generic `binding::Device` hardware form from
  libsigrok config keys; the DSLogic threshold is exposed as a 0.1 V slider.
  FX2LAFW devices get channel modes: 8 ch at 24 MHz, or 16 ch at 12 MHz on
  16-bit profiles.
- `libsigrok/src/hardware/wch-ch32h417/` — `api.c` driver
  lifecycle/configuration, `protocol.c` command protocol,
  `ch375_wrapper.c` transport (CH375DLL on Windows, libusb elsewhere).
- `libsigrok/src/hardware/<driver>/` — upstream drivers. The driver registry
  uses linker sections; `libsigrok/CMakeLists.txt` must keep
  `driver_list_start.c` first and `driver_list_stop.c` last.
- `libsigrokdecode/decoders/<id>/pd.py` — Python protocol decoders.

## Conventions

- The project is GPLv3+ overall; individual files may carry GPLv2+ headers.
  Keep an existing license header on new files.
- Follow `HACKING` (Linux kernel style for C). C++/Qt code follows the existing
  PulseView style: tabs, `namespace pv`, opening brace on its own line for
  functions/classes, and matching brace/blank-line conventions. There is no
  `.clang-format`; match the surrounding file.
- Include guards: `PULSEVIEW_<PATH>_<FILE>_HPP`, with the closing `#endif`
  comment.
- In C code use `g_try_malloc()` / `g_free()` and glib types; avoid
  `g_malloc()` (it aborts on OOM).
- User-visible strings go through `tr()`. Translations live in `l10n/*.ts`
  (`zh_cn.ts` is the Chinese translation and `en.ts` translates the
  Chinese-origin strings for English/fallback UI). The build only runs
  `lrelease` (`qt_add_translation`); run `lupdate` manually after changing
  strings and fill new entries. Do not use `qt_add_translations()` (plural),
  which runs `lupdate` and rewrites the `.ts` files during builds.
- New `Q_OBJECT` headers must be added to the `pulseview_HEADERS` list (and to
  the parallel test lists) so AUTOMOC processes them; add new sources to
  `pulseview_SOURCES`.
- `QT_NO_KEYWORDS` is defined globally: use `Q_SIGNALS`, `Q_SLOTS`, and
  `Q_EMIT` rather than the lowercase Qt keywords.
- Do not reformat vendored code (`pv/exprtk.hpp`, `libsigrok/`,
  `libsigrokdecode/decoders/`, `themes/`) unless the task requires it.
- Commit messages follow Conventional Commits, e.g. `feat:`, `fix(iap):`,
  `fix(build):`, `docs:`, `ci:`, `build(scripts):`.

## Gotchas

- **Preserve the U3 integration when updating `libsigrok`.** It is upstream
  libsigrok plus `src/hardware/wch-ch32h417`, the CH32H417 config keys in
  `libsigrok.h`/`hwdriver.c`, and the custom CMake build. `build_macos.sh`
  verifies `libsigrok/src/hardware/wch-ch32h417/api.c` exists.
- `libsigrokdecode` is still a trimmed decoder tree; do not assume upstream
  modules or build files exist there.
- Optional drivers are compiled only when their library is found (libftdi,
  libserialport, nettle, libieee1284, BlueZ/GIO). Linux-only drivers
  (`beaglelogic`, `baylibre-acme`) and Windows-unsupported ones are filtered
  in `libsigrok/CMakeLists.txt`; keep that logic when adding dependencies.
- Names are intentional: the CMake project is `pulseview`, the binary is
  `LogicAnalyzer`, and the user-facing app name is `U3LogicAnalyzer`
  (`pv/application.cpp`, macOS `Info.plist`).
- Windows uses the WCH CH375 driver/DLL; macOS/Linux use the built-in libusb
  transport and need no kernel driver. CH375 IAP mode is Windows-only; HID IAP
  works on all platforms.
- Decoder discovery checks, in order: `<app>/../Resources/decoders`,
  `<app>/../share/libsigrokdecode/decoders`, and
  `<app>/../../install/share/libsigrokdecode/decoders`. If the binary is
  elsewhere, set `SIGROKDECODE_DIR`. `build_macos.sh --run` and the Windows
  `run.bat` do this for you.
- FX2LAFW analyzers use the bundled `firmware/fx2lafw/` images. The app was
  verified end-to-end with a Saleae Logic (`0925:3881`); after upload the
  device re-enumerates as a sigrok FX2LAFW device. `firmware/asix-sigma/` and
  `firmware/sysclk-lwla/` hold the freely redistributable firmware for those
  drivers; Saleae Logic16/Pro, LeCroy, Kingst, LWLA1016 and SLA5032 firmware
  is not bundled because it is not freely redistributable (see
  `firmware/README.md`).
- The DreamSourceLab DSLogic driver includes the API v2 support from libsigrok
  PR #170 (DSLogic Plus `2a0e:0020`, U3Pro16 `2a0e:002a`). Scan must tolerate
  unreadable USB string descriptors and `dslogic_dev_open()` falls back to
  API v2 for those models if strings are unavailable. The firmware files are
  vendored under `firmware/dreamsourcelab/` (DreamSourceLab MIT-style
  license), installed to `share/sigrok-firmware` by the top-level CMake
  install rules and by `build_linux.sh`. Do not reintroduce a build/runtime
  dependency on DSView. Linux USB access needs the `60-libsigrok.rules` and
  `61-libsigrok-uaccess.rules` udev rules; CMake and the AUR package install
  them to `/usr/lib/udev/rules.d`, and the package reloads udev. Replug a
  device after installing the rules.
- DSLogic acquisition modes are selected in the Device Options dialog. The
  UI enables the first N channels and limits the toolbar samplerate list
  (Buffer 4/8/16 ch at 400/200/100 MHz, Stream 3/6/12/16 ch at
  100/50/25/20 MHz). The driver still exposes 16 probes; `MainBar` filters
  rates via `channel_mode_max_samplerate_`. Buffer mode pipelines up to 16
  in-flight 512 KiB bulk transfers; the worker uses an 8x8 bit-transpose
  instead of per-bit deinterleaving.
- The acquisition path is sensitive to 8- vs 16-channel packing:
  `Segment::unit_size_temp` is `8 / channel_num`, and channel-bit offsets /
  `channel_switch_2` depend on it. A divide-by-zero/crash in the 16-channel
  path was fixed before — do not regress it.
- `MainWindow` now scans all sigrok drivers at startup and on refresh; the
  main bar lists every non-demo device. WCH-specific hot-plug/presence logic
  remains WCH-only. WCH USB IDs are duplicated in `pv/devicepresence.cpp`,
  `main.cpp`, and `pv/toolbars/mainbar.cpp`; update all of them when adding
  hardware. Session save/restore still only persists WCH devices.
- `pv/dialogs/iapdialog.cpp` performs IAP work on a `QThread`. Widget/dialog
  access (including the completion dialog) must be marshalled to the GUI
  thread; touching UI from the worker can crash.
- On macOS, `package_app.sh` must use the Qt6 `macdeployqt`
  (`/opt/homebrew/opt/qt/bin/macdeployqt`); the script pins that path.
- CI runs `build_macos.sh` on Linux as well, so keep it portable. Releases are
  published only for `v*` tags; do not tag or push unless asked.
- Firmware is built with MounRiver Studio (RISC-V toolchain), not CMake.
  `firmware/**/obj/` contains committed build outputs — do not "clean" them.
- `README.md` and `README_zh.md` are paired; keep both in sync for user-facing
  feature/build changes.
