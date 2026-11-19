# DreamSourceLab firmware

These files are the DreamSourceLab firmware/bitstream files required by the
in-tree `dreamsourcelab-dslogic` driver. They are bundled so the analyzer
works without a separate DSView installation.

The files are renamed to the names expected by libsigrok:

| File | Source (DSView `res/`) | Purpose |
|------|------------------------|---------|
| `dreamsourcelab-dslogic-fx2.fw` | `DSLogic.fw` | DSLogic FX2 firmware |
| `dreamsourcelab-dslogic-fpga-3v3.fw` | `DSLogic33.bin` | DSLogic FPGA (3.3 V) |
| `dreamsourcelab-dslogic-fpga-5v.fw` | `DSLogic50.bin` | DSLogic FPGA (5 V) |
| `dreamsourcelab-dslogic-pro-fx2.fw` | `DSLogicPro.fw` | DSLogic Pro FX2 |
| `dreamsourcelab-dslogic-pro-fpga.fw` | `DSLogicPro.bin` | DSLogic Pro FPGA |
| `dreamsourcelab-dslogic-plus-fx2.fw` | `DSLogicPlus.fw` | DSLogic Plus FX2 |
| `dreamsourcelab-dslogic-plus-fpga.fw` | `DSLogicPlus.bin` | DSLogic Plus FPGA |
| `dreamsourcelab-dslogic-basic-fx2.fw` | `DSLogic.fw` (fallback) | DSLogic Basic FX2 |
| `dreamsourcelab-dslogic-basic-fpga.fw` | `DSLogicBasic.bin` | DSLogic Basic FPGA |
| `dreamsourcelab-dslogic-u3pro16-fpga.fw` | `DSLogicU3Pro16.bin` | DSLogic U3Pro16 FPGA |
| `dreamsourcelab-dscope-fx2.fw` | `DSCope.fw` | DSCope FX2 |
| `dreamsourcelab-dscope-fpga.fw` | `DSCope.bin` | DSCope FPGA |

The firmware is Copyright (c) 2017 DreamSourceLab and is distributed under
the MIT-style license in [`LICENSE`](LICENSE). It originates from the
[DSView repository](https://github.com/DreamSourceLab/DSView) and the
DreamSourceLab firmware resources.
