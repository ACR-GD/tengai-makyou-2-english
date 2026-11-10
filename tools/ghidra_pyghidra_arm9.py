#!/usr/bin/env python3
"""Open the analyzed ARM9 in PyGhidra (GUI) for interactive RE.

Headless export uses Ghidra analyzeHeadless + ExportVwfAnalysis.java
(see tools/ghidra_analyze_arm9.sh).  PyGhidra pip package currently fails
on Python 3.14; this launcher uses Ghidra's bundled pyghidraRun instead.

Usage:
  python3 tools/ghidra_pyghidra_arm9.py          # open GUI on existing project
  ./tools/ghidra_analyze_arm9.sh --import      # (re)import + analyse + export
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GHIDRA = Path(os.environ.get(
    "GHIDRA_INSTALL",
    "/opt/homebrew/Cellar/ghidra/12.1.1/libexec",
))
PYRUN = GHIDRA / "support" / "pyghidraRun"
PROJ = ROOT / "ghidra" / "projects" / "tengai2_arm9"


def main() -> int:
    if not PYRUN.is_file():
        print(f"pyghidraRun introuvable: {PYRUN}", file=sys.stderr)
        return 1
    if not PROJ.with_suffix(".rep").exists() and not (PROJ.parent / "tengai2_arm9.rep").exists():
        print("Projet Ghidra absent — lancez d'abord:", file=sys.stderr)
        print(f"  {ROOT / 'tools' / 'ghidra_analyze_arm9.sh'} --import", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["GHIDRA_INSTALL_DIR"] = str(GHIDRA)
    # Ouvre Ghidra GUI avec support PyGhidra (projet existant)
    cmd = [str(PYRUN), str(PROJ.parent), "tengai2_arm9"]
    print("Lancement:", " ".join(cmd))
    return subprocess.call(cmd, env=env, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
