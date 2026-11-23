# AGENTS.md — MIL-STD-1553 sigrok Decoder

## Project Overview

A [libsigrokdecode](https://sigrok.org/) protocol decoder for the **MIL-STD-1553** serial data bus (military avionics / spacecraft data bus). It decodes Manchester-encoded differential signals into command words (CW), status words (SW), and data words (DW).

- **Language:** Python
- **Framework:** libsigrokdecode API v3
- **License:** GPLv3+
- **Input:** 1 logic channel (DP — Data Positive)
- **Tags:** Embedded/industrial

---

## Key Files

| File | Purpose |
|------|---------|
| `pd.py` | Main decoder — `Decoder` class with state machine, timing, annotation output |
| `__init__.py` | Package init, imports `Decoder`, short docstring |
| `readme.md` | README with preview screenshots |
| `AGENTS.md` | This file |

---

## Architecture

### Decoder States (State Machine)

The decoder uses 4 states to walk through Manchester-encoded bits:

```
FIND_BIT_AFTER_10_BIT  ──→  FIND_BIT_AFTER_01_BIT
         ↑                       │
         └───────────────────────┘
         │
         ├──→ FIND_BIT_AFTER_COMMAND_SYNC
         └──→ FIND_BIT_AFTER_DATA_SYNC
```

- **`FIND_BIT_AFTER_10_BIT`** — Waiting for a rising edge after a `10` (high→low) pattern.
- **`FIND_BIT_AFTER_01_BIT`** — Waiting for a falling edge after a `01` (low→high) pattern.
- **`FIND_BIT_AFTER_COMMAND_SYNC`** — Processing the first bit after a command sync pulse.
- **`FIND_BIT_AFTER_DATA_SYNC`** — Processing the first bit after a data sync pulse.

### Sync Word Detection

MIL-STD-1553 uses Manchester-violating sync pulses:
- **CW sync:** 3 half-bits active + 1.5 half-bits passive. Detected by edge timing in `FIND_BIT_AFTER_01_BIT` (also a fallback in `FIND_BIT_AFTER_10_BIT`).
- **DW sync:** 1.5 half-bits active + 3 half-bits passive. Detected by edge timing in `FIND_BIT_AFTER_10_BIT` (also a fallback in `FIND_BIT_AFTER_01_BIT`).

### Word Structure (20 bit-times per word)

Each word: 3 µs sync + 16 data bits + 1 parity bit (odd parity) = 20 bit-times at 1 Mbps.

### Timing Constants

| Constant | Raw Value | Description |
|----------|-----------|-------------|
| `halfbit` (from 5e-7) | 500 ns | Half-bit period (Manchester bit = 1 µs) |
| `bitwindow` (from 4e-7) | 400 ns | Timing tolerance window |

These are scaled by samplerate in `metadata()` via `ceil(raw_value * samplerate)`. The scaling always uses the raw constants, not `self.halfbit`/`self.bitwindow`, so `metadata()` is safe to call multiple times.

### Auto Mode (Master/Slave Detection)

When `device_type = 'auto'`, the decoder distinguishes bus controller (master) from remote terminal (slave) by measuring idle time between words:
- **Idle > 14 µs** → master (BC initiated a new message)
- **Idle ≤ 14 µs** → slave (RT response within the inter-message gap)
- **First word** → always assumed master (BC initiates all transactions)

---

## Annotation Output

| # | Name | Description | Row |
|---|------|-------------|-----|
| 0 | `cw` | Command word hex value (or "SW" in slave mode) | Data |
| 1 | `dw` | Data word hex value | Data |
| 2 | `warning` | Short sync / bit count warnings | Data |
| 3 | `error` | Parity errors, bit count errors | Details |
| 4 | `cw_details` | Master-mode decoded command (RT addr, subaddr, mode code) | Details |
| 5 | `dw_details` | Data word index (`DATA-1`, `DATA-2`, ...) | Details |
| 6 | `aw_details` | Slave-mode status word bits | Details |

---

## Known Issues & Fixes

### Fixed: Decoder shows no output on PulseView re-run

**Root cause:** PulseView reuses the `Decoder` instance across capture runs (calling `decode()` again) but does not call `reset()`. Stale state from the previous capture — edge positions (`prelastsample`, `lastsample`, `actualsample`), bit accumulation (`bits`, `bitcount`), sync tracking (`syncsample`), and the idle timer (`last_word_end_sample`) — corrupts timing checks on the fresh data.

**Fix:** `decode()` re-initialises all runtime state at entry (lines 342–356 of `pd.py`), matching the values `reset()` sets, while preserving `samplerate`, `halfbit`, and `bitwindow` from `metadata()`.

**Workaround discovered during debugging:** Reassigning the PD channel to another pin and back forces PulseView to recreate the decoder session, which calls `reset()` — confirming the reuse hypothesis.

### Fixed: Timing compounding in metadata()

**Root cause:** `metadata()` used to multiply `self.halfbit` by `self.samplerate` every call. If PulseView called `metadata()` again (e.g. between captures with a different samplerate), the already-scaled value would be scaled again, producing nonsense timing.

**Fix:** `metadata()` now always scales from the raw constants (`5e-7`, `4e-7`) regardless of the current value of `self.halfbit`.

### Fixed: AttributeError on mode code 5 (unlock TX)

**Root cause:** `putcwdetails()` referenced `self.m_unlocktx` (line 192) but the class attribute is named `m_unlock`.

**Fix:** Corrected the reference to `self.m_unlock`.

---

## Development Guidelines

### For AI Agents

- **State machine modifications:** The 4 states and their transitions are tightly coupled — any new state must update transitions in all connected states.
- **Timing is critical:** All edge timing uses `isdiffinwindow()` with the scaled `halfbit`/`bitwindow` values. Never use raw sample numbers.
- **Annotation IDs:** Match the `annotations` tuple order (0–6). The `annotation_rows` references these IDs.
- **Language support:** All text arrays are single-element (English only, `self.lang = 0`). Adding i18n means expanding each array.
- **`decode()` entry guard:** Any state added to the runtime reset block at the top of `decode()` must match what `reset()` sets for the same variable — otherwise the decoder will behave differently on first load vs re-run.
- **`metadata()`:** Always scale timing from raw constants. Do not read-modify-write `self.halfbit` or `self.bitwindow`.

### Testing

The decoder is tested by loading a recorded 1553 signal in PulseView and verifying annotations appear correctly. For live-capture testing (the re-run scenario):
1. Open PulseView, add the MIL-STD-1553 decoder
2. Configure PD channel and samplerate
3. Click **RUN** — annotations should appear during/after acquisition
4. Stop, then click **RUN** again — annotations should appear on the new data without reassigning channels

### Common Pitfalls

- `self.wait()` is a blocking generator call — it suspends `decode()` until the condition is met. Never call it outside `decode()`.
- Sample positions (`samplenum`, `self.wait()` output) are relative to the current capture session — they reset on each new capture.
- The `auto` device type requires at least 2 words to establish master/slave classification.
- The `from functools import reduce` import is unused.

---

## Dependencies

- Python 3.x
- `libsigrokdecode` (bundled with PulseView / sigrok-cli)
- No external Python packages
