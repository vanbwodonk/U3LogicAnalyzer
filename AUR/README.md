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
packages. Install `sigrok-firmware-fx2lafw` separately if you use FX2LAFW /
Saleae Logic hardware.
