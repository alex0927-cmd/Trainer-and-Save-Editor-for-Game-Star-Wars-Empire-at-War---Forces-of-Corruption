from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _store_path() -> Path:
    return Path(__file__).resolve().parent.parent / "trainer_hotkeys.json"


def load_hotkeys() -> list[dict[str, str]]:
    path = _store_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("hotkeys", [])
        return [
            {"action": str(item["action"]), "key": str(item["key"])}
            for item in items
            if item.get("action") and item.get("key")
        ]
    except Exception:
        return []


def save_hotkeys(bindings: list[dict[str, str]]) -> None:
    path = _store_path()
    payload: dict[str, Any] = {
        "hotkeys": [{"action": b["action"], "key": b["key"]} for b in bindings if b.get("action") and b.get("key")]
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
