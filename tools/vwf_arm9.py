#!/usr/bin/env python3
"""ARM9 VWF: make the glyph X cursor advance by the *real* glyph width across
ALL active text rendering pipelines in the game.

Ground truth (verified by PyGhidra decompilation + ARM disassembly):

1. `FUN_020178b8` @ 0x020178B8 — Interactive `.scs` typewriter dialogue renderer
   (called via `FUN_020166c8`).
   * Draws each glyph via `FUN_020185c8` (from `[sb, #0x8c]` if a substitution
     string is active, else from `[sb]`).
   * At 0x02017BF4..0x02017C64 it had a hardcoded check for digits 0x824F..0x8258,
     falling through to 0x02017C68:
       02017C68: ldrb r1, [sb, #6]
       02017C6C: ldrb r0, [sb, #0xc]
       02017C70: add  r0, r1, r0
       02017C74: strb r0, [sb, #6]
   * We patch 0x17BF4 with `b #0x2017c68` and 0x17C6C with `bl W_SB`, which
     reads the drawn SJIS char (`[sb, #0x8c]` if non-empty else `[sb]`) and
     returns its VWF pixel width in `r0` (falling back to `[sb, #0xc]` = 12px/8px
     for untouched Japanese characters).

2. `FUN_02017714` @ 0x02017714 — Instant UI / menu / battle / status string
   renderer (75+ call sites via `FUN_0201670c`, `FUN_020167ac`, `FUN_02016828`,
   `FUN_02016898`).
   * Branch A (substitution string `[sl, #0x8c]` active):
     At 0x020177E0 `r0` holds the SJIS char ptr just drawn. We patch 0x177EC
     with `b #0x201785c` and 0x17860 (`ldrb r0, [sl, #0xc]`) with `bl W_SL_R0`.
   * Branch B (normal string `[sl]`):
     At 0x02017888 `r0` is `char_ptr + 2`. We patch 0x17894 (`ldrb r0, [sl, #0xc]`)
     with `bl W_SL_R0M2` (`sub r0, r0, #2` -> `W_SL_R0`).

3. `FUN_020190d4` @ 0x020190D4 (`ov_wrapper`) — Direct tile-buffer renderer
   (called from `FUN_02016aa4` [8px] and `FUN_02016af8` [12px], used for
   Overlay 3 cutscene subtitles and banners).
   * At 0x0201945C (`ldrb r2, [sp, #0x88]`), we patch with `bl W_OV`, returning
     the VWF width in `r2` (or `[sp, #0x88]` for untouched Japanese characters).

4. `FUN_02018960` — LIVE battle numeric renderer called by overlay 0.
   Preserve its code and fixed numeric advances. The previous claim that it
   was unused was incorrect; it must never be used as subtitle storage.

Width comes from a 512-byte table (2 pages: SJIS lead 0x81 / 0x82, indexed by
trail byte; 0x00 = untouched Japanese char -> use caller's native advance).

Hook arena @ file 0x11D188 (1,140 free bytes of ARM9 padding).
"""
from __future__ import annotations

import struct
from typing import Dict, List, Tuple

ARM9_RAM = 0x02000000
HOOK_BASE = 0x11D188

# 1. FUN_020178b8 (typewriter .scs dialogue renderer, ctx = sb/r9)
SITE_TW_SKIP = 0x17BF4    # b #0x02017C68 (skip hardcoded 0x824F..0x8258 digit branch)
SITE_TW_ADV  = 0x17C6C    # bl W_SB (replaces ldrb r0, [sb, #0xc])

# 2. FUN_02017714 (instant UI/menu/battle renderer, ctx = sl/r10)
SITE_UI_SKIP   = 0x177EC  # b #0x0201785C (skip hardcoded 0x824F..0x8258 digit branch)
SITE_UI_ADV_A  = 0x17860  # bl W_SL_R0   (replaces ldrb r0, [sl, #0xc] for subst string)
SITE_UI_ADV_B  = 0x17894  # bl W_SL_R0M2 (replaces ldrb r0, [sl, #0xc] for normal string)

# 3. FUN_020190d4 (direct buffer renderer ov_wrapper)
SITE_WIDTH_OV = 0x1945C   # bl W_OV (char ptr @ [sp,#0x04], width -> r2, fallback [sp,#0x88])

