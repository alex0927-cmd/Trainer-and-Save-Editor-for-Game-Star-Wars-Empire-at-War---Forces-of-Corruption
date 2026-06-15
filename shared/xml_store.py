from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from shared.paths import xml_dir


@dataclass
class XmlPreset:
    name: str
    description: str
    edits: dict[str, dict[str, str]]


GAMECONSTANTS_PRESETS = {
    "health_space": ("Object_Max_Health_Multiplier_Space", "99999.0"),
    "health_land": ("Object_Max_Health_Multiplier_Land", "99999.0"),
    "credit_cap": ("Credit_Cap_Per_Planet", "999999999.0"),
    "prod_speed": ("Production_Speed_Factor", "100.0"),
    "hero_respawn": ("Default_Hero_Respawn_Time", "1.0"),
    "shield_recharge": ("ShieldRechargeIntervalInSecs", "0.01"),
    "skirmish_min": ("Min_Skirmish_Credits", "999999"),
    "skirmish_max": ("Max_Skirmish_Credits", "999999"),
    "mp_credits": ("MP_Default_Credits", "999999"),
}


def backup_file(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{stamp}")
    shutil.copy2(path, backup)
    return backup


def read_tag(path: Path, tag: str) -> str | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"<{re.escape(tag)}>\s*(.*?)\s*</{re.escape(tag)}>", text, re.S)
    return match.group(1).strip() if match else None


def write_tag(path: Path, tag: str, value: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = rf"(<{re.escape(tag)}>)\s*.*?\s*(</{re.escape(tag)}>)"
    if re.search(pattern, text, re.S):
        text = re.sub(pattern, rf"\g<1>{value}\g<2>", text, count=1, flags=re.S)
    else:
        raise ValueError(f"Тег <{tag}> не знайдено у {path.name}")
    path.write_text(text, encoding="utf-8")


def set_planet_credits(path: Path, value: int) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    new_text, count = re.subn(
        r"(<Planet_Credit_Value>)\d+(</Planet_Credit_Value>)",
        rf"\g<1>{value}\g<2>",
        text,
    )
    path.write_text(new_text, encoding="utf-8")
    return count


def replace_all_tags(path: Path, tag: str, value: str) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    new_text, count = re.subn(
        rf"(<{re.escape(tag)}>)\s*.*?\s*(</{re.escape(tag)}>)",
        rf"\g<1> {value} </{re.escape(tag)}>",
        text,
        flags=re.S,
    )
    path.write_text(new_text, encoding="utf-8")
    return count


def list_xml_files() -> list[Path]:
    folder = xml_dir()
    if not folder.is_dir():
        return []
    return sorted(folder.glob("*.XML")) + sorted(folder.glob("*.xml"))
