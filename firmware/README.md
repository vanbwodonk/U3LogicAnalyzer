# Bundled firmware

Firmware needed by the bundled libsigrok drivers, installed to
`share/sigrok-firmware` by CMake and the build scripts.

| Directory | Driver / hardware | Files |
|-----------|-------------------|-------|
| `fx2lafw/` | Saleae Logic and other FX2 analyzers | all 15 `fx2lafw-*.fw` |
| `dreamsourcelab/` | DSLogic Plus/Pro/Basic/U3Pro16, DSCope | FX2 and FPGA images |
| `asix-sigma/` | ASIX Sigma | 50/100/200 MHz and 50sync images |
| `sysclk-lwla/` | Sysclk LWLA1034 | four FPGA `.rbf` images |

Not bundled because the vendor firmware is not freely redistributable:

- Saleae Logic16 (`saleae-logic16-fx2.fw` + bitstreams)
- Saleae Logic Pro 16 (`saleae-logicpro16-fx3.fw` + bitstreams)
- LeCroy LogicStudio16 (`lecroy-logicstudio16-fx2lp.fw` + bitstreams)
- Kingst LA1016/LA2016 MCU firmware and FPGA bitstreams
- Sysclk LWLA1016 and SLA5032 bitstreams
- Hantek 6xxx/DSO firmware (oscilloscopes, not logic analyzers)

Those can be produced from vendor software with the extractors in
`sigrok-util/firmware` and placed in `~/.local/share/sigrok-firmware`.