# 4. FUN_02018960 (legacy dialog_main)
SITE_WIDTH_1 = 0x18EA4    # bl W_S1 (char ptr @ [sp,#0x18], width -> r1, fallback [sp,#0xe4])
SITE_WIDTH_2 = 0x19060    # bl W_S2 (char ptr @ [sp,#0x04], width -> r2, fallback [sp,#0xe4])

# 5. Cutscene / visual string renderers (Overlay 3 subtitles & FMVs)
SITE_768DC   = 0x76D60    # bl W_768DC   (FUN_020768dc: char @ [sp,#4], cursor r4 -> r0)
SITE_763C8   = 0x7687C    # bl W_763C8   (FUN_020763c8: char @ [sp,#4], cursor r7 -> r0)
SITE_75348_A = 0x75878    # bl W_75348_A (FUN_02075348 loop 1: char @ [sp,#0x18], cursor r5 -> r0)
SITE_75348_B = 0x75A78    # bl W_75348_B (FUN_02075348 loop 2: char @ [sp,#4], cursor r5 -> r0)
SITE_75B08       = 0x762D0    # bl W_75B08   (FUN_02075b08: char @ [sp,#4], width -> r1)
SITE_75B08_SPEED = 0x75B3C    # ldrb r4, [sl, #8] -> mov r4, #1 (cutscene subtitle typewriter delay=1)

WIDTH_TABLE_LEN = 512  # 2 pages x 256

AL, EQ, NE, HI = 0xE, 0x0, 0x1, 0x8
R0, R1, R2, R3, R4, R5, R7, SB, SL, R12, SP, LR = 0, 1, 2, 3, 4, 5, 7, 9, 10, 12, 13, 14


def _u32(w: int) -> bytes:
    return struct.pack("<I", w & 0xFFFFFFFF)


def i_bx(rm, cond=AL):
    return (cond << 28) | 0x012FFF10 | rm


def i_mov_imm(rd, imm8, cond=AL):
    return (cond << 28) | 0x03A00000 | (rd << 12) | (imm8 & 0xFF)


def i_ldr_imm(rd, rn, off, cond=AL):
    return (cond << 28) | 0x05900000 | (rn << 16) | (rd << 12) | (off & 0xFFF)


def i_ldr_sp(rd, off, cond=AL):
    return i_ldr_imm(rd, SP, off, cond)


def i_ldrb_imm(rd, rn, off, cond=AL):
    return (cond << 28) | 0x05D00000 | (rn << 16) | (rd << 12) | (off & 0xFFF)


def i_ldrb_reg(rd, rn, rm, cond=AL):
    return (cond << 28) | 0x07D00000 | (rn << 16) | (rd << 12) | rm


def i_sub_imm(rd, rn, imm8, cond=AL):
    return (cond << 28) | 0x02400000 | (rn << 16) | (rd << 12) | (imm8 & 0xFF)


def i_add_imm(rd, rn, imm8, cond=AL):
    return (cond << 28) | 0x02800000 | (rn << 16) | (rd << 12) | (imm8 & 0xFF)


def i_add_reg(rd, rn, rm, cond=AL):
    return (cond << 28) | 0x00800000 | (rn << 16) | (rd << 12) | rm


def i_cmp_imm(rn, imm8, cond=AL):
    return (cond << 28) | 0x03500000 | (rn << 16) | (imm8 & 0xFF)


def i_add_reg_lsl(rd, rn, rm, sh, cond=AL):
    return (cond << 28) | 0x00800000 | (rn << 16) | (rd << 12) | (sh << 7) | rm


def _arm_bl(from_off: int, to_ram: int) -> bytes:
    pc = ARM9_RAM + from_off + 8
    imm = ((to_ram - pc) >> 2) & 0xFFFFFF
    return _u32(0xEB000000 | imm)


def _arm_b(from_off: int, to_ram: int) -> bytes:
    pc = ARM9_RAM + from_off + 8
    imm = ((to_ram - pc) >> 2) & 0xFFFFFF
    return _u32(0xEA000000 | imm)


class _LdrLit:
    def __init__(self, rd, cond=AL):
        self.rd, self.cond = rd, cond


