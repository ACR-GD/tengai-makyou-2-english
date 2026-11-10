#!/usr/bin/env bash
# Ghidra headless: import/analyze Tengai Makyou II ARM9 and export VWF notes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GHIDRA_INSTALL="${GHIDRA_INSTALL:-/opt/homebrew/Cellar/ghidra/12.1.1/libexec}"
HEADLESS="$GHIDRA_INSTALL/support/analyzeHeadless"
ARM9="$ROOT/extracted/__system__/arm9.bin"
PROJ="$ROOT/ghidra/projects"
PROJ_NAME="tengai2_arm9"
SCRIPTS="$ROOT/tools/ghidra/scripts"
LOG="$ROOT/ghidra/headless.log"

export GHIDRA_INSTALL_DIR="$GHIDRA_INSTALL"

mkdir -p "$ROOT/ghidra/projects" "$ROOT/docs"

if [[ ! -f "$ARM9" ]]; then
  echo "Missing $ARM9 — extract ROM first." >&2
  exit 1
fi

IMPORT=0
if [[ "${1:-}" == "--import" ]]; then
  IMPORT=1
  shift
fi

if [[ $IMPORT -eq 1 ]] || [[ ! -d "$PROJ/$PROJ_NAME.rep" ]]; then
  echo "==> Import + analyse ARM9 @ 0x02000000"
  "$HEADLESS" "$PROJ" "$PROJ_NAME" \
    -import "$ARM9" \
    -overwrite \
    -processor ARM:LE:32:v8 \
    -loader BinaryLoader \
    -loader-baseAddr 0x02000000 \
    -analysisTimeoutPerFile 900 \
    -log "$LOG" \
    "$@"
else
  echo "==> Projet existant — export seulement"
fi

echo "==> Export VWF (Java post-script)"
"$HEADLESS" "$PROJ" "$PROJ_NAME" \
  -process arm9.bin \
  -noanalysis \
  -scriptPath "$SCRIPTS" \
  -postScript ExportVwfAnalysis.java "$ROOT" \
  -log "$LOG"

echo "Done. Voir docs/ghidra_arm9_vwf.md et ghidra/headless.log"
