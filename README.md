# U3LogicAnalyzer

[中文文档](README_zh.md) | **English**

U3LogicAnalyzer is the PC host software for the CH32H417 / CH569 USB logic
analyzer, based on PulseView 0.5.0 with a bundled sigrok stack
(libsigrok + libsigrokdecode). It supports 130 protocol decoders
(I2C / SPI / UART ...).

![U3LogicAnalyzer running on macOS with a CH32H417 analyzer](docs/images/u3logic-analyzer-macos.png)

## Features

- CH32H417 (USB 3.0, up to 200 MHz sampling) and CH569 hot-plug detection
- Full libsigrok hardware driver set, including FX2LAFW/Saleae Logic,
  DreamSourceLab, Hantek, serial DMMs/PSUs, SCPI instruments, and more
- Bundled DreamSourceLab and FX2LAFW firmware (no DSView or
  `sigrok-firmware-fx2lafw` package needed)
- Hardware-aware Device Options: voltage threshold (DSLogic: 0.0-5.0 V in
  0.1 V steps), Buffer/Stream mode, RLE, capture ratio, external clock and
  clock edge
- DSLogic channel modes: Buffer 4 ch @ 400 MHz / 8 ch @ 200 MHz / 16 ch @
  100 MHz and Stream 3 ch @ 100 MHz / 6 ch @ 50 MHz / 12 ch @ 25 MHz /
  16 ch @ 20 MHz
- For long captures prefer Stream mode: buffer mode uploads only after the
  acquisition finishes, while stream mode transfers data during acquisition
  (2 s @ 10 MHz / 16 ch: ~2.0 s stream vs ~3.4 s buffer)
- Device → Trigger Option provides Simple per-channel triggers and
  multi-stage Advanced triggers (up to 16 stages). Serial trigger, per-channel
  invert/counter controls are not supported by the current libsigrok driver.
