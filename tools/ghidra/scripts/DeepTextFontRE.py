# Deep RE script for Tengai Makyou II ARM9: text files, .scs/.scb VM, and font system.
# @category Tengai2

import json
from pathlib import Path
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

RAM_BASE = 0x02000000

def _addr(off):
    return currentProgram.getAddressFactory().getAddress(hex(off))

def _decompile(func, timeout=60):
    if func is None:
        return ""
    ifc = DecompInterface()
    ifc.openProgram(currentProgram)
    try:
        res = ifc.decompileFunction(func, timeout, ConsoleTaskMonitor())
        if res and res.decompileCompleted():
            return res.getDecompiledFunction().getC()
    finally:
        ifc.dispose()
    return ""

def _xrefs_to(ram_addr):
    addr = _addr(ram_addr)
    refs = getReferencesTo(addr)
    out = []
    for r in refs:
        fa = r.getFromAddress()
        fn = getFunctionContaining(fa)
        out.append({
            "from": str(fa),
            "type": str(r.getReferenceType()),
            "func": fn.getName() if fn else None,
            "func_entry": str(fn.getEntryPoint()) if fn else None,
        })
    return out

def _xrefs_in_range(start_ram, end_ram):
    out = []
    cur = _addr(start_ram)
    end = _addr(end_ram)
    while cur and cur.compareTo(end) <= 0:
        refs = getReferencesTo(cur)
        for r in refs:
            fa = r.getFromAddress()
            fn = getFunctionContaining(fa)
            out.append({
                "to": str(cur),
                "from": str(fa),
                "type": str(r.getReferenceType()),
                "func": fn.getName() if fn else None,
                "func_entry": str(fn.getEntryPoint()) if fn else None,
            })
        cur = cur.add(1)
    return out

def run():
    fm = currentProgram.getFunctionManager()
    report = {"xrefs": {}, "functions": {}}

    # Key addresses in ARM9:
    # 0x020A1DAC: 'string_work/grph/HalfCharacter_bit.cobj'
    # 0x020A1DD4: 'string_work/grph/font12_GothicW3_bit.cobj'
    # 0x020CF7A8: '/string_work/grph/HalfCharacter_bit.cobj'
    # 0x020CF7D4: '/string_work/grph/font12_GothicW3_bit.cobj'
    # 0x0211FA24: 'string_work/grph/HalfCharacter_bit.cobj'
    # 0x0211FA4C: 'string_work/grph/font12_GothicW3_bit.cobj'
    # 0x020D3C6C..0x020EB4C0: script/ table
    # 0x020EB6CC: font state / table referenced in docs
    # 0x02016A00..0x02019600: text / font rendering functions
    targets = {
        "half_char_1": (0x020A1DA0, 0x020A1E00),
        "half_char_2": (0x020CF7A0, 0x020CF800),
        "half_char_3": (0x0211FA20, 0x0211FA80),
        "script_table_head": (0x020D3C60, 0x020D3D00),
        "script_table_sys": (0x020EB420, 0x020EB4C0),
        "font_state_020EB6CC": (0x020EB6C0, 0x020EB720),
        "menu_files": (0x020CF580, 0x020CF670),
    }

    funcs_to_decomp = set()
    for name, (s, e) in targets.items():
        xr = _xrefs_in_range(s, e)
        report["xrefs"][name] = xr
        for r in xr:
            if r["func_entry"]:
                funcs_to_decomp.add(int(r["func_entry"], 16))
            else:
                # check if from address is a pointer inside a table or literal pool
                from_int = int(r["from"], 16)
                xr2 = _xrefs_in_range(from_int - 4, from_int + 4)
                r["indirect_xrefs"] = xr2
                for r2 in xr2:
                    if r2["func_entry"]:
                        funcs_to_decomp.add(int(r2["func_entry"], 16))

    # Also add all functions in the 0x02016000..0x0201A000 and 0x02038000..0x0203B000 ranges
    for rng_s, rng_e in [(0x02016000, 0x0201A000), (0x02038000, 0x0203B000)]:
        fn = getFunctionAfter(_addr(rng_s - 1))
        while fn and fn.getEntryPoint().getOffset() < rng_e:
            funcs_to_decomp.add(fn.getEntryPoint().getOffset())
            fn = getFunctionAfter(fn.getEntryPoint())

    for faddr in sorted(funcs_to_decomp):
        fn = fm.getFunctionAt(_addr(faddr))
        if fn:
            callers = _xrefs_to(faddr)
            report["functions"][hex(faddr)] = {
                "name": fn.getName(),
                "entry": str(fn.getEntryPoint()),
                "callers": callers,
                "decompile": _decompile(fn),
            }

    # tools/ghidra/scripts -> repository root
    out_path = Path(__file__).resolve().parents[3] / "docs" / "ghidra_deep_re.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Wrote", out_path, "with", len(report["functions"]), "functions")

run()
