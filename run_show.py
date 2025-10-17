#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_showtime.py
One-click showcase:
  1) Run pytest -q
  2) Run demo_showcase.py (import and capture output)
Pretty, minimal dependencies (ANSI colors only).

Usage:
  python run_showtime.py
  python run_showtime.py --no-tests
  python run_showtime.py --demo-only
"""

import os
import sys
import time
import subprocess
import io
import contextlib
from datetime import datetime

# ANSI helpers
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDER = "\033[4m"

FG = {
    "gray": "\033[90m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
}

def banner(text, color="cyan"):
    line = "═" * (len(text) + 2)
    print(f"{FG[color]}{BOLD}╔{line}╗{RESET}")
    print(f"{FG[color]}{BOLD}║ {text} ║{RESET}")
    print(f"{FG[color]}{BOLD}╚{line}╝{RESET}")

def step(title, subtitle=None, color="magenta"):
    print(f"\n{FG[color]}{BOLD}▶ {title}{RESET}")
    if subtitle:
        print(f"{FG[color]}{DIM}  {subtitle}{RESET}")

def good(msg): print(f"{FG['green']}✔ {msg}{RESET}")
def warn(msg): print(f"{FG['yellow']}⚠ {msg}{RESET}")
def bad(msg):  print(f"{FG['red']}✘ {msg}{RESET}")
def info(msg): print(f"{FG['blue']}ℹ {msg}{RESET}")

def run_pytest():
    step("Running tests (pytest -q)", "Collect & execute unit tests")
    t0 = time.time()
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q"], capture_output=True, text=True)
        dt = time.time() - t0
        # Stream pretty output
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        if out:
            print(f"{FG['white']}{out}{RESET}")
        if err:
            print(f"{FG['red']}{err}{RESET}")
        code = proc.returncode
        if code == 0:
            good(f"pytest SUCCESS in {dt:.2f}s")
        else:
            bad(f"pytest FAILED with exit code {code} in {dt:.2f}s")
        return code
    except FileNotFoundError:
        bad("pytest not found. Please `pip install pytest`.")
        return 127

def highlight_demo_line(line: str) -> str:
    s = line
    # highlight HTTP calls
    if "GET /" in s or "POST /" in s:
        s = f"{FG['cyan']}{BOLD}{s}{RESET}"
    # highlight status codes
    for code,color in [(" 200 ", "green"), (" 201 ", "green"), (" 4", "yellow"), (" 5", "red")]:
        if code in s:
            s = s.replace(code, f"{FG[color]}{BOLD}{code}{RESET}")
    # warnings
    if "UserWarning" in s or "WARNING" in s:
        s = f"{FG['yellow']}{s}{RESET}"
    # tracebacks
    if "Traceback (most recent call last)" in s:
        s = f"{FG['red']}{BOLD}{s}{RESET}"
    return s

def run_demo_showcase():
    step("Running demo_showcase", "Import and execute demo_showcase.main() with capture")
    t0 = time.time()
    # Ensure project root in import path
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)

    try:
        import demo_showcase
    except Exception as e:
        bad(f"Failed to import demo_showcase.py: {e}")
        return 2

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            demo_showcase.main()
    except SystemExit:
        # Some scripts may call sys.exit(); ignore to keep pretty flow
        pass
    except Exception as e:
        bad(f"Error running demo_showcase.main(): {e}")
        return 3

    out = buf.getvalue().splitlines()
    # Pretty print with highlights
    if not out:
        warn("demo_showcase produced no output.")
    else:
        print()
        for line in out:
            print(highlight_demo_line(line))
    dt = time.time() - t0
    good(f"demo_showcase finished in {dt:.2f}s")
    return 0

def main():
    banner("AI Backend — Showtime")
    info(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    args = set(sys.argv[1:])
    skip_tests = "--no-tests" in args or "--demo-only" in args

    # Step 1: tests
    if not skip_tests:
        rc = run_pytest()
        if rc != 0:
            warn("Tests failed; continuing to run demo_showcase for visibility...")

    # Step 2: demo
    rc2 = run_demo_showcase()

    print()
    banner("Summary")
    if not skip_tests:
        if rc == 0:
            print(f"{FG['green']}Tests: PASS{RESET}")
        else:
            print(f"{FG['red']}Tests: FAIL (exit {rc}){RESET}")
    else:
        print(f"{FG['yellow']}Tests: skipped{RESET}")

    print(f"{FG['green'] if rc2==0 else FG['red']}Demo: {'OK' if rc2==0 else 'ERROR'}{RESET}")
    print()
    info("Done. Tip: use `python run_showtime.py --demo-only` to skip tests.")

if __name__ == "__main__":
    main()
