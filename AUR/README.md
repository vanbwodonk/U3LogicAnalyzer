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
