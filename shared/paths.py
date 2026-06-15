from __future__ import annotations

import os
from pathlib import Path


def find_game_root() -> Path:
    """Locate Forces of Corruption data2 folder."""
    env = os.environ.get("EAW_FOC_ROOT")
    if env:
        path = Path(env)
        if (path / "swfoc.exe").is_file():
            return path

    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "data2",
        here.parents[1] / "data2",
        Path(r"C:\Games\Star Wars Empire At War Collection\data2"),
    ]
    for candidate in candidates:
        if (candidate / "swfoc.exe").is_file():
            return candidate

    return candidates[0]


def xml_dir(game_root: Path | None = None) -> Path:
    root = game_root or find_game_root()
    return root / "Data" / "XML"


PROCESS_NAMES = ("swfoc.exe", "sweaw.exe")
