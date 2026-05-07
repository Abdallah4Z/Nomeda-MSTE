"""
Nomeda — Unified Logging System
Writes to: data/logs/{component}.log + combined main.log
Usage:
    from modules.logging import get_logger
    log = get_logger("ser")
    log.info("Model loaded")
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Component loggers
COMPONENTS = ["main", "ser", "fer", "stt", "tts", "llm", "rag", "fusion", "video", "voice", "api"]

# Formatters
FILE_FMT = logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(name)-10s | %(message)s",
    datefmt="%H:%M:%S"
)
CONSOLE_FMT = logging.Formatter(
    "\033[36m[%(name)s]\033[0m %(message)s"
)

_LOGGERS = {}

def get_logger(name: str, console: bool = True) -> logging.Logger:
    """Get or create a component logger. Writes to data/logs/{name}.log and combined main.log."""
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(f"nomeda.{name}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Only add handlers once
    if not logger.handlers:
        # Component-specific log file
        comp_log = LOG_DIR / f"{name}.log"
        fh = RotatingFileHandler(str(comp_log), maxBytes=10_000_000, backupCount=3)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(FILE_FMT)
        logger.addHandler(fh)

        # Combined main log (all components)
        main_log = LOG_DIR / "main.log"
        mh = RotatingFileHandler(str(main_log), maxBytes=20_000_000, backupCount=5)
        mh.setLevel(logging.INFO)
        mh.setFormatter(FILE_FMT)
        logger.addHandler(mh)

        # Console output
        if console:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            ch.setFormatter(CONSOLE_FMT)
            logger.addHandler(ch)

    _LOGGERS[name] = logger
    return logger


def get_all_log_files() -> dict:
    """Return dict of {component: log_file_path} for all components."""
    return {name: str(LOG_DIR / f"{name}.log") for name in COMPONENTS}


def print_log_paths():
    """Print all log file locations."""
    print("\n" + "=" * 60)
    print("  Nomeda Log Files")
    print("=" * 60)
    for name in COMPONENTS:
        path = LOG_DIR / f"{name}.log"
        size = path.stat().st_size if path.exists() else 0
        print(f"  {name:10s} → {path}  ({size/1024:.1f} KB)")
    print("=" * 60 + "\n")


def tail_log(component: str, lines: int = 20):
    """Return last N lines of a component log."""
    path = LOG_DIR / f"{component}.log"
    if not path.exists():
        return f"No log for '{component}'"
    with open(path) as f:
        all_lines = f.readlines()
    return "".join(all_lines[-lines:])


if __name__ == "__main__":
    # Test / print paths
    log = get_logger("main")
    log.info("Logging system initialized")
    for comp in COMPONENTS:
        get_logger(comp).debug(f"Logger '{comp}' ready")
    print_log_paths()
