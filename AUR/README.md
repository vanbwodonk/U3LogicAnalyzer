# AUR packaging for U3LogicAnalyzer

Local Arch Linux package that clones the GitHub repository and builds the
bundled sigrok stack plus the U3LogicAnalyzer application.

```bash
cd AUR
makepkg -si
```

The PKGBUILD builds:

1. bundled `libsigrok` (including the WCH CH32H417 driver)
2. bundled `libsigrokcxx`
3. bundled `libsigrokdecode` (130 decoders)
4. the `LogicAnalyzer` application

Because the patched sigrok libraries are installed into `/usr/lib`, this
package conflicts with the distribution's `libsigrok` / `libsigrokdecode`
packages. FX2LAFW/Saleae firmware is bundled, so no separate
`sigrok-firmware-fx2lafw` package is required.

## Build dependencies (Qt6)

The application builds against Qt6. `qt6-base` and `qt6-svg` are runtime
dependencies; `qt6-tools` provides `Qt6LinguistTools` for the translations.
`makepkg -s` installs them from `depends`/`makedepends`, but CI jobs that run
`makepkg --nodeps` or reuse a prebuilt container must install them first:

```bash
sudo pacman -S --needed --noconfirm qt6-base qt6-svg qt6-tools
```

If the build stops with `Could not find a package configuration file provided
by "Qt6"`, the build environment still has the old Qt5 dependency set. Do not
work around it by adding `Qt6_DIR` by hand; install the Qt6 packages (or fix
the container image) so the normal `find_package(Qt6)` search succeeds.

## DreamSourceLab DSLogic firmware

DSView and `sigrok-firmware-fx2lafw` are **not** required. DreamSourceLab and
FX2LAFW firmware is bundled under `firmware/` and installed to
`/usr/share/sigrok-firmware` by the application CMake install rules.

## USB access (udev)

The package installs:

- `/usr/lib/udev/rules.d/60-libsigrok.rules`
- `/usr/lib/udev/rules.d/61-libsigrok-uaccess.rules`

The `post_install`/`post_upgrade` hook reloads udev and triggers USB events.
Unplug and replug the analyzer once after installation so systemd-logind
grants your user access through the uaccess ACL.
