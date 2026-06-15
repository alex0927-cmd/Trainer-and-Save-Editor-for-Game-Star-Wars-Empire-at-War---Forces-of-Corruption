from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _store_path() -> Path:
    path = Path(__file__).resolve().parent.parent / "trainer_calibration.json"
    return path


def load_bindings() -> dict[str, list[int]]:
    path = _store_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: [int(x) for x in v] for k, v in data.get("addresses", {}).items()}
    except Exception:
        return {}


def save_bindings(addresses: dict[str, list[int]]) -> None:
    path = _store_path()
    payload: dict[str, Any] = {"addresses": {k: v for k, v in addresses.items() if v}}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
