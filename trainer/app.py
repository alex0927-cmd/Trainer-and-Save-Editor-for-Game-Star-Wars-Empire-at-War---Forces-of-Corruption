from __future__ import annotations

import traceback
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from shared.process import attach, list_game_processes
from trainer.cheats import PlayerTrainer
from trainer.file_logger import SessionFileLogger, trainer_root
from trainer.hotkey_store import load_hotkeys, save_hotkeys
from trainer.hotkeys import HotkeyManager, format_key_display

CHEATS = [
    ("credits", "1. Безлімітні кредити (галактика)", "Калібруйте → заморожує лише ваш рахунок"),
    ("tactical_credits", "2. Безлімітні тактичні ресурси", "Кредити в бою / скірміш"),
    ("god_mode", "3. Безсмертя юнітів", "Тільки ваші юніти"),
    ("no_cooldown", "4. Здібності без перезарядки", "Тільки ваші герої"),
    ("unit_cap", "5. Нескінченний ліміт юнітів", "Тільки для гравця"),
    ("instant_build", "6. Миттєве будівництво", "Тільки ваші будівлі"),
    ("free_build", "7. Будівництво за 1 кредит", "Тільки ваші покупки"),
    ("map_reveal", "8. Відкрита карта (Maphack)", "Бачите все"),
    ("fast_speed", "9. Швидкість гри x3", "Прискорює симуляцію"),
    ("weak_enemies", "10. Слабкі вороги (x5 урон)", "Вороги отримують більше урону"),
    ("super_damage", "+ Бонус: ваш урон x10", "Тільки ваші атаки"),
]

VALUE_ROWS = [
    ("credits", "Галактичні кредити", "9999999"),
    ("tactical_credits", "Тактичні кредити", "999999"),
    ("health", "HP юніта", "99999"),
    ("cooldown", "Перезарядка (сек)", "0"),
]

ACTION_LABELS: dict[str, str] = {
    "pull_all": "Оновити все з гри",
}
for key, title, _default in VALUE_ROWS:
    ACTION_LABELS[f"apply:{key}"] = f"Застосувати — {title}"
    ACTION_LABELS[f"pull:{key}"] = f"Зчитати — {title}"
for key, title, _hint in CHEATS:
    ACTION_LABELS[f"toggle:{key}"] = f"Перемкнути — {title}"


def all_action_ids() -> list[str]:
    ids = [f"apply:{k}" for k, _, _ in VALUE_ROWS]
    ids += [f"pull:{k}" for k, _, _ in VALUE_ROWS]
    ids += [f"toggle:{k}" for k, _, _ in CHEATS]
    ids.append("pull_all")
    return ids


class TrainerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("EAW FOC Trainer +10 — тільки для гравця")
        self.geometry("780x820")
        self.minsize(680, 640)
        self.configure(bg="#1a1a2e")

        self.trainer: PlayerTrainer | None = None
        self._vars: dict[str, tk.BooleanVar] = {}
        self._auto_bind_step: dict[str, bool] = {}
        self._live_labels: dict[str, ttk.Label] = {}
        self._target_entries: dict[str, ttk.Entry] = {}
        self._hotkey_labels: dict[str, ttk.Label] = {}
        self._refresh_job: str | None = None
        self._hotkey_manager = HotkeyManager(log=self._log)
        self._hotkey_bindings: list[dict[str, str]] = load_hotkeys()
        self._capture_dialog: tk.Toplevel | None = None
        self._file_logger = SessionFileLogger()
        self._file_log_var = tk.BooleanVar(value=False)
        self._last_live: dict[str, float | None] = {}

        self._build_ui()
        self._refresh_process_list()
        self._reload_hotkeys()
        self._log_event("Трейнер запущено")

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#1a1a2e")
        style.configure("TLabel", background="#1a1a2e", foreground="#eaeaea", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#ffd700")
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TCheckbutton", background="#1a1a2e", foreground="#eaeaea", font=("Segoe UI", 10))
        style.configure("Hotkey.TLabel", foreground="#ffd700", font=("Segoe UI", 9, "bold"))

        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Star Wars: Empire at War — Forces of Corruption", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(
            top,
            text="Усі чити впливають ЛИШЕ на вас. Гарячі клавіші працюють навіть коли гра у фокусі.",
            foreground="#7bed9f",
        ).pack(anchor=tk.W, pady=(4, 8))

        proc_row = ttk.Frame(top)
        proc_row.pack(fill=tk.X, pady=4)
        ttk.Label(proc_row, text="Процес:").pack(side=tk.LEFT)
        self.proc_combo = ttk.Combobox(proc_row, width=28, state="readonly")
        self.proc_combo.pack(side=tk.LEFT, padx=6)
        ttk.Button(proc_row, text="Оновити", command=self._refresh_process_list).pack(side=tk.LEFT)
        ttk.Button(proc_row, text="Підключитися", command=self._connect).pack(side=tk.LEFT, padx=6)

        self.status_label = ttk.Label(top, text="Статус: не підключено", foreground="#ff6b6b")
        self.status_label.pack(anchor=tk.W, pady=4)

        cal = ttk.LabelFrame(
            self,
            text="Значення з гри (поточне оновлюється автоматично → відредагуйте «Бажане» → Застосувати)",
            padding=10,
        )
        cal.pack(fill=tk.X, padx=10, pady=6)

        for key, title, default_target in VALUE_ROWS:
            self._add_value_row(cal, key, title, default_target)

        btn_row = ttk.Frame(cal)
        btn_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btn_row, text="Оновити все з гри", command=self._pull_all_from_game).pack(side=tk.LEFT)
        hk_all = ttk.Label(btn_row, text="—", width=10, style="Hotkey.TLabel")
        hk_all.pack(side=tk.LEFT, padx=4)
        self._hotkey_labels["pull_all"] = hk_all
        ttk.Button(btn_row, text="⌨", width=3, command=lambda: self._start_key_capture("pull_all")).pack(side=tk.LEFT)
        ttk.Label(
            btn_row,
            text="  Авто-зв'язати: змініть значення в грі між двома натисканнями",
            foreground="#888",
        ).pack(side=tk.LEFT, padx=8)

        cheat_frame = ttk.LabelFrame(self, text="Чити (+10)", padding=10)
        cheat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        for key, title, hint in CHEATS:
            var = tk.BooleanVar(value=False)
            self._vars[key] = var
            row = ttk.Frame(cheat_frame)
            row.pack(fill=tk.X, pady=2)
            cb = ttk.Checkbutton(row, text=title, variable=var, command=lambda k=key: self._toggle_cheat(k))
            cb.pack(side=tk.LEFT)
            ttk.Label(row, text=f"  — {hint}", foreground="#888").pack(side=tk.LEFT)
            hk = ttk.Label(row, text="—", width=10, style="Hotkey.TLabel")
            hk.pack(side=tk.RIGHT, padx=(4, 0))
            self._hotkey_labels[f"toggle:{key}"] = hk
            ttk.Button(row, text="⌨", width=3, command=lambda k=key: self._start_key_capture(f"toggle:{k}")).pack(
                side=tk.RIGHT
            )

        hk_frame = ttk.LabelFrame(
            self,
            text="Гарячі клавіші — натисніть ⌨ біля дії або додайте вручну (працює в грі)",
            padding=8,
        )
        hk_frame.pack(fill=tk.X, padx=10, pady=4)

        add_row = ttk.Frame(hk_frame)
        add_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(add_row, text="Дія:").pack(side=tk.LEFT)
        self._hk_action_combo = ttk.Combobox(
            add_row,
            width=42,
            state="readonly",
            values=[ACTION_LABELS[a] for a in all_action_ids()],
        )
        self._hk_action_combo.pack(side=tk.LEFT, padx=6)
        if self._hk_action_combo["values"]:
            self._hk_action_combo.current(0)
        ttk.Button(add_row, text="Назначити клавішу", command=self._start_key_capture_from_combo).pack(side=tk.LEFT, padx=4)
        ttk.Button(add_row, text="Очистити всі", command=self._clear_all_hotkeys).pack(side=tk.LEFT, padx=4)

        self._hk_list = tk.Listbox(
            hk_frame,
            height=5,
            bg="#0f0f1a",
            fg="#ccc",
            selectbackground="#3d3d6b",
            font=("Consolas", 9),
        )
        self._hk_list.pack(fill=tk.X)
        ttk.Button(hk_frame, text="Видалити обране", command=self._delete_selected_hotkey).pack(anchor=tk.W, pady=(4, 0))

        log_frame = ttk.LabelFrame(self, text="Журнал", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        log_top = ttk.Frame(log_frame)
        log_top.pack(fill=tk.X, pady=(0, 4))
        ttk.Checkbutton(
            log_top,
            text="Записувати все у файл",
            variable=self._file_log_var,
            command=self._toggle_file_logging,
        ).pack(side=tk.LEFT)
        self._file_log_path_label = ttk.Label(
            log_top,
            text=f"({trainer_root() / 'trainer.log'})",
            foreground="#888",
            font=("Segoe UI", 8),
        )
        self._file_log_path_label.pack(side=tk.LEFT, padx=8)

        self.log_box = scrolledtext.ScrolledText(
            log_frame, height=6, bg="#0f0f1a", fg="#ccc", font=("Consolas", 9), state=tk.DISABLED
        )
        self.log_box.pack(fill=tk.BOTH, expand=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _add_value_row(self, parent: ttk.Frame, key: str, title: str, default_target: str) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=3)
        ttk.Label(row, text=f"{title}:", width=20).pack(side=tk.LEFT)
        ttk.Label(row, text="Поточне:").pack(side=tk.LEFT)
        live = ttk.Label(row, text="—", width=12, foreground="#7bed9f")
        live.pack(side=tk.LEFT, padx=(2, 10))
        self._live_labels[key] = live
        ttk.Label(row, text="Бажане:").pack(side=tk.LEFT)
        entry = ttk.Entry(row, width=12)
        entry.insert(0, default_target)
        entry.pack(side=tk.LEFT, padx=(2, 6))
        self._target_entries[key] = entry
        ttk.Button(row, text="Зчитати", width=8, command=lambda k=key: self._pull_one(k)).pack(side=tk.LEFT, padx=2)
        hk_pull = ttk.Label(row, text="—", width=8, style="Hotkey.TLabel")
        hk_pull.pack(side=tk.LEFT, padx=1)
        self._hotkey_labels[f"pull:{key}"] = hk_pull
        ttk.Button(row, text="⌨", width=3, command=lambda k=key: self._start_key_capture(f"pull:{k}")).pack(
            side=tk.LEFT, padx=(0, 2)
        )
        ttk.Button(row, text="Застосувати", width=10, command=lambda k=key: self._apply_one(k)).pack(side=tk.LEFT, padx=2)
        hk_apply = ttk.Label(row, text="—", width=8, style="Hotkey.TLabel")
        hk_apply.pack(side=tk.LEFT, padx=1)
        self._hotkey_labels[f"apply:{key}"] = hk_apply
        ttk.Button(row, text="⌨", width=3, command=lambda k=key: self._start_key_capture(f"apply:{k}")).pack(
            side=tk.LEFT, padx=(0, 2)
        )
        ttk.Button(row, text="Авто-зв'язати", width=12, command=lambda k=key: self._auto_bind(k)).pack(side=tk.LEFT, padx=2)

    def _log(self, msg: str, category: str = "LOG") -> None:
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)
        self._file_logger.write(msg, category=category)

    def _log_event(self, msg: str) -> None:
        self._log(msg, category="EVENT")

    def _toggle_file_logging(self) -> None:
        enabled = self._file_log_var.get()
        path = self._file_logger.set_enabled(enabled)
        if enabled:
            self._log_event(f"Запис у файл увімкнено → {path}")
        else:
            self._log_event("Запис у файл вимкнено")

    def _action_id_from_combo(self) -> str | None:
        label = self._hk_action_combo.get()
        for action_id, action_label in ACTION_LABELS.items():
            if action_label == label:
                return action_id
        return None

    def _bindings_as_tuples(self) -> list[tuple[str, str]]:
        return [(b["key"], b["action"]) for b in self._hotkey_bindings]

    def _key_for_action(self, action_id: str) -> str | None:
        for binding in self._hotkey_bindings:
            if binding["action"] == action_id:
                return binding["key"]
        return None

    def _reload_hotkeys(self) -> None:
        self._hotkey_manager.install(self._bindings_as_tuples(), self._on_hotkey_pressed)
        self._refresh_hotkey_displays()

    def _refresh_hotkey_displays(self) -> None:
        action_to_key: dict[str, str] = {}
        for binding in self._hotkey_bindings:
            action_to_key[binding["action"]] = binding["key"]

        for action_id, label in self._hotkey_labels.items():
            key = action_to_key.get(action_id)
            label.configure(text=format_key_display(key) if key else "—")

        self._hk_list.delete(0, tk.END)
        for binding in self._hotkey_bindings:
            action_id = binding["action"]
            title = ACTION_LABELS.get(action_id, action_id)
            self._hk_list.insert(tk.END, f"{format_key_display(binding['key'])}  →  {title}")

    def _set_binding(self, action_id: str, key: str | None) -> None:
        self._hotkey_bindings = [b for b in self._hotkey_bindings if b["action"] != action_id]
        if key:
            self._hotkey_bindings = [b for b in self._hotkey_bindings if b["key"] != key]
            self._hotkey_bindings.append({"action": action_id, "key": key})
        save_hotkeys(self._hotkey_bindings)
        self._reload_hotkeys()
        if key:
            title = ACTION_LABELS.get(action_id, action_id)
            self._log(f"Гаряча клавіша: {format_key_display(key)} → {title}")
        else:
            title = ACTION_LABELS.get(action_id, action_id)
            self._log(f"Гарячу клавішу знято: {title}")

    def _start_key_capture_from_combo(self) -> None:
        action_id = self._action_id_from_combo()
        if action_id:
            self._start_key_capture(action_id)

    def _start_key_capture(self, action_id: str) -> None:
        if self._capture_dialog and self._capture_dialog.winfo_exists():
            return
        title = ACTION_LABELS.get(action_id, action_id)
        dlg = tk.Toplevel(self)
        dlg.title("Назначення клавіші")
        dlg.geometry("420x120")
        dlg.configure(bg="#1a1a2e")
        dlg.transient(self)
        dlg.grab_set()
        self._capture_dialog = dlg
        ttk.Label(
            dlg,
            text=f"Натисніть клавішу для:\n{title}\n(Esc — скасувати, можна з Ctrl/Alt/Shift)",
            justify=tk.CENTER,
        ).pack(expand=True, pady=16)

        def on_done(key: str | None) -> None:
            def finish() -> None:
                if dlg.winfo_exists():
                    dlg.destroy()
                self._capture_dialog = None
                if key:
                    self._set_binding(action_id, key.lower())
                else:
                    self._reload_hotkeys()

            self.after(0, finish)

        self._hotkey_manager.capture_key_async(on_done)

    def _delete_selected_hotkey(self) -> None:
        sel = self._hk_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if 0 <= idx < len(self._hotkey_bindings):
            removed = self._hotkey_bindings.pop(idx)
            save_hotkeys(self._hotkey_bindings)
            self._reload_hotkeys()
            title = ACTION_LABELS.get(removed["action"], removed["action"])
            self._log(f"Видалено: {format_key_display(removed['key'])} → {title}")

    def _clear_all_hotkeys(self) -> None:
        if not self._hotkey_bindings:
            return
        if messagebox.askyesno("Підтвердження", "Очистити всі гарячі клавіші?"):
            self._hotkey_bindings.clear()
            save_hotkeys(self._hotkey_bindings)
            self._reload_hotkeys()
            self._log("Усі гарячі клавіші очищено.")

    def _on_hotkey_pressed(self, action_id: str) -> None:
        title = ACTION_LABELS.get(action_id, action_id)
        self._log_event(f"Гаряча клавіша → {title}")
        self.after(0, lambda: self._execute_hotkey_action(action_id))

    def _execute_hotkey_action(self, action_id: str) -> None:
        if action_id == "pull_all":
            self._pull_all_from_game(silent=True)
            return
        if action_id.startswith("apply:"):
            self._apply_one(action_id.split(":", 1)[1], silent=True)
            return
        if action_id.startswith("pull:"):
            self._pull_one(action_id.split(":", 1)[1], silent=True)
            return
        if action_id.startswith("toggle:"):
            cheat_key = action_id.split(":", 1)[1]
            if cheat_key not in self._vars:
                return
            if not self.trainer:
                self._log("Гаряча клавіша: спочатку підключіться до гри.")
                return
            new_val = not self._vars[cheat_key].get()
            self._vars[cheat_key].set(new_val)
            self._toggle_cheat(cheat_key)
            return

    def _refresh_process_list(self) -> None:
        procs = list_game_processes()
        labels = [f"{name} (PID {pid})" for name, pid in procs]
        self.proc_combo["values"] = labels
        if labels:
            self.proc_combo.current(0)

    def _connect(self) -> None:
        try:
            if self.trainer:
                self.trainer.shutdown()
                self._log_event("Відключено від попереднього процесу")
            proc = attach()
            self.trainer = PlayerTrainer(proc.pm, player_id=0, log=self._log, module_name=proc.name)
            self.trainer.start_loop()
            self.status_label.configure(
                text=f"Статус: підключено до {proc.name} (PID {proc.pid})", foreground="#7bed9f"
            )
            self._log(f"Підключено до {proc.name}, PID={proc.pid}, модуль @ {hex(proc.base)}")
            self._log_event(f"Підключення: {proc.name} PID={proc.pid}")
            self._pull_all_from_game()
            self._start_live_refresh()
        except Exception as exc:
            self._log_event(f"Помилка підключення: {exc}")
            self._file_logger.write(traceback.format_exc(), category="ERROR")
            messagebox.showerror("Помилка", str(exc))
            self.status_label.configure(text="Статус: помилка підключення", foreground="#ff6b6b")

    def _require_trainer(self) -> PlayerTrainer | None:
        if not self.trainer:
            messagebox.showwarning("Увага", "Спочатку підключіться до гри!")
            return None
        return self.trainer

    def _set_entry(self, key: str, value: float) -> None:
        entry = self._target_entries.get(key)
        if not entry:
            return
        entry.delete(0, tk.END)
        if key == "cooldown":
            entry.insert(0, f"{value:.1f}")
        else:
            entry.insert(0, str(int(value)))

    def _get_entry_value(self, key: str, silent: bool = False) -> float | None:
        entry = self._target_entries.get(key)
        if not entry:
            return None
        try:
            return float(entry.get().strip().replace(",", ".").replace(" ", ""))
        except ValueError:
            if silent:
                self._log("Гаряча клавіша: некоректне число в «Бажане».")
            else:
                messagebox.showwarning("Увага", "Введіть коректне число в полі «Бажане».")
            return None

    def _pull_one(self, key: str, silent: bool = False) -> None:
        if not self.trainer:
            if silent:
                self._log("Гаряча клавіша: спочатку підключіться до гри.")
            else:
                self._require_trainer()
            return
        current = self.trainer.pull_current_into_target(key)
        if current is not None:
            self._set_entry(key, current)

    def _pull_all_from_game(self, silent: bool = False) -> None:
        if not self.trainer:
            if silent:
                self._log("Гаряча клавіша: спочатку підключіться до гри.")
            else:
                self._require_trainer()
            return
        live = self.trainer.get_live_values()
        for key in self._live_labels:
            current = live.get(key)
            if current is not None:
                self._set_entry(key, current)
                if key == "credits":
                    self.trainer.credits.target_value = current
                elif key == "tactical_credits":
                    self.trainer.tactical_credits.target_value = current
        self._update_live_labels()

    def _apply_one(self, key: str, silent: bool = False) -> None:
        if not self.trainer:
            if silent:
                self._log("Гаряча клавіша: спочатку підключіться до гри.")
            else:
                self._require_trainer()
            return
        val = self._get_entry_value(key, silent=silent)
        if val is not None:
            self._log_event(f"Застосувати [{key}] = {val}")
            self.trainer.apply_user_value(key, val)

    def _auto_bind(self, key: str) -> None:
        t = self._require_trainer()
        if not t:
            return
        if not self._auto_bind_step.get(key):
            self._log_event(f"Авто-зв'язати [{key}] — крок 1")
            if key == "cooldown":
                val = self._get_entry_value(key)
                if val is None:
                    return
                t.calibrate_cooldown(val)
                current = t.pull_current_into_target(key)
                if current is not None:
                    self._set_entry(key, current)
                self._auto_bind_step[key] = False
                return
            t.start_auto_bind(key)
            self._auto_bind_step[key] = True
            messagebox.showinfo(
                "Авто-зв'язування",
                f"Змініть «{key}» у грі (витратьте/заробіть кредити, отримайте урон тощо),\n"
                "потім натисніть «Авто-зв'язати» ще раз.",
            )
        else:
            self._log_event(f"Авто-зв'язати [{key}] — крок 2")
            current = t.finish_auto_bind(key)
            self._auto_bind_step[key] = False
            if current is not None:
                self._set_entry(key, current)
            self._update_live_labels()

    def _update_live_labels(self) -> None:
        if not self.trainer:
            return
        live = self.trainer.get_live_values()
        for key, label in self._live_labels.items():
            val = live.get(key)
            if val is None:
                label.configure(text="—")
            elif key == "cooldown":
                label.configure(text=f"{val:.1f}")
            else:
                label.configure(text=f"{int(val):,}".replace(",", " "))
            if self._file_logger.enabled:
                prev = self._last_live.get(key)
                if val != prev:
                    if val is None:
                        self._log(f"Live [{key}]: змінилось → —", category="LIVE")
                    elif key == "cooldown":
                        self._log(f"Live [{key}]: {prev} → {val:.1f}", category="LIVE")
                    else:
                        self._log(f"Live [{key}]: {prev} → {int(val)}", category="LIVE")
                self._last_live[key] = val

    def _start_live_refresh(self) -> None:
        self._stop_live_refresh()
        self._tick_live_refresh()

    def _stop_live_refresh(self) -> None:
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
            self._refresh_job = None

    def _tick_live_refresh(self) -> None:
        self._update_live_labels()
        self._refresh_job = self.after(1000, self._tick_live_refresh)

    def _toggle_cheat(self, key: str) -> None:
        t = self._require_trainer()
        if not t:
            self._vars[key].set(False)
            return
        enabled = self._vars[key].get()
        self._log_event(f"Чит [{key}]: {'УВІМК' if enabled else 'ВИМК'}")
        ok = t.set_cheat(key, enabled)
        if not ok:
            self._vars[key].set(False)

    def _on_close(self) -> None:
        self._log_event("Трейнер закривається")
        self._stop_live_refresh()
        self._hotkey_manager.uninstall()
        if self.trainer:
            self.trainer.shutdown()
        self._file_logger.close()
        self.destroy()


def main() -> None:
    app = TrainerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
