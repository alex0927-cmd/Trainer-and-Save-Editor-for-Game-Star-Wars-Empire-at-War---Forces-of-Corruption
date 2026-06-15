from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

import pymem
import pymem.process

from shared.paths import PROCESS_NAMES

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32


@dataclass
class GameProcess:
    pm: pymem.Pymem
    name: str
    pid: int
    base: int
    is_64bit: bool


def list_game_processes() -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    # enumerate via toolhelp
    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == -1:
        return found

    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
    if kernel32.Process32First(snapshot, ctypes.byref(entry)):
        while True:
            exe = entry.szExeFile.decode("ascii", errors="ignore").lower()
            if exe in PROCESS_NAMES:
                found.append((exe, entry.th32ProcessID))
            if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                break
    kernel32.CloseHandle(snapshot)
    return found


def attach(process_name: str | None = None) -> GameProcess:
    candidates = list_game_processes()
    if not candidates:
        raise RuntimeError(
            "Гра не запущена. Спочатку запустіть swfoc.exe (Forces of Corruption)."
        )

    if process_name:
        candidates = [c for c in candidates if c[0] == process_name.lower()]
        if not candidates:
            raise RuntimeError(f"Процес {process_name} не знайдено.")

    name, pid = candidates[0]
    pm = pymem.Pymem()
    pm.open_process_from_id(pid)

    module = pymem.process.module_from_name(pm.process_handle, name)
    is_64bit = bool(pm.is_64_bit)

    return GameProcess(pm=pm, name=name, pid=pid, base=module.lpBaseOfDll, is_64bit=is_64bit)


def is_window_foreground(pid: int) -> bool:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    proc_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
    return proc_id.value == pid
