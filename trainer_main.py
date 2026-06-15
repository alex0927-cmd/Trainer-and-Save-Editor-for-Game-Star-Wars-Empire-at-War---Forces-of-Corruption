"""
Entry point for PyInstaller and direct launch.
Usage: python trainer_main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from trainer.app import main

if __name__ == "__main__":
    main()
