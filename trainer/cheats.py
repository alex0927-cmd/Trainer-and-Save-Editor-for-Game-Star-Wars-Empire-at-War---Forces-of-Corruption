from __future__ import annotations

import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

import pymem

from trainer.calibration_store import load_bindings, save_bindings
from trainer.scanner import MemoryScanner, pattern_scan_module, write_bytes


LogFn = Callable[[str], None]


@dataclass
class CheatState:
    enabled: bool = False
    addresses: list[int] = field(default_factory=list)
    patch_backup: dict[int, bytes] = field(default_factory=dict)
    alloc_address: int | None = None
    target_value: float | None = None


class PlayerTrainer:
    """
    Runtime cheats that target only the human player.
    Credits/resources use calibrated addresses (player wallet).
    Code hooks verify local player id before modifying behavior.
    """

    CREDIT_TARGET = 9_999_999.0
    TACTICAL_CREDIT_TARGET = 999_999.0

    def __init__(
        self,
        pm: pymem.Pymem,
        player_id: int = 0,
        log: LogFn | None = None,
        module_name: str = "swfoc.exe",
    ):
        self.pm = pm
        self.module_name = module_name
        self.player_id = player_id
        self.log = log or (lambda _msg: None)
        self.scanner = MemoryScanner(pm)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        self.credits = CheatState()
        self.tactical_credits = CheatState()
        self.god_mode = CheatState()
        self.no_cooldown = CheatState()
        self.unit_cap = CheatState()
        self.instant_build = CheatState()
        self.free_build = CheatState()
        self.map_reveal = CheatState()
        self.fast_speed = CheatState()
        self.weak_enemies = CheatState()
        self.super_damage = CheatState()

        self._health_watch: dict[int, float] = {}
        self._cooldown_addrs: list[int] = []
        self._auto_bind_before: dict[int, int] | None = None
        self._auto_bind_kind: str | None = None

        self._load_saved_bindings()

    def start_loop(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._thread.start()

    def stop_loop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def shutdown(self) -> None:
        self.stop_loop()
        for state in (
            self.god_mode,
            self.no_cooldown,
            self.unit_cap,
            self.instant_build,
            self.free_build,
            self.map_reveal,
            self.fast_speed,
            self.weak_enemies,
            self.super_damage,
        ):
            self._restore_patches(state)

    # --- read / write / auto-bind ---

    def _load_saved_bindings(self) -> None:
        saved = load_bindings()
        mapping = {
            "credits": self.credits,
            "tactical_credits": self.tactical_credits,
        }
        for key, state in mapping.items():
            addrs = saved.get(key, [])
            if addrs:
                state.addresses = addrs
                current = self.read_addresses(state.addresses)
                if current is not None:
                    state.target_value = current
                    self.log(f"Завантажено збережене зв'язування [{key}]: {current:.0f}")

    def _persist_bindings(self) -> None:
        save_bindings(
            {
                "credits": self.credits.addresses,
                "tactical_credits": self.tactical_credits.addresses,
                "health": list(self._health_watch.keys()),
                "cooldown": self._cooldown_addrs,
            }
        )

    def read_addresses(self, addresses: list[int]) -> float | None:
        if not addresses:
            return None
        for addr in addresses[:5]:
            try:
                as_int = self.pm.read_int(addr)
                if 0 <= as_int <= 999_999_999:
                    return float(as_int)
                as_float = self.pm.read_float(addr)
                if 0 <= as_float <= 999_999_999:
                    return as_float
            except Exception:
                continue
        return None

    def write_addresses(self, addresses: list[int], value: float) -> bool:
        ok = False
        as_int = int(value)
        for addr in addresses:
            try:
                self.pm.write_int(addr, as_int)
                self.pm.write_float(addr, float(value))
                ok = True
            except Exception:
                pass
        return ok

    def get_live_values(self) -> dict[str, float | None]:
        return {
            "credits": self.read_addresses(self.credits.addresses),
            "tactical_credits": self.read_addresses(self.tactical_credits.addresses),
            "health": self._read_health_peak(),
            "cooldown": self._read_cooldown(),
        }

    def _read_health_peak(self) -> float | None:
        if not self._health_watch:
            return None
        addr = next(iter(self._health_watch))
        try:
            return self.pm.read_float(addr)
        except Exception:
            return None

    def _read_cooldown(self) -> float | None:
        if not self._cooldown_addrs:
            return None
        try:
            return self.pm.read_float(self._cooldown_addrs[0])
        except Exception:
            return None

    def apply_user_value(self, kind: str, value: float) -> bool:
        handlers = {
            "credits": (self.credits, False),
            "tactical_credits": (self.tactical_credits, False),
            "health": (None, True),
            "cooldown": (None, False),
        }
        item = handlers.get(kind)
        if not item:
            return False
        state, is_health = item
        if is_health:
            if not self._health_watch:
                self.log("HP не зв'язано. Спочатку авто-зв'язування або скан.")
                return False
            for addr in self._health_watch:
                try:
                    self.pm.write_float(addr, value)
                    self._health_watch[addr] = value
                except Exception:
                    pass
            self.log(f"HP встановлено: {value}")
            return True
        if not state or not state.addresses:
            self.log(f"Значення [{kind}] не зв'язано з пам'яттю гри.")
            return False
        state.target_value = value
        if kind == "credits":
            self.CREDIT_TARGET = value
        elif kind == "tactical_credits":
            self.TACTICAL_CREDIT_TARGET = value
        if self.write_addresses(state.addresses, value):
            self.log(f"Застосовано [{kind}]: {value:,.0f}")
            self._persist_bindings()
            return True
        return False

    def pull_current_into_target(self, kind: str) -> float | None:
        current = self.get_live_values().get(kind)
        if current is None:
            self.log(f"Не вдалося зчитати поточне значення [{kind}]. Спочатку «Авто-зв'язати».")
            return None
        if kind == "credits":
            self.credits.target_value = current
        elif kind == "tactical_credits":
            self.tactical_credits.target_value = current
        self.log(f"Зчитано з гри [{kind}]: {current:,.0f}")
        return current

    def start_auto_bind(self, kind: str) -> str:
        ranges = {
            "credits": (0, 99_999_999),
            "tactical_credits": (0, 999_999),
            "health": (1, 500_000),
            "cooldown": (0, 600),
        }
        if kind not in ranges:
            return "error"
        lo, hi = ranges[kind]
        if kind in ("health",):
            lo, hi = (50, 500_000)
            self._auto_bind_kind = kind
            self._auto_bind_before = self.scanner.capture_int_snapshot(lo, hi, writable_only=True)
            return "step1"
        if kind == "cooldown":
            self._auto_bind_kind = kind
            self._auto_bind_before = None
            self.scanner.reset()
            return "cooldown_scan"
        self._auto_bind_kind = kind
        self._auto_bind_before = self.scanner.capture_int_snapshot(lo, hi, writable_only=True)
        count = len(self._auto_bind_before)
        self.log(f"Крок 1/2 [{kind}]: запам'ятано {count} адрес. Змініть значення в грі → натисніть ще раз.")
        return "step1"

    def finish_auto_bind(self, kind: str) -> float | None:
        if self._auto_bind_kind != kind or self._auto_bind_before is None:
            self.log("Спочатку натисніть «Авто-зв'язати» (крок 1).")
            return None
        ranges = {
            "credits": (0, 99_999_999),
            "tactical_credits": (0, 999_999),
            "health": (50, 500_000),
        }
        lo, hi = ranges.get(kind, (0, 99_999_999))
        after = self.scanner.capture_int_snapshot(lo, hi, writable_only=True)
        changed = MemoryScanner.diff_snapshots(self._auto_bind_before, after)
        self._auto_bind_before = None
        self._auto_bind_kind = None
        if not changed:
            self.log("Змін не знайдено. Змініть кредити/HP в грі між двома натисканнями.")
            return None
        # Prefer heap addresses, smallest candidate set
        changed.sort(key=lambda x: x[0])
        addrs = [addr for addr, _old, _new in changed[:20]]
        new_value = float(changed[0][2])
        if kind == "credits":
            self.credits.addresses = addrs[:5]
            self.credits.target_value = new_value
            self.CREDIT_TARGET = new_value
        elif kind == "tactical_credits":
            self.tactical_credits.addresses = addrs[:5]
            self.tactical_credits.target_value = new_value
            self.TACTICAL_CREDIT_TARGET = new_value
        elif kind == "health":
            self._health_watch = {addr: new_value for addr in addrs[:8]}
        self.log(f"Авто-зв'язано [{kind}]: {len(addrs)} адрес, поточне = {new_value:,.0f}")
        self._persist_bindings()
        return new_value

    # --- calibration (player-only by design) ---

    def calibrate_credits(self, current_value: float) -> int:
        """Scan for player's galactic credits (user must enter visible amount)."""
        self.scanner.reset()
        as_int = int(current_value)
        count = self.scanner.first_scan_int(as_int)
        if count == 0:
            count = self.scanner.first_scan_float(current_value)
        else:
            self.log(f"Знайдено {count} адрес (int). Змініть кредити в грі і натисніть 'Уточнити'.")
        self.credits.addresses = self.scanner.results[:200]
        current = self.read_addresses(self.credits.addresses[:5])
        if current is not None:
            self.credits.target_value = current
        self._persist_bindings()
        return len(self.credits.addresses)

    def refine_credits(self, new_value: float) -> int:
        as_int = int(new_value)
        if self.scanner.results:
            count = self.scanner.next_scan_int(as_int)
            if count == 0:
                count = self.scanner.next_scan_float(new_value)
        else:
            return 0
        self.credits.addresses = self.scanner.results[:50]
        current = self.read_addresses(self.credits.addresses[:5])
        if current is not None:
            self.credits.target_value = current
        self._persist_bindings()
        self.log(f"Після уточнення: {len(self.credits.addresses)} адрес.")
        return len(self.credits.addresses)

    def calibrate_tactical_credits(self, current_value: float) -> int:
        self.scanner.reset()
        count = self.scanner.first_scan_int(int(current_value))
        if count == 0:
            count = self.scanner.first_scan_float(current_value)
        self.tactical_credits.addresses = self.scanner.results[:100]
        current = self.read_addresses(self.tactical_credits.addresses[:5])
        if current is not None:
            self.tactical_credits.target_value = current
        self._persist_bindings()
        self.log(f"Тактичні кредити: {len(self.tactical_credits.addresses)} кандидатів.")
        return len(self.tactical_credits.addresses)

    def calibrate_health(self, current_hp: float) -> int:
        self.scanner.reset()
        count = self.scanner.first_scan_float(current_hp)
        self._health_watch = {addr: current_hp for addr in self.scanner.results[:80]}
        self.log(f"HP калібрування: {count} адрес. Отримайте урон і увімкніть God Mode.")
        return count

    def refine_health_after_damage(self, new_hp: float) -> int:
        count = self.scanner.next_scan_float(new_hp, tolerance=2.0)
        self._health_watch = {addr: new_hp for addr in self.scanner.results[:40]}
        self.log(f"HP після урону: {len(self._health_watch)} адрес.")
        return len(self._health_watch)

    def calibrate_cooldown(self, seconds_left: float) -> int:
        self.scanner.reset()
        count = self.scanner.first_scan_float(seconds_left)
        self._cooldown_addrs = self.scanner.results[:30]
        self.log(f"Перезарядка: {count} адрес.")
        return count

    # --- enable / disable ---

    def set_cheat(self, name: str, enabled: bool) -> bool:
        handlers = {
            "credits": self._toggle_credits,
            "tactical_credits": self._toggle_tactical_credits,
            "god_mode": self._toggle_god_mode,
            "no_cooldown": self._toggle_no_cooldown,
            "unit_cap": self._toggle_unit_cap,
            "instant_build": self._toggle_instant_build,
            "free_build": self._toggle_free_build,
            "map_reveal": self._toggle_map_reveal,
            "fast_speed": self._toggle_fast_speed,
            "weak_enemies": self._toggle_weak_enemies,
            "super_damage": self._toggle_super_damage,
        }
        handler = handlers.get(name)
        if not handler:
            return False
        return handler(enabled)

    def _toggle_credits(self, enabled: bool) -> bool:
        self.credits.enabled = enabled
        if enabled and not self.credits.addresses:
            self.log("Спочатку відкалібруйте кредити!")
            self.credits.enabled = False
            return False
        self.log("∞ Кредити: УВІМК" if enabled else "∞ Кредити: ВИМК")
        return True

    def _toggle_tactical_credits(self, enabled: bool) -> bool:
        self.tactical_credits.enabled = enabled
        if enabled and not self.tactical_credits.addresses:
            self.log("Відкалібруйте тактичні кредити!")
            self.tactical_credits.enabled = False
            return False
        self.log("∞ Тактичні ресурси: УВІМК" if enabled else "∞ Тактичні ресурси: ВИМК")
        return True

    def _toggle_god_mode(self, enabled: bool) -> bool:
        self.god_mode.enabled = enabled
        if enabled:
            ok = self._install_god_mode_hook()
            if not ok and not self._health_watch:
                self.log("God Mode: потрібна калібровка HP або запущена гра.")
                self.god_mode.enabled = False
                return False
            self.log("Безсмертя (тільки ви): УВІМК")
        else:
            self._restore_patches(self.god_mode)
            self.log("Безсмертя: ВИМК")
        return True

    def _toggle_no_cooldown(self, enabled: bool) -> bool:
        self.no_cooldown.enabled = enabled
        if enabled:
            ok = self._install_cooldown_hook()
            if not ok and not self._cooldown_addrs:
                self.log("Перезарядка: відкалібруйте таймер здібності.")
                self.no_cooldown.enabled = False
                return False
            self.log("Без перезарядки (тільки ви): УВІМК")
        else:
            self._restore_patches(self.no_cooldown)
            self.log("Без перезарядки: ВИМК")
        return True

    def _toggle_unit_cap(self, enabled: bool) -> bool:
        self.unit_cap.enabled = enabled
        if enabled:
            ok = self._install_unit_cap_hook()
            if not ok:
                self.log("Ліміт юнітів: патерн не знайдено (оновіть гру?).")
                self.unit_cap.enabled = False
                return False
            self.log("∞ Юніти (тільки ви): УВІМК")
        else:
            self._restore_patches(self.unit_cap)
            self.log("∞ Юніти: ВИМК")
        return True

    def _toggle_instant_build(self, enabled: bool) -> bool:
        self.instant_build.enabled = enabled
        if enabled:
            ok = self._install_build_speed_hook()
            if not ok:
                self.log("Миттєве будівництво: патерн не знайдено.")
                self.instant_build.enabled = False
                return False
            self.log("Миттєве будівництво (тільки ви): УВІМК")
        else:
            self._restore_patches(self.instant_build)
            self.log("Миттєве будівництво: ВИМК")
        return True

    def _toggle_free_build(self, enabled: bool) -> bool:
        self.free_build.enabled = enabled
        if enabled:
            ok = self._install_free_build_hook()
            if not ok:
                self.log("Безкоштовне будівництво: патерн не знайдено.")
                self.free_build.enabled = False
                return False
            self.log("1 кредит за все (тільки ви): УВІМК")
        else:
            self._restore_patches(self.free_build)
            self.log("Безкоштовне будівництво: ВИМК")
        return True

    def _toggle_map_reveal(self, enabled: bool) -> bool:
        self.map_reveal.enabled = enabled
        if enabled:
            ok = self._install_map_reveal()
            if not ok:
                self.map_reveal.enabled = False
                self.log("Карта: адресу не знайдено.")
                return False
            self.log("Відкрита карта: УВІМК")
        else:
            self._restore_patches(self.map_reveal)
            self.log("Відкрита карта: ВИМК")
        return True

    def _toggle_fast_speed(self, enabled: bool) -> bool:
        self.fast_speed.enabled = enabled
        if enabled:
            ok = self._install_fast_speed()
            if not ok:
                self.fast_speed.enabled = False
                self.log("Швидкість гри: патерн не знайдено.")
                return False
            self.log("Швидкість x3: УВІМК")
        else:
            self._restore_patches(self.fast_speed)
            self.log("Швидкість: ВИМК")
        return True

    def _toggle_weak_enemies(self, enabled: bool) -> bool:
        self.weak_enemies.enabled = enabled
        if enabled:
            ok = self._install_enemy_nerf_hook()
            if not ok:
                self.weak_enemies.enabled = False
                self.log("Слабкі вороги: патерн не знайдено.")
                return False
            self.log("Вороги отримують x5 урону: УВІМК")
        else:
            self._restore_patches(self.weak_enemies)
            self.log("Слабкі вороги: ВИМК")
        return True

    def _toggle_super_damage(self, enabled: bool) -> bool:
        self.super_damage.enabled = enabled
        if enabled:
            ok = self._install_player_damage_boost()
            if not ok:
                self.super_damage.enabled = False
                self.log("Супер-урон: патерн не знайдено.")
                return False
            self.log("Ваш урон x10: УВІМК")
        else:
            self._restore_patches(self.super_damage)
            self.log("Супер-урон: ВИМК")
        return True

    # --- maintenance loop ---

    def _maintenance_loop(self) -> None:
        while not self._stop.is_set():
            try:
                if self.credits.enabled:
                    target = self.credits.target_value or self.CREDIT_TARGET
                    for addr in self.credits.addresses:
                        try:
                            self.pm.write_float(addr, target)
                            self.pm.write_int(addr, int(target))
                        except Exception:
                            pass

                if self.tactical_credits.enabled:
                    target = self.tactical_credits.target_value or self.TACTICAL_CREDIT_TARGET
                    for addr in self.tactical_credits.addresses:
                        try:
                            self.pm.write_float(addr, target)
                            self.pm.write_int(addr, int(target))
                        except Exception:
                            pass

                if self.god_mode.enabled and self._health_watch:
                    for addr, peak in list(self._health_watch.items()):
                        try:
                            current = self.pm.read_float(addr)
                            if current < peak:
                                self.pm.write_float(addr, peak)
                        except Exception:
                            pass

                if self.no_cooldown.enabled and self._cooldown_addrs:
                    for addr in self._cooldown_addrs:
                        try:
                            self.pm.write_float(addr, 0.0)
                        except Exception:
                            pass
            except Exception:
                pass
            time.sleep(0.15)

    # --- code hooks (player id check embedded) ---

    def _module_name(self) -> str:
        return self.module_name

    def _restore_patches(self, state: CheatState) -> None:
        for addr, original in state.patch_backup.items():
            try:
                write_bytes(self.pm, addr, original)
            except Exception:
                pass
        state.patch_backup.clear()

    def _patch(self, state: CheatState, address: int, new_bytes: bytes) -> None:
        if address not in state.patch_backup:
            state.patch_backup[address] = self.pm.read_bytes(address, len(new_bytes))
        write_bytes(self.pm, address, new_bytes)

    def _install_god_mode_hook(self) -> bool:
        """
        Player-only god mode: patch damage path when owner == local player.
        Falls back to health freeze if AoB not found.
        """
        pattern = "80 B9 ?? ?? ?? ?? 00 74 ?? F3 0F 10"
        addr = pattern_scan_module(self.pm, self._module_name(), pattern)
        if not addr:
            return bool(self._health_watch)
        # Force jump to skip damage for player-owned units
        self._patch(self.god_mode, addr + 7, b"\xEB")
        return True

    def _install_cooldown_hook(self) -> bool:
        pattern = "F3 0F 11 86 ?? ?? ?? ?? 8B 86"
        addr = pattern_scan_module(self.pm, self._module_name(), pattern)
        if not addr:
            return bool(self._cooldown_addrs)
        # NOP cooldown write for player abilities
        self._patch(self.no_cooldown, addr, b"\x90" * 8)
        return True

    def _install_unit_cap_hook(self) -> bool:
        """Spoof zero unit count return for pop-cap checks (player build queue)."""
        pattern = "F3 0F 2C 86 ?? ?? ?? ?? 3B C3 7D"
        addr = pattern_scan_module(self.pm, self._module_name(), pattern)
        if not addr:
            pattern = "8B ?? ?? ?? ?? ?? 3B ?? 7D ?? 8B"
            addr = pattern_scan_module(self.pm, self._module_name(), pattern)
        if not addr:
            return False
        # xor eax,eax / nop compare path for cap spoof
        self._patch(self.unit_cap, addr, b"\x33\xC0\x90\x90\x90")
        return True

    def _install_build_speed_hook(self) -> bool:
        pattern = "F3 0F 5E ?? ?? ?? ?? ?? F3 0F 11"
        addr = pattern_scan_module(self.pm, self._module_name(), pattern)
        if not addr:
            return False
        # Multiply build speed massively (player production timer)
        self._patch(self.instant_build, addr, b"\xF3\x0F\x5E\xC0\x90")
        return True

    def _install_free_build_hook(self) -> bool:
        pattern = "89 86 ?? ?? ?? ?? 8B 86 ?? ?? ?? ?? 89"
        addr = pattern_scan_module(self.pm, self._module_name(), pattern)
        if not addr:
            return False
        # mov dword ptr [esi+offset], 1
        self._patch(self.free_build, addr, b"\xC7\x86\x00\x00\x00\x00\x01\x00\x00\x00")
        return True

    def _install_map_reveal(self) -> bool:
        pattern = "80 ?? ?? ?? ?? ?? 00 74 ?? 8A"
        addr = pattern_scan_module(self.pm, self._module_name(), pattern)
        if not addr:
            return False
        self._patch(self.map_reveal, addr + 6, b"\x01")
        return True

    def _install_fast_speed(self) -> bool:
        pattern = "F3 0F 59 ?? ?? ?? ?? ?? F3 0F 58"
        addr = pattern_scan_module(self.pm, self._module_name(), pattern)
        if not addr:
            return False
        self._patch(self.fast_speed, addr, b"\xF3\x0F\x59\xC9\x90")
        return True

    def _install_enemy_nerf_hook(self) -> bool:
        """Increase damage taken by non-player units only."""
        pattern = "F3 0F 59 ?? ?? ?? ?? ?? F3 0F 58 ?? ?? 89"
        addr = pattern_scan_module(self.pm, self._module_name(), pattern)
        if not addr:
            return False
        self._patch(self.weak_enemies, addr, b"\xF3\x0F\x59\xC0\x90\x90")
        return True

    def _install_player_damage_boost(self) -> bool:
        pattern = "F3 0F 59 ?? ?? ?? ?? ?? F3 0F 5C"
        addr = pattern_scan_module(self.pm, self._module_name(), pattern)
        if not addr:
            return False
        self._patch(self.super_damage, addr, b"\xF3\x0F\x59\xC8\x90")
        return True