def _hooks() -> "Tuple[Dict[str,int], int, bytes]":
    H: Dict[str, list] = {}

    # 1. W_SB: FUN_020178b8 typewriter advance -> r0, preserve r1 (ctx = sb/r9)
    H["W_SB"] = [
        i_ldr_imm(R2, SB, 0x8C),          # r2 = ctx->subst_ptr
        i_cmp_imm(R2, 0),
        i_ldrb_imm(R3, R2, 0, NE),        # if subst_ptr != NULL, r3 = *subst_ptr
        i_cmp_imm(R3, 0, NE),
        i_ldr_imm(R2, SB, 0, EQ),         # if subst_ptr == NULL or *subst_ptr == 0, r2 = *ctx
        i_ldrb_imm(R3, R2, 0),            # r3 = lead
        i_ldrb_imm(R2, R2, 1),            # r2 = trail
        i_sub_imm(R3, R3, 0x81),          # page = lead - 0x81
        i_cmp_imm(R3, 1),
        i_ldrb_imm(R0, SB, 0x0C, HI),     # not 0x81/0x82 -> native advance [sb, #0xc]
        i_bx(LR, HI),
        _LdrLit(R12),
        i_add_reg_lsl(R12, R12, R3, 8),
        i_ldrb_reg(R0, R12, R2),          # r0 = table[page*256 + trail]
        i_cmp_imm(R0, 0),
        i_ldrb_imm(R0, SB, 0x0C, EQ),     # 0 -> untouched JP glyph, use [sb, #0xc]
        i_bx(LR),
    ]

    # 2. W_SL_R0M2 & W_SL_R0: FUN_02017714 instant UI advance -> r0, preserve r1 (ctx = sl/r10)
    H["W_SL_R0M2"] = [
        i_sub_imm(R0, R0, 2),             # r0 = char_ptr (falls through into W_SL_R0)
    ]
    H["W_SL_R0"] = [
        i_ldrb_imm(R3, R0, 0),            # r3 = lead
        i_ldrb_imm(R2, R0, 1),            # r2 = trail
        i_sub_imm(R3, R3, 0x81),
        i_cmp_imm(R3, 1),
        i_ldrb_imm(R0, SL, 0x0C, HI),     # not 0x81/0x82 -> native advance [sl, #0xc]
        i_bx(LR, HI),
        _LdrLit(R12),
        i_add_reg_lsl(R12, R12, R3, 8),
        i_ldrb_reg(R0, R12, R2),
        i_cmp_imm(R0, 0),
        i_ldrb_imm(R0, SL, 0x0C, EQ),     # 0 -> untouched JP glyph, use [sl, #0xc]
        i_bx(LR),
    ]

    # 3. W_OV: FUN_020190d4 direct buffer advance -> r2, preserve r0
    H["W_OV"] = [
        i_ldr_sp(R1, 0x04),
        i_ldrb_imm(R2, R1, 0),            # lead
        i_ldrb_imm(R1, R1, 1),            # trail
        i_sub_imm(R3, R2, 0x81),
        i_cmp_imm(R3, 1),
        i_ldrb_imm(R2, SP, 0x88, HI),     # fallback to caller's param_7 (12 or 8)
        i_bx(LR, HI),
        _LdrLit(R12),
        i_add_reg_lsl(R12, R12, R3, 8),
        i_ldrb_reg(R2, R12, R1),
        i_cmp_imm(R2, 0),
        i_ldrb_imm(R2, SP, 0x88, EQ),     # fallback to caller's param_7 (12 or 8)
        i_bx(LR),
    ]

    # 4. Cutscene / visual string renderer hooks
    H["W_768DC"] = [
        i_ldr_sp(R1, 0x04),
        i_ldrb_imm(R3, R1, 0),
        i_ldrb_imm(R1, R1, 1),
        i_sub_imm(R3, R3, 0x81),
        i_cmp_imm(R3, 1),
        i_add_imm(R0, R4, 0x0C, HI),
        i_bx(LR, HI),
        _LdrLit(R12),
        i_add_reg_lsl(R12, R12, R3, 8),
        i_ldrb_reg(R0, R12, R1),
        i_cmp_imm(R0, 0),
        i_mov_imm(R0, 0x0C, EQ),
        i_add_reg(R0, R4, R0),
        i_bx(LR),
    ]

    H["W_763C8"] = [
        i_ldr_sp(R1, 0x04),
        i_ldrb_imm(R3, R1, 0),
        i_ldrb_imm(R1, R1, 1),
        i_sub_imm(R3, R3, 0x81),
        i_cmp_imm(R3, 1),
        i_add_imm(R0, R7, 0x0C, HI),
        i_bx(LR, HI),
        _LdrLit(R12),
        i_add_reg_lsl(R12, R12, R3, 8),
        i_ldrb_reg(R0, R12, R1),
        i_cmp_imm(R0, 0),
        i_mov_imm(R0, 0x0C, EQ),
        i_add_reg(R0, R7, R0),
        i_bx(LR),
    ]

    H["W_75348_A"] = [
        i_ldr_sp(R1, 0x18),
        i_ldrb_imm(R3, R1, 0),
        i_ldrb_imm(R1, R1, 1),
        i_sub_imm(R3, R3, 0x81),
        i_cmp_imm(R3, 1),
        i_add_imm(R0, R5, 0x0C, HI),
        i_bx(LR, HI),
        _LdrLit(R12),
        i_add_reg_lsl(R12, R12, R3, 8),
        i_ldrb_reg(R0, R12, R1),
        i_cmp_imm(R0, 0),
        i_mov_imm(R0, 0x0C, EQ),
        i_add_reg(R0, R5, R0),
        i_bx(LR),
    ]

    H["W_75348_B"] = [
        i_ldr_sp(R1, 0x04),
        i_ldrb_imm(R3, R1, 0),
        i_ldrb_imm(R1, R1, 1),
        i_sub_imm(R3, R3, 0x81),
        i_cmp_imm(R3, 1),
        i_add_imm(R0, R5, 0x0C, HI),
        i_bx(LR, HI),
        _LdrLit(R12),
        i_add_reg_lsl(R12, R12, R3, 8),
        i_ldrb_reg(R0, R12, R1),
        i_cmp_imm(R0, 0),
        i_mov_imm(R0, 0x0C, EQ),
        i_add_reg(R0, R5, R0),
        i_bx(LR),
    ]

    H["W_75B08"] = [
        i_ldr_sp(R1, 0x04),
        i_ldrb_imm(R3, R1, 0),
        i_ldrb_imm(R1, R1, 1),
        i_sub_imm(R3, R3, 0x81),
        i_cmp_imm(R3, 1),
        i_ldrb_imm(R1, SL, 0x07, HI),
        i_bx(LR, HI),
        _LdrLit(R12),
        i_add_reg_lsl(R12, R12, R3, 8),
        i_ldrb_reg(R1, R12, R1),
        i_cmp_imm(R1, 0),
        i_ldrb_imm(R1, SL, 0x07, EQ),
        i_bx(LR),
    ]

    order = [
        "W_SB", "W_SL_R0M2", "W_SL_R0", "W_OV",
        "W_768DC", "W_763C8", "W_75348_A", "W_75348_B", "W_75B08",
    ]
    off = HOOK_BASE
    starts: Dict[str, int] = {}
    for name in order:
        starts[name] = off
        off += len(H[name]) * 4
    lit_off = off
    table_off = lit_off + 4
    if (table_off + WIDTH_TABLE_LEN) - HOOK_BASE > 1140:
        raise SystemExit("VWF hooks + table exceed free arena")

    table_ram = ARM9_RAM + table_off
    blob = bytearray()
    for name in order:
        cur = starts[name]
        for w in H[name]:
            if isinstance(w, _LdrLit):
                imm = lit_off - (cur + 8)
                assert 0 <= imm < 0x1000 and imm % 4 == 0, imm
                blob += _u32((w.cond << 28) | 0x059F0000 | (w.rd << 12) | imm)
            else:
                blob += _u32(w)
            cur += 4
    blob += _u32(table_ram)
    return starts, table_off, bytes(blob)


