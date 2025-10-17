#!/usr/bin/env bash
# run_showtime.sh — convenience wrapper with a bit of flair
set -e

# Colors
c_reset="\033[0m"; c_cyan="\033[96m"; c_bold="\033[1m"
echo -e "${c_cyan}${c_bold}>>> Launching AI Backend Showtime ...${c_reset}"

# Use project local python if available
PYTHON_BIN="${PYTHON_BIN:-python}"

"$PYTHON_BIN" run_show.py "$@"
