from __future__ import annotations

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from shared.paths import find_game_root, xml_dir
from shared.xml_store import (
    GAMECONSTANTS_PRESETS,
    backup_file,
    list_xml_files,
    read_tag,
    replace_all_tags,
    set_planet_credits,
    write_tag,
)


class EditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("EAW FOC Game Editor")
        self.geometry("800x700")
        self.minsize(700, 600)
        self.configure(bg="#16213e")

        self.game_root = find_game_root()
        self.xml_path = xml_dir(self.game_root)

        self._fields: dict[str, tk.StringVar] = {}
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#16213e")
        style.configure("TLabel", background="#16213e", foreground="#eaeaea", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#ffd700")

        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Редактор Star Wars: Empire at War — Forces of Corruption", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(
            top,
            text="Редагує XML-файли гри. Для читів лише для гравця використовуйте Trainer.",
            foreground="#7bed9f",
        ).pack(anchor=tk.W, pady=4)

        path_row = ttk.Frame(top)
        path_row.pack(fill=tk.X, pady=4)
        ttk.Label(path_row, text="Папка гри:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=str(self.game_root))
        ttk.Entry(path_row, textvariable=self.path_var, width=55).pack(side=tk.LEFT, padx=6)
        ttk.Button(path_row, text="...", width=3, command=self._browse_root).pack(side=tk.LEFT)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self.tab_economy = ttk.Frame(notebook, padding=10)
        self.tab_combat = ttk.Frame(notebook, padding=10)
        self.tab_prod = ttk.Frame(notebook, padding=10)
        self.tab_factions = ttk.Frame(notebook, padding=10)
        self.tab_planets = ttk.Frame(notebook, padding=10)
        notebook.add(self.tab_economy, text="Економіка")
        notebook.add(self.tab_combat, text="Бойові")
        notebook.add(self.tab_prod, text="Виробництво")
        notebook.add(self.tab_factions, text="Фракції")
        notebook.add(self.tab_planets, text="Планети")

        self._add_field(self.tab_economy, "credit_cap", "Ліміт кредитів на планету", "GAMECONSTANTS.XML")
        self._add_field(self.tab_economy, "skirmish_min", "Мін. кредити (скірміш)", "GAMECONSTANTS.XML")
        self._add_field(self.tab_economy, "skirmish_max", "Макс. кредити (скірміш)", "GAMECONSTANTS.XML")
        self._add_field(self.tab_economy, "planet_income", "Дохід планет (усі)", "PLANETS.XML")

        self._add_field(self.tab_combat, "health_space", "Множник HP (космос)", "GAMECONSTANTS.XML")
        self._add_field(self.tab_combat, "health_land", "Множник HP (суша)", "GAMECONSTANTS.XML")
        self._add_field(self.tab_combat, "hero_respawn", "Час відродження героя (сек)", "GAMECONSTANTS.XML")
        self._add_field(self.tab_combat, "shield_recharge", "Інтервал щитів (сек)", "GAMECONSTANTS.XML")

        self._add_field(self.tab_prod, "prod_speed", "Швидкість виробництва", "GAMECONSTANTS.XML")

        self._add_field(self.tab_factions, "credit_factor", "Множник накопичення кредитів", "FACTIONS.XML")
        self._add_field(self.tab_factions, "maintenance", "Витрати на флот (0=безкоштовно)", "FACTIONS.XML")

        planet_row = ttk.Frame(self.tab_planets)
        planet_row.pack(fill=tk.X, pady=4)
        ttk.Label(planet_row, text="Встановити Planet_Credit_Value для всіх планет:").pack(side=tk.LEFT)
        self.planet_credit_var = tk.StringVar(value="99999")
        ttk.Entry(planet_row, textvariable=self.planet_credit_var, width=12).pack(side=tk.LEFT, padx=6)

        file_frame = ttk.LabelFrame(self, text="XML файли", padding=8)
        file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.file_list = tk.Listbox(file_frame, height=6, bg="#0f0f1a", fg="#ccc", font=("Consolas", 9))
        self.file_list.pack(fill=tk.BOTH, expand=True)
        self._refresh_file_list()

        btn_row = ttk.Frame(self, padding=10)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Завантажити значення", command=self._load_values).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Зберегти зміни", command=self._save).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text="Чит-пресет (макс.)", command=self._apply_cheat_preset).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text="Відновити ваніль", command=self._restore_vanilla_preset).pack(side=tk.LEFT)

        self.log = scrolledtext.ScrolledText(
            self, height=5, bg="#0f0f1a", fg="#aaa", font=("Consolas", 9), state=tk.DISABLED
        )
        self.log.pack(fill=tk.X, padx=10, pady=(0, 10))

    def _add_field(self, parent: ttk.Frame, key: str, label: str, source: str) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text=label, width=35).pack(side=tk.LEFT)
        var = tk.StringVar()
        self._fields[key] = var
        ttk.Entry(row, textvariable=var, width=20).pack(side=tk.LEFT)
        ttk.Label(row, text=f"  [{source}]", foreground="#666").pack(side=tk.LEFT)

    def _log_msg(self, msg: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _browse_root(self) -> None:
        path = filedialog.askdirectory(initialdir=str(self.game_root))
        if path:
            self.game_root = Path(path)
            self.xml_path = xml_dir(self.game_root)
            self.path_var.set(str(self.game_root))
            self._refresh_file_list()
            self._load_values()

    def _refresh_file_list(self) -> None:
        self.file_list.delete(0, tk.END)
        for f in list_xml_files():
            self.file_list.insert(tk.END, f.name)

    def _gc_path(self) -> Path:
        return self.xml_path / "GAMECONSTANTS.XML"

    def _load_values(self) -> None:
        gc = self._gc_path()
        mapping = {
            "credit_cap": "Credit_Cap_Per_Planet",
            "skirmish_min": "Min_Skirmish_Credits",
            "skirmish_max": "Max_Skirmish_Credits",
            "health_space": "Object_Max_Health_Multiplier_Space",
            "health_land": "Object_Max_Health_Multiplier_Land",
            "hero_respawn": "Default_Hero_Respawn_Time",
            "shield_recharge": "ShieldRechargeIntervalInSecs",
            "prod_speed": "Production_Speed_Factor",
        }
        for key, tag in mapping.items():
            val = read_tag(gc, tag)
            if val and key in self._fields:
                self._fields[key].set(val)

        factions = self.xml_path / "FACTIONS.XML"
        if factions.is_file():
            cf = read_tag(factions, "Credits_Accumulation_Factor")
            mc = read_tag(factions, "Maintenance_Cost")
            if cf:
                self._fields["credit_factor"].set(cf)
            if mc:
                self._fields["maintenance"].set(mc)

        planets = self.xml_path / "PLANETS.XML"
        if planets.is_file():
            val = read_tag(planets, "Planet_Credit_Value")
            if val:
                self._fields["planet_income"].set(val)

        self._log_msg("Значення завантажено.")

    def _save(self) -> None:
        try:
            gc = self._gc_path()
            if gc.is_file():
                backup_file(gc)
                tag_map = {
                    "credit_cap": "Credit_Cap_Per_Planet",
                    "skirmish_min": "Min_Skirmish_Credits",
                    "skirmish_max": "Max_Skirmish_Credits",
                    "health_space": "Object_Max_Health_Multiplier_Space",
                    "health_land": "Object_Max_Health_Multiplier_Land",
                    "hero_respawn": "Default_Hero_Respawn_Time",
                    "shield_recharge": "ShieldRechargeIntervalInSecs",
                    "prod_speed": "Production_Speed_Factor",
                }
                for key, tag in tag_map.items():
                    if key in self._fields and self._fields[key].get().strip():
                        write_tag(gc, tag, self._fields[key].get().strip())

            factions = self.xml_path / "FACTIONS.XML"
            if factions.is_file():
                backup_file(factions)
                if self._fields["credit_factor"].get().strip():
                    replace_all_tags(factions, "Credits_Accumulation_Factor", self._fields["credit_factor"].get().strip())
                if self._fields["maintenance"].get().strip():
                    replace_all_tags(factions, "Maintenance_Cost", self._fields["maintenance"].get().strip())

            exp = self.xml_path / "EXPANSION_FACTIONS.XML"
            if exp.is_file():
                backup_file(exp)
                if self._fields["credit_factor"].get().strip():
                    replace_all_tags(exp, "Credits_Accumulation_Factor", self._fields["credit_factor"].get().strip())
                if self._fields["maintenance"].get().strip():
                    replace_all_tags(exp, "Maintenance_Cost", self._fields["maintenance"].get().strip())

            planets = self.xml_path / "PLANETS.XML"
            if planets.is_file():
                backup_file(planets)
                income = self._fields.get("planet_income")
                if income and income.get().strip():
                    set_planet_credits(planets, int(float(income.get().strip())))
                elif self.planet_credit_var.get().strip():
                    set_planet_credits(planets, int(float(self.planet_credit_var.get().strip())))

            messagebox.showinfo("Готово", "XML збережено! Перезапустіть гру.")
            self._log_msg("Збережено успішно.")
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            self._log_msg(f"Помилка: {exc}")

    def _apply_cheat_preset(self) -> None:
        self._fields["credit_cap"].set("999999999.0")
        self._fields["skirmish_min"].set("999999")
        self._fields["skirmish_max"].set("999999")
        self._fields["health_space"].set("99999.0")
        self._fields["health_land"].set("99999.0")
        self._fields["hero_respawn"].set("1.0")
        self._fields["shield_recharge"].set("0.01")
        self._fields["prod_speed"].set("100.0")
        self._fields["credit_factor"].set("100.0")
        self._fields["maintenance"].set("0.0")
        self._fields["planet_income"].set("99999")
        self.planet_credit_var.set("99999")
        self._log_msg("Чит-пресет застосовано до полів. Натисніть 'Зберегти'.")

    def _restore_vanilla_preset(self) -> None:
        self._fields["credit_cap"].set("40000.0")
        self._fields["skirmish_min"].set("2000")
        self._fields["skirmish_max"].set("8000")
        self._fields["health_space"].set("1.5")
        self._fields["health_land"].set("1.0")
        self._fields["hero_respawn"].set("360.0")
        self._fields["shield_recharge"].set("3.0")
        self._fields["prod_speed"].set("1.0")
        self._fields["credit_factor"].set("0.95")
        self._fields["maintenance"].set("0.25")
        self._fields["planet_income"].set("100")
        self.planet_credit_var.set("100")
        self._log_msg("Ванільні значення завантажено. Натисніть 'Зберегти'.")


def main() -> None:
    app = EditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
