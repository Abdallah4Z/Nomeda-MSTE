#!/usr/bin/env python3
"""Nomeda — Log Viewer / Tailing Utility
Usage:
    python3 scripts/logs.py              # Show all log paths
    python3 scripts/logs.py tail ser     # Last 20 lines of SER log
    python3 scripts/logs.py tail tts 50  # Last 50 lines of TTS log
    python3 scripts/logs.py watch        # Watch all logs (tail -f style)
    python3 scripts/logs.py watch tts llm  # Watch specific logs
"""

import os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.logging import get_logger, get_all_log_files, print_log_paths, tail_log

LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"

def cmd_tail(component, lines=20):
    """Tail a specific component log."""
    try:
        lines = int(lines)
    except (ValueError, TypeError):
        lines = 20
    print(tail_log(component, lines))

def cmd_watch(components=None):
    """Watch log files in real time."""
    if components:
        if isinstance(components, str):
            components = [components]
    else:
        components = list(get_all_log_files().keys())

    files = {}
    for comp in components:
        fpath = LOG_DIR / f"{comp}.log"
        if fpath.exists():
            files[comp] = {"path": fpath, "pos": fpath.stat().st_size}
        else:
            files[comp] = {"path": fpath, "pos": 0}

    print(f"Watching: {', '.join(files.keys())}")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            for comp, info in files.items():
                path = info["path"]
                if not path.exists():
                    continue
                size = path.stat().st_size
                if size > info["pos"]:
                    with open(path) as f:
                        f.seek(info["pos"])
                        new = f.read()
                    for line in new.strip().split("\n"):
                        print(f"\033[90m[{comp}]\033[0m {line}")
                    info["pos"] = size
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("list", "paths", "ls"):
        print_log_paths()
    elif args[0] == "tail" and len(args) >= 2:
        cmd_tail(args[1], args[2] if len(args) > 2 else 20)
    elif args[0] == "watch":
        cmd_watch(args[1:] if len(args) > 1 else None)
    else:
        print("Usage: python3 scripts/logs.py [list|tail <comp> [lines]|watch [comps...]]")
