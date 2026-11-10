# Export VWF / dialogue text-renderer analysis for Tengai Makyou II ARM9.
# @category Tengai2
# @runtime PyGhidra

"""Headless post-script: dump functions, disassembly and decompiler output
around known VWF patch sites and SJIS glyph-index literals."""

import json
from pathlib import Path

from ghidra.app.decompiler import DecompInterface
from ghidra.program.model.address import AddressSet
from ghidra.util.task import ConsoleTaskMonitor

RAM_BASE = 0x02000000

SITES = {
    "dialog_main": 0x02018960,
    "sjis_glyph_index": 0x02018D40,
    "line_reset_site": 0x02018D48,
    "xpos_r5_main": 0x02018D90,
    "wrap_r5_1": 0x02018E98,
    "width_site_1": 0x02018EA4,
    "wrap_r5_2": 0x02019054,
    "width_site_2": 0x02019060,
    "xpos_r5_alt": 0x02018F64,
    "ov_wrapper": 0x020190D4,
    "ov_render_loop": 0x0201930C,
    "ov_xpos_fp": 0x02019340,
    "ov_fp_advance": 0x02019448,
    "ov_wrap_fp": 0x02019450,
    "ov_width_site": 0x0201945C,
    "vwf_hook_arena": 0x0211D188,
    "literal_17A0": 0x020190FC,  # typical ldr pc,#0x17A0 site
}

OUT = Path(__file__).resolve().parents[3] / "docs" / "ghidra_arm9_vwf.json"
LINES_OUT = Path(__file__).resolve().parents[3] / "docs" / "ghidra_arm9_vwf.md"


def _addr(off: int):
    return currentProgram.getAddressFactory().getAddress(hex(off))


def _disasm_range(start: int, count: int = 24) -> list[str]:
    listing = currentProgram.getListing()
    out = []
    addr = _addr(start)
    for _ in range(count):
        ins = listing.getInstructionAt(addr)
        if ins is None:
            break
        out.append(f"{ins.getAddress()}  {ins}")
        addr = ins.getFallThrough()
        if addr is None:
            break
    return out


def _decompile(func) -> str:
    if func is None:
        return ""
    ifc = DecompInterface()
    ifc.openProgram(currentProgram)
    try:
        res = ifc.decompileFunction(func, 60, ConsoleTaskMonitor())
        if res and res.decompileCompleted():
            return res.getDecompiledFunction().getC()
    finally:
        ifc.dispose()
    return ""


def _find_17a0_refs() -> list[dict]:
    listing = currentProgram.getListing()
    mem = currentProgram.getMemory()
    hits = []
    target = 0x17A0
    for block in mem.getBlocks():
        addr = block.getStart()
        end = block.getEnd()
        while addr and addr.compareTo(end) <= 0:
            try:
                val = currentProgram.getMemory().getInt(addr) & 0xFFFFFFFF
                if val == target:
                    ins = listing.getInstructionContaining(addr)
                    fn = currentProgram.getFunctionManager().getFunctionContaining(addr)
                    hits.append(
                        {
                            "literal_addr": str(addr),
                            "in_function": fn.getName() if fn else None,
                            "instruction": str(ins) if ins else None,
                        }
                    )
            except Exception:
                pass
            addr = addr.add(4)
            if addr is None:
                break
    return hits[:40]


def run():
    fm = currentProgram.getFunctionManager()
    listing = currentProgram.getListing()
    report = {
        "program": currentProgram.getName(),
        "image_base": str(currentProgram.getImageBase()),
        "language": str(currentProgram.getLanguageID()),
        "sites": {},
        "sjis_literal_refs": _find_17a0_refs(),
    }

    seen_funcs = set()

    for name, ram in SITES.items():
        addr = _addr(ram)
        func = fm.getFunctionContaining(addr)
        ins = listing.getInstructionAt(addr)
        entry = {
            "ram": hex(ram),
            "file_offset": hex(ram - RAM_BASE),
            "instruction": str(ins) if ins else None,
            "function": None,
            "function_entry": None,
            "disasm": _disasm_range(ram, 20),
        }
        if func:
            entry["function"] = func.getName()
            entry["function_entry"] = str(func.getEntryPoint())
            fid = str(func.getEntryPoint())
            if fid not in seen_funcs:
                seen_funcs.add(fid)
                entry["decompile"] = _decompile(func)
        report["sites"][name] = entry

    # Functions whose names mention text-like strings from manual RE
    for label, ram in [
        ("FUN_dialog_loop", 0x02018A94),
        ("FUN_ov_text", 0x02019158),
    ]:
        func = fm.getFunctionAt(_addr(ram))
        if func and str(func.getEntryPoint()) not in seen_funcs:
            seen_funcs.add(str(func.getEntryPoint()))
            report["extra_functions"] = report.get("extra_functions", {})
            report["extra_functions"][label] = {
                "entry": str(func.getEntryPoint()),
                "name": func.getName(),
                "decompile": _decompile(func),
            }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md = ["# ARM9 VWF — export Ghidra\n"]
    md.append(f"Programme : `{report['program']}` @ `{report['image_base']}`\n")
    for name, data in report["sites"].items():
        md.append(f"## {name} (`{data['ram']}`)\n")
        if data.get("function"):
            md.append(f"Fonction : `{data['function']}` @ `{data['function_entry']}`\n")
        md.append("```\n" + "\n".join(data["disasm"]) + "\n```\n")
    md.append("## Références littéral 0x17A0 (index SJIS)\n")
    for h in report["sjis_literal_refs"][:15]:
        md.append(f"- `{h['literal_addr']}` in `{h['in_function']}` — `{h['instruction']}`\n")
    LINES_OUT.write_text("".join(md), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"Wrote {LINES_OUT}")


run()
