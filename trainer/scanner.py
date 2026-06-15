from __future__ import annotations

import re
import struct
import threading
from dataclasses import dataclass, field

import pymem
import pymem.memory
import pymem.pattern
import pymem.process
import pymem.ressources.structure as mem_struct


@dataclass
class ScanResult:
    addresses: list[int] = field(default_factory=list)


def ce_pattern_to_bytes(pattern: str) -> bytes:
    """Cheat-Engine style 'F3 0F ?? 86' -> regex bytes for pymem."""
    parts = pattern.strip().split()
    chunks: list[str] = []
    for part in parts:
        if part in ("??", "?"):
            chunks.append(".")
        else:
            chunks.append(re.escape(bytes.fromhex(part).decode("latin1")))
    return "".join(chunks).encode("latin1")


def iter_readable_regions(handle: int, is_64bit: bool) -> list[tuple[int, int]]:
    """Return (base, size) for committed readable regions."""
    limit = 0x7FFFFFFF0000 if is_64bit else 0x7FFF0000
    allowed = {
        mem_struct.MEMORY_PROTECTION.PAGE_READWRITE,
        mem_struct.MEMORY_PROTECTION.PAGE_READONLY,
        mem_struct.MEMORY_PROTECTION.PAGE_WRITECOPY,
        mem_struct.MEMORY_PROTECTION.PAGE_EXECUTE_READ,
        mem_struct.MEMORY_PROTECTION.PAGE_EXECUTE_READWRITE,
    }
    regions: list[tuple[int, int]] = []
    address = 0
    while address < limit:
        try:
            mbi = pymem.memory.virtual_query(handle, address)
        except Exception:
            break
        next_address = mbi.BaseAddress + mbi.RegionSize
        if (
            mbi.state == mem_struct.MEMORY_STATE.MEM_COMMIT
            and mbi.protect in allowed
            and mbi.RegionSize > 0
        ):
            regions.append((mbi.BaseAddress, mbi.RegionSize))
        if next_address <= address:
            break
        address = next_address
    return regions


class MemoryScanner:
    """Value scanner across all readable process memory (like Cheat Engine)."""

    MAX_RESULTS = 500

    def __init__(self, pm: pymem.Pymem):
        self.pm = pm
        self._results: list[int] = []
        self._lock = threading.Lock()
        self._regions: list[tuple[int, int]] | None = None

    def _get_regions(self) -> list[tuple[int, int]]:
        if self._regions is None:
            self._regions = iter_readable_regions(self.pm.process_handle, bool(self.pm.is_64_bit))
        return self._regions

    def reset(self) -> None:
        with self._lock:
            self._results = []

    @property
    def results(self) -> list[int]:
        with self._lock:
            return list(self._results)

    def first_scan_int(self, value: int) -> int:
        needle = struct.pack("<i", value)
        matches = self._scan_bytes(needle, step=4, align=4)
        with self._lock:
            self._results = matches[: self.MAX_RESULTS]
        return len(self._results)

    def first_scan_float(self, value: float) -> int:
        needle = struct.pack("<f", value)
        matches = self._scan_bytes(needle, step=1, align=1)
        with self._lock:
            self._results = matches[: self.MAX_RESULTS]
        return len(self._results)

    def next_scan_int(self, value: int) -> int:
        matches: list[int] = []
        with self._lock:
            current = list(self._results)
        for addr in current:
            try:
                if self.pm.read_int(addr) == value:
                    matches.append(addr)
            except Exception:
                pass
        with self._lock:
            self._results = matches[: self.MAX_RESULTS]
        return len(self._results)

    def next_scan_float(self, value: float, tolerance: float = 0.5) -> int:
        matches: list[int] = []
        with self._lock:
            current = list(self._results)
        for addr in current:
            try:
                if abs(self.pm.read_float(addr) - value) <= tolerance:
                    matches.append(addr)
            except Exception:
                pass
        with self._lock:
            self._results = matches[: self.MAX_RESULTS]
        return len(self._results)

    def _scan_bytes(self, needle: bytes, step: int, align: int) -> list[int]:
        matches: list[int] = []
        handle = self.pm.process_handle
        for base, size in self._get_regions():
            if size > 64 * 1024 * 1024:
                continue
            try:
                data = pymem.memory.read_bytes(handle, base, size)
            except Exception:
                continue
            offset = 0
            while True:
                idx = data.find(needle, offset)
                if idx == -1:
                    break
                if idx % align == 0:
                    matches.append(base + idx)
                    if len(matches) >= self.MAX_RESULTS:
                        return matches
                offset = idx + step
        return matches

    def capture_int_snapshot(
        self,
        min_value: int,
        max_value: int,
        *,
        max_entries: int = 150_000,
        writable_only: bool = True,
    ) -> dict[int, int]:
        """Snapshot addr->int for auto-bind (change detection)."""
        snapshot: dict[int, int] = {}
        handle = self.pm.process_handle
        writable = {
            mem_struct.MEMORY_PROTECTION.PAGE_READWRITE,
            mem_struct.MEMORY_PROTECTION.PAGE_WRITECOPY,
            mem_struct.MEMORY_PROTECTION.PAGE_EXECUTE_READWRITE,
        }
        for base, size in self._get_regions():
            if size > 8 * 1024 * 1024:
                continue
            if writable_only:
                try:
                    mbi = pymem.memory.virtual_query(handle, base)
                    if mbi.protect not in writable:
                        continue
                except Exception:
                    continue
            try:
                data = pymem.memory.read_bytes(handle, base, size)
            except Exception:
                continue
            for offset in range(0, len(data) - 4, 4):
                value = struct.unpack_from("<i", data, offset)[0]
                if min_value <= value <= max_value:
                    snapshot[base + offset] = value
                    if len(snapshot) >= max_entries:
                        return snapshot
        return snapshot

    @staticmethod
    def diff_snapshots(before: dict[int, int], after: dict[int, int]) -> list[tuple[int, int, int]]:
        changed: list[tuple[int, int, int]] = []
        for addr, old_value in before.items():
            new_value = after.get(addr)
            if new_value is not None and new_value != old_value:
                changed.append((addr, old_value, new_value))
        return changed


def pattern_scan_module(pm: pymem.Pymem, module_name: str, pattern: str) -> int | None:
    try:
        module = pymem.process.module_from_name(pm.process_handle, module_name)
        byte_pattern = ce_pattern_to_bytes(pattern)
        return pymem.pattern.pattern_scan_module(pm.process_handle, module, byte_pattern)
    except Exception:
        return None


def write_bytes(pm: pymem.Pymem, address: int, data: bytes) -> None:
    pm.write_bytes(address, data, len(data))


def read_bytes(pm: pymem.Pymem, address: int, size: int) -> bytes:
    return pm.read_bytes(address, size)
