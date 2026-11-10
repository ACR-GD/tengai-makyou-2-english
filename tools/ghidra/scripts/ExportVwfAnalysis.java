// Export VWF / dialogue text-renderer sites from analyzed ARM9.
//@category Tengai2
//@menupath Tools.Tengai2.Export VWF Analysis

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.MemoryBlock;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.LinkedHashMap;
import java.util.Map;

public class ExportVwfAnalysis extends GhidraScript {

    /** ARM9 load address in NDS (matches -loader-baseAddr). */
    private static final long NDS_ARM9_RAM = 0x02000000L;

    private static final Map<String, Long> SITES = new LinkedHashMap<>();

    static {
        SITES.put("dialog_main", 0x02018960L);
        SITES.put("sjis_glyph_index", 0x02018D40L);
        SITES.put("line_reset_site", 0x02018D48L);
        SITES.put("xpos_r5_main", 0x02018D90L);
        SITES.put("wrap_r5_1", 0x02018E98L);
        SITES.put("width_site_1", 0x02018EA4L);
        SITES.put("wrap_r5_2", 0x02019054L);
        SITES.put("width_site_2", 0x02019060L);
        SITES.put("xpos_r5_alt", 0x02018F64L);
        SITES.put("ov_wrapper", 0x020190D4L);
        SITES.put("ov_render_loop", 0x0201930CL);
        SITES.put("ov_xpos_fp", 0x02019340L);
        SITES.put("ov_fp_advance", 0x02019448L);
        SITES.put("ov_wrap_fp", 0x02019450L);
        SITES.put("ov_width_site", 0x0201945CL);
        SITES.put("vwf_hook_arena", 0x0211D188L);
    }

    @Override
    public void run() throws Exception {
        String root = getScriptArgs().length > 0
                ? getScriptArgs()[0]
                : System.getProperty("user.dir");
        File docs = new File(root, "docs");
        docs.mkdirs();
        File mdOut = new File(docs, "ghidra_arm9_vwf.md");

        try (PrintWriter pw = new PrintWriter(new FileWriter(mdOut))) {
            pw.println("# ARM9 VWF — export Ghidra\n");
            pw.println("Programme : `" + currentProgram.getName() + "` @ `"
                    + currentProgram.getImageBase() + "`\n");

            for (Map.Entry<String, Long> e : SITES.entrySet()) {
                dumpSite(pw, e.getKey(), e.getValue());
            }

            pw.println("## Littéraux 0x17A0 (table SJIS)\n");
            int found = 0;
            for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
                Address addr = block.getStart();
                Address end = block.getEnd();
                while (addr != null && addr.compareTo(end) <= 0) {
                    try {
                        int val = currentProgram.getMemory().getInt(addr);
                        if (val == 0x17A0) {
                            Instruction ins = currentProgram.getListing().getInstructionContaining(addr);
                            Function fn = getFunctionContaining(addr);
                            pw.println("- `" + addr + "` in `"
                                    + (fn != null ? fn.getName() : "?") + "` — "
                                    + (ins != null ? ins : "?"));
                            if (++found >= 20) break;
                        }
                    } catch (Exception ex) {
                        // skip unreadable
                    }
                    addr = addr.add(4);
                }
                if (found >= 20) break;
            }
        }

        println("Wrote " + mdOut.getAbsolutePath());
    }

    private void dumpSite(PrintWriter pw, String name, long ram) throws Exception {
        Address addr = toAddr(ram);
        Function func = getFunctionContaining(addr);
        Instruction ins = currentProgram.getListing().getInstructionAt(addr);

        pw.println("## " + name + " (`0x" + Long.toHexString(ram) + "`)\n");
        pw.println("Offset fichier : `0x" + Long.toHexString(fileOffset(ram)) + "`\n");
        if (func != null) {
            pw.println("Fonction : `" + func.getName() + "` @ `" + func.getEntryPoint() + "`\n");
            String dec = decompile(func);
            if (!dec.isEmpty()) {
                pw.println("### Décompilation\n```c\n" + dec + "```\n");
            }
        }
        if (ins != null) {
            pw.println("Instruction : `" + ins + "`\n");
        }
        pw.println("### Désassemblage\n```");
        Address cur = addr;
        for (int i = 0; i < 22 && cur != null; i++) {
            Instruction line = currentProgram.getListing().getInstructionAt(cur);
            if (line == null) break;
            pw.println(line.getAddress() + "  " + line);
            cur = line.getFallThrough();
        }
        pw.println("```\n");
    }

    private long fileOffset(long ram) {
        return ram >= NDS_ARM9_RAM ? ram - NDS_ARM9_RAM : ram;
    }

    private String decompile(Function func) {
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        try {
            DecompileResults res = ifc.decompileFunction(func, 60, monitor);
            if (res != null && res.decompileCompleted()) {
                return res.getDecompiledFunction().getC();
            }
        } finally {
            ifc.dispose();
        }
        return "";
    }
}