- DSLogic buffer depth is enforced in the sample-count list: uncompressed
  buffer depth is `256 Mbit / channels`, so 400 MHz with 4 channels is limited
  to 167.77 ms. Enabling RLE extends the available depth.
  - Windows: CH375 driver mode (CH375DLL)
  - macOS / Linux: libusb transport inside the driver, no kernel module
    required (protocol based on WCH's official CH37X_LINUX SDK)
- IAP firmware-upgrade dialog (HID mode on all platforms;
  CH375 mode is Windows-only)
- Software updates through GitHub Releases
- Protocol-decoder channel-assignment dialog
- Chinese UI, dark theme, new toolbar icons
- 130 protocol decoders
- Decoder auto-discovery - no `SIGROKDECODE_DIR` environment variable needed
- macOS .app / DMG packaging
- App name: U3LogicAnalyzer

## Firmware project

The firmware project is included in [`firmware`](firmware/), including the APP, IAP, V3F/V5F projects, and generated firmware files.

Original project: [OSHWHub - CH32H417 Logic Analyzer](https://oshwhub.com/q2h2/project_bszkxrnf?jlc_vid=E1VbBAYEQQUPUAJWQAVZAQBXRVMMUFdQFFJbAgJVRgcxVlNeQVVdU1JXRFNdUTsOAxUeFF5JWA4dDxMOAgNABAsLWA%3D%3D)

## Complete flow (from scratch)

### Step 1 - Get the sources

The repository is self-contained: `libsigrok` (with the wch-ch32h417 driver
and the libusb transport) and `libsigrokdecode` (130 decoders) are included
in-tree:

```bash
git clone <repo-url> U3LogicAnalyzer
cd U3LogicAnalyzer
./build_macos.sh
```

The build scripts still accept `LIBSIGROK_SRC` / `LIBSIGROKDECODE_SRC` to
point at alternative source directories (or sibling dirs with the same names).

### Step 2 - Install dependencies

macOS (Homebrew):

```bash
brew install pkgconf cmake ninja qt@5 glibmm@2.66 glib libusb hidapi \
             libserialport libftdi nettle libzip boost python@3.14
```

Linux (Debian/Ubuntu example):

```bash
    sudo apt install build-essential cmake ninja-build pkg-config \
      qtbase5-dev qttools5-dev libqt5svg5-dev libglib2.0-dev \
      libglibmm-2.4-dev libusb-1.0-0-dev libserialport-dev \
      libftdi1-dev libnettle-dev libieee1284-3-dev libbluetooth-dev \
      libhidapi-dev libzip-dev libboost-dev libboost-filesystem-dev \
      libboost-serialization-dev python3-dev
```

### Step 3 - Build

```bash
./build_macos.sh            # output: build/pulseview_build/LogicAnalyzer
./build_macos.sh --clean    # full rebuild

# Linux-only alternative
./build_linux.sh            # output: build/linux/pulseview_build/LogicAnalyzer
./build_linux.sh --debug    # debug build
./build_linux.sh --clean --run
```

### Step 4 - Run

```bash
./build_macos.sh --run
# or: ./build/pulseview_build/LogicAnalyzer
# hardware debugging: ./build/pulseview_build/LogicAnalyzer -l 5
```

Decoders are discovered automatically (no environment variables needed).
With a device attached, the log should show `Scan found 1 devices
(wch-ch32h417)` and continuous `Read ... bytes from pipe` lines.

### Step 5 (optional) - Package the macOS app / DMG

```bash
./package_app.sh
./package_app.sh --dmg
open build/U3LogicAnalyzer.dmg
```

## Windows

Build under MSYS2 MINGW64. The companion package's `README_CH32H417.md`
describes `setup_env.sh` / `build.sh`; the repository also ships
`build_windows.sh` which produces `build/LogicAnalyzer-win64.zip`
(exe + DLLs + decoders + run.bat).

## CI / releases

[`.github/workflows/build.yml`](.github/workflows/build.yml) builds macOS /
Linux / Windows on push to master and pull requests. Pushing a `v*` tag
(e.g. `git tag v1.1 && git push origin v1.1`) creates a GitHub Release with:

- `U3LogicAnalyzer.dmg` (macOS installer image)
- `U3LogicAnalyzer-linux.tar.gz` (Linux binary + decoders; needs system Qt5/glib)
- `LogicAnalyzer-win64.zip` (Windows portable package)

## Known limitations

- CH375 driver mode is Windows-only; macOS/Linux use the libusb transport.
- IAP CH375 mode is Windows-only; HID mode works on all platforms.

## Changes vs upstream PulseView

1. U3 customizations: renamed to U3LogicAnalyzer, Chinese UI, CH32H417/CH569
   support, IAP firmware-upgrade dialog, decoder-channel dialog, dark theme,
   new toolbar icons, zh_CN translations.
   The bundled libsigrok now contains the complete upstream hardware driver
   set (FX2LAFW/Saleae, DreamSourceLab, Hantek, serial/SCPI instruments, ...)
   alongside the CH32H417 driver; the GUI scans all drivers.
2. macOS / Linux enablement:
   - `build_macos.sh` / `build_windows.sh` / `package_app.sh`
   - libusb transport layer in `ch375_wrapper.c` (non-Windows), async buffered
     upload equivalent to the CH375DLL semantics
   - clang build fixes (missing return types, std::thread member pointer,
     unconditional Windows API usage, boost_system, -Wl,-Bdynamic)
   - crash fix: `unit_size_temp` divide-by-zero (16-channel case)
   - decoder auto-discovery
3. App renamed to U3LogicAnalyzer (.app bundle, Info.plist, window title).

## FAQ

- Decoder menu empty? Decoders are auto-discovered now; if it is still empty,
  check `build/install/share/libsigrokdecode/decoders` exists or set
  `SIGROKDECODE_DIR` and restart.
- Device not found? Run with `-l 5`; on macOS/Linux the driver uses libusb -
  confirm the device (VID 1a86, PID 5537) is visible to the OS. FX2LAFW-based
  analyzers use the bundled firmware; if you run a build from an unusual
  location, set `SIGROK_FIRMWARE_DIR` to the installed `sigrok-firmware`
  directory.
- DSLogic is not detected on Linux and the log says `LIBUSB_ERROR_ACCESS`?
  USB access requires udev rules. The AUR package installs them to
  `/usr/lib/udev/rules.d/60-libsigrok.rules` and
  `61-libsigrok-uaccess.rules`; replug the analyzer after installation. For
  a build-tree run, install them manually:

  ```bash
  sudo install -Dm644 libsigrok/contrib/60-libsigrok.rules \
     /usr/lib/udev/rules.d/60-libsigrok.rules
  sudo install -Dm644 libsigrok/contrib/61-libsigrok-uaccess.rules \
     /usr/lib/udev/rules.d/61-libsigrok-uaccess.rules
  sudo udevadm control --reload-rules
  sudo udevadm trigger
  ```

- DreamSourceLab DSLogic not detected, or firmware/FPGA upload fails? All
  supported DreamSourceLab firmware is bundled in
  [`firmware/dreamsourcelab/`](firmware/dreamsourcelab) and is installed to
  `share/sigrok-firmware` by the build. DSView is **not** required. If you run
  a build from an unusual location, point libsigrok at the bundled directory:

  ```bash
  export SIGROK_FIRMWARE_DIR="$PWD/firmware/dreamsourcelab"
  ```

- App fails to launch after packaging? Make sure the qt@5 `macdeployqt` is
  used (the script pins it) and no stale `build/LogicAnalyzer.app` remains.

## Licensing

The whole project, including the bundled `libsigrok` and `libsigrokdecode`
trees, is distributed under the GNU GPL v3 or later (GPLv3+); the
U3-specific driver code (wch-ch32h417, incl. the libusb transport) is
(C) Q2H2 under GPLv3+. Third-party resources (QDarkStyleSheet, DarkStyle,
QHexView, ExprTk, Tango icons) retain their own licenses and attributions -
see "Resource authors and licenses" in the upstream section below.

---

## Original upstream README

The sigrok project aims at creating a portable, cross-platform,
Free/Libre/Open-Source signal analysis software suite that supports various
device types (such as logic analyzers, oscilloscopes, multimeters, and more).

PulseView is a Qt-based LA/scope/MSO GUI for sigrok.

### Status

PulseView is in a usable state and has had official tarball releases.

### Copyright and license

PulseView is licensed under the terms of the GNU General Public License
(GPL), version 3 or later.

While some individual source code files are licensed under the GPLv2+, and
some files are licensed under the GPLv3+ or MIT, this doesn't change the fact
that the program as a whole is licensed under the terms of the GPLv3+ (e.g.
also due to the fact that it links against GPLv3+ libraries).

Please see the individual source files for the full list of copyright holders.

### Copyright notices

A copyright notice indicating a range of years, must be interpreted as having
had copyrightable material added in each of those years.

Example:

```text
Copyright (C) 2010-2013 Contributor Name
```

is to be interpreted as

```text
Copyright (C) 2010,2011,2012,2013 Contributor Name
```

### Resource authors and licenses

`icons/application-exit.png`, `icons/document-new.png`,
`icons/document-open.png`, `icons/document-save-as.png`,
`icons/edit-paste.svg`, `icons/help-browser.png`,
`icons/media-playback-pause.png`, `icons/media-playback-start.png`,
`icons/preferences-system.png`, `icons/search.svg`, `icons/window-new.png`,
`icons/zoom-fit-best.png`, `icons/zoom-in.png`, `icons/zoom-out.png`:
Tango Icon Library

- <http://tango.freedesktop.org/Tango_Desktop_Project>
- License: Public Domain

`icons/information.svg`: Bobarino

- <https://en.wikipedia.org/wiki/File:Information.svg>
- License: GFDL 1.2 or later / CC-BY-SA 3.0

`icons/add-math-channel.svg`: Inductiveload

- <https://en.wikipedia.org/wiki/File:Icon_Mathematical_Plot.svg>
- License: Public Domain

QDarkStyleSheet: Colin Duquesnoy

- <https://github.com/ColinDuquesnoy/QDarkStyleSheet>
- License: CC-BY 4.0

DarkStyle: Juergen Skrotzky

- <https://github.com/Jorgen-VikingGod/Qt-Frameless-Window-DarkStyle>
- License: MIT

QHexView: Victor Anjin

- <https://github.com/virinext/QHexView>
- License: MIT

ExprTk: Arash Partow

- <https://www.partow.net/programming/exprtk/index.html>
- License: MIT

### Mailing list

<https://lists.sourceforge.net/lists/listinfo/sigrok-devel>

### IRC

You can find the sigrok developers in the #sigrok IRC channel on Libera.Chat.

### Website

<http://sigrok.org/wiki/PulseView>
