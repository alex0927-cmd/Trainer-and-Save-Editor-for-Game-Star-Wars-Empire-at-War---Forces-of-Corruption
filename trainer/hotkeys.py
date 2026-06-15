from __future__ import annotations

import threading
from typing import Callable

import keyboard

LogFn = Callable[[str], None]
ActionHandler = Callable[[str], None]


def format_key_display(key: str) -> str:
    parts = key.split("+")
    labels = {
        "ctrl": "Ctrl",
        "alt": "Alt",
        "shift": "Shift",
        "windows": "Win",
        "space": "Пробіл",
        "enter": "Enter",
        "esc": "Esc",
        "tab": "Tab",
        "backspace": "Backspace",
        "delete": "Delete",
        "up": "↑",
        "down": "↓",
        "left": "←",
        "right": "→",
        "page up": "PgUp",
        "page down": "PgDn",
        "home": "Home",
        "end": "End",
        "insert": "Ins",
    }
    out: list[str] = []
    for part in parts:
        low = part.strip().lower()
        if low in labels:
            out.append(labels[low])
        elif low.startswith("f") and low[1:].isdigit():
            out.append(low.upper())
        elif len(low) == 1:
            out.append(low.upper())
        else:
            out.append(part.capitalize())
    return " + ".join(out)


class HotkeyManager:
    """Глобальні гарячі клавіші (працюють навіть коли гра у фокусі)."""

    def __init__(self, log: LogFn | None = None) -> None:
        self.log = log or (lambda _msg: None)
        self._handles: list = []
        self._handler: ActionHandler | None = None
        self._capture_hook = None
        self._paused = False

    def install(self, bindings: list[tuple[str, str]], on_action: ActionHandler) -> None:
        """bindings: [(key, action_id), ...]"""
        self.uninstall()
        if self._paused:
            self._handler = on_action
            return
        self._handler = on_action
        seen_keys: set[str] = set()
        for key, action_id in bindings:
            norm_key = key.strip().lower()
            if not norm_key or norm_key in seen_keys:
                continue
            seen_keys.add(norm_key)
            try:
                handle = keyboard.add_hotkey(
                    norm_key,
                    lambda a=action_id: self._dispatch(a),
                    suppress=False,
                    trigger_on_release=False,
                )
                self._handles.append(handle)
            except Exception as exc:
                self.log(f"Не вдалося призначити [{format_key_display(norm_key)}]: {exc}")

    def uninstall(self) -> None:
        for handle in self._handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                pass
        self._handles.clear()

    def pause(self) -> None:
        self._paused = True
        self.uninstall()

    def resume(self, bindings: list[tuple[str, str]]) -> None:
        self._paused = False
        if self._handler:
            self.install(bindings, self._handler)

    def _dispatch(self, action_id: str) -> None:
        if self._handler:
            self._handler(action_id)

    def capture_key_async(self, on_done: Callable[[str | None], None]) -> None:
        """Чекає натискання клавіші в окремому потоці. None = скасовано (Esc)."""

        def worker() -> None:
            self.pause()
            self._stop_capture_hook()
            result: str | None = None
            done = threading.Event()

            def hook(event: keyboard.KeyboardEvent) -> None:
                nonlocal result
                if event.event_type != keyboard.KEY_DOWN:
                    return
                if event.name == "esc":
                    result = None
                    done.set()
                    return
                combo = self._event_to_hotkey(event)
                if combo:
                    result = combo
                    done.set()

            self._capture_hook = keyboard.hook(hook, suppress=True)
            done.wait(timeout=30)
            self._stop_capture_hook()
            try:
                on_done(result)
            finally:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _stop_capture_hook(self) -> None:
        if self._capture_hook is not None:
            try:
                keyboard.unhook(self._capture_hook)
            except Exception:
                pass
            self._capture_hook = None

    @staticmethod
    def _event_to_hotkey(event: keyboard.KeyboardEvent) -> str | None:
        name = (event.name or "").strip().lower()
        if not name or name in ("esc",):
            return None
        modifiers: list[str] = []
        if keyboard.is_pressed("ctrl"):
            modifiers.append("ctrl")
        if keyboard.is_pressed("alt"):
            modifiers.append("alt")
        if keyboard.is_pressed("shift"):
            modifiers.append("shift")
        if keyboard.is_pressed("windows"):
            modifiers.append("windows")
        if name in modifiers:
            return None
        parts = modifiers + [name]
        return "+".join(parts)
