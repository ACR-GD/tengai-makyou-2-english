# Far East of Eden II: Manjimaru — English Translation v0.9 (beta)

An English translation patch for **Tengai Makyou II: Manji Maru**, Hudson's
2005 Nintendo DS remake of the 1992 PC Engine CD classic. It was never
released in English, until now.

## Download

Get **`Tengai Makyou II - Manji Maru (English v0.9).zip`** from the
[v0.9 beta release](https://github.com/ACR-GD/tengai-makyou-2-english/releases/tag/v0.9-beta). It contains the BPS patch and a
README. The game is not included: patch your own dump of the Japanese ROM.

| | Size | CRC32 | SHA-1 |
|---|---|---|---|
| Japanese ROM (input) | 134,217,728 | `0DF79A80` | `0717fcc412af42c2b1d7ac9178974e1259fb7c63` |
| English ROM (output) | 136,533,316 | `6B9354BA` | `5037474264683be52447181e7e7f10b2a228bf14` |

Apply with [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/),
Flips or MultiPatch.

## What's translated

- All 11,661 lines of story and NPC dialogue
- All 189 cutscene subtitles, refitted to the cutscene layouts
- Battles: commands, messages, enemies, items, spells, arts and equipment
- Field menus, shops, inns and storage
- Place names on the menus, the province map and the world map
- Title screen, New/Load menu, save/load screens
- A new variable-width font

## Tools

The Python tools used to make the patch are in [`tools/`](tools). They need
Python 3.11+ and Pillow (`pip install -r requirements.txt`; `capstone` and
`numpy` only for the analysis scripts). This repository does not contain the
game, files unpacked from it, or the translation data the build reads
(`translation/`). The tools document the formats and techniques, and you can
run them on your own dump.

| Tool | Purpose |
|---|---|
| `nds_extract.py` | Unpack a DS ROM (ARM9/ARM7, overlays, NitroFS files) |
| `build_en_vwf_rom.py` | Full build: scripts, font, names, graphics, BPS patch |
| `bps_patch.py` / `bps_apply.py` | Write a BPS patch / apply one and verify every CRC32 |
| `scs_codec.py`, `scs_build_en.py` | `.scs` dialogue script format and rebuilder |
| `vwf_font.py`, `vwf_arm9.py`, `text_raster.py` | Variable-width font and its ARM9 hooks |
| `ov008_build.py`, `subtitle_layout.py` | Cutscene subtitle text and on-screen positions |
| `native_*.py`, `combat_text.py`, `battle_panel.py` | Relocated menu, battle and name strings |
| `cmp_codec.py` and `*_graphics.py` | `CMP`/LZ10 graphics containers and the repainted UI art |
| `disasm.py`, `ghidra/` | ARM disassembly and Ghidra scripts used for research |

Check a patched ROM yourself:

```sh
python3 tools/bps_apply.py "Japanese.nds" "Tengai Makyou II - Manji Maru (English v0.9).bps" "English.nds"
```

It stops on a wrong source ROM, and otherwise writes a ROM that matches the
output CRC32 above.

`docs/VWF.md` describes how the variable-width font works.

## Known issues (beta)

- The whole game hasn't been played start to finish on the patched ROM yet:
  later menus and cutscenes are verified against the game data, not on screen.
- Some stylized artwork (two intro name banners, the "Manto 2" TV ad, a brush
  drawing, a wanted poster) and the staff roll are still in Japanese.
- A few small menu boxes use short forms (Gear/Item/Scrl, Manji, Gokur., Nxt).
- Tested on melonDS 1.1 and DeSmuME 0.9.12, not yet on real hardware.

Bug reports with screenshots are very welcome: please [open an issue](../../issues).

*Unofficial fan translation, not affiliated with Hudson Soft, Konami or RED.*