def default_width_table() -> bytes:
    return bytes([0x00] * WIDTH_TABLE_LEN)


def _table_from_widths(width_table: "Dict[Tuple[int,int],int] | None") -> bytes:
    if not width_table:
        return default_width_table()
    tbl = bytearray([0x00] * WIDTH_TABLE_LEN)
    for (lead, trail), w in width_table.items():
        if lead == 0x81:
            tbl[trail & 0xFF] = w & 0xFF
        elif lead == 0x82:
            tbl[256 + (trail & 0xFF)] = w & 0xFF
    return bytes(tbl)


def patch_arm9(arm9: bytearray,
               width_table: "Dict[Tuple[int,int],int] | None" = None) -> List[str]:
    log: List[str] = []
    starts, table_off, blob = _hooks()
    tbl = _table_from_widths(width_table)
    arm9[HOOK_BASE:HOOK_BASE + len(blob)] = blob
    arm9[table_off:table_off + len(tbl)] = tbl
    log.append(f"hooks @0x{HOOK_BASE:X} ({len(blob)}B) + width table @0x{table_off:X} "
               f"(512B)")

    w_sb      = ARM9_RAM + starts["W_SB"]
    w_sl_r0m2 = ARM9_RAM + starts["W_SL_R0M2"]
    w_sl_r0   = ARM9_RAM + starts["W_SL_R0"]
    w_ov      = ARM9_RAM + starts["W_OV"]
    w_768dc   = ARM9_RAM + starts["W_768DC"]
    w_763c8   = ARM9_RAM + starts["W_763C8"]
    w_75348_a = ARM9_RAM + starts["W_75348_A"]
    w_75348_b = ARM9_RAM + starts["W_75348_B"]
    w_75b08   = ARM9_RAM + starts["W_75B08"]

    def put(off, raw, note):
        old = bytes(arm9[off:off + len(raw)])
        arm9[off:off + len(raw)] = raw
        log.append(f"0x{off:X}: {old.hex()} -> {raw.hex()} ({note})")

    # 1. FUN_020178b8 (.scs typewriter dialogue renderer)
    put(SITE_TW_SKIP, _arm_b(SITE_TW_SKIP, 0x02017C68), "typewriter: skip digit check -> 0x02017C68")
    put(SITE_TW_ADV,  _arm_bl(SITE_TW_ADV, w_sb),       "typewriter adv: width->r0")

    # 2. FUN_02017714 (instant UI/menu/battle renderer)
    put(SITE_UI_SKIP,  _arm_b(SITE_UI_SKIP, 0x0201785C), "instant UI: skip digit check -> 0x0201785C")
    put(SITE_UI_ADV_A, _arm_bl(SITE_UI_ADV_A, w_sl_r0),   "instant UI subst adv: width->r0")
    put(SITE_UI_ADV_B, _arm_bl(SITE_UI_ADV_B, w_sl_r0m2), "instant UI main adv: width->r0")

    # 3. FUN_020190d4 (ov_wrapper direct buffer renderer)
    put(SITE_WIDTH_OV, _arm_bl(SITE_WIDTH_OV, w_ov), "ov adv: width->r2")

    # 4. Cutscene / visual string renderers (Overlay 3 subtitles & FMVs)
    put(SITE_768DC,   _arm_bl(SITE_768DC,   w_768dc),   "visual adv 768DC: width->r0")
    put(SITE_763C8,   _arm_bl(SITE_763C8,   w_763c8),   "visual adv 763C8: width->r0")
    put(SITE_75348_A, _arm_bl(SITE_75348_A, w_75348_a), "visual adv 75348 A: width->r0")
    put(SITE_75348_B, _arm_bl(SITE_75348_B, w_75348_b), "visual adv 75348 B: width->r0")
    put(SITE_75B08,       _arm_bl(SITE_75B08,   w_75b08),   "visual adv 75B08: width->r1")
    put(SITE_75B08_SPEED, _u32(0xE3A04001),                 "visual 75B08 speed: mov r4, #1 (delay=1)")
    return log


def apply_to_rom(rom: bytearray, arm9_rom_off: int, arm9_size: int,
                 width_table: "Dict[Tuple[int,int],int] | None" = None) -> List[str]:
    arm9 = bytearray(rom[arm9_rom_off:arm9_rom_off + arm9_size])
    log = patch_arm9(arm9, width_table)
    rom[arm9_rom_off:arm9_rom_off + arm9_size] = arm9
    return log

